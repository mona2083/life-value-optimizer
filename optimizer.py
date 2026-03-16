# optimizer.py
# OR-Toolsを使った0-1ナップサック問題（4価値軸・2制約）

from ortools.sat.python import cp_model

def run_optimizer(
    items: list[dict],
    total_budget: int,       # 初期費用の上限（$）
    monthly_budget: int,     # 月次費用の上限（$）
    target_monthly_savings: int,  # 目標月次貯蓄額（$）
    weights: dict,           # {"time": int, "health": int, "satisfaction": int, "savings": int}
) -> dict:
    """
    items: [
        {
            "name": str,
            "initial_cost": int,   # 初期費用（$）
            "monthly_cost": int,   # 月次費用（$）
            "time": int,           # 時間節約スコア（1〜10）
            "health": int,         # 健康スコア（1〜10）
            "satisfaction": int,   # 満足度スコア（1〜10）
        }
    ]
    """

    model = cp_model.CpModel()
    n = len(items)

    # 意思決定変数：各アイテムを買う(1) or 買わない(0)
    x = [model.NewBoolVar(f"x_{i}") for i in range(n)]

    # 制約1：初期費用の合計 ≤ 総予算
    model.Add(
        sum(x[i] * items[i]["initial_cost"] for i in range(n)) <= total_budget
    )

    # 制約2：月次費用の合計 ≤ 月次予算
    model.Add(
        sum(x[i] * items[i]["monthly_cost"] for i in range(n)) <= monthly_budget
    )

    # 貯蓄スコアの計算
    # OR-Toolsは整数のみ扱えるため100倍して整数化し、最後に戻す
    # 実際の月次貯蓄 = monthly_budget - 月次費用合計
    # 貯蓄スコア = min(実際の月次貯蓄 / 目標月次貯蓄, 1.0) → 0〜100の整数で扱う

    # 月次費用の合計（変数）
    total_monthly_cost = sum(x[i] * items[i]["monthly_cost"] for i in range(n))
    actual_savings = monthly_budget - total_monthly_cost

    # 貯蓄スコアを0〜100の整数で表現
    # target_monthly_savingsが0の場合のゼロ除算を防ぐ
    if target_monthly_savings > 0:
        # 貯蓄スコア × 100 = min(actual_savings × 100 / target, 100)
        # OR-Toolsで上限を設けるためにAddMinEquality使用
        raw_savings_score = model.NewIntVar(0, 100, "raw_savings_score")
        scaled_savings = model.NewIntVar(0, monthly_budget * 100, "scaled_savings")
        model.Add(scaled_savings == actual_savings * 100)

        # scaled_savings / target_monthly_savings を整数で近似
        savings_score_uncapped = model.NewIntVar(0, monthly_budget * 100 // target_monthly_savings + 1, "savings_score_uncapped")
        model.AddDivisionEquality(savings_score_uncapped, scaled_savings, target_monthly_savings)

        # 上限100で頭打ち
        model.AddMinEquality(raw_savings_score, [savings_score_uncapped, model.NewConstant(100)])
    else:
        # 目標貯蓄額が0の場合、貯蓄スコアは常に最大
        raw_savings_score = model.NewConstant(100)

    # 目的関数：4軸の重み付きスコアを最大化
    # 貯蓄スコアはすでに0〜100スケール、他のスコアは1〜10なので10倍して統一
    model.Maximize(
        sum(
            x[i] * (
                weights["time"]         * items[i]["time"]         * 10 +
                weights["health"]       * items[i]["health"]       * 10 +
                weights["satisfaction"] * items[i]["satisfaction"] * 10
            )
            for i in range(n)
        )
        + weights["savings"] * raw_savings_score
    )

    solver = cp_model.CpSolver()
    status = solver.Solve(model)

    if status in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        selected = [items[i] for i in range(n) if solver.Value(x[i]) == 1]
        total_initial  = sum(item["initial_cost"] for item in selected)
        total_monthly  = sum(item["monthly_cost"]  for item in selected)
        actual_monthly_savings = monthly_budget - total_monthly
        savings_rate   = min(actual_monthly_savings / target_monthly_savings, 1.0) \
                         if target_monthly_savings > 0 else 1.0

        return {
            "status": "ok",
            "selected": selected,
            "total_initial_cost":      total_initial,
            "total_monthly_cost":      total_monthly,
            "actual_monthly_savings":  actual_monthly_savings,
            "target_monthly_savings":  target_monthly_savings,
            "savings_rate":            savings_rate,          # 0〜1
            "savings_shortfall":       max(target_monthly_savings - actual_monthly_savings, 0),
            "total_value":             solver.ObjectiveValue(),
        }
    else:
        return {
            "status": "no_solution",
            "selected": [],
            "total_initial_cost": 0,
            "total_monthly_cost": 0,
            "actual_monthly_savings": monthly_budget,
            "target_monthly_savings": target_monthly_savings,
            "savings_rate": 1.0 if target_monthly_savings == 0 else 0.0,
            "savings_shortfall": target_monthly_savings,
            "total_value": 0,
        }


# ── 動作確認用 ────────────────────────────────────────
if __name__ == "__main__":
    items = [
        {"name": "車",      "initial_cost": 30000, "monthly_cost": 500, "time": 8, "health": 2, "satisfaction": 7},
        {"name": "自転車",  "initial_cost": 500,   "monthly_cost": 0,   "time": 3, "health": 8, "satisfaction": 6},
        {"name": "ジム",    "initial_cost": 100,   "monthly_cost": 50,  "time": 1, "health": 9, "satisfaction": 5},
        {"name": "Netflix", "initial_cost": 0,     "monthly_cost": 18,  "time": 0, "health": 0, "satisfaction": 4},
    ]

    result = run_optimizer(
        items=items,
        total_budget=2000,
        monthly_budget=200,
        target_monthly_savings=100,
        weights={"time": 3, "health": 5, "satisfaction": 2, "savings": 4},
    )

    print("選ばれたアイテム:", [item["name"] for item in result["selected"]])
    print("初期費用合計:    $", result["total_initial_cost"])
    print("月次費用合計:    $", result["total_monthly_cost"])
    print("実際の月次貯蓄: $", result["actual_monthly_savings"])
    print("目標達成率:      ", f"{result['savings_rate']:.0%}")
    print("貯蓄不足額:     $", result["savings_shortfall"])
    print("合計バリュー:    ", result["total_value"])