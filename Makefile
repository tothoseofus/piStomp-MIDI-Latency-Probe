# Reusable LV2 build: override CC, BINARY and BUILD_DIR for target platform.
CC = gcc
CPPFLAGS ?=
CFLAGS = -O2 -std=c11 -fPIC -Wall -Wextra -Wpedantic
LDFLAGS = -shared
BINARY = latency_probe.so
BUILD_DIR = build
BUNDLE = $(BUILD_DIR)/pistomp-midi-latency-probe.lv2
VERSION := $(strip $(shell cat VERSION))
VERSION_MINOR := $(word 2,$(subst ., ,$(VERSION)))
VERSION_MICRO := $(word 3,$(subst ., ,$(VERSION)))
MODGUI_FILES = $(wildcard lv2/modgui/*)

.PHONY: all clean package
all: $(BUNDLE)/$(BINARY) $(BUNDLE)/manifest.ttl $(BUNDLE)/latency_probe.ttl $(BUNDLE)/modgui.ttl $(addprefix $(BUNDLE)/modgui/,$(notdir $(MODGUI_FILES))) $(BUNDLE)/LICENSE

$(BUNDLE):
	mkdir -p $@

$(BUNDLE)/$(BINARY): src/latency_probe.c | $(BUNDLE)
	$(CC) $(CPPFLAGS) $(CFLAGS) $(LDFLAGS) -o $@ $<

$(BUNDLE)/manifest.ttl: lv2/manifest.ttl | $(BUNDLE)
	sed 's/latency_probe\.so/$(BINARY)/' $< > $@

$(BUNDLE)/latency_probe.ttl: lv2/latency_probe.ttl VERSION | $(BUNDLE)
	sed -e "s/@LV2_MINOR@/$(VERSION_MINOR)/g" -e "s/@LV2_MICRO@/$(VERSION_MICRO)/g" $< > $@

$(BUNDLE)/modgui.ttl: lv2/modgui.ttl | $(BUNDLE)
	cp $< $@

$(BUNDLE)/modgui/%: lv2/modgui/% | $(BUNDLE)
	mkdir -p $(BUNDLE)/modgui
	cp $< $@

$(BUNDLE)/LICENSE: LICENSE | $(BUNDLE)
	cp $< $@

# Optional for manual local packaging. GitHub Actions uploads the bundle
# directory directly, avoiding the ZIP-inside-ZIP issue.
package: all
	cd $(BUILD_DIR) && zip -qr ../pistomp-midi-latency-probe.zip pistomp-midi-latency-probe.lv2

clean:
	rm -rf $(BUILD_DIR) pistomp-midi-latency-probe.zip
