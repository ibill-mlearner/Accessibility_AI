from __future__ import annotations

from flask import Blueprint, Response, current_app

from ....logging_config import DomainEvent


def _api_view_html() -> str:
    """Build a lightweight API test page for v1 endpoints."""
    return """<!doctype html>
<html lang=\"en\">
  <head>
    <meta charset=\"utf-8\" />
    <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\" />
    <title>API v1 Test View</title>
    <style>
      body { font-family: Arial, sans-serif; margin: 2rem; line-height: 1.4; }
      code { background: #f4f4f4; padding: 0.2rem 0.4rem; border-radius: 4px; }
      textarea { width: 100%; min-height: 8rem; }
      input, select, button, textarea { margin-top: 0.4rem; margin-bottom: 0.8rem; }
      .grid { display: grid; grid-template-columns: 1fr 1fr; gap: 1rem; }
      pre { background: #111; color: #fff; padding: 1rem; border-radius: 6px; overflow: auto; }
      .hint { color: #555; }
    </style>
  </head>
  <body>
    <h1>Accessibility AI - API v1 Test View</h1>
    <p class=\"hint\">Use this page to inspect and test the currently implemented API v1 endpoints.</p>

    <h2>Available endpoints</h2>
    <ul>
      <li><code>GET /api/v1/health</code></li>
      <li><code>POST /api/v1/ai/interactions</code></li>
      <li><code>GET|POST /api/v1/chats</code></li>
      <li><code>GET|PUT|PATCH|DELETE /api/v1/chats/&lt;id&gt;</code></li>
      <li><code>GET|POST /api/v1/messages</code></li>
      <li><code>GET|PUT|PATCH|DELETE /api/v1/messages/&lt;id&gt;</code></li>
      <li><code>GET|POST /api/v1/classes</code></li>
      <li><code>GET|PUT|PATCH|DELETE /api/v1/classes/&lt;id&gt;</code></li>
      <li><code>GET|POST /api/v1/features</code></li>
      <li><code>GET|PUT|PATCH|DELETE /api/v1/features/&lt;id&gt;</code></li>
      <li><code>GET|POST /api/v1/notes</code></li>
      <li><code>GET|PUT|PATCH|DELETE /api/v1/notes/&lt;id&gt;</code></li>
      <li><code>GET /api/v1/api_view</code></li>
    </ul>

    <h2>Try an endpoint</h2>
    <div class=\"grid\">
      <div>
        <label for=\"method\">Method</label><br />
        <select id=\"method\">
          <option>GET</option>
          <option>POST</option>
          <option>PUT</option>
          <option>PATCH</option>
          <option>DELETE</option>
        </select><br />

        <label for=\"path\">Path (starts with /api/v1)</label><br />
        <input id=\"path\" type=\"text\" value=\"/api/v1/health\" size=\"60\" /><br />

        <label for=\"payload\">JSON body (optional)</label><br />
        <textarea id=\"payload\">{}</textarea><br />

        <button id=\"send\">Send Request</button>
      </div>

      <div>
        <h3>Response</h3>
        <pre id=\"output\">No request sent yet.</pre>
      </div>
    </div>

    <script>
      const methodEl = document.getElementById('method');
      const pathEl = document.getElementById('path');
      const payloadEl = document.getElementById('payload');
      const outputEl = document.getElementById('output');

      document.getElementById('send').addEventListener('click', async () => {
        const method = methodEl.value;
        const path = pathEl.value;

        const options = { method, headers: { 'Content-Type': 'application/json' } };

        if (method !== 'GET' && method !== 'DELETE') {
          try {
            options.body = JSON.stringify(JSON.parse(payloadEl.value || '{}'));
          } catch (error) {
            outputEl.textContent = `Invalid JSON body: ${error.message}`;
            return;
          }
        }

        try {
          const response = await fetch(path, options);
          const text = await response.text();
          let parsed;
          try {
            parsed = JSON.parse(text);
          } catch {
            parsed = text;
          }

          outputEl.textContent = JSON.stringify(
            { status: response.status, ok: response.ok, body: parsed },
            null,
            2,
          );
        } catch (error) {
          outputEl.textContent = `Request failed: ${error.message}`;
        }
      });
    </script>
  </body>
</html>
"""


def api_view() -> Response:
    """Render a simple built-in API test page for v1 endpoints."""
    current_app.extensions["event_bus"].publish(DomainEvent("api.viewed"))
    return Response(_api_view_html(), mimetype="text/html")


def register_api_view_route(api_v1_bp: Blueprint) -> None:
    """Attach the standalone API view route to the v1 blueprint."""
    api_v1_bp.add_url_rule("/api_view", endpoint="api_view", view_func=api_view, methods=["GET"])
