"""
Tiger MCP Client: Communicates with Tiger MCP server via JSON-RPC 2.0 over stdio.
"""

import json
import logging
import os
import shutil
import subprocess
from typing import Any, Dict, List, Optional

logger = logging.getLogger("tiger_agent.mcp_client")


class TigerMCPClient:
    """
    Client for interacting with the Tiger MCP server process (`tiger mcp start`).
    Handles process lifecycle, protocol handshakes, and JSON-RPC dispatching.
    """

    def __init__(self, cli_path: Optional[str] = None, read_only_mode: Optional[str] = None):
        """
        Args:
            cli_path: Absolute or relative path to the `tiger` CLI binary.
                      Defaults to discovering from PATH or ~/.local/bin/tiger.
            read_only_mode: Optional 'prod', 'all', or 'off' to enforce read-only safety.
        """
        self.cli_path = cli_path or self._find_tiger_binary()
        self.read_only_mode = read_only_mode
        self._proc: Optional[subprocess.Popen] = None
        self._msg_id = 0
        self.server_info: Dict[str, Any] = {}
        self.capabilities: Dict[str, Any] = {}
        self.instructions: str = ""

    @staticmethod
    def _find_tiger_binary() -> str:
        """Find the tiger CLI binary in common locations or PATH."""
        # 1. Environment variable override
        if os.environ.get("TIGER_CLI_PATH"):
            return os.environ["TIGER_CLI_PATH"]

        # 2. System PATH
        which_path = shutil.which("tiger")
        if which_path:
            return which_path

        # 3. Standard local user installation path
        home_local = os.path.expanduser("~/.local/bin/tiger")
        if os.path.isfile(home_local) and os.access(home_local, os.X_OK):
            return home_local

        # 4. Standard Homebrew paths
        brew_paths = ["/opt/homebrew/bin/tiger", "/usr/local/bin/tiger"]
        for p in brew_paths:
            if os.path.isfile(p) and os.access(p, os.X_OK):
                return p

        # Default fallback
        return "tiger"

    def start(self) -> "TigerMCPClient":
        """Spawn the `tiger mcp start` background process and perform handshake."""
        if self._proc is not None:
            return self

        env = os.environ.copy()
        if self.read_only_mode:
            env["TIGER_READ_ONLY"] = self.read_only_mode

        logger.info(f"Starting Tiger MCP server with binary: {self.cli_path}")
        try:
            self._proc = subprocess.Popen(
                [self.cli_path, "mcp", "start"],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1,
                env=env,
            )
        except FileNotFoundError as exc:
            raise RuntimeError(
                f"Tiger CLI not found at '{self.cli_path}'. "
                "Install it with: curl -fsSL https://cli.tigerdata.com | sh"
            ) from exc

        # Perform MCP initialize handshake
        self._initialize()
        return self

    def _next_id(self) -> int:
        self._msg_id += 1
        return self._msg_id

    def _send_request(self, method: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Send a JSON-RPC request and wait for the response."""
        if not self._proc or not self._proc.stdin or not self._proc.stdout:
            raise RuntimeError("Tiger MCP server process is not running.")

        req_id = self._next_id()
        payload = {
            "jsonrpc": "2.0",
            "id": req_id,
            "method": method,
            "params": params if params is not None else {},
        }

        req_str = json.dumps(payload) + "\n"
        self._proc.stdin.write(req_str)
        self._proc.stdin.flush()

        line = self._proc.stdout.readline()
        if not line:
            stderr_out = self._proc.stderr.read() if self._proc.stderr else ""
            raise RuntimeError(f"Tiger MCP server terminated unexpectedly: {stderr_out}")

        res = json.loads(line)
        if "error" in res:
            err = res["error"]
            raise RuntimeError(f"Tiger MCP error {err.get('code')}: {err.get('message')}")

        return res.get("result", {})

    def _send_notification(self, method: str, params: Optional[Dict[str, Any]] = None) -> None:
        """Send a JSON-RPC notification (no response expected)."""
        if not self._proc or not self._proc.stdin:
            raise RuntimeError("Tiger MCP server process is not running.")

        payload = {
            "jsonrpc": "2.0",
            "method": method,
            "params": params if params is not None else {},
        }
        self._proc.stdin.write(json.dumps(payload) + "\n")
        self._proc.stdin.flush()

    def _initialize(self) -> None:
        """Execute MCP initialize and initialized notification sequence."""
        res = self._send_request(
            "initialize",
            {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "tiger-ai-agent", "version": "1.0.0"},
            },
        )
        self.server_info = res.get("serverInfo", {})
        self.capabilities = res.get("capabilities", {})
        self.instructions = res.get("instructions", "")
        self._send_notification("notifications/initialized")

    def list_tools(self) -> List[Dict[str, Any]]:
        """List all tools exposed by the Tiger MCP server."""
        res = self._send_request("tools/list")
        return res.get("tools", [])

    def list_prompts(self) -> List[Dict[str, Any]]:
        """List all prompts / skills exposed by the Tiger MCP server."""
        res = self._send_request("prompts/list")
        return res.get("prompts", [])

    def call_tool(self, name: str, arguments: Dict[str, Any]) -> Any:
        """Call a specific tool on the Tiger MCP server."""
        res = self._send_request("tools/call", {"name": name, "arguments": arguments})
        return res

    def search_docs(
        self,
        query: str,
        source: str = "tiger",
        limit: int = 5,
        semantic_weight: float = 0.7,
    ) -> List[Dict[str, Any]]:
        """
        Search Tiger Data or PostgreSQL documentation using hybrid semantic and keyword search.
        """
        res = self.call_tool(
            "search_docs",
            {
                "query": query,
                "source": source,
                "limit": limit,
                "semanticWeight": semantic_weight,
            },
        )
        content_items = res.get("content", [])
        if not content_items:
            return []
        first_item = content_items[0]
        if first_item.get("type") == "text":
            try:
                data = json.loads(first_item["text"])
                return data.get("results", [])
            except json.JSONDecodeError:
                return [{"content": first_item["text"]}]
        return content_items

    def view_skill(self, skill_name: str, path: str = ".") -> str:
        """
        Retrieve built-in skill documentation or lists of skills.
        """
        res = self.call_tool("view_skill", {"skill_name": skill_name, "path": path})
        content_items = res.get("content", [])
        if content_items and content_items[0].get("type") == "text":
            return content_items[0]["text"]
        return str(res)

    def list_services(self) -> Any:
        """List database services in Tiger Cloud."""
        return self.call_tool("service_list", {})

    def stop(self) -> None:
        """Terminate the Tiger MCP server process cleanly."""
        if self._proc:
            try:
                if self._proc.stdin:
                    self._proc.stdin.close()
                if self._proc.stdout:
                    self._proc.stdout.close()
                if self._proc.stderr:
                    self._proc.stderr.close()
                self._proc.terminate()
                self._proc.wait(timeout=3)
            except Exception:
                self._proc.kill()
            finally:
                self._proc = None

    def __enter__(self):
        return self.start()

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.stop()
