#!/bin/bash
# Stop all Ollama servers

echo "Stopping all Ollama servers..."

# Find and kill all ollama serve processes
pids=$(pgrep -f "ollama serve" || true)

if [ -n "$pids" ]; then
    echo "Killing Ollama PIDs: $pids"
    kill $pids 2>/dev/null || true
    sleep 1
    # Force kill if still running
    pids=$(pgrep -f "ollama serve" || true)
    if [ -n "$pids" ]; then
        kill -9 $pids 2>/dev/null || true
    fi
    echo "✓ All Ollama servers stopped"
else
    echo "No Ollama servers running"
fi

# Clean up log files
rm -f /tmp/ollama_*.log
echo "✓ Cleaned up log files"
