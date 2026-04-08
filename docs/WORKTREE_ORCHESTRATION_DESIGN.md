# Multi-Agent Worktree Orchestration Design

**Status:** Draft  
**Created:** April 8, 2026  
**Applies to:** Cerebro, Zenith, Luma  
**Related:** Cerebro #4, #5, #8 | Zenith orchestration contract

---

## Executive Summary

เอกสารนี้ออกแบบ architecture สำหรับ **multi-agent isolation** และ **worktree management** ใน oatrice ecosystem รองรับ scenarios:

1. Multiple agents (Agent-TheMiddle_Way, Agent-JarWise, Agent-Luma) ใช้ Luma CLI พร้อมกัน
2. Self-modification: Agents แก้ไข Luma เอง (Agent-Luma-feat-1, Agent-Luma-feat-2)
3. Conflict detection และ merge queue ก่อน PR

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                    CEREBRO (Central Hub)                        │
│  ┌──────────────┐  ┌──────────────┐  ┌─────────────────────┐  │
│  │ Dashboard    │  │ Worktree     │  │ Conflict Detection  │  │
│  │ (Monitor all)│  │ Registry     │  │ & Merge Queue       │  │
│  │              │  │ (cache)      │  │ + HITL Approval     │  │
│  └──────────────┘  └──────────────┘  └─────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
                              │
              ┌───────────────┼───────────────┐
              │               │               │
              ▼               ▼               ▼
┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐
│ Agent-TMW       │  │ Agent-JarWise   │  │ Agent-Luma      │
│                 │  │                 │  │ (Luma self-edit) │
└────────┬────────┘  └────────┬────────┘  └────────┬────────┘
         │                    │                    │
         └────────────────────┼────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│              ZENITH (Orchestrator)                          │
│  ┌──────────────┐  ┌──────────────┐  ┌────────────────────┐  │
│  │ Agent-Spawner│  │ Worktree     │  │ Luma CLI         │  │
│  │              │  │ Lifecycle    │  │ Wrapper          │  │
│  │              │  │ (create/run) │  │                  │  │
│  └──────────────┘  └──────────────┘  └────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
                              │
              ┌───────────────┼───────────────┐
              │               │               │
              ▼               ▼               ▼
┌─────────────────────────────────────────────────────────────┐
│              LUMA WORKTREE POOL (Isolated)                  │
│                                                             │
│  ┌────────────┐ ┌────────────┐ ┌────────────────────────┐  │
│  │ luma-wt-1  │ │ luma-wt-2  │ │ luma-self-feat-1       │  │
│  │ (pinned    │ │ (pinned    │ │ (branch: feat/abc)     │  │
│  │  commit)   │ │  commit)   │ │ .luma_state.json       │  │
│  └────────────┘ └────────────┘ └────────────────────────┘  │
│                                                             │
│  ┌─────────────────────────────────────────────────────────┐│
│  │ luma-self-feat-2 (branch: feat/xyz)                   ││
│  │ → Conflict detection → Merge queue → HITL approval     ││
│  └─────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────┘
```

---

## Design Decisions

### 1. Worktree Ownership: Hybrid Model

| Layer | Responsibility | Rationale |
|-------|---------------|-----------|
| **Cerebro** | Registry, Conflict Detection, HITL Coordination | Central visibility, cross-agent coordination |
| **Zenith** | Worktree Lifecycle Management (create/run/destroy) | Close to execution, knows when to spawn |
| **Luma** | State Storage (Source of Truth) | Owns its own repo state |

**Flow:**
1. Cerebro: "Need worktree for Agent-X"
2. Zenith: Create worktree (via Luma action if available, else direct git)
3. Zenith: Run Luma CLI in that worktree
4. Zenith: Report state back to Cerebro

### 2. State Isolation: Hybrid (Worktree + Cerebro Cache)

**Source of Truth (in each worktree):**
- `.luma_state.json` - Luma CLI read/write
- `.luma_metrics.json` - Actual metrics
- `.luma_ai_usage.jsonl` - Usage logs

**Cerebro Cache (for dashboard/visibility):**
- `data/luma-worktrees/wt-{id}.json` - Snapshot of latest state
- `data/luma-conflicts/pending-merges.json` - Merge queue

**Sync Strategy:**
- **Write:** Luma → worktree files (real-time) → Zenith → Cerebro cache (async)
- **Read:** Dashboard reads from Cerebro cache (fast), "refresh" button pulls latest

### 3. Communication Pattern: Push Primary + Poll Backup

| Pattern | Use Case | Implementation |
|---------|----------|----------------|
| **Push** | Real-time state update | Zenith POST to Cerebro `/api/v1/worktree-state` after run |
| **Poll** | Dashboard refresh, backup sync | Cerebro poll Zenith status periodically or on-demand |
| **WebSocket** | Future real-time dashboard | Consider for Phase 2 |

**Failure handling:**
- If push fails, Cerebro uses poll as fallback
- If both fail, worktree marked "stale" in dashboard

### 4. Conflict Detection: Auto + Queue + HITL

```
Agent-Luma-feat-1  แก้ main.py ─┐
                                │
