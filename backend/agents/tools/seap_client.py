"""
Client SEAP (e-licitatie.ro) — Licitatii si achizitii directe per CUI.
API public, rate limit strict — delay 3s intre request-uri.
"""

import asyncio
import re

from loguru import logger

from backend.agents.tools.retry import with_retry
from backend.http_client import get_client

SEAP_NOTICES_URL = "https://e-licitatie.ro/api-pub/NoticeCommon/GetCANoticeList/"
SEAP_DIRECT_URL = "https://e-licitatie.ro/api-pub/DirectAcquisitionCommon/GetDirectAcquisitionList/"
# Angle A: proceduri DESCHISE (oportunitati). api-pub cere Referer OBLIGATORIU, altfel respinge.
SEAP_CNOTICE_URL = "https://e-licitatie.ro/api-pub/NoticeCommon/GetCNoticeList/"
SEAP_SUPPLIER_LOOKUP_URL = "https://e-licitatie.ro/api-pub/ComboPub/searchSuppliers"

# Starea unei achizitii directe. Masurat pe STRABAG (188 rezultate): id=7 "Oferta
# acceptata" 170, id=6 "Oferta refuzata" 12, id=3 "Conditii refuzate" 3,
# id=4 "Conditii neacceptate la termen" 2, id=8 "Oferta neacceptata in termen" 1.
# DOAR id=7 inseamna contract castigat. Enumerarea de stari NU e garantat completa
# (id=4 a aparut in masuratoarea noastra, dar lipsea dintr-un esantion de 100),
# deci se compara cu 7, nu cu o lista de "stari rele" — o stare noua nu trebuie
# sa poata intra ca "castigat".
DA_STATE_WON = 7
DA_STATE_PARAM = "sysDirectAcquisitionStateId"  # filtru server-side confirmat: total 188 -> 170
_SICAP_HEADERS = {"Content-Type": "application/json", "Referer": "https://e-licitatie.ro"}
OPEN_NOTICE_TYPE_IDS = [2, 17]  # CN (anunt de participare) + SCN (simplificat) = proceduri deschise
REQUEST_DELAY = 3

# `total` din raspuns e PLAFONAT la aceste valori. Un `total` egal cu plafonul nu
# inseamna "atatea rezultate", ci "cel putin atatea" — deci nu se poate construi
# nicio verificare de plauzibilitate pe el fara sa stim ca e sub plafon.
TOTAL_CAP_CA = 3000
TOTAL_CAP_DA = 2000

# Numarul maxim de itemi adusi per endpoint. 200 confirmat functional pe
# GetCANoticeList — elimina paginarea pentru orice firma normala.
DETAIL_PAGE_SIZE = 200


class SeapSourceError(RuntimeError):
    """Raspuns SICAP nefolosibil (HTTP != 200, JSON invalid, forma neasteptata).

    Exista ca tip separat pentru ca "sursa a esuat" si "firma n-are contracte"
    sa NU mai arate identic in aval — azi ambele produc zero, iar SICAP nu expune
    niciun header de rate-limit, deci o blocare se poate manifesta ca 200 cu
    lista goala.
    """


def _normalize_cui(raw) -> str:
    """'RO 6891914' / 'ro6891914' / 6891914 -> '6891914'."""
    return "".join(c for c in str(raw or "").upper().replace("RO", "") if c.isdigit())


def _cui_from_supplier_field(supplier: str) -> str:
    """Extrage CUI-ul din campul `supplier` al unui item DA.

    Formatul REAL, masurat: `'RO 6891914 STRABAG'` — CUI-ul e al DOILEA token,
    dupa prefixul `RO`. Difera de `searchSuppliers`, unde textul e
    `'6891914 STRABAG'`, fara prefix. Furnizorii straini pot sa n-aiba `RO`.
    """
    # `RO\s*` (nu `RO\s+`): forma lipita "RO6891914" apare in date reale.
    m = re.match(r"^\s*(?:RO\s*)?(\d+)", str(supplier or ""), re.IGNORECASE)
    return m.group(1) if m else ""


