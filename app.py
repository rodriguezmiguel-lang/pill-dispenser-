import os
import sqlite3
import time
from flask import Flask, request, jsonify, render_template

app = Flask(__name__)

DB_PATH = os.environ.get("DB_PATH", "data.db")


def db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = db()
    c = conn.cursor()
    c.execute(
        """
        CREATE TABLE IF NOT EXISTS schedule (
            deviceId TEXT NOT NULL,
            hour INTEGER NOT NULL,
            minute INTEGER NOT NULL
        )
        """
    )
    c.execute(
        """
        CREATE TABLE IF NOT EXISTS history (
            deviceId TEXT NOT NULL,
            timestamp INTEGER NOT NULL
        )
        """
    )
    conn.commit()
    conn.close()


init_db()


@app.get("/")
def index():
    device_id = request.args.get("deviceId", "distributeur01")
    return render_template("index.html", deviceId=device_id)


@app.get("/nurse/<deviceId>")
def nurse(deviceId):
    conn = db()
    sched = conn.execute(
        "SELECT hour, minute FROM schedule WHERE deviceId=? ORDER BY hour, minute",
        (deviceId,),
    ).fetchall()
    conn.close()
    return render_template("nurse.html", deviceId=deviceId, sched=sched)


@app.get("/patient/<deviceId>")
def patient(deviceId):
    conn = db()
    hist = conn.execute(
        "SELECT timestamp FROM history WHERE deviceId=? ORDER BY timestamp DESC LIMIT 50",
        (deviceId,),
    ).fetchall()
    conn.close()
    return render_template("patient.html", deviceId=deviceId, hist=hist)


# ========= API (IDA): horarios =========
@app.get("/api/schedule/<deviceId>")
def api_get_schedule(deviceId):
    conn = db()
    rows = conn.execute(
        "SELECT hour, minute FROM schedule WHERE deviceId=? ORDER BY hour, minute",
        (deviceId,),
    ).fetchall()
    conn.close()
    times = [{"hour": int(r["hour"]), "minute": int(r["minute"])} for r in rows]
    return jsonify({"times": times})


@app.post("/api/schedule/<deviceId>")
def api_set_schedule(deviceId):
    data = request.get_json(force=True, silent=False)

    if not isinstance(data, dict) or "times" not in data or not isinstance(data["times"], list):
        return jsonify({"ok": False, "error": "Body must be {times:[{hour,minute},...]}"}), 400

    times = data["times"]

    # estricto a 3 horarios (porque tu UI y ESP asumen 3)
    if len(times) != 3:
        return jsonify({"ok": False, "error": "Exactly 3 times are required"}), 400

    cleaned = []
    for t in times:
        if not isinstance(t, dict) or "hour" not in t or "minute" not in t:
            return jsonify({"ok": False, "error": "each time must have hour and minute"}), 400
        h = int(t["hour"])
        m = int(t["minute"])
        if h < 0 or h > 23 or m < 0 or m > 59:
            return jsonify({"ok": False, "error": "invalid hour/minute"}), 400
        cleaned.append((h, m))

    conn = db()
    conn.execute("DELETE FROM schedule WHERE deviceId=?", (deviceId,))
    for h, m in cleaned:
        conn.execute(
            "INSERT INTO schedule (deviceId, hour, minute) VALUES (?, ?, ?)",
            (deviceId, h, m),
        )
    conn.commit()
    conn.close()

    return jsonify({"ok": True})


# ========= API (VUELTA): confirmación =========
@app.post("/api/taken")
def api_taken():
    data = request.get_json(force=True, silent=False)

    if not isinstance(data, dict):
        return jsonify({"ok": False, "error": "Body must be JSON"}), 400

    device_id = data.get("deviceId")
    ts = data.get("timestamp", int(time.time()))

    if not device_id or not isinstance(device_id, str):
        return jsonify({"ok": False, "error": "deviceId is required"}), 400

    try:
        ts = int(ts)
    except Exception:
        return jsonify({"ok": False, "error": "timestamp must be int"}), 400

    conn = db()
    conn.execute(
        "INSERT INTO history (deviceId, timestamp) VALUES (?, ?)",
        (device_id, ts),
    )
    conn.commit()
    conn.close()

    return jsonify({"ok": True})


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "3000"))
    app.run(host="0.0.0.0", port=port)
