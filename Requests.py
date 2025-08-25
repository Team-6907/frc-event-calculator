from requests.auth import HTTPBasicAuth
import os, dotenv
import requests, json
from rich import print
from statbotics import Statbotics

from Utils import load_json_data, write_json_data


def get_auth_headers():
    dotenv.load_dotenv()
    username = os.getenv("AUTH_USERNAME")
    token = os.getenv("AUTH_TOKEN")
    return HTTPBasicAuth(username, token)


def data_filename(season, eventCode):  # the JSON filename of each Event
    return f"data/{season}-{eventCode}.json"


def season_events_filename(season):  # the JSON filename of Event Listings
    return f"data/{season}EventListings.json"


def regional_adjustments_filename(season):
    # the JSON filename of Regional Points Adjustments (if necessary)
    return f"data/{season}RegionalAdjustments.json"


# requests functions


def request_event_teams(season, eventCode):

    # if JSON data exists, get JSON
    data = load_json_data(data_filename(season, eventCode))
    if data is not None:
        if "Teams" in data.keys():
            return data["Teams"]
    else:
        data = {}

    # if JSON doesn't exist, request FRC-events API
    apiResponse = requests.get(
        f"https://frc-api.firstinspires.org/v3.0/{season}/teams?eventCode={eventCode}",
        auth=get_auth_headers(),
    )
    teamsData = json.loads(apiResponse.content)["teams"]
    data["Teams"] = teamsData
    write_json_data(data, data_filename(season, eventCode))
    return teamsData


def request_event_rankings(season, eventCode):
    data = load_json_data(data_filename(season, eventCode))
    if data is not None:
        if "Rankings" in data.keys():
            return data["Rankings"]
    else:
        data = {}
    apiResponse = requests.get(
        f"https://frc-api.firstinspires.org/v3.0/{season}/rankings/{eventCode}",
        auth=get_auth_headers(),
    )
    rankingsData = json.loads(apiResponse.content)["Rankings"]
    data["Rankings"] = rankingsData
    write_json_data(data, data_filename(season, eventCode))
    return rankingsData


def request_event_alliances(season, eventCode):
    data = load_json_data(data_filename(season, eventCode))
    if data is not None:
        if "Alliances" in data.keys():
            return data["Alliances"]
    else:
        data = {}
    apiResponse = requests.get(
        f"https://frc-api.firstinspires.org/v3.0/{season}/alliances/{eventCode}",
        auth=get_auth_headers(),
    )
    alliancesData = json.loads(apiResponse.content)["Alliances"]
    data["Alliances"] = alliancesData
    write_json_data(data, data_filename(season, eventCode))
    return alliancesData


def request_quals_matches(season, eventCode):
    data = load_json_data(data_filename(season, eventCode))
    if data is not None:
        if "Qualifications" in data.keys():
            return data["Qualifications"]
    else:
        data = {}
    apiResponse = requests.get(
        f"https://frc-api.firstinspires.org/v3.0/{season}/matches/{eventCode}?tournamentLevel=Qualification",
        auth=get_auth_headers(),
    )
    qualsData = json.loads(apiResponse.content)["Matches"]
    data["Qualifications"] = qualsData
    write_json_data(data, data_filename(season, eventCode))
    return qualsData


def request_playoff_matches(season, eventCode):
    data = load_json_data(data_filename(season, eventCode))
    if data is not None:
        if "Playoffs" in data.keys():
            return data["Playoffs"]
    else:
        data = {}
    apiResponse = requests.get(
        f"https://frc-api.firstinspires.org/v3.0/{season}/matches/{eventCode}?tournamentLevel=Playoff",
        auth=get_auth_headers(),
    )
    playoffsData = json.loads(apiResponse.content)["Matches"]
    data["Playoffs"] = playoffsData
    write_json_data(data, data_filename(season, eventCode))
    return playoffsData


def request_event_awards(season, eventCode):
    data = load_json_data(data_filename(season, eventCode))
    if data is not None:
        if "Awards" in data.keys():
            return data["Awards"]
    else:
        data = {}
    apiResponse = requests.get(
        f"https://frc-api.firstinspires.org/v3.0/{season}/awards/event/{eventCode}",
        auth=get_auth_headers(),
    )
    awardsData = json.loads(apiResponse.content)["Awards"]
    data["Awards"] = awardsData
    write_json_data(data, data_filename(season, eventCode))
    return awardsData


def request_event_listings(season):
    data = load_json_data(season_events_filename(season))
    if data is not None:
        pass
    else:
        data = {}
    for week in [1, 2, 3, 4, 5, 6]:
        if f"Week {week}" in data.keys():
            continue
        apiResponse = requests.get(
            f"https://frc-api.firstinspires.org/v3.0/{season}/events?excludeDistrict=true&weekNumber={week}",
            auth=get_auth_headers(),
        )
        data[f"Week {week}"] = json.loads(apiResponse.content)
    write_json_data(data, season_events_filename(season))
    return data


def request_regional_adjustments(season):
    adjustmentsData = load_json_data(regional_adjustments_filename(season))
    if adjustmentsData is not None:
        data = adjustmentsData["Teams"]
    else:
        data = {}
    adjustments = {}
    if data is None:
        data = {}
    for teamStr, adjustment in data.items():
        teamNumber = int(teamStr)
        adjustments[teamNumber] = adjustment
    return adjustments


def request_statbotics_epa(season: int, teamNumber: int, eventCode: str):
    eventKey = str(season) + eventCode.lower()
    sb = Statbotics()
    return sb.get_team_event(teamNumber, eventKey)["epa"]["total_points"]["mean"]
