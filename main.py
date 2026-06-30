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

# Progress tracking for the UI
current_status = "Idle"
current_progress = 0
total_sims = 0
current_top10 = []
current_bracket = None

def generate_ui_bracket(matchups_tally, r32_slot_tally, ratings, use_elo_probs=False):
    def get_code(team_name):
        fixed_codes = {
            'Netherlands': 'NED', 'United States': 'USA', 'England': 'ENG',
            'South Korea': 'KOR', 'Spain': 'ESP', 'Italy': 'ITA', 'Japan': 'JPN',
            'Morocco': 'MAR', 'Colombia': 'COL', 'France': 'FRA', 'Germany': 'GER',
            'Portugal': 'POR', 'Belgium': 'BEL', 'Croatia': 'CRO', 'Switzerland': 'SUI',
            'Denmark': 'DEN', 'Ivory Coast': 'CIV', 'Nigeria': 'NGA', 'Iran': 'IRN',
            'Australia': 'AUS', 'Saudi Arabia': 'KSA', 'Canada': 'CAN', 'Peru': 'PER',
            'Chile': 'CHI', 'Wales': 'WAL', 'Argentina': 'ARG', 'Mexico': 'MEX',
            'Brazil': 'BRA', 'Uruguay': 'URU', 'Sweden': 'SWE', 'Senegal': 'SEN',
            'Austria': 'AUT', 'South Africa': 'RSA', 'New Zealand': 'NZL', 
            'DR Congo': 'DRC', 'Bosnia and Herzegovina': 'BIH', 'Cape Verde': 'CPV'
        }
        return fixed_codes.get(team_name, team_name[:3].upper())

    def build_match(t1, t2, match_id, stage):
        pair = tuple(sorted([t1, t2]))
        stage_data = matchups_tally[stage].get(pair)
        
        count = stage_data['count'] if stage_data else 0
        w1_count = stage_data['wins'].get(t1, 0) if stage_data else 0
        w2_count = stage_data['wins'].get(t2, 0) if stage_data else 0
        
        if count > 0:
            w1 = w1_count >= w2_count
        else:
            from simulator import simulate_match, get_adjusted_elo
            elo1 = ratings.get(t1, 1500)
            elo2 = ratings.get(t2, 1500)
            adj_elo1 = get_adjusted_elo(t1, elo1)
            adj_elo2 = get_adjusted_elo(t2, elo2)
            
            winner_team, _, _, _ = simulate_match(t1, t2, adj_elo1, adj_elo2, location='USA', is_knockout=True)
            w1 = (winner_team == t1)
            
        if use_elo_probs:
            from simulator import get_adjusted_elo
            elo1 = ratings.get(t1, 1500)
            elo2 = ratings.get(t2, 1500)
            adj_elo1 = get_adjusted_elo(t1, elo1)
            adj_elo2 = get_adjusted_elo(t2, elo2)
            disp_p1 = 1 / (1 + 10 ** ((adj_elo2 - adj_elo1) / 400))
            disp_p2 = 1.0 - disp_p1
        else:
            if count > 0:
                disp_p1 = w1_count / count
                disp_p2 = 1.0 - disp_p1
            else:
                disp_p1 = 1.0 if w1 else 0.0
                disp_p2 = 0.0 if w1 else 1.0
            
        winner = t1 if w1 else t2
            
        name1 = f"{t1} ({disp_p1*100:.1f}%)"
        name2 = f"{t2} ({disp_p2*100:.1f}%)"
        
        m = {
            'id': match_id,
            'team1': {'name': name1, 'code': get_code(t1), 'score': 'W' if w1 else 'L', 'winner': w1},
            'team2': {'name': name2, 'code': get_code(t2), 'score': 'L' if w1 else 'W', 'winner': not w1}
        }
        return m, winner

    c = []
    for j in range(16):
        if len(r32_slot_tally[j]) == 0:
            c.append(('Unknown A', 'Unknown B'))
        else:
            most_common_pair = max(r32_slot_tally[j].items(), key=lambda x: x[1])[0]
            c.append(most_common_pair)
            
    left_r32 = [c[1], c[4], c[0], c[2], c[3], c[5], c[6], c[7]]
    right_r32 = [c[10], c[11], c[8], c[9], c[12], c[14], c[13], c[15]]
    
    def process_side(side_r32_matches, side_prefix):
        rounds = {}
        r32_ui = []
        r16_teams = []
        
        for i, match in enumerate(side_r32_matches):
            m, w = build_match(match[0], match[1], f"{side_prefix}_roundOf32_{i}", 'r32')
            r32_ui.append(m)
            r16_teams.append(w)
            
        rounds['roundOf32'] = r32_ui
        
        r16_ui = []
        qf_teams = []
        r16_matchups = [(r16_teams[0], r16_teams[1]), (r16_teams[2], r16_teams[3]), (r16_teams[4], r16_teams[5]), (r16_teams[6], r16_teams[7])]
        for i, match in enumerate(r16_matchups):
            m, w = build_match(match[0], match[1], f"{side_prefix}_roundOf16_{i}", 'r16')
            r16_ui.append(m)
            qf_teams.append(w)
            
        rounds['roundOf16'] = r16_ui
        
        qf_ui = []
        sf_teams = []
        qf_matchups = [(qf_teams[0], qf_teams[1]), (qf_teams[2], qf_teams[3])]
        for i, match in enumerate(qf_matchups):
            m, w = build_match(match[0], match[1], f"{side_prefix}_quarterFinals_{i}", 'qf')
            qf_ui.append(m)
            sf_teams.append(w)
            
        rounds['quarterFinals'] = qf_ui
        
        sf_ui = []
        final_teams = []
        sf_matchups = [(sf_teams[0], sf_teams[1])]
        for i, match in enumerate(sf_matchups):
            m, w = build_match(match[0], match[1], f"{side_prefix}_semiFinals_{i}", 'sf')
            sf_ui.append(m)
            final_teams.append(w)
            
        rounds['semiFinals'] = sf_ui
        
        return rounds, final_teams[0]

    left_rounds, left_finalist = process_side(left_r32, 'L')
    right_rounds, right_finalist = process_side(right_r32, 'R')
    
    final_ui, _ = build_match(left_finalist, right_finalist, 'F_1', 'final')
    
    ui_data = {
        'left': left_rounds,
        'right': right_rounds,
        'final': final_ui
    }
    return ui_data

