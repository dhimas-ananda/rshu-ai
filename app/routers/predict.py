"""app/routers/predict.py v3.2"""
import asyncio
from fastapi import APIRouter, HTTPException, Request
from ..schemas import PredictRequest, PredictResponse

router = APIRouter()
TIMEOUT_SEC = 12


@router.post("/api/predict", response_model=PredictResponse)
async def predict(payload: PredictRequest, request: Request):
    matcher   = getattr(request.app.state, "matcher",   None)
    semaphore = getattr(request.app.state, "semaphore", None)

    if not matcher:
        raise HTTPException(503, "Pipeline tidak tersedia.")
    if not matcher.loaded:
        raise HTTPException(503,
            "Master data SDKI belum dimuat. "
            "Jalankan import_sdki.py lalu POST /api/reload.")

    # Minimal validasi: setidaknya satu field terisi
    has_input = any([
        payload.keluhan_utama.strip(),
        payload.keluhan_menyertai.strip(),
        payload.text.strip(),
    ])
    if not has_input:
        raise HTTPException(422,
            "Isi minimal keluhan utama atau TTV sebelum analisis.")

    if semaphore and semaphore.locked() and semaphore._value == 0:
        raise HTTPException(503,
            "Server sedang sibuk. Coba lagi dalam beberapa detik.")

    async def _run():
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, lambda: matcher.predict(
            text=payload.text,
            top_k=payload.top_k,
            keluhan_utama=payload.keluhan_utama,
            keluhan_menyertai=payload.keluhan_menyertai,
            kondisi_latar=payload.kondisi_latar,
        ))

    try:
        if semaphore:
            async with semaphore:
                result = await asyncio.wait_for(_run(), timeout=TIMEOUT_SEC)
        else:
            result = await asyncio.wait_for(_run(), timeout=TIMEOUT_SEC)
    except asyncio.TimeoutError:
        raise HTTPException(504, "Prediksi terlalu lama.")
    except Exception as exc:
        raise HTTPException(500, f"Error prediksi: {exc}") from exc

    return PredictResponse(**result)
