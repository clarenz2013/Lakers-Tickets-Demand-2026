"""Build a table of Lakers home games with LeBron and Luka availability flags."""
import time
from pathlib import Path

import pandas as pd
from nba_api.stats.endpoints import leaguegamefinder, playergamelog

LAKERS_ID = 1610612747
LEBRON_ID = 2544
LUKA_ID = 1629029
SEASONS = [f"{y}-{str(y + 1)[-2:]}" for y in range(2018, 2027)]
OUTPUT_FILE = Path("data/clean/lakers_home_games.csv")


def get_lakers_games(season):
    finder = leaguegamefinder.LeagueGameFinder(
        team_id_nullable=LAKERS_ID,
        season_nullable=season,
        season_type_nullable="Regular Season",
        timeout=60,
    )
    df = finder.get_data_frames()[0]
    time.sleep(1)
    return df


def games_played_for_lakers(player_id, season):
    """Game IDs where the player appeared AND was on the Lakers."""
    log = playergamelog.PlayerGameLog(
        player_id=player_id,
        season=season,
        season_type_all_star="Regular Season",
        timeout=60,
    ).get_data_frames()[0]
    time.sleep(1)
    if log.empty:
        return set()
    id_col = next(c for c in log.columns if c.lower() == "game_id")
    with_lakers = log[log["MATCHUP"].str.startswith("LAL")]
    return set(with_lakers[id_col])


def main():
    seasons = []
    for season in SEASONS:
        print(f"Pulling {season}...")
        games = get_lakers_games(season)
        if games.empty:
            print(f"  No games found for {season}, skipping.")
            continue

        games = games.sort_values("GAME_DATE").reset_index(drop=True)
        games["season"] = season
        games["win"] = (games["WL"] == "W").astype(int)
        games["wins_before"] = games["win"].cumsum() - games["win"]
        games["win_pct_entering"] = games["wins_before"] / games.index

        lebron = games_played_for_lakers(LEBRON_ID, season)
        luka = games_played_for_lakers(LUKA_ID, season)
        games["lebron_played"] = games["GAME_ID"].isin(lebron).astype(int)
        games["luka_played"] = games["GAME_ID"].isin(luka).astype(int)
        seasons.append(games)

    df = pd.concat(seasons, ignore_index=True)
    df = df[df["MATCHUP"].str.contains("vs.", regex=False)].copy()

    df["game_date"] = pd.to_datetime(df["GAME_DATE"])
    df["opponent"] = df["MATCHUP"].str.split().str[-1]
    df["day_of_week"] = df["game_date"].dt.day_name()
    df["month"] = df["game_date"].dt.month

    keep = ["season", "GAME_ID", "game_date", "opponent", "WL",
            "win_pct_entering", "lebron_played", "luka_played",
            "day_of_week", "month"]
    df = df[keep].rename(columns={"GAME_ID": "game_id", "WL": "result"})

    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(OUTPUT_FILE, index=False)

    print(f"\nSaved {len(df)} home games to {OUTPUT_FILE}.")
    print(df.groupby("season")[["lebron_played", "luka_played"]].agg(["count", "sum"]))


if __name__ == "__main__":
    main()