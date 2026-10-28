"""Serve the latest district aggregates to the Android emulator on this computer."""

from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_FILE = PROJECT_ROOT / "outputs" / "eicv7_district_double_exclusion.csv"
HOST = "127.0.0.1"
PORT = 8765


class DistrictDataHandler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        if self.path.split("?", 1)[0] != "/district_estimates.csv":
            self.send_error(404, "Not found")
            return
        try:
            contents = DATA_FILE.read_bytes()
        except OSError:
            self.send_error(503, "Run scripts/analyze_eicv7.py to generate district data")
            return

        self.send_response(200)
        self.send_header("Content-Type", "text/csv; charset=utf-8")
        self.send_header("Content-Length", str(len(contents)))
        self.send_header("Cache-Control", "no-store, no-cache, must-revalidate")
        self.end_headers()
        self.wfile.write(contents)

    def log_message(self, format: str, *args: object) -> None:
        print(f"{self.log_date_time_string()} {format % args}")


if __name__ == "__main__":
    server = ThreadingHTTPServer((HOST, PORT), DistrictDataHandler)
    print(f"Serving {DATA_FILE} at http://{HOST}:{PORT}/district_estimates.csv")
    print("Keep this process running while using Refresh in the Android emulator.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("Stopping district data server.")
    finally:
        server.server_close()
