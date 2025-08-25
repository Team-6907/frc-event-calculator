from rich import print

from Team import Team
from Alliance import Alliance
from Match import Match
from Requests import (
    request_event_alliances,
    request_event_awards,
    request_event_rankings,
    request_event_teams,
    request_playoff_matches,
    request_quals_matches,
)


class Event:
    def __init__(self, season: int, eventCode: str):
        self.season = season
        self.eventCode = eventCode

        self.rankings = {}
        self.alliances = {}
        self.teams = {}
        self.qualsMatches = {}
        self.playoffMatches = {}
        self.awards = {}

        self.get_event_teams()
        self.get_event_rankings()
        self.get_event_alliances()
        self.get_event_matches()
        self.get_event_awards()

    def __str__(self):
        return f"<Event {self.season} {self.eventCode}>"

    def __repr__(self):
        return self.__str__()
    
    # Methods to initialize an event

    def get_event_teams(self):
        teams = request_event_teams(self.season, self.eventCode)
        for teamData in teams:
            self.register_team(teamData)
        return teams

    def get_event_rankings(self):
        rankings = request_event_rankings(self.season, self.eventCode)
        for rankingData in rankings:
            mTeam = self.update_rankings(rankingData)
            self.rankings[rankingData["rank"]] = mTeam
        return rankings

    def get_event_alliances(self):
        alliances = request_event_alliances(self.season, self.eventCode)
        for allianceData in alliances:
            mAlliance = Alliance(self)
            mAlliance.register_alliance(allianceData["number"])
            mTeam1 = self.get_team_from_number(allianceData["captain"])
            mTeam2 = self.get_team_from_number(allianceData["round1"])
            mTeam3 = self.get_team_from_number(allianceData["round2"])
            if allianceData["round3"] is not None:
                mTeam4 = self.get_team_from_number(allianceData["round3"])
            else:
                mTeam4 = None
            if allianceData["backup"] is not None:
                mBackup = self.get_team_from_number(allianceData["backup"])
            else:
                mBackup = None
            mAlliance.register_team(mTeam1)
            mAlliance.register_team(mTeam2)
            mAlliance.register_team(mTeam3)
            mAlliance.register_team(mTeam4)
            mAlliance.register_team(mBackup)
            self.alliances[allianceData["number"]] = mAlliance
        return alliances

    def get_event_matches(self):
        qualsMatches = request_quals_matches(self.season, self.eventCode)
        playoffMatches = request_playoff_matches(self.season, self.eventCode)
        for match in qualsMatches:
            self.register_match(match, "qualification")
        for match in playoffMatches:
            self.register_match(match, "playoff")

    def get_event_awards(self):
        awards = request_event_awards(self.season, self.eventCode)
        for awardData in awards:
            self.register_team_award(awardData)

    def register_team(self, teamData) -> Team:
        mTeam = Team(teamData["teamNumber"], self)
        mTeam.name = teamData["nameShort"]
        mTeam.rookieYear = teamData["rookieYear"]
        mTeam.districtCode = teamData["districtCode"]
        self.teams[teamData["teamNumber"]] = mTeam

    def update_rankings(self, rankingData):
        mTeam = self.get_team_from_number(rankingData["teamNumber"])
        mTeam.ranking = rankingData["rank"]
        mTeam.sortOrder = (
            rankingData["sortOrder1"],
            rankingData["sortOrder2"],
            rankingData["sortOrder3"],
            rankingData["sortOrder4"],
            rankingData["sortOrder5"],
            rankingData["sortOrder6"],
        )
        mTeam.WLT = (rankingData["wins"], rankingData["losses"], rankingData["ties"])
        return mTeam

    def register_match(self, matchData, tournamentLevel):
        mMatch = Match(self, tournamentLevel, matchData["matchNumber"])
        mMatch.redScore = [
            matchData["scoreRedFinal"],
            matchData["scoreRedFoul"],
            matchData["scoreRedAuto"],
        ]
        mMatch.blueScore = [
            matchData["scoreBlueFinal"],
            matchData["scoreBlueFoul"],
            matchData["scoreBlueAuto"],
        ]
        for key, value in matchData.items():
            if key not in [
                "scoreRedFinal",
                "scoreBlueFinal",
                "scoreRedFoul",
                "scoreBlueFoul",
                "scoreRedAuto",
                "scoreBlueAuto",
            ]:
                if key.startswith("scoreRed"):
                    mMatch.redScore.append(value)
                elif key.startswith("scoreBlue"):
                    mMatch.blueScore.append(value)
        if tournamentLevel == "playoff":
            mRedTeam = self.get_team_from_number(matchData["teams"][0]["teamNumber"])
            mMatch.register_alliance(mRedTeam.alliance, True)
            mBlueTeam = self.get_team_from_number(matchData["teams"][3]["teamNumber"])
            mMatch.register_alliance(mBlueTeam.alliance, False)
        for station in range(6):
            mTeam = self.get_team_from_number(matchData["teams"][station]["teamNumber"])
            mMatch.register_team(
                mTeam, (station < 3), matchData["teams"][station]["dq"]
            )
        mMatch.isReplay = matchData["isReplay"]
        mMatch.matchVideoLink = matchData["matchVideoLink"]
        matchNumber = matchData["matchNumber"]
        if tournamentLevel == "qualification":
            self.qualsMatches[matchNumber] = mMatch
        elif tournamentLevel == "playoff":
            self.playoffMatches[matchNumber] = mMatch

    def register_team_award(self, awardData):
        awardName = awardData["name"]
        if awardData["teamNumber"] is not None:
            try:
                mTeam = self.get_team_from_number(awardData["teamNumber"])
                if awardData["person"] is None:
                    mTeam.awards.append(awardName)
            except KeyError:
                mTeam = None
        else:
            mTeam = None
        mAwardTo = {"Team": mTeam, "Person": awardData["person"]}
        if awardName in self.awards.keys():
            self.awards[awardName].append(mAwardTo)
        else:
            self.awards[awardName] = [mAwardTo]

    def get_team_from_number(self, teamNumber) -> Team:
        """
        Get Team base on the TeamNumber.
        """
        mTeam = self.teams[teamNumber]
        return mTeam

    def get_team_from_rank(self, rank) -> Team:
        mTeam = self.rankings[rank]
        return mTeam

    def get_alliance_from_number(self, allianceNumber) -> Alliance:
        mAlliance = self.alliances[allianceNumber]
        return mAlliance

    def get_quals_from_number(self, matchNumber) -> Match:
        try:
            mMatch = self.qualsMatches[matchNumber]
            return mMatch
        except KeyError:
            return None

    def get_playoff_from_number(self, matchNumber) -> Match:
        try:
            mMatch = self.playoffMatches[matchNumber]
            return mMatch
        except KeyError:
            return None

    def get_final_from_number(self, finalNumber) -> Match:
        if self.season <= 2022:
            matchNumber = finalNumber + 18
        else:
            matchNumber = finalNumber + 13
        mMatch = self.get_playoff_from_number(matchNumber)
        return mMatch

    def get_finals(self) -> Match:
        return (
            self.get_final_from_number(1),
            self.get_final_from_number(2),
            self.get_final_from_number(3),
        )

    def get_winner_and_finalist(self):
        final1 = self.get_final_from_number(1)
        final2 = self.get_final_from_number(2)
        final1Winner, final1Loser = final1.get_match_winloser()
        final2Winner, final2Loser = final2.get_match_winloser()
        if final1Winner == final2Winner:
            return final1Winner, final1Loser
        else:
            return self.get_final_from_number(3).get_match_winloser()

    def get_playoff_from_round_2022(self, round, roundNumber, finalNumber) -> Match:
        if self.season <= 2022:
            if finalNumber not in [1, 2, 3]:
                return None
            match round:
                case "Quarter":
                    if roundNumber not in [1, 2, 3, 4]:
                        return None
                    matchNumber = 3 * (roundNumber - 1) + finalNumber
                case "Semi":
                    if roundNumber not in [1, 2]:
                        return None
                    matchNumber = 3 * (roundNumber + 3) + finalNumber
                case "Final":
                    matchNumber = 18 + finalNumber
                case _:
                    return None
            mMatch = self.get_playoff_from_number(matchNumber)
            return mMatch
        return None

    def get_playoffs_from_round_2022(self, round, roundNumber) -> list:
        matches = []
        if self.season <= 2022:
            for finalNumber in [1, 2, 3]:
                matches.append(
                    self.get_playoff_from_round_2022(round, roundNumber, finalNumber)
                )
        return matches

    def get_round_winloser_2022(self, round, roundNumber):
        matches = self.get_playoffs_from_round_2022(round, roundNumber)
        if matches[0].get_match_winloser() == matches[1].get_match_winloser():
            return matches[0].get_match_winloser()
        else:
            return matches[2].get_match_winloser()

    def get_recipients_from_award(self, awardName):
        try:
            return self.awards[awardName]
        except KeyError:
            pass

    def get_regional_points_rankings_2026(self):
        teams = []
        for mTeam in self.teams.values():
            teams.append((mTeam.regional_points_2025(), mTeam.teamNumber))
        teams = sorted(teams)[::-1]
        rankings = {}
        for i in range(len(teams)):
            rankings[i + 1] = {
                "team": self.get_team_from_number(teams[i][1]),
                "points": teams[i][0],
            }
        return rankings

    def get_regional_statistics_2025(self):
        """
        Important statistics for the event (2025+ season only).
        """

        # the average score of the current regional
        s = 0
        for mMatch in self.qualsMatches:
            s += mMatch.redScore[0]
            s += mMatch.blueScore[0]
        avgScore = s / (len(self.qualsMatches) * 2)

        # the score of Match 11-16
        titleScore = {}
        s = []
        for matchNumber in range(11, 17):
            mMatch = self.get_playoff_from_number(matchNumber)
            

        # the RP of rank 1, 4, 8
        RP = {}
        for rank in (1, 4, 8):
            RP[rank] = self.get_team_from_rank(rank).sortOrder[0]
        
        # 