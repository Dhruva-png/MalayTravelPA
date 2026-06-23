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
ollama>=0.1.8
"""

import json
import random
import re
import time
import uuid
from datetime import date, datetime, timedelta
from io import BytesIO
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import requests
import streamlit as st

st.set_page_config(
    page_title="MarvelAI · Claims Portal",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded",
)

OLLAMA_URL   = "http://localhost:11434/api/generate"
OLLAMA_MODEL = "llama3.2"
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

def inject_css() -> None:
    st.markdown("""
    <style>
    /* ── Root palette ─────────────────────────────── */
    :root {
        --brand-primary  : #0A2540;   /* deep navy          */
        --brand-accent   : #00A3FF;   /* electric blue      */
        --brand-success  : #00C9A7;   /* teal green         */
        --brand-warning  : #FFB830;   /* amber              */
        --brand-danger   : #FF4757;   /* crisp red          */
        --surface        : #FFFFFF;
        --surface-raised : #F4F7FB;
        --border         : #E2E8F0;
        --text-primary   : #0A2540;
        --text-secondary : #64748B;
        --font-sans      : "Inter", "Segoe UI", sans-serif;
        --font-mono      : "JetBrains Mono", "Fira Code", monospace;
    }

    /* ── Global resets ─────────────────────────────── */
    html, body, [data-testid="stAppViewContainer"] {
        background: var(--surface-raised) !important;
        font-family: var(--font-sans) !important;
        color: var(--text-primary) !important;
    }

    /* ── Sidebar ───────────────────────────────────── */
    [data-testid="stSidebar"] {
        background: var(--brand-primary) !important;
        border-right: 3px solid var(--brand-accent) !important;
    }
    [data-testid="stSidebar"] * {
        color: #FFFFFF !important;
    }
    [data-testid="stSidebar"] .stRadio label {
        font-size: 0.9rem;
        padding: 0.4rem 0;
        border-radius: 6px;
        cursor: pointer;
        transition: background 0.15s;
    }
    [data-testid="stSidebar"] .stRadio label:hover {
        background: rgba(0,163,255,0.15) !important;
    }

    /* ── Cards ─────────────────────────────────────── */
    .card {
        background: var(--surface);
        border: 1px solid var(--border);
        border-radius: 12px;
        padding: 1.4rem 1.6rem;
        margin-bottom: 1rem;
        box-shadow: 0 1px 4px rgba(10,37,64,0.06);
    }
    .card-metric {
        background: var(--surface);
        border: 1px solid var(--border);
        border-radius: 10px;
        padding: 1.1rem 1.2rem;
        text-align: center;
        box-shadow: 0 1px 3px rgba(10,37,64,0.05);
    }
    .metric-value {
        font-size: 2rem;
        font-weight: 700;
        color: var(--brand-primary);
        line-height: 1.1;
    }
    .metric-label {
        font-size: 0.75rem;
        color: var(--text-secondary);
        text-transform: uppercase;
        letter-spacing: 0.08em;
        margin-top: 0.3rem;
    }
    .metric-delta-up   { color: var(--brand-success); font-size: 0.8rem; }
    .metric-delta-down { color: var(--brand-danger);  font-size: 0.8rem; }

    /* ── Status badges ─────────────────────────────── */
    .badge {
        display: inline-block;
        padding: 0.2rem 0.65rem;
        border-radius: 999px;
        font-size: 0.72rem;
        font-weight: 600;
        letter-spacing: 0.05em;
        text-transform: uppercase;
    }
    .badge-success  { background:#D1FAF4; color:#00856F; }
    .badge-warning  { background:#FFF3CD; color:#7D5A00; }
    .badge-danger   { background:#FFE4E6; color:#B91C1C; }
    .badge-info     { background:#DBEAFE; color:#1D4ED8; }
    .badge-neutral  { background:#F1F5F9; color:#475569; }

    /* ── Section headers ───────────────────────────── */
    .section-header {
        font-size: 1.05rem;
        font-weight: 700;
        color: var(--brand-primary);
        border-left: 4px solid var(--brand-accent);
        padding-left: 0.75rem;
        margin: 1.4rem 0 0.9rem;
        letter-spacing: -0.01em;
    }

    /* ── Fraud score bar ───────────────────────────── */
    .fraud-bar-wrapper { width: 100%; background: var(--border); border-radius: 999px; height: 10px; margin: 0.4rem 0; }
    .fraud-bar { height: 10px; border-radius: 999px; transition: width 0.4s ease; }

    /* ── JSON output ───────────────────────────────── */
    .json-box {
        background: #F8FAFC;
        border: 1px solid var(--border);
        border-radius: 8px;
        padding: 1rem;
        font-family: var(--font-mono);
        font-size: 0.8rem;
        overflow-x: auto;
        line-height: 1.7;
    }

    /* ── Tables ────────────────────────────────────── */
    .dataframe thead th {
        background: var(--brand-primary) !important;
        color: #fff !important;
        font-size: 0.78rem;
        text-transform: uppercase;
        letter-spacing: 0.06em;
    }

    /* ── Hide Streamlit chrome ─────────────────────── */
    #MainMenu, footer, header { visibility: hidden; }
    [data-testid="stDecoration"] { display: none; }
    </style>
    """, unsafe_allow_html=True)


def generate_mock_claims(n: int = 120) -> pd.DataFrame:
    """Generate synthetic claims data for dashboard analytics."""
    random.seed(42)
    statuses  = ["Approved", "Pending", "Rejected", "Under Review", "Fraud Flagged"]
    weights   = [0.40, 0.25, 0.15, 0.12, 0.08]
    base_date = datetime(2024, 1, 1)

    records = []
    for i in range(n):
        cov  = random.choice(COVERAGE_TYPES)
        geo  = random.choice(GEOGRAPHIES)
        stat = random.choices(statuses, weights=weights)[0]
        fraud_score = (
            random.uniform(65, 98) if stat == "Fraud Flagged"
            else random.uniform(0, 40)
        )
        amount_map = {
            "Accidental Death"    : (50000, 500000),
            "Permanent Disability": (20000, 300000),
            "Hospitalisation"     : (2000,  80000),
            "Emergency Evacuation": (5000,  150000),
            "Trip Cancellation"   : (500,   15000),
            "Baggage Loss"        : (200,   5000),
        }
        lo, hi = amount_map[cov]
        records.append({
            "claim_id"     : f"CLM-{10000 + i}",
            "submitted_at" : base_date + timedelta(days=random.randint(0, 365)),
            "coverage_type": cov,
            "geography"    : geo,
            "status"       : stat,
            "claim_amount" : round(random.uniform(lo, hi), 2),
            "fraud_score"  : round(fraud_score, 1),
            "processing_days": random.randint(1, 45),
        })
    return pd.DataFrame(records)


def mock_ocr_text(doc_type_hint: str = "hospital_bill") -> str:
    """Return mock OCR-extracted text for a given document type."""
    samples = {
        "hospital_bill": """
CITY GENERAL HOSPITAL — PATIENT BILL
Patient: Dhruva Sandeep
Policy No: TRV-2024-INS-88742
Date of Admission: 14 March 2024    Date of Discharge: 19 March 2024
Accident Date: 13 March 2024        Location: Bangkok, Thailand
Diagnosis: Fracture of right radius (S52.3), Laceration of forearm
Treatment: Surgical fixation, physiotherapy sessions
Room Charges: ₹42,000   Surgical Charges: ₹1,18,500
Medicines: ₹12,340      Consultation: ₹8,500
TOTAL DUE: ₹1,81,340
Nominee: Rani Ramnani (Spouse)
Bank Account: HDFC Bank, A/C 50200012345678, IFSC HDFC0001234
""",
        "death_certificate": """
DEATH CERTIFICATE — MUNICIPALITY OF PARIS, FRANCE
Deceased: Anita Raghunathan, DOB: 12-Jun-1978
Date of Death: 03 November 2024
Cause: Road Traffic Accident — multiple trauma
Policy No: TRV-2024-GBL-44211
Insurer: MarvelAI Travel PA
Nominee/Claimant: Vikram Raghunathan (Husband)
Nationality: Indian    Passport: P9234567
Bank Account: SBI, A/C 31209876543, IFSC SBIN0007654
""",
        "disability_report": """
DISABILITY ASSESSMENT REPORT
Patient: Sandeep Pillai     Policy No: TRV-2024-SEA-30019
Date of Accident: 22 January 2024    Location: Kuala Lumpur, Malaysia
Nature of Injury: Traumatic amputation of left index finger (M00.87)
Disability %: 15% Permanent Partial Disability
Assessed by: Dr. Fatimah Binti Hassan, MBBS, MS Ortho
Hospital: Sunway Medical Centre, Petaling Jaya
Hospitalisation: 22 Jan 2024 – 28 Jan 2024
Treatment Cost: MYR 28,500 (approx ₹5,10,000)
Nominee: Deepa Pillai (Spouse)
Bank Account: Axis Bank, A/C 9170200012345678, IFSC UTIB0001234
""",
    }
    return samples.get(doc_type_hint, samples["hospital_bill"])

def ollama_generate(prompt: str, stream: bool = False) -> Optional[str]:
    """
    Call the local Ollama /api/generate endpoint.
    Returns the model's text response or None on failure.
    """
    payload = {
        "model" : OLLAMA_MODEL,
        "prompt": prompt,
        "stream": stream,
        "options": {"temperature": 0.1, "num_predict": 1024},
    }
    try:
        response = requests.post(OLLAMA_URL, json=payload, timeout=OLLAMA_TIMEOUT)
        response.raise_for_status()
        return response.json().get("response", "").strip()
    except requests.exceptions.ConnectionError:
        st.error(
            "⚠️ **Ollama not reachable.** "
            "Start the local Ollama server with `ollama serve` and ensure "
            f"`{OLLAMA_MODEL}` is pulled via `ollama pull {OLLAMA_MODEL}`."
        )
    except requests.exceptions.Timeout:
        st.error("⏱️ **LLM request timed out.** The model may be loading — please retry.")
    except requests.exceptions.HTTPError as e:
        st.error(f"🔴 **Ollama HTTP error:** {e}")
    except Exception as e:
        st.error(f"🔴 **Unexpected error calling LLM:** {e}")
    return None

CLASSIFY_PROMPT = """You are an expert insurance document classifier.
Given the OCR text of an insurance-related document, classify it into exactly one
of these categories:
Death Certificate, Hospital Bill, Medical Report, Disability Assessment,
Police Report, Boarding Pass, Insurance Policy, Claim Form, Discharge Summary, Unknown.

Respond with ONLY the category name. No explanation, no punctuation.

DOCUMENT TEXT:
\"\"\"
{text}
\"\"\"

Category:"""

EXTRACT_PROMPT = """You are a precise insurance data extraction engine.
Extract the following fields from the document text and return a valid JSON object.
If a field is not found, use null. Dates must be in ISO 8601 format (YYYY-MM-DD).
Currency amounts must be numeric (no symbols).

Required fields:
- policy_number       (string)
- insured_name        (string)
- nominee_name        (string)
- nominee_relation    (string)
- accident_date       (date)
- accident_location   (string)
- nature_of_injury    (string)
- diagnosis_codes     (array of strings, ICD-10 codes)
- admission_date      (date)
- discharge_date      (date)
- treatment_costs_inr (number)
- disability_percent  (number or null)
- bank_account_number (string)
- bank_name           (string)
- bank_ifsc           (string)

Return ONLY the JSON object. No markdown, no explanation.

DOCUMENT TEXT:
\"\"\"
{text}
\"\"\"

JSON:"""

FRAUD_PROMPT = """You are a senior insurance fraud analyst specialising in Travel PA claims.
Analyse the document text for anomalies and fraud indicators.

Score the claim on a scale from 0 (no risk) to 100 (definite fraud).
Look for:
- Injury description inconsistent with accident type or mechanism
- Treatment costs unusually high or low for the stated diagnosis
- Dates that are logically impossible (discharge before admission, accident after policy expiry)
- Vague or generic language suggesting fabrication
- Missing or mismatched nominee / bank details
- Diagnosis codes inconsistent with described injury

Respond ONLY with a JSON object in this exact format:
{{
  "fraud_score": <integer 0-100>,
  "risk_level": "<Low|Medium|High|Critical>",
  "flags": ["<flag 1>", "<flag 2>"],
  "summary": "<one-sentence fraud assessment>"
}}

DOCUMENT TEXT:
\"\"\"
{text}
\"\"\"

JSON:"""


def classify_document(text: str) -> str:
    """Use LLM to classify the document type."""
    prompt   = CLASSIFY_PROMPT.format(text=text[:3000])  # token budget
    response = ollama_generate(prompt)
    if response:
        # Sanitise: keep only the first line and match to known types
        first_line = response.strip().split("\n")[0].strip(" .,\"'")
        for doc_type in DOC_TYPES:
            if doc_type.lower() in first_line.lower():
                return doc_type
        return first_line or "Unknown"
    return "Unknown (LLM unavailable)"


def extract_data(text: str) -> Dict[str, Any]:
    """Use LLM to extract structured claim data as a dict."""
    prompt   = EXTRACT_PROMPT.format(text=text[:3000])
    response = ollama_generate(prompt)
    if not response:
        return {}
    # Strip any markdown fences before parsing
    clean = re.sub(r"```(?:json)?|```", "", response).strip()
    try:
        return json.loads(clean)
    except json.JSONDecodeError:
        st.warning("⚠️ LLM returned non-JSON output for extraction; using raw text.")
        return {"raw_response": response}


def score_fraud(text: str) -> Dict[str, Any]:
    """Use LLM to compute a fraud risk score and return flags."""
    prompt   = FRAUD_PROMPT.format(text=text[:3000])
    response = ollama_generate(prompt)
    if not response:
        return {}
    clean = re.sub(r"```(?:json)?|```", "", response).strip()
    try:
        return json.loads(clean)
    except json.JSONDecodeError:
        st.warning("⚠️ LLM returned non-JSON output for fraud scoring; showing raw.")
        return {"raw_response": response}

# Simulated policy database
MOCK_POLICIES: Dict[str, Dict] = {
    "TRV-2024-INS-88742": {
        "holder"         : "Rajesh Kumar Sharma",
        "coverage_start" : date(2024, 3, 1),
        "coverage_end"   : date(2024, 4, 30),
        "coverage_types" : ["Hospitalisation", "Accidental Death", "Permanent Disability"],
        "sum_assured"    : 500000,
    },
    "TRV-2024-GBL-44211": {
        "holder"         : "Anita Raghunathan",
        "coverage_start" : date(2024, 10, 25),
        "coverage_end"   : date(2024, 11, 15),
        "coverage_types" : ["Accidental Death", "Emergency Evacuation"],
        "sum_assured"    : 1000000,
    },
    "TRV-2024-SEA-30019": {
        "holder"         : "Santhosh Pillai",
        "coverage_start" : date(2024, 1, 20),
        "coverage_end"   : date(2024, 2, 5),
        "coverage_types" : ["Permanent Disability", "Hospitalisation"],
        "sum_assured"    : 300000,
    },
}

SUBMITTED_CLAIMS: List[str] = ["TRV-2024-INS-77001", "TRV-2024-GBL-11980"]


def validate_claim(extracted: Dict[str, Any]) -> List[Dict[str, str]]:
    """
    Run rule-based validations on extracted claim data.
    Returns a list of validation result dicts:
      {"rule": str, "status": "Pass"|"Fail"|"Warning", "message": str}
    """
    results: List[Dict[str, str]] = []

    policy_no  = extracted.get("policy_number")
    acc_date_s = extracted.get("accident_date")
    adm_date_s = extracted.get("admission_date")
    dis_date_s = extracted.get("discharge_date")
    cost       = extracted.get("treatment_costs_inr")
    disability = extracted.get("disability_percent")

    policy = MOCK_POLICIES.get(policy_no) if policy_no else None
    if not policy_no:
        results.append({"rule": "Policy Number Present", "status": "Fail",
                         "message": "Policy number not found in document."})
    elif not policy:
        results.append({"rule": "Policy Exists", "status": "Fail",
                         "message": f"Policy '{policy_no}' not found in system."})
    else:
        results.append({"rule": "Policy Exists", "status": "Pass",
                         "message": f"Policy {policy_no} verified."})

    if policy and extracted.get("insured_name"):
        name_match = (
            extracted["insured_name"].strip().lower()
            == policy["holder"].strip().lower()
        )
        results.append({
            "rule"   : "Insured Name Match",
            "status" : "Pass" if name_match else "Fail",
            "message": "Name matches policy record." if name_match
                       else f"Name mismatch: '{extracted['insured_name']}' vs '{policy['holder']}'.",
        })

    # ── Rule 3: Accident within coverage period ───────────────────────────────
    if policy and acc_date_s:
        try:
            acc_date = datetime.fromisoformat(str(acc_date_s)).date()
            in_period = policy["coverage_start"] <= acc_date <= policy["coverage_end"]
            results.append({
                "rule"   : "Accident Within Coverage Period",
                "status" : "Pass" if in_period else "Fail",
                "message": f"Accident {acc_date} within {policy['coverage_start']} – {policy['coverage_end']}."
                           if in_period
                           else f"Accident on {acc_date} is OUTSIDE coverage period "
                                f"{policy['coverage_start']} – {policy['coverage_end']}.",
            })
        except (ValueError, TypeError):
            results.append({"rule": "Accident Within Coverage Period", "status": "Warning",
                             "message": f"Could not parse accident date: {acc_date_s}"})
    else:
        results.append({"rule": "Accident Date Present", "status": "Warning",
                         "message": "Accident date not extracted."})

    # ── Rule 4: Logical date sequence ─────────────────────────────────────────
    if adm_date_s and dis_date_s:
        try:
            adm = datetime.fromisoformat(str(adm_date_s)).date()
            dis = datetime.fromisoformat(str(dis_date_s)).date()
            if dis >= adm:
                results.append({"rule": "Discharge After Admission", "status": "Pass",
                                 "message": f"Discharged {dis} (admitted {adm})."})
            else:
                results.append({"rule": "Discharge After Admission", "status": "Fail",
                                 "message": f"Discharge ({dis}) precedes admission ({adm}) — impossible dates."})
        except (ValueError, TypeError):
            results.append({"rule": "Discharge After Admission", "status": "Warning",
                             "message": "Could not parse hospitalisation dates."})

    # ── Rule 5: Benefit eligibility ───────────────────────────────────────────
    if policy:
        for cov in policy["coverage_types"]:
            results.append({
                "rule"   : f"Coverage: {cov}",
                "status" : "Pass",
                "message": f"'{cov}' included in policy {policy_no}.",
            })

    # ── Rule 6: Duplicate claim detection ─────────────────────────────────────
    if policy_no in SUBMITTED_CLAIMS:
        results.append({"rule": "Duplicate Claim Check", "status": "Fail",
                         "message": f"A claim for policy {policy_no} was already submitted."})
    else:
        results.append({"rule": "Duplicate Claim Check", "status": "Pass",
                         "message": "No duplicate claim found for this policy."})

    # ── Rule 7: Treatment cost within sum assured ─────────────────────────────
    if policy and cost:
        try:
            cost_f = float(cost)
            if cost_f <= policy["sum_assured"]:
                results.append({"rule": "Cost Within Sum Assured", "status": "Pass",
                                 "message": f"₹{cost_f:,.0f} ≤ Sum Assured ₹{policy['sum_assured']:,.0f}."})
            else:
                results.append({"rule": "Cost Within Sum Assured", "status": "Warning",
                                 "message": f"₹{cost_f:,.0f} exceeds sum assured ₹{policy['sum_assured']:,.0f}."})
        except (ValueError, TypeError):
            pass

    # ── Rule 8: Disability percentage range ──────────────────────────────────
    if disability is not None:
        try:
            pct = float(disability)
            if 0 < pct <= 100:
                results.append({"rule": "Disability % Valid", "status": "Pass",
                                 "message": f"Disability {pct}% is within valid range."})
            else:
                results.append({"rule": "Disability % Valid", "status": "Fail",
                                 "message": f"Disability percentage {pct}% is out of range (1–100)."})
        except (ValueError, TypeError):
            pass

    # ── Rule 9: Bank details present ─────────────────────────────────────────
    has_bank = all(extracted.get(f) for f in ["bank_account_number", "bank_name", "bank_ifsc"])
    results.append({
        "rule"   : "Bank Details Present",
        "status" : "Pass" if has_bank else "Warning",
        "message": "All bank details found." if has_bank else "Incomplete bank details — manual verification required.",
    })

    return results

def badge_html(status: str) -> str:
    mapping = {
        "Pass"    : "badge-success",
        "Fail"    : "badge-danger",
        "Warning" : "badge-warning",
        "High"    : "badge-danger",
        "Medium"  : "badge-warning",
        "Low"     : "badge-success",
        "Critical": "badge-danger",
    }
    cls = mapping.get(status, "badge-neutral")
    return f'<span class="badge {cls}">{status}</span>'


def metric_card(label: str, value: str, delta: str = "", delta_up: bool = True) -> str:
    delta_cls  = "metric-delta-up" if delta_up else "metric-delta-down"
    delta_html = f'<div class="{delta_cls}">{delta}</div>' if delta else ""
    return f"""
    <div class="card-metric">
        <div class="metric-value">{value}</div>
        <div class="metric-label">{label}</div>
        {delta_html}
    </div>"""


def fraud_bar_html(score: float) -> str:
    if score < 30:
        colour = "#00C9A7"
    elif score < 60:
        colour = "#FFB830"
    else:
        colour = "#FF4757"
    return f"""
    <div class="fraud-bar-wrapper">
        <div class="fraud-bar" style="width:{score}%; background:{colour};"></div>
    </div>
    <small style="color:var(--text-secondary);">{score:.1f} / 100</small>
    """


def section_header(title: str) -> None:
    st.markdown(f'<div class="section-header">{title}</div>', unsafe_allow_html=True)

def page_dashboard(df: pd.DataFrame) -> None:
    st.markdown("## 📊 Claims Analytics Dashboard")
    st.markdown("Real-time overview of submitted travel PA insurance claims.")

    # ── Filters ───────────────────────────────────────────────────────────────
    with st.expander("🔍 Filter Claims", expanded=False):
        c1, c2, c3 = st.columns(3)
        with c1:
            sel_cov = st.multiselect("Coverage Type", COVERAGE_TYPES, default=COVERAGE_TYPES)
        with c2:
            sel_geo = st.multiselect("Geography", GEOGRAPHIES, default=GEOGRAPHIES)
        with c3:
            min_d = df["submitted_at"].min().date()
            max_d = df["submitted_at"].max().date()
            date_range = st.date_input("Travel Period", (min_d, max_d))

    # Apply filters
    mask = (
        df["coverage_type"].isin(sel_cov) &
        df["geography"].isin(sel_geo)
    )
    if isinstance(date_range, (list, tuple)) and len(date_range) == 2:
        mask &= (
            (df["submitted_at"].dt.date >= date_range[0]) &
            (df["submitted_at"].dt.date <= date_range[1])
        )
    fdf = df[mask]

    # ── KPI Metric Row ────────────────────────────────────────────────────────
    section_header("Key Performance Indicators")
    m1, m2, m3, m4, m5 = st.columns(5)

    total_claims  = len(fdf)
    total_value   = fdf["claim_amount"].sum()
    approved      = len(fdf[fdf["status"] == "Approved"])
    fraud_flagged = len(fdf[fdf["status"] == "Fraud Flagged"])
    avg_days      = fdf["processing_days"].mean()

    with m1:
        st.markdown(metric_card("Total Claims", f"{total_claims:,}"), unsafe_allow_html=True)
    with m2:
        st.markdown(metric_card("Total Value", f"₹{total_value/1e6:.2f}M"), unsafe_allow_html=True)
    with m3:
        pct = f"{approved/total_claims*100:.1f}% ↑" if total_claims else "—"
        st.markdown(metric_card("Approved", f"{approved:,}", pct, True), unsafe_allow_html=True)
    with m4:
        st.markdown(metric_card("Fraud Flagged", f"{fraud_flagged:,}",
                                f"{fraud_flagged/total_claims*100:.1f}%", False),
                    unsafe_allow_html=True)
    with m5:
        st.markdown(metric_card("Avg Processing", f"{avg_days:.1f}d"), unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # ── Charts Row 1 ──────────────────────────────────────────────────────────
    section_header("Claims Distribution")
    ch1, ch2 = st.columns(2)

    with ch1:
        status_counts = fdf["status"].value_counts().reset_index()
        status_counts.columns = ["Status", "Count"]
        color_map = {
            "Approved"     : "#00C9A7",
            "Pending"      : "#FFB830",
            "Rejected"     : "#FF4757",
            "Under Review" : "#00A3FF",
            "Fraud Flagged": "#9333EA",
        }
        fig = px.pie(
            status_counts, names="Status", values="Count",
            color="Status", color_discrete_map=color_map,
            title="Claim Status Breakdown",
            hole=0.55,
        )
        fig.update_traces(textposition="outside", textinfo="label+percent")
        fig.update_layout(
            showlegend=False,
            margin=dict(t=40, b=10, l=10, r=10),
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor ="rgba(0,0,0,0)",
            title_font_size=13,
        )
        st.plotly_chart(fig, use_container_width=True)

    with ch2:
        cov_amounts = (
            fdf.groupby("coverage_type")["claim_amount"]
            .sum()
            .reset_index()
            .sort_values("claim_amount", ascending=True)
        )
        fig2 = px.bar(
            cov_amounts,
            x="claim_amount", y="coverage_type",
            orientation="h",
            title="Total Claim Value by Coverage Type",
            labels={"claim_amount": "Amount (₹)", "coverage_type": ""},
            color="claim_amount",
            color_continuous_scale=["#DBEAFE", "#0A2540"],
        )
        fig2.update_layout(
            coloraxis_showscale=False,
            margin=dict(t=40, b=10, l=10, r=10),
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor ="rgba(0,0,0,0)",
            title_font_size=13,
        )
        st.plotly_chart(fig2, use_container_width=True)

    # ── Charts Row 2 ──────────────────────────────────────────────────────────
    section_header("Trend & Geography")
    ch3, ch4 = st.columns(2)

    with ch3:
        fdf_copy = fdf.copy()
        fdf_copy["month"] = fdf_copy["submitted_at"].dt.to_period("M").dt.to_timestamp()
        monthly = (
            fdf_copy.groupby(["month", "status"])["claim_id"]
            .count()
            .reset_index()
            .rename(columns={"claim_id": "count"})
        )
        fig3 = px.area(
            monthly, x="month", y="count", color="status",
            title="Monthly Submissions by Status",
            color_discrete_map=color_map,
            labels={"month": "Month", "count": "Claims"},
        )
        fig3.update_layout(
            margin=dict(t=40, b=10, l=10, r=10),
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor ="rgba(0,0,0,0)",
            title_font_size=13,
            legend_title_text="",
        )
        st.plotly_chart(fig3, use_container_width=True)

    with ch4:
        geo_counts = fdf.groupby("geography").agg(
            claims=("claim_id", "count"),
            avg_fraud=("fraud_score", "mean"),
        ).reset_index()
        fig4 = px.scatter(
            geo_counts,
            x="claims", y="avg_fraud",
            size="claims", color="geography",
            text="geography",
            title="Geography: Volume vs Avg Fraud Score",
            labels={"claims": "Claim Count", "avg_fraud": "Avg Fraud Score"},
        )
        fig4.update_traces(textposition="top center")
        fig4.update_layout(
            showlegend=False,
            margin=dict(t=40, b=10, l=10, r=10),
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor ="rgba(0,0,0,0)",
            title_font_size=13,
        )
        st.plotly_chart(fig4, use_container_width=True)

    # ── Recent Claims Table ───────────────────────────────────────────────────
    section_header("Recent Claims")
    display_df = fdf.sort_values("submitted_at", ascending=False).head(15).copy()
    display_df["submitted_at"] = display_df["submitted_at"].dt.strftime("%d %b %Y")
    display_df["claim_amount"] = display_df["claim_amount"].apply(lambda x: f"₹{x:,.0f}")
    display_df["fraud_score"]  = display_df["fraud_score"].apply(lambda x: f"{x:.1f}")
    st.dataframe(
        display_df.rename(columns={
            "claim_id"      : "Claim ID",
            "submitted_at"  : "Submitted",
            "coverage_type" : "Coverage",
            "geography"     : "Geography",
            "status"        : "Status",
            "claim_amount"  : "Amount",
            "fraud_score"   : "Fraud Score",
            "processing_days": "Days",
        }),
        use_container_width=True,
        hide_index=True,
    )

def page_ingestion() -> None:
    st.markdown("## 📥 Claim Document Ingestion")
    st.markdown(
        "Upload claim-related documents (scanned images or PDFs). "
        "The system will extract and classify each file automatically."
    )

    uploaded_files = st.file_uploader(
        "Drop claim documents here",
        type=["pdf", "png", "jpg", "jpeg", "tiff"],
        accept_multiple_files=True,
        help="Accepted formats: PDF, PNG, JPG, TIFF — max 10 MB per file",
    )

    if not uploaded_files:
        st.info("👆 Upload one or more documents to begin.")
        return

    section_header(f"{len(uploaded_files)} Document(s) Uploaded")

    # Document-type selector (mock OCR source)
    mock_type_map = {
        "Hospital Bill"       : "hospital_bill",
        "Death Certificate"   : "death_certificate",
        "Disability Report"   : "disability_report",
    }
    selected_mock = st.selectbox(
        "🔬 For this demo, choose the mock OCR content to use:",
        list(mock_type_map.keys()),
        help="In production, a real OCR engine extracts text from the uploaded file.",
    )

    for file in uploaded_files:
        with st.container():
            st.markdown('<div class="card">', unsafe_allow_html=True)
            c1, c2 = st.columns([3, 1])
            with c1:
                st.markdown(f"**{file.name}**  "
                            f"<span style='color:var(--text-secondary);font-size:0.82rem;'>"
                            f"{file.size / 1024:.1f} KB · {file.type}</span>",
                            unsafe_allow_html=True)
            with c2:
                # Preview image if possible
                if file.type.startswith("image/"):
                    st.image(file, use_container_width=True)
                else:
                    st.markdown("📄 PDF document")

            # Store OCR text and file metadata in session state
            ocr_key  = f"ocr_{file.name}"
            meta_key = f"meta_{file.name}"
            if ocr_key not in st.session_state:
                st.session_state[ocr_key]  = mock_ocr_text(mock_type_map[selected_mock])
                st.session_state[meta_key] = {
                    "filename"   : file.name,
                    "size_kb"    : round(file.size / 1024, 1),
                    "upload_ts"  : datetime.now().isoformat(),
                    "claim_ref"  : f"CLM-{uuid.uuid4().hex[:8].upper()}",
                }

            meta = st.session_state[meta_key]
            st.markdown(
                f"**Claim Ref:** `{meta['claim_ref']}`  &nbsp;|&nbsp;  "
                f"**Uploaded:** {meta['upload_ts'][:19].replace('T', ' ')}",
                unsafe_allow_html=True,
            )

            with st.expander("🔍 View Extracted OCR Text"):
                st.code(st.session_state[ocr_key], language="text")

            st.markdown("</div>", unsafe_allow_html=True)

    if uploaded_files:
        st.success(
            f"✅ {len(uploaded_files)} document(s) ingested. "
            "Proceed to **Processing & Extraction** in the sidebar."
        )

def page_processing() -> None:
    st.markdown("## ⚙️ Processing & Data Extraction")
    st.markdown(
        "Classify each document type and extract structured data fields "
        "using the local LLM (`llama3.2`)."
    )

    # Collect ingested documents from session state
    ocr_keys = [k for k in st.session_state if k.startswith("ocr_")]
    if not ocr_keys:
        st.warning("No documents ingested yet. Go to **Claim Ingestion** first.")
        return

    for ocr_key in ocr_keys:
        filename = ocr_key.replace("ocr_", "")
        meta_key = f"meta_{filename}"
        meta     = st.session_state.get(meta_key, {})
        text     = st.session_state[ocr_key]

        st.markdown(f'<div class="card">', unsafe_allow_html=True)
        st.markdown(f"### 📄 {filename}")
        st.markdown(f"Claim Ref: `{meta.get('claim_ref', 'N/A')}`")

        col_cls, col_ext = st.columns(2)

        # ── Classification ────────────────────────────────────────────────────
        with col_cls:
            section_header("Step 1 · Document Classification")
            cls_key = f"cls_{filename}"
            if st.button(f"🏷 Classify", key=f"btn_cls_{filename}"):
                with st.spinner("Sending to LLM for classification…"):
                    doc_type = classify_document(text)
                    st.session_state[cls_key] = doc_type
            if cls_key in st.session_state:
                st.markdown(
                    f"**Detected Type:** "
                    f"{badge_html(st.session_state[cls_key])}",
                    unsafe_allow_html=True,
                )
            else:
                st.caption("Click **Classify** to detect document type.")

        # ── Extraction ────────────────────────────────────────────────────────
        with col_ext:
            section_header("Step 2 · Structured Data Extraction")
            ext_key = f"ext_{filename}"
            if st.button(f"🔎 Extract Data", key=f"btn_ext_{filename}"):
                with st.spinner("LLM extracting structured fields…"):
                    extracted = extract_data(text)
                    st.session_state[ext_key] = extracted
            if ext_key in st.session_state:
                extracted = st.session_state[ext_key]
                st.markdown('<div class="json-box">', unsafe_allow_html=True)
                st.json(extracted)
                st.markdown("</div>", unsafe_allow_html=True)
            else:
                st.caption("Click **Extract Data** to pull structured fields.")

        st.markdown("</div>", unsafe_allow_html=True)
        st.markdown("<br>", unsafe_allow_html=True)

def page_validation() -> None:
    st.markdown("## ✅ Claim Validation")
    st.markdown("Run policy rule checks against extracted claim data.")

    ext_keys = [k for k in st.session_state if k.startswith("ext_")]
    if not ext_keys:
        st.warning(
            "No extracted data found. Complete **Processing & Extraction** first."
        )
        return

    for ext_key in ext_keys:
        filename = ext_key.replace("ext_", "")
        extracted: Dict = st.session_state[ext_key]
        meta: Dict      = st.session_state.get(f"meta_{filename}", {})

        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.markdown(f"### 📄 {filename}  —  `{meta.get('claim_ref', '')}`")

        val_key = f"val_{filename}"
        run_btn = st.button("▶ Run Validation Rules", key=f"btn_val_{filename}")
        if run_btn:
            results = validate_claim(extracted)
            st.session_state[val_key] = results

        if val_key in st.session_state:
            results = st.session_state[val_key]

            # Summary counts
            passes   = sum(1 for r in results if r["status"] == "Pass")
            fails    = sum(1 for r in results if r["status"] == "Fail")
            warnings = sum(1 for r in results if r["status"] == "Warning")

            mc1, mc2, mc3 = st.columns(3)
            with mc1:
                st.markdown(
                    metric_card("Passed", str(passes), "✔", True),
                    unsafe_allow_html=True,
                )
            with mc2:
                st.markdown(
                    metric_card("Failed", str(fails), "✖", False),
                    unsafe_allow_html=True,
                )
            with mc3:
                st.markdown(
                    metric_card("Warnings", str(warnings), "⚠", False),
                    unsafe_allow_html=True,
                )

            st.markdown("<br>", unsafe_allow_html=True)
            section_header("Rule-by-Rule Results")

            for r in results:
                badge  = badge_html(r["status"])
                icon   = "✅" if r["status"] == "Pass" else ("❌" if r["status"] == "Fail" else "⚠️")
                st.markdown(
                    f"{icon} &nbsp; **{r['rule']}** &nbsp; {badge}  \n"
                    f"<small style='color:var(--text-secondary);'>{r['message']}</small>",
                    unsafe_allow_html=True,
                )
                st.divider()

            # Overall recommendation
            if fails == 0 and warnings == 0:
                st.success("🎉 All validation rules passed. Claim is eligible for processing.")
            elif fails > 0:
                st.error(f"🚫 {fails} rule(s) failed. Claim requires manual review before approval.")
            else:
                st.warning(f"⚠️ {warnings} warning(s) found. Secondary verification recommended.")

        st.markdown("</div>", unsafe_allow_html=True)
        st.markdown("<br>", unsafe_allow_html=True)

def page_fraud_scoring() -> None:
    st.markdown("## 🕵️ AI Fraud Detection & Scoring")
    st.markdown(
        "The local LLM analyses claim text for anomalous patterns, "
        "inconsistencies, and fraud indicators, returning a risk score and flags."
    )

    ocr_keys = [k for k in st.session_state if k.startswith("ocr_")]
    if not ocr_keys:
        st.warning("No documents ingested. Go to **Claim Ingestion** first.")
        return

    for ocr_key in ocr_keys:
        filename = ocr_key.replace("ocr_", "")
        text     = st.session_state[ocr_key]
        meta     = st.session_state.get(f"meta_{filename}", {})

        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.markdown(f"### 📄 {filename}  —  `{meta.get('claim_ref', '')}`")

        fraud_key = f"fraud_{filename}"
        if st.button("🔍 Run Fraud Analysis", key=f"btn_fraud_{filename}"):
            with st.spinner("LLM analysing for fraud signals…"):
                result = score_fraud(text)
                st.session_state[fraud_key] = result

        if fraud_key in st.session_state:
            result = st.session_state[fraud_key]

            if "raw_response" in result:
                st.code(result["raw_response"], language="json")
            else:
                score      = result.get("fraud_score", 0)
                risk_level = result.get("risk_level", "Unknown")
                flags      = result.get("flags", [])
                summary    = result.get("summary", "")

                # Score gauge
                fc1, fc2 = st.columns([1, 2])
                with fc1:
                    section_header("Fraud Score")
                    st.markdown(
                        f'<div style="font-size:3rem;font-weight:800;color:'
                        f'{"#FF4757" if score >= 60 else "#FFB830" if score >= 30 else "#00C9A7"};">'
                        f'{score}</div>',
                        unsafe_allow_html=True,
                    )
                    st.markdown(fraud_bar_html(score), unsafe_allow_html=True)
                    st.markdown(
                        f"**Risk Level:** {badge_html(risk_level)}",
                        unsafe_allow_html=True,
                    )

                with fc2:
                    section_header("Fraud Flags Detected")
                    if flags:
                        for flag in flags:
                            st.markdown(f"🚩 {flag}")
                    else:
                        st.markdown("✅ No specific flags raised.")

                    if summary:
                        st.markdown("---")
                        st.markdown(f"**Assessment:** _{summary}_")

                # Recommendation
                st.markdown("<br>", unsafe_allow_html=True)
                if score < 30:
                    st.success("✅ Low fraud risk. Proceed with standard processing.")
                elif score < 60:
                    st.warning("⚠️ Medium fraud risk. Additional verification recommended.")
                else:
                    st.error("🚨 High / Critical fraud risk. Escalate to Special Investigations Unit (SIU).")

        else:
            st.caption("Click **Run Fraud Analysis** to score this document.")

        st.markdown("</div>", unsafe_allow_html=True)
        st.markdown("<br>", unsafe_allow_html=True)

def render_sidebar() -> str:
    with st.sidebar:
        # Logo / Brand
        st.markdown("""
        <div style="padding:1.2rem 0 1rem;">
            <div style="font-size:1.5rem;font-weight:800;letter-spacing:-0.02em;">
                🛡️ MarvelAI
            </div>
            <div style="font-size:0.72rem;opacity:0.65;letter-spacing:0.12em;
                        text-transform:uppercase;margin-top:0.2rem;">
                Travel PA Claims Portal
            </div>
            <hr style="border-color:rgba(255,255,255,0.15);margin:0.9rem 0 0.5rem;">
        </div>
        """, unsafe_allow_html=True)

        # LLM status indicator
        try:
            r = requests.get("http://localhost:11434", timeout=2)
            llm_ok = r.status_code == 200
        except Exception:
            llm_ok = False

        if llm_ok:
            st.markdown(
                '🟢 <span style="font-size:0.78rem;">Ollama LLM Online</span>',
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                '🔴 <span style="font-size:0.78rem;">Ollama Offline — AI features limited</span>',
                unsafe_allow_html=True,
            )

        st.markdown("<br>", unsafe_allow_html=True)

        # Navigation
        pages = {
            "📊  Dashboard (Analytics)"       : "dashboard",
            "📥  Claim Ingestion"             : "ingestion",
            "⚙️  Processing & Extraction"     : "processing",
            "✅  Validation"                  : "validation",
            "🕵️  AI Fraud Scoring"            : "fraud",
        }

        selected_label = st.radio(
            "Navigation",
            list(pages.keys()),
            label_visibility="collapsed",
        )

        st.markdown("<br><hr style='border-color:rgba(255,255,255,0.12);'>", unsafe_allow_html=True)

        # Session info
        doc_count = len([k for k in st.session_state if k.startswith("ocr_")])
        st.markdown(
            f'<div style="font-size:0.75rem;opacity:0.6;">'
            f'📂 {doc_count} document(s) in session</div>',
            unsafe_allow_html=True,
        )

        if st.button("🗑 Clear Session", use_container_width=True):
            for k in list(st.session_state.keys()):
                del st.session_state[k]
            st.rerun()

        # Version footer
        st.markdown(
            '<div style="font-size:0.68rem;opacity:0.4;margin-top:2rem;text-align:center;">'
            'MarvelAI Claims Portal v1.0<br>Powered by llama3.2 (Ollama)</div>',
            unsafe_allow_html=True,
        )

        return pages[selected_label]

def main() -> None:
    inject_css()

    # Generate (or retrieve cached) mock claims data
    if "mock_claims_df" not in st.session_state:
        st.session_state["mock_claims_df"] = generate_mock_claims(120)

    # Render sidebar and get active page
    active_page = render_sidebar()

    # Route to the selected page
    if active_page == "dashboard":
        page_dashboard(st.session_state["mock_claims_df"])
    elif active_page == "ingestion":
        page_ingestion()
    elif active_page == "processing":
        page_processing()
    elif active_page == "validation":
        page_validation()
    elif active_page == "fraud":
        page_fraud_scoring()


if __name__ == "__main__":
    main()