# Release v0.0.1 — Latency Monitor

First public release of **piStomp MIDI Latency Probe**, a lightweight LV2 diagnostic plugin for measuring guitar-to-MIDI timing without introducing a synthesiser into the measurement path.

## ⚠️ IMPORTANT SAFETY WARNING

**NEVER CONNECT THE `Encoded MIDI Right` OUTPUT TO SPEAKERS, HEADPHONES, AN AMPLIFIER OR ANY AUDIO MONITORING PATH.** This is **diagnostic PCM data**, not listening audio. The signal contains sharp marker pulses which can create loud clicks and may damage equipment or hearing. **Record it only with monitoring muted. Do not play back the right channel of captured or reconstructed files.**

## Features

- Copies the mono guitar input directly to the left audio output without intentional delay.
- Encodes incoming timestamped MIDI channel messages as recoverable PCM data on the right audio output.
- Bundled Python decoder reconstructs a MIDI event CSV and a waveform with MIDI-event impulses for offline timing analysis.
- Preserves original LV2 MIDI sample timestamps, including notes that arrive simultaneously.
- Minimal MOD GUI with draggable audio/MIDI ports and an explicit warning about the right output.
- MOD GUI screenshot and thumbnail are bundled for MOD/MODEP compatibility.
- GitHub Actions configurations for Raspberry Pi 5 / piStomp ARM64, Linux x86-64 and Windows x86-64 (MinGW-w64); desktop host compatibility still requires local validation.
- Licensed under **GNU GPL version 3 only (GPL-3.0-only)**.

## Usage

Connect the source guitar audio to both GuitarMidi-LV2 and the probe's **Dry Guitar In**. Connect GuitarMidi-LV2's MIDI output to the probe's **MIDI In**. Capture the probe's **Dry Audio Left** and **Encoded MIDI Right** outputs as stereo WAV, with all monitoring of the right/data channel disabled and with no effects, mixing, gain changes, or sample-rate conversion on that channel. Then run `tools/decode.py` to extract MIDI timestamps and create the visual analysis track.

## Limitations

- Encodes MIDI channel voice messages; SysEx and system real-time messages are not supported.
- Uses a fixed FIFO; prolonged event bursts may overflow it.
- Captures the timestamps presented to the probe, not the neural-network inference duration or the true physical instant of a guitar pluck.
- The encoded audio must be recorded without signal processing or lossy compression.

**Release tag:** `v0.0.1`  
**Release name:** `Latency Monitor`

## Ownership and plugin URI

Copyright © 2026 Ken Spanks. GPL-3.0-only.

Plugin URI and homepage: https://github.com/tothoseofus/piStomp-MIDI-Latency-Probe

**Breaking LV2 identity change:** Pre-release `example.org` pedalboard entries need to be replaced with the new plugin URI.
