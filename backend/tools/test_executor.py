import unittest
from backend.tools.executor import ToolExecutor

class TestToolExecutor(unittest.TestCase):
    def setUp(self):
        self.executor = ToolExecutor()

    def test_valid_action(self):
        result = self.executor.execute({"tool": "get_deployments", "arguments": {"service": "api_gateway"}})
        self.assertEqual(result.status, "success")
        self.assertIn("ev_dep_001", result.evidence_ids)

    def test_invalid_tool(self):
        result = self.executor.execute({"tool": "delete_database", "arguments": {}})
        self.assertEqual(result.status, "error_invalid_tool")

    def test_invalid_action(self):
        result = self.executor.execute("not an action")
        self.assertEqual(result.status, "error_invalid_action")

    def test_invalid_arguments(self):
        result = self.executor.execute({"tool": "get_deployments", "arguments": "bad"})
        self.assertEqual(result.status, "error_invalid_arguments")

if __name__ == "__main__":
    unittest.main()
