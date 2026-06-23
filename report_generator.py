import csv
import json
import os

def generate_reports(results_tally, num_sims, output_dir):
    os.makedirs(output_dir, exist_ok=True)
    
    # Sort teams by win probability BEFORE turning them into percentages?
    # Wait, the existing code turns them into percentages here:
    # Actually I will just keep the raw counts and format them, but the CSV generation also relies on percentages.
    # Let's just create a formatted string from the percentage.
    
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
