import yaml
import json
from collections import defaultdict
from elo_fetcher import fetch_elo_ratings
from simulator import run_one_simulation
from report_generator import generate_reports

def main():
    with open('config.yaml', 'r') as f:
        config = yaml.safe_load(f)
        
    with open('teams.json', 'r') as f:
        teams = json.load(f)
        
    with open('matches.json', 'r') as f:
        matches = json.load(f)
        
    ratings = fetch_elo_ratings(cache_hours=config.get('elo_cache_hours', 24))
    
    num_sims = config.get('num_simulations', 1000)
    print(f"Running {num_sims} simulations...")
    
    tally = defaultdict(lambda: {'r32': 0, 'r16': 0, 'qf': 0, 'sf': 0, 'final': 0, 'winner': 0})
    
    for i in range(num_sims):
        result = run_one_simulation(teams, matches, ratings)
        
        for team in result['r32']: tally[team]['r32'] += 1
        for team in result['r16']: tally[team]['r16'] += 1
        for team in result['qf']: tally[team]['qf'] += 1
        for team in result['sf']: tally[team]['sf'] += 1
        for team in result['final']: tally[team]['final'] += 1
        tally[result['winner']]['winner'] += 1
        
        if (i+1) % max(1, num_sims // 10) == 0:
            print(f"Simulated {i+1}/{num_sims}")
            
    generate_reports(tally, num_sims, config.get('output_dir', './outputs'))

if __name__ == '__main__':
    main()
