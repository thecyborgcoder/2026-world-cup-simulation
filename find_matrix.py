import urllib.request, json
req = urllib.request.Request('https://api.github.com/search/repositories?q=2026+world+cup+matrix', headers={'User-Agent': 'Mozilla'})
try:
  resp = urllib.request.urlopen(req).read().decode('utf-8')
  data = json.loads(resp)
  for item in data.get('items', []): print(item['html_url'])
except Exception as e: print(e)