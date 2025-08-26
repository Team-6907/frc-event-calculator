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

## Streamlit Dashboard (v2.1.0)

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
- **🏆 Event Analysis**: Smart event selection (dropdown + manual override), improved progress tracking, and formatted data tables with team info
- **📊 Points Calculator**: Redesigned interface with better input validation, visual points breakdown, and comprehensive team performance metrics
- **🏁 Regional Pool**: Enhanced season building with detailed progress tracking, qualification status indicators, and summary statistics

### UI Improvements:
- Modern design with emoji icons and better visual hierarchy
- Mobile-friendly forms with text inputs instead of number spinners
- Enhanced error handling with expandable details and contextual help
- Better data visualization with column configuration and status indicators

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
