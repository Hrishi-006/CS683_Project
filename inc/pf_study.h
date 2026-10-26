#ifndef PF_STUDY_H
#define PF_STUDY_H

#include <cstdint>

// CS683: observation-only bookkeeping for the prefetch-aware LLC study.
// Tracks the fate of prefetched lines in the LLC and counts harmful evictions.
// Nothing here feeds back into the simulation. Single-core only.
namespace pf_study
{
void llc_fill(long set, long ways, uint64_t block, bool is_prefetch, uint64_t pf_ip, bool victim_valid, uint64_t victim_block);
void llc_demand_hit(uint64_t block);
void llc_demand_miss(long set, uint64_t block);
void upper_demand_hit(uint64_t block);
void reset_stats();
void print_stats();
} // namespace pf_study

#endif