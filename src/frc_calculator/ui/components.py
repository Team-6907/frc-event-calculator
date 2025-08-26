from __future__ import annotations

import os
from typing import Callable, Iterable, Optional, Tuple, List

import streamlit as st

from frc_calculator.data.frc_events import data_filename, request_event_teams


# Common weeks constant used across UI
WEEKS: Tuple[int, ...] = (1, 2, 3, 4, 5, 6)


def _seed_ctx_from_query_params() -> None:
    """One-time seed of session state context from URL query params."""
    if st.session_state.get("_ctx_seeded", False):
        return
    try:
        qp = st.query_params if hasattr(st, "query_params") else {}
    except Exception:
        qp = {}

    # Map query param keys to session_state keys
    mapping = {
        "season": "ctx_season",
        "event": "ctx_event",
        "team": "ctx_team",
        "pool_week": "ctx_pool_week",
        "pool_rules": "ctx_pool_rules",
        "scope": "ctx_scope",
    }
    for qk, sk in mapping.items():
        if qk in qp and qp[qk]:
            st.session_state[sk] = str(qp[qk])

    st.session_state["_ctx_seeded"] = True


def _sync_query_params(params: dict) -> None:
    """Update URL query params with provided values if supported."""
    try:
        # Only include non-empty values; cast everything to str
        clean = {k: str(v) for k, v in params.items() if v is not None and v != ""}
        if hasattr(st, "query_params"):
            # Use new property API when available
            st.query_params.clear()
            st.query_params.update(clean)
        else:
            # Fallback (older Streamlit)
            st.experimental_set_query_params(**clean)
    except Exception:
        # Silently ignore if query params are not available
        pass


