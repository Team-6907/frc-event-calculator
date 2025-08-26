from __future__ import annotations

import os
from typing import Callable, Iterable, Optional, Tuple, List

import streamlit as st

from frc_calculator.data.frc_events import data_filename


# Common weeks constant used across UI
WEEKS: Tuple[int, ...] = (1, 2, 3, 4, 5, 6)


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

