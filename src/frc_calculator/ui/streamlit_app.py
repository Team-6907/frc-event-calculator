from __future__ import annotations

import os
import traceback
from typing import Any, Dict

import streamlit as st

from frc_calculator.models.event import Event
from frc_calculator.services.season import Season
from frc_calculator.data.frc_events import (
    request_event_listings,
    data_filename,
    AuthError,
    ApiError,
)
from frc_calculator.utils.io_utils import load_json_data


st.set_page_config(page_title="FRC Event Calculator", layout="wide")


def set_env_from_sidebar() -> bool:
    st.sidebar.header("FRC API Credentials")
    default_user = os.getenv("AUTH_USERNAME", "")
    default_token = os.getenv("AUTH_TOKEN", "")
    username = st.sidebar.text_input("AUTH_USERNAME", value=default_user)
    token = st.sidebar.text_input("AUTH_TOKEN", value=default_token, type="password")
    # Do not write .env automatically; just set process env for this run
    os.environ["AUTH_USERNAME"] = username
    os.environ["AUTH_TOKEN"] = token

    st.sidebar.caption(
        "Your credentials are only used locally to call the FRC Events API."
    )

    if st.sidebar.button("Refresh event listings", key="refresh_event_listings_btn"):
        try:
            get_event_options.clear()
        except Exception:
            pass
        st.toast("Event listings cache cleared.", icon="🔄")

    # Validate credentials button
    if username and token:
        if st.sidebar.button("Validate credentials", key="validate_creds_btn"):
            try:
                # Use a lightweight call (week 1 listings) to validate
                request_event_listings(2024)
                st.sidebar.success("Credentials look valid.")
            except AuthError:
                st.sidebar.error("Invalid username/token. Please check and try again.")
            except ApiError as e:
                st.sidebar.warning(str(e))
            except Exception:
                st.sidebar.warning("Could not validate right now. Try again later.")
    # Return whether credentials are present
    return bool(username and token)


@st.cache_data(show_spinner=False, ttl=3600)
def get_event_options(season: int) -> list[tuple[str, str]]:
    """Return list of (label, code) for events in a season.
    Label format: "<Event Name> <Season> [<CODE>]".
    """
    # If credentials missing, try to load cached listings file directly; else call API
    if not (os.getenv("AUTH_USERNAME") and os.getenv("AUTH_TOKEN")):
        cached = load_json_data(f"data/{season}EventListings.json")
        if not cached:
            return []
        listings = cached
    else:
        try:
            listings = request_event_listings(int(season))
        except AuthError:
            return []
        except Exception:
            return []

    options: list[tuple[str, str]] = []
    for week in [1, 2, 3, 4, 5, 6]:
        week_key = f"Week {week}"
        events = listings.get(week_key, {}).get("Events", [])
        for e in events:
            code = e.get("code") or e.get("eventCode") or ""
            if not code:
                continue
            name = e.get("name") or e.get("nameShort") or code
            label = f"{name} {season} [{code}]"
            options.append((label, code))
    # de-duplicate while preserving order
    seen = set()
    uniq: list[tuple[str, str]] = []
    for label, code in options:
        if code in seen:
            continue
        seen.add(code)
        uniq.append((label, code))
    return uniq


