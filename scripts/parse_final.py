import csv, glob, math, os, re


def parse(path):
    txt = open(path).read()
    m = re.search(r"^CPU 0 cumulative IPC: ([\d.]+) instructions: (\d+)", txt, re.M)
    if not m:
        return None
    r = {"ipc": float(m.group(1)), "instr": int(m.group(2))}
    for lvl, name in (("L1D", "cpu0_L1D"), ("L2C", "cpu0_L2C"), ("LLC", "LLC")):
        m = re.search(rf"^cpu0->{name} LOAD\s+ACCESS:\s+(\d+) HIT:\s+(\d+) MISS:\s+(\d+)", txt, re.M)
        r[lvl + "_load_miss"] = int(m.group(3))
        m = re.search(rf"^cpu0->{name} PREFETCH REQUESTED:\s+\d+ ISSUED:\s+(\d+) USEFUL:\s+(\d+) USELESS:\s+(\d+)", txt, re.M)
        r[lvl + "_pf_issued"], r[lvl + "_pf_useful"], r[lvl + "_pf_useless"] = (int(x) for x in m.groups())
    m = re.search(r"^PFSTUDY LLC_PF_FILLS: (\d+) USED_LLC: (\d+) USED_UPPER_ONLY: (\d+) UNUSED: (\d+) STILL_RESIDENT: (\d+) HARMFUL_EVICTIONS: (\d+)",
                  txt, re.M)
    r.update(zip(["pf_fills", "used_llc", "used_upper", "unused", "resident", "harmful"], map(int, m.groups())))
    return r


def ratio(a, b):
    return a / b if b else 0.0


runs = {}
for f in sorted(glob.glob("results/raw/final/*.txt")):
    cfg, trace = os.path.basename(f)[:-4].split("__", 1)
    r = parse(f)
    if r is None:
        print("unfinished:", f)
        continue
    runs.setdefault(trace, {})[cfg] = r

header = ["trace", "group", "ipc_pref", "ipc_nopref", "speedup", "llc_mpki_pref", "llc_mpki_nopref", "l1d_pf_accuracy", "l2_pf_accuracy",
          "llc_miss_coverage", "llc_pf_fills_pki", "frac_used_llc", "frac_used_upper_only", "frac_unused", "harmful_pki"]
rows = []
for trace, r in runs.items():
    if "srrip" not in r or "srrip_nopref" not in r:
        continue
    p, n = r["srrip"], r["srrip_nopref"]
    kilo = p["instr"] / 1000
    classified = p["used_llc"] + p["used_upper"] + p["unused"]
    rows.append([
        trace, "AI" if "llama" in trace else "control", p["ipc"], n["ipc"], round(p["ipc"] / n["ipc"], 3),
        round(p["LLC_load_miss"] / kilo, 2), round(n["LLC_load_miss"] / (n["instr"] / 1000), 2),
        round(ratio(p["L1D_pf_useful"], p["L1D_pf_useful"] + p["L1D_pf_useless"]), 3),
        round(ratio(p["L2C_pf_useful"], p["L2C_pf_useful"] + p["L2C_pf_useless"]), 3),
        round(ratio(n["LLC_load_miss"] - p["LLC_load_miss"], n["LLC_load_miss"]), 3),
        round(p["pf_fills"] / kilo, 2),
        round(ratio(p["used_llc"], classified), 3), round(ratio(p["used_upper"], classified), 3), round(ratio(p["unused"], classified), 3),
        round(p["harmful"] / kilo, 3),
    ])
rows.sort(key=lambda x: (x[1], -x[4]))

os.makedirs("results", exist_ok=True)
with open("results/final_checkpoint1.csv", "w", newline="") as fh:
    csv.writer(fh).writerows([header] + rows)
for row in [header] + rows:
    print(*row, sep="\t")

for group in ("AI", "control"):
    s = [row[4] for row in rows if row[1] == group]
    if s:
        print(f"\ngeomean speedup ({group}): {math.exp(sum(map(math.log, s)) / len(s)):.3f}")
