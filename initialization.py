from models import Participant
import math

class Hierarchy:
    def __init__(self, h):
        self.h = h
        self.levels = {j: [] for j in range(1, h+1)}

    def add_participant(self, participant):
        if 1 <= participant.j <= self.h:
            self.levels[participant.j].append(participant)
            print(f"Added participant: P_{participant.i}{participant.j}")
        else:
            raise ValueError(f"Ervenytelen szint: {participant.j}. A maximum szint {self.h}.")

    def print_level(self, level_num):
        if level_num in self.levels:
            print(f"Level: {level_num}")
            for participant in self.levels[level_num]:
                print(participant)
        else:
            print(f"Hiba: A(z) {level_num}. szint nem letezik")

    def is_qualified(self, subset):
        if len(set(subset)) < len(subset):
            return False, "Egy resztvevo tobbszor is szerepel"

        for participant in subset:
            if participant not in self.levels[participant.j]:
                return False, f"A resztvevo {participant} nem szerepel a hierarchiaban"

        total_power = sum(p.j for p in subset)
        if total_power < (self.h + 1):
            return False, f"Alacsony hatalom: {total_power}, kell: {self.h + 1}"

        for j in range(1, self.h+1):
            count_at_level_j = len([p for p in subset if p.j == j])
            limit = math.ceil((self.h + 1) / j) - 1
            if count_at_level_j > limit:
                return False, f"Tul sok resztvevo a(z) {j}. szinten! A limit: {limit}"
        
        return True, "a csoport kvalifikalt"
    
