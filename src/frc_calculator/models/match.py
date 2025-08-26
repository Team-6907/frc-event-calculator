from __future__ import annotations

from frc_calculator.models.alliance import AnonymousAlliance, Alliance


class Match:
    def __init__(self, event, tournamentLevel: str, matchNumber: int):
        self.event = event
        self.tournamentLevel = tournamentLevel
        self.isReplay = False
        self.matchVideoLink = None
        self.matchNumber = matchNumber
        self.dqTeams = []
        self.redScore = []  # waiting for the event to assign
        self.blueScore = []
        if tournamentLevel == "qualification":
            self.redAlliance = AnonymousAlliance(event)
            self.blueAlliance = AnonymousAlliance(event)
        if tournamentLevel == "playoff":
            self.redAlliance = None
            self.blueAlliance = None

    def __str__(self):
        if self.tournamentLevel == "qualification":
            return f"<Qualification {self.matchNumber}>"
        if self.tournamentLevel == "playoff":
            if self.event.season <= 2022:
                if self.matchNumber <= 12:
                    if self.matchNumber % 3 == 0:
                        return f"<Quarter {(self.matchNumber - 1) // 3 + 1} Tiebreaker>"
                    else:
                        return f"<Quarter {(self.matchNumber - 1) // 3 + 1} Match {self.matchNumber % 3}>"
                elif self.matchNumber <= 18:
                    if self.matchNumber % 3 == 0:
                        return f"<Semi {(self.matchNumber - 1) // 3 - 3} Tiebreaker>"
                    else:
                        return f"<Semi {(self.matchNumber - 1) // 3 - 3} Match {self.matchNumber % 3}>"
                elif self.matchNumber <= 20:
                    return f"<Final {self.matchNumber - 18}>"
                else:
                    return f"<Final Tiebreaker>"
            else:
                if self.matchNumber <= 13:
                    return f"<Playoff Match {self.matchNumber}>"
                elif self.matchNumber <= 15:
                    return f"<Final {self.matchNumber - 13}>"
                else:
                    return f"<Final Tiebreaker>"

    def __repr__(self):
        return self.__str__()

    def register_team(self, mTeam, red: bool, disqualified: bool):
        if self.tournamentLevel == "qualification":
            mTeam.qualsMatches.append(self)
            if red:
                self.redAlliance.register_team(mTeam)
            else:
                self.blueAlliance.register_team(mTeam)
        elif self.tournamentLevel == "playoff":
            mTeam.playoffMatches.append(self)
        if disqualified:
            self.dqTeams.append(mTeam)

    def register_alliance(self, mAlliance: Alliance, red: bool):
        if self.tournamentLevel == "playoff":
            if red:
                self.redAlliance = mAlliance
            else:
                self.blueAlliance = mAlliance
            mAlliance.playoffMatches.append(self)

    def result_query(self, mTeam):
        if self.redAlliance.is_member(mTeam):
            red = True
        elif self.blueAlliance.is_member(mTeam):
            red = False
        else:
            return "wrong team"
        if mTeam in self.dqTeams:
            return "disqualified"
        if self.redScore == self.blueScore:
            return "tie"
        if red == (self.redScore > self.blueScore):
            return "win"
        return "lose"

    def result_query_by_alliance(self, mAlliance: Alliance):
        if mAlliance not in (self.redAlliance, self.blueAlliance):
            return "wrong alliance"
        if mAlliance.teams[0] in self.dqTeams:
            return "disqualified"
        if self.redScore == self.blueScore:
            return "tie"
        if (self.redAlliance == mAlliance) == (self.redScore > self.blueScore):
            return "win"
        return "lose"

    def get_match_winloser(self):
        if self.redScore >= self.blueScore:
            return self.redAlliance, self.blueAlliance
        else:
            return self.blueAlliance, self.redAlliance

    def score_query_by_team(self, mTeam):
        if self.redAlliance.is_member(mTeam):
            return self.redScore[0]
        elif self.blueAlliance.is_member(mTeam):
            return self.blueScore[0]
        return 0

