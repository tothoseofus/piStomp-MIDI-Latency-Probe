# piStomp MIDI Latency Probe (v0.0.1)

**⚠️ DANGER — DO NOT CONNECT THE ENCODED MIDI PCM OUTPUT TO SPEAKERS, HEADPHONES OR AMPLIFIERS.**

The right channel is **diagnostic PCM DATA, not audio for listening**. Its sharp pulses can cause loud clicks and may damage equipment or hearing. **Route the right output to a recorder only, with monitoring disabled. Do not audition recorded or reconstructed PCM data.**

A lightweight LV2 diagnostic for measuring audio-to-MIDI arrival timing without a synthesiser. Dry input passes to the left audio output, MIDI messages are encoded into the right diagnostic PCM channel. Use the included Python decoder to recover sample timestamps and export CSV/impulse markers.

Designed and tested for Raspberry Pi 5 / piStomp, with Linux x86-64 and Windows x86-64 build targets. **Windows MOD Desktop runtime compatibility is not yet verified.**

Author: **Ken Spanks**. Licence: **GPL-3.0-only**. Source: https://github.com/tothoseofus/piStomp-MIDI-Latency-Probe

Installation: extract the platform ZIP to obtain `pistomp-midi-latency-probe.lv2`, install it in your LV2 plug-in directory, and refresh/restart the host. Do not feed the right audio output into live monitoring or a playback chain.
