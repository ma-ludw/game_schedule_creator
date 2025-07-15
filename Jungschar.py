from Group import Group


class Jungschar():
    
    def __init__(self, jungschar_id: int,  n_groups: int):
        self.name = str(jungschar_id)
        self.id = jungschar_id
        self.n_groups = n_groups
        self.groups = [Group(i) for i in range(n_groups)]

    def change_n_groups(self, n_groups):
        self.n_groups = n_groups
        self.groups = [Group(i) for i in range(n_groups)]
