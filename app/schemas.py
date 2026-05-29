"""app/schemas.py v3.2"""
from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field

class PredictRequest(BaseModel):
    # text boleh kosong — engine pakai keluhan_utama sebagai primary
    text:              str = Field(default="", max_length=2000)
    top_k:             int = Field(default=149, ge=1, le=149)
    jenis_form:        str = Field(default="dewasa")
    keluhan_utama:     str = Field(default="")
    keluhan_menyertai: str = Field(default="")
    kondisi_latar:     str = Field(default="")   # RPD/faktor risiko background

class TestRequest(PredictRequest):
    label_notes: Optional[str] = None

class LabelRequest(BaseModel):
    is_correct:         Optional[bool] = None
    label_notes:        Optional[str]  = None
    label_diagnosis_id: Optional[int]  = None

class DiagnosisResultOut(BaseModel):
    id_diagnosa:      int
    kode_diagnosa:    str
    nama_diagnosa:    str
    score:            float
    confidence:       float = 0.0
    matched_major:    int
    matched_minor:    int
    matched_risiko:   int   = 0
    max_score:        float = 0.0
    mayor_coverage:   float = 0.0
    matched_symptoms: List[str]
    explanation:      List[str]

class PredictResponse(BaseModel):
    input_text:       str
    normalized_text:  str
    matched_symptoms: list = []
    matched_vitals:   list = []
    ambiguous_terms:  List[str] = []
    top_diagnoses:    List[DiagnosisResultOut]
    best_diagnosis:   Optional[DiagnosisResultOut] = None
    confidence:       float = 0.0
    message:          Optional[str] = None

class TestRunResponse(PredictResponse):
    run_id: int; model_version: str = "v3.2"; saved_at: datetime

class LabelResponse(BaseModel):
    id: int; is_correct: Optional[bool]; label_notes: Optional[str]
    label_diagnosis_id: Optional[int]; updated_at: datetime

class HistoryItem(BaseModel):
    id: int; input_text: str
    best_diagnosis_code: Optional[str]; best_diagnosis_name: Optional[str]
    confidence: Optional[float]; matched_symptom_count: int
    model_version: str; is_correct: Optional[bool]; created_at: datetime

class HistoryResponse(BaseModel):
    total: int; page: int; limit: int; items: List[HistoryItem]

class StatsResponse(BaseModel):
    total_run: int; total_labeled: int; total_benar: int; total_salah: int
    akurasi_global: Optional[float]; model_version: str; computed_at: datetime

class ReloadResponse(BaseModel):
    status: str; diagnosa_count: int; phrase_count: int; reloaded_at: datetime
