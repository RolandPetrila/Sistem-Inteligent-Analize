-- 005: FTS5 Full-Text Search pentru companies
-- Fix: companies.id este TEXT (UUID), nu INTEGER — folosim FTS5 standalone cu cui UNINDEXED pentru join
-- Idempotent: DROP IF EXISTS la inceput pentru a permite re-rulare

-- Sterge tabela veche (si shadow tables) daca exista
DROP TABLE IF EXISTS companies_fts;
DROP TRIGGER IF EXISTS companies_fts_ai;
DROP TRIGGER IF EXISTS companies_fts_ad;
DROP TRIGGER IF EXISTS companies_fts_au;

-- FTS5 table standalone (fara content= care necesita INTEGER rowid)
-- cui e stocat UNINDEXED pentru join, dar nu e indexat full-text
CREATE VIRTUAL TABLE IF NOT EXISTS companies_fts USING fts5(
    cui UNINDEXED,
    name,
    caen_code,
    county,
    city,
    tokenize='unicode61'
);

-- Populeaza din date existente
INSERT INTO companies_fts(cui, name, caen_code, county, city)
SELECT cui,
       COALESCE(name, ''),
       COALESCE(caen_code, ''),
       COALESCE(county, ''),
       COALESCE(city, '')
FROM companies;

-- Trigger: INSERT
CREATE TRIGGER IF NOT EXISTS companies_fts_ai
AFTER INSERT ON companies BEGIN
    INSERT INTO companies_fts(cui, name, caen_code, county, city)
    VALUES (new.cui, COALESCE(new.name,''), COALESCE(new.caen_code,''), COALESCE(new.county,''), COALESCE(new.city,''));
END;

-- Trigger: DELETE
CREATE TRIGGER IF NOT EXISTS companies_fts_ad
AFTER DELETE ON companies BEGIN
    DELETE FROM companies_fts WHERE cui = old.cui;
END;

-- Trigger: UPDATE
CREATE TRIGGER IF NOT EXISTS companies_fts_au
AFTER UPDATE ON companies BEGIN
    DELETE FROM companies_fts WHERE cui = old.cui;
    INSERT INTO companies_fts(cui, name, caen_code, county, city)
    VALUES (new.cui, COALESCE(new.name,''), COALESCE(new.caen_code,''), COALESCE(new.county,''), COALESCE(new.city,''));
END;
