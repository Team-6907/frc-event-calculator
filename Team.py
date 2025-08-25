from Utils import erfinv
from rich import print
import math

from Requests import request_regional_adjustments, request_statbotics_epa
from Constants import get_constants


class Team:
    """
    A `Team` represents a team in a specific event,
    that is, `Team` instances are different if the event changes.
    """

    def __init__(self, teamNumber: int, event):
        self.teamNumber = teamNumber
        self.event = event

        # waiting for requests
        self.rookieYear = 0
        self.name = ""
        self.districtCode = None

        # waiting for the event to assign
        self.sortOrder = None
        self.alliance = None
        self.allianceRole = 0
        self.ranking = 0
        self.awards = []

        # waiting to match
        self.playoffMatches = []
        self.qualsMatches = []

        self.seasonTeam = None

    def __str__(self):
        return f"<Team {self.teamNumber}>"

    def __repr__(self):
        return self.__str__()

    def register_alliance(self, mAlliance, allianceRole: int):

        # simulating alliance selection
        self.alliance = mAlliance
        self.allianceRole = allianceRole

    def succession(self):
        """
        The succession in the alliance selection.
        """
        # self-calculate alliance succession
        if self.alliance is not None:
            match self.allianceRole:
                case 1:
                    return self.alliance.allianceNumber * 2 - 1
                case 2:
                    return self.alliance.allianceNumber * 2
                case 3:
                    return 25 - self.alliance.allianceNumber
                case 4:
                    return 24 + self.alliance.allianceNumber
                case _:
                    return None
        else:
            return None

    def succession_of_points(self):
        """
        The succession of a team based on regional pool rules.
        """
        if self.alliance is not None:
            match self.allianceRole:
                case 1:
                    return self.alliance.allianceNumber
                case 2:
                    return self.alliance.allianceNumber
                case 3:
                    return 17 - self.alliance.allianceNumber
                case _:
                    return 17
        else:
            return 17

    def get_win_playoffs(self, final=True):
        """
        The playoffs a team wins if eligible.
        """
        result = []
        for mMatch in self.playoffMatches:
            if mMatch.result_query(self) == "win":
                if final or mMatch not in self.event.get_finals():
                    result.append(mMatch)
        return result

    def get_win_finals(self):
        """
        The finals a team wins if eligible.
        """
        result = []
        for mMatch in self.event.get_finals():
            if mMatch.result_query(self) == "win" and mMatch in self.get_win_playoffs():
                result.append(mMatch)
        return result

    def qualification_points_2025(self):
        if self.ranking == 0:
            return 0
        alpha = 1.07
        N = len(self.event.teams)
        R = self.ranking
        QP = math.ceil(
            erfinv((N - 2 * R + 2) / (alpha * N)) * 10 / erfinv(1 / alpha) + 12
        )
        return QP

    def alliance_selection_points_2025(self):
        return 17 - self.succession_of_points()

    def playoff_advancement_points_2025(self):
        if self.alliance is not None:
            if self.event.get_final_from_number(1) in self.alliance.playoffMatches:
                beta = 20
            else:
                if self.event.season <= 2022:
                    if (
                        self.event.get_playoff_from_round_2022("Semi", 1, 1)
                        in self.alliance.playoffMatches
                    ):
                        beta = 10
                    elif (
                        self.event.get_playoff_from_round_2022("Semi", 2, 1)
                        in self.alliance.playoffMatches
                    ):
                        beta = 10
                    else:
                        beta = 0
                else:
                    if (
                        self.event.get_playoff_from_number(13)
                        in self.alliance.playoffMatches
                    ):
                        beta = 13
                    elif (
                        self.event.get_playoff_from_number(12)
                        in self.alliance.playoffMatches
                    ):
                        beta = 7
                    else:
                        beta = 0
            if beta != 0:
                DEProportion = len(self.get_win_playoffs(final=False)) / len(
                    self.alliance.get_win_playoffs(final=False)
                )
                DEPoints = DEProportion * beta
                if self.alliance == self.event.get_winner_and_finalist()[0]:
                    FinalPoints = 5 * len(self.get_win_finals())
                else:
                    FinalPoints = 0
                return math.ceil(DEPoints + FinalPoints)
        return 0

    def awards_points_2025(self):
        awardPoints = 0
        for award in self.awards:
            match award:
                case "Regional Winners":
                    pass
                case "Regional Finalists":
                    pass
                case "Regional Chairman's Award":
                    awardPoints += 45
                case "Regional FIRST Impact Award":
                    awardPoints += 45
                case "Regional Engineering Inspiration Award":
                    awardPoints += 28
                case "Rookie All Star Award":
                    awardPoints += 8
                case _:
                    awardPoints += 5
        return awardPoints

    def team_age_points_2025(self):
        if self.event.season == self.rookieYear:
            return 10
        if self.event.season == self.rookieYear + 1:
            return 5
        else:
            return 0

    def best_3_match_score(self):
        """
        The best 3 score of matches a team participated in.
        """
        scores = [0, 0, 0]
        matches = self.qualsMatches + self.playoffMatches
        for mMatch in matches:
            if (
                mMatch.score_query_by_team(self) is not None
                and mMatch.result_query(self) != "disqualified"
            ):
                scores.append(mMatch.score_query_by_team(self))
        scores = sorted(scores)[::-1]
        return tuple(scores[0:3])

    def regional_points_2025(self):
        """
        The Regional Points a team earns at a single event.
        """
        teamAgePoints = self.team_age_points_2025()
        qualsPoints = self.qualification_points_2025()
        alliancePoints = self.alliance_selection_points_2025()
        playoffPoints = self.playoff_advancement_points_2025()
        awardPoints = self.awards_points_2025()
        return (
            teamAgePoints + qualsPoints + alliancePoints + playoffPoints + awardPoints,
            playoffPoints,
            alliancePoints,
            qualsPoints,
            *(self.best_3_match_score()),
        )

    def verbose_regional_points_2025(self):
        """
        Print the Regional Points details.
        """
        print(
            f"""
            Suppose [green][{self.event.season} {self.event.eventCode}][/green] is held in [green]2025[/green], [red]Team {self.teamNumber}[/red] gets event points as follows:
            Team Age Points: {self.team_age_points_2025()}
            Qualification Performance Points: {self.qualification_points_2025()}
            Alliance Selection Points: {self.alliance_selection_points_2025()}
            Playoff Advancement Points: {self.playoff_advancement_points_2025()}
            Award Points: {self.awards_points_2025()} [yellow]({", ".join(self.awards)})[/yellow]
            Total Points in [green][{self.event.season} {self.event.eventCode}][/green]: {self.regional_points_2025()}
            If this regional is [red]Team {self.teamNumber}[/red]'s only regional this year, it earns {round(self.regional_points_2025()[0] * 0.6) + 14} in [green]Event 2[/green]. That is {round(self.regional_points_2025()[0] * 1.6) + 14} ({">=" if round(self.regional_points_2025()[0] * 1.6) >= 69 else "<"}83) in the Regional Pool.
            Therefore, [red]Team {self.teamNumber}[/red] might be {"[green]ELIGIBLE[/green]" if round(self.regional_points_2025()[0] * 1.6) >= 69 else "[red]NOT ELIGIBLE[/red]"} to the FIRST Championship.
            """
        )
    
    def get_statbotics_epa(self):
        """
        Get EPA from Statbotics.
        """
        return request_statbotics_epa(self.event.season, self.teamNumber, self.event.eventCode)


