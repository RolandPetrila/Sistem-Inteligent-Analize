"""
Mapare ORIENTATIVA CAEN (diviziune, 2 cifre) -> prefixe CPV (diviziune, 2 cifre).

NU exista crosswalk oficial CAEN<->CPV: CAEN descrie ce FACE firma, CPV ce se ACHIZITIONEAZA.
Harta e euristica, folosita DOAR pentru a filtra orientativ licitatiile deschise pe sectorul
firmei (Angle A). Rezultatele se marcheaza explicit „orientativ" in raport.

Rafinare viitoare (v2): invata CPV-urile reale din contractele castigate ale firmei (Angle B /
istoric SEAP) -> cel mai bun „CPV real" per firma, in loc de aceasta mapare la nivel de sector.
"""

# CAEN diviziune -> liste de prefixe CPV diviziune (primele 2 cifre din codul CPV de 8 cifre)
CAEN_TO_CPV: dict[str, list[str]] = {
    # Agricultura, silvicultura, pescuit
    "01": ["03", "16", "77"], "02": ["03", "77"], "03": ["03", "15"],
    # Industrie extractiva
    "05": ["09", "14"], "06": ["09"], "07": ["14"], "08": ["14", "44"], "09": ["09", "76"],
    # Alimentar, bauturi, tutun
    "10": ["15"], "11": ["15"], "12": ["15"],
    # Textile, imbracaminte, piele
    "13": ["19", "18"], "14": ["18"], "15": ["18", "19"],
    # Lemn, hartie, tiparire
    "16": ["03", "44"], "17": ["22", "44"], "18": ["22", "79"],
    # Chimie, farma, cauciuc, plastic
    "19": ["09"], "20": ["24"], "21": ["33", "24"], "22": ["44", "19"], "23": ["44"],
    # Metalurgie, produse metalice
    "24": ["44"], "25": ["44", "42"],
    # Electronice, electrice, echipamente
    "26": ["30", "32", "38"], "27": ["31"], "28": ["42", "43"],
    # Auto, alte mijloace de transport
    "29": ["34"], "30": ["34"],
    # Mobila, alte industrii, reparatii/instalare
    "31": ["39"], "32": ["33", "37", "39"], "33": ["50", "51"],
    # Utilitati (energie, apa, deseuri)
    "35": ["09", "31", "65"], "36": ["65"], "37": ["90"], "38": ["90"], "39": ["90"],
    # Constructii
    "41": ["45", "71"], "42": ["45"], "43": ["45", "44"],
    # Comert (auto, en-gros, en-detail)
    "45": ["34", "50"], "46": ["15", "30", "44"], "47": ["15", "30", "39"],
    # Transport, depozitare, posta
    "49": ["60", "34"], "50": ["60"], "51": ["60"], "52": ["63"], "53": ["64"],
    # Hoteluri, restaurante
    "55": ["55"], "56": ["55", "15"],
    # Editare, IT, telecom, servicii informatice
    "58": ["79", "22"], "59": ["92"], "60": ["92", "32"], "61": ["64", "32"],
    "62": ["72", "48"], "63": ["72", "48"],
    # Financiar, asigurari
    "64": ["66"], "65": ["66"], "66": ["66"],
    # Imobiliare
    "68": ["70"],
    # Profesional, stiintific, tehnic
    "69": ["79"], "70": ["79"], "71": ["71", "73"], "72": ["73"], "73": ["79"],
    "74": ["79", "92"], "75": ["85"],
    # Servicii administrative si suport
    "77": ["34", "70"], "78": ["79"], "79": ["63", "79"], "80": ["79"],
    "81": ["90", "77"], "82": ["79"],
    # Administratie publica
    "84": ["75"],
    # Educatie
    "85": ["80"],
    # Sanatate, asistenta sociala
    "86": ["85", "33"], "87": ["85"], "88": ["85"],
    # Arta, recreere
    "90": ["92"], "91": ["92"], "92": ["92"], "93": ["92", "37"],
    # Alte servicii
    "94": ["98"], "95": ["50"], "96": ["98", "90"],
}


def caen_to_cpv_prefixes(caen_code: str) -> list[str]:
    """Prefixele CPV (diviziune) orientative pentru o firma cu codul CAEN dat. [] daca necunoscut."""
    digits = "".join(c for c in str(caen_code or "") if c.isdigit())
    if len(digits) < 2:
        return []
    return CAEN_TO_CPV.get(digits[:2], [])
