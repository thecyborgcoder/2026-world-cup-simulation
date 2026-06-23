import os
import time
import urllib.request
import csv

ELO_URL = 'https://www.eloratings.net/World.tsv'
TEAMS_URL = 'https://www.eloratings.net/en.teams.tsv'

def fetch_elo_ratings(cache_hours=24):
    cache_file = 'elo_cache.tsv'
    teams_cache_file = 'teams_cache.tsv'
    
    # Check cache
    if os.path.exists(cache_file) and os.path.exists(teams_cache_file):
        file_mod_time = os.path.getmtime(cache_file)
        if (time.time() - file_mod_time) / 3600 < cache_hours:
            return load_from_cache(cache_file, teams_cache_file)
            
    print("Fetching latest Elo ratings...")
    # Fetch Teams mapping
    req = urllib.request.Request(TEAMS_URL, headers={'User-Agent': 'Mozilla/5.0'})
    teams_data = urllib.request.urlopen(req).read().decode('utf-8', errors='ignore')
    with open(teams_cache_file, 'w', encoding='utf-8') as f:
        f.write(teams_data)
        
    # Fetch World ratings
    req = urllib.request.Request(ELO_URL, headers={'User-Agent': 'Mozilla/5.0'})
    world_data = urllib.request.urlopen(req).read().decode('utf-8', errors='ignore')
    with open(cache_file, 'w', encoding='utf-8') as f:
        f.write(world_data)
        
    return load_from_cache(cache_file, teams_cache_file)

def load_from_cache(elo_file, teams_file):
    # Parse teams mapping
    code_to_name = {}
    with open(teams_file, 'r', encoding='utf-8') as f:
        for line in f:
            parts = line.strip().split('\t')
            if len(parts) >= 2:
                code_to_name[parts[0]] = parts[1]
                
    # Parse elo ratings
    ratings = {}
    with open(elo_file, 'r', encoding='utf-8') as f:
        for line in f:
            parts = line.strip().split('\t')
            if len(parts) >= 4:
                code = parts[2]
                try:
                    rating = int(parts[3])
                except ValueError:
                    continue
                name = code_to_name.get(code, code)
                # handle special cases
                if name == 'United States': name = 'United States'
                elif name == 'South Korea': name = 'South Korea'
                
                # We will map standard names so simulation can match exactly
                ratings[name] = rating
                # Map alt names
                if len(parts) > 2 and parts[0] in code_to_name:
                    pass # can add logic if needed
                    
    # Some hardcoded aliases just in case
    aliases = {
        'USA': 'United States',
        'Korea Republic': 'South Korea',
        'Curacao': 'Curaçao',
        "Cote d'Ivoire": "Ivory Coast",
        "Turkey": "Türkiye",
        'Czech Republic': 'Czechia',
        'Cape Verde': 'Cabo Verde',
        'Bosnia': 'Bosnia and Herzegovina',
        'Iran': 'Iran', # Just ensuring normal mapping
    }
    
    # expand the dictionary with aliases
    for alt, main in aliases.items():
        if main in ratings:
            ratings[alt] = ratings[main]
        elif alt in ratings:
            ratings[main] = ratings[alt]

    return ratings

if __name__ == '__main__':
    ratings = fetch_elo_ratings()
    print("Ratings loaded:", len(ratings))
    for t in ['Mexico', 'United States', 'Argentina', 'Germany', 'Spain']:
        print(f"{t}: {ratings.get(t)}")
