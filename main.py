import io
from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from extractor import extract_text_from_pdf
from analyzer import analyze_contract

app = FastAPI(title="BacaDulu API", version="1.0.0")

# CORS — izinkan frontend akses API ini
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # ganti dengan domain frontend saat production
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def health_check():
    return {"status": "ok", "service": "BacaDulu API"}

@app.post("/analyze")
async def analyze(file: UploadFile = File(...)):
    # Validasi tipe file
    if not file.filename.endswith(".pdf"):
        raise HTTPException(
            status_code=400,
            detail="Hanya file PDF yang diterima."
        )

    # Baca file sebagai bytes
    file_bytes = await file.read()

    # Batasi ukuran file: max 10MB
    if len(file_bytes) > 10 * 1024 * 1024:
        raise HTTPException(
            status_code=400,
            detail="Ukuran file maksimal 10MB."
        )

    # Extract text dari PDF
    try:
        contract_text = extract_text_from_pdf(io.BytesIO(file_bytes))
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))

    # Analisis dengan Gemini
    result = analyze_contract(contract_text)

    # Kalau ada error dari parser
    if "error" in result:
        raise HTTPException(status_code=500, detail=result["error"])

    return result