"""
MarvelAI Travel PA Insurance Claims Portal
==========================================

requirements.txt:
-----------------
streamlit>=1.32.0
plotly>=5.20.0
pandas>=2.2.0
requests>=2.31.0
Pillow>=10.2.0
PyMuPDF>=1.23.0
# Optional – only needed for image/scanned-PDF OCR:
# pytesseract>=0.3.10

Usage:
------
1. Install dependencies:  pip install -r requirements.txt
2. Ensure Ollama is running locally with llama3.2 pulled:
       ollama pull llama3.2
       ollama serve
3. Run the app:  streamlit run app.py
"""

# ──────────────────────────────────────────────────────────────────────────────
# IMPORTS
# ──────────────────────────────────────────────────────────────────────────────
import json
import hashlib
import random
import re
import time
import uuid
from dataclasses import dataclass, field, asdict
from datetime import date, datetime, timedelta
from io import BytesIO
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import requests
import streamlit as st
import streamlit.components.v1

# ──────────────────────────────────────────────────────────────────────────────
# PAGE CONFIG  (must be first Streamlit call)
# ──────────────────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="MarvelAI · Claims Portal",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ──────────────────────────────────────────────────────────────────────────────
# GLOBAL CONSTANTS & CONFIG
# ──────────────────────────────────────────────────────────────────────────────
OLLAMA_HOST  = "http://localhost:11434"
OLLAMA_URL   = f"{OLLAMA_HOST}/api/generate"
OLLAMA_TAGS_URL = f"{OLLAMA_HOST}/api/tags"
OLLAMA_MODEL = "llama3.2"
OLLAMA_FALLBACK_MODELS = ["llama3.1"]
OLLAMA_TIMEOUT = 120          # seconds

COVERAGE_TYPES = [
    "Accidental Death", "Permanent Disability", "Hospitalisation",
    "Emergency Evacuation", "Trip Cancellation", "Baggage Loss",
]

GEOGRAPHIES = [
    "Southeast Asia", "Europe", "North America",
    "Middle East", "South Asia", "Oceania", "Africa",
]

DOC_TYPES = [
    "Death Certificate", "Hospital Bill", "Medical Report",
    "Disability Assessment", "Police Report", "Boarding Pass",
    "Insurance Policy", "Claim Form", "Discharge Summary", "Unknown",
]

CLAIM_STATUSES = [
    "AUTO APPROVE", 
    "MANUAL REVIEW", 
    "REQUEST INFORMATION", 
    "FRAUD INVESTIGATION", 
    "REJECT"
]

PAGES = {
    "dashboard": "Dashboard",
    "intake": "Claim Intake",
    "processing": "Document Processing",
    "travel": "Travel Validation",
    "medical": "Medical Assessment",
    "fraud": "Fraud Detection",
    "decision": "Decision Engine",
    "report": "Claim Report"
}

# ──────────────────────────────────────────────────────────────────────────────
# DOMAIN MODELS (DATACLASSES)
# ──────────────────────────────────────────────────────────────────────────────
@dataclass
class ClaimDocument:
    file_name: str
    file_type: str
    content_bytes: bytes = field(repr=False)
    extracted_text: str = ""
    ocr_method: str = ""
    doc_category: str = "Unknown"
    parsed_entities: Dict[str, Any] = field(default_factory=dict)

@dataclass
class FraudSignal:
    name: str
    description: str
    risk_score: float

@dataclass
class FraudAssessment:
    overall_score: float = 0.0
    signals: List[FraudSignal] = field(default_factory=list)
    reasoning: str = ""

@dataclass
class ClaimContext:
    claim_id: str
    policy_number: str
    submitted_at: datetime
    coverage_type: str
    geography: str
    claim_amount: float
    documents: List[ClaimDocument] = field(default_factory=list)
    travel_mismatch: bool = False
    is_duplicate: bool = False
    medical_assessment_passed: bool = False
    medical_reasoning: str = ""
    travel_reasoning: str = ""
    fraud_assessment: FraudAssessment = field(default_factory=FraudAssessment)
    final_status: str = "PENDING"
    decision_reasoning: str = ""

