from __future__ import annotations

from frc_calculator.models.event import Event
from frc_calculator.models.team import Team, SeasonTeam
from frc_calculator.data.frc_events import request_event_listings
from frc_calculator.config.constants import get_constants


class Season:
    def __init__(self, season: int, useSeason: int, *, progress=None, max_week=None):
        self.season = season
        self.useSeason = useSeason
        self.allowBackfillIn2026 = True
        self.max_week = max_week

        self.seasonTeams = {}
        self.events = {}

        self._progress = progress

        self.find_season_events()

    def find_season_events(self):
        seasonData = request_event_listings(self.season)
        # Only process events up to the requested week if specified
        weeks_to_process = [1, 2, 3, 4, 5, 6]
        if self.max_week is not None:
            weeks_to_process = [w for w in weeks_to_process if w <= self.max_week]

        for weekNumber in weeks_to_process:
            weekStr = f"Week {weekNumber}"
            for eventData in seasonData[weekStr]["Events"]:
                self.register_event(weekNumber, eventData["code"], eventData["country"])

    def register_season_team(self, eventTeam: Team, weekNumber: int):
        teamNumber = eventTeam.teamNumber
        mSeasonTeam = self.get_season_team_from_number(teamNumber)
        mSeasonTeam.name = eventTeam.name
        mSeasonTeam.rookieYear = eventTeam.rookieYear
        mSeasonTeam.districtCode = eventTeam.districtCode
        mSeasonTeam.events.append((weekNumber, eventTeam.event))
        mSeasonTeam.eventTeams.append((weekNumber, eventTeam))
        eventTeam.seasonTeam = mSeasonTeam

    def get_season_team_from_number(self, teamNumber: int):
        if teamNumber not in self.seasonTeams:
            mSeasonTeam = SeasonTeam(self.useSeason, teamNumber)
            self.seasonTeams[teamNumber] = mSeasonTeam
        else:
            mSeasonTeam = self.seasonTeams[teamNumber]
        return mSeasonTeam

    def register_event(self, weekNumber: int, eventCode: str, country: str):
        mEvent = Event(self.season, eventCode, progress=None)
        mEvent.weekNumber = weekNumber
        mEvent.country = country
        if weekNumber not in self.events:
            self.events[weekNumber] = [mEvent]
        else:
            self.events[weekNumber].append(mEvent)
        for _, mTeam in mEvent.teams.items():
            self.register_season_team(mTeam, weekNumber)
        if self._progress:
            try:
                self._progress(eventCode)
            except Exception:
                pass

    def regional_pool_2025(self, weekNumber: int):
        if self.useSeason < 2025:
            return {}

        if weekNumber >= 3:
            self.regional_pool_2025(weekNumber - 1)

        sortPool = []
        for _, mSeasonTeam in self.seasonTeams.items():
            if mSeasonTeam.districtCode is None:
                sortCriteria = (
                    *(mSeasonTeam.get_regional_points(weekNumber)),
                    mSeasonTeam.teamNumber,
                )
                if sortCriteria[0:7] != (0, 0, 0, 0, 0, 0, 0, 0, 0):
                    sortPool.append(sortCriteria)
        sortPool = sorted(sortPool, reverse=True)
        regionalPool = {}
        for index in range(len(sortPool)):
            sortCriteria = sortPool[index]
            regionalPool[index + 1] = {
                "team": self.get_season_team_from_number(sortCriteria[9]),
                "points": sortCriteria[0:7],
                "firstEvent": sortCriteria[7],
                "secondEvent": sortCriteria[8]
            }

        poolCount = 0
        succession = 1

        match self.useSeason:
            case 2025:
                while succession <= len(regionalPool):
                    mSeasonTeam = regionalPool[succession]["team"]
                    mAutoAdvancement = mSeasonTeam.get_auto_advancement_2025(weekNumber)
                    if (
                        mAutoAdvancement["isQualified"]
                        and (not mSeasonTeam.isQualified)
                        and (not mSeasonTeam.isDeclined)
                    ):
                        poolCount += 1
                        mSeasonTeam.isQualified = True
                        mSeasonTeam.qualifiedFor = f"{mAutoAdvancement['qualifiedFor']} (Week {weekNumber} Slot {poolCount})"
                        mSeasonTeam.qualifiedEvent = mAutoAdvancement["qualifiedEvent"]
                    succession += 1
            case 2026:
                if weekNumber == 2:
                    events = self.events[1] + self.events[2]
                else:
                    events = self.events[weekNumber]
                for mEvent in events:
                    rankings = mEvent.get_regional_points_rankings_2026()
                    autoAdvancementCount = 0
                    succession = 1
                    if mEvent.country == "USA":
                        ironBowl = 3
                    else:
                        ironBowl = 4
                    while autoAdvancementCount < ironBowl:
                        try:
                            mTeam = rankings[succession]["team"]
                        except KeyError:
                            break
                        mSeasonTeam = mTeam.seasonTeam
                        if not mSeasonTeam.isQualified:
                            if not mSeasonTeam.isDeclined:
                                poolCount += 1
                                mSeasonTeam.isQualified = True
                                mSeasonTeam.qualifiedFor = (
                                    f"{mTeam.event.eventCode} Slot {autoAdvancementCount + 1} (Week {weekNumber} Slot {poolCount})"
                                )
                                mSeasonTeam.qualifiedEvent = mTeam.event
                            autoAdvancementCount += 1
                        succession += 1

        succession = 1
        Const = get_constants(self.useSeason)
        while poolCount < Const.weeklySlots()[weekNumber - 2] and succession <= len(
            regionalPool
        ):
            mSeasonTeam = regionalPool[succession]["team"]
            if not mSeasonTeam.isQualified:
                if not mSeasonTeam.isDeclined:
                    poolCount += 1
                    mSeasonTeam.isQualified = True
                    mSeasonTeam.qualifiedFor = f"Week {weekNumber} Slot {poolCount}"
            succession += 1

        for rank, mRanking in regionalPool.items():
            mSeasonTeam = mRanking["team"]
            mRanking["qualified"] = {
                "isQualified": mSeasonTeam.isQualified,
                "qualifiedFor": mSeasonTeam.qualifiedFor,
                "qualifiedEvent": mSeasonTeam.qualifiedEvent,
                "declined": mSeasonTeam.isDeclined,
            }

        return regionalPool
