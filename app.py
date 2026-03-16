# app.py
import streamlit as st
import pandas as pd
from optimizer import run_optimizer
from sensitivity import run_sensitivity, make_line_chart, make_heatmap
from llm import get_item_defaults, get_result_summary
from lang import LANG, PRESETS
from default_items import DEFAULT_ITEMS, CATEGORIES, CATEGORY_CONSTRAINTS
from lifestyle import calculate_lifestyle_adjustments, INCOME_REASON_OPTIONS
from risk_cost import calculate_risk_costs


# ── ヘルパー関数 ──────────────────────────────────────
def _build_category_df(lang: str, category: str, exclude_names: set = None) -> pd.DataFrame:
    name_key = "name_ja" if lang == "ja" else "name_en"
    note_key = "note_ja" if lang == "ja" else "note_en"
    exclude_names = exclude_names or set()
    items = [item for item in DEFAULT_ITEMS if item["category"] == category]
    rows = []
    for item in items:
        name = item[name_key]
        # ライフスタイル設定で除外対象のアイテムはpriority=0
        priority = 0 if name in exclude_names else item.get("priority", 0)
        rows.append({
            "name":         name,
            "initial_cost": item["initial_cost"],
            "monthly_cost": item["monthly_cost"],
            "time":         item["time"],
            "health":       item["health"],
            "satisfaction": item["satisfaction"],
            "priority":     priority,
            "mandatory":    False,
            "category":     item["category"],
            "note":         item.get(note_key, ""),
        })
    return pd.DataFrame(rows)


def _init_all_category_dfs(lang: str, exclude_names: set = None) -> dict:
    return {cat: _build_category_df(lang, cat, exclude_names) for cat in CATEGORIES[lang]}


# ── 言語選択 ──────────────────────────────────────────
with st.sidebar:
    lang_choice = st.radio("🌐 Language / 言語", ["日本語", "English"], horizontal=True)
    lang = "ja" if lang_choice == "日本語" else "en"

T = LANG[lang]

# 言語切替時にデータを再初期化
if "items_lang" not in st.session_state or st.session_state.items_lang != lang:
    st.session_state.items_lang = lang
    st.session_state.category_dfs = _init_all_category_dfs(lang)

# ── タイトル ──────────────────────────────────────────
st.title(T["title"])
st.caption(T["caption"])

# ── Step 1: ユーザー属性・収入・固定費 ───────────────
st.header(T["step1"])

col1, col2, col3 = st.columns(3)
with col1:
    age    = st.number_input(T["age"],    min_value=18, max_value=100, value=42)
with col2:
    gender = st.selectbox(T["gender"],    T["gender_options"])
with col3:
    family = st.selectbox(T["family"],    T["family_options"])

col4, col5 = st.columns(2)
with col4:
    horizon_years = st.selectbox(T["horizon"], [1, 5, 10, 20, 50], index=1)
with col5:
    monthly_income = st.number_input(T["monthly_income"], min_value=0, value=4000, step=100)

st.subheader(T["fixed_costs_title"])
col_f1, col_f2, col_f3 = st.columns(3)
with col_f1:
    rent      = st.number_input(T["rent"],       min_value=0, value=1500, step=50)
    utilities = st.number_input(T["utilities"],  min_value=0, value=150,  step=10)
with col_f2:
    internet = st.number_input(T["internet"], min_value=0, value=130, step=10)
    groceries = st.number_input(T["groceries"],  min_value=0, value=400,  step=50)
with col_f3:
    health_insurance_fixed = st.number_input(T["health_insurance_fixed"], min_value=0, value=150, step=10)
    other_fixed            = st.number_input(T["other_fixed"],            min_value=0, value=0,   step=50)

total_fixed        = rent + utilities + internet + groceries + health_insurance_fixed + other_fixed
disposable_income  = max(monthly_income - total_fixed, 0)

st.metric(
    T["disposable_income"],
    f"${disposable_income:,}",
    delta=f"収入${monthly_income:,} − 固定費${total_fixed:,}" if lang == "ja"
          else f"Income${monthly_income:,} − Fixed${total_fixed:,}",
    delta_color="off",
    help=T["disposable_income_help"],
)