def _json_or_raise(response, what: str) -> dict:
    """Corp de raspuns folosibil, sau exceptie — niciodata zero tacut."""
    if response.status_code != 200:
        raise SeapSourceError(f"{what}: HTTP {response.status_code}")
    try:
        data = response.json()
    except Exception as e:
        raise SeapSourceError(f"{what}: corp non-JSON ({e})") from e
    if not isinstance(data, dict) or "items" not in data:
        raise SeapSourceError(f"{what}: forma neasteptata (chei: {sorted(data)[:8] if isinstance(data, dict) else type(data).__name__})")
    return data


async def resolve_supplier_id(cui: str, use_cache: bool = True) -> dict:
    """CUI -> id intern de furnizor SICAP (`winnerId` / `supplierId`).

    Filtrarea dupa furnizor NU se face pe CUI pe niciunul dintre endpoint-uri:
    `spiCuiSupplier` (folosit pana la 2026-07-24) era o cheie NECUNOSCUTA, iar
    SICAP ignora tacut cheile necunoscute — deci raspunsul era lista nefiltrata
    la nivel national, identica pentru orice CUI si chiar fara niciun filtru
    (verificat: acelasi set de id-uri, acelasi `total` plafonat).

    Potrivire EXACTA pe primul token, nu `startswith`: exista CUI-uri de 7 cifre
    (ex. 8000138) confundabile cu prefixe ale unora de 8.

    Returneaza {"resolved": bool, "supplier_id": int | None, "reason": str}.
    Ambiguitatea (>=2 potriviri) NU se rezolva prin ghicire — se raporteaza.
    """
    cui_clean = _normalize_cui(cui)
    if not cui_clean:
        return {"resolved": False, "supplier_id": None, "reason": "CUI invalid"}

    if use_cache:
        from backend.services import cache_service
        ck = cache_service.make_cache_key("seap_supplier_id", cui_clean)
        cached = await cache_service.get(ck)
        if isinstance(cached, dict) and "resolved" in cached:
            return cached

    async def _lookup():
        c = get_client()
        return await c.get(SEAP_SUPPLIER_LOOKUP_URL, params={"filter": cui_clean},
                           headers={"Referer": "https://e-licitatie.ro"})

    resp = await with_retry(_lookup, retries=1, backoff=[3], source_name="SEAP searchSuppliers")
    if resp.status_code != 200:
        raise SeapSourceError(f"searchSuppliers: HTTP {resp.status_code}")
    try:
        payload = resp.json()
    except Exception as e:
        raise SeapSourceError(f"searchSuppliers: corp non-JSON ({e})") from e

    items = payload if isinstance(payload, list) else (payload.get("items") or [])
    exact = [
        it for it in items
        if isinstance(it, dict)
        and _normalize_cui(str(it.get("text") or "").strip().split(" ")[0]) == cui_clean
    ]

    # TREI rezultate, nu doua. "Nu figureaza in registru" e un RASPUNS DEFINITIV
    # (firma nu e furnizor, deci nu are contracte), nu un esec de verificare.
    # Colapsate impreuna, o BLOCARE a sursei ar arata identic cu o firma fara
    # contracte — exact clasa de bug reparata mai jos, mutata cu un strat mai sus.
    if len(exact) == 1:
        result = {"resolved": True, "outcome": "resolved", "supplier_id": exact[0].get("id"),
                  "reason": "", "supplier_text": str(exact[0].get("text") or "")}
    elif not exact:
        result = {"resolved": False, "outcome": "not_a_supplier", "supplier_id": None,
                  "reason": "firma nu figureaza in registrul de furnizori SICAP"}
    else:
        # Ambiguitatea NU e un raspuns: nu stim care furnizor e firma ceruta.
        result = {"resolved": False, "outcome": "ambiguous", "supplier_id": None,
                  "reason": f"{len(exact)} furnizori cu acelasi CUI — ambiguu, nu ghicim"}

    if use_cache:
        from backend.services import cache_service
        ck = cache_service.make_cache_key("seap_supplier_id", cui_clean)
        await cache_service.set(ck, result, "seap_supplier_id")
    return result


