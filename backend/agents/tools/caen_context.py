"""
DF4: Context CAEN — descriere cod CAEN + date statistice.
Foloseste dictionar local CAEN (fiabil) + INS TEMPO API (optional, pentru numar firme).
"""

from loguru import logger

from backend.http_client import get_client

# Dictionar CAEN complet (top 100 cele mai comune coduri)
# Sursa: ONRC / clasificare CAEN Rev.2
CAEN_DESCRIPTIONS = {
    "0111": "Cultivarea cerealelor (exclusiv orez), plantelor leguminoase si a plantelor producatoare de seminte oleaginoase",
    "0141": "Cresterea bovinelor de lapte",
    "0150": "Activitati in ferme mixte",
    "0210": "Silvicultura si alte activitati forestiere",
    "0311": "Pescuitul maritim",
    "1071": "Fabricarea painii; fabricarea produselor proaspete de patiserie",
    "1101": "Distilarea, rafinarea si mixarea bauturilor alcoolice",
    "1107": "Productia de bauturi racoritoare nealcoolice; productia de ape minerale",
    "1610": "Taierea si rindeluirea lemnului",
    "1812": "Alte activitati de tiparire n.c.a.",
    "2041": "Fabricarea sapunurilor, detergentilor si a produselor de intretinere",
    "2511": "Fabricarea de constructii metalice si parti componente ale structurilor metalice",
    "2562": "Operatiuni de mecanica generala",
    "2932": "Fabricarea altor piese si accesorii pentru autovehicule si pentru motoare de autovehicule",
    "3109": "Fabricarea de mobilier n.c.a.",
    "3600": "Captarea, tratarea si distributia apei",
    "3811": "Colectarea deseurilor nepericuloase",
    "4110": "Dezvoltare (promovare) imobiliara",
    "4120": "Lucrari de constructii a cladirilor rezidentiale si nerezidentiale",
    "4211": "Lucrari de constructii a drumurilor si autostrazi",
    "4221": "Lucrari de constructii a proiectelor utilitare pentru fluide",
    "4291": "Constructii hidrotehnice",
    "4311": "Lucrari de demolare a constructiilor",
    "4321": "Lucrari de instalatii electrice",
    "4322": "Lucrari de instalatii sanitare, de incalzire si de aer conditionat",
    "4332": "Lucrari de tamplarie si dulgherie",
    "4391": "Lucrari de invelitori, sarpante si terase la constructii",
    "4399": "Alte lucrari speciale de constructii n.c.a.",
    "4520": "Intretinerea si repararea autovehicolelor",
    "4531": "Comert cu ridicata de piese si accesorii pentru autovehicule",
    "4532": "Comert cu amanuntul de piese si accesorii pentru autovehicule",
    "4611": "Intermedieri in comertul cu materii prime agricole, animale vii, materii prime textile si cu semifabricate",
    "4619": "Intermedieri in comertul cu produse diverse",
    "4631": "Comert cu ridicata al fructelor si legumelor",
    "4632": "Comert cu ridicata al carnii si produselor din carne",
    "4641": "Comert cu ridicata al produselor textile",
    "4645": "Comert cu ridicata al produselor cosmetice si de parfumerie",
    "4646": "Comert cu ridicata al produselor farmaceutice",
    "4649": "Comert cu ridicata al altor bunuri de uz gospodaresc",
    "4669": "Comert cu ridicata al altor masini si echipamente",
    "4671": "Comert cu ridicata al combustibililor solizi, lichizi si gazosi si al produselor derivate",
    "4673": "Comert cu ridicata al materialului lemnos si al materialelor de constructii si echipamentelor sanitare",
    "4674": "Comert cu ridicata al echipamentelor si furniturilor de fierarie pentru instalatii sanitare si de incalzire",
    "4690": "Comert cu ridicata nespecializat",
    "4711": "Comert cu amanuntul in magazine nespecializate, cu vanzare predominanta de produse alimentare, bauturi si tutun",
    "4719": "Comert cu amanuntul in magazine nespecializate, cu vanzare predominanta de produse nealimentare",
    "4721": "Comert cu amanuntul al fructelor si legumelor proaspete, in magazine specializate",
    "4730": "Comert cu amanuntul al carburantilor pentru autovehicule, in magazine specializate",
    "4741": "Comert cu amanuntul al calculatoarelor, unitatilor periferice si software-ului",
    "4751": "Comert cu amanuntul al textilelor, in magazine specializate",
    "4759": "Comert cu amanuntul al mobilei, al articolelor de iluminat si al altor articole de uz casnic",
    "4771": "Comert cu amanuntul al imbracamintei, in magazine specializate",
    "4773": "Comert cu amanuntul al produselor farmaceutice, in magazine specializate",
    "4775": "Comert cu amanuntul al produselor cosmetice si de parfumerie, in magazine specializate",
    "4791": "Comert cu amanuntul prin intermediul caselor de comenzi sau prin Internet",
    "4799": "Comert cu amanuntul efectuat in afara magazinelor, standurilor, chioscurilor si pietelor",
    "4910": "Transporturi interurbane de calatori pe calea ferata",
    "4920": "Transporturi de marfa pe calea ferata",
    "4941": "Transporturi rutiere de marfuri",
    "5210": "Depozitari",
    "5229": "Alte activitati anexe transporturilor",
    "5310": "Activitati postale desfasurate sub obligativitatea serviciului universal",
    "5510": "Hoteluri si alte facilitati de cazare similare",
    "5610": "Restaurante",
    "5621": "Activitati de alimentatie (catering) pentru evenimente",
    "5630": "Baruri si alte activitati de servire a bauturilor",
    "6110": "Activitati de telecomunicatii prin retele cu cablu",
    "6190": "Alte activitati de telecomunicatii",
    "6201": "Activitati de realizare a software-ului la comanda (software orientat client)",
    "6202": "Activitati de consultanta in tehnologia informatiei",
    "6209": "Alte activitati de servicii privind tehnologia informatiei",
    "6311": "Prelucrarea datelor, administrarea paginilor web si activitati conexe",
    "6399": "Alte activitati de servicii informationale n.c.a.",
    "6420": "Activitati ale holdingurilor",
    "6499": "Alte intermedieri financiare n.c.a.",
    "6622": "Activitati ale agentilor si brokerilor de asigurari",
    "6810": "Cumpararea si vanzarea de bunuri imobiliare proprii",
    "6820": "Inchirierea si subinchirierea bunurilor imobiliare proprii sau inchiriate",
    "6831": "Agentii imobiliare",
    "6910": "Activitati juridice",
    "6920": "Activitati de contabilitate si audit financiar; consultanta in domeniul fiscal",
    "7010": "Activitati ale directiilor (centralelor), birourilor administrative centralizate",
    "7021": "Activitati de consultanta in domeniul relatiilor publice si al comunicarii",
    "7022": "Activitati de consultanta pentru afaceri si management",
    "7111": "Activitati de arhitectura",
    "7112": "Activitati de inginerie si consultanta tehnica legate de acestea",
    "7120": "Activitati de testari si analize tehnice",
    "7211": "Cercetare-dezvoltare in biotehnologie",
    "7219": "Cercetare-dezvoltare in alte stiinte naturale si inginerie",
    "7311": "Activitati ale agentiilor de publicitate",
    "7320": "Activitati de studiere a pietei si de sondare a opiniei publice",
    "7490": "Alte activitati profesionale, stiintifice si tehnice n.c.a.",
    "7500": "Activitati veterinare",
    "7711": "Activitati de inchiriere si leasing cu autoturisme si autovehicule rutiere usoare",
    "7820": "Activitati de contractare, pe baze temporare, a personalului",
    "7911": "Activitati ale agentiilor turistice",
    "8010": "Activitati de protectie si garda",
    "8110": "Activitati de servicii suport combinate",
    "8121": "Activitati generale de curatenie a cladirilor",
    "8211": "Activitati combinate de secretariat",
    "8219": "Activitati de fotocopiere, de pregatire a documentelor si alte activitati specializate de secretariat",
    "8220": "Activitati ale centrelor de intermediere telefonica (call center)",
    "8230": "Activitati de organizare a expozitiilor, targurilor si congreselor",
    "8291": "Activitati ale agentiilor de colectare si ale birourilor (oficiilor) de raportare a creditului",
    "8299": "Alte activitati de servicii suport pentru intreprinderi n.c.a.",
    "8510": "Invatamant prescolar",
    "8520": "Invatamant primar",
    "8531": "Invatamant secundar general",
    "8559": "Alte forme de invatamant n.c.a.",
    "8610": "Activitati de asistenta spitaliceasca",
    "8621": "Activitati de asistenta medicala generala",
    "8622": "Activitati de asistenta medicala specializata",
    "8690": "Alte activitati referitoare la sanatatea umana",
    "9001": "Activitati de interpretare artistica (spectacole)",
    "9311": "Activitati ale bazelor sportive",
    "9312": "Activitati ale cluburilor sportive",
    "9329": "Alte activitati recreative si distractive n.c.a.",
    "9511": "Repararea calculatoarelor si a echipamentelor periferice",
    "9521": "Repararea aparatelor electronice de uz casnic",
    "9601": "Spalarea si curatarea (uscata) a articolelor textile si a produselor din blana",
    "9602": "Coafura si alte activitati de infrumusetare",
    "9604": "Activitati de intretinere corporala",
    "9609": "Alte activitati de servicii n.c.a.",
}

