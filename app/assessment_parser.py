"""
app/assessment_parser.py v2.0
Konversi input terstruktur assessment perawat → teks klinis untuk engine AI.
Coverage diperluas untuk semua pola input umum perawat RSHU.
"""
from __future__ import annotations
from typing import Optional

# ── GCS ──────────────────────────────────────────────────────────
GCS_CATEGORY = [
    (13, 15, "composmentis",  "sadar penuh"),
    (10, 12, "somnolen",      "penurunan tingkat kesadaran"),
    (8,   9, "stupor",        "penurunan tingkat kesadaran berat"),
    (3,   7, "koma",          "tidak sadar penurunan tingkat kesadaran berat"),
]

def gcs_category(total):
    for lo,hi,name,desc in GCS_CATEGORY:
        if lo <= total <= hi:
            return name, desc
    return "tidak diketahui", ""

def gcs_to_text(e, v, m):
    total = e + v + m
    name, desc = gcs_category(total)
    # GCS normal (13-15): hanya kirim skor, tanpa label kesadaran
    if total >= 13:
        return f"GCS {total} E{e}V{v}M{m}"
    parts = [f"GCS {total} E{e}V{v}M{m}", f"kesadaran {name}",
             "penurunan tingkat kesadaran"]
    if total <= 8:
        parts.append("penurunan kesadaran berat")
    return ", ".join(parts)

# ── Kondisi Umum ─────────────────────────────────────────────────
KU_MAP = {
    "baik":                "",
    "cukup":               "tampak lemah",
    "cukup baik":          "tampak lemah",
    "sedang":              "tampak lemah",
    "lemah":               "tampak lemah, kelelahan, kondisi lemah",
    "buruk":               "tampak lemah, kondisi buruk, penurunan kondisi umum",
    "tidak sadar":         "penurunan tingkat kesadaran, tidak sadar",
    "sangat lemah":        "tampak lemah sangat, kondisi sangat buruk",
    "gelisah":             "gelisah, tidak tenang",
    "rewel":               "gelisah, rewel",
    "somnolen":            "somnolen, penurunan tingkat kesadaran",
    "apatis":              "apatis, kondisi menurun",
    "composmentis":        "",
    "cm":                  "",
}

# ── Mukosa ────────────────────────────────────────────────────────
MUKOSA_MAP = {
    "lembab":            "",
    "basah":             "",
    "normal":            "",
    "kering":            "mukosa kering, dehidrasi, membran mukosa kering",
    "agak kering":       "mukosa kering ringan",
    "sedikit kering":    "mukosa kering ringan",
    "sangat kering":     "mukosa sangat kering, dehidrasi berat",
    "pucat":             "mukosa pucat, anemia, membran mukosa pucat",
    "kemerahan":         "mukosa hiperemis",
    "hiperemis":         "mukosa hiperemis",
    "ikterik":           "mukosa ikterik, jaundice",
    "kering pucat":      "mukosa kering pucat, dehidrasi anemia",
    "pucat kering":      "mukosa kering pucat, dehidrasi anemia",
    "sianosis":          "mukosa sianosis, hipoksia",
}

# ── Turgor ────────────────────────────────────────────────────────
TURGOR_MAP = {
    "normal":            "",
    "baik":              "",
    "cepat":             "",
    "kembali cepat":     "",
    "<2":                "",
    "<2 detik":          "",
    "menurun":           "turgor kulit menurun, dehidrasi",
    "kurang":            "turgor kulit menurun",
    "agak menurun":      "turgor kulit sedikit menurun",
    "sedikit menurun":   "turgor kulit sedikit menurun",
    "lambat":            "turgor kulit menurun, dehidrasi",
    "kembali lambat":    "turgor kulit menurun, dehidrasi",
    "2-4":               "turgor kulit menurun",
    "2-4 detik":         "turgor kulit menurun, dehidrasi",
    "buruk":             "turgor kulit sangat menurun, dehidrasi berat",
    "sangat lambat":     "turgor kulit sangat menurun, dehidrasi berat",
    ">4":                "turgor kulit sangat menurun, dehidrasi berat",
    ">4 detik":          "turgor kulit sangat menurun, dehidrasi berat",
    "jelek":             "turgor kulit sangat menurun",
}