Agent-Luma-feat-2  แก้ main.py ─┼─→ Cerebro Conflict Detection
                                │
                                ▼
                  ┌─────────────────────────┐
                  │  ตรวจพบ: แก้ไฟล์ซ้ำกัน  │
                  └────────────┬────────────┘
                               │
         ┌─────────────────────┼─────────────────────┐
         │                     │                     │
         ▼                     ▼                     ▼
  ┌─────────────┐      ┌─────────────┐      ┌─────────────┐
  │ Auto-merge  │      │ Merge Queue │      │ Manual      │
  │ ได้ (คนละ   │      │ (รอ review) │      │ (HITL via   │
  │ function)   │      │             │      │ Akasa)      │
  └──────┬──────┘      └──────┬──────┘      └──────┬──────┘
         │                     │                     │
         ▼                     ▼                     ▼
     Merge ทันที          รอ approve       ส่ง Telegram
                                               │
                                        คนกด ✅ หรือ ❌
                                               │
                                        จบ / retry
```

---

## Component Specifications

### Cerebro Components

```typescript
// lib/luma-worktree-registry.ts
interface LumaWorktree {
  id: string;                    // "luma-wt-jarwise-001"
  agent: string;                 // "Agent-JarWise"
  worktreePath: string;          // "../Luma-worktrees/wt-001"
  pinnedCommit: string;        // "abc123"
  branch: string;               // "feat/jarwise-integration"
  stateFile: string;            // ".luma_state.json"
  status: "active" | "conflict" | "merged" | "closed" | "stale";
  lastSync: string;             // ISO timestamp
  metrics: LumaMetricsSnapshot;
}

// lib/luma-conflicts.ts
interface ConflictResolution {
  worktrees: [string, string];        // ["luma-self-1", "luma-self-2"]
  conflictingFiles: string[];        // ["main.py", "agents/coder.py"]
  resolutionType: "auto" | "queued" | "manual";
  
  // Auto merge
  autoMergeable: boolean;            // true if non-overlapping changes
  
  // Queue
  queuePosition: number;
  estimatedMergeTime: string;
  
  // Manual/HITL
  hitlRequestId?: string;           // Akasa notification ID
  manualSteps?: string[];           // Instructions for manual resolve
}

// API endpoints
POST /api/v1/worktree-state       // Zenith pushes state
GET  /api/v1/worktrees            // Dashboard queries
POST /api/v1/resolve-conflict     // HITL approval/reject
```

### Zenith Components

```python
# zenith_core/luma_worktree.py
class LumaWorktreeManager:
    def ensure_worktree(
        self,
        agent_id: str,
        base_commit: str,
        branch_name: str
    ) -> WorktreeInfo:
        """
        Create or reuse worktree for agent.
        
        Strategy:
        1. Try Luma CLI: --action ensure_worktree
        2. Fallback: direct git worktree add
        """
        pass
    
    def destroy_worktree(self, worktree_id: str) -> None:
        """Clean up after agent done."""
        pass

# zenith_core/luma_cli.py
class LumaCLIWrapper:
    def run_in_worktree(
        self,
        worktree_path: str,
        action: str,
        project_key: str
    ) -> LumaActionResponse:
        """Run Luma CLI in specific worktree."""
        pass
    
    def report_state_to_cerebro(
        self,
        worktree_id: str,
        state: LumaWorktreeState
    ) -> bool:
        """Push state to Cerebro (with retry)."""
        pass
```

### Luma Components

```python
# actions/worktree.py (proposed)
class EnsureWorktreeAction:
    """
    Luma action to manage its own worktrees.
    
    Input: {
        "agent_id": "Agent-JarWise",
        "base_commit": "abc123",
        "branch_name": "feat/jarwise-integration"
    }
    
    Output: {
        "worktree_path": "../Luma-worktrees/wt-001",
        "branch": "feat/jarwise-integration",
        "created": true
    }
    """
    pass
```

---

## Use Case Scenarios

### Scenario A: Agents ใช้ Luma เป็น Tool (Read-only)

```
Agent-JarWise  →  Zenith  →  Luma (worktree: luma-wt-jarwise)
                                ├── pinned to: commit-abc123
                                ├── .luma_state.json (isolated)
                                └── read-only to main repo