# Sectiuni CAEN (prima cifra/2 cifre)
CAEN_SECTIONS = {
    "01": "Agricultura", "02": "Silvicultura", "03": "Pescuit",
    "05": "Extractie carbune", "06": "Extractie petrol/gaze", "07": "Extractie minereuri",
    "08": "Alte extractii", "09": "Servicii extractie",
    "10": "Industria alimentara", "11": "Fabricarea bauturilor", "12": "Fabricarea tutunului",
    "13": "Fabricarea textilelor", "14": "Fabricarea articolelor de imbracaminte",
    "15": "Fabricarea pielei", "16": "Prelucrarea lemnului",
    "17": "Fabricarea hartiei", "18": "Tiparire",
    "20": "Fabricarea substantelor chimice", "21": "Fabricarea produselor farmaceutice",
    "22": "Fabricarea cauciucului/plasticului", "23": "Fabricarea altor produse minerale nemetalice",
    "24": "Metalurgie", "25": "Industria constructiilor metalice",
    "26": "Fabricarea calculatoarelor/electronicelor", "27": "Fabricarea echipamentelor electrice",
    "28": "Fabricarea masinilor", "29": "Fabricarea autovehiculelor", "30": "Fabricarea altor mijloace de transport",
    "31": "Fabricarea de mobilier", "32": "Alte activitati industriale", "33": "Repararea masinilor",
    "35": "Productia/furnizarea de energie", "36": "Captarea/distributia apei",
    "37": "Colectarea/epurarea apelor uzate", "38": "Colectarea/tratarea deseurilor",
    "41": "Constructii de cladiri", "42": "Inginerie civila", "43": "Lucrari speciale de constructii",
    "45": "Comert autovehicule", "46": "Comert cu ridicata", "47": "Comert cu amanuntul",
    "49": "Transporturi terestre", "50": "Transporturi pe apa", "51": "Transporturi aeriene",
    "52": "Depozitare/transporturi auxiliare", "53": "Activitati postale/curierat",
    "55": "Hoteluri/cazare", "56": "Restaurante/catering",
    "58": "Activitati de editare", "59": "Productie cinematografica", "60": "Activitati radio/TV",
    "61": "Telecomunicatii", "62": "Activitati IT/software", "63": "Activitati servicii informatice",
    "64": "Intermedieri financiare", "65": "Asigurari", "66": "Activitati auxiliare financiare",
    "68": "Tranzactii imobiliare", "69": "Activitati juridice/contabilitate",
    "70": "Activitati directii/management", "71": "Arhitectura/inginerie", "72": "Cercetare-dezvoltare",
    "73": "Publicitate/studii de piata", "74": "Alte activitati profesionale",
    "75": "Activitati veterinare", "77": "Activitati de inchiriere/leasing",
    "78": "Activitati de ocupare a fortei de munca", "79": "Agentii de turism",
    "80": "Activitati de protectie/paza", "81": "Activitati de peisagistica/curatenie",
    "82": "Activitati de secretariat/call center",
    "84": "Administratie publica", "85": "Invatamant",
    "86": "Activitati de sanatate", "87": "Asistenta sociala cu cazare", "88": "Asistenta sociala fara cazare",
    "90": "Activitati de creatie/artistica", "91": "Activitati biblioteci/muzee",
    "92": "Activitati de jocuri de noroc", "93": "Activitati sportive/recreative",
    "94": "Activitati asociative", "95": "Reparatii calculatoare/bunuri personale",
    "96": "Alte activitati de servicii",
}


