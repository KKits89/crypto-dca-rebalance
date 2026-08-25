import streamlit as st
import yfinance as yf
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
import numpy as np
import requests
from datetime import datetime
from streamlit_autorefresh import st_autorefresh
import gspread
from google.oauth2.service_account import Credentials

# --- ΡΥΘΜΙΣΗ ΣΕΛΙΔΑΣ ---
st.set_page_config(layout="wide", page_title="Crypto DCA Pro Terminal", page_icon="⚡")

# --- CUSTOM PROFESSIONAL CSS (TERMINAL / FINTECH LOOK) ---
st.markdown("""
<style>
    .stApp {
        background-color: #0e1117;
        color: #e6e6e6;
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
    }
    
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}

    .metric-card {
        background-color: #161b22;
        border: 1px solid #30363d;
        border-radius: 6px;
        padding: 16px;
        margin-bottom: 12px;
    }
    
    h1, h2, h3 {
        color: #f0f6fc;
        font-weight: 600;
        letter-spacing: -0.5px;
    }

    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
        background-color: #0e1117;
        padding: 4px 0;
    }
    .stTabs [data-baseweb="tab"] {
        background-color: #161b22;
        border-radius: 4px;
        color: #8b949e;
        border: 1px solid #30363d;
        padding: 8px 16px;
        font-weight: 500;
    }
    .stTabs [aria-selected="true"] {
        background-color: #21262d !important;
        color: #58a6ff !important;
        border-color: #58a6ff !important;
    }

    .stButton>button {
        background-color: #21262d;
        color: #c9d1d9;
        border: 1px solid #30363d;
        border-radius: 6px;
        font-weight: 500;
        transition: all 0.2s ease;
    }
    .stButton>button:hover {
        background-color: #30363d;
        border-color: #8b949e;
        color: #ffffff;
    }

    dataframe {
        border-radius: 6px;
        border: 1px solid #30363d;
    }
</style>
""", unsafe_allow_html=True)

# --- ΑΥΤΟΜΑΤΗ ΑΝΑΝΕΩΣΗ ΑΝΑ 1 ΛΕΠΤΟ ---
st_autorefresh(interval=60 * 1000, key="datarefresh")

st.title("⚡ Crypto DCA & Smart Terminal")

# --- GOOGLE SHEETS SETUP ---
def get_g_sheet():
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds_dict = dict(st.secrets["gcp_service_account"])
    creds = Credentials.from_service_account_info(creds_dict, scopes=scope)
    client = gspread.authorize(creds)
    sheet = client.open("CryptoPortfolio").sheet1 
    return sheet

@st.cache_data(ttl=10)
def load_transactions_from_sheet():
    try:
        sheet = get_g_sheet()
        data_rows = sheet.get_all_records()
        
        if not data_rows:
            sheet.append_row(["Date", "Asset", "Amount", "USD_Cost"])
            return pd.DataFrame(columns=["Date", "Asset", "Amount", "USD_Cost"])
            
        df = pd.DataFrame(data_rows)
        df.columns = [str(col).strip().capitalize() for col in df.columns]
        if 'Usd_cost' in df.columns and 'USD_Cost' not in df.columns:
            df.rename(columns={'Usd_cost': 'USD_Cost'}, inplace=True)
            
        for col in ['Amount', 'USD_Cost']:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col].astype(str).str.replace(',', ''), errors='coerce').fillna(0.0)
            elif col.lower() in df.columns:
                df[col.lower()] = pd.to_numeric(df[col.lower()].astype(str).str.replace(',', ''), errors='coerce').fillna(0.0)
                
        return df
    except Exception as e:
        st.error(f"Σφάλμα σύνδεσης με το Google Sheet: {e}")
        return pd.DataFrame(columns=["Date", "Asset", "Amount", "USD_Cost"])

def get_latest_transaction_date(df):
    if not df.empty:
        for col in df.columns:
            if 'date' in col.lower():
                valid_dates = df[col].dropna()
                if not valid_dates.empty:
                    return str(valid_dates.max())
    return "N/A"

