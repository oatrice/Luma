import unittest
from unittest.mock import MagicMock, patch
from luma_core.llm import _create_model

class TestProviderNameFix(unittest.TestCase):
    @patch("luma_core.llm.GeminiAPIModel")
    @patch("luma_core.llm._attach_usage_metadata")
    def test_create_model_tags_gemini_as_gemini_api(self, mock_attach, mock_gemini_api):
        mock_gemini_instance = MagicMock()
        mock_gemini_api.return_value = mock_gemini_instance
        
        # Test 1: provider 'gemini' should be tagged as 'gemini-api'
        # Currently, it is tagged as 'gemini' (RED phase)
        _create_model("gemini", purpose="general")
        
        # Check call arguments of _attach_usage_metadata
        calls = mock_attach.call_args_list
        found_gemini_api = False
        for call in calls:
            # call.kwargs is where we find provider
            if call.kwargs.get("provider") == "gemini-api":
                found_gemini_api = True
        
        if found_gemini_api:
            print("Verified: Provider is already 'gemini-api'!")
        else:
            print("Captured expected failure: Provider is still 'gemini' (or something else)")
            self.fail("Provider 'gemini' was not tagged as 'gemini-api'")

if __name__ == "__main__":
    unittest.main()
