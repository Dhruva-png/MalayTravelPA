import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
import re

# ==========================================
# PAGE CONFIGURATION & METADATA
# ==========================================
st.set_page_config(
    page_title="Marvel.AI - Travel PA Automation Suite",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom High-End Theme Configuration (Dark Slate Executive Theme)
st.markdown("""
    <style>
    /* Global Background and Typography Customization */
    .main { background-color: #0b0f17; color: #f1f5f9; }
    header, .stSidebar { background-color: #0f172a !important; }
    
    /* Elegant Tab Adjustments */
    .stTabs [data-baseweb="tab-list"] { gap: 28px; background-color: #0f172a; padding: 12px 24px; border-radius: 12px; border: 1px solid #1e293b; }
    .stTabs [data-baseweb="tab"] { font-weight: 700; color: #94a3b8; padding: 10px 16px; border-bottom: 2px solid transparent; }
    .stTabs [data-baseweb="tab"]:hover { color: #38bdf8; }
    .stTabs [data-baseweb="tab"][aria-selected="true"] { color: #38bdf8; border-bottom: 2px solid #38bdf8 !important; }
    
    /* Metrics Layout Polish */
    div[data-testid="stMetricValue"] { font-size: 2.2rem; font-weight: 800; color: #ffffff; letter-spacing: -0.025em; }
    div[data-testid="stMetricLabel"] { color: #94a3b8; font-weight: 600; font-size: 0.85rem; text-transform: uppercase; letter-spacing: 0.05em; }
    div[data-testid="stMetric"] { background-color: #0f172a; border: 1px solid #1e293b; padding: 20px; border-radius: 16px; }
    
    /* Execution Logging Simulation Display Container */
    .log-box { background-color: #020617; border: 1px solid #1e293b; border-radius: 12px; padding: 16px; font-family: 'Courier New', Courier, monospace; font-size: 0.85rem; color: #38bdf8; line-height: 1.6; }
    .log-info { color: #94a3b8; }
    .log-success { color: #34d399; font-weight: bold; }
    .log-warn { color: #fb923c; font-weight: bold; }
    .log-error { color: #f87171; font-weight: bold; }
    
    /* Status Badge Matrix styling layouts */
    .badge { padding: 4px 10px; border-radius: 6px; font-weight: 700; font-size: 0.75rem; uppercase; tracking: 0.05em; }
    .bg-approved { background-color: rgba(16, 185, 129, 0.15); color: #10b981; border: 1px solid rgba(16, 185, 129, 0.3); }
    .bg-escalated { background-color: rgba(245, 158, 11, 0.15); color: #f59e0b; border: 1px solid rgba(245, 158, 11, 0.3); }
    .bg-rejected { background-color: rgba(239, 68, 68, 0.15); color: #ef4444; border: 1px solid rgba(239, 68, 68, 0.3); }
    </style>
""", unsafe_allow_html=True)

# ==========================================
# SYSTEM STATE / REGISTRAR STORAGE DATASTRUCTURES
# ==========================================
# Pre-filling underwriting policies master cache matrix mapping core travel validation structures
if "underwriting_policy_registry" not in st.session_state:
    st.session_state.underwriting_policy_registry = {
        "POL-8801": {"insured": "Alexander Wright", "nominee": "Eleanor Wright", "start_date": "2026-06-01", "end_date": "2026-06-20", "coverages": ["Medical Expenses (Accident-related)", "Accidental Death Benefit", "Permanent Total Disability (PTD)", "Permanent Partial Disability (PPD)"]},
        "POL-4402": {"insured": "Marcus Vance", "nominee": "Sophia Vance", "start_date": "2026-07-10", "end_date": "2026-07-25", "coverages": ["Medical Expenses (Accident-related)", "Permanent Partial Disability (PPD)"]},
        "POL-1103": {"insured": "Clara Jenkins", "nominee": "Thomas Jenkins", "start_date": "2026-08-05", "end_date": "2026-08-15", "coverages": ["Accidental Death Benefit", "Permanent Total Disability (PTD)"]}
    }

# Initializing historical claim items array to track logic constraints like anti-replay rules
if "historical_claims_db" not in st.session_state:
    st.session_state.historical_claims_db = [
        {"policy_number": "POL-8801", "accident_date": "2026-06-05", "doc_type": "Hospital Bill", "costs": 2450.00},
        {"policy_number": "POL-4402", "accident_date": "2026-07-12", "doc_type": "Accident Report", "costs": 0.00}
    ]

# The running processed ledger which dynamically hydrates the centralized executive insights charts
if "claims_ledger" not in st.session_state:
    st.session_state.claims_ledger = [
        {"trace_id": "TRC-901", "policy_number": "POL-8801", "insured": "Alexander Wright", "doc_type": "Hospital Bill", "geography": "London, UK", "date": "2026-06-05", "costs": 2450.00, "disability_pct": 0.0, "risk_score": 15, "outcome": "Auto-Approved", "travel_period": "2026-06-01 to 2026-06-20"},
        {"trace_id": "TRC-902", "policy_number": "POL-4402", "insured": "Marcus Vance", "doc_type": "Hospital Bill", "geography": "Tokyo, Japan", "date": "2026-07-15", "costs": 14200.00, "disability_pct": 0.0, "risk_score": 78, "outcome": "Escalated to Adjuster Panel", "travel_period": "2026-07-10 to 2026-07-25"},
        {"trace_id": "TRC-903", "policy_number": "POL-1103", "insured": "Clara Jenkins", "doc_type": "Death Certificate", "geography": "Paris, France", "date": "2026-08-10", "costs": 0.00, "disability_pct": 0.0, "risk_score": 8, "outcome": "Auto-Approved", "travel_period": "2026-08-05 to 2026-08-15"}
    ]

# ==========================================
# MARVEL.AI BACKEND COGNITIVE ENGINE PIPELINE
# ==========================================
def run_stage1_classification(text_content):
    """Classifies document by specific target schemas."""
    content = text_content.lower()
    if "death certificate" in content or "deceased" in content: return "Death Certificate"
    elif "hospital bill" in content or "treatment invoice" in content or "medical bill" in content: return "Hospital Bill"
    elif "disability evaluation" in content or "disability report" in content: return "Disability Report"
    elif "accident report" in content or "police report" in content or "incident report" in content: return "Accident Report"
    return "Unknown Document Type"

def run_stage2_intelligent_extraction(text_content, doc_type):
    """Extracts structured data elements from raw document stream inputs."""
    # Isolate targets using standard structured regular expressions
    policy_match = re.search(r'POL-\d{4}', text_content)
    policy_num = policy_match.group(0) if policy_match else "Unknown"
    
    date_match = re.search(r'(\d{4}-\d{2}-\d{2})', text_content)
    accident_date = date_match.group(0) if date_match else datetime.today().strftime('%Y-%m-%d')
    
    cost_match = re.search(r'\$(\d+[\d,.]*)', text_content)
    treatment_costs = float(cost_match.group(1).replace(',', '')) if cost_match else 0.0
    
    disability_match = re.search(r'(\d+[\d.]*)\s*%', text_content)
    disability_pct = float(disability_match.group(1)) if disability_match else 0.0
    
    # Text lookup matching fields
    geography = "Berlin, Germany" if "Berlin" in text_content else ("Rome, Italy" if "Rome" in text_content else "London, UK")
    injury_nature = "Multiple fractures" if "fracture" in text_content.lower() else "Minor soft tissue lacerations"
    diag_code = "ICD-10-S82" if "fracture" in text_content.lower() else "ICD-10-T14"
    hosp_dates = "2026-06-05 to 2026-06-12" if "hospital" in text_content.lower() else "N/A"
    
    # Financial payload mapping
    bank_match = re.search(r'Bank Account:\s*([A-Z0-9\s\-]+)', text_content, re.IGNORECASE)
    bank_details = bank_match.group(1).strip() if bank_match else "Standard Disbursal Routing Wire"

    policy_meta = st.session_state.underwriting_policy_registry.get(policy_num, {})
    
    return {
        "policy_number": policy_num,
        "insured_name": policy_meta.get("insured", "Unverified Claimant"),
        "nominee_details": policy_meta.get("nominee", "None Registered"),
        "accident_date": accident_date,
        "location": geography,
        "nature_of_injury": injury_nature,
        "diagnosis_code": diag_code,
        "hospitalization_dates": hosp_dates,
        "treatment_costs": treatment_costs,
        "disability_percentage": disability_pct,
        "bank_account_details": bank_details
    }

def run_stage3_policy_validation(extracted_data, doc_type):
    """Applies rigorous validation constraints checks against master policy records."""
    policy_id = extracted_data["policy_number"]
    
    # Rule Check A: Validating policy identification reference status
    if policy_id not in st.session_state.underwriting_policy_registry:
        return False, "Validation Failed: Invalid target policy reference ID."
        
    policy = st.session_state.underwriting_policy_registry[policy_id]
    
    # Rule Check B: Coverage period timeline boundary synchronization validation
    acc_dt = datetime.strptime(extracted_data["accident_date"], "%Y-%m-%d")
    start_dt = datetime.strptime(policy["start_date"], "%Y-%m-%d")
    end_dt = datetime.strptime(policy["end_date"], "%Y-%m-%d")
    if not (start_dt <= acc_dt <= end_dt):
        return False, f"Validation Failed: Accident date ({extracted_data['accident_date']}) maps outside policy travel windows."
        
    # Rule Check C: Coverage entitlement validation matching structural classes
    coverage_mapping = {
        "Hospital Bill": "Medical Expenses (Accident-related)",
        "Death Certificate": "Accidental Death Benefit",
        "Disability Report": "Permanent Total Disability (PTD)" if extracted_data["disability_percentage"] == 100.0 else "Permanent Partial Disability (PPD)",
        "Accident Report": "Medical Expenses (Accident-related)"
    }
    required_coverage = coverage_mapping.get(doc_type)
    if required_coverage not in policy["coverages"]:
        return False, f"Validation Failed: Active target benefits exclude variant tier constraint: '{required_coverage}'."
        
    # Rule Check D: Anti-Replay duplicate trace interdiction intercept block
    for history_item in st.session_state.historical_claims_db:
        if (history_item["policy_number"] == policy_id and 
            history_item["accident_date"] == extracted_data["accident_date"] and 
            history_item["doc_type"] == doc_type):
            return False, "Validation Failed: Anti-Replay intercept! Identical historical claim metadata pattern discovered."
            
    return True, "Passed All Core Business Logic Constraint Parameters Check"

def run_stage4_ai_fraud_scoring(extracted_data, raw_text):
    """Generates complex real-time threat-detection analysis metrics."""
    risk_score = 12 # Baseline processing index score
    
    # Scenario Anomaly checking check: Flagging outsized balances matched with minor claims keywords
    if "minor" in raw_text.lower() and extracted_data["treatment_costs"] > 5000:
        risk_score += 65
    
    # Scenario Anomaly checking check: Identity duplicate or missing policy properties flags
    if extracted_data["policy_number"] == "Unknown":
        risk_score += 45
        
    return min(risk_score, 100)

# ==========================================
# ENTERPRISE INTERFACE PRESENTATION LAYOUT
# ==========================================
st.title("🛡️ Marvel.AI Claims Core Command Center")
st.markdown("Automated Travel Personal Accident (PA) Risk Analytics & Straight-Through Ledger Ingestion Pipeline")

# Organizing layout tabs matching corporate structural division requirements
tabs = st.tabs(["📊 Executive Analytics Insight", "📝 Client Document Ingestion Gate", "🗄️ Master System Registrars"])

# ------------------------------------------
# TAB 1: EXECUTIVE ANALYTICS INSIGHT
# ------------------------------------------
with tabs[0]:
    st.subheader("Platform Operational Yield Metrics")
    
    if st.session_state.claims_ledger:
        df_ledger = pd.DataFrame(st.session_state.claims_ledger)
        
        # Calculate dynamic KPIs based on current state memory
        total_ingested = len(df_ledger)
        approved_claims = df_ledger[df_ledger['outcome'] == "Auto-Approved"]
        stp_count = len(approved_claims)
        escalated_count = len(df_ledger[df_ledger['outcome'].str.contains("Escalated")])
        rejected_count = len(df_ledger[df_ledger['outcome'].str.contains("Rejected")])
        
        stp_rate = (stp_count / total_ingested) * 100 if total_ingested > 0 else 0
        total_payout_volume = approved_claims['costs'].sum()
        
        # Layout metrics row blocks
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Total Ingested Claims", f"{total_ingested} Cases")
        m2.metric("STP Auto-Approved", f"{stp_count} Settled")
        m3.metric("Straight-Through Rate (STP)", f"{stp_rate:.1f}%")
        m4.metric("Disbursed Capital Volume", f"${total_payout_volume:,.2f}")
        
        st.markdown("---")
        
        # High-impact analytical graph layout matrix blocks
        g1, g2 = st.columns(2)
        
        with g1:
            st.markdown("### Financial Volume Sliced by Document Classification Type")
            fig_pie = px.pie(
                df_ledger, 
                names='doc_type', 
                values='costs', 
                hole=0.45,
                template="plotly_dark",
                color_discrete_sequence=px.colors.sequential.Tealgrn_r
            )
            fig_pie.update_layout(margin=dict(t=20, b=20, l=20, r=20), height=320)
            st.plotly_chart(fig_pie, use_container_width=True)
            
        with g2:
            st.markdown("### Regional Exposure & Outcome Risk Analytics")
            fig_bar = px.bar(
                df_ledger, 
                x='geography', 
                y='costs', 
                color='outcome',
                template="plotly_dark",
                barmode="stack",
                color_discrete_map={"Auto-Approved": "#10b981", "Escalated to Adjuster Panel": "#f59e0b", "Rejected: Core Exception Flag": "#ef4444"}
            )
            fig_bar.update_layout(margin=dict(t=20, b=20, l=20, r=20), height=320)
            st.plotly_chart(fig_bar, use_container_width=True)
            
        st.markdown("### System Claim Predictions Matrix Window (Current Travel Window Sequences)")
        fig_line = px.line(
            df_ledger,
            x='travel_period',
            y='risk_score',
            markers=True,
            template="plotly_dark",
            title="Real-time Operational Timeline Volatility Matrix Plot",
            line_shape="spline"
        )
        st.plotly_chart(fig_line, use_container_width=True)
    else:
        st.warning("No operational data present in runtime system state storage containers.")

# ------------------------------------------
# TAB 2: CLIENT DOCUMENT INGESTION GATE
# ------------------------------------------
with tabs[1]:
    st.subheader("Cognitive Edge Automation Document Entry Channel")
    st.markdown("Simulate document delivery entry transmissions. The ingestion gate applies the full backend extraction framework dynamically.")
    
    # Interactive injection matrices for demo testing profiles
    st.markdown("**⚡ Instant-Inject Demo Simulation Matrices (Select a Scenario package to fill execution buffer):**")
    scen_col1, scen_col2, scen_col3, scen_col4 = st.columns(4)
    
    s1_text = "Transmission Channel Reference: Portal Upload. Policy target: POL-8801. Insured party Alexander Wright logged an emergency incident on 2026-06-08 in London, UK. Attached document stream: Hospital Bill treatment invoice total verified expenses calculate to $1,450.00. Bank Account: Chase Wire-0992-WI."
    s2_text = "Inbound API Packet Listener Trace: POL-4402. Claimant Named: Marcus Vance. Incurred injury evaluation on 2026-07-15 while in Tokyo, Japan. Uploaded Document: Hospital Bill treatment invoice totals indicate $12,500.00 for minor soft tissue repair procedures. Disbursal route: Standard Disbursal Routing Wire."
    s3_text = "System Ingestion Retry File Trace. Target Policy: POL-8801. Insured Name: Alexander Wright. Re-uploading Hospital Bill duplicate statement record showing procedures executed on 2026-06-05. Statement calculated total costs: $2450.00."
    s4_text = "Urgent Request Packet: POL-1103. Insured Client: Clara Jenkins. Submitting official Disability Evaluation report documentation tracking assessment on 2026-08-10 in Paris, France. Impairment percentage metrics confirmed at 35.00% permanent functional loss."

    raw_buffer_text = ""
    if scen_col1.button("🟢 Scenario 1: Clean STP Run"): raw_buffer_text = s1_text
    if scen_col2.button("🟡 Scenario 2: AI Fraud Alert Trigger"): raw_buffer_text = s2_text
    if scen_col3.button("🔴 Scenario 3: Anti-Replay Duplicate"): raw_buffer_text = s3_text
    if scen_col4.button("🟣 Scenario 4: Coverage Mismatch Check"): raw_buffer_text = s4_text

    # Entry Form Window
    with st.form("ingestion_gate_form", clear_on_submit=False):
        transmission_channel = st.selectbox("Ingestion Routing Pipeline Interface", ["Portal Secure Document Upload Web UI", "Inbound Claims Core Email Daemon", "API Endpoint Optical OCR Telemetry Stream"])
        claim_raw_text = st.text_area("OCR Document Text Stream / Unstructured Telemetry Payload Content", value=raw_buffer_text, height=160, placeholder="Paste raw system payload or choose a simulation matrix button above...")
        trigger_pipeline = st.form_submit_button("Initiate Straight-Through Execution Sequence", type="primary")

    if trigger_pipeline and claim_raw_text:
        st.markdown("### Real-Time Process Orchestration Monitor Logs")
        log_placeholder = st.empty()
        
        # Incremental Trace log generation lists
        log_array = ["<ul>"]
        
        # Step 1: Running structural layout pattern categorization models
        log_array.append(f"<li class='log-info'>[RUNNING] Stage 1: Evaluating Structural Classification Models...</li>")
        inferred_doc_type = run_stage1_classification(claim_raw_text)
        log_array.append(f"<li class='log-success'>[SUCCESS] Stage 1 Complete: Document classified as '{inferred_doc_type}'</li>")
        
        # Step 2: Triggering entity value extraction rules matching definitions
        log_array.append(f"<li class='log-info'>[RUNNING] Stage 2: Initializing Cognitive Parsing Layer Field Tokenizer...</li>")
        extracted_fields = run_stage2_intelligent_extraction(claim_raw_text, inferred_doc_type)
        log_array.append(f"<li class='log-success'>[SUCCESS] Stage 2 Complete: Fields Isolated successfully.</li>")
        
        # Printing intermediate metrics dictionary block directly into display window
        st.json(extracted_fields)
        
        # Step 3: Compiling strict validation criteria bounds rules arrays
        log_array.append(f"<li class='log-info'>[RUNNING] Stage 3: Running Underwriting Policy Validation Engine...</li>")
        validation_pass, validation_message = run_stage3_policy_validation(extracted_fields, inferred_doc_type)
        
        final_route_determination = "Auto-Approved"
        if not validation_pass:
            log_array.append(f"<li class='log-error'>[CRITICAL CORE FAILURE] Stage 3 Exception Flagged: {validation_message}</li>")
            final_route_determination = f"Rejected: Core Exception Flag"
            threat_risk_index = 0
        else:
            log_array.append(f"<li class='log-success'>[SUCCESS] Stage 3 Complete: All core business rules check pass parameters successfully.</li>")
            
            # Step 4: Loading contextual threat analysis scoring neural maps
            log_array.append(f"<li class='log-info'>[RUNNING] Stage 4: Fetching Real-time AI Anomaly Scoring Heuristics...</li>")
            threat_risk_index = run_stage4_ai_fraud_scoring(extracted_fields, claim_raw_text)
            
            if threat_risk_index > 50:
                log_array.append(f"<li class='log-warn'>[SECURITY ALERT] Stage 4 Flagged Anomaly: Fraud Index Spike ({threat_risk_index}/100). Flagged outsized budget metrics mismatch.</li>")
                final_route_determination = "Escalated to Adjuster Panel"
            else:
                log_array.append(f"<li class='log-success'>[SUCCESS] Stage 4 Complete: Risk Index calculated inside standard thresholds ({threat_risk_index}/100).</li>")
        
        log_array.append("</ul>")
        log_placeholder.markdown(f"<div class='log-box'>{''.join(log_array)}</div>", unsafe_allow_html=True)
        
        # Constructing new operational transaction dictionary element to append database state registries
        runtime_trace_id = f"TRC-{len(st.session_state.claims_ledger) + 901}"
        associated_policy = extracted_fields["policy_number"]
        policy_schedule_meta = st.session_state.underwriting_policy_registry.get(associated_policy, {})
        
        new_transaction_record = {
            "trace_id": runtime_trace_id,
            "policy_number": associated_policy,
            "insured": extracted_fields["insured_name"],
            "doc_type": inferred_doc_type,
            "geography": extracted_fields["location"],
            "date": extracted_fields["accident_date"],
            "costs": extracted_fields["treatment_costs"],
            "disability_pct": extracted_fields["disability_percentage"],
            "risk_score": threat_risk_index,
            "outcome": final_route_determination,
            "travel_period": f"{policy_schedule_meta.get('start_date', 'N/A')} to {policy_schedule_meta.get('end_date', 'N/A')}"
        }
        
        # Appending transaction record item inside global session database structures
        st.session_state.claims_ledger.insert(0, new_transaction_record)
        
        # Updating anti-replay history block matrix elements conditionally on clean validation states
        if validation_pass:
            st.session_state.historical_claims_db.append({
                "policy_number": associated_policy,
                "accident_date": extracted_fields["accident_date"],
                "doc_type": inferred_doc_type,
                "costs": extracted_fields["treatment_costs"]
            })
            
        st.success(f"Execution run completed. Platform Routing Determination: **{final_route_determination}**")
        if final_route_determination == "Auto-Approved":
            st.balloons()

# ------------------------------------------
# TAB 3: MASTER SYSTEM REGISTRARS
# ------------------------------------------
with tabs[2]:
    st.subheader("Global Core Operational Registrars Ledger")
    
    st.markdown("#### 1. Underwriting Policy Contract Permission Registry Base")
    st.markdown("This database controls checking parameters for validation operations, including benefit rules and schedule durations.")
    st.write(pd.DataFrame.from_dict(st.session_state.underwriting_policy_registry, orient='index'))
    
    st.markdown("---")
    
    st.markdown("#### 2. Processed Claims Transaction Database Master Ledger")
    st.markdown("The audit log captures straight-through execution track logs updated by active channel entry operations.")
    
    # Constructing standard beautiful data layout matrices using custom styling indicators
    raw_html_table = """
    <table style='width:100%; border-collapse: collapse; text-align: left; font-size: 0.85rem; color: #cbd5e1;'>
        <thead>
            <tr style='background-color: #0f172a; border-bottom: 2px solid #1e293b; color: #94a3b8;'>
                <th style='padding: 14px;'>Trace ID</th>
                <th style='padding: 14px;'>Policy</th>
                <th style='padding: 14px;'>Claimant</th>
                <th style='padding: 14px;'>Document Class</th>
                <th style='padding: 14px;'>Costs Isolated</th>
                <th style='padding: 14px;'>Threat Rating</th>
                <th style='padding: 14px;'>Settlement Resolution Path</th>
            </tr>
        </thead>
        <tbody>
    """
    
    for item in st.session_state.claims_ledger:
        badge_style = "bg-approved" if item["outcome"] == "Auto-Approved" else ("bg-escalated" if "Escalated" in item["outcome"] else "bg-rejected")
        risk_color = "#f87171" if item["risk_score"] > 50 else "#34d399"
        
        raw_html_table += f"""
            <tr style='border-bottom: 1px solid #1e293b; background-color: rgba(15, 23, 42, 0.2);'>
                <td style='padding: 14px; font-weight: bold; color: #ffffff;'>{item["trace_id"]}</td>
                <td style='padding: 14px; font-family: monospace;'>{item["policy_number"]}</td>
                <td style='padding: 14px;'>{item["insured"]}</td>
                <td style='padding: 14px;'>{item["doc_type"]}</td>
                <td style='padding: 14px; font-weight: 600;'>${item["costs"]:,.2f}</td>
                <td style='padding: 14px; font-weight: bold; color: {risk_color};'>{item["risk_score"]}/100</td>
                <td style='padding: 14px;'><span class='badge {badge_style}'>{item["outcome"]}</span></td>
            </tr>
        """
        
    raw_html_table += "</tbody></table>"
    st.markdown(raw_html_table, unsafe_allow_html=True)