const form = document.getElementById("scan-form");
const input = document.getElementById("url-input");
const button = document.getElementById("scan-button");
const errorEl = document.getElementById("error");
const resultEl = document.getElementById("result");
const urlEl = document.getElementById("target-url");
const statusEl = document.getElementById("status");
const safeEl = document.getElementById("safe-score");
const phishEl = document.getElementById("phish-score");

function showError(msg) {
  errorEl.hidden = false;
  errorEl.textContent = msg;
  resultEl.hidden = true;
}

function clearError() {
  errorEl.hidden = true;
  errorEl.textContent = "";
}

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  clearError();
  button.disabled = true;
  button.textContent = "Analyzing...";

  try {
    const resp = await fetch("/api/predict", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ url: input.value.trim() })
    });
    let data = {};
    const contentType = resp.headers.get("content-type") || "";
    if (contentType.includes("application/json")) {
      try {
        data = await resp.json();
      } catch (_err) {
        data = {};
      }
    }

    if (!resp.ok || !data.ok) {
      showError(data.error || "Prediction failed.");
      return;
    }

    const safe = (data.safe_probability * 100).toFixed(2);
    const phish = (data.phishing_probability * 100).toFixed(2);

    urlEl.href = data.url;
    urlEl.textContent = data.url;
    statusEl.textContent = data.is_safe
      ? "Result: likely safe"
      : "Result: likely phishing";
    safeEl.textContent = `Safe probability: ${safe}%`;
    phishEl.textContent = `Phishing probability: ${phish}%`;
    resultEl.hidden = false;
  } catch (_err) {
    showError("Backend is unreachable.");
  } finally {
    button.disabled = false;
    button.textContent = "Analyze";
  }
});
