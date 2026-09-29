// SPDX-License-Identifier: MIT
#pragma once
#include "cache.h"
#include "modules.h"
#include "../../../include/cache.hpp"
struct lab_fifo : champsim::modules::replacement {
  archlab::Replacement state;
  explicit lab_fifo(CACHE* c) : replacement(c), state(static_cast<std::size_t>(c->NUM_SET), static_cast<std::size_t>(c->NUM_WAY), archlab::Policy::FIFO) {}
  long find_victim(uint32_t, uint64_t, long set, const champsim::cache_block*, champsim::address, champsim::address, access_type) { return static_cast<long>(state.victim(static_cast<std::size_t>(set))); }
  void replacement_cache_fill(uint32_t, long set, long way, champsim::address, champsim::address, champsim::address, access_type) {
    if(way >= 0 && way < intern_->NUM_WAY) state.fill(static_cast<std::size_t>(set), static_cast<std::size_t>(way));
  }
  void update_replacement_state(uint32_t, long set, long way, champsim::address, champsim::address, champsim::address, access_type type, uint8_t hit) {
    if(hit && type != access_type::WRITE && way >= 0 && way < intern_->NUM_WAY) state.touch(static_cast<std::size_t>(set), static_cast<std::size_t>(way));
  }
};
