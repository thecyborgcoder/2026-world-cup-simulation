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
            
            if (i + 1) % max(1, num_sims // 10) == 0:
                print(f"Simulated {i + 1}/{num_sims}")
                
    generate_reports(tally, num_sims, config.get('output_dir', './outputs'))

if __name__ == '__main__':
    # Required for Windows multiprocessing
    multiprocessing.freeze_support()
    main()
