"""
POST /api/reports/{report_id}/send-email — campul `message` (mesaj personal
utilizator, din modalul EmailModal.tsx) trebuie sa ajunga REAL in corpul
emailului compus.

Bug original (verificat la sursa 2026-07-16): `SendEmailRequest` nu declara
deloc `message` -> pydantic v2 (extra="ignore" implicit, fara
`model_config = ConfigDict(extra="forbid")` pe acest model) il arunca
silentios la validare -> `send_report_email` compunea un `body_html` fix,
fara sa foloseasca vreodata textul utilizatorului. NU e o eroare 422 pe
codul vechi (nu exista extra="forbid" in lant) — request-ul vechi intoarce
200 "cu succes", dar mesajul dispare tacut.

Aceste teste verifica DOAR corpul compus trimis catre `send_email` (mockuit)
— nu se trimite niciun email real.
"""

import re as _re
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

_SELECT_COLS_RE = _re.compile(r"SELECT\s+(.*?)\s+FROM", _re.IGNORECASE | _re.DOTALL)


@pytest.fixture
def client():
    """TestClient cu DB + servicii externe mockuite (pattern din test_routers.py)."""
    with patch("backend.database.db") as mock_db:
        mock_db.connect = AsyncMock()
        mock_db.run_migrations = AsyncMock()
        mock_db.close = AsyncMock()
        mock_db.fetch_one = AsyncMock(return_value=None)
        mock_db.fetch_all = AsyncMock(return_value=[])
        mock_db.execute = AsyncMock()

        with patch("backend.http_client.startup", new_callable=AsyncMock):
            with patch("backend.http_client.shutdown", new_callable=AsyncMock):
                with patch("backend.services.cache_service.cleanup_expired", new_callable=AsyncMock):
                    with patch("backend.services.scheduler.start_scheduler", new_callable=AsyncMock, return_value=AsyncMock()):
                        with patch("backend.services.scheduler.stop_scheduler", new_callable=AsyncMock):
                            from backend.main import app
                            yield TestClient(app)


@pytest.fixture
def report_row(tmp_path):
    """Un raport fals cu un PDF real pe disc (in interiorul outputs_dir mockuit)."""
    pdf_path = tmp_path / "raport.pdf"
    pdf_path.write_bytes(b"%PDF-1.4 fake pdf content")
    return {"id": "report-1", "pdf_path": str(pdf_path)}


def _send_email(client, report_row, outputs_dir, payload):
    """Helper: POST /send-email cu DB + outputs_dir + transport de email mockuite.
    Returneaza (response, mock_send_email) — mock_send_email.call_args are body_html real."""
    with patch("backend.routers.reports.db") as mock_db, \
         patch("backend.routers.reports.settings") as mock_settings, \
         patch(
             "backend.services.notification.send_email",
             new=AsyncMock(return_value=True),
         ) as mock_send:
        mock_settings.outputs_dir = str(outputs_dir)
        mock_db.fetch_one = AsyncMock(return_value=report_row)
        resp = client.post(
            f"/api/reports/{report_row['id']}/send-email", json=payload
        )
    return resp, mock_send


def _make_projecting_fetch_one(full_row: dict):
    """Simuleaza un driver DB REAL (nu un mock naiv): intoarce DOAR coloanele
    cerute explicit in clauza SELECT a interogarii, nu tot dict-ul de test.

    Asta e exact mecanismul care a mascat FINDING-ul adiacent: SELECT-ul din
    `send_report_email` cerea doar `id, pdf_path` -> chiar daca DB-ul real avea
    `title`/`created_at` populate, randul intors la runtime NU le continea deloc
    -> `.get('title', ...)` cadea mereu pe default. Un mock care intoarce
    necoditionat `full_row` (ca `_send_email` de mai sus) NU poate prinde acest
    bug — de-aia testele din clasa `TestReportMetadataInEmail` folosesc acest
    helper in loc de `_send_email`."""

    async def _fetch_one(sql, params=None):
        match = _SELECT_COLS_RE.search(sql)
        if not match:
            return dict(full_row)
        cols = [c.strip() for c in match.group(1).split(",")]
        return {c: full_row.get(c) for c in cols}

    return _fetch_one


