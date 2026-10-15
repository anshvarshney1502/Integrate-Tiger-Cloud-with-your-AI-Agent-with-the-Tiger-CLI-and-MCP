"""
Tiger Agent Guardrails: Enforces security policies, read-only permissions, and query safety.
"""

import re
from typing import Any, Dict, List, Optional, Tuple


class GuardrailViolation(Exception):
    """Raised when an operation violates defined safety policies."""
    pass


class TigerGuardrails:
    """
    Enforces safe interactions between AI agents and Tiger Cloud resources.
    Protects production environments, prevents runaway queries, and enforces
    safe testing on service forks.
    """

    MUTATING_SERVICE_TOOLS = {
        "service_create",
        "service_delete",
        "service_fork",
        "service_resize",
        "service_start",
        "service_stop",
        "service_rename",
        "service_update_password",
    }

    DESTRUCTIVE_SQL_PATTERNS = [
        re.compile(r"\bDROP\s+(DATABASE|SCHEMA|TABLE|INDEX)\b", re.IGNORECASE),
        re.compile(r"\bTRUNCATE\b", re.IGNORECASE),
        re.compile(r"\bALTER\s+TABLE\s+.*\s+DROP\s+COLUMN\b", re.IGNORECASE),
        re.compile(r"\bDELETE\s+FROM\s+\w+\s*(;|$)", re.IGNORECASE),  # DELETE without WHERE
        re.compile(r"\bUPDATE\s+\w+\s+SET\s+.*\s*(;|$)", re.IGNORECASE),  # UPDATE without WHERE
    ]

    def __init__(
        self,
        mode: str = "prod",
        prod_services: Optional[List[str]] = None,
        max_limit: int = 100,
        enforce_fork_for_migrations: bool = True,
    ):
        """
        Args:
            mode: 'prod' (protect PROD services), 'all' (read-only for all), 'off' (unrestricted).
            prod_services: List of service IDs considered production.
            max_limit: Default row limit to inject or verify on SELECT queries.
            enforce_fork_for_migrations: Require schema migrations to be tested on forks.
        """
        self.mode = mode.lower()
        self.prod_services = set(prod_services or [])
        self.max_limit = max_limit
        self.enforce_fork_for_migrations = enforce_fork_for_migrations

    def validate_tool_call(self, tool_name: str, arguments: Dict[str, Any]) -> None:
        """
        Verify if a tool call is permitted under the current guardrail policy.
        """
        if self.mode == "all" and tool_name in self.MUTATING_SERVICE_TOOLS:
            raise GuardrailViolation(
                f"Tool '{tool_name}' blocked: mode 'all' enforces strict read-only across all services."
            )

        if self.mode == "prod" and tool_name in self.MUTATING_SERVICE_TOOLS:
            target_service = arguments.get("service_id")
            if target_service and target_service in self.prod_services:
                raise GuardrailViolation(
                    f"Tool '{tool_name}' blocked on production service '{target_service}'. "
                    f"Create a service fork first using 'service_fork' to test changes safely."
                )

        if tool_name == "db_query":
            self.validate_sql_query(
                arguments.get("query", ""),
                service_id=arguments.get("service_id"),
            )

    def validate_sql_query(self, query: str, service_id: Optional[str] = None) -> None:
        """
        Inspect SQL queries for dangerous or unconstrained operations.
        """
        clean_query = query.strip()
        if not clean_query:
            return

        is_prod = service_id in self.prod_services if service_id else False

        # In read-only mode or on PROD, disallow any non-SELECT / non-EXPLAIN statements
        if self.mode == "all" or (self.mode == "prod" and is_prod):
            first_word = clean_query.split()[0].upper()
            if first_word not in {"SELECT", "EXPLAIN", "SHOW", "WITH"}:
                raise GuardrailViolation(
                    f"Write/DDL query rejected on protected target (Service: {service_id or 'all'}). "
                    f"Query starts with '{first_word}'. Only read-only queries are permitted."
                )

        # Check for catastrophic unconstrained DELETE or UPDATE without WHERE
        for pattern in self.DESTRUCTIVE_SQL_PATTERNS:
            if pattern.search(clean_query):
                raise GuardrailViolation(
                    f"Potentially destructive query rejected: matches pattern '{pattern.pattern}'. "
                    f"Ensure operations specify explicit WHERE clauses or test on a fork."
                )

    def sanitize_select_limit(self, query: str) -> str:
        """
        Inject a reasonable LIMIT if a SELECT query does not specify one,
        preventing unexpected memory spikes or large data egress.
        """
        trimmed = query.strip()
        if trimmed.upper().startswith("SELECT") and not re.search(r"\bLIMIT\s+\d+", trimmed, re.IGNORECASE):
            # If the query ends with a semicolon, strip it and append LIMIT
            if trimmed.endswith(";"):
                trimmed = trimmed[:-1].strip()
            return f"{trimmed} LIMIT {self.max_limit};"
        return query
