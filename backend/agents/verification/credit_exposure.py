"""
P1-4: Bonitate & Expunere comerciala recomandata (RON) — metrica NOUA, ADITIVA.
Determinista (ZERO apel AI — lectia LEAD_GENERATION: date per-entitate = randare
determinista Python, nu LLM), calculata din bilant + culoarea de risc existenta.
NU modifica scoring-ul 0-100 existent — doar il consuma (read-only).

Formula: media a 3 metode standard de trade-credit (cifra lunara / activ net /
venit operational), ponderata cu multiplicatorul culorii de risc, anulata
(kill-switch) daca firma e inactiva ANAF, in insolventa (BPI) sau in zona
Altman DISTRESS.
"""

MULTIPLIER_BY_COLOR = {"Verde": 1.0, "Galben": 0.5, "Rosu": 0.15}

DISCLAIMER = (
    "Estimare orientativa pe SANATATE FINANCIARA (bilant), NU pe istoric de plati "
    "(DSO/comportament real) — RIS nu e birou de credit. Proxy de bonitate, nu scor "
    "de creditworthiness complet; limita se revizuieste periodic."
)


def _v(field):
    if isinstance(field, dict):
        return field.get("value")
    return field


def _fmt_short(v: float) -> str:
    """Format compact pentru string-ul de formula (ex. 1.2M, 450K)."""
    av = abs(v)
    if av >= 1_000_000:
        return f"{v / 1_000_000:.1f}M"
    if av >= 1_000:
        return f"{v / 1_000:.0f}K"
    return f"{v:.0f}"


def commercial_exposure_ron(verified: dict) -> dict:
    """
    Calculeaza expunerea comerciala recomandata (RON).

    `base` = media metodelor cu valoare > 0:
      - Metoda 1 (cifra lunara): 0.10 * (cifra_afaceri / 12)
      - Metoda 2 (activ net): 0.10 * capitaluri_proprii
      - Metoda 3 (venit operational): 0.50 * profit_net, DOAR daca profit_net > 0
      - daca nicio metoda disponibila -> base = 0.
    `mult` = {Verde: 1.0, Galben: 0.5, Rosu: 0.15}[color].
    `expunere` = base * mult.
    Kill-switch -> expunere = 0 daca ORICARE: inactiv ANAF, insolventa (BPI found),
    Altman zone == DISTRESS.
    """
    financial = verified.get("financial", {}) or {}
    risk = verified.get("risk", {}) or {}
    risk_score = verified.get("risk_score", {}) or {}
    predictive = verified.get("predictive_scores", {}) or {}

    ca = _v(financial.get("cifra_afaceri"))
    profit_net = _v(financial.get("profit_net"))
    capitaluri = _v(financial.get("capitaluri_proprii"))

    color = risk_score.get("score") or "Rosu"

    inactiv = bool(_v(risk.get("anaf_inactive")))
    bpi_val = _v(risk.get("bpi_insolventa"))
    insolventa = bool(bpi_val.get("found")) if isinstance(bpi_val, dict) else False
    altman = predictive.get("altman_z", {}) or {}
    altman_distress = altman.get("zone") == "DISTRESS"

    methods: list[tuple[str, float]] = []

    if isinstance(ca, int | float) and ca > 0:
        m1 = 0.10 * (ca / 12)
        methods.append((f"(CA {_fmt_short(ca)}/12)x10%", m1))

    if isinstance(capitaluri, int | float) and capitaluri > 0:
        m2 = 0.10 * capitaluri
        methods.append(("capitaluri x10%", m2))

    if isinstance(profit_net, int | float) and profit_net > 0:
        m3 = 0.50 * profit_net
        methods.append(("profit x50%", m3))

    metode_folosite = len(methods)
    base = sum(v for _, v in methods) / metode_folosite if metode_folosite else 0.0

    mult = MULTIPLIER_BY_COLOR.get(color, 0.15)
    expunere = base * mult

    kill_reasons = []
    if inactiv:
        kill_reasons.append("firma inactiva ANAF")
    if insolventa:
        kill_reasons.append("insolventa (BPI)")
    if altman_distress:
        kill_reasons.append("Altman DISTRESS")

    kill_switch = bool(kill_reasons)
    if kill_switch:
        expunere = 0.0

    expunere_ron = int(round(expunere, -2))

    if methods:
        formula = " + ".join(name for name, _ in methods) + f", medie, x{mult} {color}"
    else:
        formula = f"nicio metoda disponibila, x{mult} {color}"
    if kill_switch:
        formula += f" — KILL-SWITCH ({', '.join(kill_reasons)}) -> expunere 0"

    return {
        "expunere_ron": expunere_ron,
        "metode_folosite": metode_folosite,
        "formula": formula,
        "kill_switch": kill_switch,
        "disclaimer": DISCLAIMER,
    }
