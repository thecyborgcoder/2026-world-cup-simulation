import json
import os
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import main

class WorldCupHandler(SimpleHTTPRequestHandler):
    def translate_path(self, path):
        if path == '/':
            path = '/index.html'
        path = '/ui' + path
        return super().translate_path(path)

    def do_GET(self):
        if self.path == '/api/progress':
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            
            progress_data = {
                'status': main.current_status,
                'progress': main.current_progress,
                'total': main.total_sims,
                'top10': main.current_top10,
                'bracket': main.current_bracket
            }
            self.wfile.write(json.dumps(progress_data).encode('utf-8'))
        else:
            super().do_GET()

    def do_POST(self):
        if self.path == '/api/simulate':
            content_length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(content_length).decode('utf-8')
            
            try:
                payload = json.loads(body)
                num_sims = int(payload.get('simulations', 1000))
                
                print(f"Received request to run {num_sims} simulations.")
                bracket_data, stats_data = main.run_simulations_for_ui(num_sims)
                
                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                
                response_data = {
                    'data': bracket_data,
                    'stats': stats_data
                }
                self.wfile.write(json.dumps(response_data).encode('utf-8'))
                
            except Exception as e:
                import traceback
                traceback.print_exc()
                self.send_response(500)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({"error": str(e)}).encode('utf-8'))
        else:
            self.send_response(404)
            self.end_headers()

if __name__ == '__main__':
    port = 8000
    server_address = ('', port)
    
    httpd = ThreadingHTTPServer(server_address, WorldCupHandler)
    print(f"Starting server on http://localhost:{port}/")
    print("API available at POST /api/simulate")
    print("Progress API available at GET /api/progress")
    print("Press Ctrl+C to stop.")
    httpd.serve_forever()