class SeasonTeam:
    """
    A `SeasonTeam` represents a team in the whole season.
    It is automatically created when a Season is initialized.
    """

    def __init__(self, season: int, teamNumber: int):
        self.teamNumber = teamNumber
        self.season = season
        self.events = []
        self.eventTeams = []

        if self.isPrequalified:
            self.isQualified = True
            self.qualifiedFor = "Pre-qualified"
        else:
            self.isQualified = False
            self.qualifiedFor = None

        self.qualifiedEvent = None

    def __str__(self):
        return f"<SeasonTeam {self.teamNumber}>"

    def __repr__(self):
        return self.__str__()

    @property
    def isPrequalified(self):
        """
        Whether a team is pre-qualified before the season starts.
        """
        Const = get_constants(self.season)
        if self.teamNumber in Const.preQualified:
            return True
        else:
            return False

    @property
    def isDeclined(self):
        """
        Whether a team has declined the Championship in the Regional Pool.
        """
        Const = get_constants(self.season)
        if self.teamNumber in Const.declined:
            return True
        else:
            return False

    def events_before_week_number(self, weekNumber: int):
        """
        The `Team`s a `SeasonTeam` shows up as before and during a week.
        """
        events = []
        for mWeekEventTeam in self.eventTeams:
            if mWeekEventTeam[0] <= weekNumber:
                events.append(mWeekEventTeam[1])
        return events

    def events_at_week_number(self, weekNumber: int):
        """
        The `Team`s a `SeasonTeam` shows up as during a week.
        """
        events = []
        for mWeekEventTeam in self.eventTeams:
            if mWeekEventTeam[0] == weekNumber:
                events.append(mWeekEventTeam[1])
        return events

    def get_regional_points(self, weekNumber: int):
        """
        Calculate a `SeasonTeam`'s total regional points in the season.
        """
        events = self.events_before_week_number(weekNumber)
        regionalPoints = [0, 0, 0, 0, 0, 0, 0]
        eventCount = 0
        for mEventTeam in events:
            currentPoints = mEventTeam.regional_points_2025()
            if eventCount <= 1:
                regionalPoints[0] += currentPoints[0]
            regionalPoints[1] = max(regionalPoints[1], currentPoints[1])
            regionalPoints[2] = max(regionalPoints[2], currentPoints[2])
            regionalPoints[3] = max(regionalPoints[3], currentPoints[3])
            maxScore3 = regionalPoints[4:7] + list(currentPoints)[4:7]
            regionalPoints[4:7] = sorted(maxScore3)[5:2:-1]
            eventCount += 1
        if len(events) == 1:
            regionalPoints[0] += round(regionalPoints[0] * 0.6 + 14)
        adjustments = request_regional_adjustments(self.season)
        if self.teamNumber in adjustments and weekNumber == 6:
            regionalPoints[0] += adjustments[self.teamNumber]
        return tuple(regionalPoints)

    def get_auto_advancement_2025(self, weekNumber: int):
        """
        Decide whether a team is auto-eligible in 2025 at this week.
        That is: FIA, EI or Winner Captain and 1st pick.
        """
        preQualifiedResult = {
            "isQualified": True,
            "qualifiedFor": "Pre-qualified",
            "qualifiedEvent": None,
        }

        # currently support: 2025-2026 only
        Const = get_constants(self.season)
        if self.teamNumber in Const.preQualified:
            return preQualifiedResult

        if weekNumber == 2:
            events = self.events_before_week_number(2)
        if weekNumber >= 3:
            events = self.events_at_week_number(weekNumber)
        qualified = False
        qualifyInfo = ""
        qualifyEvent = None
        for mEventTeam in events:
            if "Regional FIRST Impact Award" in mEventTeam.awards:
                qualified = True
                qualifyInfo = "FIA"
                qualifyEvent = mEventTeam.event
            elif "Regional Chairman's Award" in mEventTeam.awards:
                qualified = True
                qualifyInfo = "FIA"
                qualifyEvent = mEventTeam.event
            elif "Regional Engineering Inspiration Award" in mEventTeam.awards:
                qualified = True
                qualifyInfo = "EI"
                qualifyEvent = mEventTeam.event
            elif (
                "Regional Winners" in mEventTeam.awards and mEventTeam.allianceRole <= 2
            ):
                qualified = True
                qualifyInfo = "Winner"
                qualifyEvent = mEventTeam.event
            if qualified:
                break
        if qualified:
            return {
                "isQualified": True,
                "qualifiedFor": qualifyInfo,
                "qualifiedEvent": qualifyEvent,
            }
        else:
            return {"isQualified": False, "qualifiedFor": None, "qualifiedEvent": None}
