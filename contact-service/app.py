"""Tiny contact-form mail relay for static sites (standard library only).
Receives a JSON POST on / and sends an e-mail over SMTP.

Environment variables:
  SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASS   SMTP account (SMTP_PASS is a secret: set it in your host's UI, never in git)
  CONTACT_TO            recipient address (required)
  SITE_NAME             shown in the From header and the mail body (default "the website")
  ALLOWED_TOPICS        optional, comma-separated list of accepted values for the "topic" field
  RATE_LIMIT_PER_HOUR   max messages per client IP per hour (default 5)

JSON body: name, email, phone, message, consent (must be true), optional topic,
and "website" (honeypot field: must stay empty, bots fill it)."""
import json, os, re, smtplib, ssl, sys, time, threading
from email.message import EmailMessage
from email.utils import formatdate, make_msgid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

HOST = os.environ.get("SMTP_HOST", "")
PORT = int(os.environ.get("SMTP_PORT", "465"))
USER = os.environ.get("SMTP_USER", "")
PASS = os.environ.get("SMTP_PASS", "")
TO = os.environ.get("CONTACT_TO", "")
SITE = os.environ.get("SITE_NAME", "the website")
LIMIT = int(os.environ.get("RATE_LIMIT_PER_HOUR", "5"))
TOPICS = {t.strip() for t in os.environ.get("ALLOWED_TOPICS", "").split(",") if t.strip()}
PHONE_RE = re.compile(r"^[+0-9 ().\-]{6,25}$")
EMAIL_RE = re.compile(r"^[^@\s<>\",;]{1,64}@[^@\s<>\",;]{1,190}\.[A-Za-z]{2,}$")
hits, lock = {}, threading.Lock()


def configured():
    return bool(HOST and USER and PASS and TO and PASS != "CHANGE_ME")


def clean(v, n):
    v = v if isinstance(v, str) else ""
    return re.sub(r"[\r\n\t]+", " ", v).strip()[:n]


def limited(ip):
    now = time.time()
    with lock:
        h = [t for t in hits.get(ip, []) if now - t < 3600]
        if len(h) >= LIMIT:
            hits[ip] = h
            return True
        h.append(now)
        hits[ip] = h
        if len(hits) > 5000:
            for k in [k for k, v in hits.items() if not v or now - v[-1] > 3600]:
                hits.pop(k, None)
    return False


def send(name, email, phone, topic, message):
    m = EmailMessage()
    m["Subject"] = f"New message from {SITE} – {topic}" if topic else f"New message from {SITE}"
    m["From"] = f"{SITE} <{USER}>"
    m["To"] = TO
    m["Reply-To"] = f"{name} <{email}>"
    m["Date"] = formatdate(localtime=True)
    m["Message-ID"] = make_msgid(domain=USER.split("@")[-1])
    m.set_content(
        f"New message from the website\n\nName: {name}\nEmail: {email}\nPhone: {phone}\n"
        f"Topic: {topic or 'not specified'}\n\nMessage:\n{message}\n\n"
        "Use Reply to answer: the reply goes to the sender's address.\n")
    with smtplib.SMTP_SSL(HOST, PORT, timeout=20, context=ssl.create_default_context()) as s:
        s.login(USER, PASS)
        s.send_message(m)


class H(BaseHTTPRequestHandler):
    server_version = "contact"

    def log_message(self, fmt, *a):
        sys.stdout.write("%s %s\n" % (self.address_string(), fmt % a))
        sys.stdout.flush()

    def reply(self, code, obj):
        b = json.dumps(obj).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(b)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(b)

    def do_GET(self):  # health check
        self.reply(200, {"ok": True, "configured": configured()})

    def do_POST(self):
        # Last X-Forwarded-For entry: the one added by our own reverse proxy, not spoofable by the client.
        ip = (self.headers.get("X-Forwarded-For", "").split(",")[-1].strip()) or self.client_address[0]
        try:
            n = int(self.headers.get("Content-Length", "0"))
            if n <= 0 or n > 8192:
                return self.reply(413, {"ok": False, "error": "invalid size"})
            d = json.loads(self.rfile.read(n).decode("utf-8"))
            if not isinstance(d, dict):
                raise ValueError
        except Exception:
            return self.reply(400, {"ok": False, "error": "invalid request"})
        if clean(d.get("website"), 50):  # honeypot: pretend it worked
            return self.reply(200, {"ok": True})
        name, email, phone = clean(d.get("name"), 100), clean(d.get("email"), 254), clean(d.get("phone"), 25)
        topic = clean(d.get("topic"), 60)
        if TOPICS and topic not in TOPICS:
            topic = ""
        message = (d.get("message") if isinstance(d.get("message"), str) else "").strip()[:3000]
        if len(name) < 2 or not EMAIL_RE.match(email) or not PHONE_RE.match(phone) \
                or len(re.sub(r"\D", "", phone)) < 8 or len(message) < 5 or d.get("consent") is not True:
            return self.reply(422, {"ok": False, "error": "invalid fields"})
        if not configured():
            print("SMTP not configured: set SMTP_HOST, SMTP_USER, SMTP_PASS and CONTACT_TO", flush=True)
            return self.reply(503, {"ok": False, "error": "unavailable"})
        if limited(ip):
            return self.reply(429, {"ok": False, "error": "too many requests"})
        try:
            send(name, email, phone, topic, message)
        except Exception as e:
            print("send failed: %s: %s" % (type(e).__name__, e), flush=True)
            return self.reply(502, {"ok": False, "error": "send failed"})
        print("sent ok (%s)" % (topic or "no topic"), flush=True)
        self.reply(200, {"ok": True})


if __name__ == "__main__":
    ThreadingHTTPServer(("0.0.0.0", 8080), H).serve_forever()
