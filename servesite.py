from flask import Flask, send_file
import os

app = Flask(__name__)

@app.route("/")
def serve_dashboard():
    # Get the full path to the HTML file
    html_path = os.path.join(os.path.dirname(__file__), "frontend_dashboard.html")
    return send_file(html_path, mimetype="text/html")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
