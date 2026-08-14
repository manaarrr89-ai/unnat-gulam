import os
import time
import threading
import urllib.parse
import requests
import logging
import json
from flask import Flask, jsonify
from instagrapi import Client

sessions = []

i = 1
while True:
    value = os.getenv(f"SESSION_ID_{i}")
    if not value:
        break
    sessions.append(value)
    i += 1
GROUP_ID = os.getenv("GROUP_ID", "").strip()
MESSAGE_TEXT = os.getenv("MESSAGE_TEXT", "Hello 👋")
SELF_URL = os.getenv("SELF_URL", "")
NC_TITLES_RAW = os.getenv("NC_TITLES", "") 
SPAM_START_OFFSET = int(os.getenv("SPAM_START_OFFSET", "1"))
NC_START_OFFSET = int(os.getenv("NC_START_OFFSET", "1"))
SELF_PING_INTERVAL = int(os.getenv("SELF_PING_INTERVAL", "60"))
COOLDOWN_ON_ERROR = int(os.getenv("COOLDOWN_ON_ERROR", "300"))
DOC_ID = os.getenv("DOC_ID", "29088580780787855")
CSRF_TOKEN = os.getenv("CSRF_TOKEN", "")


START_TIME = time.time()
app = Flask(__name__)
logs_lock = threading.Lock()

logging.getLogger("werkzeug").disabled = True
app.logger.disabled = True

dashboard_status = {}

def log(msg, session="system"):
    line = f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {msg}"
    print(line, flush=True)

def update_dashboard(acc_name, key, value):
    with logs_lock:

        if acc_name not in dashboard_status:
            return

        if key == "log":

            dashboard_status[acc_name].setdefault("logs", [])

            dashboard_status[acc_name]["logs"].append(value)

            if len(dashboard_status[acc_name]["logs"]) > 20:
                dashboard_status[acc_name]["logs"].pop(0)

        else:
            dashboard_status[acc_name][key] = value

@app.route("/")
def health():
    return jsonify({"status": "ok", "message": "Bot process alive"})

@app.route("/dashboard")
def dashboard():

    uptime = int(time.time() - START_TIME)

    h = uptime // 3600
    m = (uptime % 3600) // 60
    s = uptime % 60

    runtime = f"{h:02}:{m:02}:{s:02}"

    with logs_lock:
        cards = dict(dashboard_status)

    active_cards = []

    for acc in cards.values():
        if acc and acc.get("username"):
            active_cards.append(acc)

    html = f"""
<!DOCTYPE html>
<html>
<head>

<title>SINISTERS ⚡ SX⁷</title>

<meta http-equiv="refresh" content="2">

<style>

*{{
margin:0;
padding:0;
box-sizing:border-box;
}}

body{{
background:#f2f2f2;
font-family:Consolas,monospace;
padding:40px;
}}

.header{{
text-align:center;
font-size:42px;
font-weight:bold;
margin-bottom:8px;
}}

.runtime{{
text-align:center;
font-size:20px;
margin-bottom:35px;
}}

.container{{
display:flex;
justify-content:center;
flex-wrap:wrap;
gap:25px;
}}

.card{{
width:320px;
height:760px;
background:white;
border:2px solid #111;
border-radius:14px;
padding:18px;
box-shadow:0 8px 18px rgba(0,0,0,.18);
display:flex;
flex-direction:column;
}}

.username{{
font-size:24px;
font-weight:bold;
text-align:center;
padding-bottom:14px;
border-bottom:2px solid #222;
margin-bottom:8px;
}}

.status{{
height:52px;
display:flex;
align-items:center;
justify-content:center;
font-size:18px;
font-weight:bold;
border-bottom:2px solid #222;
margin-bottom:6px;
}}

.logs{{
flex:1;
display:flex;
flex-direction:column;
overflow:hidden;
}}

.logline{{
height:31px;
display:flex;
align-items:center;
padding:0 8px;
font-size:15px;
border-bottom:1px solid #e5e5e5;
}}

.logline:last-child{{
border-bottom:none;
}}

.footer{{
margin-top:35px;
text-align:center;
font-size:15px;
font-weight:bold;
}}

</style>

</head>

<body>

<div class="header">
SINISTERS ⚡ SX⁷
</div>

<div class="runtime">
RUNTIME ⏳ {runtime}
</div>

<div class="container">
"""

    for acc in active_cards:

        logs = acc.get("logs", [])

        if len(logs) > 20:
            logs = logs[-20:]

        logs = logs + [""] * (20 - len(logs))

        html += f"""
<div class="card">

<div class="username">
{acc.get("username","-")}
</div>

<div class="status">
{acc.get("status","❌ INACTIVE")}
</div>

<div class="logs">
"""

        for line in logs:
            html += f'<div class="logline">{line}</div>'

        html += """
</div>

</div>
"""

    html += f"""
</div>

<div class="footer">
ACTIVE SESSIONS : {len(active_cards)}
</div>

</body>
</html>
"""

    return html

