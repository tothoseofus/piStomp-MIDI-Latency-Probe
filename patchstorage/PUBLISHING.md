# Patchstorage publication checklist

1. Run **Create Release** from GitHub Actions after committing this update and verifying the `VERSION` file. It creates the `v0.0.1` GitHub release with three platform-specific LV2 bundle ZIPs.
2. In Patchstorage, create a new LV2 plugin listing for piStomp MIDI Latency Probe. Use `DESCRIPTION.md` verbatim, **especially the safety warning at its top**.
3. Upload the Linux x86-64 and Raspberry Pi ARM64 release ZIPs to the matching supported platform targets. Do not select a target for Windows unless Patchstorage offers it; the Windows release remains downloadable from GitHub.
4. Use `lv2/modgui/screenshot-latency-probe.png` for the artwork and attach/link the GitHub source repository. Set the licence to GPLv3. Check that author is Ken Spanks.
5. Confirm the published listing clearly says **DO NOT CONNECT THE RIGHT PCM OUTPUT TO SPEAKERS OR AMPLIFIERS**, then publish it.

Patchstorage publication is deliberately a **separate reviewed step**, not automatic on tagging. Patchstorage requires an authenticated account and target configuration; no credentials are bundled or requested in the repository.
