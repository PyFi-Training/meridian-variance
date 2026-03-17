"""
app.py  —  Meridian Components Variance Analysis
Run: streamlit run app.py
"""

import os, sys, asyncio
import pandas as pd
import streamlit as st

sys.path.insert(0, "src")

from analysis.run.pipeline import compute_variances, _run_async, _count_calls
from analysis.inspect.chat import _build_context
from analysis.config import CONFIG
from analysis.utilities import fmt_dollars, fmt_percent
from openai import OpenAI

st.set_page_config(page_title="Meridian Variance Analysis", page_icon="📊", layout="wide")

st.markdown("""
<style>
.dept-header{background:#1F2D3D;color:white;padding:6px 14px;border-radius:4px;
font-weight:600;font-size:13px;margin:16px 0 4px 0;}
.plant-badge{background:#2E4057;color:white;padding:8px 14px;border-radius:6px;
font-weight:700;font-size:14px;margin:20px 0 6px 0;}
.brief-box{background:white;border-left:4px solid #1F2D3D;padding:16px 20px;
border-radius:6px;margin:8px 0;line-height:1.6;}
.new-plant-box{background:#EBF5FB;border:1px solid #2E86C1;border-radius:6px;
padding:12px 16px;margin:12px 0;font-size:13px;}
</style>
""", unsafe_allow_html=True)

# ── API key ───────────────────────────────────────────────────────────────────
api_key = os.environ.get("OPENAI_API_KEY") or st.secrets.get("OPENAI_API_KEY", "")
if not api_key:
    api_key = st.sidebar.text_input("OpenAI API Key", type="password")
if api_key:
    os.environ["OPENAI_API_KEY"] = api_key

# ── Session state ─────────────────────────────────────────────────────────────
for k, v in [("results", None), ("prev_results", None),
             ("chat_history", []), ("run_label", "")]:
    if k not in st.session_state:
        st.session_state[k] = v

# ── Header ────────────────────────────────────────────────────────────────────
st.title("📊 Meridian Components Ltd")
st.markdown("#### AI-Powered Variance Analysis  |  Budget vs Actual")
st.divider()

# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("### Demo Controls")
    st.markdown("---")
    st.markdown("**Data source**")

    data_mode = st.radio("", ["Pre-loaded demo data", "Upload CSV files"],
                         label_visibility="collapsed")

    uploaded_files = []
    month_num = None
    plant_files_map = {
        1: ["data/input/month_1_plant_a.csv", "data/input/month_1_plant_b.csv"],
        2: ["data/input/month_2_plant_a.csv", "data/input/month_2_plant_b.csv"],
        3: ["data/input/month_3_plant_a.csv", "data/input/month_3_plant_b.csv",
            "data/input/month_3_plant_c.csv"],
    }

    if data_mode == "Pre-loaded demo data":
        demo_choice = st.selectbox("Select month", [
            "Month 1 — Plants A & B (Baseline)",
            "Month 2 — Plants A & B (Steel costs worsening)",
            "Month 3 — Plants A, B & C (Peak + new plant)",
        ])
        month_num = int(demo_choice[6])
        n_lines = len(plant_files_map[month_num]) * 38
        st.caption(f"{len(plant_files_map[month_num])} plants · {n_lines} line items")
        if month_num == 3:
            st.markdown("""<div class='new-plant-box'>
🏭 <b>Plant C added</b> — Leeds defence electronics.<br>
Pipeline handles it automatically. Zero config changes.
</div>""", unsafe_allow_html=True)
    else:
        uploaded_files = st.file_uploader(
            "Upload plant CSV file(s)", type="csv", accept_multiple_files=True,
            label_visibility="collapsed",
        )
        if uploaded_files:
            st.success(f"✓ {len(uploaded_files)} file(s) ready")
            for f in uploaded_files:
                st.caption(f"📄 {f.name}")

    st.markdown("---")
    run_btn = st.button("▶  Run Analysis", type="primary",
                        use_container_width=True, disabled=not api_key)
    if not api_key:
        st.caption("⚠️ Add OpenAI API key to run")

    if st.session_state.results:
        st.markdown("---")
        st.markdown("**Last run stats**")
        df_s = st.session_state.results["df"]
        st.metric("Line items", len(df_s))
        st.metric("Plants", df_s["plant"].nunique())
        st.metric("API calls fired", _count_calls(df_s))