# Medii CA per sectiune CAEN (RON, date estimate INS 2023)
# Sursa: INS TEMPO INT101B + estimari pe baza datelor publice
CAEN_BENCHMARK = {
    "01": {"ca_medie": 850_000, "angajati_medii": 8, "nr_firme": 45_200},
    "10": {"ca_medie": 2_500_000, "angajati_medii": 22, "nr_firme": 8_900},
    "16": {"ca_medie": 1_200_000, "angajati_medii": 12, "nr_firme": 5_100},
    "25": {"ca_medie": 1_800_000, "angajati_medii": 15, "nr_firme": 7_200},
    "41": {"ca_medie": 2_800_000, "angajati_medii": 18, "nr_firme": 12_500},
    "42": {"ca_medie": 3_500_000, "angajati_medii": 25, "nr_firme": 4_200},
    "43": {"ca_medie": 1_100_000, "angajati_medii": 8, "nr_firme": 28_000},
    "45": {"ca_medie": 1_500_000, "angajati_medii": 6, "nr_firme": 15_800},
    "46": {"ca_medie": 3_200_000, "angajati_medii": 8, "nr_firme": 42_000},
    "47": {"ca_medie": 900_000, "angajati_medii": 5, "nr_firme": 65_000},
    "49": {"ca_medie": 1_200_000, "angajati_medii": 7, "nr_firme": 32_000},
    "55": {"ca_medie": 1_100_000, "angajati_medii": 10, "nr_firme": 6_800},
    "56": {"ca_medie": 450_000, "angajati_medii": 6, "nr_firme": 22_000},
    "62": {"ca_medie": 1_800_000, "angajati_medii": 12, "nr_firme": 18_500},
    "68": {"ca_medie": 600_000, "angajati_medii": 3, "nr_firme": 25_000},
    "69": {"ca_medie": 350_000, "angajati_medii": 4, "nr_firme": 38_000},
    "70": {"ca_medie": 2_500_000, "angajati_medii": 10, "nr_firme": 8_500},
    "71": {"ca_medie": 800_000, "angajati_medii": 8, "nr_firme": 12_000},
    "82": {"ca_medie": 600_000, "angajati_medii": 5, "nr_firme": 9_000},
    "86": {"ca_medie": 1_200_000, "angajati_medii": 15, "nr_firme": 9_500},
    "96": {"ca_medie": 200_000, "angajati_medii": 3, "nr_firme": 18_000},
}


