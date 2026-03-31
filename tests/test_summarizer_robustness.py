import unittest
import json
import os
import tempfile
from datetime import datetime, timezone
from luma_core.metrics_summarizer import summarize_usage_stats

class TestSummarizerRobustness(unittest.TestCase):
    def setUp(self):
        # Create a temporary log file
        self.log_fd, self.log_path = tempfile.mkstemp(suffix=".jsonl")
        self.project = {
            "name": "TestProject",
            "path": "/fake/path",
            "repo": "test/repo"
        }
        
        # Write some sample entries
        self.entries = [
            {
                "ts": datetime.now(timezone.utc).isoformat(),
                "event": "llm_call",
                "status": "success",
                "session_id": "old_session",
                "project_name": "TestProject",
                "duration_ms": 100
            },
            {
                "ts": datetime.now(timezone.utc).isoformat(),
                "event": "llm_call",
                "status": "error",
                "session_id": "old_session",
                "project_name": "TestProject",
                "duration_ms": 200
            }
        ]
        
        with open(self.log_path, "w") as f:
            for e in self.entries:
                f.write(json.dumps(e) + "\n")

    def tearDown(self):
        os.close(self.log_fd)
        if os.path.exists(self.log_path):
            os.remove(self.log_path)

    def test_summary_with_wrong_session_id_returns_zero(self):
        # Current behavior: returns 0 if session_id doesn't match
        summary = summarize_usage_stats(self.log_path, self.project, session_id="new_session")
        self.assertEqual(summary["total_calls"], 0)
        print(f"Verified: Summary with wrong session ID is 0: {summary['total_calls']}")

    def test_summary_fallback_logic(self):
        # Even if session_id is "new_session", we can get project stats if we pass no session_id
        # and a since_hours filter.
        summary = summarize_usage_stats(self.log_path, self.project, session_id=None, since_hours=1)
        
        # Should now find the 2 entries in self.entries (total_calls: 2)
        self.assertEqual(summary["total_calls"], 2)
        self.assertEqual(summary["success_count"], 1)
        self.assertEqual(summary["error_count"], 1)
        print(f"Verified: Fallback summary found calls: {summary['total_calls']}")

    def test_summary_since_hours_filter(self):
        # test event from 2 hours ago
        summary = summarize_usage_stats(self.log_path, self.project, since_hours=1)
        # Should find current entries (which are very recent)
        self.assertEqual(summary["total_calls"], 2)
        
        # Test with very small window (unlikely to match unless run exactly at same microsecond)
        # Or I can manually add an old entry
        with open(self.log_path, "a") as f:
            old_entry = self.entries[0].copy()
            old_entry["ts"] = "2020-01-01T00:00:00Z"
            f.write(json.dumps(old_entry) + "\n")
            
        summary_limited = summarize_usage_stats(self.log_path, self.project, since_hours=24)
        self.assertEqual(summary_limited["total_calls"], 2) # Still 2, old one filtered out
        print("Verified: Old entry was filtered out by since_hours.")

if __name__ == "__main__":
    unittest.main()
