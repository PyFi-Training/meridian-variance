# Meridian Variance Demo — Presenter Playbook
**Meridian Components Ltd | FY2025 | PyFi Demo**

---

## Overview

This is a 8–12 minute screen-share demo showing how Python + AI compresses a three-day finance workflow into a single function call. The audience is finance professionals — they know Excel, they've used ChatGPT, and they're sceptical that Python offers them anything meaningfully better.

Your job is to make the argument concrete, not abstract. Every time you make a claim, show it in the code.

---

## The Business Story (tell this before opening any code)

Meridian Components is a mid-sized precision manufacturer doing around £50M in annual revenue across two plants:

- **Plant A** — precision aerospace and automotive parts, Sheffield. ~£32M revenue, 38 budget lines.
- **Plant B** — industrial valves and hydraulic components, Birmingham. ~£22M revenue, 38 budget lines.

Every month, the FP&A manager spends the better part of three days on the management accounts pack. Most of that time is variance commentary — pulling actuals from the ERP, reconciling to budget across 76 line items, writing a sentence of explanation per line, summarising by department, and producing the CFO brief.

The problem isn't that they can't do it. It's that a trained finance professional is spending 20+ hours a month writing sentences like "above budget due to higher raw material costs" — time that should be on analysis, not narration.

**This demo shows what happens when Python takes over the narration.**

---

## The Argument (make this explicit early)

Before you open the notebook, say this:

> "Someone watching this might think — I could just open ChatGPT and paste the data in. And you'd be right, kind of. But here's the difference. ChatGPT in a browser is a tool you use. Python is infrastructure you build. One requires a human every single time. The other runs without you."

Then open the notebook and prove it.

---

## Demo Flow — Notebook (`notebooks/demo.ipynb`)

### Cell 1 — Setup
Run `%pip install .. -q` and set the API key. Don't linger here.

---

### Cell 2 — The raw data
Run the cell that loads both CSVs and prints the line counts.

**Say:** "Two CSV files. One per plant. That's all the pipeline needs. Everything else is computed — nothing is hardcoded."

Point to the columns: plant, department, line item, budget, actual, is_revenue.

**Say:** "The is_revenue column is important. You'll see why in a moment."

---

### Cell 3 — The variance engine
Run `load()` and `compute_variances()`. Show the output DataFrame.

**Say:** "Here's a rule that Excel gets wrong silently. Revenue and cost lines are directionally opposite. If revenue comes in above budget, that's good. If costs come in above budget, that's bad. They're the same number with opposite meaning. Python encodes this once, in `compute_variances()`, and applies it correctly to all 76 lines every time. If you're doing this in Excel with a shared formula, you're relying on whoever built the model to have thought of this. One wrong sign convention and the CFO is looking at a report where good news looks like bad news."

Show the `is_favourable` column. Point to a revenue line and a cost line side by side.

---

### Cell 4 — Worst variances
Run the ranking cell.

**Say:** "Instant ranking across the whole group. No sorting, no filtering, no pivot table. This is the list the CFO cares about. We haven't called the AI yet — this is pure Python."

---

### Cell 5 — Show the prompts (the governed AI moment — most important cell)

Run the prompt display cells for both commentary and severity.

**Say:** "Before we fire anything at scale, I want to show you what's actually going inside. For every single line item, Python constructs a prompt like this. It's not generic. It knows the plant, the department, the line name, the budget, the actual, the variance direction. And it enforces rules — one sentence, maximum 28 words, no filler phrases, correct directional language. The model can't hallucinate that something is favourable when it's unfavourable because Python has already encoded that in the prompt."

Pause here. Let it land.

**Say:** "Now contrast this with opening ChatGPT. You paste a table. You type 'write variance commentary'. You get output that sort of looks right. But you have no control over format, length, tone, or direction. And you do this 76 times. Manually. One at a time."

---

### Cell 6 — Run the full pipeline

Run `analysis.run()` and watch the terminal output scroll.

**Say:** "171 API calls. Three passes. Watch the counter."

Let it run. Don't talk over the output — let the audience watch the numbers tick.

When it finishes, say: "That's the whole pipeline. Line-item commentary, severity classification, department summaries, plant executive briefs, and the consolidated CFO report. Done."

