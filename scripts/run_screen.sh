#!/bin/bash
# usage: scripts/run_screen.sh [warmup] [sim] [jobs]
# runs every trace in traces/ with and without prefetching
export W=${1:-10000000} S=${2:-50000000} OUT=results/raw/screen
J=${3:-6}
mkdir -p "$OUT"

run_one() {
  local cfg=$1 t=$2
  local out="$OUT/${cfg}__$(basename "$t").txt"
  # skip if already done
  grep -q "^CPU 0 cumulative IPC" "$out" 2>/dev/null && return
  bin/1C.fullBW.$cfg --warmup-instructions "$W" --simulation-instructions "$S" "$t" > "$out" 2>&1
}
export -f run_one

for cfg in srrip srrip_nopref; do
  for t in traces/*; do echo "$cfg $t"; done
done | xargs -P "$J" -n 2 bash -c 'run_one "$@"' _
