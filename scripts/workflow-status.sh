#!/bin/bash
# MVP 進捗ダッシュボード
# 使い方: bash scripts/workflow-status.sh

ISSUES_DIR="issues"

echo ""
echo "=================================="
echo "  MVP 進捗ダッシュボード"
echo "=================================="
echo ""

DONE=0
TOTAL=0

for issue_file in "$ISSUES_DIR"/issue[0-9]*.md; do
  [ -f "$issue_file" ] || continue

  # ## Issue ID セクションがあればそこから、なければファイル名から取得
  ISSUE_ID=$(awk '/^## Issue ID/{getline; print; exit}' "$issue_file" | tr -d ' ')
  [ -z "$ISSUE_ID" ] && ISSUE_ID=$(basename "$issue_file" .md)
  TITLE=$(awk '/^## Title/{getline; print}' "$issue_file" | sed 's/^[[:space:]]*//')
  BRANCH=$(awk '/^## Branch/{getline; print}' "$issue_file" | tr -d ' ')
  DEPS=$(awk '/^## Dependencies/{found=1; next} found && /^##/{exit} found && /^- /{printf "%s ", $2}' "$issue_file")

  TOTAL=$((TOTAL + 1))

  # main にマージ済みかチェック
  if git log main --oneline 2>/dev/null | grep -q "$ISSUE_ID\|$(echo "$BRANCH" | sed 's|feature/||')"; then
    ICON="✓"
    STATUS="done"
    DONE=$((DONE + 1))
  # ローカルまたはリモートにブランチが存在するか
  elif git branch --list "$BRANCH" 2>/dev/null | grep -q . || \
       git branch -r 2>/dev/null | grep -q "$BRANCH"; then
    ICON="⏳"
    STATUS="in progress"
  else
    ICON="○"
    STATUS="pending"
  fi

  DEPS_DISPLAY=""
  [ -n "$(echo "$DEPS" | tr -d ' ')" ] && DEPS_DISPLAY=" (依存: ${DEPS%% })"

  printf "  %s %-10s  %-8s  %s%s\n" "$ICON" "$ISSUE_ID" "$STATUS" "$TITLE" "$DEPS_DISPLAY"
done

echo ""
echo "----------------------------------"
printf "  完了: %d / %d\n" "$DONE" "$TOTAL"
echo "=================================="
echo ""
