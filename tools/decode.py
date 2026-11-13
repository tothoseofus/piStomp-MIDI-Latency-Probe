#!/usr/bin/env python3
"""Decode stereo PCM packets emitted by piStomp MIDI Latency Probe.

Requires: pip install numpy soundfile
Usage: python tools/decode.py recording.wav
Writes: recording_midi_events.csv and recording_reconstructed.wav
"""
import argparse
import csv
from pathlib import Path
import numpy as np
import soundfile as sf

PACKET_SAMPLES = 15

def parse_recording(path):
    audio, sr = sf.read(path, always_2d=True, dtype='float32')
    if audio.shape[1] != 2:
        raise SystemExit('Expected two channels: left dry audio, right MIDI PCM')
    r = audio[:, 1]
    events = []
    i = 0
    while i <= len(r) - PACKET_SAMPLES:
        if r[i] > -0.94:
            i += 1
            continue
        if abs(float(r[i+14]) + 0.75) > 0.03:
            i += 1
            continue
        samples = r[i+1:i+14]
        raw = np.rint(samples * 512.0 - 1.0).astype(np.int32)
        if np.any(raw < 0) or np.any(raw > 255) or np.max(np.abs(samples - (raw+1)/512.0)) > 0.005:
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
        frame = int.from_bytes(b[4:12], 'little')
        events.append(dict(marker_sample=i, original_frame=frame,
                           status=status, data1=data1, data2=data2))
        i += PACKET_SAMPLES
    if not events:
        raise SystemExit('No valid MIDI PCM packets found on right channel')
    # marker_sample = original_frame - recording_start_frame + serialisation_delay.
    # Packet serialisation can only delay, never advance an event. Therefore the
    # largest (original_frame - marker_sample) gives recording_start_frame.
    origin = max(e['original_frame'] - e['marker_sample'] for e in events)
    def label(e):
        s, d1, d2 = e['status'], e['data1'], e['data2']
        typ = s & 0xF0
        if typ == 0x90 and d2 > 0: return 'Note On'
        if typ == 0x80 or (typ == 0x90 and d2 == 0): return 'Note Off'
        return {0xA0:'Poly Aftertouch',0xB0:'CC',0xC0:'Program Change',
                0xD0:'Channel Pressure',0xE0:'Pitch Bend'}.get(typ,'Other')
    rows = []
    decoded_impulses = np.zeros(len(r), dtype='float32')
    for e in events:
        rel = e['original_frame'] - origin
        status = e['status']
        typ = label(e)
        if 0 <= rel < len(r):
            if typ == 'Note On': val = 0.85
            elif typ == 'Note Off': val = -0.85
            elif typ == 'CC': val = 0.45
            else: val = 0.25
            # If simultaneous events coincide, CSV retains all of them.
            decoded_impulses[rel] = np.clip(decoded_impulses[rel] + val, -1, 1)
        rows.append(dict(time_seconds=f'{rel/sr:.9f}', relative_sample=rel,
                         channel=(status & 0xF)+1, event=typ,
                         note_or_data1=e['data1'], velocity_or_data2=e['data2'],
                         hex=f'{status:02X} {e["data1"]:02X} {e["data2"]:02X}',
                         actual_marker_sample=e['marker_sample'],
                         marker_delay_samples=e['marker_sample']-rel))
    path = Path(path)
    csv_path = path.with_name(path.stem+'_midi_events.csv')
    wav_path = path.with_name(path.stem+'_reconstructed.wav')
    with csv_path.open('w', newline='', encoding='utf-8') as out:
        writer = csv.DictWriter(out, fieldnames=list(rows[0].keys()))
        writer.writeheader(); writer.writerows(rows)
    sf.write(wav_path, np.column_stack([audio[:,0], decoded_impulses]), sr, subtype='FLOAT')
    print(f'Decoded {len(rows)} MIDI events at {sr} Hz')
    print(f'CSV: {csv_path}')
    print(f'Reconstructed dry guitar L / MIDI impulses R: {wav_path}')
    print(f'Max packet serialisation delay: {max(row["marker_delay_samples"] for row in rows)} samples')

if __name__ == '__main__':
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('recording', help='Stereo WAV from piStomp latency probe')
    parse_recording(ap.parse_args().recording)