total_budget = st.number_input(
    T["total_budget"], min_value=0, value=5000, step=500, help=T["total_budget_help"]
)

st.divider()

# ── Step 2: 目標設定 ──────────────────────────────────
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
    w_time         = st.slider(T["w_time"],         1, 10, preset["time"])
with col9:
    w_health       = st.slider(T["w_health"],       1, 10, preset["health"])
with col10:
    w_satisfaction = st.slider(T["w_satisfaction"], 1, 10, preset["satisfaction"])
with col11:
    w_savings      = st.slider(T["w_savings"],      1, 10, preset["savings"])

st.divider()

# ── Step 2.5: ライフスタイル設定 ──────────────────────
st.header(T["step_lifestyle"])

col_ls1, col_ls2 = st.columns(2)
with col_ls1:
    diet     = st.selectbox(T["diet_label"],     T["diet_options"])
    exercise = st.selectbox(T["exercise_label"], T["exercise_options"])
with col_ls2:
    smoking  = st.selectbox(T["smoking_label"],  T["smoking_options"])
    alcohol  = st.selectbox(T["alcohol_label"],  T["alcohol_options"])

st.subheader(T["income_title"])
col_inc1, col_inc2, col_inc3 = st.columns(3)
with col_inc1:
    income_increase = st.number_input(T["income_increase"], min_value=0, value=0, step=50)
with col_inc2:
    income_years    = st.selectbox(T["income_years"], [1, 2, 3, 5, 10, 15, 20], index=2)
with col_inc3:
    income_reason   = st.selectbox(T["income_reason"], INCOME_REASON_OPTIONS[lang])

lifestyle_adj = calculate_lifestyle_adjustments({
    "diet":            diet,
    "exercise":        exercise,
    "smoking":         smoking,
    "alcohol":         alcohol,
    "income_increase": income_increase,
    "income_years":    income_years,
    "income_reason":   income_reason,
    "monthly_budget":  disposable_income,
    "horizon_years":   horizon_years,
    "savings_years": savings_period_years,
}, lang)

col_adj1, col_adj2 = st.columns(2)
col_adj1.metric(T["lifestyle_diet_note"],   f"${lifestyle_adj['diet_cost_adjustment']:+,}")
col_adj2.metric(T["lifestyle_health_note"], f"{lifestyle_adj['health_score_adjustment']:+} pt")

if lifestyle_adj["future_note"]:
    st.info(lifestyle_adj["future_note"])

# ライフスタイルに応じてアイテムを自動除外（session_stateを更新）
exclude_names = lifestyle_adj["exclude_names"]
for cat, df in st.session_state.category_dfs.items():
    for i, row in df.iterrows():
        if row["name"] in exclude_names:
            st.session_state.category_dfs[cat].at[i, "priority"] = 0
            key = f"priority_{cat}_{i}"
            if key in st.session_state:
                st.session_state[key] = 0

st.divider()

# ── Step 3: アイテム選択（タブ形式）─────────────────
st.header(T["step3"])
st.caption(T["step3_caption"])

category_keys   = list(CATEGORIES[lang].keys())
category_labels = list(CATEGORIES[lang].values())
tabs = st.tabs(category_labels)

