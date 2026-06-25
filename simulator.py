import random
from probabilities import generate_random_score

def get_location_for_group(group_name):
    if group_name == 'A': return 'Mexico'
    if group_name == 'B': return 'Canada'
    return 'USA'

MATCH_LOCATIONS = {
    73: 'USA', 74: 'USA', 75: 'Mexico', 76: 'USA', 77: 'USA', 78: 'USA', 79: 'Mexico', 80: 'USA',
    81: 'USA', 82: 'USA', 83: 'Canada', 84: 'USA', 85: 'Canada', 86: 'USA', 87: 'USA', 88: 'USA',
    89: 'USA', 90: 'USA', 91: 'USA', 92: 'Mexico', 93: 'USA', 94: 'USA', 95: 'USA', 96: 'Canada',
    97: 'USA', 98: 'USA', 99: 'USA', 100: 'USA',
    101: 'USA', 102: 'USA',
    103: 'USA', 
    104: 'USA'
}

def get_location_for_match(match_number):
    return MATCH_LOCATIONS.get(match_number, 'USA')

def get_adjusted_elo(team, elo, match_num=None):
    if match_num is None or match_num <= 96:
        if team in ['United States', 'Canada', 'Mexico']:
            return elo + 100
    else:
        if team == 'United States':
            return elo + 100
        elif team in ['Canada', 'Mexico']:
            return elo + 30
    return elo

def simulate_match(team_a, team_b, elo_a, elo_b, location='USA', is_knockout=False):
    # Note: elo_a and elo_b should already be adjusted before calling this function


    goals_a, goals_b = generate_random_score(elo_a, elo_b, is_knockout=is_knockout)
    
    if is_knockout:
        if goals_a > goals_b: return team_a, 'RT', goals_a, goals_b
        elif goals_b > goals_a: return team_b, 'RT', goals_a, goals_b
        else:
            # Extra Time
            et_goals_a, et_goals_b = generate_random_score(elo_a, elo_b, scale=0.15, is_knockout=is_knockout)
            tot_a = goals_a + et_goals_a
            tot_b = goals_b + et_goals_b
            if tot_a > tot_b: return team_a, 'ET', tot_a, tot_b
            elif tot_b > tot_a: return team_b, 'ET', tot_a, tot_b
            else:
                # Penalties: 50/50 flip
                return (team_a, 'PEN', tot_a, tot_b) if random.random() < 0.5 else (team_b, 'PEN', tot_a, tot_b)
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
        if random.random() < 0.5:
            ta, tb = tb, ta
            sa, sb = sb, sa
        if ta in stats and tb in stats:
            stats[ta]['gs'] += sa
            stats[tb]['gs'] += sb
            stats[ta]['gd'] += (sa - sb)
            stats[tb]['gd'] += (sb - sa)
            elo_a, elo_b = ratings.get(ta, 1500), ratings.get(tb, 1500)
            adj_elo_a = get_adjusted_elo(ta, elo_a)
            adj_elo_b = get_adjusted_elo(tb, elo_b)

            if sa > sb: stats[ta]['points'] += 3
            elif sa == sb:
                stats[ta]['points'] += 1
                stats[tb]['points'] += 1
            else: stats[tb]['points'] += 3
            stats[ta]['matches'] += 1
            stats[tb]['matches'] += 1
            played_pairs.add(tuple(sorted([ta, tb])))
            match_results.append({'ta': ta, 'tb': tb, 'sa': sa, 'sb': sb, 'is_knockout': False, 'elo_a': adj_elo_a, 'elo_b': adj_elo_b})
            
    # Simulate remaining matches
    location = get_location_for_group(group_name)
    shuffled_teams = list(group_teams)
    random.shuffle(shuffled_teams)
    for i in range(len(shuffled_teams)):
        for j in range(i + 1, len(shuffled_teams)):
            ta, tb = shuffled_teams[i], shuffled_teams[j]
            if random.random() < 0.5:
                ta, tb = tb, ta
            if tuple(sorted([ta, tb])) not in played_pairs:
                elo_a, elo_b = ratings.get(ta, 1500), ratings.get(tb, 1500)
                adj_elo_a = get_adjusted_elo(ta, elo_a)
                adj_elo_b = get_adjusted_elo(tb, elo_b)
                
                ga, gb = simulate_match(ta, tb, adj_elo_a, adj_elo_b, location=location)
                stats[ta]['gd'] += (ga - gb)
                stats[tb]['gd'] += (gb - ga)
                stats[ta]['gs'] += ga
                stats[tb]['gs'] += gb
                
                if ga > gb: stats[ta]['points'] += 3
                elif ga == gb: 
                    stats[ta]['points'] += 1
                    stats[tb]['points'] += 1
                else: stats[tb]['points'] += 3
                
                match_results.append({'ta': ta, 'tb': tb, 'sa': ga, 'sb': gb, 'is_knockout': False, 'elo_a': adj_elo_a, 'elo_b': adj_elo_b})
                
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
            lambda ts: {t: stats[t]['gd'] for t in ts},         # 2. Overall GD
            lambda ts: {t: stats[t]['gs'] for t in ts},         # 3. Overall GS
            get_h2h_pts,                                        # 4. H2H Points
            get_h2h_gd,                                         # 5. H2H GD
            get_h2h_gs,                                         # 6. H2H GS
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
    return sorted_teams, stats, match_results

