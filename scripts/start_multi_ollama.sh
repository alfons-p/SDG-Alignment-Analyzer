#!/bin/bash
# Start multiple Ollama servers for parallel LLM labeling
# Usage: ./start_multi_ollama.sh [num_servers] [model]
# Default: 3 servers with qwen3:8b

NUM_SERVERS=${1:-3}
MODEL=${2:-"qwen3:8b"}
BASE_PORT=11434

echo "=========================================="
echo "Starting $NUM_SERVERS Ollama servers"
echo "Model: $MODEL"
echo "=========================================="

# Check if model is available
if ! ollama list | grep -q "$MODEL"; then
    echo "Model $MODEL not found. Pulling..."
    ollama pull $MODEL
fi

# Function to start a server
start_server() {
    local server_num=$1
    local port=$2
    local log_file="/tmp/ollama_${port}.log"

    echo "Starting Ollama server $server_num on port $port..."

    # Check if port is already in use
    if lsof -Pi :$port -sTCP:LISTEN -t >/dev/null 2>&1; then
        echo "  Port $port already in use, skipping..."
        return
    fi

    # Start Ollama server with custom host
    OLLAMA_HOST=0.0.0.0:$port ollama serve > "$log_file" 2>&1 &
    local pid=$!

    echo "  Server $server_num started (PID: $pid, Port: $port)"
    echo "  Log: $log_file"

    # Wait for server to be ready
    sleep 2
    for i in {1..30}; do
        if curl -s http://localhost:$port/api/tags > /dev/null 2>&1; then
            echo "  ✓ Server $server_num ready"
            return 0
        fi
        sleep 1
    done

    echo "  ✗ Server $server_num failed to start"
    return 1
}

# Start all servers
for i in $(seq 1 $NUM_SERVERS); do
    PORT=$((BASE_PORT + i - 1))
    start_server $i $PORT
done

echo ""
echo "=========================================="
echo "All servers started!"
echo ""
echo "To use with run_analysis.py:"
echo "  python scripts/run_analysis.py \\"
echo "    --input data/raw/2025/SA/ \\"
echo "    --output results \\"
echo "    --use-llm-labeling \\"
echo "    --llm-model $MODEL \\"
echo "    --llm-ollama-hosts $(seq -s ',' -f 'localhost:%g' $BASE_PORT $((BASE_PORT + NUM_SERVERS - 1)))"
echo ""
echo "To stop all servers:"
echo "  ./scripts/stop_multi_ollama.sh"
echo "=========================================="
