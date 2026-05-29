"""
app/assessment_parser.py
Konversi input terstruktur assessment perawat → teks klinis untuk engine AI.

Assessment adalah temuan OBJEKTIF dari perawat — berbeda dengan keluhan subjektif pasien.
Semua output mapping ke gejala Objektif di SDKI.
"""
from __future__ import annotations
from typing import Optional

# ── GCS (Glasgow Coma Scale) ─────────────────────────────────────
GCS_E = {4:"spontan", 3:"terhadap suara", 2:"terhadap nyeri", 1:"tidak ada"}
GCS_V = {5:"orientasi baik", 4:"bingung", 3:"kata tidak tepat", 2:"suara saja", 1:"tidak ada"}
GCS_M = {6:"mengikuti perintah", 5:"lokalisir nyeri", 4:"fleksi normal",
         3:"fleksi abnormal", 2:"ekstensi", 1:"tidak ada"}

GCS_CATEGORY = {
    (13, 15): ("composmentis",     "CM",    "sadar penuh"),
    (10, 12): ("somnolen",         "somnolen", "kesadaran menurun ringan"),
    (8,  9):  ("stupor",           "stupor",   "kesadaran menurun sedang"),
    (3,  7):  ("koma",             "koma",     "tidak sadar"),
}

def gcs_category(total: int) -> tuple:
    for (lo, hi), info in GCS_CATEGORY.items():
        if lo <= total <= hi:
            return info
    return ("tidak diketahui", "", "")

def gcs_to_text(e: int, v: int, m: int) -> str:
    """Konversi GCS E/V/M ke teks klinis yang bisa dicocokkan engine."""
    total = e + v + m
    cat_name, cat_abbr, cat_desc = gcs_category(total)
    parts = [f"GCS {total} E{e}V{v}M{m}"]
    parts.append(f"kesadaran {cat_name}")
    if total <= 12:
        parts.append("penurunan tingkat kesadaran")
    if total <= 8:
        parts.append("penurunan kesadaran berat")
    return ", ".join(parts)

# ── Kondisi Umum ─────────────────────────────────────────────────
KU_MAP = {
    "baik":        "",                          # normal, tidak perlu ditambah ke engine
    "cukup":       "tampak lemah",
    "cukup baik":  "tampak lemah",
    "lemah":       "tampak lemah, kelelahan, kondisi lemah",
    "buruk":       "tampak lemah, kondisi buruk, penurunan kondisi umum",
    "tidak sadar": "penurunan tingkat kesadaran, tidak sadar",
}

# ── Mukosa ────────────────────────────────────────────────────────
MUKOSA_MAP = {
    "lembab":       "",              # normal
    "normal":       "",
    "kering":       "mukosa kering, dehidrasi",
    "sangat kering":"mukosa sangat kering, dehidrasi berat",
    "pucat":        "mukosa pucat, anemia",
    "kemerahan":    "mukosa hiperemis",
}

# ── Turgor Kulit ─────────────────────────────────────────────────
TURGOR_MAP = {
    "normal":    "",
    "menurun":   "turgor kulit menurun, dehidrasi",
    "buruk":     "turgor kulit sangat menurun, dehidrasi berat",
    "<2":        "",
    "2-4":       "turgor kulit menurun",
    ">4":        "turgor kulit sangat menurun",
}

# ── Akral / CRT ──────────────────────────────────────────────────
AKRAL_MAP = {
    "ahkm":          "",             # aktif hangat kering merah = normal
    "normal":        "",
    "hangat":        "",
    "dingin":        "akral dingin, perfusi perifer tidak efektif",
    "pucat":         "akral pucat, perfusi perifer menurun",
    "sianosis":      "sianosis, akral sianotik, kulit kebiruan",
    "edema":         "edema pada ekstremitas",
    "dingin pucat":  "akral dingin pucat, perfusi perifer tidak efektif",
}

