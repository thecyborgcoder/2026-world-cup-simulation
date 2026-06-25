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
    
    global_run_stats = {
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
            
            # Aggregate run stats
            rs = result['run_stats']
            for k in ['group_games', 'group_goals', 'group_draws', 'team_a_wins', 'team_b_wins',
                      'winner_goals', 'loser_goals', 'ko_games', 'ko_goals', 'ko_winner_goals', 'ko_loser_goals', 'rt_wins', 'et_wins', 'pen_wins']:
                global_run_stats[k] += rs[k]
                
            for b in rs['elo_diff']:
                for k in rs['elo_diff'][b]:
                    global_run_stats['elo_diff'][b][k] += rs['elo_diff'][b][k]
                    
            for t in rs['elo_tier']:
                for k in rs['elo_tier'][t]:
                    global_run_stats['elo_tier'][t][k] += rs['elo_tier'][t][k]
            
            if (i + 1) % max(1, num_sims // 10) == 0:
                print(f"Simulated {i + 1}/{num_sims}")
                
    generate_reports(tally, matchups_tally, global_run_stats, num_sims, config.get('output_dir', './outputs'))

if __name__ == '__main__':
    # Required for Windows multiprocessing
    multiprocessing.freeze_support()
    main()
