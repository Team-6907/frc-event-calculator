from __future__ import annotations

import os
import statistics
from typing import Any, Dict, List

import streamlit as st
import pandas as pd

from frc_calculator.models.event import Event
from frc_calculator.services.season import Season
from frc_calculator.data.frc_events import (
    request_event_listings,
    data_filename,
    AuthError,
    ApiError,
)
from frc_calculator.utils.io_utils import load_json_data
from frc_calculator.utils.event_stats import (
    calculate_event_statistics,
    calculate_radar_chart_data,
)
from frc_calculator.ui.components import (
    select_event_single,
    select_event_multi,
    ensure_event_data_available,
    make_status_progress,
    validate_int,
    epa_progress_ui,
    render_context_bar,
)
from frc_calculator.ui.charts import (
    render_radar_chart_visualization,
    render_radar_dimensions_breakdown,
    render_radar_chart_comparison,
    render_radar_dimensions_comparison,
)


st.set_page_config(
    page_title="FRC Event Calculator", layout="wide", initial_sidebar_state="collapsed"
)

# Initialize session state for event listings
if "event_listings_loaded" not in st.session_state:
    st.session_state.event_listings_loaded = False
if "last_fetch_time" not in st.session_state:
    st.session_state.last_fetch_time = None


def auto_fetch_event_listings(*, silent: bool = False) -> None:
    """Automatically fetch event listings for 2023, 2024, and 2025 seasons if credentials are available.

    If silent=True, performs fetching without UI status/toasts or reruns.
    """
    if not (os.getenv("AUTH_USERNAME") and os.getenv("AUTH_TOKEN")):
        return

    # Check if we need to fetch any event listings
    seasons_to_fetch = []
    for season in [2023, 2024, 2025]:
        cache_file = f"cache/{season}EventListings.json"
        if not os.path.exists(cache_file) or os.path.getsize(cache_file) == 0:
            seasons_to_fetch.append(season)

    if not seasons_to_fetch:
        return

    if silent:
        for season in seasons_to_fetch:
            try:
                request_event_listings(season)
            except Exception:
                continue
        try:
            get_event_options.clear()
        except Exception:
            pass
        st.session_state.event_listings_loaded = True
        st.session_state.last_fetch_time = pd.Timestamp.now()
        return

    # Show status for auto-fetching (non-silent)
    with st.status("🚀 Auto-fetching event listings...", expanded=False) as status:
        for season in seasons_to_fetch:
            try:
                status.write(f"📥 Fetching {season} event listings...")
                request_event_listings(season)
                status.write(f"✅ {season} event listings loaded successfully!")
            except AuthError:
                status.write(f"❌ Authentication failed for {season}")
                break
            except Exception as e:
                status.write(f"⚠️ Error fetching {season}: {str(e)}")
                continue

        status.update(label="✅ Event listings auto-fetch completed!", state="complete")

        # Clear the get_event_options cache to force refresh
        try:
            get_event_options.clear()
            st.toast("🔄 Event options cache refreshed!", icon="🔄")
        except Exception:
            pass

        # Update session state to trigger UI refresh
        st.session_state.event_listings_loaded = True
        st.session_state.last_fetch_time = pd.Timestamp.now()

        # Force a rerun to refresh the UI
        st.rerun()


