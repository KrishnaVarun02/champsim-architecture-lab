// SPDX-License-Identifier: MIT
#pragma once
#include "modules.h"
#include "../../../include/ltage.hpp"
struct lab_ltage_long : champsim::modules::branch_predictor {
  archlab::LTage predictor{archlab::TageConfig::long_history()};
  using branch_predictor::branch_predictor;
  bool predict_branch(champsim::address ip) { return predictor.predict(ip.to<uint64_t>()); }
  void last_branch_result(champsim::address ip, champsim::address, bool taken, uint8_t) { predictor.update(ip.to<uint64_t>(), taken); }
};
