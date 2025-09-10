"""
Event statistics utilities for comprehensive FRC event analysis.
Provides functions to calculate various event statistics and metrics.
"""

from __future__ import annotations
from typing import Dict, List, Tuple, Optional, Any
import statistics
import os
from frc_calculator.models.event import Event
from frc_calculator.models.team import Team
from frc_calculator.models.match import Match
from frc_calculator.utils.io_utils import load_json_data, write_json_data
from frc_calculator.data.frc_events import data_filename


def calculate_average_qual_scores(event: Event) -> Dict[str, float]:
    """Calculate average qualification match scores for red and blue alliances."""
    red_scores = []
    blue_scores = []

    for match in event.qualsMatches.values():
        if match.redScore and match.blueScore:
            if match.redScore[0] and match.blueScore[0]:
                red_scores.append(match.redScore[0])  # Final score is at index 0
                blue_scores.append(match.blueScore[0])

    if not red_scores or not blue_scores:
        return {"red_avg": 0.0, "blue_avg": 0.0, "overall_avg": 0.0, "total_matches": 0}

    red_avg = statistics.mean(red_scores)
    blue_avg = statistics.mean(blue_scores)
    overall_avg = statistics.mean(red_scores + blue_scores)

    return {
        "red_avg": round(red_avg, 2),
        "blue_avg": round(blue_avg, 2),
        "overall_avg": round(overall_avg, 2),
        "total_matches": len(red_scores),
    }


def get_playoff_match_scores(event: Event) -> List[Dict[str, Any]]:
    """Get scores for all playoff matches (Match 11 onwards) for both alliances."""
    playoff_scores = []

    # Sort playoff matches by match number
    sorted_matches = sorted(event.playoffMatches.items())

    for match_num, match in sorted_matches:
        if match_num >= 11:  # Match 11 onwards
            # Handle None scores properly
            red_score = None
            blue_score = None

            if match.redScore and len(match.redScore) > 0:
                red_score = match.redScore[0]  # First element is final score

            if match.blueScore and len(match.blueScore) > 0:
                blue_score = match.blueScore[0]  # First element is final score

            playoff_scores.append(
                {
                    "match_number": match_num,
                    "match_name": str(match),
                    "red_score": red_score,
                    "blue_score": blue_score,
                    "red_alliance": (
                        match.redAlliance.allianceNumber
                        if hasattr(match.redAlliance, "allianceNumber")
                        else "TBD"
                    ),
                    "blue_alliance": (
                        match.blueAlliance.allianceNumber
                        if hasattr(match.blueAlliance, "allianceNumber")
                        else "TBD"
                    ),
                }
            )

    return playoff_scores


def get_ranking_points_details(
    event: Event, ranks: List[int] = [1, 4, 8]
) -> List[Dict[str, Any]]:
    """Get detailed ranking points for specified ranks."""
    ranking_details = []

    for rank in ranks:
        try:
            team = event.get_team_from_rank(rank)
            ranking_details.append(
                {
                    "rank": rank,
                    "team_number": team.teamNumber,
                    "team_name": team.name,
                    "ranking_points": team.sortOrder[0] if team.sortOrder else 0,
                    "wins": team.WLT[0] if hasattr(team, "WLT") and team.WLT else 0,
                    "losses": team.WLT[1] if hasattr(team, "WLT") and team.WLT else 0,
                    "ties": team.WLT[2] if hasattr(team, "WLT") and team.WLT else 0,
                }
            )
        except (KeyError, IndexError):
            ranking_details.append(
                {
                    "rank": rank,
                    "team_number": "N/A",
                    "team_name": "No team at this rank",
                    "ranking_points": 0,
                    "wins": 0,
                    "losses": 0,
                    "ties": 0,
                }
            )

    return ranking_details


