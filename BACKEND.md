# Backend Perspectives Emploi

API FastAPI destinée au site Perspectives Emploi.

## Démarrage
`pip install -r requirements.txt`
`uvicorn server:app --reload`

Variable d'environnement :
`ALLOWED_ORIGINS=https://kushnwbt.github.io`

Endpoints :
- `GET /health`
- `POST /api/cv/analyse` avec un champ multipart `cv`

Le CV est traité en mémoire et n'est pas enregistré par ce code.