# --- SIDEBAR: ΡΥΘΜΙΣΕΙΣ & ΚΑΤΑΧΩΡΗΣΗ (BUY / SELL) ---
st.sidebar.markdown("### ⚙️ Trade & Execution")

new_cash_to_invest = st.sidebar.number_input("Cash to Invest Today ($)", value=0.0, step=10.0)

st.sidebar.markdown("---")
st.sidebar.markdown("### 📝 New Order Entry")

raw_df_initial = load_transactions_from_sheet()
latest_date = get_latest_transaction_date(raw_df_initial)
st.sidebar.caption(f"📅 Last Transaction: **{latest_date}**")

tx_type = st.sidebar.radio("Order Type:", ["🟢 BUY", "🔴 SELL"], horizontal=True)

asset_input = st.sidebar.text_input("Asset Ticker", "BTC").upper().strip()
amount_input = st.sidebar.number_input("Amount", value=0.0, format="%.6f")
cost_input = st.sidebar.number_input("USD Total ($)", value=0.0, format="%.2f")

if st.sidebar.button("Execute Order"):
    if amount_input > 0 and cost_input > 0 and asset_input:
        t_date = datetime.now().strftime("%Y-%m-%d")
        
        final_amount = -amount_input if "SELL" in tx_type else amount_input
        final_cost = -cost_input if "SELL" in tx_type else cost_input
        
        try:
            sheet = get_g_sheet()
            sheet.append_row([t_date, asset_input, f"{final_amount:.8f}", f"{final_cost:.2f}"])
            st.cache_data.clear()
            st.sidebar.success("Order logged successfully!")
            st.rerun()
        except Exception as e:
            st.sidebar.error(f"Execution Error: {e}")
    else:
        st.sidebar.error("Please fill valid asset, amount and USD cost (> 0).")

# --- ΔΙΚΛΕΙΔΑ ΑΣΦΑΛΕΙΑΣ: ΕΜΦΑΝΙΣΗ & UNDO ΤΕΛΕΥΤΑΙΑΣ ΕΓΓΡΑΦΗΣ ---
st.sidebar.markdown("---")
st.sidebar.markdown("### 🛡️ Risk & Undo Last")

raw_df_check = load_transactions_from_sheet()

if not raw_df_check.empty:
    last_row = raw_df_check.iloc[-1]
    st.sidebar.markdown(
        f"<div style='font-size: 12px; color: #8b949e; background: #161b22; padding: 8px; border-radius: 4px; border: 1px solid #30363d;'>"
        f"<b>Last Entry:</b> {last_row.get('Date', 'N/A')} | {last_row.get('Asset', 'N/A')}<br>"
        f"<b>Amt:</b> {last_row.get('Amount', 'N/A')} | <b>Cost:</b> ${last_row.get('USD_Cost', 'N/A')}"
        f"</div>", 
        unsafe_allow_html=True
    )
    
    if st.sidebar.button("↩️ Revert Last Entry"):
        try:
            sheet = get_g_sheet()
            all_values = sheet.get_all_values()
            if len(all_values) > 1:
                row_to_delete = len(all_values)
                sheet.delete_rows(row_to_delete)
                st.cache_data.clear()
                st.sidebar.success("Last transaction reverted.")
                st.rerun()
            else:
                st.sidebar.warning("No transactions left to delete.")
        except Exception as e:
            st.sidebar.error(f"Error reverting: {e}")

# --- ΔΙΑΒΑΣΜΑ ΠΟΡΤΟΦΟΛΙΟΥ ΑΠΟ ΤΟ GOOGLE SHEET ---
def load_portfolio():
    df = load_transactions_from_sheet()
    if df.empty:
        return {}
    
    col_asset = next((c for c in df.columns if 'asset' in c.lower()), 'Asset')
    col_amount = next((c for c in df.columns if 'amount' in c.lower()), 'Amount')
    col_cost = next((c for c in df.columns if 'cost' in c.lower() or 'usd' in c.lower()), 'USD_Cost')
    
    summary = df.groupby(col_asset).agg({col_amount: 'sum', col_cost: 'sum'}).to_dict('index')

    default_settings = {
        "BTC": {"target_pct": 0.55, "cmc_slug": "bitcoin"},
        "ETH": {"target_pct": 0.20, "cmc_slug": "ethereum"},
        "SOL": {"target_pct": 0.15, "cmc_slug": "solana"},
        "ZEC": {"target_pct": 0.05, "cmc_slug": "zcash"},
        "HYPE": {"target_pct": 0.05, "cmc_slug": "hyperliquid"}
    }

    formatted_summary = {}
    for asset, data in summary.items():
        amt = float(data[col_amount])
        cst = float(data[col_cost])
        
        formatted_summary[asset] = {
            'total_cost': cst,
            'amount': amt
        }
        if asset in default_settings:
            formatted_summary[asset].update(default_settings[asset])
        else:
            formatted_summary[asset]['target_pct'] = 0.0
            formatted_summary[asset]['cmc_slug'] = asset.lower()
            
    return formatted_summary

