import os
from dotenv import load_dotenv
from luma_core.llm import get_llm
from langchain_core.messages import HumanMessage

load_dotenv()

def verify_chain():
    print("🚀 Initializing LLM Fallback Chain...")
    try:
        llm = get_llm()
        print(f"🔗 Chain initialized. Active provider: {llm}")
        
        print("\n📤 Testing invocation (this might trigger fallbacks)...")
        messages = [HumanMessage(content="Hello, tell me exactly which model you are.")]
        
        # We expect this to fail Model 1-7 and succeed at Model 8 (Gemini API)
        # after my fix for the run_manager bug.
        response = llm.invoke(messages)
        print(f"\n✅ Success! Response from: {type(llm)}")
        print(f"📝 Content: {response.content[:100]}...")
        
    except Exception as e:
        print(f"\n❌ Chain failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    verify_chain()
