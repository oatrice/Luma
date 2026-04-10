#!/bin/bash
# Install Git hooks for Luma

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# Get git directory (handles both regular repos and worktrees)
GIT_DIR=$(cd "$REPO_ROOT" && git rev-parse --git-dir 2>/dev/null) || {
    echo "✗ Not a git repository"
    exit 1
}

HOOKS_DIR="$GIT_DIR/hooks"

echo "🔧 Installing Git hooks..."
echo "→ Git directory: $GIT_DIR"

# Create hooks directory if it doesn't exist
mkdir -p "$HOOKS_DIR"

# Install pre-commit hook
if [ -f "$SCRIPT_DIR/pre-commit" ]; then
    cp "$SCRIPT_DIR/pre-commit" "$HOOKS_DIR/pre-commit"
    chmod +x "$HOOKS_DIR/pre-commit"
    echo "✓ Installed pre-commit hook"
else
    echo "✗ pre-commit script not found"
fi

# Install pre-push hook
if [ -f "$SCRIPT_DIR/pre-push" ]; then
    cp "$SCRIPT_DIR/pre-push" "$HOOKS_DIR/pre-push"
    chmod +x "$HOOKS_DIR/pre-push"
    echo "✓ Installed pre-push hook"
else
    echo "✗ pre-push script not found"
fi

echo ""
echo "✅ Git hooks installed successfully!"
echo ""
echo "To skip hooks temporarily:"
echo "  git commit --no-verify"
echo "  git push --no-verify"
