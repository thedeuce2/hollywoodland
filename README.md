# HOLLYWOODLAND — Talent Agency & Showbiz Management Sim

Build a boutique Hollywood talent agency from the ground up — scout rising prospects, negotiate representation contracts, match clients to open movie and TV casting calls, broker acting fees and backend points, and guide your roster through box office runs, TV renewals, home media tails, and annual awards season.

## Quick Install & Play (Windows)

1. Install **Python 3.11 or 3.12** from [python.org](https://www.python.org/downloads/) (check **"Add Python to PATH"** during setup).
2. Download or clone this repository.
3. Double-click **`Install Requirements.bat`** (installs `PySide6` and `Pillow`).
4. Double-click **`Launch Hollywoodland.bat`** to play!

## Quick Install & Play (macOS / Linux / CLI)

```bash
pip install -r requirements.txt
python main.py
```

## Optional Command-Line Flags

```bash
python main.py --player "Your Name" --agency "Starlight Talent" --budget 50000
```

## Running Tests

```bash
pytest tests/test_hollywoodland.py -v
```