portfolio_data = load_portfolio()

@st.cache_data(ttl=25)
def get_cmc_prices(symbols_list):
    api_key = st.secrets["CMC_API_KEY"]
    url = "https://pro-api.coinmarketcap.com/v1/cryptocurrency/quotes/latest"
    symbols_str = ",".join(symbols_list)
    
    parameters = {"symbol": symbols_str, "convert": "USD"}
    headers = {"Accepts": "application/json", "X-CMC_PRO_API_KEY": api_key}
    
    try:
        response = requests.get(url, headers=headers, params=parameters)
        data = response.json()
        prices = {}
        for sym in symbols_list:
            if sym in data.get("data", {}):
                prices[sym] = data["data"][sym]["quote"]["USD"]["price"]
        return prices
    except Exception as e:
        return {}

all_symbols = list(portfolio_data.keys())
cmc_prices = get_cmc_prices(all_symbols) if all_symbols else {}

def get_rsi(series, period=14):
    delta = series.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

def calculate_new_avg(old_cost, old_amount, new_money, current_price):
    if old_amount <= 0:
        return current_price
    if new_money <= 0 or current_price <= 0:
        return old_cost / old_amount if old_amount > 0 else 0
    new_amount = new_money / current_price
    return (old_cost + new_money) / (old_amount + new_amount)

try:
    eur_ticker = yf.Ticker("EURUSD=X")
    eur_rate = eur_ticker.history(period="1d")['Close'].iloc[-1]
    usd_to_eur = 1.0 / eur_rate
except:
    usd_to_eur = 0.92

current_values = {}
total_current_portfolio = 0
total_invested_cost = sum(d["total_cost"] for d in portfolio_data.values() if d["amount"] > 0) if portfolio_data else 0

for asset, data in portfolio_data.items():
    if data["amount"] <= 0:
        continue 
        
    price = cmc_prices.get(asset, data["total_cost"] / data["amount"] if data["amount"] > 0 else 0)
    
    rsi = 50.0
    sma_50 = price
    
    try:
        ticker_str = f"{asset}-USD"
        hist = yf.Ticker(ticker_str).history(period="100d")
        if hist.empty or len(hist) < 15:
            hist = yf.Ticker(asset).history(period="100d")
            
        if not hist.empty and len(hist) >= 50:
            sma_50 = hist['Close'].tail(50).mean()
        else:
            sma_50 = price
            
        if not hist.empty and len(hist) >= 15:
            rsi = get_rsi(hist['Close']).iloc[-1]
        else:
            avg_p = (data["total_cost"] / data["amount"]) if data["amount"] > 0 else price
            if price < avg_p:
                rsi = 40.0
            elif price > avg_p:
                rsi = 60.0
            else:
                rsi = 50.0
    except:
        sma_50 = price
        rsi = 50.0

    val = data["amount"] * price
    avg_price = (data["total_cost"] / data["amount"]) if data["amount"] > 0 else 0
    pnl_usd = val - data["total_cost"]
    pnl_pct = (pnl_usd / data["total_cost"]) * 100 if data["total_cost"] > 0 else 0
    is_healthy_dip = price >= sma_50

    current_values[asset] = {
        "price": price,
        "avg_price": avg_price,
        "current_val": val,
        "pnl_usd": pnl_usd,
        "pnl_pct": pnl_pct,
        "sma_50": sma_50,
        "rsi": rsi,
        "is_healthy_dip": is_healthy_dip
    }
    total_current_portfolio += val

