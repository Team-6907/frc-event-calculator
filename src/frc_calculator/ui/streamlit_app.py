from __future__ import annotations

import os
import traceback
import statistics
from typing import Any, Dict, List

import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
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


st.set_page_config(
    page_title="FRC Event Calculator", layout="wide", initial_sidebar_state="collapsed"
)


def render_credentials_setup() -> bool:
    """Render credentials setup in main area with better UX"""
    st.markdown("### 🔐 FRC Events API Setup")
    st.markdown(
        "Enter your FRC Events API credentials to access live data. Without them, only cached data will be available."
    )

    col1, col2, col3 = st.columns([2, 2, 1])

    with col1:
        default_user = os.getenv("AUTH_USERNAME", "")
        username = st.text_input(
            "Username",
            value=default_user,
            placeholder="Enter your FRC Events API username",
            help="Your FRC Events API username",
        )

    with col2:
        default_token = os.getenv("AUTH_TOKEN", "")
        token = st.text_input(
            "Auth Token",
            value=default_token,
            type="password",
            placeholder="Enter your auth token",
            help="Your FRC Events API authorization token",
        )

    with col3:
        st.markdown("<br>", unsafe_allow_html=True)  # Add spacing
        if username and token:
            if st.button("✓ Validate", type="primary", use_container_width=True):
                with st.spinner("Validating credentials..."):
                    try:
                        request_event_listings(2024)
                        st.success("✓ Credentials validated successfully!")
                        return True
                    except AuthError:
                        st.error("❌ Invalid credentials. Please check and try again.")
                        return False
                    except Exception as e:
                        st.warning(f"⚠️ Validation failed: {str(e)}")
                        return False
        else:
            st.button("✓ Validate", disabled=True, use_container_width=True)

    # Set environment variables
    os.environ["AUTH_USERNAME"] = username
    os.environ["AUTH_TOKEN"] = token

    # Additional actions
    col1, col2 = st.columns(2)
    with col1:
        if st.button("🔄 Clear Event Cache", help="Clear cached event listings"):
            try:
                get_event_options.clear()
                st.toast("✓ Event listings cache cleared", icon="🔄")
            except Exception:
                pass

    with col2:
        if st.button("🤖 Clear EPA Cache", help="Clear cached EPA data"):
            st.toast(
                "💡 EPA data is cached in cache/{season}-{event}.json files", icon="🤖"
            )

    st.markdown("---")
    return bool(username and token)