def decode_session(session):
    if not session:
        return session
    try:
        return urllib.parse.unquote(session)
    except Exception:
        return session

def login_session(session_id, name_hint=""):
    session_id = decode_session(session_id)
    try:
        cl = Client()
        cl.login_by_sessionid(session_id)
        uname = getattr(cl, "username", None) or name_hint or "unknown"
        log(f"✅ Logged in {uname}", session=name_hint or "system")
        return cl
    except Exception as e:
        log(f"❌ Login failed ({name_hint}): {e}", session=name_hint or "system")
        return None

def safe_send_message(cl, gid, msg, acc_name):
    try:
        cl.direct_send(msg, thread_ids=[int(gid)])
        log(f"✅ {getattr(cl,'username','?')} sent to {gid}", session=acc_name)

        update_dashboard(
            acc_name,
            "log",
            f"📨 SENT - {gid}"
        )

        return True
    except Exception as e:
        log(f"⚠ Send failed ({getattr(cl,'username','?')}) -> {gid}: {e}", session=acc_name)
        update_dashboard(
            acc_name,
            "log",
            "❌ SENT FAILED"
        )
        return False

def safe_change_title_direct(cl, gid, new_title, acc_name):
    try:
        tt = cl.direct_thread(int(gid))
        try:
            tt.update_title(new_title)
            log(
                f"📝 {getattr(cl,'username','?')} changed title (direct) for {gid} -> {new_title}",
                session=acc_name
            )
            return True
        except Exception:
            log(
                f"⚠ direct .update_title() failed for {gid} — will attempt GraphQL fallback",
                session=acc_name
            )
    except Exception:
        pass

    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
            "X-CSRFToken": CSRF_TOKEN,
            "X-Requested-With": "XMLHttpRequest",
            "Referer": f"https://www.instagram.com/direct/t/{gid}/",
        }
        cookies = {"csrftoken": CSRF_TOKEN}
        try:
            cl.private.headers.update(headers)
            cl.private.cookies.update(cookies)
            variables = {"thread_fbid": gid, "new_title": new_title}
            payload = {"doc_id": DOC_ID, "variables": json.dumps(variables)}
            resp = cl.private.post("https://www.instagram.com/api/graphql/", data=payload, timeout=10)
            try:
                result = resp.json()
                if "errors" in result:
                    log(
                        f"❌ GraphQL title change errors for {gid}: {result['errors']}",
                        session=acc_name
                    )
                    return False
                log(
                    f"📝 {getattr(cl,'username','?')} changed title (graphql) for {gid} -> {new_title}",
                    session=acc_name
                )

                update_dashboard(
                    acc_name,
                    "log",
                    f"⚡ {new_title}"
                )
                return True
            except Exception as e:
                log(
                    f"⚠ Title change unexpected response for {gid}: {e} (status {resp.status_code})",
                    session=acc_name
                )

                update_dashboard(
                    acc_name,
                    "log",
                    "❌ RENAME FAILED"
                )
                return False
        except Exception as e:
            log(f"⚠ Exception performing GraphQL title change for {gid}: {e}", session=acc_name)
            return False
    except Exception as e:
        log(f"⚠ Unexpected fallback error for title change {gid}: {e}", session=acc_name)
        return False

def spam_loop(accounts, groups):
    if not groups:
        log("⚠ No groups for messaging loop.", session="system")
        return

    time.sleep(SPAM_START_OFFSET)

    active_accounts = [a for a in accounts if a["client"]]

    if not active_accounts:
        return

    delay = 45 / len(active_accounts)

    while True:

        for acc in active_accounts:

            if acc.get("cooldown_until", 0) > time.time():
                continue

            try:
                ok = safe_send_message(
                    acc["client"],
                    groups[0],
                    MESSAGE_TEXT,
                    acc["name"]
                )

                if not ok:
                    acc["cooldown_until"] = time.time() + COOLDOWN_ON_ERROR

            except Exception as e:
                log(
                    f"❌ Exception in {acc['name']} message loop: {e}",
                    session=acc["name"]
                )
                acc["cooldown_until"] = time.time() + COOLDOWN_ON_ERROR

            time.sleep(delay)

def parse_nc_titles():
    """
    Returns a list of 4 titles, one per account.
    If NC_TITLES_RAW has fewer than 4, it pads with MESSAGE_TEXT[:40].
    """
    base = [t.strip() for t in NC_TITLES_RAW.split(",") if t.strip()]
    default_title = MESSAGE_TEXT[:40] or "NC"
    if not base:
        base = [default_title]
    return base