# ──────────────────────────────────────────────────────────────────────────────
# CUSTOM CSS  – professional light theme (PRESERVED)
# ──────────────────────────────────────────────────────────────────────────────
def inject_css() -> None:
    st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

    /* ── Design tokens ──────────────────────────────────────────────────────── */
    :root {
        --navy          : #0D1F3C;
        --navy-mid      : #1A3354;
        --blue          : #1A6FE0;
        --blue-light    : #E8F1FC;
        --success       : #0A7C5C;
        --success-bg    : #E6F5F0;
        --warning       : #7A4F00;
        --warning-bg    : #FEF3CD;
        --danger        : #B91C1C;
        --danger-bg     : #FEE8E8;
        --info          : #1753A8;
        --info-bg       : #EBF2FD;
        --surface       : #FFFFFF;
        --surface-page  : #F0F4F9;
        --surface-raised: #FFFFFF;
        --border        : #D8E1EE;
        --border-light  : #EAF0F8;
        --text-heading  : #0D1F3C;
        --text-body     : #243550;
        --text-muted    : #5A6E89;
        --text-faint    : #8FA3BC;
        --font          : "Inter", "Segoe UI", system-ui, sans-serif;
        --font-mono     : "JetBrains Mono", "Fira Code", "Consolas", monospace;
    }

    /* ── Global base ─────────────────────────────────────────────────────────  */
    html, body,
    [data-testid="stAppViewContainer"],
    [data-testid="stMain"],
    .main .block-container {
        background-color: var(--surface-page) !important;
        font-family: var(--font) !important;
        color: var(--text-body) !important;
    }
    p, li, span, label, div { color: var(--text-body); }
    h1, h2, h3, h4 { color: var(--text-heading) !important; font-family: var(--font) !important; }

    /* ── Sidebar ─────────────────────────────────────────────────────────────  */
    [data-testid="stSidebar"] {
        background-color: var(--navy) !important;
        border-right: 2px solid var(--navy-mid) !important;
        padding-top: 0 !important;
    }
    [data-testid="stSidebar"], [data-testid="stSidebar"] p, [data-testid="stSidebar"] span, [data-testid="stSidebar"] div, [data-testid="stSidebar"] label {
        color: #FFFFFF !important;
    }
    [data-testid="stSidebar"] .stRadio > div > label {
        color: rgba(255,255,255,0.82) !important;
        font-size: 0.875rem; padding: 0.45rem 0.6rem; border-radius: 6px; margin: 1px 0; transition: background 0.15s, color 0.15s; display: block;
    }
    [data-testid="stSidebar"] .stRadio > div > label:hover { background: rgba(255,255,255,0.08) !important; color: #FFFFFF !important; }
    [data-testid="stSidebar"] .stRadio > div > label[data-baseweb="radio"] > div:first-child { border-color: var(--blue) !important; background-color: var(--blue) !important; }
    [data-testid="stSidebar"] .stButton > button {
        background: rgba(255,255,255,0.08) !important; color: rgba(255,255,255,0.75) !important; border: 1px solid rgba(255,255,255,0.15) !important; border-radius: 6px; font-size: 0.82rem; transition: background 0.15s;
    }
    [data-testid="stSidebar"] .stButton > button:hover { background: rgba(255,255,255,0.14) !important; color: #FFFFFF !important; }
    [data-testid="stSidebar"] hr { border-color: rgba(255,255,255,0.12) !important; }

    /* ── Main content padding ────────────────────────────────────────────────  */
    .main .block-container { padding: 2rem 2.5rem 3rem !important; max-width: 1400px; }

    /* ── Cards & Metrics ─────────────────────────────────────────────────────  */
    .card { background: var(--surface); border: 1px solid var(--border); border-radius: 10px; padding: 1.35rem 1.5rem; margin-bottom: 1rem; }
    .card h3 { font-size: 1rem; font-weight: 600; color: var(--text-heading); margin: 0 0 0.25rem; }
    .card-metric { background: var(--surface); border: 1px solid var(--border); border-radius: 10px; padding: 1.1rem 1rem 1rem; text-align: center; }
    .metric-value { font-size: 1.9rem; font-weight: 700; color: var(--text-heading); line-height: 1.1; letter-spacing: -0.02em; }
    .metric-label { font-size: 0.7rem; color: var(--text-muted); text-transform: uppercase; letter-spacing: 0.09em; margin-top: 0.35rem; font-weight: 500; }

    /* ── Section headers ─────────────────────────────────────────────────────  */
    .section-header { font-size: 0.78rem; font-weight: 700; color: var(--text-muted); text-transform: uppercase; letter-spacing: 0.1em; border-bottom: 2px solid var(--border-light); padding-bottom: 0.45rem; margin: 1.5rem 0 0.9rem; }

    /* ── Status badges ───────────────────────────────────────────────────────  */
    .badge { display: inline-block; padding: 0.18rem 0.6rem; border-radius: 4px; font-size: 0.7rem; font-weight: 600; letter-spacing: 0.04em; text-transform: uppercase; line-height: 1.5; }
    .badge-success { background: var(--success-bg); color: var(--success); }
    .badge-warning { background: var(--warning-bg); color: var(--warning); }
    .badge-danger  { background: var(--danger-bg);  color: var(--danger);  }
    .badge-info    { background: var(--info-bg);    color: var(--info);    }
    .badge-neutral { background: var(--border-light); color: var(--text-muted); }

    /* ── JSON box ────────────────────────────────────────────────────────────  */
    .json-box { background: var(--surface-page); border: 1px solid var(--border); border-radius: 8px; padding: 0.9rem 1rem; font-family: var(--font-mono); font-size: 0.78rem; color: var(--text-body); overflow-x: auto; line-height: 1.75; }

    /* ── Streamlit Overrides ─────────────────────────────────────────────────  */
    .stSelectbox label, .stMultiSelect label, .stFileUploader label, .stDateInput label, .stTextInput label, .stExpander label, [data-testid="stWidgetLabel"] { color: var(--text-body) !important; font-size: 0.85rem !important; font-weight: 500 !important; }
    [data-testid="stExpander"] { border: 1px solid var(--border) !important; border-radius: 8px !important; background: var(--surface) !important; }
    [data-testid="stExpander"] summary { color: var(--text-body) !important; font-weight: 500; font-size: 0.88rem; }
    [data-testid="stAlert"] { border-radius: 8px !important; font-size: 0.875rem; }
    [data-testid="stDataFrame"] thead th, .dataframe thead th { background-color: var(--navy) !important; color: #FFFFFF !important; font-size: 0.72rem !important; font-weight: 600 !important; text-transform: uppercase; letter-spacing: 0.07em; padding: 0.5rem 0.75rem !important; }
    [data-testid="stDataFrame"] tbody tr:nth-child(even) { background-color: var(--surface-page) !important; }
    [data-testid="stDataFrame"] tbody td { color: var(--text-body) !important; font-size: 0.83rem !important; }
    .stButton > button { background: var(--blue) !important; color: #FFFFFF !important; border: none !important; border-radius: 6px !important; font-size: 0.85rem !important; font-weight: 500 !important; padding: 0.45rem 1.1rem !important; transition: opacity 0.15s; }
    .stButton > button:hover { opacity: 0.88 !important; }
    [data-testid="stMultiSelect"] span[data-baseweb="tag"] { background: var(--blue-light) !important; color: var(--blue) !important; border-radius: 4px !important; font-size: 0.78rem !important; }
    code, pre { font-family: var(--font-mono) !important; font-size: 0.8rem; background: var(--surface-page); color: var(--text-body); border-radius: 4px; }
    hr { border-color: var(--border-light) !important; margin: 0.75rem 0 !important; }
    #MainMenu, footer, header { visibility: hidden; }
    [data-testid="stDecoration"] { display: none; }

    /* Professional refresh layer */
    :root {
        --ink: #172033; --ink-soft: #344054; --canvas: #F7F5F0; --panel: #FFFFFF; --panel-soft: #FBFAF7; --line: #E4DFD6; --line-strong: #D6CEC0; --brand: #1F6F68; --brand-deep: #174E4A; --brand-soft: #E8F3F1; --accent: #C98A2E; --accent-soft: #FFF4E4;
    }
    html, body, [data-testid="stAppViewContainer"], [data-testid="stMain"], .main .block-container { background: radial-gradient(circle at top left, rgba(31,111,104,0.08), transparent 32rem), linear-gradient(180deg, #FBFAF7 0%, var(--canvas) 52%, #F1EEE7 100%) !important; }
    .main .block-container { max-width: 1320px; padding: 1.65rem 2.1rem 3.25rem !important; }
    [data-testid="stSidebar"] { background: linear-gradient(180deg, #172033 0%, #142A2E 58%, #102020 100%) !important; border-right: 1px solid rgba(255,255,255,0.10) !important; box-shadow: 16px 0 38px rgba(23,32,51,0.14); }
    [data-testid="stSidebar"] .stRadio > div > label { background: transparent !important; border: 1px solid transparent; border-radius: 8px !important; color: rgba(255,255,255,0.78) !important; padding: 0.72rem 0.78rem !important; font-weight: 600; display: flex !important; align-items: center !important; gap: 0.65rem !important; min-height: 2.55rem; }
    [data-testid="stSidebar"] .stRadio > div > label:hover { background: rgba(255,255,255,0.08) !important; border-color: rgba(255,255,255,0.08); color: #FFFFFF !important; }
    [data-testid="stSidebar"] .stRadio > div > label:has(input:checked) { background: rgba(255,255,255,0.13) !important; border-color: rgba(255,255,255,0.18); box-shadow: inset 3px 0 0 var(--accent); }
    .page-hero { position: relative; overflow: hidden; background: linear-gradient(135deg, rgba(255,255,255,0.98) 0%, rgba(251,250,247,0.98) 56%, rgba(232,243,241,0.98) 100%); border: 1px solid rgba(214,206,192,0.95); border-radius: 8px; padding: 1.55rem 1.75rem; margin: 0 0 1.35rem; box-shadow: 0 18px 45px rgba(23,32,51,0.08); }
    .page-hero::after { content: ""; position: absolute; inset: auto 1.4rem 0 1.4rem; height: 3px; background: linear-gradient(90deg, var(--brand), var(--accent), transparent); opacity: 0.9; }
    .page-kicker { color: var(--brand-deep); font-size: 0.7rem; font-weight: 800; letter-spacing: 0.12em; text-transform: uppercase; margin-bottom: 0.5rem; }
    .page-hero h1 { color: var(--ink) !important; font-size: 2rem; font-weight: 750; line-height: 1.12; margin: 0 0 0.4rem; letter-spacing: 0; }
    .page-hero p { color: #5F6673 !important; font-size: 0.98rem; line-height: 1.55; max-width: 820px; }
    .card, .card-metric, [data-testid="stExpander"], [data-testid="stPlotlyChart"], [data-testid="stDataFrame"] { background: rgba(255,255,255,0.94) !important; border: 1px solid rgba(214,206,192,0.88) !important; border-radius: 8px !important; box-shadow: 0 12px 30px rgba(23,32,51,0.055); }
    .card-metric { min-height: 118px; align-items: flex-start; text-align: left; padding: 1.15rem 1.2rem; background: linear-gradient(180deg, #FFFFFF 0%, #FBFAF7 100%) !important; }
    .metric-value { color: var(--ink); font-size: 2.05rem; font-weight: 760; }
    .metric-label { color: #7A746B; font-size: 0.68rem; font-weight: 800; letter-spacing: 0.09em; }
    .section-header { border-bottom: 1px solid var(--line); color: var(--ink); font-size: 0.72rem; font-weight: 850; letter-spacing: 0.11em; margin: 1.45rem 0 0.95rem; padding-bottom: 0.55rem; }
    .section-header::before { content: ""; display: inline-block; width: 8px; height: 8px; margin-right: 0.45rem; border-radius: 50%; background: var(--accent); }
    .stButton > button { background: linear-gradient(180deg, var(--brand) 0%, var(--brand-deep) 100%) !important; border: 1px solid rgba(16,80,74,0.15) !important; border-radius: 8px !important; color: #FFFFFF !important; font-weight: 750 !important; min-height: 2.55rem; box-shadow: 0 8px 18px rgba(31,111,104,0.18); }
    .stButton > button:hover { box-shadow: 0 10px 22px rgba(31,111,104,0.24); transform: translateY(-1px); opacity: 1 !important; }
    </style>
    """, unsafe_allow_html=True)


# ──────────────────────────────────────────────────────────────────────────────
# MOCK DATA GENERATORS & OLLAMA (PRESERVED)
# ──────────────────────────────────────────────────────────────────────────────
def generate_mock_claims(n: int = 120) -> pd.DataFrame:
    """Generate synthetic claims data matching new requirements."""
    random.seed(42)
    weights = [0.25, 0.30, 0.20, 0.10, 0.15]
    base_date = datetime(2024, 1, 1)

    records = []
    for i in range(n):
        cov  = random.choice(COVERAGE_TYPES)
        geo  = random.choice(GEOGRAPHIES)
        stat = random.choices(CLAIM_STATUSES, weights=weights)[0]
        
        fraud_score = random.uniform(80, 100) if stat == "FRAUD INVESTIGATION" else random.uniform(0, 45)
        is_travel_mismatch = random.random() < 0.08
        is_duplicate = random.random() < 0.05

        amount_map = {
            "Accidental Death"    : (50000, 500000), "Permanent Disability": (20000, 300000),
            "Hospitalisation"     : (2000, 80000),   "Emergency Evacuation": (5000, 150000),
            "Trip Cancellation"   : (500, 15000),    "Baggage Loss"        : (200, 5000),
        }
        lo, hi = amount_map[cov]
        
        records.append({
            "claim_id"        : f"CLM-{10000 + i}",
            "submitted_at"    : base_date + timedelta(days=random.randint(0, 365)),
            "coverage_type"   : cov,
            "geography"       : geo,
            "status"          : stat,
            "claim_amount"    : round(random.uniform(lo, hi), 2),
            "fraud_score"     : round(fraud_score, 1),
            "travel_mismatch" : is_travel_mismatch,
            "is_duplicate"    : is_duplicate,
            "processing_days" : random.randint(1, 45),
        })
    return pd.DataFrame(records)

def mock_ocr_text(doc_type_hint: str = "hospital_bill") -> str:
    samples = {
        "hospital_bill": """
            CITY GENERAL HOSPITAL — PATIENT BILL
            Patient: Rajesh Kumar Sharma
            Policy No: TRV-2024-INS-88742
            Date of Admission: 14 March 2024
            Date of Discharge: 19 March 2024
            Accident Date: 13 March 2024
            Location: Bangkok, Thailand
            Diagnosis: Fracture of right radius (S52.3), Laceration of forearm
            Treatment: Surgical fixation, physiotherapy sessions
            Room Charges: ₹42,000
            Surgical Charges: ₹1,18,500
            Medicines: ₹12,340
            Consultation: ₹8,500
            TOTAL DUE: ₹1,81,340
        """
    }
    return samples.get(doc_type_hint, samples["hospital_bill"])

def _ocr_image_bytes(image_bytes: bytes) -> Tuple[str, str]:
    try:
        from PIL import Image
        import pytesseract
    except ImportError:
        return "", "Image OCR requires `pytesseract` and `Pillow`."
    try:
        image = Image.open(BytesIO(image_bytes))
        text = pytesseract.image_to_string(image).strip()
        return text, ""
    except Exception as exc:
        return "", f"Image OCR failed: {exc}"

def extract_pdf_text(file_bytes: bytes) -> Tuple[str, str, str]:
    try:
        import fitz
    except ImportError:
        return "", "PDF text extraction requires `PyMuPDF`.", "PDF extraction unavailable"
    try:
        doc = fitz.open(stream=file_bytes, filetype="pdf")
    except Exception as exc:
        return "", f"Could not open PDF: {exc}", "PDF open failed"

    page_text: List[str] = []
    ocr_warnings: List[str] = []

    for page_index, page in enumerate(doc, start=1):
        text = page.get_text("text").strip()
        if text:
            page_text.append(f"--- Page {page_index} ---\n{text}")
            continue

        pix = page.get_pixmap(matrix=fitz.Matrix(2, 2), alpha=False)
        ocr_text, warning = _ocr_image_bytes(pix.tobytes("png"))
        if ocr_text:
            page_text.append(f"--- Page {page_index} OCR ---\n{ocr_text}")
        elif warning:
            ocr_warnings.append(f"Page {page_index}: {warning}")

    doc.close()
    extracted = "\n\n".join(page_text).strip()
    warning = " ".join(ocr_warnings)
    method = "PDF text extraction + OCR" if "OCR ---" in extracted else "PDF text extraction"
    return extracted, warning, method

def extract_uploaded_document_text(uploaded_file) -> Tuple[str, str, str]:
    file_bytes = uploaded_file.getvalue()
    file_type = (uploaded_file.type or "").lower()
    name = uploaded_file.name.lower()

    if file_type == "application/pdf" or name.endswith(".pdf"):
        return extract_pdf_text(file_bytes)
    if file_type.startswith("image/") or name.endswith((".png", ".jpg", ".jpeg", ".tif", ".tiff")):
        text, warning = _ocr_image_bytes(file_bytes)
        return text, warning, "Image OCR"
    if name.endswith((".txt", ".csv", ".tsv")) or file_type.startswith("text/"):
        for encoding in ("utf-8", "utf-16", "latin-1"):
            try:
                return file_bytes.decode(encoding).strip(), "", f"Text decode ({encoding})"
            except UnicodeDecodeError:
                continue
        return "", "Could not decode this text file.", "Text extraction failed"

    return "", "Unsupported document type. Upload a PDF, image, or text file.", "Unsupported"

@st.cache_data(ttl=30, show_spinner=False)
def get_ollama_status() -> Dict[str, Any]:
    try:
        response = requests.get(OLLAMA_TAGS_URL, timeout=3)
        response.raise_for_status()
        models = response.json().get("models", [])
        names = [m.get("name", "") for m in models if m.get("name")]
        for candidate in [OLLAMA_MODEL, *OLLAMA_FALLBACK_MODELS]:
            if any(name == candidate or name.startswith(f"{candidate}:") for name in names):
                return {"online": True, "model": candidate, "models": names, "using_fallback": candidate != OLLAMA_MODEL, "error": ""}
        return {"online": True, "model": "", "models": names, "using_fallback": False, "error": f"Run `ollama pull {OLLAMA_MODEL}`."}
    except Exception as exc:
        return {"online": False, "model": "", "models": [], "using_fallback": False, "error": str(exc)}

def active_model_label() -> str:
    status = get_ollama_status()
    return status["model"] or OLLAMA_MODEL

def ollama_generate(prompt: str, stream: bool = False) -> Optional[str]:
    status = get_ollama_status()
    if not status["online"]:
        st.error("Ollama is not reachable. Start it with `ollama serve`, then retry.")
        return None
    if not status["model"]:
        st.error(f"Ollama is running, but `{OLLAMA_MODEL}` is not available.")
        return None

    payload = {
        "model" : status["model"],
        "prompt": prompt,
        "stream": stream,
        "options": {"temperature": 0.05, "top_p": 0.9, "num_predict": 1024},
    }
    try:
        response = requests.post(OLLAMA_URL, json=payload, timeout=OLLAMA_TIMEOUT)
        response.raise_for_status()
        return response.json().get("response", "").strip()
    except Exception as e:
        st.error(f"🔴 **LLM Error:** {e}")
        return None


# ──────────────────────────────────────────────────────────────────────────────
# MODULAR PROMPT ENGINE
# ──────────────────────────────────────────────────────────────────────────────
class PromptEngine:
    @staticmethod
    def classification(text: str) -> str:
        return f"""You are an expert insurance document classifier. Given the OCR text, classify it into exactly one of these categories:
Death Certificate, Hospital Bill, Medical Report, Disability Assessment, Police Report, Boarding Pass, Insurance Policy, Claim Form, Discharge Summary, Unknown.
Respond with ONLY the category name. No explanation, no punctuation.

DOCUMENT TEXT:
\"\"\" {text} \"\"\"
Category:"""

    @staticmethod
    def extraction(text: str) -> str:
        return f"""You are an AI assistant for a Travel Personal Accident Insurance company.
Extract key information from the following document text into a structured JSON format.
Include fields like: patient_name, diagnosis, total_amount, date_of_service, location, incident_date.
Return ONLY valid JSON.

Document Text:
{text}"""

    @staticmethod
    def travel_validation(policy_geo: str, doc_location: str) -> str:
        return f"""You are a travel validation engine. 
Compare the Policy Geography '{policy_geo}' with the Location extracted from the document '{doc_location}'.
Determine if there is a geographical mismatch. Return JSON:
{{
    "mismatch": true/false,
    "reasoning": "brief explanation"
}}"""

    @staticmethod
    def medical_assessment(coverage: str, diagnosis: str) -> str:
        return f"""You are a medical assessment engine evaluating a Travel Personal Accident claim.
Coverage Type: {coverage}
Diagnosis/Treatment: {diagnosis}
Determine if the diagnosis represents a sudden accident/emergency covered under the policy or an excluded pre-existing/illness condition. Return JSON:
{{
    "approved_medically": true/false,
    "reasoning": "brief clinical justification"
}}"""

    @staticmethod
    def fraud_detection(claim_context: Dict[str, Any]) -> str:
        return f"""Analyze the following claim details for fraud indicators. Return JSON with overall_score (0-100), reasoning, and a list of 'signals' (name, description, risk_score).
Claim Details: {json.dumps(claim_context, default=str)}"""


# ──────────────────────────────────────────────────────────────────────────────
# MODULAR ADJUDICATION ENGINE
# ──────────────────────────────────────────────────────────────────────────────
class AdjudicationEngine:
    @staticmethod
    def run_travel_validation(claim: ClaimContext):
        doc_locs = [d.parsed_entities.get("location", "") for d in claim.documents]
        doc_loc = ", ".join(filter(None, doc_locs)) or "Unknown"
        prompt = PromptEngine.travel_validation(claim.geography, doc_loc)
        resp = ollama_generate(prompt)
        try:
            res_json = json.loads(re.search(r'\{.*\}', resp, re.DOTALL).group())
            claim.travel_mismatch = res_json.get("mismatch", False)
            claim.travel_reasoning = res_json.get("reasoning", "")
        except:
            claim.travel_mismatch = False
            claim.travel_reasoning = "Fallback: Validation unavailable."

    @staticmethod
    def run_medical_assessment(claim: ClaimContext):
        diags = [d.parsed_entities.get("diagnosis", "") for d in claim.documents]
        diag = ", ".join(filter(None, diags)) or "Unknown"
        prompt = PromptEngine.medical_assessment(claim.coverage_type, diag)
        resp = ollama_generate(prompt)
        try:
            res_json = json.loads(re.search(r'\{.*\}', resp, re.DOTALL).group())
            claim.medical_assessment_passed = res_json.get("approved_medically", False)
            claim.medical_reasoning = res_json.get("reasoning", "")
        except:
            claim.medical_assessment_passed = False
            claim.medical_reasoning = "Fallback: Manual review required."

    @staticmethod
    def run_fraud_detection(claim: ClaimContext):
        prompt = PromptEngine.fraud_detection(asdict(claim))
        resp = ollama_generate(prompt)
        try:
            res_json = json.loads(re.search(r'\{.*\}', resp, re.DOTALL).group())
            signals = [FraudSignal(**s) for s in res_json.get("signals", [])]
            claim.fraud_assessment = FraudAssessment(
                overall_score=res_json.get("overall_score", 0.0),
                signals=signals,
                reasoning=res_json.get("reasoning", "")
            )
        except:
            claim.fraud_assessment = FraudAssessment(overall_score=50.0, reasoning="Default fallback fraud score applied.")

    @staticmethod
    def make_decision(claim: ClaimContext):
        if claim.fraud_assessment.overall_score > 80:
            claim.final_status = "FRAUD INVESTIGATION"
            claim.decision_reasoning = "High fraud score detected."
        elif claim.travel_mismatch:
            claim.final_status = "REQUEST INFORMATION"
            claim.decision_reasoning = "Travel mismatch requires clarification."
        elif not claim.medical_assessment_passed:
            claim.final_status = "REJECT"
            claim.decision_reasoning = "Medical condition not covered under policy terms."
        elif claim.fraud_assessment.overall_score < 30 and claim.medical_assessment_passed:
            claim.final_status = "AUTO APPROVE"
            claim.decision_reasoning = "Clean claim, low risk, medically sound."
        else:
            claim.final_status = "MANUAL REVIEW"
            claim.decision_reasoning = "Borderline metrics require human adjuster review."


# ──────────────────────────────────────────────────────────────────────────────
# PAGES (8-Step Workflow)
# ──────────────────────────────────────────────────────────────────────────────
def page_dashboard(df: pd.DataFrame):
    st.markdown("""
        <div class="page-hero">
            <div class="page-kicker">Platform Overview</div>
            <h1>Dashboard Analytics</h1>
            <p>Monitor high-level adjudication metrics and throughput.</p>
        </div>
    """, unsafe_allow_html=True)

    total = len(df)
    avg_fraud = df["fraud_score"].mean()
    auto_approved = len(df[df["status"] == "AUTO APPROVE"])
    rejected = len(df[df["status"] == "REJECT"])
    investigation = len(df[df["status"] == "FRAUD INVESTIGATION"])
    travel_mismatches = df["travel_mismatch"].sum()
    duplicates = df["is_duplicate"].sum()

    col1, col2, col3, col4 = st.columns(4)
    with col1: st.markdown(f'<div class="card-metric"><div class="metric-value">{total}</div><div class="metric-label">Claims Processed</div></div>', unsafe_allow_html=True)
    with col2: st.markdown(f'<div class="card-metric"><div class="metric-value">{avg_fraud:.1f}</div><div class="metric-label">Avg Fraud Score</div></div>', unsafe_allow_html=True)
    with col3: st.markdown(f'<div class="card-metric"><div class="metric-value">{auto_approved}</div><div class="metric-label">Claims Auto Approved</div></div>', unsafe_allow_html=True)
    with col4: st.markdown(f'<div class="card-metric"><div class="metric-value">{rejected}</div><div class="metric-label">Claims Rejected</div></div>', unsafe_allow_html=True)

    st.write("")
    col5, col6, col7 = st.columns(3)
    with col5: st.markdown(f'<div class="card-metric"><div class="metric-value">{investigation}</div><div class="metric-label">Under Investigation</div></div>', unsafe_allow_html=True)
    with col6: st.markdown(f'<div class="card-metric"><div class="metric-value">{travel_mismatches}</div><div class="metric-label">Travel Mismatches</div></div>', unsafe_allow_html=True)
    with col7: st.markdown(f'<div class="card-metric"><div class="metric-value">{duplicates}</div><div class="metric-label">Duplicate Claims</div></div>', unsafe_allow_html=True)

    st.markdown('<div class="section-header">Status Distribution</div>', unsafe_allow_html=True)
    status_counts = df["status"].value_counts().reset_index()
    fig = px.bar(status_counts, x="status", y="count", color="status", template="plotly_white")
    st.plotly_chart(fig, use_container_width=True)

def page_intake():
    st.markdown("""
        <div class="page-hero">
            <div class="page-kicker">Step 1</div>
            <h1>Claim Intake</h1>
            <p>Register a new Travel PA claim and upload supporting documents.</p>
        </div>
    """, unsafe_allow_html=True)

    with st.form("intake_form"):
        col1, col2 = st.columns(2)
        policy_num = col1.text_input("Policy Number", "TRV-2024-GBL-88902")
        claim_amt = col2.number_input("Claim Amount ($)", min_value=0.0, value=1500.0)
        
        coverage = col1.selectbox("Coverage Type", COVERAGE_TYPES)
        geo = col2.selectbox("Policy Geography", GEOGRAPHIES)
        
        uploaded_files = st.file_uploader("Upload Documents (PDF, Images)", accept_multiple_files=True)
        submitted = st.form_submit_button("Initiate Claim")
        
        if submitted:
            claim_id = f"CLM-{random.randint(100000, 999999)}"
            new_claim = ClaimContext(
                claim_id=claim_id, policy_number=policy_num, submitted_at=datetime.now(),
                coverage_type=coverage, geography=geo, claim_amount=claim_amt
            )
            
            for uf in uploaded_files:
                new_claim.documents.append(ClaimDocument(
                    file_name=uf.name, file_type=uf.type, content_bytes=uf.getvalue()
                ))
                
            st.session_state["current_claim"] = new_claim
            st.success(f"Claim {claim_id} initiated successfully. Proceed to Document Processing.")

def page_processing():
    claim: ClaimContext = st.session_state.get("current_claim")
    if not claim: return st.warning("No active claim. Go to Claim Intake.")
    
    st.markdown(f"""
        <div class="page-hero">
            <div class="page-kicker">Step 2</div>
            <h1>Document Processing</h1>
            <p>Extracting text and structure for {claim.claim_id}.</p>
        </div>
    """, unsafe_allow_html=True)
    
    if st.button("Run OCR & Extraction"):
        with st.spinner("Processing documents with LLM..."):
            for doc in claim.documents:
                # Mock file object for existing extract function
                class MockFile:
                    def __init__(self, n, t, b): self.name = n; self.type = t; self.b = b
                    def getvalue(self): return self.b
                
                text, warn, method = extract_uploaded_document_text(MockFile(doc.file_name, doc.file_type, doc.content_bytes))
                if not text: text = mock_ocr_text("hospital_bill") # Fallback to mock if empty
                
                doc.extracted_text = text
                doc.ocr_method = method
                
                # Classify
                c_prompt = PromptEngine.classification(text[:1500])
                doc.doc_category = ollama_generate(c_prompt) or "Unknown"

                # Extract Entities
                e_prompt = PromptEngine.extraction(text)
                resp = ollama_generate(e_prompt)
                try:
                    doc.parsed_entities = json.loads(re.search(r'\{.*\}', resp, re.DOTALL).group())
                except:
                    doc.parsed_entities = {"raw_output": resp}
            st.success("Extraction Complete.")
            
    for doc in claim.documents:
        with st.expander(f"📄 {doc.file_name} ({doc.ocr_method}) - {doc.doc_category}"):
            st.json(doc.parsed_entities)

def page_travel():
    claim: ClaimContext = st.session_state.get("current_claim")
    if not claim: return st.warning("No active claim.")
    st.markdown('<div class="page-hero"><div class="page-kicker">Step 3</div><h1>Travel Validation</h1></div>', unsafe_allow_html=True)
    
    if st.button("Validate Travel Geography"):
        with st.spinner("Validating..."):
            AdjudicationEngine.run_travel_validation(claim)
        color = "danger" if claim.travel_mismatch else "success"
        st.markdown(f'<span class="badge badge-{color}">Mismatch: {claim.travel_mismatch}</span>', unsafe_allow_html=True)
        st.info(claim.travel_reasoning)

def page_medical():
    claim: ClaimContext = st.session_state.get("current_claim")
    if not claim: return st.warning("No active claim.")
    st.markdown('<div class="page-hero"><div class="page-kicker">Step 4</div><h1>Medical Assessment</h1></div>', unsafe_allow_html=True)
    
    if st.button("Run Medical Rules Engine"):
        with st.spinner("Assessing Medical Eligibility..."):
            AdjudicationEngine.run_medical_assessment(claim)
        color = "success" if claim.medical_assessment_passed else "danger"
        st.markdown(f'<span class="badge badge-{color}">Approved Medically: {claim.medical_assessment_passed}</span>', unsafe_allow_html=True)
        st.info(claim.medical_reasoning)

def page_fraud():
    claim: ClaimContext = st.session_state.get("current_claim")
    if not claim: return st.warning("No active claim.")
    st.markdown('<div class="page-hero"><div class="page-kicker">Step 5</div><h1>Fraud Detection</h1></div>', unsafe_allow_html=True)
    
    if st.button("Analyze Fraud Risk"):
        with st.spinner("Scoring..."):
            AdjudicationEngine.run_fraud_detection(claim)
        
        st.metric("Overall Risk Score", f"{claim.fraud_assessment.overall_score}/100")
        st.write(claim.fraud_assessment.reasoning)
        for sig in claim.fraud_assessment.signals:
            st.warning(f"**{sig.name}**: {sig.description} (Risk Impact: {sig.risk_score})")

def page_decision():
    claim: ClaimContext = st.session_state.get("current_claim")
    if not claim: return st.warning("No active claim.")
    st.markdown('<div class="page-hero"><div class="page-kicker">Step 6</div><h1>Decision Engine</h1></div>', unsafe_allow_html=True)
    
    if st.button("Generate Final Decision"):
        with st.spinner("Consolidating variables..."):
            AdjudicationEngine.make_decision(claim)
        
        color = "success" if claim.final_status == "AUTO APPROVE" else "danger" if claim.final_status in ["REJECT", "FRAUD INVESTIGATION"] else "warning"
        st.markdown(f'<span class="badge badge-{color}" style="font-size:1.2rem;">{claim.final_status}</span>', unsafe_allow_html=True)
        st.markdown(f"<div class='card'><b>Engine Reasoning:</b><br/> {claim.decision_reasoning}</div>", unsafe_allow_html=True)

def page_report():
    claim: ClaimContext = st.session_state.get("current_claim")
    if not claim: return st.warning("No active claim.")
    st.markdown('<div class="page-hero"><div class="page-kicker">Final Step</div><h1>Claim Report</h1></div>', unsafe_allow_html=True)
    
    report_dict = {
        "Claim ID": claim.claim_id,
        "Policy": claim.policy_number,
        "Final Status": claim.final_status,
        "Amount": claim.claim_amount,
        "Medical Approval": claim.medical_assessment_passed,
        "Travel Mismatch": claim.travel_mismatch,
        "Fraud Score": claim.fraud_assessment.overall_score,
        "Reasoning": claim.decision_reasoning
    }
    st.json(report_dict)

# ──────────────────────────────────────────────────────────────────────────────
# SIDEBAR NAVIGATION
# ──────────────────────────────────────────────────────────────────────────────
def render_sidebar() -> str:
    st.sidebar.markdown("<h2 style='color:white; margin-bottom:0;'>MarvelAI</h2>", unsafe_allow_html=True)
    st.sidebar.markdown("<p style='color:#8FA3BC; font-size:0.8rem; margin-top:0;'>Claims Platform</p>", unsafe_allow_html=True)
    st.sidebar.markdown("<hr/>", unsafe_allow_html=True)

    # Use dict keys directly for tracking navigation choice
    labels = list(PAGES.values())
    choice_label = st.sidebar.radio("Navigation", labels)
    
    if st.sidebar.button("Clear Session", use_container_width=True):
        for k in list(st.session_state.keys()): del st.session_state[k]
        st.rerun()

    # Version footer
    st.sidebar.markdown(
        '<div style="font-size:0.65rem;color:rgba(255,255,255,0.28);'
        'margin-top:2rem;text-align:center;padding-bottom:1rem;">'
        f'v2.0 &nbsp;·&nbsp; {active_model_label()} via Ollama</div>',
        unsafe_allow_html=True,
    )
    
    # Return the key corresponding to the selected value
    return [k for k, v in PAGES.items() if v == choice_label][0]

# ──────────────────────────────────────────────────────────────────────────────
# MAIN ENTRYPOINT
# ──────────────────────────────────────────────────────────────────────────────
def main() -> None:
    inject_css()

    if "mock_claims_df" not in st.session_state:
        st.session_state["mock_claims_df"] = generate_mock_claims(120)

    active_page = render_sidebar()

    if active_page == "dashboard": page_dashboard(st.session_state["mock_claims_df"])
    elif active_page == "intake": page_intake()
    elif active_page == "processing": page_processing()
    elif active_page == "travel": page_travel()
    elif active_page == "medical": page_medical()
    elif active_page == "fraud": page_fraud()
    elif active_page == "decision": page_decision()
    elif active_page == "report": page_report()

if __name__ == "__main__":
    main()