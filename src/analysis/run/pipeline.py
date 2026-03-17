"""
pipeline.py
───────────────────────────────────────────────────────────────────────────
Three-pass AI pipeline, all calls issued concurrently with asyncio.

Pass 1 — Line-item commentary       ~76 calls  (38 lines × 2 plants)
Pass 2 — Department summaries       ~16 calls  (8 depts × 2 plants)
Pass 3 — Plant executive briefs      2 calls
         Consolidated CFO brief      1 call
         Severity classification    ~76 calls  (one per line item)
                                   ─────────
Total                              ~171 calls fired concurrently
"""

import os
import asyncio
import pandas as pd
from openai import AsyncOpenAI
from analysis.config import CONFIG
from analysis.utilities import fmt_dollars, fmt_percent, severity


# ── Load ──────────────────────────────────────────────────────────────────────

def load() -> pd.DataFrame:
    """Load both plant CSVs and return a single combined DataFrame."""
    a = pd.read_csv(CONFIG.plant_a_path)
    b = pd.read_csv(CONFIG.plant_b_path)
    df = pd.concat([a, b], ignore_index=True)
    df.columns = [c.strip().lower().replace(" ", "_") for c in df.columns]
    df["budget"]     = pd.to_numeric(df["budget"],     errors="coerce").fillna(0)
    df["actual"]     = pd.to_numeric(df["actual"],     errors="coerce").fillna(0)
    df["is_revenue"] = df["is_revenue"].astype(str).str.lower().isin(["true", "1", "yes"])
    return df


# ── Variance Engine ───────────────────────────────────────────────────────────

def compute_variances(df: pd.DataFrame) -> pd.DataFrame:
    """
    Sign convention:
      Revenue lines:  favourable = actual > budget  →  variance = actual − budget
      Cost lines:     favourable = actual < budget  →  variance = budget − actual
    Positive variance = always favourable.
    """
    df = df.copy()
    df["variance_dollars"] = df.apply(
        lambda r: r["actual"] - r["budget"] if r["is_revenue"]
                  else r["budget"] - r["actual"],
        axis=1,
    )
    df["variance_pct"] = df.apply(
        lambda r: r["variance_dollars"] / abs(r["budget"]) if r["budget"] != 0 else 0,
        axis=1,
    )
    df["is_favourable"] = df["variance_dollars"] >= 0
    return df


# ── Prompt builders ───────────────────────────────────────────────────────────

def _commentary_system() -> str:
    return (
        f"You are a senior finance director writing variance commentary for "
        f"{CONFIG.company_name}, a {CONFIG.industry} business, {CONFIG.period}.\n\n"
        "Rules:\n"
        "- One sentence, maximum 28 words\n"
        "- Open with: Above budget / Below budget / In line with budget\n"
        "- Give a specific operational reason — no generic filler\n"
        "- Never use: noteworthy, significant, substantial, it is worth noting\n"
        "- Revenue above budget = favourable; Revenue below budget = unfavourable\n"
        "- Cost above budget = unfavourable; Cost below budget = favourable\n"
        "- Return ONLY the sentence, nothing else"
    )


def _commentary_user(row: pd.Series) -> str:
    direction = (
        "Above budget (favourable)"   if     row["is_revenue"] and     row["is_favourable"] else
        "Below budget (unfavourable)" if     row["is_revenue"] and not row["is_favourable"] else
        "Below budget (favourable)"   if not row["is_revenue"] and     row["is_favourable"] else
        "Above budget (unfavourable)"
    )
    return (
        f"Plant: {row['plant']}\n"
        f"Department: {row['department']}\n"
        f"Line item: {row['line_item']}\n"
        f"Budget: {fmt_dollars(row['budget'])}\n"
        f"Actual: {fmt_dollars(row['actual'])}\n"
        f"Variance: {fmt_dollars(abs(row['variance_dollars']))} — {direction} "
        f"({fmt_percent(abs(row['variance_pct']))})\n\n"
        "Write one sentence of variance commentary."
    )


def _severity_system() -> str:
    return (
        "You classify financial variances by severity. "
        "Return ONLY one word: HIGH, MEDIUM, or LOW.\n"
        "HIGH   = variance > 15% OR material dollar impact on plant P&L\n"
        "MEDIUM = variance 7–15%\n"
        "LOW    = variance < 7% and immaterial in dollar terms"
    )


def _severity_user(row: pd.Series) -> str:
    return (
        f"Line: {row['line_item']} | Plant: {row['plant']}\n"
        f"Budget: {fmt_dollars(row['budget'])} | Actual: {fmt_dollars(row['actual'])}\n"
        f"Variance: {fmt_percent(row['variance_pct'])} | "
        f"{'Favourable' if row['is_favourable'] else 'Unfavourable'}\n"
        "Severity?"
    )


