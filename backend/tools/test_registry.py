import unittest
from backend.tools.registry import ToolRegistry

class TestTools(unittest.TestCase):
    def setUp(self):
        self.registry = ToolRegistry()

    def test_get_deployments(self):
        res = self.registry.execute("get_deployments", service="api_gateway")
        self.assertEqual(res.tool, "get_deployments")
        self.assertEqual(res.status, "success")
        self.assertIn("ev_dep_001", res.evidence_ids)

    def test_search_logs(self):
        res = self.registry.execute("search_logs", service="payment_service")
        self.assertEqual(res.tool, "search_logs")
        self.assertEqual(res.status, "success")
        self.assertIn("ev_log_003", res.evidence_ids)

    def test_query_metrics(self):
        res = self.registry.execute("query_metrics", metric_name="db_cpu_utilization")
        self.assertEqual(res.tool, "query_metrics")
        self.assertEqual(res.status, "success")
        self.assertIn("ev_met_002", res.evidence_ids)

    def test_compare_versions(self):
        res = self.registry.execute("compare_versions", service="user_service")
        self.assertEqual(res.tool, "compare_versions")
        self.assertEqual(res.status, "success")
        self.assertIn("ev_code_002", res.evidence_ids)

    def test_check_dependency_health(self):
        res = self.registry.execute("check_dependency_health", service="stripe")
        self.assertEqual(res.tool, "check_dependency_health")
        self.assertEqual(res.status, "success")
        self.assertIn("ev_dep_002", res.evidence_ids)

    def test_invalid_tool(self):
        res = self.registry.execute("unknown_tool")
        self.assertEqual(res.tool, "unknown_tool")
        self.assertEqual(res.status, "error_invalid_tool")
        self.assertEqual(res.evidence_ids, [])

if __name__ == '__main__':
    unittest.main()
