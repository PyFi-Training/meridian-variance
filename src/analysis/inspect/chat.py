import os
import pandas as pd
from openai import OpenAI
from analysis.config import CONFIG
from analysis.utilities import fmt_dollars, fmt_percent


def _build_context(df: pd.DataFrame,
                   dept_summaries: dict = None,
                   plant_briefs: dict = None,
                   cfo_brief: str = None) -> str:
    """
    Build the full context string injected into every Chat session.
    Python controls exactly what the model receives — company name,
    period, plant structure, every line item with its variance,
    pre-computed department summaries, and the CFO brief.
    This is governed AI: structured input, no manual pasting.
    """
    lines = []
    lines.append(f"COMPANY: {CONFIG.company_name}")
    lines.append(f"PERIOD: {CONFIG.period}")
    lines.append(f"INDUSTRY: {CONFIG.industry}\n")

    # Consolidated totals
    rev  = df[df["is_revenue"]]
    cost = df[~df["is_revenue"]]
    gp_bud = rev["budget"].sum() - cost["budget"].sum()
    gp_act = rev["actual"].sum() - cost["actual"].sum()
    lines.append("GROUP TOTALS:")
    lines.append(f"  Revenue   Budget {fmt_dollars(rev['budget'].sum())} | "
                 f"Actual {fmt_dollars(rev['actual'].sum())} | "
                 f"Var {fmt_dollars(rev['actual'].sum()-rev['budget'].sum())}")
    lines.append(f"  Costs     Budget {fmt_dollars(cost['budget'].sum())} | "
                 f"Actual {fmt_dollars(cost['actual'].sum())} | "
                 f"Var {fmt_dollars(cost['budget'].sum()-cost['actual'].sum())}")
    lines.append(f"  Gr Profit Budget {fmt_dollars(gp_bud)} | "
                 f"Actual {fmt_dollars(gp_act)} | "
                 f"Var {fmt_dollars(gp_act - gp_bud)}\n")

    # Per-plant line items
    for plant in df["plant"].unique():
        plant_df = df[df["plant"] == plant]
        lines.append(f"{plant.upper()} LINE ITEMS "
                     f"(dept | line | budget | actual | var$ | var% | fav | severity):")
        for _, r in plant_df.iterrows():
            sev = r.get("ai_severity", "")
            fav = "FAV" if r["is_favourable"] else "UNF"
            lines.append(
                f"  {r['department']} | {r['line_item']} | "
                f"{fmt_dollars(r['budget'])} | {fmt_dollars(r['actual'])} | "
                f"{fmt_dollars(r['variance_dollars'])} | "
                f"{fmt_percent(r['variance_pct'])} | {fav} | {sev}"
            )
        lines.append("")

    # Department summaries
    if dept_summaries:
        lines.append("DEPARTMENT SUMMARIES:")
        for (plant, dept), summary in dept_summaries.items():
            lines.append(f"\n{plant} — {dept}:")
            lines.append(summary)
        lines.append("")

    # CFO brief
    if cfo_brief:
        lines.append("CFO BRIEF:")
        lines.append(cfo_brief)

    return "\n".join(lines)


class Chat:
    """
    Conversational interface over the full variance report.
    Context is injected once at init — including all line items,
    department summaries, plant briefs, and the CFO brief.
    Every message carries the full history.
    """

    def __init__(self,
                 df: pd.DataFrame = None,
                 dept_summaries: dict = None,
                 plant_briefs: dict = None,
                 cfo_brief: str = None):

        self._client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])

        if df is None:
            try:
                df = pd.read_csv(CONFIG.output_path)
            except FileNotFoundError:
                raise RuntimeError(
                    "No output CSV found. Run analysis.run() first, "
                    "or pass df= directly."
                )

        context = _build_context(df, dept_summaries, plant_briefs, cfo_brief)

        self._history = [{
            "role": "system",
            "content": (
                f"You are a senior finance analyst at {CONFIG.company_name}. "
                f"You have full access to the {CONFIG.period} variance report for both plants. "
                f"Answer questions precisely using the data. "
                f"Format dollars with commas. Use parentheses for unfavourable variances. "
                f"Be concise and direct — this is for an executive audience.\n\n"
                f"VARIANCE DATA:\n{context}"
            ),
        }]

    def msg(self, question: str) -> str:
        self._history.append({"role": "user", "content": question})
        response = self._client.chat.completions.create(
            model=CONFIG.chat_model,
            messages=self._history,
            temperature=CONFIG.chat_temperature,
        )
        reply = response.choices[0].message.content
        self._history.append({"role": "assistant", "content": reply})
        print(f"\n{reply}\n")
        return reply

    def reset(self) -> None:
        system = self._history[0]
        self._history = [system]
        print("Conversation reset.")
