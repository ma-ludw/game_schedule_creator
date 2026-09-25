"""OpenCL implementation of batched schedule generation and scoring."""

from __future__ import annotations

import math
from importlib import import_module
import time
from typing import Any

import numpy as np


class OpenCLUnavailableError(RuntimeError):
    """Raised when a usable OpenCL GPU or program cannot be created."""


_SEARCH_KERNEL = r"""
inline uint next_random(uint *state) {
    uint value = *state;
    value ^= value << 13;
    value ^= value >> 17;
    value ^= value << 5;
    *state = value;
    return value;
}

inline score_t variance_of_counts(__global int *values, uint length) {
    if (length == 0) {
        return (score_t)0;
    }
    score_t sum = (score_t)0;
    for (uint index = 0; index < length; ++index) {
        sum += (score_t)values[index];
    }
    score_t mean = sum / (score_t)length;
    score_t squared_deviations = (score_t)0;
    for (uint index = 0; index < length; ++index) {
        score_t difference = (score_t)values[index] - mean;
        squared_deviations += difference * difference;
    }
    return squared_deviations / (score_t)length;
}

inline score_t variance_with_implicit_zeros(
    __global int *values,
    uint stored_length,
    uint total_length
) {
    if (total_length == 0) {
        return (score_t)0;
    }
    score_t sum = (score_t)0;
    for (uint index = 0; index < stored_length; ++index) {
        sum += (score_t)values[index];
    }
    score_t mean = sum / (score_t)total_length;
    score_t squared_deviations = (score_t)(total_length - stored_length) * mean * mean;
    for (uint index = 0; index < stored_length; ++index) {
        score_t difference = (score_t)values[index] - mean;
        squared_deviations += difference * difference;
    }
    return squared_deviations / (score_t)total_length;
}

__kernel void generate_and_score(
    __global const int *pair_first,
    __global const int *pair_second,
    __global int *schedules,
    __global score_t *costs,
    __global int *scratch,
    const uint team_count,
    const uint game_count,
    const uint round_count,
    const uint pair_count,
    const uint scratch_stride,
    const uint event_count,
    const uint random_seed,
    const uint candidate_count
) {
    uint candidate = get_global_id(0);
    if (candidate >= candidate_count) {
        return;
    }

    __global int *pair_counts = scratch + candidate * scratch_stride;
    __global int *last_pair_cycle = pair_counts + pair_count;
    __global int *game_counts = last_pair_cycle + pair_count;
    __global int *game_team_counts = game_counts + game_count;
    __global int *team_totals = game_team_counts + game_count * team_count;
    __global int *team_last_round = team_totals + team_count;
    __global int *game_order = team_last_round + team_count;
    __global int *schedule = schedules + candidate * event_count * 3;

    for (uint pair = 0; pair < pair_count; ++pair) {
        pair_counts[pair] = 0;
        last_pair_cycle[pair] = -1;
    }
    for (uint game = 0; game < game_count; ++game) {
        game_counts[game] = 0;
    }
    for (uint index = 0; index < game_count * team_count; ++index) {
        game_team_counts[index] = 0;
    }
    for (uint team = 0; team < team_count; ++team) {
        team_totals[team] = 0;
        team_last_round[team] = -1;
    }
    for (uint game = 0; game < game_count; ++game) {
        game_order[game] = (int)game;
    }
    for (uint event = 0; event < event_count * 3; ++event) {
        schedule[event] = -1;
    }

    uint state = random_seed ^ (candidate * 0x9E3779B9u + 0xA511E9B3u);
    if (state == 0) {
        state = 1;
    }
    uint pair_start = pair_count > 0 ? next_random(&state) % pair_count : 0;
    int pair_step = (next_random(&state) & 1u) ? -1 : 1;
    uint maximum_games = min(game_count, team_count / 2);
    uint cycle = 0;
    uint pairs_used_in_cycle = 0;

    for (uint round = 0; round < round_count && pair_count > 0; ++round) {
        for (uint game = 0; game < game_count; ++game) {
            game_order[game] = (int)game;
        }
        for (int game = (int)game_count - 1; game > 0; --game) {
            uint swap_index = next_random(&state) % ((uint)game + 1);
            int value = game_order[game];
            game_order[game] = game_order[swap_index];
            game_order[swap_index] = value;
        }

        uint games_scheduled = 0;
        for (uint pass = 0; pass < 2 && games_scheduled < maximum_games; ++pass) {
            for (uint offset = 0; offset < pair_count; ++offset) {
                if (games_scheduled >= maximum_games) {
                    break;
                }
                int pair_index = (int)pair_start + pair_step * (int)offset;
                if (pair_index < 0) {
                    pair_index += (int)pair_count;
                } else if (pair_index >= (int)pair_count) {
                    pair_index -= (int)pair_count;
                }

                int first_team = pair_first[pair_index];
                int second_team = pair_second[pair_index];
                if (team_last_round[first_team] == (int)round
                    || team_last_round[second_team] == (int)round) {
                    continue;
                }
                if (pass == 0 && last_pair_cycle[pair_index] == (int)cycle) {
                    continue;
                }

                uint game_slot = game_count - 1 - games_scheduled;
                int selected_game = game_order[game_slot];
                uint event_slot = round * game_count + (uint)selected_game;
                schedule[event_slot * 3] = selected_game;
                schedule[event_slot * 3 + 1] = first_team;
                schedule[event_slot * 3 + 2] = second_team;

                team_last_round[first_team] = (int)round;
                team_last_round[second_team] = (int)round;
                if (pass == 0) {
                    last_pair_cycle[pair_index] = (int)cycle;
                    ++pairs_used_in_cycle;
                }
                pair_counts[pair_index] += 1;
                game_counts[selected_game] += 1;
                game_team_counts[selected_game * team_count + (uint)first_team] += 1;
                game_team_counts[selected_game * team_count + (uint)second_team] += 1;
                team_totals[first_team] += 1;
                team_totals[second_team] += 1;
                ++games_scheduled;
            }
        }
        if (pairs_used_in_cycle >= pair_count) {
            ++cycle;
            pairs_used_in_cycle = 0;
        }
    }

    score_t game_variance = variance_of_counts(game_counts, game_count);
    score_t game_team_variance = variance_of_counts(
        game_team_counts,
        game_count * team_count
    );
    score_t team_variance = variance_of_counts(team_totals, team_count);
    uint possible_team_pairs = team_count * (team_count - 1) / 2;
    score_t matchup_variance = variance_with_implicit_zeros(
        pair_counts,
        pair_count,
        possible_team_pairs
    );
    costs[candidate] = game_variance
        + game_team_variance * (score_t)10
        + team_variance * (score_t)10
        + matchup_variance;
}

__kernel void find_best_candidate(
    __global const score_t *costs,
    __global int *best_index,
    __global score_t *best_cost,
    const uint candidate_count
) {
    if (get_global_id(0) != 0) {
        return;
    }
    int selected = 0;
    score_t minimum_cost = costs[0];
    for (uint candidate = 1; candidate < candidate_count; ++candidate) {
        if (costs[candidate] < minimum_cost) {
            selected = (int)candidate;
            minimum_cost = costs[candidate];
        }
    }
    best_index[0] = selected;
    best_cost[0] = minimum_cost;
}

__kernel void gather_best_schedule(
    __global const int *schedules,
    __global const int *best_index,
    __global int *best_schedule,
    const uint event_count
) {
    uint item = get_global_id(0);
    if (item >= event_count * 3) {
        return;
    }
    uint candidate = (uint)best_index[0];
    best_schedule[item] = schedules[candidate * event_count * 3 + item];
}
"""


