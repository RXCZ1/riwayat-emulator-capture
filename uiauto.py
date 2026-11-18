#!/usr/bin/env python3
"""Drive the riwayat app UI to open a chapter, so the HMAC-signed chapter
request fires and the Frida capture logs it. Runs adb commands, logs to
uiauto.log, stops as soon as X-NHV-Signature appears in capture.log.
No credentials are used; if a login wall appears it is logged and the
run ends as inconclusive."""
import subprocess
import sys
import time
import re
import xml.etree.ElementTree as ET

CAPTURE_LOG = "capture.log"
UI_LOG = "uiauto.log"
PKG = "com.fadariwyat.cenele"
MAIN = PKG + "/.MainActivity"


def log(msg):
    line = "[%s] %s" % (time.strftime("%H:%M:%S"), msg)
    print(line, flush=True)
    with open(UI_LOG, "a", encoding="utf-8") as f:
        f.write(line + "\n")


def adb(*args, timeout=40):
    try:
        r = subprocess.run(["adb"] + list(args), capture_output=True,
                           text=True, timeout=timeout)
        return r.stdout + r.stderr
    except Exception as e:
        return "<adb error: %s>" % e


def ensure_foreground():
    out = adb("shell", "dumpsys", "activity", "activities")
    m = re.search(r"ResumedActivity:.*?(\S+/\S+)", out)
    cur = m.group(1) if m else ""
    if PKG not in cur:
        log("foreground is %s (not the app); relaunching" % (cur or "?"))
        adb("shell", "am", "start", "-n", MAIN)
        time.sleep(6)


def dump_ui():
    adb("shell", "uiautomator", "dump", "/sdcard/ui.xml")
    time.sleep(1)
    adb("pull", "/sdcard/ui.xml", "ui.xml")
    try:
        with open("ui.xml", encoding="utf-8") as f:
            return f.read()
    except Exception:
        return ""


def parse_clickables(xml_text):
    nodes = []
    try:
        root = ET.fromstring(xml_text)
    except Exception:
        return nodes
    for n in root.iter("node"):
        if n.get("clickable") != "true":
            continue
        m = re.match(r"\[(\d+),(\d+)\]\[(\d+),(\d+)\]", n.get("bounds", ""))
        if not m:
            continue
        x1, y1, x2, y2 = map(int, m.groups())
        w, h = x2 - x1, y2 - y1
        if w < 20 or h < 20:
            continue
        nodes.append({
            "text": n.get("text", "") or "",
            "desc": n.get("content-desc", "") or "",
            "x": (x1 + x2) // 2,
            "y": (y1 + y2) // 2,
            "w": w,
            "h": h,
        })
    return nodes


def signature_seen():
    try:
        with open(CAPTURE_LOG, encoding="utf-8", errors="ignore") as f:
            return "X-NHV-Signature" in f.read()
    except Exception:
        return False


def main():
    log("uiauto starting")
    adb("shell", "am", "start", "-n", MAIN)
    time.sleep(10)
    deadline = time.time() + 600  # 10 minutes max
    tapped = set()
    while time.time() < deadline:
        if signature_seen():
            log("SUCCESS: X-NHV-Signature seen in capture log")
            return 0
        ensure_foreground()
        xml_text = dump_ui()
        if not xml_text:
            log("empty UI dump; waiting")
            time.sleep(5)
            continue
        low = xml_text.lower()
        if ("تسجيل الدخول" in xml_text or "login" in low
                or "sign in" in low):
            log("NOTE: possible login wall visible")
        nodes = parse_clickables(xml_text)
        log("found %d clickable nodes" % len(nodes))
        # Prefer nodes with text, largest area first; skip the top bar.
        nodes.sort(key=lambda n: (1 if n["text"] else 0, n["w"] * n["h"]),
                   reverse=True)
        acted = False
        for n in nodes:
            key = (n["x"], n["y"])
            if key in tapped:
                continue
            if n["y"] < 120:
                continue
            label = n["text"] or n["desc"] or "(no text)"
            log("tapping '%s' at %d,%d size %dx%d"
                % (label, n["x"], n["y"], n["w"], n["h"]))
            adb("shell", "input", "tap", str(n["x"]), str(n["y"]))
            tapped.add(key)
            acted = True
            time.sleep(6)
            break
        if not acted:
            log("no new tappable nodes; clearing history and retrying")
            tapped.clear()
            time.sleep(5)
    log("TIMEOUT: no signature captured within 10 minutes")
    return 1


if __name__ == "__main__":
    sys.exit(main())
