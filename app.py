
import math
from datetime import date, timedelta
from dateutil.relativedelta import relativedelta

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

st.set_page_config(page_title="Interactive Loan Calculator", page_icon="💸", layout="wide")

# -----------------------------
# Sidebar: User / Loan Inputs
# -----------------------------
with st.sidebar:
    st.title("💸 Loan Calculator")
    st.caption("Play with inputs and instantly see graphs, tables, and summaries.")

    # Borrower details
    st.subheader("Borrower")
    name = st.text_input("Name", value="Alex Doe", help="For personalization in the report.")
    age = st.number_input("Age", min_value=0, max_value=120, value=30)
    region = st.text_input("Country/Region (optional)", value="")

    # Loan basics
    st.subheader("Loan Details")
    purchase_price = st.number_input("Purchase Price (optional)", min_value=0.0, value=500000.0, step=1000.0, format="%.2f")
    deposit = st.number_input("Deposit / Down Payment", min_value=0.0, value=100000.0, step=1000.0, format="%.2f")
    principal = st.number_input("Loan Amount (principal)", min_value=0.0, value=max(0.0, purchase_price - deposit), step=1000.0, format="%.2f")
    apr = st.number_input("Annual Interest Rate (APR, %)", min_value=0.0, max_value=100.0, value=7.5, step=0.05, format="%.2f") / 100.0

    loan_years = st.slider("Duration (years)", min_value=1, max_value=40, value=25, help="Total term length")

    comp_map = {"Monthly (12)": 12, "Quarterly (4)": 4, "Biannual (2)": 2, "Annual (1)": 1}
    comp_choice = st.selectbox("Compounding frequency", list(comp_map.keys()), index=0)
    comp_per_year = comp_map[comp_choice]

    payfreq_map = {"Monthly (12)": 12, "Biweekly (26)": 26, "Weekly (52)": 52}
    pay_choice = st.selectbox("Repayment frequency", list(payfreq_map.keys()), index=0)
    pay_per_year = payfreq_map[pay_choice]

    start_date = st.date_input("First Payment Date", value=date.today())

    st.subheader("Advanced Options")
    extra_payment = st.slider("Extra Payment per period", min_value=0.0, max_value=20000.0, value=0.0, step=100.0)
    interest_only_toggle = st.toggle("Interest-only period?")
    io_months = 0
    if interest_only_toggle:
        if pay_per_year == 12:
            io_months = st.number_input("Interest-only Months", min_value=1, max_value=60, value=12, step=1)
        else:
            st.info("Interest-only period is applied in **months** and converted to your payment frequency.")
            io_months = st.number_input("Interest-only Months", min_value=1, max_value=60, value=12, step=1)

    fees_checked = st.checkbox("Include one-time fees (origination, closing)")
    one_time_fees = 0.0
    roll_fees = False
    if fees_checked:
        one_time_fees = st.number_input("One-time Fees (total)", min_value=0.0, value=0.0, step=100.0)
        roll_fees = st.checkbox("Roll fees into the loan (increase principal)", value=True)

    escrow_toggle = st.toggle("Add monthly escrow (tax/insurance/HOA)")
    escrow_amount = 0.0
    if escrow_toggle:
        escrow_amount = st.number_input("Escrow amount per month", min_value=0.0, value=0.0, step=50.0)

    inflation_checked = st.checkbox("Adjust with expected inflation (for informational charts)")
    inflation_rate = 0.0
    if inflation_checked:
        inflation_rate = st.number_input("Expected Annual Inflation (%)", min_value=0.0, max_value=50.0, value=3.0, step=0.1) / 100.0

    show_table = st.checkbox("Show full amortization table", value=True)

# -----------------------------
# Helper functions
# -----------------------------
def periodic_rate_from_apr(apr: float, comp_per_year: int, pay_per_year: int) -> float:
    """Convert APR with compounding 'comp_per_year' to an effective per-payment rate"""
    ear = (1 + apr/comp_per_year) ** comp_per_year - 1  # effective annual rate
    per = (1 + ear) ** (1 / pay_per_year) - 1
    return per

