"""app/numeric_parser.py"""
import re
from dataclasses import dataclass
from typing import List, Tuple

@dataclass
class VitalReading:
    param: str; value: float; unit: str; raw_text: str

@dataclass
class _NM:
    vital: VitalReading; label: str; canonical: str

_VITAL_PAT: List[Tuple[str, str, str]] = [
    ("suhu",       r"suhu\s*:?\s*(\d+[.,]\d+|\d+)",       "°C"),
    ("nadi",       r"nadi\s*:?\s*(\d+)",                   "x/mnt"),
    ("rr",         r"frekuensi napas\s*:?\s*(\d+)",        "x/mnt"),
    ("spo2",       r"saturasi oksigen\s*:?\s*(\d+)",       "%"),
    ("td_sis",     r"tekanan darah\s*:?\s*(\d+)\s*(\d+)", "mmHg"),
    ("gcs",        r"gcs\s*:?\s*(\d+)",                    ""),
    ("gula_darah", r"gula darah\s*:?\s*(\d+)",             "mg/dL"),
    ("hemoglobin", r"hemoglobin\s*:?\s*(\d+[.,]\d+|\d+)", "g/dL"),
    ("nyeri",      r"skala nyeri\s*:?\s*(\d+)",            "skala"),
    ("imt",        r"\bimt\s*:?\s*(\d+[.,]\d+|\d+)",      "kg/m2"),
]

_RULES: List[Tuple] = [
    ("suhu",  ">=",39.0,"Demam tinggi (suhu >=39C)",           "demam",                       True),
    ("suhu",  ">=",38.0,"Demam (suhu >=38C)",                  "demam",                       True),
    ("suhu",  "<", 36.0,"Hipotermia (suhu <36C)",              "suhu tubuh rendah",            True),
    ("nadi",  ">=",120, "Takikardia (>=120/mnt)",              "nadi cepat",                  True),
    ("nadi",  ">=",100, "Takikardia ringan (>=100/mnt)",       "nadi cepat",                  True),
    ("nadi",  "<", 60,  "Bradikardia (<60/mnt)",               "nadi lambat",                 True),
    ("rr",    ">=",25,  "Takipnea berat (>=25/mnt)",           "frekuensi napas cepat",       True),
    ("rr",    ">", 20,  "Takipnea (>20/mnt)",                  "frekuensi napas cepat",       True),
    ("rr",    "<", 12,  "Bradipnea (<12/mnt)",                 "frekuensi napas lambat",      True),
    ("spo2",  "<", 90,  "Hipoksia berat (SpO2<90%)",           "penurunan saturasi oksigen",  True),
    ("spo2",  "<", 95,  "Hipoksia (SpO2<95%)",                 "penurunan saturasi oksigen",  True),
    ("td_sis","<", 90,  "Hipotensi (<90 mmHg)",                "tekanan darah rendah",        True),
    ("td_sis",">=",140, "Hipertensi (>=140 mmHg)",             "tekanan darah tinggi",        True),
    ("td_sis",">=",180, "Hipertensi berat (>=180 mmHg)",       "tekanan darah tinggi",        True),
    ("gcs",   "<", 9,   "Penurunan kesadaran berat",           "penurunan tingkat kesadaran", True),
    ("gcs",   "<", 14,  "Penurunan kesadaran sedang",          "penurunan tingkat kesadaran", True),
    ("nyeri", ">=",7,   "Nyeri berat (skor 7-10)",             "nyeri berat",                 True),
    ("nyeri", ">=",4,   "Nyeri sedang (skor 4-6)",             "nyeri sedang",                True),
    ("nyeri", ">=",1,   "Nyeri ringan (skor 1-3)",             "nyeri ringan",                True),
    ("gula_darah","<",  70, "Hipoglikemia (<70 mg/dL)",        "gula darah rendah",           True),
    ("gula_darah",">=",200, "Hiperglikemia (>=200 mg/dL)",     "gula darah tinggi",           True),
    ("hemoglobin","<",  8,  "Anemia berat (Hb<8)",             "hemoglobin rendah",           True),
    ("hemoglobin","<", 12,  "Anemia (Hb<12)",                  "hemoglobin rendah",           True),
    ("imt",   "<", 18.5,"Berat badan kurang (IMT<18.5)",       "berat badan kurang",          True),
    ("imt",   ">=",25,  "Berat badan lebih (IMT>=25)",         "berat badan berlebih",        True),
]

def _f(s): return float(str(s).replace(",","."))

def extract_vitals(text: str) -> List[VitalReading]:
    results = []
    for param, pattern, unit in _VITAL_PAT:
        for m in re.finditer(pattern, text, re.IGNORECASE):
            try:
                results.append(VitalReading(
                    param=param, value=_f(m.group(1)),
                    unit=unit, raw_text=m.group(0)))
            except Exception: pass
    return results

def apply_thresholds(vitals, phrase_to_concepts):
    matches=[]; raw_vitals=[]
    for v in vitals:
        status="normal"; best=None
        for param,op,thr,label,canonical,_ in _RULES:
            if v.param != param: continue
            hit = ((op==">=" and v.value>=thr) or (op=="<" and v.value<thr)
                   or (op=="<=" and v.value<=thr) or (op==">" and v.value>thr))
            if hit: status=label; best=(label,canonical); break
        raw_vitals.append({"param":v.param,"value":v.value,"unit":v.unit,
                            "raw_text":v.raw_text,"status":status})
        if best: matches.append(_NM(vital=v,label=best[0],canonical=best[1]))
    return matches, raw_vitals
