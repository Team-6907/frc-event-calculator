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


st.set_page_config(
    page_title="FRC Event Calculator", 
    layout="wide",
    initial_sidebar_state="collapsed"
)


def render_credentials_setup() -> bool:
    """Render credentials setup in main area with better UX"""
    st.markdown("### 🔐 FRC Events API Setup")
    st.markdown("Enter your FRC Events API credentials to access live data. Without them, only cached data will be available.")
    
    col1, col2, col3 = st.columns([2, 2, 1])
    
    with col1:
        default_user = os.getenv("AUTH_USERNAME", "")
        username = st.text_input(
            "Username", 
            value=default_user,
            placeholder="Enter your FRC Events API username",
            help="Your FRC Events API username"
        )
    
    with col2:
        default_token = os.getenv("AUTH_TOKEN", "")
        token = st.text_input(
            "Auth Token", 
            value=default_token, 
            type="password",
            placeholder="Enter your auth token",
            help="Your FRC Events API authorization token"
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
    if st.button("🔄 Clear Cache", help="Clear cached event listings"):
        try:
            get_event_options.clear()
            st.toast("✓ Event listings cache cleared", icon="🔄")
        except Exception:
            pass
    
    st.markdown("---")
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
                help="Choose from available events"
            )
            mapping = {label: code for label, code in opts}
            event_code = mapping.get(selected_label, "")
            
            # Show manual override option
            if st.checkbox("Enter custom event code", key="manual_override_analysis"):
                event_code = st.text_input(
                    "Event Code",
                    value=event_code,
                    placeholder="e.g., AZVA, CAFR, CTHAR",
                    key="analysis_event_manual",
                    help="Enter the 4-5 character event code"
                ).strip().upper()
        else:
            st.info("💡 No events loaded. Enter credentials above or provide an event code.")
            event_code = st.text_input(
                "Event Code",
                value="AZVA",
                placeholder="e.g., AZVA, CAFR, CTHAR", 
                key="analysis_event_manual_fallback",
                help="Enter the 4-5 character event code"
            ).strip().upper()
    
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
                    "Alliance": team.alliance.allianceNumber if team.alliance else "—",
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
                    "Alliance": st.column_config.TextColumn(width="small")
                }
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
                        "Team #": getattr(rec.get("Team"), "teamNumber", "—"),
                        "Recipient": rec.get("Person", "—"),
                    }
                )
        
        st.markdown("### 🏅 Awards")
        if award_rows:
            st.dataframe(
                award_rows, 
                use_container_width=True, 
                hide_index=True,
                column_config={
                    "Team #": st.column_config.TextColumn(width="small")
                }
            )
        else:
            st.info("💡 No awards data available for this event.")

    except AuthError:
        st.error("🔐 **Authentication Error**: Invalid credentials. Please check your username and token above.")
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
                help="Choose from available events"
            )
            mapping = {label: code for label, code in opts}
            event_code = mapping.get(selected_label, "")
            
            if st.checkbox("Enter custom event code", key="manual_override_points"):
                event_code = st.text_input(
                    "Event Code",
                    value=event_code,
                    placeholder="e.g., AZVA, CAFR, CTHAR",
                    key="points_event_manual",
                    help="Enter the 4-5 character event code"
                ).strip().upper()
        else:
            st.info("💡 No events loaded. Enter credentials above or provide an event code.")
            event_code = st.text_input(
                "Event Code",
                value="AZVA",
                placeholder="e.g., AZVA, CAFR, CTHAR",
                key="points_event_manual_fallback",
                help="Enter the 4-5 character event code"
            ).strip().upper()
    
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
        
        with st.spinner(f"📥 Loading {season} {event_code} and calculating points for Team {team_number}..."):
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
                help="Total regional points earned at this event"
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
                column_config={
                    "Points": st.column_config.NumberColumn(width="small")
                }
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
                column_config={
                    "Score": st.column_config.NumberColumn(width="small")
                }
            )
            
    except AuthError:
        st.error("🔐 **Authentication Error**: Invalid credentials. Please check your username and token above.")
    except ApiError as e:
        st.warning(f"🌐 **API Error**: {str(e)}")
    except KeyError:
        st.error(f"❌ **Team not found**: Team {team_number} was not found in event {event_code}. Please check the team number.")
    except Exception as e:
        st.error("❌ **Error**: Failed to calculate points.")
        with st.expander("See error details"):
            st.exception(e)


def render_regional_pool_tab() -> None:
    st.markdown("### 🏁 Regional Pool Standings")
    st.markdown("View championship qualification standings based on regional point calculations.")
    
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
        st.warning("⚠️ Please enter valid numeric values for season, rules season, and top N.")
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
            total_events = sum(len(listings.get(f"Week {w}", {}).get("Events", [])) for w in range(1, week_int + 1))
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
                    recent_placeholder.caption(f"🔄 Recently processed: {recent_display}")
                except Exception:
                    pass

            season_obj = Season(season_int, useSeason=use_season_int, progress=on_event_built)
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
                    "Team Name": getattr(row["team"], 'name', '—'),
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
                }
            )
            
            # Summary stats
            qualified_count = sum(1 for row in rows if "✅" in row["Qualified"])
            st.markdown(f"**📊 Summary:** Showing {len(rows)} teams • {qualified_count} qualified for championships")
        else:
            st.info("No standings data available.")

    except AuthError:
        st.error("🔐 **Authentication Error**: Invalid credentials. Please check your username and token above.")
    except ApiError as e:
        st.warning(f"🌐 **API Error**: {str(e)}")
    except Exception as e:
        st.error("❌ **Error**: Failed to build regional pool standings.")
        with st.expander("See error details"):
            st.exception(e)


def main() -> None:
    st.title("🏁 FRC Event Calculator")
    st.markdown("**The complete toolkit for FRC event analysis and championship qualification tracking**")
    
    # Credentials setup with better UX
    has_creds = render_credentials_setup()
    
    # Main application tabs
    tab1, tab2, tab3 = st.tabs(["🏆 Analyze Event", "📊 Calculate Points", "🏁 Regional Pool"])
    
    with tab1:
        render_event_analysis_tab()
    with tab2:
        render_points_tab()
    with tab3:
        render_regional_pool_tab()


if __name__ == "__main__":
    main()
