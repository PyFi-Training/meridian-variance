# Meridian Components — Variance Analysis Demo
### PyFi | Python + AI for Finance

A two-plant manufacturing variance analysis pipeline that fires **~171 concurrent OpenAI API calls** across three passes to produce line-item commentary, severity classification, department summaries, plant executive briefs, and a consolidated CFO report — in a single function call.

---

## Repository layout

```
data/
  input/
    plant_a.csv          # Plant A — Precision Parts (~$32M revenue, 38 lines)
    plant_b.csv          # Plant B — Industrial Components (~$22M revenue, 38 lines)
  output/
    variance_report.csv  # written by analysis.run()

src/
  analysis/
    config/              # company settings, model selection
    run/                 # three-pass async pipeline
    inspect/             # Chat class with injected context
    utilities/           # formatting helpers

notebooks/
  demo.ipynb             # teaching entry point

app.py                   # Streamlit deployment
```

---

## Quick start

```bash
pip install .
```

In `notebooks/demo.ipynb`:

```python
import os
os.environ["OPENAI_API_KEY"] = "sk-..."

import analysis
results = analysis.run()
```

Then chat:

```python
from analysis import Chat

chat = Chat(
    df=results["df"],
    dept_summaries=results["dept_summaries"],
    plant_briefs=results["plant_briefs"],
    cfo_brief=results["cfo_brief"],
)

chat.msg("Compare raw material performance across both plants.")
chat.msg("Which three lines should the CFO prioritise on Monday?")
```

---

## Streamlit

```bash
streamlit run app.py
```

---

## Pipeline — call count

| Pass | Description | Calls |
|---|---|---|
| 1 | Line-item commentary | 76 |
| 2 | Severity classification + department summaries | 92 |
| 3 | Plant briefs + CFO consolidated brief | 3 |
| **Total** | | **~171** |

All fired concurrently via `asyncio.gather()`.

---

Built by [PyFi](https://pyfi.com) — Python and AI training for finance professionals.
