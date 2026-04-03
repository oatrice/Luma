# PR Draft Prompt

You are an AI assistant helping to create a Pull Request description.
    
TASK: Guided planning can fail on multi-issue runs due to overlong feature dirs and sticky LLM fallback
ISSUE: {
  "title": "Guided planning can fail on multi-issue runs due to overlong feature dirs and sticky LLM fallback",
  "number": 35,
  "body": "## Summary\n\nGuided Planning can fail during a multi-issue run for two independent reasons that surfaced in the same Zenith workflow:\n\n1. `Analyst`/`Spec` build `docs/features/...` directory names directly from the combined multi-issue title, which can exceed the filesystem basename limit and raise `OSError: [Errno 63] File name too long`.\n2. The LLM fallback chain resumes from the saved `FALLBACK_ACTIVE_INDEX` but does not wrap back to earlier models. If the saved model fails transiently, the entire chain can stop without trying the remaining configured models.\n\n## Impact\n\n- Guided Feature Workflow can stop in the Planning phase even when other fallback models are still available.\n- Multi-issue planning is especially vulnerable because combined titles are much longer than single-issue titles.\n- Zenith loses the expected `Analyst -> Spec -> SBE -> Architect` handoff and drops into manual recovery.\n\n## Reproduction\n\n1. In Zenith, start Guided Feature Workflow with multiple selected issues, for example `#13-14-15-8`.\n2. Run Planning Phase.\n3. Observe one of these failures:\n   - `Analyst` or `Spec` tries to create an overlong `docs/features/...` directory name and fails with `File name too long`.\n   - `Spec`/`SBE` starts from a saved fallback model index, that model aborts, and the fallback chain does not retry earlier configured models.\n\n## Expected\n\n- Feature directory naming should stay within filesystem limits for multi-issue runs.\n- Fallback LLM selection should try the full configured chain, starting from the saved index and wrapping around the list.\n\n## Proposed Fix\n\n- Centralize feature directory naming behind a byte-safe helper that truncates long slugs and appends a short hash suffix when needed.\n- Update `FallbackModel` to iterate through the model list in circular order instead of only trying `range(start_idx, len(models))`.\n- Add regression tests for both behaviors.\n\n## Acceptance Criteria\n\n- Multi-issue planning does not fail when the combined issue title is very long.\n- `Analyst` and `Spec` both create safe feature directory names for multi-issue runs.\n- When `FALLBACK_ACTIVE_INDEX` points near the end of the model chain and that model fails, Luma still retries the earlier models.\n- Regression tests cover both the directory naming bug and the fallback rotation bug.\n\n## Related\n\n- Observed while planning Zenith issues:\n  - https://github.com/oatrice/Zenith/issues/13\n  - https://github.com/oatrice/Zenith/issues/14\n  - https://github.com/oatrice/Zenith/issues/15\n  - https://github.com/oatrice/Zenith/issues/8\n\n\n## \ud83e\udde0 AI Brain Context\n- [task.md](https://raw.githubusercontent.com/oatrice/Luma/feat/35-handle-long-feature-dirs/docs/features/15_issue-35_guided-planning-can-fail-on-multi-issue-runs-due-to-overlong-feature-dirs-and-sticky-llm-fallback/ai_brain/task.md)\n- [walkthrough.md](https://raw.githubusercontent.com/oatrice/Luma/feat/35-handle-long-feature-dirs/docs/features/15_issue-35_guided-planning-can-fail-on-multi-issue-runs-due-to-overlong-feature-dirs-and-sticky-llm-fallback/ai_brain/walkthrough.md)\n- [implementation_plan.md](https://raw.githubusercontent.com/oatrice/Luma/feat/35-handle-long-feature-dirs/docs/features/15_issue-35_guided-planning-can-fail-on-multi-issue-runs-due-to-overlong-feature-dirs-and-sticky-llm-fallback/ai_brain/implementation_plan.md)\n\n\nCloses #35",
  "url": "https://github.com/oatrice/Luma/issues/35"
}

