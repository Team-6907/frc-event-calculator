import math


class SeasonConstants:
    """
    class.variables requirement:

    prequalified: tuple
    championshipSlots: int
    prequalifiedCount: int

    totalTeamCount: int
    districtTeamCount: int

    regionalError: int

    regionalsCountPerWeek: tuple[5]
    regionalsCount: int

    ironBowl: int

    weeksError: tuple[5]
    """

    @classmethod
    def openSlots(cls):
        return cls.championshipSlots - cls.prequalifiedCount

    @classmethod
    def regionalTeamCount(cls):
        return cls.totalTeamCount - cls.districtTeamCount

    @classmethod
    def freeSlots(cls):
        return cls.regionalTeamCount() - cls.regionalsCount * cls.ironBowl

    @classmethod
    def regionalSlots(cls):
        return (
            math.floor(cls.openSlots() * cls.regionalTeamCount() / cls.totalTeamCount)
            + cls.regionalError
        )

    @classmethod
    def regionalsProportionPerWeek(cls):
        return tuple(
            weeklyCount / cls.regionalsCount
            for weeklyCount in cls.regionalsCountPerWeek
        )

    @classmethod
    def weeklySlots(cls):
        return tuple(
            math.floor(
                cls.regionalSlots() * cls.regionalsProportionPerWeek()[i]
                + cls.weeksError[i]
            )
            for i in range(5)
        )


class DefaultConstants(SeasonConstants):
    preQualified = ()
    declined = ()

    championshipSlots = 600
    prequalifiedCount = 32

    totalTeamCount = 3522
    districtTeamCount = 1670

    regionalError = -6

    regionalsCountPerWeek = (18, 15, 14, 10, 12)
    regionalsCount = 69

    ironBowl = 4

    weeksError = (0, 0, 0, 0, 0)

    districtTeamsTBD = []


class Season2025Constants(SeasonConstants):
    preQualified = (
        3132,
        4403,
        1538,
        9432,
        987,
        2638,
        3990,
        2614,
        5985,
        2438,
        8159,
        3478,
        1902,
        4613,
        4522,
    )

    declined = (
        8557,
        3986,
        5528,
        1339,
        7536,
        1787,
        7433,
        3544,
        10541,
        10142,
        1493,
        3166,
        7021,
        8169,
        8777,
        9523,
        5655,
        10002,
        6483,
        7050,
        329,
        5584,
    )

    championshipSlots = 600
    prequalifiedCount = 32

    totalTeamCount = 3522
    districtTeamCount = 1670

    regionalError = -6

    regionalsCountPerWeek = (18, 15, 14, 10, 12)
    regionalsCount = 69

    ironBowl = 4

    weeksError = (-2, 4, 1, 0, 3)

    districtTeamsTBD = []


class Season2026Constants(SeasonConstants):
    preQualified = (
        5985,
        2486,
        4613,
        1816,
        1902,
    )

    declined = ()

    weeksError = (0, 0, 0, 0, 0)

    championshipSlots = 600
    prequalifiedCount = 9

    totalTeamCount = 3522
    districtTeamCount = 1670 + 289 + 69  # California 289, Wisconsin 69

    regionalError = -6

    regionalsCountPerWeek = (18, 15, 14, 10, 12)
    regionalsCount = 80

    ironBowl = 3


def get_constants(season):
    match season:
        case 2025:
            return Season2025Constants
        case 2026:
            return Season2026Constants
        case _:
            return DefaultConstants
