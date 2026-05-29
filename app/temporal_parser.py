"""
app/temporal_parser.py v2.0

Perubahan dari v1:
- strip_temporal() membuang ekspresi waktu dari teks sebelum masuk engine
  sehingga "sejak 3 hari" tidak menembak gejala yang mengandung kata "hari"
- Threshold lama/sebentar bersifat kontekstual per KELOMPOK KONDISI
  bukan satu angka global
- Kata waktu dalam input HANYA dipakai sebagai modifier confidence,
  tidak pernah dicocokkan ke gejala
"""
from __future__ import annotations
import re
from dataclasses import dataclass
from typing import Optional, Tuple

# ── Pola ekspresi waktu yang harus DI-STRIP dari teks ─────────────
# Semua pola ini dibuang sebelum teks masuk ke engine matching.
_STRIP_PATTERNS = [
    # Pola komprehensif: "sejak/sudah [durasi/kata_waktu] lalu/yang lalu/terakhir"
    # Harus diproses PERTAMA sebelum pola individual
    re.compile(
        r"\b(?:sejak|sudah|selama)\s+"
        r"(?:\d+(?:[.,]\d+)?\s*(?:jam|hari|minggu|pekan|bulan|tahun|thn|mgg|bln)\b\s*|"
        r"(?:tadi|pagi|malam|siang|sore|kemarin|semalam|subuh|sebentar|beberapa\s+\w+)\s*)"
        r"(?:yang\s+)?(?:lalu|terakhir|ini)?\b",
        re.IGNORECASE
    ),
    # "sejak X hari/minggu/bulan/tahun yang lalu / terakhir / ini"
    re.compile(
        r"(?:sejak|selama|sudah|sudah\s+sekitar|kurang\s+lebih|±|kira[-\s]kira)?\s*"
        r"\d+(?:[.,]\d+)?\s*"
        r"(?:jam|hari|hr|minggu|mgg|pekan|bulan|bln|tahun|thn|th)\b"
        r"(?:\s*(?:yang\s+lalu|lalu|terakhir|ini|ke\s+depan))?",
        re.IGNORECASE
    ),
    # "sejak tadi pagi/malam/siang", "sejak kemarin"
    re.compile(
        r"sejak\s+(?:tadi\s+(?:pagi|malam|siang|sore)|kemarin|hari\s+ini|"
        r"pagi\s+ini|malam\s+ini|minggu\s+lalu|bulan\s+lalu)",
        re.IGNORECASE
    ),
    # kata kualitatif waktu
    re.compile(
        r"\b(?:sudah\s+lama|sejak\s+lama|lama\s+sekali|bertahun[-\s]tahun|"
        r"menahun|kambuh[-\s]kambuhan|berulang[-\s]ulang|hilang\s+timbul|"
        r"tidak\s+kunjung\s+sembuh|tidak\s+sembuh[-\s]sembuh|"
        r"tadi\s+pagi|tadi\s+malam|tadi\s+siang|pagi\s+ini|malam\s+ini|"
        r"beberapa\s+hari|beberapa\s+jam|beberapa\s+minggu|beberapa\s+bulan|"
        r"seminggu|sebulan|setahun|satu\s+(?:hari|minggu|bulan|tahun))\b",
        re.IGNORECASE
    ),
    # "tiba-tiba", "mendadak" — kata onset (juga dibuang dari matching)
    re.compile(
        r"\b(?:tiba[-\s]tiba|mendadak|secara\s+tiba[-\s]tiba|onset\s+mendadak)\b",
        re.IGNORECASE
    ),
]

def strip_temporal(text: str) -> str:
    """
    Buang semua ekspresi waktu dari teks sebelum masuk engine matching.
    Hasilnya hanya berisi kata klinis yang relevan ke gejala.

    Contoh:
      "nyeri dada sejak 3 hari yang lalu" → "nyeri dada"
      "demam tiba-tiba tadi malam"        → "demam"
      "batuk sudah 2 minggu tidak sembuh" → "batuk"
    """
    t = text
    for pat in _STRIP_PATTERNS:
        t = pat.sub(" ", t)
    # Bersihkan kata waktu tersisa yang lolos
    t = re.sub(r"\bsejak\s+lalu\b", " ", t, flags=re.IGNORECASE)
    t = re.sub(r"\btadi\s*$|^\s*tadi\b", " ", t, flags=re.IGNORECASE)
    t = re.sub(r"\btidak\s+sembuh[-\s]?(?:sembuh)?\b", " ", t, flags=re.IGNORECASE)
    t = re.sub(r"\bpagi\s*$", " ", t, flags=re.IGNORECASE)
    # Bersihkan kata connector yang tertinggal setelah strip
    # Contoh: "kelelahan sejak lalu" → "kelelahan", "tidak bisa jalan sekali" → "tidak bisa jalan"
    _LEFTOVER = re.compile(
        r"\b(?:sejak|sudah|selama|sudah\s+sekitar|sudah\s+lebih|"
        r"sekali|lagi|terus|masih|belum|sampai|hingga|kembali)\b\s*$",
        re.IGNORECASE
    )
    t = _LEFTOVER.sub("", t).strip()
    # Bersihkan spasi ganda
    return re.sub(r"\s+", " ", t).strip()


