# optimizer.py
# 効用理論ベースの最適化
# - B案（順位パーセンタイル）による優先度ボーナス
# - 貯蓄効用を全アイテム効用合計に対する比率で表現
# - ペット保険・車保険の依存制約

from ortools.sat.python import cp_model


def _calc_priority_weights(candidates: list[dict]) -> list[float]:
    """
    B案：順位パーセンタイルによる優先度ボーナス
    priority=0のアイテムは呼び出し前に除外済み
    同じpriority値 → 同じweight
    全員同じpriority → 全員1.5倍（均等扱い）
    """
    priorities = [
        item.get("priority", 1)
        for item in candidates
        if item.get("category") != "_savings"
    ]
    unique_p = sorted(set(priorities))
    n_unique = len(unique_p)

    weights_out = []
    for item in candidates:
        if item.get("category") == "_savings":
            weights_out.append(1.0)
            continue
        p    = item.get("priority", 1)
        rank = unique_p.index(p)
        if n_unique == 1:
            w = 1.5
        else:
            # rank=0(最高優先) → 2.0倍, rank=n_unique-1(最低優先) → 1.0倍
            w = 2.0 - (rank / (n_unique - 1)) * 1.0
        weights_out.append(w)
    return weights_out


def _base_utility(item: dict, weights: dict) -> int:
    """
    アイテムの基本効用（整数）
    health: -10〜10 → +10オフセットで0〜20に変換
    100倍して整数化（OR-Tools用）
    """
    return (
        weights["time"]         * int(item["time"])               * 100 +
        weights["health"]       * (int(item["health"]) + 10)      * 100 +
        weights["satisfaction"] * int(item["satisfaction"])       * 100
    )


