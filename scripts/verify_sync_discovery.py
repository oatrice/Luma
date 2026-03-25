from luma_core.ai_brain_sync import AntigravityBrain, GeminiCLIBrain

def verify_sync_discovery():
    print("🔍 Testing Session Discovery...")
    
    # Check Antigravity
    print("\n--- [Antigravity Brain] ---")
    antigravity_sessions = AntigravityBrain.get_all_sessions()
    if antigravity_sessions:
        print(f"✅ Found {len(antigravity_sessions)} sessions.")
        for s in antigravity_sessions[:3]:
            print(f"  - ID: {s['session_id'][:12]}... | Preview: {s['preview'][:50]}")
    else:
        print("ℹ️ No Antigravity sessions found.")
        
    # Check Gemini CLI
    print("\n--- [Gemini CLI Brain] ---")
    gemini_sessions = GeminiCLIBrain.get_all_sessions()
    if gemini_sessions:
        print(f"✅ Found {len(gemini_sessions)} sessions.")
        for s in gemini_sessions[:3]:
            print(f"  - ID: {s['session_id'][:12]}... | Preview: {s['preview'][:50]}")
    else:
        print("ℹ️ No Gemini CLI sessions found.")

if __name__ == "__main__":
    verify_sync_discovery()
