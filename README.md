# 💰 The Life-Value Optimizer

**Maximize your life quality within a limited budget — powered by AI + Mathematical Optimization**

> A portfolio project by **Manami Oyama** | AI Engineer / Data Scientist  
> Built for CPT job search (Data Science / AI Engineering roles)

---

## 🌐 Live Demo

> _[Streamlit Community Cloud URL — add after deployment]_

---

## 📌 What is this?

The Life-Value Optimizer is a **full-stack AI web application** that helps users find the optimal combination of lifestyle spending — gym, Netflix, travel fund, bicycle, and more — within a real monthly budget.

Unlike a simple budget tracker, this app treats spending as **investment decisions**:

- A bicycle isn't just "$500" — it saves time, builds health, and brings satisfaction.
- Savings aren't just "leftover money" — they compete directly with other items for priority.
- Your lifestyle habits (diet, exercise, smoking) affect the health scores of every item.

The optimizer finds the combination that **maximizes your total life value**, not just minimizes your spending.

---

## 🎯 Why This Project

This app demonstrates the **PM × Data Science × AI Engineering** skill stack required for real-world AI product roles:

| Skill | Demonstrated by |
|---|---|
| **Problem formulation** | Translating "what makes life better" into a mathematical model |
| **Mathematical optimization** | OR-Tools CP-SAT solver with custom utility functions |
| **LLM integration** | Gemini API for item auto-fill and result summaries |
| **Full-stack Python** | Streamlit UI with session state management |
| **Product thinking** | User-centered UX, progressive disclosure, sensible defaults |
| **Bilingual UX** | Full Japanese / English language support |

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────┐
│              Streamlit UI               │
│   app.py  ←→  lang.py (i18n)           │
└────────────┬────────────────────────────┘
             │
     ┌───────┴────────┐
     │                │
┌────▼─────┐   ┌──────▼──────┐
│optimizer │   │  llm.py     │
│  .py     │   │  Gemini API │
│ OR-Tools │   └─────────────┘
└────┬─────┘
     │
┌────▼──────────┐  ┌──────────────┐  ┌──────────────┐
│sensitivity.py │  │ lifestyle.py │  │ risk_cost.py │
│ (what-if      │  │ (health adj) │  │ (future cost │
│  analysis)    │  │              │  │  prediction) │
└───────────────┘  └──────────────┘  └──────────────┘
             │
