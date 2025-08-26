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

# Run Streamlit dashboard (V2.6.1)
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

### Streamlit (V2.6.1) UX
- **Global Context Bar (scope-aware)**: Single persistent bar for Season/Event on event-scoped tabs, and Season/Rules/Week on Regional Pool; selections persist across tabs and sync to URL query params
- **Analyze Event tab**: Uses the context bar for season/event, retains improved progress and tables
- **Calculate Points tab**: Uses the context bar for season/event; Team input is now a dropdown populated from the selected event (falls back to manual input if data unavailable)
- **Regional Pool tab**: Season/Rules/Week moved to the context bar with detailed progress tracking and better summaries
- **Event Statistics tab**: Uses the context bar for season/event; retains EPA integration and analytics
- **Event Radar tab**: Multi-event comparison remains specialized (unchanged)
 - **Settings Dialog**: Credentials and cache controls moved into a modal; compact status bar replaces always-on controls

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
- `frc_events.py`: Handles FRC Events API requests with automatic JSON caching under `cache/`
- `statbotics.py`: Optional Statbotics EPA integration
- `utils/event_stats.py`: Event statistical analysis with EPA integration, comprehensive metrics, and radar chart calculations
- `ui/streamlit_app.py`: Streamlit dashboard with five tabs, using shared components and charts
- `ui/components.py`: Shared Streamlit helpers (context bar, event selectors, validation, progress callbacks)
- `ui/charts.py`: Radar chart rendering utilities

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
3. Responses cached as JSON files under `cache/` directory
4. Models parse cached data and calculate points/rankings
5. Results displayed via Rich console tables, Streamlit tables, or JSON output

### Environment Requirements
- Python 3.10+
- FRC Events API credentials in `.env` file (`AUTH_USERNAME`, `AUTH_TOKEN`)
- Internet access on first run (subsequent runs use cache)

Notes:
- Invalid credentials are surfaced clearly in the UI; listings/requests will not silently appear empty.
- Without credentials, only locally cached data in `cache/` is used.

### Progress System
- CLI shows spinners/progress bars for long operations
- Streamlit shows: status updates for event analysis, a progress bar + live status text + recent codes for season builds
- Programmatic API is silent unless progress callback provided

## V2.6.1 Highlights
- **Settings Dialog + Status Bar**: Consolidated credentials & cache management; smaller surface area, better flow
- **Silent Validation**: Validate action fetches listings quietly and confirms success succinctly
- **Dialog Width**: Increased modal width to reduce form clutter

## V2.6.0 Highlights
- **Scope-Aware Context Bar**: Unified selection experience across tabs with URL deep-linking
- **Team Dropdown in Points**: Team picker derives from event teams; improves discoverability and speed
- **Regional Pool Integration**: Season/Rules/Week inputs centralized; Top N remains local to tab
- **State Persistence**: Session + query params keep context stable across reloads and shareable via URL

## V2.5.0 Highlights
- **Shared UI Components**: Centralized event selection, progress callbacks, and validation under `ui/components.py` to remove duplication across tabs
- **Charts Extraction**: Moved radar chart rendering into `ui/charts.py` for better separation and easier styling updates
- **Refactors Only**: No functional behavior changes; UI is lighter and more maintainable

## V2.4.2 Highlights
- **Bug Fix**: Fixed progress tracking discrepancy in Regional Pool (was showing "20/7 events", now correctly shows "7/7 events")
- **Accurate Event Counting**: Progress bar now only counts events for the requested week, not all weeks
- **Performance Improvement**: Season building now only processes events up to the requested week
- **NEW Event Radar Tab**: 8-dimensional radar chart analysis with interactive Plotly visualization
- **Colorblind-Friendly Design**: High contrast, colorblind-safe color palette for better accessibility
- **Radar Chart Dimensions**: Overall competitiveness, ranking point difficulty, non-playoff team strength (TANK), returning team strength (HOME), veteran team count (REIGN), playoff competitiveness (Title), and finals performance (CHAMP)
- **Enhanced Analysis**: Comprehensive event profiling with dimensional breakdowns and tier classification
- **Interactive Visualization**: Plotly-powered radar charts with detailed interpretation guides and metric breakdowns
- **Performance Optimizations**: Streamlined EPA progress reporting for improved user experience

## V2.3.1 Highlights
- **Enhanced Progress UX**: Cleaner, less verbose progress indicators for Event Statistics tab with filtered messages showing only key milestones
- **Better EPA Progress**: Shows percentage completion with reduced update frequency for improved performance
- **Collapsed Status**: Progress status starts collapsed by default for less intrusive user experience
- **Performance Optimizations**: Reduced DOM updates during EPA data fetching for smoother operation

## V2.2.0 Highlights
- **NEW Event Statistics Tab**: Comprehensive event analysis with score trends, playoff performance, EPA integration, and statistical insights
- **EPA Integration**: Seamless Statbotics EPA data fetching with progress tracking and caching
- **Advanced Analytics**: Qualification vs playoff score comparisons, match score distributions, and team performance metrics
- **Enhanced Caching**: Improved cache management with separate EPA cache controls and better user feedback
- **Performance Optimizations**: Better progress indicators for long-running operations and smarter data loading

## V2.1.0 Highlights
- **Modernized UI/UX**: Complete Streamlit interface redesign with better visual hierarchy, emoji icons, and improved spacing
- **Enhanced Forms**: Replaced number spinners with text inputs, smart event selection, and better mobile experience
- **Improved Credential Management**: Moved from sidebar to main interface with inline validation and clearer error messaging
- **Better Data Visualization**: Enhanced table formatting, column configuration, progress indicators, and summary statistics
- **Enhanced Error Handling**: Expandable error details, contextual help, and actionable guidance messages

## Testing Notes
- Tests in `Test.py` use live FRC Events API data or cached responses from `cache/` directory
- Tests verify core functionality: event parsing, team rankings, alliance structure, matches, awards, and points calculations
- For consistent test results, ensure API credentials are configured or that relevant cache files exist in `cache/`
