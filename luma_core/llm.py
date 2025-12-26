import os
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_openai import ChatOpenAI 
from .config import (
    LLM_PROVIDER,
    OPENROUTER_API_KEY, OPENROUTER_GENERAL_MODEL, OPENROUTER_CODE_MODEL,
    GOOGLE_API_KEY, GEMINI_GENERAL_MODEL, GEMINI_CODE_MODEL
)

def get_llm(temperature=0.7, purpose="general"):
    """Factory function to get the configured LLM instance"""
    if LLM_PROVIDER == "openrouter":
        model_name = OPENROUTER_GENERAL_MODEL
        if purpose == "code":
            model_name = OPENROUTER_CODE_MODEL
        
        print(f"🔌 Using OpenRouter ({model_name})...")
        return ChatOpenAI(
            model=model_name,
            openai_api_key=OPENROUTER_API_KEY,
            openai_api_base="https://openrouter.ai/api/v1",
            temperature=temperature,
            max_tokens=4000
        )
    elif LLM_PROVIDER == "gemini":
        model_name = GEMINI_GENERAL_MODEL
        if purpose == "code":
            model_name = GEMINI_CODE_MODEL

        print(f"🔌 Using Gemini ({model_name})...")
        return ChatGoogleGenerativeAI(
            model=model_name, 
            google_api_key=GOOGLE_API_KEY,
            temperature=temperature,
            request_timeout=120
        )
    else:
        raise ValueError(f"Unknown LLM_PROVIDER: {LLM_PROVIDER}")
