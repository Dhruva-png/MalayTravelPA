import streamlit as st
import pandas as pd
import random
import time
from datetime import datetime
import plotly.express as px
from typing import List, Dict, Any

# ==========================================
# 1. CONFIGURATION & CSS INJECTION
# ==========================================
st.set_page_config(
    page_title="Marvel.AI | Travel PA Claims", 
    layout="wide", 
    page_icon="🛡️",
    initial_sidebar_state="expanded"
)

# Custom CSS for production-level polish
st.markdown("""
    <style>
        .block-container { padding-top: 2rem; padding-bottom: 2rem; }
        .stMetric { background-color: rgba(25, 30, 40, 0.5); padding: 15px; border-radius: 8px; border: 1px solid rgba(255,255,255,0.1); }
        .st-emotion-cache-1wivap2 { border-radius: 8px; }
    </style>
""", unsafe_allow_html=True)

# ==========================================
# 2. STATE INITIALIZATION (DATA LAYER)
# ==========================================
def initialize_state() -> None:
    """Initializes the database/state if it doesn't exist."""
    if 'claims' not in st.session_state:
        st.session_state.claims = pd.DataFrame([
            {"Claim ID": "CLM-1001", "Policy Number": "POL-8801", "Insured Name": "Alexander Wright", "Coverage Type": "Medical Expenses", "Location": "London, UK", "Amount": 1450.00, "Fraud Score": 12, "Status": "Approved", "Travel Period": "June 2026"},
            {"Claim ID": "CLM-1002", "Policy Number": "POL-8802", "Insured Name": "Sophia Chen", "Coverage Type": "Permanent Total Disability", "Location": "Tokyo, JP", "Amount": 85000.00, "Fraud Score": 65, "Status": "Escalated", "Travel Period": "June 2026"},
            {"Claim ID": "CLM-1003", "Policy Number": "POL-8803", "Insured Name": "Mateo Rossi", "Coverage Type": "Accidental Death", "Location": "Rome, IT", "Amount": 50000.00, "Fraud Score": 8, "Status": "Approved", "Travel Period": "May 2026"},
            {"Claim ID": "CLM-1004", "Policy Number": "POL-8804", "Insured Name": "Liam Smith", "Coverage Type": "Permanent Partial Disability", "Location": "Paris, FR", "Amount": 12500.00, "Fraud Score": 92, "Status": "Rejected", "Travel Period": "June 2026"},
        ])

    if 'policies' not in st.session_state:
        st.session_state.policies = pd.DataFrame([
            {"Policy": "POL-8801", "Name": "Alexander Wright", "Nominee": "Emma Wright", "Valid": "2026-06-01 to 2026-06-30", "Coverages": "Medical, PPD, PTD, Death"},
            {"Policy": "POL-8802", "Name": "Sophia Chen", "Nominee": "Liam Chen", "Valid": "2026-06-05 to 2026-07-10", "Coverages": "Medical, PTD"},
            {"Policy": "POL-8803", "Name": "Mateo Rossi", "Nominee": "Isabella Rossi", "Valid": "2026-05-10 to 2026-05-25", "Coverages": "Medical, Death"},
        ])

# ==========================================
# 3. UI MODULES (VIEW LAYER)
# ==========================================
def render_analytics() -> None:
    """Renders the executive analytics dashboard."""
    st.title("📊 Outcome Analytics")
    st.caption("Real-time telemetry across coverage types, geography, and travel periods.")
    
    df = st.session_state.claims
    
    # KPI Strip
    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Total Payout Exposure", f"${df['Amount'].sum():,.2f}")
    k2.metric("Total Claims Processed", len(df))
    k3.metric("STP Approved", f"{len(df[df['Status'] == 'Approved'])}")
    k4.metric("Flagged / Rejected", f"{len(df[df['Status'] == 'Rejected'])}")
    
    st.divider()

    c1, c2 = st.columns(2)
    with c1:
        st.subheader("Exposure by Coverage Type")
        fig_pie = px.pie(df, names="Coverage Type", values="Amount", hole=0.4, 
                         color_discrete_sequence=px.colors.sequential.Teal)
        fig_pie.update_layout(margin=dict(t=10, b=10, l=0, r=0), plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)")
        st.plotly_chart(fig_pie, use_container_width=True)

    with c2:
        st.subheader("Geographic Risk Heatmap")
        fig_bar = px.bar(df, x="Location", y="Amount", color="Status",
                         color_discrete_map={"Approved": "#10b981", "Escalated": "#f59e0b", "Rejected": "#ef4444"})
        fig_bar.update_layout(margin=dict(t=10, b=10, l=0, r=0), plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)")
        st.plotly_chart(fig_bar, use_container_width=True)