def _parse_ca_notice(item: dict) -> dict:
    """Atribuire clasica (GetCANoticeList).

    Numele de campuri sunt cele MASURATE pe raspunsul real (2026-07-24), nu cele
    presupuse. Codul anterior citea `contractingAuthorityName`, `publicationDate`,
    `contractCurrency` si `sysNoticeTypeDescription` — NICIUNUL nu exista pe acest
    endpoint, deci 4 din 7 campuri erau goale MEREU, mascate de `.get(k, default)`.

    `ronContractValue` e 0.0 pe acordurile-cadru reale (valoarea nu e un numar unic).
    Zero NU se raporteaza ca valoare — ar dezumfla totalul; se marcheaza necunoscut.
    """
    raw_value = item.get("ronContractValue")
    value = raw_value if isinstance(raw_value, int | float) and raw_value > 0 else None
    state = item.get("sysNoticeState")
    return {
        "title": item.get("contractTitle") or "",
        "value": value,
        "value_unknown": value is None,
        "currency": item.get("currencyCode") or "RON",
        "authority": item.get("contractingAuthorityNameAndFN") or "",
        "date": item.get("noticeStateDate") or "",
        "notice_no": item.get("noticeNo") or "",
        # Starea NOTIFICARII, nu a achizitiei — se persista, NU se filtreaza pe ea
        # pana nu stim ce id inseamna "anulat".
        "state": (state or {}).get("text", "") if isinstance(state, dict) else str(state or ""),
        "state_id": (state or {}).get("id") if isinstance(state, dict) else None,
        "cpv": _cpv_code8(item.get("cpvCodeAndName") or ""),
    }


def _parse_direct_acquisition(item: dict) -> dict:
    """Achizitie directa (GetDirectAcquisitionList).

    Nume de campuri MASURATE pe raspunsul real filtrat (2026-07-24). Doua campuri
    din parserul anterior nu existau deloc pe acest endpoint, deci erau goale
    dintotdeauna, mascate de `.get(k, default)` si de faptul ca datele erau oricum
    neatribuite:
        contractingAuthorityName -> NU EXISTA; real: `contractingAuthority`
        sysDirectAcqStateName    -> NU EXISTA; real: `sysDirectAcquisitionState`,
                                    si e OBIECT {id, text}, nu string
    """
    state = item.get("sysDirectAcquisitionState")
    state_id = state.get("id") if isinstance(state, dict) else None
    return {
        "title": item.get("directAcquisitionName") or "",
        "value": item.get("closingValue"),
        "authority": item.get("contractingAuthority") or "",
        "date": item.get("publicationDate") or "",
        "notice_no": item.get("uniqueIdentificationCode") or "",
        "state": state.get("text", "") if isinstance(state, dict) else str(state or ""),
        "state_id": state_id,
        "won": state_id == DA_STATE_WON,
        "cpv": _cpv_code8(item.get("cpvCode") or ""),
        "supplier_cui": _cui_from_supplier_field(item.get("supplier")),
    }


def seap_status(seap) -> str:
    """Verdictul unui payload SEAP, intr-un singur loc pentru toti consumatorii.

    'verified_with_contracts' — atribuiri confirmate pentru firma ceruta
    'verified_empty'          — verificat, firma NU are contracte publice (fapt)
    'unverified'              — nu stim (sursa a esuat / furnizor nerezolvat)

    Distinctia dintre ultimele doua e intreg scopul acestei functii: pana la
    2026-07-24 ambele arata ca "0", iar zero era prezentat ca fapt.
    Accepta si forma WRAPPED (`_make_field`), ca sa nu se re-implementeze
    unwrap-ul in fiecare consumator.
    """
    if not isinstance(seap, dict):
        return "unverified"
    inner = seap.get("value") if isinstance(seap.get("value"), dict) else seap
    if not inner.get("contracts_verified"):
        return "unverified"
    return "verified_with_contracts" if (inner.get("total_contracts", 0) or 0) > 0 else "verified_empty"


def _cpv_code8(raw: str) -> str:
    """Extrage codul CPV de 8 cifre dintr-un sir gen '09123000-7 - Gaze naturale' sau '09123000-7'."""
    head = str(raw or "").split(" - ", 1)[0].split("-")[0]
    digits = "".join(c for c in head if c.isdigit())
    return digits[:8] if len(digits) >= 8 else ""


