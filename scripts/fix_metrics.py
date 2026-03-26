import json
import sys
from datetime import datetime

with open(sys.argv[1], "r") as f:
    data = json.load(f)

for issue_key, record in data.get("issues", {}).items():
    # Fix emojis
    if record.get("issue_status") and "✅ Closed" in record["issue_status"]:
        record["issue_status"] = record["issue_status"].replace("✅ Closed", "❌ Closed")
        
    start_str = record.get("start_datetime")
    end_str = record.get("actual_completion_date")
    if start_str and end_str:
        start_dt = datetime.fromisoformat(start_str.replace("Z", "+00:00")).replace(tzinfo=None)
        end_dt = datetime.fromisoformat(end_str.replace("Z", "+00:00")).replace(tzinfo=None)
        diff_days = (end_dt - start_dt).total_seconds() / 86400.0
        record["actual_mandays"] = max(0.5, round(diff_days * 2) / 2.0)

with open(sys.argv[1], "w", encoding="utf-8") as f:
    json.dump(data, f, indent=2, ensure_ascii=False)
