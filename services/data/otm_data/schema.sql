CREATE TABLE IF NOT EXISTS candidates (
    cand_id      TEXT PRIMARY KEY,
    name         TEXT NOT NULL,
    party        TEXT,
    election_yr  INTEGER,
    office_state TEXT,
    office       TEXT,          -- 'H', 'S', 'P'
    district     TEXT,          -- zero-padded, e.g. '06'
    pcc_cmte_id  TEXT           -- principal campaign committee
);

CREATE TABLE IF NOT EXISTS committees (
    cmte_id TEXT PRIMARY KEY,
    name    TEXT NOT NULL,
    cand_id TEXT
);

CREATE TABLE IF NOT EXISTS candidate_committee (
    cand_id     TEXT NOT NULL,
    cmte_id     TEXT NOT NULL,
    cmte_type   TEXT,
    cmte_desig  TEXT,
    election_yr INTEGER,
    PRIMARY KEY (cand_id, cmte_id, election_yr)
);

CREATE TABLE IF NOT EXISTS contributions (
    sub_id        TEXT PRIMARY KEY,   -- FEC unique transaction id
    cmte_id       TEXT NOT NULL,
    name          TEXT,
    city          TEXT,
    state         TEXT,
    zip_code      TEXT,
    employer      TEXT,
    occupation    TEXT,
    transaction_dt DATE,
    amount        NUMERIC(14,2) NOT NULL,
    entity_type   TEXT,
    memo_cd       TEXT
);

CREATE INDEX IF NOT EXISTS idx_contrib_cmte ON contributions (cmte_id);
CREATE INDEX IF NOT EXISTS idx_candcmte_cand ON candidate_committee (cand_id);
CREATE INDEX IF NOT EXISTS idx_cand_office ON candidates (office, office_state, district, election_yr);