async def _fetch_seap_pages(url: str, base_payload: dict, cap: int, id_of, source_name: str) -> tuple[list[dict], int | None]:
    """Paginare `pageIndex`-based pana la min(`total`, `cap`) itemi. (CERINTA #16 C)

    Inainte, fetch-ul aducea DOAR pagina 0 (`pageSize=200`) -> pentru o firma cu >200
    achizitii directe (MOSSLEIN: 485), setul era trunchiat la 200 iar `items_truncated`
    ramanea True desi numarul real (485) incape sub plafonul serverului (2000). Acum se
    aduc TOATE paginile pana la `total` (sau pana la `cap`, plafonul serverului).

    Returneaza `(items, total)`. Ridica `SeapSourceError` DOAR pe esecul paginii 0
    (comportament neschimbat: apelantul intoarce `_unverified`). O pagina >=1 care esueaza
    NU arunca — pastreaza ce s-a adus (marcat partial in aval prin `len(items) < total`),
    exact ca `_fetch_recent_open_notices`: un rate-limit tranzitoriu pe pagina 3 nu trebuie
    sa arunce 400 de itemi deja verificati.

    CANAR anti-"parametru ignorat TACIT" (acelasi mod de esec ca scarul `spiCuiSupplier`):
    SICAP ignora tacit cheile/parametrii nesuportati. Daca `pageIndex` ar fi ignorat, fiecare
    pagina ar reintoarce pagina 0 -> acumulare de duplicate -> numar si valoare umflate ~Nx,
    prezentate cu aceeasi incredere ca un set complet. Se deduplica pe id-ul STABIL emis de
    server; daca o pagina >=1 aduce un id deja vazut, paginarea e considerata ignorata: se
    opreste, se pastreaza doar itemii unici (fara dublare), iar `len < total` marcheaza corect
    setul ca partial. (Verificat LIVE 2026-07-30 ca pageIndex functioneaza; canarul e plasa.)
    """
    all_items: list[dict] = []
    seen: set = set()
    total: int | None = None
    max_pages = cap // DETAIL_PAGE_SIZE + 1  # plasa de siguranta: nu depasi plafonul serverului
    for page in range(max_pages + 1):
        payload = {**base_payload, "pageSize": DETAIL_PAGE_SIZE, "pageIndex": page}

        async def _fetch(p=payload):  # p=payload: capteaza valoarea curenta (nu closure pe var de bucla)
            c = get_client()
            return await c.post(url, json=p, headers=_SICAP_HEADERS)

        try:
            resp = await with_retry(_fetch, retries=1, backoff=[3], source_name=source_name)
            data = _json_or_raise(resp, source_name)
        except SeapSourceError:
            if page == 0:
                raise
            logger.warning(f"[seap] {source_name}: pagina {page} esuata — pastrez {len(all_items)} itemi, marchez partial")
            break

        items = [it for it in (data.get("items") or []) if isinstance(it, dict)]
        page_total = data.get("total")
        if total is None and isinstance(page_total, int):
            total = page_total

        dup = 0
        for it in items:
            iid = id_of(it)
            if iid is not None and iid in seen:
                dup += 1
                continue
            if iid is not None:
                seen.add(iid)
            all_items.append(it)

        if page > 0 and dup:
            logger.warning(
                f"[seap] {source_name}: pagina {page} aduce {dup}/{len(items)} id-uri deja "
                f"vazute -> pageIndex pare IGNORAT; opresc la {len(all_items)} itemi (fara dublare)"
            )
            break

        target = min(total, cap) if isinstance(total, int) else len(all_items)
        # oprire normala: pagina incompleta (nu mai sunt) sau am atins targetul
        if len(items) < DETAIL_PAGE_SIZE or len(all_items) >= target:
            break

        await asyncio.sleep(REQUEST_DELAY)  # secvential: SICAP are anunt anti-bot din 15.07.2026

    return all_items, total


