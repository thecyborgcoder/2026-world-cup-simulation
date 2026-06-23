import multiprocessing
import yaml
import json
from collections import defaultdict
from elo_fetcher import fetch_elo_ratings
from simulator import run_one_simulation
from report_generator import generate_reports

# Global variables for worker processes to avoid IPC overhead
_teams = None
_matches = None
_ratings = None

def init_worker(teams, matches, ratings):
    global _teams, _matches, _ratings
    _teams = teams
    _matches = matches
    _ratings = ratings

def worker_sim(_):
    # Execute a single simulation using the globally cached data
    return run_one_simulation(_teams, _matches, _ratings)

def main():
    with open('config.yaml', 'r') as f:
        config = yaml.safe_load(f)
        
    with open('teams.json', 'r') as f:
        teams = json.load(f)
        
    with open('matches.json', 'r') as f:
        matches = json.load(f)
        
    ratings = fetch_elo_ratings(cache_hours=config.get('elo_cache_hours', 24))
    
    num_sims = config.get('num_simulations', 1000)
    cpu_cores = multiprocessing.cpu_count()
    print(f"Running {num_sims} simulations across {cpu_cores} CPU cores...")
    
    tally = defaultdict(lambda: {'r32': 0, 'r16': 0, 'qf': 0, 'sf': 0, 'final': 0, 'winner': 0})
    
    # Matchup tracking: {stage: { (team_a, team_b): {'count': 0, 'wins': {team_a: 0, team_b: 0}} }}
    matchups_tally = {
        'r32': defaultdict(lambda: {'count': 0, 'wins': defaultdict(int)}),
        'r16': defaultdict(lambda: {'count': 0, 'wins': defaultdict(int)}),
        'qf': defaultdict(lambda: {'count': 0, 'wins': defaultdict(int)}),
        'sf': defaultdict(lambda: {'count': 0, 'wins': defaultdict(int)}),
        'final': defaultdict(lambda: {'count': 0, 'wins': defaultdict(int)})
    }
    
    def process_matchups(bracket, winners, stage):
        for i, match in enumerate(bracket):
            # Sort to ensure (A, B) is same as (B, A)
            pair = tuple(sorted(match))
            winner = winners[i] if stage != 'final' else winners[0]
            
            matchups_tally[stage][pair]['count'] += 1
            matchups_tally[stage][pair]['wins'][winner] += 1
    
    # Chunk size optimizations for IPC
    chunk_size = max(1, num_sims // (cpu_cores * 8))
    
    # Spawn pool and execute simulations in parallel
    with multiprocessing.Pool(initializer=init_worker, initargs=(teams, matches, ratings)) as pool:
        for i, result in enumerate(pool.imap_unordered(worker_sim, range(num_sims), chunksize=chunk_size)):
            for team in result['r32']: tally[team]['r32'] += 1
            for team in result['r16']: tally[team]['r16'] += 1
            for team in result['qf']: tally[team]['qf'] += 1
            for team in result['sf']: tally[team]['sf'] += 1
            for team in result['final']: tally[team]['final'] += 1
            tally[result['winner']]['winner'] += 1
            
            # Aggregate Matchups
            process_matchups(result['r32_bracket'], result['r16'], 'r32')
            process_matchups(result['r16_bracket'], result['qf'], 'r16')
            process_matchups(result['qf_bracket'], result['sf'], 'qf')
            process_matchups(result['sf_bracket'], result['final'], 'sf')
            process_matchups(result['final_bracket'], [result['winner']], 'final')
            
            if (i + 1) % max(1, num_sims // 10) == 0:
                print(f"Simulated {i + 1}/{num_sims}")
                
    generate_reports(tally, matchups_tally, num_sims, config.get('output_dir', './outputs'))

if __name__ == '__main__':
    # Required for Windows multiprocessing
    multiprocessing.freeze_support()
    main()
