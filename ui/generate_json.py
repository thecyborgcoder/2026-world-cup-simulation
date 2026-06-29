import json

# Define the 32 teams for the knockout
left_teams = [
    "Argentina", "ARG", "Sweden", "SWE",
    "Mexico", "MEX", "Senegal", "SEN",
    "Netherlands", "NED", "USA", "USA",
    "England", "ENG", "Ecuador", "ECU",
    "Brazil", "BRA", "Japan", "JPN",
    "Uruguay", "URU", "South Korea", "KOR",
    "Spain", "ESP", "Morocco", "MAR",
    "Italy", "ITA", "Colombia", "COL"
]

right_teams = [
    "France", "FRA", "Nigeria", "NGA",
    "Germany", "GER", "Canada", "CAN",
    "Portugal", "POR", "Iran", "IRN",
    "Belgium", "BEL", "Peru", "PER",
    "Croatia", "CRO", "Australia", "AUS",
    "Switzerland", "SUI", "Chile", "CHI",
    "Denmark", "DEN", "Saudi Arabia", "KSA",
    "Ivory Coast", "CIV", "Wales", "WAL"
]

def format_teams(teams_list):
    res = []
    for i in range(0, len(teams_list), 2):
        res.append({"name": teams_list[i], "code": teams_list[i+1]})
    return res

left_t = format_teams(left_teams)
right_t = format_teams(right_teams)

import random
random.seed(42) # deterministic

def simulate_match(t1, t2, match_id):
    s1 = random.randint(0, 3)
    s2 = random.randint(0, 3)
    p1 = p2 = None
    if s1 > s2:
        w1 = True
    elif s2 > s1:
        w1 = False
    else:
        # Penalties
        p1 = random.randint(3, 5)
        p2 = random.randint(0, p1 - 1)
        if random.choice([True, False]):
            w1 = True
        else:
            w1 = False
            p1, p2 = p2, p1

    m = {
        "id": match_id,
        "team1": {"name": t1["name"], "code": t1["code"], "score": s1, "winner": w1},
        "team2": {"name": t2["name"], "code": t2["code"], "score": s2, "winner": not w1}
    }
    if p1 is not None:
        m["team1"]["penalties"] = p1
        m["team2"]["penalties"] = p2
        
    winner = t1 if w1 else t2
    return m, winner

def run_bracket_side(teams, prefix):
    rounds = {}
    current_teams = teams
    round_names = ["roundOf32", "roundOf16", "quarterFinals", "semiFinals"]
    round_counts = [8, 4, 2, 1]
    
    for r_idx, r_name in enumerate(round_names):
        matches = []
        next_teams = []
        for i in range(round_counts[r_idx]):
            t1 = current_teams[i*2]
            t2 = current_teams[i*2+1]
            match_id = f"{prefix}_{r_name}_{i}"
            m, w = simulate_match(t1, t2, match_id)
            matches.append(m)
            next_teams.append(w)
        rounds[r_name] = matches
        current_teams = next_teams
        
    return rounds, current_teams[0]

left_rounds, left_finalist = run_bracket_side(left_t, "L")
right_rounds, right_finalist = run_bracket_side(right_t, "R")

final_match, winner = simulate_match(left_finalist, right_finalist, "F_1")

data = {
    "left": left_rounds,
    "right": right_rounds,
    "final": final_match
}

with open("data.json", "w") as f:
    json.dump(data, f, indent=2)