def _render_credentials_and_cache_controls() -> None:
    """Render credentials and cache tools (for use inside Settings dialog)."""
    st.markdown("#### 🔐 FRC Events API Setup")
    st.caption(
        "Enter your API credentials to access live data. Without them, only cached data is used."
    )

    col1, col2, col3 = st.columns([2, 2, 1.6])

    with col1:
        default_user = os.getenv("AUTH_USERNAME", "")
        username = st.text_input(
            "Username",
            value=default_user,
            placeholder="FRC Events API username",
            help="Your FRC Events API username",
            key="settings_username",
        )

    with col2:
        default_token = os.getenv("AUTH_TOKEN", "")
        token = st.text_input(
            "Auth Token",
            value=default_token,
            type="password",
            placeholder="FRC Events API token",
            help="Your FRC Events API authorization token",
            key="settings_token",
        )

    with col3:
        st.markdown("<br>", unsafe_allow_html=True)
        validate_disabled = not (username and token)
        if st.button("Validate", type="primary", use_container_width=True, disabled=validate_disabled, key="settings_validate"):
            with st.spinner("Validating credentials and loading listings..."):
                try:
                    os.environ["AUTH_USERNAME"] = username
                    os.environ["AUTH_TOKEN"] = token
                    request_event_listings(2024)
                    auto_fetch_event_listings(silent=True)
                    st.success("Credentials validated. Event listings refreshed.")
                except AuthError:
                    st.error("❌ Invalid credentials. Please check and try again.")
                except Exception as e:
                    st.warning(f"⚠️ Validation failed: {str(e)}")

    st.divider()

    st.markdown("#### 🧹 Cache Management")
    c1, c2, c3 = st.columns(3)

    def _delete_file_silent(path: str) -> None:
        try:
            if os.path.exists(path):
                os.remove(path)
        except Exception:
            pass

    with c1:
        if st.button("🔄 Clear Event Listings", help="Delete cached event listings files", key="clear_event_listings"):
            try:
                # Clear get_event_options cache and delete listings files
                get_event_options.clear()
                cache_dir = "cache"
                if os.path.isdir(cache_dir):
                    for fname in os.listdir(cache_dir):
                        if fname.endswith("EventListings.json"):
                            _delete_file_silent(os.path.join(cache_dir, fname))
                st.success("Event listings cache cleared")
            except Exception as e:
                st.warning(f"Could not clear listings cache: {e}")

    with c2:
        if st.button("🗑️ Clear Current Event", help="Delete cache for the currently selected event", key="clear_current_event"):
            try:
                season = st.session_state.get("ctx_season")
                event = st.session_state.get("ctx_event")
                if season and event:
                    _delete_file_silent(data_filename(int(season), str(event)))
                    st.success(f"Cleared cache for {season} {event}")
                else:
                    st.info("No current event selected")
            except Exception as e:
                st.warning(f"Could not clear event cache: {e}")

    with c3:
        if st.button("🤖 Clear EPA Cache", help="Remove EPA data from cached event files", key="clear_epa_cache"):
            try:
                cache_dir = "cache"
                cleared = 0
                if os.path.isdir(cache_dir):
                    for fname in os.listdir(cache_dir):
                        if fname.endswith(".json") and "EventListings" not in fname:
                            fpath = os.path.join(cache_dir, fname)
                            try:
                                from frc_calculator.utils.io_utils import load_json_data, write_json_data
                                data = load_json_data(fpath)
                                if data and "EPAData" in data:
                                    data.pop("EPAData", None)
                                    write_json_data(data, fpath)
                                    cleared += 1
                            except Exception:
                                continue
                st.success(f"Cleared EPA data from {cleared} cache file(s)")
            except Exception as e:
                st.warning(f"Could not clear EPA cache: {e}")


@st.dialog("⚙️ Settings")
def _settings_dialog():
    # Widen dialog to reduce clutter on forms
    try:
        st.markdown(
            """
            <style>
            /* Increase the width of Streamlit dialog */
            div[data-testid="stDialog"] > div {width: 92vw; max-width: 1100px;}
            div[data-testid="stDialog"] section {width: 92vw; max-width: 1100px;}
            </style>
            """,
            unsafe_allow_html=True,
        )
    except Exception:
        pass
    _render_credentials_and_cache_controls()
    st.markdown("")
    st.caption("Close this dialog to return to the app.")


def render_top_status_bar() -> None:
    """Compact status + Settings entry, replaces always-on credentials section."""
    live = bool(os.getenv("AUTH_USERNAME") and os.getenv("AUTH_TOKEN"))
    col1, col2 = st.columns([5, 1])
    with col1:
        st.markdown(
            f"**API Status:** {'🟢 Live' if live else '🟡 Cache-only'}  |  "
            f"Season: {st.session_state.get('ctx_season', '—')}  "
            f"Event: {st.session_state.get('ctx_event', '—')}  "
        )
    with col2:
        if st.button("⚙️ Settings", use_container_width=True):
            _settings_dialog()


@st.cache_data(show_spinner=False, ttl=3600)
def get_event_options(season: int) -> list[tuple[str, str]]:
    """Return list of (label, code) for events in a season.
    Label format: "<Event Name> <Season> [<CODE>]".
    """
    # Ensure season is an integer
    season = int(season)

    # Add session state dependency to force cache invalidation
    _ = st.session_state.get("event_listings_loaded", False)
    _ = st.session_state.get("last_fetch_time", None)

    # Check if credentials are available (either from environment or session state)
    has_credentials = bool(os.getenv("AUTH_USERNAME") and os.getenv("AUTH_TOKEN"))

    # Debug logging
    print(
        f"get_event_options called for season {season}, has_credentials: {has_credentials}"
    )

    # If credentials missing, try to load cached listings file directly; else call API
    if not has_credentials:
        cache_file = f"cache/{season}EventListings.json"
        cached = load_json_data(cache_file)
        if not cached:
            # Debug: log when cache file is not found
            print(f"Cache file not found: {cache_file}")
            return []
        listings = cached
        print(f"Loaded {season} from cache, found {len(listings)} weeks")
    else:
        try:
            listings = request_event_listings(season)
            print(f"Loaded {season} from API, found {len(listings)} weeks")
        except AuthError:
            print(f"Auth error for {season}")
            return []
        except Exception as e:
            print(f"API error for {season}: {e}")
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

    print(f"Generated {len(options)} options for season {season}")

    # de-duplicate while preserving order
    seen = set()
    uniq: list[tuple[str, str]] = []
    for label, code in options:
        if code in seen:
            continue
        seen.add(code)
        uniq.append((label, code))

    print(f"Final {len(uniq)} unique options for season {season}")
    return uniq


