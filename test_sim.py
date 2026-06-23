import json
from elo_fetcher import fetch_elo_ratings
from simulator import run_one_simulation

with open('teams.json', 'r') as f:
    teams = json.load(f)
with open('matches.json', 'r') as f:
    matches = json.load(f)

ratings = fetch_elo_ratings(cache_hours=24)

# Run 5 simulations and print the R32 teams to see if they vary
for i in range(5):
    res = run_one_simulation(teams, matches, ratings)
    r32_teams = sorted(res['r32'])
    print(f"Sim {i} R32 teams ({len(r32_teams)}): {r32_teams}")
    
    # Let's also print Group K standings for Sim 0
    if i == 0:
        from simulator import get_standings
        group_m = [m for m in matches if m['team_a'] in teams['K'] and m['team_b'] in teams['K']]
        standings, stats = get_standings('K', teams['K'], group_m, ratings)
        print("Group K Stats:")
        for t in standings:
            print(f"  {t}: {stats[t]}")
