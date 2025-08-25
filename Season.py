from rich import print

from Event import Event
from Team import Team, SeasonTeam
from Requests import request_event_listings, request_regional_adjustments
from Constants import get_constants


class Season:
    def __init__(self, season: int, useSeason: int):

        self.season = season  # the real season where teams were competing at
        self.useSeason = useSeason  # the season of game rules we are calculating on
        self.allowBackfillIn2026 = True

        self.seasonTeams = {}  # where SeasonTeam_s are stored
        self.events = {}  # where Event_s are stored

        # GET Season Events Listings from FRC-events API
        # then store the events and register them
        self.find_season_events()

    def find_season_events(self):

        # GET Season Events Listings
        seasonData = request_event_listings(self.season)

        # the Data returned is classified by weekNumber
        for weekNumber in [1, 2, 3, 4, 5, 6]:
            weekStr = f"Week {weekNumber}"
            for eventData in seasonData[weekStr]["Events"]:
                self.register_event(weekNumber, eventData["code"])

    def register_season_team(self, eventTeam: Team, weekNumber: int):

        # get seasonTeam singletons
        teamNumber = eventTeam.teamNumber
        mSeasonTeam = self.get_season_team_from_number(teamNumber)
        mSeasonTeam.districtCode = eventTeam.districtCode
        mSeasonTeam.events.append((weekNumber, eventTeam.event))
        mSeasonTeam.eventTeams.append((weekNumber, eventTeam))

        # register the seasonTeam singletons to each Team in Event_s
        eventTeam.seasonTeam = mSeasonTeam

    def get_season_team_from_number(self, teamNumber: int):

        # seasonTeam should be a singleton
        if teamNumber not in self.seasonTeams:
            mSeasonTeam = SeasonTeam(self.useSeason, teamNumber)
            self.seasonTeams[teamNumber] = mSeasonTeam
        else:
            mSeasonTeam = self.seasonTeams[teamNumber]
        return mSeasonTeam

    def register_event(self, weekNumber: int, eventCode: str):
        mEvent = Event(self.season, eventCode)

        # Season.events classifies Event_s by weekNumber
        if weekNumber not in self.events:
            self.events[weekNumber] = [mEvent]
        else:
            self.events[weekNumber].append(mEvent)

        # for every Team in an Event, register the seasonTeam
        for teamNumber, mTeam in mEvent.teams.items():
            self.register_season_team(mTeam, weekNumber)

    def regional_pool_2025(self, weekNumber: int):
        """
        The regional pool under 2025 game rules.
        """

        # Before 2025, there is no regional pool
        if self.useSeason < 2025:
            return {}

        # If weekNumber == 2, the regional pool takes week 1-2 into account;
        # if weekNumber >= 3, just take the week only,
        # then we calculate the regional pool recursively.
        if weekNumber >= 3:
            self.regional_pool_2025(weekNumber - 1)

        # Now we sort the regional pool first
        sortPool = []
        for _, mSeasonTeam in self.seasonTeams.items():
            if mSeasonTeam.districtCode is None:
                # sortCriteria is (Points, 1st, 2nd, ..., 6th, teamNumber)
                # Here we assume that the 7th criteria (random pick) is trivial
                sortCriteria = (
                    *(mSeasonTeam.get_regional_points(weekNumber)),
                    mSeasonTeam.teamNumber,
                )
                if sortCriteria[0:7] != (0, 0, 0, 0, 0, 0, 0):
                    # All-zero teams haven't played yet
                    sortPool.append(sortCriteria)
        sortPool = sorted(sortPool, reverse=True)
        regionalPool = {}
        for index in range(len(sortPool)):
            sortCriteria = sortPool[index]
            regionalPool[index + 1] = {
                "team": self.get_season_team_from_number(sortCriteria[7]),
                "points": sortCriteria[0:7],
            }

        # Now that the regional pool is sorted
        poolCount = 0
        succession = 1

        # Firstly, filter all regional-qualified team this week
        match self.useSeason:

            # In 2025, things just happen when
            # 1. Pre-qualified
            # 2. FIA, EI or Regional Winner 0-1st pick
            case 2025:
                while succession <= len(regionalPool):
                    # for each succession, get the SeasonTeam according to the rank
                    mSeasonTeam = regionalPool[succession]["team"]
                    mAutoAdvancement = mSeasonTeam.get_auto_advancement_2025(weekNumber)

                    # poolCount += 1 only when
                    # 1. The team should have been eligible
                    # 2. It is not eligible now
                    # 3. It doesn't decline the slot
                    if (
                        mAutoAdvancement["isQualified"]
                        and (not mSeasonTeam.isQualified)
                        and (not mSeasonTeam.isDeclined)
                    ):
                        poolCount += 1
                        mSeasonTeam.isQualified = True
                        mSeasonTeam.qualifiedFor = mAutoAdvancement["qualifiedFor"]
                        mSeasonTeam.qualifiedEvent = mAutoAdvancement["qualifiedEvent"]
                    succession += 1

            # In 2026, things happen when
            # 1. Pre-qualified
            # 2. The first 3 teams in the regional (not qualified yet)
            case 2026:
                # get all events this week (or week 1-2 if week 2)
                if weekNumber == 2:
                    events = self.events[1] + self.events[2]
                else:
                    events = self.events[weekNumber]

                for mEvent in events:
                    rankings = mEvent.get_regional_points_rankings_2026()

                    # if 2026 season allows backfill to slots
                    if self.allowBackfillIn2026:
                        autoAdvancementCount = 0
                        succession = 1
                        while autoAdvancementCount < 3:
                            try:
                                mTeam = rankings[succession]["team"]
                            except KeyError:
                                # special issue when all teams are qualified in an event
                                break
                            mSeasonTeam = mTeam.seasonTeam
                            if not mSeasonTeam.isQualified:
                                if not mSeasonTeam.isDeclined:
                                    poolCount += 1
                                    mSeasonTeam.isQualified = True
                                    mSeasonTeam.qualifiedFor = (
                                        f"Slot {autoAdvancementCount + 1}"
                                    )
                                    mSeasonTeam.qualifiedEvent = mTeam.event
                                autoAdvancementCount += 1
                            succession += 1

                    # if backfill is not allowed
                    else:
                        for rank in range(1, 4):
                            mTeam = rankings[rank]["team"]
                            mSeasonTeam = mTeam.seasonTeam
                            if not mSeasonTeam.isQualified:
                                if not mSeasonTeam.isDeclined:
                                    poolCount += 1
                                    mSeasonTeam.isQualified = True
                                    mSeasonTeam.qualifiedFor = f"Rank {rank}"
                                    mSeasonTeam.qualifiedEvent = mTeam.event

        # Now we can qualify top teams in the regional rankings
        succession = 1
        Const = get_constants(self.useSeason)

        while poolCount < Const.weeklySlots()[weekNumber - 2]:
            mSeasonTeam = regionalPool[succession]["team"]
            if not mSeasonTeam.isQualified:
                if not mSeasonTeam.isDeclined:
                    poolCount += 1
                    mSeasonTeam.isQualified = True
                    mSeasonTeam.qualifiedFor = f"Week {weekNumber}"
            succession += 1
        
        # returns
        for rank, mRanking in regionalPool.items():
            mSeasonTeam = mRanking["team"]
            mRanking["qualified"] = {
                "isQualified": mSeasonTeam.isQualified,
                "qualifiedFor": mSeasonTeam.qualifiedFor,
                "qualifiedEvent": mSeasonTeam.qualifiedEvent,
                "declined": mSeasonTeam.isDeclined,
            }

        return regionalPool


