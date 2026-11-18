# Riwayat Emulator Capture

Owner-authorized dynamic-analysis test rig for the genuine **فضاء الروايات**
app (`com.fadariwyat.cenele`).

## What it does

1. Downloads the **genuine, unmodified** app from APKPure at runtime
   (EFForg `apkeep`).
2. Starts a rooted Android 11 (API 30) ARM64 cloud emulator
   (GitHub-hosted runner, `google_apis` image — no Play Store, `adb root`).
3. Installs the genuine app as a **system app** (`/system/priv-app`), so
   its own license check passes on its own through the check's
   system-app branch. Nothing is patched, spoofed, or bypassed.
4. Runs Frida (`ssl_hook.js`) to observe the live HMAC-signed chapter
   request in plaintext (BoringSSL `SSL_write`/`SSL_read` in
   `libflutter.so`), and drives the UI to open a chapter.
5. Uploads the capture as a workflow artifact for offline verification.

## What is NOT in this repo

- No APKs (the app is downloaded at runtime).
- No secrets, keys, API keys, or passwords.
- No license-check bypass, no patch, no installer spoofing.

## Run it

Actions → "Riwayat Emulator Capture" → Run workflow. The run takes a
while (ARM64 software emulation is slow). Download the `riwayat-capture`
artifact when it finishes.
