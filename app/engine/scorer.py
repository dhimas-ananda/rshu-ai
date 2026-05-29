"""app/engine/scorer.py v3.2 — dengan temporal modifier"""
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
from .extractor import ConceptMatch

NEGATION_MULT  = -1.5
AMBIGUITY_MULT =  0.72
FUZZY_MULT     =  0.84

SOURCE_WEIGHTS = {
    "keluhan_utama":    3.0,
    "numeric":          2.5,
    "keluhan_menyertai":0.8,
    "exact":            1.0,
    "alias":            1.0,
    "keyword":          0.75,
    "coverage":         0.65,
    "fuzzy":            0.55,
}


@dataclass
class EvidenceItem:
    concept_id:   int
    concept_type: str
    tipe_gejala:  str
    matched_text: str
    match_source: str
    negated:      bool
    ambiguous:    bool
    fuzzy_score:  float
    bobot_khusus: float
    input_source: str = "exact"
    effective_score: float = 0.0

    def compute(self) -> float:
        base = self.bobot_khusus if self.bobot_khusus > 0 else (
            3.0 if self.tipe_gejala == "Mayor" else
            0.8 if self.concept_type == "risiko" else 1.0
        )
        if self.input_source == "keluhan_menyertai" and self.tipe_gejala == "Mayor":
            base = base * 0.35
        sw = SOURCE_WEIGHTS.get(self.input_source,
             SOURCE_WEIGHTS.get(self.match_source, 1.0))
        s = base * sw
        if self.ambiguous:          s *= AMBIGUITY_MULT
        if self.fuzzy_score < 1.0:  s *= (FUZZY_MULT + (1-FUZZY_MULT)*self.fuzzy_score)
        if self.negated:             s *= NEGATION_MULT
        self.effective_score = round(s, 4)
        return self.effective_score

    def explain(self) -> str:
        mark = "\u2717" if self.negated else "\u2713"
        tipe = "Faktor Risiko" if self.concept_type=="risiko" else f"Gejala {self.tipe_gejala}"
        src  = {"keluhan_utama":"keluhan utama","numeric":"numerik/TTV",
                "keluhan_menyertai":"keluhan menyertai"}.get(self.input_source,"")
        s = f"{mark} '{self.matched_text}' \u2192 {tipe}"
        if src: s += f" [{src}]"
        if self.match_source == "fuzzy": s += f" [fuzzy {self.fuzzy_score:.0%}]"
        if self.ambiguous: s += " [ambigu]"
        bw = f"{self.bobot_khusus:.2f}" if self.bobot_khusus > 0 else "default"
        s += f" (bobot={bw})"
        return s


