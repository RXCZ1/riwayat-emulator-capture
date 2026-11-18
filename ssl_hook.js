// Minimal Flutter BoringSSL hook for the riwayat app (ARM64 libflutter.so).
// Hooks SSL_write / SSL_read at the verified offsets and logs the plaintext
// HTTP traffic (the HMAC-signed chapter request carries X-NHV-Signature).
// Read-only observation: nothing is patched, nothing is bypassed.
console.log("[*] ssl_hook loading");

var LIB = "libflutter.so";
var OFF_WRITE = 0x75127c; // SSL_write
var OFF_READ = 0x750a84;  // SSL_read

function asText(ptr, len) {
    try {
        if (len <= 0 || len > 65536) return "";
        return ptr.readUtf8String(len) || "";
    } catch (e) {
        return "";
    }
}

function interesting(s) {
    return s.indexOf("cenele") !== -1 ||
           s.indexOf("X-NHV") !== -1 ||
           s.indexOf("chapters") !== -1;
}

function tryHook() {
    var base = Module.findBaseAddress(LIB);
    if (base === null) return false;
    console.log("[*] libflutter.so base: " + base);
    var w = base.add(OFF_WRITE);
    var r = base.add(OFF_READ);
    Interceptor.attach(w, {
        onEnter: function (args) {
            try {
                var len = args[2].toInt32();
                var s = asText(args[1], len);
                if (s && interesting(s)) {
                    console.log("[SSL_WRITE len=" + len + "]\n" + s);
                }
            } catch (e) {
                console.log("[hook write err] " + e);
            }
        }
    });
    Interceptor.attach(r, {
        onEnter: function (args) { this.buf = args[1]; },
        onLeave: function (retval) {
            try {
                var len = retval.toInt32();
                var s = asText(this.buf, len);
                if (s && interesting(s)) {
                    console.log("[SSL_READ len=" + len + "]\n" + s);
                }
            } catch (e) {
                console.log("[hook read err] " + e);
            }
        }
    });
    console.log("[*] hooks installed on SSL_write/SSL_read");
    return true;
}

if (!tryHook()) {
    console.log("[*] libflutter.so not loaded yet; polling...");
    var iv = setInterval(function () {
        if (tryHook()) clearInterval(iv);
    }, 500);
}
