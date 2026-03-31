import unittest
from unittest.mock import MagicMock, patch
from luma_core.state_manager import LumaState, WorkflowPhase, IssueData
from luma_core.actions.workflow_actions import action_create_pr

class TestPRPhaseFix(unittest.TestCase):
    def test_action_create_pr_in_reviewing_phase(self):
        # Setup state in REVIEWING phase
        state = LumaState(
            phase=WorkflowPhase.REVIEWING,
            active_issues=[IssueData(number=59, title="Test Issue", html_url="http://gh.com/59")],
            active_branch="feat/59-test"
        )
        project = {"path": "/fake/path", "name": "TestProject"}
        
        # We need to mock transition_to and PreflightChecker to avoid side effects
        with patch("luma_core.actions.workflow_actions.transition_to") as mock_transition:
            with patch("luma_core.actions.workflow_actions.PreflightChecker"):
                # Mock transition result (success)
                mock_transition.return_value = (True, "OK")
                
                # Capture print output
                with patch("builtins.print") as mock_print:
                    action_create_pr(state, project, auto_approve=True)
                    
                    # Verify if it succeeded (transitioned to PREFLIGHT)
                    printed_messages = [str(call.args[0]) for call in mock_print.call_args_list]
                    
                    found_transition = any("Transitioning to PREFLIGHT phase" in m for m in printed_messages)
                    
                    if found_transition:
                        print("Verified: PR creation started from REVIEWING phase!")
                    else:
                        error_msg = f"❌ Cannot create PR in '{WorkflowPhase.REVIEWING.value}' phase"
                        found_error = any(error_msg in m for m in printed_messages)
                        if found_error:
                            self.fail("PR creation still fails in REVIEWING phase")
                        else:
                            self.fail("Test failed to detect either success or expected error")

if __name__ == "__main__":
    unittest.main()
