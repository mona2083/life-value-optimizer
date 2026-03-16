# lifestyle.py

DIET_ADJUSTMENT = {
    "ja": {
        "健康志向":       {"cost": 100,  "health": 2},
        "標準":           {"cost": 0,    "health": 0},
        "ファストフード": {"cost": -50,  "health": -3},
        "外食多め":       {"cost": 150,  "health": -1},
    },
    "en": {
        "Health-conscious": {"cost": 100,  "health": 2},
        "Standard":         {"cost": 0,    "health": 0},
        "Fast Food":        {"cost": -50,  "health": -3},
        "Eat Out Often":    {"cost": 150,  "health": -1},
    }
}

EXERCISE_HEALTH_ADJUSTMENT = {
    "ja": {"週5以上": 2, "週2〜4": 1, "週1以下": 0},
    "en": {"5+ days/week": 2, "2-4 days/week": 1, "1 or less/week": 0},
}

SMOKING_HEALTH_ADJUSTMENT = {
    "ja": {
        "なし":                   0,
        "ライト（1日1〜5本）":   -2,
        "ミディアム（1日6〜15本）": -4,
        "ヘビー（1日16本以上）": -6,
    },
    "en": {
        "None":              0,
        "Light (1-5/day)":  -2,
        "Medium (6-15/day)":-4,
        "Heavy (16+/day)":  -6,
    }
}

ALCOHOL_HEALTH_ADJUSTMENT = {
    "ja": {
        "ほぼ飲まない": 0,
        "週1〜2杯":    -1,
        "週3〜5杯":    -2,
        "毎日":        -4,
    },
    "en": {
        "Rarely":           0,
        "1-2 times/week":  -1,
        "3-5 times/week":  -2,
        "Daily":           -4,
    }
}

INCOME_REASON_OPTIONS = {
    "ja": ["学校卒業", "資格取得", "転職", "昇給", "その他"],
    "en": ["School Graduation", "Certification", "Job Change", "Promotion", "Other"],
}

# ライフスタイルに応じて優先度を0にするアイテム名
EXCLUDE_IF_NO_SMOKING = {"タバコ/Vape", "Tobacco / Vape"}
EXCLUDE_IF_NO_ALCOHOL  = {"お酒", "Alcohol"}


def calculate_lifestyle_adjustments(lifestyle: dict, lang: str) -> dict:
    diet_data    = DIET_ADJUSTMENT[lang].get(lifestyle.get("diet", ""), {"cost": 0, "health": 0})
    diet_adj     = diet_data["cost"]
    diet_health  = diet_data["health"]
    exercise_adj = EXERCISE_HEALTH_ADJUSTMENT[lang].get(lifestyle.get("exercise", ""), 0)
    smoking_adj  = SMOKING_HEALTH_ADJUSTMENT[lang].get(lifestyle.get("smoking", ""), 0)
    alcohol_adj  = ALCOHOL_HEALTH_ADJUSTMENT[lang].get(lifestyle.get("alcohol", ""), 0)
    health_adj   = diet_health + exercise_adj + smoking_adj + alcohol_adj

    income_increase = lifestyle.get("income_increase", 0)
    income_years    = lifestyle.get("income_years", 0)
    horizon_years   = lifestyle.get("horizon_years", 1)
    income_reason   = lifestyle.get("income_reason", "")
    current_budget  = lifestyle.get("monthly_budget", 0)
    savings_years = lifestyle.get("savings_years", 99) 

    if income_increase > 0 and income_years <= savings_years:
        future_budget = current_budget + income_increase
        if lang == "ja":
            future_note = f"※{income_years}年後に月+${income_increase:,}の収入増を見込んでいます（理由：{income_reason}）"
        else:
            future_note = f"※ Projected income increase of +${income_increase:,}/month in {income_years} year(s) ({income_reason})"
    else:
        future_budget = current_budget
        future_note   = ""

    # 自動除外アイテム名のセット
    exclude_names = set()
    smoking = lifestyle.get("smoking", "")
    alcohol  = lifestyle.get("alcohol", "")
    if smoking in ["なし", "None"]:
        exclude_names |= EXCLUDE_IF_NO_SMOKING
    if alcohol in ["ほぼ飲まない", "Rarely"]:
        exclude_names |= EXCLUDE_IF_NO_ALCOHOL

    return {
        "diet_cost_adjustment":    diet_adj,
        "health_score_adjustment": health_adj,
        "future_monthly_budget":   future_budget,
        "future_note":             future_note,
        "exclude_names":           exclude_names,
    }