def generate_url_string(state, platform):
    fallback_url = f"https://{'gitlab.com/' if platform == 'gitlab' else 'github.com/'}{state.get('issue_source_repo', state.get('repo'))}/issues/{state.get('issue_data', {}).get('number')}"
    return f"`Closes {state.get('issue_data', {}).get('url', fallback_url)}`"

print("--- URL Generation Tests ---\n")

# Test Case 1: Luma (GitLab) - has explicit URL in issue_data
state1 = {
    "repo": "oatricedev/Luma",
    "issue_data": {
        "number": 101,
        "url": "https://gitlab.com/oatricedev/Luma/-/issues/101"
    }
}
print(f"1. Luma (GitLab with explicit URL):")
print(f"   Result: {generate_url_string(state1, 'gitlab')}\n")

# Test Case 2: Zenith (GitHub) - no explicit URL, falls back to string building
state2 = {
    "repo": "oatrice/Zenith",
    "issue_data": {
        "number": 42
    }
}
print(f"2. Zenith (GitHub without explicit URL):")
print(f"   Result: {generate_url_string(state2, 'github')}\n")

# Test Case 3: Another GitLab repo - no explicit URL
state3 = {
    "repo": "someorg/AnotherApp",
    "issue_data": {
        "number": 99
    }
}
print(f"3. Custom Repo (GitLab without explicit URL):")
print(f"   Result: {generate_url_string(state3, 'gitlab')}\n")

# Test Case 4: Cerebro (GitLab) - no explicit URL
state4 = {
    "repo": "oatricedev/Cerebro",
    "issue_data": {
        "number": 15
    }
}
print(f"4. Cerebro (GitLab without explicit URL):")
print(f"   Result: {generate_url_string(state4, 'gitlab')}\n")

# Test Case 5: Cerebro (GitLab) - has explicit URL in issue_data (Real World Scenario)
state5 = {
    "repo": "oatricedev/Cerebro",
    "issue_data": {
        "number": 15,
        "url": "https://gitlab.com/oatricedev/Cerebro/-/issues/15"
    }
}
print(f"5. Cerebro (GitLab with explicit URL from API - Real World Scenario):")
print(f"   Result: {generate_url_string(state5, 'gitlab')}\n")
