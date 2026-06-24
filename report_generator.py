import csv
import json
import os

def generate_reports(results_tally, matchups_tally, global_run_stats, num_sims, output_dir):
    os.makedirs(output_dir, exist_ok=True)
    
    # Calculate percentages
    for team, stats in results_tally.items():
        for key in stats:
            stats[key] = (stats[key] / num_sims) * 100.0
            
    # Sort teams by win probability
    sorted_teams = sorted(results_tally.items(), key=lambda x: x[1].get('winner', 0), reverse=True)
    
    def format_prob(prob):
        if prob >= 99.999:
            return ">99.9%"
        if prob <= 0.001:
            return "<0.1%"
        if prob >= 99.95:
            return ">99.9%"
        if prob <= 0.05:
            return "<0.1%"
        return f"{prob:.1f}%"

    # Generate MD
    md_path = os.path.join(output_dir, 'simulation_report.md')
    with open(md_path, 'w', encoding='utf-8') as f:
        f.write("# 2026 World Cup Simulation Results\n\n")
        f.write(f"**Total Simulations:** {num_sims}\n\n")
        f.write("> **Note on Probabilities:** A value of `>99.9%` indicates the team advanced in virtually every Monte Carlo simulation run, but may not have officially mathematically clinched a spot yet.\n\n")
        f.write("| Team | R32 % | R16 % | QF % | SF % | Final % | Win % |\n")
        f.write("|---|---|---|---|---|---|---|\n")
        for team, stats in sorted_teams:
            r32 = format_prob(stats.get('r32', 0))
            r16 = format_prob(stats.get('r16', 0))
            qf = format_prob(stats.get('qf', 0))
            sf = format_prob(stats.get('sf', 0))
            final = format_prob(stats.get('final', 0))
            win = format_prob(stats.get('winner', 0))
            f.write(f"| {team} | {r32} | {r16} | {qf} | {sf} | {final} | {win} |\n")
            
    # Generate Bracket Matchups MD
    matchups_md_path = os.path.join(output_dir, 'bracket_matchups.md')
    with open(matchups_md_path, 'w', encoding='utf-8') as f:
        f.write("# 2026 World Cup Most Likely Matchups\n\n")
        f.write(f"**Based on {num_sims} simulations**\n\n")
        
        stages = [
            ('Final', 'final'),
            ('Semi-Finals', 'sf'),
            ('Quarter-Finals', 'qf'),
            ('Round of 16', 'r16'),
            ('Round of 32', 'r32')
        ]
        
        for stage_name, stage_key in stages:
            f.write(f"## {stage_name}\n\n")
            f.write("| Matchup | Probability | Team A Win % | Team B Win % |\n")
            f.write("|---|---|---|---|\n")
            
            # Sort matchups by frequency
            stage_matchups = matchups_tally[stage_key]
            sorted_matchups = sorted(stage_matchups.items(), key=lambda x: x[1]['count'], reverse=True)
            
            # Print top 15
            for pair, data in sorted_matchups[:15]:
                ta, tb = pair
                count = data['count']
                prob = (count / num_sims) * 100
                
                wa_count = data['wins'].get(ta, 0)
                wb_count = data['wins'].get(tb, 0)
                
                wa_prob = (wa_count / count) * 100 if count > 0 else 0
                wb_prob = (wb_count / count) * 100 if count > 0 else 0
                
                f.write(f"| {ta} vs {tb} | {prob:.1f}% | {ta} ({wa_prob:.1f}%) | {tb} ({wb_prob:.1f}%) |\n")
            f.write("\n")
            
    # Generate Diagnostic Report
    diag_md_path = os.path.join(output_dir, 'diagnostic_report.md')
    with open(diag_md_path, 'w', encoding='utf-8') as f:
        rs = global_run_stats
        
        total_group_games = max(1, rs['group_games'])
        total_ko_games = max(1, rs['ko_games'])
        decisive_group_games = max(1, rs['team_a_wins'] + rs['team_b_wins'])
        
        f.write("# Simulation Diagnostics\n\n")
        f.write("### Overall Data\n")
        f.write(f"- **Total Matches Simulated**: {rs['group_games'] + rs['ko_games']}\n\n")
        
        f.write("### Group Stage Breakdown\n")
        f.write(f"- **Matches Simulated**: {rs['group_games']}\n")
        f.write(f"- **Total Goals Scored**: {rs['group_goals']}\n")
        f.write(f"- **Avg Goals per Match**: {rs['group_goals'] / total_group_games:.2f}\n")
        f.write(f"- **Matches Ending in a Draw**: {rs['group_draws']} ({(rs['group_draws'] / total_group_games) * 100:.1f}%)\n")
        f.write(f"- **Matches Ending with a Winner**: {rs['team_a_wins'] + rs['team_b_wins']} ({((rs['team_a_wins'] + rs['team_b_wins']) / total_group_games) * 100:.1f}%)\n")
        f.write(f"  - Team A Wins: {rs['team_a_wins']} ({(rs['team_a_wins'] / total_group_games) * 100:.1f}%)\n")
        f.write(f"  - Team B Wins: {rs['team_b_wins']} ({(rs['team_b_wins'] / total_group_games) * 100:.1f}%)\n")
        f.write(f"- **Avg Goals by Winning Team**: {rs['winner_goals'] / decisive_group_games:.2f}\n")
        f.write(f"- **Avg Goals by Losing Team**: {rs['loser_goals'] / decisive_group_games:.2f}\n\n")
        
        f.write("### Knockout Stage Breakdown\n")
        f.write(f"- **Total Knockout Matches**: {rs['ko_games']}\n")
        f.write(f"- **Won in Regular Time (90m)**: {rs['rt_wins']} ({(rs['rt_wins'] / total_ko_games) * 100:.1f}%)\n")
        f.write(f"- **Won in Extra Time (120m)**: {rs['et_wins']} ({(rs['et_wins'] / total_ko_games) * 100:.1f}%)\n")
        f.write(f"- **Decided by Penalty Shootout**: {rs['pen_wins']} ({(rs['pen_wins'] / total_ko_games) * 100:.1f}%)\n\n")
        
        f.write("### Match Outcomes by Elo Difference\n")
        f.write(f"| {'Elo Diff':<10} | {'Games':<10} | {'Fav Win%':<9} | {'Dog Win%':<9} | {'Draw%':<6} |\n")
        f.write(f"|{'-'*12}|{'-'*12}|{'-'*11}|{'-'*11}|{'-'*8}|\n")
        for b in ['0-50', '51-150', '151-300', '300+']:
            st = rs['elo_diff'][b]
            if st['games'] > 0:
                g = st['games']
                f.write(f"| {b:<10} | {g:<10} | {st['favorite_wins']/g*100:<9.1f} | {st['underdog_wins']/g*100:<9.1f} | {st['draws']/g*100:<6.1f} |\n")
        f.write("\n")
        
        f.write("### Team Performance by Elo Tier\n")
        f.write(f"| {'Elo Tier':<10} | {'Games':<10} | {'Win%':<6} | {'Draw%':<6} | {'Loss%':<6} |\n")
        f.write(f"|{'-'*12}|{'-'*12}|{'-'*8}|{'-'*8}|{'-'*8}|\n")
        for t in ['1900+', '1800-1899', '1700-1799', '1600-1699', '<1600']:
            st = rs['elo_tier'][t]
            if st['games'] > 0:
                g = st['games']
                f.write(f"| {t:<10} | {g:<10} | {st['w']/g*100:<6.1f} | {st['d']/g*100:<6.1f} | {st['l']/g*100:<6.1f} |\n")
                
    # Generate CSV
    csv_path = os.path.join(output_dir, 'simulation_results.csv')
    
    with open(csv_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['Team', 'R32_%', 'R16_%', 'QF_%', 'SF_%', 'Final_%', 'Win_%'])
        for team, stats in sorted_teams:
            writer.writerow([
                team, 
                f"{stats.get('r32', 0):.2f}",
                f"{stats.get('r16', 0):.2f}",
                f"{stats.get('qf', 0):.2f}",
                f"{stats.get('sf', 0):.2f}",
                f"{stats.get('final', 0):.2f}",
                f"{stats.get('winner', 0):.2f}"
            ])
            
    print(f"Reports generated in {output_dir}")
