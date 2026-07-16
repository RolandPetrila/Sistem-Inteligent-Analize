# Roland Intelligence System (RIS)

Sistem local de Business Intelligence care extrage automat date din surse publice romanesti (ANAF, ONRC, SEAP, BPI), le proceseaza prin agenti AI si produce rapoarte profesionale.

## Stack

- **Backend:** Python 3.13 + FastAPI + SQLite (WAL mode)
- **Frontend:** React 19 + Vite + TypeScript + Tailwind CSS
- **AI:** Claude CLI + Groq + Mistral + Gemini + Cerebras (5-level fallback)
- **PDF:** fpdf2 | **DOCX:** python-docx | **Excel:** openpyxl | **PPTX:** python-pptx

## Quick Start

```bash
# 1. Clone
git clone https://github.com/RolandPetrila/Sistem-Inteligent-Analize.git
cd Sistem-Inteligent-Analize

# 2. Backend
pip install -r requirements.txt
cp .env.example .env   # Editeaza cu API keys (vezi .env.example)
python -m backend.main  # Port 8001

# 3. Frontend
cd frontend
npm install
npm run dev             # Port 5173
```

Sau dublu-click **RIS.vbs** pentru pornire automata (serviciu Windows `RIS-Backend` +
PWA in Chrome pe portul 8001).

## Functionalitati

- 9 tipuri de analiza (profil complet, risc partener, competitie, licitatii, etc.)
- Scor risc 0-100 pe 6 dimensiuni (financiar, juridic, fiscal, operational, reputational, piata)
- 8 formate raport: PDF, DOCX, HTML, Excel, PPTX, 1-Pager, Compare PDF, ZIP
- Comparatie 2+ firme side-by-side
- Batch analysis CSV (procesare multipla)
- Monitorizare automata firme cu alerte Telegram
- 85 REST endpoints + 1 WebSocket + 15 pagini frontend (16 rute, incl. 404)

## Teste

```bash
python -m pytest tests/ -v          # numarul de teste e afisat de comanda
cd frontend && npx vitest run --pool=threads --exclude "**/Companies.test.tsx"
# Companies.test.tsx e exclus intentionat — hang preexistent confirmat pe acest
# repo, indiferent de pool. Vezi RIS_TEST.bat pentru rularea completa cu log.
# Sau: dublu-click RIS_TEST.bat  (scrie TEST_RESULTS.log)
```

## API Docs

Porneste backend-ul, apoi deschide: `http://localhost:8001/docs`

## Licenta

Proiect privat. (c) Roland Petrila 2026.