# ── Akral ─────────────────────────────────────────────────────────
AKRAL_MAP = {
    "ahkm":              "",
    "hkm":               "",
    "hangat kering merah": "",
    "hangat":            "",
    "normal":            "",
    "baik":              "",
    "akral baik":        "",
    "dingin":            "akral dingin, perfusi perifer tidak efektif",
    "akral dingin":      "akral dingin, perfusi perifer tidak efektif",
    "dingin kering":     "akral dingin, perfusi perifer tidak efektif",
    "dingin basah":      "akral dingin berkeringat, perfusi perifer tidak efektif",
    "dingin lembab":     "akral dingin lembab, perfusi perifer tidak efektif",
    "dingin pucat":      "akral dingin pucat, perfusi perifer tidak efektif",
    "pucat":             "akral pucat, perfusi perifer menurun",
    "sianosis":          "sianosis, akral sianotik, kulit kebiruan",
    "sianotik":          "sianosis, akral sianotik",
    "biru":              "sianosis akral, kulit kebiruan",
    "edema":             "edema pada ekstremitas",
    "bengkak":           "edema pada ekstremitas",
    "crt > 2":           "pengisian kapiler lambat, CRT memanjang",
    "crt >2":            "pengisian kapiler lambat, CRT memanjang",
    "crt > 3":           "pengisian kapiler sangat lambat, perfusi perifer tidak efektif",
    "crt >3":            "pengisian kapiler sangat lambat",
    "dingin pucat sianosis": "akral dingin pucat sianosis, perfusi perifer sangat tidak efektif",
}

# ── CRT ──────────────────────────────────────────────────────────
CRT_MAP = {
    "<2":             "",
    "<2 detik":       "",
    "2 detik":        "",
    "normal":         "",
    ">2":             "pengisian kapiler lambat, CRT memanjang",
    ">2 detik":       "pengisian kapiler lambat",
    "2-3 detik":      "pengisian kapiler lambat",
    "lambat":         "pengisian kapiler lambat",
    ">3":             "pengisian kapiler sangat lambat, perfusi perifer tidak efektif",
    ">3 detik":       "pengisian kapiler sangat lambat, perfusi perifer tidak efektif",
    "3 detik":        "pengisian kapiler lambat",
    "4 detik":        "pengisian kapiler sangat lambat",
    "sangat lambat":  "pengisian kapiler sangat lambat, perfusi perifer tidak efektif",
    "memanjang":      "pengisian kapiler lambat, CRT memanjang",
}

# ── Suara Napas ───────────────────────────────────────────────────
NAPAS_MAP = {
    "vesikuler":          "",
    "normal":             "",
    "bersih":             "",
    "jernih":             "",
    "ronkhi":             "ronkhi, suara napas tambahan ronkhi",
    "rh+":                "ronkhi",
    "rh +:":              "ronkhi",
    "ronkhi basah":       "ronkhi basah, cairan di saluran napas",
    "ronkhi kasar":       "ronkhi kasar, sekret di jalan napas",
    "ronkhi halus":       "ronkhi halus, cairan di alveoli",
    "krepitasi":          "krepitasi, ronkhi halus",
    "wheezing":           "wheezing, mengi, suara napas mengi",
    "wh+":                "wheezing",
    "mengi":              "mengi, wheezing",
    "ngik":               "mengi, wheezing",
    "stridor":            "stridor, suara napas stridor, obstruksi jalan napas",
    "stridor inspirasi":  "stridor, obstruksi jalan napas atas",
    "diminished":         "suara napas menurun, ekspansi paru berkurang",
    "menurun":            "suara napas menurun",
    "melemah":            "suara napas melemah, ekspansi paru berkurang",
    "tidak ada":          "suara napas tidak terdengar",
    "bronkial":           "suara napas bronkial, konsolidasi paru",
    "ronkhi wheezing":    "ronkhi, wheezing, suara napas tambahan",
    "rh+ wh+":            "ronkhi, wheezing",
    "rh- wh-":            "",
    "rh - wh -":          "",
    "retraksi":           "retraksi dada, penggunaan otot bantu napas",
    "napas cuping hidung": "napas cuping hidung, sesak napas",
    "takipnea":           "frekuensi napas cepat, takipnea",
    "sesak":              "sesak napas, dispnea",
    "ortopnea":           "ortopnea, sesak berbaring",
}