```

**Key:** แต่ละ agent ใช้ Luma คนละ worktree แต่ **pin ที่ commit เดียวกัน** (stable)

### Scenario B: Agents แก้ไข Luma เอง (Write)

```
Agent-Luma-feat-1  →  Luma (worktree: luma-self-1, branch: feat/abc)
                           ↓
                    Cerebro Conflict Detection
                           ↓
Agent-Luma-feat-2  →  Luma (worktree: luma-self-2, branch: feat/xyz)
                           ↓
              Merge Queue → PR Review → Close both
```

**Key:** Cerebro track ว่ามีกี่ feature branch กำลังแก้ Luma และ detect conflict

---

## Data Flow Examples

### 1. Worktree Creation Flow

```
[Cerebro] ส่ง request → [Zenith]
   "Create worktree for Agent-JarWise"
                            │
                            ▼
                   [Zenith] ตรวจ: Luma มี ensure_worktree?
                            │
                   ┌─────────┴─────────┐
                   │                   │
                   ▼                   ▼
              [Yes: Luma]          [No: Direct git]
                   │                   │
                   ▼                   ▼
         luma --action ensure    git worktree add
         --agent-id jarwise      ../Luma-worktrees/jarwise-001
                            │
                            ▼
         [Zenith] ได้ worktree_path
                            │
                            ▼
         [Zenith] รัน Luma CLI ใน worktree นั้น
                            │
                            ▼
         [Zenith] POST state → [Cerebro]
                            │
                            ▼
         [Cerebro] Update cache, Dashboard refresh
```

### 2. Conflict Detection Flow

```
[Agent-Luma-feat-1] แก้ main.py ──┐
                                  │
[Agent-Luma-feat-2] แก้ main.py ──┼──→ [Zenith] report ทั้งสอง
                                  │
                                  ▼
                         [Cerebro] Conflict Detection
                         - เปรียบเทียบ branch feat/abc vs feat/xyz
                         - หา overlapping files
                                  │
                    ┌─────────────┼─────────────┐
                    ▼             ▼             ▼
               Non-conflict   Overlap      Same function
               → Auto-merge   → Queue      → HITL
```

---

## Integration Points

### Cerebro ↔ Zenith

| Direction | Method | Payload | Purpose |
|-----------|--------|---------|---------|
| Cerebro → Zenith | API/CLI | `{ agent_id, task, requirements }` | Request agent spawn |
| Zenith → Cerebro | POST /api/v1/worktree-state | `{ worktree_id, status, state }` | Push state |
| Cerebro → Zenith | GET /api/v1/worktree-status | Query params | Poll backup |

### Zenith ↔ Luma

| Direction | Method | Payload | Purpose |
|-----------|--------|---------|---------|
| Zenith → Luma | CLI | `--action ensure_worktree --agent-id x` | Create worktree |
| Luma → Zenith | JSON stdout | `{ worktree_path, branch, created }` | Return path |
| Zenith → Luma | CLI | `python3 main.py --auto --action y --json` | Run action |
| Luma → Zenith | JSON stdout | `LumaActionResponse` | Return result |

---

## Open Questions

1. **Luma version pinning:** ถ้า Agent-A ใช้ Luma v1.2.0 และ Agent-B ใช้ v1.3.0 (breaking changes) จะ handle ยังไง?

2. **Worktree cleanup:** Destroy worktree เมื่อไหร่? (agent done, after merge, or keep for history?)

3. **Scale limits:** สูงสุดกี่ worktree? (disk space, git performance)

4. **Nested worktrees:** ถ้า Cerebro เองก็อยู่ใน worktree (feat-4-5-3) จะมีปัญหา recursive ไหม?

---

## Next Steps

### Immediate (Cerebro #4, #5, #8)

1. [ ] Implement `lib/luma-worktree-registry.ts` - Cerebro
2. [ ] Implement worktree-aware dashboard cards - Cerebro #5
3. [ ] Add GitHub repo sync with worktree metadata - Cerebro #4

### Near-term (Zenith integration)

4. [ ] Add `ensure_worktree` action to Luma (optional)
5. [ ] Implement `LumaWorktreeManager` - Zenith
6. [ ] Add state push to Cerebro - Zenith

### Future (Conflict resolution)

7. [ ] Implement conflict detection algorithm - Cerebro
8. [ ] Add merge queue with HITL - Cerebro + Akasa
9. [ ] WebSocket real-time updates

---

## References

- Zenith: `docs/contracts/luma_orchestration_contract.md`
- Cerebro: `docs/ROADMAP.md` (Phase 2: Orchestration & Integration)
- Luma: `docs/cross_repo_link_guide.md`

---

## Change Log

| Date | Version | Changes |
|------|---------|---------|
| 2026-04-08 | 0.1.0 | Initial draft from design discussion |

