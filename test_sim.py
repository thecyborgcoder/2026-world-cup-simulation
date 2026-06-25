"""
test_sim.py

This script runs a highly detailed, single-pass simulation of the 2026 World Cup.
Unlike the main simulation (which runs silently 100,000+ times across multiple CPU cores), 
this script is designed for manual diagnostic testing and evaluation.

It "unrolls" the main simulation loop to intercept data at every step, allowing it to:
1. Print the expected Win/Draw/Loss probabilities for every single match.
2. Log the exact scorelines and advancing teams.
3. Build and display visual text diagrams of the final Group Stage standings.
4. Track and print the entire Knockout Bracket progression from R32 to the Final.
5. Output final tournament metrics (e.g., average goals, draw %, avg goals by winners).

Crucially, it imports and utilizes the exact same core engine, Elo calculations, 
and tiebreaker logic as the full simulation to ensure perfect 1:1 accuracy.
"""

import json
import math
import os
from elo_fetcher import fetch_elo_ratings
from simulator import get_location_for_match, simulate_match, get_standings, build_knockout_bracket
from probabilities import get_expected_goals, nbinom_prob

# Buffer for markdown output
report_lines = []

def log(text):
    print(text)
    report_lines.append(text)

def get_match_probabilities(elo_a, elo_b, rho=-0.10):
    xg_a, xg_b = get_expected_goals(elo_a, elo_b)
    prob_w, prob_d, prob_l = 0.0, 0.0, 0.0
    
    for i in range(11):
        for j in range(11):
            p = nbinom_prob(xg_a, 5.0, i) * nbinom_prob(xg_b, 5.0, j)
            if rho != 0:
                if i == 0 and j == 0: p *= max(0, 1 - xg_a * xg_b * rho)
                elif i == 0 and j == 1: p *= max(0, 1 + xg_a * rho)
                elif i == 1 and j == 0: p *= max(0, 1 + xg_b * rho)
                elif i == 1 and j == 1: p *= max(0, 1 - rho)
                
            if i > j: prob_w += p
            elif i == j: prob_d += p
            else: prob_l += p
            
    return prob_w, prob_d, prob_l