def render_event_analysis_tab() -> None:
    st.subheader("Analyze Event")
    col1, col2, col3 = st.columns([1, 3, 1])
    with col1:
        season = st.number_input(
            "Season",
            min_value=2010,
            max_value=2035,
            value=2024,
            step=1,
            key="analysis_season",
        )
    with col2:
        opts = get_event_options(int(season))
        selected_label = st.selectbox(
            "Event",
            options=[o[0] for o in opts] if opts else [],
            index=0 if opts else None,
            key="analysis_event_select",
            placeholder="Select an event",
        )
        manual_code = st.text_input(
            "Or enter event code",
            value="" if opts else "AZVA",
            key="analysis_event_manual",
            help="Use this if the list is empty or you know the code.",
        )
        if selected_label and opts:
            mapping = {label: code for label, code in opts}
            event_code = mapping.get(selected_label, manual_code.strip().upper())
        else:
            event_code = manual_code.strip().upper()
    with col3:
        run = st.button("Analyze", type="primary")

    if not run:
        return

    try:
        # If no credentials and no local cache for this event, guide the user
        if not (os.getenv("AUTH_USERNAME") and os.getenv("AUTH_TOKEN")):
            if not os.path.exists(data_filename(int(season), str(event_code))):
                st.error(
                    "Credentials are required to fetch this event. Enter them in the sidebar, or pre-populate the cache file under data/."
                )
                return
        with st.status(f"Fetching {season} {event_code} data...", expanded=True) as status:
            def on_progress(msg: str):
                try:
                    status.write(msg)
                except Exception:
                    pass

            event = Event(season, event_code, progress=on_progress)
            status.update(label="Done", state="complete")

        # Teams table
        team_rows = []
        for team in event.teams.values():
            team_rows.append(
                {
                    "Team": team.teamNumber,
                    "Name": team.name,
                    "Rank": team.ranking,
                    "Alliance": team.alliance.allianceNumber if team.alliance else None,
                }
            )
        st.markdown("### Teams, Rankings, Alliances")
        st.dataframe(team_rows, use_container_width=True, hide_index=True)

        # Awards table
        award_rows = []
        for award_name, recipients in event.awards.items():
            for rec in recipients:
                award_rows.append(
                    {
                        "Award": award_name,
                        "Team": getattr(rec.get("Team"), "teamNumber", None),
                        "Person": rec.get("Person"),
                    }
                )
        if award_rows:
            st.markdown("### Awards")
            st.dataframe(award_rows, use_container_width=True, hide_index=True)
        else:
            st.info("No awards recorded in this event (or not available).")

    except AuthError:
        st.error("Invalid FRC Events API credentials. Please re-enter username/token.")
    except ApiError as e:
        st.warning(str(e))
    except Exception as e:
        st.error("Failed to fetch or render event data.")
        st.exception(e)


def render_points_tab() -> None:
    st.subheader("Calculate Team Points (2025 rules)")
    c1, c2, c3, c4 = st.columns([1, 3, 1, 1])
    with c1:
        season = st.number_input(
            "Season",
            min_value=2010,
            max_value=2035,
            value=2024,
            step=1,
            key="points_season",
        )
    with c2:
        opts = get_event_options(int(season))
        selected_label = st.selectbox(
            "Event",
            options=[o[0] for o in opts] if opts else [],
            index=0 if opts else None,
            key="points_event_select",
            placeholder="Select an event",
        )
        manual_code = st.text_input(
            "Or enter event code",
            value="" if opts else "AZVA",
            key="points_event_manual",
        )
        if selected_label and opts:
            mapping = {label: code for label, code in opts}
            event_code = mapping.get(selected_label, manual_code.strip().upper())
        else:
            event_code = manual_code.strip().upper()
    with c3:
        team_number = st.number_input(
            "Team Number",
            min_value=1,
            max_value=99999,
            value=1234,
            step=1,
            key="points_team",
        )
    with c4:
        run = st.button("Compute", type="primary")

    if not run:
        return

    try:
        # If no credentials and no local cache for this event, guide the user
        if not (os.getenv("AUTH_USERNAME") and os.getenv("AUTH_TOKEN")):
            if not os.path.exists(data_filename(int(season), str(event_code))):
                st.error(
                    "Credentials are required to fetch this event. Enter them in the sidebar, or pre-populate the cache file under data/."
                )
                return
        with st.spinner("Building event and computing points..."):
            event = Event(season, event_code)
            team = event.get_team_from_number(int(team_number))

            total, playoff, alliance, quals, b1, b2, b3 = team.regional_points_2025()
            breakdown = {
                "Team Age": team.team_age_points_2025(),
                "Qualification": team.qualification_points_2025(),
                "Alliance Selection": team.alliance_selection_points_2025(),
                "Playoff Advancement": team.playoff_advancement_points_2025(),
                "Awards": team.awards_points_2025(),
            }

        st.metric("Total Event Points", total)
        st.markdown("### Breakdown")
        st.dataframe(
            [{"Category": k, "Points": v} for k, v in breakdown.items()],
            use_container_width=True,
            hide_index=True,
        )
        st.markdown("### Best 3 Match Scores")
        st.write((b1, b2, b3))
    except AuthError:
        st.error("Invalid FRC Events API credentials. Please re-enter username/token.")
    except ApiError as e:
        st.warning(str(e))
    except KeyError:
        st.error("Team not found in this event. Check the team number.")
    except Exception as e:
        st.error("Failed to compute points.")
        st.exception(e)