def _send_email_projecting(client, full_row, outputs_dir, payload):
    """Ca `_send_email`, dar cu `fetch_one` proiectat pe coloanele SELECT reale
    (vezi `_make_projecting_fetch_one`) — sensibil la SQL-ul din cod, nu doar
    la ce alegem noi sa punem in dict-ul mockuit."""
    with patch("backend.routers.reports.db") as mock_db, \
         patch("backend.routers.reports.settings") as mock_settings, \
         patch(
             "backend.services.notification.send_email",
             new=AsyncMock(return_value=True),
         ) as mock_send:
        mock_settings.outputs_dir = str(outputs_dir)
        mock_db.fetch_one = AsyncMock(side_effect=_make_projecting_fetch_one(full_row))
        resp = client.post(
            f"/api/reports/{full_row['id']}/send-email", json=payload
        )
    return resp, mock_send


class TestMessageReachesEmailBody:
    """Non-vacuitate: pe codul VECHI, `message` era ignorat silentios de
    pydantic (camp nedeclarat) -> body_html nu continea niciodata textul
    utilizatorului. Aceste teste PICA pe codul vechi (verificat manual cu
    `git stash push -- backend/routers/reports.py`) si TREC pe codul nou."""

    def test_message_appears_in_composed_body(self, client, report_row, tmp_path):
        payload = {
            "to": "destinatar@exemplu.com",
            "subject": "Raport test",
            "message": "Te rog verifica sectiunea de risc financiar cat mai curand.",
        }
        resp, mock_send = _send_email(client, report_row, tmp_path, payload)

        assert resp.status_code == 200, resp.text
        assert resp.json()["ok"] is True
        mock_send.assert_awaited_once()
        body_html = mock_send.call_args.kwargs["body_html"]
        assert "Te rog verifica sectiunea de risc financiar cat mai curand." in body_html

    def test_message_absent_does_not_break_existing_body(self, client, report_row, tmp_path):
        """Fara `message` (sau None) -> corpul ramane compus normal, fara sectiune goala."""
        payload = {"to": "destinatar@exemplu.com", "subject": "Raport test"}
        resp, mock_send = _send_email(client, report_row, tmp_path, payload)

        assert resp.status_code == 200, resp.text
        body_html = mock_send.call_args.kwargs["body_html"]
        assert "Raportul generat de Roland Intelligence System este atasat." in body_html

    def test_message_blank_whitespace_not_rendered(self, client, report_row, tmp_path):
        """Un mesaj gol/doar spatii nu trebuie sa produca un <p> gol in corp."""
        payload = {"to": "destinatar@exemplu.com", "message": "   \n  "}
        resp, mock_send = _send_email(client, report_row, tmp_path, payload)

        assert resp.status_code == 200, resp.text
        body_html = mock_send.call_args.kwargs["body_html"]
        # Restul corpului trebuie sa fie neschimbat, fara un <p></p> gol adaugat.
        assert "<p></p>" not in body_html


