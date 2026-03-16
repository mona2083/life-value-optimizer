# app.py
import streamlit as st
import pandas as pd
from optimizer import run_optimizer
from sensitivity import run_sensitivity, make_line_chart, make_heatmap, get_recommendations
from llm import get_item_defaults, get_result_summary
from lang import LANG, PRESETS

# ── 言語選択（サイドバー最上部）────────────────────
with st.sidebar:
    lang_choice = st.radio("🌐 Language / 言語", ["日本語", "English"], horizontal=True)
    lang = "ja" if lang_choice == "日本語" else "en"

T = LANG[lang]

# ── タイトル ─────────────────────────────────────
st.title(T["title"])
st.caption(T["caption"])

# ── Step 1: ユーザー属性 ─────────────────────────
st.header(T["step1"])

col1, col2, col3 = st.columns(3)
with col1:
    age = st.number_input(T["age"], min_value=18, max_value=100, value=42)
with col2:
    gender = st.selectbox(T["gender"], T["gender_options"])
with col3:
    family = st.selectbox(T["family"], T["family_options"])

col4, col5 = st.columns(2)
with col4:
    horizon_years = st.selectbox(T["horizon"], [1, 5, 10, 20, 50], index=1)
with col5:
    monthly_budget = st.number_input(T["monthly_budget"], min_value=0, value=500, step=50)

total_budget = st.number_input(
    T["total_budget"],
    min_value=0,
    value=5000,
    step=500,
    help=T["total_budget_help"],
)

st.divider()

# ── Step 2: 目標設定 ─────────────────────────────
st.header(T["step2"])

col6, col7 = st.columns(2)
with col6:
    savings_goal = st.number_input(T["savings_goal"], min_value=0, value=1200, step=100)
with col7:
    savings_period_years = st.selectbox(T["savings_period"], [1, 5, 10, 20, 50], index=0)

target_monthly_savings = int(savings_goal / (savings_period_years * 12))
st.caption(T["monthly_savings_cap"].format(target_monthly_savings))

st.subheader(T["priority"])

goal_preset = st.radio(T["goal_type"], T["goal_options"], horizontal=True)
preset = PRESETS[lang][goal_preset]

col8, col9, col10, col11 = st.columns(4)
with col8:
    w_time = st.slider(T["w_time"], 1, 10, preset["time"])
with col9:
    w_health = st.slider(T["w_health"], 1, 10, preset["health"])
with col10:
    w_satisfaction = st.slider(T["w_satisfaction"], 1, 10, preset["satisfaction"])
with col11:
    w_savings = st.slider(T["w_savings"], 1, 10, preset["savings"])

st.divider()

# ── Step 3: アイテム入力 ─────────────────────────
st.header(T["step3"])

# session_stateでdata_editorのデータを管理（AI補完で行追加するため）
if "items_df" not in st.session_state:
    st.session_state.items_df = pd.DataFrame([
        {T["col_name"]: "車",      T["col_initial"]: 30000, T["col_monthly"]: 500, T["col_time"]: 8, T["col_health"]: 2, T["col_satisfaction"]: 7},
        {T["col_name"]: "自転車",  T["col_initial"]: 500,   T["col_monthly"]: 0,   T["col_time"]: 3, T["col_health"]: 8, T["col_satisfaction"]: 6},
        {T["col_name"]: "ジム",    T["col_initial"]: 100,   T["col_monthly"]: 50,  T["col_time"]: 1, T["col_health"]: 9, T["col_satisfaction"]: 5},
        {T["col_name"]: "Netflix", T["col_initial"]: 0,     T["col_monthly"]: 18,  T["col_time"]: 0, T["col_health"]: 0, T["col_satisfaction"]: 4},
    ])

# LLM補完UI
col_ai1, col_ai2 = st.columns([3, 1])
with col_ai1:
    ai_item_name = st.text_input(
        T["ai_item_placeholder"],
        label_visibility="collapsed",
        placeholder=T["ai_item_placeholder"],
    )
with col_ai2:
    if st.button(T["ai_complete_button"]) and ai_item_name:
        with st.spinner("AI..."):
            defaults = get_item_defaults(ai_item_name, lang)
        if defaults:
            new_row = pd.DataFrame([{
                T["col_name"]:         ai_item_name,
                T["col_initial"]:      defaults.get("initial_cost", 0),
                T["col_monthly"]:      defaults.get("monthly_cost", 0),
                T["col_time"]:         defaults.get("time", 5),
                T["col_health"]:       defaults.get("health", 5),
                T["col_satisfaction"]: defaults.get("satisfaction", 5),
            }])
            st.session_state.items_df = pd.concat(
                [st.session_state.items_df, new_row], ignore_index=True
            )
        else:
            st.warning(T["ai_error_complete"])