def render_event_analysis_tab() -> None:
    st.markdown("### 🏆 Event Analysis")
    st.markdown("Analyze team rankings, alliances, and awards for any FRC event.")

    # Use global context bar (event scope)
    ctx = render_context_bar("analysis", "event", get_event_options, season_default=2024)
    season, event_code = ctx.get("season"), ctx.get("event")
    run = st.button("🔍 Analyze Event", type="primary")

    if not run:
        return

    if not event_code:
        st.warning("⚠️ Please enter a valid season year and event code.")
        return

    try:
        # Check for data availability
        if not ensure_event_data_available(season, event_code):
            return

        # Fetch event data with better progress UI
        with st.status(f"📥 Loading {season} {event_code}...", expanded=True) as status:
            on_progress = make_status_progress(status)
            event = Event(int(season), event_code, progress=on_progress)
            status.update(label="✅ Event data loaded successfully!", state="complete")

        # Results section with better formatting
        st.markdown("---")

        # Teams table with improved styling
        team_rows = []
        for team in event.teams.values():
            team_rows.append(
                {
                    "Team #": team.teamNumber,
                    "Team Name": team.name,
                    "Rank": team.ranking,
                    "Alliance": team.alliance.allianceNumber if team.alliance else None,
                }
            )

        st.markdown("### 🏆 Teams & Rankings")
        if team_rows:
            st.dataframe(
                team_rows,
                use_container_width=True,
                hide_index=True,
                column_config={
                    "Team #": st.column_config.NumberColumn(width="small"),
                    "Rank": st.column_config.NumberColumn(width="small"),
                    "Alliance": st.column_config.TextColumn(width="small"),
                },
            )
        else:
            st.info("No team data available for this event.")

        # Awards table with better formatting
        award_rows = []
        for award_name, recipients in event.awards.items():
            for rec in recipients:
                award_rows.append(
                    {
                        "Award": award_name,
                        "Team #": getattr(rec.get("Team"), "teamNumber", None),
                        "Recipient": rec.get("Person", None),
                    }
                )

        st.markdown("### 🏅 Awards")
        if award_rows:
            st.dataframe(
                award_rows,
                use_container_width=True,
                hide_index=True,
                column_config={"Team #": st.column_config.TextColumn(width="small")},
            )
        else:
            st.info("💡 No awards data available for this event.")

    except AuthError:
        st.error(
            "🔐 **Authentication Error**: Invalid credentials. Please check your username and token above."
        )
    except ApiError as e:
        st.warning(f"🌐 **API Error**: {str(e)}")
    except Exception as e:
        st.error("❌ **Error**: Failed to load event data.")
        with st.expander("See error details"):
            st.exception(e)


def render_points_tab() -> None:
    st.markdown("### 📊 Team Points Calculator")
    st.markdown("Calculate regional points for any team using 2025+ FRC rules.")

    # Inputs via global context bar (event scope + team)
    ctx = render_context_bar("points", "event", get_event_options, season_default=2024)
    season, event_code = ctx.get("season"), ctx.get("event")
    team_number_str = str(ctx.get("team", "")).strip()
    run = st.button("📈 Calculate Points", type="primary")

    if not run:
        return

    # Validate inputs
    team_number = validate_int(team_number_str, "team number")
    if not event_code or team_number is None:
        st.warning("⚠️ Please enter valid season, event code, and team number.")
        return

    try:
        # Check for data availability
        if not ensure_event_data_available(season, event_code):
            return

        with st.spinner(
            f"📥 Loading {season} {event_code} and calculating points for Team {team_number}..."
        ):
            event = Event(int(season), event_code)
            team = event.get_team_from_number(int(team_number))

            total, playoff, alliance, quals, b1, b2, b3 = team.regional_points_2025()
            breakdown = {
                "Team Age": team.team_age_points_2025(),
                "Qualification": team.qualification_points_2025(),
                "Alliance Selection": team.alliance_selection_points_2025(),
                "Playoff Advancement": team.playoff_advancement_points_2025(),
                "Awards": team.awards_points_2025(),
            }

        st.markdown("---")

        # Better results display
        col1, col2 = st.columns([1, 2])

        with col1:
            st.metric(
                "🏆 Total Event Points",
                total,
                help="Total regional points earned at this event",
            )

            # Team info
            st.markdown("#### Team Info")
            st.write(f"**Team:** {team.teamNumber}")
            st.write(f"**Name:** {team.name}")
            st.write(f"**Rank:** {team.ranking}")
            if team.alliance:
                st.write(f"**Alliance:** {team.alliance.allianceNumber}")

        with col2:
            st.markdown("#### 📈 Points Breakdown")
            breakdown_df = [{"Category": k, "Points": v} for k, v in breakdown.items()]
            st.dataframe(
                breakdown_df,
                use_container_width=True,
                hide_index=True,
                column_config={"Points": st.column_config.NumberColumn(width="small")},
            )

            st.markdown("#### 🎯 Best 3 Match Scores")
            scores_df = [
                {"Match": f"Best {i+1}", "Score": score}
                for i, score in enumerate([b1, b2, b3])
            ]
            st.dataframe(
                scores_df,
                use_container_width=True,
                hide_index=True,
                column_config={"Score": st.column_config.NumberColumn(width="small")},
            )

    except AuthError:
        st.error(
            "🔐 **Authentication Error**: Invalid credentials. Please check your username and token above."
        )
    except ApiError as e:
        st.warning(f"🌐 **API Error**: {str(e)}")
    except KeyError:
        st.error(
            f"❌ **Team not found**: Team {team_number} was not found in event {event_code}. Please check the team number."
        )
    except Exception as e:
        st.error("❌ **Error**: Failed to calculate points.")
        with st.expander("See error details"):
            st.exception(e)


