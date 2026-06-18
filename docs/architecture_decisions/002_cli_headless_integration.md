# ADR 002: CLI Headless Integration (Zenith/External Caller Contract)

## Status
Accepted

## Context
External tools (such as the Zenith agent operating in an OpenShell Sandbox) need a reliable way to invoke Luma to perform actions programmatically, without requiring an interactive TTY menu. We needed an integration contract between Luma and external callers.

## Decision
We decided to expose Luma via a CLI wrapper that operates in a "Headless Mode".
Key technical decisions:
1. **Invocation**: External callers invoke Luma via `python main.py --action "<action_name>"`.
2. **Output Contract**: When invoked in headless mode with a flag like `--json`, Luma guarantees that its `stdout` will strictly contain machine-readable JSON output (preventing logs or interactive UI prompts from corrupting the stdout stream).
3. **Subprocess Integration**: External callers (like Zenith's `zenith_core/luma.py` controller) use subprocess calls to interact with Luma's local repository path, parsing the JSON response.

## Consequences
- **Positive**: Enables automated agents and CI/CD pipelines to seamlessly drive Luma workflows.
- **Negative/Constraints**: Luma developers must rigorously isolate standard logs from `stdout` in headless mode to prevent JSON parsing errors on the consumer side.