GIT CONTEXT:
COMMITS:
5990a85 feat: Guided planning can fail on multi-issue runs due t...
72c1ba1 docs: sync AI brain artifacts
dd7df44 chore(release): v1.11.0 with guided planning and metrics tracking
966cb6c feat: Enhance Guided Planning for multi-issue runs with compact naming and circular LLM fallback
6f79f33 feat: Enhance Guided Planning for multi-issue runs with safe directory naming and circular LLM fallback
cbaf87f 🐛 fix(llm): Correct fallback model rotation logic
0e75b0a ✨ feat(usage): Record action events and filter metric logs
96091c4 ✨ feat(feature_dirs): Centralize feature directory naming logic
db295d1 ✨ feat(metrics): Prompt for post story points

STATS:
.luma_metrics.json                                 |  44 +++-
 CHANGELOG.md                                       |  11 +
 README.md                                          |   4 +-
 .../ai_brain/implementation_plan.md                |  38 ++++
 .../ai_brain/task.md                               |  13 ++
 .../ai_brain/walkthrough.md                        |  29 +++
 .../analysis.md                                    | 147 +++++++++++++
 .../plan.md                                        | 132 ++++++++++++
 .../sbe.md                                         |  72 +++++++
 .../spec.md                                        | 122 +++++++++++
 luma_core/actions/metrics_actions.py               |  20 +-
 luma_core/actions/utils.py                         |  24 +++
 luma_core/actions/workflow_actions.py              |   4 +
 luma_core/agents/analyst.py                        |  10 +-
 luma_core/agents/sbe_agent.py                      |  10 +-
 luma_core/agents/spec_agent.py                     |  10 +-
 luma_core/feature_dirs.py                          | 180 ++++++++++++++++
 luma_core/issue_metrics.py                         |   4 +
 luma_core/llm.py                                   |   8 +-
 luma_core/metrics_summarizer.py                    |   4 +
 luma_core/usage_tracker.py                         |  56 ++++-
 main.py                                            |  76 +++++--
 package.json                                       |   2 +-
 tests/test_feature_dir_naming.py                   |  98 +++++++++
 tests/test_issue_metrics.py                        |  30 +++
 tests/test_llm_fallback_rotation.py                |  52 +++++
 tests/test_main_headless_cli.py                    | 229 +++++++++++++++++++++
 tests/test_metrics_summarizer.py                   |  22 ++
 28 files changed, 1376 insertions(+), 75 deletions(-)

KEY FILE DIFFS:
diff --git a/luma_core/actions/metrics_actions.py b/luma_core/actions/metrics_actions.py
index 050b8cc..827179c 100644
--- a/luma_core/actions/metrics_actions.py
+++ b/luma_core/actions/metrics_actions.py
@@ -141,24 +141,8 @@ def action_manage_issue_metrics(state: LumaState, project: dict):
             if gh_sync_result.get("paradoxes_fixed", 0) > 0:
                 print(f"   ⏱️  Fixed {gh_sync_result['paradoxes_fixed']} Time Paradox(es).")
 
-            completed_missing_post_points = [
-                record
-                for record in list_issue_metrics(selected_project["path"])
-                if record.post_story_point is None
-                and record.repository == selected_project.get("repo")
-                and any(
-                    marker in (record.issue_status or "").lower()
-                    for marker in ("done", "complete", "released", "closed")
-                )
-            ]
-            if completed_missing_post_points:
-                print(
-                    "\n   📌 Re-estimate Post Story Point for completed issues missing actual complexity..."
-                )
-                prompt_post_story_points_for_records(
-                    selected_project,
-                    completed_missing_post_points,
-                )
+            # Suggest and prompt for post story points for newly completed issues
+            prompt_missing_post_story_points(selected_project)
             continue
 
         print("❌ Invalid selection")
diff --git a/luma_core/actions/utils.py b/luma_core/actions/utils.py
index defe06b..4b92a53 100644
--- a/luma_core/actions/utils.py
+++ b/luma_core/actions/utils.py
@@ -598,6 +598,30 @@ def prompt_post_story_points_for_records(project: dict, records: list) -> int:
 
     return updated
 
