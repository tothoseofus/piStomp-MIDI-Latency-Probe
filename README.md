# piStomp MIDI Latency Probe

Lightweight LV2 plugin for audio-to-MIDI and MIDI-instrument response-time measurements on piStomp v3 (Pi 5) and other LV2 hosts.

## ⚠️ DANGER — NEVER CONNECT THE ENCODED MIDI PCM OUTPUT TO SPEAKERS OR AN AMPLIFIER

**DO NOT LISTEN TO, MONITOR, PLAY BACK THROUGH SPEAKERS/HEADPHONES, OR CONNECT THE `Encoded MIDI Right` OUTPUT TO A SPEAKER, AMPLIFIER, PA SYSTEM OR OTHER AUDIO PLAYBACK DEVICE.**

**The right output is NOT MUSIC OR AN AUDIO SIGNAL FOR LISTENING. It carries diagnostic PCM DATA with abrupt full-scale marker samples. It can produce loud clicks and potentially damage connected equipment or hearing.**

**Route `Encoded MIDI Right` ONLY to a recording/capture input configured for direct, unprocessed capture. Mute its monitoring/playback. When analysing recordings, do not audition the raw or reconstructed MIDI pulse channel.** The `Dry Audio Left` output carries normal guitar audio, but any stereo recording containing the right-channel data must also be treated as diagnostic data, **not played through speakers**.

---

## Purpose

* `Dry Guitar In` (mono audio) is copied **without any intentional delay** to `Dry Audio Left`.
* `MIDI In` accepts LV2 MIDI channel messages and encodes their status/data/timestamp as sample-accurate PCM packets in `Encoded MIDI Right`.
* No synthesiser, internal file writing, external model, persistent worker, or blocking operation in the audio callback.

## Build

On GitHub, upload files preserving folder layout and enable Actions. The reusable `build.yml` workflow builds all three platforms and uploads `.lv2` bundles as GitHub Actions artifacts.

If building locally on Linux with LV2 headers and a compiler: `make CC=gcc all`.

## Platforms and GitHub Actions artifacts

The workflow builds three independent binary bundles using the same DSP source, MIDI packet format, MOD GUI, and GPL-3.0-only licence:

| Artifact | Target | Binary |
|---|---|---|
| `vX.Y.Z-pistomp-midi-latency-probe-pistomp-aarch64-RUN` | piStomp 3 / Raspberry Pi 5 Linux ARM64 | `latency_probe.so` |
| `vX.Y.Z-pistomp-midi-latency-probe-linux-x86_64-RUN` | Linux x86-64 LV2 hosts / MOD Desktop | `latency_probe.so` |
| `vX.Y.Z-pistomp-midi-latency-probe-windows-x86_64-RUN` | Windows x86-64 LV2 hosts / MOD Desktop | `latency_probe.dll` |

**No ZIP inside ZIP:** GitHub Actions uploads the built `.lv2` files directly. The Actions download itself is a ZIP; extract those contents into a directory named `pistomp-midi-latency-probe.lv2` if the downloaded ZIP does not retain the bundle directory. A proper bundle has `manifest.ttl`, `latency_probe.ttl`, `modgui.ttl`, the platform binary and the `modgui/` assets together.

The MOD GUI is cosmetic: no JavaScript or controls, and no DSP/UI interaction. Standard LV2 hosts can ignore the MOD-specific files.

For a manual ZIP, `make package` is still available, but the Actions workflow does **not** use it. Windows is cross-compiled via MinGW-w64 on Ubuntu; runtime compatibility with MOD Desktop Windows still requires an on-device check.

## Install on piStomp

Download the appropriate GitHub Actions artifact and unzip it. Install the `pistomp-midi-latency-probe.lv2` directory under your piStomp LV2 bundle directory (e.g. `/home/patch/.lv2` or your existing custom-plugin location). Refresh/restart the plugin host as needed.

## Two measurement modes