new_total_portfolio = total_current_portfolio + new_cash_to_invest
tot_eur = total_current_portfolio * usd_to_eur
total_pnl_usd = total_current_portfolio - total_invested_cost
pnl_eur = total_pnl_usd * usd_to_eur
total_pnl_pct = (total_pnl_usd / total_invested_cost) * 100 if total_invested_cost > 0 else 0

strict_allocations = {}
for asset, data in portfolio_data.items():
    if data["amount"] <= 0:
        continue
    cur_val = current_values[asset]["current_val"]
    ideal_val = new_total_portfolio * data["target_pct"]
    strict_allocations[asset] = max(0, ideal_val - cur_val)

total_strict_weight = sum(strict_allocations.values())
if total_strict_weight == 0:
    total_strict_weight = 1.0

smart_allocations = {}
total_smart_weight = 0
for asset, data in portfolio_data.items():
    if data["amount"] <= 0:
        continue
    cur_val = current_values[asset]["current_val"]
    ideal_val = new_total_portfolio * data["target_pct"]
    base_need = max(0, ideal_val - cur_val)
    pnl = current_values[asset]["pnl_usd"]
    stats = current_values[asset]

    if pnl < 0 and stats["is_healthy_dip"]:
        base_bonus = min(abs(pnl) / total_current_portfolio * 2, 0.5) if total_current_portfolio > 0 else 0
        rsi_multiplier = 1.3 if stats["rsi"] < 40 else 1.0
        pnl_weight = 1.0 + (base_bonus * rsi_multiplier)
    else:
        pnl_weight = 1.0

    smart_weight = base_need * pnl_weight
    smart_allocations[asset] = smart_weight
    total_smart_weight += smart_weight

if total_smart_weight == 0:
    total_smart_weight = 1.0

# --- TABS ---
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "📊 Portfolio Dashboard", 
    "📈 Performance Charts", 
    "📋 Ledger & Trades", 
    "🛠 Simulator",
    "🛡️ Risk & Exit Strategy"
])

with tab1:
    col1, col2, col3 = st.columns(3)
    col1.metric("Total Asset Value", f"${total_current_portfolio:,.2f}", f"€{tot_eur:,.2f}")
    col2.metric("Total Net PnL", f"${total_pnl_usd:+,.2f}", f"{total_pnl_pct:+.2f}% ({pnl_eur:+,.2f}€)")
    col3.metric("Allocatable Cash", f"${new_cash_to_invest:,.2f}")

    st.markdown("---")
    st.markdown("### 📊 Asset Allocation & Execution Matrix")

    table_data = []
    for asset, data in portfolio_data.items():
        if data["amount"] <= 0:
            continue
        stats = current_values[asset]
        strict_share = strict_allocations.get(asset, 0) / total_strict_weight
        strict_buy = new_cash_to_invest * strict_share
        smart_share = smart_allocations.get(asset, 0) / total_smart_weight
        smart_buy = new_cash_to_invest * smart_share
        
        new_avg = calculate_new_avg(data['total_cost'], data['amount'], smart_buy, stats['price'])
        pnl_str = f"{stats['pnl_usd']:+.2f}$ ({stats['pnl_pct']:+.2f}%)"

        slug = data.get("cmc_slug", asset.lower())
        cmc_url = f"https://coinmarketcap.com/currencies/{slug}/"

        table_data.append({
            "Asset": cmc_url,
            "Name": asset,
            "Amount": f"{data['amount']:.6f} ({data['total_cost']:.2f}$)",
            "Avg Price": f"${stats['avg_price']:.2f}",
            "New Avg": f"${new_avg:.2f}",
            "Curr Price": f"${stats['price']:.2f}",
            "SMA 50": f"${stats['sma_50']:.2f}",
            "RSI": f"{stats['rsi']:.1f}",
            "PnL": pnl_str,
            "Strict Buy": f"${strict_buy:.2f}",
            "Smart Buy": f"${smart_buy:.2f}"
        })

    df_metrics = pd.DataFrame(table_data)
    if not df_metrics.empty:
        df_metrics.index = df_metrics.index + 1
    
    st.dataframe(
        df_metrics,
        width='stretch',
        column_config={
            "Asset": st.column_config.LinkColumn(
                "Asset Link",
                help="Open CoinMarketCap",
                display_text=r"https://coinmarketcap.com/currencies/(.*?)/"
            ),
            "Name": None
        }
    )

