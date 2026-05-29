"""app/engine/extractor.py v2.3"""
from __future__ import annotations
import re
from dataclasses import dataclass
from typing import Dict, List, Optional, Set, Tuple
from .fuzzy import FuzzyIndex

NEG = frozenset({"tidak","tanpa","bukan","belum","ga","gak","nggak","tiada",
                 "tidak ada","tidak terdapat","tidak ditemukan","minus"})
STOP = frozenset({
    # Kata penghubung umum
    "dan","atau","yang","dengan","pada","di","ke","dari","untuk","dalam",
    "tidak","bukan","tanpa","juga","serta","namun","tetapi","sudah","telah",
    "sedang","akan","oleh","karena","akibat","seperti","bila","jika","ketika",
    "sangat","cukup","agak","sedikit","mis","misalnya","contoh","antara",
    "lain","saat","setelah","juga","namun","ada","adalah",
    # Kata narasi klinis yang tidak diagnostik (bukan nama gejala)
    "pasien","klien","penderita","px",           # subjek
    "dikeluhkan","didapatkan","dirasakan",       # pasif narasi
    "nampak","muncul","timbul","terjadi",        # kata umum
    "berupa","yaitu","yakni","misalnya","misal", # kata pengantar
    "merupakan","adanya","dilaporkan",           # kata sambung
})
FUZZY_THR = 0.68
KW_SCORE  = 0.58
COV_THR   = 0.60
COV_SCORE = 0.55


@dataclass
class ConceptMatch:
    concept_id:   int
    concept_type: str
    matched_text: str
    match_source: str
    negated:      bool  = False
    ambiguous:    bool  = False
    fuzzy_score:  float = 1.0
    raw_value:    Optional[str] = None
    input_source: str = "exact"

    def to_dict(self) -> dict:
        return {"concept_id":self.concept_id,"concept_type":self.concept_type,
                "matched_text":self.matched_text,"match_source":self.match_source,
                "negated":self.negated,"ambiguous":self.ambiguous,
                "fuzzy_score":round(self.fuzzy_score,3),"input_source":self.input_source}


def _has_neg(tokens: List[str], start: int, window: int = 5) -> bool:
    return any(t in NEG for t in tokens[max(0,start-window):start])


