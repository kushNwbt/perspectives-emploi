from pathlib import Path
from fastapi import FastAPI
from fastapi.responses import HTMLResponse, FileResponse

ROOT = Path(__file__).resolve().parent
app = FastAPI(title="Perspectives Emploi ChromeOS")

@app.get("/", response_class=HTMLResponse)
def home():
    # index.html owns application script loading. Do not inject a second navigation controller.
    html = (ROOT / "index.html").read_text(encoding="utf-8")
    return HTMLResponse(html, headers={"Cache-Control": "no-store, max-age=0"})

@app.get("/{path:path}")
def assets(path: str):
    target = (ROOT / path).resolve()
    if ROOT not in target.parents or not target.is_file():
        return FileResponse(ROOT / "index.html", headers={"Cache-Control": "no-store, max-age=0"})
    return FileResponse(target, headers={"Cache-Control": "no-store, max-age=0"})