CRT_MAP = {
    "<2":  "",               # normal
    "2":   "",
    ">2":  "pengisian kapiler lambat, CRT memanjang",
    ">3":  "pengisian kapiler sangat lambat, perfusi perifer tidak efektif",
    "3":   "pengisian kapiler lambat",
    "4":   "pengisian kapiler sangat lambat",
}

# ── Suara Napas ───────────────────────────────────────────────────
NAPAS_MAP = {
    "vesikuler":   "",
    "normal":      "",
    "ronkhi":      "ronkhi, suara napas tambahan ronkhi",
    "rh+":         "ronkhi",
    "wheezing":    "wheezing, mengi, suara napas mengi",
    "wh+":         "wheezing",
    "stridor":     "stridor, suara napas stridor",
    "diminished":  "suara napas menurun",
    "ronkhi wheezing": "ronkhi, wheezing",
    "rh+ wh+":    "ronkhi, wheezing",
}

# ── Bising Usus ───────────────────────────────────────────────────
BU_MAP = {
    "normal":      "",
    "meningkat":   "bising usus meningkat, peristaltik meningkat",
    "hiperaktif":  "bising usus hiperaktif, peristaltik meningkat",
    "menurun":     "bising usus menurun, peristaltik menurun",
    "hipoaktif":   "bising usus menurun",
    "tidak ada":   "bising usus tidak terdengar, ileus",
    "absent":      "bising usus tidak terdengar",
}

# ── Edema ─────────────────────────────────────────────────────────
EDEMA_MAP = {
    "tidak":       "",
    "tidak ada":   "",
    "+1":          "edema ringan",
    "+2":          "edema sedang",
    "+3":          "edema berat",
    "+4":          "edema berat, anasarka",
    "anasarka":    "edema seluruh tubuh, anasarka",
    "ekstremitas": "edema pada ekstremitas",
    "kaki":        "edema kaki",
}

# ── Kondisi Kulit ─────────────────────────────────────────────────
KULIT_MAP = {
    "normal":   "",
    "pucat":    "kulit pucat",
    "ikterik":  "ikterik, kulit kuning, jaundice",
    "sianosis": "sianosis, kulit kebiruan",
    "lesi":     "lesi kulit, gangguan integritas kulit",
    "luka":     "luka, gangguan integritas kulit",
    "kering":   "kulit kering",
    "gatal":    "pruritus, gatal",
}

# ── Distensi Abdomen ──────────────────────────────────────────────
ABDOMEN_MAP = {
    "normal":  "",
    "supel":   "",             # supel = lembut/normal
    "keras":   "abdomen keras, rigiditas",
    "kembung": "distensi abdomen, kembung",
    "distensi":"distensi abdomen",
    "nyeri tekan": "nyeri tekan abdomen",
    "defans":  "defans muskular, nyeri tekan hebat",
}

# ── Orientasi / Tingkat Kesadaran ────────────────────────────────
ORIENTASI_MAP = {
    "cm":           "",               # compos mentis = normal
    "compos mentis":"",
    "composmentis": "",
    "sadar":        "",
    "somnolen":     "somnolen, penurunan tingkat kesadaran",
    "apatis":       "apatis, penurunan kesadaran ringan",
    "delirium":     "delirium, bingung, disorientasi",
    "stupor":       "stupor, penurunan kesadaran berat",
    "koma":         "koma, tidak sadar, penurunan tingkat kesadaran berat",
    "tidak sadar":  "penurunan tingkat kesadaran, tidak sadar",
}

# ── Master mapping ────────────────────────────────────────────────
ALL_MAPS = {
    "kondisi_umum": KU_MAP,
    "mukosa":       MUKOSA_MAP,
    "turgor":       TURGOR_MAP,
    "akral":        AKRAL_MAP,
    "crt":          CRT_MAP,
    "suara_napas":  NAPAS_MAP,
    "bu":           BU_MAP,
    "edema":        EDEMA_MAP,
    "kulit":        KULIT_MAP,
    "abdomen":      ABDOMEN_MAP,
    "orientasi":    ORIENTASI_MAP,
}

