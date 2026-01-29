
import sys
import os
sys.path.insert(0, os.getcwd())
from luma_core.github_project import fetch_kanban_cards

def search_issues():
    cards = fetch_kanban_cards(7) # JarWise
    keywords = {
        "OCR": ["ocr", "scan", "transcribe", "slip"],
        "PDF": ["pdf", "statement", "credit"],
        "Wallet": ["wallet", "jar", "pocket", "balance", "dashboard", "list"]
    }
    
    print("SEARCH RESULTS:")
    for category, keys in keywords.items():
        print(f"\n--- {category} Related --")
        found = False
        for c in cards:
            if c.status in ["Done", "Closed"]: continue
            if any(k in c.title.lower() for k in keys):
                print(f"[{c.status}] #{c.issue_number} {c.title}")
                found = True
        if not found:
            print("No active issues found.")

if __name__ == "__main__":
    search_issues()
