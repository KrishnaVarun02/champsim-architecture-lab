#include "cache.hpp"
#include "ltage.hpp"
#include <fstream>
#include <iomanip>
#include <iostream>
#include <sstream>
#include <string>
int main(int argc,char** argv) {
  try {
    if(argc!=2) throw std::runtime_error("usage: bench TRACE.txt (B hex_pc 0|1 or M hex_address)");
    std::ifstream input(argv[1]); if(!input) throw std::runtime_error("cannot open trace");
    archlab::LTage tage, longtage(archlab::TageConfig::long_history()); archlab::Bimodal base;
    archlab::Cache lru(64,8,64,archlab::Policy::LRU), lfu(64,8,64,archlab::Policy::LFU), fifo(64,8,64,archlab::Policy::FIFO);
    uint64_t branches=0, tage_miss=0, long_miss=0, base_miss=0; std::string line; unsigned lineno=0;
    while(std::getline(input,line)) {
      ++lineno; if(line.empty() || line[0]=='#') continue;
      std::istringstream row(line); char kind; uint64_t address; int taken; std::string extra;
      if(!(row>>kind>>std::hex>>address)) throw std::runtime_error("invalid trace at line " + std::to_string(lineno));
      if(kind=='B') {
        if(!(row>>std::dec>>taken) || (taken!=0 && taken!=1)) throw std::runtime_error("branch outcome must be 0 or 1");
        ++branches; tage_miss += tage.predict(address)!=bool(taken); long_miss += longtage.predict(address)!=bool(taken); base_miss += base.predict(address)!=bool(taken);
        tage.update(address,taken); longtage.update(address,taken); base.update(address,taken);
      } else if(kind=='M') { lru.access(address); lfu.access(address); fifo.access(address); }
      else throw std::runtime_error("unknown trace record");
      if(row>>extra) throw std::runtime_error("extra trace fields");
    }
    std::cout<<"{\"branches\":"<<branches<<",\"bimodal_misses\":"<<base_miss<<",\"ltage_misses\":"<<tage_miss<<",\"ltage_long_misses\":"<<long_miss<<",\"memory_accesses\":"<<lru.hits+lru.misses<<",\"lru_misses\":"<<lru.misses<<",\"lfu_misses\":"<<lfu.misses<<",\"fifo_misses\":"<<fifo.misses<<"}\n";
  } catch(const std::exception& e) { std::cerr<<e.what()<<'\n'; return 1; }
}