def nc_loop(accounts, groups, titles_map):
    if not groups:
        log("⚠ No groups for title loop.", session="system")
        return

    per_account_titles = parse_nc_titles()

    time.sleep(NC_START_OFFSET)

    active_accounts = [a for a in accounts if a["client"]]

    if not active_accounts:
        return

    delay = 180 / len(active_accounts)

    while True:

        for i, acc in enumerate(active_accounts):

            if acc.get("cooldown_until", 0) > time.time():
                continue

            try:
                title = per_account_titles[i % len(per_account_titles)]

                ok = safe_change_title_direct(
                    acc["client"],
                    groups[0],
                    title,
                    acc["name"]
                )

                if not ok:
                    acc["cooldown_until"] = time.time() + COOLDOWN_ON_ERROR

            except Exception as e:
                log(
                    f"❌ Exception in {acc['name']} rename loop: {e}",
                    session=acc["name"]
                )
                acc["cooldown_until"] = time.time() + COOLDOWN_ON_ERROR

            time.sleep(delay)

def self_ping_loop():
    while True:
        if SELF_URL:
            try:
                requests.get(SELF_URL, timeout=10)
                log("🔁 Self ping successful", session="system")
            except Exception as e:
                log(f"⚠ Self ping failed: {e}", session="system")
        time.sleep(SELF_PING_INTERVAL)

def start_bot():
    all_sessions = [decode_session(s) for s in sessions]
    if not GROUP_ID:
        log("❌ GROUP_ID is empty", session="system")
        return

    groups = [GROUP_ID]

    titles_map = {}
    raw_titles = os.getenv("GROUP_TITLES", "")
    if raw_titles:
        try:
            titles_map = json.loads(raw_titles)
        except Exception as e:
            log(f"⚠ GROUP_TITLES JSON parse error: {e}. Using fallback titles.", session="system")

    accounts = []
    for i, s in enumerate(all_sessions, 1):
        
        acc_name = f"acc{i}"
        dashboard_status.setdefault(acc_name, {})
        if not s:
            accounts.append({
                "name": acc_name,
                "display_name": f"USER {i}",
                "client": None,
                "active": False,
                "cooldown_until": 0
            })
            continue

        if "|" in s:
            username, sessionid = s.split("|", 1)
        else:
            username = f"USER {i}"
            sessionid = s
            acc_name = f"acc{i}"

        if not sessionid:
            accounts.append({"name": acc_name, "display_name": username or f"USER {i}", "client": None, "active": False, "cooldown_until": 0})
            continue

        log(f"🔐 Logging in account {i}...", session="system")
        cl = login_session(sessionid, acc_name)

        if cl:

            update_dashboard(acc_name, "username", username)
            update_dashboard(acc_name, "status", "✔ ACTIVE")
            update_dashboard(acc_name, "sent", "Waiting...")
            update_dashboard(acc_name, "rename", "Waiting...")

            accounts.append({"name": acc_name, "display_name": username, "client": cl, "active": True, "cooldown_until": 0})

        else:
            update_dashboard(acc_name, "username", username)
            update_dashboard(acc_name, "status", "❌ INACTIVE")
            update_dashboard(acc_name, "sent", "-")
            update_dashboard(acc_name, "rename", "-")

            accounts.append({"name": acc_name, "display_name": username, "client": None, "active": False, "cooldown_until": 0})

    if not any(a["client"] for a in accounts):
        log("❌ No accounts logged in, aborting.", session="system")
        return

    try:
        t1 = threading.Thread(target=spam_loop, args=(accounts, groups), daemon=True)
        t1.start()
        log(
            "▶ Started spam loop",
            session="system"
        )
    except Exception as e:
        log(f"❌ Failed to start spam loop thread: {e}", session="system")

    try:
        t2 = threading.Thread(target=nc_loop, args=(accounts, groups, titles_map), daemon=True)
        t2.start()
        log(
            "▶ Started nc loop",
            session="system"
        )

    except Exception as e:
        log(f"❌ Failed to start nc loop thread: {e}", session="system")

    try:
        t3 = threading.Thread(target=self_ping_loop, daemon=True)
        t3.start()
    except Exception as e:
        log(f"⚠ Failed to start self-ping thread: {e}", session="system")


def run_bot_once():
    try:
        threading.Thread(target=start_bot, daemon=True).start()
    except Exception as e:
        print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] ❌ Failed to start bot (import-time): {e}", flush=True)

run_bot_once()

if __name__ == "__main__":

    port = int(os.getenv("PORT", "10000"))

    app.run(
        host="0.0.0.0",
        port=port,
        debug=False,
        use_reloader=False
    )