+def prompt_missing_post_story_points(project: dict):
+    """Find issues that are complete but missing post_story_point and prompt for them."""
+    from luma_core.issue_metrics import list_issue_metrics
+    
+    completed_missing_post_points = [
+        record
+        for record in list_issue_metrics(project["path"])
+        if record.post_story_point is None
+        and record.repository == project.get("repo")
+        and any(
+            marker in (record.issue_status or "").lower()
+            for marker in ("done", "complete", "released", "closed")
+        )
+    ]
+    
+    if completed_missing_post_points:
+        print(
+            "\n   📌 Re-estimate Post Story Point for completed issues missing actual complexity..."
+        )
+        prompt_post_story_points_for_records(
+            project,
+            completed_missing_post_points,
+        )
+
 def _edit_issue_metrics_record(project: dict, record: IssueMetricsRecord, is_new: bool = False):
     print(f"\n📝 Issue Metrics for #{record.issue_number} - {record.issue_title}")
     print(f"   Project: {project['name']}")
diff --git a/luma_core/actions/workflow_actions.py b/luma_core/actions/workflow_actions.py
index f160b72..392ec2f 100644
--- a/luma_core/actions/workflow_actions.py
+++ b/luma_core/actions/workflow_actions.py
@@ -750,6 +750,10 @@ def action_guided_workflow(state: LumaState, project: dict):
         if gh_sync_result["updated"] > 0:
             print(f"   📊 Synced {gh_sync_result['updated']} records from GH.")
 