# ── Bising Usus ───────────────────────────────────────────────────
BU_MAP = {
    "normal":           "",
    "normoaktif":       "",
    "positif":          "",
    "ada":              "",
    "+":                "",
    "aktif":            "",
    "meningkat":        "bising usus meningkat, peristaltik meningkat",
    "hiperaktif":       "bising usus hiperaktif, peristaltik sangat meningkat",
    "bu meningkat":     "bising usus meningkat",
    "bu hiperaktif":    "bising usus hiperaktif",
    "bising usus +":    "",
    "bising usus meningkat": "bising usus meningkat, peristaltik meningkat",
    "menurun":          "bising usus menurun, peristaltik menurun",
    "hipoaktif":        "bising usus menurun, peristaltik menurun",
    "lemah":            "bising usus melemah",
    "bu menurun":       "bising usus menurun",
    "tidak ada":        "bising usus tidak terdengar, ileus",
    "absent":           "bising usus tidak terdengar, ileus",
    "bu -":             "bising usus tidak terdengar, ileus",
    "negatif":          "bising usus tidak terdengar",
    "-":                "bising usus tidak terdengar",
}

# ── Edema ─────────────────────────────────────────────────────────
EDEMA_MAP = {
    "tidak":            "",
    "tidak ada":        "",
    "negatif":          "",
    "-":                "",
    "minimal":          "edema minimal",
    "ringan":           "edema ringan",
    "+1":               "edema derajat 1, edema ringan",
    "+":                "edema ringan",
    "+1/4":             "edema ringan",
    "derajat 1":        "edema ringan",
    "sedang":           "edema sedang, pembengkakan",
    "+2":               "edema derajat 2, edema sedang",
    "+2/4":             "edema sedang",
    "derajat 2":        "edema sedang",
    "berat":            "edema berat, pembengkakan berat",
    "+3":               "edema derajat 3, edema berat",
    "+3/4":             "edema berat",
    "derajat 3":        "edema berat",
    "+4":               "edema derajat 4 anasarka, edema seluruh tubuh",
    "+4/4":             "edema anasarka, edema seluruh tubuh",
    "anasarka":         "edema anasarka, edema seluruh tubuh",
    "derajat 4":        "edema sangat berat, anasarka",
    "ekstremitas":      "edema pada ekstremitas",
    "kaki":             "edema kaki",
    "perifer":          "edema perifer",
    "bilateral":        "edema bilateral",
    "pitting":          "pitting edema",
    "non pitting":      "edema non pitting",
    "presacral":        "edema presacral",
    "pitting +1":       "pitting edema ringan",
    "pitting +2":       "pitting edema sedang",
    "pitting +3":       "pitting edema berat",
}

