"""
F8-1: Teste pentru modul funding_programs.
Testeaza matching programe finantare, filtrare, get_funding_summary.
"""
from backend.agents.tools.funding_programs import _load_programs, get_funding_summary, match_programs


class TestLoadPrograms:
    def test_incarca_programe(self):
        progs = _load_programs()
        assert isinstance(progs, list)
        assert len(progs) > 0

    def test_structura_program(self):
        progs = _load_programs()
        prog = progs[0]
        assert "id" in prog
        assert "nume" in prog
        assert "eligibilitate" in prog
        assert "activ" in prog

    def test_programe_active_exist(self):
        progs = _load_programs()
        active = [p for p in progs if p.get("activ")]
        assert len(active) > 0

    def test_toate_au_id_unic(self):
        progs = _load_programs()
        ids = [p["id"] for p in progs]
        assert len(ids) == len(set(ids))

    def test_cache_in_memory(self):
        # A doua apelare returneaza acelasi obiect (cache in-memory)
        progs1 = _load_programs()
        progs2 = _load_programs()
        assert progs1 is progs2


class TestMatchPrograms:
    def test_firma_it_eligibila(self):
        # Firma IT cu 5 angajati, 2 ani, fara datorii — eligibila la PNRR Digitalizare
        result = match_programs(caen_code="6201", angajati=5, vechime_ani=2, are_datorii_anaf=False)
        assert isinstance(result, list)
        # PNRR IMM Digitalizare trebuie sa apara (activ, regiuni=toate, CAEN 6201 nu e exclus)
        ids = [p["id"] for p in result]
        assert "pnrr_imm_digitalizare" in ids

    def test_firma_cu_datorii_exclude(self):
        # Firma cu datorii ANAF nu poate accesa fonduri (toate programele au datorii_anaf=False)
        result_fara = match_programs(caen_code="6201", angajati=5, vechime_ani=2, are_datorii_anaf=False)
        result_cu = match_programs(caen_code="6201", angajati=5, vechime_ani=2, are_datorii_anaf=True)
        # Firma cu datorii trebuie sa aiba mai putine sau egale optiuni
        assert len(result_cu) <= len(result_fara)

    def test_firma_cu_datorii_nu_primeste_programe(self):
        # Toate programele din JSON au datorii_anaf=false, deci cu datorii = 0 programe
        result = match_programs(caen_code="6201", angajati=5, vechime_ani=2, are_datorii_anaf=True)
        assert len(result) == 0

    def test_firma_mare_exclude_imm(self):
        # Firma cu 500 angajati depaseste angajati_max=249 pentru IMM
        result_mare = match_programs(caen_code="6201", angajati=500, vechime_ani=5, are_datorii_anaf=False)
        result_mica = match_programs(caen_code="6201", angajati=5, vechime_ani=5, are_datorii_anaf=False)
        # Firma mare are mai putine optiuni (exclude IMM-urile)
        assert len(result_mare) <= len(result_mica)
        # Firma mare (500) e sub 9999, dar peste 249 — deci nu prinde PNRR IMM
        ids_mare = [p["id"] for p in result_mare]
        assert "pnrr_imm_digitalizare" not in ids_mare

    def test_sortare_dupa_suma(self):
        result = match_programs(caen_code="0111", angajati=2, vechime_ani=1, are_datorii_anaf=False)
        if len(result) >= 2:
            sume = [p["suma_max_eur"] for p in result]
            assert sume == sorted(sume, reverse=True)

    def test_returneaza_campuri_obligatorii(self):
        result = match_programs(caen_code="6201", angajati=5, vechime_ani=2, are_datorii_anaf=False)
        for prog in result:
            assert "id" in prog
            assert "nume" in prog
            assert "suma_max_eur" in prog
            assert "link" in prog

    def test_returneaza_si_campuri_optionale(self):
        result = match_programs(caen_code="6201", angajati=5, vechime_ani=2, are_datorii_anaf=False)
        for prog in result:
            assert "termen" in prog
            assert "descriere" in prog
            assert "sursa" in prog

    def test_caen_exclus_6419(self):
        # CAEN 6419 e exclus din toate programele
        result = match_programs(caen_code="6419", angajati=5, vechime_ani=2, are_datorii_anaf=False)
        assert isinstance(result, list)
        # Nu trebuie sa apara niciun program care exclude 6419
        for prog in result:
            # Verifica ca nu au aparut programe care ar trebui sa excluda 6419
            assert prog["id"] not in [
                "pnrr_imm_digitalizare", "por_2021_competitivitate",
                "granturi_imm_2024", "hg_807_ajutor_stat"
            ]

    def test_program_inactiv_exclus(self):
        # startup_nation_2024 are activ=false — nu trebuie sa apara
        result = match_programs(caen_code="5811", angajati=1, vechime_ani=0, are_datorii_anaf=False)
        ids = [p["id"] for p in result]
        assert "startup_nation_2024" not in ids

    def test_program_expirat_exclus(self):
        # startup_nation_2024 are termen=2024-12-31 si activ=false — dublu exclus
        result = match_programs(caen_code="5811", angajati=1, vechime_ani=0, are_datorii_anaf=False)
        ids = [p["id"] for p in result]
        assert "startup_nation_2024" not in ids

    def test_angajati_zero_valide(self):
        # Firma cu 0 angajati (solo founder) — AFIR agricol accepta angajati_min=0
        result = match_programs(caen_code="0141", angajati=0, are_datorii_anaf=False)
        assert isinstance(result, list)
        ids = [p["id"] for p in result]
        assert "afir_masura_4_1" in ids

    def test_fara_parametri_nu_crapa(self):
        result = match_programs()
        assert isinstance(result, list)

    def test_caen_agricol_afir_eligibil(self):
        # CAEN 0111 e in caen_includ pt AFIR
        result = match_programs(caen_code="0111", angajati=5, vechime_ani=3, are_datorii_anaf=False)
        ids = [p["id"] for p in result]
        assert "afir_masura_4_1" in ids

    def test_caen_fara_program_specific(self):
        # CAEN IT nu e in caen_includ pt AFIR (lista includ restrictiva)
        result = match_programs(caen_code="6201", angajati=5, vechime_ani=3, are_datorii_anaf=False)
        ids = [p["id"] for p in result]
        assert "afir_masura_4_1" not in ids

    def test_vechime_prea_mica_exclus(self):
        # por_2021_competitivitate are vechime_ani_min=2
        result = match_programs(caen_code="1811", angajati=5, vechime_ani=0, are_datorii_anaf=False, regiune="NE")
        ids = [p["id"] for p in result]
        assert "por_2021_competitivitate" not in ids

    def test_regiune_leader_rural(self):
        # LEADER/GAL e disponibil doar in rural
        result_rural = match_programs(caen_code="5610", angajati=5, vechime_ani=1, are_datorii_anaf=False, regiune="rural")
        result_urban = match_programs(caen_code="5610", angajati=5, vechime_ani=1, are_datorii_anaf=False, regiune="B")
        ids_rural = [p["id"] for p in result_rural]
        ids_urban = [p["id"] for p in result_urban]
        assert "leader_gal" in ids_rural
        assert "leader_gal" not in ids_urban

    def test_suma_sortata_afir_primul(self):
        # AFIR are 1.5M EUR — trebuie sa fie primul daca e eligibil
        result = match_programs(caen_code="0111", angajati=5, vechime_ani=3, are_datorii_anaf=False)
        if result:
            assert result[0]["id"] == "afir_masura_4_1"
            assert result[0]["suma_max_eur"] == 1500000


