# sensitivity.py
# 感度分析ロジック：月次予算・初期費用上限を変化させて結果を収集

import numpy as np
import plotly.graph_objects as go
from optimizer import run_optimizer


def run_sensitivity(
    items: list[dict],
    monthly_budget: int,
    total_budget: int,
    target_monthly_savings: int,
    weights: dict,
    steps: int = 20,
) -> dict:
    """
    月次予算・初期費用上限をそれぞれ50%〜200%の範囲で変化させ、
    各ステップの最適化結果を収集する
    """

    monthly_range = np.linspace(monthly_budget * 0.5, monthly_budget * 2.0, steps).astype(int)
    initial_range = np.linspace(total_budget   * 0.5, total_budget   * 2.0, steps).astype(int)

    # 月次予算の感度分析（初期費用上限は固定）
    monthly_values  = []
    monthly_selections = {item["name"]: [] for item in items}

    for mb in monthly_range:
        result = run_optimizer(items, total_budget, int(mb), target_monthly_savings, weights)
        monthly_values.append(result["total_value"])
        selected_names = {item["name"] for item in result["selected"]}
        for item in items:
            monthly_selections[item["name"]].append(1 if item["name"] in selected_names else 0)

    # 初期費用上限の感度分析（月次予算は固定）
    initial_values  = []
    initial_selections = {item["name"]: [] for item in items}

    for ib in initial_range:
        result = run_optimizer(items, int(ib), monthly_budget, target_monthly_savings, weights)
        initial_values.append(result["total_value"])
        selected_names = {item["name"] for item in result["selected"]}
        for item in items:
            initial_selections[item["name"]].append(1 if item["name"] in selected_names else 0)

    return {
        "monthly_range":      monthly_range,
        "monthly_values":     monthly_values,
        "monthly_selections": monthly_selections,
        "initial_range":      initial_range,
        "initial_values":     initial_values,
        "initial_selections": initial_selections,
    }


def make_line_chart(x_values, y_values, current_x: int, x_label: str, y_label: str, title: str) -> go.Figure:
    """折れ線グラフ：予算 vs 合計バリュー"""
    fig = go.Figure()

    fig.add_trace(go.Scatter(
        x=x_values,
        y=y_values,
        mode="lines+markers",
        name=y_label,
        line=dict(color="#4F8EF7", width=2),
    ))

    # 現在の設定を縦線で表示
    fig.add_vline(
        x=current_x,
        line_dash="dash",
        line_color="orange",
        annotation_text=f"Current: ${current_x:,}",
        annotation_position="top right",
    )

    fig.update_layout(
        title=title,
        xaxis_title=x_label,
        yaxis_title=y_label,
        height=350,
        margin=dict(t=50, b=40),
    )
    return fig


def make_heatmap(x_values, selections: dict, current_x: int, x_label: str, title: str) -> go.Figure:
    """ヒートマップ：予算ごとのアイテム選択"""
    item_names = list(selections.keys())
    z = [selections[name] for name in item_names]

    fig = go.Figure(go.Heatmap(
        x=x_values,
        y=item_names,
        z=z,
        colorscale=[[0, "#EEEEEE"], [1, "#4F8EF7"]],
        showscale=False,
        zmin=0,
        zmax=1,
    ))

    # 現在の設定を縦線で表示
    fig.add_vline(
        x=current_x,
        line_dash="dash",
        line_color="orange",
    )

    fig.update_layout(
        title=title,
        xaxis_title=x_label,
        yaxis_title="",
        height=300,
        margin=dict(t=50, b=40),
    )
    return fig

def get_recommendations(
    items: list[dict],
    result: dict,
    sens: dict,
    monthly_budget: int,
    total_budget: int,
) -> dict:
    """
    感度分析データと最適化結果から推奨アクションを生成する
    """
    current_selected = {item["name"] for item in result["selected"]}
    unselected = [item for item in items if item["name"] not in current_selected]

    remaining_monthly = monthly_budget - result["total_monthly_cost"]
    remaining_initial = total_budget  - result["total_initial_cost"]

    # 今すぐ追加できるアイテム（残余予算で賄えるもの）
    can_add_now = [
        item for item in unselected
        if item["monthly_cost"] <= remaining_monthly
        and item["initial_cost"] <= remaining_initial
    ]

    # 感度分析から「あといくら増やせば追加できるか」を検出
    budget_increase = []
    seen = set()

    for i, mb in enumerate(sens["monthly_range"]):
        if mb <= monthly_budget:
            continue  # 現在値より低い予算はスキップ
        for item in items:
            name = item["name"]
            if name in current_selected or name in seen:
                continue
            if sens["monthly_selections"][name][i] == 1:
                budget_increase.append({
                    "item":     name,
                    "increase": int(mb - monthly_budget),
                })
                seen.add(name)

    return {"can_add_now": can_add_now, "budget_increase": budget_increase}