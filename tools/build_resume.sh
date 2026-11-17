#!/bin/bash
# Build the résumé files with headless Chrome (PDF) and macOS textutil (Word).
#   bash tools/build_resume.sh [out_dir]     default out_dir: assets
# Needs Google Chrome and network access for Google Fonts. Build into a scratch folder first,
# compare the words (pdftotext -layout), then copy over assets/ and run python3 tools/test_resume.py.
set -euo pipefail
SITE="$(cd "$(dirname "$0")/.." && pwd)"
OUT="${1:-$SITE/assets}"
CHROME="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
PROFILE="${TMPDIR:-/tmp}/chrome-pdf-$$"
mkdir -p "$OUT"

pdf() {  # pdf <source.html> <out.pdf>
  local url="file://$(python3 -c 'import sys, urllib.parse; print(urllib.parse.quote(sys.argv[1]))' "$1")"
  rm -f "$2"
  "$CHROME" --headless=new --disable-gpu --no-pdf-header-footer --user-data-dir="$PROFILE" \
    --virtual-time-budget=10000 --print-to-pdf="$2" "$url" >/dev/null 2>&1 &
  local pid=$!
  for _ in $(seq 1 60); do [ -s "$2" ] && break; sleep 1; done
  sleep 1; kill "$pid" 2>/dev/null || true   # Chrome can hang after writing; the PDF is complete
  [ -s "$2" ] || { echo "PDF not written: $2" >&2; exit 1; }
  echo "wrote $2 ($(pdfinfo "$2" 2>/dev/null | awk '/^Pages/ {print $2}') pages)"
}

# Plain résumés for job boards: one source file each, PDF and Word.
for src in "$SITE"/tools/resume/resume-ats*.html; do
  name=$(basename "$src" .html)
  case "$name" in
    resume-ats) base=Ciarra_Mazaredo_Resume_ATS ;;
    resume-ats-marketing-ops) base=Ciarra_Mazaredo_Resume_ATS_MarketingOps ;;
    resume-ats-ai-automation) base=Ciarra_Mazaredo_Resume_ATS_AIAutomation ;;
    *) echo "unknown source $name" >&2; exit 1 ;;
  esac
  pdf "$src" "$OUT/$base.pdf"
  textutil -convert docx "$src" -output "$OUT/$base.docx"
  echo "wrote $OUT/$base.docx"
done

# Designed Chief of Staff résumé: its source lives beside the site, in Resume/.
DESIGNED="$SITE/../Ciarra_Mazaredo_Resume_ChiefOfStaff.html"
if [ "${WITH_DESIGNED:-0}" = 1 ] && [ -f "$DESIGNED" ]; then
  pdf "$DESIGNED" "$OUT/Ciarra_Mazaredo_Resume_ChiefOfStaff.pdf"
fi
rm -rf "$PROFILE"
