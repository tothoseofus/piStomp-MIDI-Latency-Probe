#!/usr/bin/env python3
"""Decode stereo MIDI PCM packets from piStomp MIDI Latency Probe.

Install:  python -m pip install numpy soundfile
Decode:   python tools/decode.py recording.wav
Instrument response latency:
          python tools/decode.py recording.wav --mode instrument

WARNING: The right channel is diagnostic PCM DATA. Never monitor, play through
speakers/headphones or route it to an amplifier. Reconstructed WAVs are unsafe
for listening too: their right channel contains diagnostic impulses.
"""
import argparse
import csv
from pathlib import Path
import numpy as np
import soundfile as sf

PACKET_SAMPLES = 15


def decode_packets(audio, sr):
    if audio.shape[1] != 2:
        raise SystemExit('Expected stereo recording: left=audio, right=encoded MIDI PCM')
    right = audio[:, 1]
    events = []
    i = 0
    while i <= len(right) - PACKET_SAMPLES:
        if right[i] > -0.94 or abs(float(right[i + 14]) + 0.75) > 0.03:
            i += 1
            continue
        samples = right[i + 1:i + 14]
        raw = np.rint(samples * 512.0 - 1.0).astype(np.int32)
        if np.any(raw < 0) or np.any(raw > 255) or np.max(np.abs(samples - (raw + 1) / 512.0)) > 0.005:
            i += 1
            continue
        b = bytes(raw.tolist())
        if b[0] != 1 or np.bitwise_xor.reduce(raw[:12]) != raw[12]:
            i += 1
            continue
        status, data1, data2 = b[1], b[2], b[3]
        if not (0x80 <= status <= 0xEF):
            i += 1
            continue
        events.append(dict(marker_sample=i,
                           original_frame=int.from_bytes(b[4:12], 'little'),
                           status=status, data1=data1, data2=data2))
        i += PACKET_SAMPLES
    if not events:
        raise SystemExit('No valid MIDI PCM packets on right channel. Check routing and recording format.')

    # Any serialised packet can be delayed but not brought forward. At least
    # one non-delayed marker is necessary to recover the recording origin.
    origin = max(e['original_frame'] - e['marker_sample'] for e in events)
    for e in events:
        e['relative_sample'] = e['original_frame'] - origin
    return events


def label(status, data2):
    typ = status & 0xF0
    if typ == 0x90 and data2 > 0:
        return 'Note On'
    if typ == 0x80 or (typ == 0x90 and data2 == 0):
        return 'Note Off'
    return {0xA0: 'Poly Aftertouch', 0xB0: 'CC', 0xC0: 'Program Change',
            0xD0: 'Channel Pressure', 0xE0: 'Pitch Bend'}.get(typ, 'Other')


def export_events(path, audio, sr, events):
    rows = []
    impulses = np.zeros(len(audio), dtype='float32')
    for e in events:
        rel = e['relative_sample']
        status = e['status']
        typ = label(status, e['data2'])
        if 0 <= rel < len(audio):
            val = 0.85 if typ == 'Note On' else -0.85 if typ == 'Note Off' else 0.45 if typ == 'CC' else 0.25
            impulses[rel] = np.clip(impulses[rel] + val, -1, 1)
        rows.append(dict(time_seconds=f'{rel / sr:.9f}', relative_sample=rel,
                         channel=(status & 0x0F) + 1, event=typ,
                         note_or_data1=e['data1'], velocity_or_data2=e['data2'],
                         hex=f'{status:02X} {e["data1"]:02X} {e["data2"]:02X}',
                         actual_marker_sample=e['marker_sample'],
                         marker_delay_samples=e['marker_sample'] - rel))
    csv_path = path.with_name(path.stem + '_midi_events.csv')
    wav_path = path.with_name(path.stem + '_reconstructed.wav')
    with csv_path.open('w', newline='', encoding='utf-8') as out:
        writer = csv.DictWriter(out, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)
    sf.write(wav_path, np.column_stack([audio[:, 0], impulses]), sr, subtype='FLOAT')
    print(f'Decoded {len(rows)} MIDI events at {sr} Hz')
    print(f'MIDI events: {csv_path}')
    print(f'Reconstructed diagnostic WAV (DO NOT PLAY right channel): {wav_path}')
    print(f'Max packet serialisation delay: {max(row["marker_delay_samples"] for row in rows)} samples')


