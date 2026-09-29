CXX ?= c++
CXXFLAGS ?= -O2 -std=c++17 -Wall -Wextra -Wpedantic
CPPFLAGS += -Iinclude
.PHONY: all test synthetic clean sanitize
all: build/bench build/unit
build:
	mkdir -p build
build/bench: src/bench.cc include/ltage.hpp include/cache.hpp | build
	$(CXX) $(CPPFLAGS) $(CXXFLAGS) $< -o $@
build/unit: tests/unit.cc include/ltage.hpp include/cache.hpp | build
	$(CXX) $(CPPFLAGS) $(CXXFLAGS) $< -o $@
test: all
	./build/unit
	python3 -m unittest discover -s tests -p 'test_*.py' -v
synthetic: all
	python3 scripts/synthetic.py --out build/synthetic
	python3 scripts/run_synthetic.py --traces build/synthetic --output results/synthetic.csv
sanitize:
	$(MAKE) clean
	$(MAKE) CXXFLAGS='-O1 -g -std=c++17 -Wall -Wextra -fsanitize=address,undefined -fno-omit-frame-pointer' test
clean:
	rm -rf build
