import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
import json

st.set_page_config(
    page_title="Marvel.AI - Travel PA Automation Suite",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
    <style>
    .main {background-color: #0f1116; color: #e2e8f0;}
    .stTabs [data-baseweb="tab-list"] {gap: 24px;}
    .stTabs [data-baseweb="tab"] {
        font-weight: 600; color: #94a3b8; background-color: transparent; 
        border-bottom: 2px solid transparent; padding: 10px 4px;
    }
    .stTabs [data-baseweb="tab"]:hover {color: #38bdf8;}
    .stTabs [data-baseweb="tab"][aria-selected="true"] {color: #38bdf8; border-bottom: 2px solid #38bdf8;}
    div[data-testid="stMetricValue"] {font-size: 2rem; font-weight: 700; color: #f8fafc;}
    div[data-testid="stMetricLabel"] {color: #94a3b8; font-weight: 500;}
    .status-badge {padding: 6px 12px; border-radius: 6px; font-weight: 600; font-size: 0.85rem;}
    .status-approved {background-color: #065f46; color: #34d399;}
    .status-escalated {background-color: #7c2d12; color: #fb923c;}
    .status-rejected {background-color: #7f1d1d; color: #f87171;}
    </style>
""", unsafe_allow_html=True)

if "policy_registry" not in st.session_state:
    st.session_state.policy_registry = {
        "POL-1001": {"insured": "Alice Smith", "nominee": "Bob Smith", "start": "2026-06-01", "end": "2026-06-15", "coverages": ["Medical Expenses (Accident-related)", "Accidental Death Benefit", "Permanent Total Disability (PTD)", "Permanent Partial Disability (PPD)"]},
        "POL-2002": {"insured": "Charlie Brown", "nominee": "Sally Brown", "start": "2026-07-01", "end": "2026-07-10", "coverages": ["Medical Expenses (Accident-related)"]},
        "POL-3003": {"insured": "Diana Prince", "nominee": "Steve Trevor", "start": "2026-08-20", "end": "2026-09-05", "coverages": ["Accidental Death Benefit", "Permanent Total Disability (PTD)"]}
    }

if "historical_claims" not in st.session_state:
    st.session_state.historical_claims = [
        {"policy_number": "POL-1001", "accident_date": "2026-06-05", "type": "Hospital Bill", "costs": 1450.00},
        {"policy_number": "POL-2002", "accident_date": "2026-07-04", "type": "Accident Report", "costs": 0.00}
    ]

if "processed_claims_ledger" not in st.session_state:
    st.session_state.processed_claims_ledger = [
        {"claim_id": "CLM-9901", "policy_number": "POL-1001", "insured": "Alice Smith", "type": "Hospital Bill", "geography": "London, UK", "date": "2026-06-03", "costs": 1200.00, "outcome": "Auto-Approved for Instant Settlement Routing", "risk_score": 12},
        {"claim_id": "CLM-9902", "policy_number": "POL-2002", "insured": "Charlie Brown", "type": "Hospital Bill", "geography": "Tokyo, Japan", "date": "2026-07-04", "costs": 450.00, "outcome": "Auto-Approved for Instant Settlement Routing", "risk_score": 5},
        {"claim_id": "CLM-9903", "policy_number": "POL-3003", "insured": "Diana Prince", "type": "Death Certificate", "geography": "New York, USA", "date": "2026-08-25", "costs": 0.00, "outcome": "Escalated to Adjuster Panel: High Risk Fraud Suspicion", "risk_score": 75}
    ]

def pipeline_classify(text):
    content = text.lower()
    if "hospital bill" in content or "treatment invoice" in content: return "Hospital Bill"
    elif "death certificate" in content: return "Death Certificate"
    elif "disability evaluation" in content or "disability percentage" in content: return "Disability Report"
    elif "accident incident" in content or "police report" in content: return "Accident Report"
    return "Unknown Document Type"

def pipeline_extract(text, doc_type):
    policy = "POL-1001" if "POL-1001" in text else ("POL-2002" if "POL-2002" in text else ("POL-3003" if "POL-3003" in text else "Unknown"))
    
    cost_search = pd.Series([text]).str.extract(r'\$(\d+[\d,.]*)')
    costs = float(cost_search[0].str.replace(',', '').iloc[0]) if not cost_search.dropna().empty else 0.0
    
    dis_search = pd.Series([text]).str.extract(r'(\d+[\d.]*)%')
    disability = float(dis_search[0].iloc[0]) if not dis_search.dropna().empty else 0.0

    date_search = pd.Series([text]).str.extract(r'(\d{4}-\d{2}-\d{2})')
    acc_date = date_search[0].iloc[0] if not date_search.dropna().empty else datetime.today().strftime('%Y-%m-%d')

    geo = "Paris, France" if "Paris" in text else ("Berlin, Germany" if "Berlin" in text else "Rome, Italy")

    return {
        "policy_number": policy, "accident_date": acc_date, "location": geo,
        "treatment_costs": costs, "disability_percentage": disability
    }

def pipeline_validate(data, doc_type):
    policy_id = data["policy_number"]
    if policy_id not in st.session_state.policy_registry:
        return False, "Validation Failed: Invalid target policy reference ID."
        
    policy = st.session_state.policy_registry[policy_id]
    acc_dt = datetime.strptime(data["accident_date"], "%Y-%m-%d")
    start_dt = datetime.strptime(policy["start"], "%Y-%m-%d")
    end_dt = datetime.strptime(policy["end"], "%Y-%m-%d")
    
    if not (start_dt <= acc_dt <= end_dt):
        return False, f"Validation Failed: Accident date ({data['accident_date']}) maps outside travel schedule windows."
        
    coverage_mapping = {
        "Hospital Bill": "Medical Expenses (Accident-related)",
        "Death Certificate": "Accidental Death Benefit",
        "Disability Report": "Permanent Total Disability (PTD)" if data["disability_percentage"] == 100.00 else "Permanent Partial Disability (PPD)"
    }
    if coverage_mapping.get(doc_type) not in policy["coverages"]:
        return False, f"Validation Failed: Policy level parameters lack dynamic entitlement tier: '{coverage_mapping.get(doc_type)}'."
        
    for past in st.session_state.historical_claims:
        if past["policy_number"] == policy_id and past["accident_date"] == data["accident_date"] and past["type"] == doc_type:
            return False, "Validation Failed: Anti-Replay boundary intercept! Duplicate entry detected."
            
    return True, "Passed Validation Checks"

def pipeline_ai_risk(data, text):
    risk_score = 10
    if "minor" in text.lower() and data["treatment_costs"] > 10000:
        risk_score += 75
    if data["policy_number"] == "Unknown":
        risk_score += 40
    return min(risk_score, 100)

st.title("🛡️ Marvel.AI Claims Core Command Center")
st.markdown("Automated Travel Personal Accident (PA) Risk Analytics & Straight-Through Ledger Ingestion Pipeline")

tabs = st.tabs(["📊 Executive Insights & Analytics", "📝 Client Claims Entry Portal", "🗄️ System Registrar Ledger"])

with tabs[0]:
    df = pd.DataFrame(st.session_state.processed_claims_ledger)
    
    total_claims = len(df)
    approved_count = len(df[df['outcome'].str.contains("Auto-Approved")])
    escalated_count = len(df[df['outcome'].str.contains("Escalated")])
    rejected_count = len(df[df['outcome'].str.contains("Rejected")])
    total_payout = df[df['outcome'].str.contains("Auto-Approved")]['costs'].sum()

    m1, m2, m3, m4, m5 = st.columns(5)
    m1.metric("Total Ingested Claims", total_claims)
    m2.metric("Auto-Approved Settlements", approved_count)
    m3.metric("STP Approval Rate", f"{(approved_count/total_claims)*100:.1f}%" if total_claims > 0 else "0%")
    m4.metric("Escalated Adjuster Cases", escalated_count)
    m5.metric("Total Disbursed Volume", f"${total_payout:,.2f}")
    
    st.markdown("---")
    
    g1, g2 = st.columns(2)
    with g1:
        st.subheader("Claim Categories Distribution Profile")
        fig1 = px.pie(df, names='type', values='costs', hole=0.4, template="plotly_dark", color_discrete_sequence=px.colors.sequential.Cyan_r)
        st.plotly_chart(fig1, use_container_width=True)
    with g2:
        st.subheader("Regional Risk Liability Allocation")
        fig2 = px.bar(df, x='geography', y='costs', color='outcome', template="plotly_dark", barmode="stack")
        st.plotly_chart(fig2, use_container_width=True)

with tabs[1]:
    st.subheader("Electronic Claims Submission Gateway")
    st.markdown("Upload raw text payloads or select pre-configured scenario packages to view the Marvel.AI response pipeline in real time.")
    
    # Quick Injection Templates for Demo Execution
    st.markdown("**⚡ Quick-Inject Demo Simulation Matrices:**")
    scen_col1, scen_col2, scen_col3, scen_col4 = st.columns(4)
    
    scen_1_text = "Submission for Policy: POL-1001. Patient Alice Smith experienced a severe motor vehicle accident incident on 2026-06-08 in Berlin, Germany. Hospital Bill statement and treatment invoice total expenses calculated to $4,500.00."
    scen_2_text = "Claim Request Form: POL-2002. Insured: Charlie Brown. Hospital Bill treatment invoice generated for a sprained finger following a minor fall on 2026-07-04. Total claimed medical costs: $12,500.00."
    scen_3_text = "Resubmitting documentation file trace. Policy Trace Reference: POL-1001. Insured Name: Alice Smith. Hospital Bill duplicate copy showing emergency procedures executed on 2026-06-05. Statement total costs: $1450.00."
    scen_4_text = "Urgent Request: POL-2002. Claimant: Charlie Brown. Formal Disability Evaluation report issued on 2026-07-05 indicating permanent partial disability impairment percentage tracking at 15.00%."

    raw_input_text = ""
    if scen_col1.button("🟢 Inject: Happy Path (POL-1001)"): raw_input_text = scen_1_text
    if scen_col2.button("🟡 Inject: Fraud Price Spike (POL-2002)"): raw_input_text = scen_2_text
    if scen_col3.button("🔴 Inject: Anti-Replay Duplicate"): raw_input_text = scen_3_text
    if scen_col4.button("❌ Inject: Coverage Mismatch"): raw_input_text = scen_4_text

    with st.form("ingestion_form", clear_on_submit=False):
        channel = st.selectbox("Source Transmission Interface Channel", ["Customer Web Portal", "API Cloud Ingestion Endpoint", "Inbound Claims Email Listener"])
        claim_document_payload = st.text_area("Paste Raw Unstructured Document Content / OCR Stream", value=raw_input_text, height=180, placeholder="Provide document structural raw contents here...")
        submit_btn = st.form_submit_button("Initiate Pipeline Evaluation Run", type="primary")

    if submit_btn and claim_document_payload:
        st.markdown("### Real-Time Pipeline Processing Traces")
        
        doc_type = pipeline_classify(claim_document_payload)
        st.info(f"**Step 1: Document Classifier Layer Output** ➜ Inferred Type: `{doc_type}`")
        
        data_fields = pipeline_extract(claim_document_payload, doc_type)
        st.json(data_fields)
        
        valid, rule_msg = pipeline_validate(data_fields, doc_type)
        
        if not valid:
            st.error(f"**Step 3: Core Validation Rejection** ➜ Code Exception: {rule_msg}")
            final_outcome = f"Rejected: {rule_msg}"
            risk_score = 0
        else:
            st.success(f"**Step 3: Core Validation Metrics Approved** ➜ Verification Message: {rule_msg}")
            
            risk_score = pipeline_ai_risk(data_fields, claim_document_payload)
            if risk_score > 50:
                st.warning(f"**Step 4: AI Advanced Fraud Protection Safeguard Triggered** ➜ Risk Assessment Metrics Spike: `{risk_score}/100`")
                final_outcome = "Escalated to Adjuster Panel: High Risk Fraud Suspicion"
            else:
                st.success(f"**Step 4: AI Anomaly Analysis Confirmed Low Risk** ➜ Assessment Index: `{risk_score}/100`")
                final_outcome = "Auto-Approved for Instant Settlement Routing"
        
        new_id = f"CLM-{len(st.session_state.processed_claims_ledger) + 9901}"
        target_policy = data_fields["policy_number"]
        insured_name = st.session_state.policy_registry.get(target_policy, {}).get("insured", "Unknown Claimant")
        
        new_record = {
            "claim_id": new_id, "policy_number": target_policy, "insured": insured_name,
            "type": doc_type, "geography": data_fields["location"], "date": data_fields["accident_date"],
            "costs": data_fields["treatment_costs"], "outcome": final_outcome, "risk_score": risk_score
        }
        
        st.session_state.processed_claims_ledger.append(new_record)
        st.balloons()
        st.markdown(f"**Final Platform Routing Status Determination:** `{final_outcome}`")

with tabs[2]:
    st.subheader("Underlying Global System Registrars")
    
    st.markdown("#### 1. Underwriting Policy Permissions Master Registry")
    st.write(pd.DataFrame.from_dict(st.session_state.policy_registry, orient='index'))
    
    st.markdown("#### 2. Runtime Dynamic Processed Claims Master Ledger Database")
    
    ledger_df = pd.DataFrame(st.session_state.processed_claims_ledger)
    
    def render_custom_table(dataframe):
        html = "<table style='width:100%; border-collapse: collapse;'><thead><tr style='background-color:#1e293b; color:#cbd5e1; text-align:left;'><th style='padding:12px;'>Claim ID</th><th style='padding:12px;'>Policy</th><th style='padding:12px;'>Insured</th><th style='padding:12px;'>Coverage Type</th><th style='padding:12px;'>Cost</th><th style='padding:12px;'>Risk Index</th><th style='padding:12px;'>Status Resolution Route</th></tr></thead><tbody>"
        for _, row in dataframe.iterrows():
            badge_class = "status-approved" if "Auto-Approved" in row['outcome'] else ("status-escalated" if "Escalated" in row['outcome'] else "status-rejected")
            html += f"<tr style='border-bottom: 1px solid #334155; color:#f1f5f9;'>"
            html += f"<td style='padding:12px; font-weight:bold;'>{row['claim_id']}</td>"
            html += f"<td style='padding:12px;'>{row['policy_number']}</td>"
            html += f"<td style='padding:12px;'>{row['insured']}</td>"
            html += f"<td style='padding:12px;'>{row['type']}</td>"
            html += f"<td style='padding:12px;'>${row['costs']:,.2f}</td>"
            html += f"<td style='padding:12px; font-weight:bold; color:{'#ef4444' if row['risk_score']>50 else '#34d399'};'>{row['risk_score']}/100</td>"
            html += f"<td style='padding:12px;'><span class='status-badge {badge_class}'>{row['outcome']}</span></td>"
            html += "</tr>"
        html += "</tbody></table>"
        return html

    st.markdown(render_custom_table(ledger_df), unsafe_allow_html=True)