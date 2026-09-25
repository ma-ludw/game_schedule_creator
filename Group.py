
class Group:
    """A named team belonging to a Jungschar."""

    def __init__(self, group_id: int) -> None:
        self.name = f"Team {group_id + 1}"
        self.id = group_id