# ── Human handoff keywords ──────────────────────────────────────────────

HUMAN_HANDOFF_KEYWORDS = [
    "转人工", "找客服", "人工客服", "联系客服",
    "真人客服", "转接人工", "找人工", "有人吗",
    "客服热线", "联系人工",
]

HUMAN_HANDOFF_MESSAGE = {
    "message": "如需人工协助，请发送邮件至香水AI团队，我们将尽快回复。",
    "contact_email": "support@perfume-ai.example.com",
}


def human_handoff_check(text: str) -> dict | None:
    """Detect explicit human handoff requests. Returns handoff info dict or None."""
    for kw in HUMAN_HANDOFF_KEYWORDS:
        if kw in text:
            return {
                "is_handoff": True,
                "matched_keyword": kw,
                **HUMAN_HANDOFF_MESSAGE,
            }
    return None


CRISIS_KEYWORDS = [
    # High severity — immediate block
    "自杀", "自残", "不想活", "想死", "活不下去",
    "伤害自己", "伤害别人", "结束生命", "轻生",
    "没有意义了", "想消失", "离开这个世界", "死了算了",
    "活着好累", "活够了", "不想活了", "寻死",
    "割腕", "跳楼", "上吊", "安眠药",
    # Medium severity — warn but don't block
    "想不开", "绝望", "撑不下去了",
    "没人需要我", "崩溃", "撑不住",
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
    high_risk = {
        "自杀", "自残", "想死", "轻生", "结束生命",
        "割腕", "跳楼", "上吊", "安眠药", "寻死",
        "死了算了", "离开这个世界", "活够了", "不想活了",
    }
    severity = "high" if any(kw in high_risk for kw in matched) else "medium"

    return {
        "is_crisis": True,
        "severity": severity,
        "matched_keywords": matched,
        "hotlines": CRISIS_HOTLINES,
    }
