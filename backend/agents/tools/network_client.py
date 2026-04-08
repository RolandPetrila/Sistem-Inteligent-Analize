"""
Network Client — Retea de firme prin asociati/administratori comuni.
Phase R6 F1-3: Query SQL recursiv pe tabelul company_administrators.
Phase Gemini-3: NetworkX BFS depth-4 + Toxic PageRank.

Upgrade-uri:
- Traversal la adancime 4 (nu doar 1) folosind NetworkX + BFS
- Toxic PageRank: daca 30%+ din firmele unui nod-persoana sunt inactive/insolvente,
  orice firma noua cu acel asociat primeste flag TOXIC_NETWORK
- Detects shell companies: persoane cu 5+ firme active = potential conflict interes
"""

from loguru import logger

from backend.database import db

try:
    import networkx as nx
    _NX_AVAILABLE = True
except ImportError:
    _NX_AVAILABLE = False
    logger.warning("[network] networkx nu este instalat — depth-4 traversal dezactivat")


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


async def _load_full_network() -> tuple[dict, dict]:
    """
    Incarca toata reteaua din DB intr-o structura in-memory.
    Returns:
        cui_to_persons: {cui -> [person_name, ...]}
        person_to_cuis: {person_name -> [(cui, company_name, is_active), ...]}
    """
    rows = await db.fetch_all(
        """
        SELECT ca.cui, ca.person_name, ca.company_name, ca.role, c.is_active
        FROM company_administrators ca
        LEFT JOIN companies c ON c.cui = ca.cui
        """
    )

    cui_to_persons: dict[str, list[str]] = {}
    person_to_cuis: dict[str, list[tuple]] = {}

    for row in rows:
        cui = row["cui"]
        person = row["person_name"]
        company_name = row["company_name"] or "N/A"
        is_active = row["is_active"]

        if cui not in cui_to_persons:
            cui_to_persons[cui] = []
        if person not in cui_to_persons[cui]:
            cui_to_persons[cui].append(person)

        if person not in person_to_cuis:
            person_to_cuis[person] = []
        person_to_cuis[person].append((cui, company_name, is_active))

    return cui_to_persons, person_to_cuis


def _build_networkx_graph(
    cui_to_persons: dict,
    person_to_cuis: dict,
) -> "nx.Graph":
    """
    Construieste un graf bipartit: noduri de tip CUI si noduri de tip PERSON.
    Edge: (cui, person) daca persoana e asociata/administrator la firma.
    """
    G = nx.Graph()

    for cui, persons in cui_to_persons.items():
        G.add_node(f"c:{cui}", node_type="company")
        for person in persons:
            G.add_node(f"p:{person}", node_type="person")
            G.add_edge(f"c:{cui}", f"p:{person}")

    return G


def _bfs_depth4(G: "nx.Graph", start_cui: str, max_depth: int = 4) -> dict[str, int]:
    """
    BFS din nodul start_cui, returneaza {cui -> distanta} pentru toate firmele
    accesibile la adancimea <= max_depth.
    """
    start_node = f"c:{start_cui}"
    if start_node not in G:
        return {}

    visited: dict[str, int] = {}  # node -> depth
    queue = [(start_node, 0)]

    while queue:
        node, depth = queue.pop(0)
        if node in visited:
            continue
        visited[node] = depth

        if depth < max_depth:
            for neighbor in G.neighbors(node):
                if neighbor not in visited:
                    queue.append((neighbor, depth + 1))

    # Returneaza doar nodurile de tip company (nu persons), excluzand start
    result = {}
    for node, depth in visited.items():
        if node.startswith("c:") and node != start_node:
            cui = node[2:]
            result[cui] = depth

    return result


def _calculate_toxic_pagerank(
    person_to_cuis: dict,
    threshold: float = 0.30,
) -> set[str]:
    """
    Identifica persoane "toxice": asociate cu >threshold% firme inactive/insolvente.
    Returneaza setul de nume persoane toxice.
    """
    toxic_persons: set[str] = set()

    for person, cuis_info in person_to_cuis.items():
        if len(cuis_info) < 2:
            continue
        inactive_count = sum(1 for _, _, is_active in cuis_info if is_active == 0)
        total = len(cuis_info)
        if total > 0 and (inactive_count / total) >= threshold:
            toxic_persons.add(person)

    return toxic_persons


