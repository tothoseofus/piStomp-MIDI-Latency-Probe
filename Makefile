CC = aarch64-linux-gnu-gcc
CFLAGS = -O2 -std=c11 -fPIC -Wall -Wextra -Wpedantic
LDFLAGS = -shared
BUNDLE = build/pistomp-midi-latency-probe.lv2

.PHONY: all clean package
all: $(BUNDLE)/latency_probe.so $(BUNDLE)/manifest.ttl $(BUNDLE)/latency_probe.ttl

$(BUNDLE):
	mkdir -p $@

$(BUNDLE)/latency_probe.so: src/latency_probe.c | $(BUNDLE)
	$(CC) $(CFLAGS) $(LDFLAGS) -o $@ $<

$(BUNDLE)/manifest.ttl: lv2/manifest.ttl | $(BUNDLE)
	cp $< $@

$(BUNDLE)/latency_probe.ttl: lv2/latency_probe.ttl | $(BUNDLE)
	cp $< $@

package: all
	cd build && zip -qr ../pistomp-midi-latency-probe-aarch64.zip pistomp-midi-latency-probe.lv2

clean:
	rm -rf build pistomp-midi-latency-probe-aarch64.zip
