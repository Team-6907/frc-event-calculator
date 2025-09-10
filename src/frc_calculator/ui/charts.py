from __future__ import annotations

from typing import Any, Dict

import pandas as pd
import plotly.graph_objects as go
import streamlit as st


def render_radar_chart_visualization(
    radar_data: Dict[str, float], event_code: str, season: int
) -> None:
    """Render the radar chart visualization for a single event."""
    st.markdown(f"### 📡 {event_code} {season} - 8-Dimensional Radar Analysis")

    dimensions = list(radar_data.keys())
    values = list(radar_data.values())

    fig = go.Figure()
    fig.add_trace(
        go.Scatterpolar(
            r=values,
            theta=dimensions,
            fill="toself",
            name=f"{event_code} {season}",
            line=dict(color="rgb(0, 114, 178)", width=3),
            fillcolor="rgba(0, 114, 178, 0.2)",
        )
    )

    max_value = max(values) if values else 20
    scale_max = max(20, max_value * 1.2)

    # Detect theme using st.context.theme.type
    is_dark_theme = st.context.theme.type == "dark"
    
    text_color = "white" if is_dark_theme else "black"
    grid_color = "rgba(255, 255, 255, 0.6)" if is_dark_theme else "rgba(128, 128, 128, 0.6)"
    line_color = "rgba(255, 255, 255, 0.8)" if is_dark_theme else "rgba(128, 128, 128, 0.8)"

    fig.update_layout(
        polar=dict(
            radialaxis=dict(
                visible=True,
                range=[0, scale_max],
                gridcolor=grid_color,
                tickfont=dict(size=10, color=text_color),
                linecolor=line_color,
            ),
            angularaxis=dict(
                tickfont=dict(size=12, color=text_color),
                linecolor=line_color,
            ),
            bgcolor="rgba(0,0,0,0)",
        ),
        showlegend=True,
        title=dict(text=f"Event Performance Radar - {event_code} {season}", x=0.5, font=dict(size=16, color=text_color)),
        font=dict(color=text_color),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        height=500,
    )

    st.plotly_chart(fig, use_container_width=True)

    with st.expander("📖 Radar Chart Interpretation Guide"):
        st.markdown(
            """
        - Overall: Event competitiveness (20 - qual avg / 10)
        - RP: Ranking point difficulty (20-(RP-3)*10)
        - TANK: Non-playoff teams' strength (20 - EPA median / 6)
        - HOME: Returning teams' strength (20 - EPA median / 6)
        - REIGN: Veteran team presence (20 - count * 2.5)
        - TITLE: Playoff competitiveness (20 - playoff avg / 10)
        - CHAMP: Finals peak performance (20 - highest score / 25)
        """
        )


def render_radar_dimensions_breakdown(radar_data: Dict[str, float]) -> None:
    """Render detailed breakdown of radar dimensions for a single event."""
    st.markdown("### 📊 Dimensional Breakdown")

    col1, col2 = st.columns(2)
    with col1:
        st.markdown("#### 🏆 Competition Metrics")
        st.metric("Overall", f"{radar_data.get('Overall', 0):.2f}")
        st.metric("RP", f"{radar_data.get('RP', 0):.2f}")
        st.metric("TITLE", f"{radar_data.get('TITLE', 0):.2f}")
        st.metric("CHAMP", f"{radar_data.get('CHAMP', 0):.2f}")
    with col2:
        st.markdown("#### 🤖 Team Strength Metrics")
        st.metric("TANK", f"{radar_data.get('TANK', 0):.2f}")
        st.metric("HOME", f"{radar_data.get('HOME', 0):.2f}")
        st.metric("REIGN", f"{radar_data.get('REIGN', 0):.2f}")
        st.markdown("---")

    total_score = sum(v for v in radar_data.values() if isinstance(v, (int, float)))
    avg_score = total_score / len(radar_data) if radar_data else 0
    c1, c2 = st.columns(2)
    with c1:
        st.metric("Total Score", f"{total_score:.1f}")
    with c2:
        st.metric("Average Score", f"{avg_score:.2f}")