def init_worker(teams, matches, ratings):
    global _teams, _matches, _ratings
    _teams = teams
    _matches = matches
    _ratings = ratings

def worker_sim(_):
    # Execute a single simulation using the globally cached data
    return run_one_simulation(_teams, _matches, _ratings)


def run_simulations(override_num_sims=None):
    import yaml
    import json
    from elo_fetcher import fetch_elo_ratings
    import multiprocessing
    from collections import defaultdict
    
    with open('config.yaml', 'r') as f:
        config = yaml.safe_load(f)
        
    with open('teams.json', 'r') as f:
        teams = json.load(f)
        
    with open('matches.json', 'r') as f:
        matches = json.load(f)
        
    ratings = fetch_elo_ratings(cache_hours=config.get('elo_cache_hours', 24))
    
    global current_status, current_progress, total_sims, current_top10, current_bracket
    current_status = "Fetching Data & ELO Ratings..."
    current_progress = 0
    current_top10 = []
    current_bracket = None
    
    num_sims = override_num_sims if override_num_sims is not None else config.get('num_simulations', 1000)
    total_sims = num_sims

    cpu_cores = multiprocessing.cpu_count()
    print(f"Running {num_sims} simulations across {cpu_cores} CPU cores...")
    
    tally = defaultdict(lambda: {'r32': 0, 'r16': 0, 'qf': 0, 'sf': 0, 'final': 0, 'winner': 0})
    r32_slot_tally = [defaultdict(int) for _ in range(16)]

    
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
    chunk_size = max(1, num_sims // (cpu_cores * 50))
    
    current_status = "Spawning Worker Processes..."
    import time
    
    def process_result(i, result):
        global current_progress, current_status, current_top10, current_bracket
        for team in result['r32']: tally[team]['r32'] += 1
        for team in result['r16']: tally[team]['r16'] += 1
        for team in result['qf']: tally[team]['qf'] += 1
        for team in result['sf']: tally[team]['sf'] += 1
        for team in result['final']: tally[team]['final'] += 1
        tally[result['winner']]['winner'] += 1
        for j, match in enumerate(result['r32_bracket']):
            pair = tuple(sorted(match))
            r32_slot_tally[j][pair] += 1

        
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
        
        current_status = "Simulating..."
        current_progress = i + 1
        
        if (i + 1) % 100 == 0 or (i + 1) == num_sims:
            sorted_teams = sorted(tally.items(), key=lambda x: x[1].get('winner', 0), reverse=True)[:10]
            temp_top10 = []
            for team, stats in sorted_teams:
                temp_top10.append({
                    'Team': team,
                    'R32_%': f"{(stats.get('r32', 0)/(i+1))*100:.2f}",
                    'R16_%': f"{(stats.get('r16', 0)/(i+1))*100:.2f}",
                    'QF_%': f"{(stats.get('qf', 0)/(i+1))*100:.2f}",
                    'SF_%': f"{(stats.get('sf', 0)/(i+1))*100:.2f}",
                    'Final_%': f"{(stats.get('final', 0)/(i+1))*100:.2f}",
                    'Win_%': f"{(stats.get('winner', 0)/(i+1))*100:.2f}"
                })
            current_top10 = temp_top10
            use_elo_probs = (num_sims < 10)
            current_bracket = generate_ui_bracket(matchups_tally, r32_slot_tally, ratings, use_elo_probs)
        
        if i % 100 == 0:
            time.sleep(0.0001)
        
        if (i + 1) % max(1, num_sims // 10) == 0:
            print(f"Simulated {i + 1}/{num_sims}")

    if num_sims < 10:
        current_status = "Simulating..."
        init_worker(teams, matches, ratings)
        for i in range(num_sims):
            result = worker_sim(i)
            process_result(i, result)
    else:
        # Spawn pool and execute simulations in parallel
        with multiprocessing.Pool(initializer=init_worker, initargs=(teams, matches, ratings)) as pool:
            for i, result in enumerate(pool.imap_unordered(worker_sim, range(num_sims), chunksize=chunk_size)):
                process_result(i, result)
                
    current_status = "Aggregating Results..."
    
    return tally, matchups_tally, global_run_stats, num_sims, config, r32_slot_tally, ratings

def main():
    run_simulations_for_ui(None)

def run_simulations_for_ui(num_sims):
    tally, matchups_tally, global_run_stats, num_sims, config, r32_slot_tally, ratings = run_simulations(num_sims)
    
    use_elo_probs = (num_sims < 10) if num_sims else False
    ui_data = generate_ui_bracket(matchups_tally, r32_slot_tally, ratings, use_elo_probs=use_elo_probs)
    
    sorted_teams = sorted(tally.items(), key=lambda x: x[1].get('winner', 0), reverse=True)
    ui_stats = []
    for team, stats in sorted_teams:
        ui_stats.append({
            'Team': team,
            'R32_%': f"{(stats.get('r32', 0)/num_sims)*100:.2f}",
            'R16_%': f"{(stats.get('r16', 0)/num_sims)*100:.2f}",
            'QF_%': f"{(stats.get('qf', 0)/num_sims)*100:.2f}",
            'SF_%': f"{(stats.get('sf', 0)/num_sims)*100:.2f}",
            'Final_%': f"{(stats.get('final', 0)/num_sims)*100:.2f}",
            'Win_%': f"{(stats.get('winner', 0)/num_sims)*100:.2f}"
        })
        
    # Save the output to disk so it loads automatically on the next page refresh
    import os
    import json as json_mod
    os.makedirs('ui', exist_ok=True)
    with open('ui/data.json', 'w') as f:
        json_mod.dump(ui_data, f, indent=2)
    with open('ui/stats.json', 'w') as f:
        json_mod.dump(ui_stats, f, indent=2)
        
    generate_reports(tally, matchups_tally, global_run_stats, num_sims, config.get('output_dir', './outputs'))
        
    return ui_data, ui_stats


if __name__ == '__main__':
    # Required for Windows multiprocessing
    multiprocessing.freeze_support()
    main()
