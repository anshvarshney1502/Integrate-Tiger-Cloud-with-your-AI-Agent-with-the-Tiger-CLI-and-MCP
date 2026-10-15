# Integrate Tiger Cloud with your AI Agent with Tiger CLI and MCP

[![Tiger MCP](https://img.shields.io/badge/Tiger%20MCP-v0.26.0-orange?style=flat-square&logo=postgresql)](https://www.tigerdata.com/docs/get-started/quickstart/mcp-cli)
[![TimescaleDB](https://img.shields.io/badge/TimescaleDB-Hypertables-blue?style=flat-square)](https://www.tigerdata.com)
[![Protocol](https://img.shields.io/badge/MCP-2024--11--05-brightgreen?style=flat-square)](https://modelcontextprotocol.io)
[![License](https://img.shields.io/badge/license-MIT-purple?style=flat-square)](LICENSE)

A production-ready integration framework, AI agent, and developer toolkit connecting **Tiger Cloud** (managed TimescaleDB / PostgreSQL) to AI coding agents (**Antigravity**, **Claude Code**, **Cursor**, **VS Code**, **Devin**, **Codex**, and **Gemini CLI**) via the **Tiger CLI** and the **Model Context Protocol (MCP)**.

---

## 🌟 Overview

**Tiger MCP** gives AI agents programmatic, natural-language access to Tiger Cloud. Bundled directly inside the `tiger` CLI binary, Tiger MCP exposes:
- **19 MCP Tools** for database service lifecycle operations, metrics observation, and SQL querying.
- **11 Built-in MCP Skills & Prompts** for time-series hypertable design, migration planning, candidate evaluation, pgvector search, and hyperfunctions.
- **Hybrid Semantic & BM25 Documentation Search** wired to Tiger Data and PostgreSQL docs, allowing agents to ground answers in authoritative, up-to-date guidance.
- **Configurable Safety Guardrails** supporting read-only protection (`prod`, `all`, `off`), dangerous DDL blocking, and automatic query row limits.

---

## 🏗️ Architecture & Comparison: Where Each Fits

Tiger Cloud provides three complementary interaction layers:

```
┌─────────────────────────────────────────────────────────────┐
│                       AI Coding Agent                       │
│        (Antigravity / Claude Code / Cursor / Gemini)        │
└──────────────────────────────┬──────────────────────────────┘
                               │  JSON-RPC 2.0 (stdio)
                               ▼
┌─────────────────────────────────────────────────────────────┐
│                 Tiger CLI Binary (`tiger`)                  │
│                                                             │
│   ┌─────────────────────────────────────────────────────┐   │
│   │                 Tiger MCP Server                    │   │
│   │                                                     │   │
│   │  • 19 Typed MCP Tools (service_*, db_query, ...)    │   │
│   │  • 11 Built-in Skills (hypertables, pgvector, ...)  │   │
│   │  • Hybrid Docs Search (vector + BM25 keyword)       │   │
│   │  • Safety Guardrails (read_only=prod / all / off)   │   │
│   └──────────────────────────┬──────────────────────────┘   │
│                              │                              │
│   ┌──────────────────────────┴──────────────────────────┐   │
│   │            Command Line Interface (CLI)             │   │
│   │     `tiger service *`, `tiger db *`, `tiger auth`   │   │
│   └──────────────────────────┬──────────────────────────┘   │
└──────────────────────────────┼──────────────────────────────┘
                               │ HTTPS / TLS (OAuth 2.0 / API)
                               ▼
┌─────────────────────────────────────────────────────────────┐
│                 Tiger Cloud Platform & DB                   │
│         (Managed PostgreSQL, TimescaleDB, pgvector)         │
└─────────────────────────────────────────────────────────────┘
```

| Layer | Primary Audience | Best Used For | Execution Style |
| :--- | :--- | :--- | :--- |
| **Tiger MCP** | AI Agents (Claude, Antigravity, Cursor) | Reasoning, natural language exploration, schema advice, docs search, assisted operations | Dynamic / Agentic |
| **Tiger CLI** | Developers & CI/CD Pipelines | Explicit, deterministic scripting, migrations, interactive `psql`, connection strings | Deterministic / Scriptable |
| **Tiger REST API** | Applications & Backend Services | Custom backend integrations, programmatic orchestration in custom languages | HTTP / API |

### CLI Commands vs. MCP Tools

| Operation | Tiger CLI Command | Tiger MCP Tool | Guardrail Protection |
| :--- | :--- | :--- | :--- |
| **Create Service** | `tiger service create` | `service_create` | Blocked if `read_only=all` |
| **List Services** | `tiger service list` | `service_list` | Allowed in read-only |
| **Get Service Info** | `tiger service get <id>` | `service_get` | Allowed in read-only |
| **Fork Service** | `tiger service fork <id>` | `service_fork` | Safe testing workflow |
| **Resize Service** | `tiger service resize <id>` | `service_resize` | Blocked on PROD services |
| **Execute SQL** | `tiger db query <id> -c "..."` | `db_query` | Enforces read-only DDL blocks & row limits |
| **Interactive psql** | `tiger db psql <id>` | *(CLI only)* | Interactive terminal session |
| **Search Documentation** | *(MCP only)* | `search_docs` | Hybrid semantic + BM25 search |
| **Built-in Skill Guide** | *(MCP only)* | `view_skill` | Authoritative optimization guides |

---

## ⚡ Quickstart Guide

### 1. Install the Tiger CLI
Install Tiger CLI across macOS, Linux, or Windows:

```bash
# macOS (Homebrew)
brew install --cask timescale/tap/tiger-cli

# Linux / macOS (Direct install script)
curl -fsSL https://cli.tigerdata.com | sh
```

Or run the automated setup script included in this repository:
```bash
./scripts/setup_tiger.sh antigravity
```

### 2. Authenticate Tiger CLI
In your terminal, sign in with OAuth 2.0:
```bash
tiger auth login
```
*(For headless or remote environments, run `tiger auth login --headless`)*

Confirm your authentication:
```bash
tiger service list
```

### 3. Install Tiger MCP for your AI Agent
Configure your agent client with a single command:

```bash
# Google Antigravity
tiger mcp install antigravity

# Claude Code
tiger mcp install claude-code

# Cursor
tiger mcp install cursor

# VS Code
tiger mcp install vscode

# Gemini CLI
tiger mcp install gemini
```

---

## 🛡️ Working Safely with AI Agents

To ensure AI agents cannot inadvertently alter production data or run runaway queries:

1. **Enforce Read-Only Mode**:
   ```bash
   # Protect services tagged PROD (Recommended for agents)
   tiger config set read_only prod

   # Protect all services (Complete read-only)
   tiger config set read_only all
   ```
2. **Always Fork Production to Test Changes**:
   ```bash
   tiger service fork <prod-service-id>
   ```
   Or ask your agent: *"Fork service prod-123 so I can test this hypertable migration."*
3. **Dedicated Read-Only Database Roles**:
   Connect agents using a least-privilege read-only role (`tiger db create role <id> --name readonly --read-only`).
4. **Project Instructions (`CLAUDE.md`)**:
   Keep production guardrails in your project repository to prevent unapproved mutations.

---

## 🚀 Repository Contents & Features

```
├── CLAUDE.md                   # AI Agent safety rules and guardrails checklist
├── .agent-rules                # Antigravity agent configuration & safety policies
├── dashboard/                  # Interactive Web UI for Tiger MCP & Agent Chat
│   ├── index.html              # Modern dark-mode dashboard
│   ├── style.css               # Styling
│   └── app.js                  # Frontend client communicating with agent API
├── mcp_configs/                # Ready-to-use client JSON configurations
│   ├── antigravity.json        # Google Antigravity configuration
│   ├── claude_code.json        # Anthropic Claude Code configuration
│   ├── cursor.json             # Cursor IDE configuration
│   ├── gemini_cli.json         # Gemini CLI configuration
│   └── vscode.json             # Visual Studio Code configuration
├── scripts/
│   ├── setup_tiger.sh          # One-click installer & configurator
│   └── verify_mcp.py           # Comprehensive verification test suite
├── sql/                        # Production-grade SQL patterns & skills
│   ├── 01_iot_hypertable.sql   # Hypertables, compression & continuous aggregates
│   ├── 02_pgvector_search.sql  # AI vector similarity search with HNSW indexes
│   ├── 03_hybrid_bm25_vector.sql # Reciprocal Rank Fusion (RRF) hybrid search
│   ├── 04_timescaledb_hyperfunctions.sql # Financial OHLCV & percentiles
│   └── 05_zero_downtime_migrations.sql   # Safe zero-downtime DDL patterns
├── src/tiger_agent/            # Core Python framework
│   ├── mcp_client.py           # Robust JSON-RPC 2.0 stdio MCP client
│   ├── guardrails.py           # Production safety & query limit enforcer
│   ├── agent.py                # Intelligent agent reasoning engine
│   ├── cli.py                  # Terminal CLI interface (chat, docs, skills)
│   └── server.py               # Lightweight dashboard HTTP & API server
└── tests/                      # Automated unit test suite
    ├── test_guardrails.py      # Tests for guardrail policies & sanitization
    └── test_mcp_client.py      # Tests for MCP handshake, tools & skills
```

---

## 💻 Running the Tiger AI Agent

### 1. Verification Suite
Verify your Tiger CLI installation, MCP stdio communication, tool listing, documentation search, and guardrails:
```bash
python3 scripts/verify_mcp.py
```

### 2. Interactive Terminal Chat
Start an interactive conversation with the Tiger Agent in your terminal:
```bash
python3 -m tiger_agent.cli chat
```

### 3. Built-in Skills Inspection
Inspect any built-in TimescaleDB skill directly from the CLI:
```bash
python3 -m tiger_agent.cli skill setup-timescaledb-hypertables
```

### 4. Hybrid Documentation Search
Search official Tiger Data documentation:
```bash
python3 -m tiger_agent.cli docs "compression policy chunk interval"
```

### 5. Launch the Local Web Dashboard
Run the included web dashboard:
```bash
python3 -m tiger_agent.cli serve --port 8080
```
Open [http://localhost:8080](http://localhost:8080) in your browser to interactively explore tools, query documentation, inspect skills, and chat with the agent!

---

## 🧪 Running Unit Tests

Run the full test suite with:
```bash
python3 -m unittest discover tests
```

---

## 📚 References & Links

- [Tiger Data MCP Quickstart](https://www.tigerdata.com/docs/get-started/quickstart/mcp-cli)
- [Get Started with Tiger CLI](https://www.tigerdata.com/docs/get-started/quickstart/tiger-cli)
- [Tiger CLI & Tiger MCP Comparison](https://www.tigerdata.com/docs/learn/tiger-cli-mcp)
- [Tiger Cloud Agent Best Practices](https://www.tigerdata.com/docs/build/tiger-cli-mcp/agent-best-practices)
- [Model Context Protocol (MCP) Specification](https://modelcontextprotocol.io)

---

## 📄 License
MIT License. Built for the developer community and Hacktoberfest 2026.
