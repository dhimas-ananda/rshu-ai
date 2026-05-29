"""app/routers/test.py"""
import json
from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException, Request, Query
from ..schemas import TestRequest, TestRunResponse, HistoryResponse, HistoryItem
from ..db import get_cursor

router = APIRouter()

@router.post("/api/test", response_model=TestRunResponse)
async def test_predict(payload: TestRequest, request: Request):
    matcher = getattr(request.app.state, "matcher", None)
    if not matcher or not matcher.loaded:
        raise HTTPException(503, "Master data belum dimuat.")
    try:
        result = matcher.predict(
            text=payload.text, top_k=payload.top_k,
            keluhan_utama=payload.keluhan_utama,
            subjektif=payload.subjektif,
            objektif=payload.objektif,
            kondisi_latar=payload.kondisi_latar,
        )
    except Exception as exc:
        raise HTTPException(500, str(exc)) from exc
    best = result.get("best_diagnosis")
    now  = datetime.now(timezone.utc)
    try:
        with get_cursor(dict_cursor=False) as (_, cur):
            cur.execute("""
                INSERT INTO run_log
                  (input_text, normalized_text, top_diagnoses,
                   best_diagnosis_id, best_diagnosis_code,
                   confidence, model_version, created_at)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s)
                RETURNING id
            """, (payload.text, result["normalized_text"],
                  json.dumps(result["top_diagnoses"][:10]),
                  best.get("id_diagnosa") if best else None,
                  best.get("kode_diagnosa") if best else None,
                  best.get("confidence",0) if best else 0,
                  "v3", now))
            run_id = cur.fetchone()[0]
    except Exception as exc:
        raise HTTPException(500, f"Gagal simpan log: {exc}") from exc
    return TestRunResponse(**result, run_id=run_id, model_version="v3", saved_at=now)

@router.get("/api/test", response_model=HistoryResponse)
async def history(page: int = Query(1,ge=1), limit: int = Query(20,ge=1,le=100)):
    try:
        with get_cursor() as (_, cur):
            cur.execute("SELECT COUNT(*) AS n FROM run_log")
            total = cur.fetchone()["n"]
            cur.execute("""
                SELECT r.id,r.input_text,r.best_diagnosis_code,
                       d.nama AS best_diagnosis_name,
                       r.confidence, r.model_version,
                       COALESCE(
                         (SELECT COUNT(*) FROM jsonb_array_elements(
                           CASE WHEN jsonb_typeof(r.top_diagnoses)='array'
                                THEN r.top_diagnoses ELSE '[]'::jsonb END
                         ) WHERE value->'score' IS NOT NULL),0) AS syms,
                       f.is_correct, r.created_at
                FROM run_log r
                LEFT JOIN diagnosa d ON d.kode=r.best_diagnosis_code
                LEFT JOIN feedback f ON f.id_run=r.id
                ORDER BY r.created_at DESC
                LIMIT %s OFFSET %s
            """, (limit, (page-1)*limit))
            rows = cur.fetchall()
    except Exception as exc:
        raise HTTPException(500, str(exc))
    items = [HistoryItem(
        id=r["id"], input_text=r["input_text"],
        best_diagnosis_code=r["best_diagnosis_code"],
        best_diagnosis_name=r.get("best_diagnosis_name"),
        confidence=r["confidence"],
        matched_symptom_count=int(r.get("syms",0) or 0),
        model_version=r["model_version"] or "v3",
        is_correct=r["is_correct"], created_at=r["created_at"]
    ) for r in rows]
    return HistoryResponse(total=total, page=page, limit=limit, items=items)
