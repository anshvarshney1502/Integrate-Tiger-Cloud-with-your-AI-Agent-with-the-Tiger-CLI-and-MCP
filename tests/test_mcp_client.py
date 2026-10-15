import os
import sys
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src")))

from tiger_agent.mcp_client import TigerMCPClient
from tiger_agent.agent import TigerAgent
from tiger_agent.guardrails import TigerGuardrails


class TestTigerMCPIntegration(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.client = TigerMCPClient()
        cls.client.start()

    @classmethod
    def tearDownClass(cls):
        cls.client.stop()

    def test_handshake_successful(self):
        self.assertIn("name", self.client.server_info)
        self.assertEqual(self.client.server_info["name"], "tiger")

    def test_list_tools(self):
        tools = self.client.list_tools()
        self.assertGreaterEqual(len(tools), 15)
        names = [t["name"] for t in tools]
        self.assertIn("db_query", names)
        self.assertIn("service_list", names)
        self.assertIn("search_docs", names)
        self.assertIn("view_skill", names)

    def test_list_prompts(self):
        prompts = self.client.list_prompts()
        self.assertGreaterEqual(len(prompts), 8)
        names = [p["name"] for p in prompts]
        self.assertIn("setup-timescaledb-hypertables", names)
        self.assertIn("find-hypertable-candidates", names)

    def test_search_docs(self):
        results = self.client.search_docs(query="retention policy", limit=3)
        self.assertIsInstance(results, list)
        self.assertGreater(len(results), 0)

    def test_view_skill(self):
        skill_text = self.client.view_skill("setup-timescaledb-hypertables", path=".")
        self.assertIn("hypertable", skill_text.lower())

    def test_agent_status_query(self):
        guards = TigerGuardrails()
        agent = TigerAgent(mcp_client=self.client, guardrails=guards)
        res = agent.ask("Is the Tiger MCP server active?")
        self.assertEqual(res["type"], "status")
        self.assertIn("active", res["answer"].lower())


if __name__ == "__main__":
    unittest.main()
