CRISIS_KEYWORDS = [
    "自杀", "自残", "不想活", "想死", "活不下去",
    "伤害自己", "伤害别人", "结束生命", "轻生",
]

CRISIS_HOTLINES: list[dict] = [
    {"name": "全国心理援助热线", "phone": "400-161-9995", "region": "全国"},
    {"name": "北京心理危机研究与干预中心", "phone": "010-82951332", "region": "北京"},
    {"name": "上海心理援助热线", "phone": "021-12320-5", "region": "上海"},
    {"name": "生命热线 (希望24)", "phone": "400-161-9995", "region": "全国 24h"},
    {"name": "杭州心理危机干预热线", "phone": "0571-85029595", "region": "浙江 24h"},
]


def crisis_check(text: str) -> dict:
    matched = []
    for kw in CRISIS_KEYWORDS:
        if kw in text:
            matched.append(kw)

    if not matched:
        return {
            "is_crisis": False,
            "severity": "none",
            "matched_keywords": [],
            "hotlines": [],
        }

    # Severity by keyword count or specific high-risk keywords
    high_risk = {"自杀", "自残", "想死", "轻生", "结束生命"}
    severity = "high" if any(kw in high_risk for kw in matched) else "medium"

    return {
        "is_crisis": True,
        "severity": severity,
        "matched_keywords": matched,
        "hotlines": CRISIS_HOTLINES,
    }
