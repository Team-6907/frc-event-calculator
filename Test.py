import unittest

from frc_calculator.models.event import Event


class EventTest(unittest.TestCase):
    def test_event(self):
        mEvent = Event(2024, "AZVA")

        self.assertEqual(mEvent.season, 2024)
        self.assertEqual(mEvent.eventCode, "AZVA")

    def test_event_rankings(self):
        mEvent = Event(2024, "AZVA")

        self.assertEqual(
            mEvent.get_team_from_number(6907), mEvent.get_team_from_rank(8)
        )

    def test_event_alliance(self):
        mEvent = Event(2024, "AZVA")

        self.assertEqual(mEvent.get_alliance_from_number(4).allianceNumber, 4)
        self.assertEqual(
            mEvent.get_alliance_from_number(4),
            mEvent.get_team_from_number(6907).alliance,
        )

    def test_event_matches(self):
        mEvent = Event(2024, "AZVA")

        self.assertEqual(mEvent.get_quals_from_number(1).matchNumber, 1)
        self.assertEqual(mEvent.get_playoff_from_number(13).matchNumber, 13)
        self.assertEqual(
            mEvent.get_playoff_from_number(14), mEvent.get_final_from_number(1)
        )

    def test_get_winner_and_finalist(self):
        mEvent = Event(2024, "AZVA")

        self.assertEqual(
            mEvent.get_winner_and_finalist(),
            (mEvent.get_alliance_from_number(1), mEvent.get_alliance_from_number(7)),
        )

    def test_round_2022(self):
        mEvent = Event(2019, "KSLA")

        self.assertEqual(
            mEvent.get_playoff_from_round_2022("Semi", 1, 1),
            mEvent.get_playoff_from_number(13),
        )
        self.assertEqual(
            mEvent.get_round_winloser_2022("Quarter", 2),
            (mEvent.get_alliance_from_number(4), mEvent.get_alliance_from_number(5)),
        )

    def test_award_recipients(self):
        mEvent = Event(2024, "AZVA")

        self.assertEqual(
            mEvent.get_recipients_from_award("Innovation in Control Award")[0]["Team"],
            mEvent.get_team_from_number(6907),
        )
        self.assertEqual(
            mEvent.get_recipients_from_award("Volunteer of the Year")[0]["Person"],
            "George Williams",
        )

    def test_points_rankings(self):
        mEvent = Event(2024, "AZVA")
        secondPlace = mEvent.get_regional_points_rankings_2026()[2]

        self.assertEqual(secondPlace["team"], mEvent.get_team_from_number(6036))
        self.assertEqual(secondPlace["points"], (70, 30, 16, 19, 127, 112, 99))


if __name__ == "__main__":
    unittest.main()
