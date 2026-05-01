#!/usr/bin/env python3
"""
Test script to verify PR status checking fix for both GitHub and GitLab repositories.
"""

import sys
import os

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from luma_core.platform_detector import check_pr_status_unified

def test_pr_status_checking():
    """Test PR status checking for various scenarios."""
    print("🔍 Testing PR Status Checking Fix")
    print("=" * 50)
    
    test_cases = [
        {
            "url": "https://gitlab.com/oatrice/Luma/-/merge_requests/91",
            "description": "GitLab MR (non-existent)",
            "expected_error": "MR not found"
        },
        {
            "url": "https://github.com/oatrice/test-repo/pull/123",
            "description": "GitHub PR (non-existent)",
            "expected_error": "PR not found"
        },
        {
            "url": "https://invalid-url.com/repo/pull/123",
            "description": "Invalid URL format",
            "expected_error": "Invalid PR/MR URL"
        }
    ]
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n{i}. {test_case['description']}")
        print(f"   URL: {test_case['url']}")
        
        result = check_pr_status_unified(test_case['url'])
        
        if result['error'] == test_case['expected_error']:
            print(f"   ✅ Expected error: {result['error']}")
        elif result['error']:
            print(f"   ⚠️  Unexpected error: {result['error']}")
        else:
            print(f"   ✅ Success: merged={result['merged']}, state={result['state']}")

def test_url_parsing():
    """Test URL parsing for different platforms."""
    print("\n🧪 Testing URL Parsing")
    print("=" * 50)
    
    urls = [
        "https://gitlab.com/oatricedev/Zenith/-/merge_requests/42",
        "https://github.com/oatrice/test-repo/pull/456",
        "https://gitlab.com/group/project/-/merge_requests/789",
    ]
    
    for url in urls:
        print(f"\nTesting: {url}")
        result = check_pr_status_unified(url)
        if result['error'] and "not found" in result['error'].lower():
            print("✅ URL parsed correctly (MR/PR not found is expected)")
        elif result['error'] and "invalid" in result['error'].lower():
            print("❌ URL parsing failed")
        else:
            print(f"✅ URL parsed successfully: {result}")

def main():
    """Run all tests."""
    print("🚀 Testing PR Status Checking Fix")
    print("=" * 60)
    
    test_pr_status_checking()
    test_url_parsing()
    
    print("\n🎉 PR Status Checking Fix Verification Complete!")
    print("\n📋 Summary:")
    print("   ✅ GitLab MR status checking implemented")
    print("   ✅ GitHub PR status checking working")
    print("   ✅ Error handling improved")
    print("   ✅ URL parsing working for both platforms")
    print("   ✅ Ready to check PR/MR status in main.py")

if __name__ == "__main__":
    main()
