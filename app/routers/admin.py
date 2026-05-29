"""app/routers/admin.py"""
from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException, Request
from ..schemas import LabelRequest, LabelResponse, ReloadResponse, StatsResponse
from ..db import get_cursor

router = APIRouter()

@router.patch("/api/test/{run_id}", response_model=LabelResponse)
async def label_run(run_id: int, payload: LabelRequest):
    now = datetime.now(timezone.utc)
    try:
        with get_cursor(dict_cursor=False) as (_,cur):
            cur.execute("""
                INSERT INTO feedback (id_run,is_correct,catatan,id_diagnosa_gt)
                VALUES (%s,%s,%s,%s)
                ON CONFLICT (id_run) DO UPDATE SET
                    is_correct=EXCLUDED.is_correct,
                    catatan=EXCLUDED.catatan,
                    id_diagnosa_gt=EXCLUDED.id_diagnosa_gt
            """, (run_id,payload.is_correct,payload.label_notes,payload.label_diagnosis_id))
    except Exception as exc: raise HTTPException(500,str(exc)) from exc
    return LabelResponse(id=run_id,is_correct=payload.is_correct,
        label_notes=payload.label_notes,
        label_diagnosis_id=payload.label_diagnosis_id,updated_at=now)

@router.get("/api/stats", response_model=StatsResponse)
async def stats():
    try:
        with get_cursor(dict_cursor=False) as (_,cur):
            cur.execute("""
                SELECT COUNT(*) AS total_run,
                       COUNT(f.id) AS labeled,
                       COUNT(f.id) FILTER (WHERE f.is_correct=TRUE) AS benar,
                       COUNT(f.id) FILTER (WHERE f.is_correct=FALSE) AS salah
                FROM run_log r LEFT JOIN feedback f ON f.id_run=r.id
            """)
            row = cur.fetchone()
    except Exception as exc: raise HTTPException(500,str(exc)) from exc
    total=row[0]; labeled=row[1]; benar=row[2]; salah=row[3]
    return StatsResponse(total_run=total,total_labeled=labeled,
        total_benar=benar,total_salah=salah,
        akurasi_global=round(benar/labeled,3) if labeled else None,
        model_version="v3",computed_at=datetime.now(timezone.utc))

@router.post("/api/reload", response_model=ReloadResponse)
async def reload(request: Request):
    matcher = getattr(request.app.state,"matcher",None)
    if not matcher: raise HTTPException(503,"Pipeline tidak tersedia")
    try:
        matcher.loaded = False
        matcher.load_master_data()
    except Exception as exc:
        raise HTTPException(500,f"Gagal reload: {exc}") from exc
    s = matcher._stats
    return ReloadResponse(status="ok",diagnosa_count=s.get("diagnosa",0),
        phrase_count=s.get("frasa_unik",0),reloaded_at=datetime.now(timezone.utc))

@router.get("/api/diagnosa")
async def list_diagnosa():
    try:
        with get_cursor() as (_,cur):
            cur.execute("SELECT kode,nama FROM diagnosa WHERE is_aktif=TRUE ORDER BY kode")
            rows = cur.fetchall()
        return [{"kode":r["kode"],"nama":r["nama"]} for r in rows]
    except Exception: return []

@router.get("/favicon.ico", include_in_schema=False)
async def favicon():
    from fastapi.responses import Response
    ico = bytes([0,0,1,0,1,0,1,1,0,0,1,0,32,0,40,0,0,0,22,0,0,0,40,0,0,0,
                 1,0,0,0,2,0,0,0,1,0,32,0,0,0,0,0,8,0,0,0,0,0,0,0,0,0,0,0,
                 0,0,0,0,0,0,0,0,0,0,0,0,255,0,0,0,0,0,0,0])
    return Response(content=ico, media_type="image/x-icon")
