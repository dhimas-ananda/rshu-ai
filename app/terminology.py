"""app/terminology.py"""
import re
from typing import List, Tuple

_SHORTHAND_RULES: List[Tuple[re.Pattern, str]] = [
    (re.compile(r"\bTD\s*:?\s*(\d+)\s*/\s*(\d+)", re.I), r"tekanan darah \1 \2"),
    (re.compile(r"\bTD\s*:?\s*(\d+)",              re.I), r"tekanan darah \1"),
    (re.compile(r"\bSpO2\s*:?\s*(\d+)",            re.I), r"saturasi oksigen \1"),
    (re.compile(r"\bSaO2\s*:?\s*(\d+)",            re.I), r"saturasi oksigen \1"),
    (re.compile(r"\bRR\s*:?\s*(\d+)",              re.I), r"frekuensi napas \1"),
    (re.compile(r"\bHR\s*:?\s*(\d+)",              re.I), r"nadi \1"),
    (re.compile(r"\bGCS\s*:?\s*(\d+)",             re.I), r"gcs \1"),
    (re.compile(r"\bGDS\s*:?\s*(\d+)",             re.I), r"gula darah \1"),
    (re.compile(r"\bHb\s*:?\s*(\d+[,.]?\d*)",     re.I), r"hemoglobin \1"),
    (re.compile(r"\bBB\s*:?\s*(\d+[,.]?\d*)",     re.I), r"berat badan \1"),
    (re.compile(r"\bTB\s*:?\s*(\d+[,.]?\d*)",     re.I), r"tinggi badan \1"),
    (re.compile(r"\bBAB\b",                         re.I), "buang air besar"),
    (re.compile(r"\bBAK\b",                         re.I), "buang air kecil"),
    (re.compile(r"\bSOB\b",                         re.I), "sesak napas"),
    (re.compile(r"(\d+)\s*x/(?:mnt|menit)",        re.I), r"\1 per menit"),
    (re.compile(r"\bSuhu\s*:?\s*(\d+[,.]?\d*)",   re.I), r"suhu \1"),
    (re.compile(r"\bT\s*:?\s*(\d+[,.]?\d*)\s*[°]?[Cc]", re.I), r"suhu \1"),
]

_SYN_PAIRS = [
    ("sesak nafas","sesak napas"),("nafas sesak","sesak napas"),
    ("susah nafas","sesak napas"),("sulit nafas","sesak napas"),
    ("sulit bernapas","sesak napas"),("dispnea","sesak napas"),
    ("dyspnea","sesak napas"),("takipnea","frekuensi napas cepat"),
    ("bradipnea","frekuensi napas lambat"),("nafas cepat","frekuensi napas cepat"),
    ("whezing","mengi"),("wheezing","mengi"),("rales","ronkhi"),
    ("ronki","ronkhi"),("rhonki","ronkhi"),("rhonchi","ronkhi"),
    ("sputum","dahak"),("sekret","dahak"),
    ("hipotensi","tekanan darah rendah"),("hipertensi","tekanan darah tinggi"),
    ("takikardia","nadi cepat"),("takikardi","nadi cepat"),
    ("bradikardia","nadi lambat"),("bradikardi","nadi lambat"),
    ("palpitasi","jantung berdebar"),
    ("edema perifer","bengkak pada kaki"),("edema","pembengkakan"),
    ("sianosis","kulit kebiruan"),("diaforesis","berkeringat banyak"),
    ("demam tinggi","demam"),("febris","demam"),("pireksia","demam"),
    ("nausea","mual"),("rasa ingin muntah","mual"),
    ("emesis","muntah"),("hematemesis","muntah darah"),
    ("melena","bab hitam"),("diare","bab cair"),
    ("konstipasi","susah bab"),("anoreksia","tidak nafsu makan"),
    ("disfagia","susah menelan"),("kolik","nyeri kram"),
    ("angina","nyeri dada"),("artralgia","nyeri sendi"),
    ("mialgia","nyeri otot"),("sefalgia","sakit kepala"),
    ("headache","sakit kepala"),("somnolen","mengantuk berlebihan"),
    ("konfusi","bingung"),("vertigo","pusing berputar"),
    ("sinkop","pingsan"),("parestesia","kesemutan"),
    ("oliguria","produksi urin sedikit"),("anuria","tidak ada urin"),
    ("hematuria","urin berdarah"),("disuria","nyeri saat kencing"),
    ("fatigue","kelelahan"),("letargi","lemas"),
    ("malaise","tidak enak badan"),("hipoglikemia","gula darah rendah"),
    ("hiperglikemia","gula darah tinggi"),("pusing","kepala pusing"),
]
_SYN_RE = [
    (re.compile(rf"\b{re.escape(s)}\b"), t)
    for s,t in sorted(_SYN_PAIRS, key=lambda x:-len(x[0]))
]

def expand_shorthands(text: str) -> str:
    for pat, repl in _SHORTHAND_RULES:
        text = pat.sub(repl, text)
    return text

def apply_clinical_synonyms(text: str) -> str:
    for pat, tgt in _SYN_RE:
        text = pat.sub(tgt, text)
    return text


# Singkatan assessment perawat
import re as _re2

_ASSESS_PAT = [
    (_re2.compile(r'\bAHKM\b'),                   'akral hangat kering merah normal'),
    (_re2.compile(r'\bRh\s*\+'),                 'ronkhi positif'),
    (_re2.compile(r'\bRh\s*-\b'),                ''),
    (_re2.compile(r'\bWh\s*\+'),                 'wheezing positif'),
    (_re2.compile(r'\bWh\s*-\b'),                ''),
    (_re2.compile(r'\bBU\s+meningkat\b', _re2.I),'bising usus meningkat'),
    (_re2.compile(r'\bBU\s+menurun\b', _re2.I),  'bising usus menurun'),
    (_re2.compile(r'\bBU\b'),                     'bising usus'),
    (_re2.compile(r'\bCRT\s*>\s*3', _re2.I),     'pengisian kapiler sangat lambat'),
    (_re2.compile(r'\bCRT\s*>\s*2', _re2.I),     'pengisian kapiler lambat'),
    (_re2.compile(r'\bCM\b'),                     'composmentis'),
    (_re2.compile(r'\bDBN\b'),                    ''),
    (_re2.compile(r'\bTAK\b'),                    ''),
    (_re2.compile(r'\bAICD\s*\+', _re2.I),       'asimetri ikterik sianosis dyspnea'),
    (_re2.compile(r'\bAICD\s*-', _re2.I),         ''),
    (_re2.compile(r'\bSupel\b', _re2.I),          ''),
    (_re2.compile(r'\bSupl\b', _re2.I),           ''),
    (_re2.compile(r'\bEks\s+AHKM\b', _re2.I),   ''),
]

def expand_assessment_abbrev(text):
    for pat, repl in _ASSESS_PAT:
        text = pat.sub(repl, text)
    import re
    return re.sub(r'\s+', ' ', text).strip()
