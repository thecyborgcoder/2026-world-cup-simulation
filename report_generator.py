import csv
import json
import os

def generate_reports(results_tally, matchups_tally, num_sims, output_dir):
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