with tab2:
    st.markdown("### 📈 Historical Valuation & Metrics")
    
    raw_tx_df = load_transactions_from_sheet()
    if not raw_tx_df.empty:
        try:
            date_col = next((c for c in raw_tx_df.columns if 'date' in c.lower()), None)
            cost_col = next((c for c in raw_tx_df.columns if 'cost' in c.lower() or 'usd' in c.lower()), None)
            
            if date_col and cost_col:
                raw_tx_df[date_col] = pd.to_datetime(raw_tx_df[date_col])
                daily_costs = raw_tx_df.groupby(date_col)[cost_col].sum().reset_index()
                daily_costs = daily_costs.sort_values(by=date_col)
                daily_costs['Cumulative_Cost'] = daily_costs[cost_col].cumsum()
                
                min_date = daily_costs[date_col].min()
                max_date = pd.to_datetime(datetime.now().strftime("%Y-%m-%d"))
                
                full_calendar = pd.date_range(start=min_date, end=max_date)
                calendar_df = pd.DataFrame({date_col: full_calendar})
                
                timeline_df = pd.merge(calendar_df, daily_costs[[date_col, 'Cumulative_Cost']], on=date_col, how='left')
                timeline_df['Cumulative_Cost'] = timeline_df['Cumulative_Cost'].ffill().fillna(0)
                
                days_count = len(timeline_df)
                if days_count > 1:
                    cost_start = timeline_df['Cumulative_Cost'].iloc[0]
                    timeline_df['Portfolio_Value'] = np.linspace(cost_start if cost_start > 0 else 1, total_current_portfolio, days_count)
                else:
                    timeline_df['Portfolio_Value'] = [total_current_portfolio]

                fig_timeline = go.Figure()
                
                fig_timeline.add_trace(go.Scatter(
                    x=timeline_df[date_col], 
                    y=timeline_df['Cumulative_Cost'],
                    mode='lines',
                    name='Invested Cost ($)',
                    line=dict(color='#8b949e', width=2)
                ))
                
                fig_timeline.add_trace(go.Scatter(
                    x=timeline_df[date_col], 
                    y=timeline_df['Portfolio_Value'],
                    mode='lines',
                    name='Portfolio Value ($)',
                    line=dict(color='#58a6ff', width=2.5),
                    fill='tonexty',
                    fillcolor='rgba(88, 166, 255, 0.05)'
                ))
                
                # Gridlines (διακεκομμένες γραμμές) στο timeline γράφημα
                fig_timeline.update_layout(
                    title="Portfolio Valuation vs Basis Cost",
                    xaxis_title="",
                    yaxis_title="USD ($)",
                    paper_bgcolor="#0e1117",
                    plot_bgcolor="#161b22",
                    font_color="#e6e6e6",
                    hovermode="x unified",
                    xaxis=dict(
                        type='date', 
                        gridcolor='#30363d', 
                        gridwidth=1, 
                        griddash='dash'
                    ),
                    yaxis=dict(
                        gridcolor='#30363d', 
                        gridwidth=1, 
                        griddash='dash'
                    )
                )
                st.plotly_chart(fig_timeline, width='stretch')
        except Exception as e:
            st.info(f"Timeline chart notice: {e}")

    st.markdown("---")
    col_chart1, col_chart2 = st.columns(2)
    
    with col_chart1:
        if current_values:
            # Official/Brand Colors based on uploaded logos:
            # BTC: Orange (#F7931A), ETH: Blue (#627EEA), SOL: Purple/Cyan gradient look, HYPE: Mint/Teal (#4EEDCC), ZEC: Yellow (#F4B728)
            brand_colors = {
                "BTC": "#F7931A",
                "ETH": "#627EEA",
                "SOL": "#9945FF",
                "HYPE": "#4EEDCC",
                "ZEC": "#F4B728"
            }
            
            assets_in_pie = list(current_values.keys())
            pie_colors = [brand_colors.get(asset, "#8b949e") for asset in assets_in_pie]
            
            fig_pie = px.pie(
                names=assets_in_pie,
                values=[info["current_val"] for info in current_values.values()],
                title="Asset Share Distribution",
                hole=0.5,
                color=assets_in_pie,
                color_discrete_map=brand_colors
            )
            fig_pie.update_layout(
                paper_bgcolor="#0e1117", 
                font_color="#e6e6e6",
                legend=dict(bgcolor="rgba(0,0,0,0)", bordercolor="#30363d")
            )
            st.plotly_chart(fig_pie, width='stretch')
        else:
            st.info("No assets available.")
        
    with col_chart2:
        if current_values:
            assets_list = list(current_values.keys())
            pnl_values = [info["pnl_usd"] for info in current_values.values()]
            colors = ['#238636' if v >= 0 else '#da3633' for v in pnl_values]
            
            fig_bar = go.Figure(data=[go.Bar(x=assets_list, y=pnl_values, marker_color=colors)])
            
            # Gridlines (διακεκομμένες γραμμές) στο PnL Bar Chart
            fig_bar.update_layout(
                title="PnL Breakdown per Asset ($)",
                paper_bgcolor="#0e1117",
                plot_bgcolor="#161b22",
                font_color="#e6e6e6",
                xaxis=dict(
                    gridcolor='#30363d', 
                    gridwidth=1, 
                    griddash='dash'
                ),
                yaxis=dict(
                    gridcolor='#30363d', 
                    gridwidth=1, 
                    griddash='dash'
                )
            )
            st.plotly_chart(fig_bar, width='stretch')
        else:
            st.info("No data available.")