# ── Load helper ───────────────────────────────────────────────────────────────
def load_data() -> pd.DataFrame:
    dfs = []
    if data_mode == "Pre-loaded demo data":
        for path in plant_files_map[month_num]:
            dfs.append(pd.read_csv(path))
    else:
        for f in uploaded_files:
            dfs.append(pd.read_csv(f))
    df = pd.concat(dfs, ignore_index=True)
    df.columns = [c.strip().lower().replace(" ", "_") for c in df.columns]
    df["budget"] = pd.to_numeric(df["budget"], errors="coerce").fillna(0)
    df["actual"] = pd.to_numeric(df["actual"], errors="coerce").fillna(0)
    df["is_revenue"] = df["is_revenue"].astype(str).str.lower().isin(["true","1","yes"])
    return df


# ── Run ───────────────────────────────────────────────────────────────────────
if run_btn:
    can_run = (data_mode == "Pre-loaded demo data") or len(uploaded_files) > 0
    if not can_run:
        st.error("Upload at least one CSV file.")
        st.stop()

    if st.session_state.results:
        st.session_state.prev_results = st.session_state.results

    label = demo_choice if data_mode == "Pre-loaded demo data" else \
            f"Upload: {', '.join(f.name for f in uploaded_files)}"

    with st.spinner("Loading and computing variances..."):
        df = load_data()
        df = compute_variances(df)

    total = _count_calls(df)
    with st.spinner(f"Firing {total} concurrent API calls..."):
        ai = asyncio.run(_run_async(df, verbose=False))

    df["ai_commentary"] = ai["commentary"]
    df["ai_severity"]   = ai["severity"]
    os.makedirs("data/output", exist_ok=True)
    df.to_csv(CONFIG.output_path, index=False)

    st.session_state.results = {
        "df": df, "dept_summaries": ai["dept_summaries"],
        "plant_briefs": ai["plant_briefs"], "cfo_brief": ai["cfo_brief"],
        "label": label,
    }
    st.session_state.chat_history = []
    st.success(f"✓ {total} calls complete · {len(df)} lines · "
               f"{df['plant'].nunique()} plant(s) · {df.groupby(['plant','department']).ngroups} dept groups")

if not st.session_state.results:
    st.info("Select a data source in the sidebar and click ▶ Run Analysis.")
    with st.expander("📋 CSV format"):
        st.code("plant,department,line_item,budget,actual,is_revenue\n"
                "Plant A,Revenue,Product Sales,18500000,19420000,True\n"
                "Plant A,Cost of Sales,Raw Materials,9200000,10380000,False", language="csv")
    st.stop()

r   = st.session_state.results
df  = r["df"]
prev = st.session_state.prev_results

# ── Tabs ──────────────────────────────────────────────────────────────────────
t1, t2, t3, t4 = st.tabs([
    "📈 Summary & CFO Brief",
    "📋 Variance Detail",
    "🔄 Month Comparison",
    "💬 Ask the Report",
])

# ─────────────────────────────────────────────
# TAB 1 — SUMMARY
# ─────────────────────────────────────────────
with t1:
    rev  = df[df["is_revenue"]]
    cost = df[~df["is_revenue"]]
    gp_bud = rev["budget"].sum() - cost["budget"].sum()
    gp_act = rev["actual"].sum() - cost["actual"].sum()

    st.caption(f"**Run:** {r['label']}")
    k1,k2,k3,k4,k5 = st.columns(5)
    k1.metric("Group Revenue", fmt_dollars(rev["actual"].sum()),
              fmt_dollars(rev["actual"].sum()-rev["budget"].sum()))
    k2.metric("Group Costs", fmt_dollars(cost["actual"].sum()),
              fmt_dollars(cost["budget"].sum()-cost["actual"].sum()))
    k3.metric("Gross Profit", fmt_dollars(gp_act), fmt_dollars(gp_act-gp_bud))
    k4.metric("HIGH Risk Lines",
              len(df[(~df["is_favourable"])&(df["ai_severity"]=="HIGH")]))
    k5.metric("Plants", df["plant"].nunique())

    st.divider()
    plants = df["plant"].unique()
    cols = st.columns(len(plants))
    for i, plant in enumerate(plants):
        p=df[df["plant"]==plant]; pr=p[p["is_revenue"]]; pc=p[~p["is_revenue"]]
        pgp_act=pr["actual"].sum()-pc["actual"].sum()
        pgp_bud=pr["budget"].sum()-pc["budget"].sum()
        with cols[i]:
            st.markdown(f"**{plant}**")
            st.metric("Revenue", fmt_dollars(pr["actual"].sum()),
                      fmt_dollars(pr["actual"].sum()-pr["budget"].sum()))
            st.metric("Gross Profit", fmt_dollars(pgp_act), fmt_dollars(pgp_act-pgp_bud))

    st.divider()
    st.subheader("Consolidated CFO Brief")
    st.markdown(f'<div class="brief-box">{r["cfo_brief"].replace(chr(10),"<br>")}</div>',
                unsafe_allow_html=True)
    for plant in plants:
        with st.expander(f"{plant} Executive Brief"):
            st.write(r["plant_briefs"][plant])

