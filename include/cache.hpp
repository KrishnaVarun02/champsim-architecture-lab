// SPDX-License-Identifier: MIT
#pragma once
#include <cstdint>
#include <limits>
#include <stdexcept>
#include <vector>

namespace archlab {
enum class Policy { LRU, LFU, FIFO };
class Replacement {
  struct State { uint64_t inserted = 0, touched = 0, frequency = 0; bool valid = false; };
  std::size_t sets_, ways_;
  Policy policy_;
  uint64_t tick_ = 0;
  std::vector<State> state_;
  State& get(std::size_t s, std::size_t w) { if(s >= sets_ || w >= ways_) throw std::out_of_range("cache set/way"); return state_[s * ways_ + w]; }
 public:
  Replacement(std::size_t sets, std::size_t ways, Policy policy) : sets_(sets), ways_(ways), policy_(policy), state_(sets * ways) { if(!sets || !ways) throw std::invalid_argument("cache geometry must be positive"); }
  void fill(std::size_t set, std::size_t way) { auto& s = get(set, way); s = State{++tick_, tick_, 1, true}; }
  void touch(std::size_t set, std::size_t way) { auto& s = get(set, way); s.touched = ++tick_; if(s.frequency < std::numeric_limits<uint64_t>::max()) ++s.frequency; }
  std::size_t victim(std::size_t set) {
    std::size_t v = 0;
    for(std::size_t w = 0; w < ways_; ++w) {
      const auto& s = get(set,w); const auto& best = get(set,v);
      if(!s.valid) return w;
      const bool better = policy_ == Policy::LRU ? s.touched < best.touched : policy_ == Policy::FIFO ? s.inserted < best.inserted : (s.frequency < best.frequency || (s.frequency == best.frequency && s.touched < best.touched));
      if(better) v = w;
    }
    return v;
  }
};

class Cache {
  struct Line { uint64_t tag = 0; bool valid = false; };
  std::size_t sets_, ways_, line_size_;
  std::vector<Line> lines_;
  Replacement replacement_;
 public:
  uint64_t hits = 0, misses = 0;
  Cache(std::size_t sets, std::size_t ways, std::size_t line_size, Policy policy) : sets_(sets), ways_(ways), line_size_(line_size), lines_(sets * ways), replacement_(sets,ways,policy) { if(!line_size) throw std::invalid_argument("line size must be positive"); }
  bool access(uint64_t address) {
    const auto block = address / line_size_; const auto set = block % sets_; const auto tag = block / sets_;
    for(std::size_t w = 0; w < ways_; ++w) { auto& l = lines_[set * ways_ + w]; if(l.valid && l.tag == tag) { ++hits; replacement_.touch(set,w); return true; } }
    ++misses; const auto w = replacement_.victim(set); lines_[set * ways_ + w] = Line{tag,true}; replacement_.fill(set,w); return false;
  }
};
}
