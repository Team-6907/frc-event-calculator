from __future__ import annotations

import os
import json
from typing import Any, Dict

import dotenv
import requests
from requests.auth import HTTPBasicAuth

from frc_calculator.utils.io_utils import load_json_data, write_json_data


class AuthError(Exception):
    """Raised when FRC API returns 401/403 due to invalid credentials."""


class ApiError(Exception):
    """Raised for other non-200 API responses that should interrupt flow."""


def _safe_parse_list(apiResponse: requests.Response, top_key: str, *, context: str) -> list:
    """Parse a requests response expecting JSON with a top-level list under top_key.

    Returns an empty list on error and prints a short diagnostic message.
    """
    if apiResponse.status_code == 401 or apiResponse.status_code == 403:
        raise AuthError(f"Invalid credentials for {context} (HTTP {apiResponse.status_code}).")
    if apiResponse.status_code == 429:
        # Rate limited – surface as ApiError so UI can instruct to retry later
        raise ApiError(f"Rate limited for {context} (HTTP 429). Try again later.")
    if apiResponse.status_code != 200:
        # Other errors: log and return empty list, keeping app functional
        print(f"API request failed for {context}: Status {apiResponse.status_code}")
        try:
            print(f"Response: {apiResponse.text[:200]}")
        except Exception:
            pass
        return []
    content = apiResponse.content or b""
    if not content.strip():
        print(f"Empty response for {context}")
        return []
    try:
        obj = json.loads(content)
    except json.JSONDecodeError as e:
        preview = None
        try:
            preview = apiResponse.text[:200]
        except Exception:
            preview = "<unavailable>"
        print(f"JSON decode error for {context}: {e}. Content: {preview}")
        return []
    try:
        data = obj[top_key]
    except Exception:
        print(f"Missing key '{top_key}' in response for {context}")
        return []
    if not isinstance(data, list):
        print(f"Unexpected payload type for {context}: expected list under '{top_key}'")
        return []
    return data


def get_auth_headers() -> HTTPBasicAuth:
    dotenv.load_dotenv()
    username = os.getenv("AUTH_USERNAME")
    token = os.getenv("AUTH_TOKEN")
    return HTTPBasicAuth(username, token)


def data_filename(season: int, eventCode: str) -> str:
    return f"cache/{season}-{eventCode}.json"


def season_events_filename(season: int) -> str:
    return f"cache/{season}EventListings.json"


def regional_adjustments_filename(season: int) -> str:
    return f"cache/{season}RegionalAdjustments.json"


def _merge_cache(data: Dict[str, Any] | None) -> Dict[str, Any]:
    return {} if data is None else data


def request_event_teams(season: int, eventCode: str):
    data = load_json_data(data_filename(season, eventCode))
    if data is not None and "Teams" in data:
        return data["Teams"]
    data = _merge_cache(data)
    apiResponse = requests.get(
        f"https://frc-api.firstinspires.org/v3.0/{season}/teams?eventCode={eventCode}",
        auth=get_auth_headers(),
        timeout=20,
    )
    teamsData = _safe_parse_list(apiResponse, "teams", context=f"{season} {eventCode} teams")
    data["Teams"] = teamsData
    write_json_data(data, data_filename(season, eventCode))
    return teamsData


def request_event_rankings(season: int, eventCode: str):
    data = load_json_data(data_filename(season, eventCode))
    if data is not None and "Rankings" in data:
        return data["Rankings"]
    data = _merge_cache(data)
    apiResponse = requests.get(
        f"https://frc-api.firstinspires.org/v3.0/{season}/rankings/{eventCode}",
        auth=get_auth_headers(),
        timeout=20,
    )
    rankingsData = _safe_parse_list(apiResponse, "Rankings", context=f"{season} {eventCode} rankings")
    data["Rankings"] = rankingsData
    write_json_data(data, data_filename(season, eventCode))
    return rankingsData