# ─────────────────────────────────────────────
# TAB 2 — DETAIL
# ─────────────────────────────────────────────
with t2:
    c1,c2 = st.columns(2)
    with c1:
        filt = st.selectbox("Filter",
                            ["All lines","Unfavourable only","HIGH severity only","Favourable only"])
    with c2:
        pf = st.selectbox("Plant", ["All plants"]+list(df["plant"].unique()))

    fd = df.copy()
    if filt=="Unfavourable only": fd=fd[~fd["is_favourable"]]
    elif filt=="HIGH severity only": fd=fd[fd["ai_severity"]=="HIGH"]
    elif filt=="Favourable only": fd=fd[fd["is_favourable"]]
    if pf!="All plants": fd=fd[fd["plant"]==pf]

    for plant in fd["plant"].unique():
        st.markdown(f'<div class="plant-badge">🏭 {plant}</div>', unsafe_allow_html=True)
        for dept in fd[fd["plant"]==plant]["department"].unique():
            dd=fd[(fd["plant"]==plant)&(fd["department"]==dept)]
            st.markdown(f'<div class="dept-header">{dept.upper()}</div>',
                        unsafe_allow_html=True)
            key=(plant,dept)
            if key in r["dept_summaries"]:
                with st.expander("Department summary"):
                    st.write(r["dept_summaries"][key])
            disp=pd.DataFrame({
                "Line Item": dd["line_item"].values,
                "Budget":    [fmt_dollars(v) for v in dd["budget"]],
                "Actual":    [fmt_dollars(v) for v in dd["actual"]],
                "Variance $":[fmt_dollars(v) for v in dd["variance_dollars"]],
                "Var %":     [fmt_percent(v) for v in dd["variance_pct"]],
                "":          ["✅" if v else "❌" for v in dd["is_favourable"]],
                "Severity":  dd["ai_severity"].values,
                "AI Commentary": dd["ai_commentary"].values,
            })
            st.dataframe(disp, use_container_width=True, hide_index=True,
                         column_config={"AI Commentary":st.column_config.TextColumn(width="large"),
                                        "Severity":st.column_config.TextColumn(width="small"),
                                        "":st.column_config.TextColumn(width="small")})