The **same plugin and stereo PCM format** support both workflows. No plugin rebuild or DSP change is necessary. The left channel is always the supplied audio input; the right channel is always **diagnostic MIDI PCM, NEVER listening audio**.

### Mode A — audio-to-MIDI (GuitarMidi)

```
               +--------------------------> Probe: Dry Guitar In
Guitar Input --+---> GuitarMidi: Audio In
                           GuitarMidi: MIDI Out ---> Probe: MIDI In

Probe: Dry Audio Left ------> Output 1 (left)
Probe: Encoded MIDI Right --> RECORDER ONLY (right, monitoring MUTED)
```

Record the two outputs as stereo **with no effects, gain adjustments, pan mixing or resampling on the right channel**. Use piStomp's existing recorder or an external stereo capture. **WARNING: Never route the right channel into a loudspeaker, amplifier, monitor bus, or headphones. Disable monitoring on the recorder.** It contains encoded diagnostic PCM, not music. If recording to integer PCM, use 16-bit or better, preferably 32-bit float WAV. Do not use MP3 or other lossy compression.

### Mode B — MIDI-to-audio (MIDI instrument response latency)

Feed a MIDI source to both the **instrument under test** and the **Probe: MIDI In**. Feed the instrument’s **audio output** to **Probe: Dry Guitar In** (the port name is historical: it accepts any mono audio). Capture the Probe’s stereo outputs unchanged:

```text
MIDI keyboard / MIDI test generator --+--> Instrument: MIDI In
                                     +--> Probe: MIDI In

Instrument: Audio Out --------------------> Probe: Dry Guitar In
Probe: Dry Audio Left -------------------> RECORDER left channel
Probe: Encoded MIDI Right --------------> RECORDER right channel (MONITORING OFF)
```

**DANGER: The encoded MIDI right output must NEVER go to speakers, headphones, an amplifier or a live monitoring bus.** Do not audition either the recorded encoded-right channel or the reconstructed impulse-right channel. Instrument audio can be monitored separately with a *safe, independent* route, not via diagnostic right-channel playback.

This measures time from the **MIDI Note On arriving at the Probe** to the first detectable audio attack at the Probe audio input. In the simplest setup, route the same MIDI stream to both ports; for a hardware instrument, its analogue audio output must be connected to a suitable audio interface input and level-matched. It includes instrument processing, its patch attack envelope and any audio routing latency. It does *not* measure the MIDI controller's internal scan time or any latency before the MIDI split. For best accuracy, split MIDI close to the instrument and use equally direct signal paths.

For automated estimates, use isolated short notes with adequate silence before each note, preferably a percussive patch with fast attack and no reverb or delay. Consecutive/polyphonic notes or notes over a sustained tail are flagged as ambiguous. The waveform's first detectable attack depends on a threshold, so this measures practical **audio response**, not necessarily the first nonzero PCM sample.

## Decode on Windows or other computer

```
py -m pip install numpy soundfile
py tools/decode.py measurement.wav

# For MIDI instrument response measurements:
py tools/decode.py instrument_recording.wav --mode instrument
```

Writes `measurement_midi_events.csv` with precise incoming MIDI event timestamps and `measurement_reconstructed.wav` with the dry guitar left, MIDI impulses right (positive = Note On; negative = Note Off). **The reconstructed WAV is also diagnostic data: do not play the right channel through speakers or headphones.** Where multiple events share the same exact sample, CSV contains them all and the reconstructed WAV combines their visual markers.

### Instrument response latency output

`--mode instrument` retains the normal MIDI event CSV and reconstructed diagnostic WAV, and also writes `instrument_recording_instrument_latency.csv`. Each Note On has its own row, with MIDI time, detected audio attack time, latency (samples and milliseconds), and a status. Only rows marked `measured` enter the printed summary; possible statuses include `audio_already_sounding`, `overlapping_notes`, `no_detectable_attack`, and `insufficient_recording`.

