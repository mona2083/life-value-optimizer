# llm.py
# Gemini API連携：アイテム補完 / 結果サマリー

import json
import streamlit as st
from google import genai

_client = genai.Client(api_key=st.secrets["GEMINI_API_KEY"])


def get_item_defaults(item_name: str, lang: str) -> dict | None:
    """
    アイテム名 → デフォルト値をGeminiで補完
    JSON以外を返さないよう明示的に指示している
    """
    prompt = f"""
You are a financial and lifestyle advisor.
Return ONLY a JSON object. No explanation, no markdown, no backticks.

Estimate realistic values for: "{item_name}"
{{
  "initial_cost": <one-time USD cost, integer>,
  "monthly_cost": <monthly USD cost, integer>,
  "time":         <time saving score 1-10, integer>,
  "health":       <health benefit score 1-10, integer>,
  "satisfaction": <satisfaction score 1-10, integer>
}}
"""
    try:
        response = _client.models.generate_content(
            model="gemini-2.5-flash-lite",
            contents=prompt,
        )
        text = response.text.strip()
        start = text.find("{")
        end   = text.rfind("}") + 1
        return json.loads(text[start:end])
    except Exception as e:
        return None


def get_result_summary(
    result: dict,
    user_profile: dict,
    weights: dict,
    lang: str,
) -> str | None:
    """
    最適化結果 → 自然言語サマリーをGeminiで生成
    """
    selected_names = [item["name"] for item in result["selected"]]

    if lang == "ja":
        prompt = f"""
あなたはライフスタイルアドバイザーです。
以下の最適化結果を2〜3文で要約してください。
専門用語は使わず、わかりやすく前向きなトーンで。

ユーザー: {user_profile.get('age')}歳 / {user_profile.get('family')}
優先度: 時間節約={weights['time']}, 健康={weights['health']}, 満足度={weights['satisfaction']}, 貯蓄={weights['savings']}
選ばれたアイテム: {', '.join(selected_names) or 'なし'}
月次費用合計: ${result['total_monthly_cost']}
実際の月次貯蓄: ${result['actual_monthly_savings']}
貯蓄目標達成率: {result['savings_rate']:.0%}
"""
    else:
        prompt = f"""
You are a lifestyle advisor.
Summarize the following optimization result in 2-3 sentences.
Use simple, friendly, and encouraging language. No jargon.

User: Age {user_profile.get('age')} / {user_profile.get('family')}
Priorities: Time={weights['time']}, Health={weights['health']}, Satisfaction={weights['satisfaction']}, Savings={weights['savings']}
Selected: {', '.join(selected_names) or 'None'}
Total monthly cost: ${result['total_monthly_cost']}
Actual monthly savings: ${result['actual_monthly_savings']}
Savings goal rate: {result['savings_rate']:.0%}
"""
    try:
        response = _client.models.generate_content(
            model="gemini-2.5-flash-lite",
            contents=prompt,
        )
        return response.text.strip()
    except Exception as e:
        return None