def run_optimizer(
    items: list[dict],
    total_budget: int,
    monthly_budget: int,
    target_monthly_savings: int,
    weights: dict,
) -> dict:
    """
    items: [
        {
            "name": str,
            "initial_cost": int,
            "monthly_cost": int,
            "time": int,           # 1〜10
            "health": int,         # -10〜10
            "satisfaction": int,   # 1〜10
            "priority": int,       # 0=対象外, 1以上=候補
            "mandatory": bool,
            "category": str,
        }
    ]
    weights: {"time": int, "health": int, "satisfaction": int, "savings": int}
    """

    # 候補アイテム抽出（priority>0 または mandatory）
    candidates = [
        item for item in items
        if item.get("priority", 0) > 0 or item.get("mandatory", False)
    ]

    if not candidates:
        return _no_solution(monthly_budget, target_monthly_savings)

    n = len(candidates)

    # 優先度ボーナス（100倍して整数化）
    priority_weights_float = _calc_priority_weights(candidates)
    priority_weights_int   = [int(w * 100) for w in priority_weights_float]

    # 基本効用（整数）
    base_utils = [_base_utility(item, weights) for item in candidates]

    # 最終効用 = 基本効用 × 優先度ボーナス / 100（整数演算）
    utilities = [
        (base_utils[i] * priority_weights_int[i]) // 100
        for i in range(n)
    ]

    # ── OR-Toolsモデル ────────────────────────────────
    model = cp_model.CpModel()
    x     = [model.NewBoolVar(f"x_{i}") for i in range(n)]

    # 必須アイテムを固定
    for i, item in enumerate(candidates):
        if item.get("mandatory", False):
            model.Add(x[i] == 1)

    # 制約1：初期費用合計 ≤ 総予算
    model.Add(
        sum(x[i] * candidates[i]["initial_cost"] for i in range(n)) <= total_budget
    )

    # 制約2：月次費用合計 ≤ 月次予算
    model.Add(
        sum(x[i] * candidates[i]["monthly_cost"] for i in range(n)) <= monthly_budget
    )

    # 制約3：移動手段は最低1つ・最大1つ（パッケージ）
    transport_idx = [
        i for i, item in enumerate(candidates)
        if item.get("category") == "transport"
    ]
    if transport_idx:
        model.Add(sum(x[i] for i in transport_idx) >= 1)
        model.Add(sum(x[i] for i in transport_idx) <= 1)

    # 制約4：ペット保険はペットが選ばれた場合のみ
    pet_idx = [
        i for i, item in enumerate(candidates)
        if item.get("name", "") in ("ペット", "Pet")
        and item.get("category") == "wellness"
    ]
    pet_insurance_idx = [
        i for i, item in enumerate(candidates)
        if item.get("name", "") in ("ペット保険", "Pet Insurance")
    ]
    if pet_insurance_idx:
        if pet_idx:
            for pi in pet_insurance_idx:
                model.Add(x[pi] <= sum(x[i] for i in pet_idx))
        else:
            for pi in pet_insurance_idx:
                model.Add(x[pi] == 0)

    # 制約5：車保険は「車メイン」が選ばれた場合のみ
    car_primary_idx = [
        i for i, item in enumerate(candidates)
        if item.get("name", "") in ("車メイン", "Car (Primary)")
    ]
    car_insurance_idx = [
        i for i, item in enumerate(candidates)
        if item.get("name", "") in ("車保険", "Car Insurance")
    ]
    if car_insurance_idx:
        if car_primary_idx:
            for ci in car_insurance_idx:
                model.Add(x[ci] <= sum(x[i] for i in car_primary_idx))
        else:
            for ci in car_insurance_idx:
                model.Add(x[ci] == 0)

    # ── 目的関数 ──────────────────────────────────────
    # アイテム効用合計
    items_value = sum(x[i] * utilities[i] for i in range(n))

    # 実際の月次貯蓄
    total_monthly_cost_var = model.NewIntVar(0, monthly_budget, "total_monthly_cost")
    model.Add(
        total_monthly_cost_var == sum(
            x[i] * candidates[i]["monthly_cost"] for i in range(n)
        )
    )
    actual_savings_var = model.NewIntVar(0, monthly_budget, "actual_savings")
    model.Add(actual_savings_var == monthly_budget - total_monthly_cost_var)

    # 貯蓄効用の設計：
    # 全アイテム効用合計(total_max_utility)に対する比率で表現
    # w_savings=10かつ全額節約 → 全アイテム選択時と同等の効用
    # w_savings=5  → 全アイテムの50%
    # w_savings=1  → 全アイテムの10%
    total_max_utility = sum(utilities)
    savings_coefficient = (
        total_max_utility * weights["savings"]
    ) // (10 * max(monthly_budget, 1))

    savings_value = model.NewIntVar(
        0, monthly_budget * savings_coefficient + 1, "savings_value"
    )
    model.Add(savings_value == actual_savings_var * savings_coefficient)

    # 目的関数：アイテム効用 + 貯蓄効用
    model.Maximize(items_value + savings_value)

    # ── ソルバー実行 ──────────────────────────────────
    solver = cp_model.CpSolver()
    status = solver.Solve(model)

    if status in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        selected       = [candidates[i] for i in range(n) if solver.Value(x[i]) == 1]
        total_initial  = sum(item["initial_cost"] for item in selected)
        total_monthly  = sum(item["monthly_cost"]  for item in selected)
        actual_savings = monthly_budget - total_monthly
        savings_rate   = (
            min(actual_savings / target_monthly_savings, 1.0)
            if target_monthly_savings > 0 else 1.0
        )

        return {
            "status":                "ok",
            "selected":              selected,
            "total_initial_cost":    total_initial,
            "total_monthly_cost":    total_monthly,
            "actual_monthly_savings":actual_savings,
            "target_monthly_savings":target_monthly_savings,
            "savings_rate":          savings_rate,
            "savings_shortfall":     max(target_monthly_savings - actual_savings, 0),
            "total_value":           solver.ObjectiveValue(),
        }
    else:
        return _no_solution(monthly_budget, target_monthly_savings)


def _no_solution(monthly_budget: int, target_monthly_savings: int) -> dict:
    return {
        "status":                "no_solution",
        "selected":              [],
        "total_initial_cost":    0,
        "total_monthly_cost":    0,
        "actual_monthly_savings":monthly_budget,
        "target_monthly_savings":target_monthly_savings,
        "savings_rate":          1.0 if target_monthly_savings == 0 else 0.0,
        "savings_shortfall":     target_monthly_savings,
        "total_value":           0,
    }


