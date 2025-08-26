# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

### Development
```bash
# Install package in development mode
pip install -e .

# Install dependencies
pip install -r requirements.txt

# Run tests
python Test.py

# Run Streamlit dashboard (V2)
streamlit run src/frc_calculator/ui/streamlit_app.py
```

### CLI Usage
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

### Streamlit (V2) UX
- Sidebar: enter `AUTH_USERNAME` and `AUTH_TOKEN`. Use "Validate credentials" to check quickly. "Refresh event listings" clears cached listings.
- Analyze Event tab: choose season and event from dropdown (labels like "Arizona Valley Regional 2024 [AZVA]") or enter a code manually. Shows progress and renders tables. Requires credentials if cache missing.
- Calculate Points tab: compute 2025 points for a team with breakdown and best 3 match scores. Requires credentials if cache missing.
- Regional Pool tab: builds season with a progress bar, live status (built count + latest code), and recent events list. Requires credentials unless all events are cached.

## Architecture

### Core Models
- `Event`: Represents a single FRC event with teams, rankings, alliances, matches, and awards
- `Team`: Individual team within an event, contains ranking and regional points calculations
- `SeasonTeam`: Aggregates a team's performance across multiple events in a season
- `Alliance`: Playoff alliance with captain and picks
- `Match`: Individual qualification or playoff matches
- `Season`: Manages all events in a season and calculates regional pool standings

### Key Services
- `Season`: Builds complete season view from FRC Events API, calculates regional pools using 2025+ rules
- `frc_events.py`: Handles FRC Events API requests with automatic JSON caching under `data/`
- `statbotics.py`: Optional Statbotics EPA integration
- `ui/streamlit_app.py`: Streamlit dashboard with three tabs and progress UI

### Points Calculation Systems
The codebase implements two regional points systems:
- **2025+ Rules** (`regional_points_2025()`): Used for current seasons, includes qualification points, alliance selection, playoff advancement, awards, and rookie bonuses
- **2026 Rules** (`regional_points_2026()`): Modified system with different slot allocation and backfill rules

### Regional Pool Logic
- **2025**: Weekly auto-advancement + slot fill system
- **2026**: Top-3 per event with optional backfill
- Constants for each season are defined in `config/constants.py`

### Data Flow
1. CLI commands trigger Event or Season creation
2. Data fetched from FRC Events API (with progress indicators)
3. Responses cached as JSON files under `data/` directory
4. Models parse cached data and calculate points/rankings
5. Results displayed via Rich console tables, Streamlit tables, or JSON output

### Environment Requirements
- Python 3.10+
- FRC Events API credentials in `.env` file (`AUTH_USERNAME`, `AUTH_TOKEN`)
- Internet access on first run (subsequent runs use cache)

Notes:
- Invalid credentials are surfaced clearly in the UI; listings/requests will not silently appear empty.
- Without credentials, only locally cached data in `data/` is used.

### Progress System
- CLI shows spinners/progress bars for long operations
- Streamlit shows: status updates for event analysis, a progress bar + live status text + recent codes for season builds
- Programmatic API is silent unless progress callback provided

## V2 Highlights
- Streamlit dashboard with event dropdowns and manual overrides
- Credential validation, clear auth errors, and safer API client with timeouts and error handling
- Improved progress feedback for building regional pools
