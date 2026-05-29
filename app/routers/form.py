"""app/routers/form.py"""
import os
from fastapi import APIRouter
from fastapi.responses import HTMLResponse, RedirectResponse

router = APIRouter()
_TMPL = os.path.join(os.path.dirname(os.path.dirname(__file__)),"templates","rshu_form.html")

def _html():
    with open(_TMPL, encoding="utf-8") as f: return f.read()

@router.get("/", response_class=HTMLResponse)
async def index(): return HTMLResponse(_html())

@router.get("/form/dewasa", response_class=HTMLResponse)
async def form_dewasa(): return HTMLResponse(_html())

@router.get("/form/anak")
async def form_anak(): return RedirectResponse("/")

@router.get("/form/kebidanan")
async def form_kebidanan(): return RedirectResponse("/")

@router.get("/form/igd")
async def form_igd(): return RedirectResponse("/")