mSeason = Season(2025, useSeason=2025)
mSeason.allowBackfillIn2026 = True
# mSeasonTeam = mSeason.get_season_team_from_number(6907)
# print(mSeasonTeam.get_auto_advancement_2025(weekNumber=6))

mSeasonTeam = mSeason.get_season_team_from_number(5449)
mSeasonTeam.eventTeams[0][1].verbose_regional_points_2025()

mPool = mSeason.regional_pool_2025(weekNumber=6)

# data = [pool["points"][0] for key, pool in mPool.items()]

# import matplotlib.pyplot as plt

# plt.hist(data, bins=187)
# plt.show()


# teamList = {}
# for weekNumber in [2, 3, 4, 5, 6]:
#     regionalPool = mSeason.regional_pool(weekNumber=weekNumber)
#     for rank, mRanking in regionalPool.items():
#         mSeasonTeam = mRanking["team"]
#         if (len(mSeasonTeam.events_before_week_number(weekNumber)) == 1
#             and mSeasonTeam.get_regional_points(6)[0] < 83
#             and mSeasonTeam.get_regional_points(weekNumber)[0] >= 83
#         ):
#             teamList[mSeasonTeam.teamNumber] = {
#                 "team": mSeasonTeam,
#                 "firstWeek": mSeasonTeam.events[0][0],
#                 "secondWeek": mSeasonTeam.events[1][0],
#                 "firstPoints": mSeasonTeam.get_regional_points(weekNumber),
#                 "finalPoints": mSeasonTeam.get_regional_points(6)
#             }

# teamListings = []
# for teamNumber in [9599, 9624, 6106, 2472, 3550, 2473, 9470, 8871, 2584, 9458, 9597, 967, 3216, 4087, 7530, 2135, 7428, 4005, 2169, 8024]:
#     info = teamList[teamNumber]
#     mSeasonTeam = info["team"]
#     print(info)