# ── 動作確認用 ────────────────────────────────────────
if __name__ == "__main__":
    items = [
        {"name": "車メイン",   "category": "transport",    "initial_cost": 25000, "monthly_cost": 650, "time": 8, "health": 2,  "satisfaction": 8, "priority": 3, "mandatory": False},
        {"name": "自転車のみ", "category": "transport",    "initial_cost": 500,   "monthly_cost": 10,  "time": 3, "health": 8,  "satisfaction": 6, "priority": 1, "mandatory": False},
        {"name": "ジム",       "category": "health",       "initial_cost": 100,   "monthly_cost": 50,  "time": 1, "health": 9,  "satisfaction": 6, "priority": 1, "mandatory": False},
        {"name": "ヨガ",       "category": "health",       "initial_cost": 50,    "monthly_cost": 30,  "time": 1, "health": 8,  "satisfaction": 8, "priority": 2, "mandatory": False},
        {"name": "Netflix",    "category": "entertainment","initial_cost": 0,     "monthly_cost": 18,  "time": 0, "health": 0,  "satisfaction": 7, "priority": 2, "mandatory": False},
        {"name": "Spotify",    "category": "entertainment","initial_cost": 0,     "monthly_cost": 11,  "time": 0, "health": 0,  "satisfaction": 7, "priority": 1, "mandatory": False},
        {"name": "外食",       "category": "food",         "initial_cost": 0,     "monthly_cost": 150, "time": 3, "health": 2,  "satisfaction": 7, "priority": 2, "mandatory": False},
        {"name": "旅行積立",   "category": "wellness",     "initial_cost": 0,     "monthly_cost": 150, "time": 0, "health": 3,  "satisfaction": 9, "priority": 1, "mandatory": False},
        {"name": "ペット",     "category": "wellness",     "initial_cost": 500,   "monthly_cost": 100, "time": 0, "health": 5,  "satisfaction": 9, "priority": 2, "mandatory": False},
        {"name": "ペット保険", "category": "insurance",    "initial_cost": 0,     "monthly_cost": 40,  "time": 0, "health": 2,  "satisfaction": 6, "priority": 3, "mandatory": False},
        {"name": "車保険",     "category": "insurance",    "initial_cost": 0,     "monthly_cost": 120, "time": 0, "health": 2,  "satisfaction": 6, "priority": 2, "mandatory": False},
        {"name": "賃貸保険",   "category": "insurance",    "initial_cost": 0,     "monthly_cost": 20,  "time": 0, "health": 2,  "satisfaction": 6, "priority": 1, "mandatory": False},
    ]

    print("=== テスト1: 貯蓄重視(w_savings=8) ===")
    result = run_optimizer(
        items=items,
        total_budget=5000,
        monthly_budget=1470,
        target_monthly_savings=667,  # 8000/12ヶ月
        weights={"time": 2, "health": 8, "satisfaction": 6, "savings": 8},
    )
    print("選ばれたアイテム:", [item["name"] for item in result["selected"]])
    print("月次費用合計:    $", result["total_monthly_cost"])
    print("実際の月次貯蓄: $", result["actual_monthly_savings"])
    print("目標達成率:      ", f"{result['savings_rate']:.0%}")
    print()

    print("=== テスト2: 満足度重視(w_savings=1) ===")
    result2 = run_optimizer(
        items=items,
        total_budget=5000,
        monthly_budget=1470,
        target_monthly_savings=667,
        weights={"time": 2, "health": 8, "satisfaction": 6, "savings": 1},
    )
    print("選ばれたアイテム:", [item["name"] for item in result2["selected"]])
    print("月次費用合計:    $", result2["total_monthly_cost"])
    print("実際の月次貯蓄: $", result2["actual_monthly_savings"])
    print("目標達成率:      ", f"{result2['savings_rate']:.0%}")