@dataclass
class DiagnosisScore:
    id_diagnosa:     int
    kode_diagnosa:   str
    nama_diagnosa:   str
    evidence:        List[EvidenceItem] = field(default_factory=list)
    score:           float = 0.0
    positive_score:  float = 0.0
    negative_score:  float = 0.0
    mayor_score:     float = 0.0
    matched_mayor:   int   = 0
    matched_minor:   int   = 0
    matched_risiko:  int   = 0
    max_score:       float = 0.0
    max_mayor:       float = 0.0
    # Temporal modifier — diset dari luar setelah finalize
    temporal_modifier: float = 0.0
    temporal_context:  str   = ""

    def finalize(self):
        seen = set()
        for ev in self.evidence:
            key = (ev.concept_id, ev.concept_type)
            if key in seen: continue
            seen.add(key)
            s = ev.compute()
            self.score += s
            if s >= 0:
                self.positive_score += s
                if ev.concept_type == "gejala" and ev.tipe_gejala == "Mayor":
                    self.mayor_score += s
            else:
                self.negative_score += abs(s)
            if ev.concept_type == "gejala":
                if ev.tipe_gejala == "Mayor": self.matched_mayor += 1
                else:                          self.matched_minor += 1
            elif ev.concept_type == "risiko": self.matched_risiko += 1
        self.score = round(self.score, 3)

    def confidence(self) -> float:
        if self.max_score <= 0: return 0.03
        total_cov = self.positive_score / self.max_score
        mayor_cov = (self.mayor_score / self.max_mayor) if self.max_mayor > 0 else total_cov
        combined  = (mayor_cov * 0.65) + (total_cov * 0.35)
        bonus = 0.0
        if self.matched_mayor >= 3:   bonus += 0.10
        elif self.matched_mayor >= 2:  bonus += 0.07
        elif self.matched_mayor >= 1:  bonus += 0.04
        if self.matched_risiko:        bonus += 0.04
        total_abs = self.positive_score + self.negative_score
        penalty = 0.0
        if total_abs > 0 and (self.negative_score/total_abs) > 0.25:
            penalty = -0.12 * (self.negative_score/total_abs)
        # Temporal modifier ditambahkan di sini
        conf = combined + bonus + penalty + self.temporal_modifier
        return round(min(0.97, max(0.03, conf)), 3)

    def to_dict(self) -> dict:
        seen=set(); syms=[]; expl=[]
        for ev in self.evidence:
            if ev.matched_text not in seen:
                seen.add(ev.matched_text)
                syms.append(ev.matched_text); expl.append(ev.explain())
        # Tambahkan keterangan temporal ke explanation jika ada
        if self.temporal_context and self.temporal_modifier != 0:
            sign = "+" if self.temporal_modifier > 0 else ""
            expl.append(
                f"\u23f1 Konteks waktu: {self.temporal_context} "
                f"(confidence {sign}{self.temporal_modifier:+.0%})"
            )
        return {
            "id_diagnosa":       self.id_diagnosa,
            "kode_diagnosa":     self.kode_diagnosa,
            "nama_diagnosa":     self.nama_diagnosa,
            "score":             self.score,
            "confidence":        self.confidence(),
            "matched_major":     self.matched_mayor,
            "matched_minor":     self.matched_minor,
            "matched_risiko":    self.matched_risiko,
            "max_score":         round(self.max_score, 3),
            "mayor_coverage":    round(self.mayor_score/self.max_mayor,3) if self.max_mayor>0 else 0.0,
            "temporal_modifier": self.temporal_modifier,
            "matched_symptoms":  syms,
            "explanation":       expl,
        }


class EvidenceScorer:
    def __init__(self):
        self.concept_to_diagnoses: Dict = {}
        self.diagnosis_max_scores: Dict = {}
        self.diagnosis_max_mayor:  Dict = {}
        self.diagnosis_map:        Dict = {}

    def score(self, concepts: List[ConceptMatch],
              temporal=None) -> List[DiagnosisScore]:
        """
        Score semua konsep yang ditemukan.
        temporal: TemporalContext dari temporal_parser, atau None.
        """
        scores: Dict[int, DiagnosisScore] = {}
        for c in concepts:
            if c.concept_type == "penyebab": continue
            for rel in self.concept_to_diagnoses.get((c.concept_type, c.concept_id), []):
                did  = rel["id_diagnosa"]
                diag = self.diagnosis_map.get(did)
                if not diag: continue
                if did not in scores:
                    scores[did] = DiagnosisScore(
                        id_diagnosa=did,
                        kode_diagnosa=diag["kode_diagnosa"],
                        nama_diagnosa=diag["nama_diagnosa"],
                        max_score=self.diagnosis_max_scores.get(did, 0.0),
                        max_mayor=self.diagnosis_max_mayor.get(did, 0.0),
                    )
                tipe = "Mayor" if rel.get("tipe_gejala") == "Mayor" else "Minor"
                scores[did].evidence.append(EvidenceItem(
                    concept_id=c.concept_id, concept_type=c.concept_type,
                    tipe_gejala=tipe, matched_text=c.matched_text,
                    match_source=c.match_source, negated=c.negated,
                    ambiguous=c.ambiguous, fuzzy_score=c.fuzzy_score,
                    bobot_khusus=float(rel.get("bobot_khusus") or 0.0),
                    input_source=getattr(c, "input_source", c.match_source),
                ))

        for ds in scores.values():
            ds.finalize()
            # Terapkan temporal modifier
            if temporal is not None:
                from ..temporal_parser import get_temporal_modifier
                mod = get_temporal_modifier(temporal, ds.kode_diagnosa)
                ds.temporal_modifier = mod
                if mod != 0:
                    ds.temporal_context = str(temporal)

        return sorted(scores.values(),
                      key=lambda x: (x.confidence(), x.score, x.matched_mayor),
                      reverse=True)
