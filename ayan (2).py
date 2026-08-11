import os
import time
import threading
import urllib.parse
import requests
import json
from flask import Flask, jsonify
from instagrapi import Client  # [web:16]

SESSION_ID_1 = os.getenv("SESSION_ID_1")
SESSION_ID_2 = os.getenv("SESSION_ID_2")
SESSION_ID_3 = os.getenv("SESSION_ID_3")
SESSION_ID_4 = os.getenv("SESSION_ID_4")
SESSION_ID_5 = os.getenv("SESSION_ID_5")
SESSION_ID_6 = os.getenv("SESSION_ID_6")
GROUPS_1 = os.getenv("GROUPS_1", "")
GROUPS_2 = os.getenv("GROUPS_2", "")
GROUPS_3 = os.getenv("GROUPS_3", "")
GROUPS_4 = os.getenv("GROUPS_4", "")
GROUPS_5 = os.getenv("GROUPS_5", "")
GROUPS_6 = os.getenv("GROUPS_6", "")
MESSAGE_TEXT = os.getenv("MESSAGE_TEXT", "Hello 👋")
SELF_URL = os.getenv("SELF_URL", "")
NC_TITLES_RAW = os.getenv("NC_TITLES", "") 
SPAM_START_OFFSET = int(os.getenv("SPAM_START_OFFSET", "1"))
SPAM_GAP_BETWEEN_ACCOUNTS = int(os.getenv("SPAM_GAP_BETWEEN_ACCOUNTS", "40"))
NC_START_OFFSET = int(os.getenv("NC_START_OFFSET", "1"))
NC_ACC_GAP = int(os.getenv("NC_ACC_GAP", "180"))

MSG_REFRESH_DELAY = int(os.getenv("MSG_REFRESH_DELAY", "1"))
BURST_COUNT = int(os.getenv("BURST_COUNT", "1"))
SELF_PING_INTERVAL = int(os.getenv("SELF_PING_INTERVAL", "60"))
COOLDOWN_ON_ERROR = int(os.getenv("COOLDOWN_ON_ERROR", "300"))
DOC_ID = os.getenv("DOC_ID", "29088580780787855")
CSRF_TOKEN = os.getenv("CSRF_TOKEN", "")

app = Flask(__name__)
MAX_SESSION_LOGS = 200
session_logs = {
    "acc1": [],
    "acc2": [],
    "acc3": [],
    "acc4": [],
    "acc5": [],
    "acc6": [],
    "system": []
}
logs_lock = threading.Lock()

def _push_log(session, msg):
    if session not in session_logs:
        session = "system"
    with logs_lock:
        session_logs[session].append(msg)
        if len(session_logs[session]) > MAX_SESSION_LOGS:
            session_logs[session].pop(0)


def log(msg, session="system"):
    line = f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {msg}"
    print(line, flush=True)
    _push_log(session, msg)


