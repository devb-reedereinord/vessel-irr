import streamlit as st
import numpy as np
import pandas as pd

# Regression formulas
def estimate_resale_price(vessel_type, investment_term, three_yr_tc):
    if vessel_type == "Suezmax" and investment_term == 5:
        resale_million = -2.055e-2 + 2.150e-3 * three_yr_tc
    elif vessel_type == "Suezmax" and investment_term == 10:
        resale_million = -15.61 + 2.164e-3 * three_yr_tc
    elif vessel_type == "Aframax" and investment_term == 5:
        resale_million = -0.3278 + 2.016e-3 * three_yr_tc
    else:  # Aframax 10yr
        resale_million = -11.22 + 1.915e-3 * three_yr_tc
    return resale_million * 1_000_000

# Manual IRR function using Newton-Raphson method
def calculate_irr(cash_flows, guess=0.1, max_iterations=1000, tolerance=1e-6):
    rate = guess
    for i in range(max_iterations):
        npv = sum(cf / (1 + rate) ** idx for idx, cf in enumerate(cash_flows))
        derivative = sum(-idx * cf / (1 + rate) ** (idx + 1) for idx, cf in enumerate(cash_flows))
        if derivative == 0:
            return float('nan')
        new_rate = rate - npv / derivative
        if abs(new_rate - rate) < tolerance:
            return new_rate * 100
        rate = new_rate
    return float('nan')

# Streamlit app
st.title("Vessel Investment IRR Calculator")

st.sidebar.header("Input Parameters")

# Inputs
vessel_type = st.sidebar.selectbox("Vessel Type", ["Suezmax", "Aframax"])
purchase_price = st.sidebar.number_input("Purchase Price (USD)", min_value=0, value=50000000)
opex_day = st.sidebar.number_input("Opex (USD/day)", min_value=0, value=10000)
opex_growth = st.sidebar.number_input("Opex Growth Rate (% per year)", min_value=0.0, value=2.0)
dd_cost = st.sidebar.number_input("Dry Dock Cost (USD, optional)", min_value=0, value=0)
dd_year = st.sidebar.number_input("Dry Dock Year (optional)", min_value=0, value=0)
investment_term = st.sidebar.selectbox("Investment Term (years)", [5, 10])
three_yr_tc = st.sidebar.number_input("3yr TC at Sale Year (USD/day)", min_value=0, value=30000)

# Mortgage and loan parameters
mortgage_percent = st.sidebar.number_input("Mortgage Percentage (%)", min_value=0.0, max_value=100.0, value=60.0)
loan_interest_rate = st.sidebar.number_input("Loan Interest Rate (% per year)", min_value=0.0, value=5.0)
loan_arrangement_fee = st.sidebar.number_input("Loan Arrangement Fee (USD)", min_value=0, value=100000)
loan_repayment_term = st.sidebar.number_input("Loan Repayment Time (Years)", min_value=1, max_value=10, value=5)
sale_commission_rate = 1.0  # 1% sale commission

# Earnings inputs
earn_years_1_3 = st.sidebar.number_input("Earnings Estimate Years 1-3 (USD/day)", min_value=0, value=25000)
earn_years_4_5 = st.sidebar.number_input("Earnings Estimate Years 4-5 (USD/day)", min_value=0, value=27000)
if investment_term == 10:
    earn_years_6_10 = st.sidebar.number_input("Earnings Estimate Years 6-10 (USD/day)", min_value=0, value=29000)

# Calculate resale price
resale_price = estimate_resale_price(vessel_type, investment_term, three_yr_tc)
resale_price_net = resale_price * (1 - sale_commission_rate / 100)

# Build cash flows
initial_equity = purchase_price * (1 - mortgage_percent / 100)
loan_amount = purchase_price * (mortgage_percent / 100)
annual_loan_payment = (loan_amount * loan_interest_rate / 100) / (1 - (1 + loan_interest_rate / 100) ** (-loan_repayment_term))

cash_flows = [-initial_equity - loan_arrangement_fee]
cf_table = [{"Year": 0, "Cash Flow (USD)": -initial_equity - loan_arrangement_fee, "Notes": "Equity + Loan Fee"}]

opex = opex_day * 365
for year in range(1, investment_term + 1):
    if year <= 3:
        earnings = earn_years_1_3 * 365
    elif year <= 5:
        earnings = earn_years_4_5 * 365
    else:
        earnings = earn_years_6_10 * 365

    net_cash = earnings - opex
    note = "Earnings - Opex"

    # Deduct loan payment if within loan term
    if year <= loan_repayment_term:
        net_cash -= annual_loan_payment
        note += " - Loan Payment"

    # Deduct DD cost if this is the DD year
    if dd_year == year and dd_cost > 0:
        net_cash -= dd_cost
        note += " - DD Cost"

    # Add net resale price in final year
    if year == investment_term:
        net_cash += resale_price_net
        note += " + Net Resale Value"

    cash_flows.append(net_cash)
    cf_table.append({"Year": year, "Cash Flow (USD)": net_cash, "Notes": note})

    # Increase opex for next year
    opex *= (1 + opex_growth / 100)

# Calculate IRR
irr_result = calculate_irr(cash_flows)

st.header("Results")
st.metric("Internal Rate of Return (IRR)", f"{irr_result:.2f}%")
st.metric("Estimated Net Resale Price", f"${resale_price_net:,.0f}")

# Always create cf_df
cf_df = pd.DataFrame(cf_table)

# Show cash flow table
show_cf = st.checkbox("Show Cash Flows Table")
if show_cf:
    st.dataframe(cf_df)

# Option to export
export = st.checkbox("Download Cash Flow as CSV")
if export:
    csv = cf_df.to_csv(index=False).encode('utf-8')
    st.download_button("Download CSV", data=csv, file_name="cash_flows.csv", mime="text/csv")
