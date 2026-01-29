
import os
import sys
# Try loading dotenv from common paths
try:
    from dotenv import load_dotenv
    load_dotenv()
    print("Loaded .env via dotenv")
except ImportError:
    print("dotenv not found")

token = os.getenv("GITHUB_TOKEN")
print(f"GITHUB_TOKEN Present: {bool(token)}")
print(f"CWD: {os.getcwd()}")
print(f"Python: {sys.version}")
