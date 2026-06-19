CRISIS_KEYWORDS = [
    "自杀", "自残", "不想活", "想死", "活不下去",
    "伤害自己", "伤害别人", "结束生命", "轻生",
]


def crisis_check(text: str) -> dict:
    matched = []
    for kw in CRISIS_KEYWORDS:
        if kw in text:
            matched.append(kw)

    if not matched:
        return {"is_crisis": False, "severity": "none", "matched_keywords": []}

    # Severity by keyword count or specific high-risk keywords
    high_risk = {"自杀", "自残", "想死", "轻生", "结束生命"}
    severity = "high" if any(kw in high_risk for kw in matched) else "medium"

    return {
        "is_crisis": True,
        "severity": severity,
        "matched_keywords": matched,
    }