@st.cache_data(show_spinner=False, ttl=3600)
def get_event_options(season: int) -> list[tuple[str, str]]:
    """Return list of (label, code) for events in a season.
    Label format: "<Event Name> <Season> [<CODE>]".
    """
    # Ensure season is an integer
    season = int(season)

    # If credentials missing, try to load cached listings file directly; else call API
    if not (os.getenv("AUTH_USERNAME") and os.getenv("AUTH_TOKEN")):
        cache_file = f"cache/{season}EventListings.json"
        cached = load_json_data(cache_file)
        if not cached:
            # Debug: log when cache file is not found
            print(f"Cache file not found: {cache_file}")
            return []
        listings = cached
    else:
        try:
            listings = request_event_listings(season)
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
    st.markdown("### 🏆 Event Analysis")
    st.markdown("Analyze team rankings, alliances, and awards for any FRC event.")

    # Better form layout
    col1, col2, col3 = st.columns([1, 2, 1])

    with col1:
        season = st.text_input(
            "Season",
            value="2024",
            help="Enter the competition season year",
            key="analysis_season",
        )

    with col2:
        # Smart event selection
        opts = get_event_options(int(season) if season.isdigit() else 2024)

        if opts:
            selected_label = st.selectbox(
                "Select Event",
                options=[o[0] for o in opts],
                index=0,
                key="analysis_event_select",
                help="Choose from available events",
            )
            mapping = {label: code for label, code in opts}
            event_code = mapping.get(selected_label, "")

            # Show manual override option
            if st.checkbox("Enter custom event code", key="manual_override_analysis"):
                event_code = (
                    st.text_input(
                        "Event Code",
                        value=event_code,
                        placeholder="e.g., AZVA, CAFR, CTHAR",
                        key="analysis_event_manual",
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
                    key="analysis_event_manual_fallback",
                    help="Enter the 4-5 character event code",
                )
                .strip()
                .upper()
            )

    with col3:
        st.markdown("<br><br>", unsafe_allow_html=True)  # Add spacing
        run = st.button("🔍 Analyze Event", type="primary", use_container_width=True)

    if not run:
        return

    if not season.isdigit() or not event_code:
        st.warning("⚠️ Please enter a valid season year and event code.")
        return

    try:
        # Check for data availability
        if not (os.getenv("AUTH_USERNAME") and os.getenv("AUTH_TOKEN")):
            if not os.path.exists(data_filename(int(season), str(event_code))):
                st.error(
                    "🔐 **Credentials required**: Set up your API credentials above to fetch this event data."
                )
                return

        # Fetch event data with better progress UI
        with st.status(f"📥 Loading {season} {event_code}...", expanded=True) as status:

            def on_progress(msg: str):
                try:
                    status.write(f"• {msg}")
                except Exception:
                    pass

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

    # Improved form layout
    col1, col2, col3, col4 = st.columns([1, 2, 1, 1])

    with col1:
        season = st.text_input(
            "Season",
            value="2024",
            help="Competition season year",
            key="points_season",
        )

    with col2:
        # Smart event selection (similar to analysis tab)
        opts = get_event_options(int(season) if season.isdigit() else 2024)

        if opts:
            selected_label = st.selectbox(
                "Select Event",
                options=[o[0] for o in opts],
                index=0,
                key="points_event_select",
                help="Choose from available events",
            )
            mapping = {label: code for label, code in opts}
            event_code = mapping.get(selected_label, "")

            if st.checkbox("Enter custom event code", key="manual_override_points"):
                event_code = (
                    st.text_input(
                        "Event Code",
                        value=event_code,
                        placeholder="e.g., AZVA, CAFR, CTHAR",
                        key="points_event_manual",
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
                    key="points_event_manual_fallback",
                    help="Enter the 4-5 character event code",
                )
                .strip()
                .upper()
            )

    with col3:
        team_number = st.text_input(
            "Team Number",
            value="1234",
            placeholder="e.g., 254",
            help="FRC team number",
            key="points_team",
        )

    with col4:
        st.markdown("<br><br>", unsafe_allow_html=True)
        run = st.button("📈 Calculate Points", type="primary", use_container_width=True)

    if not run:
        return

    # Validate inputs
    if not season.isdigit() or not event_code or not team_number.isdigit():
        st.warning("⚠️ Please enter valid season, event code, and team number.")
        return

    try:
        # Check for data availability
        if not (os.getenv("AUTH_USERNAME") and os.getenv("AUTH_TOKEN")):
            if not os.path.exists(data_filename(int(season), str(event_code))):
                st.error(
                    "🔐 **Credentials required**: Set up your API credentials above to fetch this event data."
                )
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