def assign_3rd_place(best_thirds):
    slots = [74, 77, 79, 80, 81, 82, 85, 87]
    allowed_groups = {
        74: ['A','B','C','D','F'],
        77: ['C','D','F','G','H'],
        79: ['C','E','F','H','I'],
        80: ['E','H','I','J','K'],
        81: ['B','E','F','I','J'],
        82: ['A','E','H','I','J'],
        85: ['E','F','G','I','J'],
        87: ['D','E','I','J','L']
    }
    
    # Sort groups to be deterministic
    t3_groups = sorted([x['group'] for x in best_thirds])
    
    def solve(idx, current_assignment):
        if idx == 8:
            return current_assignment
        slot = slots[idx]
        for group in t3_groups:
            if group not in current_assignment.values() and group in allowed_groups[slot]:
                current_assignment[slot] = group
                res = solve(idx + 1, current_assignment)
                if res: return res
                del current_assignment[slot]
        return None
        
    assignment = solve(0, {})
    
    # Fallback just in case no valid matrix exists (shouldn't happen, but just to be safe)
    if not assignment:
        assignment = {s: t3_groups[i] for i, s in enumerate(slots)}
        
    # Map back to team names
    group_to_team = {x['group']: x['team'] for x in best_thirds}
    return {slot: group_to_team[group] for slot, group in assignment.items()}

def build_knockout_bracket(groups_standings, group_stats, ratings):
    firsts = {g: standings[0] for g, standings in groups_standings.items()}
    seconds = {g: standings[1] for g, standings in groups_standings.items()}
    
    thirds = []
    for g, standings in groups_standings.items():
        t3 = standings[2]
        thirds.append({'group': g, 'team': t3, 'points': group_stats[g][t3]['points'], 'gd': group_stats[g][t3]['gd'], 'gs': group_stats[g][t3]['gs']})
        
    thirds.sort(key=lambda x: (x['points'], x['gd'], x['gs'], ratings.get(x['team'], 1500)), reverse=True)
    best_thirds = thirds[:8]
    
    r32 = {}
    # Runners-up vs Runners-up
    r32[73] = (seconds['A'], seconds['B'])
    r32[78] = (seconds['E'], seconds['I'])
    r32[83] = (seconds['K'], seconds['L'])
    r32[88] = (seconds['D'], seconds['G'])
    
    # Winners vs Runners-up
    r32[75] = (firsts['F'], seconds['C'])
    r32[76] = (firsts['C'], seconds['F'])
    r32[84] = (firsts['H'], seconds['J'])
    r32[86] = (firsts['J'], seconds['H'])
    
    # Winners vs 3rd place
    t3_assignment = assign_3rd_place(best_thirds)
    r32[74] = (firsts['E'], t3_assignment[74])
    r32[77] = (firsts['I'], t3_assignment[77])
    r32[79] = (firsts['A'], t3_assignment[79])
    r32[80] = (firsts['L'], t3_assignment[80])
    r32[81] = (firsts['D'], t3_assignment[81])
    r32[82] = (firsts['G'], t3_assignment[82])
    r32[85] = (firsts['B'], t3_assignment[85])
    r32[87] = (firsts['K'], t3_assignment[87])
    
    return [r32[i] for i in range(73, 89)]