# ── Klasifikasi temporal ──────────────────────────────────────────
@dataclass
class TemporalContext:
    kategori:     str            # 'akut' | 'subakut' | 'kronis' | 'unknown'
    hari:         Optional[float]
    matched_text: str
    is_onset:     bool = False

    def __str__(self):
        if self.is_onset:   return f"AKUT [onset mendadak: '{self.matched_text}']"
        if self.hari:       return f"{self.kategori.upper()} [~{self.hari:.0f} hari: '{self.matched_text}']"
        return f"{self.kategori.upper()} [kualitatif: '{self.matched_text}']"


# ── Threshold per kelompok kondisi ───────────────────────────────
# Berbeda-beda karena "lama" itu relatif per kondisi:
#   demam: 3+ hari sudah subakut, 7+ hari sudah signifikan
#   nyeri: <30 hari akut, 30-90 subakut, >90 kronis (SDKI)
#   mobilitas/nutrisi: minggu-bulan baru dianggap kronik
#
# Tapi untuk simplisitas, threshold ini diterapkan di MODIFIER PER DIAGNOSA
# bukan di ekstraksi. Threshold global tetap dipakai untuk mengklasifikasi,
# lalu profil per diagnosa yang mengatur dampaknya.

AKUT_MAX   =  14   # < 14 hari → AKUT
KRONIS_MIN =  90   # > 90 hari → KRONIS

# ── Ekstraksi durasi ──────────────────────────────────────────────
_ONSET = re.compile(
    r"\b(tiba[-\s]tiba|mendadak|secara\s+tiba[-\s]tiba|onset\s+mendadak|"
    r"tiba2|dadakan)\b", re.IGNORECASE)

_KUALITATIF_KRONIS = re.compile(
    r"\b(sudah\s+lama|sejak\s+lama|lama\s+sekali|bertahun[-\s]tahun|menahun|"
    r"kambuh[-\s]kambuhan|berulang[-\s]ulang|hilang\s+timbul|"
    r"tidak\s+(?:kunjung\s+)?sembuh[-\s]?(?:sembuh)?|"
    r"sudah\s+bertahun|menahun|kronis|kronik)\b", re.IGNORECASE)

# Pola angka + satuan — ordered by specificity (tahun > bulan > minggu > hari > jam)
_DUR_PATTERNS = [
    (re.compile(r"(\d+(?:[.,]\d+)?)\s*(?:tahun|thn|th)\b", re.I), 365.0),
    (re.compile(r"(\d+(?:[.,]\d+)?)\s*(?:bulan|bln)\b",    re.I),  30.0),
    (re.compile(r"(\d+(?:[.,]\d+)?)\s*(?:minggu|mgg|pekan|week)\b", re.I), 7.0),
    (re.compile(r"(\d+(?:[.,]\d+)?)\s*(?:hari|hr|day)\b",  re.I),   1.0),
    (re.compile(r"(\d+(?:[.,]\d+)?)\s*(?:jam|hour|hr)\b",  re.I),   1/24),
]

_KUAL_AKUT = [
    (re.compile(r"\b(tadi\s+(?:pagi|malam|siang|sore)|pagi\s+ini|malam\s+ini|barusan|baru\s+saja)\b", re.I), 0.3),
    (re.compile(r"\b(kemarin|hari\s+ini)\b", re.I), 1.0),
    (re.compile(r"\b(beberapa\s+jam)\b",     re.I), 0.2),
    (re.compile(r"\b(beberapa\s+hari)\b",    re.I), 3.0),
    (re.compile(r"\b(seminggu|satu\s+minggu|sepekan)\b", re.I), 7.0),
    (re.compile(r"\b(sebulan|satu\s+bulan)\b", re.I), 30.0),
    (re.compile(r"\b(setahun|satu\s+tahun)\b", re.I), 365.0),
]


def extract_temporal(text: str) -> Optional[TemporalContext]:
    """Ekstrak konteks temporal dari teks asli (sebelum strip)."""
    if not text: return None

    # 1. Onset mendadak
    m = _ONSET.search(text)
    if m: return TemporalContext("akut", 0.5, m.group(0), is_onset=True)

    # 2. Kualitatif kronik
    m = _KUALITATIF_KRONIS.search(text)
    if m: return TemporalContext("kronis", None, m.group(0))

    # 3. Angka + satuan — ambil yang terpanjang
    best_days = None; best_text = ""; best_len = 0
    for pat, mult in _DUR_PATTERNS:
        m = pat.search(text)
        if m:
            days = float(m.group(1).replace(",",".")) * mult
            if len(m.group(0)) > best_len:
                best_days = days; best_text = m.group(0); best_len = len(m.group(0))

    if best_days is not None:
        kat = "akut" if best_days < AKUT_MAX else "kronis" if best_days > KRONIS_MIN else "subakut"
        return TemporalContext(kat, best_days, best_text)

    # 4. Kualitatif dengan estimasi hari
    for pat, est_days in _KUAL_AKUT:
        m = pat.search(text)
        if m:
            kat = "akut" if est_days < AKUT_MAX else "kronis" if est_days > KRONIS_MIN else "subakut"
            return TemporalContext(kat, est_days, m.group(0))

    return None