def render_regional_pool_tab() -> None:
    st.markdown("### 🏁 Regional Pool Standings")
    st.markdown(
        "View championship qualification standings based on regional point calculations."
    )

    # Better form layout
    col1, col2, col3, col4, col5 = st.columns([1, 1, 1, 1, 1])

    with col1:
        season = st.text_input(
            "Season",
            value="2025",
            help="Competition season year",
            key="pool_season",
        )

    with col2:
        use_season = st.text_input(
            "Rules Season",
            value="2025",
            help="Which year's rules to use for calculations",
            key="pool_rules_season",
        )

    with col3:
        week = st.selectbox(
            "Week",
            options=[1, 2, 3, 4, 5, 6],
            index=5,  # Default to week 6
            help="Calculate standings through this week",
            key="pool_week",
        )

    with col4:
        top_n = st.text_input(
            "Top N (0=all)",
            value="50",
            help="Show top N teams (0 for all teams)",
            key="pool_top",
        )

    with col5:
        st.markdown("<br>", unsafe_allow_html=True)
        run = st.button("🏆 Build Standings", type="primary", use_container_width=True)

    if not run:
        return

    # Validate inputs
    if not season.isdigit() or not use_season.isdigit() or not top_n.isdigit():
        st.warning(
            "⚠️ Please enter valid numeric values for season, rules season, and top N."
        )
        return

    try:
        if not (os.getenv("AUTH_USERNAME") and os.getenv("AUTH_TOKEN")):
            st.error(
                "🔐 **Credentials required**: Building season standings requires API access to fetch all event data."
            )
            return

        # Pre-count events for better progress tracking
        season_int = int(season)
        use_season_int = int(use_season)
        week_int = int(week)
        top_n_int = int(top_n) if top_n != "0" else 0

        try:
            listings = request_event_listings(season_int)
            total_events = sum(
                len(listings.get(f"Week {w}", {}).get("Events", []))
                for w in range(1, week_int + 1)
            )
        except Exception:
            total_events = 0

        if total_events <= 0:
            with st.spinner("🔄 Building season data (this may take a while)..."):
                season_obj = Season(season_int, useSeason=use_season_int)
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
                season_int, useSeason=use_season_int, progress=on_event_built
            )
            progress_bar.progress(1.0)
            status_placeholder.success("✅ All events processed successfully!")

        # Calculate pool standings
        pool = season_obj.regional_pool_2025(week_int)

        # Format results
        rows = []
        for rank, row in pool.items():
            qualified_status = "✅ Yes" if row["qualified"]["isQualified"] else "❌ No"
            rows.append(
                {
                    "Rank": rank,
                    "Team #": row["team"].teamNumber,
                    "Team Name": getattr(row["team"], "name", "—"),
                    "Points": row["points"][0],
                    "Qualified": qualified_status,
                    "Qualification Reason": row["qualified"]["qualifiedFor"] or "—",
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
                    "Points": st.column_config.NumberColumn(width="medium"),
                    "Qualified": st.column_config.TextColumn(width="small"),
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

    # Form layout following existing patterns
    col1, col2, col3 = st.columns([1, 2, 1])

    with col1:
        season = st.text_input(
            "Season",
            value="2024",
            help="Enter the competition season year",
            key="stats_season",
        )

    with col2:
        # Smart event selection (same pattern as other tabs)
        opts = get_event_options(int(season) if season.isdigit() else 2024)

        if opts:
            selected_label = st.selectbox(
                "Select Event",
                options=[o[0] for o in opts],
                index=0,
                key="stats_event_select",
                help="Choose from available events",
            )
            mapping = {label: code for label, code in opts}
            event_code = mapping.get(selected_label, "")

            # Manual override option
            if st.checkbox("Enter custom event code", key="manual_override_stats"):
                event_code = (
                    st.text_input(
                        "Event Code",
                        value=event_code,
                        placeholder="e.g., AZVA, CAFR, CTHAR",
                        key="stats_event_manual",
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
                    key="stats_event_manual_fallback",
                    help="Enter the 4-5 character event code",
                )
                .strip()
                .upper()
            )

    with col3:
        st.markdown("<br>", unsafe_allow_html=True)
        include_epa = st.checkbox(
            "Include EPA Data",
            value=True,
            help="EPA data is cached after first fetch. Uncheck to skip EPA analysis for faster results.",
            key="include_epa_stats",
        )
        run = st.button(
            "📊 Generate Statistics", type="primary", use_container_width=True
        )

    if not run:
        return

    if not season.isdigit() or not event_code:
        st.warning("⚠️ Please enter a valid season year and event code.")
        return

    try:
        # Check for data availability
        if not (os.getenv("AUTH_USERNAME") and os.getenv("AUTH_TOKEN")):
            if not os.path.exists(data_filename(int(season), str(event_code))):
                st.error(
                    "🔐 **Credentials required**: Set up your API credentials above to fetch this event data."
                )
                return

        # Load event data with improved progress indicator
        with st.status(
            f"📊 Analyzing {season} {event_code}...",
            expanded=False,
        ) as status:
            # Event loading progress (simplified)
            def on_progress(msg: str):
                try:
                    # Only show key milestones, not every detail
                    if "teams" in msg or "rankings" in msg or "alliances" in msg:
                        status.write(f"• Loading {msg}")
                except Exception:
                    pass

            event = Event(int(season), event_code, progress=on_progress)

            # Statistics calculation progress with better UX
            progress_bar = st.progress(0.0)
            progress_text = st.empty()
            epa_container = st.empty()

            def stats_progress(msg):
                try:
                    if isinstance(msg, dict) and msg.get("type") == "epa_progress":
                        # Handle EPA progress with progress bar
                        current = msg["current"]
                        total = msg["total"]
                        team = msg["team"]
                        eta = msg.get("eta", "")

                        progress = current / total
                        progress_bar.progress(progress)

                        # Clean progress display
                        percent = int(progress * 100)
                        progress_text.text(
                            f"🤖 Fetching EPA data: {percent}% ({current}/{total} teams){eta}"
                        )

                        # Show current team being processed (less frequently for performance)
                        if current % 3 == 0 or current <= 3:  # Update every 3rd team
                            epa_container.caption(f"Processing Team {team}...")
                    else:
                        # Handle regular text progress - only show key milestones
                        if isinstance(msg, str):
                            # Only show important progress steps, filter out verbose ones
                            key_steps = [
                                "Loading",
                                "Calculating average",
                                "Starting EPA",
                                "EPA data cached",
                            ]
                            if any(step in msg for step in key_steps):
                                status.write(f"• {msg}")
                except Exception:
                    pass

            stats = calculate_event_statistics(
                event, progress_callback=stats_progress, include_epa=include_epa
            )

            # Clean up progress elements
            progress_bar.empty()
            progress_text.empty()
            epa_container.empty()

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


def render_event_radar_tab() -> None:
    """Render the Event Radar Chart tab with 8-dimensional analysis."""
    st.markdown("### 📡 Event Radar Comparison Analysis")
    st.markdown(
        "Compare up to 5 events using 8-dimensional radar chart analysis. Select multiple events to see side-by-side performance comparisons across all metrics."
    )

    # Form layout following existing patterns
    col1, col2, col3 = st.columns([1, 2, 1])

    with col1:
        season = st.text_input(
            "Season",
            value="2025",
            help="Season locked at 2025",
            key="radar_season",
            disabled=True,
        )

    with col2:
        # Debug: Show season and event options info
        st.markdown(f"**Season:** {season} (Type: {type(season)})")

        # Smart event selection for multiple events
        opts = get_event_options(int(season) if season.isdigit() else 2024)

        # Debug: Show options count
        st.markdown(f"**Events found:** {len(opts) if opts else 0}")

        if opts:
            selected_labels = st.multiselect(
                "Select Events (up to 5)",
                options=[o[0] for o in opts],
                default=[opts[0][0]] if opts else [],
                key="radar_event_select",
                help="Choose up to 5 events to compare",
                max_selections=5,
            )
            mapping = {label: code for label, code in opts}
            event_codes = [mapping.get(label, "") for label in selected_labels]

            # Manual override option
            if st.checkbox("Enter custom event codes", key="manual_override_radar"):
                custom_codes = st.text_area(
                    "Event Codes (one per line)",
                    value="\n".join(event_codes),
                    placeholder="AZVA\nCAFR\nCTHAR",
                    key="radar_event_manual",
                    help="Enter event codes, one per line (max 5)",
                    height=100,
                )
                event_codes = [
                    code.strip().upper()
                    for code in custom_codes.split("\n")
                    if code.strip()
                ]
                event_codes = event_codes[:5]  # Limit to 5 events
        else:
            st.info(
                "💡 No events loaded. Enter credentials above or provide event codes."
            )
            custom_codes = st.text_area(
                "Event Codes (one per line)",
                value="AZVA",
                placeholder="AZVA\nCAFR\nCTHAR",
                key="radar_event_manual_fallback",
                help="Enter event codes, one per line (max 5)",
                height=100,
            )
            event_codes = [
                code.strip().upper()
                for code in custom_codes.split("\n")
                if code.strip()
            ]
            event_codes = event_codes[:5]  # Limit to 5 events

    with col3:
        st.markdown("<br>", unsafe_allow_html=True)
        include_epa = st.checkbox(
            "Include EPA Data",
            value=True,
            help="EPA data required for TANK and HOME dimensions. Uncheck to exclude these dimensions.",
            key="include_epa_radar",
        )

        # Debug: Add cache clearing button for radar tab
        if st.button("🔄 Clear Event Cache", key="clear_radar_cache"):
            get_event_options.clear()
            st.toast("✓ Event cache cleared for radar tab", icon="🔄")

        run = st.button(
            "📡 Generate Radar Comparison", type="primary", use_container_width=True
        )

    if not run:
        return

    if not season.isdigit() or not event_codes:
        st.warning("⚠️ Please enter a valid season year and at least one event code.")
        return

    if len(event_codes) == 0:
        st.warning("⚠️ Please select at least one event to analyze.")
        return

    try:
        # Check for data availability for all events
        if not (os.getenv("AUTH_USERNAME") and os.getenv("AUTH_TOKEN")):
            missing_events = []
            for event_code in event_codes:
                if not os.path.exists(data_filename(int(season), str(event_code))):
                    missing_events.append(event_code)

            if missing_events:
                st.error(
                    f"🔐 **Credentials required**: Set up your API credentials above to fetch data for: {', '.join(missing_events)}"
                )
                return

        # Load event data and calculate radar charts for all events
        all_radar_data = {}
        events = {}

        with st.status(
            f"📡 Analyzing {len(event_codes)} events for radar chart comparison...",
            expanded=False,
        ) as status:
            for i, event_code in enumerate(event_codes):
                status.write(f"• Loading {event_code}...")

                # Event loading progress
                def on_progress(msg: str):
                    try:
                        # Only show key milestones, not every detail
                        if "teams" in msg or "rankings" in msg or "alliances" in msg:
                            status.write(f"• {event_code}: Loading {msg}")
                    except Exception:
                        pass

                event = Event(int(season), event_code, progress=on_progress)
                events[event_code] = event

                # Radar chart calculation progress
                progress_bar = st.progress(0.0)
                progress_text = st.empty()
                epa_container = st.empty()

                def radar_progress(msg):
                    try:
                        if isinstance(msg, dict) and msg.get("type") == "epa_progress":
                            # Handle EPA progress with progress bar
                            current = msg["current"]
                            total = msg["total"]
                            eta = msg.get("eta", "")

                            progress = current / total
                            progress_bar.progress(progress)

                            # Clean progress display
                            percent = int(progress * 100)
                            progress_text.text(
                                f"🤖 {event_code}: Fetching EPA data: {percent}% ({current}/{total} teams){eta}"
                            )

                            # Show current team being processed
                            if current % 3 == 0 or current <= 3:
                                epa_container.caption(
                                    f"{event_code}: Processing Team {msg['team']}..."
                                )
                        else:
                            # Handle regular text progress - only show key milestones
                            if isinstance(msg, str):
                                key_steps = [
                                    "Calculating Overall",
                                    "Calculating RP",
                                    "Calculating TANK",
                                    "Calculating REIGN",
                                    "Calculating Title",
                                    "Calculating CHAMP",
                                    "Fetching historical data",
                                ]
                                if any(step in msg for step in key_steps):
                                    status.write(f"• {event_code}: {msg}")
                    except Exception:
                        pass

                radar_data = calculate_radar_chart_data(
                    event, progress_callback=radar_progress, include_epa=include_epa
                )
                all_radar_data[event_code] = radar_data

                # Clean up progress elements
                progress_bar.empty()
                progress_text.empty()
                epa_container.empty()

            status.update(
                label="✅ All events analyzed successfully!", state="complete"
            )

        st.markdown("---")

        # Display radar chart comparison and analysis
        render_radar_chart_comparison(all_radar_data, int(season))
        render_radar_dimensions_comparison(all_radar_data)

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


def render_radar_chart_visualization(
    radar_data: Dict[str, float], event_code: str, season: int
) -> None:
    """Render the radar chart visualization."""
    st.markdown(f"### 📡 {event_code} {season} - 8-Dimensional Radar Analysis")

    # Prepare data for radar chart
    dimensions = list(radar_data.keys())
    values = list(radar_data.values())

    # Create radar chart using plotly
    fig = go.Figure()

    fig.add_trace(
        go.Scatterpolar(
            r=values,
            theta=dimensions,
            fill="toself",
            name=f"{event_code} {season}",
            line=dict(color="rgb(0, 114, 178)", width=3),  # High contrast blue
            fillcolor="rgba(0, 114, 178, 0.2)",  # Semi-transparent blue
        )
    )

    # Determine max value for proper scaling
    max_value = max(values) if values else 20
    scale_max = max(20, max_value * 1.2)  # At least 20, or 120% of max value

    fig.update_layout(
        polar=dict(
            radialaxis=dict(
                visible=True,
                range=[0, scale_max],
                gridcolor="rgba(255, 255, 255, 0.6)",  # Higher contrast white grid
                tickfont=dict(size=10, color="white"),
                linecolor="rgba(255, 255, 255, 0.8)",  # High contrast axis lines
            ),
            angularaxis=dict(
                tickfont=dict(size=12, color="white"),
                linecolor="rgba(255, 255, 255, 0.8)",  # High contrast axis lines
            ),
            bgcolor="rgba(0,0,0,0)",
        ),
        showlegend=True,
        title=dict(
            text=f"Event Performance Radar - {event_code} {season}",
            x=0.5,
            font=dict(size=16),
        ),
        font=dict(color="white"),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        height=500,
    )

    # Display the chart
    st.plotly_chart(fig, use_container_width=True)

    # Add interpretation guide
    with st.expander("📖 Radar Chart Interpretation Guide"):
        st.markdown(
            """
        **Dimension Explanations:**

        - **Overall**: Event competitiveness (20 - qual avg / 10) - *higher = weaker region*
        - **RP**: Ranking point difficulty (20-(RP-3)*10) - *RP=3.0→20pts (weak), RP=4.0→10pts (medium), RP=5.0→0pts (strong)*
        - **TANK**: Non-playoff teams' strength (20 - EPA median / 6) - *higher = weaker non-playoff teams*
        - **HOME**: Returning teams' strength (20 - EPA median / 6) - *higher = weaker returning teams*
        - **REIGN**: Veteran team presence (20 - count * 2.5) - *higher = fewer veteran teams (weaker region)*
        - **TITLE**: Playoff competitiveness (20 - playoff avg / 10) - *higher = weaker playoff performance*
        - **CHAMP**: Finals peak performance (20 - highest score / 25) - *higher = weaker finals performance*

        **Reading the Chart:**
        - **Larger area = weaker overall region** (higher scores across dimensions)
        - **Smaller area = stronger overall region** (lower scores across dimensions)
        - **Higher values = weaker performance** in that dimension
        - **Lower values = stronger performance** in that dimension
        """
        )


def render_radar_dimensions_breakdown(radar_data: Dict[str, float]) -> None:
    """Render detailed breakdown of radar dimensions."""
    st.markdown("### 📊 Dimensional Breakdown")

    # Create two columns for metrics display
    col1, col2 = st.columns(2)

    with col1:
        st.markdown("#### 🏆 Competition Metrics")
        st.metric(
            "Overall",
            f"{radar_data.get('Overall', 0):.2f}",
            help="Event competitiveness - higher = weaker region",
        )
        st.metric(
            "RP",
            f"{radar_data.get('RP', 0):.2f}",
            help="Ranking point difficulty - RP=3.0→20pts (weak), RP=4.0→10pts (medium), RP=5.0→0pts (strong)",
        )
        st.metric(
            "TITLE",
            f"{radar_data.get('TITLE', 0):.2f}",
            help="Playoff competitiveness - higher = weaker playoff performance",
        )
        st.metric(
            "CHAMP",
            f"{radar_data.get('CHAMP', 0):.2f}",
            help="Finals performance - higher = weaker finals",
        )

    with col2:
        st.markdown("#### 🤖 Team Strength Metrics")
        st.metric(
            "TANK",
            f"{radar_data.get('TANK', 0):.2f}",
            help="Strength of non-playoff teams - higher = weaker teams",
        )
        st.metric(
            "HOME",
            f"{radar_data.get('HOME', 0):.2f}",
            help="Strength of returning teams - higher = weaker teams",
        )
        st.metric(
            "REIGN",
            f"{radar_data.get('REIGN', 0):.2f}",
            help="Veteran team presence - higher = fewer veteran teams (weaker region)",
        )
        st.markdown("---")

    # Summary analysis
    st.markdown("#### 📈 Event Profile Summary")

    # Calculate overall score and provide interpretation
    total_score = sum(v for v in radar_data.values() if isinstance(v, (int, float)))
    avg_score = total_score / len(radar_data) if radar_data else 0

    col1, col2 = st.columns(2)
    with col1:
        st.metric("Total Score", f"{total_score:.1f}")
    with col2:
        st.metric("Average Score", f"{avg_score:.2f}")


def render_radar_chart_comparison(
    all_radar_data: Dict[str, Dict[str, float]], season: int
) -> None:
    """Render the radar chart comparison visualization for multiple events."""
    st.markdown(f"### 📡 Event Radar Comparison - {season} Season")

    # Prepare data for radar chart comparison
    dimensions = (
        list(next(iter(all_radar_data.values())).keys()) if all_radar_data else []
    )

    # Create radar chart using plotly with multiple traces
    fig = go.Figure()

    # Colorblind-friendly high contrast palette for multiple events
    colors = [
        "rgb(0, 114, 178)",  # High contrast blue
        "rgb(213, 94, 0)",  # High contrast orange
        "rgb(0, 158, 115)",  # High contrast teal
        "rgb(204, 121, 167)",  # High contrast magenta
        "rgb(230, 159, 0)",  # High contrast yellow
    ]

    for i, (event_code, radar_data) in enumerate(all_radar_data.items()):
        values = list(radar_data.values())
        color = colors[i % len(colors)]

        fig.add_trace(
            go.Scatterpolar(
                r=values,
                theta=dimensions,
                fill="toself",
                name=f"{event_code} {season}",
                line=dict(
                    color=color, width=3
                ),  # Increased line width for better visibility
                fillcolor=color.replace("rgb", "rgba").replace(
                    ")", ", 0.2)"
                ),  # Reduced opacity for better contrast
                opacity=0.8,  # Increased overall opacity for better visibility
            )
        )

    # Determine max value for proper scaling
    all_values = [
        val
        for data in all_radar_data.values()
        for val in data.values()
        if isinstance(val, (int, float))
    ]
    max_value = max(all_values) if all_values else 20
    scale_max = max(20, max_value * 1.2)  # At least 20, or 120% of max value

    fig.update_layout(
        polar=dict(
            radialaxis=dict(
                visible=True,
                range=[0, scale_max],
                gridcolor="rgba(255, 255, 255, 0.6)",  # Higher contrast white grid
                tickfont=dict(size=10, color="white"),
                linecolor="rgba(255, 255, 255, 0.8)",  # High contrast axis lines
            ),
            angularaxis=dict(
                tickfont=dict(size=12, color="white"),
                linecolor="rgba(255, 255, 255, 0.8)",  # High contrast axis lines
            ),
            bgcolor="rgba(0,0,0,0)",
        ),
        showlegend=True,
        title=dict(
            text=f"Event Performance Radar Comparison - {season} Season",
            x=0.5,
            font=dict(size=16),
        ),
        font=dict(color="white"),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        height=500,
    )

    # Display the chart
    st.plotly_chart(fig, use_container_width=True)

    # Add interpretation guide
    with st.expander("📖 Radar Chart Comparison Guide"):
        st.markdown(
            """
        **Dimension Explanations:**

        - **Overall**: Event competitiveness (20 - qual avg / 10) - *higher = weaker region*
        - **RP**: Ranking point difficulty (20-(RP-3)*10) - *RP=3.0→20pts (weak), RP=4.0→10pts (medium), RP=5.0→0pts (strong)*
        - **TANK**: Non-playoff teams' strength (20 - EPA median / 6) - *higher = weaker non-playoff teams*
        - **HOME**: Returning teams' strength (20 - EPA median / 6) - *higher = weaker returning teams*
        - **REIGN**: Veteran team presence (20 - count * 2.5) - *higher = fewer veteran teams (weaker region)*
        - **TITLE**: Playoff competitiveness (20 - playoff avg / 10) - *higher = weaker playoff performance*
        - **CHAMP**: Finals peak performance (20 - highest score / 25) - *higher = weaker finals performance*

        **Reading the Comparison:**
        - **Larger areas = weaker regions** (higher scores across dimensions)
        - **Smaller areas = stronger regions** (lower scores across dimensions)
        - **Higher values = weaker performance** in that dimension
        - **Lower values = stronger performance** in that dimension
        - Overlapping areas show similar performance profiles
        - Use the legend to toggle individual events on/off
        """
        )


def render_radar_dimensions_comparison(
    all_radar_data: Dict[str, Dict[str, float]],
) -> None:
    """Render detailed comparison breakdown of radar dimensions across multiple events."""
    st.markdown("### 📊 Dimensional Comparison")

    # Get all dimensions from the first event (they should all have the same dimensions)
    dimensions = (
        list(next(iter(all_radar_data.values())).keys()) if all_radar_data else []
    )

    # Create comparison table
    comparison_data = []
    for event_code, radar_data in all_radar_data.items():
        row = {"Event": event_code}
        for dimension in dimensions:
            row[dimension] = f"{radar_data.get(dimension, 0):.2f}"

        # Calculate total and average scores
        total_score = sum(v for v in radar_data.values() if isinstance(v, (int, float)))
        avg_score = total_score / len(radar_data) if radar_data else 0
        row["Total"] = f"{total_score:.1f}"
        row["Average"] = f"{avg_score:.2f}"

        comparison_data.append(row)

    # Display comparison table
    if comparison_data:
        st.markdown("#### 📋 Event Performance Comparison")
        df = pd.DataFrame(comparison_data)
        st.dataframe(df, use_container_width=True)

    # Create side-by-side metrics for each dimension
    st.markdown("#### 📊 Dimension-by-Dimension Analysis")

    for dimension in dimensions:
        st.markdown(f"**{dimension}**")
        cols = st.columns(len(all_radar_data))

        for i, (event_code, radar_data) in enumerate(all_radar_data.items()):
            with cols[i]:
                value = radar_data.get(dimension, 0)
                st.metric(
                    event_code,
                    f"{value:.2f}",
                    help=f"{dimension} score for {event_code}",
                )

        st.markdown("---")

    # Summary analysis
    st.markdown("#### 📈 Comparison Summary")

    # Find best performing event in each dimension
    best_performers = {}
    for dimension in dimensions:
        best_event = max(all_radar_data.items(), key=lambda x: x[1].get(dimension, 0))
        best_performers[dimension] = (best_event[0], best_event[1].get(dimension, 0))

    col1, col2 = st.columns(2)
    with col1:
        st.markdown("**🏆 Top Performers by Dimension:**")
        for dimension, (event, score) in best_performers.items():
            st.markdown(f"- **{dimension}**: {event} ({score:.2f})")

    with col2:
        # Calculate overall rankings
        event_totals = {}
        for event_code, radar_data in all_radar_data.items():
            total = sum(v for v in radar_data.values() if isinstance(v, (int, float)))
            event_totals[event_code] = total

        # Sort by total score
        sorted_events = sorted(event_totals.items(), key=lambda x: x[1], reverse=True)

        st.markdown("**📊 Overall Rankings:**")
        for i, (event, total) in enumerate(sorted_events):
            medal = (
                "🥇" if i == 0 else "🥈" if i == 1 else "🥉" if i == 2 else f"{i+1}."
            )
            st.markdown(f"{medal} **{event}**: {total:.1f}")


def main() -> None:
    st.title("🏁 FRC Event Calculator")
    st.markdown(
        "**The complete toolkit for FRC event analysis and championship qualification tracking**"
    )

    # Credentials setup with better UX
    render_credentials_setup()

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