def render_radar_chart_comparison(
    all_radar_data: Dict[str, Dict[str, float]], season: int
) -> None:
    """Render the radar chart comparison visualization for multiple events."""
    st.markdown(f"### 📡 Event Radar Comparison - {season} Season")

    dimensions = list(next(iter(all_radar_data.values())).keys()) if all_radar_data else []
    fig = go.Figure()
    colors = [
        "rgb(0, 114, 178)",
        "rgb(213, 94, 0)",
        "rgb(0, 158, 115)",
        "rgb(204, 121, 167)",
        "rgb(230, 159, 0)",
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
                line=dict(color=color, width=3),
                fillcolor=color.replace("rgb", "rgba").replace(")", ", 0.2)"),
                opacity=0.8,
            )
        )

    scale_max = 1

    # Detect theme using st.context.theme.type
    is_dark_theme = st.context.theme.type == "dark"
    
    text_color = "white" if is_dark_theme else "black"
    grid_color = "rgba(255, 255, 255, 0.6)" if is_dark_theme else "rgba(128, 128, 128, 0.6)"
    line_color = "rgba(255, 255, 255, 0.8)" if is_dark_theme else "rgba(128, 128, 128, 0.8)"

    fig.update_layout(
        polar=dict(
            radialaxis=dict(
                visible=True,
                range=[0, scale_max],
                gridcolor=grid_color,
                tickfont=dict(size=10, color=text_color),
                linecolor=line_color,
            ),
            angularaxis=dict(
                tickfont=dict(size=12, color=text_color),
                linecolor=line_color,
            ),
            bgcolor="rgba(0,0,0,0)",
        ),
        showlegend=True,
        title=dict(text=f"Event Performance Radar Comparison - {season} Season", x=0.5, font=dict(size=16, color=text_color)),
        font=dict(color=text_color),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        height=500,
    )

    st.plotly_chart(fig, use_container_width=True)

    with st.expander("📖 Radar Chart Comparison Guide"):
        st.markdown(
            """
        Use the legend to toggle events. Larger areas indicate weaker regions across dimensions.
        """
        )


def render_radar_dimensions_comparison(
    final_data: Dict[str, Dict[str, float]], all_radar_data: Dict[str, Dict[str, float]]
) -> None:
    """Render comparison breakdown table and per-dimension metrics across events."""
    st.markdown("### 📊 Dimensional Comparison")

    dimensions = list(next(iter(final_data.values())).keys()) if final_data else []
    comparison_data = []
    for event_code, radar_data in final_data.items():
        row = {"Event": event_code}
        for dimension in dimensions:
            if all_radar_data[event_code][dimension] and all_radar_data[event_code][dimension] != 6907:
                if dimension in ["REIGN", "CHAMP"]:
                    row[dimension] = f"{radar_data.get(dimension, 0):.2f} ({all_radar_data[event_code].get(dimension, 0):.0f})"
                else:
                    row[dimension] = f"{radar_data.get(dimension, 0):.2f} ({all_radar_data[event_code].get(dimension, 0):.2f})"
            else:
                row[dimension] = "—"
        total_score = sum(v for v in radar_data.values() if isinstance(v, (int, float)))
        avg_score = total_score / len(radar_data) if radar_data else 0
        row["Total"] = f"{total_score:.1f}"
        row["Average"] = f"{avg_score:.2f}"
        comparison_data.append(row)

    if comparison_data:
        st.markdown("#### 📋 Event Performance Comparison")
        df = pd.DataFrame(comparison_data)
        st.dataframe(df, use_container_width=True)

    st.markdown("#### 📈 Comparison Summary")
    best_performers = {}
    for dimension in dimensions:
        best_event = max(final_data.items(), key=lambda x: x[1].get(dimension, 0))
        best_performers[dimension] = (best_event[0], best_event[1].get(dimension, 0))

    col1, col2 = st.columns(2)
    with col1:
        st.markdown("**🏆 Top Performers by Dimension:**")
        for dimension, (event, score) in best_performers.items():
            st.markdown(f"- **{dimension}**: {event} ({score:.2f})")
    with col2:
        event_totals = {}
        for event_code, radar_data in final_data.items():
            total = sum(v for v in radar_data.values() if isinstance(v, (int, float)))
            event_totals[event_code] = total
        sorted_events = sorted(event_totals.items(), key=lambda x: x[1], reverse=True)
        st.markdown("**📊 Overall Rankings:**")
        for i, (event, total) in enumerate(sorted_events):
            medal = ("🥇" if i == 0 else "🥈" if i == 1 else "🥉" if i == 2 else f"{i+1}.")
            st.markdown(f"{medal} **{event}**: {total:.1f}")