def render_ingestion() -> None:
    """Renders the secure client document ingestion gateway."""
    st.title("📥 Claim Ingestion Gateway")
    st.caption("Securely attach client documents (Medical Bills, Police Reports, Death Certificates) for batch AI processing.")
    
    with st.container(border=True):
        tab1, tab2 = st.tabs(["📎 Attach Documents (Client/Agent Upload)", "💻 Raw Payload (API Ingestion)"])
        
        with tab1:
            # PROFESSIONAL ADDITION: Multiple file uploading enabled
            uploaded_files = st.file_uploader(
                "Upload Supporting Documents", 
                type=["pdf", "jpg", "jpeg", "png", "docx", "xlsx"], 
                accept_multiple_files=True,
                help="You can attach multiple files at once. Marvel.AI will process them as a batch."
            )
            
            if uploaded_files:
                st.success(f"Successfully attached {len(uploaded_files)} document(s). Ready for pipeline execution.")
                with st.expander("View Attached Files"):
                    for file in uploaded_files:
                        st.text(f"📄 {file.name} ({(file.size / 1024):.1f} KB)")
        
        with tab2:
            raw_text = st.text_area("Paste OCR or JSON Payload:", height=150, placeholder="E.g., Policy POL-8805, Insured: John Doe...")

        if st.button("⚡ Execute Marvel.AI Pipeline", type="primary", use_container_width=True):
            if not uploaded_files and not raw_text:
                st.error("⚠️ Please attach at least one document or provide a text payload.")
                return
            
            # Simulate Batch Processing
            files_to_process = uploaded_files if uploaded_files else [{"name": "Raw_Payload_Extracted.txt"}]
            
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            for idx, file in enumerate(files_to_process):
                filename = file.name if hasattr(file, 'name') else file['name']
                
                with st.status(f"Processing {filename}...", expanded=True) as status:
                    st.write("🔒 **Security Check:** Scanning for malware and verifying file integrity...")
                    time.sleep(0.5)
                    
                    st.write("📄 **A. Classification:** Routing document to designated OCR model...")
                    time.sleep(0.8)
                    doc_type = random.choice(["Hospital Bill", "Death Certificate", "Disability Report", "Accident Report"])
                    
                    st.write("🧠 **B. Data Extraction:** Pulling 11 core data attributes...")
                    time.sleep(0.8)
                    
                    st.write("⚖️ **C. Validation:** Checking benefits against Master Policy ledger...")
                    time.sleep(0.5)
                    
                    status.update(label=f"Completed: {filename} (Classified as {doc_type})", state="complete", expanded=False)
                
                # Update progress bar
                progress = int(((idx + 1) / len(files_to_process)) * 100)
                progress_bar.progress(progress)
            
            st.toast("Batch Processing Complete!", icon="✅")
            
            # Display Consolidated Results
            st.divider()
            st.subheader("Marvel.AI Processing Report")
            
            # Simulate an extracted claim result for the batch
            fraud_score = random.randint(10, 90)
            decision = "Approved" if fraud_score < 40 else ("Escalated" if fraud_score < 75 else "Rejected")
            
            if decision == "Approved":
                st.success(f"**PIPELINE DECISION: STP APPROVED** (Fraud Risk: {fraud_score}/100)")
            elif decision == "Escalated":
                st.warning(f"**PIPELINE DECISION: MANUAL REVIEW REQUIRED** (Fraud Risk: {fraud_score}/100)")
            else:
                st.error(f"**PIPELINE DECISION: REJECTED** (Fraud Risk: {fraud_score}/100)")

            with st.expander("View Extracted Data Payload", expanded=True):
                c1, c2, c3 = st.columns(3)
                c1.metric("Inferred Policy", f"POL-{random.randint(8805, 8999)}")
                c1.metric("Insured Name", "Client / Claimant Name")
                c1.metric("Diagnosis Code", "ICD-10-S82")
                
                c2.metric("Accident Date", "2026-06-10")
                c2.metric("Location", "Extracted City, Country")
                c2.metric("Nature of Injury", "Extracted Description")
                
                c3.metric("Hospitalization", "2026-06-10 to 2026-06-14")
                c3.metric("Total Claimed Amount", f"${random.randint(500, 25000):,.2f}")
                c3.metric("Disability %", f"{random.randint(0, 100)}%")