class TestMessageHtmlEscaping:
    """Non-negociabil: text liber de la utilizator care intra intr-un body_html
    trebuie escapat HTML — altfel e o gaura de injectie in emailul trimis."""

    def test_script_tag_is_escaped_not_active(self, client, report_row, tmp_path):
        payload = {
            "to": "destinatar@exemplu.com",
            "message": "Salut <script>alert(1)</script> te rog verifica.",
        }
        resp, mock_send = _send_email(client, report_row, tmp_path, payload)

        assert resp.status_code == 200, resp.text
        body_html = mock_send.call_args.kwargs["body_html"]
        assert "<script>alert(1)</script>" not in body_html
        assert "&lt;script&gt;alert(1)&lt;/script&gt;" in body_html

    def test_bold_tag_is_escaped(self, client, report_row, tmp_path):
        payload = {"to": "destinatar@exemplu.com", "message": "<b>important</b>"}
        resp, mock_send = _send_email(client, report_row, tmp_path, payload)

        assert resp.status_code == 200, resp.text
        body_html = mock_send.call_args.kwargs["body_html"]
        assert "<b>important</b>" not in body_html
        assert "&lt;b&gt;important&lt;/b&gt;" in body_html

    def test_newlines_preserved_as_br(self, client, report_row, tmp_path):
        payload = {"to": "destinatar@exemplu.com", "message": "Linia 1\nLinia 2"}
        resp, mock_send = _send_email(client, report_row, tmp_path, payload)

        assert resp.status_code == 200, resp.text
        body_html = mock_send.call_args.kwargs["body_html"]
        assert "Linia 1<br>Linia 2" in body_html


class TestMessageDiacritics:
    """Istoric de crash-uri pe encoding in proiect (PDF latin-1) — verifica
    ca diacriticele romanesti trec nemodificate prin compunerea body_html."""

    def test_diacritics_preserved(self, client, report_row, tmp_path):
        text = "Va rog sa verificati raportul: capitaluri proprii, imprumuturi si contracte."
        text_diacritics = "Vă rog să verificați raportul – capitaluri, împrumuturi și contracte, mulțumesc!"
        payload = {"to": "destinatar@exemplu.com", "message": text_diacritics}
        resp, mock_send = _send_email(client, report_row, tmp_path, payload)

        assert resp.status_code == 200, resp.text
        body_html = mock_send.call_args.kwargs["body_html"]
        assert text_diacritics in body_html
        assert text not in body_html  # sanity: nu comparam cu varianta fara diacritice


class TestMessageLengthValidation:
    """Plafon rezonabil (5000 caractere) — in stilul field_validator existent
    pentru `to` din acelasi fisier."""

    def test_message_too_long_returns_422(self, client, report_row, tmp_path):
        payload = {"to": "destinatar@exemplu.com", "message": "x" * 5001}
        with patch("backend.routers.reports.db") as mock_db, \
             patch("backend.routers.reports.settings") as mock_settings:
            mock_settings.outputs_dir = str(tmp_path)
            mock_db.fetch_one = AsyncMock(return_value=report_row)
            resp = client.post(
                f"/api/reports/{report_row['id']}/send-email", json=payload
            )
        assert resp.status_code == 422

    def test_message_at_limit_is_accepted(self, client, report_row, tmp_path):
        payload = {"to": "destinatar@exemplu.com", "message": "x" * 5000}
        resp, mock_send = _send_email(client, report_row, tmp_path, payload)
        assert resp.status_code == 200, resp.text