def get_team_epa_data(
    event: Event, progress_callback=None, use_cache=True
) -> List[Dict[str, Any]]:
    """Get EPA data for all teams participating in the event with caching support and batch processing."""
    cache_filename = data_filename(event.season, event.eventCode)

    # Try to load cached EPA data first
    if use_cache:
        cached_data = load_json_data(cache_filename)
        if cached_data and "EPAData" in cached_data:
            if progress_callback:
                try:
                    progress_callback("Loading EPA data from cache...")
                except Exception:
                    pass
            return cached_data["EPAData"]

    # If no cache or cache disabled, fetch EPA data using batch processing
    epa_data = []
    total_teams = len(event.teams)

    if progress_callback:
        try:
            progress_callback(
                f"Fetching EPA data for {total_teams} teams using batch processing..."
            )
        except Exception:
            pass

    try:
        # Use correct Statbotics API batch fetching
        from statbotics import Statbotics  # type: ignore

        sb = Statbotics()
        eventKey = str(event.season) + event.eventCode.lower()

        if progress_callback:
            try:
                progress_callback(
                    {
                        "type": "epa_progress",
                        "current": 0,
                        "total": total_teams,
                        "team": "Batch fetch",
                        "eta": "",
                    }
                )
            except Exception:
                pass

        # Get all team events for this event using the correct API method
        team_events = sb.get_team_events(
            event=eventKey, limit=200
        )  # Higher limit to get all teams

        # Create a lookup dictionary for EPA values
        epa_lookup = {}
        if team_events:
            for te in team_events:
                if te and "team" in te and "epa" in te:
                    team_num = te["team"]
                    epa_data_obj = te["epa"]

                    # Extract EPA mean value from the nested structure
                    epa_val = None
                    if (
                        isinstance(epa_data_obj, dict)
                        and "total_points" in epa_data_obj
                    ):
                        total_points = epa_data_obj["total_points"]
                        if isinstance(total_points, dict) and "mean" in total_points:
                            epa_val = total_points["mean"]

                    epa_lookup[team_num] = epa_val

        # Process all teams using the lookup
        for i, team in enumerate(event.teams.values()):
            if (
                progress_callback and i % 10 == 0
            ):  # Update every 10th team for batch mode
                try:
                    progress_callback(
                        {
                            "type": "epa_progress",
                            "current": i + 1,
                            "total": total_teams,
                            "team": team.teamNumber,
                            "eta": " (batch mode)",
                        }
                    )
                except Exception:
                    pass

            epa = epa_lookup.get(team.teamNumber)
            epa_data.append(
                {
                    "team_number": team.teamNumber,
                    "team_name": team.name,
                    "epa": (
                        round(epa, 2)
                        if epa is not None and isinstance(epa, (int, float))
                        else "N/A"
                    ),
                    "rank": team.ranking,
                }
            )

    except Exception as batch_error:
        # Fallback to individual requests if batch fails
        if progress_callback:
            try:
                progress_callback(
                    f"Batch fetch failed ({str(batch_error)}), falling back to individual requests..."
                )
            except Exception:
                pass

        import time

        start_time = time.time()

        for i, team in enumerate(event.teams.values()):
            # Update progress every team with ETA
            if progress_callback:
                try:
                    elapsed = time.time() - start_time
                    if i > 0:  # Avoid division by zero
                        eta_seconds = (elapsed / i) * (total_teams - i)
                        eta_minutes = eta_seconds / 60
                        eta_str = (
                            f", ETA: {eta_minutes:.1f}m"
                            if eta_minutes > 1
                            else f", ETA: {eta_seconds:.0f}s"
                        )
                    else:
                        eta_str = ""

                    progress_callback(
                        {
                            "type": "epa_progress",
                            "current": i + 1,
                            "total": total_teams,
                            "team": team.teamNumber,
                            "eta": eta_str,
                        }
                    )
                except Exception:
                    pass

            try:
                epa = team.get_statbotics_epa()
                epa_data.append(
                    {
                        "team_number": team.teamNumber,
                        "team_name": team.name,
                        "epa": round(epa, 2) if epa is not None else "N/A",
                        "rank": team.ranking,
                    }
                )
            except Exception:
                # If EPA retrieval fails, still include team with N/A EPA
                epa_data.append(
                    {
                        "team_number": team.teamNumber,
                        "team_name": team.name,
                        "epa": "N/A",
                        "rank": team.ranking,
                    }
                )

    # Sort by EPA (highest first), putting N/A values at the end
    epa_data.sort(
        key=lambda x: (x["epa"] == "N/A", -x["epa"] if x["epa"] != "N/A" else 0)
    )

    # Cache the EPA data
    if use_cache:
        try:
            cached_data = load_json_data(cache_filename) or {}
            cached_data["EPAData"] = epa_data
            write_json_data(cached_data, cache_filename)
            if progress_callback:
                try:
                    progress_callback("EPA data cached for future use")
                except Exception:
                    pass
        except Exception:
            # If caching fails, continue without caching
            pass

    return epa_data