def _dept_summary_system() -> str:
    return (
        f"You are a finance director at {CONFIG.company_name} writing a department summary "
        f"for the {CONFIG.period} management accounts.\n\n"
        "Rules:\n"
        "- Two to three sentences maximum\n"
        "- Identify the dominant driver of the department's net variance\n"
        "- Flag any line that requires CFO attention\n"
        "- Use plain finance language, no filler\n"
        "- Return ONLY the summary paragraph"
    )


def _dept_summary_user(plant: str, dept: str, dept_df: pd.DataFrame) -> str:
    lines = []
    for _, r in dept_df.iterrows():
        fav = "FAV" if r["is_favourable"] else "UNF"
        lines.append(
            f"  {r['line_item']}: budget {fmt_dollars(r['budget'])} | "
            f"actual {fmt_dollars(r['actual'])} | "
            f"var {fmt_dollars(r['variance_dollars'])} ({fmt_percent(r['variance_pct'])}) {fav}"
        )
    net_var = dept_df["variance_dollars"].sum()
    return (
        f"Plant: {plant} | Department: {dept}\n"
        f"Net department variance: {fmt_dollars(net_var)}\n\n"
        "Line items:\n" + "\n".join(lines) + "\n\nWrite the department summary."
    )


def _plant_brief_system() -> str:
    return (
        f"You are the CFO of {CONFIG.company_name}. Write an executive summary of one plant's "
        f"financial performance for {CONFIG.period}.\n\n"
        "Rules:\n"
        "- Three paragraphs: (1) headline performance, (2) key cost drivers, (3) recommended actions\n"
        "- Maximum 120 words total\n"
        "- Be direct, specific, and action-oriented\n"
        "- Return ONLY the three paragraphs"
    )


def _plant_brief_user(plant: str, plant_df: pd.DataFrame, dept_summaries: dict) -> str:
    rev  = plant_df[plant_df["is_revenue"]]
    cost = plant_df[~plant_df["is_revenue"]]
    rev_var  = (rev["actual"]  - rev["budget"]).sum()
    cost_var = (cost["budget"] - cost["actual"]).sum()
    gp_bud   = rev["budget"].sum() - cost["budget"].sum()
    gp_act   = rev["actual"].sum() - cost["actual"].sum()

    summaries = "\n\n".join(
        f"{dept}:\n{summary}"
        for dept, summary in dept_summaries.items()
    )
    return (
        f"Plant: {plant}\n"
        f"Total Revenue: budget {fmt_dollars(rev['budget'].sum())} | "
        f"actual {fmt_dollars(rev['actual'].sum())} | var {fmt_dollars(rev_var)}\n"
        f"Total Costs: budget {fmt_dollars(cost['budget'].sum())} | "
        f"actual {fmt_dollars(cost['actual'].sum())} | var {fmt_dollars(cost_var)}\n"
        f"Gross Profit: budget {fmt_dollars(gp_bud)} | actual {fmt_dollars(gp_act)} | "
        f"var {fmt_dollars(gp_act - gp_bud)}\n\n"
        f"Department summaries:\n{summaries}\n\n"
        "Write the plant executive brief."
    )


def _cfo_brief_system() -> str:
    return (
        f"You are the Group CFO of {CONFIG.company_name}. Write a consolidated executive brief "
        f"covering both manufacturing plants for {CONFIG.period}.\n\n"
        "Rules:\n"
        "- Four paragraphs: (1) group headline, (2) Plant A performance, "
        "(3) Plant B performance, (4) group priorities and actions\n"
        "- Maximum 180 words total\n"
        "- Be direct, comparative, and action-oriented\n"
        "- Return ONLY the four paragraphs"
    )


def _cfo_brief_user(full_df: pd.DataFrame, plant_briefs: dict) -> str:
    rev  = full_df[full_df["is_revenue"]]
    cost = full_df[~full_df["is_revenue"]]
    gp_bud = rev["budget"].sum() - cost["budget"].sum()
    gp_act = rev["actual"].sum() - cost["actual"].sum()
    briefs = "\n\n".join(f"{p}:\n{b}" for p, b in plant_briefs.items())
    return (
        f"Group Total Revenue: budget {fmt_dollars(rev['budget'].sum())} | "
        f"actual {fmt_dollars(rev['actual'].sum())}\n"
        f"Group Total Costs: budget {fmt_dollars(cost['budget'].sum())} | "
        f"actual {fmt_dollars(cost['actual'].sum())}\n"
        f"Group Gross Profit: budget {fmt_dollars(gp_bud)} | actual {fmt_dollars(gp_act)}\n\n"
        f"Plant briefs:\n{briefs}\n\nWrite the consolidated CFO brief."
    )


