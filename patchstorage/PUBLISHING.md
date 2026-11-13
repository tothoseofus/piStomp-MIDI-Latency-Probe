# Publish to Patchstorage

**DANGER: NEVER CONNECT THE ENCODED MIDI PCM OUTPUT TO SPEAKERS, HEADPHONES OR AMPLIFIERS. RECORD WITH MONITORING DISABLED.**

1. Add repository Actions secrets `PATCHSTORAGE_USERNAME` and `PATCHSTORAGE_PASSWORD` (the Patchstorage account that owns the listing).
2. Publish the appropriate GitHub release using `Publish Release`.
3. Go to Actions → `Upload to Patchstorage` → Run workflow, entering the published tag (for example `v0.0.1`). **This publishes or updates the live Patchstorage listing.**
4. The uploader downloads the official GitHub release builds for piStomp ARM64 and Linux x86-64 only. Windows is served from GitHub Releases.
5. Check the Patchstorage listing afterward for accurate licence, platform files, safety description and artwork.

It will skip a matching release with both platforms, reject attempts to overwrite another owner's listing, reject downgrade, and fail if GPL-3.0-only cannot be mapped correctly.
