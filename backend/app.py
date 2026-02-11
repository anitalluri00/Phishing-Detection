from __future__ import annotations

import ipaddress
import socket
from pathlib import Path
from urllib.parse import urlparse

import joblib
import numpy as np
from flask import Flask, jsonify, render_template, request

try:
    from .feature_extraction import extract_features
except ImportError:
    from feature_extraction import extract_features


BASE_DIR = Path(__file__).resolve().parent
MODEL_PATH = BASE_DIR / "model" / "model.pkl"

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 16 * 1024

ALLOWED_SCHEMES = {"http", "https"}
BLOCKED_HOSTS = {"localhost"}

MODEL_BUNDLE = None
MODEL_LOAD_ERROR = ""


def _is_private_ip(value: str) -> bool:
    try:
        ip = ipaddress.ip_address(value)
        return (
            ip.is_private
            or ip.is_loopback
            or ip.is_link_local
            or ip.is_reserved
            or ip.is_multicast
        )
    except ValueError:
        return False


def normalize_and_validate_url(raw_url) -> tuple[str, str]:
    if raw_url is None:
        raw_url = ""
    if not isinstance(raw_url, str):
        raw_url = str(raw_url)
    raw_url = raw_url.strip()

    if not raw_url:
        return "", "Please enter a URL."

    parsed = urlparse(raw_url)
    if not parsed.scheme and not parsed.netloc and parsed.path:
        raw_url = f"http://{raw_url}"
        parsed = urlparse(raw_url)

    if parsed.scheme.lower() not in ALLOWED_SCHEMES:
        return "", "Only http:// or https:// URLs are allowed."

    hostname = parsed.hostname
    if not hostname:
        return "", "Invalid URL."

    hostname = hostname.lower()
    if hostname in BLOCKED_HOSTS or hostname.endswith(".local"):
        return "", "Local network URLs are not allowed."

    if _is_private_ip(hostname):
        return "", "Local network URLs are not allowed."

    try:
        infos = socket.getaddrinfo(hostname, None)
    except socket.gaierror:
        # In restricted environments DNS can be unavailable; keep validation strict
        # for known local targets but allow unresolved public hosts to proceed.
        return raw_url, ""

    for info in infos:
        ip = info[4][0]
        if _is_private_ip(ip):
            return "", "Local network URLs are not allowed."

    return raw_url, ""


def _load_model():
    global MODEL_BUNDLE
    global MODEL_LOAD_ERROR

    if MODEL_BUNDLE is None and not MODEL_LOAD_ERROR:
        try:
            MODEL_BUNDLE = joblib.load(MODEL_PATH)
        except Exception as exc:
            MODEL_LOAD_ERROR = str(exc)
    return MODEL_BUNDLE


def predict_url(url: str) -> tuple[float, float]:
    model_bundle = _load_model()
    if model_bundle is None:
        raise RuntimeError("Prediction model is unavailable.")

    model = model_bundle["model"] if isinstance(model_bundle, dict) else model_bundle
    features = np.array(extract_features(url), dtype=float).reshape(1, -1)

    probs = model.predict_proba(features)[0]
    classes = list(model.classes_)
    prob_legit = float(probs[classes.index(0)]) if 0 in classes else float(probs[0])
    prob_phish = float(probs[classes.index(1)]) if 1 in classes else float(probs[-1])
    return prob_legit, prob_phish


@app.errorhandler(413)
def payload_too_large(_error):
    if request.path.startswith("/api/"):
        return jsonify({"ok": False, "error": "Request payload is too large."}), 413
    return render_template("index.html", xx=-1, url="", error="Request payload is too large."), 413


@app.route("/health", methods=["GET"])
def health():
    model = _load_model()
    return jsonify({"status": "ok", "model_loaded": bool(model)}), 200


@app.route("/api/predict", methods=["POST"])
def predict_api():
    payload = request.get_json(silent=True) or {}
    raw_url = payload.get("url", "")
    url, error = normalize_and_validate_url(raw_url)
    if error:
        return jsonify({"ok": False, "error": error}), 400

    try:
        safe_probability, phishing_probability = predict_url(url)
    except RuntimeError:
        return jsonify({"ok": False, "error": "Prediction model is unavailable."}), 503

    return jsonify(
        {
            "ok": True,
            "url": url,
            "safe_probability": safe_probability,
            "phishing_probability": phishing_probability,
            "is_safe": safe_probability >= 0.5,
        }
    )


@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        raw_url = request.form.get("url", "")
        url, error = normalize_and_validate_url(raw_url)
        if error:
            return render_template("index.html", xx=-1, url="", error=error)
        try:
            safe_probability, _ = predict_url(url)
        except RuntimeError:
            return render_template("index.html", xx=-1, url="", error="Prediction model is unavailable.")
        return render_template("index.html", xx=round(safe_probability, 2), url=url, error="")

    return render_template("index.html", xx=-1, url="", error="")


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)
