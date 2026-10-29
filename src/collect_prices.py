"""Daily snapshot of SeatGeek ticket prices for home games of selected NBA teams."""
import csv
import os
import time
from datetime import datetime, timezone
from pathlib import Path

import requests
from dotenv import load_dotenv

load_dotenv()
CLIENT_ID = os.getenv("SEATGEEK_CLIENT_ID")
URL = "https://api.seatgeek.com/2/events"
OUTPUT_FILE = Path("data/raw/price_snapshots.csv")

# SeatGeek team names (slugs). Add more teams to this list any time.
TEAMS = [
    "los-angeles-lakers",
    "philadelphia-76ers",
    "los-angeles-clippers",
    "new-york-knicks",
    "golden-state-warriors",
    "boston-celtics",
    "san-antonio-spurs",
    "oklahoma-city-thunder",
]

FIELDS = [
    "snapshot_time_utc", "event_id", "game_datetime_local", "title",
    "venue", "home_team", "away_team", "lowest_price", "average_price",
    "median_price", "highest_price", "listing_count",
]


def fetch_events(team_slug):
    params = {
        "client_id": CLIENT_ID,
        "performers.slug": team_slug,
        "datetime_utc.gte": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        "sort": "datetime_utc.asc",
        "per_page": 100,
    }
    response = requests.get(URL, params=params, timeout=30)
    response.raise_for_status()
    return response.json().get("events", [])


def get_teams(event):
    home_slug, home_name, away_name = None, None, None
    for performer in event.get("performers", []):
        if performer.get("home_team"):
            home_slug, home_name = performer.get("slug"), performer.get("name")
        elif performer.get("away_team"):
            away_name = performer.get("name")
    return home_slug, home_name, away_name


def main():
    if not CLIENT_ID:
        raise SystemExit("No SEATGEEK_CLIENT_ID found. Check your .env file.")

    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    rows = []

    for team_slug in TEAMS:
        try:
            events = fetch_events(team_slug)
        except requests.RequestException as err:
            status = err.response.status_code if err.response is not None else "network error"
            print(f"WARNING: {team_slug} failed ({status}). Skipping.")
            continue

        saved = 0
        for event in events:
            home_slug, home, away = get_teams(event)
            if home_slug != team_slug:
                continue  # keep only this team's home games
            stats = event.get("stats") or {}
            rows.append({
                "snapshot_time_utc": now,
                "event_id": event.get("id"),
                "game_datetime_local": event.get("datetime_local"),
                "title": event.get("title"),
                "venue": (event.get("venue") or {}).get("name"),
                "home_team": home,
                "away_team": away,
                "lowest_price": stats.get("lowest_price"),
                "average_price": stats.get("average_price"),
                "median_price": stats.get("median_price"),
                "highest_price": stats.get("highest_price"),
                "listing_count": stats.get("listing_count"),
            })
            saved += 1

        print(f"{team_slug}: {saved} home games")
        if saved == 0:
            print(f"  WARNING: nothing found for {team_slug}. The name may be wrong.")
        time.sleep(0.5)

    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    is_new_file = not OUTPUT_FILE.exists()
    with open(OUTPUT_FILE, "a", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS)
        if is_new_file:
            writer.writeheader()
        writer.writerows(rows)

    print(f"\nSaved {len(rows)} rows to {OUTPUT_FILE}.")


if __name__ == "__main__":
    main()