def get_alliance_structure(event: Event) -> Dict[str, List[Dict[str, Any]]]:
    """Get alliance captains, 1st picks, and non-playoff teams."""
    captains = []
    first_picks = []
    non_playoff_teams = []

    # Get all teams in alliances
    alliance_teams = set()

    for alliance in event.alliances.values():
        if alliance.teams:
            # Captain (first team)
            captain = alliance.teams[0]
            captains.append(
                {
                    "alliance_number": alliance.allianceNumber,
                    "team_number": captain.teamNumber,
                    "team_name": captain.name,
                    "rank": captain.ranking,
                }
            )
            alliance_teams.add(captain.teamNumber)

            # First pick (second team)
            if len(alliance.teams) > 1 and alliance.teams[1] is not None:
                first_pick = alliance.teams[1]
                first_picks.append(
                    {
                        "alliance_number": alliance.allianceNumber,
                        "team_number": first_pick.teamNumber,
                        "team_name": first_pick.name,
                        "rank": first_pick.ranking,
                    }
                )
                alliance_teams.add(first_pick.teamNumber)

            # Add all alliance team numbers to the set
            for team in alliance.teams:
                if team is not None:
                    alliance_teams.add(team.teamNumber)

    # Find teams that didn't make playoffs
    for team in event.teams.values():
        if team.teamNumber not in alliance_teams:
            non_playoff_teams.append(
                {
                    "team_number": team.teamNumber,
                    "team_name": team.name,
                    "rank": team.ranking,
                }
            )

    # Sort lists by rank
    captains.sort(key=lambda x: x["rank"] if x["rank"] else float("inf"))
    first_picks.sort(key=lambda x: x["rank"] if x["rank"] else float("inf"))
    non_playoff_teams.sort(key=lambda x: x["rank"] if x["rank"] else float("inf"))

    return {
        "captains": captains,
        "first_picks": first_picks,
        "non_playoff_teams": non_playoff_teams,
    }


def find_multi_year_teams(
    current_event_code: str, current_season: int, years_to_check: List[int] = None
) -> List[Dict[str, Any]]:
    """Find teams that competed in the same regional across multiple years."""
    if years_to_check is None:
        years_to_check = [
            current_season - 1,
            current_season + 1,
        ]  # Check previous and next year

    multi_year_teams = []
    current_teams = set()

    # Load current event teams
    try:
        current_data = load_json_data(
            f"cache/{current_season}-{current_event_code}.json"
        )
        if current_data and "Teams" in current_data:
            current_teams = {team["teamNumber"] for team in current_data["Teams"]}
    except Exception:
        return []

    # Check other years
    for year in years_to_check:
        if year == current_season:
            continue

        try:
            other_data = load_json_data(f"cache/{year}-{current_event_code}.json")
            if other_data and "Teams" in other_data:
                other_teams = {team["teamNumber"] for team in other_data["Teams"]}
                common_teams = current_teams.intersection(other_teams)

                if common_teams:
                    # Get team details for common teams
                    for team_data in other_data["Teams"]:
                        if team_data["teamNumber"] in common_teams:
                            multi_year_teams.append(
                                {
                                    "team_number": team_data["teamNumber"],
                                    "team_name": team_data.get("nameShort", "Unknown"),
                                    "years": f"{year}, {current_season}",
                                    "other_year": year,
                                }
                            )
        except Exception:
            continue

    # Remove duplicates and sort by team number
    seen = set()
    unique_teams = []
    for team in multi_year_teams:
        if team["team_number"] not in seen:
            seen.add(team["team_number"])
            unique_teams.append(team)

    unique_teams.sort(key=lambda x: x["team_number"])
    return unique_teams


