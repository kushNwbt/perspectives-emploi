"""ChromeOS/web entrypoint for Perspectives Emploi V6.24.5.
Keeps the V6.24.5 API intact and serves the exact desktop web assets from the same origin.
"""
from fastapi.staticfiles import StaticFiles
from server import app

# API routes are registered by server.py first. The catch-all static mount therefore
# serves index.html/style.css/app.js without shadowing /api/* and /health.
app.mount("/", StaticFiles(directory=".", html=True), name="perspectives-ui")
