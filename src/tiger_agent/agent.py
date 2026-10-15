"""
Tiger AI Agent: Intelligent assistant powered by Tiger MCP tools, built-in skills, and guardrails.
"""

import json
import logging
import os
import re
from typing import Any, Dict, List, Optional

from .guardrails import TigerGuardrails, GuardrailViolation
from .mcp_client import TigerMCPClient

logger = logging.getLogger("tiger_agent.agent")


class TigerAgent:
    """
    Autonomous and interactive AI Agent interfacing with Tiger Cloud.
    Leverages Tiger MCP for tools and skills, with guardrails for safe execution.
    """

    def __init__(
        self,
        mcp_client: Optional[TigerMCPClient] = None,
        guardrails: Optional[TigerGuardrails] = None,
    ):
        self.mcp = mcp_client or TigerMCPClient()
        self.guardrails = guardrails or TigerGuardrails()
        self._initialized = False

    def start(self) -> "TigerAgent":
        """Initialize the MCP client connection and load capabilities."""
        if not self._initialized:
            self.mcp.start()
            self._initialized = True
        return self

    def stop(self) -> None:
        """Shut down the agent and MCP process."""
        if self._initialized:
            self.mcp.stop()
            self._initialized = False

    def __enter__(self):
        return self.start()

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.stop()

    def get_capabilities_summary(self) -> Dict[str, Any]:
        """Return a structured overview of available Tiger MCP tools and prompts."""
        tools = self.mcp.list_tools()
        prompts = self.mcp.list_prompts()
        return {
            "server_info": self.mcp.server_info,
            "instructions": self.mcp.instructions,
            "tools_count": len(tools),
            "prompts_count": len(prompts),
            "tools": [{"name": t["name"], "description": t.get("description", "")} for t in tools],
            "prompts": [{"name": p["name"], "description": p.get("description", "")} for p in prompts],
            "guardrail_mode": self.guardrails.mode,
        }

    def ask(self, user_prompt: str, target_service_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Process a natural language user request and execute relevant MCP tools or skills.
        """
        prompt_lower = user_prompt.lower()

        # 1. Check if the user is asking about Tiger MCP status or capabilities
        if any(w in prompt_lower for w in ["status", "capabilities", "is the tiger mcp server active", "active"]):
            summary = self.get_capabilities_summary()
            return {
                "type": "status",
                "answer": (
                    f"Yes! The Tiger MCP server '{summary['server_info'].get('title', 'Tiger MCP')}' "
                    f"(v{summary['server_info'].get('version', 'unknown')}) is active with "
                    f"{summary['tools_count']} tools and {summary['prompts_count']} built-in skills.\n"
                    f"Current Guardrail Mode: {self.guardrails.mode.upper()}."
                ),
                "data": summary,
            }

        # 2. Check if user is asking to list services
        if "list" in prompt_lower and ("service" in prompt_lower or "services" in prompt_lower):
            self.guardrails.validate_tool_call("service_list", {})
            try:
                res = self.mcp.list_services()
                return {
                    "type": "service_list",
                    "answer": "Here are your active Tiger Cloud services:",
                    "data": res,
                }
            except Exception as e:
                return {
                    "type": "error",
                    "answer": f"Could not list services from Tiger Cloud: {e}",
                    "tip": "Ensure you are authenticated with 'tiger auth login' or have set credentials.",
                }

        # 3. Check if user is searching documentation
        doc_match = re.search(r"(?:search|find|docs|documentation|about)\s+(?:about\s+)?([a-z0-9_\- ]+)", prompt_lower)
        if any(w in prompt_lower for w in ["docs", "documentation", "how to", "search docs"]):
            query = user_prompt
            if doc_match:
                query = doc_match.group(1).replace("documentation", "").replace("docs", "").strip()
            if not query:
                query = user_prompt

            results = self.mcp.search_docs(query=query, limit=4)
            return {
                "type": "documentation",
                "query": query,
                "answer": f"Found {len(results)} relevant section(s) in Tiger Data documentation for '{query}':",
                "results": results,
            }

        # 4. Check if user wants a built-in skill (hypertables, pgvector, migration, postgis)
        skill_map = {
            "hypertable": "setup-timescaledb-hypertables",
            "candidate": "find-hypertable-candidates",
            "vector": "pgvector-semantic-search",
            "embedding": "pgvector-semantic-search",
            "rag": "pgvector-semantic-search",
            "migration": "postgres-database-migration",
            "hybrid": "postgres-hybrid-text-search",
            "postgis": "design-postgis-tables",
            "hyperfunction": "timescaledb-hyperfunctions",
        }
        for keyword, skill_name in skill_map.items():
            if keyword in prompt_lower and any(w in prompt_lower for w in ["skill", "guide", "design", "best practice", "how to"]):
                skill_content = self.mcp.view_skill(skill_name, path=".")
                return {
                    "type": "skill",
                    "skill_name": skill_name,
                    "answer": f"Retrieved Tiger MCP built-in skill: {skill_name}",
                    "content": skill_content,
                }

        # 5. Check if user wants to execute a query
        if prompt_lower.startswith("select") or prompt_lower.startswith("explain") or "query" in prompt_lower:
            query = user_prompt
            if "query:" in user_prompt:
                query = user_prompt.split("query:", 1)[1].strip()

            # Apply query limit sanitization & validation
            safe_query = self.guardrails.sanitize_select_limit(query)
            try:
                self.guardrails.validate_sql_query(safe_query, service_id=target_service_id)
            except GuardrailViolation as gv:
                return {
                    "type": "guardrail_violation",
                    "error": str(gv),
                    "query": safe_query,
                }

            if not target_service_id:
                return {
                    "type": "dry_run_sql",
                    "answer": f"Validated SQL query for execution (no service_id specified):\n\n```sql\n{safe_query}\n```",
                    "query": safe_query,
                    "status": "ready_to_execute",
                }

            try:
                res = self.mcp.call_tool(
                    "db_query",
                    {"service_id": target_service_id, "query": safe_query},
                )
                return {
                    "type": "query_result",
                    "query": safe_query,
                    "result": res,
                }
            except Exception as e:
                return {
                    "type": "query_error",
                    "error": str(e),
                    "query": safe_query,
                }

        # 6. Fallback: Search docs and offer tailored suggestions
        results = self.mcp.search_docs(query=user_prompt, limit=3)
        return {
            "type": "general_assistance",
            "answer": (
                f"I parsed your request with Tiger MCP. Here is relevant guidance from "
                f"Tiger Data documentation to help implement this:"
            ),
            "results": results,
            "recommended_tools": ["db_query", "service_create", "view_skill"],
        }
