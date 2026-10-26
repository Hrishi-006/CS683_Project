import csv, glob, os, re

rows = {}
for f in sorted(glob.glob("results/raw/screen/*.txt")):
    cfg, trace = os.path.basename(f)[:-4].split("__", 1)
    txt = open(f).read()
    ipc = re.search(r"^CPU 0 cumulative IPC: ([\d.]+) instructions: (\d+)", txt, re.M)
    llc = re.search(r"^cpu0->LLC LOAD\s+ACCESS:\s+(\d+) HIT:\s+(\d+) MISS:\s+(\d+)", txt, re.M)
    if not ipc or not llc:
        print("unfinished:", f)
        continue
    instr = int(ipc.group(2))
    acc, hit, miss = (int(x) for x in llc.groups())
    rows.setdefault(trace, {})[cfg] = (float(ipc.group(1)), 1000 * miss / instr, hit / max(acc, 1))

header = ["trace", "ipc_pref", "ipc_nopref", "speedup", "llc_load_mpki_pref", "llc_load_mpki_nopref", "llc_load_hitrate_nopref"]
out = []
for trace, r in rows.items():
    if "srrip" in r and "srrip_nopref" in r:
        p, n = r["srrip"], r["srrip_nopref"]
        out.append([trace, p[0], n[0], round(p[0] / n[0], 3), round(p[1], 2), round(n[1], 2), round(n[2], 3)])
out.sort(key=lambda x: -x[3])

with open("results/screening.csv", "w", newline="") as fh:
    csv.writer(fh).writerows([header] + out)
for row in [header] + out:
    print(*row, sep="\t")
