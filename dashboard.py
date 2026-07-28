"""Dashboard web simple para ver métricas.

Ejecutar: python dashboard.py
Acceder: http://localhost:8080
"""

import json
from http.server import HTTPServer, BaseHTTPRequestHandler

from metrics_db import init_db, obtener_todos_tweets, obtener_estadisticas_por_fuente


class DashboardHandler(BaseHTTPRequestHandler):
    """Handler para el dashboard web."""

    def do_GET(self) -> None:
        """Maneja las peticiones GET."""
        if self.path == "/" or self.path == "/index.html":
            self._serve_dashboard()
        elif self.path == "/api/tweets":
            self._serve_tweets()
        elif self.path == "/api/stats":
            self._serve_stats()
        else:
            self._serve_404()

    def _serve_dashboard(self) -> None:
        """Sirve la página principal del dashboard."""
        html = """<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Trending2Tweet - Dashboard</title>
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: #0f0f23; color: #e0e0e0; padding: 20px; }
        h1 { color: #00d4ff; margin-bottom: 20px; }
        .stats { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 15px; margin-bottom: 30px; }
        .stat-card { background: #1a1a2e; padding: 20px; border-radius: 10px; border: 1px solid #333; }
        .stat-card h3 { color: #888; font-size: 14px; margin-bottom: 5px; }
        .stat-card .value { font-size: 28px; font-weight: bold; color: #00d4ff; }
        table { width: 100%; border-collapse: collapse; background: #1a1a2e; border-radius: 10px; overflow: hidden; }
        th, td { padding: 12px 15px; text-align: left; border-bottom: 1px solid #333; }
        th { background: #252540; color: #00d4ff; font-weight: 600; }
        tr:hover { background: #252540; }
        .emoji { font-size: 18px; }
        .loading { text-align: center; padding: 40px; color: #888; }
        .refresh-btn { background: #00d4ff; color: #0f0f23; border: none; padding: 10px 20px; border-radius: 5px; cursor: pointer; font-weight: bold; margin-bottom: 20px; }
        .refresh-btn:hover { background: #00b8d9; }
    </style>
</head>
<body>
    <h1>📊 Trending2Tweet Dashboard</h1>
    <button class="refresh-btn" onclick="loadData()">🔄 Actualizar</button>

    <div class="stats" id="stats">
        <div class="stat-card"><h3>Total Tweets</h3><div class="value" id="total">-</div></div>
        <div class="stat-card"><h3>Total Likes</h3><div class="value" id="likes">-</div></div>
        <div class="stat-card"><h3>Total Retweets</h3><div class="value" id="rts">-</div></div>
        <div class="stat-card"><h3>Total Impresiones</h3><div class="value" id="impressions">-</div></div>
    </div>

    <h2 style="margin-bottom: 15px;">Tweets recientes</h2>
    <table>
        <thead>
            <tr>
                <th>ID</th>
                <th>Source</th>
                <th>Texto</th>
                <th>Likes</th>
                <th>RTs</th>
                <th>Replies</th>
                <th>Impresiones</th>
                <th>Fecha</th>
            </tr>
        </thead>
        <tbody id="tweets">
            <tr><td colspan="8" class="loading">Cargando...</td></tr>
        </tbody>
    </table>

    <script>
        async function loadData() {
            try {
                const [tweetsRes, statsRes] = await Promise.all([
                    fetch('/api/tweets'),
                    fetch('/api/stats')
                ]);
                const tweets = await tweetsRes.json();
                const stats = await statsRes.json();

                // Actualizar stats
                document.getElementById('total').textContent = stats.total_tweets || 0;
                document.getElementById('likes').textContent = stats.total_likes || 0;
                document.getElementById('rts').textContent = stats.total_retweets || 0;
                document.getElementById('impressions').textContent = (stats.total_impressions || 0).toLocaleString();

                // Actualizar tabla
                const tbody = document.getElementById('tweets');
                if (tweets.length === 0) {
                    tbody.innerHTML = '<tr><td colspan="8" class="loading">No hay tweets aún</td></tr>';
                    return;
                }

                tbody.innerHTML = tweets.map(t => `
                    <tr>
                        <td>${t.tweet_id.substring(0, 15)}...</td>
                        <td>${t.source}</td>
                        <td>${(t.texto || '').substring(0, 60)}...</td>
                        <td>❤️ ${t.likes_latest || 0}</td>
                        <td>🔁 ${t.retweets_latest || 0}</td>
                        <td>💬 ${t.replies_latest || 0}</td>
                        <td>👁 ${(t.impressions_latest || 0).toLocaleString()}</td>
                        <td>${(t.published_at || '').substring(0, 16)}</td>
                    </tr>
                `).join('');
            } catch (e) {
                console.error('Error cargando datos:', e);
            }
        }

        loadData();
        setInterval(loadData, 30000); // Auto-refresh cada 30s
    </script>
</body>
</html>"""

        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(html.encode("utf-8"))

    def _serve_tweets(self) -> None:
        """Sirve los tweets como JSON."""
        init_db()
        tweets = obtener_todos_tweets(limit=50)
        self._send_json(tweets)

    def _serve_stats(self) -> None:
        """Sirve las estadísticas como JSON."""
        init_db()
        tweets = obtener_todos_tweets(limit=500)

        stats = {
            "total_tweets": len(tweets),
            "total_likes": sum(t["likes_latest"] or 0 for t in tweets),
            "total_retweets": sum(t["retweets_latest"] or 0 for t in tweets),
            "total_replies": sum(t["replies_latest"] or 0 for t in tweets),
            "total_impressions": sum(t["impressions_latest"] or 0 for t in tweets),
        }
        self._send_json(stats)

    def _send_json(self, data: dict | list) -> None:
        """Envía una respuesta JSON."""
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(data, default=str).encode("utf-8"))

    def _serve_404(self) -> None:
        """Sirve una respuesta 404."""
        self.send_response(404)
        self.send_header("Content-Type", "text/plain")
        self.end_headers()
        self.wfile.write(b"404 Not Found")

    def log_message(self, format: str, *args) -> None:
        """Silencia los logs de requests."""
        pass


def main() -> None:
    """Inicia el servidor del dashboard."""
    port = 8080
    server = HTTPServer(("0.0.0.0", port), DashboardHandler)
    print(f"🌐 Dashboard corriendo en http://localhost:{port}")
    print("   Presiona Ctrl+C para detener")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n👋 Dashboard detenido")
        server.server_close()


if __name__ == "__main__":
    main()
