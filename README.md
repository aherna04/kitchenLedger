# Kitchen Ledger

Local-first web app for cataloging scanned handwritten recipes. Drop scans into an inbox folder, OCR-assist transcription, correct ingredients and directions beside the image, and organize with multi-tag filters.

## Quick start (Docker)

```bash
cp .env.example .env
# Edit KL_HOST_PATH only — Compose hardcodes container paths to /media
mkdir -p "$(grep KL_HOST_PATH .env | cut -d= -f2)/"{inbox,hero}
docker compose up --build
```

- Frontend: http://localhost:5174
- API docs: http://localhost:8001/docs

Ports `5174` / `8001` avoid clashing with Image Organizer on `5173` / `8000`. Inside the container, `KL_ROOT` is always `/media` (your host folder is bind-mounted there).

## Workflow

1. Drop **recipe scans** and **dish photos** into `{KL_HOST_PATH}/inbox/`.
2. Open **Inbox** and click **Scan**. Files are indexed and OCR'd into drafts; they **stay in inbox** until you process them.
3. For a recipe scan: open the draft, correct the transcription, add tags, and **Mark reviewed** — the scan file moves to `recipes/`.
4. For a dish photo: on the draft card choose **Link as hero to…** and pick the recipe — the file moves to `hero/` and the orphan draft is removed. (Or use **Set hero from draft…** on the recipe detail page.)
5. Browse and search recipes; filter by multiple tags (AND). Cards prefer the hero thumbnail when available.

Optional: files already named to match a scan stem in `hero/` still auto-attach on Scan.


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
