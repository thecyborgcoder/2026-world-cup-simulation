import random
from probabilities import generate_random_score

def get_location_for_group(group_name):
    if group_name == 'A': return 'Mexico'
    if group_name == 'B': return 'Canada'
    return 'USA'

def get_location_for_knockout(team_a, team_b, round_name):
    if round_name in ['r32', 'r16']:
        if 'Canada' in [team_a, team_b]: return 'Canada'
        if 'Mexico' in [team_a, team_b]: return 'Mexico'
    return 'USA'

def simulate_match(team_a, team_b, elo_a, elo_b, location='USA', is_knockout=False):
    # Apply bonus only if playing in home country
    if team_a == 'United States' and location == 'USA': elo_a += 100
    if team_a == 'Canada' and location == 'Canada': elo_a += 100
    if team_a == 'Mexico' and location == 'Mexico': elo_a += 100

    if team_b == 'United States' and location == 'USA': elo_b += 100
    if team_b == 'Canada' and location == 'Canada': elo_b += 100
    if team_b == 'Mexico' and location == 'Mexico': elo_b += 100

    goals_a, goals_b = generate_random_score(elo_a, elo_b)
    
    if is_knockout:
        if goals_a > goals_b: return team_a
        elif goals_b > goals_a: return team_b
        else:
            # Extra Time
            et_goals_a, et_goals_b = generate_random_score(elo_a, elo_b, scale=0.3333)
            if et_goals_a > et_goals_b: return team_a
            elif et_goals_b > et_goals_a: return team_b
            else:
                # Penalties: 50/50 flip
                return team_a if random.random() < 0.5 else team_b
    else:
        return goals_a, goals_b

def get_standings(group_name, group_teams, group_matches, ratings):
    stats = {t: {'points': 0, 'gd': 0, 'gs': 0, 'matches': 0} for t in group_teams}
    played_pairs = set()
    match_results = []
    
    # Apply historical matches if any
    for m in group_matches:
        ta, tb = m['team_a'], m['team_b']
        sa, sb = m['score_a'], m['score_b']
        if ta in stats and tb in stats:
            stats[ta]['gs'] += sa
            stats[tb]['gs'] += sb
            stats[ta]['gd'] += (sa - sb)
            stats[tb]['gd'] += (sb - sa)
            if sa > sb: stats[ta]['points'] += 3
            elif sa == sb:
                stats[ta]['points'] += 1
                stats[tb]['points'] += 1
            else: stats[tb]['points'] += 3
            stats[ta]['matches'] += 1
            stats[tb]['matches'] += 1
            played_pairs.add(tuple(sorted([ta, tb])))
            match_results.append({'ta': ta, 'tb': tb, 'sa': sa, 'sb': sb})
            
    # Simulate remaining matches
    location = get_location_for_group(group_name)
    for i in range(len(group_teams)):
        for j in range(i + 1, len(group_teams)):
            ta, tb = group_teams[i], group_teams[j]
            if tuple(sorted([ta, tb])) not in played_pairs:
                ga, gb = simulate_match(ta, tb, ratings.get(ta, 1500), ratings.get(tb, 1500), location=location)
                stats[ta]['gd'] += (ga - gb)
                stats[tb]['gd'] += (gb - ga)
                stats[ta]['gs'] += ga
                stats[tb]['gs'] += gb
                
                if ga > gb: stats[ta]['points'] += 3
                elif ga == gb: 
                    stats[ta]['points'] += 1
                    stats[tb]['points'] += 1
                else: stats[tb]['points'] += 3
                
                match_results.append({'ta': ta, 'tb': tb, 'sa': ga, 'sb': gb})
                
    # Multi-pass recursive tiebreaker function
    def sort_tied_teams(teams):
        if len(teams) <= 1: return teams
        
        def get_h2h_pts(ts):
            sc = {t: 0 for t in ts}
            for m in match_results:
                if m['ta'] in ts and m['tb'] in ts:
                    if m['sa'] > m['sb']: sc[m['ta']] += 3
                    elif m['sa'] == m['sb']: sc[m['ta']] += 1; sc[m['tb']] += 1
                    else: sc[m['tb']] += 3
            return sc

        def get_h2h_gd(ts):
            sc = {t: 0 for t in ts}
            for m in match_results:
                if m['ta'] in ts and m['tb'] in ts:
                    sc[m['ta']] += (m['sa'] - m['sb'])
                    sc[m['tb']] += (m['sb'] - m['sa'])
            return sc

        def get_h2h_gs(ts):
            sc = {t: 0 for t in ts}
            for m in match_results:
                if m['ta'] in ts and m['tb'] in ts:
                    sc[m['ta']] += m['sa']
                    sc[m['tb']] += m['sb']
            return sc
            
        criteria_funcs = [
            lambda ts: {t: stats[t]['points'] for t in ts},     # 1. Total Points
            get_h2h_pts,                                        # 2. H2H Points
            get_h2h_gd,                                         # 3. H2H GD
            get_h2h_gs,                                         # 4. H2H GS
            lambda ts: {t: stats[t]['gd'] for t in ts},         # 5. Overall GD
            lambda ts: {t: stats[t]['gs'] for t in ts},         # 6. Overall GS
            lambda ts: {t: ratings.get(t, 1500) for t in ts},   # 7. FIFA Ranking (Elo)
            lambda ts: {t: t for t in ts}                       # 8. Name (Fallback)
        ]
        
        for idx, func in enumerate(criteria_funcs):
            scores = func(teams)
            unique_scores = set(scores.values())
            if len(unique_scores) > 1:
                from collections import defaultdict
                grouped = defaultdict(list)
                for t in teams:
                    grouped[scores[t]].append(t)
                    
                is_reverse = (idx != 7) # Sort descending for all except Name
                sorted_scores = sorted(unique_scores, reverse=is_reverse)
                
                result = []
                for s in sorted_scores:
                    result.extend(sort_tied_teams(grouped[s]))
                return result
                
        return teams

    sorted_teams = sort_tied_teams(group_teams)
    return sorted_teams, stats

