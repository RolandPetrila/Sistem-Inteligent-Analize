"""CERINTA #5 (2026-07-26): onestitate ping AEGRM/RNPM (finding #4-LOW promovat).

Auto-fetch-ul AEGRM (aegrm.justportal.ro) e DNS-dead si nereparabil din cod, DAR
capacitatea "garantii reale mobiliare" NU e pierduta — portalul oficial RNPM
(co.rnpm.ro) e viu si e deja linkat neconditionat in raport (CERINTA #4, b1ff0dc).
Doua suprafete raportau starea ca o capacitate MOARTA seaca (clasa "regula care minte"):
  - mesajul `ping_aegrm` (butonul "Testeaza" din Settings)
  - nota din dashboard-ul de audit (intrarea `aegrm`)
Fix chirurgical: ambele mentioneaza calea manuala co.rnpm.ro. Constrangerea C:
NICIODATA verde-OK pe absenta (auto CHIAR e mort) — mesajul poarta onestitatea, nu `ok`.

E1 (ping, DISCRIMINANT): mock DNS-dead -> message contine co.rnpm.ro.
                          Non-vac.: pe HEAD b1ff0dc mesajul e "AEGRM indisponibil (posibil
                          DNS-dead)" FARA co.rnpm.ro -> PICA.
E2 (ping, garda de stare): pe aceeasi cale, ok RAMANE False, NICIODATA True. [SANTINELA
                          anti-minciuna-opusa — poate trece si pe HEAD; nu e dovada non-vac.]
E3 (dashboard, row-isolated): rândul `aegrm` (script-text SI HTML regenerat) mentioneaza
                          co.rnpm.ro. Non-vac.: pe HEAD nota nu contine co.rnpm.ro -> PICA.
                          Izolare pe RAND (nu pe fisier intreg) — evita trap-ul de vacuitate.
"""

import pathlib
from unittest.mock import AsyncMock, patch

import pytest

ROOT = pathlib.Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "tools" / "generate_audit_dashboard.py"
HTML = ROOT / "AUDIT_FUNCTII.html"

# Forma REALA a erorii DNS-dead de la aegrm_client (verificata in sweep-uri anterioare +
# markerii din connectivity._NETWORK_ERROR_MARKERS: "getaddrinfo" + "11001" o prind).
_DNS_DEAD = {"has_data": False, "error": "[Errno 11001] getaddrinfo failed"}


def _patch_check(return_value=None, side_effect=None):
    """Patch pe simbolul din aegrm_client (ping_aegrm il importa local de acolo)."""
    return patch(
        "backend.agents.tools.aegrm_client.check_aegrm_guarantees",
        new_callable=AsyncMock,
        return_value=return_value,
        side_effect=side_effect,
    )


class TestPingAegrmMentionsManualPath:
    """E1 — toate cele 3 ramuri non-verzi mentioneaza calea manuala co.rnpm.ro."""

    @pytest.mark.asyncio
    async def test_dns_dead_message_mentions_rnpm(self):
        # E1 principal: forma DNS-dead reala -> ramura _looks_like_network_error.
        from backend.agents.tools.connectivity import ping_aegrm

        with _patch_check(return_value=_DNS_DEAD):
            result = await ping_aegrm()

        assert "co.rnpm.ro" in result["message"], (
            "mesajul DNS-dead nu mentioneaza calea manuala co.rnpm.ro (citeste ca 'capacitate moarta')"
        )

    @pytest.mark.asyncio
    async def test_unexpected_exception_message_mentions_rnpm(self):
        # Ramura `except Exception` (client-ul arunca inainte de a intoarce dict).
        from backend.agents.tools.connectivity import ping_aegrm

        with _patch_check(side_effect=RuntimeError("boom")):
            result = await ping_aegrm()

        assert "co.rnpm.ro" in result["message"]

    @pytest.mark.asyncio
    async def test_no_data_non_network_message_mentions_rnpm(self):
        # Ramura "raspuns fara date" (eroare care NU e de retea, ex. HTTP 404).
        from backend.agents.tools.connectivity import ping_aegrm

        with _patch_check(return_value={"has_data": False, "error": "HTTP 404"}):
            result = await ping_aegrm()

        assert "co.rnpm.ro" in result["message"]


