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

# --- CUSTOM PROFESSIONAL FINTECH UI & CSS (MODERN TERMINAL LOOK) ---
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

    .stApp {
        background-color: #0b0f19;
        color: #f3f4f6;
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
    }
    
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}

    /* Metric Cards Styling */
    div[data-testid="stMetric"] {
        background-color: #111827;
        border: 1px solid #1f2937;
        padding: 18px 20px;
        border-radius: 10px;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
        transition: transform 0.2s ease, border-color 0.2s ease;
    }
    div[data-testid="stMetric"]:hover {
        border-color: #3b82f6;
        transform: translateY(-2px);
    }
    div[data-testid="stMetric"] label {
        color: #9ca3af !important;
        font-weight: 500;
        font-size: 0.875rem !important;
    }
    div[data-testid="stMetric"] div[data-testid="stMetricValue"] {
        color: #f9fafb !important;
        font-weight: 700;
        font-size: 1.5rem !important;
    }

    /* Headings */
    h1, h2, h3, h4 {
        color: #f9fafb !important;
        font-weight: 650 !important;
        letter-spacing: -0.025em;
    }

    p, span, label, div {
        color: #d1d5db;
    }

    /* Tabs Styling */
    .stTabs [data-baseweb="tab-list"] {
        gap: 10px;
        background-color: #0b0f19;
        padding: 6px 0;
        border-bottom: 1px solid #1f2937;
    }
    .stTabs [data-baseweb="tab"] {
        background-color: #111827;
        border-radius: 8px;
        color: #9ca3af;
        border: 1px solid #1f2937;
        padding: 10px 18px;
        font-weight: 500;
        font-size: 0.9rem;
        transition: all 0.2s ease;
    }
    .stTabs [data-baseweb="tab"]:hover {
        background-color: #1f2937;
        color: #f3f4f6;
    }
    .stTabs [aria-selected="true"] {
        background-color: #1d4ed8 !important;
        color: #ffffff !important;
        border-color: #3b82f6 !important;
        box-shadow: 0 0 15px rgba(59, 130, 246, 0.3);
    }

    /* Buttons Styling */
    .stButton>button {
        background: linear-gradient(135deg, #1f2937 0%, #111827 100%);
        color: #f3f4f6;
        border: 1px solid #374151;
        border-radius: 8px;
        font-weight: 600;
        padding: 0.5rem 1rem;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
    }
    .stButton>button:hover {
        background: linear-gradient(135deg, #374151 0%, #1f2937 100%);
        border-color: #60a5fa;
        color: #ffffff;
        box-shadow: 0 4px 12px rgba(59, 130, 246, 0.2);
    }

    /* Sidebar Customization */
    section[data-testid="stSidebar"] {
        background-color: #0d1322;
        border-right: 1px solid #1f2937;
    }
    section[data-testid="stSidebar"] hr {
        border-color: #1f2937;
    }

    /* Inputs & Selectboxes */
    .stTextInput input, .stNumberInput input, .stSelectbox div[data-baseweb="select"] {
        background-color: #111827 !important;
        border: 1px solid #374151 !important;
        color: #f3f4f6 !important;
        border-radius: 8px !important;
    }

    /* Sliders Styling (Slate Grey) */
    span[data-baseweb="tag"] {
        background-color: #1f2937 !important;
        color: #e5e7eb !important;
    }
    div.stSlider > div[data-baseweb="slider"] div[role="slider"] {
        background-color: #9ca3af !important;
        border-color: #f3f4f6 !important;
    }
    div.stSlider > div[data-baseweb="slider"] div > div > div {
        background-color: #4b5563 !important;
    }
</style>
""", unsafe_allow_html=True)

# --- ΑΥΤΟΜΑΤΗ ΑΝΑΝΕΩΣΗ ΑΝΑ 1 ΛΕΠΤΟ ---
st_autorefresh(interval=60 * 1000, key="datarefresh")

st.markdown("# ⚡ Crypto DCA & Smart Terminal")

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
        st.error(f"⚠️ Σφάλμα σύνδεσης με το Google Sheet: {e}")
        return pd.DataFrame(columns=["Date", "Asset", "Amount", "USD_Cost"])

def get_latest_transaction_date(df):
    if not df.empty:
        for col in df.columns:
            if 'date' in col.lower():
                valid_dates = df[col].dropna()
                if not valid_dates.empty:
                    return str(valid_dates.max())
    return "N/A"

# --- ΑΡΧΙΚΟ ΦΟΡΤΩΜΑ ΓΙΑ ΕΝΤΟΠΙΣΜΟ ASSETS ---
raw_df_initial = load_transactions_from_sheet()
unique_assets_in_sheet = []
if not raw_df_initial.empty:
    col_asset = next((c for c in raw_df_initial.columns if 'asset' in c.lower()), 'Asset')
    unique_assets_in_sheet = [str(x).upper().strip() for x in raw_df_initial[col_asset].unique() if str(x).strip() != '']

default_slugs = {
    "BTC": "bitcoin",
    "ETH": "ethereum",
    "SOL": "solana",
    "ZEC": "zcash",
    "HYPE": "hyperliquid",
    "PUMP": "pump-fun"
}

# --- SIDEBAR: ΡΥΘΜΙΣΕΙΣ & ΚΑΤΑΧΩΡΗΣΗ ---
st.sidebar.markdown("### ⚙️ Trade & Execution Engine")

new_cash_to_invest = st.sidebar.number_input("💵 Cash to Invest Today ($)", value=0.0, step=10.0)

st.sidebar.markdown("---")
st.sidebar.markdown("### 📝 Order & Loss Management")

latest_date = get_latest_transaction_date(raw_df_initial)
st.sidebar.caption(f"📅 Last Transaction: **{latest_date}**")

# Mode selection: Buy/Sell vs External Burn/Loss/Withdrawal
action_mode = st.sidebar.radio("Action Type:", ["📥 Buy / 📤 Standard Sell", "🔥 External Loss / Poker / Burn"], horizontal=False)

if "Standard" in action_mode:
    tx_type = st.sidebar.radio("Order Direction:", ["🟢 BUY", "🔴 SELL"], horizontal=True)
    asset_input = st.sidebar.text_input("Coin Ticker", "BTC").upper().strip()
    amount_input = st.sidebar.number_input("Amount", value=0.0, format="%.6f")
    cost_input = st.sidebar.number_input("USD Total ($)", value=0.0, format="%.2f")

    if st.sidebar.button("🚀 Execute Order"):
        if amount_input > 0 and cost_input > 0 and asset_input:
            t_date = datetime.now().strftime("%Y-%m-%d")
            final_amount = -amount_input if "SELL" in tx_type else amount_input
            final_cost = -cost_input if "SELL" in tx_type else cost_input
            
            try:
                sheet = get_g_sheet()
                sheet.append_row([t_date, asset_input, f"{final_amount:.8f}", f"{final_cost:.2f}"])
                st.cache_data.clear()
                st.sidebar.success("✅ Order logged successfully!")
                st.rerun()
            except Exception as e:
                st.sidebar.error(f"⚠️ Execution Error: {e}")
        else:
            st.sidebar.error("⚠️ Please fill valid coin, amount and USD cost (> 0).")
else:
    st.sidebar.markdown("<small style='color: #9ca3af;'>Καταχώρισε απώλειες (π.χ. πόκερ, hacks, fees, δώρα) για να αφαιρεθούν σωστά τα coins και τα κόστη τους από το portfolio χωρίς να μπουν μετρητά στο ταμείο.</small>", unsafe_allow_html=True)
    burn_asset = st.sidebar.text_input("Coin Ticker to Remove", "BTC").upper().strip()
    burn_amount = st.sidebar.number_input("Amount to Remove", value=0.0, format="%.6f")
    burn_cost_lost = st.sidebar.number_input("Original USD Cost to Write Off ($)", value=0.0, format="%.2f")

    if st.sidebar.button("🔥 Log Loss / Withdrawal"):
        if burn_amount > 0 and burn_cost_lost > 0 and burn_asset:
            t_date = datetime.now().strftime("%Y-%m-%d")
            # Περνάμε αρνητικό amount και αρνητικό cost ώστε να αφαιρεθούν καθαρά από το summary
            try:
                sheet = get_g_sheet()
                sheet.append_row([t_date, burn_asset, f"-{burn_amount:.8f}", f"-{burn_cost_lost:.2f}"])
                st.cache_data.clear()
                st.sidebar.success("✅ Loss / Withdrawal logged successfully!")
                st.rerun()
            except Exception as e:
                st.sidebar.error(f"⚠️ Error: {e}")
        else:
            st.sidebar.error("⚠️ Fill valid coin, amount and written-off cost.")

st.sidebar.markdown("---")
st.sidebar.markdown("### 🛡️ Risk & Undo Last")

if not raw_df_initial.empty:
    last_row = raw_df_initial.iloc[-1]
    st.sidebar.markdown(
        f"<div style='font-size: 12px; color: #9ca3af; background: #111827; padding: 10px; border-radius: 8px; border: 1px solid #1f2937;'>"
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
                st.sidebar.success("✅ Last transaction reverted.")
                st.rerun()
            else:
                st.sidebar.warning("⚠️ No transactions left to delete.")
        except Exception as e:
            st.sidebar.error(f"⚠️ Error reverting: {e}")

# --- ΥΠΟΛΟΓΙΣΜΟΣ ΤΡΕΧΟΥΣΩΝ ΑΞΙΩΝ ΠΡΟΣΩΡΙΝΑ ---
@st.cache_data(ttl=25)
def get_cmc_prices_temp(symbols_list):
    api_key = st.secrets["CMC_API_KEY"]
    url = "https://pro-api.coinmarketcap.com/v1/cryptocurrency/quotes/latest"
    symbols_str = ",".join(symbols_list)
    try:
        response = requests.get(url, headers={"Accepts": "application/json", "X-CMC_PRO_API_KEY": api_key}, params={"symbol": symbols_str, "convert": "USD"})
        data = response.json()
        prices = {}
        for sym in symbols_list:
            if sym in data.get("data", {}):
                prices[sym] = data["data"][sym]["quote"]["USD"]["price"]
        return prices
    except:
        return {}

temp_df = load_transactions_from_sheet()
temp_portfolio_vals = {}
tot_val_temp = 0

if not temp_df.empty:
    c_asset = next((c for c in temp_df.columns if 'asset' in c.lower()), 'Asset')
    c_amount = next((c for c in temp_df.columns if 'amount' in c.lower()), 'Amount')
    c_cost = next((c for c in temp_df.columns if 'cost' in c.lower() or 'usd' in c.lower()), 'USD_Cost')
    summary_temp = temp_df.groupby(c_asset).agg({c_amount: 'sum', c_cost: 'sum'}).to_dict('index')
    
    prices_temp = get_cmc_prices_temp(list(summary_temp.keys()))
    for ast, dat in summary_temp.items():
        amt = float(dat[c_amount])
        cst = float(dat[c_cost])
        if amt > 0:
            p = prices_temp.get(ast, cst / amt if amt > 0 else 0)
            val = amt * p
            temp_portfolio_vals[ast] = val
            tot_val_temp += val
        else:
            temp_portfolio_vals[ast] = 0.0

# --- SIDEBAR: ΕΠΙΛΟΓΗ DCA ASSETS & TARGET ALLOCATION WEIGHTS ---
st.sidebar.markdown("---")
st.sidebar.markdown("### 🎯 Target Allocation Setup")
st.sidebar.caption("Επέλεξε ποια coins συμμετέχουν ενεργά στο DCA πλάνο σου.")

default_dca_selection = [ast for ast in unique_assets_in_sheet if ast != "PUMP"]
active_dca_assets = st.sidebar.multiselect(
    "Active DCA Coins (Core Portfolio):", 
    options=unique_assets_in_sheet, 
    default=default_dca_selection
)

st.sidebar.markdown("#### Target Weights (%) για τα DCA Coins")
target_weights = {}

tot_dca_val_temp = sum(temp_portfolio_vals.get(ast, 0.0) for ast in active_dca_assets)

for asset in active_dca_assets:
    val = temp_portfolio_vals.get(asset, 0.0)
    auto_pct = (val / tot_dca_val_temp * 100.0) if tot_dca_val_temp > 0 else (100.0 / len(active_dca_assets) if active_dca_assets else 0.0)
    
    target_weights[asset] = st.sidebar.slider(f"{asset} Target %", 0.0, 100.0, float(round(auto_pct, 1)), 1.0, key=f"weight_{asset}")

total_weight_sum = sum(target_weights.values())
if active_dca_assets:
    if abs(total_weight_sum - 100.0) > 0.01:
        st.sidebar.error(f"⚠️ Άθροισμα ποσοστών DCA: {total_weight_sum:.1f}% (Πρέπει να είναι ακριβώς 100%)!")
    else:
        st.sidebar.success(f"✅ Άθροισμα ποσοστών DCA: 100.0%")

# --- ΔΙΑΒΑΣΜΑ ΠΟΡΤΟΦΟΛΙΟΥ ΑΠΟ ΤΟ GOOGLE SHEET ---
def load_portfolio():
    df = load_transactions_from_sheet()
    if df.empty:
        return {}
    
    col_asset = next((c for c in df.columns if 'asset' in c.lower()), 'Asset')
    col_amount = next((c for c in df.columns if 'amount' in c.lower()), 'Amount')
    col_cost = next((c for c in df.columns if 'cost' in c.lower() or 'usd' in c.lower()), 'USD_Cost')
    
    summary = df.groupby(col_asset).agg({col_amount: 'sum', col_cost: 'sum'}).to_dict('index')

    formatted_summary = {}
    for asset, data in summary.items():
        amt = float(data[col_amount])
        cst = float(data[col_cost])
        
        assigned_pct = (target_weights.get(asset, 0.0) / 100.0) if asset in active_dca_assets else 0.0
        
        formatted_summary[asset] = {
            'total_cost': cst,
            'amount': amt,
            'target_pct': assigned_pct,
            'is_dca': asset in active_dca_assets,
            'cmc_slug': default_slugs.get(asset, asset.lower())
        }
            
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

@st.cache_data(ttl=300)
def get_fear_and_greed():
    try:
        res = requests.get("https://api.alternative.me/fng/?limit=1")
        data = res.json()
        return int(data["data"][0]["value"]), data["data"][0]["value_classification"]
    except:
        return 50, "Neutral"

all_symbols = list(portfolio_data.keys())
cmc_prices = get_cmc_prices(all_symbols) if all_symbols else {}
fng_value, fng_label = get_fear_and_greed()

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

def compute_smart_score(stats, fng):
    sc = 50
    if stats['rsi'] < 30:
        sc += 25
    elif stats['rsi'] < 42:
        sc += 15
    elif stats['rsi'] > 68:
        sc -= 25
    if stats['price'] <= stats['bb_lower']:
        sc += 20
    if fng < 30:
        sc += 15
    elif fng > 75:
        sc -= 15
    return max(0, min(100, sc))

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
    bb_lower = price * 0.95
    
    try:
        ticker_str = "HYPE32196-USD" if asset == "HYPE" else f"{asset}-USD"
        hist = yf.Ticker(ticker_str).history(period="100d")
        if hist.empty or len(hist) < 15:
            hist = yf.Ticker(asset).history(period="100d")
            
        if not hist.empty and len(hist) >= 50:
            sma_50 = hist['Close'].tail(50).mean()
        if not hist.empty and len(hist) >= 20:
            rolling_mean = hist['Close'].rolling(window=20).mean().iloc[-1]
            rolling_std = hist['Close'].rolling(window=20).std().iloc[-1]
            bb_lower = rolling_mean - (2 * rolling_std)
        if not hist.empty and len(hist) >= 15:
            rsi_series = get_rsi(hist['Close'])
            if not rsi_series.empty and not pd.isna(rsi_series.iloc[-1]):
                rsi = float(rsi_series.iloc[-1])
    except:
        pass

    val = data["amount"] * price
    avg_price = (data["total_cost"] / data["amount"]) if data["amount"] > 0 else 0
    pnl_usd = val - data["total_cost"]
    pnl_pct = (pnl_usd / data["total_cost"]) * 100 if data["total_cost"] > 0 else 0

    temp_stats = {
        "price": price,
        "avg_price": avg_price,
        "current_val": val,
        "pnl_usd": pnl_usd,
        "pnl_pct": pnl_pct,
        "sma_50": sma_50,
        "bb_lower": bb_lower,
        "rsi": rsi,
        "is_healthy_dip": price >= sma_50
    }
    temp_stats["score"] = compute_smart_score(temp_stats, fng_value)

    current_values[asset] = temp_stats
    total_current_portfolio += val

new_total_portfolio = total_current_portfolio + new_cash_to_invest
tot_eur = total_current_portfolio * usd_to_eur
total_pnl_usd = total_current_portfolio - total_invested_cost
pnl_eur = total_pnl_usd * usd_to_eur
total_pnl_pct = (total_pnl_usd / total_invested_cost) * 100 if total_invested_cost > 0 else 0

strict_allocations = {}
for asset, data in portfolio_data.items():
    if data["amount"] <= 0 or not data["is_dca"]:
        continue
    cur_val = current_values[asset]["current_val"]
    ideal_val = new_total_portfolio * data["target_pct"]
    strict_allocations[asset] = max(0, ideal_val - cur_val)

total_strict_weight = sum(strict_allocations.values()) or 1.0

smart_allocations = {}
total_smart_weight = 0
for asset, data in portfolio_data.items():
    if data["amount"] <= 0 or not data["is_dca"]:
        continue
    cur_val = current_values[asset]["current_val"]
    ideal_val = new_total_portfolio * data["target_pct"]
    base_need = max(0, ideal_val - cur_val)
    score = current_values[asset]["score"]
    score_multiplier = max(0.1, score / 50.0)
    
    smart_weight = base_need * score_multiplier
    smart_allocations[asset] = smart_weight
    total_smart_weight += smart_weight

total_smart_weight = total_smart_weight or 1.0

# --- TABS ---
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "📊 Portfolio Dashboard", 
    "📈 Performance Charts", 
    "📋 Ledger & Trades", 
    "🛠 Smart Advisor & Profit Engine",
    "🛡️ Risk & Exit Strategy"
])

with tab1:
    col1, col2, col3 = st.columns(3)
    col1.metric("Total Coin Value", f"${total_current_portfolio:,.2f}", f"€{tot_eur:,.2f}")
    col2.metric("Total Net PnL", f"${total_pnl_usd:+,.2f}", f"{total_pnl_pct:+.2f}% ({pnl_eur:+,.2f}€)")
    col3.metric("Allocatable Cash", f"${new_cash_to_invest:,.2f}")

    st.markdown("---")
    st.markdown("### 📊 Coin Allocation & Execution Matrix")

    table_data = []
    for asset, data in portfolio_data.items():
        if data["amount"] <= 0:
            continue
        stats = current_values[asset]
        
        if data["is_dca"]:
            strict_share = strict_allocations.get(asset, 0) / total_strict_weight
            strict_buy = new_cash_to_invest * strict_share
            smart_share = smart_allocations.get(asset, 0) / total_smart_weight
            smart_buy = new_cash_to_invest * smart_share
            new_avg = calculate_new_avg(data['total_cost'], data['amount'], smart_buy, stats['price'])
            strict_str = f"${strict_buy:.2f}"
            smart_str = f"${smart_buy:.2f}"
            new_avg_str = f"${new_avg:.2f}"
        else:
            strict_str = "— (External Play)"
            smart_str = "— (External Play)"
            new_avg_str = f"${stats['avg_price']:.2f}"

        pnl_str = f"{stats['pnl_usd']:+.2f}$ ({stats['pnl_pct']:+.2f}%)"
        slug = data.get("cmc_slug", asset.lower())
        cmc_url = f"https://coinmarketcap.com/currencies/{slug}/"

        table_data.append({
            "Coin": cmc_url,
            "Name": asset,
            "Invested_Numeric": data['total_cost'],
            "Amount": f"{data['amount']:.6f} ({data['total_cost']:.2f}$)",
            "Avg Price": f"${stats['avg_price']:.2f}",
            "New Avg": new_avg_str,
            "Curr Price": f"${stats['price']:.2f}",
            "SMA 50": f"${stats['sma_50']:.2f}",
            "RSI": f"{stats['rsi']:.1f}",
            "PnL": pnl_str,
            "Strict Buy": strict_str,
            "Smart Buy": smart_str
        })

    df_metrics = pd.DataFrame(table_data)
    if not df_metrics.empty:
        df_metrics = df_metrics.sort_values(by="Invested_Numeric", ascending=False)
        df_metrics = df_metrics.drop(columns=["Invested_Numeric"])
        df_metrics.index = range(1, len(df_metrics) + 1)
    
    st.dataframe(
        df_metrics,
        width='stretch',
        column_config={
            "Coin": st.column_config.LinkColumn(
                "Coin Link",
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
                    x=timeline_df[date_col], y=timeline_df['Cumulative_Cost'],
                    mode='lines', name='Invested Cost ($)', line=dict(color='#9ca3af', width=2)
                ))
                fig_timeline.add_trace(go.Scatter(
                    x=timeline_df[date_col], y=timeline_df['Portfolio_Value'],
                    mode='lines', name='Portfolio Value ($)', line=dict(color='#3b82f6', width=2.5),
                    fill='tonexty', fillcolor='rgba(59, 130, 246, 0.08)'
                ))
                fig_timeline.update_layout(
                    title="Portfolio Valuation vs Basis Cost",
                    xaxis_title="", yaxis_title="USD ($)",
                    paper_bgcolor="#0b0f19", plot_bgcolor="#111827", font_color="#f3f4f6",
                    hovermode="x unified",
                    xaxis=dict(type='date', gridcolor='#1f2937', gridwidth=1, griddash='dash'),
                    yaxis=dict(gridcolor='#1f2937', gridwidth=1, griddash='dash')
                )
                st.plotly_chart(fig_timeline, width='stretch')
        except Exception as e:
            pass

    st.markdown("---")
    col_chart1, col_chart2 = st.columns(2)
    with col_chart1:
        if current_values:
            brand_colors = {"BTC": "#F7931A", "ETH": "#627EEA", "SOL": "#9945FF", "HYPE": "#4EEDCC", "ZEC": "#F4B728", "PUMP": "#FF2D55"}
            assets_in_pie = list(current_values.keys())
            fig_pie = px.pie(
                names=assets_in_pie, values=[info["current_val"] for info in current_values.values()],
                title="Coin Share Distribution", hole=0.5, color=assets_in_pie, color_discrete_map=brand_colors
            )
            fig_pie.update_layout(paper_bgcolor="#0b0f19", plot_bgcolor="#111827", font_color="#f3f4f6", legend=dict(bgcolor="rgba(0,0,0,0)", bordercolor="#1f2937"))
            st.plotly_chart(fig_pie, width='stretch')
        
    with col_chart2:
        if current_values:
            assets_list = list(current_values.keys())
            pnl_values = [info["pnl_usd"] for info in current_values.values()]
            colors = ['#10b981' if v >= 0 else '#ef4444' for v in pnl_values]
            fig_bar = go.Figure(data=[go.Bar(x=assets_list, y=pnl_values, marker_color=colors)])
            fig_bar.update_layout(
                title="PnL Breakdown per Coin ($)",
                paper_bgcolor="#0b0f19", plot_bgcolor="#111827", font_color="#f3f4f6",
                xaxis=dict(gridcolor='#1f2937', gridwidth=1, griddash='dash'),
                yaxis=dict(gridcolor='#1f2937', gridwidth=1, griddash='dash')
            )
            st.plotly_chart(fig_bar, width='stretch')

with tab3:
    st.markdown("### 📋 Transaction Ledgers")
    raw_df = load_transactions_from_sheet()
    if not raw_df.empty:
        raw_df.index = raw_df.index + 1
        st.dataframe(raw_df, width='stretch')
    else:
        st.info("No recorded transactions.")

with tab4:
    st.markdown("### 🧠 Smart Advisor & Profit Engine")
    col_adv_1, col_adv_2 = st.columns(2)
    with col_adv_1:
        st.markdown("#### 🤖 Smart DCA Timing & Scoring Engine")
        st.caption(f"Global Market Sentiment (Fear & Greed): **{fng_value}/100 ({fng_label})**")
        selected_dca_asset = st.selectbox("Select Coin to Evaluate for DCA:", list(current_values.keys()))
        test_dca_amount = st.number_input("Amount to Put ($)", value=100.0, step=10.0, key="smart_dca_amt")
        
        if selected_dca_asset and selected_dca_asset in current_values:
            stats = current_values[selected_dca_asset]
            score = stats["score"]
            st.markdown(f"### Score Result: **{score} / 100**")
            if score >= 70:
                st.success("🟢 **STRONG BUY SIGNAL:** Εξαιρετική ευκαιρία! Βάλτα όλα τώρα.")
            elif score >= 45:
                st.warning("🟡 **BALANCED DCA:** Ουδέτερη αγορά, σπαστά ποσά.")
            else:
                st.error("🔴 **HOLD CASH / OVERBOUGHT:** Αποφυγή αγοράς τώρα.")
                    
    with col_adv_2:
        st.markdown("#### 🎯 Target Profit Extractor (Take Profit)")
        target_profit_goal = st.number_input("Desired Net Profit to Extract ($)", value=200.0, step=50.0, key="target_profit_goal")
        if total_pnl_usd > 0:
            profitable_assets = {k: v for k, v in current_values.items() if v["pnl_usd"] > 0}
            if profitable_assets:
                total_prof_sum = sum(v["pnl_usd"] for v in profitable_assets.values())
                extract_data = []
                for asset, stats in profitable_assets.items():
                    weight = stats["pnl_usd"] / total_prof_sum
                    dollar_to_pull = target_profit_goal * weight
                    amount_to_sell = dollar_to_pull / stats["price"]
                    total_holding_amount = portfolio_data[asset]["amount"]
                    pct_of_holding = (amount_to_sell / total_holding_amount) * 100 if total_holding_amount > 0 else 0
                    
                    extract_data.append({
                        "Coin": asset,
                        "Sell Amount": f"{amount_to_sell:.6f} {asset}",
                        "% of Holding": f"{pct_of_holding:.1f}%",
                        "Est. Cash Back": f"${dollar_to_pull:,.2f}",
                        "Current Price": f"${stats['price']:,.2f}"
                    })
                st.table(pd.DataFrame(extract_data))

with tab5:
    st.markdown("### 🛡️ Risk & Exit Strategy Terminal")
    calc_basis = st.radio("Calculation Basis:", ["Current Price (Dynamic)", "Average Cost (Static)"], horizontal=True)
    st.markdown("---")
    
    for asset, data in portfolio_data.items():
        if data["amount"] <= 0:
            continue
        stats = current_values[asset]
        curr_p = stats['price']
        avg_p = stats['avg_price']
        total_amt = data['amount']
        total_cst = data['total_cost']
        base_price = curr_p if "Current" in calc_basis else avg_p
        
        with st.container():
            c_left, c_mid, c_right = st.columns([1.2, 2.4, 2.4])
            with c_left:
                st.markdown(f"**{asset}**<br>Price: `${curr_p:,.2f}`<br>Avg: `${avg_p:,.2f}`", unsafe_allow_html=True)
            with c_mid:
                sl_pct = st.slider(f"SL % {asset}", -50.0, -1.0, -10.0, step=1.0, key=f"sl_{asset}", label_visibility="collapsed")
                sl_price = base_price * (1 + sl_pct / 100.0)
                sl_pnl_usd = (total_amt * sl_price) - total_cst
                st.markdown(f"SL: ${sl_price:,.2f} ({sl_pct}%) | PnL: `${sl_pnl_usd:+,.2f}`")
            with c_right:
                tp_pct = st.slider(f"TP % {asset}", 5.0, 300.0, 50.0, step=5.0, key=f"tp_{asset}", label_visibility="collapsed")
                tp_price = base_price * (1 + tp_pct / 100.0)
                tp_pnl_usd = (total_amt * tp_price) - total_cst
                st.markdown(f"TP: ${tp_price:,.2f} (+{tp_pct}%) | PnL: `${tp_pnl_usd:+,.2f}`")
            st.markdown("---")