def render_context_bar(
    active_tab: str,
    default_scope: str,
    get_options_func: Callable[[int], list[tuple[str, str]]],
    *,
    season_default: int = 2025,
) -> dict:
    """Render a unified, scope-aware context bar.

    Returns a dict with keys that may include:
    - scope: "event" or "season"
    - season, event, team (for event scope)
    - pool_week, pool_rules (for season scope / Regional Pool)
    """
    _seed_ctx_from_query_params()

    # Scope is fixed per tab for now (no toggle). Persist it for deep links.
    scope = default_scope
    st.session_state["ctx_scope"] = scope

    container = st.container()
    key_prefix = f"{active_tab.lower()}_ctx"
    with container:
        if scope == "event":
            # Event-scoped: Season + Event; optional Team for points tab
            col1, col2, col3 = st.columns([1, 2, 1])

            # Season
            with col1:
                season_str = st.text_input(
                    "Season",
                    value=str(
                        st.session_state.get("ctx_season", str(season_default))
                    ),
                    key=f"{key_prefix}_season",
                    help="Competition season year",
                )
                season_int = int(season_str) if season_str.isdigit() else int(season_default)
                # Persist global season
                st.session_state["ctx_season"] = season_str

            # Event selection with manual override
            opts = get_options_func(season_int)
            mapping = {label: code for label, code in opts}
            labels = list(mapping.keys())

            with col2:
                current_code = str(st.session_state.get("ctx_event", "")).upper()
                # Try to resolve current label from code
                current_label = None
                if current_code:
                    for lbl, code in mapping.items():
                        if code.upper() == current_code:
                            current_label = lbl
                            break

                selected_label = st.selectbox(
                    "Select Event",
                    options=labels if labels else ["No events loaded"],
                    index=(labels.index(current_label) if current_label in labels else 0)
                    if labels
                    else 0,
                    key=f"{key_prefix}_event_select",
                    disabled=not bool(labels),
                    help="Choose from available events",
                )
                event_code = mapping.get(selected_label, "") if labels else ""

                # Manual override
                manual = st.checkbox(
                    "Enter custom code",
                    key=f"{key_prefix}_manual_event",
                    help="Override the dropdown",
                )
                if manual:
                    event_code = (
                        st.text_input(
                            "Event Code",
                            value=event_code or current_code,
                            placeholder="e.g., AZVA",
                            key=f"{key_prefix}_event_manual",
                        )
                        .strip()
                        .upper()
                    )

            with col3:
                team_value = None
                if active_tab.lower() in {"points", "calculate points", "team points"}:
                    # Try to provide a dropdown of teams for the selected event
                    team_opts: list[tuple[str, str]] = []
                    try:
                        if season_int and event_code:
                            has_creds = bool(os.getenv("AUTH_USERNAME") and os.getenv("AUTH_TOKEN"))
                            has_cache = os.path.exists(
                                data_filename(int(season_int), str(event_code))
                            )
                            if has_creds or has_cache:
                                raw = request_event_teams(int(season_int), str(event_code))
                            else:
                                raw = []
                            for t in raw:
                                num = t.get("teamNumber")
                                name = t.get("nameShort") or ""
                                label = f"{num} — {name}" if name else f"{num}"
                                team_opts.append((label, str(num)))
                            team_opts.sort(key=lambda x: int(x[1]))
                    except Exception:
                        team_opts = []

                    current_team = str(st.session_state.get("ctx_team", "")).strip()
                    if team_opts:
                        labels = [lab for lab, _ in team_opts]
                        values = [val for _, val in team_opts]
                        try:
                            default_index = values.index(current_team) if current_team in values else 0
                        except Exception:
                            default_index = 0
                        selected_label = st.selectbox(
                            "Team",
                            options=labels,
                            index=default_index,
                            key=f"{key_prefix}_team_select",
                            help="Select a team from this event",
                        )
                        mapping = {lab: val for lab, val in team_opts}
                        team_value = mapping.get(selected_label, values[0] if values else "")
                    else:
                        team_value = st.text_input(
                            "Team Number",
                            value=current_team or "1234",
                            placeholder="e.g., 254",
                            key=f"{key_prefix}_team",
                            help="FRC team number",
                        )
                    # Persist global team
                    st.session_state["ctx_team"] = team_value

            # Persist selections to session and URL
            st.session_state["ctx_event"] = event_code
            # Update query params for deep links
            _sync_query_params(
                {
                    "scope": scope,
                    "season": season_int,
                    "event": event_code,
                    "team": st.session_state.get("ctx_team", None),
                }
            )

            return {
                "scope": scope,
                "season": season_int,
                "event": event_code,
                "team": st.session_state.get("ctx_team", team_value),
            }

        else:
            # Season-scoped (Regional Pool): Season + Rules + Week
            col1, col2, col3 = st.columns([1, 1, 1])
            with col1:
                season_str = st.text_input(
                    "Season",
                    value=str(
                        st.session_state.get("ctx_season", str(season_default))
                    ),
                    key=f"{key_prefix}_season",
                    help="Competition season year",
                )
                season_int = int(season_str) if season_str.isdigit() else int(season_default)
                st.session_state["ctx_season"] = season_str

            with col2:
                rules_str = st.text_input(
                    "Rules Season",
                    value=str(st.session_state.get("ctx_pool_rules", str(season_int))),
                    key=f"{key_prefix}_pool_rules",
                    help="Which year's rules to use",
                )
                st.session_state["ctx_pool_rules"] = rules_str

            with col3:
                week_val = st.selectbox(
                    "Week",
                    options=list(WEEKS),
                    index=(list(WEEKS).index(int(st.session_state.get("ctx_pool_week", 6)))
                           if str(st.session_state.get("ctx_pool_week", "6")).isdigit()
                           else 5),
                    key=f"{key_prefix}_pool_week_select",
                    help="Calculate standings through this week",
                )
                st.session_state["ctx_pool_week"] = int(week_val)

            # Update query params
            _sync_query_params(
                {
                    "scope": scope,
                    "season": season_int,
                    "pool_rules": rules_str,
                    "pool_week": st.session_state.get("ctx_pool_week", week_val),
                }
            )

            return {
                "scope": scope,
                "season": season_int,
                "pool_rules": rules_str,
                "pool_week": int(st.session_state.get("ctx_pool_week", week_val)),
            }


def select_event_single(
    season_default: int,
    key_prefix: str,
    get_options_func: Callable[[int], list[tuple[str, str]]],
) -> tuple[int, str]:
    """Render season + single event selector with manual override and fallback.

    Returns (season_int, event_code_upper).
    """
    season_str = st.text_input(
        "Season",
        value=str(season_default),
        help="Enter the competition season year",
        key=f"{key_prefix}_season",
    )

    season_int = int(season_str) if season_str.isdigit() else int(season_default)

    opts = get_options_func(season_int)
    event_code = ""

    if opts:
        selected_label = st.selectbox(
            "Select Event",
            options=[o[0] for o in opts],
            index=0,
            key=f"{key_prefix}_event_select",
            help="Choose from available events",
        )
        mapping = {label: code for label, code in opts}
        event_code = mapping.get(selected_label, "")

        # Manual override
        if st.checkbox(
            "Enter custom event code", key=f"manual_override_{key_prefix}"
        ):
            event_code = (
                st.text_input(
                    "Event Code",
                    value=event_code,
                    placeholder="e.g., AZVA, CAFR, CTHAR",
                    key=f"{key_prefix}_event_manual",
                    help="Enter the 4-5 character event code",
                )
                .strip()
                .upper()
            )
    else:
        st.info(
            "💡 No events loaded. Enter credentials above or provide an event code."
        )
        event_code = (
            st.text_input(
                "Event Code",
                value="AZVA",
                placeholder="e.g., AZVA, CAFR, CTHAR",
                key=f"{key_prefix}_event_manual_fallback",
                help="Enter the 4-5 character event code",
            )
            .strip()
            .upper()
        )

    return season_int, event_code


