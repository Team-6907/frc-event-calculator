# FRC Event Calculator

[English](README.md) | [中文（简体）](README.zh-CN.md)

Analyzer and points calculator for FRC (FIRST Robotics Competition) events. Implements 2025+ regional points rules, supports full-season pool calculation, and provides both CLI and Python API with local caching and live progress indicators.

## Features

- Event analysis: teams, rankings, alliances, matches, awards
- 2025+ regional points: qualification, alliance selection, playoff advancement, awards, rookie bonuses
- Regional pool: weekly auto-advancement + slot fill rules (2025); top‑3 per event with backfill option (2026)
- Caching: automatic JSON caching of FRC Events API responses under `cache/`
- Progress: spinners and progress bars for long fetches in CLI
- Statbotics EPA: optional per-event EPA retrieval
- CLI and API: human‑readable tables and JSON output

## Requirements

- Python 3.10+
- FRC Events API credentials (`AUTH_USERNAME`, `AUTH_TOKEN`)
- Internet access on first run (later runs use cache)

## Installation

```bash
git clone <repository-url>
cd frc-event-calculator
pip install -e .
```

## Configuration

Create a `.env` file at project root:

```
AUTH_USERNAME=your_username
AUTH_TOKEN=your_api_token
```

Get credentials from the official FRC Events API: https://frc-api.firstinspires.org/

## CLI Usage

Progress indicators are shown during long fetches; first run will be slower (cache warm‑up).

```bash
# Analyze a specific event
frc-calculator analyze-event 2024 AZVA

# Calculate regional points for a team
frc-calculator calculate-points 2024 AZVA 1234 --verbose
frc-calculator calculate-points 2024 AZVA 1234 --json

# View regional pool standings
frc-calculator regional-pool 2025 --week 6 --top 50
frc-calculator regional-pool 2026 --week 3 --use-season 2026
```

Notes:
- `regional-pool` first counts season events (fast) and then builds each event (slow, with a progress bar). Subsequent runs are faster due to caching under `cache/`.

## Streamlit Dashboard (v2.6.0)

A modern, user-friendly Streamlit dashboard with enhanced UI/UX and comprehensive FRC event analysis tools.

Installation:

```bash
pip install -e .
pip install -r requirements.txt  # ensures streamlit is installed
```

Run the dashboard:

```bash
streamlit run src/frc_calculator/ui/streamlit_app.py
```

### Features:
- **🔐 Enhanced Credential Setup**: Moved from sidebar to main interface with inline validation, clear error messaging, and better security indicators
- **🧭 Global Context Bar (NEW)**: Single, persistent bar for Season/Event (event‑scoped tabs) and Season/Rules/Week (Regional Pool). Selections persist across tabs and sync to the URL for deep links.
- **🏆 Event Analysis**: Smart event selection (dropdown + manual override), improved progress tracking, and formatted data tables with team info
- **📊 Points Calculator**: Team dropdown populated from the selected event for intuitive selection; enhanced results with visual points breakdown and team details
- **🏁 Regional Pool**: Season‑scoped inputs moved into the context bar with detailed progress tracking, qualification status indicators, and summary statistics
- **📈 Event Statistics**: Comprehensive event analysis with score trends, playoff performance, EPA integration, and statistical insights
- **📡 Event Radar**: NEW! 8-dimensional radar chart analysis providing comprehensive event insights across multiple performance metrics including competitiveness, team strength, and playoff performance

### UI Improvements:
- Modern design with emoji icons and better visual hierarchy
- Mobile-friendly forms with text inputs instead of number spinners
- Enhanced error handling with expandable details and contextual help
- Better data visualization with column configuration and status indicators
- Deep-linking via query params for `tab`, `scope`, `season`, `event`, `team`, `pool_week`, and `pool_rules`

## Python API

```python
from frc_calculator.models.event import Event
from frc_calculator.services.season import Season

# Single event
event = Event(2024, "AZVA")
team = event.get_team_from_number(1234)
points = team.regional_points_2025()
print(points)

# Regional pool
season = Season(2025, useSeason=2025)
pool_w6 = season.regional_pool_2025(weekNumber=6)
print(list(pool_w6.items())[:5])
```

## Caching & Data

- Cache files live under `cache/` (auto‑created) and mirror FRC Events API responses.
- Re‑runs prefer cache unless a missing section is needed.
- You can safely delete `cache/` to force re‑fetch.

## Project Structure

```
src/frc_calculator/
  cli/app.py                  # CLI commands
  config/constants.py         # Season constants (2025/2026)
  data/frc_events.py          # FRC Events API + caching
  data/statbotics.py          # Statbotics EPA client
  models/{event,team,alliance,match}.py
  services/season.py          # Season builder + regional pool
  utils/{io_utils,math_utils}.py
  ui/components.py            # Shared Streamlit helpers (selection, progress, validation)
  ui/charts.py                # Radar chart rendering helpers
  ui/streamlit_app.py         # Streamlit dashboard (tabs use helpers)
```

## Development

```bash
pip install -e .
pip install -r requirements.txt

# Run tests (note: uses live network unless you provide cached data)
python Test.py
```