# ── Async callers ─────────────────────────────────────────────────────────────

async def _call(client: AsyncOpenAI, system: str, user: str,
                model: str, max_tokens: int, temperature: float,
                sem: asyncio.Semaphore) -> str:
    async with sem:
        for attempt in range(3):
            try:
                r = await client.chat.completions.create(
                    model=model,
                    messages=[{"role": "system", "content": system},
                              {"role": "user",   "content": user}],
                    max_tokens=max_tokens,
                    temperature=temperature,
                )
                return r.choices[0].message.content.strip()
            except Exception as e:
                if attempt == 2:
                    return f"[Error: {str(e)[:60]}]"
                await asyncio.sleep(2 ** attempt)


# ── Main pipeline ─────────────────────────────────────────────────────────────

async def _run_async(df: pd.DataFrame, verbose: bool, api_key: str = "") -> dict:
    key = api_key or os.environ.get("OPENAI_API_KEY", "")
    client = AsyncOpenAI(api_key=key)
    # Create semaphore fresh inside this event loop — avoids cross-loop errors on Streamlit Cloud
    sem = asyncio.Semaphore(20)
    results = {}

    # ── PASS 1: Line-item commentary (~76 calls) ──────────────────────────────
    if verbose:
        print(f"  Pass 1 — line-item commentary ({len(df)} calls, concurrent)...")

    commentary_tasks = [
        _call(client, _commentary_system(), _commentary_user(row),
              CONFIG.commentary_model, CONFIG.commentary_max_tokens,
              CONFIG.commentary_temperature, sem)
        for _, row in df.iterrows()
    ]
    results["commentary"] = await asyncio.gather(*commentary_tasks)

    # ── PASS 2: Severity classification (~76 calls, concurrent with dept summaries)
    if verbose:
        print(f"  Pass 2 — severity classification ({len(df)} calls) + "
              f"department summaries ({df.groupby(['plant','department']).ngroups} calls), concurrent...")

    severity_tasks = [
        _call(client, _severity_system(), _severity_user(row),
              CONFIG.commentary_model, 5, 0.0, sem)
        for _, row in df.iterrows()
    ]

    # ── PASS 2b: Department summaries (16 calls) ──────────────────────────────
    dept_groups = list(df.groupby(["plant", "department"]))
    dept_summary_tasks = [
        _call(client, _dept_summary_system(),
              _dept_summary_user(plant, dept, dept_df),
              CONFIG.summary_model, CONFIG.summary_max_tokens,
              CONFIG.summary_temperature, sem)
        for (plant, dept), dept_df in dept_groups
    ]

    # Fire severity + dept summaries all at once
    all_pass2 = await asyncio.gather(*(severity_tasks + dept_summary_tasks))
    results["severity"]       = list(all_pass2[:len(df)])
    dept_summary_results      = list(all_pass2[len(df):])

    # Map dept summaries back to (plant, dept) keys
    dept_summaries = {
        (plant, dept): dept_summary_results[i]
        for i, ((plant, dept), _) in enumerate(dept_groups)
    }
    results["dept_summaries"] = dept_summaries

    # ── PASS 3: Plant briefs (2 calls) + CFO brief (1 call) ───────────────────
    if verbose:
        n_pass3 = len(CONFIG.plants) + 1
        print(f"  Pass 3 — plant executive briefs ({len(CONFIG.plants)} calls) + "
              f"consolidated CFO brief (1 call), concurrent...")

    actual_plants = df["plant"].unique().tolist()
    plant_brief_tasks = []
    for plant in actual_plants:
        plant_df     = df[df["plant"] == plant]
        plant_depts  = {
            dept: dept_summaries[(plant, dept)]
            for (p, dept) in dept_summaries
            if p == plant
        }
        plant_brief_tasks.append(
            _call(client, _plant_brief_system(),
                  _plant_brief_user(plant, plant_df, plant_depts),
                  CONFIG.summary_model, CONFIG.cfo_brief_max_tokens,
                  CONFIG.summary_temperature, sem)
        )

    plant_brief_results = await asyncio.gather(*plant_brief_tasks)
    plant_briefs = {p: plant_brief_results[i] for i, p in enumerate(actual_plants)}
    results["plant_briefs"] = plant_briefs

    cfo_brief = await _call(
        client, _cfo_brief_system(), _cfo_brief_user(df, plant_briefs),
        CONFIG.summary_model, CONFIG.cfo_brief_max_tokens, CONFIG.summary_temperature, sem,
    )
    results["cfo_brief"] = cfo_brief

    return results


