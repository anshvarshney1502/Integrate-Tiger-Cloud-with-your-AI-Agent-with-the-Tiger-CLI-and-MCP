"""
Tiger Agent Dashboard Server: Zero-dependency HTTP & API server for the web UI.
"""

import http.server
import json
import os
import urllib.parse
from typing import Optional

from .agent import TigerAgent
from .guardrails import TigerGuardrails
from .mcp_client import TigerMCPClient

DASHBOARD_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "dashboard"))


class TigerAgentHTTPHandler(http.server.SimpleHTTPRequestHandler):
    agent: TigerAgent

    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=DASHBOARD_DIR, **kwargs)

    def _send_json(self, data: dict, status: int = 200):
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()
        self.wfile.write(json.dumps(data).encode("utf-8"))

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path

        if path == "/api/status":
            summary = self.agent.get_capabilities_summary()
            self._send_json(summary)
            return

        if path == "/api/tools":
            tools = self.agent.mcp.list_tools()
            self._send_json({"tools": tools})
            return

        if path == "/api/prompts":
            prompts = self.agent.mcp.list_prompts()
            self._send_json({"prompts": prompts})
            return

        if path == "/api/skill":
            qs = urllib.parse.parse_qs(parsed.query)
            name = qs.get("name", ["setup-timescaledb-hypertables"])[0]
            try:
                content = self.agent.mcp.view_skill(skill_name=name, path=".")
                self._send_json({"name": name, "content": content})
            except Exception as e:
                self._send_json({"error": str(e)}, status=500)
            return

        # Fallback to static files
        super().do_GET()

    def do_POST(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path

        content_length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_length).decode("utf-8")
        data = json.loads(body) if body else {}

        if path == "/api/search":
            query = data.get("query", "")
            limit = int(data.get("limit", 5))
            semantic_weight = float(data.get("semantic_weight", 0.7))
            try:
                results = self.agent.mcp.search_docs(
                    query=query,
                    limit=limit,
                    semantic_weight=semantic_weight,
                )
                self._send_json({"query": query, "results": results})
            except Exception as e:
                self._send_json({"error": str(e)}, status=500)
            return

        if path == "/api/ask":
            prompt = data.get("prompt", "")
            service_id = data.get("service_id", None)
            try:
                res = self.agent.ask(user_prompt=prompt, target_service_id=service_id)
                self._send_json(res)
            except Exception as e:
                self._send_json({"error": str(e)}, status=500)
            return

        self._send_json({"error": "Endpoint not found"}, status=404)


def run_server(port: int = 8080, mcp_client: Optional[TigerMCPClient] = None, guardrails: Optional[TigerGuardrails] = None):
    mcp = mcp_client or TigerMCPClient()
    guards = guardrails or TigerGuardrails()
    agent = TigerAgent(mcp_client=mcp, guardrails=guards)
    agent.start()

    TigerAgentHTTPHandler.agent = agent

    server_address = ("", port)
    httpd = http.server.HTTPServer(server_address, TigerAgentHTTPHandler)
    print(f"\n🐅 Tiger Agent Web Dashboard running at: http://localhost:{port}/")
    print("Press Ctrl+C to stop.\n")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping server...")
    finally:
        agent.stop()
        httpd.server_close()
