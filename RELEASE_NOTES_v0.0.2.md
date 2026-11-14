
# piStomp MIDI Latency Probe v0.0.2

## What's New

### MIDI-to-Audio Instrument Latency Measurement

The probe now supports a second measurement use case:
measuring the time between a MIDI Note On message and
the corresponding audio output from a MIDI instrument.

Connect the same MIDI source to both the instrument and
the Latency Probe. Connect the instrument's audio output
to the probe's audio input.

The updated Python decoder supports:

- MIDI-to-audio latency measurement.
- Automatic detection of instrument audio attacks.
- Per-note latency results in CSV format.
- Mean, median and percentile latency statistics.
- Configurable detection thresholds and search windows.
- Flagging of ambiguous or overlapping note events.

The existing audio-to-MIDI measurement functionality
remains unchanged.

## Compatibility

- Raspberry Pi 5 / piStomp ARM64
- Linux x86-64
- Windows x86-64 LV2 hosts

No changes to the LV2 DSP or PCM encoding format.

## IMPORTANT SAFETY WARNING

**NEVER CONNECT THE ENCODED MIDI PCM OUTPUT TO
SPEAKERS, HEADPHONES OR AMPLIFIERS.**

The right audio channel contains diagnostic PCM data,
not listening audio. Sharp pulses may produce loud clicks
and potentially damage equipment or hearing.

Connect this output only to a recorder with monitoring
disabled. Do not play back the encoded right channel.

## Licence

Copyright (C) 2026 Ken Spanks

GNU GPL v3 only (GPL-3.0-only).
