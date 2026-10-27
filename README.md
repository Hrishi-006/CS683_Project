# Prefetch-Aware LLC Insertion Under Aggressive Prefetching

CS683 course project, IIT Bombay. Hrishikesh Bingewar (24b3983@iitb.ac.in).
Built on [DPC4 ChampSim](https://github.com/CMU-SAFARI/ChampSim); the original README is in [README_ChampSim.md](README_ChampSim.md).

## Problem statement

Prefetched lines that are never used still occupy last-level cache (LLC) space and can evict lines that the program reuses. Prefetch-aware insertion policies (PACMan, SHiP++) fix this by inserting prefetches at low priority, but they were designed with older prefetchers on SPEC benchmarks. The Fourth Data Prefetching Championship (DPC4) uses aggressive prefetchers (Berti at L1D, Pythia at L2) that may consume most useful prefetches before the LLC.

**Question:** do prefetch-aware LLC insertion policies still pay off under the DPC4 prefetchers, on Llama2 AI traces and non-AI control traces?

## Checkpoint 1 findings

Setup: single-core DPC4 ChampSim with SRRIP at the LLC, 4 Llama2 and 4 control traces (mcf, omnetpp, sssp, pr-3), 50M warmup + 200M simulated instructions, with and without prefetching.

- **The LLC copy of a prefetch almost never serves a demand:** at most 0.2% of LLC prefetch fills, on every trace. Useful prefetches are consumed in L1D or L2.
- **Llama2:** prefetching gives a 1.93× geometric-mean speedup, with almost no LLC pollution (at most 0.3% of fills unused, near-zero harmful evictions).
- **Controls:** 1.23× geometric-mean speedup, but 42% to 81% of fills are never used. On pr-3, prefetching causes 18.3 harmful evictions per kilo-instruction and slows the program down to 0.87×.
- **Hypothesis for Checkpoint 2:** low-priority prefetch insertion should cost almost nothing on Llama2 and help polluting traces such as pr-3.

Results are in [results/final_checkpoint1.csv](results/final_checkpoint1.csv) and [results/plots/](results/plots/); the run and plot scripts are in [scripts/](scripts/).