def main():
    log("# 2026 World Cup Detailed Simulation Test Report\n")
    print("Loading data...")
    with open('teams.json', 'r') as f:
        teams = json.load(f)
    with open('matches.json', 'r') as f:
        matches = json.load(f)
        
    ratings = fetch_elo_ratings(cache_hours=24)
    hosts = ['United States', 'Canada', 'Mexico']
    
    all_simulated_matches = []
    groups_standings = {}
    group_stats = {}
    
    log("## Group Stage Matches (Simulated Remaining)\n")
    
    for group_name, group_teams in teams.items():
        # Determine location just for display/API compatibility, bonus is flat now
        if group_name == 'A': loc = 'Mexico'
        elif group_name == 'B': loc = 'Canada'
        else: loc = 'USA'
        
        group_m = [m for m in matches if m['team_a'] in group_teams and m['team_b'] in group_teams]
        played_pairs = {tuple(sorted([m['team_a'], m['team_b']])) for m in group_m}
        
        for i in range(len(group_teams)):
            for j in range(i + 1, len(group_teams)):
                ta, tb = group_teams[i], group_teams[j]
                if tuple(sorted([ta, tb])) not in played_pairs:
                    elo_a, elo_b = ratings.get(ta, 1500), ratings.get(tb, 1500)
                    adj_elo_a = elo_a + 100 if ta in hosts else elo_a
                    adj_elo_b = elo_b + 100 if tb in hosts else elo_b
                    
                    pw, pd, pl = get_match_probabilities(adj_elo_a, adj_elo_b)
                    ga, gb = simulate_match(ta, tb, elo_a, elo_b, location=loc, is_knockout=False)
                    
                    log(f"**[{group_name}] {ta} vs {tb} @ {loc}**")
                    log(f"   Win Probs: {ta} {pw*100:.1f}% | Draw {pd*100:.1f}% | {tb} {pl*100:.1f}%")
                    log(f"   Result: **{ta} {ga} - {gb} {tb}**\n")
                    
                    all_simulated_matches.append({'ta': ta, 'tb': tb, 'ga': ga, 'gb': gb, 'is_knockout': False, 'elo_a': adj_elo_a, 'elo_b': adj_elo_b})
                    # Add to group_m so get_standings can calculate everything correctly
                    group_m.append({'team_a': ta, 'team_b': tb, 'score_a': ga, 'score_b': gb})
                    
        standings, stats, _ = get_standings(group_name, group_teams, group_m, ratings)
        groups_standings[group_name] = standings
        group_stats[group_name] = stats
        
    log("## Final Group Stage Standings\n")
    for group_name in sorted(groups_standings.keys()):
        log(f"### Group {group_name}")
        log(f"| {'Team':<25} | {'Pts':<3} | {'GD':<3} | {'GS':<3} |")
        log(f"|{'-'*27}|{'-'*5}|{'-'*5}|{'-'*5}|")
        for t in groups_standings[group_name]:
            s = group_stats[group_name][t]
            log(f"| {t:<25} | {s['points']:<3} | {s['gd']:<3} | {s['gs']:<3} |")
        log("")
            
    log("\n## Knockout Stage Bracket\n")
    
    r32_bracket = build_knockout_bracket(groups_standings, group_stats, ratings)
    
    def run_ko_round(bracket, start_match_num, round_name):
        log(f"### {round_name.upper()}")
        next_round = []
        for i, match in enumerate(bracket):
            ta, tb = match
            match_num = start_match_num + i
            loc = get_location_for_match(match_num)
            
            elo_a, elo_b = ratings.get(ta, 1500), ratings.get(tb, 1500)
            adj_elo_a = elo_a + 100 if ta in hosts else elo_a
            adj_elo_b = elo_b + 100 if tb in hosts else elo_b
            pw, pd, pl = get_match_probabilities(adj_elo_a, adj_elo_b)
            
            winner, method, ga, gb = simulate_match(ta, tb, elo_a, elo_b, location=loc, is_knockout=True)
            
            log(f"**Match {match_num} @ {loc}: {ta} vs {tb}**")
            log(f"   90m Probs: {ta} {pw*100:.1f}% | Draw {pd*100:.1f}% | {tb} {pl*100:.1f}%")
            log(f"   Advancing: **{winner}** (via {method})\n")
            
            next_round.append(winner)
            all_simulated_matches.append({'ta': ta, 'tb': tb, 'ga': ga, 'gb': gb, 'winner': winner, 'method': method, 'is_knockout': True, 'elo_a': adj_elo_a, 'elo_b': adj_elo_b})
            
        return next_round

    r32_teams = run_ko_round(r32_bracket, 73, "Round of 32")
    
    w = {73 + i: winner for i, winner in enumerate(r32_teams)}
    r16_bracket = [
        (w[74], w[77]), (w[73], w[75]), (w[76], w[78]), (w[79], w[80]),
        (w[83], w[84]), (w[81], w[82]), (w[85], w[87]), (w[86], w[88])
    ]
    r16_teams = run_ko_round(r16_bracket, 89, "Round of 16")
    
    w16 = {89 + i: winner for i, winner in enumerate(r16_teams)}
    qf_bracket = [
        (w16[89], w16[90]), (w16[91], w16[92]), 
        (w16[93], w16[94]), (w16[95], w16[96])
    ]
    qf_teams = run_ko_round(qf_bracket, 97, "Quarter-Finals")
    
    wqf = {97 + i: winner for i, winner in enumerate(qf_teams)}
    sf_bracket = [
        (wqf[97], wqf[98]), (wqf[99], wqf[100])
    ]
    sf_teams = run_ko_round(sf_bracket, 101, "Semi-Finals")
    
    wsf = {101 + i: winner for i, winner in enumerate(sf_teams)}
    final_bracket = [(wsf[101], wsf[102])]
    final_teams = run_ko_round(final_bracket, 104, "Final")
    
    winner = final_teams[0]
    
    log("\n" + "="*50)
    log(f" TOURNAMENT WINNER: {winner.upper()} ")
    log("="*50 + "\n")
    
    log("## Simulation Diagnostics\n")
    
    total_matches = len(all_simulated_matches)
    group_matches = [m for m in all_simulated_matches if not m['is_knockout']]
    ko_matches = [m for m in all_simulated_matches if m['is_knockout']]
    
    # Group Stage Stats
    total_goals = sum(m['ga'] + m['gb'] for m in group_matches)
    avg_goals = total_goals / max(1, len(group_matches))
    
    team_a_wins = 0
    draws = 0
    team_b_wins = 0
    winner_goals = 0
    loser_goals = 0
    
    for m in group_matches:
        if m['ga'] > m['gb']:
            team_a_wins += 1
            winner_goals += m['ga']
            loser_goals += m['gb']
        elif m['ga'] < m['gb']:
            team_b_wins += 1
            winner_goals += m['gb']
            loser_goals += m['ga']
        else:
            draws += 1
            
    win_pct = (team_a_wins + team_b_wins) / len(group_matches) * 100
    draw_pct = draws / len(group_matches) * 100
    
    decisive_games = team_a_wins + team_b_wins
    avg_winner_goals = winner_goals / max(1, decisive_games) if decisive_games > 0 else 0
    avg_loser_goals = loser_goals / max(1, decisive_games) if decisive_games > 0 else 0
    
    # Knockout Stats
    rt_wins = sum(1 for m in ko_matches if m['method'] == 'RT')
    et_wins = sum(1 for m in ko_matches if m['method'] == 'ET')
    pen_wins = sum(1 for m in ko_matches if m['method'] == 'PEN')
    
    log("### Overall Data")
    log(f"- **Total Matches Simulated**: {total_matches}")
    
    log("\n### Group Stage Breakdown")
    log(f"- **Matches Simulated**: {len(group_matches)}")
    log(f"- **Total Goals Scored**: {total_goals}")
    log(f"- **Avg Goals per Match**: {avg_goals:.2f}")
    log(f"- **Matches Ending in a Draw**: {draws} ({draw_pct:.1f}%)")
    log(f"- **Matches Ending with a Winner**: {decisive_games} ({win_pct:.1f}%)")
    log(f"  - Team A Wins: {team_a_wins} ({team_a_wins/len(group_matches)*100:.1f}%)")
    log(f"  - Team B Wins: {team_b_wins} ({team_b_wins/len(group_matches)*100:.1f}%)")
    log(f"- **Avg Goals by Winning Team**: {avg_winner_goals:.2f}")
    log(f"- **Avg Goals by Losing Team**: {avg_loser_goals:.2f}")
    
    ko_total_goals = sum(m.get('ga', 0) + m.get('gb', 0) for m in ko_matches)
    ko_avg_goals = ko_total_goals / max(1, len(ko_matches))
    ko_winner_goals = sum(m['ga'] if m['winner'] == m['ta'] else m['gb'] for m in ko_matches)
    ko_loser_goals = sum(m['gb'] if m['winner'] == m['ta'] else m['ga'] for m in ko_matches)
    ko_avg_winner_goals = ko_winner_goals / max(1, len(ko_matches))
    ko_avg_loser_goals = ko_loser_goals / max(1, len(ko_matches))

    log("\n### Knockout Stage Breakdown")
    log(f"- **Total Knockout Matches**: {len(ko_matches)}")
    log(f"- **Total Goals Scored**: {ko_total_goals}")
    log(f"- **Avg Goals per Match**: {ko_avg_goals:.2f}")
    log(f"- **Avg Goals by Winning Team**: {ko_avg_winner_goals:.2f}")
    log(f"- **Avg Goals by Losing Team**: {ko_avg_loser_goals:.2f}")
    log(f"- **Won in Regular Time (90m)**: {rt_wins} ({rt_wins/len(ko_matches)*100:.1f}%)")
    log(f"- **Won in Extra Time (120m)**: {et_wins} ({et_wins/max(1,len(ko_matches))*100:.1f}%)")
    log(f"- **Decided by Penalty Shootout**: {pen_wins} ({pen_wins/max(1,len(ko_matches))*100:.1f}%)")
    
    # Elo Difference Breakdown
    elo_diff_stats = {
        '0-50': {'games': 0, 'favorite_wins': 0, 'underdog_wins': 0, 'draws': 0},
        '51-150': {'games': 0, 'favorite_wins': 0, 'underdog_wins': 0, 'draws': 0},
        '151-300': {'games': 0, 'favorite_wins': 0, 'underdog_wins': 0, 'draws': 0},
        '300+': {'games': 0, 'favorite_wins': 0, 'underdog_wins': 0, 'draws': 0}
    }
    
    elo_tier_stats = {
        '1900+': {'w': 0, 'd': 0, 'l': 0, 'games': 0},
        '1800-1899': {'w': 0, 'd': 0, 'l': 0, 'games': 0},
        '1700-1799': {'w': 0, 'd': 0, 'l': 0, 'games': 0},
        '1600-1699': {'w': 0, 'd': 0, 'l': 0, 'games': 0},
        '<1600': {'w': 0, 'd': 0, 'l': 0, 'games': 0}
    }
    
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

    for m in all_simulated_matches:
        ea, eb = m['elo_a'], m['elo_b']
        diff = abs(ea - eb)
        bucket = get_diff_bucket(diff)
        
        winner = None
        if not m['is_knockout']:
            if m['ga'] > m['gb']: winner = 'a'
            elif m['ga'] < m['gb']: winner = 'b'
            else: winner = 'draw'
        else:
            winner = 'a' if m['winner'] == m['ta'] else 'b'
            
        elo_diff_stats[bucket]['games'] += 1
        is_a_favorite = ea >= eb
        
        if winner == 'draw':
            elo_diff_stats[bucket]['draws'] += 1
        elif winner == 'a':
            if is_a_favorite: elo_diff_stats[bucket]['favorite_wins'] += 1
            else: elo_diff_stats[bucket]['underdog_wins'] += 1
        else:
            if not is_a_favorite: elo_diff_stats[bucket]['favorite_wins'] += 1
            else: elo_diff_stats[bucket]['underdog_wins'] += 1
            
        t_a = get_tier(ea)
        t_b = get_tier(eb)
        elo_tier_stats[t_a]['games'] += 1
        elo_tier_stats[t_b]['games'] += 1
        
        if winner == 'draw':
            elo_tier_stats[t_a]['d'] += 1
            elo_tier_stats[t_b]['d'] += 1
        elif winner == 'a':
            elo_tier_stats[t_a]['w'] += 1
            elo_tier_stats[t_b]['l'] += 1
        else:
            elo_tier_stats[t_a]['l'] += 1
            elo_tier_stats[t_b]['w'] += 1
            
    log("\n### Match Outcomes by Elo Difference")
    log(f"| {'Elo Diff':<10} | {'Games':<5} | {'Fav Win%':<9} | {'Dog Win%':<9} | {'Draw%':<6} |")
    log(f"|{'-'*12}|{'-'*7}|{'-'*11}|{'-'*11}|{'-'*8}|")
    for b in ['0-50', '51-150', '151-300', '300+']:
        st = elo_diff_stats[b]
        if st['games'] > 0:
            g = st['games']
            log(f"| {b:<10} | {g:<5} | {st['favorite_wins']/g*100:<9.1f} | {st['underdog_wins']/g*100:<9.1f} | {st['draws']/g*100:<6.1f} |")
        
    log("\n### Team Performance by Elo Tier")
    log(f"| {'Elo Tier':<10} | {'Games':<5} | {'Win%':<6} | {'Draw%':<6} | {'Loss%':<6} |")
    log(f"|{'-'*12}|{'-'*7}|{'-'*8}|{'-'*8}|{'-'*8}|")
    for t in ['1900+', '1800-1899', '1700-1799', '1600-1699', '<1600']:
        st = elo_tier_stats[t]
        if st['games'] > 0:
            g = st['games']
            log(f"| {t:<10} | {g:<5} | {st['w']/g*100:<6.1f} | {st['d']/g*100:<6.1f} | {st['l']/g*100:<6.1f} |")
    
    # Write to file
    os.makedirs('outputs', exist_ok=True)
    with open('outputs/test_sim_report.md', 'w', encoding='utf-8') as f:
        f.write('\n'.join(report_lines))
        
    print("\n[INFO] Complete report saved to outputs/test_sim_report.md")

if __name__ == '__main__':
    main()
