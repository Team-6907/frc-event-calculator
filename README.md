# FRC Event Calculator

[English](README.md) | [中文（简体）](README.zh-CN.md)

Analyzer and points calculator for FRC (FIRST Robotics Competition) events. Implements 2025+ regional points rules, supports full-season pool calculation, and provides both CLI and Python API with local caching and live progress indicators.

## Features

- Event analysis: teams, rankings, alliances, matches, awards
- 2025+ regional points: qualification, alliance selection, playoff advancement, awards, rookie bonuses
- Regional pool: weekly auto-advancement + slot fill rules (2025); top‑3 per event with backfill option (2026)
- Caching: automatic JSON caching of FRC Events API responses under `data/`
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
- `regional-pool` first counts season events (fast) and then builds each event (slow, with a progress bar). Subsequent runs are faster due to caching under `data/`.

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

- Cache files live under `data/` (auto‑created) and mirror FRC Events API responses.
- Re‑runs prefer cache unless a missing section is needed.
- You can safely delete `data/` to force re‑fetch.

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
- Tests currently rely on live FRC Events API (or local cache). If you want deterministic tests, record responses into `data/` first.

## License

Add your license here.

## Support

- Open issues in the repository with repro steps and logs
- Ensure your `.env` is set and network is reachable on first run

## Changelog

### v1.0.0
- Refactored to a clean package with CLI and progress indicators
- Preserved all original calculations and APIs (now under `src/frc_calculator`)
- Added local cache auto‑creation and better UX
