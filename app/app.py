from flask import Flask, jsonify, render_template_string
from prometheus_flask_exporter import PrometheusMetrics
import requests

app = Flask(__name__)
metrics = PrometheusMetrics(app)  # Exposes /metrics for Prometheus

# Simple HTML page that uses browser GPS and sends it to /location/update
HTML = """
<!DOCTYPE html>
<html>
<head><title>Classroom GPS</title></head>
<body>
  <h2>Classroom GPS Locator</h2>
  <button onclick="shareLocation()">Share My Location</button>
  <p id="status">Click the button to share location.</p>
  <script>
    function shareLocation() {
      navigator.geolocation.getCurrentPosition(pos => {
        fetch('/location/update', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            latitude: pos.coords.latitude,
            longitude: pos.coords.longitude,
            accuracy: pos.coords.accuracy
          })
        }).then(() => {
          document.getElementById('status').innerText = 'Location shared successfully!';
        });
      }, err => {
        // Fallback: use IP-based location if browser GPS is denied
        fetch('/location/update-by-ip', { method: 'POST' })
          .then(() => {
            document.getElementById('status').innerText = 'Used IP-based location as fallback.';
          });
      });
    }
  </script>
</body>
</html>
"""

current_location = {}

@app.route('/')
def index():
    return render_template_string(HTML)


@app.route('/location/update', methods=['POST'])
def update_location():
    """Receives GPS coords from the browser."""
    from flask import request
    global current_location
    current_location = request.get_json()
    current_location["source"] = "Browser GPS"
    return jsonify({"status": "updated"})


@app.route('/location/update-by-ip', methods=['POST'])
def update_by_ip():
    """Fallback: fetch location using the server's public IP."""
    global current_location
    response = requests.get("http://ip-api.com/json/", timeout=5)
    data = response.json()
    current_location = {
        "latitude": data.get("lat"),
        "longitude": data.get("lon"),
        "city": data.get("city"),
        "accuracy": "city-level",
        "source": "IP Geolocation (fallback)"
    }
    return jsonify({"status": "updated"})


@app.route('/location', methods=['GET'])
def get_location():
    """Returns the current classroom location."""
    if not current_location:
        return jsonify({"error": "No location available yet. Visit / to share location."}), 404
    return jsonify(current_location)


@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint for Kubernetes probes."""
    return jsonify({"status": "healthy"})


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