# ── Kondisi Kulit ─────────────────────────────────────────────────
KULIT_MAP = {
    "normal":           "",
    "baik":             "",
    "intak":            "",
    "utuh":             "",
    "pucat":            "kulit pucat, warna kulit pucat",
    "pucat keabu-abuan": "kulit pucat keabu, hipoperfusi",
    "ikterik":          "ikterik, kulit kuning, jaundice",
    "kuning":           "ikterik, jaundice, kulit kuning",
    "sianosis":         "sianosis, kulit kebiruan",
    "kebiruan":         "sianosis, kulit kebiruan",
    "biru":             "sianosis, kulit kebiruan",
    "lesi":             "lesi kulit, gangguan integritas kulit",
    "luka":             "luka, gangguan integritas kulit",
    "lecet":            "lecet, kerusakan integritas kulit",
    "eritema":          "eritema, kemerahan kulit",
    "ruam":             "ruam kulit",
    "rash":             "ruam kulit",
    "urtikaria":        "urtikaria, biduran",
    "gatal":            "pruritus, gatal",
    "kering":           "kulit kering",
    "bersisik":         "kulit bersisik, kering",
    "hangat":           "kulit hangat, suhu meningkat",
    "panas":            "kulit panas, suhu meningkat",
    "berkeringat":      "diaforesis, berkeringat",
    "diaphoresis":      "diaforesis, berkeringat berlebih",
    "dekubitus":        "luka dekubitus, tekanan, gangguan integritas kulit",
    "nekrotik":         "jaringan nekrotik, gangguan integritas jaringan",
    "ptekie":           "ptekie, bintik perdarahan",
    "ekimosis":         "ekimosis, memar",
    "hematom":          "hematoma, perdarahan bawah kulit",
    "bekas luka":       "jaringan parut, riwayat luka",
    "luka operasi":     "luka pasca operasi, insisi bedah",
    "jahitan":          "jahitan, luka pasca operasi",
    "lembab":           "",
    "merah":            "kemerahan kulit",
    "kehitaman":        "hiperpigmentasi, perubahan warna kulit",
}

# ── Abdomen ───────────────────────────────────────────────────────
ABDOMEN_MAP = {
    "normal":           "",
    "datar":            "",
    "flat":             "",
    "supel":            "",
    "lunak":            "",
    "lembut":           "",
    "tidak tegang":     "",
    "keras":            "abdomen keras, rigiditas abdomen",
    "tegang":           "abdomen tegang, rigiditas",
    "kembung":          "distensi abdomen, kembung",
    "distensi":         "distensi abdomen",
    "distensi abdomen": "distensi abdomen, perut membesar",
    "nyeri tekan":      "nyeri tekan abdomen",
    "nyeri tekan +":    "nyeri tekan abdomen",
    "nyeri tekan positif": "nyeri tekan abdomen",
    "defans":           "defans muskular, nyeri tekan berat",
    "defans muskular":  "defans muskular, rigiditas abdomen",
    "asites":           "asites, cairan bebas abdomen",
    "hepar teraba":     "hepatomegali, pembesaran hati",
    "lien teraba":      "splenomegali, pembesaran limpa",
    "massa":            "massa abdomen",
    "nyeri ulu hati":   "nyeri epigastrium",
    "epigastrik":       "nyeri epigastrium",
    "mcburney +":       "nyeri titik McBurney, appendisitis",
    "murphy +":         "nyeri murphy, kolesistitis",
    "blumberg +":       "nyeri lepas, peritonitis",
}

