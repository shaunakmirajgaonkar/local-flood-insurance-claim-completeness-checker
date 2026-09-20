from __future__ import annotations

from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from analytics import (
    REQUIRED_COLUMNS,
    add_screening_columns,
    classify_completeness,
    compact_report_table,
    evidence_checklist,
    markdown_table,
    scenario_score,
)

BASE_DIR = Path(__file__).resolve().parent
SAMPLE_FILE = BASE_DIR / "data" / "sample_flood_claims.csv"
ASSETS = BASE_DIR / "assets"

st.set_page_config(
    page_title="Local Flood Claim Completeness Checker",
    page_icon="🧾",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
    <style>
    .stApp { background: #f5f8fc; color: #172033; }
    [data-testid="stSidebar"] { background: #ffffff; border-right: 1px solid #e4e9f1; }
    .hero { background: linear-gradient(135deg,#ffffff 0%,#eef6ff 50%,#f5f2ff 100%); border:1px solid #e2e8f0; border-radius:24px; padding:28px 30px; margin-bottom:20px; box-shadow:0 12px 35px rgba(45,62,80,.08); }
    .hero h1 { margin:0; font-size:2.2rem; color:#152238; }
    .hero p { margin:.5rem 0 0; color:#5c6b82; font-size:1.02rem; }
    .eyebrow { color:#4f46e5; font-weight:800; letter-spacing:.08em; text-transform:uppercase; font-size:.78rem; }
    .metric-card { background:#fff; border:1px solid #e3e8f0; border-radius:18px; padding:18px 20px; box-shadow:0 8px 24px rgba(53,70,91,.06); }
    .metric-label { color:#6a768a; font-size:.84rem; }
    .metric-value { color:#172033; font-size:1.72rem; font-weight:800; margin-top:3px; }
    .badge { display:inline-block; padding:6px 10px; border-radius:999px; font-weight:700; font-size:.78rem; }
    .note { background:#fff; border-left:4px solid #4f46e5; border-radius:10px; padding:12px 14px; color:#526176; }
    .small { color:#657289; font-size:.88rem; }
    </style>
    """,
    unsafe_allow_html=True,
)


def metric_card(label: str, value: str, caption: str = "") -> None:
    st.markdown(
        f'<div class="metric-card"><div class="metric-label">{label}</div><div class="metric-value">{value}</div><div class="small">{caption}</div></div>',
        unsafe_allow_html=True,
    )


def load_sample() -> pd.DataFrame:
    return pd.read_csv(SAMPLE_FILE)


def validate_upload(df: pd.DataFrame) -> None:
    missing = [c for c in REQUIRED_COLUMNS if c not in df.columns]
    if missing:
        st.error("Uploaded CSV is missing required columns: " + ", ".join(missing))
        st.stop()


def class_counts(df: pd.DataFrame) -> pd.Series:
    return df["claim_completeness_class"].value_counts().reindex(
        ["Ready for submission review", "Mostly complete", "Evidence gaps", "Major gaps"], fill_value=0
    )


def main() -> None:
    st.markdown(
        '<div class="hero"><div class="eyebrow">LOCAL-FIRST · CLAIM PREPARATION INTELLIGENCE</div><h1>🧾 Flood Insurance Claim Completeness Checker</h1><p>Organize locally supplied claim evidence, damage records, receipts, reports, and documentation signals into a transparent completeness screen before submission review.</p></div>',
        unsafe_allow_html=True,
    )

    with st.sidebar:
        st.markdown("### Workspace")
        upload = st.file_uploader("Upload claim CSV", type=["csv"])
        use_sample = st.checkbox("Use bundled sample data", value=not bool(upload))
        st.caption("All processing stays local to this application.")
        st.markdown("---")
        st.markdown("### Navigation")
        page = st.radio(
            "Open module",
            [
                "Overview",
                "Completeness Matrix",
                "Evidence Checklist",
                "Damage & Documentation",
                "Priority Review",
                "Scenario Lab",
                "Reports & Export",
                "Data Explorer",
            ],
            label_visibility="collapsed",
        )

    if upload is not None:
        try:
            raw = pd.read_csv(upload)
            validate_upload(raw)
        except Exception as exc:
            st.error(f"Could not read the uploaded CSV: {exc}")
            st.stop()
    else:
        if not use_sample:
            st.info("Upload a CSV or enable the bundled sample dataset in the sidebar.")
            st.stop()
        raw = load_sample()

    df = add_screening_columns(raw)

    if page == "Overview":
        c1, c2, c3, c4 = st.columns(4)
        with c1: metric_card("Claims screened", f"{len(df):,}", "Local dataset")
        with c2: metric_card("Average completeness", f"{df['claim_completeness_score'].mean():.1f}/100", "Evidence readiness signal")
        with c3: metric_card("Claims with gaps", f"{int((df['missing_evidence_count'] > 0).sum()):,}", "At least one checklist gap")
        with c4: metric_card("Urgent review", f"{int((df['review_priority'] == 'Urgent review').sum()):,}", "Score or timing trigger")

        st.markdown("### Completeness distribution")
        left, right = st.columns([1.05, 1])
        with left:
            cc = class_counts(df).reset_index()
            cc.columns = ["Class", "Claims"]
            fig = px.bar(cc, x="Class", y="Claims", text="Claims")
            fig.update_layout(template="plotly_white", height=360, margin=dict(l=10,r=10,t=20,b=10))
            st.plotly_chart(fig, use_container_width=True)
        with right:
            area = df.groupby("area", as_index=False)["claim_completeness_score"].mean().sort_values("claim_completeness_score")
            fig = px.bar(area, x="claim_completeness_score", y="area", orientation="h", text_auto=".1f")
            fig.update_layout(template="plotly_white", height=360, margin=dict(l=10,r=10,t=20,b=10), xaxis_title="Average score")
            st.plotly_chart(fig, use_container_width=True)

        st.markdown('<div class="note">This checker organizes evidence completeness only. It does not determine coverage, claim validity, settlement value, or insurer acceptance.</div>', unsafe_allow_html=True)

    elif page == "Completeness Matrix":
        st.markdown("### Claim completeness matrix")
        cols = st.multiselect(
            "Fields to show",
            ["claim_id","area","claim_type","claim_completeness_score","claim_completeness_class","missing_evidence_count","dominant_gap","review_priority","submission_deadline_days_remaining","photos_count","receipts_count"],
            default=["claim_id","area","claim_completeness_score","claim_completeness_class","missing_evidence_count","dominant_gap","review_priority"],
        )
        if not cols:
            st.warning("Select at least one field.")
        else:
            view = df[cols].copy()
            sort_col = "claim_completeness_score" if "claim_completeness_score" in view.columns else cols[0]
            st.dataframe(view.sort_values(sort_col, ascending=False), use_container_width=True, hide_index=True)

        score_hist = px.histogram(df, x="claim_completeness_score", nbins=15)
        score_hist.update_layout(template="plotly_white", height=320, margin=dict(l=10,r=10,t=20,b=10))
        st.plotly_chart(score_hist, use_container_width=True)

    elif page == "Evidence Checklist":
        st.markdown("### Evidence checklist")
        selected = st.selectbox("Select claim", df["claim_id"].astype(str).tolist())
        row = df.loc[df["claim_id"].astype(str) == selected].iloc[0]
        st.metric("Completeness score", f"{row['claim_completeness_score']:.1f}/100")
        checklist = evidence_checklist(row)
        checklist["Status"] = checklist["Present / complete"].map({True:"Present / complete", False:"Gap to review"})
        st.dataframe(checklist[["Evidence item","Status","Suggested record"]], use_container_width=True, hide_index=True)
        missing = checklist.loc[~checklist["Present / complete"], "Evidence item"].tolist()
        st.markdown("**Potential gaps:** " + (", ".join(missing) if missing else "None flagged by the checklist."))

    elif page == "Damage & Documentation":
        st.markdown("### Damage and documentation signals")
        a, b = st.columns(2)
        with a:
            fig = px.scatter(df, x="photos_count", y="damage_description_score", size="receipts_count", color="claim_completeness_class", hover_name="claim_id")
            fig.update_layout(template="plotly_white", height=380, margin=dict(l=10,r=10,t=20,b=10))
            st.plotly_chart(fig, use_container_width=True)
        with b:
            documentation = pd.DataFrame({
                "Evidence area": ["Policy","Incident date","Repair estimate","Ownership","Inventory","Room records","Moisture","Mitigation","Local report","Witness","Adjuster contact"],
                "Completion %": [
                    df["policy_document_present"].mean()*100,
                    df["incident_date_documented"].mean()*100,
                    df["repair_estimate_present"].mean()*100,
                    df["ownership_document_present"].mean()*100,
                    df["damaged_item_inventory_complete"].mean()*100,
                    df["room_damage_records_complete"].mean()*100,
                    df["moisture_documented"].mean()*100,
                    df["mitigation_actions_recorded"].mean()*100,
                    df["local_incident_report_present"].mean()*100,
                    df["witness_details_present"].mean()*100,
                    df["adjuster_contact_recorded"].mean()*100,
                ],
            })
            fig = px.bar(documentation.sort_values("Completion %"), x="Completion %", y="Evidence area", orientation="h", text_auto=".0f")
            fig.update_layout(template="plotly_white", height=380, margin=dict(l=10,r=10,t=20,b=10))
            st.plotly_chart(fig, use_container_width=True)

        st.markdown("### Deadline context")
        deadline = df.groupby("submission_deadline_days_remaining", as_index=False).size().rename(columns={"size":"Claims"})
        fig = px.bar(deadline, x="submission_deadline_days_remaining", y="Claims", text="Claims")
        fig.update_layout(template="plotly_white", height=320, margin=dict(l=10,r=10,t=20,b=10), xaxis_title="Days remaining (locally supplied)")
        st.plotly_chart(fig, use_container_width=True)

    elif page == "Priority Review":
        st.markdown("### Priority review queue")
        priority = df.sort_values(["review_priority","claim_completeness_score"], ascending=[True, True])
        focus = st.multiselect("Priority groups", ["Urgent review","Priority review","Routine review"], default=["Urgent review","Priority review"])
        view = priority[priority["review_priority"].isin(focus)]
        st.dataframe(view[["claim_id","area","claim_completeness_score","claim_completeness_class","missing_evidence_count","dominant_gap","submission_deadline_days_remaining","review_priority"]], use_container_width=True, hide_index=True)
        top = df["dominant_gap"].value_counts().reset_index()
        top.columns = ["Dominant gap", "Claims"]
        fig = px.bar(top, x="Claims", y="Dominant gap", orientation="h", text="Claims")
        fig.update_layout(template="plotly_white", height=320, margin=dict(l=10,r=10,t=20,b=10))
        st.plotly_chart(fig, use_container_width=True)

    elif page == "Scenario Lab":
        st.markdown("### Before-vs-after completeness scenario lab")
        c1, c2, c3, c4, c5 = st.columns(5)
        with c1: photo_change = st.slider("Add photos", -3, 8, 2)
        with c2: receipt_change = st.slider("Add receipts", -2, 6, 1)
        with c3: desc_change = st.slider("Description score change", -25, 25, 10)
        with c4: add_est = st.checkbox("Add repair estimate", value=True)
        with c5: add_inv = st.checkbox("Complete item inventory", value=True)
        scenario = scenario_score(df, photo_change, receipt_change, desc_change, add_est, add_inv)
        base_mean = df["claim_completeness_score"].mean()
        scen_mean = scenario["claim_completeness_score"].mean()
        x1, x2, x3 = st.columns(3)
        with x1: metric_card("Baseline average", f"{base_mean:.1f}/100")
        with x2: metric_card("Scenario average", f"{scen_mean:.1f}/100")
        with x3: metric_card("Average change", f"{scen_mean-base_mean:+.1f}", "Modeled checklist effect")
        comp = df[["claim_id","claim_completeness_score"]].rename(columns={"claim_completeness_score":"Baseline"}).merge(scenario[["claim_id","claim_completeness_score"]].rename(columns={"claim_completeness_score":"Scenario"}), on="claim_id")
        long = comp.melt(id_vars="claim_id", var_name="View", value_name="Score")
        fig = px.box(long, x="View", y="Score", points=False)
        fig.update_layout(template="plotly_white", height=340, margin=dict(l=10,r=10,t=20,b=10))
        st.plotly_chart(fig, use_container_width=True)
        st.dataframe(scenario[["claim_id","claim_completeness_score","claim_completeness_class","missing_evidence_count","dominant_gap"]].sort_values("claim_completeness_score"), use_container_width=True, hide_index=True)

    elif page == "Reports & Export":
        st.markdown("### Report-ready outputs")
        report = compact_report_table(df)
        st.dataframe(report, use_container_width=True, hide_index=True)
        report_md = "# Flood Claim Completeness Screening Report\n\n"
        report_md += "This locally generated report summarizes documentation-completeness signals. It does not determine coverage or settlement.\n\n"
        report_md += "## Summary\n\n"
        report_md += f"- Claims screened: {len(df)}\n- Average completeness score: {df['claim_completeness_score'].mean():.1f}/100\n- Claims with checklist gaps: {(df['missing_evidence_count'] > 0).sum()}\n\n"
        report_md += "## Priority snapshot\n\n" + markdown_table(report) + "\n"
        st.download_button("Download Markdown report", report_md, file_name="flood_claim_completeness_report.md", mime="text/markdown")
        st.download_button("Download screened CSV", df.to_csv(index=False), file_name="screened_flood_claims.csv", mime="text/csv")

    elif page == "Data Explorer":
        st.markdown("### Data explorer")
        st.dataframe(df, use_container_width=True, hide_index=True)
        st.download_button("Download normalized dataset", df.to_csv(index=False), file_name="normalized_flood_claims.csv", mime="text/csv")
        st.markdown("### Required columns")
        st.code("\n".join(REQUIRED_COLUMNS))


if __name__ == "__main__":
    main()