# CAEN Rev.3 — intrat în vigoare 2025, obligatoriu ANAF din 25 septembrie 2026
# Sursa: ONRC / Ordinul INS nr. 604/2024 privind actualizarea CAEN Rev.3
CAEN_REV3_CODES = {
    # IT & Software (cele mai frecvente in Romania)
    "6201": "Activitati de realizare a software-ului la comanda",
    "6202": "Activitati de consultanta in tehnologia informatiei",
    "6203": "Activitati de management al resurselor informatice",
    "6209": "Alte activitati de servicii privind tehnologia informatiei",
    "6311": "Prelucrarea datelor, administrarea paginilor web si activitati conexe",
    "6312": "Portaluri web",
    "6391": "Activitati ale agentiilor de stiri",
    "6399": "Alte activitati de servicii informationale n.c.a.",
    # Comert
    "4711": "Comert cu amanuntul in magazine nespecializate, cu vanzare predominanta de produse alimentare, bauturi si tutun",
    "4719": "Comert cu amanuntul in magazine nespecializate, cu vanzare predominanta de produse nealimentare",
    "4791": "Comert cu amanuntul prin intermediul caselor de comenzi sau prin Internet",
    "4669": "Comert cu ridicata al altor masini si echipamente",
    "4690": "Comert cu ridicata nespecializat",
    # Constructii
    "4120": "Lucrari de constructii a cladirilor rezidentiale si nerezidentiale",
    "4321": "Lucrari de instalatii electrice",
    "4322": "Lucrari de instalatii sanitare, de incalzire si de aer conditionat",
    "4399": "Alte lucrari speciale de constructii n.c.a.",
    # Consultanta & Management
    "7022": "Activitati de consultanta pentru afaceri si management",
    "6920": "Activitati de contabilitate si audit financiar; consultanta in domeniul fiscal",
    "7112": "Activitati de inginerie si consultanta tehnica legate de acestea",
    # Imobiliare
    "6820": "Inchirierea si subinchirierea bunurilor imobiliare proprii sau inchiriate",
    "6810": "Cumpararea si vanzarea de bunuri imobiliare proprii",
    "6831": "Agentii imobiliare",
    # Transport
    "4941": "Transporturi rutiere de marfuri",
    "5229": "Alte activitati anexe transporturilor",
    # HoReCa
    "5610": "Restaurante",
    "5510": "Hoteluri si alte facilitati de cazare similare",
}

