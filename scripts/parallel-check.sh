#!/bin/bash
# 並列実行可能な issue グループを特定する
#
# 判定基準:
#   1. ステータスが pending（main にマージ未済み、ローカルブランチなし）
#   2. 依存 issue がすべて main にマージ済み
#   3. 他の pending issue と Editable Files が重複しない
#
# 使い方:
#   bash scripts/parallel-check.sh          # グループ表示
#   bash scripts/parallel-check.sh --json   # JSON 出力（Supervisor が読み込む用）

ISSUES_DIR="issues"
JSON_MODE=false
[ "$1" = "--json" ] && JSON_MODE=true

# ---------- ユーティリティ ----------

# issue ファイルから Editable Files を抽出（src/... 行のみ）
get_editable_files() {
  local file="$1"
  awk '/^## Editable Files/{found=1; next} found && /^##/{exit} found && /^- /{print $2}' "$file"
}

# issue ファイルから Dependencies を抽出
get_deps() {
  local file="$1"
  awk '/^## Dependencies/{found=1; next} found && /^##/{exit} found && /^- /{print $2}' "$file"
}

# issue ファイルから Branch を抽出
get_branch() {
  local file="$1"
  awk '/^## Branch/{getline; print; exit}' "$file" | tr -d ' '
}

# issue が main にマージ済みか判定
is_merged() {
  local issue_id="$1"
  local branch="$2"
  git log main --oneline 2>/dev/null | grep -qE "$issue_id|$(echo "$branch" | sed 's|feature/||')"
}

# ローカルまたはリモートにブランチが存在するか判定
branch_exists() {
  local branch="$1"
  git branch --list "$branch" 2>/dev/null | grep -q . || \
  git branch -r 2>/dev/null | grep -q "$branch"
}

# ---------- issue 情報収集 ----------

declare -A ISSUE_STATUS   # issue_id → done | in_progress | pending
declare -A ISSUE_FILES    # issue_id → スペース区切りの Editable Files
declare -A ISSUE_DEPS     # issue_id → スペース区切りの依存 issue ID
declare -A ISSUE_BRANCH   # issue_id → ブランチ名
declare -A ISSUE_TITLE    # issue_id → タイトル

for issue_file in "$ISSUES_DIR"/issue[0-9]*.md; do
  [ -f "$issue_file" ] || continue

  ISSUE_ID=$(awk '/^## Issue ID/{getline; print; exit}' "$issue_file" | tr -d ' ')
  [ -z "$ISSUE_ID" ] && ISSUE_ID=$(basename "$issue_file" .md)

  BRANCH=$(get_branch "$issue_file")
  TITLE=$(awk '/^## Title/{getline; print; exit}' "$issue_file" | sed 's/^[[:space:]]*//')
  FILES=$(get_editable_files "$issue_file" | tr '\n' ' ')
  DEPS=$(get_deps "$issue_file" | tr '\n' ' ')

  ISSUE_TITLE[$ISSUE_ID]="$TITLE"
  ISSUE_BRANCH[$ISSUE_ID]="$BRANCH"
  ISSUE_FILES[$ISSUE_ID]="$FILES"
  ISSUE_DEPS[$ISSUE_ID]="$DEPS"

  if is_merged "$ISSUE_ID" "$BRANCH"; then
    ISSUE_STATUS[$ISSUE_ID]="done"
  elif branch_exists "$BRANCH"; then
    ISSUE_STATUS[$ISSUE_ID]="in_progress"
  else
    ISSUE_STATUS[$ISSUE_ID]="pending"
  fi
done

# ---------- 並列化可能グループの特定 ----------

# pending かつ依存がすべて done の issue を抽出
READY=()
for id in "${!ISSUE_STATUS[@]}"; do
  [ "${ISSUE_STATUS[$id]}" = "pending" ] || continue

  all_deps_done=true
  for dep in ${ISSUE_DEPS[$id]}; do
    dep=$(echo "$dep" | grep -oE 'issue[0-9]+')
    [ -z "$dep" ] && continue
    if [ "${ISSUE_STATUS[$dep]}" != "done" ]; then
      all_deps_done=false
      break
    fi
  done

  $all_deps_done && READY+=("$id")
done

# READY リスト内で Editable Files が重複しないグループを貪欲法で作成
declare -a GROUPS   # "issue01 issue03" 形式の文字列配列
declare -A ASSIGNED # issue_id → グループインデックス

for id in "${READY[@]}"; do
  placed=false
  for i in "${!GROUPS[@]}"; do
    conflict=false
    for existing_id in ${GROUPS[$i]}; do
      # Files の重複チェック
      for f in ${ISSUE_FILES[$id]}; do
        if echo "${ISSUE_FILES[$existing_id]}" | grep -qF "$f"; then
          conflict=true
          break 2
        fi
      done
    done
    if ! $conflict; then
      GROUPS[$i]="${GROUPS[$i]} $id"
      ASSIGNED[$id]=$i
      placed=true
      break
    fi
  done
  if ! $placed; then
    GROUPS+=("$id")
    ASSIGNED[$id]=$((${#GROUPS[@]} - 1))
  fi
done

# ---------- 出力 ----------

if $JSON_MODE; then
  # JSON 形式で出力（Supervisor が読み込む用）
  echo "{"
  echo "  \"ready\": ["
  for i in "${!READY[@]}"; do
    id="${READY[$i]}"
    sep=","
    [ $((i + 1)) -eq ${#READY[@]} ] && sep=""
    printf '    {"id": "%s", "branch": "%s", "title": "%s", "group": %d}%s\n' \
      "$id" "${ISSUE_BRANCH[$id]}" "${ISSUE_TITLE[$id]}" "${ASSIGNED[$id]:-0}" "$sep"
  done
  echo "  ],"
  echo "  \"groups\": ["
  for i in "${!GROUPS[@]}"; do
    sep=","
    [ $((i + 1)) -eq ${#GROUPS[@]} ] && sep=""
    ids=$(echo "${GROUPS[$i]}" | tr ' ' '\n' | grep -v '^$' | sed 's/.*/"&"/' | paste -sd ',' -)
    echo "    [$ids]$sep"
  done
  echo "  ]"
  echo "}"
else
  # 人間向け表示
  echo ""
  echo "============================================"
  echo "  並列実行可能グループ"
  echo "============================================"

  if [ ${#READY[@]} -eq 0 ]; then
    echo ""
    echo "  並列実行可能な issue はありません。"
    echo "  （pending issue がないか、依存が未完了です）"
    echo ""
  else
    for i in "${!GROUPS[@]}"; do
      echo ""
      printf "  【グループ %d】同時実行可\n" $((i + 1))
      for id in ${GROUPS[$i]}; do
        [ -z "$id" ] && continue
        printf "    %-10s  %s\n" "$id" "${ISSUE_TITLE[$id]}"
        printf "              branch: %s\n" "${ISSUE_BRANCH[$id]}"
        [ -n "${ISSUE_FILES[$id]}" ] && \
          printf "              files:  %s\n" "${ISSUE_FILES[$id]}"
      done
    done
    echo ""
    echo "--------------------------------------------"
    printf "  実行可能: %d issue  /  %d グループ\n" "${#READY[@]}" "${#GROUPS[@]}"
  fi

  echo "============================================"
  echo ""
fi