# ─────────────────────────────────────────────
# TAB 3 — COMPARISON
# ─────────────────────────────────────────────
with t3:
    if prev is None:
        st.info("Run the analysis twice to compare months side by side.")
        st.markdown("**Demo sequence:**")
        st.markdown("1. Select **Month 1** → Run Analysis")
        st.markdown("2. Select **Month 2** → Run Analysis")
        st.markdown("3. Come back here to see movers")
        st.markdown("4. Select **Month 3** → Run Analysis — see Plant C appear automatically")
    else:
        curr_df=r["df"]; prev_df=prev["df"]
        st.markdown(f"**{prev['label'][:35]}**  →  **{r['label'][:35]}**")
        st.divider()

        def totals(d):
            rv=d[d["is_revenue"]]; co=d[~d["is_revenue"]]
            return {"rev":rv["actual"].sum(),"rev_bud":rv["budget"].sum(),
                    "cost":co["actual"].sum(),"cost_bud":co["budget"].sum(),
                    "gp":rv["actual"].sum()-co["actual"].sum(),
                    "gp_bud":rv["budget"].sum()-co["budget"].sum()}

        c=totals(curr_df); p=totals(prev_df)
        st.subheader("Group — Month on Month")
        m1,m2,m3=st.columns(3)
        m1.metric("Revenue", fmt_dollars(c["rev"]),
                  f"MoM {fmt_dollars(c['rev']-p['rev'])}")
        m2.metric("Costs", fmt_dollars(c["cost"]),
                  f"MoM {fmt_dollars(p['cost']-c['cost'])}")
        m3.metric("Gross Profit", fmt_dollars(c["gp"]),
                  f"MoM {fmt_dollars(c['gp']-p['gp'])}")

        st.divider()
        st.subheader("Biggest Movers")

        ci=curr_df.set_index(["plant","line_item"])
        pi=prev_df.set_index(["plant","line_item"])
        common=ci.index.intersection(pi.index)
        movers=[]
        for idx in common:
            cv=float(ci.loc[idx,"variance_dollars"])
            pv=float(pi.loc[idx,"variance_dollars"])
            delta=cv-pv
            movers.append({"Plant":idx[0],"Line Item":idx[1],
                            "Prev Var $":fmt_dollars(pv),
                            "Curr Var $":fmt_dollars(cv),
                            "Movement":fmt_dollars(delta),
                            "_d":delta})
        mdf=pd.DataFrame(movers).sort_values("_d").drop("_d",axis=1)

        col_w, col_i = st.columns(2)
        with col_w:
            st.markdown("**Worsened most**")
            st.dataframe(mdf.head(8), use_container_width=True, hide_index=True)
        with col_i:
            st.markdown("**Improved most**")
            st.dataframe(mdf.tail(8).iloc[::-1], use_container_width=True, hide_index=True)

        # New plant detection
        new_lines=ci.index.difference(pi.index)
        if len(new_lines)>0:
            st.divider()
            new_plants=list(set([i[0] for i in new_lines]))
            st.subheader(f"🆕 New this run: {', '.join(new_plants)}")
            st.markdown(
                f"**{len(new_lines)} new line items** processed automatically. "
                f"No configuration changes — the pipeline handled it."
            )
            nd=curr_df[curr_df["plant"].isin(new_plants)]
            nr=nd[nd["is_revenue"]]; nc=nd[~nd["is_revenue"]]
            n1,n2,n3=st.columns(3)
            n1.metric("Revenue", fmt_dollars(nr["actual"].sum()),
                      fmt_dollars(nr["actual"].sum()-nr["budget"].sum()))
            n2.metric("Costs", fmt_dollars(nc["actual"].sum()),
                      fmt_dollars(nc["budget"].sum()-nc["actual"].sum()))
            n3.metric("Additional API calls", len(nd)*2+3)
            with st.expander(f"View {new_plants[0]} lines"):
                nd_disp=pd.DataFrame({
                    "Department":nd["department"].values,
                    "Line Item":nd["line_item"].values,
                    "Budget":[fmt_dollars(v) for v in nd["budget"]],
                    "Actual":[fmt_dollars(v) for v in nd["actual"]],
                    "Variance $":[fmt_dollars(v) for v in nd["variance_dollars"]],
                    "":["✅" if v else "❌" for v in nd["is_favourable"]],
                    "AI Commentary":nd["ai_commentary"].values,
                })
                st.dataframe(nd_disp, use_container_width=True, hide_index=True,
                             column_config={"AI Commentary":st.column_config.TextColumn(width="large")})

# ─────────────────────────────────────────────
# TAB 4 — CHAT
# ─────────────────────────────────────────────
with t4:
    st.caption("Full context injected automatically — all lines, dept summaries, plant briefs, CFO brief.")
    client=OpenAI(api_key=api_key)
    context=_build_context(df,r["dept_summaries"],r["plant_briefs"],r["cfo_brief"])

    for msg in st.session_state.chat_history:
        with st.chat_message(msg["role"]):
            st.write(msg["content"])

    if prompt:=st.chat_input("e.g. Compare raw material trends across all plants"):
        st.session_state.chat_history.append({"role":"user","content":prompt})
        with st.chat_message("user"): st.write(prompt)
        messages=[{"role":"system","content":(
            f"You are a senior finance analyst at {CONFIG.company_name}. "
            f"You have the full {CONFIG.period} variance report. "
            f"Answer precisely. Format dollars with commas. "
            f"Unfavourable in parentheses.\n\nVARIANCE DATA:\n{context}"
        )}]+[{"role":m["role"],"content":m["content"]}
             for m in st.session_state.chat_history]
        with st.chat_message("assistant"):
            resp=client.chat.completions.create(
                model=CONFIG.chat_model,messages=messages,
                temperature=CONFIG.chat_temperature,stream=True)
            reply=st.write_stream(
                c.choices[0].delta.content or ""
                for c in resp if c.choices[0].delta.content)
        st.session_state.chat_history.append({"role":"assistant","content":reply})

    if st.session_state.chat_history:
        if st.button("Clear conversation"): st.session_state.chat_history=[]; st.rerun()
