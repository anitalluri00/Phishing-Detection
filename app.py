"""
Compatibility entrypoint.

Use backend/app.py for the main application.
"""

from backend.app import app


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)