async def get_contracts_won(cui: str, page_size: int = 20, use_cache: bool = True, eur_ron_rate: float | None = None) -> dict:
    """Contracte publice ATRIBUITE firmei, pe SICAP.

    CONTRACT DE RETUR — `contracts_verified` este cheia pe care trebuie s-o
    citeasca ORICE consumator:
      True  -> `contracts` / `direct_acquisitions` sunt atribuite firmei cerute,
               verificate prin filtrare server-side pe id-ul intern de furnizor.
      False -> NU stim nimic despre firma. `reason` spune de ce. Listele sunt
               goale, iar zero NU inseamna "firma n-are contracte".

    De ce exista flagul: pana la 2026-07-24 aceasta functie trimitea
    `spiCuiSupplier`, o cheie pe care SICAP o ignora TACUT (cheile necunoscute nu
    produc eroare). Raspunsul era lista nefiltrata la nivel national — identica
    pentru orice CUI si chiar fara niciun filtru. Fiecare raport a prezentat
    contractele altor firme ca fiind ale firmei analizate.

    `page_size` e pastrat in semnatura pentru compatibilitate cu apelantii
    existenti, dar nu mai limiteaza rezultatul: numaratoarea vine din `total`.
    """
    cui_clean = _normalize_cui(cui)
    if not cui_clean:
        return {"cui": str(cui), "contracts_verified": False, "contracts": [],
                "direct_acquisitions": [], "reason": "CUI invalid",
                "total_contracts": 0, "won_cpv_codes": [], "source": "SEAP"}

    if use_cache:
        from backend.services import cache_service
        cache_key = cache_service.make_cache_key("seap_history", cui_clean)
        cached = await cache_service.get(cache_key)
        if isinstance(cached, dict) and "contracts_verified" in cached:
            logger.debug(f"SEAP: cache hit for CUI {cui_clean}")
            return cached

    def _empty_result(verified: bool, reason: str) -> dict:
        return {"cui": cui_clean, "contracts_verified": verified, "contracts": [],
                "direct_acquisitions": [], "reason": reason, "total_contracts": 0,
                "contracts_count": 0, "direct_count": 0, "total_value": None,
                "won_cpv_codes": [], "source": "SEAP",
                "counts_reliable": verified, "total_capped": False, "items_truncated": False}

    def _unverified(reason: str) -> dict:
        """NU s-a putut determina — sursa a esuat sau raspunsul e ambiguu."""
        return _empty_result(False, reason)

    def _confirmed_empty(reason: str) -> dict:
        """VERIFICAT: firma nu are contracte publice. E un fapt, nu o lipsa de date.

        Distinctia conteaza in trei locuri: completitudinea numara checkul ca
        REUSIT, narativul spune "fara istoric identificat" (nu "date
        indisponibile"), iar o BLOCARE a sursei nu mai poate fi confundata cu
        o firma curata.
        """
        return _empty_result(True, reason)

    # PAS 1 — rezolutia CUI -> id intern. GARDA CRITICA: daca nu se rezolva,
    # ne oprim AICI. Un request fara parametrul de furnizor NU e un fallback:
    # intoarce lista nefiltrata (plafonul de 3000/2000) si reinvie exact iluzia
    # "o firma castiga tot".
    try:
        resolution = await resolve_supplier_id(cui_clean, use_cache=use_cache)
    except SeapSourceError as e:
        logger.warning(f"[seap] rezolutie furnizor esuata pt {cui_clean}: {e}")
        return _unverified(f"sursa indisponibila la rezolutie: {e}")

    if not resolution.get("resolved"):
        if resolution.get("outcome") == "not_a_supplier":
            # Raspuns definitiv, nu esec: firma nu e furnizor -> nu are contracte.
            return _confirmed_empty(resolution.get("reason") or "nu figureaza ca furnizor")
        return _unverified(resolution.get("reason") or "furnizor nerezolvat")

    supplier_id = resolution["supplier_id"]
    results = {
        "cui": cui_clean,
        "contracts_verified": True,
        "supplier_id": supplier_id,
        "contracts": [],
        "direct_acquisitions": [],
        "source": "SEAP",
        "reason": "",
    }

    # PAS 2 — atribuiri clasice (CA notices), filtrate pe `winnerId`.
    # `sysNoticeTypeIds: []` = TOATE tipurile. Masurat pe STRABAG: tip 3 -> 84,
    # toate -> 177 (tip 18 singur aduce 92). Pentru IMM-uri, unde procedurile
    # simplificate sunt canalul principal, fixarea pe [3] ar rata grosul.
    # Referer OBLIGATORIU la api-pub SICAP (in `_SICAP_HEADERS`) — fara el da HTTP 403.
    # Paginat (CERINTA #16 C): aduce TOATE atribuirile pana la `total`, nu doar primele 200.
    ca_base = {
        "winnerId": supplier_id, "sysNoticeTypeIds": [],
        "sortField": "publicationDate", "sortOrder": "desc",
    }
    try:
        ca_items, ca_total = await _fetch_seap_pages(
            SEAP_NOTICES_URL, ca_base, TOTAL_CAP_CA,
            lambda it: it.get("caNoticeId") or it.get("noticeNo"), "SEAP CA notices",
        )
        results["contracts"] = [_parse_ca_notice(it) for it in ca_items]
        results["contracts_count"] = ca_total if isinstance(ca_total, int) else len(results["contracts"])
        results["contracts_count_capped"] = results["contracts_count"] >= TOTAL_CAP_CA
    except SeapSourceError as e:
        logger.warning(f"[seap] CA notices pt {cui_clean}: {e}")
        return _unverified(f"atribuiri clasice indisponibile: {e}")

    await asyncio.sleep(REQUEST_DELAY)  # secvential: SICAP are anunt anti-bot din 15.07.2026

    # PAS 3 — achizitii directe. ACELASI endpoint ca inainte, dar cu parametrul
    # corect: `supplierId` (NU `winnerId` — fiecare endpoint are alt nume, nu
    # exista simetrie). Plus filtru de stare server-side: fara el, `total` numara
    # si ofertele REFUZATE ca si cum ar fi contracte castigate (masurat pe STRABAG:
    # 188 rezultate, dintre care doar 170 castigate).
    # Paginat (CERINTA #16 C): aduce TOATE achizitiile directe pana la `total`. La MOSSLEIN,
    # 485 directe erau trunchiate la 200 -> `items_truncated=True` desi 485 < plafon 2000.
    da_base = {
        "supplierId": supplier_id,
        DA_STATE_PARAM: DA_STATE_WON,
        "sortField": "publicationDate", "sortOrder": "desc",
    }
    try:
        da_items, da_total = await _fetch_seap_pages(
            SEAP_DIRECT_URL, da_base, TOTAL_CAP_DA,
            lambda it: it.get("directAcquisitionId") or it.get("uniqueIdentificationCode"), "SEAP direct",
        )
        parsed = [_parse_direct_acquisition(it) for it in da_items]

        # DOUA LINII DE APARARE, ambele independente de filtrele serverului — tocmai
        # pentru ca modul de esec al acestei surse e "parametru ignorat TACIT", nu eroare.
        # Aplicate acum pe TOATE paginile agregat (`parsed` = toti itemii paginati):
        #   (a) furnizorul: itemul poarta `supplier`, deci se poate valida per-item
        #   (b) starea: se re-verifica local ca e chiar "Oferta acceptata"
        kept, wrong_supplier, not_won = [], 0, 0
        for p in parsed:
            if p["supplier_cui"] != cui_clean:
                wrong_supplier += 1
            elif not p["won"]:
                not_won += 1
            else:
                kept.append(p)
        if wrong_supplier:
            logger.warning(
                f"[seap] {wrong_supplier}/{len(parsed)} achizitii directe aruncate — furnizor "
                f"diferit de CUI {cui_clean}; filtrul server-side pare RUPT"
            )
        if not_won:
            logger.warning(
                f"[seap] {not_won}/{len(parsed)} achizitii directe aruncate — stare != "
                f"'Oferta acceptata'; filtrul de stare pare IGNORAT"
            )

        results["direct_acquisitions"] = kept
        results["direct_dropped_mismatch"] = wrong_supplier
        results["direct_dropped_not_won"] = not_won

        server_filters_held = not wrong_supplier and not not_won
        # `da_total` vine din `_fetch_seap_pages` (paginat). E autoritar DOAR daca ambele
        # filtre server-side au tinut. Daca nu, cade pe numaratoarea locala — care e la
        # randul ei nesigura daca setul a fost trunchiat de plafon (vezi mai jos).
        results["direct_count"] = (
            da_total if isinstance(da_total, int) and server_filters_held else len(kept)
        )
        results["direct_count_capped"] = isinstance(da_total, int) and da_total >= TOTAL_CAP_DA
    except SeapSourceError as e:
        logger.warning(f"[seap] achizitii directe pt {cui_clean}: {e}")
        return _unverified(f"achizitii directe indisponibile: {e}")

    # Numaratoarea vine din `total`, nu din `len(items)`. Inainte, ambele erau
    # plafonate la 10 de `items[:10]` cu page_size=20, deci orice firma raporta
    # cel mult 10 contracte — mascat cat timp datele erau oricum false. STRABAG
    # (177 atribuiri clasice) ar fi raportat "10".
    results["total_contracts"] = results["contracts_count"] + results["direct_count"]

    # GARDA DE TRUNCHIERE. Doua moduri distincte in care numarul poate minti:
    #   (a) `total` atinge plafonul serverului (3000 CA / 2000 DA) -> nu e un numar,
    #       e un "cel putin atat";
    #   (b) am adus mai putini itemi decat spune `total` (pageSize) -> orice
    #       numaratoare sau filtrare LOCALA pe setul adus da un numar fals mic,
    #       prezentat cu aceeasi incredere ca unul complet.
    # Ambele se declara explicit; consumatorii nu trebuie sa le deduca.
    results["total_capped"] = bool(
        results.get("contracts_count_capped") or results.get("direct_count_capped")
    )
    results["items_truncated"] = bool(
        len(results["contracts"]) < results["contracts_count"]
        or len(results["direct_acquisitions"]) < results["direct_count"]
    )
    results["counts_reliable"] = not (results["total_capped"] or results["items_truncated"])

    # Valoarea insumeaza doar itemii ADUSI, nu tot `total` — deci e un minim, nu
    # un total real. Se declara ca atare, ca sa nu fie citita drept cifra de afaceri.
    total_value_ron = 0
    eur_rate = eur_ron_rate or 4.97
    for c in results["contracts"] + results["direct_acquisitions"]:
        val = c.get("value")
        if isinstance(val, int | float):
            if str(c.get("currency", "RON")).upper() == "EUR":
                total_value_ron += val * eur_rate
            else:
                total_value_ron += val
    results["total_value"] = round(total_value_ron)
    results["total_value_currency"] = "RON"
    results["total_value_is_partial"] = (
        len(results["contracts"]) < results["contracts_count"]
        or len(results["direct_acquisitions"]) < results["direct_count"]
        or any(c.get("value_unknown") for c in results["contracts"])
    )

    # Angle A v2: CPV-uri REAL castigate (competente dovedite) — matching precis
    # al oportunitatilor. Alimentat acum din contracte verificate; inainte marca
    # "competenta dovedita" pe baza contractelor altor firme.
    won_cpv: list[str] = []
    _seen_cpv: set[str] = set()
    for c in results["contracts"] + results["direct_acquisitions"]:
        code = c.get("cpv", "")
        if code and code not in _seen_cpv:
            _seen_cpv.add(code)
            won_cpv.append(code)
    results["won_cpv_codes"] = won_cpv

    if use_cache:
        from backend.services import cache_service
        cache_key = cache_service.make_cache_key("seap_history", cui_clean)
        await cache_service.set(cache_key, results, "seap_history")

    return results