# ── Orientasi / Kesadaran ─────────────────────────────────────────
ORIENTASI_MAP = {
    "cm":                "",
    "compos mentis":     "",
    "composmentis":      "",
    "sadar":             "",
    "sadar baik":        "",
    "sadar penuh":       "",
    "alert":             "",
    "orientasi baik":    "",
    "apatis":            "apatis, kurang respon, kesadaran menurun ringan",
    "somnolen":          "somnolen, penurunan tingkat kesadaran",
    "mengantuk":         "somnolen, penurunan tingkat kesadaran ringan",
    "delirium":          "delirium, bingung, disorientasi, agitasi",
    "bingung":           "bingung, konfusi, disorientasi",
    "disorientasi":      "disorientasi, gangguan orientasi",
    "gelisah":           "gelisah, agitasi",
    "agitasi":           "agitasi, gelisah berlebihan",
    "stupor":            "stupor, penurunan kesadaran berat, respons hanya nyeri",
    "koma":              "koma, tidak sadar, penurunan tingkat kesadaran berat",
    "tidak sadar":       "penurunan tingkat kesadaran, tidak sadar",
    "setengah sadar":    "somnolen, penurunan tingkat kesadaran",
    "semi koma":         "stupor mendekati koma",
    "unresponsive":      "tidak merespons, koma",
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

def lookup(category, value):
    m = ALL_MAPS.get(category, {})
    key = value.lower().strip()
    return m.get(key, "")

def assessment_to_text(data):
    """Konversi dict assessment → teks klinis untuk engine AI."""
    # expand_free_text dipanggil untuk assessment_text di bawah
    parts = []
    ge = data.get("gcs_e"); gv = data.get("gcs_v"); gm = data.get("gcs_m")
    if ge and gv and gm:
        try: parts.append(gcs_to_text(int(ge), int(gv), int(gm)))
        except (ValueError, TypeError): pass
    for field, category in [
        ("kondisi_umum","kondisi_umum"), ("orientasi","orientasi"),
        ("mukosa","mukosa"),             ("turgor","turgor"),
        ("akral","akral"),               ("crt","crt"),
        ("suara_napas","suara_napas"),   ("bu","bu"),
        ("edema","edema"),               ("kulit","kulit"),
        ("abdomen","abdomen"),
    ]:
        val = data.get(field, "")
        if val:
            text = lookup(category, str(val))
            if text: parts.append(text)
    extra = data.get("assessment_text", "").strip()
    if extra:
        # Ekspansi singkatan sebelum append
        parts.append(expand_free_text(extra))
    return ", ".join(p for p in parts if p)


# ── Ekspansi singkatan teks bebas ────────────────────────────────
import re

_ABBREV_RULES = [
    # Format: (pattern, replacement)
    (re.compile(r"\bEks\.?\s+AHKM\b", re.I), ""),
    (re.compile(r"\bAHKM\b",          re.I), "akral hangat kering merah normal"),
    (re.compile(r"\bHKM\b",           re.I), "akral hangat kering merah normal"),
    (re.compile(r"\bRh\s*\+",        re.I), "ronkhi positif"),
    (re.compile(r"\bRh\s*-",          re.I), ""),
    (re.compile(r"\bWh\s*\+",        re.I), "wheezing positif"),
    (re.compile(r"\bWh\s*-",          re.I), ""),
    (re.compile(r"\bRh[-\s]*Wh[-\s]*([+-])", re.I), lambda m: "ronkhi wheezing" if m.group(1)=='+' else ""),
    (re.compile(r"\bBU\s+meningkat\b",  re.I), "bising usus meningkat"),
    (re.compile(r"\bBU\s+menurun\b",    re.I), "bising usus menurun"),
    (re.compile(r"\bBU\s+hiperaktif\b", re.I), "bising usus hiperaktif"),
    (re.compile(r"\bBU\s+[-]\b",        re.I), "bising usus tidak terdengar"),
    (re.compile(r"\bBU\b",               re.I), "bising usus"),
    (re.compile(r"\bCRT\s*>\s*3",       re.I), "pengisian kapiler sangat lambat"),
    (re.compile(r"\bCRT\s*>\s*2",       re.I), "pengisian kapiler lambat"),
    (re.compile(r"\bCRT\s*<\s*2",       re.I), ""),
    (re.compile(r"\bCRT\s+memanjang\b", re.I), "pengisian kapiler lambat"),
    (re.compile(r"\bCM\b"),                    "composmentis"),
    (re.compile(r"\bKU\s+lemah\b",      re.I), "kondisi umum lemah"),
    (re.compile(r"\bKU\s+sedang\b",     re.I), "kondisi umum lemah"),
    (re.compile(r"\bKU\s+baik\b",       re.I), ""),
    (re.compile(r"\bKU\s+buruk\b",      re.I), "kondisi umum buruk"),
    (re.compile(r"\bKU\b"),                    "kondisi umum"),
    (re.compile(r"\bDBN\b"),                   ""),
    (re.compile(r"\bTAK\b"),                   ""),
    (re.compile(r"\bAICD\s*\+",  re.I), "asimetri ikterik sianosis dispnea"),
    (re.compile(r"\bAICD\s*-",    re.I), ""),
    (re.compile(r"\bAICD\b",      re.I), ""),
    (re.compile(r"\bSupel\b",     re.I), ""),
    (re.compile(r"\bSupl\b",      re.I), ""),
    (re.compile(r"\bEks\s+AHKM\b", re.I), ""),
    (re.compile(r"\bNAD\b"),                   ""),
    (re.compile(r"\bNTE\b"),                   "tidak ada kelainan"),
    (re.compile(r"\bPtekie\s*\+", re.I), "ptekie, bintik perdarahan"),
    (re.compile(r"\bJVP\s+meningkat\b", re.I), "distensi vena jugular, JVP meningkat"),
    (re.compile(r"\bJVD\b",       re.I), "distensi vena jugular"),
    (re.compile(r"\bdistensi\s+vena\s+jugular\b", re.I), "distensi vena jugular, peningkatan tekanan vena"),
    (re.compile(r"\bOrtopnea\b",  re.I), "ortopnea, sesak saat berbaring"),
    (re.compile(r"\bNCH\b"),                   "napas cuping hidung, sesak napas"),
    (re.compile(r"\bNCH\b"), "pernapasan cuping hidung"),
    (re.compile(r"\bnapas(?:an)?\s+cuping(?:\s+hidung)?\b", re.I), "pernapasan cuping hidung"),
    (re.compile(r"\bretraksi\s+(dada|ics|intercostal)\b", re.I), "retraksi dada, penggunaan otot bantu napas"),
    (re.compile(r"\bPNH\b"),                   "napas cuping hidung"),
    (re.compile(r"\bS1S2\s+normal\b", re.I),  ""),
    (re.compile(r"\bmur\s*mur\b",    re.I),   "murmur jantung"),
    (re.compile(r"\bmurmur\b",        re.I),   "murmur jantung"),
    (re.compile(r"\bgallop\b",        re.I),   "irama gallop, gagal jantung"),
    (re.compile(r"\bsianosis\s+perifer\b", re.I), "sianosis perifer, akral kebiruan"),
    (re.compile(r"\bsianosis\s+sentral\b", re.I), "sianosis sentral, hipoksia berat"),
    (re.compile(r"\bdekubitus\b",     re.I), "luka dekubitus, gangguan integritas kulit"),
    (re.compile(r"\bmeringis\b",      re.I), "tampak meringis kesakitan"),
    (re.compile(r"\bluka\s+operasi\b", re.I), "luka pasca operasi"),
    (re.compile(r"\bbekas\s+(?:op|operasi)\b\s*\+?", re.I), "bekas operasi"),
    (re.compile(r"\bpus\s*\+",       re.I), "pus, infeksi, sekret purulen"),
    (re.compile(r"\bpus\s*-",         re.I), ""),
    (re.compile(r"\bod?ema\s+bilateral\b", re.I), "edema bilateral ekstremitas"),
    (re.compile(r"\bedema\s+pitting\s*\++(\d?)", re.I), lambda m: f"pitting edema +{m.group(1) or 1}"),
    (re.compile(r"\bmukosa\s+kering\b", re.I), "mukosa kering, dehidrasi"),
    (re.compile(r"\bmukosa\s+lembab\b", re.I), ""),
]

def expand_free_text(text):
    """Ekspansi singkatan dari teks bebas assessment perawat."""
    # Buang prefix "O:" dari catatan objektif (format IGD: "O: 456 KU lemah...")
    import re as _re3
    text = _re3.sub(r"^\s*O\s*:\s*\d*\s*", "", text, flags=_re3.IGNORECASE)
    # Buang "S:" prefix (catatan subjektif di IGD)
    text = _re3.sub(r"^\s*S\s*:\s*", "", text, flags=_re3.IGNORECASE)
    for pat, repl in _ABBREV_RULES:
        if callable(repl):
            text = pat.sub(repl, text)
        else:
            text = pat.sub(repl, text)
    return re.sub(r"\s+", " ", text).strip()