def pmt(rate, nper, pv):
    """Payment formula for amortizing loan. Returns positive payment amount."""
    if rate == 0:
        return pv / nper
    return (rate * pv) / (1 - (1 + rate) ** (-nper))

def build_schedule(principal: float,
                   apr: float,
                   years: int,
                   comp_per_year: int,
                   pay_per_year: int,
                   start_date: date,
                   extra_payment: float = 0.0,
                   io_months: int = 0,
                   escrow_monthly: float = 0.0,
                   inflation_rate: float = 0.0,
                   roll_fees: bool = False,
                   fees: float = 0.0) -> pd.DataFrame:
    """Return amortization schedule DataFrame."""
    # Optionally roll fees into principal
    pv = principal + (fees if roll_fees else 0.0)

    nper = years * pay_per_year
    rate = periodic_rate_from_apr(apr, comp_per_year, pay_per_year)
    base_payment = pmt(rate, nper, pv)

    # Convert IO months to number of payments (approximate via monthly->periods)
    io_periods = int(round(io_months * pay_per_year / 12))

    # Build schedule iteratively
    bal = pv
    rows = []
    current_date = start_date

    # Helper for advancing date by payment frequency
    def advance_date(d: date) -> date:
        if pay_per_year == 12:
            return d + relativedelta(months=+1)
        elif pay_per_year == 26:
            return d + timedelta(days=14)
        elif pay_per_year == 52:
            return d + timedelta(days=7)
        else:
            return d + relativedelta(months=+1)

    escrow_per_period = escrow_monthly * (12 / pay_per_year) if escrow_monthly else 0.0

    i = 0
    total_interest = 0.0
    total_principal = 0.0
    total_payment = 0.0
    total_escrow = 0.0
    total_extra = 0.0

    while bal > 1e-6 and i < nper + 6000:
        interest = bal * rate
        if i < io_periods:
            scheduled_principal = 0.0
            scheduled_payment = interest
        else:
            scheduled_payment = base_payment
            scheduled_principal = scheduled_payment - interest
            if scheduled_principal < 0:
                scheduled_principal = 0.0

        extra = extra_payment
        if scheduled_principal + extra > bal:
            extra = max(0.0, bal - scheduled_principal)

        principal_component = scheduled_principal + extra
        payment_component = scheduled_payment + extra

        new_bal = bal - principal_component
        if new_bal < 0:
            payment_component += new_bal
            principal_component += new_bal
            new_bal = 0.0

        inflation_per_period = (1 + inflation_rate) ** (1 / pay_per_year) - 1 if inflation_rate else 0.0
        inflation_factor = (1 + inflation_per_period) ** i

        rows.append({
            "Period": i + 1,
            "Date": current_date,
            "Payment": round(payment_component, 8),
            "Interest": round(interest, 8),
            "Principal": round(principal_component, 8),
            "Extra_Principal": round(extra, 8),
            "Escrow": round(escrow_per_period, 8),
            "Total_Outflow": round(payment_component + escrow_per_period, 8),
            "Balance": round(new_bal, 8),
            "Inflation_Adjusted_Payment": (payment_component / inflation_factor) if inflation_rate else None
        })

        total_interest += interest
        total_principal += principal_component
        total_payment += payment_component
        total_escrow += escrow_per_period
        total_extra += extra

        bal = new_bal
        current_date = advance_date(current_date)
        i += 1

    df = pd.DataFrame(rows)
    meta = {
        "base_payment": base_payment,
        "periodic_rate": rate,
        "n_periods": i,
        "total_interest": total_interest,
        "total_principal": total_principal,
        "total_payment": total_payment,
        "total_escrow": total_escrow,
        "total_extra": total_extra,
        "rolled_fees": fees if roll_fees else 0.0,
        "fees_paid_upfront": fees if not roll_fees else 0.0
    }
    return df, meta