Hints:
- The CLI shows progress spinners/bars; programmatic API is silent unless you pass a progress callback.
- Tests currently rely on live FRC Events API (or local cache). If you want deterministic tests, record responses into `cache/` first.

## License

Add your license here.

## Support

- Open issues in the repository with repro steps and logs
- Ensure your `.env` is set and network is reachable on first run

## Changelog

### v2.6.0 (Scope-Aware Context Bar + Team Dropdown)
- **🧭 Global Context Bar**: Unified season/event selectors across tabs with scope awareness (event vs season) and URL deep-linking
- **📊 Points Tab Team Dropdown**: Team number is now a dropdown populated from the selected event (falls back to text input when data unavailable)
- **🏁 Regional Pool Integration**: Season, rules season, and week inputs moved into the context bar (Top N stays local)
- **🔗 URL Sync**: Selections mirror to query params for shareable links and state restoration
- **🧹 Refactor**: Removed per-tab duplicate selectors in Analyze, Points, and Statistics tabs, now consume shared context

### v2.5.0 (UI Helpers Refactor)
- **🧩 Shared UI Components**: Extracted common Streamlit UI patterns into `ui/components.py` (event selectors, validation, progress callbacks)
- **📈 Charts Module**: Moved radar chart rendering into `ui/charts.py` for cleaner separation and easier styling
- **🧹 Reduced Duplication**: Refactored Analyze, Points, Statistics, and Radar tabs to use the shared helpers with no behavior change
- **🔧 Minor Cleanup**: Removed unused imports and unified numeric validation; kept existing UX intact

### v2.4.3 (Auto-Fetch Event Listings)
- **🚀 NEW Auto-Fetch Feature**: Automatically fetches 2023, 2024, and 2025 event listings on app startup when credentials are provided
- **⚡ Improved Startup Experience**: Eliminates "No events loaded" message by pre-loading event data automatically
- **🔄 Smart Cache Management**: Intelligent cache invalidation and UI refresh after event listings are loaded
- **📱 Better User Experience**: No more need to manually restart the app after entering credentials
- **🔧 Session State Management**: Enhanced state management for seamless event data loading and UI updates

### v2.4.2 (Progress Tracking Bug Fix)
- **🐛 Bug Fix**: Fixed progress tracking discrepancy in Regional Pool (was showing "20/7 events", now correctly shows "7/7 events")
- **📊 Accurate Event Counting**: Progress bar now only counts events for the requested week, not all weeks
- **⚡ Performance Improvement**: Season building now only processes events up to the requested week
- **📡 NEW Event Radar Tab**: 8-dimensional radar chart analysis with interactive Plotly visualization
- **🎨 Colorblind-Friendly Design**: High contrast, colorblind-safe color palette for better accessibility
- **📊 Radar Chart Dimensions**: Overall competitiveness, ranking point difficulty, non-playoff team strength (TANK), returning team strength (HOME), veteran team count (REIGN), playoff competitiveness (Title), and finals performance (CHAMP)
- **🔍 Enhanced Analysis**: Comprehensive event profiling with dimensional breakdowns and tier classification
- **📈 Interactive Visualization**: Plotly-powered radar charts with detailed interpretation guides and metric breakdowns
- **⚡ Performance Optimizations**: Streamlined EPA progress reporting for improved user experience
- **🔄 Enhanced EPA Processing**: Improved batch processing with fallback mechanisms for better reliability

### v2.2.0 (Event Statistics & Analysis)
- **📈 New Event Statistics Tab**: Comprehensive event analysis with score trends, playoff performance, EPA integration, and statistical insights
- **🤖 EPA Integration**: Seamless Statbotics EPA data fetching with progress tracking and caching
- **📊 Advanced Analytics**: Qualification vs playoff score comparisons, match score distributions, and team performance metrics
- **🔧 Enhanced Caching**: Improved cache management with separate EPA cache controls and better user feedback
- **⚡ Performance Optimizations**: Better progress indicators for long-running operations and smarter data loading

### v2.1.0 (UI/UX Overhaul)
- **🎨 Complete UI Redesign**: Modern interface with emoji icons, better visual hierarchy, and improved spacing
- **📱 Mobile-Friendly Forms**: Replaced number spinners with text inputs for better mobile experience
- **🔐 Enhanced Credential Management**: Moved from sidebar to main interface with inline validation and clearer error messaging
- **📊 Better Data Visualization**: Enhanced table formatting, column configuration, progress indicators, and summary statistics
- **🚀 Improved User Experience**: Contextual help, expandable error details, and actionable guidance messages

### v2.0.0 (Refactor)
- Added Streamlit dashboard with event dropdowns and manual overrides
- Credential validation in UI; clear auth errors; safer API client with timeouts
- Improved progress feedback for regional pool builds (status + recent events)
- Documentation updated (README, README.zh-CN, CLAUDE.md)

### v1.0.0
- Refactored to a clean package with CLI and progress indicators
- Preserved all original calculations and APIs (now under `src/frc_calculator`)
- Added local cache auto‑creation and better UX