class TestReportMetadataInEmail:
    """FINDING ADIACENT gasit in timp ce se repara `message` (semnalat, apoi
    extins la cererea coordonatorului): SELECT-ul din `send_report_email` cerea
    DOAR `id, pdf_path` (verificat: `reports.py:240` inainte de fix). Coloanele
    reale exista in schema (confirmat cu `PRAGMA table_info(reports)` pe
    `data/ris.db`: `title TEXT`, `created_at DATETIME`), dar NU erau selectate
    -> `.get('title', 'Raport')`/`.get('created_at', 'N/A')` cadeau mereu pe
    default -> FIECARE email trimis avea subiectul generic "Raport RIS — Raport"
    si subsolul "Generat: N/A", indiferent de firma/data reala din raport.

    Randul `REAL_REPORT_ROW` de mai jos e o COPIE a unui rand real citit direct
    din `data/ris.db` pe 2026-07-16 (`SELECT id, title, created_at, pdf_path
    FROM reports ORDER BY created_at DESC LIMIT 1`) — NU o forma inventata.
    """

    REAL_REPORT_ROW = {
        "id": "bc14a0f1-8356-4575-8869-69c6ef7c3a03",
        "title": "FULL_COMPANY_PROFILE — COMPANIA NATIONALA DE TRANSPORTURI AERIENE ROMANE TAROM SA",
        "created_at": "2026-07-16 13:15:20",
    }

    def _real_row(self, tmp_path):
        pdf_path = tmp_path / "raport.pdf"
        pdf_path.write_bytes(b"%PDF-1.4 fake pdf content")
        return {**self.REAL_REPORT_ROW, "pdf_path": str(pdf_path)}

    def test_real_title_and_date_reach_subject_and_footer(self, client, tmp_path):
        """Non-vacuitate (verificat manual cu `git stash push -- backend/routers/reports.py`):
        pe codul VECHI, `fetch_one` proiectat pe SQL-ul real (`SELECT id, pdf_path ...`)
        intoarce un rand FARA `title`/`created_at` -> subiectul compus e
        "Raport RIS — Raport" si subsolul "Generat: N/A", chiar daca DB-ul real
        are titlul si data de mai sus. Pe codul NOU, SELECT-ul le cere -> apar REAL."""
        row = self._real_row(tmp_path)
        payload = {"to": "destinatar@exemplu.com"}  # fara subject explicit -> default din titlu
        resp, mock_send = _send_email_projecting(client, row, tmp_path, payload)

        assert resp.status_code == 200, resp.text
        mock_send.assert_awaited_once()
        subject = mock_send.call_args.kwargs["subject"]
        body_html = mock_send.call_args.kwargs["body_html"]

        assert self.REAL_REPORT_ROW["title"] in subject
        assert self.REAL_REPORT_ROW["title"] in body_html
        assert self.REAL_REPORT_ROW["created_at"] in body_html
        assert subject != "Raport RIS — Raport"
        assert "Generat: N/A" not in body_html

    def test_missing_title_and_date_still_fall_back_safely(self, client, tmp_path):
        """Regresie: un raport vechi/incomplet (title sau created_at NULL in DB)
        nu trebuie sa produca 'None' literal in subiect/subsol."""
        pdf_path = tmp_path / "raport.pdf"
        pdf_path.write_bytes(b"%PDF-1.4 fake")
        row = {"id": "report-null", "title": None, "created_at": None, "pdf_path": str(pdf_path)}
        resp, mock_send = _send_email_projecting(client, row, tmp_path, {"to": "x@y.com"})

        assert resp.status_code == 200, resp.text
        subject = mock_send.call_args.kwargs["subject"]
        body_html = mock_send.call_args.kwargs["body_html"]
        assert subject == "Raport RIS — Raport"
        assert "None" not in subject
        assert "None" not in body_html
        assert "Generat: N/A" in body_html

    def test_title_escaped_in_html_body_but_raw_in_mime_subject_header(self, client, tmp_path):
        """Titlul vine din DB (nume firma), dar disciplina de escaping e aceeasi
        ca la `message`. Antetul MIME "Subject:" ramane text BRUT (nu e HTML —
        daca l-am escapa acolo, destinatarul ar vedea literal "&amp;" in subiectul
        din inbox); doar varianta din <h2> (corpul HTML) trebuie escapata."""
        pdf_path = tmp_path / "raport.pdf"
        pdf_path.write_bytes(b"%PDF-1.4 fake")
        row = {
            "id": "report-html-title",
            "title": "S&C <TEST> FIRMA S.R.L.",
            "created_at": "2026-07-16 10:00:00",
            "pdf_path": str(pdf_path),
        }
        resp, mock_send = _send_email_projecting(client, row, tmp_path, {"to": "x@y.com"})

        assert resp.status_code == 200, resp.text
        subject = mock_send.call_args.kwargs["subject"]
        body_html = mock_send.call_args.kwargs["body_html"]

        assert subject == "Raport RIS — S&C <TEST> FIRMA S.R.L."
        assert "<h2>Raport RIS — S&amp;C &lt;TEST&gt; FIRMA S.R.L.</h2>" in body_html
        assert "<h2>Raport RIS — S&C <TEST> FIRMA S.R.L.</h2>" not in body_html
