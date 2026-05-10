#!/bin/bash
# Pre-PR check: gh pr create 実行前に Acceptance Criteria / Definition of Done の未完了項目を検証する
# Claude Code の PreToolUse hook から呼び出される（stdin に tool input JSON が渡される）

INPUT=$(cat)
COMMAND=$(echo "$INPUT" | python3 -c "import sys, json; d=json.load(sys.stdin); print(d.get('command',''))" 2>/dev/null)

# gh pr create コマンド以外はスキップ
if ! echo "$COMMAND" | grep -qE "gh pr create"; then
  exit 0
fi

BRANCH=$(git branch --show-current 2>/dev/null)
if [ -z "$BRANCH" ]; then
  exit 0
fi

# ブランチ名から issue ID を抽出（例: feature/issue04-scan-command → issue04）
ISSUE_ID=$(echo "$BRANCH" | grep -oE 'issue[0-9]+')
if [ -z "$ISSUE_ID" ]; then
  exit 0
fi

ISSUE_FILE="issues/${ISSUE_ID}.md"
if [ ! -f "$ISSUE_FILE" ]; then
  echo "Warning: $ISSUE_FILE が見つかりません。チェックをスキップします。"
  exit 0
fi

# 未完了チェックボックス（- [ ]）をカウント
UNCHECKED=$(grep -c "^- \[ \]" "$ISSUE_FILE" 2>/dev/null || echo "0")

if [ "$UNCHECKED" -gt 0 ]; then
  echo ""
  echo "=========================================="
  echo " PR 作成ブロック: 未完了チェックあり"
  echo "=========================================="
  echo " Issue:   $ISSUE_FILE"
  echo " 未完了:  ${UNCHECKED} 件"
  echo ""
  grep "^- \[ \]" "$ISSUE_FILE" | while IFS= read -r line; do
    echo "  $line"
  done
  echo ""
  echo " 全項目を [ ] → [x] に更新してから再実行してください。"
  echo "=========================================="
  echo ""
  exit 2
fi

echo "[pre-pr-check] OK: ${ISSUE_ID} の全チェック項目が完了しています"
exit 0
