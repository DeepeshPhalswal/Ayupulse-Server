from flask import Flask, request, jsonify, render_template_string
from flask_cors import CORS
import time
import numpy as np
import os
from dotenv import load_dotenv

# Load .env file
load_dotenv()

HOST = os.getenv("FLASK_HOST", "127.0.0.1")
PORT = int(os.getenv("FLASK_PORT", 5000))
DEBUG = os.getenv("FLASK_DEBUG", "False").lower() == "true"


app = Flask(__name__)
CORS(app)

# Buffers for recent PPG samples (IR channel)
ppg_buffer = []
timestamps = []

# HTML dashboard with Chart.js
html_page = """
<!DOCTYPE html>
<html>
<head>
  <title>PPG Live Dashboard</title>
  <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
  <meta http-equiv="refresh" content="5">
  <style>
    body { font-family: Arial; margin: 2em; }
    h1 { color: #333; }
    table { border-collapse: collapse; width: 100%; margin-top: 1em; }
    th, td { border: 1px solid #ccc; padding: 6px; text-align: left; }
    #chartContainer { width: 100%; height: 300px; }
  </style>
</head>
<body>
  <h1>Live PPG Dashboard</h1>
  <p><strong>Heart Rate:</strong> {{ bpm }} BPM</p>

  <div id="chartContainer">
    <canvas id="ppgChart"></canvas>
  </div>

  <script>
    const labels = {{ times|safe }};
    const data = {
      labels: labels,
      datasets: [{
        label: 'IR PPG',
        data: {{ ir_values|safe }},
        borderColor: 'red',
        fill: false,
        pointRadius: 0
      }]
    };
    const config = {
      type: 'line',
      data: data,
      options: {
        animation: false,
        scales: {
          x: { display: false },
          y: { display: true }
        }
      }
    };
    new Chart(
      document.getElementById('ppgChart'),
      config
    );
  </script>

  <table>
    <tr><th>Time</th><th>IR</th><th>Red</th></tr>
    {% for entry in data %}
    <tr>
      <td>{{ entry['time'] }}</td>
      <td>{{ entry['ir'] }}</td>
      <td>{{ entry['red'] }}</td>
    </tr>
    {% endfor %}
  </table>
</body>
</html>
"""

@app.route('/data', methods=['POST'])
def receive_data():
    d = request.get_json()
    if d is None:
        return "Invalid", 400

    t = time.time()
    ir = d.get('ir', 0)
    red = d.get('red', 0)

    # Store for display table
    entry = {
        'time': time.strftime("%H:%M:%S"),
        'ir': ir,
        'red': red
    }

    # Append to buffers (limit length)
    ppg_buffer.append(ir)
    timestamps.append(t)
    if len(ppg_buffer) > 1000:  # ~10s @100Hz
        ppg_buffer.pop(0)
        timestamps.pop(0)

    # Also keep table data
    if 'table_buffer' not in globals():
        globals()['table_buffer'] = []
    globals()['table_buffer'].append(entry)
    globals()['table_buffer'] = globals()['table_buffer'][-50:]

    return jsonify({"status": "ok"})

@app.route('/')
def dashboard():
    bpm = compute_bpm()
    return render_template_string(
        html_page,
        data=globals().get('table_buffer', [])[::-1],
        bpm=bpm if bpm else "N/A",
        times=list(range(len(ppg_buffer))),
        ir_values=ppg_buffer
    )

def compute_bpm():
    """
    Very simple peak-based BPM estimation over last N seconds.
    """
    if len(ppg_buffer) < 50:
        return None

    # Convert lists to numpy arrays
    ir = np.array(ppg_buffer, dtype=float)
    t = np.array(timestamps, dtype=float)

    # High-pass filter (remove DC baseline)
    ir = ir - np.mean(ir)

    # Simple peak detection
    peaks = []
    threshold = np.std(ir) * 0.8
    for i in range(1, len(ir)-1):
        if ir[i] > ir[i-1] and ir[i] > ir[i+1] and ir[i] > threshold:
            peaks.append(t[i])

    if len(peaks) < 2:
        return None

    # Compute BPM from peak intervals
    intervals = np.diff(peaks)
    mean_interval = np.mean(intervals)
    bpm = 60.0 / mean_interval
    return round(bpm, 1)

# if __name__ == '__main__':
#     app.run(host='0.0.0.0', port=5000, debug=True)

if __name__ == '__main__':
    app.run(host=HOST, port=PORT, debug=DEBUG)