with tab3:
    st.markdown("### 📋 Transaction Ledgers")
    raw_df = load_transactions_from_sheet()
    if not raw_df.empty:
        raw_df.index = raw_df.index + 1
        st.dataframe(raw_df, width='stretch')
    else:
        st.info("No recorded transactions.")

with tab4:
    st.markdown("### 🛠 Rebalancing Simulator")
    sim_cash = st.number_input("Simulator Capital ($)", value=100.0, step=10.0, key="sim_cash")
    
    new_targets = {}
    col_s1, col_s2 = st.columns(2)
    
    for asset, data in portfolio_data.items():
        if data["amount"] <= 0:
            continue
        new_targets[asset] = col_s1.slider(
            f"Target % [{asset}]", 
            0.0, 1.0, float(data.get("target_pct", 0.1)), key=f"slider_{asset}"
        )
        
    if st.button("Run Simulation"):
        sim_results = []
        for asset, data in portfolio_data.items():
            if data["amount"] <= 0:
                continue
            stats = current_values[asset]
            simulated_buy = sim_cash * new_targets[asset]
            old_avg = stats['avg_price']
            new_avg = calculate_new_avg(data['total_cost'], data['amount'], simulated_buy, stats['price'])
            
            sim_results.append({
                "Asset": asset,
                "Old Avg": f"${old_avg:.2f}",
                "Sim Buy": f"${simulated_buy:.2f}",
                "New Avg Price": f"${new_avg:.2f}"
            })
        col_s2.table(pd.DataFrame(sim_results))
        col_s2.success("Simulation computed.")

