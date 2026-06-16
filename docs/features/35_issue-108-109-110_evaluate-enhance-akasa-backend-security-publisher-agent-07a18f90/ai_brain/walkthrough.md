# OpenClaw Telemetry Tracker Walkthrough

The Telemetry Tracker has been successfully implemented and verified. It collects OS-level, Docker-level, and LM Studio metrics with low overhead, and correlates them with OpenClaw sessions.

## Changes Made

### 1. Database Setup (`schema.sql`)
- Created a simple SQLite schema with a `telemetry` table.
- Stores `timestamp`, `target` (e.g., `host_os`, `host_lmstudio`, `docker_container_name`), `cpu_percent`, and `ram_mb`.
- Added indexes on `timestamp` and `target` to ensure fast queries.

### 2. Metric Collection Daemon (`collector.py`)
- Built a lightweight collector using Python standard libraries and native OS commands (`ps`, `docker stats`) to keep overhead negligible.
- **Host & LM Studio:** Uses `ps -A -o %cpu,rss,command` to calculate overall CPU/RAM and isolates the `LM Studio` processes automatically.
- **Docker:** Parses `docker stats --no-stream` to retrieve live telemetry of running containers (like `openclaw-gateway`, `openclaw-cli`).
- Runs in a continuous loop, pushing metrics into SQLite (`telemetry.db`) every 5 seconds. Time is strictly formatted as UTC to align with the OpenClaw `.jsonl` session logs.

### 3. Session Analyzer (`analyzer.py`)
- Created a CLI tool to query the collected data for specific OpenClaw sessions.
- Automatically searches `~/.openclaw/agents/main/sessions/` for the relevant `.jsonl` session file and extracts its exact `Start` and `End` timestamps.
- Avoids `.trajectory.jsonl` files and seamlessly handles both ISO strings and UNIX timestamps.
- Queries the `telemetry.db` SQLite database to produce an aggregated summary report of **Peak RAM (MB)** and **Average CPU (%)** per target during that specific session.

## Validation Results

**Manual Verification:**
1. Ran `collector.py` locally and verified it successfully initialized `telemetry.db` and began recording metrics for both `ps` outputs and Docker containers.
2. Verified `analyzer.py` on a real historical OpenClaw session (`7e0b4f83-6509-4610-875b-4a8bc442c0ee`). 
3. Confirmed it successfully parsed the session JSONL start/end times (`2026-06-15 04:51:34` to `04:55:50`) and displayed the correct metrics table.

> [!TIP]
> You can now run the collector in the background (`nohup python3 collector.py &`) and analyze any session by running `python3 analyzer.py --session <session_id>`.