def build_knockout_bracket(groups_standings, group_stats, ratings):
    winners = []
    runners_up = []
    thirds = []
    for g, standings in groups_standings.items():
        winners.append((g, standings[0]))
        runners_up.append((g, standings[1]))
        t3 = standings[2]
        thirds.append({'group': g, 'team': t3, 'points': group_stats[g][t3]['points'], 'gd': group_stats[g][t3]['gd'], 'gs': group_stats[g][t3]['gs']})
        
    # Third-place ranking logic: Total Points, Overall GD, Overall GS, Elo Rating
    thirds.sort(key=lambda x: (x['points'], x['gd'], x['gs'], ratings.get(x['team'], 1500)), reverse=True)
    best_thirds = thirds[:8]
    
    r32_matches = []
    
    # 8 group winners face 8 best thirds
    w8_groups = [g for g, t in winners[:8]]
    w8_teams = [t for g, t in winners[:8]]
    t3_groups = [x['group'] for x in best_thirds]
    t3_teams = [x['team'] for x in best_thirds]
    
    # Dynamic matrix to avoid teams from same group playing each other
    def solve_assignment(w_g, t_g, current):
        if len(current) == 8: return current
        i = len(current)
        for j in range(8):
            if j not in [idx for idx, _ in current]:
                if t_g[j] != w_g[i]: # Group constraint
                    res = solve_assignment(w_g, t_g, current + [(j, t3_teams[j])])
                    if res: return res
        return None
        
    assignment = solve_assignment(w8_groups, t3_groups, [])
    if not assignment:
        assignment = [(i, t3_teams[i]) for i in range(8)] # Fallback if no valid matrix found
        
    for i in range(8):
        r32_matches.append((w8_teams[i], assignment[i][1]))
        
    # The remaining 4 winners face 4 runners-up
    r32_matches.append((winners[8][1], runners_up[0][1]))
    r32_matches.append((winners[9][1], runners_up[1][1]))
    r32_matches.append((winners[10][1], runners_up[2][1]))
    r32_matches.append((winners[11][1], runners_up[3][1]))
    
    # The remaining 8 runners-up face each other
    r32_matches.append((runners_up[4][1], runners_up[5][1]))
    r32_matches.append((runners_up[6][1], runners_up[7][1]))
    r32_matches.append((runners_up[8][1], runners_up[9][1]))
    r32_matches.append((runners_up[10][1], runners_up[11][1]))
    
    return r32_matches

def simulate_knockout(bracket, ratings, round_name):
    next_round = []
    for match in bracket:
        ta, tb = match
        loc = get_location_for_knockout(ta, tb, round_name)
        winner = simulate_match(ta, tb, ratings.get(ta, 1500), ratings.get(tb, 1500), location=loc, is_knockout=True)
        next_round.append(winner)
    
    new_bracket = []
    for i in range(0, len(next_round), 2):
        if i + 1 < len(next_round):
            new_bracket.append((next_round[i], next_round[i+1]))
            
    return next_round, new_bracket

def run_one_simulation(teams, matches_played, ratings):
    groups_standings = {}
    group_stats = {}
    
    for group_name, group_teams in teams.items():
        group_m = [m for m in matches_played if m['team_a'] in group_teams and m['team_b'] in group_teams]
        standings, stats = get_standings(group_name, group_teams, group_m, ratings)
        groups_standings[group_name] = standings
        group_stats[group_name] = stats
        
    r32_bracket = build_knockout_bracket(groups_standings, group_stats, ratings)
    
    r16_teams, r16_bracket = simulate_knockout(r32_bracket, ratings, 'r32')
    qf_teams, qf_bracket = simulate_knockout(r16_bracket, ratings, 'r16')
    sf_teams, sf_bracket = simulate_knockout(qf_bracket, ratings, 'qf')
    final_teams, final_bracket = simulate_knockout(sf_bracket, ratings, 'sf')
    winner, _ = simulate_knockout(final_bracket, ratings, 'final')
    
    return {
        'r32': [team for match in r32_bracket for team in match],
        'r16': r16_teams,
        'qf': qf_teams,
        'sf': sf_teams,
        'final': final_teams,
        'winner': winner[0]
    }
