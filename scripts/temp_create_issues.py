
import sys
import os
import requests
import time

# Add root to sys.path to import luma_core
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from luma_core.github_client import get_github_headers

REPO = "oatrice/JarWise-Root"
API_URL = f"https://api.github.com/repos/{REPO}/issues"

ISSUES = [
    {
        "title": "[Improvement]: Improve OCR Accuracy for e-slips",
        "body": """## 🚀 Getting Started
- [ ] Moved issue to **In Progress** in Project Board

## 🎯 Objective
Improve the accuracy of reading e-slip images for auto-importing expenses, specifically targeting Thai banking slips and various receipt formats. Currently, the OCR misses some fields or misinterprets dates/amounts.

---

## 📝 Specifications

### OCR Engine & Regex
- [ ] **Validation:** Improve regex patterns for tracking IDs and transaction references.
- [ ] **Amount Extraction:** Handle cases with 'THB', commas, and leading/trailing junk text.
- [ ] **Date Parsing:** Support multiple date formats (DD/MM/YY, DD MMM YYYY) commonly used in Thai slips.

### Error Handling
- [ ] **Low Confidence:** Flag items for manual review if confidence score is below threshold.
- [ ] **Duplicate Detection:** Ensure re-scanning same slip doesn't duplicate transaction.

---

## 🏗️ Technical Considerations
- [ ] **Library:** Review current OCR library settings.
- [ ] **Preprocessing:** Consider image pre-processing (grayscale, contrast) before OCR.

## ✅ Definition of Done
- [ ] Test with at least 10 different slip formats.
- [ ] Accuracy > 90% for standard transfer slips."""
    },
    {
        "title": "[Feature]: Import Credit Card Statement (PDF)",
        "body": """## 🚀 Getting Started
- [ ] Moved issue to **In Progress** in Project Board

## 🎯 Objective
Enable users to upload monthly credit card statements (PDF) to auto-extract transactions, facilitating bulk import of historical data.

---

## 📝 Specifications

### PDF Parsing
- [ ] **File Upload:** Support PDF file selection in Web/Android.
- [ ] **Text Extraction:** Extract text content from PDF.
- [ ] **Structure Analysis:** Identify transaction rows vs header/footer.

### Data Mapping
- [ ] **Fields:** Extract Date, Description, Amount.
- [ ] **Sign:** Determine if expense (positive) or payment/refund (negative).

---

## 🏗️ Technical Considerations
- [ ] **Security:** Ensure PDF is processed locally or securely.
- [ ] **Performance:** Handle large statements (multiple pages) without freezing UI.

## ✅ Definition of Done
- [ ] Can parse standard statements from major banks (KBank, SCB, etc.).
- [ ] UI for reviewing extracted data before saving."""
    },
    {
        "title": "[Feature]: Wallet/Jar List UI",
        "body": """## 🚀 Getting Started
- [ ] Moved issue to **In Progress** in Project Board

## 🎯 Objective
Create a dedicated UI to display a list of all Wallets/Jars with their current balances, allowing users to view their financial overview at a glance.

---

## 📝 Specifications

### UI Components
- [ ] **List View:** Display Jars as cards or list items.
- [ ] **Card Details:** Show Name, Icon, Current Balance, and Target (if any).
- [ ] **Actions:** Tap to view transaction history for that jar.

### Logic
- [ ] **Sorting:** Sort by recently used or custom order.
- [ ] **Total:** Show Grand Total of all jars at the top.

---

## 🏗️ Technical Considerations
- [ ] **State:** Use existing Jar Store/Provider.
- [ ] **Refresh:** Auto-update balance when transaction is added.

## ✅ Definition of Done
- [ ] UI matches design system.
- [ ] Balances are accurate and live-updated."""
    }
]

def create_issues():
    log = []
    headers = get_github_headers()
    
    if not headers:
        log.append("❌ No headers (TOKEN missing?)")
    else:
        log.append(f"🚀 Creating {len(ISSUES)} issues in {REPO}...")
        
        for issue in ISSUES:
            log.append(f"Creating: {issue['title']}...")
            try:
                resp = requests.post(API_URL, headers=headers, json=issue, timeout=15)
                if resp.status_code == 201:
                    data = resp.json()
                    log.append(f"✅ Created #{data['number']}: {data['html_url']}")
                    time.sleep(1) 
                else:
                    log.append(f"❌ Failed: {resp.status_code} {resp.text}")
            except Exception as e:
                log.append(f"❌ Error: {e}")
                
    with open("creation_result.txt", "w") as f:
        f.write("\n".join(log))

if __name__ == "__main__":
    create_issues()
