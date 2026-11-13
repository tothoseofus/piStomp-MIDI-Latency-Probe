# piStomp MIDI Latency Probe — prototype v0.1.0

Lightweight LV2 plugin for GuitarMidi-LV2 benchmarking on piStomp v3 (Pi 5).

## Purpose

* `Dry Guitar In` (mono audio) is copied **without any intentional delay** to `Dry Audio Left`.
* `MIDI In` accepts LV2 MIDI channel messages and encodes their status/data/timestamp as sample-accurate PCM packets in `Encoded MIDI Right`.
* No synthesiser, internal file writing, external model, persistent worker, or blocking operation in the audio callback.

## Build

On GitHub, upload files preserving folder layout and enable Actions. The workflow builds using `aarch64-linux-gnu-gcc` and uploads `pistomp-midi-latency-probe-aarch64.zip`.

If building locally on Linux with LV2 headers and a compiler: `make CC=gcc package` (for native x86-64, rename the zip accordingly).

## Install on piStomp

Unzip artifact. Install the `pistomp-midi-latency-probe.lv2` directory under your piStomp LV2 bundle directory (e.g. `/home/patch/.lv2` or your existing custom-plugin location). Refresh/restart the plugin host as needed.

## MODEP wiring

```
               +--------------------------> Probe: Dry Guitar In
Guitar Input --+---> GuitarMidi: Audio In
                           GuitarMidi: MIDI Out ---> Probe: MIDI In

Probe: Dry Audio Left ------> Output 1 (left)
Probe: Encoded MIDI Right --> Output 2 (right)
```

Record the two outputs as stereo **with no effects, gain adjustments, pan mixing or resampling on the right channel**. Use piStomp's existing recorder or an external stereo capture. **Do not listen to the right channel**: it contains encoded diagnostic PCM, not music. If recording to integer PCM, use 16-bit or better, preferably 32-bit float WAV. Do not use MP3 or other lossy compression.

## Decode on Windows or other computer

```
py -m pip install numpy soundfile
py tools/decode.py measurement.wav
```

Writes `measurement_midi_events.csv` with precise incoming MIDI event timestamps and `measurement_reconstructed.wav` with the dry guitar left, MIDI impulses right (positive = Note On; negative = Note Off). Where multiple events share the same exact sample, CSV contains them all and the reconstructed WAV combines their visual markers.

## Format and timing

Each channel MIDI event is represented by a **15-sample** PCM packet:

1. Sync: -1.0
2. Version: encoded byte 1
3. Status byte
4. Data 1
5. Data 2 (0 for two-byte messages)
6–13. Original event frame timestamp, little-endian uint64
14. XOR checksum over payload bytes 2–13 (version through frame)
15. End marker: -0.75

Byte `b` is encoded as `(b + 1) / 512.0` (positive and recoverable in 16-bit or float WAV). Original event timestamp is from the LV2 frame offset (not the time the PCM packet happened to be emitted). Packets can span blocks and events may have identical sample timestamps.

**Important**: The decoder estimates the recording's start frame from the earliest non-delayed packet. It assumes the recording starts after the plugin is active, a normal running LV2 graph, and has at least one unqueued packet. No sample-rate conversion, independent sample-clock drift, or channel-specific processing should occur between plugin outputs and the WAV. The plugin preserves host-provided timestamps; it cannot undo upstream GuitarMidi block/timestamp quantisation.

## Limitations

* Prototype encodes MIDI channel voice messages only (Note On/Off, CC, program change, pitch bend and aftertouch), **not SysEx/system real-time**.
* Fixed 1024-record static FIFO; if more than 1023 MIDI events arrive faster than 15 frames each for a sustained period, events may drop. This would need an overflow/status indicator in a later version.
* If the right channel is silenced or attenuated by the recorder, the byte stream cannot be recovered.
* This captures MIDI **arrival time at the probe**. It doesn't directly measure the TFLite model's execution time; guitar attack detection against the dry waveform remains a separate analysis step.
* The 15-sample serialisation doesn't change the original MIDI timestamps, but the PCM pulse starts can be delayed when MIDI events overlap. Use the decoder's reconstructed WAV or CSV, **not the original right-channel packet locations**, for latency measurements.

License: MIT.
