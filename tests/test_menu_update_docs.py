import unittest
from luma_core.state_manager import WorkflowPhase
from main import MENU_ACTIONS

class TestMenuUpdateDocs(unittest.TestCase):
    def test_update_docs_in_preflight(self):
        """Test that Update Docs (option 7) is available in PREFLIGHT phase."""
        self.assertIn("7", MENU_ACTIONS)
        self.assertIn(WorkflowPhase.PREFLIGHT, MENU_ACTIONS["7"]["valid_phases"])

if __name__ == "__main__":
    unittest.main()