def render_loading_season(season_int, use_season_int, pool_week):
        # Pre-count events for better progress tracking
    week_int = pool_week

    try:
        listings = request_event_listings(season_int)
        # Only count events for the requested week, not all weeks
        total_events = 0
        for week in range(1, week_int + 1):
            total_events += len(listings.get(f"Week {week}", {}).get("Events", []))
    except Exception:
        total_events = 0

    if total_events <= 0:
        with st.spinner("🔄 Building season data (this may take a while)..."):
            season_obj = Season(
                season_int, useSeason=use_season_int, max_week=week_int
            )
    else:
        st.info(
            f"📊 **Building {total_events} events through week {week_int}**\n\n"
            f"This may take several minutes on first run. Cached data will speed up future runs."
        )

        # Enhanced progress tracking
        progress_bar = st.progress(0.0)
        status_placeholder = st.empty()
        recent_placeholder = st.empty()
        built = 0
        recent_codes: list[str] = []

        def on_event_built(_code: str):
            nonlocal built, recent_codes
            built += 1
            recent_codes.append(_code)
            try:
                progress = min(built / total_events, 1.0)
                progress_bar.progress(progress)

                status_placeholder.markdown(
                    f"**Progress:** {built}/{total_events} events ({progress:.1%})\n\n"
                    f"**Currently processing:** {_code}"
                )

                recent_display = ", ".join(recent_codes[-6:])
                recent_placeholder.caption(
                    f"🔄 Recently processed: {recent_display}"
                )
            except Exception:
                pass

        season_obj = Season(
            season_int,
            useSeason=use_season_int,
            progress=on_event_built,
            max_week=week_int,
        )
        progress_bar.progress(1.0)
        status_placeholder.success("✅ All events in the season processed successfully!")
    
    return season_obj


def render_regional_pool_tab() -> None:
    st.markdown("### 🏁 Regional Pool Standings")
    st.markdown(
        "View championship qualification standings based on regional point calculations."
    )

    # Scope-aware context bar (season scope for pool)
    ctx = render_context_bar("pool", "season", get_event_options, season_default=2025)

    # Additional per-tab inputs
    col_a, col_b = st.columns([1, 1])
    with col_a:
        top_n = st.text_input(
            "Top N (0=all)",
            value="50",
            help="Show top N teams (0 for all teams)",
            key="pool_top",
        )
    with col_b:
        st.markdown("<br>", unsafe_allow_html=True)
        run = st.button("🏆 Build Standings", type="primary", use_container_width=True)

    if not run:
        return

    # Validate inputs
    season_int = validate_int(str(ctx.get("season")), "season")
    use_season_int = validate_int(str(ctx.get("pool_rules")), "rules season")
    top_n_int = validate_int(top_n, "top N")
    if season_int is None or use_season_int is None or top_n_int is None:
        return

    try:
        if not (os.getenv("AUTH_USERNAME") and os.getenv("AUTH_TOKEN")):
            st.error(
                "🔐 **Credentials required**: Building season standings requires API access to fetch all event data."
            )
            return

        week_int = int(ctx.get("pool_week"))

        season_obj = render_loading_season(season_int, use_season_int, week_int)

        # Calculate pool standings
        pool = season_obj.regional_pool_2025(week_int)

        # Format results
        rows = []
        for rank, row in pool.items():
            qualified_text = row["qualified"]["qualifiedFor"]
            if qualified_text is None:
                qualified_reason = "—"
            elif "(Week" in qualified_text:
                qualified_reason = "🚁 " + qualified_text
            elif "Week" in qualified_text:
                qualified_reason = "🌏 " + qualified_text
            elif qualified_text == "Declined":
                qualified_reason = "❌ Declined"
            else:
                qualified_reason = "⏩ Pre-qualified"
            qualified_status = "✅ Yes" if row["qualified"]["isQualified"] else "❌ No"
            rows.append(
                {
                    "Rank": rank,
                    "Team #": row["team"].teamNumber,
                    "Team Name": getattr(row["team"], "name", "—"),
                    "Points": row["points"][0],
                    "Event 1": row["firstEvent"],
                    "Event 2": row["secondEvent"],
                    "Qualified": qualified_status,
                    "Qualification Reason": qualified_reason,
                }
            )

        # Apply limit
        if top_n_int > 0:
            rows = rows[:top_n_int]

        st.markdown("---")
        st.markdown(f"### 🏆 Regional Pool Standings (Week {week_int})")

        if rows:
            st.dataframe(
                rows,
                use_container_width=True,
                hide_index=True,
                column_config={
                    "Rank": st.column_config.NumberColumn(width="small"),
                    "Team #": st.column_config.NumberColumn(width="small"),
                    "Team Name": st.column_config.TextColumn(width="medium"),
                    "Points": st.column_config.NumberColumn(width="small"),
                    "Event 1": st.column_config.NumberColumn(width="small"),
                    "Event 2": st.column_config.NumberColumn(width="small"),
                    "Qualified": st.column_config.TextColumn(width="small"),
                    "Qualification Reason": st.column_config.TextColumn(width="medium"),
                },
            )

            # Summary stats
            qualified_count = sum(1 for row in rows if "✅" in row["Qualified"])
            st.markdown(
                f"**📊 Summary:** Showing {len(rows)} teams • {qualified_count} qualified for championships"
            )
        else:
            st.info("No standings data available.")

    except AuthError:
        st.error(
            "🔐 **Authentication Error**: Invalid credentials. Please check your username and token above."
        )
    except ApiError as e:
        st.warning(f"🌐 **API Error**: {str(e)}")
    except Exception as e:
        st.error("❌ **Error**: Failed to build regional pool standings.")
        with st.expander("See error details"):
            st.exception(e)