# Build schedule
schedule_df, meta = build_schedule(
    principal=principal,
    apr=apr,
    years=loan_years,
    comp_per_year=comp_per_year,
    pay_per_year=pay_per_year,
    start_date=start_date,
    extra_payment=extra_payment,
    io_months=io_months,
    escrow_monthly=escrow_amount,
    inflation_rate=inflation_rate,
    roll_fees=roll_fees,
    fees=one_time_fees
)

# -----------------------------
# Top Summary Cards
# -----------------------------
st.markdown(f"### 👋 Hello, **{name}**{' from ' + region if region else ''}! Here's your loan summary.")
col1, col2, col3, col4 = st.columns(4)
with col1:
    st.metric("Loan Amount", f"${principal:,.0f}")
with col2:
    st.metric("APR", f"{apr*100:.2f}%")
with col3:
    st.metric("Term", f"{loan_years} years")
with col4:
    st.metric("Payments", f"{meta['n_periods']} ({list(payfreq_map.keys())[list(payfreq_map.values()).index(pay_per_year)]})")

col5, col6, col7, col8 = st.columns(4)
with col5:
    st.metric("Base Payment (per period)", f"${meta['base_payment']:.2f}")
with col6:
    st.metric("Total Interest", f"${meta['total_interest']:.2f}")
with col7:
    st.metric("Total Principal", f"${meta['total_principal']:.2f}")
with col8:
    st.metric("Total Escrow", f"${meta['total_escrow']:.2f}")

# -----------------------------
# Charts
# -----------------------------
tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs([
    "📉 Balance Over Time",
    "📊 Payment Breakdown",
    "📈 Cumulative Totals",
    "🧮 Yearly Summary",
    "📆 Interest vs Principal Ratio",
    "📉 Inflation Adjusted Analysis",
    "⚡ Extra Payments Impact"
])

with tab1:
    fig_bal = px.line(schedule_df, x="Date", y="Balance", title="Outstanding Balance Over Time")
    st.plotly_chart(fig_bal, use_container_width=True)

with tab2:
    N = min(120, len(schedule_df))
    small = schedule_df.head(N)
    fig_bar = go.Figure()
    fig_bar.add_trace(go.Bar(x=small["Date"], y=small["Interest"], name="Interest"))
    fig_bar.add_trace(go.Bar(x=small["Date"], y=small["Principal"], name="Principal"))
    fig_bar.add_trace(go.Bar(x=small["Date"], y=small["Extra_Principal"], name="Extra Principal"))
    fig_bar.update_layout(barmode="stack", title=f"Payment Breakdown (first {N} periods)")
    st.plotly_chart(fig_bar, use_container_width=True)

with tab3:
    schedule_df["Cum_Interest"] = schedule_df["Interest"].cumsum()
    schedule_df["Cum_Principal"] = schedule_df["Principal"].cumsum()
    fig_cum = px.area(schedule_df, x="Date", y=["Cum_Principal", "Cum_Interest"], title="Cumulative Principal vs Interest")
    st.plotly_chart(fig_cum, use_container_width=True)

    pie = go.Figure(data=[go.Pie(labels=["Total Principal", "Total Interest"], values=[meta["total_principal"], meta["total_interest"]])])
    pie.update_layout(title="Total Cost Breakdown")
    st.plotly_chart(pie, use_container_width=True)

with tab4:
    if len(schedule_df) > 0:
        df_year = schedule_df.copy()
        df_year["Year"] = pd.to_datetime(df_year["Date"]).dt.year
        yearly = df_year.groupby("Year").agg({
            "Payment":"sum", "Interest":"sum", "Principal":"sum", "Extra_Principal":"sum",
            "Escrow":"sum", "Total_Outflow":"sum"
        }).reset_index()
        st.dataframe(yearly, use_container_width=True)
        fig_year = px.bar(yearly, x="Year", y=["Interest", "Principal", "Extra_Principal"], title="Yearly Payment Breakdown (Stacked)")
        st.plotly_chart(fig_year, use_container_width=True)
    else:
        st.info("No data to summarize.")

