import os
import numpy
from models import Participant


p11 = Participant(2,6)
p11.__repr__()

class Hieararchy:
    def __init__(self, h):
        self.h = h
        self.levels = {j: [] for j in range(1, h+1)}

    def add_participant(self, participant):
        if 1 <= participant.j <= self.h:
            self.levels[participant.j].append(participant)
            print(f"Added participant: P_{participant.i}{participant.j}")
        else:
            raise ValueError(f"Érvénytelen szint: {participant.j}. A maximum szint {self.h}.")

    def is_qualified(self, subset):



        return True