for tab, category in zip(tabs, category_keys):
    with tab:
        constraint       = CATEGORY_CONSTRAINTS[category]
        constraint_label = constraint["label_ja"] if lang == "ja" else constraint["label_en"]
        df               = st.session_state.category_dfs[category]
        st.caption(constraint_label)

        # ヘッダー
        h = st.columns([1, 1, 3, 2, 2, 1, 1, 1, 2])
        h[0].caption(T["col_priority"])
        h[1].caption(T["col_mandatory"])
        h[2].caption(T["col_name"])
        h[3].caption(T["col_initial"])
        h[4].caption(T["col_monthly"])
        h[5].caption(T["col_time"])
        h[6].caption(T["col_health"])
        h[7].caption(T["col_satisfaction"])
        h[8].caption(T["col_note"])
        st.divider()

        for i, row in df.iterrows():
            _p_key = f"priority_{category}_{i}"
            _m_key = f"mandatory_{category}_{i}"

            if _p_key not in st.session_state:
                st.session_state[_p_key] = int(row["priority"])
            if _m_key not in st.session_state:
                st.session_state[_m_key] = bool(row["mandatory"])

            r = st.columns([1, 1, 3, 2, 2, 1, 1, 1, 2])

            priority  = r[0].number_input(
                "", min_value=0, max_value=99,
                key=_p_key, label_visibility="collapsed", step=1,
            )
            mandatory = r[1].checkbox(
                "", key=_m_key, label_visibility="collapsed",
            )

            r[2].write(row["name"])

            # 初期費用・月次費用は編集可能
            _ic_key = f"initial_cost_{category}_{i}"
            _mc_key = f"monthly_cost_{category}_{i}"
            if _ic_key not in st.session_state:
                st.session_state[_ic_key] = int(row["initial_cost"])
            if _mc_key not in st.session_state:
                st.session_state[_mc_key] = int(row["monthly_cost"])

            initial_cost = r[3].number_input(
                "", min_value=0, key=_ic_key,
                label_visibility="collapsed", step=50,
            )
            monthly_cost = r[4].number_input(
                "", min_value=0, key=_mc_key,
                label_visibility="collapsed", step=10,
            )

            r[5].write(str(int(row["time"])))
            r[6].write(str(int(row["health"])))
            r[7].write(str(int(row["satisfaction"])))
            r[8].caption(str(row.get("note", "")))

            # DataFrameを即時更新
            st.session_state.category_dfs[category].at[i, "priority"]     = priority
            st.session_state.category_dfs[category].at[i, "mandatory"]    = mandatory
            st.session_state.category_dfs[category].at[i, "initial_cost"] = initial_cost
            st.session_state.category_dfs[category].at[i, "monthly_cost"] = monthly_cost

        st.divider()

        # LLM補完（カテゴリごと）
        col_ai1, col_ai2 = st.columns([3, 1])
        with col_ai1:
            ai_name = st.text_input(
                T["ai_item_placeholder"],
                key=f"ai_input_{category}",
                label_visibility="collapsed",
                placeholder=T["ai_item_placeholder"],
            )
        with col_ai2:
            if st.button(T["ai_complete_button"], key=f"ai_btn_{category}") and ai_name:
                with st.spinner("AI..."):
                    defaults = get_item_defaults(ai_name, lang)
                if defaults:
                    new_idx = len(st.session_state.category_dfs[category])
                    new_row = pd.DataFrame([{
                        "name":         ai_name,
                        "initial_cost": defaults.get("initial_cost", 0),
                        "monthly_cost": defaults.get("monthly_cost", 0),
                        "time":         defaults.get("time", 5),
                        "health":       defaults.get("health", 5),
                        "satisfaction": defaults.get("satisfaction", 5),
                        "priority":     1,
                        "mandatory":    False,
                        "category":     category,
                        "note":         "",
                    }])
                    st.session_state.category_dfs[category] = pd.concat(
                        [st.session_state.category_dfs[category], new_row],
                        ignore_index=True,
                    )
                    st.session_state[f"priority_{category}_{new_idx}"]     = 1
                    st.session_state[f"mandatory_{category}_{new_idx}"]    = False
                    st.session_state[f"initial_cost_{category}_{new_idx}"] = defaults.get("initial_cost", 0)
                    st.session_state[f"monthly_cost_{category}_{new_idx}"] = defaults.get("monthly_cost", 0)
                    st.rerun()
                else:
                    st.warning(T["ai_error_complete"])

st.divider()

# ── リスクコスト ──────────────────────────────────────
use_risk = st.toggle(T["risk_toggle"], value=False)
effective_monthly_budget = int(lifestyle_adj["future_monthly_budget"])