async def _fetch_recent_open_notices(days_back: int, max_pages: int, use_cache: bool = True) -> list[dict]:
    """Descarca proceduri deschise SICAP (nefiltrate). Cache 6h per-fereastra, partajat intre firme."""
    if use_cache:
        from backend.services import cache_service
        ck = cache_service.make_cache_key("seap_cnotice_raw", str(days_back))
        cached = await cache_service.get(ck)
        if isinstance(cached, dict):
            return cached.get("notices", [])

    from datetime import UTC, datetime, timedelta
    start = (datetime.now(UTC) - timedelta(days=days_back)).strftime("%Y-%m-%dT00:00:00.000Z")

    notices: list[dict] = []
    for page in range(max_pages):
        body = {
            "sysNoticeTypeIds": OPEN_NOTICE_TYPE_IDS, "sortProperties": [],
            "pageSize": 100, "pageIndex": page, "hasUnansweredQuestions": False,
            "startTenderReceiptDeadline": None, "sysProcedureStateId": None,
            "sysProcedurePhaseId": None, "startPublicationDate": start, "endPublicationDate": None,
        }

        async def _fetch(b=body):
            c = get_client()
            return await c.post(SEAP_CNOTICE_URL, json=b, headers=_SICAP_HEADERS)

        try:
            resp = await with_retry(_fetch, retries=1, backoff=[3], source_name="SEAP open tenders")
        except Exception as e:
            # Esec de pagina (rate-limit tranzitoriu) -> pastram ce am colectat deja, nu aruncam
            logger.warning(f"[seap] pagina {page} CNoticeList esuata: {e} — pastrez {len(notices)} rezultate")
            break
        if resp.status_code != 200:
            logger.warning(f"SEAP CNoticeList HTTP {resp.status_code}")
            break
        data = resp.json()
        items = data.get("items") or (data.get("searchResult") or {}).get("items") or []
        if not items:
            break
        for it in items:
            if not isinstance(it, dict):
                continue
            cca = str(it.get("cpvCodeAndName") or "")
            notices.append({
                "title": it.get("contractTitle", ""),
                "authority": it.get("contractingAuthorityNameAndFN", ""),
                "cpv": cca.split(" - ", 1)[0].strip() if cca else "",
                "cpv_name": cca.split(" - ", 1)[1].strip() if " - " in cca else "",
                "value": it.get("estimatedValueRon"),
                "deadline": it.get("maxTenderReceiptDeadline") or it.get("minTenderReceiptDeadline") or "",
                "notice_no": it.get("noticeNo", ""),
                "procedure_id": it.get("procedureId"),
            })
        if page < max_pages - 1:
            await asyncio.sleep(REQUEST_DELAY)  # politicos intre pagini

    if use_cache and notices:
        from backend.services import cache_service
        ck = cache_service.make_cache_key("seap_cnotice_raw", str(days_back))
        await cache_service.set(ck, {"notices": notices}, "seap_cnotice_raw")
    return notices


