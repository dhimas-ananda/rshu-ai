"""app/engine/fuzzy.py"""
from typing import FrozenSet, List, Optional, Tuple

def _tri(text: str) -> FrozenSet[str]:
    p = f"## {text} ##"
    return frozenset(p[i:i+3] for i in range(len(p)-2))

class FuzzyIndex:
    def __init__(self, threshold: float = 0.68):
        self.threshold = threshold
        self._e: List[Tuple[str, FrozenSet[str], dict]] = []

    def add(self, phrase: str, meta: dict) -> None:
        if phrase and len(phrase) > 2:
            self._e.append((phrase, _tri(phrase), meta))

    def best_match(self, text: str) -> Optional[Tuple[str, float, dict]]:
        if not text or not self._e: return None
        qt = _tri(text); ql = len(qt)
        best_score = 0.0; best_phrase = None; best_meta = None
        for phrase, pt, meta in self._e:
            pl = len(pt)
            if pl == 0: continue
            if 2.0 * min(ql, pl) / (ql + pl) < self.threshold: continue
            s = 2.0 * len(qt & pt) / (ql + pl)
            if s >= self.threshold and s > best_score:
                best_score, best_phrase, best_meta = s, phrase, meta
        return (best_phrase, best_score, best_meta) if best_phrase else None
