#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
EVIDENCE_DIR="$ROOT_DIR/docs/evidence"
RELEASE_DIR="$EVIDENCE_DIR/releases"

BUNDLE_DATE="${1:-20260314}"
BUNDLE_NAME="so101-e2e-evidence-${BUNDLE_DATE}"
BUNDLE_ROOT="$RELEASE_DIR/$BUNDLE_NAME"
PAYLOAD_DIR="$BUNDLE_ROOT/payload"
MANIFEST_MD="$BUNDLE_ROOT/MANIFEST.md"
MANIFEST_JSON="$BUNDLE_ROOT/manifest.json"
SHA_FILE="$BUNDLE_ROOT/SHA256SUMS.txt"
ARCHIVE_FILE="$RELEASE_DIR/${BUNDLE_NAME}.tar.gz"

FILES=(
  "docs/evidence/E2E-001_冷启动通过_2026-03-14.md"
  "docs/evidence/E2E-001_启动脚本说明_2026-03-14.md"
  "docs/evidence/E2E-001_实跑记录_2026-03-14.md"
  "docs/evidence/E2E-002_演示脚本_2026-03-14.md"
  "docs/evidence/E2E-002_回归清单_2026-03-14.md"
  "docs/evidence/E2E-002_首轮回归记录_2026-03-14.md"
  "docs/evidence/FE-002_FE-003_取证步骤_2026-03-14.md"
  "docs/evidence/MES-002_联调记录_2026-03-14.md"
  "docs/evidence/browser/e2e-002-agent-browser-20260314.png"
  "docs/evidence/browser/e2e-002-agent-browser-live-20260314.png"
  "docs/evidence/fe-002-fe-003-demo-20260314190106.webm"
  "docs/evidence/fe-002-order-flow-20260314190106.png"
  "docs/evidence/fe-003-detection-stream-20260314190106.png"
  "docs/evidence/fe-inject-20260314201226.log"
  "docs/任务清单.md"
  "docs/进度日志.md"
  "tools/e2e/start_e2e_stack.sh"
  "tools/e2e/stop_e2e_stack.sh"
  "tools/e2e/run_demo_sequence.sh"
)

mkdir -p "$PAYLOAD_DIR"
rm -rf "$BUNDLE_ROOT"
mkdir -p "$PAYLOAD_DIR"

for rel in "${FILES[@]}"; do
  src="$ROOT_DIR/$rel"
  if [[ ! -f "$src" ]]; then
    echo "missing required file: $rel" >&2
    exit 1
  fi
  mkdir -p "$PAYLOAD_DIR/$(dirname "$rel")"
  cp "$src" "$PAYLOAD_DIR/$rel"
done

manifest_entries=()
for rel in "${FILES[@]}"; do
  size="$(stat -c %s "$ROOT_DIR/$rel")"
  sha="$(sha256sum "$ROOT_DIR/$rel" | awk '{print $1}')"
  manifest_entries+=("{\"path\":\"$rel\",\"size\":$size,\"sha256\":\"$sha\"}")
done

{
  echo "# SO101 E2E Evidence Bundle"
  echo
  echo "- bundle: \`$BUNDLE_NAME\`"
  echo "- generated_at: \`$(date '+%Y-%m-%d %H:%M:%S %z')\`"
  echo "- archive: \`docs/evidence/releases/${BUNDLE_NAME}.tar.gz\`"
  echo "- file_count: \`${#FILES[@]}\`"
  echo
  echo "## Included Files"
  echo
  for rel in "${FILES[@]}"; do
    size="$(stat -c %s "$ROOT_DIR/$rel")"
    sha="$(sha256sum "$ROOT_DIR/$rel" | awk '{print $1}')"
    echo "- \`$rel\`"
    echo "  size: \`${size}\` bytes"
    echo "  sha256: \`${sha}\`"
  done
} >"$MANIFEST_MD"

{
  echo "{"
  echo "  \"bundle\": \"$BUNDLE_NAME\","
  echo "  \"generated_at\": \"$(date -Iseconds)\","
  echo "  \"file_count\": ${#FILES[@]},"
  echo "  \"files\": ["
  for i in "${!manifest_entries[@]}"; do
    sep=","
    if [[ "$i" -eq $((${#manifest_entries[@]} - 1)) ]]; then
      sep=""
    fi
    echo "    ${manifest_entries[$i]}$sep"
  done
  echo "  ]"
  echo "}"
} >"$MANIFEST_JSON"

(
  cd "$PAYLOAD_DIR"
  find . -type f | sort | sed 's#^\./##' | while read -r rel; do
    sha256sum "$rel"
  done
) >"$SHA_FILE"

rm -f "$ARCHIVE_FILE"
(
  cd "$RELEASE_DIR"
  tar -czf "$(basename "$ARCHIVE_FILE")" "$(basename "$BUNDLE_ROOT")"
)

echo "bundle_root: $BUNDLE_ROOT"
echo "archive: $ARCHIVE_FILE"
echo "manifest: $MANIFEST_MD"
echo "sha256: $SHA_FILE"
