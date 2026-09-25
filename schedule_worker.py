from PySide6.QtCore import QObject, Signal

from Jungschar import Jungschar
from ScheduleGenerator import ScheduleGenerator


class ScheduleWorker(QObject):
    """Run schedule generation outside the UI thread and relay its events."""

    progress = Signal(int)
    status = Signal(str)
    completed = Signal(object)
    failed = Signal(str)

    def __init__(self, jungscharen: list[Jungschar], rounds: int, game_names: list[str]) -> None:
        super().__init__()
        self.jungscharen = jungscharen
        self.rounds = rounds
        self.game_names = game_names
        self.cancel_requested = False

    def cancel(self) -> None:
        self.cancel_requested = True

    def run(self) -> None:
        try:
            generator = ScheduleGenerator(
                self.jungscharen,
                self.rounds,
                len(self.game_names),
                self.game_names,
                progress_update_callback=self.progress.emit,
                cancellation_callback=lambda: self.cancel_requested,
                status_update_callback=self.status.emit,
            )
            self.completed.emit(generator.generate_schedule())
        except Exception as error:
            self.failed.emit(str(error))