def simulate_knockout(bracket, ratings, start_match_num):
    next_round = []
    match_data = []
    for i, match in enumerate(bracket):
        ta, tb = match
        if random.random() < 0.5:
            ta, tb = tb, ta
        match_num = start_match_num + i
        loc = get_location_for_match(match_num)
        elo_a, elo_b = ratings.get(ta, 1500), ratings.get(tb, 1500)
        adj_elo_a = get_adjusted_elo(ta, elo_a, match_num)
        adj_elo_b = get_adjusted_elo(tb, elo_b, match_num)
        
        winner, method, ga, gb = simulate_match(ta, tb, adj_elo_a, adj_elo_b, location=loc, is_knockout=True)
        next_round.append(winner)
        match_data.append({'ta': ta, 'tb': tb, 'winner': winner, 'method': method, 'is_knockout': True, 'elo_a': adj_elo_a, 'elo_b': adj_elo_b, 'sa': ga, 'sb': gb})
    return next_round, match_data

def run_one_simulation(teams, matches_played, ratings):
    groups_standings = {}
    group_stats = {}
    all_matches = []
    
    for group_name, group_teams in teams.items():
        group_m = [m for m in matches_played if m['team_a'] in group_teams and m['team_b'] in group_teams]
        standings, stats, match_results = get_standings(group_name, group_teams, group_m, ratings)
        groups_standings[group_name] = standings
        group_stats[group_name] = stats
        all_matches.extend(match_results)
        
    r32_bracket = build_knockout_bracket(groups_standings, group_stats, ratings)
    r32_teams, r32_data = simulate_knockout(r32_bracket, ratings, 73)
    all_matches.extend(r32_data)
    
    # R16 Mapping
    w = {73 + i: winner for i, winner in enumerate(r32_teams)}
    r16_bracket = [
        (w[74], w[77]), (w[73], w[75]), (w[76], w[78]), (w[79], w[80]),
        (w[83], w[84]), (w[81], w[82]), (w[85], w[87]), (w[86], w[88])
    ]
    r16_teams, r16_data = simulate_knockout(r16_bracket, ratings, 89)
    all_matches.extend(r16_data)
    
    # QF Mapping
    w16 = {89 + i: winner for i, winner in enumerate(r16_teams)}
    qf_bracket = [
        (w16[89], w16[90]), (w16[91], w16[92]), 
        (w16[93], w16[94]), (w16[95], w16[96])
    ]
    qf_teams, qf_data = simulate_knockout(qf_bracket, ratings, 97)
    all_matches.extend(qf_data)
    
    # SF Mapping
    wqf = {97 + i: winner for i, winner in enumerate(qf_teams)}
    sf_bracket = [
        (wqf[97], wqf[98]), (wqf[99], wqf[100])
    ]
    sf_teams, sf_data = simulate_knockout(sf_bracket, ratings, 101)
    all_matches.extend(sf_data)
    
    # Final & 3rd Place Match
    wsf = {101 + i: winner for i, winner in enumerate(sf_teams)}
    lsf = {101 + i: sf_bracket[i][0] if winner == sf_bracket[i][1] else sf_bracket[i][1] for i, winner in enumerate(sf_teams)}
    
    third_place_bracket = [(lsf[101], lsf[102])]
    third_place_teams, third_place_data = simulate_knockout(third_place_bracket, ratings, 103)
    all_matches.extend(third_place_data)
    
    final_bracket = [(wsf[101], wsf[102])]
    final_teams, final_data = simulate_knockout(final_bracket, ratings, 104)
    all_matches.extend(final_data)
    
    def get_tier(elo):
        if elo >= 1900: return '1900+'
        if elo >= 1800: return '1800-1899'
        if elo >= 1700: return '1700-1799'
        if elo >= 1600: return '1600-1699'
        return '<1600'
        
    def get_diff_bucket(diff):
        if diff <= 50: return '0-50'
        if diff <= 150: return '51-150'
        if diff <= 300: return '151-300'
        return '300+'

    run_stats = {
        'group_games': 0, 'group_goals': 0, 'group_draws': 0, 'team_a_wins': 0, 'team_b_wins': 0,
        'winner_goals': 0, 'loser_goals': 0,
        'ko_games': 0, 'ko_goals': 0, 'ko_winner_goals': 0, 'ko_loser_goals': 0, 'rt_wins': 0, 'et_wins': 0, 'pen_wins': 0,
        'elo_diff': {
            '0-50': {'games': 0, 'favorite_wins': 0, 'underdog_wins': 0, 'draws': 0},
            '51-150': {'games': 0, 'favorite_wins': 0, 'underdog_wins': 0, 'draws': 0},
            '151-300': {'games': 0, 'favorite_wins': 0, 'underdog_wins': 0, 'draws': 0},
            '300+': {'games': 0, 'favorite_wins': 0, 'underdog_wins': 0, 'draws': 0}
        },
        'elo_tier': {
            '1900+': {'w': 0, 'd': 0, 'l': 0, 'games': 0},
            '1800-1899': {'w': 0, 'd': 0, 'l': 0, 'games': 0},
            '1700-1799': {'w': 0, 'd': 0, 'l': 0, 'games': 0},
            '1600-1699': {'w': 0, 'd': 0, 'l': 0, 'games': 0},
            '<1600': {'w': 0, 'd': 0, 'l': 0, 'games': 0}
        }
    }

    for m in all_matches:
        ea, eb = m['elo_a'], m['elo_b']
        diff = abs(ea - eb)
        bucket = get_diff_bucket(diff)
        
        winner = None
        if m['sa'] > m['sb']:
            winner = 'a'
        elif m['sa'] < m['sb']:
            winner = 'b'
        else:
            winner = 'draw'
            
        if not m['is_knockout']:
            run_stats['group_games'] += 1
            run_stats['group_goals'] += (m['sa'] + m['sb'])
            if winner == 'a': 
                run_stats['team_a_wins'] += 1
                run_stats['winner_goals'] += m['sa']
                run_stats['loser_goals'] += m['sb']
            elif winner == 'b': 
                run_stats['team_b_wins'] += 1
                run_stats['winner_goals'] += m['sb']
                run_stats['loser_goals'] += m['sa']
            else: 
                run_stats['group_draws'] += 1
        else:
            run_stats['ko_games'] += 1
            run_stats['ko_goals'] += (m['sa'] + m['sb'])
            if m['method'] == 'RT': run_stats['rt_wins'] += 1
            elif m['method'] == 'ET': run_stats['et_wins'] += 1
            elif m['method'] == 'PEN': run_stats['pen_wins'] += 1
            
            advancing_winner = 'a' if m['winner'] == m['ta'] else 'b'
            if advancing_winner == 'a':
                run_stats['ko_winner_goals'] += m['sa']
                run_stats['ko_loser_goals'] += m['sb']
            else:
                run_stats['ko_winner_goals'] += m['sb']
                run_stats['ko_loser_goals'] += m['sa']
            
        run_stats['elo_diff'][bucket]['games'] += 1
        is_a_favorite = ea >= eb
        
        if winner == 'draw':
            run_stats['elo_diff'][bucket]['draws'] += 1
        elif winner == 'a':
            if is_a_favorite: run_stats['elo_diff'][bucket]['favorite_wins'] += 1
            else: run_stats['elo_diff'][bucket]['underdog_wins'] += 1
        else:
            if not is_a_favorite: run_stats['elo_diff'][bucket]['favorite_wins'] += 1
            else: run_stats['elo_diff'][bucket]['underdog_wins'] += 1
            
        if not m['is_knockout']:
            t_a = get_tier(ea)
            t_b = get_tier(eb)
            run_stats['elo_tier'][t_a]['games'] += 1
            run_stats['elo_tier'][t_b]['games'] += 1
            
            if winner == 'draw':
                run_stats['elo_tier'][t_a]['d'] += 1
                run_stats['elo_tier'][t_b]['d'] += 1
            elif winner == 'a':
                run_stats['elo_tier'][t_a]['w'] += 1
                run_stats['elo_tier'][t_b]['l'] += 1
            else:
                run_stats['elo_tier'][t_a]['l'] += 1
                run_stats['elo_tier'][t_b]['w'] += 1
    
    return {
        'r32': [team for match in r32_bracket for team in match],
        'r16': r32_teams,
        'qf': r16_teams,
        'sf': qf_teams,
        'final': sf_teams,
        'winner': final_teams[0],
        'r32_bracket': r32_bracket,
        'r16_bracket': r16_bracket,
        'qf_bracket': qf_bracket,
        'sf_bracket': sf_bracket,
        'final_bracket': final_bracket,
        'run_stats': run_stats
    }
