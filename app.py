import streamlit as st
import json
from diagnostic_engine import DiagnosticEngine

st.set_page_config(page_title="LastMile Clinician | AIORI-3", layout="wide", page_icon="📡")

st.markdown("""
    <style>
    .main-title { font-size: 32px; font-weight: 700; color: #1E3A8A; margin-bottom: 0px; }
    .sub-title { font-size: 16px; color: #4B5563; margin-bottom: 25px; }
    .card { background-color: #F9FAFB; padding: 20px; border-radius: 10px; border-left: 5px solid #2563EB; margin-bottom: 15px; }
    .card-inconclusive { background-color: #FFFBEB; padding: 20px; border-radius: 10px; border-left: 5px solid #F59E0B; margin-bottom: 15px; }
    </style>
""", unsafe_allow_html=True)

st.markdown('<div class="main-title">LastMile Clinician (PS-015)</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-title">Explainable Home and Last-Mile Connectivity Diagnostic System | RFC 2330 Compliant</div>', unsafe_allow_html=True)

st.sidebar.header("🔬 Diagnostic Control Center")
test_mode = st.sidebar.selectbox(
    "Select Evaluation Mode",
    [
        "Live System Diagnostics",
        "Controlled Fault: Gateway Unreachable",
        "Controlled Fault: DNS Failure",
        "Controlled Fault: Induced Packet Loss",
        "Controlled Fault: Network Congestion"
    ]
)

mode_mapping = {
    "Live System Diagnostics": None,
    "Controlled Fault: Gateway Unreachable": "GATEWAY_UNREACHABLE",
    "Controlled Fault: DNS Failure": "DNS_FAILURE",
    "Controlled Fault: Induced Packet Loss": "INDUCED_PACKET_LOSS",
    "Controlled Fault: Network Congestion": "CONGESTION"
}

run_button = st.sidebar.button("🚀 Run Diagnosis", use_container_width=True)

st.sidebar.markdown("---")
st.sidebar.info("""
**AIORI Hackathon 3 Compliant:**
- RFC 2330 Statistical Measurement Framework
- Transparent Decision Trees (No Guessing)
- Formal 'Inconclusive' Handling
- Evidence-Based Escalation Report
""")

engine = DiagnosticEngine()

if run_button or "last_diag" in st.session_state:
    if run_button:
        with st.spinner("Executing RFC 2330 probes across local and last-mile hops..."):
            diag_state = mode_mapping[test_mode]
            results = engine.run_guided_diagnosis(simulated_state=diag_state)
            st.session_state["last_diag"] = results
    else:
        results = st.session_state["last_diag"]

    m1, m2, m3, m4 = st.columns(4)
    gw_loss = results["metrics"]["gateway"]["loss_pct"]
    gw_rtt = results["metrics"]["gateway"]["avg_rtt_ms"]
    wan_loss = results["metrics"]["wan"]["loss_pct"]
    wan_rtt = results["metrics"]["wan"]["avg_rtt_ms"]
    dns_status = results["metrics"]["dns"]["status"]

    m1.metric("Local Gateway Loss", f"{gw_loss}%", delta="-Normal" if gw_loss == 0 else "FAIL", delta_color="inverse")
    m2.metric("Gateway Latency", f"{gw_rtt if gw_rtt else '--'} ms")
    m3.metric("WAN Packet Loss", f"{wan_loss}%", delta="-Normal" if wan_loss == 0 else "DEGRADED", delta_color="inverse")
    m4.metric("DNS Status", dns_status, delta="OK" if dns_status == "SUCCESS" else "ERROR", delta_color="normal" if dns_status == "SUCCESS" else "inverse")

    st.markdown("---")

    col_diag, col_evidence = st.columns([1.2, 1])

    with col_diag:
        st.subheader("🎯 Diagnostic Finding & Root-Cause Analysis")
        card_class = "card-inconclusive" if results["is_inconclusive"] else "card"
        badge = "⚠️ INCONCLUSIVE" if results["is_inconclusive"] else "✅ RESOLVED"
        
        st.markdown(f"""
        <div class="{card_class}">
            <h4>{badge}: {results['category']}</h4>
            <p><strong>Verdict:</strong> {results['verdict']}</p>
            <p><strong>Actionable Step:</strong> {results['recommendation']}</p>
        </div>
        """, unsafe_allow_html=True)

        st.subheader("🌲 Explainable Decision Trace")
        st.markdown("""
        ```mermaid
        graph TD
            A[Start RFC 2330 Probe] --> B{Gateway Reachable?}
            B -- No --> C[Fault: Local Gateway Unreachable]
            B -- Yes --> D{Public WAN Reachable?}
            D -- No --> E[Fault: Access Line Down]
            D -- Yes --> F{DNS Resolution Ok?}
            F -- No --> G[Fault: DNS Resolver Down]
            F -- Yes --> H{WAN Loss > 15%?}
            H -- Yes --> I[Fault: Last-Mile Packet Loss]
            H -- No --> J{WAN RTT > 180ms?}
            J -- Yes --> K[Fault: Network Congestion]
            J -- No --> L[Verdict: Optimal Connection]
        ```
        """)

    with col_evidence:
        st.subheader("📋 Empirical Evidence Chain")
        for item in results["evidence"]:
            st.markdown(f"- {item}")
        
        st.markdown("#### Raw Measurement Telemetry")
        st.json(results["metrics"])

    st.markdown("---")
    st.subheader("📄 Evidence-Based ISP Escalation Ticket")
    escalation_text = f"""### AIORI-3 PS-015 ISP Escalation Report
**Timestamp:** {results['timestamp']}
**Classification:** {results['category']}
**Diagnostic Verdict:** {results['verdict']}

#### Network Measurements (RFC 2330 Standard)
* Default Gateway Reachability: {'UP' if results['metrics']['gateway']['reachable'] else 'DOWN'} ({results['metrics']['gateway']['loss_pct']}% Loss)
* Public WAN Reachability: {'UP' if results['metrics']['wan']['reachable'] else 'DOWN'} ({results['metrics']['wan']['loss_pct']}% Loss, Avg RTT: {results['metrics']['wan']['avg_rtt_ms']} ms)
* DNS Resolver Status: {results['metrics']['dns']['status']}

#### Concrete Observations
{chr(10).join(['* ' + e for e in results['evidence']])}

#### System Demarcation
- Local home Wi-Fi/LAN status verified before tagging upstream faults.
- Diagnosis derived without unverified physical assumptions.
"""
    st.text_area("Copy-Pasteable ISP Ticket", escalation_text, height=180)
    st.download_button("📥 Export Escalation Report (.md)", escalation_text, file_name="network_escalation_ticket.md")
else:
    st.info("👈 Select a test mode or simulated fault in the left panel and click **'Run Diagnosis'** to inspect live telemetry.")