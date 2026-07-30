"""Ce sectiuni narative se randeaza in raport (CERINTA #17 / P6).

Cand `_has_sufficient_data(key, verified_data)` e False, `agent_synthesis.generate_section`
intoarce un FILLER determinist ("Sectiunea '{title}' nu a putut fi generata din cauza datelor
insuficiente...", `word_count=0`) MARCAT cu `INSUFFICIENT_DATA_MARKER=True`. Pe masuratori reale,
sectiunea `competition` cadea pe acest filler in ~92% din rapoarte (colectarea de competitori e
rar populata) — un paragraf de umplutura care nu adauga nimic. P6: astfel de sectiuni se OMIT din
raport, DAR niciodata cu pretul unui raport gol.

Design (CERINTA #17):
- **mark-and-skip la randare**, NU don't-emit: `execute()` trebuie sa intoarca MEREU toate cheile
  de sectiune (invariant garantat de `test_synthesis_partial_preservation`), deci cheia ramane in
  `report_sections` (deci si in DB / regenerare / chat), iar omiterea se face la RANDARE.
- Markerul e setat la UN SINGUR punct de emisie (in sinteza) si citit AICI — nume/logica in acelasi
  modul, ca sa nu apara clasa "cod care citeste o cheie pe care nimic n-o scrie fiabil".
- Randat de HTML/PDF/DOCX/PPTX prin `visible_sections(report_sections)` in loc de iterarea bruta.
"""

# Marcaj EXPLICIT pus de sinteza pe fillerul "date insuficiente". Nume DISTINCT de `insufficient_data`
# (care e deja o cheie bool pe item-ele din `due_diligence` checklist) — obiecte diferite, dar nume
# separat = zero suprapunere semantica. Cheiaza omiterea pe ACEST marker, NU pe `word_count==0` (o
# sectiune scurta legitima l-ar putea avea) si NU pe substring-matching pe proza (o editare a textului
# ar dezactiva tacut omiterea).
INSUFFICIENT_DATA_MARKER = "insufficient_data_filler"


def is_filler_section(section: object) -> bool:
    """True daca `section` e fillerul determinist "date insuficiente" (marcat la emisie).

    Garda `isinstance(dict)` e portanta, nu decorativa: pe calea de eroare a orchestratorului
    (`orchestrator.py`) `report_sections` poate avea o valoare STRING, nu un dict.
    """
    return bool(isinstance(section, dict) and section.get(INSUFFICIENT_DATA_MARKER))


def visible_sections(report_sections: dict) -> dict:
    """Sectiunile de randat, in ordinea originala: exclude fillerele "date insuficiente".

    INVARIANT #4 (niciodata body gol): daca TOATE sectiunile sunt filler, le pastreaza pe toate —
    atunci fillerul "date insuficiente" ESTE raspunsul onest (ex. COMPETITION_ANALYSIS cu competitie
    insuficienta), nu zgomot de omis. Omiterea e corecta doar cand raman alte sectiuni cu continut.
    """
    if not isinstance(report_sections, dict):
        return report_sections
    visible = {k: v for k, v in report_sections.items() if not is_filler_section(v)}
    return visible if visible else report_sections
