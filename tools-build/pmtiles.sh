#!/usr/bin/env bash
# 인천 바탕지도 PMTiles 추출 — GitHub Actions 에서만 돈다(이 클라우드 세션은 build.protomaps.com·GitHub 릴리스가 막혀 있다).
# 이미 있으면(캐시) 건너뛴다. 결과: astro/public/tiles/incheon.pmtiles + incheon.json(출처 빌드 날짜·크기·SHA-256).
set -euo pipefail
cd "$(dirname "$0")/.."
out=astro/public/tiles
mkdir -p "$out"
if [ -s "$out/incheon.pmtiles" ]; then echo "캐시 있음 — 추출 생략"; exit 0; fi
ver=$(python3 -c "import json;print(json.load(open('tools-build/pmtiles.json'))['go_pmtiles'])")
bbox=$(python3 -c "import json;print(json.load(open('tools-build/pmtiles.json'))['bbox'])")
maxz=$(python3 -c "import json;print(json.load(open('tools-build/pmtiles.json'))['maxzoom'])")
tmp=$(mktemp -d)
curl -fsSL "https://github.com/protomaps/go-pmtiles/releases/download/v${ver}/go-pmtiles_${ver}_Linux_x86_64.tar.gz" -o "$tmp/p.tgz"
tar -xzf "$tmp/p.tgz" -C "$tmp"
build=$(curl -fsSL https://build-metadata.protomaps.dev/builds.json | python3 -c "import json,sys;b=json.load(sys.stdin);print(sorted(x['key'] for x in b)[-1])")
"$tmp/pmtiles" extract "https://build.protomaps.com/${build}" "$out/incheon.pmtiles" --bbox="$bbox" --maxzoom="$maxz"
sha=$(sha256sum "$out/incheon.pmtiles" | cut -d' ' -f1)
size=$(stat -c %s "$out/incheon.pmtiles")
printf '{"source":"https://build.protomaps.com/%s","bbox":"%s","maxzoom":%s,"bytes":%s,"sha256":"%s","extracted":"%s","license":"ODbL · © OpenStreetMap · Protomaps"}\n' \
  "$build" "$bbox" "$maxz" "$size" "$sha" "$(date -u +%F)" > "$out/incheon.json"
cat "$out/incheon.json"