if use_risk:
    st.subheader(T["risk_title"])
    st.caption(T["risk_caption"])

    transport_df = st.session_state.category_dfs.get("transport", pd.DataFrame())
    car_selected = any(
        ("車メイン" in str(row.get("name", "")) or "Car (Primary)" in str(row.get("name", "")))
        and (row.get("priority", 0) > 0 or row.get("mandatory", False))
        for _, row in transport_df.iterrows()
    ) if not transport_df.empty else False

    raw_costs = calculate_risk_costs(
        age=int(age),
        family=family,
        horizon_years=int(horizon_years),
        monthly_budget=effective_monthly_budget,
        car_selected=car_selected,
    )

    risk_df = pd.DataFrame([
        {
            T["risk_col_category"]: T["risk_categories"][c["category"]],
            T["risk_col_cost"]:     c["monthly_cost"],
        }
        for c in raw_costs
    ])

    edited_risk_df = st.data_editor(
        risk_df, num_rows="fixed",
        use_container_width=True,
        key="risk_editor",
    )

    total_risk = int(edited_risk_df[T["risk_col_cost"]].sum())
    effective_monthly_budget = max(int(lifestyle_adj["future_monthly_budget"]) - total_risk, 0)

    st.metric(
        T["risk_effective"],
        f"${effective_monthly_budget:,}",
        delta=f"-${total_risk:,}",
        delta_color="inverse",
    )

st.divider()

# ── 必須・候補アイテムのサマリー（ボタン上）─────────
all_items_preview = []
for category, df in st.session_state.category_dfs.items():
    for i, row in df.iterrows():
        all_items_preview.append({
            "name":         row["name"],
            "initial_cost": int(st.session_state.get(f"initial_cost_{category}_{i}", int(row["initial_cost"]))),
            "monthly_cost": int(st.session_state.get(f"monthly_cost_{category}_{i}", int(row["monthly_cost"]))),
            "priority":     int(row["priority"]),
            "mandatory":    bool(row["mandatory"]),
            "category":     row["category"],
        })

mandatory_preview = [item for item in all_items_preview if item["mandatory"]]
candidate_preview = [item for item in all_items_preview if item["priority"] > 0 or item["mandatory"]]

m_initial = sum(item["initial_cost"] for item in mandatory_preview)
m_monthly = sum(item["monthly_cost"]  for item in mandatory_preview)
c_initial = sum(item["initial_cost"] for item in candidate_preview)
c_monthly = sum(item["monthly_cost"]  for item in candidate_preview)

st.subheader(T["mandatory_summary_title"])
col_p1, col_p2, col_p3, col_p4 = st.columns(4)
col_p1.metric(T["must_initial"],  f"${m_initial:,}",
              delta=f"上限${int(total_budget):,}" if lang == "ja" else f"Limit${int(total_budget):,}",
              delta_color="inverse" if m_initial > int(total_budget) else "off")
col_p2.metric(T["must_monthly"],  f"${m_monthly:,}",
              delta=f"予算${effective_monthly_budget:,}" if lang == "ja" else f"Budget${effective_monthly_budget:,}",
              delta_color="inverse" if m_monthly > effective_monthly_budget else "off")
col_p3.metric(T["cand_initial"],  f"${c_initial:,}")
col_p4.metric(T["cand_monthly"],  f"${c_monthly:,}")

if m_initial > int(total_budget):
    st.error(T["validation_initial_over"].format(m_initial, int(total_budget)))
if m_monthly > effective_monthly_budget:
    st.error(T["validation_monthly_over"].format(m_monthly, effective_monthly_budget))

