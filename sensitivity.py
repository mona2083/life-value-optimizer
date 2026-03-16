# sensitivity.py
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
    monthly_range = np.linspace(monthly_budget * 0.5, monthly_budget * 2.0, steps).astype(int)
    initial_range = np.linspace(total_budget   * 0.5, total_budget   * 2.0, steps).astype(int)

    # 候補アイテム名一覧（感度分析のヒートマップ用）
    candidate_names = [item["name"] for item in items
                       if item.get("priority", 0) > 0 or item.get("mandatory", False)]

    monthly_values     = []
    monthly_selections = {name: [] for name in candidate_names}

    for mb in monthly_range:
        result = run_optimizer(items, total_budget, int(mb), target_monthly_savings, weights)
        monthly_values.append(result["total_value"])
        selected_names = {item["name"] for item in result["selected"]}
        for name in candidate_names:
            monthly_selections[name].append(1 if name in selected_names else 0)

    initial_values     = []
    initial_selections = {name: [] for name in candidate_names}

    for ib in initial_range:
        result = run_optimizer(items, int(ib), monthly_budget, target_monthly_savings, weights)
        initial_values.append(result["total_value"])
        selected_names = {item["name"] for item in result["selected"]}
        for name in candidate_names:
            initial_selections[name].append(1 if name in selected_names else 0)

    return {
        "monthly_range":      monthly_range,
        "monthly_values":     monthly_values,
        "monthly_selections": monthly_selections,
        "initial_range":      initial_range,
        "initial_values":     initial_values,
        "initial_selections": initial_selections,
    }


def get_recommendations(
    items: list[dict],
    result: dict,
    sens: dict,
    monthly_budget: int,
    total_budget: int,
) -> dict:
    current_selected = {item["name"] for item in result["selected"]}

    # 候補だが選ばれなかったアイテム
    unselected = [item for item in items
                  if item["name"] not in current_selected
                  and (item.get("priority", 0) > 0)
                  and not item.get("mandatory", False)]

    remaining_monthly = monthly_budget - result["total_monthly_cost"]
    remaining_initial = total_budget   - result["total_initial_cost"]

    can_add_now = [
        item for item in unselected
        if item["monthly_cost"] <= remaining_monthly
        and item["initial_cost"] <= remaining_initial
    ]

    budget_increase = []
    seen = set()

    for i, mb in enumerate(sens["monthly_range"]):
        if mb <= monthly_budget:
            continue
        for item in items:
            name = item["name"]
            if name in current_selected or name in seen:
                continue
            if name in sens["monthly_selections"] and sens["monthly_selections"][name][i] == 1:
                budget_increase.append({
                    "item":     name,
                    "increase": int(mb - monthly_budget),
                })
                seen.add(name)

    return {"can_add_now": can_add_now, "budget_increase": budget_increase}


def make_line_chart(x_values, y_values, current_x, x_label, y_label, title):
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=x_values, y=y_values,
        mode="lines+markers",
        line=dict(color="#4F8EF7", width=2),
    ))
    fig.add_vline(
        x=current_x, line_dash="dash", line_color="orange",
        annotation_text=f"Current: ${current_x:,}",
        annotation_position="top right",
    )
    fig.update_layout(title=title, xaxis_title=x_label, yaxis_title=y_label,
                      height=350, margin=dict(t=50, b=40))
    return fig


def make_heatmap(x_values, selections, current_x, x_label, title):
    item_names = list(selections.keys())
    z = [selections[name] for name in item_names]
    fig = go.Figure(go.Heatmap(
        x=x_values, y=item_names, z=z,
        colorscale=[[0, "#EEEEEE"], [1, "#4F8EF7"]],
        showscale=False, zmin=0, zmax=1,
    ))
    fig.add_vline(x=current_x, line_dash="dash", line_color="orange")
    fig.update_layout(title=title, xaxis_title=x_label,
                      height=300, margin=dict(t=50, b=40))
    return fig