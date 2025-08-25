from typing import override


class AllianceBase:
    def __init__(self, event):
        self.event = event
        self.teams = []

    def __repr__(self):
        return self.__str__()

    def register_team(self, mTeam):
        self.teams.append(mTeam)

    def is_member(self, mTeam):
        return mTeam in self.teams


class AnonymousAlliance(AllianceBase):
    def __init__(self, event):
        AllianceBase.__init__(self, event)
        self.match = None  # quals should have a specific match

    def __str__(self):
        return f"<Alliance {self.teams[0].teamNumber} {self.teams[1].teamNumber} {self.teams[2].teamNumber}>"

    def register_match(self, mMatch):
        self.match = mMatch

    def get_team_from_station(self, station):
        return self.teams[station - 1]


class Alliance(AllianceBase):
    def __init__(self, event):
        super().__init__(event)
        self.allianceNumber = 0
        self.playoffMatches = []

    def __str__(self):
        return f"<Alliance {self.allianceNumber}>"

    def register_alliance(self, allianceNumber):
        self.allianceNumber = allianceNumber

    @override
    def register_team(self, mTeam):
        super().register_team(mTeam)
        if mTeam is not None:
            mTeam.register_alliance(self, len(self.teams))

    def get_win_playoffs(self, final=True):
        result = []
        for mMatch in self.playoffMatches:
            if mMatch.result_query_by_alliance(self) == "win":
                if final or mMatch not in self.event.get_finals():
                    result.append(mMatch)
        return result