@app.route("/dashboard")
def dashboard():
    return """
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>SINISTERS ⚡ SX⁷</title>
<style>
    * { box-sizing: border-box; }
    body {
        margin: 0;
        min-height: 100vh;
        background:
            radial-gradient(circle at 20% 0%, #182033 0%, transparent 35%),
            radial-gradient(circle at 80% 0%, #101827 0%, transparent 35%),
            #070a10;
        color: #e8edf7;
        font-family: Inter, ui-sans-serif, system-ui, -apple-system, Segoe UI, sans-serif;
    }
    .wrap {
        width: min(1100px, calc(100% - 28px));
        margin: 0 auto;
        padding: 34px 0 50px;
    }
    .header {
        text-align: center;
        padding: 20px 0 28px;
    }
    .title {
        margin: 0;
        font-size: clamp(28px, 5vw, 48px);
        font-weight: 900;
        letter-spacing: 3px;
        text-shadow: 0 0 28px rgba(120, 150, 255, .25);
    }
    .sub {
        margin-top: 8px;
        color: #7f8ba3;
        font-size: 12px;
        letter-spacing: 2px;
        text-transform: uppercase;
    }
    .logs {
        display: flex;
        flex-direction: column;
        gap: 10px;
    }
    .log {
        border: 1px solid #202938;
        background: rgba(14, 18, 27, .88);
        border-radius: 14px;
        padding: 13px 16px;
        box-shadow: 0 8px 28px rgba(0,0,0,.22);
        animation: in .2s ease-out;
    }
    .log.sent { border-left: 3px solid #4aa3ff; }
    .log.rename { border-left: 3px solid #b46cff; }
    .log.ping { border-left: 3px solid #39d98a; }
    .time {
        color: #69758b;
        font-size: 11px;
        margin-bottom: 5px;
        font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
    }
    .msg {
        color: #e9eef8;
        font-size: 14px;
        line-height: 1.45;
        word-break: break-word;
    }
    .empty {
        text-align: center;
        color: #657087;
        border: 1px dashed #273043;
        border-radius: 14px;
        padding: 40px 20px;
    }
    @keyframes in {
        from { opacity: 0; transform: translateY(5px); }
        to { opacity: 1; transform: translateY(0); }
    }
</style>
</head>
<body>
<div class="wrap">
    <div class="header">
        <h1 class="title">SINISTERS ⚡ SX⁷</h1>
        <div class="sub">Live Activity Logs</div>
    </div>
    <div id="logs" class="logs">
        <div class="empty">Waiting for logs...</div>
    </div>
</div>

<script>
function classify(s) {
    if (/sent to|SENT/i.test(s)) return "sent";
    if (/changed title \\(graphql\\)|graphql/i.test(s)) return "rename";
    if (/Self ping/i.test(s)) return "ping";
    return null;
}

async function refreshLogs() {
    try {
        const r = await fetch("/status", {cache: "no-store"});
        const data = await r.json();
        const all = [];

        for (const key of ["acc1","acc2","acc3","acc4","acc5","acc6"]) {
            const d = data[key] || {};
            for (const k of ["last_send_ok","last_title_ok"]) {
                if (d[k]) all.push({text: d[k], type: classify(d[k])});
            }
        }

        for (const s of (data.system_last || [])) {
            all.push({text: s, type: classify(s)});
        }

        const filtered = all.filter(x => x.type).slice(-100);
        const root = document.getElementById("logs");

        if (!filtered.length) {
            root.innerHTML = '<div class="empty">No matching logs yet.</div>';
            return;
        }

        root.innerHTML = filtered.reverse().map(x => {
            const m = x.text.match(/^\\[([^\\]]+)\\]\\s*(.*)$/);
            const tm = m ? m[1] : "";
            const body = m ? m[2] : x.text;
            return `<div class="log ${x.type}">
                <div class="time">${escapeHtml(tm)}</div>
                <div class="msg">${escapeHtml(body)}</div>
            </div>`;
        }).join("");
    } catch (e) {
        document.getElementById("logs").innerHTML =
            '<div class="empty">Dashboard temporarily unavailable.</div>';
    }
}

function escapeHtml(s) {
    return String(s).replace(/[&<>"']/g, c => ({
        "&":"&amp;", "<":"&lt;", ">":"&gt;", '"':"&quot;", "'":"&#039;"
    }[c]));
}

refreshLogs();
setInterval(refreshLogs, 2000);
</script>
</body>
</html>
"""

@app.route("/health")
def health():
    return jsonify({"status": "ok", "message": "Bot process alive"})

def summarize(lines):
    rev = list(reversed(lines))
    last_login = next((l for l in rev if "Logged in" in l), None)
    last_send_ok = next((l for l in rev if "✅" in l and "sent to" in l), None)
    last_send_err = next((l for l in rev if "Send failed" in l or "⚠ send failed" in l), None)
    last_title_ok = next((l for l in rev if "changed title" in l and "📝" in l), None)
    last_title_err = next((l for l in rev if "Title change" in l or "GraphQL title" in l), None)
    return {
        "last_login": last_login,
        "last_send_ok": last_send_ok,
        "last_send_error": last_send_err,
        "last_title_ok": last_title_ok,
        "last_title_error": last_title_err,
    }

@app.route("/status")
def status():
    with logs_lock:
        acc1_logs = session_logs["acc1"][-80:]
        acc2_logs = session_logs["acc2"][-80:]
        acc3_logs = session_logs["acc3"][-80:]
        acc4_logs = session_logs["acc4"][-80:]
        acc5_logs = session_logs["acc5"][-80:]
        acc6_logs = session_logs["acc6"][-80:]
        system_last = session_logs["system"][-20:]

    return jsonify({
        "ok": True,
        "acc1": summarize(acc1_logs),
        "acc2": summarize(acc2_logs),
        "acc3": summarize(acc3_logs),
        "acc4": summarize(acc4_logs),
        "acc5": summarize(acc5_logs),
        "acc6": summarize(acc6_logs),
        "system_last": system_last
    })

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
        cl.login_by_sessionid(session_id)  # [web:16]
        uname = getattr(cl, "username", None) or name_hint or "unknown"
        log(f"✅ Logged in {uname}", session=name_hint or "system")
        return cl
    except Exception as e:
        log(f"❌ Login failed ({name_hint}): {e}", session=name_hint or "system")
        return None