def render_event_statistics_tab() -> None:
    """Render the Event Statistics tab with comprehensive event analysis."""
    st.markdown("### 📈 Event Statistics")
    st.markdown(
        "Comprehensive event analysis including averages, playoff scores, EPA data, and historical comparisons."
    )

    # Unified inputs
    col_left, col_right = st.columns([2, 1])
    with col_left:
        ctx = render_context_bar("stats", "event", get_event_options, season_default=2024)
        season, event_code = ctx.get("season"), ctx.get("event")
    with col_right:
        include_epa = st.checkbox(
            "Include EPA Data",
            value=True,
            help="EPA data is cached after first fetch. Uncheck to skip EPA analysis for faster results.",
            key="include_epa_stats",
        )
        run = st.button("📊 Generate Statistics", type="primary")

    if not run:
        return

    if not event_code:
        st.warning("⚠️ Please enter a valid season year and event code.")
        return

    try:
        # Check for data availability
        if not ensure_event_data_available(season, event_code):
            return

        # Load event data with improved progress indicator
        with st.status(
            f"📊 Analyzing {season} {event_code}...",
            expanded=False,
        ) as status:
            # Event loading progress (simplified)
            on_progress = make_status_progress(
                status, filter_keys=["teams", "rankings", "alliances"]
            )
            event = Event(int(season), event_code, progress=on_progress)

            # Statistics calculation progress
            epa_cb, epa_cleanup = epa_progress_ui()

            def stats_progress(msg):
                if isinstance(msg, dict) and msg.get("type") == "epa_progress":
                    epa_cb(msg)
                elif isinstance(msg, str):
                    key_steps = [
                        "Loading",
                        "Calculating average",
                        "Starting EPA",
                        "EPA data cached",
                    ]
                    if any(step in msg for step in key_steps):
                        try:
                            status.write(f"• {msg}")
                        except Exception:
                            pass

            stats = calculate_event_statistics(
                event, progress_callback=stats_progress, include_epa=include_epa
            )

            # Clean up progress elements
            epa_cleanup()

            status.update(label="✅ Event analysis complete!", state="complete")

        st.markdown("---")

        # Display statistics in organized sections
        render_average_scores_section(stats["average_scores"])
        render_playoff_scores_section(stats["playoff_scores"])
        render_ranking_details_section(stats["ranking_details"])

        if include_epa:
            render_epa_section(stats["epa_data"])
        else:
            st.markdown("### 🤖 Expected Points Added (EPA) Analysis")
            st.info(
                "💡 EPA data was not requested. Check 'Include EPA Data' to see EPA analysis."
            )

        render_alliance_structure_section(stats["alliance_structure"])
        render_multi_year_section(stats["multi_year_teams"], event_code, int(season))

    except AuthError:
        st.error(
            "🔐 **Authentication Error**: Invalid credentials. Please check your username and token above."
        )
    except ApiError as e:
        st.warning(f"🌐 **API Error**: {str(e)}")
    except Exception as e:
        st.error("❌ **Error**: Failed to generate event statistics.")
        with st.expander("See error details"):
            st.exception(e)


def render_average_scores_section(avg_scores: Dict[str, float]) -> None:
    """Render the average qualification scores section."""
    st.markdown("### 🎯 Average Qualification Match Scores")

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric(
            "🔴 Red Alliance",
            f"{avg_scores['red_avg']:.1f}",
            help="Average score for red alliance in qualification matches",
        )

    with col2:
        st.metric(
            "🔵 Blue Alliance",
            f"{avg_scores['blue_avg']:.1f}",
            help="Average score for blue alliance in qualification matches",
        )

    with col3:
        st.metric(
            "⚖️ Overall Average",
            f"{avg_scores['overall_avg']:.1f}",
            help="Combined average score across all qualification matches",
        )

    with col4:
        st.metric(
            "🏁 Total Matches",
            avg_scores["total_matches"],
            help="Number of qualification matches played",
        )