class OpenCLScheduleSearch:
    """Search batches of candidate schedules entirely on an OpenCL GPU."""

    CANDIDATES_PER_BATCH_LIMIT = 4096
    CANDIDATES_PER_BATCH_WORK_TARGET = 50_000_000
    DEVICE_MEMORY_BUDGET = 256 * 1024 * 1024

    def __init__(
        self,
        pairings: list[tuple[int, int]],
        team_count: int,
        game_count: int,
        round_count: int,
        *,
        device: Any | None = None,
    ) -> None:
        try:
            cl = import_module("pyopencl")
        except ImportError as error:
            raise OpenCLUnavailableError(
                "PyOpenCL is not installed; install requirements-gpu.txt to enable GPU search."
            ) from error

        self._cl = cl
        self.team_count = team_count
        self.game_count = game_count
        self.round_count = round_count
        self.pair_count = len(pairings)
        if not self.pair_count:
            raise OpenCLUnavailableError("GPU search requires at least one valid matchup.")

        try:
            if device is None:
                devices = [
                    candidate
                    for platform in cl.get_platforms()
                    for candidate in platform.get_devices(
                        device_type=cl.device_type.GPU,
                    )
                ]
                if not devices:
                    raise OpenCLUnavailableError(
                        "No OpenCL-compatible GPU was found; using CPU search."
                    )
                device = max(
                    devices,
                    key=lambda candidate: (
                        not bool(getattr(candidate, "host_unified_memory", False)),
                        candidate.max_compute_units * candidate.max_clock_frequency,
                        candidate.global_mem_size,
                    ),
                )
            if device is None:
                raise OpenCLUnavailableError(
                    "No OpenCL-compatible GPU was found; using CPU search."
                )
            self.device = device
            self.context = cl.Context([device])
            self.queue = cl.CommandQueue(self.context)
        except OpenCLUnavailableError:
            raise
        except Exception as error:
            raise OpenCLUnavailableError(
                f"OpenCL initialization failed ({error}); using CPU search."
            ) from error
        extensions = set(self.device.extensions.split())
        if "cl_khr_fp64" in extensions or "cl_amd_fp64" in extensions:
            self.score_dtype = np.float64
            score_type = "double"
            extension_name = (
                "cl_khr_fp64"
                if "cl_khr_fp64" in extensions
                else "cl_amd_fp64"
            )
            extension = f"#pragma OPENCL EXTENSION {extension_name} : enable\n"
        else:
            self.score_dtype = np.float32
            score_type = "float"
            extension = ""
        kernel_source = _SEARCH_KERNEL.replace(
            "inline score_t variance_of_counts",
            f"{extension}typedef {score_type} score_t;\n"
            "inline score_t variance_of_counts",
        )
        try:
            self.program = cl.Program(self.context, kernel_source).build()
            self.generate_kernel = cl.Kernel(
                self.program,
                "generate_and_score",
            )
            self.find_best_kernel = cl.Kernel(
                self.program,
                "find_best_candidate",
            )
            self.gather_best_kernel = cl.Kernel(
                self.program,
                "gather_best_schedule",
            )
        except Exception as error:
            raise OpenCLUnavailableError(
                f"OpenCL kernel compilation failed ({error}); using CPU search."
            ) from error

        flags = cl.mem_flags
        pair_array = np.asarray(pairings, dtype=np.int32).reshape((-1, 2))
        self.pair_first_buffer = cl.Buffer(
            self.context,
            flags.READ_ONLY | flags.COPY_HOST_PTR,
            hostbuf=np.ascontiguousarray(pair_array[:, 0]),
        )
        self.pair_second_buffer = cl.Buffer(
            self.context,
            flags.READ_ONLY | flags.COPY_HOST_PTR,
            hostbuf=np.ascontiguousarray(pair_array[:, 1]),
        )

        self.event_count = round_count * game_count
        self.scratch_stride = (
            2 * self.pair_count
            + 2 * game_count
            + game_count * team_count
            + 2 * team_count
        )
        self.bytes_per_candidate = (
            self.scratch_stride * np.dtype(np.int32).itemsize
            + self.event_count * 3 * np.dtype(np.int32).itemsize
            + np.dtype(np.float32).itemsize
        )
        memory_budget = min(
            self.DEVICE_MEMORY_BUDGET,
            max(1, int(self.device.global_mem_size * 0.1)),
        )
        memory_limited_batch = max(1, memory_budget // self.bytes_per_candidate)
        estimated_work = (
            2 * round_count * self.pair_count
            + self.pair_count
            + game_count * team_count
            + self.event_count
        )
        work_limited_batch = max(
            1,
            self.CANDIDATES_PER_BATCH_WORK_TARGET // max(1, estimated_work),
        )
        self.batch_size = min(
            self.CANDIDATES_PER_BATCH_LIMIT,
            memory_limited_batch,
            work_limited_batch,
        )

    def search(
        self,
        *,
        deadline: float | None,
        max_candidates: int | None,
        cancellation_requested: Any,
        progress_callback: Any,
    ) -> tuple[list[list[tuple[int, int, int]]], float]:
        cl = self._cl
        flags = cl.mem_flags
        scratch_buffer = cl.Buffer(
            self.context,
            flags.READ_WRITE,
            self.batch_size * self.scratch_stride * np.dtype(np.int32).itemsize,
        )
        schedule_buffer = cl.Buffer(
            self.context,
            flags.READ_WRITE,
            self.batch_size * self.event_count * 3 * np.dtype(np.int32).itemsize,
        )
        cost_buffer = cl.Buffer(
            self.context,
            flags.READ_WRITE,
            self.batch_size * np.dtype(self.score_dtype).itemsize,
        )
        best_schedule_buffer = cl.Buffer(
            self.context,
            flags.WRITE_ONLY,
            self.event_count * 3 * np.dtype(np.int32).itemsize,
        )
        best_index_buffer = cl.Buffer(
            self.context,
            flags.READ_WRITE,
            np.dtype(np.int32).itemsize,
        )
        best_cost_buffer = cl.Buffer(
            self.context,
            flags.WRITE_ONLY,
            np.dtype(self.score_dtype).itemsize,
        )

        best_schedule: list[list[tuple[int, int, int]]] | None = None
        best_cost = math.inf
        completed = 0
        self.completed_candidates = 0
        seed = int(np.random.SeedSequence().generate_state(1, dtype=np.uint32)[0])
        last_progress_at = time.monotonic()

        while (
            (
                completed == 0
                or deadline is None
                or time_before_deadline(deadline)
            )
            and (max_candidates is None or completed < max_candidates)
            and (completed == 0 or not cancellation_requested())
        ):
            active_count = self.batch_size
            if max_candidates is not None:
                active_count = min(active_count, max_candidates - completed)
            self.generate_kernel(
                self.queue,
                (active_count,),
                None,
                self.pair_first_buffer,
                self.pair_second_buffer,
                schedule_buffer,
                cost_buffer,
                scratch_buffer,
                np.uint32(self.team_count),
                np.uint32(self.game_count),
                np.uint32(self.round_count),
                np.uint32(self.pair_count),
                np.uint32(self.scratch_stride),
                np.uint32(self.event_count),
                np.uint32(seed),
                np.uint32(active_count),
            )

            self.find_best_kernel(
                self.queue,
                (1,),
                None,
                cost_buffer,
                best_index_buffer,
                best_cost_buffer,
                np.uint32(active_count),
            )
            batch_best_cost = np.empty(1, dtype=self.score_dtype)
            cl.enqueue_copy(
                self.queue,
                batch_best_cost,
                best_cost_buffer,
            ).wait()
            batch_cost = float(batch_best_cost[0])
            if batch_cost < best_cost:
                self.gather_best_kernel(
                    self.queue,
                    (self.event_count * 3,),
                    None,
                    schedule_buffer,
                    best_index_buffer,
                    best_schedule_buffer,
                    np.uint32(self.event_count),
                )
                candidate_array = np.empty(
                    (self.event_count, 3),
                    dtype=np.int32,
                )
                cl.enqueue_copy(
                    self.queue,
                    candidate_array,
                    best_schedule_buffer,
                ).wait()
                best_schedule = self._to_schedule(candidate_array)
                best_cost = batch_cost

            completed += active_count
            self.completed_candidates = completed
            now = time.monotonic()
            if (
                now - last_progress_at >= 0.2
                or (max_candidates is not None and completed >= max_candidates)
                or (deadline is not None and now >= deadline)
                or cancellation_requested()
            ):
                progress_callback(completed, best_cost)
                last_progress_at = now
            seed = (seed + 0x9E3779B9) & 0xFFFFFFFF

        if best_schedule is None:
            raise RuntimeError("OpenCL search ended before producing a candidate schedule.")
        return best_schedule, best_cost

    def _to_schedule(
        self,
        candidate: np.ndarray,
    ) -> list[list[tuple[int, int, int]]]:
        schedule: list[list[tuple[int, int, int]]] = []
        for round_index in range(self.round_count):
            round_games = []
            for game_index in range(self.game_count):
                game_number, first_team, second_team = candidate[
                    round_index * self.game_count + game_index
                ]
                if game_number >= 0:
                    round_games.append(
                        (int(game_number), int(first_team), int(second_team))
                    )
            schedule.append(round_games)
        return schedule


def time_before_deadline(deadline: float) -> bool:
    return time.monotonic() < deadline