def calculate_radar_chart_data(
    event: Event, progress_callback=None, include_epa=True
) -> Dict[str, float]:
    """Calculate the 8 dimensions for radar chart analysis."""
    radar_data = {}

    # 1. Overall: Enhanced competitiveness measure
    if progress_callback:
        try:
            progress_callback("Calculating Overall dimension...")
        except Exception:
            pass

    avg_scores = calculate_average_qual_scores(event)
    radar_data["Overall"] = avg_scores["overall_avg"]

    # 2. RP: Enhanced depth measure based on 4th team performance
    if progress_callback:
        try:
            progress_callback("Calculating RP dimension...")
        except Exception:
            pass

    try:
        fourth_team = event.get_team_from_rank(4)
        fourth_rp = fourth_team.sortOrder[0] if fourth_team.sortOrder else 0
        radar_data["RP"] = fourth_rp
    except (KeyError, IndexError):
        radar_data["RP"] = 0

    # 3. TANK: Selected team competitiveness based on non-selected teams' EPA median
    # 4. HOME: Ground Head Snakes scale based on recent 2 years returning teams' EPA median
    if include_epa:
        if progress_callback:
            try:
                progress_callback("Calculating TANK and HOME dimensions...")
            except Exception:
                pass

        epa_data = get_team_epa_data(event, progress_callback)
        alliance_structure = get_alliance_structure(event)

        # TANK calculation - Enhanced non-playoff team strength measure
        non_playoff_epas = []
        for team_data in epa_data:
            team_num = team_data["team_number"]
            if any(
                t["team_number"] == team_num
                for t in alliance_structure["non_playoff_teams"]
            ):
                if isinstance(team_data["epa"], (int, float)) and team_data["epa"] != 0:
                    non_playoff_epas.append(team_data["epa"])

        if non_playoff_epas:
            tank_median = statistics.median(non_playoff_epas)
            radar_data["TANK"] = tank_median
        else:
            radar_data["TANK"] = 0

        # HOME calculation
        multi_year_teams = find_multi_year_teams(
            event.eventCode, event.season, [event.season - 1, event.season - 2]
        )
        multi_year_numbers = {t["team_number"] for t in multi_year_teams}

        home_epas = []
        for team_data in epa_data:
            if team_data["team_number"] in multi_year_numbers:
                if isinstance(team_data["epa"], (int, float)) and team_data["epa"] != 0:
                    home_epas.append(team_data["epa"])

        if home_epas:
            home_median = statistics.median(home_epas)
            radar_data["HOME"] = home_median
        else:
            radar_data["HOME"] = 6907
    else:
        radar_data["TANK"] = 0
        radar_data["HOME"] = 0

    # 5. REIGN: Count of teams that made top 16 in current year AND also made top 16 in 2023 or 2024
    if progress_callback:
        try:
            progress_callback("Calculating REIGN dimension...")
        except Exception:
            pass

    current_top16 = set()
    alliance_structure = (
        get_alliance_structure(event) if not include_epa else alliance_structure
    )

    # Get current year's top 16 (captains + first picks)
    for captain in alliance_structure["captains"]:
        current_top16.add(captain["team_number"])
    for pick in alliance_structure["first_picks"]:
        current_top16.add(pick["team_number"])

    reign_teams = set()  # Use set to avoid double counting same team across years
    check_years = (
        [2023, 2024] if event.season == 2025 else [event.season - 2, event.season - 1]
    )

    for year in check_years:
        hasHistory = 0
        if year == event.season:
            continue

        try:
            # First try to load cached data
            historical_data = load_json_data(f"cache/{year}-{event.eventCode}.json")

            # If no cached data, try to fetch it
            if not historical_data:
                if progress_callback:
                    try:
                        progress_callback(
                            f"Fetching historical data for {year} {event.eventCode}..."
                        )
                    except Exception:
                        pass

                try:
                    # Import here to avoid circular imports
                    from frc_calculator.models.event import Event as HistoricalEvent

                    # Fetch the historical event data (this will cache it)
                    _ = HistoricalEvent(year, event.eventCode)

                    # Load the newly cached data
                    historical_data = load_json_data(
                        f"cache/{year}-{event.eventCode}.json"
                    )
                except Exception as e:
                    if progress_callback:
                        try:
                            progress_callback(
                                f"Could not fetch {year} {event.eventCode}: {str(e)}"
                            )
                        except Exception:
                            pass
                    continue

            # Process the historical data if available
            if historical_data and historical_data["Alliances"]:
                hasHistory += 1
                historical_top16 = set()
                for alliance_data in historical_data["Alliances"]:
                    # Add captain (always exists)
                    if "captain" in alliance_data and alliance_data["captain"]:
                        historical_top16.add(alliance_data["captain"])

                    # Add first pick (round1)
                    if "round1" in alliance_data and alliance_data["round1"]:
                        historical_top16.add(alliance_data["round1"])

                # Add teams that are in both current and historical top 16
                reign_teams.update(current_top16.intersection(historical_top16))
        except Exception as e:
            if progress_callback:
                try:
                    progress_callback(f"Error processing {year} data: {str(e)}")
                except Exception:
                    pass
            continue

    # REIGN: More veteran teams (stronger region) should get LOWER points (weaker region)
    # Scale: 0 teams = 20 points (weak region), 8+ teams = 0 points (strong region)
    if hasHistory != 0:
        reign_count = len(reign_teams)
    else:
        reign_count = 6907
    radar_data["REIGN"] = reign_count

    # 6. Title: Match 11+ average points
    if progress_callback:
        try:
            progress_callback("Calculating Title dimension...")
        except Exception:
            pass

    playoff_scores = get_playoff_match_scores(event)
    if playoff_scores:
        all_playoff_points = []
        for match in playoff_scores:
            # Filter out None values
            if match["red_score"] is not None and isinstance(
                match["red_score"], (int, float)
            ):
                all_playoff_points.append(match["red_score"])
            if match["blue_score"] is not None and isinstance(
                match["blue_score"], (int, float)
            ):
                all_playoff_points.append(match["blue_score"])

        if all_playoff_points:
            playoff_avg = statistics.mean(all_playoff_points)
            radar_data["TITLE"] = playoff_avg
        else:
            radar_data["TITLE"] = 0
    else:
        radar_data["TITLE"] = 0

    # 7. CHAMP: Highest score from finals matches
    if progress_callback:
        try:
            progress_callback("Calculating CHAMP dimension...")
        except Exception:
            pass

    finals_scores = []
    for match in playoff_scores:
        # Check if this is a finals match (2025+ format: matches 14-16 are finals)
        is_finals = False
        if match["match_number"] >= 14 and match["match_number"] <= 16:
            is_finals = True
        elif "Final" in match["match_name"]:
            is_finals = True

        if is_finals:
            # Filter out None values and ensure scores are valid numbers
            if (
                match["red_score"] is not None
                and isinstance(match["red_score"], (int, float))
                and match["red_score"] > 0
            ):
                finals_scores.append(match["red_score"])
            if (
                match["blue_score"] is not None
                and isinstance(match["blue_score"], (int, float))
                and match["blue_score"] > 0
            ):
                finals_scores.append(match["blue_score"])

    if finals_scores:
        champ_score = max(finals_scores)
        # CHAMP: Higher finals scores (stronger finals) should get LOWER points (weaker region)
        # Scale: 100 score = 18 points, 200 score = 8 points, 300 score = 0 points
        radar_data["CHAMP"] = champ_score
    else:
        radar_data["CHAMP"] = 0

    return radar_data