# ── 最適化実行 ────────────────────────────────────────
if st.button(T["run_button"], type="primary"):

    # 全カテゴリからアイテムを収集（編集済みコストを使用）
    all_items = []
    for category, df in st.session_state.category_dfs.items():
        for i, row in df.iterrows():
            all_items.append({
                "name":         row["name"],
                "initial_cost": int(st.session_state.get(f"initial_cost_{category}_{i}", int(row["initial_cost"]))),
                "monthly_cost": int(st.session_state.get(f"monthly_cost_{category}_{i}", int(row["monthly_cost"]))),
                "time":         int(row["time"]),
                "health":       int(row["health"]),
                "satisfaction": int(row["satisfaction"]),
                "priority":     int(row["priority"]),
                "mandatory":    bool(row["mandatory"]),
                "category":     row["category"],
            })

    # ライフスタイル補正を健康スコアに反映
    health_adj = lifestyle_adj["health_score_adjustment"]
    all_items = [
        {**item, "health": max(-10, min(10, item["health"] + health_adj))}
        for item in all_items
    ]

    weights = {
        "time": w_time, "health": w_health,
        "satisfaction": w_satisfaction, "savings": w_savings,
    }

    # バリデーション
    mandatory_items  = [item for item in all_items if item["mandatory"]]
    candidate_items  = [item for item in all_items if item["priority"] > 0 or item["mandatory"]]
    transport_cands  = [item for item in candidate_items if item["category"] == "transport"]

    errors   = []
    warnings_list = []

    if sum(item["initial_cost"] for item in mandatory_items) > int(total_budget):
        errors.append(T["validation_initial_over"].format(
            sum(item["initial_cost"] for item in mandatory_items), int(total_budget)))
    if sum(item["monthly_cost"] for item in mandatory_items) > effective_monthly_budget:
        errors.append(T["validation_monthly_over"].format(
            sum(item["monthly_cost"] for item in mandatory_items), effective_monthly_budget))
    if not transport_cands:
        warnings_list.append(T["validation_no_transport"])

    for w in warnings_list:
        st.warning(w)

    if errors:
        for e in errors:
            st.error(e)
    else:
        with st.spinner("Optimizing..."):
            result = run_optimizer(
                items=all_items,
                total_budget=int(total_budget),
                monthly_budget=effective_monthly_budget,
                target_monthly_savings=target_monthly_savings,
                weights=weights,
            )
            sens = run_sensitivity(
                items=all_items,
                monthly_budget=effective_monthly_budget,
                total_budget=int(total_budget),
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

            if lifestyle_adj["future_note"]:
                st.caption(lifestyle_adj["future_note"])

            # メトリクス
            col12, col13, col14, col15 = st.columns(4)
            col12.metric(T["total_initial"],  f"${result['total_initial_cost']:,}")
            col13.metric(T["total_monthly"],  f"${result['total_monthly_cost']:,}")
            col14.metric(T["actual_savings"], f"${result['actual_monthly_savings']:,}")
            col15.metric(T["savings_rate"],   f"{result['savings_rate']:.0%}")

            if result["savings_shortfall"] > 0:
                st.warning(T["shortfall_warn"].format(result["savings_shortfall"]))

            # 選ばれたアイテム一覧
            st.subheader(T["selected_items"])
            if result["selected"]:
                selected_by_cat = {}
                for item in result["selected"]:
                    cat = item.get("category", "other")
                    selected_by_cat.setdefault(cat, []).append(item)

                for cat, cat_items in selected_by_cat.items():
                    cat_label = CATEGORIES[lang].get(cat, cat)
                    st.markdown(f"**{cat_label}**")
                    cat_df = pd.DataFrame(cat_items)[
                        ["name", "initial_cost", "monthly_cost", "time", "health", "satisfaction"]
                    ].rename(columns={
                        "name":         T["col_name"],
                        "initial_cost": T["col_initial"],
                        "monthly_cost": T["col_monthly"],
                        "time":         T["col_time"],
                        "health":       T["col_health"],
                        "satisfaction": T["col_satisfaction"],
                    })
                    st.dataframe(cat_df, use_container_width=True, hide_index=True)

            # 推奨アクション
            # 推奨アクション：優先度順の未選択候補アイテム
            selected_names_set = {item["name"] for item in result["selected"]}
            car_chosen = any("車メイン" in n or "Car (Primary)" in n for n in selected_names_set)
            pet_chosen = any(n in ("ペット", "Pet") for n in selected_names_set)

            # 未選択の候補アイテムを優先度順にソート
            unselected_candidates = [
                item for item in all_items
                if item["name"] not in selected_names_set
                and item.get("priority", 0) > 0
                and not item.get("mandatory", False)
                and item.get("category") not in ("_savings",)
                # 依存制約フィルタ
                and not (item["name"] in ("車保険", "Car Insurance") and not car_chosen)
                and not (item["name"] in ("ペット保険", "Pet Insurance") and not pet_chosen)
            ]
            unselected_candidates.sort(key=lambda x: x.get("priority", 99))

            if unselected_candidates:
                st.subheader(T["rec_title"])
                remaining_monthly = effective_monthly_budget - result["total_monthly_cost"]
                remaining_initial = int(total_budget) - result["total_initial_cost"]

                for item in unselected_candidates[:5]:  # 上位5件
                    shortfall_monthly = max(item["monthly_cost"] - remaining_monthly, 0)
                    shortfall_initial = max(item["initial_cost"] - remaining_initial, 0)

                    if shortfall_monthly == 0 and shortfall_initial == 0:
                        st.success(
                            f"優先度{item['priority']}: **{item['name']}**　"
                            f"初期費用${item['initial_cost']:,} / 月次費用${item['monthly_cost']:,}　"
                            f"→ {T['rec_within_budget']}"
                            if lang == "ja" else
                            f"Priority {item['priority']}: **{item['name']}**　"
                            f"Initial${item['initial_cost']:,} / Monthly${item['monthly_cost']:,}　"
                            f"→ {T['rec_within_budget']}"
                        )
                    else:
                        shortfall_msg = []
                        if shortfall_monthly > 0:
                            shortfall_msg.append(f"月次あと${shortfall_monthly:,}" if lang == "ja" else f"${shortfall_monthly:,}/month more")
                        if shortfall_initial > 0:
                            shortfall_msg.append(f"初期費用あと${shortfall_initial:,}" if lang == "ja" else f"${shortfall_initial:,} more initial")
                        st.info(
                            f"優先度{item['priority']}: **{item['name']}**　"
                            f"初期費用${item['initial_cost']:,} / 月次費用${item['monthly_cost']:,}　"
                            f"→ {' / '.join(shortfall_msg)}必要"
                            if lang == "ja" else
                            f"Priority {item['priority']}: **{item['name']}**　"
                            f"Initial${item['initial_cost']:,} / Monthly${item['monthly_cost']:,}　"
                            f"→ {' / '.join(shortfall_msg)} needed"
                        )
            # 選ばれたアイテム名のセット
            selected_names_set = {item["name"] for item in result["selected"]}

            # 車が選ばれていない場合、車保険を推奨から除外
            car_chosen = any(
                "車メイン" in name or "Car (Primary)" in name
                for name in selected_names_set
            )

            # ペットが選ばれていない場合、ペット保険を推奨から除外
            pet_chosen = any(
                "ペット" in name or "Pet" in name
                for name in selected_names_set
            )

            def _should_show_rec(item_name: str) -> bool:
                if ("車保険" in item_name or "Car Insurance" in item_name) and not car_chosen:
                    return False
                if ("ペット保険" in item_name or "Pet Insurance" in item_name) and not pet_chosen:
                    return False
                return True

            # 感度分析グラフ
            st.header(T["sensitivity_title"])
            tab_m, tab_i = st.tabs([T["tab_monthly"], T["tab_initial"]])

            with tab_m:
                st.plotly_chart(make_line_chart(
                    sens["monthly_range"], sens["monthly_values"],
                    effective_monthly_budget,
                    T["chart_monthly_x"], T["chart_value"], T["chart_line_title_m"],
                ), use_container_width=True)

            with tab_i:
                st.plotly_chart(make_line_chart(
                    sens["initial_range"], sens["initial_values"],
                    int(total_budget),
                    T["chart_initial_x"], T["chart_value"], T["chart_line_title_i"],
                ), use_container_width=True)

        else:
            st.error(T["result_ng"])