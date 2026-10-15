"""
Tiger Agent CLI: Command-line interface for the Tiger AI Agent.
"""

import argparse
import json
import sys
from typing import Optional

from .agent import TigerAgent
from .guardrails import TigerGuardrails
from .mcp_client import TigerMCPClient


def main():
    parser = argparse.ArgumentParser(
        prog="tiger-agent",
        description="Interact with Tiger Cloud using AI Agent, Tiger CLI, and Tiger MCP",
    )
    parser.add_argument("--read-only", choices=["prod", "all", "off"], default="prod", help="Guardrail read-only policy")
    parser.add_argument("--cli-path", default=None, help="Path to tiger CLI binary")

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Command: status
    subparsers.add_parser("status", help="Show Tiger MCP connection and capability status")

    # Command: tools
    subparsers.add_parser("tools", help="List all Tiger MCP tools")

    # Command: prompts (skills)
    subparsers.add_parser("prompts", help="List all Tiger MCP prompts / skills")

    # Command: docs
    docs_parser = subparsers.add_parser("docs", help="Search Tiger Data documentation")
    docs_parser.add_argument("query", help="Documentation search query")
    docs_parser.add_argument("--limit", type=int, default=3, help="Max results")

    # Command: skill
    skill_parser = subparsers.add_parser("skill", help="View a built-in Tiger MCP skill")
    skill_parser.add_argument("name", help="Name of the skill (e.g. setup-timescaledb-hypertables)")

    # Command: chat
    chat_parser = subparsers.add_parser("chat", help="Start an interactive chat session with the AI Agent")
    chat_parser.add_argument("--service-id", default=None, help="Target service ID for queries")

    # Command: serve
    serve_parser = subparsers.add_parser("serve", help="Launch the local Web Dashboard")
    serve_parser.add_argument("--port", type=int, default=8080, help="Port to listen on")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(0)

    guardrails = TigerGuardrails(mode=args.read_only)
    mcp_client = TigerMCPClient(cli_path=args.cli_path, read_only_mode=args.read_only)

    if args.command == "serve":
        from .server import run_server
        run_server(port=args.port, mcp_client=mcp_client, guardrails=guardrails)
        return

    agent = TigerAgent(mcp_client=mcp_client, guardrails=guardrails)
    with agent:
        if args.command == "status":
            summary = agent.get_capabilities_summary()
            print("\n🐅 Tiger MCP Status:")
            print(f"  • Server: {summary['server_info'].get('title')} v{summary['server_info'].get('version')}")
            print(f"  • Tools: {summary['tools_count']} available")
            print(f"  • Built-in Skills: {summary['prompts_count']} available")
            print(f"  • Guardrail Mode: {summary['guardrail_mode'].upper()}\n")

        elif args.command == "tools":
            tools = agent.mcp.list_tools()
            print(f"\n🐅 Tiger MCP Tools ({len(tools)}):")
            for t in tools:
                print(f"  - {t['name']}: {t.get('description', '').strip()[:80]}...")
            print()

        elif args.command == "prompts":
            prompts = agent.mcp.list_prompts()
            print(f"\n🐅 Tiger MCP Built-in Skills & Prompts ({len(prompts)}):")
            for p in prompts:
                print(f"  - {p['name']}: {p.get('description', '').strip()[:80]}...")
            print()

        elif args.command == "docs":
            print(f"\n🔍 Searching Tiger Data docs for: '{args.query}'...\n")
            results = agent.mcp.search_docs(query=args.query, limit=args.limit)
            for i, r in enumerate(results, 1):
                title = r.get("title") or r.get("id") or f"Result {i}"
                content = r.get("content", "").strip()[:200].replace("\n", " ")
                print(f"[{i}] {title}\n    {content}...\n")

        elif args.command == "skill":
            print(f"\n📘 Retrieving Tiger MCP Skill: '{args.name}'...\n")
            content = agent.mcp.view_skill(skill_name=args.name, path=".")
            print(content)
            print()

        elif args.command == "chat":
            print("\n🤖 Welcome to Tiger Agent CLI Chat! Type 'exit' or 'quit' to stop.\n")
            while True:
                try:
                    user_input = input("tiger-agent> ").strip()
                    if not user_input:
                        continue
                    if user_input.lower() in ["exit", "quit"]:
                        print("Goodbye!")
                        break
                    res = agent.ask(user_input, target_service_id=args.service_id)
                    print("\n" + res.get("answer", json.dumps(res, indent=2)) + "\n")
                except (KeyboardInterrupt, EOFError):
                    print("\nExiting...")
                    break


if __name__ == "__main__":
    main()
