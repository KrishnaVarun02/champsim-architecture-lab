// SPDX-License-Identifier: MIT
#pragma once
#include <algorithm>
#include <array>
#include <cstdint>
#include <stdexcept>
#include <vector>

namespace archlab {
struct TageConfig {
  std::vector<unsigned> histories{4, 8, 13, 22, 38, 64, 110, 192};
  unsigned entries = 512;
  unsigned base_entries = 4096;
  unsigned tag_bits = 12;
  bool loop = true;
  static TageConfig long_history() {
    TageConfig c;
    c.histories = {4, 9, 20, 44, 96, 210, 460, 1000};
    return c;
  }
};

// Educational L-TAGE-style predictor: tagged geometric history + loop side predictor.
// Prediction is pure. Update recomputes provider with the SAME history; callers must
// resolve a branch before predicting the next one (the pinned ChampSim does this).
class LTage {
  struct Entry { uint16_t tag = 0; int8_t counter = -1; uint8_t useful = 0; bool valid = false; };
  struct Loop { uint64_t pc = 0; uint32_t count = 0, trip = 0; uint8_t confidence = 0, age = 0; bool valid = false, direction = true; };
  struct Lookup { int provider = -1, alternate = -1; bool provider_pred = false, alt_pred = false, tage_pred = false, final_pred = false; int loop = -1; bool loop_valid = false; };
  TageConfig cfg_;
  std::vector<int8_t> base_;
  std::vector<std::vector<Entry>> banks_;
  std::array<uint8_t, 2048> history_{};
  std::array<Loop, 64> loops_{};
  unsigned head_ = 0;
  uint32_t path_ = 0, random_ = 0x9e3779b9U;
  uint64_t updates_ = 0;
  int8_t use_alt_ = 0;
  template<typename T> static void sat(T& x, bool up, int lo, int hi) { x = static_cast<T>(std::max(lo, std::min(hi, static_cast<int>(x) + (up ? 1 : -1)))); }
  uint32_t random() { random_ ^= random_ << 13; random_ ^= random_ >> 17; random_ ^= random_ << 5; return random_; }
  unsigned fold(unsigned length, unsigned bits) const {
    unsigned h = 0;
    for (unsigned i = 0; i < length; ++i) h ^= unsigned(history_[(head_ + i) % history_.size()]) << (i % bits);
    return h;
  }
  unsigned index(uint64_t pc, unsigned b) const { return static_cast<unsigned>((pc >> 2) ^ (pc >> 11) ^ fold(cfg_.histories[b], 16) ^ (path_ << (b % 4))) & (cfg_.entries - 1); }
  uint16_t tag(uint64_t pc, unsigned b) const { return static_cast<uint16_t>((pc ^ (pc >> 17) ^ fold(cfg_.histories[b], cfg_.tag_bits) ^ (fold(cfg_.histories[b], cfg_.tag_bits - 1) << 1)) & ((1U << cfg_.tag_bits) - 1)); }
  unsigned base_index(uint64_t pc) const { return static_cast<unsigned>(pc >> 2) & (cfg_.base_entries - 1); }
  unsigned loop_set(uint64_t pc) const { return static_cast<unsigned>((pc >> 2) ^ (pc >> 8)) % 16 * 4; }
  Lookup lookup(uint64_t pc) const {
    Lookup l;
    l.alt_pred = base_[base_index(pc)] >= 0;
    for (int b = static_cast<int>(banks_.size()) - 1; b >= 0; --b) {
      const auto& e = banks_[b][index(pc, b)];
      if (e.valid && e.tag == tag(pc, b)) {
        if (l.provider < 0) { l.provider = b; l.provider_pred = e.counter >= 0; }
        else { l.alternate = b; l.alt_pred = e.counter >= 0; break; }
      }
    }
    l.tage_pred = l.alt_pred;
    if (l.provider >= 0) {
      const auto& e = banks_[l.provider][index(pc, l.provider)];
      const bool weak = e.counter == -1 || e.counter == 0;
      l.tage_pred = (weak && use_alt_ >= 0) ? l.alt_pred : l.provider_pred;
    }
    l.final_pred = l.tage_pred;
    if (cfg_.loop) {
      for (unsigned i = loop_set(pc); i < loop_set(pc) + 4; ++i) {
        const auto& e = loops_[i];
        if (e.valid && e.pc == pc) {
          l.loop = static_cast<int>(i);
          l.loop_valid = e.confidence >= 3 && e.trip > 0 && e.count <= e.trip;
          if (l.loop_valid) l.final_pred = e.count == e.trip ? !e.direction : e.direction;
          break;
        }
      }
    }
    return l;
  }
  void update_loop(uint64_t pc, bool taken, const Lookup& l) {
    if (!cfg_.loop) return;
    if (l.loop < 0) {
      const auto start = loop_set(pc);
      unsigned victim = start;
      for (unsigned i = start; i < start + 4; ++i) {
        if (!loops_[i].valid) { victim = i; break; }
        if (loops_[i].age < loops_[victim].age) victim = i;
      }
      if (loops_[victim].valid && loops_[victim].age > 0) {
        for (unsigned i = start; i < start + 4; ++i) --loops_[i].age;
      } else loops_[victim] = Loop{pc, 1, 0, 0, 1, true, taken};
      return;
    }
    auto& e = loops_[l.loop];
    if (l.loop_valid) {
      if (l.final_pred != taken) e.confidence = 0;
      else sat(e.age, true, 0, 7);
    }
    if (taken == e.direction) {
      if (++e.count > 1000000) { e.count = 0; e.trip = 0; e.confidence = 0; }
    } else {
      if (e.count == e.trip && e.trip > 0) sat(e.confidence, true, 0, 7);
      else { e.trip = e.count; e.confidence = 0; }
      e.count = 0;
    }
  }
 public:
  explicit LTage(TageConfig cfg = {}) : cfg_(std::move(cfg)), base_(cfg_.base_entries, -1), banks_(cfg_.histories.size(), std::vector<Entry>(cfg_.entries)) {
    auto pow2 = [](unsigned n) { return n && !(n & (n - 1)); };
    if (!pow2(cfg_.entries) || !pow2(cfg_.base_entries) || cfg_.tag_bits < 2 || cfg_.tag_bits > 16 || cfg_.histories.empty()) throw std::invalid_argument("invalid TAGE geometry");
    unsigned prev = 0;
    for (auto n : cfg_.histories) { if (n <= prev || n > history_.size()) throw std::invalid_argument("history lengths must increase and fit history buffer"); prev = n; }
  }
  bool predict(uint64_t pc) const { return lookup(pc).final_pred; }
  void update(uint64_t pc, bool taken) {
    const auto l = lookup(pc);
    update_loop(pc, taken, l);
    sat(base_[base_index(pc)], taken, -2, 1);
    if (l.provider >= 0) {
      auto& e = banks_[l.provider][index(pc, l.provider)];
      const bool weak = e.counter == -1 || e.counter == 0;
      if (weak && l.provider_pred != l.alt_pred) sat(use_alt_, l.alt_pred == taken, -8, 7);
      if (l.provider_pred != l.alt_pred) sat(e.useful, l.provider_pred == taken, 0, 3);
      sat(e.counter, taken, -4, 3);
      if (e.useful == 0 && l.alternate >= 0) sat(banks_[l.alternate][index(pc, l.alternate)].counter, taken, -4, 3);
    }
    if (l.tage_pred != taken) {
      unsigned allocated = 0;
      for (int b = l.provider + 1; b < static_cast<int>(banks_.size()); ++b) {
        auto& e = banks_[b][index(pc, b)];
        if (e.useful == 0 && (allocated == 0 || (random() & 1U))) {
          e = Entry{tag(pc, b), static_cast<int8_t>(taken ? 0 : -1), 0, true};
          if (++allocated == 2) break;
        }
      }
      if (!allocated) for (int b = l.provider + 1; b < static_cast<int>(banks_.size()); ++b) { auto& e = banks_[b][index(pc, b)]; if (e.useful) --e.useful; }
    }
    if (++updates_ % 262144 == 0) for (auto& b : banks_) for (auto& e : b) e.useful >>= 1;
    head_ = (head_ + static_cast<unsigned>(history_.size()) - 1) % static_cast<unsigned>(history_.size());
    history_[head_] = taken;
    path_ = (path_ << 1) ^ static_cast<uint32_t>(pc >> 2);
  }
  uint64_t updates() const { return updates_; }
};

class Bimodal {
  std::array<int8_t,16384> counters_{};
 public:
  bool predict(uint64_t pc) const { return counters_[pc % 16381] >= 2; }
  void update(uint64_t pc, bool taken) { auto& c = counters_[pc % 16381]; c = static_cast<int8_t>(std::max(0, std::min(3, int(c) + (taken ? 1 : -1)))); }
};
}