def render_regional_pool_tab() -> None:
    st.subheader("Regional Pool Standings")
    c1, c2, c3, c4, c5 = st.columns([1, 1, 1, 1, 1])
    with c1:
        season = st.number_input(
            "Season",
            min_value=2010,
            max_value=2035,
            value=2025,
            step=1,
            key="pool_season",
        )
    with c2:
        use_season = st.number_input(
            "Rules Season",
            min_value=2010,
            max_value=2035,
            value=2025,
            step=1,
            key="pool_rules_season",
        )
    with c3:
        week = st.number_input("Week", min_value=1, max_value=6, value=6, step=1, key="pool_week")
    with c4:
        top_n = st.number_input(
            "Top N (0=all)",
            min_value=0,
            max_value=5000,
            value=50,
            step=1,
            key="pool_top",
        )
    with c5:
        run = st.button("Build Standings", type="primary")

    if not run:
        return

    try:
        if not (os.getenv("AUTH_USERNAME") and os.getenv("AUTH_TOKEN")):
            st.error(
                "Credentials are required to build season standings unless you have cached data for all events. Enter them in the sidebar."
            )
            return
        # Pre-count events for progress bar (cheap)
        try:
            listings = request_event_listings(int(season))
            total_events = sum(len(listings.get(f"Week {w}", {}).get("Events", [])) for w in [1, 2, 3, 4, 5, 6])
        except Exception:
            total_events = 0

        if total_events <= 0:
            with st.spinner("Building season (this may take a while)..."):
                season_obj = Season(int(season), useSeason=int(use_season))
        else:
            st.info(
                f"Preparing to build {total_events} events. This can take several minutes on first run; cached data speeds it up next time."
            )
            progress = st.progress(0.0)
            status_placeholder = st.empty()
            recent_placeholder = st.empty()
            built = 0
            recent_codes: list[str] = []

            def on_event_built(_code: str):
                nonlocal built, recent_codes
                built += 1
                recent_codes.append(_code)
                try:
                    progress.progress(min(built / total_events, 1.0))
                    status_placeholder.write(
                        f"Building events: {built}/{total_events} — latest: {_code}"
                    )
                    recent = ", ".join(recent_codes[-8:])
                    recent_placeholder.caption(f"Recent: {recent}")
                except Exception:
                    pass

            season_obj = Season(int(season), useSeason=int(use_season), progress=on_event_built)
            progress.progress(1.0)

        pool = season_obj.regional_pool_2025(int(week))

        rows = []
        for rank, row in pool.items():
            rows.append(
                {
                    "Rank": rank,
                    "Team": row["team"].teamNumber,
                    "Points": row["points"][0],
                    "Qualified": row["qualified"]["isQualified"],
                    "Reason": row["qualified"]["qualifiedFor"],
                }
            )
        rows = rows[: (top_n or len(rows))]
        st.dataframe(rows, use_container_width=True, hide_index=True)

    except AuthError:
        st.error("Invalid FRC Events API credentials. Please re-enter username/token.")
    except ApiError as e:
        st.warning(str(e))
    except Exception as e:
        st.error("Failed to build regional pool standings.")
        st.exception(e)


def main() -> None:
    st.title("FRC Event Calculator Dashboard")
    has_creds = set_env_from_sidebar()

    if not has_creds:
        st.warning(
            "Enter FRC Events API credentials in the sidebar. Without them, only locally cached data can be used and event lists may be empty."
        )

    tab1, tab2, tab3 = st.tabs(["Analyze Event", "Calculate Points", "Regional Pool"])
    with tab1:
        render_event_analysis_tab()
    with tab2:
        render_points_tab()
    with tab3:
        render_regional_pool_tab()


if __name__ == "__main__":
    main()