def ensure_event_data_available(season: int, event_code: str) -> bool:
    """Ensure data can be loaded: credentials or cache must exist.

    Shows an error and returns False when unavailable.
    """
    if not (os.getenv("AUTH_USERNAME") and os.getenv("AUTH_TOKEN")):
        if not os.path.exists(data_filename(int(season), str(event_code))):
            st.error(
                "🔐 **Credentials required**: Set up your API credentials above to fetch this event data."
            )
            return False
    return True


def make_status_progress(status, *, filter_keys: Optional[Iterable[str]] = None):
    """Create a progress callback that writes filtered messages to a Streamlit status block."""

    def _cb(msg: str):
        try:
            if not isinstance(msg, str):
                return
            if filter_keys:
                if any(k in msg for k in filter_keys):
                    status.write(f"• {msg}")
            else:
                status.write(f"• {msg}")
        except Exception:
            # Ignore UI write errors
            pass

    return _cb


def validate_int(value: str, field_name: str) -> Optional[int]:
    """Validate a string as int, show a warning, and return the int or None."""
    if not value.isdigit():
        st.warning(f"⚠️ Please enter a valid number for {field_name}.")
        return None
    return int(value)


def select_event_multi(
    season_default: int,
    key_prefix: str,
    get_options_func: Callable[[int], list[tuple[str, str]]],
    *,
    max_selections: int = 5,
    fallback_default: Optional[List[str]] = None,
) -> tuple[int, List[str]]:
    """Render season + multi-event selector with manual override and fallback.

    Returns (season_int, [event_codes_upper]).
    """
    season_str = st.text_input(
        "Season",
        value=str(season_default),
        help="Enter the competition season year",
        key=f"{key_prefix}_season",
        disabled=False,
    )
    season_int = int(season_str) if season_str.isdigit() else int(season_default)

    opts = get_options_func(season_int)
    event_codes: List[str] = []

    if opts:
        selected_labels = st.multiselect(
            "Select Events (up to 5)",
            options=[o[0] for o in opts],
            default=[opts[0][0]] if opts else [],
            key=f"{key_prefix}_event_select",
            help="Choose up to 5 events to compare",
            max_selections=max_selections,
        )
        mapping = {label: code for label, code in opts}
        event_codes = [mapping.get(label, "") for label in selected_labels]

        if st.checkbox("Enter custom event codes", key=f"manual_override_{key_prefix}"):
            custom_codes = st.text_area(
                "Event Codes (one per line)",
                value="\n".join(event_codes),
                placeholder="AZVA\nCAFR\nCTHAR",
                key=f"{key_prefix}_event_manual",
                help="Enter event codes, one per line (max 5)",
                height=100,
            )
            event_codes = [
                code.strip().upper()
                for code in custom_codes.split("\n")
                if code.strip()
            ][:max_selections]
    else:
        st.info(
            "💡 No events loaded. Enter credentials above or provide event codes."
        )
        default_codes = fallback_default or ["AZVA"]
        custom_codes = st.text_area(
            "Event Codes (one per line)",
            value="\n".join(default_codes),
            placeholder="AZVA\nCAFR\nCTHAR",
            key=f"{key_prefix}_event_manual_fallback",
            help="Enter event codes, one per line (max 5)",
            height=100,
        )
        event_codes = [
            code.strip().upper()
            for code in custom_codes.split("\n")
            if code.strip()
        ][:max_selections]

    return season_int, [c for c in event_codes if c]


def epa_progress_ui():
    """Provide EPA progress callback and cleanup for consistent UI.

    Returns (callback, cleanup_fn).
    """
    progress_bar = st.progress(0.0)
    progress_text = st.empty()
    epa_container = st.empty()

    def _cb(msg):
        try:
            if isinstance(msg, dict) and msg.get("type") == "epa_progress":
                current = msg.get("current", 0)
                total = msg.get("total", 1) or 1
                team = msg.get("team", "")
                eta = msg.get("eta", "")
                progress = min(max(current / total, 0.0), 1.0)
                progress_bar.progress(progress)
                percent = int(progress * 100)
                progress_text.text(
                    f"🤖 Fetching EPA data: {percent}% ({current}/{total} teams){eta}"
                )
                if isinstance(current, int) and (current % 3 == 0 or current <= 3):
                    epa_container.caption(f"Processing Team {team}...")
        except Exception:
            pass

    def _cleanup():
        try:
            progress_bar.empty()
            progress_text.empty()
            epa_container.empty()
        except Exception:
            pass

    return _cb, _cleanup
