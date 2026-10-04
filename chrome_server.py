from pathlib import Path
from fastapi import FastAPI
from fastapi.responses import HTMLResponse, FileResponse

ROOT = Path(__file__).resolve().parent
app = FastAPI(title="Perspectives Emploi ChromeOS")

@app.get("/", response_class=HTMLResponse)
def home():
    html = (ROOT / "index.html").read_text(encoding="utf-8")
    scripts = '<script src="/cv-metiers-compatibles.js?v=0.1"></script><script src="/app-compatible-loader.js?v=0.1"></script>'
    html = html.replace("</body>", scripts + "</body>")
    return HTMLResponse(html)

@app.get("/{path:path}")
def assets(path: str):
    target = (ROOT / path).resolve()
    if ROOT not in target.parents or not target.is_file():
        return FileResponse(ROOT / "index.html")
    return FileResponse(target)
