import io
import os
import re
from typing import Dict, List

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

app = FastAPI(title="Perspectives Emploi API", version="0.1.0")

origins = [x.strip() for x in os.getenv(
    "ALLOWED_ORIGINS",
    "https://kushnwbt.github.io"
).split(",") if x.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

MAX_SIZE = 10 * 1024 * 1024
ALLOWED = {"pdf", "docx", "txt"}

def extract_text(name: str, raw: bytes) -> str:
    ext = name.rsplit(".", 1)[-1].lower() if "." in name else ""
    if ext == "txt":
        return raw.decode("utf-8", errors="ignore")
    if ext == "pdf":
        from pypdf import PdfReader
        reader = PdfReader(io.BytesIO(raw))
        return "\n".join((p.extract_text() or "") for p in reader.pages)
    if ext == "docx":
        from docx import Document
        doc = Document(io.BytesIO(raw))
        return "\n".join(p.text for p in doc.paragraphs)
    raise HTTPException(400, "Format non accepté")

def has_any(text: str, words: List[str]) -> bool:
    t = text.lower()
    return any(w.lower() in t for w in words)

def analyse_cv(text: str) -> Dict:
    compact = re.sub(r"\s+", " ", text).strip()
    sections = {
        "Expériences": has_any(text, ["expérience", "experiences", "parcours professionnel", "emploi"]),
        "Compétences": has_any(text, ["compétence", "competences", "savoir-faire", "skills"]),
        "Formation": has_any(text, ["formation", "diplôme", "diplome", "certification"]),
        "Coordonnées": bool(re.search(r"[\w.+-]+@[\w.-]+\.\w+", text)) or bool(re.search(r"(?:\+33|0)[1-9](?:[ .-]?\d{2}){4}", text)),
    }
    score = 35
    score += sum(10 for ok in sections.values() if ok)
    if len(compact) > 700: score += 10
    if len(compact) > 1400: score += 10
    score = min(score, 95)

    priorities = []
    if not sections["Expériences"]:
        priorities.append({"niveau":"Prioritaire","titre":"Clarifier les expériences","conseil":"Ajoutez une rubrique Expériences clairement identifiable avec les postes, structures et dates."})
    if not sections["Compétences"]:
        priorities.append({"niveau":"À améliorer","titre":"Rendre les compétences visibles","conseil":"Ajoutez une rubrique Compétences avec des savoir-faire réellement maîtrisés et vérifiables."})
    if not sections["Formation"]:
        priorities.append({"niveau":"À améliorer","titre":"Structurer la formation","conseil":"Présentez les diplômes, titres ou certifications avec leur intitulé et leur date."})
    if not priorities:
        priorities.append({"niveau":"Bon","titre":"Structure principale repérée","conseil":"Conservez les rubriques clairement identifiables et vérifiez que chaque expérience décrit des missions concrètes."})

    return {
        "score": score,
        "statut": "Bon" if score >= 75 else "À renforcer" if score >= 55 else "Prioritaire",
        "sections": sections,
        "priorites": priorities[:3],
        "meta": {"caracteres": len(text), "mots": len(text.split())},
        "avertissement": "Diagnostic pédagogique fondé sur les éléments détectés dans le CV. Il ne garantit pas le passage d’un ATS ni un recrutement."
    }

@app.get("/health")
def health():
    return {"status": "ok", "service": "Perspectives Emploi API"}

@app.post("/api/cv/analyse")
async def cv_analyse(cv: UploadFile = File(...)):
    name = cv.filename or "cv"
    ext = name.rsplit(".", 1)[-1].lower() if "." in name else ""
    if ext not in ALLOWED:
        raise HTTPException(400, "Format non accepté. PDF, DOCX ou TXT uniquement.")
    raw = await cv.read(MAX_SIZE + 1)
    if len(raw) > MAX_SIZE:
        raise HTTPException(413, "Le fichier dépasse 10 Mo.")
    try:
        text = extract_text(name, raw)
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(422, "Impossible de lire ce document.")
    if len(text.strip()) < 40:
        raise HTTPException(422, "Le document ne contient pas assez de texte exploitable.")
    return analyse_cv(text)
