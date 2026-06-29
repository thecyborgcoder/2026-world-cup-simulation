import sys

content = open('main.py', 'r').read()

import_str = '''
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
    
    num_sims = override_num_sims if override_num_sims is not None else config.get('num_simulations', 1000)
'''

content = content.replace("def main():\n    with open('config.yaml', 'r') as f:\n        config = yaml.safe_load(f)\n        \n    with open('teams.json', 'r') as f:\n        teams = json.load(f)\n        \n    with open('matches.json', 'r') as f:\n        matches = json.load(f)\n        \n    ratings = fetch_elo_ratings(cache_hours=config.get('elo_cache_hours', 24))\n    \n    num_sims = config.get('num_simulations', 1000)", import_str)

slot_tally = '''
    r32_slot_tally = [defaultdict(int) for _ in range(16)]
'''
content = content.replace("tally = defaultdict(lambda: {'r32': 0, 'r16': 0, 'qf': 0, 'sf': 0, 'final': 0, 'winner': 0})", "tally = defaultdict(lambda: {'r32': 0, 'r16': 0, 'qf': 0, 'sf': 0, 'final': 0, 'winner': 0})" + slot_tally)

loop_tally = '''
            for j, match in enumerate(result['r32_bracket']):
                pair = tuple(sorted(match))
                r32_slot_tally[j][pair] += 1
'''
content = content.replace("tally[result['winner']]['winner'] += 1", "tally[result['winner']]['winner'] += 1" + loop_tally)

ret_stmt = '''
    return tally, matchups_tally, global_run_stats, num_sims, config, r32_slot_tally, ratings

def main():
    tally, matchups_tally, global_run_stats, num_sims, config, _, _ = run_simulations()
    generate_reports(tally, matchups_tally, global_run_stats, num_sims, config.get('output_dir', './outputs'))

def run_simulations_for_ui(num_sims):
    tally, matchups_tally, global_run_stats, num_sims, config, r32_slot_tally, ratings = run_simulations(num_sims)
    
    def get_code(team_name):
        return team_name[:3].upper()

    def build_match(t1, t2, match_id, stage):
        pair = tuple(sorted([t1, t2]))
        stage_data = matchups_tally[stage].get(pair)
        
        if stage_data and stage_data['count'] > 0:
            count = stage_data['count']
            w1_count = stage_data['wins'].get(t1, 0)
            p1 = w1_count / count
        else:
            elo1 = ratings.get(t1, 1500)
            elo2 = ratings.get(t2, 1500)
            p1 = 1 / (1 + 10 ** ((elo2 - elo1) / 400))
            
        p2 = 1.0 - p1
        w1 = p1 > 0.5
        winner = t1 if w1 else t2
        
        name1 = f"{t1} ({p1*100:.1f}%)"
        name2 = f"{t2} ({p2*100:.1f}%)"
        
        m = {
            'id': match_id,
            'team1': {'name': name1, 'code': get_code(t1), 'score': 'W' if w1 else 'L', 'winner': w1},
            'team2': {'name': name2, 'code': get_code(t2), 'score': 'L' if w1 else 'W', 'winner': not w1}
        }
        return m, winner

    consensus_r32_matches = []
    for j in range(16):
        if len(r32_slot_tally[j]) == 0:
            consensus_r32_matches.append(('Unknown A', 'Unknown B'))
        else:
            most_common_pair = max(r32_slot_tally[j].items(), key=lambda x: x[1])[0]
            consensus_r32_matches.append(most_common_pair)
            
    left_r32 = consensus_r32_matches[0:8]
    right_r32 = consensus_r32_matches[8:16]
    
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
        
    return ui_data, ui_stats
'''
content = content.replace("generate_reports(tally, matchups_tally, global_run_stats, num_sims, config.get('output_dir', './outputs'))", ret_stmt)

with open('main.py', 'w') as f:
    f.write(content)
print('Patched main.py')