def render_playoff_scores_section(playoff_scores: List[Dict[str, Any]]) -> None:
    """Render the playoff match scores section."""
    st.markdown("### 🏆 Playoff Match Scores (Match 11+)")

    if not playoff_scores:
        st.info("💡 No playoff matches found for this event.")
        return

    # Format for display
    display_data = []
    for match in playoff_scores:
        display_data.append(
            {
                "Match": f"Match {match['match_number']}",
                "Match Type": match["match_name"],
                "🔴 Red Score": match["red_score"],
                "🔴 Red Alliance": (
                    f"Alliance {match['red_alliance']}"
                    if match["red_alliance"] != "TBD"
                    else "TBD"
                ),
                "🔵 Blue Score": match["blue_score"],
                "🔵 Blue Alliance": (
                    f"Alliance {match['blue_alliance']}"
                    if match["blue_alliance"] != "TBD"
                    else "TBD"
                ),
            }
        )

    st.dataframe(
        display_data,
        use_container_width=True,
        hide_index=True,
        column_config={
            "🔴 Red Score": st.column_config.NumberColumn(width="small"),
            "🔵 Blue Score": st.column_config.NumberColumn(width="small"),
        },
    )


def render_ranking_details_section(ranking_details: List[Dict[str, Any]]) -> None:
    """Render the ranking points details section."""
    st.markdown("### 🏅 Ranking Points Analysis (Rank 1, 4, 8)")

    display_data = []
    for rank_data in ranking_details:
        display_data.append(
            {
                "Rank": rank_data["rank"],
                "Team #": (
                    rank_data["team_number"]
                    if rank_data["team_number"] != "N/A"
                    else None
                ),
                "Team Name": (
                    rank_data["team_name"][:30] + "..."
                    if len(str(rank_data["team_name"])) > 30
                    else rank_data["team_name"]
                ),
                "Ranking Points": rank_data["ranking_points"],
                "W-L-T": f"{rank_data['wins']}-{rank_data['losses']}-{rank_data['ties']}",
            }
        )

    st.dataframe(
        display_data,
        use_container_width=True,
        hide_index=True,
        column_config={
            "Rank": st.column_config.NumberColumn(width="small"),
            "Team #": st.column_config.TextColumn(width="small"),
            "Ranking Points": st.column_config.NumberColumn(width="small"),
        },
    )


def render_epa_section(epa_data: List[Dict[str, Any]]) -> None:
    """Render the EPA data section."""
    st.markdown("### 🤖 Expected Points Added (EPA) Analysis")

    if not epa_data:
        st.info("💡 No EPA data available for this event.")
        return

    # Show top 10 EPA teams and summary stats
    col1, col2 = st.columns([2, 1])

    with col1:
        st.markdown("#### 🥇 Top EPA Teams")
        top_teams = []
        valid_epa_count = 0

        # Count all valid EPA entries first
        valid_epa_count = sum(
            1
            for team in epa_data
            if isinstance(team.get("epa"), (int, float)) and team["epa"] != 0
        )

        for i, team in enumerate(epa_data[:10]):
            top_teams.append(
                {
                    "Rank by EPA": i + 1,
                    "Team #": team["team_number"],
                    "Team Name": (
                        team["team_name"][:25] + "..."
                        if len(str(team["team_name"])) > 25
                        else team["team_name"]
                    ),
                    "EPA": team["epa"],
                    "Event Rank": team["rank"] if team["rank"] else None,
                }
            )

        st.dataframe(
            top_teams,
            use_container_width=True,
            hide_index=True,
            column_config={
                "Rank by EPA": st.column_config.NumberColumn(width="small"),
                "Team #": st.column_config.NumberColumn(width="small"),
                "EPA": st.column_config.NumberColumn(width="small"),
                "Event Rank": st.column_config.TextColumn(width="small"),
            },
        )

    with col2:
        st.markdown("#### 📊 EPA Summary")
        if valid_epa_count > 0:
            valid_epas = [
                team["epa"]
                for team in epa_data
                if isinstance(team.get("epa"), (int, float)) and team["epa"] != 0
            ]
            st.metric("📈 Highest EPA", f"{max(valid_epas):.1f}")
            st.metric("📉 Lowest EPA", f"{min(valid_epas):.1f}")
            st.metric("⚖️ Average EPA", f"{statistics.mean(valid_epas):.1f}")
        st.metric("✅ Teams with EPA", f"{valid_epa_count}/{len(epa_data)}")