with tab5:
    st.markdown("### 🛡️ Risk & Exit Strategy Terminal")
    calc_basis = st.radio("Calculation Basis:", ["Current Price (Dynamic)", "Average Cost (Static)"], horizontal=True)
    
    st.markdown("---")
    
    risk_table_data = []
    
    for asset, data in portfolio_data.items():
        if data["amount"] <= 0:
            continue
        stats = current_values[asset]
        curr_p = stats['price']
        avg_p = stats['avg_price']
        total_amt = data['amount']
        total_cst = data['total_cost']
        
        base_price = curr_p if "Current" in calc_basis else avg_p
        basis_label = "Current Price" if "Current" in calc_basis else "Avg Cost"
        
        with st.container():
            col_info, col_sl, col_tp = st.columns([1.5, 2, 2])
            
            with col_info:
                st.markdown(f"#### {asset}")
                st.markdown(f"**Curr:** `${curr_p:,.2f}`")
                st.markdown(f"**Avg:** `${avg_p:,.2f}`")
                st.markdown(f"**Hold:** `{total_amt:.4f}`")
                
            with col_sl:
                st.markdown(f"🔻 **Stop Loss** ({basis_label})")
                sl_pct = st.slider(f"SL % ({asset})", -50.0, -1.0, -10.0, step=1.0, key=f"sl_{asset}")
                sl_price = base_price * (1 + sl_pct / 100.0)
                
                sl_portfolio_value = total_amt * sl_price
                sl_pnl_usd = sl_portfolio_value - total_cst
                sl_pnl_eur = sl_pnl_usd * usd_to_eur
                sl_pnl_pct = (sl_pnl_usd / total_cst) * 100 if total_cst > 0 else 0
                
                st.markdown(f"Target: **`${sl_price:,.2f}`**")
                st.markdown(f"PnL: **`${sl_pnl_usd:+,.2f}` (`{sl_pnl_pct:+.2f}%`)** | `€{sl_pnl_eur:+,.2f}`")
                
            with col_tp:
                st.markdown(f"🎯 **Take Profit** ({basis_label})")
                tp_pct = st.slider(f"TP % ({asset})", 5.0, 300.0, 50.0, step=5.0, key=f"tp_{asset}")
                tp_price = base_price * (1 + tp_pct / 100.0)
                
                tp_portfolio_value = total_amt * tp_price
                tp_pnl_usd = tp_portfolio_value - total_cst
                tp_pnl_eur = tp_pnl_usd * usd_to_eur
                tp_pnl_pct = (tp_pnl_usd / total_cst) * 100 if total_cst > 0 else 0
                
                st.markdown(f"Target: **`${tp_price:,.2f}`**")
                st.markdown(f"PnL: **`${tp_pnl_usd:+,.2f}` (`{tp_pnl_pct:+.2f}%`)** | `€{tp_pnl_eur:+,.2f}`")
            
            if curr_p <= sl_price:
                status = "🚨 STOP LOSS TRIGGERED"
            elif curr_p >= tp_price:
                status = "🎯 TAKE PROFIT REACHED"
            else:
                status = "🟢 ACTIVE"
                
            if sl_price < curr_p:
                distance_to_sl_pct = ((curr_p - sl_price) / curr_p) * 100
            else:
                distance_to_sl_pct = 0.0
                
            st.markdown(f"**Status:** `{status}` | **SL Distance:** `{distance_to_sl_pct:.1f}%`")
            
            risk_table_data.append({
                "Asset": asset,
                "Basis": basis_label,
                "Current Price": f"${curr_p:,.2f}",
                "Stop Loss Target": f"${sl_price:,.2f} ({sl_pct}%)",
                "SL PnL ($)": f"${sl_pnl_usd:+,.2f} ({sl_pnl_pct:+.2f}%)",
                "Take Profit Target": f"${tp_price:,.2f} (+{tp_pct}%)",
                "TP PnL ($)": f"${tp_pnl_usd:+,.2f} ({tp_pnl_pct:+.2f}%)",
                "Status": status
            })
            
            st.markdown("---")

    st.markdown("#### 🚨 Risk Alerts & Summary")
    df_risk = pd.DataFrame(risk_table_data)
    if not df_risk.empty:
        for idx, row in df_risk.iterrows():
            if "TRIGGERED" in row["Status"]:
                st.error(f"🚨 **{row['Asset']}** — {row['Status']} at {row['Stop Loss Target']} | Est PnL: {row['SL PnL ($)']}")
            elif "REACHED" in row["Status"]:
                st.success(f"🎯 **{row['Asset']}** — {row['Status']} at {row['Take Profit Target']} | Est PnL: {row['TP PnL ($)']}")
                
        with st.expander("View Full Risk Parameters Matrix"):
            df_risk.index = df_risk.index + 1
            st.dataframe(df_risk, width='stretch')
