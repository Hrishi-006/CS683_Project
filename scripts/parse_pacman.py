# Checkpoint 2, step 1: compares PACMan-style insertion against SRRIP (both with prefetching)
# usage: python3 scripts/parse_pacman.py   -> results/pacman_checkpoint2.csv
import csv, glob, math, os, re, sys

sys.path.insert(0, os.path.dirname(__file__))


def parse(path):
    txt = open(path).read()
    m = re.search(r"^CPU 0 cumulative IPC: ([\d.]+) instructions: (\d+)", txt, re.M)
    if not m:
        return None
    r = {"ipc": float(m.group(1)), "instr": int(m.group(2))}
    m = re.search(r"^cpu0->LLC LOAD\s+ACCESS:\s+(\d+) HIT:\s+(\d+) MISS:\s+(\d+)", txt, re.M)
    r["llc_load_miss"] = int(m.group(3))
    m = re.search(r"^PFSTUDY LLC_PF_FILLS: (\d+) USED_LLC: (\d+) USED_UPPER_ONLY: (\d+) UNUSED: (\d+) STILL_RESIDENT: (\d+) HARMFUL_EVICTIONS: (\d+)",
                  txt, re.M)
    r.update(zip(["pf_fills", "used_llc", "used_upper", "unused", "resident", "harmful"], map(int, m.groups())))
    return r


runs = {}
for f in sorted(glob.glob("results/raw/final/*.txt")):
    cfg, trace = os.path.basename(f)[:-4].split("__", 1)
    if cfg not in ("srrip", "srrip_nopref", "pacman"):
        continue
    r = parse(f)
    if r is None:
        print("unfinished:", f)
        continue
    runs.setdefault(trace, {})[cfg] = r

header = ["trace", "group", "ipc_nopref", "ipc_srrip", "ipc_pacman", "pacman_vs_srrip", "pacman_vs_nopref", "mpki_srrip", "mpki_pacman",
          "harmful_pki_srrip", "harmful_pki_pacman", "pf_fills_pki_srrip", "pf_fills_pki_pacman", "unused_frac_srrip", "unused_frac_pacman"]


def frac(r):
    c = r["used_llc"] + r["used_upper"] + r["unused"]
    return round(r["unused"] / c, 3) if c else 0.0


rows = []
for trace, r in runs.items():
    if not all(k in r for k in ("srrip", "srrip_nopref", "pacman")):
        continue
    s, n, p = r["srrip"], r["srrip_nopref"], r["pacman"]
    ks, kp = s["instr"] / 1000, p["instr"] / 1000
    rows.append([trace, "AI" if "llama" in trace else "control", n["ipc"], s["ipc"], p["ipc"], round(p["ipc"] / s["ipc"], 4),
                 round(p["ipc"] / n["ipc"], 3), round(s["llc_load_miss"] / ks, 2), round(p["llc_load_miss"] / kp, 2),
                 round(s["harmful"] / ks, 3), round(p["harmful"] / kp, 3), round(s["pf_fills"] / ks, 2), round(p["pf_fills"] / kp, 2),
                 frac(s), frac(p)])
rows.sort(key=lambda x: (x[1], x[0]))

with open("results/pacman_checkpoint2.csv", "w", newline="") as fh:
    csv.writer(fh).writerows([header] + rows)
for row in [header] + rows:
    print(*row, sep="\t")

for group in ("AI", "control"):
    v = [row[5] for row in rows if row[1] == group]
    if v:
        print(f"\ngeomean pacman/srrip ({group}): {math.exp(sum(map(math.log, v)) / len(v)):.4f}")
