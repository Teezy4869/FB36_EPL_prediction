"""
Centralized Configuration for Premier League Outcome Prediction Project.
All paths are dynamically derived from the project root.
"""

from pathlib import Path
from typing import Dict, List, Any

# Dynamically resolve project root: D:\PTIT\PAYT\Mini_project
PROJECT_ROOT = Path(__file__).resolve().parent.parent

# Base directories
SRC_DIR = PROJECT_ROOT / "src"
DATA_DIR = PROJECT_ROOT / "data"
DATA_RAW_DIR = DATA_DIR / "raw"
DATA_CLEANED_DIR = DATA_DIR / "cleaned"
DATA_MODEL_DIR = DATA_DIR / "model"
REPORTS_DIR = PROJECT_ROOT / "reports"
LOGS_DIR = PROJECT_ROOT / "logs"

# Cache directory inside data/raw
CACHE_DIR = DATA_RAW_DIR / "cache"

# Source-specific raw directories (for Phase 1-4)
RAW_FOOTBALL_DATA_DIR = DATA_RAW_DIR / "football_data"
RAW_11V11_DIR = DATA_RAW_DIR / "11v11"
RAW_11V11_SEASONS_DIR = RAW_11V11_DIR / "team_seasons"
RAW_11V11_MATCHES_DIR = RAW_11V11_DIR / "matches"
RAW_WIKIPEDIA_DIR = DATA_RAW_DIR / "wikipedia"

# Ensure all essential directories exist
ALL_DIRS = [
    DATA_RAW_DIR,
    DATA_CLEANED_DIR,
    DATA_MODEL_DIR,
    REPORTS_DIR,
    LOGS_DIR,
    CACHE_DIR,
    RAW_FOOTBALL_DATA_DIR,
    RAW_11V11_SEASONS_DIR,
    RAW_11V11_MATCHES_DIR,
    RAW_WIKIPEDIA_DIR,
]


def ensure_directories() -> None:
    """Create all required project directories if they do not exist."""
    for directory in ALL_DIRS:
        directory.mkdir(parents=True, exist_ok=True)


# Network and Fetcher Configuration
USER_AGENT = "PremierLeaguePredictor/0.1 (DataEngineeringEducationalProject; Contact: student@ptit.edu.vn)"
REQUEST_TIMEOUT = 25  # seconds
RATE_LIMIT_DELAY = 1.5  # seconds between consecutive requests to the same domain
DEFAULT_DELAY = RATE_LIMIT_DELAY
MAX_RETRIES = 2
BACKOFF_FACTOR = 2.0

# Target Seasons: 2018/19 through 2025/26 (8 completed seasons)
TARGET_SEASONS: List[Dict[str, Any]] = [
    {
        "canonical": "2018-19",
        "football_data_code": "1819",
        "eleven_season": "2019",
        "wiki_slug": "2018–19_Premier_League",
    },
    {
        "canonical": "2019-20",
        "football_data_code": "1920",
        "eleven_season": "2020",
        "wiki_slug": "2019–20_Premier_League",
    },
    {
        "canonical": "2020-21",
        "football_data_code": "2021",
        "eleven_season": "2021",
        "wiki_slug": "2020–21_Premier_League",
    },
    {
        "canonical": "2021-22",
        "football_data_code": "2122",
        "eleven_season": "2022",
        "wiki_slug": "2021–22_Premier_League",
    },
    {
        "canonical": "2022-23",
        "football_data_code": "2223",
        "eleven_season": "2023",
        "wiki_slug": "2022–23_Premier_League",
    },
    {
        "canonical": "2023-24",
        "football_data_code": "2324",
        "eleven_season": "2024",
        "wiki_slug": "2023–24_Premier_League",
    },
    {
        "canonical": "2024-25",
        "football_data_code": "2425",
        "eleven_season": "2025",
        "wiki_slug": "2024–25_Premier_League",
    },
    {
        "canonical": "2025-26",
        "football_data_code": "2526",
        "eleven_season": "2026",
        "wiki_slug": "2025–26_Premier_League",
    },
]

# Source URLs for verification and Phase 0 checks
SAMPLE_URLS = {
    "football_data": {
        "robots": "https://www.football-data.co.uk/robots.txt",
        "landing": "https://www.football-data.co.uk/englandm.php",
        "sample_csv_2425": "https://www.football-data.co.uk/mmz4281/2425/E0.csv",
    },
    "eleven_v_eleven": {
        "robots": "https://www.11v11.com/robots.txt",
        "base": "https://www.11v11.com/",
        "sample_fixtures_liverpool_2425": "https://www.11v11.com/teams/liverpool/tab/matches/season/2025/",
    },
    "wikipedia": {
        "robots": "https://en.wikipedia.org/robots.txt",
        "sample_season_2425": "https://en.wikipedia.org/wiki/2024%E2%80%9325_Premier_League",
    },
    "understat": {
        "robots": "https://understat.com/robots.txt",
    },
}