def render_alliance_structure_section(
    alliance_structure: Dict[str, List[Dict[str, Any]]],
) -> None:
    """Render the alliance structure analysis section."""
    st.markdown("### 🤝 Alliance Structure Analysis")

    # Give the non-playoff teams section more horizontal room for readability
    col1, col2, col3 = st.columns([1.2, 1.2, 1.6])

    with col1:
        st.markdown("#### 👑 Alliance Captains")
        captains_data = []
        for captain in alliance_structure["captains"]:
            captains_data.append(
                {
                    "Alliance": captain["alliance_number"],
                    "Team #": captain["team_number"],
                    "Team Name": (
                        captain["team_name"][:20] + "..."
                        if len(str(captain["team_name"])) > 20
                        else captain["team_name"]
                    ),
                    "Rank": captain["rank"],
                }
            )

        if captains_data:
            st.dataframe(
                captains_data,
                use_container_width=True,
                hide_index=True,
                column_config={
                    "Alliance": st.column_config.NumberColumn(width="small"),
                    "Team #": st.column_config.NumberColumn(width="small"),
                    "Rank": st.column_config.NumberColumn(width="small"),
                },
            )
        else:
            st.info("No captain data available.")

    with col2:
        st.markdown("#### 🥈 First Picks")
        picks_data = []
        for pick in alliance_structure["first_picks"]:
            picks_data.append(
                {
                    "Alliance": pick["alliance_number"],
                    "Team #": pick["team_number"],
                    "Team Name": (
                        pick["team_name"][:20] + "..."
                        if len(str(pick["team_name"])) > 20
                        else pick["team_name"]
                    ),
                    "Rank": pick["rank"],
                }
            )

        if picks_data:
            st.dataframe(
                picks_data,
                use_container_width=True,
                hide_index=True,
                column_config={
                    "Alliance": st.column_config.NumberColumn(width="small"),
                    "Team #": st.column_config.NumberColumn(width="small"),
                    "Rank": st.column_config.NumberColumn(width="small"),
                },
            )
        else:
            st.info("No first pick data available.")

    with col3:
        non_playoff_count = len(alliance_structure["non_playoff_teams"])
        st.markdown(
            f"#### 🚫 Non-Playoff Teams &nbsp;&nbsp; "
            f"<span style='font-size:0.95rem; color:rgba(250, 250, 250, 0.7)'>Teams Not Selected</span> "
            f"<span style='font-size:1.4rem; font-weight:700'>{non_playoff_count}</span>",
            unsafe_allow_html=True,
        )

        if non_playoff_count > 0:
            # Show all non-playoff teams; scrolling will handle long lists
            non_playoff_display = []
            for team in alliance_structure["non_playoff_teams"]:
                non_playoff_display.append(
                    {
                        "Team #": team["team_number"],
                        "Rank": team["rank"] if team["rank"] else "N/A",
                    }
                )

            st.dataframe(
                non_playoff_display,
                use_container_width=True,
                hide_index=True,
                column_config={
                    "Team #": st.column_config.NumberColumn(width="medium"),
                    "Rank": st.column_config.TextColumn(width="small"),
                },
                height=min(330, len(non_playoff_display) * 35 + 40),
            )
        else:
            st.info("All teams made playoffs!")


def render_multi_year_section(
    multi_year_teams: List[Dict[str, Any]], event_code: str, current_season: int
) -> None:
    """Render the multi-year analysis section."""
    st.markdown(f"### 📅 Multi-Year Analysis for {event_code}")

    if not multi_year_teams:
        st.info(
            f"💡 No teams found that competed in {event_code} in multiple years (checked adjacent years)."
        )
        return

    st.markdown(f"#### 🔄 Teams that competed in {event_code} across multiple years")

    display_data = []
    for team in multi_year_teams:
        display_data.append(
            {
                "Team #": team["team_number"],
                "Team Name": (
                    team["team_name"][:30] + "..."
                    if len(str(team["team_name"])) > 30
                    else team["team_name"]
                ),
                "Years": team["years"],
                "Other Year": team["other_year"],
            }
        )

    st.dataframe(
        display_data,
        use_container_width=True,
        hide_index=True,
        column_config={
            "Team #": st.column_config.NumberColumn(width="small"),
            "Other Year": st.column_config.NumberColumn(width="small"),
        },
    )

    st.metric("🔄 Returning Teams", len(multi_year_teams))



