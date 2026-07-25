# Kitchen Ledger

Local-first web app for cataloging scanned handwritten recipes. Drop scans into an inbox folder, OCR-assist transcription, correct ingredients and directions beside the image, and organize with multi-tag filters.

## Quick start (Docker)

```bash
cp .env.example .env
# Edit KL_HOST_PATH only — Compose hardcodes container paths to /media
mkdir -p "$(grep KL_HOST_PATH .env | cut -d= -f2)/inbox"
docker compose up --build
```

- Frontend: http://localhost:5174
- API docs: http://localhost:8001/docs

Ports `5174` / `8001` avoid clashing with Image Organizer on `5173` / `8000`. Inside the container, `KL_ROOT` is always `/media` (your host folder is bind-mounted there).

## Workflow

1. Drop scanned recipe images into `{KL_HOST_PATH}/inbox/`.
2. Open **Inbox** and click **Scan**. Each new image is indexed, thumbnailed, and OCR'd into a draft recipe.
3. Open a recipe, correct the transcription beside the scan, add tags, and mark **reviewed**.
4. Browse and search recipes; filter by multiple tags (AND).

## Local development (without Docker)

### Backend

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
# Requires system tesseract-ocr
export KL_ROOT=/path/to/kitchen
export KL_DATA_DIR=/path/to/kitchen/.kitchenLedger
uvicorn app.main:app --reload --port 8000
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

## Stack

| Layer | Choice |
|-------|--------|
| Backend | Python 3.12, FastAPI, SQLite, Tesseract OCR |
| Frontend | React 18, TypeScript, Vite, TanStack Query |
| Deploy | Docker Compose |

See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for schema, routes, and storage layout.