def safe_send_message(cl, gid, msg, acc_name):
    try:
        cl.direct_send(msg, thread_ids=[int(gid)])  # [web:16]
        log(f"✅ {getattr(cl,'username','?')} sent to {gid}", session=acc_name)
        return True
    except Exception as e:
        log(f"⚠ Send failed ({getattr(cl,'username','?')}) -> {gid}: {e}", session=acc_name)
        return False

def safe_change_title_direct(cl, gid, new_title, acc_name):
    try:
        tt = cl.direct_thread(int(gid))  # [web:16]
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
                return True
            except Exception as e:
                log(
                    f"⚠ Title change unexpected response for {gid}: {e} (status {resp.status_code})",
                    session=acc_name
                )
                return False
        except Exception as e:
            log(f"⚠ Exception performing GraphQL title change for {gid}: {e}", session=acc_name)
            return False
    except Exception as e:
        log(f"⚠ Unexpected fallback error for title change {gid}: {e}", session=acc_name)
        return False

def spam_account_loop(acc):
    """Independent message timer for one account: one GC every 40 seconds."""
    acc_name = acc["name"]
    gc_index = 0

    time.sleep(SPAM_START_OFFSET)

    while True:
        try:
            if acc.get("cooldown_until", 0) > time.time():
                log(f"⏳ {acc_name} cooling down", session=acc_name)
            elif not acc["active"] or not acc["client"]:
                log(f"⏭ {acc_name} inactive, skipping message slot", session=acc_name)
            elif not acc["groups"]:
                log(f"⏭ {acc_name} has no groups", session=acc_name)
            else:
                cl = acc["client"]
                gid = acc["groups"][gc_index % len(acc["groups"])]

                for _ in range(BURST_COUNT):
                    ok = safe_send_message(cl, gid, MESSAGE_TEXT, acc_name)
                    if not ok:
                        log(
                            f"⛔ {acc_name} failed, applying cooldown for message loop",
                            session=acc_name
                        )
                        acc["cooldown_until"] = time.time() + COOLDOWN_ON_ERROR
                        break

                    if MSG_REFRESH_DELAY > 0:
                        time.sleep(MSG_REFRESH_DELAY)

                if acc.get("cooldown_until", 0) <= time.time():
                    log(
                        f"📨 {getattr(cl, 'username', '?')} SENT — GC "
                        f"{(gc_index % len(acc['groups'])) + 1} [{gid}]",
                        session=acc_name
                    )

                gc_index = (gc_index + 1) % len(acc["groups"])

        except Exception as e:
            log(f"❌ Exception in {acc_name} message loop: {e}", session=acc_name)
            acc["cooldown_until"] = time.time() + COOLDOWN_ON_ERROR

        time.sleep(SPAM_GAP_BETWEEN_ACCOUNTS)


def spam_loop(accounts):
    """Start one independent 40-second GC timer for every account."""
    for acc in accounts:
        threading.Thread(target=spam_account_loop, args=(acc,), daemon=True).start()


def parse_nc_titles():
    """
    Returns a list of 4 titles, one per account.
    If NC_TITLES_RAW has fewer than 4, it pads with MESSAGE_TEXT[:40].
    """
    base = [t.strip() for t in NC_TITLES_RAW.split(",") if t.strip()]
    default_title = MESSAGE_TEXT[:40] or "NC"
    while len(base) < 6:
        base.append(default_title)
    return base[:6]

def nc_account_loop(acc, titles_map):
    """Independent rename timer for one account: one GC every 180 seconds."""
    acc_name = acc["name"]
    gc_index = 0
    nc_index = 0
    per_account_titles = parse_nc_titles()

    time.sleep(NC_START_OFFSET)

    while True:
        try:
            if acc.get("cooldown_until", 0) > time.time():
                log(f"⏳ {acc_name} cooling down", session=acc_name)
            elif not acc["active"] or not acc["client"]:
                log(f"⏭ {acc_name} inactive, skipping nc slot", session=acc_name)
            elif not acc["groups"]:
                log(f"⏭ {acc_name} has no groups", session=acc_name)
            else:
                cl = acc["client"]
                gid = acc["groups"][gc_index % len(acc["groups"])]

                titles = (
                    titles_map.get(str(gid))
                    or titles_map.get(int(gid))
                    if str(gid).isdigit()
                    else titles_map.get(str(gid))
                )

                if not titles:
                    titles = per_account_titles

                if not titles:
                    titles = [MESSAGE_TEXT[:40] or "NC"]

                t = titles[nc_index % len(titles)]

                ok = safe_change_title_direct(cl, gid, t, acc_name)

                if not ok:
                    log(
                        f"⛔ {acc_name} failed, applying cooldown for nc loop",
                        session=acc_name
                    )
                    acc["cooldown_until"] = time.time() + COOLDOWN_ON_ERROR
                else:
                    log(
                        f"💠 {getattr(cl, 'username', '?')} NC"
                        f"{(nc_index % len(titles)) + 1} — GC "
                        f"{(gc_index % len(acc['groups'])) + 1} [{gid}] -> {t}",
                        session=acc_name
                    )

                # Move to the next GC. After the last GC, start GC1 again
                # and advance to the next NC title.
                gc_index = (gc_index + 1) % len(acc["groups"])
                if gc_index == 0:
                    nc_index = (nc_index + 1) % len(titles)

        except Exception as e:
            log(f"❌ Exception in {acc_name} nc loop: {e}", session=acc_name)
            acc["cooldown_until"] = time.time() + COOLDOWN_ON_ERROR

        time.sleep(NC_ACC_GAP)


