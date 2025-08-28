from __future__ import annotations

from typing import Any


def request_statbotics_epa(season: int, teamNumber: int, eventCode: str) -> Any:
    """
    Optional Statbotics access. Returns EPA mean if available, else raises ImportError
    only when called. Keeps compatibility with current behavior but more graceful.
    """
    try:
        from statbotics import Statbotics  # type: ignore
    except Exception as e:  # pragma: no cover - optional dependency
        raise ImportError("statbotics package is required for EPA calls") from e

    eventKey = str(season) + eventCode.lower()
    sb = Statbotics()
    return sb.get_team_event(teamNumber, eventKey)["epa"]["total_points"]["mean"]