with tab5:
    schedule_df["Interest_to_Principal_Ratio"] = schedule_df["Interest"] / (schedule_df["Principal"] + 1e-9)
    fig_ratio = px.line(schedule_df, x="Date", y="Interest_to_Principal_Ratio", title="Interest-to-Principal Payment Ratio Over Time")
    st.plotly_chart(fig_ratio, use_container_width=True)

with tab6:
    if inflation_rate > 0:
        valid = schedule_df.dropna(subset=["Inflation_Adjusted_Payment"])
        fig_infl = px.line(valid, x="Date", y="Inflation_Adjusted_Payment", title="Inflation-Adjusted Payments Over Time")
        st.plotly_chart(fig_infl, use_container_width=True)
    else:
        st.info("Enable inflation adjustment in sidebar to see this analysis.")

with tab7:
    alt_df, alt_meta = build_schedule(
        principal=principal,
        apr=apr,
        years=loan_years,
        comp_per_year=comp_per_year,
        pay_per_year=pay_per_year,
        start_date=start_date,
        extra_payment=0.0,
        io_months=io_months,
        escrow_monthly=escrow_amount,
        inflation_rate=inflation_rate,
        roll_fees=roll_fees,
        fees=one_time_fees
    )
    compare = pd.DataFrame({
        "Scenario":["With Extra Payments","Without Extra Payments"],
        "Total Interest":[meta["total_interest"], alt_meta["total_interest"]],
        "Total Payments":[meta["n_periods"], alt_meta["n_periods"]]
    })
    st.dataframe(compare, use_container_width=True)
    fig_comp = px.bar(compare, x="Scenario", y="Total Interest", title="Impact of Extra Payments on Total Interest")
    st.plotly_chart(fig_comp, use_container_width=True)

# -----------------------------
# Tables
# -----------------------------
st.subheader("📄 Key Figures")
summary_df = pd.DataFrame({
    "Metric": ["Loan Amount", "APR", "Term (years)", "Compounding", "Payments per Year",
               "Base Payment", "Total Interest", "Total Principal", "Total Extra", "Total Escrow",
               "Fees Rolled Into Loan", "Fees Paid Upfront"],
    "Value": [f"${principal:,.2f}", f"{apr*100:.2f}%", loan_years, comp_per_year, pay_per_year,
              f"${meta['base_payment']:,.2f}", f"${meta['total_interest']:,.2f}", f"${meta['total_principal']:,.2f}",
              f"${meta['total_extra']:,.2f}", f"${meta['total_escrow']:,.2f}",
              f"${meta['rolled_fees']:,.2f}", f"${meta['fees_paid_upfront']:,.2f}"]
})
st.dataframe(summary_df, use_container_width=True, hide_index=True)

if show_table:
    st.subheader("📅 Full Amortization Schedule")
    st.dataframe(schedule_df, use_container_width=True)

# -----------------------------
# Download options
# -----------------------------
st.download_button("⬇️ Download Amortization Schedule (CSV)", data=schedule_df.to_csv(index=False), file_name="amortization_schedule.csv", mime="text/csv")

report = f"""
# Loan Report for {name}

- Age: {age}
- Region: {region or '—'}

## Loan Summary
- Principal (Loan Amount): ${principal:,.2f}
- APR: {apr*100:.2f}%
- Term: {loan_years} years
- Repayment Frequency: {pay_choice}
- Compounding: {comp_choice}
- Base Payment (per period): ${meta['base_payment']:,.2f}

## Totals
- Total Interest: ${meta['total_interest']:,.2f}
- Total Principal: ${meta['total_principal']:,.2f}
- Total Extra Principal: ${meta['total_extra']:,.2f}
- Total Escrow: ${meta['total_escrow']:,.2f}

*Generated on: {date.today().isoformat()}*
"""
st.download_button("⬇️ Download Summary Report (Markdown)", data=report, file_name="loan_report.md", mime="text/markdown")

st.caption("Built with ❤️ using Streamlit, Plotly, NumPy, and Pandas.")