async def search_open_tenders(
    caen_code: str,
    won_cpv_codes: list[str] | None = None,
    days_back: int = 30,
    max_pages: int = 2,
    max_results: int = 15,
    use_cache: bool = True,
) -> dict:
    """
    Angle A: licitatii/proceduri DESCHISE relevante pt firma.

    v2 — matching pe DOUA niveluri:
      - CPV-uri REALE castigate de firma (`won_cpv_codes`, din istoricul SEAP) = competente dovedite;
      - fallback pe maparea ORIENTATIVA CAEN->CPV la nivel de diviziune.
    Diviziunile reale + CAEN definesc setul de filtrare; clasa CPV (4 cifre) reala marcheaza
    oportunitatile `precise` (competenta dovedita), afisate primele.

    Descarcarea SICAP e cache-uita per-fereastra (6h) si partajata; filtrarea e locala/per-firma.
    Rezilient: {available: False} la eroare.
    """
    from backend.agents.tools.caen_cpv_map import caen_to_cpv_prefixes

    caen_prefixes = set(caen_to_cpv_prefixes(caen_code))
    real_divisions: set[str] = set()
    real_classes: set[str] = set()
    for raw in (won_cpv_codes or []):
        code = _cpv_code8(raw)
        if code:
            real_divisions.add(code[:2])
            real_classes.add(code[:4])

    filter_prefixes = real_divisions | caen_prefixes
    if not filter_prefixes:
        return {"available": False, "reason": "CAEN necunoscut si fara istoric CPV", "caen_code": str(caen_code)}

    try:
        notices = await _fetch_recent_open_notices(days_back, max_pages, use_cache)
    except Exception as e:
        logger.warning(f"[seap] search_open_tenders esuat: {e}")
        return {"available": False, "error": str(e), "caen_code": str(caen_code)}

    matched: list[dict] = []
    seen: set = set()
    for it in notices:
        code8 = _cpv_code8(it.get("cpv", ""))
        div = code8[:2]
        if not div or div not in filter_prefixes:
            continue
        k = it.get("notice_no") or (it.get("title"), it.get("authority"))
        if k in seen:
            continue
        seen.add(k)
        matched.append({**it, "precise": bool(code8[:4] and code8[:4] in real_classes)})

    matched.sort(key=lambda m: not m.get("precise"))  # competente dovedite primele
    matched = matched[:max_results]

    return {
        "available": True,
        "source": "SICAP",
        "source_url": "https://e-licitatie.ro",
        "caen_code": str(caen_code),
        "cpv_prefixes": sorted(filter_prefixes),
        "basis": "istoric_real" if real_divisions else "caen_orientativ",
        "days_back": days_back,
        "count": len(matched),
        "opportunities": matched,
        "note": ("Pe baza CPV-urilor reale castigate + sector" if real_divisions
                 else "Orientativ — mapare CAEN->CPV la nivel de diviziune"),
    }
