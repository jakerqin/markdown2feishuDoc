#!/bin/zsh

set -u

PROJECT_DIR="/Users/yourname/projects/markdown2feishuDoc"
PYTHON_BIN="/Library/Developer/CommandLineTools/Library/Frameworks/Python3.framework/Versions/3.9/bin/python3.9"
LOG_DIR="$PROJECT_DIR/logs"
OUT_LOG="$LOG_DIR/feishu_sync.out.log"
ERR_LOG="$LOG_DIR/feishu_sync.err.log"

mkdir -p "$LOG_DIR"
cd "$PROJECT_DIR" || exit 1

{
  echo "===== $(date '+%Y-%m-%d %H:%M:%S') Terminal sync start ====="
  "$PYTHON_BIN" "$PROJECT_DIR/main.py"
  exit_code=$?
  echo "===== $(date '+%Y-%m-%d %H:%M:%S') Terminal sync exit: $exit_code ====="
  exit "$exit_code"
} >> "$OUT_LOG" 2>> "$ERR_LOG"
