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
        "total_matches": len(red_scores)
    }


def get_playoff_match_scores(event: Event) -> List[Dict[str, Any]]:
    """Get scores for all playoff matches (Match 11 onwards) for both alliances."""
    playoff_scores = []
    
    # Sort playoff matches by match number
    sorted_matches = sorted(event.playoffMatches.items())
    
    for match_num, match in sorted_matches:
        if match_num >= 11:  # Match 11 onwards
            playoff_scores.append({
                "match_number": match_num,
                "match_name": str(match),
                "red_score": match.redScore[0] if match.redScore else 0,
                "blue_score": match.blueScore[0] if match.blueScore else 0,
                "red_alliance": match.redAlliance.allianceNumber if hasattr(match.redAlliance, 'allianceNumber') else "TBD",
                "blue_alliance": match.blueAlliance.allianceNumber if hasattr(match.blueAlliance, 'allianceNumber') else "TBD"
            })
    
    return playoff_scores


def get_ranking_points_details(event: Event, ranks: List[int] = [1, 4, 8]) -> List[Dict[str, Any]]:
    """Get detailed ranking points for specified ranks."""
    ranking_details = []
    
    for rank in ranks:
        try:
            team = event.get_team_from_rank(rank)
            ranking_details.append({
                "rank": rank,
                "team_number": team.teamNumber,
                "team_name": team.name,
                "ranking_points": team.sortOrder[0] if team.sortOrder else 0,
                "wins": team.WLT[0] if hasattr(team, 'WLT') and team.WLT else 0,
                "losses": team.WLT[1] if hasattr(team, 'WLT') and team.WLT else 0,
                "ties": team.WLT[2] if hasattr(team, 'WLT') and team.WLT else 0,
            })
        except (KeyError, IndexError):
            ranking_details.append({
                "rank": rank,
                "team_number": "N/A",
                "team_name": "No team at this rank",
                "ranking_points": 0,
                "wins": 0,
                "losses": 0,
                "ties": 0,
            })
    
    return ranking_details


def get_team_epa_data(event: Event, progress_callback=None, use_cache=True) -> List[Dict[str, Any]]:
    """Get EPA data for all teams participating in the event with caching support."""
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
    
    # If no cache or cache disabled, fetch EPA data
    epa_data = []
    total_teams = len(event.teams)
    
    if progress_callback:
        try:
            progress_callback(f"Fetching EPA data for {total_teams} teams (this may take a while)...")
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
                    eta_str = f", ETA: {eta_minutes:.1f}m" if eta_minutes > 1 else f", ETA: {eta_seconds:.0f}s"
                else:
                    eta_str = ""
                
                progress_callback({
                    'type': 'epa_progress',
                    'current': i + 1,
                    'total': total_teams,
                    'team': team.teamNumber,
                    'eta': eta_str
                })
            except Exception:
                pass
        
        try:
            epa = team.get_statbotics_epa()
            epa_data.append({
                "team_number": team.teamNumber,
                "team_name": team.name,
                "epa": round(epa, 2) if epa is not None else "N/A",
                "rank": team.ranking
            })
        except Exception:
            # If EPA retrieval fails, still include team with N/A EPA
            epa_data.append({
                "team_number": team.teamNumber,
                "team_name": team.name,
                "epa": "N/A",
                "rank": team.ranking
            })
    
    # Sort by EPA (highest first), putting N/A values at the end
    epa_data.sort(key=lambda x: (x["epa"] == "N/A", -x["epa"] if x["epa"] != "N/A" else 0))
    
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
            captains.append({
                "alliance_number": alliance.allianceNumber,
                "team_number": captain.teamNumber,
                "team_name": captain.name,
                "rank": captain.ranking
            })
            alliance_teams.add(captain.teamNumber)
            
            # First pick (second team)
            if len(alliance.teams) > 1 and alliance.teams[1] is not None:
                first_pick = alliance.teams[1]
                first_picks.append({
                    "alliance_number": alliance.allianceNumber,
                    "team_number": first_pick.teamNumber,
                    "team_name": first_pick.name,
                    "rank": first_pick.ranking
                })
                alliance_teams.add(first_pick.teamNumber)
                
            # Add all alliance team numbers to the set
            for team in alliance.teams:
                if team is not None:
                    alliance_teams.add(team.teamNumber)
    
    # Find teams that didn't make playoffs
    for team in event.teams.values():
        if team.teamNumber not in alliance_teams:
            non_playoff_teams.append({
                "team_number": team.teamNumber,
                "team_name": team.name,
                "rank": team.ranking
            })
    
    # Sort lists by rank
    captains.sort(key=lambda x: x["rank"] if x["rank"] else float('inf'))
    first_picks.sort(key=lambda x: x["rank"] if x["rank"] else float('inf'))
    non_playoff_teams.sort(key=lambda x: x["rank"] if x["rank"] else float('inf'))
    
    return {
        "captains": captains,
        "first_picks": first_picks,
        "non_playoff_teams": non_playoff_teams
    }


def find_multi_year_teams(current_event_code: str, current_season: int, years_to_check: List[int] = None) -> List[Dict[str, Any]]:
    """Find teams that competed in the same regional across multiple years."""
    if years_to_check is None:
        years_to_check = [current_season - 1, current_season + 1]  # Check previous and next year
    
    multi_year_teams = []
    current_teams = set()
    
    # Load current event teams
    try:
        current_data = load_json_data(f"cache/{current_season}-{current_event_code}.json")
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
                            multi_year_teams.append({
                                "team_number": team_data["teamNumber"],
                                "team_name": team_data.get("nameShort", "Unknown"),
                                "years": f"{year}, {current_season}",
                                "other_year": year
                            })
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


def calculate_event_statistics(event: Event, progress_callback=None, include_epa=True) -> Dict[str, Any]:
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
    
    return {
        "average_scores": avg_scores,
        "playoff_scores": playoff_scores,
        "ranking_details": ranking_details,
        "epa_data": epa_data,
        "alliance_structure": alliance_structure,
        "multi_year_teams": multi_year_teams
    }