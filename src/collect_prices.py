"""Daily snapshot of SeatGeek ticket prices for Lakers home games."""
import csv
import os
from datetime import datetime, timezone
from pathlib import Path

import requests
from dotenv import load_dotenv

load_dotenv()
CLIENT_ID = os.getenv("SEATGEEK_CLIENT_ID")
URL = "https://api.seatgeek.com/2/events"
OUTPUT_FILE = Path("data/raw/price_snapshots.csv")

FIELDS = [
    "snapshot_time_utc", "event_id", "game_datetime_local", "title",
    "venue", "home_team", "away_team", "lowest_price", "average_price",
    "median_price", "highest_price", "listing_count",
]


def fetch_events():
    params = {
        "client_id": CLIENT_ID,
        "performers.slug": "los-angeles-lakers",
        "datetime_utc.gte": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        "sort": "datetime_utc.asc",
        "per_page": 100,
    }
    response = requests.get(URL, params=params, timeout=30)
    response.raise_for_status()
    return response.json().get("events", [])


def get_teams(event):
    home, away = None, None
    for performer in event.get("performers", []):
        if performer.get("home_team"):
            home = performer.get("name")
        elif performer.get("away_team"):
            away = performer.get("name")
    return home, away


def main():
    if not CLIENT_ID:
        raise SystemExit("No SEATGEEK_CLIENT_ID found. Check your .env file.")

    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    events = fetch_events()
    print(f"SeatGeek returned {len(events)} upcoming events.")

    rows = []
    for event in events:
        home, away = get_teams(event)
        if not home or "Lakers" not in home:
            continue  # keep only Lakers home games
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

    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    is_new_file = not OUTPUT_FILE.exists()
    with open(OUTPUT_FILE, "a", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS)
        if is_new_file:
            writer.writeheader()
        writer.writerows(rows)

    print(f"Saved {len(rows)} Lakers home games to {OUTPUT_FILE}.")


if __name__ == "__main__":
    main()