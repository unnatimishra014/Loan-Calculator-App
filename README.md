# Loan-Calculator-App

A ready-to-deploy Streamlit application that calculates loan payments and generates interactive charts and tables. It supports multiple input types (text, numbers, sliders, toggles, checkboxes) and exports the amortization schedule.

## ✨ Features
- Text, number, slider, toggle, checkbox, and date inputs
- Handles deposit/down payment, fees (rolled-in or upfront), interest-only periods, escrow
- Flexible compounding and payment frequencies
- Extra principal payments
- Interactive charts (balance over time, stacked breakdown, cumulative totals, yearly summary)
- Amortization table and downloadable CSV & Markdown report

## 🧰 Tech
- Streamlit
- Pandas & NumPy
- Plotly
- python-dateutil

## 🔧 Local Setup
```bash
# 1) Create a virtual environment (optional but recommended)
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# 2) Install dependencies
pip install -r requirements.txt

# 3) Run the app
streamlit run app.py
```
Then open the URL that Streamlit prints (usually http://localhost:8501).

## ☁️ Deploy on Streamlit Community Cloud
1. Push this folder to a **public GitHub repo**. You can use these commands:
   ```bash
   git init
   git add .
   git commit -m "Add Streamlit loan calculator"
   git branch -M main
   git remote add origin https://github.com/<your-username>/<your-repo>.git
   git push -u origin main
   ```
2. Go to https://streamlit.io/cloud, sign in, click **New app**.
3. Choose your repo, set **Main file path** to `app.py`, and deploy.
4. Once deployed, copy the live URL and share it.

## 📁 Project Structure
```
.
├── app.py
├── requirements.txt
└── README.md
```

## 📝 Notes
- The app includes a warning for potential negative amortization.
- Inflation adjustment is informational (used for an adjusted payment series only).
- Escrow input is monthly but scaled to your repayment frequency.

## 🐞 Issues & ideas
Open a GitHub issue or tweak the code to your needs. Enjoy!