edited_df = st.data_editor(
    st.session_state.items_df,
    num_rows="dynamic",
    use_container_width=True,
    key="main_data_editor",
)

st.divider()

# ── 最適化実行 ───────────────────────────────────
if st.button(T["run_button"], type="primary"):

    items = [
        {
            "name":         row[T["col_name"]],
            "initial_cost": int(row[T["col_initial"]]),
            "monthly_cost": int(row[T["col_monthly"]]),
            "time":         int(row[T["col_time"]]),
            "health":       int(row[T["col_health"]]),
            "satisfaction": int(row[T["col_satisfaction"]]),
        }
        for _, row in edited_df.iterrows()
        if row[T["col_name"]]
    ]

    weights = {
        "time":         w_time,
        "health":       w_health,
        "satisfaction": w_satisfaction,
        "savings":      w_savings,
    }

    result = run_optimizer(
        items=items,
        total_budget=int(total_budget),
        monthly_budget=int(monthly_budget),
        target_monthly_savings=target_monthly_savings,
        weights=weights,
    )

    if result["status"] == "ok":
        st.success(T["result_ok"])

        # AIサマリー
        with st.spinner("AI..."):
            summary = get_result_summary(
                result=result,
                user_profile={"age": age, "family": family},
                weights=weights,
                lang=lang,
            )
        if summary:
            st.info(f"{T['ai_summary_title']}\n\n{summary}")
        else:
            st.caption(T["ai_error_summary"])

        # メトリクス
        col12, col13, col14, col15 = st.columns(4)
        col12.metric(T["total_initial"],  f"${result['total_initial_cost']:,}")
        col13.metric(T["total_monthly"],  f"${result['total_monthly_cost']:,}")
        col14.metric(T["actual_savings"], f"${result['actual_monthly_savings']:,}")
        col15.metric(T["savings_rate"],   f"{result['savings_rate']:.0%}")

        if result["savings_shortfall"] > 0:
            st.warning(T["shortfall_warn"].format(result["savings_shortfall"]))

        # 感度分析（get_recommendationsより先に実行）
        with st.spinner("Analyzing..."):
            sens = run_sensitivity(
                items=items,
                monthly_budget=int(monthly_budget),
                total_budget=int(total_budget),
                target_monthly_savings=target_monthly_savings,
                weights=weights,
            )

        # 選ばれたアイテム一覧
        st.subheader(T["selected_items"])
        selected_df = pd.DataFrame(result["selected"]).rename(columns={
            "name":         T["col_name"],
            "initial_cost": T["col_initial"],
            "monthly_cost": T["col_monthly"],
            "time":         T["col_time"],
            "health":       T["col_health"],
            "satisfaction": T["col_satisfaction"],
        })
        st.dataframe(selected_df, use_container_width=True)

        # 推奨アクション
        recs = get_recommendations(
            items=items,
            result=result,
            sens=sens,
            monthly_budget=int(monthly_budget),
            total_budget=int(total_budget),
        )

        if recs["can_add_now"] or recs["budget_increase"]:
            st.subheader(T["rec_title"])
            for item in recs["can_add_now"]:
                st.success(T["rec_can_add"].format(
                    item["name"], item["initial_cost"], item["monthly_cost"]
                ))
            for rec in recs["budget_increase"]:
                st.info(T["rec_budget_up"].format(rec["increase"], rec["item"]))

        # 感度分析グラフ
        st.header(T["sensitivity_title"])
        tab_m, tab_i = st.tabs([T["tab_monthly"], T["tab_initial"]])

        with tab_m:
            st.plotly_chart(make_line_chart(
                sens["monthly_range"], sens["monthly_values"],
                int(monthly_budget),
                T["chart_monthly_x"], T["chart_value"], T["chart_line_title_m"],
            ), use_container_width=True)
            st.plotly_chart(make_heatmap(
                sens["monthly_range"], sens["monthly_selections"],
                int(monthly_budget),
                T["chart_monthly_x"], T["chart_heat_title_m"],
            ), use_container_width=True)

        with tab_i:
            st.plotly_chart(make_line_chart(
                sens["initial_range"], sens["initial_values"],
                int(total_budget),
                T["chart_initial_x"], T["chart_value"], T["chart_line_title_i"],
            ), use_container_width=True)
            st.plotly_chart(make_heatmap(
                sens["initial_range"], sens["initial_selections"],
                int(total_budget),
                T["chart_initial_x"], T["chart_heat_title_i"],
            ), use_container_width=True)

    else:
        st.error(T["result_ng"])