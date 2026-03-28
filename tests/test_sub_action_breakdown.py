import unittest
import json
import os
from datetime import datetime, timedelta, timezone
from luma_core.metrics_summarizer import summarize_usage_stats, format_summary_message

class TestSubActionBreakdown(unittest.TestCase):
    def setUp(self):
        self.log_path = ".test_sub_action_usage.jsonl"
        self.project = {"name": "TestProject", "path": os.getcwd()}
        self.branch = "feat/test-branch"
        
        # Test timeline:
        # T0: Sub1 Start
        # T+1m: Sub1 End / Sub2 Start
        # T+3m: Sub2 End
        t0 = datetime.now(timezone.utc) - timedelta(minutes=5)
        
        self.entries = [
            # Sub-action 1 (1 minute span)
            {
                "ts": t0.isoformat(),
                "event": "llm_call",
                "status": "success",
                "project_name": "TestProject",
                "active_branch": self.branch,
                "sub_action": "Sub1",
                "duration_ms": 1000
            },
            {
                "ts": (t0 + timedelta(minutes=1)).isoformat(),
                "event": "llm_call",
                "status": "success",
                "project_name": "TestProject",
                "active_branch": self.branch,
                "sub_action": "Sub1",
                "duration_ms": 2000
            },
            # Sub-action 2 (2 minute span)
            {
                "ts": (t0 + timedelta(minutes=1, seconds=1)).isoformat(),
                "event": "llm_call",
                "status": "success",
                "project_name": "TestProject",
                "active_branch": self.branch,
                "sub_action": "Sub2",
                "duration_ms": 500
            },
            {
                "ts": (t0 + timedelta(minutes=3)).isoformat(),
                "event": "llm_call",
                "status": "success",
                "project_name": "TestProject",
                "active_branch": self.branch,
                "sub_action": "Sub2",
                "duration_ms": 1500
            }
        ]
        
        with open(self.log_path, "w") as f:
            for entry in self.entries:
                f.write(json.dumps(entry) + "\n")

    def tearDown(self):
        if os.path.exists(self.log_path):
            os.remove(self.log_path)

    def test_summarize_with_sub_action_breakdown(self):
        summary = summarize_usage_stats(self.log_path, self.project, branch=self.branch)
        
        # Check basic counts
        self.assertEqual(summary["total_calls"], 4)
        
        # Check sub_actions breakdown (to be implemented)
        self.assertIn("sub_actions", summary)
        sub_stats = summary["sub_actions"]
        
        # Sub1 duration: T+1m - T0 = 60s
        self.assertIn("Sub1", sub_stats)
        self.assertAlmostEqual(sub_stats["Sub1"]["elapsed_ms"], 60000, delta=1000)
        
        # Sub2 duration: T+3m - T+1m 1s = 119s
        self.assertIn("Sub2", sub_stats)
        self.assertAlmostEqual(sub_stats["Sub2"]["elapsed_ms"], 119000, delta=1000)
        
        # Total Elapsed: T+3m - T0 = 180s
        self.assertEqual(summary["elapsed_ms"], 180000)

    def test_format_message_with_breakdown(self):
        summary = summarize_usage_stats(self.log_path, self.project, branch=self.branch)
        msg = format_summary_message(summary, {})
        
        # Check if breakdown is present in formatted message
        self.assertIn("⏱️ **Breakdown (Elapsed Time)**", msg)
        self.assertIn("Sub1", msg)
        self.assertIn("Sub2", msg)
        self.assertIn("1m 0s", msg) # 60s
        self.assertIn("1m 59s", msg) # 119s

if __name__ == "__main__":
    unittest.main()