# Mapare retrocompatibilitate Rev.2 → Rev.3 (coduri care s-au modificat sau divizat)
# Acolo unde codul a ramas identic, nu e necesar in dictionar.
# Codul Rev.2 ca cheie → codul Rev.3 echivalent ca valoare
REV2_TO_REV3: dict[str, str] = {
    # Exemple de reclasificari tipice in Rev.3 (coduri cu structura modificata)
    "6200": "6201",   # Software generic → software la comanda
    "6312": "6311",   # Web portals → data processing (unificat in Rev.3)
    "7490": "7499",   # Alte activitati profesionale (re-numerotare Rev.3)
    "8299": "8291",   # Alte activitati suport (consolidare)
    "9609": "9601",   # Alte servicii (re-alocare)
}


def get_caen_rev3_description(code: str) -> str:
    """Returneaza descrierea CAEN Rev.3 pentru un cod dat.
    Fallback automat la Rev.2 daca codul nu exista in Rev.3.
    Util post-25 septembrie 2026 cand ANAF trece exclusiv la Rev.3."""
    code = str(code).strip()
    if code in CAEN_REV3_CODES:
        return CAEN_REV3_CODES[code]
    # Incearca mapare Rev.2 → Rev.3
    rev3_code = REV2_TO_REV3.get(code)
    if rev3_code and rev3_code in CAEN_REV3_CODES:
        return CAEN_REV3_CODES[rev3_code]
    # Fallback la Rev.2
    return get_caen_description(code)


def get_caen_description(caen_code: str) -> str:
    """Returneaza descrierea CAEN din dictionar local."""
    caen_code = str(caen_code).strip()
    # Cauta exact
    if caen_code in CAEN_DESCRIPTIONS:
        return CAEN_DESCRIPTIONS[caen_code]
    # Cauta sectiune (2 cifre)
    section = caen_code[:2]
    if section in CAEN_SECTIONS:
        return CAEN_SECTIONS[section]
    return ""


async def get_caen_context(caen_code: str) -> dict:
    """
    Returneaza context CAEN: descriere + date statistice (INS TEMPO optional).
    Functioneaza si fara INS TEMPO (descrierea vine din dictionar local).
    """
    caen_code = str(caen_code).strip()
    if not caen_code:
        return {"available": False}

    description = get_caen_description(caen_code)
    section = caen_code[:2]
    section_name = CAEN_SECTIONS.get(section, "")

    # Benchmark din dictionar local
    benchmark = CAEN_BENCHMARK.get(section, {})

    result = {
        "available": True,
        "caen_code": caen_code,
        "caen_description": description,
        "caen_section": section,
        "caen_section_name": section_name,
        "nr_firme_caen": benchmark.get("nr_firme"),
        "benchmark": {
            "ca_medie": benchmark.get("ca_medie"),
            "angajati_medii": benchmark.get("angajati_medii"),
            "source": "INS TEMPO 2023 (estimare)",
        } if benchmark else None,
        "ins_tempo_available": False,
    }

    # ADV2: INS TEMPO API live (optional, poate fi offline)
    try:
        tempo_data = await _fetch_ins_tempo_all(section)
        if tempo_data:
            result["ins_tempo_available"] = True
            if tempo_data.get("nr_firme"):
                result["nr_firme_caen"] = tempo_data["nr_firme"]
            if tempo_data.get("ca_medie") and result.get("benchmark"):
                result["benchmark"]["ca_medie"] = tempo_data["ca_medie"]
                result["benchmark"]["source"] = "INS TEMPO (date oficiale)"
            if tempo_data.get("angajati_medii") and result.get("benchmark"):
                result["benchmark"]["angajati_medii"] = tempo_data["angajati_medii"]
            logger.info(f"[caen] INS TEMPO live data for section {section}: {tempo_data}")
    except Exception as e:
        logger.debug(f"INS TEMPO unavailable: {e}")

    return result