+        # Suggest and prompt for post story points for newly completed issues
+        from luma_core.actions.utils import prompt_missing_post_story_points
+        prompt_missing_post_story_points(project)
+
         usage_summary = summarize_usage_stats(
             usage_tracker.get_log_path(), project, usage_tracker._SESSION_ID,
             branch=state.active_branch
diff --git a/luma_core/agents/analyst.py b/luma_core/agents/analyst.py
index b06f1e9..f2b0b19 100644
--- a/luma_core/agents/analyst.py
+++ b/luma_core/agents/analyst.py
@@ -1,14 +1,14 @@
 import os
 import re
 from langchain_core.messages import SystemMessage, HumanMessage
+from luma_core.feature_dirs import build_feature_dirname, sanitize_slug
 from luma_core.llm import get_llm
 from luma_core.state import AgentState
 from luma_core.project_context import load_project_context, build_context_block
 
 def sanitize_filename(name: str) -> str:
     """Sanitize string for use in filename."""
-    name = re.sub(r'[^\w\s-]', '', name).strip().lower()
-    return re.sub(r'[-\s]+', '-', name)
+    return sanitize_slug(name)
 
 def analyst_agent(state: AgentState):
     """
@@ -142,12 +142,8 @@ def analyst_agent(state: AgentState):
         output_dir = existing_dir_path
     else:
         # specific format: N_issue-ID_slug
-        sanitized_title = sanitize_filename(task)
-        # Replace spaces with hyphens for slug style if sanitize didn't
-        sanitized_title = sanitized_title.replace(" ", "-")
-        
         issue_number = issue_data.get('number', '0')
-        output_folder_name = f"{next_index}_issue-{issue_number}_{sanitized_title}"
+        output_folder_name = build_feature_dirname(next_index, issue_number, task)
         
         output_dir = os.path.join(features_root, output_folder_name)
         os.makedirs(output_dir, exist_ok=True)
diff --git a/luma_core/agents/sbe_agent.py b/luma_core/agents/sbe_agent.py
index 66a616b..3573cd7 100644
--- a/luma_core/agents/sbe_agent.py
+++ b/luma_core/agents/sbe_agent.py
@@ -8,14 +8,14 @@ import os
 import re
 import datetime
 from langchain_core.messages import SystemMessage, HumanMessage
+from luma_core.feature_dirs import build_feature_dirname, sanitize_slug
 from luma_core.llm import get_llm
 from luma_core.state import AgentState
 
 
 def sanitize_filename(name: str) -> str:
     """Sanitize string for use in filename."""
-    name = re.sub(r'[^\w\s-]', '', name).strip().lower()
-    return re.sub(r'[-\s]+', '-', name)
+    return sanitize_slug(name)
 
 
 def sbe_agent(state: AgentState) -> dict:
@@ -147,7 +147,6 @@ def _save_sbe_file(content: str, issue_data: dict, target_dir: str) -> str:
     if not feature_dir:
         # Create new feature directory
         title = issue_data.get('title', 'unknown')
-        slug = sanitize_filename(title)[:30]
         next_index = 1
         
         if os.path.exists(features_root):
@@ -160,7 +159,10 @@ def _save_sbe_file(content: str, issue_data: dict, target_dir: str) -> str:
             if indices:
                 next_index = max(indices) + 1
         
-        feature_dir = os.path.join(features_root, f"{next_index}_issue-{issue_number}_{slug}")
+        feature_dir = os.path.join(
+            features_root,
+            build_feature_dirname(next_index, issue_number, title),
+        )
     
     # Create feature directory if needed
     os.makedirs(feature_dir, exist_ok=True)
diff --git a/luma_core/agents/spec_agent.py b/luma_core/agents/spec_agent.py
index 4c1637c..0700c85 100644
--- a/luma_core/agents/spec_agent.py
+++ b/luma_core/agents/spec_agent.py
@@ -1,6 +1,6 @@
 import os
-import re
 from langchain_core.messages import SystemMessage, HumanMessage
+from luma_core.feature_dirs import build_feature_dirname
 from luma_core.llm import get_llm
 from luma_core.state import AgentState
 from luma_core.project_context import load_project_context, build_context_block
@@ -129,9 +129,11 @@ Your goal is to write a detailed Specification Document (`spec.md`) for the user
         # Use simple timestamp-based or just count dirs
         count = len([d for d in os.listdir(features_root) if os.path.isdir(os.path.join(features_root, d))])
         next_index = count + 1
-        
-        safe_title = re.sub(r'[^\w\s-]', '', task).strip().lower().replace(" ", "-")
-        output_dir = os.path.join(features_root, f"{next_index}_issue-{issue_number}_{safe_title}")
+
+        output_dir = os.path.join(
+            features_root,
+            build_feature_dirname(next_index, issue_number, task),
+        )
         os.makedirs(output_dir, exist_ok=True)
 
     output_file = os.path.join(output_dir, "spec.md")
diff --git a/luma_core/feature_dirs.py b/luma_core/feature_dirs.py
new file mode 100644
index 0000000..c80106e
--- /dev/null
+++ b/luma_core/feature_dirs.py
@@ -0,0 +1,180 @@
+import hashlib
+import re
+
+
+MAX_DIRNAME_BYTES = 255
+MAX_FEATURE_SLUG_BYTES = 64
+MAX_FEATURE_SLUG_TOKENS = 8
+DEFAULT_FEATURE_SLUG = "feature"
+THAI_TRANSLITERATION_MAP = {
+    "ก": "k",
+    "ข": "kh",
+    "ฃ": "kh",
+    "ค": "kh",
+    "ฅ": "kh",
+    "ฆ": "kh",
+    "ง": "ng",
+    "จ": "ch",
+    "ฉ": "ch",
+    "ช": "ch",
+    "ซ": "s",
+    "ฌ": "ch",
+    "ญ": "y",
+    "ฎ": "d",
+    "ฏ": "t",
+    "ฐ": "th",
+    "ฑ": "th",
+    "ฒ": "th",
+    "ณ": "n",
+    "ด": "d",
+    "ต": "t",
+    "ถ": "th",
+    "ท": "th",
+    "ธ": "th",
+    "น": "n",
+    "บ": "b",
+    "ป": "p",
+    "ผ": "ph",
+    "ฝ": "f",
+    "พ": "ph",
+    "ฟ": "f",
+    "ภ": "ph",
+    "ม": "m",
+    "ย": "y",
+    "ร": "r",
+    "ล": "l",
+    "ว": "w",
+    "ศ": "s",
+    "ษ": "s",
+    "ส": "s",
+    "ห": "h",
+    "ฬ": "l",
+    "อ": "o",
+    "ฮ": "h",
+    "ะ": "a",
+    "ั": "a",
+    "า": "a",
+    "ำ": "am",
+    "ิ": "i",
+    "ี": "i",
+    "ึ": "ue",
+    "ื": "ue",
+    "ุ": "u",
+    "ู": "u",
+    "เ": "e",
+    "แ": "ae",
+    "โ": "o",
+    "ใ": "ai",
+    "ไ": "ai",
+    "ๅ": "a",
+    "ๆ": "",
+    "็": "",
+    "่": "",
+    "้": "",
+    "๊": "",
+    "๋": "",
+    "์": "",
+    "ํ": "m",
+    "ฯ": "",
+    "฿": "baht",
+}
+SLUG_STOPWORDS = {
+    "a",
+    "an",
+    "and",
+    "for",
+    "from",
+    "in",
+    "of",
+    "on",
+    "or",
+    "the",
+    "to",
+    "with",
+}
+
+
+def _transliterate_thai(text: str) -> str:
+    result = []
+    for char in text:
+        if char in THAI_TRANSLITERATION_MAP:
+            result.append(THAI_TRANSLITERATION_MAP[char])
+        elif "\u0E00" <= char <= "\u0E7F":
+            result.append(" ")
+        else:
+            result.append(char)
+    return "".join(result)
+
+
+def _normalize_slug(name: str) -> str:
+    transliterated = _transliterate_thai(name).replace("&", " and ")
+    ascii_text = transliterated.encode("ascii", "ignore").decode("ascii").lower()
+    ascii_text = re.sub(r"[^a-z0-9\s-]", " ", ascii_text)
+    ascii_text = re.sub(r"[-\s]+", "-", ascii_text).strip("-")
+    return ascii_text
+
+
+def _compact_slug(slug: str) -> str:
+    tokens = [token for token in slug.split("-") if token]
+    compact_tokens = []
+
+    for token in tokens:
+        if token in SLUG_STOPWORDS and compact_tokens:
+            continue
+        compact_tokens.append(token)
+        if len(compact_tokens) >= MAX_FEATURE_SLUG_TOKENS:
+            break
+
+    compacted = "-".join(compact_tokens) if compact_tokens else DEFAULT_FEATURE_SLUG
+    compacted = _truncate_to_bytes(compacted, MAX_FEATURE_SLUG_BYTES).rstrip("-_")
+    return compacted or DEFAULT_FEATURE_SLUG
+
+
+def _with_hash_suffix(slug: str, digest: str, max_bytes: int) -> str:
+    suffix = f"-{digest}"
+    available_slug_bytes = max_bytes - len(suffix.encode("utf-8"))
+    truncated_slug = _truncate_to_bytes(slug, available_slug_bytes).rstrip("-_")
+    if not truncated_slug:
+        truncated_slug = DEFAULT_FEATURE_SLUG
+    return f"{truncated_slug}{suffix}"
+
+
+def sanitize_slug(name: str) -> str:
+    """Convert free-form titles into a filesystem-safe slug."""
+    normalized = _normalize_slug(name)
+    return _compact_slug(normalized)
+
+
+def _truncate_to_bytes(value: str, max_bytes: int) -> str:
+    if max_bytes <= 0:
+        return ""
+
+    result = []
+    size = 0
+
+    for char in value:
+        char_size = len(char.encode("utf-8"))
+        if size + char_size > max_bytes:
+            break
+        result.append(char)
+        size += char_size
+
+    return "".join(result)
+
+
+def build_feature_dirname(index: int, issue_number: str, title: str) -> str:
+    """Build a docs/features directory name that stays within filesystem limits."""
+    prefix = f"{index}_issue-{issue_number}_"
+    normalized_slug = _normalize_slug(title) or DEFAULT_FEATURE_SLUG
+    compact_slug = _compact_slug(normalized_slug)
+    digest = hashlib.sha1(normalized_slug.encode("utf-8")).hexdigest()[:8]
+
+    if compact_slug != normalized_slug:
+        compact_slug = _with_hash_suffix(compact_slug, digest, MAX_FEATURE_SLUG_BYTES)
+
+    dirname = f"{prefix}{compact_slug}"
+    if len(dirname.encode("utf-8")) <= MAX_DIRNAME_BYTES:
+        return dirname
+
+    available_slug_bytes = MAX_DIRNAME_BYTES - len(prefix.encode("utf-8"))
+    return f"{prefix}{_with_hash_suffix(compact_slug, digest, available_slug_bytes)}"
diff --git a/luma_core/issue_metrics.py b/luma_core/issue_metrics.py
index a5ecc2c..9b6b0da 100644
--- a/luma_core/issue_metrics.py
+++ b/luma_core/issue_metrics.py
@@ -1527,6 +1527,10 @@ def get_earliest_usage_timestamp(project_path: str, issue_number: int) -> Option
                     except json.JSONDecodeError:
                         continue
 
+                    event_type = data.get("event")
+                    if event_type and event_type != "llm_call":
+                        continue
+
                     # Check if this entry is for the target issue
                     nums = data.get("issue_numbers", [])
                     found = issue_number in nums
diff --git a/luma_core/llm.py b/luma_core/llm.py
index a577bde..7878aeb 100644
--- a/luma_core/llm.py
+++ b/luma_core/llm.py
@@ -383,7 +383,11 @@ class FallbackModel(BaseChatModel):
         active_idx, last_reset = config.get_fallback_info(current_path)
         start_idx = active_idx if 0 <= active_idx < len(self.models) else 0
 
-        for i in range(start_idx, len(self.models)):
+        ordered_indices = list(range(start_idx, len(self.models)))
+        if start_idx > 0:
+            ordered_indices.extend(range(0, start_idx))
+
+        for position, i in enumerate(ordered_indices):
             model = self.models[i]
             call_id = uuid.uuid4().hex[:12]
             start_time = time.time()
@@ -426,7 +430,7 @@ class FallbackModel(BaseChatModel):
                     account=_mask_account(account),
                 )
                 errors.append(f"Model {i + 1} ({model_type}): {str(e)}")
-                if i < len(self.models) - 1:
+                if position < len(ordered_indices) - 1:
                     if is_retryable(error_type_enum):
                         time.sleep(1)
 
diff --git a/luma_core/metrics_summarizer.py b/luma_core/metrics_summarizer.py
index 715a302..556a700 100644
--- a/luma_core/metrics_summarizer.py
+++ b/luma_core/metrics_summarizer.py
@@ -81,6 +81,10 @@ def summarize_usage_stats(
                 except json.JSONDecodeError:
                     continue
 
+                event_type = event.get("event")
+                if event_type and event_type != "llm_call":
+                    continue
+
                 if project and not _event_matches_project(event, project):
                     continue
                 
diff --git a/luma_core/usage_tracker.py b/luma_core/usage_tracker.py
index c4b4e6e..9db5911 100644
--- a/luma_core/usage_tracker.py
+++ b/luma_core/usage_tracker.py
@@ -75,6 +75,16 @@ def get_log_path() -> str:
     return os.path.join(luma_root, _LOG_FILENAME)
 
 
+def _write_event(event: Dict[str, Any]) -> None:
+    log_path = get_log_path()
+    try:
+        with open(log_path, "a", encoding="utf-8") as f:
+            f.write(json.dumps(event, ensure_ascii=False) + "\n")
+    except Exception:
+        # Best-effort logging only
+        pass
+
+
 def _get_luma_version() -> str:
     global _LUMA_VERSION_CACHE
     if _LUMA_VERSION_CACHE is not None:
@@ -285,10 +295,42 @@ def record_llm_event(
         if key not in event and value is not None:
             event[key] = value
 
-    log_path = get_log_path()
-    try:
-        with open(log_path, "a", encoding="utf-8") as f:
-            f.write(json.dumps(event, ensure_ascii=False) + "\n")
-    except Exception:
-        # Best-effort logging only
-        pass
+    _write_event(event)
+
+
+def record_action_event(
+    *,
+    mode: str,
+    action: Optional[str],
+    project: Optional[str],
+    status: str,
+    exit_code: int,
+    duration_ms: Optional[float] = None,
+    error: Optional[str] = None,
+    caller: Optional[str] = None,
+) -> None:
+    event: Dict[str, Any] = {
+        "ts": datetime.now(timezone.utc).isoformat(),
+        "event": "action_run",
+        "mode": mode,
+        "action": action,
+        "project": project,
+        "status": status,
+        "exit_code": exit_code,
+        "duration_ms": int(round(duration_ms or 0)),
+        "session_id": _SESSION_ID,
+        "luma_version": _get_luma_version(),
+        "error": str(error)[:500] if error else None,
+    }
+
+    if caller:
+        event["caller"] = caller
+    if _current_sub_action:
+        event["sub_action"] = _current_sub_action
+
+    context = _build_context()
+    for key, value in context.items():
+        if key not in event and value is not None:
+            event[key] = value
+
+    _write_event(event)
diff --git a/main.py b/main.py
index 71d45fb..e791ecc 100644
--- a/main.py
+++ b/main.py
@@ -97,6 +97,12 @@ def build_parser() -> argparse.ArgumentParser:
         action="store_true",
         help="Emit machine-readable metadata for external consumers",
     )
+    parser.add_argument(
+        "--caller",
+        type=str,
+        default=None,
+        help="Optional caller identifier for headless telemetry",
+    )
     return parser
 
 
@@ -116,7 +122,13 @@ def parse_cli_args(argv=None):
     parser = build_parser()
     args = parser.parse_args(argv)
 
-    headless_requested = args.auto or args.action is not None or args.json or args.meta
+    headless_requested = (
+        args.auto
+        or args.action is not None
+        or args.json
+        or args.meta
+        or args.caller is not None
+    )
     if args.meta:
         if not args.json:
             raise CLIArgumentError(
@@ -307,10 +319,18 @@ def run_headless(args) -> int:
         emit_json(build_metadata_payload())
         return 0
 
+    start_time = time.perf_counter()
     current_cwd = os.getcwd()
     global_config = load_global_config()
     project_map = global_config.get("last_projects_by_path", {})
     stored_project = project_map.get(current_cwd)
+    requested_project = _get_requested_project_value(
+        args,
+        args.project or "1",
+    )
+    action_name = args.action
+    exit_code = 0
+    error_message = None
 
     try:
         project_key = resolve_project_key(
@@ -320,12 +340,17 @@ def run_headless(args) -> int:
             cli_project_explicit=args.project is not None,
         )
         requested_project = _get_requested_project_value(args, project_key)
-        action_name = args.action
+
+        project = PROJECTS[project_key]
+        state = load_state(project["path"])
+        state.project_key = project_key
+
+        usage_tracker.clear_action()
+        usage_tracker.clear_context()
+        usage_tracker.set_action(action_name)
+        usage_tracker.set_context(state, project)
 
         with redirect_stdout(sys.stderr):
-            project = PROJECTS[project_key]
-            state = load_state(project["path"])
-            state.project_key = project_key
             action_runner = _resolve_headless_action(action_name)
             result = action_runner(state, project)
 
@@ -335,25 +360,34 @@ def run_headless(args) -> int:
             print(f"✅ {action_name} completed for project {requested_project}")
         return 0
     except CLIError as exc:
-        requested_project = _get_requested_project_value(
-            args,
-            args.project or "1",
-        )
+        exit_code = exc.exit_code
+        error_message = str(exc)
         if args.json:
-            emit_json(build_error_payload(args.action, requested_project, str(exc)))
+            emit_json(build_error_payload(args.action, requested_project, error_message))
         else:
-            print(s
... (Diff truncated for size) ...


PR TEMPLATE:


INSTRUCTIONS:
1. Generate a comprehensive PR description in Markdown format.
2. If a template is provided, fill it out intelligently.
3. If no template, use a standard structure: Summary, Changes, Impact.
4. Focus on 'Why' and 'What'.
5. Do not include 'Here is the PR description' preamble. Just the body.
6. IMPORTANT: Always use the exact FULL URL for closing issues. You must write `Closes https://github.com/oatrice/Luma/issues/35`. Do NOT use short syntax (e.g., #123) and do not invent an owner/repo.
