-- ================================================================
-- RSHU AI Diagnosa Keperawatan — Schema Produksi v3
-- PostgreSQL 14+
-- 15 tabel, 2 view, 1 fungsi norm_text()
-- Data SDKI disimpan persis dari sumber.
-- Kolom tambahan hanya: id (serial), norm, is_aktif
-- ================================================================

CREATE EXTENSION IF NOT EXISTS unaccent;
CREATE EXTENSION IF NOT EXISTS pg_trgm;

-- 1. diagnosa
CREATE TABLE diagnosa (
    id          SERIAL      PRIMARY KEY,
    kode_ref    VARCHAR(10) NOT NULL,
    kode        VARCHAR(10) NOT NULL,
    nama        TEXT        NOT NULL,
    kategori    VARCHAR(80),
    subkategori VARCHAR(80),
    definisi    TEXT,
    keterangan  TEXT,
    is_aktif    BOOLEAN     NOT NULL DEFAULT TRUE,
    CONSTRAINT uq_diagnosa_kode     UNIQUE (kode),
    CONSTRAINT uq_diagnosa_kode_ref UNIQUE (kode_ref)
);
CREATE INDEX idx_diagnosa_aktif ON diagnosa (is_aktif) WHERE is_aktif = TRUE;
CREATE INDEX idx_diagnosa_kat   ON diagnosa (kategori, subkategori);

-- 2. gejala
CREATE TABLE gejala (
    id          SERIAL      PRIMARY KEY,
    kode_ref    VARCHAR(10) NOT NULL,
    nama        TEXT        NOT NULL,
    norm        TEXT,
    tipe_bentuk VARCHAR(20) NOT NULL DEFAULT 'phrase',
    is_aktif    BOOLEAN     NOT NULL DEFAULT TRUE,
    CONSTRAINT uq_gejala_kode_ref UNIQUE (kode_ref)
);
CREATE UNIQUE INDEX idx_gejala_norm ON gejala (norm)
    WHERE norm IS NOT NULL AND norm <> '';
CREATE INDEX idx_gejala_aktif ON gejala (is_aktif) WHERE is_aktif = TRUE;

-- 3. gejala_alias
CREATE TABLE gejala_alias (
    id          SERIAL      PRIMARY KEY,
    id_gejala   INT         NOT NULL REFERENCES gejala(id) ON DELETE CASCADE,
    alias_text  TEXT        NOT NULL,
    alias_norm  TEXT        NOT NULL,
    alias_type  VARCHAR(40) NOT NULL DEFAULT 'variant',
    priority    SMALLINT    NOT NULL DEFAULT 5,
    is_aktif    BOOLEAN     NOT NULL DEFAULT TRUE
);
CREATE UNIQUE INDEX idx_gejala_alias_uniq ON gejala_alias (id_gejala, alias_norm)
    WHERE alias_norm <> '';
CREATE INDEX idx_gejala_alias_norm ON gejala_alias (alias_norm);
CREATE INDEX idx_gejala_alias_trgm ON gejala_alias USING gin (alias_norm gin_trgm_ops);

-- 4. diagnosa_gejala
-- kelompok_gejala: 'mayor'|'minor'
-- tipe_gejala: disimpan AS-IS dari SDKI (Objektif, Subjektif, Esofagus, dll)
CREATE TABLE diagnosa_gejala (
    id              SERIAL      PRIMARY KEY,
    kode_ref        VARCHAR(10) NOT NULL UNIQUE,
    id_diagnosa     INT         NOT NULL REFERENCES diagnosa(id) ON DELETE CASCADE,
    id_gejala       INT         NOT NULL REFERENCES gejala(id)   ON DELETE CASCADE,
    kelompok_gejala VARCHAR(10) NOT NULL DEFAULT 'minor',
    tipe_gejala     VARCHAR(40),
    bobot_khusus    NUMERIC(5,3)         DEFAULT NULL,  -- diisi dari Excel, NULL = fallback otomatis
    is_aktif        BOOLEAN     NOT NULL DEFAULT TRUE,
    CONSTRAINT uq_diag_gejala UNIQUE (id_diagnosa, id_gejala)
);
CREATE INDEX idx_dg_diagnosa ON diagnosa_gejala (id_diagnosa);
CREATE INDEX idx_dg_gejala   ON diagnosa_gejala (id_gejala);
CREATE INDEX idx_dg_kelompok ON diagnosa_gejala (id_diagnosa, kelompok_gejala);

-- 5. penyebab
CREATE TABLE penyebab (
    id          SERIAL      PRIMARY KEY,
    kode_ref    VARCHAR(10) NOT NULL,
    nama        TEXT        NOT NULL,
    norm        TEXT,
    tipe_bentuk VARCHAR(20) NOT NULL DEFAULT 'phrase',
    is_aktif    BOOLEAN     NOT NULL DEFAULT TRUE,
    CONSTRAINT uq_penyebab_kode_ref UNIQUE (kode_ref)
);
CREATE UNIQUE INDEX idx_penyebab_norm ON penyebab (norm)
    WHERE norm IS NOT NULL AND norm <> '';