class TestPingAegrmNeverGreenOnAbsence:
    """E2 — garda anti-minciuna-opusa: pe absenta datelor, ok RAMANE False. [SANTINELA]"""

    @pytest.mark.asyncio
    async def test_dns_dead_stays_not_ok(self):
        from backend.agents.tools.connectivity import ping_aegrm

        with _patch_check(return_value=_DNS_DEAD):
            result = await ping_aegrm()

        assert result["ok"] is False, (
            "auto-fetch AEGRM e mort — a-l marca ok:True ar fi o sursa falsa-verde (minciuna opusa)"
        )

    @pytest.mark.asyncio
    async def test_real_data_still_ok(self):
        # SANTINELA inversa: daca AEGRM chiar raspunde cu date (has_data), ok:True e genuin
        # (nu pe absenta) — nu trebuie sa fi stricat calea reala.
        from backend.agents.tools.connectivity import ping_aegrm

        with _patch_check(return_value={"has_data": True, "count": 3}):
            result = await ping_aegrm()

        assert result["ok"] is True
        assert "3" in result["message"]


def _aegrm_script_line() -> str:
    """Izoleaza RANDUL EXTERNAL_SOURCES al intrarii aegrm (tuplu pe o singura linie).
    NU importa modulul — evita side-effectul `backend.main.app.routes` (ca in
    test_audit_dashboard_labels.py). Assert pe rand, nu pe fisier -> non-vacuitate reala."""
    text = SCRIPT.read_text(encoding="utf-8")
    lines = [ln for ln in text.splitlines() if '"AEGRM (garantii mobiliare)"' in ln]
    assert len(lines) == 1, f"astept exact o intrare AEGRM in EXTERNAL_SOURCES, gasit {len(lines)}"
    return lines[0]


def _aegrm_html_row() -> str:
    """Izoleaza <tr>-ul aegrm din HTML-ul regenerat (o sursa = un <tr> pe o linie, l.552)."""
    assert HTML.exists(), "AUDIT_FUNCTII.html lipseste — regenereaza cu tools/generate_audit_dashboard.py"
    html = HTML.read_text(encoding="utf-8")
    rows = [ln for ln in html.splitlines() if "AEGRM (garantii mobiliare)" in ln]
    assert len(rows) == 1, f"astept exact un rand AEGRM in HTML, gasit {len(rows)}"
    return rows[0]


class TestDashboardAegrmNote:
    """E3 — nota dashboard aliniata: cititorul afla ca exista calea manuala co.rnpm.ro."""

    def test_script_row_mentions_rnpm(self):
        # Non-vac.: pe HEAD b1ff0dc randul e "CONFIRMAT: tot DNS-dead ..." FARA co.rnpm.ro.
        assert "co.rnpm.ro" in _aegrm_script_line()

    def test_html_row_mentions_rnpm(self):
        assert "co.rnpm.ro" in _aegrm_html_row()

    def test_row_still_marks_auto_dead_not_covered(self):
        # SANTINELA constrangerea C: nota NU trebuie sa citeasca drept "capacitate acoperita/OK".
        # Trebuie sa ramana explicita ca auto-fetch-ul e indisponibil/mort — altfel am flipat in
        # minciuna opusa (sursa falsa-verde). [Poate trece si pe HEAD — e garda, nu dovada non-vac.]
        line = _aegrm_script_line().lower()
        assert ("dns-dead" in line or "indisponibil" in line), (
            "nota aegrm nu mai spune ca auto-fetch-ul e mort -> risca sa citeasca drept 'acoperit'"
        )
        for forbidden in ("0 garantii", "curat", "fara garantii"):
            assert forbidden not in line, f"nota aegrm citeste ca verde/coverage pe absenta: '{forbidden}'"
