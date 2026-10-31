import base64, hashlib, hmac, os, time

SECRET = os.getenv("DFH_SECRET", "dev-secret-change-me").encode()


def hash_pw(p):
    return hashlib.pbkdf2_hmac("sha256", p.encode(), b"dfh-demo-salt", 20000).hex()


def make_token(uid, ttl=12 * 3600):
    msg = f"{uid}|{int(time.time()) + ttl}"
    sig = hmac.new(SECRET, msg.encode(), "sha256").hexdigest()
    return base64.urlsafe_b64encode(f"{msg}|{sig}".encode()).decode()


def read_token(tok):
    try:
        uid, exp, sig = base64.urlsafe_b64decode(tok.encode()).decode().split("|")
        good = hmac.new(SECRET, f"{uid}|{exp}".encode(), "sha256").hexdigest()
        if hmac.compare_digest(sig, good) and int(exp) > time.time():
            return int(uid)
    except Exception:
        pass
    return None
