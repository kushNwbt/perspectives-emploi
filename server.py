import io
import os
import re
from typing import Dict, List

from fastapi import FastAPI, File, HTTPException, UploadFile, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import httpx
import time
import asyncio

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

def extract_cv_skill_evidence(text: str) -> List[str]:
    """Conserve des indices courts réellement présents dans le CV, sans renvoyer le texte brut."""
    lines = [re.sub(r"\\s+", " ", line).strip(" •·▪-–—\\t") for line in text.splitlines()]
    lines = [line for line in lines if 3 <= len(line) <= 140]
    section_words = ("compétence", "competence", "savoir-faire", "skills")
    stop_words = ("formation", "diplôme", "diplome", "langue", "centre d'intérêt", "profil", "coordonnée")
    action_words = (
        "accompagn", "accueill", "orient", "conseill", "anim", "organis", "coordonn",
        "recrut", "prospect", "analys", "évalu", "evalu", "gér", "ger", "suiv",
        "inform", "renseign", "développ", "developp", "pilot", "prépar", "prepar",
        "condu", "réalis", "realis", "cré", "cre", "mettr", "assur"
    )
    collected = []
    in_skills = False

    def add_item(value: str):
        item = value.strip(" •·▪-–—\\t")
        if 3 <= len(item) <= 110 and item.lower() not in {x.lower() for x in collected}:
            collected.append(item)

    for line in lines:
        low = line.lower().rstrip(":")
        if any(word in low for word in section_words) and len(line) <= 60:
            in_skills = True
            continue
        if in_skills and any(low.startswith(word) for word in stop_words):
            in_skills = False

        if in_skills:
            for part in re.split(r"[;,|•]", line):
                add_item(part)
        elif any(stem in low for stem in action_words):
            # Une mission d'expérience peut constituer un indice de compétence,
            # même si le CV n'a pas de rubrique explicitement nommée « Compétences ».
            add_item(line)

    return collected[:120]


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
    # Compléter le diagnostic avec des conseils utiles même lorsque les rubriques
    # principales sont détectées. Ces conseils restent pédagogiques et ne prétendent
    # pas évaluer la qualité réelle du contenu sans preuve textuelle suffisante.
    if sections["Expériences"] and len(compact) < 1400:
        priorities.append({"niveau":"À améliorer","titre":"Détailler les expériences","conseil":"Vérifiez que les expériences principales précisent les missions réalisées, le contexte et, lorsque c’est pertinent, des résultats concrets."})
    if sections["Compétences"]:
        priorities.append({"niveau":"À améliorer","titre":"Relier les compétences aux expériences","conseil":"Associez les compétences importantes à des expériences ou réalisations qui permettent de les illustrer concrètement."})
    if sections["Formation"]:
        priorities.append({"niveau":"Bon","titre":"Valoriser les formations utiles","conseil":"Conservez en priorité les diplômes, titres et certifications utiles au projet professionnel visé."})
    if sections["Coordonnées"]:
        priorities.append({"niveau":"Bon","titre":"Coordonnées repérées","conseil":"Les coordonnées sont détectées. Vérifiez qu’elles restent simples à repérer et à jour."})
    else:
        priorities.append({"niveau":"Prioritaire","titre":"Rendre les coordonnées visibles","conseil":"Ajoutez au minimum un moyen de contact professionnel clairement identifiable."})
    if len(compact) > 2600:
        priorities.append({"niveau":"À améliorer","titre":"Alléger les informations","conseil":"Le CV est assez dense. Hiérarchisez les informations et gardez en priorité celles qui servent le projet visé."})
    elif len(compact) < 700:
        priorities.append({"niveau":"À améliorer","titre":"Enrichir le contenu utile","conseil":"Le contenu détecté est court. Vérifiez que les expériences, missions et compétences importantes sont suffisamment détaillées."})
    if not priorities:
        priorities.append({"niveau":"Bon","titre":"Structure principale repérée","conseil":"Conservez les rubriques clairement identifiables et vérifiez que chaque expérience décrit des missions concrètes."})

    return {
        "score": score,
        "statut": "Bon" if score >= 75 else "À renforcer" if score >= 55 else "Prioritaire",
        "sections": sections,
        "priorites": priorities[:6],
        "meta": {"caracteres": len(text), "mots": len(text.split())},
        "avertissement": "Diagnostic pédagogique fondé sur les éléments détectés dans le CV. Il ne garantit pas le passage d’un ATS ni un recrutement.",
        "competences_cv": extract_cv_skill_evidence(text)
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


FT_TOKEN_CACHE = {"token": None, "expires_at": 0}
FT_LAST_CALL = 0.0
FT_CALL_LOCK = None
ROME_COMP_CACHE = {}

async def france_travail_token() -> str:
    client_id = os.getenv("FRANCE_TRAVAIL_CLIENT_ID", "").strip()
    client_secret = os.getenv("FRANCE_TRAVAIL_CLIENT_SECRET", "").strip()
    if not client_id or not client_secret:
        raise HTTPException(503, "Les identifiants France Travail ne sont pas configurés sur le serveur.")
    now = time.time()
    if FT_TOKEN_CACHE["token"] and FT_TOKEN_CACHE["expires_at"] > now + 60:
        return FT_TOKEN_CACHE["token"]
    url = "https://entreprise.francetravail.fr/connexion/oauth2/access_token?realm=/partenaire"
    data = {
        "grant_type": "client_credentials",
        "client_id": client_id,
        "client_secret": client_secret,
        "scope": "nomenclatureRome api_rome-metiersv1 api_rome-competencesv1 api_rome-fiches-metiersv1 o2dsoffre api_offresdemploiv2",
    }
    async with httpx.AsyncClient(timeout=15) as client:
        response = await client.post(url, data=data)
    if response.status_code >= 400:
        raise HTTPException(502, "Connexion à France Travail impossible.")
    payload = response.json()
    token = payload.get("access_token")
    if not token:
        raise HTTPException(502, "France Travail n’a pas retourné de jeton d’accès.")
    FT_TOKEN_CACHE["token"] = token
    FT_TOKEN_CACHE["expires_at"] = now + int(payload.get("expires_in", 1200))
    return token

def normalize_rome_jobs(payload):
    source = payload
    if isinstance(payload, dict):
        for key in ("resultats", "results", "metiers", "items"):
            if isinstance(payload.get(key), list):
                source = payload[key]
                break
    if not isinstance(source, list):
        return []
    out, seen = [], set()
    for item in source:
        if not isinstance(item, dict):
            continue
        code = item.get("code") or item.get("codeRome") or item.get("code_rome") or ""
        label = item.get("libelle") or item.get("libelleMetier") or item.get("label") or item.get("intitule") or ""
        if isinstance(item.get("metier"), dict):
            code = code or item["metier"].get("code", "")
            label = label or item["metier"].get("libelle", "")
        code, label = str(code).strip(), str(label).strip()
        key = (code, label.lower())
        if label and key not in seen:
            seen.add(key)
            out.append({"code": code, "libelle": label})
    return out[:20]

@app.get("/api/rome/metiers")
async def rome_metiers(q: str = Query(..., min_length=2, max_length=100)):
    token = await france_travail_token()
    url = "https://api.francetravail.io/partenaire/rome-metiers/v1/metiers/metier/requete"
    headers = {"Authorization": f"Bearer {token}", "Accept": "application/json"}
    # L'API ROME accepte une requête métier ; on garde l'appel côté serveur pour ne jamais exposer le secret.
    async with httpx.AsyncClient(timeout=15) as client:
        response = await client.get(url, params={"q": q}, headers=headers)
        if response.status_code in (400, 404, 422):
            # Compatibilité avec les variantes de paramètre de recherche exposées par le service.
            response = await client.get(url, params={"libelle": q}, headers=headers)
    if response.status_code == 429:
        raise HTTPException(429, "Le service ROME est momentanément très sollicité.")
    if response.status_code >= 400:
        raise HTTPException(502, "La recherche ROME est momentanément indisponible.")
    return normalize_rome_jobs(response.json())


def normalize_rome_competences(payload):
    source = payload
    if isinstance(payload, dict):
        for key in ("competences", "resultats", "results", "items"):
            if isinstance(payload.get(key), list):
                source = payload[key]
                break
    if not isinstance(source, list):
        return []
    out, seen = [], set()
    for item in source:
        if not isinstance(item, dict):
            continue
        label = item.get("libelle") or item.get("libelleCompetence") or item.get("label") or item.get("intitule") or ""
        code = item.get("code") or item.get("codeCompetence") or ""
        category = item.get("type") or item.get("categorie") or item.get("typeCompetence") or "Compétence ROME"
        label = str(label).strip()
        if label and label.lower() not in seen:
            seen.add(label.lower())
            out.append({"code": str(code).strip(), "libelle": label, "categorie": str(category).strip()})
    return out[:60]

@app.get("/api/rome/competences")
async def rome_competences(code_rome: str = Query(..., min_length=5, max_length=5)):
    global FT_LAST_CALL, FT_CALL_LOCK
    code_rome = code_rome.upper().strip()

    cached = ROME_COMP_CACHE.get(code_rome)
    if cached and cached["expires_at"] > time.time():
        return cached["data"]

    token = await france_travail_token()
    headers = {"Authorization": f"Bearer {token}", "Accept": "application/json"}
    url = f"https://api.francetravail.io/partenaire/rome-fiches-metiers/v1/fiches-rome/fiche-metier/{code_rome}"
    params = {
        "champs": (
            "code,"
            "groupescompetencesmobilisees(competences(libelle,code),enjeu(libelle,code)),"
            "groupessavoirs(savoirs(libelle,code),categoriesavoirs(libelle,code)),"
            "metier(libelle,code)"
        )
    }

    if FT_CALL_LOCK is None:
        FT_CALL_LOCK = asyncio.Lock()

    async with FT_CALL_LOCK:
        wait = 1.10 - (time.monotonic() - FT_LAST_CALL)
        if wait > 0:
            await asyncio.sleep(wait)
        async with httpx.AsyncClient(timeout=15) as client:
            response = await client.get(url, params=params, headers=headers)
        FT_LAST_CALL = time.monotonic()

    if response.status_code == 429:
        raise HTTPException(429, "Le service ROME est momentanément très sollicité.")
    if response.status_code == 404:
        raise HTTPException(404, "Fiche métier ROME introuvable.")
    if response.status_code >= 400:
        raise HTTPException(502, "La fiche métier ROME est momentanément indisponible.")

    payload = response.json()
    items, seen = [], set()
    savoir_faire, savoirs = [], []

    for group in payload.get("groupesCompetencesMobilisees", []) or []:
        enjeu = group.get("enjeu") or {}
        category = enjeu.get("libelle") or "Compétence ROME"
        for item in group.get("competences", []) or []:
            label = str(item.get("libelle") or "").strip()
            code = str(item.get("code") or "").strip()
            if label and label.lower() not in seen:
                seen.add(label.lower())
                entry={"code": code, "libelle": label, "categorie": category, "type": "savoir_faire"}
                items.append(entry)
                savoir_faire.append(entry)

    for group in payload.get("groupesSavoirs", []) or []:
        category_info = group.get("categorieSavoirs") or {}
        category = category_info.get("libelle") or "Savoir"
        for item in group.get("savoirs", []) or []:
            label = str(item.get("libelle") or "").strip()
            code = str(item.get("code") or "").strip()
            if label and label.lower() not in seen:
                seen.add(label.lower())
                entry={"code": code, "libelle": label, "categorie": category, "type": "savoir"}
                items.append(entry)
                savoirs.append(entry)

    data = {
        "codeRome": code_rome,
        "metier": payload.get("metier") or {"code": code_rome},
        "competences": items[:80],
        "savoirFaire": savoir_faire[:80],
        "savoirs": savoirs[:80],
    }
    ROME_COMP_CACHE[code_rome] = {"data": data, "expires_at": time.time() + 21600}
    return data


@app.get("/api/offres")
async def offres_emploi(code_rome: str = Query(..., min_length=5, max_length=5), commune: str = Query("", max_length=100), type_contrat: str = Query("", max_length=10)):
    token = await france_travail_token()
    headers = {"Authorization": f"Bearer {token}", "Accept": "application/json"}
    params = {"codeROME": code_rome.upper().strip(), "range": "0-19"}
    if commune.strip():
        params["commune"] = commune.strip()
    if type_contrat.strip():
        params["typeContrat"] = type_contrat.strip().upper()
    url = "https://api.francetravail.io/partenaire/offresdemploi/v2/offres/search"
    async with httpx.AsyncClient(timeout=15) as client:
        response = await client.get(url, params=params, headers=headers)
    if response.status_code == 429:
        raise HTTPException(429, "Le service Offres d’emploi est momentanément très sollicité.")
    if response.status_code >= 400:
        raise HTTPException(502, "Les offres France Travail sont momentanément indisponibles.")
    payload = response.json()
    results = payload.get("resultats", []) if isinstance(payload, dict) else []
    offers = []
    for item in results[:20]:
        lieu = item.get("lieuTravail") or {}
        entreprise = item.get("entreprise") or {}
        offers.append({
            "id": item.get("id", ""),
            "intitule": item.get("intitule", ""),
            "entreprise": entreprise.get("nom", ""),
            "lieu": lieu.get("libelle", ""),
            "typeContrat": item.get("typeContratLibelle") or item.get("typeContrat", ""),
            "description": item.get("description", ""),
            "competences": [c.get("libelle", "") for c in (item.get("competences") or []) if isinstance(c, dict) and c.get("libelle")],
            "experience": item.get("experienceLibelle") or item.get("experienceExige", ""),
            "url": item.get("origineOffre", {}).get("urlOrigine", "") or f"https://candidat.francetravail.fr/offres/recherche/detail/{item.get('id','')}",
        })
    return {"codeRome": code_rome.upper().strip(), "offres": offers}