┌────────────▼──────────┐
│   default_items.py    │
│ (50+ items, 9 categ.) │
└───────────────────────┘
```

---

## 🧮 The Optimization Model

### Decision Variables

For each item $i$: $x_i \in \{0, 1\}$ (select or not)

### Objective Function

$$\text{Maximize} \sum_i x_i \cdot u_i + \text{savings\_value}$$

Where item utility is:

$$u_i = \left( w_{time} \cdot time_i + w_{health} \cdot (health_i + 10) + w_{satisfaction} \cdot satisfaction_i \right) \times p_i$$

And priority bonus uses **rank percentile normalization**:

$$p_i = 2.0 - \frac{\text{rank}(priority_i)}{|\text{unique priorities}| - 1}$$

This means priority=1 items get 2.0× weight, lowest priority items get 1.0× — **without any hardcoded thresholds**, adapting dynamically to whatever priorities the user enters.

Savings utility competes directly with items:

$$\text{savings\_value} = \text{actual\_savings} \times \frac{\sum u_i \cdot w_{savings}}{10 \times \text{budget}}$$

When `w_savings=10`, fully saving the budget is worth as much as selecting all items. When `w_savings=1`, items dominate.

### Constraints

| Constraint | Description |
|---|---|
| $\sum x_i \cdot \text{initial\_cost}_i \leq B_{initial}$ | One-time budget limit |
| $\sum x_i \cdot \text{monthly\_cost}_i \leq B_{monthly}$ | Monthly disposable income |
| $\sum_{i \in transport} x_i = 1$ | Exactly one transport package |
| $x_{pet\_insurance} \leq x_{pet}$ | Pet insurance requires pet |
| $x_{car\_insurance} \leq x_{car}$ | Car insurance requires car |
| $x_i = 1$ for mandatory items | User-forced selections |

---

## 🗂️ Features

### Step 1 — Your Profile & Fixed Costs
- Age, gender, household structure
- Monthly income → auto-calculates disposable income after fixed costs
- Fixed costs: rent, utilities, internet/phone, groceries, health insurance

### Step 2 — Goals & Priorities
- Savings goal (e.g. "$5,000 in 2 years" → $208/month target)
- Value weights: Time Saving / Health / Satisfaction / Savings (1–10 sliders)
- Presets: "Stay Healthy", "Save Money", "Live Comfortably", "Custom"

### Step 2.5 — Lifestyle Settings
- Diet preference → adjusts food cost and health scores
- Exercise frequency, smoking, alcohol → adjusts health scores across all items
- Future income projection → raises effective budget within savings period

### Step 3 — Item Selection (9 categories, 50+ items)
- Transport as **packages** (Car / E-Bike+Uber / Bicycle Only / etc.)
- Priority input (1 = top priority, same number = same weight)
- Mandatory checkbox (force-include any item)
- Cost editing (override defaults with your real costs)
- AI auto-fill: type any item name → Gemini suggests costs and scores

### Results
- AI summary (Gemini) in natural language
- Selected items grouped by category
- Savings rate vs. goal
- Next-best recommendations (top 5 unselected by priority)
- Sensitivity analysis: how total value changes as budget increases

### Risk Cost Estimation (optional)
- Medical out-of-pocket, housing repair, car repair, education, emergency fund
- Based on age, household, car ownership
- Fully editable

---

## 🛠️ Tech Stack

| Layer | Technology |
|---|---|
| **UI** | Streamlit |
| **Optimization** | Google OR-Tools (CP-SAT solver) |
| **LLM** | Google Gemini 2.5 Flash Lite API |
| **Visualization** | Plotly |
| **Language** | Python 3.12 |
| **i18n** | Custom dictionary-based (Japanese / English) |

---

## 📁 File Structure

```
life-value-optimizer/
├── app.py              # Streamlit UI + session state management
├── optimizer.py        # OR-Tools CP-SAT model (utility theory)
├── sensitivity.py      # What-if analysis (budget sensitivity)
├── llm.py              # Gemini API (item auto-fill + summary)
├── lang.py             # Bilingual text dictionary (ja/en)
├── default_items.py    # 50+ items across 9 categories with defaults
├── lifestyle.py        # Lifestyle-based score adjustments
├── risk_cost.py        # Future risk cost estimation tables
├── requirements.txt
└── .streamlit/
    └── secrets.toml    # GEMINI_API_KEY (not committed)
```

---

## 🚀 Getting Started

### Prerequisites
- Python 3.12+
- Gemini API key ([Get one free](https://aistudio.google.com/app/apikey))

### Installation

```bash
git clone https://github.com/your-username/life-value-optimizer.git
cd life-value-optimizer
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### Configuration

Create `.streamlit/secrets.toml`:

```toml
GEMINI_API_KEY = "your-api-key-here"
```

### Run

```bash
streamlit run app.py
```

---

## 📦 Requirements

```
streamlit
ortools
google-genai
plotly
pandas
numpy
```

---

## 🔒 Security Notes

- API keys are stored in `.streamlit/secrets.toml` (gitignored)
- No user data is persisted (session-only)
- Gemini free tier: 1,500 requests/day — sufficient for demo use

---

## 👩‍💻 About the Author

**Manami Oyama**  
AI Engineer / Data Scientist / PM  
📍 Honolulu, Hawaii  
🎓 KCC (CPT eligible)

- 4 years Data Science
- 2 years AI Engineering  
- 3 years Web Development

Currently seeking CPT part-time positions in Data Science / AI Engineering.

---

## 📄 License

MIT License — free to use, modify, and distribute.