def render_loading_radar_data(all_events, include_epa):

    all_radar_data = {}
    events = {}

    total_events = len(all_events)

    st.info(
        f"📊 **Loading {total_events} events for radar chart comparison**\n\n"
        f"This may take several minutes on first run. Cached data will speed up future runs."
    )

    # Enhanced progress tracking
    progress_bar = st.progress(0.0)
    status_placeholder = st.empty()
    recent_placeholder = st.empty()
    built = 0
    recent_codes: list[str] = []

    def on_event_built(_code: str):
        nonlocal built, recent_codes
        built += 1
        recent_codes.append(_code)
        try:
            progress = min(built / total_events, 1.0)
            progress_bar.progress(progress)

            status_placeholder.markdown(
                f"**Progress:** {built}/{total_events} events ({progress:.1%})\n\n"
                f"**Currently processing:** {_code}"
            )

            recent_display = ", ".join(recent_codes[-6:])
            recent_placeholder.caption(
                f"🔄 Recently processed: {recent_display}"
            )
        except Exception:
            pass

    for mEvent in all_events:

        events[mEvent.eventCode] = mEvent

        # Radar chart calculation progress
        epa_cb, epa_cleanup = epa_progress_ui()

        def radar_progress(msg):
            if isinstance(msg, dict) and msg.get("type") == "epa_progress":
                # Reuse EPA progress elements
                # Add event code to text via status lines (optional)
                epa_cb(msg)

        radar_data = calculate_radar_chart_data(
            mEvent, progress_callback=radar_progress, include_epa=include_epa
        )
        all_radar_data[mEvent.eventCode] = radar_data

        # Clean up progress elements
        epa_cleanup()

        on_event_built(mEvent.eventCode)

    if include_epa:
        keys = ["Overall", "RP", "TANK", "HOME", "REIGN", "TITLE", "CHAMP"]
    else:
        keys = ["Overall", "RP", "REIGN", "TITLE", "CHAMP"]

    radar_01_data = {}
    max_values = {}
    min_values = {}
    for key in keys:
        max_value = -6907
        min_value = 6907
        for _, radar_data in all_radar_data.items():
            if radar_data[key] != 6907:
                max_value = max(max_value, radar_data[key])
                min_value = min(min_value, radar_data[key])
        max_values[key] = max_value
        min_values[key] = min_value

    for event_code, radar_data in all_radar_data.items():
        radar_01_data[event_code] = {}
        for key in keys:
            if radar_data[key] != 6907:
                radar_01_data[event_code][key] = (max_values[key] - radar_data[key]) / (max_values[key] - min_values[key])
            else:
                radar_01_data[event_code][key] = 0

    progress_bar.progress(1.0)
    status_placeholder.success("✅ All events in the season processed successfully!")

    return all_radar_data, radar_01_data


def render_event_radar_tab() -> None:
    """Render the Event Radar Chart tab with 8-dimensional analysis."""
    st.markdown("### 📡 Event Radar Comparison Analysis")
    st.markdown(
        "Compare up to 5 events using 8-dimensional radar chart analysis. Select multiple events to see side-by-side performance comparisons across all metrics."
    )

    # Unified inputs: season locked at 2025, multi-event select
    col_left, col_right = st.columns([2, 1])
    with col_left:
        season, event_codes = select_event_multi(2025, "radar", get_event_options)
    with col_right:
        include_epa = st.checkbox(
            "Include EPA Data",
            value=True,
            help="EPA data required for TANK and HOME dimensions. Uncheck to exclude these dimensions.",
            key="include_epa_radar",
        )
        if st.button("🔄 Clear Event Cache", key="clear_radar_cache"):
            get_event_options.clear()
            st.toast("✓ Event cache cleared for radar tab", icon="🔄")
        run = st.button("📡 Generate Radar Comparison", type="primary")

    if not run:
        return

    if not event_codes:
        st.warning("⚠️ Please enter a valid season year and at least one event code.")
        return

    if len(event_codes) == 0:
        st.warning("⚠️ Please select at least one event to analyze.")
        return

    try:
        # Check for data availability for all events
        if not (os.getenv("AUTH_USERNAME") and os.getenv("AUTH_TOKEN")):
            missing_events = [
                code
                for code in event_codes
                if not os.path.exists(data_filename(int(season), str(code)))
            ]
            if missing_events:
                st.error(
                    f"🔐 **Credentials required**: Set up your API credentials above to fetch data for: {', '.join(missing_events)}"
                )
                return
        
        season_obj = render_loading_season(season, season, 6)

        all_events = []
        for weekNumber in range(1, 7):
            for mEvent in season_obj.events[weekNumber]:
                all_events.append(mEvent)

        all_radar_data, radar_01_data = render_loading_radar_data(all_events, include_epa)

        final_data = {}
        for i, event_code in enumerate(event_codes):
            final_data[event_code] = radar_01_data[event_code]

        st.markdown("---")

        # Display radar chart comparison and analysis
        render_radar_chart_comparison(final_data, int(season))
        render_radar_dimensions_comparison(final_data, all_radar_data)

    except AuthError:
        st.error(
            "🔐 **Authentication Error**: Invalid credentials. Please check your username and token above."
        )
    except ApiError as e:
        st.warning(f"🌐 **API Error**: {str(e)}")
    except Exception as e:
        st.error("❌ **Error**: Failed to generate radar chart analysis.")
        with st.expander("See error details"):
            st.exception(e)




def main() -> None:
    st.title("🏁 FRC Event Calculator")
    st.markdown(
        "**The complete toolkit for FRC event analysis and championship qualification tracking**"
    )

    # Compact status + settings dialog entry
    render_top_status_bar()

    # Main application tabs
    tab1, tab2, tab3, tab4, tab5 = st.tabs(
        [
            "🏆 Analyze Event",
            "📊 Calculate Points",
            "🏁 Regional Pool",
            "📈 Event Statistics",
            "📡 Event Radar",
        ]
    )

    with tab1:
        render_event_analysis_tab()
    with tab2:
        render_points_tab()
    with tab3:
        render_regional_pool_tab()
    with tab4:
        render_event_statistics_tab()
    with tab5:
        render_event_radar_tab()


if __name__ == "__main__":
    main()
