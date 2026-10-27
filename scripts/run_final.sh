#!/bin/bash
# usage: scripts/run_final.sh [jobs]
# final traces, with and without prefetching (50M warmup, 200M sim)
export W=50000000 S=200000000 OUT=results/raw/final
J=${1:-6}
mkdir -p "$OUT"

run_one() {
  local cfg=$1 t=$2
  local out="$OUT/${cfg}__$(basename "$t").txt"
  # skip if already done
  grep -q "^CPU 0 cumulative IPC" "$out" 2>/dev/null && return
  bin/1C.fullBW.$cfg --warmup-instructions "$W" --simulation-instructions "$S" "$t" > "$out" 2>&1
}
export -f run_one

# slowest traces are listed first so they start first
while read -r t; do
  for cfg in srrip srrip_nopref; do echo "$cfg traces/$t"; done
done < scripts/final_traces.txt | xargs -P "$J" -n 2 bash -c 'run_one "$@"' _
