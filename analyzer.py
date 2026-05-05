import os
import json
from groq import Groq
from dotenv import load_dotenv

load_dotenv()

client = Groq(api_key=os.getenv("GROQ_API_KEY"))

SYSTEM_PROMPT = """
Kamu adalah analis ketenagakerjaan Indonesia yang berpengalaman 
dalam hukum ketenagakerjaan, khususnya UU No. 13 Tahun 2003, 
UU Cipta Kerja, dan PP No. 35 Tahun 2021.

Tugasmu adalah membaca kontrak kerja (PKWT/PKWTT) yang diberikan 
dan mengidentifikasi:
1. Klausul yang berpotensi merugikan karyawan (red flags)
2. Pertanyaan penting yang harus ditanyakan sebelum tanda tangan

ATURAN WAJIB:
- Hanya analisis isi kontrak yang diberikan, jangan mengarang
- Gunakan bahasa Indonesia yang sederhana dan mudah dipahami  
- Jika tidak ada red flag, kembalikan array kosong []
- Severity "high"   = melanggar UU atau sangat merugikan karyawan
- Severity "medium" = ambigu, perlu klarifikasi
- Severity "low"    = tidak ideal tapi masih dalam batas wajar
- Kembalikan HANYA JSON valid, tanpa teks tambahan apapun
"""

JSON_SCHEMA = """
{
  "red_flags": [
    {
      "clause": "kutipan teks klausul bermasalah, max 200 karakter",
      "issue": "penjelasan masalah dalam bahasa sederhana, max 300 karakter",
      "severity": "high | medium | low",
      "pasal_referensi": "pasal UU yang dilanggar, atau null"
    }
  ],
  "questions": [
    {
      "question": "pertanyaan spesifik yang harus ditanyakan ke HRD",
      "tujuan": "kenapa pertanyaan ini penting, max 150 karakter"
    }
  ],
  "summary": {
    "total_red_flags": 0,
    "risk_level": "high | medium | low",
    "catatan": "satu kalimat kesimpulan keseluruhan kontrak"
  }
}
"""

def analyze_contract(contract_text: str) -> dict:
    prompt = f"""
{SYSTEM_PROMPT}

KONTRAK KERJA YANG HARUS DIANALISIS:
---
{contract_text}
---

Kembalikan analisis dalam format JSON berikut:
{JSON_SCHEMA}
""".strip()

    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.1,
        response_format={"type": "json_object"}
    )

    return _parse_response(response.choices[0].message.content)

def _parse_response(raw: str) -> dict:
    try:
        clean = raw.strip()
        if clean.startswith("```"):
            clean = clean.split("```")[1]
            if clean.startswith("json"):
                clean = clean[4:]
        clean = clean.strip()

        result = json.loads(clean)

        assert "red_flags" in result
        assert "questions" in result
        assert "summary" in result

        return result

    except (json.JSONDecodeError, AssertionError) as e:
        return {
            "error": "Gagal menganalisis kontrak. Coba upload ulang.",
            "detail": str(e)
        }