def nc_loop(accounts, titles_map):
    """Start one independent 180-second GC timer for every account."""
    for acc in accounts:
        threading.Thread(
            target=nc_account_loop,
            args=(acc, titles_map),
            daemon=True
        ).start()


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
    log(
        "STARTUP: "
        f"SESSION_ID_1={repr(SESSION_ID_1)}, "
        f"SESSION_ID_2={repr(SESSION_ID_2)}, "
        f"SESSION_ID_3={repr(SESSION_ID_3)}, "
        f"SESSION_ID_4={repr(SESSION_ID_4)}, "
        f"SESSION_ID_5={repr(SESSION_ID_5)}, "
        f"SESSION_ID_6={repr(SESSION_ID_6)}, "
        f"MESSAGE_TEXT={repr(MESSAGE_TEXT)}, "
        f"NC_TITLES={repr(NC_TITLES_RAW)}",
        session="system"
    )

    sessions = [
        (decode_session(SESSION_ID_1), GROUPS_1),
        (decode_session(SESSION_ID_2), GROUPS_2),
        (decode_session(SESSION_ID_3), GROUPS_3),
        (decode_session(SESSION_ID_4), GROUPS_4),
        (decode_session(SESSION_ID_5), GROUPS_5),
        (decode_session(SESSION_ID_6), GROUPS_6),
    ]

    titles_map = {}
    raw_titles = os.getenv("GROUP_TITLES", "")
    if raw_titles:
        try:
            titles_map = json.loads(raw_titles)
        except Exception as e:
            log(f"⚠ GROUP_TITLES JSON parse error: {e}. Using fallback titles.", session="system")

    accounts = []
    for i, (s, groups_raw) in enumerate(sessions, 1):
        acc_name = f"acc{i}"
        groups = [g.strip() for g in groups_raw.split(",") if g.strip()]
        if not s:
            log(f"⚠ No session for {acc_name}, keeping slot inactive", session=acc_name)
            accounts.append({"name": acc_name, "client": None, "groups": groups, "active": False, "cooldown_until": 0})
            continue

        log(f"🔐 Logging in account {i}...", session="system")
        cl = login_session(s, acc_name)
        if cl:
            accounts.append({"name": acc_name, "client": cl, "groups": groups, "active": True, "cooldown_until": 0})
        else:
            log(f"⚠ {acc_name} login failed, keeping slot inactive", session=acc_name)
            accounts.append({"name": acc_name, "client": None, "groups": groups, "active": False, "cooldown_until": 0})

    if not any(a["client"] for a in accounts):
        log("❌ No accounts logged in, aborting.", session="system")
        return

    try:
        t1 = threading.Thread(target=spam_loop, args=(accounts,), daemon=True)
        t1.start()
        log(
            "▶ Started spam loop with 6 slots "
            f"({SPAM_START_OFFSET}s start, {SPAM_GAP_BETWEEN_ACCOUNTS}s gap between slots)",
            session="system"
        )
    except Exception as e:
        log(f"❌ Failed to start spam loop thread: {e}", session="system")

    try:
        t2 = threading.Thread(target=nc_loop, args=(accounts, titles_map), daemon=True)
        t2.start()
        log(
            "▶ Started nc loop with 6 slots "
            f"({NC_START_OFFSET}s start, {NC_ACC_GAP}s gap between slots)",
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
    log(f"HTTP server starting on port {port}", session="system")
    try:
        app.run(host="0.0.0.0", port=port)
    except Exception as e:
        log(f"❌ Flask run failed: {e}", session="system")
