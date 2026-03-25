import sys
import os
sys.path.append(os.getcwd())
try:
    print("✅ Imports successful")
except Exception as e:
    print(f"❌ Import failed: {e}")
