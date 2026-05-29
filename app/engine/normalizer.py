"""app/engine/normalizer.py"""
import re
import unicodedata

try:
    from ..terminology import apply_clinical_synonyms, expand_shorthands
except ImportError:
    def apply_clinical_synonyms(t): return t
    def expand_shorthands(t): return t

def _strip(t: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFKD", t)
                   if not unicodedata.combining(c))

def _clean_parens(t: str) -> str:
    t = re.sub(r"\s*\(\s*(?:mis\.?|misalnya|contoh|e\.g\.?|seperti|antara lain)[^)]*\)",
               "", t, flags=re.IGNORECASE)
    t = re.sub(r"\s*\([^)]{1,60}\)", "", t)
    return t.strip()

def normalize(raw: str) -> str:
    if not raw or not raw.strip(): return ""
    t = _clean_parens(raw)
    t = expand_shorthands(t)
    t = _strip(t.lower())
    t = re.sub(r"(\d),(\d)", r"\1.\2", t)
    t = re.sub(r"(\d)([a-z])", r"\1 \2", t)
    t = re.sub(r"([a-z])(\d)", r"\1 \2", t)
    t = t.replace("/", " ").replace("\\", " ")
    t = re.sub(r"[^a-z0-9\s.]", " ", t)
    t = re.sub(r"\.(?!\d)", " ", t)
    t = apply_clinical_synonyms(t)
    return re.sub(r"\s+", " ", t).strip()


# ── Frasa narasi klinis — dibuang sebelum tokenisasi ─────────────
# Kata-kata ini dipakai perawat sebagai pengantar narasi,
# tidak mengandung informasi diagnostik apapun.
# PENTING: frasa diproses SEBELUM tokenisasi agar tidak memecah
# gejala yang mengandung kata serupa (mis. "mengeluh nyeri" tetap utuh)

import re as _re

_NARR_PHRASES = [
    # Frasa "pasien/klien/penderita + kata kerja" — buang seluruh frasa
    _re.compile(r"\b(?:pasien|klien|penderita|px)\s+(?:mengeluh|menyatakan|"
                r"mengungkapkan|melaporkan|tampak|nampak|terlihat|merasa|"
                r"merasakan|mengalami|memiliki|menderita|datang dengan)\b",
                _re.IGNORECASE),
    # Kata subjek yang berdiri sendiri
    _re.compile(r"\b(?:pasien|klien|penderita|px)\b", _re.IGNORECASE),
    # Kata pasif/narasi yang tidak ada di master gejala
    _re.compile(r"\b(?:dikeluhkan|didapatkan|dirasakan|ditemukan(?:\s+adanya)?|"
                r"didapati|dilaporkan|disebutkan)\b", _re.IGNORECASE),
    # Kata penghubung narasi
    _re.compile(r"\b(?:berupa|yaitu|yakni|meliputi|antara\s+lain|"
                r"seperti\s+berikut|adalah|merupakan|di\s+antaranya)\b",
                _re.IGNORECASE),
    # Kata umum yang tidak diagnostik
    _re.compile(r"\b(?:nampak|muncul|timbul|terjadi|dirasakan)\b", _re.IGNORECASE),
]

# Token tunggal yang aman di-strip saat ada di STOP set extractor
CLINICAL_NARR_TOKENS = frozenset({
    "pasien","klien","penderita","px","dikeluhkan","didapatkan","dirasakan",
    "nampak","muncul","timbul","terjadi","berupa","yaitu","yakni","misalnya",
    "misal","adalah","merupakan","serta","adanya","adalah",
})

def strip_clinical_narr(text: str) -> str:
    """
    Buang frasa narasi klinis dari input perawat sebelum masuk engine.
    Contoh:
      "pasien mengeluh nyeri dada" → "nyeri dada"
      "tampak meringis, dikeluhkan sesak" → "tampak meringis, sesak"
      "didapatkan mual dan muntah" → "mual dan muntah"
    
    CATATAN: Fungsi ini TIDAK membuang "mengeluh", "tampak", "mengungkapkan"
    karena kata-kata ini ada di nama gejala master SDKI.
    """
    t = text
    for pat in _NARR_PHRASES:
        t = pat.sub(" ", t)
    return _re.sub(r"\s+", " ", t).strip()