def instrument_latency(path, audio, sr, events, args):
    """Estimate first detectable audio onset following isolated Note Ons.

    This is an acoustic onset estimate, not a measurement of DSP execution time.
    Reject overlapping notes and already-sounding audio by default.
    """
    x = np.asarray(audio[:, 0], dtype=np.float64)
    n = len(x)
    window = max(1, round(args.window_ms * sr / 1000))
    pre = max(window, round(args.pre_ms * sr / 1000))
    horizon = max(window, round(args.search_ms * sr / 1000))
    gate = 10 ** (args.threshold_dbfs / 20)
    rise_factor = 10 ** (args.min_rise_db / 20)
    # Causal sliding RMS ending at each sample, avoiding FFT or long convolutions.
    power = x * x
    cumulative = np.concatenate(([0.0], np.cumsum(power)))
    indices = np.arange(n)
    starts = np.maximum(0, indices - window + 1)
    rms = np.sqrt(np.maximum(0, (cumulative[indices + 1] - cumulative[starts]) / (indices - starts + 1)))
    note_ons = [e for e in events if label(e['status'], e['data2']) == 'Note On']
    note_ons.sort(key=lambda e: (e['relative_sample'], e['status'], e['data1']))
    rows = []
    for j, e in enumerate(note_ons):
        at = e['relative_sample']
        row = dict(channel=(e['status'] & 0x0F) + 1, note=e['data1'], velocity=e['data2'],
                   midi_sample=at, midi_time_s=f'{at / sr:.9f}',
                   audio_onset_sample='', audio_onset_time_s='', latency_samples='', latency_ms='',
                   status='', baseline_rms='', detection_rms_threshold='')
        if at < pre or at >= n:
            row['status'] = 'insufficient_recording'
            rows.append(row)
            continue
        # A note beginning during another note's search window cannot be
        # reliably assigned to a particular audio attack from a mono mix.
        prev_at = note_ons[j - 1]['relative_sample'] if j > 0 else None
        if prev_at is not None and at - prev_at < horizon:
            row['status'] = 'overlapping_notes'
            rows.append(row)
            continue
        until = min(n, at + horizon)
        if j + 1 < len(note_ons):
            until = min(until, note_ons[j + 1]['relative_sample'])
        # Use local pre-note RMS to detect pre-existing sound (sustain/tails).
        baseline = float(np.sqrt(np.mean(power[at - pre:at])))
        threshold = max(gate, baseline * rise_factor)
        row['baseline_rms'] = f'{baseline:.8f}'
        row['detection_rms_threshold'] = f'{threshold:.8f}'
        if baseline >= gate:
            row['status'] = 'audio_already_sounding'
        elif until - at < window:
            row['status'] = 'overlapping_notes'
        else:
            # RMS must remain above the threshold for at least one window.
            # Causal RMS has <=window latency from the physical onset.
            above = rms[at:until] >= threshold
            hits = np.flatnonzero(above)
            onset = None
            if hits.size:
                for h in hits:
                    h = int(h)
                    if h + window <= len(above) and np.all(above[h:h + window]):
                        onset = at + h
                        break
            if onset is None:
                row['status'] = 'no_detectable_attack' if until >= at + horizon else 'overlapping_notes'
            else:
                row['audio_onset_sample'] = onset
                row['audio_onset_time_s'] = f'{onset / sr:.9f}'
                row['latency_samples'] = onset - at
                row['latency_ms'] = f'{(onset - at) * 1000 / sr:.3f}'
                row['status'] = 'measured'
        rows.append(row)
    csv_path = path.with_name(path.stem + '_instrument_latency.csv')
    with csv_path.open('w', newline='', encoding='utf-8') as out:
        writer = csv.DictWriter(out, fieldnames=list(rows[0].keys()) if rows else
                                ['channel','note','velocity','midi_sample','midi_time_s','audio_onset_sample',
                                 'audio_onset_time_s','latency_samples','latency_ms','status','baseline_rms',
                                 'detection_rms_threshold'])
        writer.writeheader()
        writer.writerows(rows)
    measured = [float(row['latency_ms']) for row in rows if row['status'] == 'measured']
    print(f'Instrument latency CSV: {csv_path}')
    print(f'Isolated measurable attacks: {len(measured)}/{len(note_ons)} Note Ons')
    if measured:
        print(f'Latency: median {np.median(measured):.2f} ms; mean {np.mean(measured):.2f} ms; '
              f'5th–95th percentile {np.percentile(measured,5):.2f}–{np.percentile(measured,95):.2f} ms')
    else:
        print('No unambiguous attacks found; check baseline, routing, thresholds and note spacing.')
    print('These are threshold-dependent audio-onset estimates; instrument patch/attack envelope matters.')


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('recording', type=Path, help='Stereo WAV: left audio input, right encoded MIDI PCM')
    ap.add_argument('--mode', choices=('decode', 'instrument'), default='decode',
                    help='instrument also estimates MIDI Note On to audible attack latency')
    ap.add_argument('--threshold-dbfs', type=float, default=-45,
                    help='minimum RMS attack threshold in dBFS (default -45)')
    ap.add_argument('--min-rise-db', type=float, default=12,
                    help='rise above pre-note RMS in dB (default 12)')
    ap.add_argument('--window-ms', type=float, default=1,
                    help='causal RMS window in ms (default 1)')
    ap.add_argument('--pre-ms', type=float, default=15,
                    help='pre-note baseline window in ms (default 15)')
    ap.add_argument('--search-ms', type=float, default=250,
                    help='maximum time after Note On to search, ms (default 250)')
    args = ap.parse_args()
    if not (-120 <= args.threshold_dbfs <= 0 and 0 < args.window_ms <= 100 and
            0 < args.pre_ms <= 1000 and 0 < args.search_ms <= 5000 and 0 <= args.min_rise_db <= 80):
        ap.error('Invalid threshold or window parameters; see --help')
    audio, sr = sf.read(args.recording, always_2d=True, dtype='float32')
    events = decode_packets(audio, sr)
    export_events(args.recording, audio, sr, events)
    if args.mode == 'instrument':
        instrument_latency(args.recording, audio, sr, events, args)


if __name__ == '__main__':
    main()
