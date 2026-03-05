class Participant:
    def __init__(self, id_i, level_j):
        self.i = id_i
        self.j = level_j
        self.shares = []

    def __repr__(self):
        return f"P_{self.i}{self.j} (Level {self.j})"
    