#!/bin/bash
# Runs inside the android-emulator-runner step (emulator up, adb on PATH).
# Installs the genuine app as a system app, starts frida-server, captures
# the HMAC-signed chapter request, drives the UI to a chapter.
exec > >(tee -a run_capture.log) 2>&1
set -x

PKG="com.fadariwyat.cenele"
SYS_DIR="/system/priv-app/${PKG}"

echo "=== step 1: root + remount ==="
adb root
sleep 3
adb remount
sleep 2
WRITABLE=$(adb shell "mkdir -p ${SYS_DIR} && touch ${SYS_DIR}/.wtest && echo OK || echo NO" | tr -d '\r')
echo "writable test: ${WRITABLE}"
if [ "${WRITABLE}" != "OK" ]; then
  echo "system not writable; disabling verity and rebooting"
  adb disable-verity
  adb reboot
  adb wait-for-device
  for i in $(seq 1 90); do
    if [ "$(adb shell getprop sys.boot_completed 2>/dev/null | tr -d '\r')" = "1" ]; then echo "boot completed after verity off"; break; fi
    sleep 10
  done
  adb root
  sleep 3
  adb remount
  sleep 2
fi
adb shell "rm -f ${SYS_DIR}/.wtest" || true

echo "=== step 2: push genuine splits as system app ==="
adb shell mkdir -p "${SYS_DIR}"
adb push splits_sys/base.apk "${SYS_DIR}/base.apk"
adb push splits_sys/split_config.arm64_v8a.apk "${SYS_DIR}/split_config.arm64_v8a.apk"
adb push splits_sys/split_config.en.apk "${SYS_DIR}/split_config.en.apk"
adb push splits_sys/split_config.fr.apk "${SYS_DIR}/split_config.fr.apk"
adb push splits_sys/split_config.mdpi.apk "${SYS_DIR}/split_config.mdpi.apk"
adb shell chmod 644 "${SYS_DIR}"/*.apk
adb shell restorecon -R "${SYS_DIR}" || true
adb shell ls -la "${SYS_DIR}"

echo "=== step 3: reboot so PackageManager picks up the system app ==="
adb reboot
adb wait-for-device
for i in $(seq 1 90); do
  if [ "$(adb shell getprop sys.boot_completed 2>/dev/null | tr -d '\r')" = "1" ]; then echo "boot completed after install"; break; fi
  sleep 10
done
sleep 10
adb shell pm list packages | grep cenele || echo "APP NOT LISTED after reboot"
adb shell dumpsys package ${PKG} | grep -i -m3 "flags\|versionName" || true

echo "=== step 4: frida-server ==="
adb push frida-server /data/local/tmp/frida-server
adb shell chmod 755 /data/local/tmp/frida-server
adb shell "/data/local/tmp/frida-server >/data/local/tmp/frida.log 2>&1 &"
sleep 4
frida-ps -U || echo "frida-ps failed"

echo "=== step 5: start Frida capture (spawns the app) ==="
nohup frida -U -f ${PKG} -l ssl_hook.js --no-pause -o capture.log > frida-out.log 2>&1 &
FRIDA_PID=$!
echo "frida pid: $FRIDA_PID"
sleep 15
adb shell pidof ${PKG} || echo "app pid not found"

echo "=== step 6: UI automation to open a chapter ==="
python3 uiauto.py || true

echo "=== step 7: collect ==="
sleep 5
kill $FRIDA_PID || true
sleep 3
adb shell screencap -p /sdcard/screen.png || true
adb pull /sdcard/screen.png ./screen.png || true
echo "--- capture.log head ---"
head -c 4000 capture.log || echo "no capture.log"
echo "--- uiauto.log ---"
cat uiauto.log || echo "no uiauto.log"
ls -la
echo "DONE"
