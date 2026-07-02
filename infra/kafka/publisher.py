import json
import os
import threading
import time
import uuid

from flask import Flask, jsonify, render_template_string
from kafka import KafkaProducer
from kafka.errors import NoBrokersAvailable


BOOTSTRAP = os.environ.get('KAFKA_BOOTSTRAP_SERVERS', 'kafka:9092')
TOPIC = os.environ.get('KAFKA_TOPIC', 'load.test')
PORT = int(os.environ.get('LOAD_PUBLISHER_PORT', '8081'))

state = {
    'rate': 10,
    'running': True,
    'sent': 0,
}
lock = threading.Lock()
producer = None

PAGE = """
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>Cozy Coza Kafka Load</title>
  <style>
    body { font-family: system-ui, sans-serif; max-width: 640px; margin: 2rem auto; padding: 0 1rem; }
    h1 { margin-bottom: 0.25rem; }
    p { color: #555; }
    .card { border: 1px solid #ddd; border-radius: 12px; padding: 1.25rem; margin-top: 1rem; }
    input[type=range] { width: 100%; }
    button { margin-top: 1rem; padding: 0.6rem 1rem; border: 0; border-radius: 8px; background: #c45d3a; color: #fff; cursor: pointer; }
    .stats { margin-top: 1rem; font-size: 0.95rem; }
    code { background: #f4f4f4; padding: 0.1rem 0.35rem; border-radius: 4px; }
  </style>
</head>
<body>
  <h1>Kafka load publisher</h1>
  <p>Topic: <code>{{ topic }}</code> · bootstrap: <code>{{ bootstrap }}</code></p>
  <div class="card">
    <label for="rate">Messages per second: <strong id="rateLabel">{{ rate }}</strong></label>
    <input id="rate" type="range" min="1" max="500" value="{{ rate }}">
    <button onclick="applyRate()">Apply settings</button>
    <div class="stats">
      <div>Total sent: <strong id="sent">{{ sent }}</strong></div>
      <div>Open <a href="http://localhost:8080" target="_blank">Kafka UI</a> to inspect partitions and lag.</div>
    </div>
  </div>
  <script>
    const slider = document.getElementById('rate');
    const rateLabel = document.getElementById('rateLabel');
    slider.addEventListener('input', () => rateLabel.textContent = slider.value);
    async function applyRate() {
      const response = await fetch('/apply', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({rate: Number(slider.value)}),
      });
      const data = await response.json();
      document.getElementById('sent').textContent = data.sent;
      alert('Rate updated to ' + data.rate + ' msg/s');
    }
    setInterval(async () => {
      const response = await fetch('/stats');
      const data = await response.json();
      document.getElementById('sent').textContent = data.sent;
    }, 2000);
  </script>
</body>
</html>
"""


def wait_for_kafka():
    global producer
    while producer is None:
        try:
            producer = KafkaProducer(
                bootstrap_servers=BOOTSTRAP,
                value_serializer=lambda v: json.dumps(v).encode('utf-8'),
            )
        except NoBrokersAvailable:
            print('Waiting for Kafka...')
            time.sleep(3)


def publisher_loop():
    wait_for_kafka()
    while True:
        with lock:
            rate = state['rate']
            running = state['running']
        if not running:
            time.sleep(0.5)
            continue
        interval = 1.0 / max(rate, 1)
        payload = {
            'event': 'load.test',
            'id': str(uuid.uuid4()),
            'timestamp': time.time(),
        }
        producer.send(TOPIC, value=payload, key=str(rate).encode('utf-8'))
        with lock:
            state['sent'] += 1
        time.sleep(interval)


app = Flask(__name__)


@app.route('/')
def index():
    with lock:
        return render_template_string(
            PAGE,
            topic=TOPIC,
            bootstrap=BOOTSTRAP,
            rate=state['rate'],
            sent=state['sent'],
        )


@app.route('/stats')
def stats():
    with lock:
        return jsonify(rate=state['rate'], sent=state['sent'])


@app.route('/apply', methods=['POST'])
def apply():
    from flask import request

    data = request.get_json(silent=True) or {}
    rate = int(data.get('rate', state['rate']))
    rate = max(1, min(rate, 500))
    with lock:
        state['rate'] = rate
        sent = state['sent']
    return jsonify(rate=rate, sent=sent)


def main():
    thread = threading.Thread(target=publisher_loop, daemon=True)
    thread.start()
    app.run(host='0.0.0.0', port=PORT)


if __name__ == '__main__':
    main()
