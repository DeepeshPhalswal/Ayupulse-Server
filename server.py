from flask import Flask, request, jsonify, send_file
import os
import csv
from datetime import datetime
from dotenv import load_dotenv

# ---------------------------------------
# Load environment variables from .env
# ---------------------------------------
load_dotenv()

CSV_FILE = os.getenv("CSV_FILE", "sensors.csv")
PORT = int(os.getenv("PORT", 5000))
DEBUG = os.getenv("DEBUG", "False").lower() == "true"

FIELDNAMES = ["timestamp", "human_time", "mac", "ir1", "ir2", "ir3", "spo2", "temperature"]

app = Flask(__name__)

def ensure_csv():
    if not os.path.exists(CSV_FILE):
        with open(CSV_FILE, mode="w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
            writer.writeheader()

@app.route("/download", methods=["GET"])
def download_csv():
    if not os.path.exists(CSV_FILE):
        return {"status": "error", "message": "CSV file not found"}, 404

    return send_file(
        CSV_FILE,
        mimetype="text/csv",
        as_attachment=True,
        download_name="sensors.csv"
    )

@app.route("/data", methods=["POST"])
def data():
    try:
        payload = request.get_json(force=True)
    except Exception as e:
        return jsonify({"status": "error", "message": "Invalid JSON", "error": str(e)}), 400

    ts = payload.get("timestamp")
    if ts is None:
        ts = int(datetime.utcnow().timestamp())
    human_time = datetime.utcfromtimestamp(int(ts)).isoformat() + "Z"

    # -----------------------------------
    #   Divide PPG values by 1000 safely
    # -----------------------------------
    def safe_div(v):
        try:
            return float(v) / 1000
        except:
            return v

    ir1 = safe_div(payload.get("ir1", ""))
    ir2 = safe_div(payload.get("ir2", ""))
    ir3 = safe_div(payload.get("ir3", ""))

    row = {
        "timestamp": ts,
        "human_time": human_time,
        "mac": payload.get("mac", ""),
        "ir1": ir1,
        "ir2": ir2,
        "ir3": ir3,
        "spo2": payload.get("spo2", ""),
        "temperature": (payload.get("temperature", ""))+69
    }

    ensure_csv()
    with open(CSV_FILE, mode="a", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
        writer.writerow(row)

    return jsonify({"status": "ok", "received": row}), 200


if __name__ == "__main__":
    print(f"Server starting on port {PORT}...")
    print(f"Saving data to '{CSV_FILE}'")
    app.run(host="0.0.0.0", port=PORT, debug=DEBUG)