def render_registrar() -> None:
    """Renders the master database of all claims."""
    st.title("🗄️ Master Registrar")
    st.caption("Immutable ledger of all ingested and processed claims.")
    
    # Professional Addition: Search and Filter capabilities
    search = st.text_input("🔍 Search Registry", placeholder="Enter Claim ID, Name, or Policy Number...")
    df = st.session_state.claims
    
    if search:
        mask = df.apply(lambda row: row.astype(str).str.contains(search, case=False).any(), axis=1)
        df = df[mask]
        
    st.dataframe(df, use_container_width=True, hide_index=True)
    
    csv = df.to_csv(index=False).encode('utf-8')
    st.download_button("⬇️ Download Ledger (CSV)", data=csv, file_name="claims_ledger.csv", mime="text/csv")

def render_policy_rules() -> None:
    """Renders the rule engine and policy schedules."""
    st.title("📋 Policy & Validation Engine")
    st.caption("Active rule sets ensuring STP compliance against policy schedules.")
    
    st.subheader("Active Policy Master")
    st.dataframe(st.session_state.policies, use_container_width=True, hide_index=True)
    
    st.divider()
    st.subheader("Marvel.AI Rule Checks")
    rules = [
        {"Rule": "Coverage Period Check", "Description": "Verifies accident date falls within policy 'Valid' dates.", "Status": "Active"},
        {"Rule": "Benefit Eligibility Check", "Description": "Matches claim reason to active 'Coverages'.", "Status": "Active"},
        {"Rule": "Duplicate Detection", "Description": "Hashes document attachments to prevent double submissions.", "Status": "Active"},
    ]
    st.table(pd.DataFrame(rules))

# ==========================================
# 4. MAIN APPLICATION ROUTER
# ==========================================
def main() -> None:
    initialize_state()
    
    with st.sidebar:
        st.markdown("### ✈️ Marvel.AI\n**Travel PA Core**")
        st.divider()
        nav = st.radio("System Modules", [
            "📊 Outcome Analytics", 
            "📥 Claim Ingestion Gateway", 
            "🗄️ Master Registrar", 
            "📋 Policy & Validation Engine"
        ], label_visibility="collapsed")
        
        st.divider()
        st.caption("SYSTEM STATUS")
        st.success("🟢 All Microservices Online")
        st.caption(f"Last Sync: {datetime.now().strftime('%Y-%m-%d %H:%M')}")

    # Route to the appropriate view function
    if nav == "📊 Outcome Analytics":
        render_analytics()
    elif nav == "📥 Claim Ingestion Gateway":
        render_ingestion()
    elif nav == "🗄️ Master Registrar":
        render_registrar()
    elif nav == "📋 Policy & Validation Engine":
        render_policy_rules()

if __name__ == "__main__":
    main()