Onset detection uses a **causal 1 ms RMS window** (default), scanning up to **250 ms** after each Note On for a sustained rise crossing both a **−45 dBFS** gate and **12 dB** above local pre-note RMS. Adjust for instrument level and timbre, for example:

```shell
py tools/decode.py instrument_recording.wav --mode instrument --threshold-dbfs -55 --search-ms 500
```

The measured onset can shift with threshold, patch envelope, effects and recording level. The default algorithm *does not* try to separate mixed/polyphonic notes, and rejects Note Ons that overlap an earlier note's search window or start over audible signal; inspect the left-channel waveform if these statuses occur. If there is no audio attack within the scan window, it reports `no_detectable_attack`, not a fabricated latency.

**Clock/measurement caveat:** MIDI event timestamps and the left-channel audio are aligned within the Probe’s LV2 processing clock. This measures arrival-to-audio response *as seen by the Probe*, including any differential routing delays introduced before its inputs. Do not add effects or resampling in either branch, and disable MIDI/audio monitoring of the encoded channel.

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
* This captures MIDI **arrival time at the probe**. It does not directly measure a model's execution time; guitar onset detection remains separate. In instrument mode, measured attack latency includes the instrument patch and its audio path and is threshold dependent.
* The 15-sample serialisation doesn't change the original MIDI timestamps, but the PCM pulse starts can be delayed when MIDI events overlap. Use the decoder's reconstructed WAV or CSV, **not the original right-channel packet locations**, for latency measurements.

License: **GNU GPL version 3 only (GPL-3.0-only)**. See [LICENSE](LICENSE).

## Project information and releases

Author and copyright: **Ken Spanks © 2026**. Licence: **GPL-3.0-only**.

Project homepage and LV2 plugin URI: https://github.com/tothoseofus/piStomp-MIDI-Latency-Probe

The `VERSION` file is the single source of truth for the release number. `make` stamps `lv2:minorVersion` and `lv2:microVersion` into the generated bundle. The `Publish Release` workflow calls the reusable `build.yml` workflow, then packages and publishes the three artifacts under the matching `vX.Y.Z` tag.

**URI migration:** The pre-release plugin used `https://example.org/pistomp-midi-latency-probe`. This release intentionally changes its LV2 identity to the GitHub URI. Existing pedalboards referencing the old URI may require removing the old plugin and adding the new one.

Patchstorage publication is performed by the `Upload to Patchstorage` workflow using the official uploader and two Linux targets; Windows downloads remain on GitHub Releases. Configure the Patchstorage credentials as repository secrets first. The user-facing safety warning must remain prominent.

## Automated releases and Patchstorage publication

- `.github/workflows/build.yml` builds ARM64, Linux x86-64 and Windows x86-64 LV2 bundles. It is reusable (`workflow_call`) and can also be run independently. Artifacts contain a directly installable `.lv2` directory with **no nested ZIP**.
- `.github/workflows/release.yml` validates `VERSION`, calls `build.yml` **once**, downloads all three build artifacts from the same workflow run, validates and creates three platform release ZIPs, and publishes the GitHub release. It accepts manual dispatch from `main` or matching tags.
- `.github/workflows/patchstorage.yml` is a separate, manually dispatched **live publication** workflow. It downloads the published GitHub release ZIPs and uploads/updates the ARM64 and Linux x86-64 packages on Patchstorage through its LV2 uploader. Windows remains a GitHub release download.

Set GitHub Actions repository secrets `PATCHSTORAGE_USERNAME` and `PATCHSTORAGE_PASSWORD` before running **Upload to Patchstorage**. The account must own any existing Patchstorage listing for this plugin URI. The uploader refuses downgrades and refuses to mislabel **GPL-3.0-only** as GPL-3.0-or-later; its current licence mapping needs to recognise the correct licence identifier.

**SAFETY: Never connect the `Encoded MIDI Right` output or the diagnostic reconstructed WAV right channel to any speaker, amplifier, headphone or monitoring output.**
