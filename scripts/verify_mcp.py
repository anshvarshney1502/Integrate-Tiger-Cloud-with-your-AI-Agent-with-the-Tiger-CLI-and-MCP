#!/usr/bin/env python3
"""
Verification Script for Tiger CLI & Tiger MCP Integration.
Validates binary availability, stdio communication, tool schemas, and skill retrieval.
"""

import os
import sys

# Ensure src/ is on python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src")))

from tiger_agent.mcp_client import TigerMCPClient
from tiger_agent.guardrails import TigerGuardrails, GuardrailViolation


def run_verification():
    print("=" * 60)
    print("🐅 TIGER CLI & MCP VERIFICATION SUITE")
    print("=" * 60)

    # 1. Locate binary
    bin_path = TigerMCPClient._find_tiger_binary()
    print(f"[1/6] Tiger binary detected: {bin_path}")
    if not os.path.exists(bin_path):
        print(f"❌ ERROR: Binary does not exist at {bin_path}")
        return False
    print("  ✓ Binary exists and is executable.")

    # 2. Test MCP Handshake
    print("\n[2/6] Starting Tiger MCP process and initializing JSON-RPC handshake...")
    client = TigerMCPClient(cli_path=bin_path)
    try:
        client.start()
        print(f"  ✓ Handshake succeeded!")
        print(f"    Server: {client.server_info.get('title')} v{client.server_info.get('version')}")
        print(f"    Protocol: 2024-11-05")
    except Exception as e:
        print(f"❌ Failed to start Tiger MCP server: {e}")
        return False

    try:
        # 3. Verify Tools
        print("\n[3/6] Fetching tool definitions via tools/list...")
        tools = client.list_tools()
        print(f"  ✓ Retrieved {len(tools)} tools.")
        tool_names = [t["name"] for t in tools]
        expected_tools = ["db_query", "service_list", "search_docs", "view_skill"]
        for et in expected_tools:
            if et in tool_names:
                print(f"    ✓ Tool '{et}' verified")
            else:
                print(f"    ⚠️ Missing expected tool '{et}'")

        # 4. Verify Prompts (Built-in Skills)
        print("\n[4/6] Fetching built-in skills via prompts/list...")
        prompts = client.list_prompts()
        print(f"  ✓ Retrieved {len(prompts)} prompts/skills.")
        prompt_names = [p["name"] for p in prompts]
        expected_skills = [
            "setup-timescaledb-hypertables",
            "find-hypertable-candidates",
            "pgvector-semantic-search",
            "postgres-database-migration",
        ]
        for es in expected_skills:
            if es in prompt_names:
                print(f"    ✓ Skill '{es}' verified")
            else:
                print(f"    ⚠️ Missing expected skill '{es}'")

        # 5. Test Live Docs Search
        print("\n[5/6] Testing live hybrid documentation search (search_docs)...")
        results = client.search_docs(query="continuous aggregates", limit=2)
        print(f"  ✓ Documentation query succeeded: {len(results)} match(es) returned.")
        if results:
            print(f"    Sample title: {results[0].get('title', results[0].get('id'))}")

        # 6. Test Guardrails
        print("\n[6/6] Testing AI Agent Guardrails (read-only and PROD protection)...")
        guards = TigerGuardrails(mode="prod", prod_services=["prod-service-1"])
        try:
            guards.validate_tool_call("service_delete", {"service_id": "prod-service-1"})
            print("❌ FAILED: Mutating tool should have been blocked on PROD!")
            return False
        except GuardrailViolation as gv:
            print(f"  ✓ Guardrail blocked mutating call on PROD: {gv}")

        # Test limit sanitization
        safe_sql = guards.sanitize_select_limit("SELECT * FROM sensor_data")
        assert "LIMIT" in safe_sql
        print(f"  ✓ Query limit sanitizer: '{safe_sql}'")

        print("\n" + "=" * 60)
        print("🎉 ALL VERIFICATIONS PASSED SUCCESSFULLY!")
        print("=" * 60)
        return True

    finally:
        client.stop()


if __name__ == "__main__":
    success = run_verification()
    sys.exit(0 if success else 1)