def lookup(category: str, value: str) -> str:
    """Lookup teks klinis dari kategori dan nilai."""
    m = ALL_MAPS.get(category, {})
    key = value.lower().strip()
    return m.get(key, "")

def assessment_to_text(data: dict) -> str:
    """
    Konversi dict assessment terstruktur → teks klinis untuk engine AI.
    
    Contoh input:
      {"gcs_e": 4, "gcs_v": 4, "gcs_m": 6,
       "kondisi_umum": "lemah", "mukosa": "kering",
       "akral": "dingin", "bu": "meningkat"}
    
    Output: "GCS 14 E4V4M6 somnolen, tampak lemah, mukosa kering, ..."
    """
    parts = []

    # GCS
    ge = data.get("gcs_e"); gv = data.get("gcs_v"); gm = data.get("gcs_m")
    if ge and gv and gm:
        try:
            parts.append(gcs_to_text(int(ge), int(gv), int(gm)))
        except (ValueError, TypeError): pass

    # Field lainnya
    for field, category in [
        ("kondisi_umum", "kondisi_umum"),
        ("mukosa",       "mukosa"),
        ("turgor",       "turgor"),
        ("akral",        "akral"),
        ("crt",          "crt"),
        ("suara_napas",  "suara_napas"),
        ("bu",           "bu"),
        ("edema",        "edema"),
        ("kulit",        "kulit"),
        ("abdomen",      "abdomen"),
        ("orientasi",    "orientasi"),
    ]:
        val = data.get(field, "")
        if val:
            text = lookup(category, val)
            if text: parts.append(text)

    # Teks bebas tambahan dari perawat
    extra = data.get("assessment_text", "").strip()
    if extra: parts.append(extra)

    return ", ".join(p for p in parts if p)


# ── Ekspansi singkatan assessment ────────────────────────────────
# Singkatan yang SERING dipakai perawat di kolom teks bebas
ASSESSMENT_ABBREV = {
    r"\bCM\b":          "composmentis",
    r"\bKU\b":          "kondisi umum",
    r"\bBU\b":          "bising usus",
    r"\bBUH\b":         "bising usus hiperaktif",
    r"\bCRT\b":         "capillary refill time",
    r"\bAHKM\b":        "akral hangat kering merah",
    r"\bRh\+":          "ronkhi positif",
    r"\bRh-":           "ronkhi negatif tidak ada",
    r"\bWh\+":          "wheezing positif",
    r"\bWh-":           "wheezing negatif tidak ada",
    r"\bDBN\b":         "dalam batas normal",
    r"\bSPO2\b":        "saturasi oksigen",
    r"\bSpO2\b":        "saturasi oksigen",
    r"\bGCS\b":         "GCS",
    r"\bTD\b":          "tekanan darah",
    r"\bN\b(?=\s*\d)":  "nadi",
    r"\bS\b(?=\s*\d{2})":"suhu",
    r"\bRR\b":          "frekuensi napas",
    r"\bHR\b":          "nadi",
    r"\bAICD\b":        "asimetri ikterik sianosis dyspnea",
    r"\bTTV\b":         "tanda-tanda vital",
    r"\bHKL\b":         "hangat kering lembab",
    r"\bEKS\b":         "ekstremitas",
    r"\bExt\b":         "ekstremitas",
    r"\bsupl\b":        "supel",
    r"\bSupel\b":       "supel",
    r"\bTAK\b":         "tidak ada kelainan",
    r"\bNAD\b":         "tidak ada deformitas",
    r"\bTPF\b":         "tidak dapat diraba",
    r"\bPKT\b":         "produksi keringat tinggi",
    r"\bKPS\b":         "kondisi psikologis stabil",
}