def request_event_alliances(season: int, eventCode: str):
    data = load_json_data(data_filename(season, eventCode))
    if data is not None and "Alliances" in data:
        return data["Alliances"]
    data = _merge_cache(data)
    apiResponse = requests.get(
        f"https://frc-api.firstinspires.org/v3.0/{season}/alliances/{eventCode}",
        auth=get_auth_headers(),
        timeout=20,
    )
    alliancesData = _safe_parse_list(apiResponse, "Alliances", context=f"{season} {eventCode} alliances")
    data["Alliances"] = alliancesData
    write_json_data(data, data_filename(season, eventCode))
    return alliancesData


def request_quals_matches(season: int, eventCode: str):
    data = load_json_data(data_filename(season, eventCode))
    if data is not None and "Qualifications" in data:
        return data["Qualifications"]
    data = _merge_cache(data)
    apiResponse = requests.get(
        f"https://frc-api.firstinspires.org/v3.0/{season}/matches/{eventCode}?tournamentLevel=Qualification",
        auth=get_auth_headers(),
        timeout=20,
    )
    qualsData = _safe_parse_list(apiResponse, "Matches", context=f"{season} {eventCode} qualification matches")
    data["Qualifications"] = qualsData
    write_json_data(data, data_filename(season, eventCode))
    return qualsData


def request_playoff_matches(season: int, eventCode: str):
    data = load_json_data(data_filename(season, eventCode))
    if data is not None and "Playoffs" in data:
        return data["Playoffs"]
    data = _merge_cache(data)
    apiResponse = requests.get(
        f"https://frc-api.firstinspires.org/v3.0/{season}/matches/{eventCode}?tournamentLevel=Playoff",
        auth=get_auth_headers(),
        timeout=20,
    )
    playoffsData = _safe_parse_list(apiResponse, "Matches", context=f"{season} {eventCode} playoff matches")
    data["Playoffs"] = playoffsData
    write_json_data(data, data_filename(season, eventCode))
    return playoffsData


def request_event_awards(season: int, eventCode: str):
    data = load_json_data(data_filename(season, eventCode))
    if data is not None and "Awards" in data:
        return data["Awards"]
    data = _merge_cache(data)
    apiResponse = requests.get(
        f"https://frc-api.firstinspires.org/v3.0/{season}/awards/event/{eventCode}",
        auth=get_auth_headers(),
        timeout=20,
    )
    awardsData = _safe_parse_list(apiResponse, "Awards", context=f"{season} {eventCode} awards")
    data["Awards"] = awardsData
    write_json_data(data, data_filename(season, eventCode))
    return awardsData


def request_event_listings(season: int):
    data = load_json_data(season_events_filename(season))
    data = _merge_cache(data)
    for week in [1, 2, 3, 4, 5, 6]:
        key = f"Week {week}"
        if key in data:
            continue
        apiResponse = requests.get(
            f"https://frc-api.firstinspires.org/v3.0/{season}/events?excludeDistrict=true&weekNumber={week}",
            auth=get_auth_headers(),
            timeout=20,
        )
        
        if apiResponse.status_code in (401, 403):
            # Raise immediately for invalid credentials; UI can display a clear message
            raise AuthError(f"Invalid credentials when listing events for season {season}.")
        # Check if request was successful
        if apiResponse.status_code != 200:
            print(f"API request failed for {season} Week {week}: Status {apiResponse.status_code}")
            print(f"Response: {apiResponse.text[:200]}")
            data[key] = {"Events": []}
            continue
            
        # Check if response has content
        if not apiResponse.content.strip():
            print(f"Empty response for {season} Week {week}")
            data[key] = {"Events": []}
            continue
            
        try:
            data[key] = json.loads(apiResponse.content)
        except json.JSONDecodeError as e:
            print(f"JSON decode error for {season} Week {week}: {e}")
            print(f"Response content: {apiResponse.text[:200]}")
            data[key] = {"Events": []}
    write_json_data(data, season_events_filename(season))
    return data


def request_regional_adjustments(season: int):
    adjustmentsData = load_json_data(regional_adjustments_filename(season))
    if adjustmentsData is not None:
        data = adjustmentsData.get("Teams", {})
    else:
        data = {}
    adjustments = {}
    if data is None:
        data = {}
    for teamStr, adjustment in data.items():
        teamNumber = int(teamStr)
        adjustments[teamNumber] = adjustment
    return adjustments
