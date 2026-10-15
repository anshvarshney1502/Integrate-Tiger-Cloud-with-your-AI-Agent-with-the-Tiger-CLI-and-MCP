import os
import sys
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src")))

from tiger_agent.guardrails import TigerGuardrails, GuardrailViolation


class TestTigerGuardrails(unittest.TestCase):

    def test_allow_read_queries(self):
        guards = TigerGuardrails(mode="prod")
        guards.validate_sql_query("SELECT count(*) FROM sensor_telemetry", service_id="prod-1")
        guards.validate_sql_query("EXPLAIN ANALYZE SELECT * FROM metrics", service_id="prod-1")

    def test_block_write_on_prod(self):
        guards = TigerGuardrails(mode="prod", prod_services=["prod-1"])
        with self.assertRaises(GuardrailViolation):
            guards.validate_sql_query("INSERT INTO sensor_telemetry VALUES (NOW(), 'dev1')", service_id="prod-1")

    def test_allow_write_on_dev(self):
        guards = TigerGuardrails(mode="prod", prod_services=["prod-1"])
        # DEV service is safe to modify
        guards.validate_sql_query("INSERT INTO sensor_telemetry VALUES (NOW(), 'dev1')", service_id="dev-1")

    def test_block_mutating_tool_in_all_mode(self):
        guards = TigerGuardrails(mode="all")
        with self.assertRaises(GuardrailViolation):
            guards.validate_tool_call("service_create", {})

    def test_block_destructive_unconstrained_queries(self):
        guards = TigerGuardrails(mode="off")
        with self.assertRaises(GuardrailViolation):
            guards.validate_sql_query("TRUNCATE TABLE sensor_telemetry")
        with self.assertRaises(GuardrailViolation):
            guards.validate_sql_query("DROP TABLE metrics")

    def test_sanitize_select_limit(self):
        guards = TigerGuardrails(max_limit=50)
        q1 = guards.sanitize_select_limit("SELECT * FROM metrics")
        self.assertEqual(q1, "SELECT * FROM metrics LIMIT 50;")

        q2 = guards.sanitize_select_limit("SELECT * FROM metrics LIMIT 10")
        self.assertEqual(q2, "SELECT * FROM metrics LIMIT 10")


if __name__ == "__main__":
    unittest.main()
