# Meridian Components — Variance Analysis
### Python + AI for Finance | PyFi Demo

A production-style AI pipeline that processes a multi-plant manufacturing P&L across three months, fires ~171 concurrent OpenAI API calls, and produces line-item commentary, severity classification, department summaries, plant executive briefs, and a consolidated CFO report — in a single function call.

Built to demonstrate what a governed AI pipeline looks like in a finance context, and why Python is the foundation under everything AI does in finance.

---

## What it does

**Three-pass async pipeline:**

| Pass | Description | Calls |
|---|---|---|
| 1 | Line-item AI commentary — one per budget line | 76 |
| 2 | Severity classification + department summaries | 92 |
| 3 | Plant executive briefs + consolidated CFO brief | 3 |
| **Total** | All fired concurrently via `asyncio.gather()` | **~171** |

**Streamlit app** with four tabs:
- Summary & CFO Brief — group KPIs, consolidated executive brief, per-plant performance
- Variance Detail — filterable by plant, department, severity, or favourable/unfavourable
- Month Comparison — side-by-side movers when you run two different months; detects new plants automatically
- Ask the Report — full context injected, conversational Q&A across the full dataset

**Three months of demo data:**
- Month 1 — Plants A & B baseline (76 lines)
- Month 2 — Worsening steel costs, recovering aerospace revenue
- Month 3 — Peak raw material crisis + Plant C (Leeds, defence electronics) added automatically

---

## Repository layout

```
data/
  input/
    month_1_plant_a.csv          # Plant A — Precision Parts, Sheffield
    month_1_plant_b.csv          # Plant B — Industrial Components, Birmingham
    month_2_plant_a.csv          # Month 2 actuals — Plant A
    month_2_plant_b.csv          # Month 2 actuals — Plant B
    month_3_plant_a.csv          # Month 3 actuals — Plant A
    month_3_plant_b.csv          # Month 3 actuals — Plant B
    month_3_plant_c.csv          # Plant C — Defence Electronics, Leeds (new)
  output/
    variance_report.csv          # Written by analysis.run()

src/
  analysis/
    config/settings.py           # Company name, model selection, paths
    run/pipeline.py              # Three-pass async pipeline
    inspect/chat.py              # Chat class with programmatic context injection
    utilities/formatting.py      # fmt_dollars, fmt_percent, severity

notebooks/
  demo.ipynb                     # Teaching entry point — step-by-step walkthrough

app.py                           # Streamlit deployment
```

---

## Quick start

```bash
pip install .
```

Set your API key:

```bash
export OPENAI_API_KEY="sk-..."
```

Run in the notebook (`notebooks/demo.ipynb`):

```python
import analysis

results = analysis.run()
```

Chat with the output:

```python
from analysis import Chat

chat = Chat(
    df=results["df"],
    dept_summaries=results["dept_summaries"],
    plant_briefs=results["plant_briefs"],
    cfo_brief=results["cfo_brief"],
)

chat.msg("Which plant has the bigger raw material problem?")
chat.msg("If Plant A raw material costs returned to budget, what does group gross profit look like?")
```

---

## Streamlit app

```bash
streamlit run app.py
```

Paste your OpenAI API key into the sidebar input on first load. The key is stored in session state only — it is never written to environment variables or Streamlit secrets, and is cleared when the session ends. You will need to re-enter it each session.

Use the sidebar to select pre-loaded demo months or upload your own CSV files. Run Month 1, then Month 2, then Month 3 to see the month comparison and Plant C detection working.

**Expected CSV format:**

```
plant,department,line_item,budget,actual,is_revenue
Plant A,Revenue,Product Sales – Precision Parts,18500000,19420000,True
Plant A,Cost of Sales,Raw Materials – Steel,9200000,10380000,False
```

---

## Cost

Running the full pipeline once (~171 calls, GPT-4o) costs approximately $0.15–0.25. Loading $5 onto your OpenAI account gives you more than enough to explore the repo.

---

## Key design decisions

**Sign convention** — revenue and cost lines are directionally opposite. `compute_variances()` encodes this once and applies it correctly to every line. Changing the rule means changing one function.

**Async concurrency** — all API calls are issued simultaneously via `asyncio.gather()` with a semaphore capping concurrent connections at 20. Wall-clock time is roughly the slowest single call, not 171 × one call.

**Governed context** — the `Chat` class builds a structured context string from the full dataset before the first message. The model answers from injected data, not from training knowledge. Every cited number is traceable to a row in the variance table.

**Modular structure** — mirrors the [Steward View](https://github.com/PyFi-Training/steward-view) architecture: config in `config/`, pipeline logic in `run/`, conversational interface in `inspect/`, all exposed through a clean top-level `analysis` package.

---

## About

Built by [PyFi](https://pyfi.com) — Python and AI training for finance professionals.

PyFi's [Introduction to Python (ITP)](https://pyfi.com/itp) cohort teaches finance professionals to build pipelines like this one — from data loading through to governed AI deployment.