class ConceptExtractor:
    def __init__(self):
        self.phrase_entries:     List[Tuple[str,str,int,str]] = []
        self.phrase_to_concepts: Dict[str,List] = {}
        self.fuzzy_index:        FuzzyIndex = FuzzyIndex(FUZZY_THR)
        self._prefix_index:      Dict[str,List] = {}

    def build(self, entries: List[Tuple[str,str,int,str]]) -> None:
        self.phrase_entries=[]; self.phrase_to_concepts={}
        self.fuzzy_index=FuzzyIndex(FUZZY_THR); self._prefix_index={}
        for frasa,ctype,cid,source in entries:
            if not frasa or len(frasa)<3: continue
            toks=frasa.split()
            if all(t in STOP for t in toks): continue
            self.phrase_entries.append((frasa,ctype,cid,source))
            self.phrase_to_concepts.setdefault(frasa,[]).append((ctype,cid,source))
            self.fuzzy_index.add(frasa,{"concept_type":ctype,"concept_id":cid,"source":source})
            for tok in toks:
                if len(tok)>=4 and tok not in STOP:
                    self._prefix_index.setdefault(tok,[]).append((frasa,ctype,cid,source))
        self.phrase_entries.sort(key=lambda x:len(x[0]),reverse=True)

    def extract(self, norm_text:str, raw_text:str):
        concepts=[]; raw_vitals=[]; ambiguous=[]
        numeric,raw_vitals=self._extract_numeric(raw_text)
        concepts.extend(numeric)
        exact,used=self._extract_exact(norm_text)
        concepts.extend(exact)
        concepts.extend(self._extract_ngram(norm_text,used))
        concepts.extend(self._extract_keyword(norm_text,used))
        concepts.extend(self._extract_coverage(norm_text,used))
        if len({c.concept_id for c in concepts})<3:
            concepts.extend(self._extract_fuzzy(norm_text,used))
        for c in concepts:
            if c.ambiguous and c.matched_text not in ambiguous:
                ambiguous.append(c.matched_text)
        return concepts,raw_vitals,ambiguous

    def _extract_numeric(self,raw_text):
        try:
            from ..terminology import expand_shorthands
            from ..numeric_parser import extract_vitals,apply_thresholds
            exp=expand_shorthands(raw_text)
            vitals=extract_vitals(exp.lower())
            if not vitals: return [],[]
            nm_list,raw_vitals=apply_thresholds(vitals,self.phrase_to_concepts)
            concepts=[]
            for nm in nm_list:
                cands=self._lookup_canonical(nm.canonical)
                for ctype,cid,_ in cands:
                    c=ConceptMatch(concept_id=cid,concept_type=ctype,matched_text=nm.label,
                                   match_source="numeric",fuzzy_score=1.0,ambiguous=len(cands)>1,
                                   raw_value=f"{nm.vital.value}{nm.vital.unit}",input_source="numeric")
                    concepts.append(c)
            return concepts,raw_vitals
        except Exception: return [],[]

    def _lookup_canonical(self,canonical):
        if canonical in self.phrase_to_concepts: return self.phrase_to_concepts[canonical]
        cw=set(canonical.split()); best_n=0; best=[]
        for phrase,cands in self.phrase_to_concepts.items():
            n=len(cw&set(phrase.split()))
            if n>best_n: best_n=n; best=cands
        return best if best_n>=1 else []

    def _extract_exact(self,text):
        if not text: return [],[]
        tokens=text.split(); matches=[]; used=[]
        for frasa,ctype,cid,source in self.phrase_entries:
            for m in re.finditer(rf"\b{re.escape(frasa)}\b",text):
                span=m.span()
                if any(not(span[1]<=s or span[0]>=e) for s,e in used): continue
                before=len(text[:span[0]].split())
                cands=self.phrase_to_concepts.get(frasa,[(ctype,cid,source)])
                for ct,ci,sr in cands:
                    matches.append(ConceptMatch(concept_id=ci,concept_type=ct,matched_text=frasa,
                        match_source="exact" if sr=="master" else "alias",
                        negated=_has_neg(tokens,before),ambiguous=len(cands)>1,fuzzy_score=1.0))
                used.append(span); break
        return matches,used

    def _covered(self,text,spans):
        covered=set()
        if not spans: return covered
        tokens=text.split(); pos=0
        for i,tok in enumerate(tokens):
            try:
                ts=text.index(tok,pos); te=ts+len(tok); pos=te
                if any(ts>=s and te<=e for s,e in spans): covered.add(i)
            except ValueError: pass
        return covered

    def _extract_ngram(self,text,used):
        tokens=text.split(); covered=self._covered(text,used)
        matches=[]; added=set()
        for ws in (3,2,1):
            for i in range(len(tokens)-ws+1):
                wtoks=tokens[i:i+ws]
                if all((i+j) in covered for j in range(ws)): continue
                if all(t in STOP for t in wtoks): continue
                cand=" ".join(wtoks)
                if cand not in self.phrase_to_concepts: continue
                cands=self.phrase_to_concepts[cand]
                for ct,ci,sr in cands:
                    if (ct,ci) in added: continue
                    added.add((ct,ci))
                    matches.append(ConceptMatch(concept_id=ci,concept_type=ct,matched_text=cand,
                        match_source="exact" if sr=="master" else "alias",
                        negated=_has_neg(tokens,i),ambiguous=len(cands)>1,
                        fuzzy_score=1.0 if ws>=2 else KW_SCORE))
        return matches

    def _extract_keyword(self,text,used):
        tokens=text.split(); covered=self._covered(text,used)
        matches=[]; added=set()
        for i,tok in enumerate(tokens):
            if i in covered or len(tok)<4 or tok in STOP: continue
            if tok not in self._prefix_index: continue
            for frasa,ctype,cid,source in self._prefix_index[tok]:
                if cid in added: continue
                cands=self.phrase_to_concepts.get(frasa,[(ctype,cid,source)])
                matches.append(ConceptMatch(concept_id=cid,concept_type=ctype,matched_text=tok,
                    match_source="keyword",negated=_has_neg(tokens,i),
                    ambiguous=len(cands)>1,fuzzy_score=KW_SCORE))
                added.add(cid)
        return matches

    def _extract_coverage(self,text,used):
        tokens=text.split(); token_set=set(tokens)
        covered_f={text[s:e] for s,e in used}
        matches=[]; added=set()
        for frasa,ctype,cid,source in self.phrase_entries:
            if len(frasa.split())<2 or frasa in covered_f: continue
            ft=frasa.split(); content_ft=[t for t in ft if t not in STOP]
            if not content_ft: continue
            matched=[t for t in content_ft if t in token_set]
            cov=len(matched)/len(content_ft)
            if cov<COV_THR or cid in added: continue
            cands=self.phrase_to_concepts.get(frasa,[(ctype,cid,source)])
            for ct,ci,_ in cands:
                if ci not in added:
                    matches.append(ConceptMatch(concept_id=ci,concept_type=ct,
                        matched_text=" ".join(matched),match_source="coverage",
                        ambiguous=len(cands)>1,fuzzy_score=COV_SCORE*cov))
                    added.add(ci)
        return matches

    def _extract_fuzzy(self,text,used):
        tokens=text.split(); covered=self._covered(text,used)
        matches=[]; added=set()
        for i,tok in enumerate(tokens):
            if i in covered or len(tok)<4 or tok in STOP: continue
            for window in [tok,
                           f"{tok} {tokens[i+1]}" if i+1<len(tokens) else "",
                           f"{tok} {tokens[i+1]} {tokens[i+2]}" if i+2<len(tokens) else ""]:
                if not window: continue
                result=self.fuzzy_index.best_match(window)
                if not result: continue
                phrase,score,meta=result
                cid=meta["concept_id"]; ctype=meta["concept_type"]
                if cid in added: continue
                cands=self.phrase_to_concepts.get(phrase,[(ctype,cid,"fuzzy")])
                for ct,ci,_ in cands:
                    if ci not in added:
                        matches.append(ConceptMatch(concept_id=ci,concept_type=ct,matched_text=window,
                            match_source="fuzzy",negated=_has_neg(tokens,i),
                            ambiguous=len(cands)>1,fuzzy_score=score))
                        added.add(ci)
        return matches
