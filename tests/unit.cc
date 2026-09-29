#include "cache.hpp"
#include "ltage.hpp"
#include <cassert>
#include <iostream>
int main() {
  using namespace archlab;
  for (auto p : {Policy::LRU,Policy::LFU,Policy::FIFO}) {
    Cache c(1,2,64,p); assert(!c.access(0)); assert(c.access(63)); assert(!c.access(64)); assert(c.hits == 1 && c.misses == 2);
  }
  Replacement lru(1,2,Policy::LRU), fifo(1,2,Policy::FIFO), lfu(1,2,Policy::LFU);
  for (auto* r : {&lru,&fifo,&lfu}) { assert(r->victim(0)==0); r->fill(0,0); assert(r->victim(0)==1); r->fill(0,1); r->touch(0,0); }
  assert(lru.victim(0)==1); assert(fifo.victim(0)==0); assert(lfu.victim(0)==1);
  lfu.fill(0,1); assert(lfu.victim(0)==1); // evicted line's frequency resets
  Replacement tie(1,2,Policy::LFU); tie.fill(0,0); tie.fill(0,1); assert(tie.victim(0)==0);
  Cache isolated(2,1,64,Policy::LRU); isolated.access(0); isolated.access(64); isolated.access(128); assert(isolated.access(64));
  bool threw = false; try { Cache bad(0,2,64,Policy::LRU); } catch(const std::invalid_argument&) { threw=true; } assert(threw);
  LTage p; unsigned errors=0;
  for(unsigned i=0;i<5000;++i) { bool y=i%11!=10; if(i>1000) errors += p.predict(0x1234)!=y; p.update(0x1234,y); }
  assert(errors < 25); assert(p.updates()==5000);
  LTage a,b; unsigned alternation_errors=0;
  for(unsigned i=0;i<10000;++i) { const bool y = i%2; assert(a.predict(0x2000)==b.predict(0x2000)); if(i>2000) alternation_errors += a.predict(0x2000)!=y; a.update(0x2000,y); b.update(0x2000,y); }
  assert(alternation_errors < 20);
  LTage longp(TageConfig::long_history()); for(unsigned i=0;i<100;++i) longp.update(i*4,i%3);
  TageConfig bad; bad.entries=511; threw=false; try { LTage x(bad); } catch(const std::invalid_argument&) { threw=true; } assert(threw);
  std::cout << "unit: cache ordering, isolation, invalid geometry, predictor learning and determinism passed\n";
}
