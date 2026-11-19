#include "pacman.h"

#include <algorithm>
#include <cassert>
#include <unordered_map>

#include "cache.h"

pacman::pacman(CACHE* cache) : pacman(cache, cache->NUM_SET, cache->NUM_WAY) {}

pacman::pacman(CACHE* cache, long sets_, long ways_) : replacement(cache)
{
  std::generate_n(std::back_inserter(sets), sets_, [ways = ways_] { return pacman_set_helper{ways}; });
}

// find replacement victim
long pacman::find_victim(uint32_t triggering_cpu, uint64_t instr_id, long set, const champsim::cache_block* current_set, champsim::address ip,
                         champsim::address full_addr, access_type type)
{
  return sets.at(static_cast<std::size_t>(set)).victim();
}

// called on every tag check; only hits change state (way is not valid on a miss)
void pacman::update_replacement_state(uint32_t triggering_cpu, long set, long way, champsim::address full_addr, champsim::address ip,
                                      champsim::address victim_addr, access_type type, uint8_t hit)
{
  if (hit)
    sets.at(static_cast<std::size_t>(set)).update(way, true, type);
}

// called on every fill: this is where prefetches get their low insertion priority
void pacman::replacement_cache_fill(uint32_t triggering_cpu, long set, long way, champsim::address full_addr, champsim::address ip,
                                    champsim::address victim_addr, access_type type)
{
  sets.at(static_cast<std::size_t>(set)).update(way, false, type);
}

pacman_set_helper::pacman_set_helper(long ways) : rrpv_values(static_cast<std::size_t>(ways), maxRRPV) {}

auto pacman_set_helper::get_rrpv(long way) -> rrpv_type& { return rrpv_values.at(static_cast<std::size_t>(way)); }

long pacman_set_helper::victim()
{
  // Find the maximum RRPV
  auto victim = std::max_element(std::begin(rrpv_values), std::end(rrpv_values));

  // If the maximum element has RRPV less than the maximum, increment everything to the maximum
  std::transform(std::cbegin(rrpv_values), std::cend(rrpv_values), std::begin(rrpv_values), [diff = maxRRPV - *victim](auto x) { return x + diff; });

  // Return the way index
  return std::distance(std::begin(rrpv_values), victim);
}
void pacman_set_helper::update(long way, bool hit, access_type type)
{
  if (hit)
    get_rrpv(way) = 0;
  else if (type == access_type::PREFETCH)
    get_rrpv(way) = maxRRPV; // prefetch fill -> lowest priority
  else
    get_rrpv(way) = maxRRPV - 1; // demand fill, same as SRRIP
}