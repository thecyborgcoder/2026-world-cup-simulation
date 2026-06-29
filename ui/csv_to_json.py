import csv
import json
import os

csv_path = r'c:\code\simulation\2026-world-cup-simulation\outputs\simulation_results.csv'
json_path = 'stats.json'

data = []
if os.path.exists(csv_path):
    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            data.append(row)

with open(json_path, 'w', encoding='utf-8') as f:
    json.dump(data, f, indent=2)
