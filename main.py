import io
import os
from fastapi import FastAPI, File, UploadFile, HTTPException, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from supabase import create_client, Client

from extractor import extract_text_from_pdf
from analyzer import analyze_contract

app = FastAPI(title="Pahami Kontrak API", version="2.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Supabase client ────────────────────────────────────────────────────────────
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_ANON_KEY")

def get_supabase() -> Client | None:
    if SUPABASE_URL and SUPABASE_KEY:
        return create_client(SUPABASE_URL, SUPABASE_KEY)
    return None

VALID_PROFILES = {"fresh_grad", "freelancer", "experienced", "executive"}

@app.get("/")
def health_check():
    return {"status": "ok", "service": "Pahami Kontrak API"}

@app.post("/analyze")
async def analyze(
    file: UploadFile = File(...),
    user_profile: str = Form(default="experienced"),
    company_name: str = Form(default=""),
    consent_save: str = Form(default="true"),
):
    if not file.filename.endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Hanya file PDF yang diterima.")

    file_bytes = await file.read()

    if len(file_bytes) > 10 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="Ukuran file maksimal 10MB.")

    profile_key = user_profile if user_profile in VALID_PROFILES else "experienced"
    should_save = consent_save.lower() == "true"

    try:
        contract_text = extract_text_from_pdf(io.BytesIO(file_bytes))
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))

    result = analyze_contract(contract_text, profile_key=profile_key)

    if "error" in result:
        raise HTTPException(status_code=500, detail=result["error"])

    # ── Simpan ke Supabase jika user consent ──────────────────────────────────
    if should_save:
        supabase = get_supabase()
        if supabase:
            try:
                supabase.table("contract_analyses").insert({
                    "company_name": company_name.strip() or None,
                    "contract_type": result.get("contract_type"),
                    "risk_level": result.get("risk_level"),
                    "red_flag_count": result.get("red_flag_count", 0),
                    "profile_used": profile_key,
                    "consent_save": True,
                    "summary": result.get("summary"),
                    "industry_comparison": result.get("industry_comparison"),
                    "red_flags": result.get("red_flags", []),
                    "positive_clauses": result.get("positive_clauses", []),
                    "questions_for_hrd": result.get("questions_for_hrd", []),
                }).execute()
            except Exception as e:
                print(f"[WARN] Supabase insert failed: {e}")

    return JSONResponse(content=result)