CREATE INDEX idx_penyebab_aktif ON penyebab (is_aktif) WHERE is_aktif = TRUE;

-- 6. penyebab_alias
CREATE TABLE penyebab_alias (
    id          SERIAL      PRIMARY KEY,
    id_penyebab INT         NOT NULL REFERENCES penyebab(id) ON DELETE CASCADE,
    alias_text  TEXT        NOT NULL,
    alias_norm  TEXT        NOT NULL,
    alias_type  VARCHAR(40) NOT NULL DEFAULT 'variant',
    priority    SMALLINT    NOT NULL DEFAULT 5,
    is_aktif    BOOLEAN     NOT NULL DEFAULT TRUE
);
CREATE UNIQUE INDEX idx_penyebab_alias_uniq ON penyebab_alias (id_penyebab, alias_norm)
    WHERE alias_norm <> '';
CREATE INDEX idx_penyebab_alias_norm ON penyebab_alias (alias_norm);
CREATE INDEX idx_penyebab_alias_trgm ON penyebab_alias USING gin (alias_norm gin_trgm_ops);

-- 7. diagnosa_penyebab
CREATE TABLE diagnosa_penyebab (
    id          SERIAL      PRIMARY KEY,
    kode_ref    VARCHAR(10) NOT NULL UNIQUE,
    id_diagnosa INT         NOT NULL REFERENCES diagnosa(id)  ON DELETE CASCADE,
    id_penyebab INT         NOT NULL REFERENCES penyebab(id)  ON DELETE CASCADE,
    is_aktif    BOOLEAN     NOT NULL DEFAULT TRUE,
    CONSTRAINT uq_diag_penyebab UNIQUE (id_diagnosa, id_penyebab)
);
CREATE INDEX idx_dp_diagnosa ON diagnosa_penyebab (id_diagnosa);
CREATE INDEX idx_dp_penyebab ON diagnosa_penyebab (id_penyebab);

-- 8. faktor_risiko
CREATE TABLE faktor_risiko (
    id          SERIAL      PRIMARY KEY,
    kode_ref    VARCHAR(10) NOT NULL,
    nama        TEXT        NOT NULL,
    norm        TEXT,
    tipe_bentuk VARCHAR(20) NOT NULL DEFAULT 'phrase',
    is_aktif    BOOLEAN     NOT NULL DEFAULT TRUE,
    CONSTRAINT uq_risiko_kode_ref UNIQUE (kode_ref)
);
CREATE UNIQUE INDEX idx_risiko_norm ON faktor_risiko (norm)
    WHERE norm IS NOT NULL AND norm <> '';
CREATE INDEX idx_risiko_aktif ON faktor_risiko (is_aktif) WHERE is_aktif = TRUE;

-- 9. faktor_risiko_alias
CREATE TABLE faktor_risiko_alias (
    id          SERIAL      PRIMARY KEY,
    id_risiko   INT         NOT NULL REFERENCES faktor_risiko(id) ON DELETE CASCADE,
    alias_text  TEXT        NOT NULL,
    alias_norm  TEXT        NOT NULL,
    alias_type  VARCHAR(40) NOT NULL DEFAULT 'variant',
    priority    SMALLINT    NOT NULL DEFAULT 5,
    is_aktif    BOOLEAN     NOT NULL DEFAULT TRUE
);
CREATE UNIQUE INDEX idx_risiko_alias_uniq ON faktor_risiko_alias (id_risiko, alias_norm)
    WHERE alias_norm <> '';
CREATE INDEX idx_risiko_alias_norm ON faktor_risiko_alias (alias_norm);
CREATE INDEX idx_risiko_alias_trgm ON faktor_risiko_alias USING gin (alias_norm gin_trgm_ops);

-- 10. diagnosa_risiko
CREATE TABLE diagnosa_risiko (
    id          SERIAL      PRIMARY KEY,
    kode_ref    VARCHAR(10) NOT NULL UNIQUE,
    id_diagnosa INT         NOT NULL REFERENCES diagnosa(id)      ON DELETE CASCADE,
    id_risiko   INT         NOT NULL REFERENCES faktor_risiko(id) ON DELETE CASCADE,
    bobot_khusus    NUMERIC(5,3)         DEFAULT NULL,  -- diisi dari Excel, NULL = fallback otomatis
    is_aktif    BOOLEAN     NOT NULL DEFAULT TRUE,
    CONSTRAINT uq_diag_risiko UNIQUE (id_diagnosa, id_risiko)
);
CREATE INDEX idx_dr_diagnosa ON diagnosa_risiko (id_diagnosa);
CREATE INDEX idx_dr_risiko   ON diagnosa_risiko (id_risiko);

-- 11. numeric_rule
CREATE TABLE numeric_rule (
    id        SERIAL       PRIMARY KEY,
    param     VARCHAR(30)  NOT NULL,
    operator  VARCHAR(5)   NOT NULL,
    threshold NUMERIC(8,2) NOT NULL,
    unit      VARCHAR(20),
    label     TEXT         NOT NULL,
    norm_ref  TEXT         NOT NULL,
    kelompok  VARCHAR(10)  NOT NULL DEFAULT 'minor',
    bobot     SMALLINT     NOT NULL DEFAULT 1,
    layanan   VARCHAR(20)  NOT NULL DEFAULT 'semua',
    is_aktif  BOOLEAN      NOT NULL DEFAULT TRUE
);
CREATE INDEX idx_numrule_param ON numeric_rule (param, is_aktif);

