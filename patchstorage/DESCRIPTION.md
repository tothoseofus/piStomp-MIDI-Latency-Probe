# piStomp MIDI Latency Probe (v0.0.1)

**⚠️ DANGER — DO NOT CONNECT THE ENCODED MIDI PCM OUTPUT TO SPEAKERS, HEADPHONES OR AMPLIFIERS.**

The right channel is **diagnostic PCM DATA, not audio for listening**. Its sharp pulses can cause loud clicks and may damage equipment or hearing. **Route the right output to a recorder only, with monitoring disabled. Do not audition recorded or reconstructed PCM data.**

A lightweight LV2 diagnostic for **audio-to-MIDI and MIDI-to-audio response latency**. The mono audio input passes to the left output, while incoming MIDI is timestamped and encoded into the right diagnostic PCM channel. For guitar-to-MIDI tests, feed dry guitar plus detected MIDI. For MIDI instrument response tests, split incoming MIDI to the instrument and the probe; feed the instrument audio to the probe audio input. The included decoder recovers precise MIDI timestamps, and its optional `--mode instrument` estimates Note On-to-audio attack latency for isolated notes. Ambiguous overlapping notes and already-sounding audio are flagged rather than assigned misleading timings.

Designed and tested for Raspberry Pi 5 / piStomp, with Linux x86-64 and Windows x86-64 build targets. **Windows MOD Desktop runtime compatibility is not yet verified.**

Author: **Ken Spanks**. Licence: **GPL-3.0-only**. Source: https://github.com/tothoseofus/piStomp-MIDI-Latency-Probe

Installation: extract the platform ZIP to obtain `pistomp-midi-latency-probe.lv2`, install it in your LV2 plug-in directory, and refresh/restart the host. Do not feed the right audio output into live monitoring or a playback chain.
