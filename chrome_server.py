from pathlib import Path
from fastapi import FastAPI
from fastapi.responses import HTMLResponse, FileResponse

ROOT = Path(__file__).resolve().parent
app = FastAPI(title="Perspectives Emploi ChromeOS")

@app.get("/", response_class=HTMLResponse)
def home():
    html = (ROOT / "index.html").read_text(encoding="utf-8")
    # index.html already loads the main scripts. Do not inject duplicate copies.
    # Add only the deterministic navigation hotfix; version is bumped to defeat browser cache.
    html = html.replace("</body>", '<script src="/navigation-hotfix.js?v=20261005-4"></script></body>')
    return HTMLResponse(html, headers={"Cache-Control": "no-store, max-age=0"})

@app.get("/{path:path}")
def assets(path: str):
    target = (ROOT / path).resolve()
    if ROOT not in target.parents or not target.is_file():
        return FileResponse(ROOT / "index.html", headers={"Cache-Control": "no-store, max-age=0"})
    return FileResponse(target, headers={"Cache-Control": "no-store, max-age=0"})