def calculate_event_statistics(
    event: Event, progress_callback=None, include_epa=True
) -> Dict[str, Any]:
    """Calculate comprehensive event statistics."""
    if progress_callback:
        try:
            progress_callback("Calculating average qualification scores...")
        except Exception:
            pass

    avg_scores = calculate_average_qual_scores(event)

    if progress_callback:
        try:
            progress_callback("Extracting playoff match data...")
        except Exception:
            pass

    playoff_scores = get_playoff_match_scores(event)

    if progress_callback:
        try:
            progress_callback("Analyzing ranking details...")
        except Exception:
            pass

    ranking_details = get_ranking_points_details(event)

    if progress_callback:
        try:
            progress_callback("Analyzing alliance structure...")
        except Exception:
            pass

    alliance_structure = get_alliance_structure(event)

    if progress_callback:
        try:
            progress_callback("Checking multi-year team participation...")
        except Exception:
            pass

    multi_year_teams = find_multi_year_teams(event.eventCode, event.season)

    # Only fetch EPA data if requested
    epa_data = []
    if include_epa:
        if progress_callback:
            try:
                progress_callback("Starting EPA data collection...")
            except Exception:
                pass

        epa_data = get_team_epa_data(event, progress_callback)

    # Calculate radar chart data
    if progress_callback:
        try:
            progress_callback("Calculating radar chart data...")
        except Exception:
            pass

    radar_chart_data = calculate_radar_chart_data(event, progress_callback, include_epa)

    return {
        "average_scores": avg_scores,
        "playoff_scores": playoff_scores,
        "ranking_details": ranking_details,
        "epa_data": epa_data,
        "alliance_structure": alliance_structure,
        "multi_year_teams": multi_year_teams,
        "radar_chart_data": radar_chart_data,
    }