async def get_company_network(cui: str, max_depth: int = 4) -> dict:
    """
    Gaseste reteaua de firme conectate prin asociati/administratori comuni.

    Algoritm (upgrade NetworkX):
    1. Incarca toata reteaua din DB in memorie
    2. Construieste graf NetworkX bipartit (CUI <-> PERSON)
    3. BFS la adancime max_depth (default 4) din nodul firmei analizate
    4. Calculeaza Toxic PageRank per persoana
    5. Genereaza risk flags extinse

    Returns:
        dict cu: persons, related_companies, risk_flags, has_data, network_depth
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

    # Pas 2: Fallback SQL depth-1 (intotdeauna disponibil)
    person_names = [p["name"] for p in persons]
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

    # Grupare depth-1 pe firma
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
                "depth": 1,
            }
        companies_map[c]["persons"].append({
            "name": row["person_name"],
            "role": row["role"],
        })

    # Pas 3: NetworkX depth-4 traversal (daca disponibil)
    deep_companies: dict[str, int] = {}
    toxic_persons: set[str] = set()
    nx_stats: dict = {"available": _NX_AVAILABLE, "depth_used": 1}

    if _NX_AVAILABLE:
        try:
            cui_to_persons, person_to_cuis = await _load_full_network()

            if len(cui_to_persons) > 1:
                G = _build_networkx_graph(cui_to_persons, person_to_cuis)
                deep_companies = _bfs_depth4(G, cui, max_depth=max_depth)
                toxic_persons = _calculate_toxic_pagerank(person_to_cuis)
                nx_stats["depth_used"] = max_depth
                nx_stats["graph_nodes"] = G.number_of_nodes()
                nx_stats["graph_edges"] = G.number_of_edges()
                nx_stats["reachable_companies"] = len(deep_companies)

                # Adauga firmele gasite la depth > 1 care nu sunt in depth-1
                for deep_cui, depth in deep_companies.items():
                    if deep_cui not in companies_map and depth > 1:
                        # Gasim datele firmei din DB
                        company_row = await db.fetch_one(
                            "SELECT name, is_active FROM companies WHERE cui = ?",
                            (deep_cui,)
                        )
                        companies_map[deep_cui] = {
                            "cui": deep_cui,
                            "company_name": company_row["name"] if company_row else "N/A",
                            "persons": [],
                            "is_active": company_row["is_active"] if company_row else None,
                            "has_profile": company_row is not None,
                            "depth": depth,
                        }
                    elif deep_cui in companies_map:
                        companies_map[deep_cui]["depth"] = deep_companies[deep_cui]

        except Exception as e:
            logger.warning(f"[network] NetworkX traversal error: {e}")

    related_companies = list(companies_map.values())

    # Pas 4: Risk flags extinse
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

    # Toxic PageRank flags
    toxic_in_firm = [p["name"] for p in persons if p["name"] in toxic_persons]
    if toxic_in_firm:
        risk_flags.append({
            "type": "TOXIC_NETWORK",
            "severity": "RED",
            "detail": (
                f"Persoana(e) cu istoric toxic detectate: {', '.join(toxic_in_firm[:2])} "
                f"— asociate in trecut cu firme inactive (>30% din retea)"
            ),
        })

    # Shell company detection: persoane cu 5+ firme active = posibil conflict interes
    person_names_set = set(person_names)
    if _NX_AVAILABLE and "person_to_cuis" in dir():
        for person in person_names_set:
            cuis_info = person_to_cuis.get(person, [])  # type: ignore[name-defined]
            active_count = sum(1 for _, _, is_active in cuis_info if is_active != 0)
            if active_count >= 5:
                risk_flags.append({
                    "type": "CONFLICT_INTERESE",
                    "severity": "YELLOW",
                    "detail": f"{person} este asociat/administrator la {active_count} firme active simultan",
                })
                break  # un singur flag per analiza

    # Adancime maxima efectiva atinsa
    max_depth_reached = max((c.get("depth", 1) for c in related_companies), default=1)

    return {
        "has_data": True,
        "persons": persons,
        "related_companies": related_companies,
        "total_connected": len(related_companies),
        "risk_flags": risk_flags,
        "network_depth_reached": max_depth_reached,
        "toxic_persons": list(toxic_persons & set(person_names)),
        "stats": {
            "inactive": inactive_count,
            "unknown_status": unknown_count,
            "active": len(related_companies) - inactive_count - unknown_count,
            "depth_1": sum(1 for c in related_companies if c.get("depth", 1) == 1),
            "depth_2_plus": sum(1 for c in related_companies if c.get("depth", 1) > 1),
        },
        "nx_stats": nx_stats,
    }
