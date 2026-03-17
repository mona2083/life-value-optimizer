import json
import streamlit as st
from google import genai

_client = genai.Client(api_key=st.secrets["GEMINI_API_KEY"])


def get_item_defaults(item_name: str, lang: str) -> dict | None:
    prompt = f"""
You are a financial and lifestyle advisor.
Return ONLY a JSON object. No explanation, no markdown, no backticks.

Estimate realistic values for: "{item_name}"
{{
  "initial_cost":  <one-time USD cost, integer>,
  "monthly_cost":  <monthly USD cost, integer>,
  "health":        <physical & mental health impact, -10 to 10, integer>,
  "connections":   <social connection & relationships score, 1-10, integer>,
  "freedom":       <time freedom & autonomy score, 1-10, integer>,
  "growth":        <personal growth & purpose score, 1-10, integer>
}}
"""
    try:
        response = _client.models.generate_content(
            model="gemini-2.5-flash-lite",
            contents=prompt,
        )
        text  = response.text.strip()
        start = text.find("{")
        end   = text.rfind("}") + 1
        return json.loads(text[start:end])
    except Exception:
        return None


def get_result_summary(
    result: dict,
    user_profile: dict,
    weights: dict,
    lang: str,
) -> str | None:
    selected_names = [item["name"] for item in result["selected"]]

    if lang == "ja":
        prompt = f"""
あなたはライフスタイルアドバイザーです。
以下の最適化結果を2〜3文で要約してください。
専門用語は使わず、わかりやすく前向きなトーンで。

ユーザー: {user_profile.get('age')}歳 / {user_profile.get('family')}
価値観の重み: 健康={weights['health']}, つながり={weights['connections']}, 自由={weights['freedom']}, 成長={weights['growth']}, 貯蓄={weights['savings']}
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
Value weights: Health={weights['health']}, Connections={weights['connections']}, Freedom={weights['freedom']}, Growth={weights['growth']}, Savings={weights['savings']}
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
    except Exception:
        return None