from Group import Group


class Jungschar:
    """A participating youth group and its teams."""

    def __init__(self, jungschar_id: int, n_groups: int) -> None:
        self.name = f"Jungschar {jungschar_id + 1}"
        self.id = jungschar_id
        self.n_groups = n_groups
        self.groups = [Group(i) for i in range(n_groups)]

    def change_n_groups(self, n_groups: int) -> None:
        self.n_groups = n_groups
        self.groups = [Group(i) for i in range(n_groups)]
