"""app/engine/pipeline.py v3.2
Input AI:
  keluhan_utama     — gejala MAYOR + faktor risiko, bobot 3x
  keluhan_menyertai — gejala MINOR saja, bobot 0.8x
  text (TTV/nyeri)  — numerik terstruktur, bobot 2.5x
  kondisi_latar     — RPD/komorbiditas → HANYA faktor risiko, bobot 1.0x
BMI dihitung dari text jika ada BB dan TB.
"""
from __future__ import annotations
import logging
from typing import Dict, List, Tuple

logger = logging.getLogger(__name__)

def _run_query(sql, params=None):
    from psycopg2.extras import RealDictCursor
    from ..db import get_connection
    conn = get_connection()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(sql, params)
            return [dict(r) for r in cur.fetchall()]
    finally:
        conn.close()


class DiagnosisPipeline:
    def __init__(self):
        from .extractor import ConceptExtractor
        from .scorer import EvidenceScorer
        self.extractor = ConceptExtractor()
        self.scorer    = EvidenceScorer()
        self.loaded    = False
        self._stats    = {}

    def load_master_data(self):
        logger.info("Memuat master data v3.2...")
        diag_map = self._load_diagnoses()
        if not diag_map: raise RuntimeError("Tabel diagnosa kosong.")
        entries = self._load_gejala() + self._load_risiko()
        c2d, max_scores, max_mayor = self._load_relations(diag_map)
        self.extractor.build(entries)
        self.scorer.diagnosis_map        = diag_map
        self.scorer.concept_to_diagnoses = c2d
        self.scorer.diagnosis_max_scores = max_scores
        self.scorer.diagnosis_max_mayor  = max_mayor
        self.loaded = True
        self._stats = {
            "diagnosa":    len(diag_map),
            "frasa_unik":  len(self.extractor.phrase_to_concepts),
            "frasa_total": len(self.extractor.phrase_entries),
        }
        logger.info("v3.2 siap: %d diagnosa, %d frasa.", self._stats["diagnosa"], self._stats["frasa_unik"])

    def _load_diagnoses(self):
        try:
            rows = _run_query("SELECT id,kode,nama FROM diagnosa WHERE is_aktif=TRUE ORDER BY id")
            return {int(r["id"]): {"kode_diagnosa":r["kode"],"nama_diagnosa":r["nama"]} for r in rows}
        except Exception as exc: logger.error("Gagal load diagnosa: %s", exc); raise

    def _load_gejala(self):
        from .normalizer import normalize
        entries = []
        try:
            for r in _run_query("SELECT id,nama,norm FROM gejala WHERE is_aktif=TRUE ORDER BY id"):
                f = r["norm"] or normalize(r["nama"] or "")
                if f: entries.append((f,"gejala",int(r["id"]),"master"))
        except Exception as exc: logger.error("gejala: %s", exc)
        try:
            for r in _run_query(
                "SELECT id_gejala,alias_norm,alias_text FROM gejala_alias "
                "WHERE is_aktif=TRUE AND alias_norm IS NOT NULL AND LENGTH(alias_norm)>2 "
                "ORDER BY id_gejala,priority"):
                f = r["alias_norm"] or normalize(r["alias_text"] or "")
                if f: entries.append((f,"gejala",int(r["id_gejala"]),"alias"))
        except Exception as exc: logger.warning("alias gejala: %s", exc)
        return entries

    def _load_risiko(self):
        from .normalizer import normalize
        entries = []
        try:
            for r in _run_query("SELECT id,nama,norm FROM faktor_risiko WHERE is_aktif=TRUE ORDER BY id"):
                f = r["norm"] or normalize(r["nama"] or "")
                if f: entries.append((f,"risiko",int(r["id"]),"master"))
        except Exception as exc: logger.warning("faktor_risiko: %s", exc)
        try:
            for r in _run_query(
                "SELECT id_risiko,alias_norm,alias_text FROM faktor_risiko_alias "
                "WHERE is_aktif=TRUE AND alias_norm IS NOT NULL AND LENGTH(alias_norm)>3 "
                "ORDER BY id_risiko,priority"):
                f = r["alias_norm"] or normalize(r["alias_text"] or "")
                if f: entries.append((f,"risiko",int(r["id_risiko"]),"alias"))
        except Exception as exc: logger.warning("alias risiko: %s", exc)
        return entries

    def _load_relations(self, diag_map):
        c2d={}; max_scores={}; max_mayor={}
        try:
            for r in _run_query(
                "SELECT id_diagnosa,id_gejala,kelompok_gejala,"
                "COALESCE(bobot_khusus,0) AS bobot_khusus "
                "FROM diagnosa_gejala WHERE is_aktif=TRUE"):
                did=int(r["id_diagnosa"]); gid=int(r["id_gejala"])
                bk=float(r["bobot_khusus"] or 0)
                if did not in diag_map: continue
                tipe="Mayor" if (r["kelompok_gejala"] or "").lower()=="mayor" else "Minor"
                c2d.setdefault(("gejala",gid),[]).append(
                    {"id_diagnosa":did,"tipe_gejala":tipe,"bobot_khusus":bk})
                eff = bk if bk>0 else (3.0 if tipe=="Mayor" else 1.0)
                max_scores[did] = max_scores.get(did,0.0)+eff
                if tipe=="Mayor": max_mayor[did] = max_mayor.get(did,0.0)+eff
        except Exception as exc: logger.error("diagnosa_gejala: %s", exc)
        try:
            for r in _run_query(
                "SELECT id_diagnosa,id_risiko,"
                "COALESCE(bobot_khusus,0) AS bobot_khusus "
                "FROM diagnosa_risiko WHERE is_aktif=TRUE"):
                did=int(r["id_diagnosa"]); rid=int(r["id_risiko"])
                bk=float(r["bobot_khusus"] or 0)
                if did in diag_map:
                    c2d.setdefault(("risiko",rid),[]).append(
                        {"id_diagnosa":did,"tipe_gejala":"Minor","bobot_khusus":bk})
                    eff = bk if bk>0 else 0.6
                    max_scores[did] = max_scores.get(did,0.0)+eff
        except Exception as exc: logger.warning("diagnosa_risiko: %s", exc)
        return c2d, max_scores, max_mayor

    def predict(self, text:str="", top_k:int=149,
                keluhan_utama:str="",
                keluhan_menyertai:str="",
                kondisi_latar:str="") -> dict:
        """
        Input yang masuk AI:
          keluhan_utama     → Mayor gejala + faktor risiko, bobot 3x
          keluhan_menyertai → Minor gejala saja, bobot 0.8x
          text              → TTV + nyeri numerik, bobot 2.5x
          kondisi_latar     → Hanya faktor risiko (RPD, komorbiditas), bobot 1.0x
        """
        if not self.loaded: raise RuntimeError("Master data belum dimuat.")
        from .normalizer import normalize, strip_clinical_narr
        from ..temporal_parser import strip_temporal, extract_temporal

        ku_raw  = (keluhan_utama or text or "").strip()
        km_raw  = (keluhan_menyertai or "").strip()
        kl_raw  = (kondisi_latar or "").strip()
        num_raw = text.strip()  # untuk numerik TTV

        if not ku_raw and not num_raw and not km_raw:
            return self._empty_result()

        # Strip temporal dari keluhan (simpan teks asli untuk ekstrak waktu)
        # Strip narasi klinis dulu, lalu temporal
        ku_clean = strip_clinical_narr(ku_raw)
        km_clean = strip_clinical_narr(km_raw)
        ku_clean = strip_temporal(ku_clean)
        km_clean = strip_temporal(km_clean)

        norm_ku = normalize(ku_clean)
        norm_km = normalize(km_clean)

        all_concepts=[]; raw_vitals=[]; ambiguous=[]

        # ── 1. TTV/Nyeri numerik dari text ───────────────────
        if num_raw:
            cs, vt, _ = self.extractor.extract(normalize(num_raw), num_raw)
            for c in cs:
                if c.match_source == "numeric":
                    c.input_source = "numeric"
                    all_concepts.append(c)
            raw_vitals.extend(vt)

        # ── 2. Keluhan Utama: Mayor gejala + faktor risiko ───
        if norm_ku:
            cs, vt, ab = self.extractor.extract(norm_ku, ku_clean)
            for c in cs:
                # Keluhan utama: semua konsep diterima (gejala mayor/minor + risiko)
                # Scorer akan filter berdasarkan tipe_gejala
                c.input_source = "keluhan_utama"
            all_concepts.extend(cs)
            for v in vt:
                if v not in raw_vitals: raw_vitals.append(v)
            ambiguous.extend(ab)

        # ── 3. Keluhan Menyertai: Minor gejala saja ──────────
        if norm_km and norm_km != norm_ku:
            cs, _, _ = self.extractor.extract(norm_km, km_clean)
            for c in cs:
                c.input_source = "keluhan_menyertai"
                # Hanya gejala minor — risiko dari keluhan menyertai diabaikan
                if c.concept_type != "risiko":
                    all_concepts.append(c)

        # ── 4. Kondisi Latar: Hanya faktor risiko ────────────
        if kl_raw:
            kl_norm = normalize(strip_temporal(kl_raw))
            if kl_norm:
                cs, _, _ = self.extractor.extract(kl_norm, kl_raw)
                for c in cs:
                    if c.concept_type == "risiko":
                        c.input_source = "kondisi_latar"
                        all_concepts.append(c)

        # ── 5. BMI dari BB/TB di text ─────────────────────────
        bmi_concepts = self._extract_bmi(num_raw or ku_raw)
        all_concepts.extend(bmi_concepts)

        # ── 6. Temporal context ───────────────────────────────
        temporal = extract_temporal(ku_raw)
        if temporal:
            logger.info("Temporal: %s", temporal)

        # Score
        ranked = self.scorer.score(all_concepts, temporal=temporal)
        scored_ids = {ds.id_diagnosa for ds in ranked}
        unranked = sorted([
            {"id_diagnosa":did,"kode_diagnosa":info["kode_diagnosa"],
             "nama_diagnosa":info["nama_diagnosa"]}
            for did,info in self.scorer.diagnosis_map.items()
            if did not in scored_ids
        ], key=lambda x: x["kode_diagnosa"])

        top_list = [ds.to_dict() for ds in ranked]
        for u in unranked:
            top_list.append({
                "id_diagnosa":u["id_diagnosa"],"kode_diagnosa":u["kode_diagnosa"],
                "nama_diagnosa":u["nama_diagnosa"],"score":0.0,"confidence":0.0,
                "matched_major":0,"matched_minor":0,"matched_risiko":0,
                "max_score":round(self.scorer.diagnosis_max_scores.get(u["id_diagnosa"],0),3),
                "mayor_coverage":0.0,"matched_symptoms":[],"explanation":[],
            })
        best = top_list[0] if top_list and top_list[0]["confidence"]>0 else None
        return {
            "input_text":       ku_raw or num_raw,
            "normalized_text":  norm_ku,
            "matched_symptoms": self._out(all_concepts),
            "matched_vitals":   raw_vitals,
            "ambiguous_terms":  ambiguous,
            "top_diagnoses":    top_list[:top_k],
            "best_diagnosis":   best,
            "confidence":       best["confidence"] if best else 0.0,
            "message":          None if ranked else "Tidak ada bukti yang cocok.",
        }

    def _extract_bmi(self, text: str) -> list:
        """
        Ekstrak BB dan TB dari teks, hitung BMI, kembalikan concept matches.
        Contoh: "BB 85 TB 160" → BMI 33.2 → obesitas
        """
        if not text: return []
        import re
        from .extractor import ConceptMatch

        bb_m = re.search(r"(?:bb|berat badan)\s*:?\s*(\d+(?:[.,]\d+)?)", text, re.I)
        tb_m = re.search(r"(?:tb|tinggi badan)\s*:?\s*(\d+(?:[.,]\d+)?)", text, re.I)
        if not bb_m or not tb_m: return []

        try:
            bb = float(bb_m.group(1).replace(",","."))
            tb = float(tb_m.group(1).replace(",","."))
        except ValueError: return []

        # Pastikan satuan masuk akal
        if bb < 20 or bb > 300: return []
        if tb < 50:  tb = tb * 100  # kemungkinan input dalam meter
        if tb < 100 or tb > 250: return []

        bmi = round(bb / ((tb/100) ** 2), 1)
        logger.info("BMI dihitung: %.1f (BB=%.1f, TB=%.1f)", bmi, bb, tb)

        canonical = None
        label     = None
        if bmi < 17.0:
            canonical = "berat badan kurang"; label = f"Sangat kurus (BMI {bmi})"
        elif bmi < 18.5:
            canonical = "berat badan kurang"; label = f"Kurus (BMI {bmi})"
        elif bmi < 25.0:
            return []  # Normal — tidak perlu concept
        elif bmi < 27.0:
            canonical = "berat badan berlebih"; label = f"Overweight (BMI {bmi})"
        elif bmi < 30.0:
            canonical = "berat badan berlebih"; label = f"Obesitas I (BMI {bmi})"
        else:
            canonical = "berat badan berlebih"; label = f"Obesitas II (BMI {bmi})"

        if not canonical: return []

        cands = self.extractor._lookup_canonical(canonical)
        result = []
        for ctype, cid, _ in cands:
            result.append(ConceptMatch(
                concept_id=cid, concept_type=ctype,
                matched_text=label, match_source="numeric",
                fuzzy_score=1.0, ambiguous=len(cands)>1,
                raw_value=f"BMI={bmi}",
                input_source="numeric",
            ))
        return result

    def _empty_result(self):
        unranked = sorted([
            {"id_diagnosa":did,"kode_diagnosa":info["kode_diagnosa"],
             "nama_diagnosa":info["nama_diagnosa"]}
            for did,info in self.scorer.diagnosis_map.items()
        ], key=lambda x: x["kode_diagnosa"])
        top_list = [{
            "id_diagnosa":u["id_diagnosa"],"kode_diagnosa":u["kode_diagnosa"],
            "nama_diagnosa":u["nama_diagnosa"],"score":0.0,"confidence":0.0,
            "matched_major":0,"matched_minor":0,"matched_risiko":0,
            "max_score":0.0,"mayor_coverage":0.0,"matched_symptoms":[],"explanation":[],
        } for u in unranked]
        return {
            "input_text":"","normalized_text":"","matched_symptoms":[],
            "matched_vitals":[],"ambiguous_terms":[],"top_diagnoses":top_list,
            "best_diagnosis":None,"confidence":0.0,
            "message":"Tidak ada input yang bisa dianalisis.",
        }

    @staticmethod
    def _out(concepts):
        seen=set(); out=[]
        for c in concepts:
            key=(c.concept_id,c.concept_type,c.negated)
            if key in seen: continue
            seen.add(key)
            d=c.to_dict(); d["id_gejala"]=d.pop("concept_id"); d["source"]=d.pop("match_source")
            out.append(d)
        return out
