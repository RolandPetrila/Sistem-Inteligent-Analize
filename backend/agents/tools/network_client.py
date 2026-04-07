"""
Network Client — Retea de firme prin asociati/administratori comuni.
Phase R6 F1-3: Query SQL recursiv pe tabelul company_administrators.
"""

from loguru import logger

from backend.database import db


async def store_administrators(cui: str, company_name: str, administrators: list[dict]) -> None:
    """
    Stocheaza administratorii/asociatii unei firme in DB dupa fiecare analiza.
    Apelat din agent_official dupa obtinerea datelor openapi.ro.
    """
    if not cui or not administrators:
        return

    for person in administrators:
        name = person.get("name", "").strip()
        if not name:
            continue
        role = person.get("role", "administrator")
        ownership = person.get("ownership_pct", None)
        try:
            await db.execute(
                """
                INSERT INTO company_administrators (cui, company_name, person_name, role, ownership_pct, updated_at)
                VALUES (?, ?, ?, ?, ?, datetime('now'))
                ON CONFLICT(cui, person_name, role) DO UPDATE SET
                    company_name = excluded.company_name,
                    ownership_pct = excluded.ownership_pct,
                    updated_at = datetime('now')
                """,
                (cui, company_name, name, role, ownership),
            )
        except Exception as e:
            logger.debug(f"[network] store admin error for {cui}/{name}: {e}")

    logger.debug(f"[network] Stored {len(administrators)} persons for CUI {cui}")


async def get_company_network(cui: str) -> dict:
    """
    Gaseste reteaua de firme conectate prin asociati/administratori comuni.

    Algoritmul:
    1. Gaseste toti asociatii/administratorii firmei X (din DB)
    2. Gaseste toate celelalte firme unde aceste persoane mai apar
    3. Verifica statusul firmelor conexe (din companies table)
    4. Genereaza risk flags daca firme conexe sunt inactive/insolvente

    Returns:
        dict cu: persons, related_companies, risk_flags, has_data
    """
    if not cui:
        return {"has_data": False, "persons": [], "related_companies": [], "risk_flags": []}

    # Pas 1: Gaseste administratorii firmei curente
    persons_rows = await db.fetch_all(
        "SELECT person_name, role, ownership_pct FROM company_administrators WHERE cui = ?",
        (cui,)
    )

    if not persons_rows:
        return {
            "has_data": False,
            "persons": [],
            "related_companies": [],
            "risk_flags": [],
            "note": "Nu exista date despre administratori in DB — analizeaza firma intai",
        }

    persons = [
        {
            "name": row["person_name"],
            "role": row["role"],
            "ownership_pct": row["ownership_pct"],
        }
        for row in persons_rows
    ]
    person_names = [p["name"] for p in persons]

    # Pas 2: Gaseste firmele conexe (unde aceste persoane mai apar)
    if not person_names:
        return {"has_data": False, "persons": persons, "related_companies": [], "risk_flags": []}

    placeholders = ",".join(["?" for _ in person_names])
    related_rows = await db.fetch_all(
        f"""
        SELECT DISTINCT
            ca.cui,
            ca.company_name,
            ca.person_name,
            ca.role,
            c.last_analyzed_at,
            c.is_active
        FROM company_administrators ca
        LEFT JOIN companies c ON c.cui = ca.cui
        WHERE ca.person_name IN ({placeholders})
          AND ca.cui != ?
        ORDER BY ca.cui
        """,
        person_names + [cui],
    )

    # Grupare pe firma
    companies_map: dict[str, dict] = {}
    for row in related_rows:
        c = row["cui"]
        if c not in companies_map:
            companies_map[c] = {
                "cui": c,
                "company_name": row["company_name"] or "N/A",
                "persons": [],
                "is_active": row["is_active"],
                "has_profile": row["last_analyzed_at"] is not None,
            }
        companies_map[c]["persons"].append({
            "name": row["person_name"],
            "role": row["role"],
        })

    related_companies = list(companies_map.values())

    # Pas 3: Risk flags
    risk_flags = []
    inactive_count = sum(1 for c in related_companies if c.get("is_active") == 0)
    unknown_count = sum(1 for c in related_companies if c.get("is_active") is None)

    if any(c.get("is_active") == 0 for c in related_companies):
        inactive_names = [c["company_name"] for c in related_companies if c.get("is_active") == 0]
        risk_flags.append({
            "type": "ASOCIAT_FIRMA_INACTIVA",
            "severity": "RED" if inactive_count >= 2 else "YELLOW",
            "detail": f"Asociat comun cu {inactive_count} firma(e) inactiva(e): {', '.join(inactive_names[:3])}",
        })

    if len(related_companies) > 10:
        risk_flags.append({
            "type": "RETEA_EXTINSA",
            "severity": "YELLOW",
            "detail": f"Retea de {len(related_companies)} firme conexe — verifica conflicte de interes",
        })

    return {
        "has_data": True,
        "persons": persons,
        "related_companies": related_companies,
        "total_connected": len(related_companies),
        "risk_flags": risk_flags,
        "stats": {
            "inactive": inactive_count,
            "unknown_status": unknown_count,
            "active": len(related_companies) - inactive_count - unknown_count,
        },
    }