-- 12. pengkajian
CREATE TABLE pengkajian (
    id         SERIAL      PRIMARY KEY,
    no_rm      VARCHAR(30),
    tgl        DATE        NOT NULL DEFAULT CURRENT_DATE,
    jam        TIME,
    jenis_form VARCHAR(20) NOT NULL DEFAULT 'dewasa',
    unit       VARCHAR(80),
    id_petugas VARCHAR(60),
    form_json  JSONB,
    status     VARCHAR(20) NOT NULL DEFAULT 'draft',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX idx_pengkajian_rm  ON pengkajian (no_rm);
CREATE INDEX idx_pengkajian_tgl ON pengkajian (tgl DESC);

-- 13. run_log
CREATE TABLE run_log (
    id              SERIAL      PRIMARY KEY,
    id_pengkajian   INT         REFERENCES pengkajian(id) ON DELETE SET NULL,
    input_text      TEXT        NOT NULL,
    normalized_text TEXT,
    top_diagnoses   JSONB       NOT NULL DEFAULT '[]',
    evidence        JSONB       NOT NULL DEFAULT '[]',
    confidence      NUMERIC(5,4),
    jenis_form      VARCHAR(20),
    model_version   VARCHAR(20) NOT NULL DEFAULT 'v2',
    latency_ms      INT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX idx_runlog_pengkajian ON run_log (id_pengkajian);
CREATE INDEX idx_runlog_created    ON run_log (created_at DESC);

-- 14. feedback
CREATE TABLE feedback (
    id              SERIAL      PRIMARY KEY,
    id_run          INT         NOT NULL REFERENCES run_log(id) ON DELETE CASCADE,
    id_diagnosa_gt  INT         REFERENCES diagnosa(id) ON DELETE SET NULL,
    is_correct      BOOLEAN,
    catatan         TEXT,
    pelapor         VARCHAR(80),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_feedback_run UNIQUE (id_run)
);
CREATE INDEX idx_feedback_correct ON feedback (is_correct);

-- 15. flag
CREATE TABLE flag (
    id            SERIAL      PRIMARY KEY,
    tabel         VARCHAR(30) NOT NULL,
    id_item       INT         NOT NULL,
    jenis         VARCHAR(30) NOT NULL,
    deskripsi     TEXT        NOT NULL,
    saran         TEXT,
    pelapor       VARCHAR(80),
    status        VARCHAR(20) NOT NULL DEFAULT 'pending',
    catatan_admin TEXT,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at    TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX idx_flag_status ON flag (status);
CREATE INDEX idx_flag_tabel  ON flag (tabel, id_item);

-- Fungsi normalisasi
CREATE OR REPLACE FUNCTION norm_text(t TEXT) RETURNS TEXT AS $$
BEGIN
    IF t IS NULL OR TRIM(t) = '' THEN RETURN ''; END IF;
    RETURN TRIM(regexp_replace(regexp_replace(
        lower(unaccent(t)),'[^a-z0-9\s]',' ','g'),'\s+',' ','g'));
END;
$$ LANGUAGE plpgsql IMMUTABLE;

-- View akurasi
CREATE OR REPLACE VIEW v_akurasi AS
SELECT d.kode, d.nama,
    COUNT(r.id) AS total,
    COUNT(f.id) FILTER (WHERE f.is_correct=TRUE)  AS benar,
    COUNT(f.id) FILTER (WHERE f.is_correct=FALSE) AS salah,
    ROUND(COUNT(f.id) FILTER (WHERE f.is_correct=TRUE)::NUMERIC
          / NULLIF(COUNT(f.id) FILTER (WHERE f.is_correct IS NOT NULL),0)*100,1) AS akurasi_pct,
    ROUND(AVG(r.confidence)::NUMERIC,3) AS avg_confidence
FROM run_log r
CROSS JOIN LATERAL (SELECT (r.top_diagnoses->0->>'id')::INT AS id_d) best
JOIN diagnosa d ON d.id = best.id_d
LEFT JOIN feedback f ON f.id_run = r.id
GROUP BY d.kode, d.nama ORDER BY total DESC;

-- View coverage alias
CREATE OR REPLACE VIEW v_alias_coverage AS
SELECT g.kode_ref, g.nama, g.tipe_bentuk,
    COUNT(a.id) AS jumlah_alias,
    COUNT(a.id) FILTER (WHERE a.is_aktif) AS alias_aktif
FROM gejala g
LEFT JOIN gejala_alias a ON a.id_gejala = g.id
WHERE g.is_aktif = TRUE
GROUP BY g.id, g.kode_ref, g.nama, g.tipe_bentuk
ORDER BY jumlah_alias DESC;

-- ================================================================
-- Selesai — 15 tabel, 2 view, 1 fungsi
-- ================================================================
