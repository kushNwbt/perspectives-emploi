from pathlib import Path
from fastapi import FastAPI
from fastapi.responses import HTMLResponse, FileResponse

ROOT = Path(__file__).resolve().parent
app = FastAPI(title="Perspectives Emploi ChromeOS")

@app.get("/", response_class=HTMLResponse)
def home():
    html = (ROOT / "index.html").read_text(encoding="utf-8")
    # Load the mutation guard before the guided loader and force a fresh asset
    # version so Chromium/Railway never keeps an older interaction fix cached.
    marker = '<script src="app-compatible-loader.js?v=1.2.0"></script>'
    guarded = '<script src="mutation-guard.js?v=20261005-2"></script><script src="app-compatible-loader.js?v=20261005-2"></script><script src="multi-job-selection.js?v=20261005-2"></script>'
    html = html.replace(marker, guarded)
    return HTMLResponse(html, headers={"Cache-Control": "no-store, max-age=0"})

@app.get("/{path:path}")
def assets(path: str):
    target = (ROOT / path).resolve()
    if ROOT not in target.parents or not target.is_file():
        return FileResponse(ROOT / "index.html", headers={"Cache-Control": "no-store, max-age=0"})
    return FileResponse(target, headers={"Cache-Control": "no-store, max-age=0"})
