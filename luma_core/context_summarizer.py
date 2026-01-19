import os
import json
import re
from typing import List, Dict, Optional

class ContextSummarizer:
    def __init__(self, project_path: str):
        self.project_path = project_path
        self.rules_file = os.path.join(project_path, ".luma_rules.json")
        self.agent_dir = os.path.join(project_path, ".agent")
    
    def summarize_rules(self, limit: int = 5) -> List[str]:
        """
        Summarize project rules from multiple sources:
        1. .luma_rules.json (Highest priority)
        2. Markdown files in .agent/rules/ and .agent/workflows/
        
        Returns a list of high-priority rule strings.
        """
        reminders = []
        
        # 1. Load from .luma_rules.json helpers/reminders
        json_reminders = self._load_json_reminders()
        reminders.extend(json_reminders)
        
        # 2. Scan markdown files for MUST/SHOULD/DON'T or Alerts
        md_reminders = self._scan_markdown_rules()
        reminders.extend(md_reminders)
        
        # Deduplicate and limit
        unique_reminders = []
        seen = set()
        for r in reminders:
            if r not in seen:
                unique_reminders.append(r)
                seen.add(r)
                
        return unique_reminders[:limit]

    def _load_json_reminders(self) -> List[str]:
        """Extract explicit reminders from .luma_rules.json"""
        reminders = []
        if os.path.exists(self.rules_file):
            try:
                with open(self.rules_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    # Check for 'context_rules' or 'reminders' list
                    if "context_rules" in data:
                        reminders.extend([f"📝 {r}" for r in data["context_rules"]])
                    if "reminders" in data:
                        reminders.extend([f"📝 {r}" for r in data["reminders"]])
                    
                    # Also parse checks to see if any are CRITICAL/REQUIRED
                    if "preflight_checks" in data:
                        for check in data["preflight_checks"]:
                             if check.get("required", False):
                                 # Convert check to a reminder form
                                 msg = check.get("message", f"Check {check['name']}")
                                 reminders.append(f"🔴 PR Rule: {msg}")
            except Exception as e:
                print(f"⚠️ Error loading rules json: {e}")
        return reminders

    def _scan_markdown_rules(self) -> List[str]:
        """Scan .md files for MUST/SHOULD/DON'T keywords and GitHub Alerts"""
        found_rules = []
        
        search_paths = [
            os.path.join(self.agent_dir, "rules"),
            os.path.join(self.agent_dir, "workflows")
        ]
        
        # Simple keywords (MUST/SHOULD/DON'T) - check regular lines
        keyword_patterns = [
            (r'\bMUST\b', "🔴 MUST"),
            (r'\bSHOULD\b', "🟡 SHOULD"),
            (r'\bDON\'?T\b', "🚫 DON'T"),
        ]
        
        for path in search_paths:
            if not os.path.exists(path):
                continue
                
            for root, _, files in os.walk(path):
                for file in files:
                    if file.endswith(".md"):
                        full_path = os.path.join(root, file)
                        try:
                            with open(full_path, 'r', encoding='utf-8') as f:
                                lines = f.readlines()
                                active_alert = None
                                
                                for line in lines:
                                    line_clean = line.strip()
                                    if not line_clean: 
                                        active_alert = None
                                        continue
                                        
                                    # 1. Check for Alert Headers
                                    alert_match = re.match(r'^>\s*\[!(IMPORTANT|WARNING)\]', line_clean, re.IGNORECASE)
                                    if alert_match:
                                        tag = alert_match.group(1).upper()
                                        if tag == "IMPORTANT": active_alert = "❗ IMPORTANT"
                                        elif tag == "WARNING": active_alert = "⚠️ WARNING"
                                        continue

                                    # 2. If inside an alert, capture content (first line only for summary)
                                    if active_alert and line_clean.startswith('>'):
                                        content = re.sub(r'^>\s*', '', line_clean).strip()
                                        if content:
                                            found_rules.append(f"{active_alert}: {content}")
                                            active_alert = None # Reset after one line
                                        continue
                                    
                                    # Reset alert if loop continues past block
                                    if not line_clean.startswith('>'):
                                        active_alert = None
                                    
                                    # 3. Regular keywords check (if not in an alert check)
                                    # Skip comments or headers
                                    if line_clean.startswith('#'): continue
                                    
                                    for pattern, emoji in keyword_patterns:
                                        if re.search(pattern, line_clean, re.IGNORECASE):
                                            # Clean up modifiers
                                            clean_text = re.sub(r'^[\-\*>]+\s*', '', line_clean).strip()
                                            if len(clean_text) > 80:
                                                clean_text = clean_text[:77] + "..."
                                            found_rules.append(f"{emoji}: {clean_text}")
                                            break

                        except Exception:
                            pass
                            
        return found_rules