def _count_calls(df: pd.DataFrame) -> int:
    line_commentary  = len(df)
    severity_calls   = len(df)
    dept_summaries   = df.groupby(["plant", "department"]).ngroups
    plant_briefs     = df["plant"].nunique()
    cfo_brief        = 1
    return line_commentary + severity_calls + dept_summaries + plant_briefs + cfo_brief


def _print_summary(df: pd.DataFrame, cfo_brief: str) -> None:
    rev  = df[df["is_revenue"]]
    cost = df[~df["is_revenue"]]
    gp_bud = rev["budget"].sum() - cost["budget"].sum()
    gp_act = rev["actual"].sum() - cost["actual"].sum()

    print("\n── MERIDIAN COMPONENTS LTD  |  FY2025  |  CONSOLIDATED ─────────────")
    print(f"  Revenue   Budget: {fmt_dollars(rev['budget'].sum()):>14}  "
          f"Actual: {fmt_dollars(rev['actual'].sum()):>14}  "
          f"Var: {fmt_dollars(rev['actual'].sum()-rev['budget'].sum()):>14}")
    print(f"  Costs     Budget: {fmt_dollars(cost['budget'].sum()):>14}  "
          f"Actual: {fmt_dollars(cost['actual'].sum()):>14}  "
          f"Var: {fmt_dollars(cost['budget'].sum()-cost['actual'].sum()):>14}")
    print(f"  Gr Profit Budget: {fmt_dollars(gp_bud):>14}  "
          f"Actual: {fmt_dollars(gp_act):>14}  "
          f"Var: {fmt_dollars(gp_act-gp_bud):>14}")

    for plant in CONFIG.plants:
        p = df[df["plant"] == plant]
        pr = p[p["is_revenue"]]
        pc = p[~p["is_revenue"]]
        print(f"\n  {plant}:")
        print(f"    Revenue  {fmt_dollars(pr['actual'].sum()):>14}  "
              f"(var {fmt_dollars(pr['actual'].sum()-pr['budget'].sum())})")
        print(f"    Costs    {fmt_dollars(pc['actual'].sum()):>14}  "
              f"(var {fmt_dollars(pc['budget'].sum()-pc['actual'].sum())})")

    high = df[df.get("ai_severity", pd.Series(dtype=str)) == "HIGH"]
    if "ai_severity" in df.columns:
        print(f"\n  HIGH severity variances: {len(high[~high['is_favourable']])}")

    print("\n── CONSOLIDATED CFO BRIEF ───────────────────────────────────────────")
    for line in cfo_brief.split("\n"):
        print(f"  {line}")
    print("─" * 70)


def run(verbose: bool = True) -> dict:
    """
    Full three-pass pipeline:
      Pass 1  — line-item AI commentary          (76 concurrent calls)
      Pass 2  — severity classification +
                department summaries             (92 concurrent calls)
      Pass 3  — plant executive briefs +
                consolidated CFO brief            (3 concurrent calls)
      ─────────────────────────────────────────────────────────────────
      Total                                     ~171 API calls

    Returns dict with keys:
      df              — enriched DataFrame with commentary and severity
      dept_summaries  — {(plant, dept): summary_text}
      plant_briefs    — {plant: brief_text}
      cfo_brief       — consolidated executive brief string
    """
    if verbose:
        print(f"Loading data for {CONFIG.company_name}...")
    df = load()
    df = compute_variances(df)

    total_calls = _count_calls(df)
    if verbose:
        print(f"  {len(df)} line items | {df['plant'].nunique()} plants | "
              f"{df.groupby(['plant','department']).ngroups} dept groups")
        print(f"  Total API calls: {total_calls} — firing concurrently with asyncio\n")

    ai = asyncio.run(_run_async(df, verbose))

    df["ai_commentary"] = ai["commentary"]
    df["ai_severity"]   = ai["severity"]

    os.makedirs("data/output", exist_ok=True)
    df.to_csv(CONFIG.output_path, index=False)

    if verbose:
        _print_summary(df, ai["cfo_brief"])
        print(f"\n✓ {total_calls} API calls completed")
        print(f"✓ Output written to {CONFIG.output_path}")
        print("  Ready for Chat() — full context injected automatically.\n")

    return {
        "df":             df,
        "dept_summaries": ai["dept_summaries"],
        "plant_briefs":   ai["plant_briefs"],
        "cfo_brief":      ai["cfo_brief"],
    }