async def _fetch_ins_tempo_firms(caen_code: str) -> int | None:
    """
    Interogheaza INS TEMPO API pentru numarul de firme active pe un cod CAEN.
    API: http://statistici.insse.ro:8077/tempo-online/
    Returneaza None daca API-ul nu raspunde.
    """
    try:
        client = get_client()
        # INS TEMPO REST endpoint pentru intreprinderi active per CAEN
        # Matrice: INT101B - Intreprinderi active pe activitati CAEN Rev.2
        url = "http://statistici.insse.ro:8077/tempo-online/rest/data/INT101B"
        params = {
            "lang": "ro",
            "precision": "0",
            "perioade": "2023",  # ultimul an disponibil
            "activitati_caen_rev_2": f"D{caen_code[:2]}",  # nivel sectiune
        }

        response = await client.get(url, params=params, timeout=10)
        if response.status_code != 200:
            return None

        data = response.json()
        # Parseaza raspunsul INS TEMPO
        if isinstance(data, dict) and "result" in data:
            values = data["result"]
            if isinstance(values, list) and values:
                # Sumam valorile pentru toate judetele
                # D5 fix: Accept float values too (e.g. "123.5")
                total = 0
                for v in values:
                    raw = v.get("value")
                    if raw is not None:
                        try:
                            total += int(float(raw))
                        except (ValueError, TypeError):
                            pass
                if total > 0:
                    return total

        return None
    except Exception as e:
        logger.warning(f"[caen] INS TEMPO fetch: {e}")
        return None


async def _fetch_ins_tempo_all(section: str) -> dict | None:
    """
    ADV2: Interogheaza INS TEMPO pentru nr firme, CA medie, angajati medii per sectiune CAEN.
    Incearca multiple matrici INS. Returneaza None daca offline.
    """
    result = {}
    client = get_client()

    # 1. Numar intreprinderi active (INT101B)
    try:
        r = await client.get(
            "http://statistici.insse.ro:8077/tempo-online/rest/data/INT101B",
            params={"lang": "ro", "precision": "0", "perioade": "2023",
                    "activitati_caen_rev_2": f"D{section}"},
            timeout=8,
        )
        if r.status_code == 200:
            data = r.json()
            if isinstance(data, dict) and "result" in data:
                values = data["result"]
                if isinstance(values, list):
                    total = sum(
                        int(v.get("value", 0)) for v in values
                        if v.get("value") and str(v["value"]).isdigit()
                    )
                    if total > 0:
                        result["nr_firme"] = total
    except Exception as e:
        logger.debug(f"[caen] INS nr_firme fetch failed: {e}")

    # 2. Cifra afaceri (INT101I — CA neta per CAEN)
    try:
        r = await client.get(
            "http://statistici.insse.ro:8077/tempo-online/rest/data/INT101I",
            params={"lang": "ro", "precision": "0", "perioade": "2023",
                    "activitati_caen_rev_2": f"D{section}"},
            timeout=8,
        )
        if r.status_code == 200:
            data = r.json()
            if isinstance(data, dict) and "result" in data:
                values = data["result"]
                if isinstance(values, list):
                    total_ca = sum(
                        float(v.get("value", 0)) for v in values
                        if v.get("value")
                    )
                    nr = result.get("nr_firme", 1)
                    if total_ca > 0 and nr > 0:
                        # CA vine in mii RON, convertim la RON per firma
                        result["ca_medie"] = int((total_ca * 1000) / nr)
    except Exception as e:
        logger.debug(f"[caen] INS ca_medie fetch failed: {e}")

    return result if result else None