class TestGetFundingSummary:
    def test_lista_vida_mesaj_standard(self):
        result = get_funding_summary([])
        assert "nu s-au identificat" in result.lower()

    def test_un_program_sumar_corect(self):
        prog = [{"id": "test", "nume": "Program Test", "suma_max_eur": 50000, "link": ""}]
        result = get_funding_summary(prog)
        assert "1" in result
        assert "Program Test" in result
        assert len(result) > 10

    def test_mai_multe_programe(self):
        progs = [
            {"id": f"p{i}", "nume": f"Prog {i}", "suma_max_eur": i * 10000, "link": ""}
            for i in range(5)
        ]
        result = get_funding_summary(progs)
        assert "5" in result
        assert len(result) > 10

    def test_suma_maxima_in_sumar(self):
        progs = [
            {"id": "p1", "nume": "Mare", "suma_max_eur": 200000, "link": ""},
            {"id": "p2", "nume": "Mic", "suma_max_eur": 5000, "link": ""},
        ]
        result = get_funding_summary(progs)
        # 200,000 formatat cu virgula sau punct
        assert "200" in result

    def test_top3_apar_in_sumar(self):
        progs = [
            {"id": "p1", "nume": "Alpha", "suma_max_eur": 100000, "link": ""},
            {"id": "p2", "nume": "Beta", "suma_max_eur": 80000, "link": ""},
            {"id": "p3", "nume": "Gamma", "suma_max_eur": 60000, "link": ""},
            {"id": "p4", "nume": "Delta", "suma_max_eur": 40000, "link": ""},
        ]
        result = get_funding_summary(progs)
        assert "Alpha" in result
        assert "Beta" in result
        assert "Gamma" in result
        # Delta e al 4-lea, nu apare in top3 dar apare in "+1 alte"
        assert "+1" in result

    def test_mai_mult_de_3_mentioneaza_restul(self):
        progs = [
            {"id": f"p{i}", "nume": f"Prog {i}", "suma_max_eur": 10000, "link": ""}
            for i in range(6)
        ]
        result = get_funding_summary(progs)
        # Trebuie sa mentioneze ca mai sunt alte 3 programe
        assert "+3" in result

    def test_exact_3_programe_fara_plus(self):
        progs = [
            {"id": f"p{i}", "nume": f"Prog {i}", "suma_max_eur": 10000, "link": ""}
            for i in range(3)
        ]
        result = get_funding_summary(progs)
        # Nu trebuie sa apara "+ alte programe"
        assert "+" not in result

    def test_returneaza_string(self):
        result = get_funding_summary([{"id": "x", "nume": "Y", "suma_max_eur": 1000, "link": ""}])
        assert isinstance(result, str)
