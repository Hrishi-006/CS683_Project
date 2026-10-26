#include "pf_study.h"

#include <algorithm>
#include <deque>
#include <unordered_map>
#include <vector>
#include <fmt/core.h>

namespace
{
struct tracked_line {
  uint64_t pf_ip = 0;
  uint64_t epoch = 0;
  bool used_upper = false; // demand hit in L1D/L2C while the LLC copy existed
  bool used_llc = false;   // demand hit on the LLC copy itself
};

struct shadow_entry {
  uint64_t block = 0;
  bool by_prefetch = false;
  uint64_t pf_ip = 0;
};

struct counters {
  uint64_t fills = 0, used_llc = 0, used_upper_only = 0, unused = 0, harmful = 0;
};

uint64_t epoch = 0;
counters total;
std::unordered_map<uint64_t, counters> by_pc;
std::unordered_map<uint64_t, tracked_line> tracked;        // prefetched lines currently in the LLC
std::unordered_map<long, std::deque<shadow_entry>> shadow; // recent LLC victims per set, depth = ways

void classify(const tracked_line& t)
{
  if (t.epoch != epoch)
    return; // filled during warmup
  auto& pc = by_pc[t.pf_ip];
  if (t.used_llc) {
    ++total.used_llc;
    ++pc.used_llc;
  } else if (t.used_upper) {
    ++total.used_upper_only;
    ++pc.used_upper_only;
  } else {
    ++total.unused;
    ++pc.unused;
  }
}
} // namespace

void pf_study::llc_fill(long set, long ways, uint64_t block, bool is_prefetch, uint64_t pf_ip, bool victim_valid, uint64_t victim_block)
{
  auto& sh = shadow[set];
  // the incoming block is back in the cache, so it is no longer a pending victim
  sh.erase(std::remove_if(std::begin(sh), std::end(sh), [block](const auto& e) { return e.block == block; }), std::end(sh));

  if (victim_valid) {
    if (auto it = tracked.find(victim_block); it != std::end(tracked)) {
      classify(it->second);
      tracked.erase(it);
    }
    sh.push_front({victim_block, is_prefetch, pf_ip});
    if (std::size(sh) > static_cast<std::size_t>(ways))
      sh.pop_back();
  }

  if (is_prefetch) {
    ++total.fills;
    ++by_pc[pf_ip].fills;
    tracked[block] = tracked_line{pf_ip, epoch};
  }
}

void pf_study::llc_demand_hit(uint64_t block)
{
  if (auto it = tracked.find(block); it != std::end(tracked))
    it->second.used_llc = true;
}

void pf_study::upper_demand_hit(uint64_t block)
{
  if (auto it = tracked.find(block); it != std::end(tracked))
    it->second.used_upper = true;
}

void pf_study::llc_demand_miss(long set, uint64_t block)
{
  auto& sh = shadow[set];
  auto it = std::find_if(std::begin(sh), std::end(sh), [block](const auto& e) { return e.block == block; });
  if (it == std::end(sh))
    return;
  if (it->by_prefetch) {
    ++total.harmful;
    ++by_pc[it->pf_ip].harmful;
  }
  sh.erase(it);
}

void pf_study::reset_stats()
{
  ++epoch;
  total = {};
  by_pc.clear();
}

void pf_study::print_stats()
{
  auto resident = std::count_if(std::begin(tracked), std::end(tracked), [](const auto& kv) { return kv.second.epoch == epoch; });
  fmt::print("PFSTUDY LLC_PF_FILLS: {} USED_LLC: {} USED_UPPER_ONLY: {} UNUSED: {} STILL_RESIDENT: {} HARMFUL_EVICTIONS: {}\n", total.fills, total.used_llc,
             total.used_upper_only, total.unused, resident, total.harmful);

  std::vector<std::pair<uint64_t, counters>> pcs(std::begin(by_pc), std::end(by_pc));
  std::sort(std::begin(pcs), std::end(pcs), [](const auto& a, const auto& b) { return a.second.fills > b.second.fills; });
  pcs.resize(std::min<std::size_t>(std::size(pcs), 20));
  for (const auto& [pc, c] : pcs)
    fmt::print("PFSTUDY PC {:#x} FILLS: {} USED_LLC: {} USED_UPPER_ONLY: {} UNUSED: {} HARMFUL: {}\n", pc, c.fills, c.used_llc, c.used_upper_only, c.unused,
               c.harmful);
}