**Key number to say out loud:** "Pass 2 fires 92 calls simultaneously — severity classification and department summaries in parallel. A finance analyst doing this manually would spend most of a day on 92 sequential prompts. Python issues them concurrently and returns in roughly the time it takes to make one."

---

### Cell 7 — Show the output

Show the enriched DataFrame with `ai_commentary` and `ai_severity` columns.

Point to a HIGH severity line. Point to the commentary. Read one aloud.

**Say:** "Notice the commentary isn't generic. It's specific to this line, this plant, this context. That's because Python told the model exactly what it was looking at."

---

### Cell 8 — Department summaries

Print one department summary.

**Say:** "These are synthesised from the line items. The AI looked at everything underneath Cost of Sales and wrote a paragraph identifying the dominant driver. This would normally take a senior analyst 20-30 minutes per department across both plants."

---

### Cell 9 — CFO brief

Print the CFO brief.

**Say:** "This is the output that goes to the Monday morning review. Python generated this from the plant summaries, which it generated from the department summaries, which it generated from the line items. A hierarchy of AI output, each layer grounded in the one below it. Four paragraphs. Took less than a second."

---

### Cells 10–13 — Chat

Initialise `Chat()` and run three questions:

1. `"Compare raw material performance across Plant A and Plant B. Which plant has the bigger problem?"`
2. `"Which three line items should the CFO prioritise in Monday's review and why?"`
3. `"If we bring Plant A raw material costs back to budget, what does the group gross profit look like?"`

**Say before running:** "The Chat class injects the full context — all 76 line items, all department summaries, both plant briefs, the CFO brief — automatically. I didn't paste anything. The model has everything it needs from the first message."

After each response: let the audience read it. Don't rush.

After question 3: "That's a what-if analysis. In Excel this would be a scenario model — a separate tab, manual inputs. Here it's a question."

---

## The Closing Argument

After the chat, say:

> "What you just saw took about 90 seconds. The finance equivalent — pulling data, computing variances, writing commentary, summarising by department, drafting the CFO brief, then being available to answer what-if questions — takes a trained finance professional the better part of two days. Every month. Python doesn't replace that professional. It removes them from the parts that don't require their judgment, so they can spend their time on the parts that do."

---

## If They Ask "Why Not Just Use ChatGPT?"

**Answer:** "You could. And you'd get something that looks similar — once. The difference is what happens on month two. Python runs the same pipeline, the same way, in one call. ChatGPT in a browser requires you to paste the data, prompt each line, copy the output, repeat. That's a workflow. Python is infrastructure. The first time you build it costs you effort. Every month after that costs you nothing."

---

## Technical Questions You Might Get

**"What's asyncio?"**
> "It's Python's built-in tool for running tasks concurrently. Normally when you make an API call, Python waits for the response before making the next one. With asyncio, it fires all the calls at once and waits for all of them together. That's why 171 calls take roughly the same time as one."

**"What does the system prompt do?"**
> "It sets the rules for every response. Company name, industry context, output format, word limit, what phrases to avoid. The model follows these constraints on every single call — consistently, without being reminded."

**"Could I build this myself?"**
> "That's exactly the point. Yes. And that's what ITP teaches — how to build pipelines like this for your specific finance context, with your data, your company's rules, your output format."

---

## Files to Have Open Before You Start

1. `notebooks/demo.ipynb` — main demo, all cells cleared and ready to run
2. `data/input/plant_a.csv` — have this open in a tab so you can show the raw data visually if needed
3. Terminal in the repo directory — for if you want to show `streamlit run app.py` at the end

---

## Timing Guide

| Section | Time |
|---|---|
| Business story (verbal) | 1.5 min |
| The argument (verbal) | 1 min |
| Raw data cells | 1 min |
| Variance engine + worst lines | 2 min |
| Prompt display (governed AI moment) | 2 min |
| `analysis.run()` — live | 1.5 min |
| Output review | 1 min |
| CFO brief | 0.5 min |
| Chat (3 questions) | 2 min |
| Closing argument | 1 min |
| **Total** | **~14 min** |

Trim by cutting one chat question if you need to stay under 10 minutes.

---

*Built by PyFi — Python and AI training for finance professionals | pyfi.com*
