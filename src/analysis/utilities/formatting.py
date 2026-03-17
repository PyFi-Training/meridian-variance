def fmt_dollars(value: float) -> str:
    if value >= 0:
        return f"${value:,.0f}"
    return f"(${abs(value):,.0f})"


def fmt_percent(value: float) -> str:
    if value >= 0:
        return f"{value:.1%}"
    return f"({abs(value):.1%})"


def favour_label(is_favourable: bool) -> str:
    return "Favourable" if is_favourable else "Unfavourable"


def severity(variance_pct: float) -> str:
    """Classify variance materiality."""
    abs_pct = abs(variance_pct)
    if abs_pct >= 0.15:
        return "HIGH"
    elif abs_pct >= 0.07:
        return "MEDIUM"
    else:
        return "LOW"
