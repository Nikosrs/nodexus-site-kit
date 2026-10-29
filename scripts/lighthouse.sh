#!/usr/bin/env bash
# Mobile Lighthouse audit of a URL (local or live). Prints the scores and key metrics.
# Usage: lighthouse.sh <url> [output folder]   (default: captures/)
# Targets: performance >= 90, accessibility / best practices / SEO >= 95, LCP < 2.5 s, CLS < 0.1.
set -euo pipefail
URL="$1"; OUT="${2:-captures}"; mkdir -p "$OUT"
CHROME_PATH="${CHROME_PATH:-/Applications/Google Chrome.app/Contents/MacOS/Google Chrome}" \
npx -y lighthouse@12.6.1 "$URL" --only-categories=performance,accessibility,best-practices,seo \
  --form-factor=mobile --chrome-flags="--headless=new" --output=json --output=html \
  --output-path="$OUT/lighthouse" --quiet
python3 - "$OUT/lighthouse.report.json" <<'PY'
import json, sys
d = json.load(open(sys.argv[1])); a = d["audits"]
sc = {k: round(v["score"] * 100) for k, v in d["categories"].items()}
print("Scores:", sc)
for k in ("largest-contentful-paint", "cumulative-layout-shift", "total-blocking-time", "total-byte-weight"):
    print(f"  {a[k]['title']}: {a[k]['displayValue']}")
ok = sc["performance"] >= 90 and all(sc[c] >= 95 for c in ("accessibility", "best-practices", "seo"))
print("Targets:", "OK" if ok else "NEEDS WORK")
sys.exit(0 if ok else 1)
PY