# ── Profil temporal per diagnosa ─────────────────────────────────
# "akut"   = diagnosa ini dominan pada kondisi baru/mendadak
# "kronis" = diagnosa ini dominan pada kondisi berlangsung lama (>3 bulan)
# "netral" = tidak ada preferensi waktu

TEMPORAL_PROFILE: dict[str, str] = {
    # Nyeri
    "D.0078": "akut",      # Nyeri Akut — SDKI <6 bulan, khas akut
    "D.0079": "kronis",    # Nyeri Kronis — SDKI >3 bulan

    # Respirasi
    "D.0001": "netral",    # Bersihan jalan nafas tidak efektif
    "D.0003": "netral",    # Gangguan pertukaran gas
    "D.0005": "netral",    # Pola nafas tidak efektif

    # Kardiovaskular
    "D.0008": "akut",      # Penurunan curah jantung
    "D.0009": "netral",    # Perfusi perifer tidak efektif
    "D.0022": "akut",      # Hipervolemia
    "D.0023": "akut",      # Hipovolemia
    "D.0039": "akut",      # Risiko syok

    # GI & nutrisi
    "D.0019": "kronis",    # Defisit nutrisi
    "D.0020": "akut",      # Diare
    "D.0076": "akut",      # Nausea

    # Eliminasi
    "D.0040": "netral",    # Gangguan eliminasi urine

    # Aktivitas & istirahat
    "D.0054": "kronis",    # Gangguan mobilitas fisik
    "D.0055": "kronis",    # Gangguan mobilitas di tempat tidur
    "D.0056": "netral",    # Intoleransi aktivitas
    "D.0057": "kronis",    # Gangguan pola tidur
    "D.0058": "kronis",    # Keletihan
    "D.0062": "kronis",    # Defisit perawatan diri: mandi
    "D.0063": "kronis",    # Defisit perawatan diri: berpakaian
    "D.0064": "kronis",    # Defisit perawatan diri: makan

    # Suhu — selalu akut
    "D.0130": "akut",      # Hipertermia
    "D.0131": "akut",      # Hipotermia
    "D.0047": "akut",      # Termoregulasi tidak efektif
    "D.0046": "akut",      # Risiko termoregulasi tidak efektif

    # Psikologis
    "D.0080": "netral",    # Ansietas
    "D.0081": "netral",    # Berduka
    "D.0083": "netral",    # Gangguan citra tubuh
    "D.0091": "kronis",    # Harga diri rendah kronis
    "D.0092": "akut",      # Harga diri rendah situasional
    "D.0096": "kronis",    # Keputusasaan
    "D.0095": "kronis",    # Ketidakberdayaan
    "D.0088": "netral",    # Gangguan memori

    # Pengetahuan
    "D.0119": "kronis",    # Defisit pengetahuan — selalu berlangsung lama
    "D.0122": "kronis",    # Manajemen kesehatan tidak efektif

    # Risiko
    "D.0142": "netral",    # Risiko infeksi
    "D.0143": "netral",    # Risiko jatuh
    "D.0135": "netral",    # Risiko jatuh
    "D.0136": "netral",    # Risiko trauma fisik
    "D.0049": "netral",    # Risiko cedera
    "D.0011": "netral",    # Risiko perdarahan
    "D.0025": "akut",      # Risiko hipovolemia
    "D.0048": "netral",    # Risiko infeksi (kode lain)
}

# ── Modifier confidence ──────────────────────────────────────────
_MODIFIER: dict[Tuple[str,str], float] = {
    ("akut",   "akut"):   +0.15,
    ("akut",   "kronis"): -0.25,
    ("akut",   "netral"):  0.00,
    ("kronis", "akut"):   -0.20,
    ("kronis", "kronis"): +0.15,
    ("kronis", "netral"):  0.00,
    ("subakut","akut"):    0.00,
    ("subakut","kronis"):  0.00,
    ("subakut","netral"):  0.00,
}

def get_temporal_modifier(temporal: Optional[TemporalContext],
                           kode_diagnosa: str) -> float:
    if temporal is None or temporal.kategori == "unknown": return 0.0
    profil = TEMPORAL_PROFILE.get(kode_diagnosa, "netral")
    return _MODIFIER.get((temporal.kategori, profil), 0.0)
