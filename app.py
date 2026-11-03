import streamlit as st
import yfinance as yf
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
import numpy as np
import requests
import json
from datetime import datetime
from streamlit_autorefresh import st_autorefresh
import gspread
from google.oauth2.service_account import Credentials

# --- PAGE CONFIGURATION ---
st.set_page_config(layout="wide", page_title="Portfolio Terminal", initial_sidebar_state="expanded")

# --- FINTECH DARK PALETTE & MINIMAL TYPOGRAPHY UI ---
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500;600&display=swap');

    html, body, .stApp {
        background-color: #09090b !important;
        color: #f4f4f5 !important;
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif !important;
    }

    #MainMenu, footer {visibility: hidden;}

    /* Keep Streamlit header visible so the built-in sidebar collapse/expand button never disappears. */
    header[data-testid="stHeader"] {
        visibility: visible !important;
        background: transparent !important;
    }

    /* Metrics Cards */
    div[data-testid="stMetric"] {
        background-color: #121215 !important;
        border: 1px solid #27272a !important;
        padding: 16px 20px !important;
        border-radius: 6px !important;
        box-shadow: none !important;
    }
    div[data-testid="stMetric"] label {
        color: #a1a1aa !important;
        font-weight: 600 !important;
        font-size: 0.72rem !important;
        text-transform: uppercase !important;
        letter-spacing: 0.08em !important;
    }
    div[data-testid="stMetric"] div[data-testid="stMetricValue"] {
        color: #fafafa !important;
        font-weight: 700 !important;
        font-size: 1.4rem !important;
        font-family: 'JetBrains Mono', monospace !important;
    }

    /* Headings */
    h1, h2, h3, h4, h5 {
        color: #ffffff !important;
        font-weight: 600 !important;
        letter-spacing: -0.02em !important;
    }

    /* Navigation Tabs */
    .stTabs [data-baseweb="tab-list"] {
        gap: 4px;
        background-color: transparent;
        padding: 0;
        border-bottom: 1px solid #27272a;
    }
    .stTabs [data-baseweb="tab"] {
        background-color: transparent;
        border-radius: 6px 6px 0 0;
        color: #a1a1aa;
        border: 1px solid transparent;
        padding: 8px 16px;
        font-weight: 500;
        font-size: 0.85rem;
    }
    .stTabs [data-baseweb="tab"]:hover {
        color: #f4f4f5;
        background-color: #18181b;
    }
    .stTabs [aria-selected="true"] {
        background-color: #18181b !important;
        color: #ffffff !important;
        border-color: #27272a #27272a transparent #27272a !important;
        font-weight: 600;
    }

    /* Buttons: restrained slate palette with a calm teal primary action */
    .stButton > button, .stDownloadButton > button {
        background: #171a1f !important;
        color: #e8edf3 !important;
        border: 1px solid #2d333d !important;
        border-radius: 8px !important;
        font-weight: 600 !important;
        font-size: 0.86rem !important;
        padding: 0.48rem 0.95rem !important;
        box-shadow: none !important;
        transition: background-color 0.15s ease, border-color 0.15s ease !important;
    }
    .stButton > button:hover, .stDownloadButton > button:hover {
        background: #20262e !important;
        border-color: #475569 !important;
        color: #ffffff !important;
    }
    .stButton > button[kind="primary"], button[kind="primary"] {
        background: #243141 !important;
        color: #ffffff !important;
        border: 1px solid #3d5166 !important;
    }
    .stButton > button[kind="primary"]:hover, button[kind="primary"]:hover {
        background: #2d3e50 !important;
        border-color: #58708a !important;
    }
    .stButton > button:focus:not(:active), .stDownloadButton > button:focus:not(:active) {
        border-color: #58708a !important;
        box-shadow: 0 0 0 1px rgba(88,112,138,0.28) !important;
    }

    /* Sidebar Styling */
    section[data-testid="stSidebar"] {
        background-color: #0c0c0e !important;
        border-right: 1px solid #27272a !important;
        min-width: 310px !important;
        width: 310px !important;
    }
    section[data-testid="stSidebar"] > div {
        width: 310px !important;
    }
    /* Let main-page columns shrink to the available viewport instead of clipping. */
    div[data-testid="stHorizontalBlock"] > div[data-testid="column"] {
        min-width: 0 !important;
    }
    div[data-testid="stMetricValue"] {
        overflow-wrap: anywhere !important;
        word-break: normal !important;
        font-size: clamp(0.88rem, 1.35vw, 1.4rem) !important;
    }
    div[data-testid="stMetricLabel"] {
        overflow-wrap: anywhere !important;
    }
    .stTabs [data-baseweb="tab-list"] {
        flex-wrap: wrap !important;
        white-space: normal !important;
        row-gap: 2px !important;
    }
    .stTabs [data-baseweb="tab"] {
        padding: 7px 9px !important;
        font-size: 0.78rem !important;
    }
    /* Keep selected DCA assets readable instead of clipping their tags. */
    div[data-testid="stMultiSelect"] [data-baseweb="select"] > div {
        flex-wrap: wrap !important;
        height: auto !important;
        min-height: 42px !important;
        max-height: 120px !important;
        overflow-y: auto !important;
    }
    section[data-testid="stSidebar"] hr {
        border-color: #27272a;
        margin: 1.2rem 0;
    }

    /* Custom Input & Controls */
    .stTextInput input, .stNumberInput input, .stSelectbox div[data-baseweb="select"] {
        background-color: #12161c !important;
        border: 1px solid #303946 !important;
        color: #f1f5f9 !important;
        border-radius: 8px !important;
        font-size: 0.9rem !important;
    }
    /* JetBrains Mono uses slashed zeros; use Inter for editable values so 0 is clear. */
    .stNumberInput input, .stTextInput input {
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif !important;
        font-variant-numeric: tabular-nums !important;
        font-feature-settings: "zero" 0 !important;
        letter-spacing: 0.01em !important;
    }
    .stNumberInput button {
        background: #171a1f !important;
        color: #cbd5e1 !important;
        border-color: #343d49 !important;
    }
    .stNumberInput button:hover {
        background: #20262e !important;
        color: #ffffff !important;
    }

    /* Minus / Plus Quick Action Buttons */
    div[data-testid="stSidebar"] div[data-testid="stHorizontalBlock"] button {
        height: 38px !important;
        font-size: 1.1rem !important;
        font-weight: 600 !important;
        padding: 0 !important;
        line-height: 1 !important;
        background-color: #1b2028 !important;
        border: 1px solid #2d333d !important;
        color: #cbd5e1 !important;
    }
    div[data-testid="stSidebar"] div[data-testid="stHorizontalBlock"] button:hover {
        color: #ffffff !important;
        border-color: #475569 !important;
        background-color: #28313d !important;
    }

    /* Custom Sliders */
    div.stSlider > div[data-baseweb="slider"] div[role="slider"] {
        background-color: #8fa6bd !important;
        border: 2px solid #c7d2de !important;
        box-shadow: none;
    }
    div.stSlider > div[data-baseweb="slider"] div > div > div {
        background-color: #3f3f46 !important;
    }
    
    /* Multiselect tags - suppress Streamlit theme red completely */
    div[data-testid="stMultiSelect"] [data-baseweb="tag"],
    div[data-testid="stMultiSelect"] span[data-baseweb="tag"],
    div[data-testid="stMultiSelect"] div[data-baseweb="tag"] {
        background-color: #171c22 !important;
        background-image: none !important;
        color: #dce5ee !important;
        border: 1px solid #303945 !important;
        border-radius: 7px !important;
        box-shadow: none !important;
    }
    div[data-testid="stMultiSelect"] [data-baseweb="tag"] *,
    div[data-testid="stMultiSelect"] [data-baseweb="tag"] span,
    div[data-testid="stMultiSelect"] [data-baseweb="tag"] svg {
        color: #dce5ee !important;
        fill: #dce5ee !important;
        background-color: transparent !important;
    }
    div[data-testid="stMultiSelect"] [data-baseweb="tag"]:hover {
        background-color: #202731 !important;
        border-color: #465362 !important;
    }
    div[data-testid="stMultiSelect"] [data-baseweb="select"]:focus-within {
        border-color: #465362 !important;
        box-shadow: 0 0 0 1px rgba(70,83,98,0.22) !important;
    }

    /* Radio controls - dark outer ring + muted steel selected dot, never red */
    div[data-testid="stRadio"] [role="radiogroup"] {
        gap: 0.35rem !important;
    }
    div[data-testid="stRadio"] label[data-baseweb="radio"] {
        color: #d7dee7 !important;
        font-weight: 500 !important;
    }
    div[data-testid="stRadio"] label[data-baseweb="radio"] > div:first-child {
        background: #11151a !important;
        border: 1px solid #4a5563 !important;
        box-shadow: none !important;
    }
    div[data-testid="stRadio"] label[data-baseweb="radio"] > div:first-child > div {
        background: transparent !important;
        box-shadow: none !important;
    }
    div[data-testid="stRadio"] label[data-baseweb="radio"]:has(input:checked) > div:first-child {
        background: #11151a !important;
        border-color: #8fa6bd !important;
        box-shadow: 0 0 0 2px rgba(143,166,189,0.10) !important;
    }
    div[data-testid="stRadio"] label[data-baseweb="radio"]:has(input:checked) > div:first-child > div {
        background: #8fa6bd !important;
    }
    div[data-testid="stRadio"] input[type="radio"] {
        accent-color: #8fa6bd !important;
    }
    div[data-testid="stRadio"] label[data-baseweb="radio"]:has(input:checked) {
        color: #f5f7fa !important;
    }

    /* Sidebar section labels */
    section[data-testid="stSidebar"] label,
    section[data-testid="stSidebar"] .stMarkdown p {
        line-height: 1.35 !important;
    }

    /* Premium sidebar controls: no default Streamlit red accents. */
    .sidebar-kicker {
        color: #8b98a7 !important;
        font-size: 0.72rem !important;
        font-weight: 700 !important;
        letter-spacing: 0.06em !important;
        text-transform: uppercase !important;
        margin: 0.15rem 0 0.45rem 0 !important;
    }
    .sidebar-kicker-spaced { margin-top: 1.1rem !important; }

    section[data-testid="stSidebar"] .stButton > button {
        background: #15191f !important;
        border: 1px solid #2b323c !important;
        color: #cbd5e1 !important;
        border-radius: 7px !important;
        min-height: 34px !important;
        padding: 0.34rem 0.55rem !important;
        font-size: 0.78rem !important;
        font-weight: 600 !important;
    }
    section[data-testid="stSidebar"] .stButton > button:hover {
        background: #1d232b !important;
        border-color: #46515f !important;
        color: #ffffff !important;
    }

    .weight-label {
        display: flex;
        align-items: center;
        justify-content: space-between;
        color: #d8dee7;
        font-size: 0.76rem;
        font-weight: 650;
        margin-top: 0.72rem;
        margin-bottom: 0.28rem;
        letter-spacing: 0.015em;
    }
    .weight-label span {
        color: #8f9dab;
        font-family: 'Inter', sans-serif;
        font-weight: 600;
    }
    .weight-track {
        width: 100%;
        height: 5px;
        border-radius: 999px;
        background: #1b2027;
        overflow: hidden;
        border: 1px solid #242b34;
        margin-bottom: 0.18rem;
    }
    .weight-fill {
        height: 100%;
        border-radius: 999px;
        background: #718096;
    }
    .allocation-total {
        margin-top: 0.9rem;
        padding-top: 0.65rem;
        border-top: 1px solid #232931;
        color: #8f9aa8;
        font-size: 0.75rem;
    }
    .allocation-total strong { color: #e5e7eb; font-weight: 650; }
    .allocation-total span { color: #657180; }

</style>
""", unsafe_allow_html=True)

# Auto-refresh every 60s
st_autorefresh(interval=60 * 1000, key="datarefresh")

st.markdown("## Portfolio Terminal")

# --- GOOGLE SHEETS & CACHED API HELPERS ---
def get_g_sheet():
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds_dict = dict(st.secrets["gcp_service_account"])
    creds = Credentials.from_service_account_info(creds_dict, scopes=scope)
    client = gspread.authorize(creds)
    sheet = client.open("CryptoPortfolio").sheet1 
    return sheet

@st.cache_data(ttl=15)
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
        st.error(f"Google Sheet Connection Error: {e}")
        return pd.DataFrame(columns=["Date", "Asset", "Amount", "USD_Cost"])

@st.cache_data(ttl=60)
def get_cmc_market_data(symbols_list):
    """Resolve symbols directly through CoinMarketCap and return price + slug.
    No manual slug is required for newly added coins as long as CMC resolves
    the ticker unambiguously.
    """
    if not symbols_list:
        return {}, {}
    api_key = st.secrets.get("CMC_API_KEY", "")
    url = "https://pro-api.coinmarketcap.com/v1/cryptocurrency/quotes/latest"
    try:
        response = requests.get(
            url,
            headers={"Accepts": "application/json", "X-CMC_PRO_API_KEY": api_key},
            params={"symbol": ",".join(symbols_list), "convert": "USD"},
            timeout=5
        )
        if response.status_code == 200:
            data = response.json().get("data", {})
            prices = {}
            slugs = {}
            for sym in symbols_list:
                item = data.get(sym)
                if item and item.get("quote", {}).get("USD", {}).get("price") is not None:
                    prices[sym] = float(item["quote"]["USD"]["price"])
                    if item.get("slug"):
                        slugs[sym] = item["slug"]
            return prices, slugs
    except Exception:
        pass
    return {}, {}

def get_cmc_prices(symbols_list):
    prices, _ = get_cmc_market_data(symbols_list)
    return prices

@st.cache_data(ttl=300)
def get_fear_and_greed():
    try:
        res = requests.get("https://api.alternative.me/fng/?limit=1", timeout=5)
        data = res.json()
        return int(data["data"][0]["value"]), data["data"][0]["value_classification"]
    except Exception:
        return 50, "Neutral"

@st.cache_data(ttl=3600)
def fetch_asset_history(asset, start_date, end_date):
    """Cached daily history used by the historical portfolio-value timeline."""
    ticker_str = "HYPE32196-USD" if asset == "HYPE" else f"{asset}-USD"
    try:
        hist = yf.Ticker(ticker_str).history(start=start_date, end=end_date)
        if hist.empty and asset == "HYPE":
            hist = yf.Ticker("HYPE-USD").history(start=start_date, end=end_date)
        if hist.empty:
            hist = yf.Ticker(f"{asset}-USD").history(start=start_date, end=end_date)
        return hist
    except Exception:
        return pd.DataFrame()

@st.cache_data(ttl=300)
def fetch_asset_technicals(asset):
    ticker_str = "HYPE32196-USD" if asset == "HYPE" else f"{asset}-USD"
    try:
        hist = yf.Ticker(ticker_str).history(period="100d")
        if hist.empty or len(hist) < 15:
            hist = yf.Ticker(f"{asset}-USD").history(period="100d")
        return hist
    except Exception:
        return pd.DataFrame()

@st.cache_data(ttl=300)
def get_eur_rate():
    try:
        eur_ticker = yf.Ticker("EURUSD=X")
        eur_rate = eur_ticker.history(period="1d")['Close'].iloc[-1]
        return 1.0 / eur_rate
    except Exception:
        return 0.92

# --- PERSISTENT TARGET WEIGHT SETTINGS ---
def get_settings_sheet():
    """Open/create a separate Settings worksheet so the transaction ledger stays untouched."""
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds_dict = dict(st.secrets["gcp_service_account"])
    creds = Credentials.from_service_account_info(creds_dict, scopes=scope)
    client = gspread.authorize(creds)
    spreadsheet = client.open("CryptoPortfolio")
    try:
        return spreadsheet.worksheet("Settings")
    except gspread.WorksheetNotFound:
        ws = spreadsheet.add_worksheet(title="Settings", rows=20, cols=3)
        ws.update("A1:C1", [["Setting", "Value", "Updated"]])
        return ws

@st.cache_data(ttl=30)
def load_target_settings():
    """Load saved target-weight mode and custom weights."""
    try:
        ws = get_settings_sheet()
        rows = ws.get_all_records()
        settings = {str(r.get("Setting", "")).strip(): str(r.get("Value", "")).strip() for r in rows}
        mode = settings.get("target_weight_mode", "automatic").lower()
        if mode not in {"automatic", "custom"}:
            mode = "automatic"
        weights = {}
        raw_weights = settings.get("target_weights", "")
        if raw_weights:
            try:
                parsed = json.loads(raw_weights)
                if isinstance(parsed, dict):
                    weights = {str(k).upper(): float(v) for k, v in parsed.items() if float(v) >= 0}
            except Exception:
                weights = {}
        return mode, weights
    except Exception:
        return "automatic", {}

def save_target_settings(mode, weights):
    """Persist Target Weight mode/values without touching the transaction ledger."""
    ws = get_settings_sheet()
    values = {
        "target_weight_mode": mode,
        "target_weights": json.dumps({k: round(float(v), 2) for k, v in weights.items()}, separators=(",", ":"))
    }
    rows = ws.get_all_records()
    existing = {}
    for idx, row in enumerate(rows, start=2):
        key = str(row.get("Setting", "")).strip()
        if key:
            existing[key] = idx
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    for key, value in values.items():
        row_values = [key, value, now]
        if key in existing:
            ws.update(f"A{existing[key]}:C{existing[key]}", [row_values])
        else:
            ws.append_row(row_values)
    load_target_settings.clear()

# --- LOAD RAW DATA ---
raw_df_initial = load_transactions_from_sheet()

def get_latest_transaction_date(df):
    if not df.empty:
        for col in df.columns:
            if 'date' in col.lower():
                valid_dates = df[col].dropna()
                if not valid_dates.empty:
                    return str(valid_dates.max())
    return "N/A"

# Known exceptions only. Normal coins are resolved automatically from CMC.
default_slugs = {
    "BTC": "bitcoin", "ETH": "ethereum", "SOL": "solana",
    "ZEC": "zcash", "HYPE": "hyperliquid", "PUMP": "pump-fun"
}

# --- CHRONOLOGICAL TRANSACTION PROCESSING ENGINE ---
# Ledger convention:
#   BUY       -> Amount > 0, USD_Cost > 0
#   SELL      -> Amount < 0, USD_Cost < 0 (negative cash proceeds)
#   WRITE-OFF -> Amount < 0, USD_Cost = 0
#
# Important:
# - Realized PnL stays with the asset after a full sale.
# - A later BUY of another asset (e.g. sell SOL -> buy BTC) does NOT erase
#   the realized PnL of SOL.
# - Unrealized PnL is calculated only on currently held coins.
# - Net PnL = realized PnL + unrealized PnL.
# - gross_buy_cost tracks ordinary BUY rows; SWAP_IN rows are excluded to avoid
#   counting a conversion as fresh buying volume. It is not the same as external deposits.

asset_states = {}

if not raw_df_initial.empty:
    df_sorted = raw_df_initial.copy()

    c_date = next((c for c in df_sorted.columns if 'date' in c.lower()), None)
    c_asset = next((c for c in df_sorted.columns if 'asset' in c.lower()), 'Asset')
    c_amount = next((c for c in df_sorted.columns if 'amount' in c.lower()), 'Amount')
    c_cost = next((c for c in df_sorted.columns if 'cost' in c.lower() or 'usd' in c.lower()), 'USD_Cost')
    c_tx_type = next((c for c in df_sorted.columns if 'transaction type' in c.lower() or c.lower() == 'type'), None)

    if c_date:
        try:
            df_sorted[c_date] = pd.to_datetime(df_sorted[c_date], errors='coerce')
            # Stable sort keeps original Sheet order for transactions on the same date.
            df_sorted["_sheet_order"] = np.arange(len(df_sorted))
            df_sorted = df_sorted.sort_values(
                by=[c_date, "_sheet_order"],
                ascending=[True, True],
                na_position="last"
            )
        except Exception:
            pass

    for _, row in df_sorted.iterrows():
        ast = str(row.get(c_asset, '')).upper().strip()
        if not ast:
            continue

        try:
            amt = float(str(row.get(c_amount, 0.0)).replace(',', ''))
            cost_val = float(str(row.get(c_cost, 0.0)).replace(',', ''))
        except (ValueError, TypeError):
            continue

        if not np.isfinite(amt) or not np.isfinite(cost_val) or abs(amt) < 1e-12:
            continue

        if ast not in asset_states:
            asset_states[ast] = {
                'holdings': 0.0,
                'cost_basis': 0.0,
                'realized_pnl': 0.0,
                'gross_buy_cost': 0.0,
                'gross_external_buy_cost': 0.0,
                'realized_cost_basis': 0.0,
                'realized_proceeds': 0.0
            }

        st_asset = asset_states[ast]
        tx_type_value = str(row.get(c_tx_type, '')).strip().upper() if c_tx_type else ''

        if amt > 0:
            # BUY / SWAP_IN. Incoming swap assets get cost basis, but are not counted
            # as fresh external buys in the gross-buy denominator.
            buy_cost = abs(cost_val)
            st_asset['holdings'] += amt
            st_asset['cost_basis'] += buy_cost
            # Per-asset lifetime return includes all acquisition cost, including swaps.
            st_asset['gross_buy_cost'] += buy_cost
            # Portfolio purchase-volume denominator excludes the incoming side of swaps.
            if tx_type_value != 'SWAP_IN':
                st_asset['gross_external_buy_cost'] += buy_cost

        else:
            # Negative Amount = removal from holdings.
            sell_qty = abs(amt)

            if st_asset['holdings'] <= 1e-12:
                # No remaining position: ignore an orphan removal rather than
                # creating negative holdings or artificial PnL.
                continue

            # A zero-cost negative transaction is the app's WRITE-OFF format.
            is_writeoff = abs(cost_val) <= 1e-12

            # Never remove more than the actual holding.
            qty_removed = min(sell_qty, st_asset['holdings'])

            avg_unit_cost = (
                st_asset['cost_basis'] / st_asset['holdings']
                if st_asset['holdings'] > 0 else 0.0
            )
            cost_removed = min(
                st_asset['cost_basis'],
                qty_removed * avg_unit_cost
            )

            if is_writeoff:
                # No cash proceeds. The removed cost becomes a realized loss.
                proceeds = 0.0
            else:
                # SELL: USD_Cost is stored as a negative number.
                proceeds = abs(cost_val)

            st_asset['realized_pnl'] += proceeds - cost_removed
            st_asset['realized_cost_basis'] += cost_removed
            st_asset['realized_proceeds'] += proceeds
            st_asset['holdings'] = max(0.0, st_asset['holdings'] - qty_removed)
            st_asset['cost_basis'] = max(0.0, st_asset['cost_basis'] - cost_removed)

            # Remove floating-point dust.
            if st_asset['holdings'] <= 1e-8:
                st_asset['holdings'] = 0.0
                st_asset['cost_basis'] = 0.0

# Remove helper column if it was created.
if "_sheet_order" in df_sorted.columns if not raw_df_initial.empty else False:
    df_sorted = df_sorted.drop(columns=["_sheet_order"], errors="ignore")

unique_assets_in_sheet = list(asset_states.keys())

unique_assets_in_sheet = list(asset_states.keys())

# --- SIDEBAR: EXECUTION & CONTROL ---
st.sidebar.markdown("### Execution")
new_cash_to_invest = st.sidebar.number_input("Cash to Invest ($)", value=0.0, step=10.0)

st.sidebar.markdown("---")
st.sidebar.markdown("#### New Transaction")
latest_date = get_latest_transaction_date(raw_df_initial)
st.sidebar.caption(f"Last transaction · {latest_date}")

action_mode = st.sidebar.selectbox(
    "Action",
    ["Trade", "Swap / Convert", "Write-off"],
    label_visibility="collapsed"
)

if action_mode == "Trade":
    if "trade_direction" not in st.session_state:
        st.session_state["trade_direction"] = "BUY"

    st.sidebar.markdown('<div class="trade-direction-label">Direction</div>', unsafe_allow_html=True)
    direction_cols = st.sidebar.columns(2, gap="small")
    if direction_cols[0].button("BUY", key="trade_direction_buy", use_container_width=True):
        st.session_state["trade_direction"] = "BUY"
    if direction_cols[1].button("SELL", key="trade_direction_sell", use_container_width=True):
        st.session_state["trade_direction"] = "SELL"

    tx_type = st.session_state["trade_direction"]
    selected_key = "trade_direction_buy" if tx_type == "BUY" else "trade_direction_sell"
    st.sidebar.markdown(f"""
    <style>
    .trade-direction-label {{ margin: .15rem 0 .35rem 0; font-size: .84rem; font-weight: 600; color: #d8dee9; }}
    .st-key-trade_direction_buy button, .st-key-trade_direction_sell button {{
        min-height: 2.15rem !important; border-radius: 8px !important;
        border: 1px solid #2b3440 !important; background: #11161d !important;
        color: #aeb8c5 !important; font-weight: 650 !important; box-shadow: none !important;
    }}
    .st-key-trade_direction_buy button:hover, .st-key-trade_direction_sell button:hover {{
        border-color: #465363 !important; background: #171e27 !important; color: #eef3f8 !important;
    }}
    .st-key-{{selected_key}} button {{
        background: #263445 !important; border-color: #52677e !important;
        color: #ffffff !important; box-shadow: inset 0 0 0 1px rgba(255,255,255,.03) !important;
    }}
    .st-key-{{selected_key}} button:hover {{
        background: #2b3b4d !important; border-color: #647c95 !important; color: #ffffff !important;
    }}
    </style>
    """, unsafe_allow_html=True)

    asset_input = st.sidebar.text_input("Asset", "BTC").upper().strip()
    amount_input = st.sidebar.number_input("Quantity", value=0.0, format="%.8f")
    cost_input = st.sidebar.number_input("Total value (USDC / USD)", value=0.0, format="%.2f")

    if st.sidebar.button("Log trade", type="primary", use_container_width=True):
        if amount_input > 0 and cost_input > 0 and asset_input:
            t_date = datetime.now().strftime("%Y-%m-%d")
            if tx_type == "SELL":
                current_amt = asset_states.get(asset_input, {}).get('holdings', 0.0)
                if amount_input > current_amt + 1e-4:
                    st.sidebar.error(f"Insufficient {asset_input} balance · {current_amt:.8f} available")
                else:
                    try:
                        sheet = get_g_sheet()
                        sheet.append_row([t_date, asset_input, f"{-amount_input:.8f}", f"{-cost_input:.2f}"])
                        st.cache_data.clear()
                        st.sidebar.success("Sale recorded")
                        st.rerun()
                    except Exception as e:
                        st.sidebar.error(f"Could not record trade: {e}")
            else:
                try:
                    sheet = get_g_sheet()
                    sheet.append_row([t_date, asset_input, f"{amount_input:.8f}", f"{cost_input:.2f}"])
                    st.cache_data.clear()
                    st.sidebar.success("Purchase recorded")
                    st.rerun()
                except Exception as e:
                    st.sidebar.error(f"Could not record trade: {e}")
        else:
            st.sidebar.error("Enter an asset, quantity and total value greater than zero.")

elif action_mode == "Swap / Convert":
    swap_from_asset = st.sidebar.text_input("You give · Asset", "RAY", key="swap_from_asset").upper().strip()
    swap_from_amount = st.sidebar.number_input("You give · Quantity", value=0.0, format="%.8f", key="swap_from_amount")
    swap_to_asset = st.sidebar.text_input("You receive · Asset", "LTC", key="swap_to_asset").upper().strip()
    swap_to_amount = st.sidebar.number_input("You receive · Quantity", value=0.0, format="%.8f", key="swap_to_amount")
    swap_value = st.sidebar.number_input("Swap value (USDC / USD)", value=0.0, format="%.2f", key="swap_value")

    if st.sidebar.button("Log swap", type="primary", use_container_width=True):
        available_from = asset_states.get(swap_from_asset, {}).get('holdings', 0.0)
        if not swap_from_asset or not swap_to_asset or swap_from_asset == swap_to_asset:
            st.sidebar.error("Choose two different asset tickers.")
        elif swap_from_amount <= 0 or swap_to_amount <= 0 or swap_value <= 0:
            st.sidebar.error("Enter positive quantities and swap value.")
        elif swap_from_amount > available_from + 1e-8:
            st.sidebar.error(f"Insufficient {swap_from_asset} balance · {available_from:.8f} available")
        else:
            t_date = datetime.now().strftime("%Y-%m-%d")
            try:
                sheet = get_g_sheet()
                headers = sheet.row_values(1)
                if len(headers) < 5 or not str(headers[4]).strip():
                    sheet.update_cell(1, 5, "Transaction Type")
                sheet.append_rows([
                    [t_date, swap_from_asset, f"{-swap_from_amount:.8f}", f"{-swap_value:.2f}", "SWAP_OUT"],
                    [t_date, swap_to_asset, f"{swap_to_amount:.8f}", f"{swap_value:.2f}", "SWAP_IN"]
                ], value_input_option="USER_ENTERED")
                st.cache_data.clear()
                st.sidebar.success(f"Swap recorded · {swap_from_asset} → {swap_to_asset}")
                st.rerun()
            except Exception as e:
                st.sidebar.error(f"Could not record swap: {e}")

else:
    burn_asset = st.sidebar.text_input("Asset to remove", "BTC").upper().strip()
    burn_amount = st.sidebar.number_input("Quantity to remove", value=0.0, format="%.8f")

    if st.sidebar.button("Log write-off", type="primary", use_container_width=True):
        current_amt = asset_states.get(burn_asset, {}).get('holdings', 0.0)
        if burn_amount > current_amt + 1e-4:
            st.sidebar.error(f"Insufficient {burn_asset} balance · {current_amt:.8f} available")
        elif burn_amount > 0 and burn_asset:
            t_date = datetime.now().strftime("%Y-%m-%d")
            try:
                sheet = get_g_sheet()
                sheet.append_row([t_date, burn_asset, f"-{burn_amount:.8f}", "0.00"])
                st.cache_data.clear()
                st.sidebar.success("Write-off recorded")
                st.rerun()
            except Exception as e:
                st.sidebar.error(f"Could not record write-off: {e}")
        else:
            st.sidebar.error("Enter a quantity greater than zero.")

st.sidebar.markdown("---")
st.sidebar.markdown("### Ledger Management")

if not raw_df_initial.empty:
    last_row = raw_df_initial.iloc[-1]
    st.sidebar.markdown(
        f"<div style='font-size: 11px; color: #a1a1aa; background: #121215; padding: 10px; border-radius: 6px; border: 1px solid #27272a; font-family: \"JetBrains Mono\", monospace;'>"
        f"<b>LAST ROW:</b> {last_row.get('Date', 'N/A')} | {last_row.get('Asset', 'N/A')}<br>"
        f"<b>AMT:</b> {last_row.get('Amount', 'N/A')} | <b>COST:</b> ${last_row.get('USD_Cost', 'N/A')}"
        f"</div>", 
        unsafe_allow_html=True
    )
    
    if st.sidebar.button("Undo Last Entry"):
        try:
            sheet = get_g_sheet()
            all_values = sheet.get_all_values()
            if len(all_values) > 1:
                last_row_num = len(all_values)
                last_type = str(all_values[-1][4]).strip().upper() if len(all_values[-1]) > 4 else ""
                previous_type = str(all_values[-2][4]).strip().upper() if len(all_values[-2]) > 4 else ""
                if last_type == "SWAP_IN" and previous_type == "SWAP_OUT":
                    sheet.delete_rows(last_row_num - 1, last_row_num)
                    message = "Last swap removed (both rows)."
                else:
                    sheet.delete_rows(last_row_num)
                    message = "Last entry removed."
                st.cache_data.clear()
                st.sidebar.success(message)
                st.rerun()
        except Exception as e:
            st.sidebar.error(f"Error: {e}")

# --- TARGET ALLOCATION SETUP ---
st.sidebar.markdown("---")
st.sidebar.markdown("### Target Allocation")

def _safe_widget_key(value):
    return "".join(ch if ch.isalnum() else "_" for ch in str(value))

def _inject_selected_button_css(selected_keys, prefix):
    """Style selected sidebar buttons without relying on Streamlit's red primary theme."""
    selected_rules = []
    for raw_key in selected_keys:
        css_key = _safe_widget_key(raw_key)
        selected_rules.append(f"""
        .st-key-{prefix}_{css_key} button {{
            background: #27313c !important;
            border-color: #526274 !important;
            color: #f8fafc !important;
            box-shadow: inset 0 0 0 1px rgba(148,163,184,0.05) !important;
        }}
        .st-key-{prefix}_{css_key} button:hover {{
            background: #303c49 !important;
            border-color: #64748b !important;
        }}
        """)
    st.markdown(
        "<style>" + "".join(selected_rules) + "</style>",
        unsafe_allow_html=True,
    )

# Replace the red Streamlit multiselect chips with compact neutral toggle buttons.
default_dca_selection = [ast for ast in unique_assets_in_sheet if ast != "PUMP"]
if "_active_dca_assets_ui" not in st.session_state:
    st.session_state["_active_dca_assets_ui"] = list(default_dca_selection)
else:
    # Remove assets that no longer exist and automatically include newly discovered assets.
    previous_universe = set(st.session_state.get("_active_dca_assets_universe", []))
    current_universe = set(unique_assets_in_sheet)
    selected_now = [a for a in st.session_state["_active_dca_assets_ui"] if a in current_universe]
    for new_asset in unique_assets_in_sheet:
        if new_asset not in previous_universe and new_asset != "PUMP" and new_asset not in selected_now:
            selected_now.append(new_asset)
    st.session_state["_active_dca_assets_ui"] = selected_now
st.session_state["_active_dca_assets_universe"] = list(unique_assets_in_sheet)

active_dca_assets = list(st.session_state["_active_dca_assets_ui"])
_inject_selected_button_css(active_dca_assets, "dca_asset")

st.sidebar.markdown("<div class='sidebar-kicker'>Active assets</div>", unsafe_allow_html=True)
asset_cols = st.sidebar.columns(2, gap="small")
for idx, asset in enumerate(unique_assets_in_sheet):
    key_suffix = _safe_widget_key(asset)
    label = f"✓ {asset}" if asset in active_dca_assets else asset
    if asset_cols[idx % 2].button(label, key=f"dca_asset_{key_suffix}", use_container_width=True):
        updated = list(st.session_state["_active_dca_assets_ui"])
        if asset in updated:
            updated.remove(asset)
        else:
            updated.append(asset)
        st.session_state["_active_dca_assets_ui"] = updated
        st.rerun()

cmc_prices, cmc_resolved_slugs = get_cmc_market_data(unique_assets_in_sheet)

portfolio_data = {}
temp_portfolio_vals = {}

for ast, state in asset_states.items():
    amt = state['holdings']
    cst = state['cost_basis']
    portfolio_data[ast] = {
        'total_cost': cst,
        'amount': amt,
        'realized_pnl': state['realized_pnl'],
        'realized_cost_basis': state.get('realized_cost_basis', 0.0),
        'realized_proceeds': state.get('realized_proceeds', 0.0),
        'gross_buy_cost': state.get('gross_buy_cost', 0.0),
        'is_dca': ast in active_dca_assets,
        'cmc_slug': cmc_resolved_slugs.get(ast, default_slugs.get(ast, ast.lower()))
    }
    if amt > 1e-4:
        p = cmc_prices.get(ast, cst / amt if amt > 0 else 0)
        temp_portfolio_vals[ast] = amt * p

tot_dca_val_temp = sum(temp_portfolio_vals.get(ast, 0.0) for ast in active_dca_assets)

def persist_custom_weights_from_session():
    weights = {
        asset: float(st.session_state.get(f"num_{asset}", 0.0))
        for asset in active_dca_assets
        if f"num_{asset}" in st.session_state
    }
    try:
        save_target_settings("custom", weights)
    except Exception:
        pass

def sync_from_num(asset_name):
    st.session_state[f"slider_{asset_name}"] = st.session_state[f"num_{asset_name}"]
    if st.session_state.get("_target_mode_seen") == "custom":
        persist_custom_weights_from_session()

def sync_from_slider(asset_name):
    st.session_state[f"num_{asset_name}"] = st.session_state[f"slider_{asset_name}"]
    if st.session_state.get("_target_mode_seen") == "custom":
        persist_custom_weights_from_session()

saved_weight_mode, saved_custom_weights = load_target_settings()
if "_target_mode_ui" not in st.session_state:
    st.session_state["_target_mode_ui"] = "custom" if saved_weight_mode == "custom" else "automatic"

current_mode = st.session_state["_target_mode_ui"]
_inject_selected_button_css([current_mode], "allocation_mode")
st.sidebar.markdown("<div class='sidebar-kicker sidebar-kicker-spaced'>Allocation mode</div>", unsafe_allow_html=True)
mode_col_auto, mode_col_custom = st.sidebar.columns(2, gap="small")
if mode_col_auto.button("Automatic", key="allocation_mode_automatic", use_container_width=True):
    st.session_state["_target_mode_ui"] = "automatic"
    current_mode = "automatic"
    st.rerun()
if mode_col_custom.button("Custom", key="allocation_mode_custom", use_container_width=True):
    st.session_state["_target_mode_ui"] = "custom"
    current_mode = "custom"
    st.rerun()

if current_mode != saved_weight_mode:
    try:
        save_target_settings(current_mode, saved_custom_weights)
        saved_weight_mode = current_mode
    except Exception:
        pass

target_weights = {}

for asset in active_dca_assets:
    val = temp_portfolio_vals.get(asset, 0.0)
    auto_pct = (val / tot_dca_val_temp * 100.0) if tot_dca_val_temp > 0 else (100.0 / len(active_dca_assets) if active_dca_assets else 0.0)

    num_key = f"num_{asset}"
    slider_key = f"slider_{asset}"
    initial_pct = saved_custom_weights.get(asset, auto_pct) if current_mode == "custom" else auto_pct

    if current_mode == "automatic":
        st.session_state[num_key] = float(round(initial_pct, 1))
        st.session_state[slider_key] = st.session_state[num_key]
    elif num_key not in st.session_state or st.session_state.get("_target_mode_seen") != "custom":
        st.session_state[num_key] = float(round(initial_pct, 1))
        st.session_state[slider_key] = st.session_state[num_key]

    st.sidebar.markdown(
        f"<div class='weight-label'>{asset}<span>{st.session_state[num_key]:.1f}%</span></div>",
        unsafe_allow_html=True,
    )

    # In automatic mode the allocation is informative, so show a clean bar instead of disabled inputs.
    if current_mode == "automatic":
        pct = max(0.0, min(100.0, float(st.session_state[num_key])))
        st.sidebar.markdown(
            f"<div class='weight-track'><div class='weight-fill' style='width:{pct:.1f}%'></div></div>",
            unsafe_allow_html=True,
        )
    else:
        st.sidebar.number_input(
            label=f"{asset}_num",
            min_value=0.0,
            max_value=100.0,
            step=0.5,
            key=num_key,
            on_change=sync_from_num,
            args=(asset,),
            label_visibility="collapsed"
        )
        st.sidebar.slider(
            label=f"{asset}_slider",
            min_value=0.0,
            max_value=100.0,
            key=slider_key,
            on_change=sync_from_slider,
            args=(asset,),
            label_visibility="collapsed"
        )

    target_weights[asset] = st.session_state[num_key]

st.session_state["_target_mode_seen"] = current_mode

for asset in portfolio_data:
    portfolio_data[asset]['target_pct'] = (target_weights.get(asset, 0.0) / 100.0) if asset in active_dca_assets else 0.0

total_weight_sum = sum(target_weights.values())
if current_mode == "custom" and active_dca_assets and abs(total_weight_sum - 100.0) > 0.1:
    st.sidebar.markdown(
        f"<div class='allocation-total'>Total <strong>{total_weight_sum:.1f}%</strong><span> / 100%</span></div>",
        unsafe_allow_html=True
    )

# --- INDICATORS & CORE METRICS ENGINE ---
fng_value, fng_label = get_fear_and_greed()
usd_to_eur = get_eur_rate()

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
    if stats['rsi'] < 30: sc += 25
    elif stats['rsi'] < 42: sc += 15
    elif stats['rsi'] > 68: sc -= 25
    if stats['price'] <= stats['bb_lower']: sc += 20
    if fng < 30: sc += 15
    elif fng > 75: sc -= 15
    return max(0, min(100, sc))

current_values = {}
total_current_portfolio = 0.0
total_active_cost = 0.0
total_realized_pnl = sum(state['realized_pnl'] for state in asset_states.values())
total_gross_invested = sum(state.get('gross_external_buy_cost', 0.0) for state in asset_states.values())

for asset, data in portfolio_data.items():
    amt = data["amount"]
    cst = data["total_cost"]
    
    if amt <= 1e-4:
        continue 
        
    price = cmc_prices.get(asset, cst / amt if amt > 0 else 0)
    # Keep the existing Smart Buy defaults/logic unchanged; the dashboard uses
    # separate availability flags so missing technical history is not presented as real data.
    rsi, sma_50, bb_lower = 50.0, price, price * 0.95
    bb_mid, bb_upper = None, None
    momentum_24h, momentum_7d = None, None
    has_sma_50 = False
    has_bollinger = False
    hist = fetch_asset_technicals(asset)
    if not hist.empty and 'Close' in hist.columns:
        closes = pd.to_numeric(hist['Close'], errors='coerce').dropna()
        if len(closes) >= 50:
            sma_50 = float(closes.tail(50).mean())
            has_sma_50 = True
        if len(closes) >= 20:
            bb_mid = float(closes.rolling(window=20).mean().iloc[-1])
            rsd = float(closes.rolling(window=20).std().iloc[-1])
            bb_lower = bb_mid - (2 * rsd)
            bb_upper = bb_mid + (2 * rsd)
            has_bollinger = True
        if len(closes) >= 2 and closes.iloc[-2] != 0:
            momentum_24h = (float(closes.iloc[-1]) / float(closes.iloc[-2]) - 1) * 100
        if len(closes) >= 8 and closes.iloc[-8] != 0:
            momentum_7d = (float(closes.iloc[-1]) / float(closes.iloc[-8]) - 1) * 100
        if len(closes) >= 15:
            rsi_series = get_rsi(closes)
            if not rsi_series.empty and not pd.isna(rsi_series.iloc[-1]):
                rsi = float(rsi_series.iloc[-1])

    val = amt * price
    avg_price = (cst / amt) if amt > 0 else 0.0
    pnl_unrealized_usd = val - cst
    pnl_unrealized_pct = (pnl_unrealized_usd / cst) * 100 if cst > 0 else 0.0

    realized_cost_basis = data.get("realized_cost_basis", 0.0)
    realized_return_pct = (
        (data["realized_pnl"] / realized_cost_basis) * 100
        if realized_cost_basis > 0 else 0.0
    )

    temp_stats = {
        "price": price, 
        "avg_price": avg_price, 
        "current_val": val,
        "pnl_usd": pnl_unrealized_usd,          # Unrealized PnL
        "pnl_pct": pnl_unrealized_pct,          # Unrealized PnL %
        "realized_pnl": data["realized_pnl"],   # Realized PnL
        "realized_cost_basis": realized_cost_basis,
        "realized_proceeds": data.get("realized_proceeds", 0.0),
        "realized_return_pct": realized_return_pct,
        "sma_50": sma_50,
        "has_sma_50": has_sma_50,
        "bb_lower": bb_lower,
        "bb_mid": bb_mid,
        "bb_upper": bb_upper,
        "has_bollinger": has_bollinger,
        "momentum_24h": momentum_24h,
        "momentum_7d": momentum_7d,
        "rsi": rsi
    }
    temp_stats["score"] = compute_smart_score(temp_stats, fng_value)

    current_values[asset] = temp_stats
    total_current_portfolio += val
    total_active_cost += cst

new_total_portfolio = total_current_portfolio + new_cash_to_invest
tot_eur = total_current_portfolio * usd_to_eur

total_unrealized_pnl = total_current_portfolio - total_active_cost
total_net_pnl_usd = total_unrealized_pnl + total_realized_pnl
pnl_eur = total_net_pnl_usd * usd_to_eur

# Overall return is measured against ALL capital ever used for BUYs,
# not only the cost basis of positions that are still open.
# This prevents the percentage from becoming distorted after a full sale.
total_pnl_pct = (
    (total_net_pnl_usd / total_gross_invested) * 100
    if total_gross_invested > 0 else 0.0
)

# DCA Allocations Logic
strict_allocations = {}
for asset, data in portfolio_data.items():
    if data["amount"] <= 1e-4 or not data["is_dca"] or asset not in current_values:
        continue
    cur_val = current_values[asset]["current_val"]
    ideal_val = new_total_portfolio * data["target_pct"]
    strict_allocations[asset] = max(0, ideal_val - cur_val)

total_strict_weight = sum(strict_allocations.values()) or 1.0

smart_allocations = {}
total_smart_weight = 0
for asset, data in portfolio_data.items():
    if data["amount"] <= 1e-4 or not data["is_dca"] or asset not in current_values:
        continue
    cur_val = current_values[asset]["current_val"]
    ideal_val = new_total_portfolio * data["target_pct"]
    base_need = max(0, ideal_val - cur_val)
    score = current_values[asset]["score"]
    smart_weight = base_need * max(0.1, score / 50.0)
    smart_allocations[asset] = smart_weight
    total_smart_weight += smart_weight

total_smart_weight = total_smart_weight or 1.0

# --- MAIN NAVIGATION TABS ---
tab1, tab2, tab6, tab3, tab4, tab5 = st.tabs([
    "Overview", "Analytics", "Profit & Rebalance", "Ledgers & Export", "Smart Advisor", "Risk & Exit Laddering"
])

# --- TAB 1: OVERVIEW ---
with tab1:
    c1, c2, c3 = st.columns(3)
    c1.metric("Total Portfolio Value", f"${total_current_portfolio:,.2f}", f"€{tot_eur:,.2f}")
    c2.metric(
        "Net PnL (Unrealized + Realized)", 
        f"${total_net_pnl_usd:+,.2f} (€{pnl_eur:+,.2f})", 
        f"Unrealized: {total_unrealized_pnl:+,.2f} | Realized: {total_realized_pnl:+,.2f}"
    )
    c3.metric("Allocatable Cash", f"${new_cash_to_invest:,.2f}")
    st.markdown("---")
    st.markdown("##### Active Positions & Allocation Matrix")

    table_data = []
    for asset, data in portfolio_data.items():
        if data["amount"] <= 1e-4 or asset not in current_values:
            continue
        stats = current_values[asset]
        
        if data["is_dca"]:
            strict_buy = new_cash_to_invest * (strict_allocations.get(asset, 0) / total_strict_weight)
            smart_buy = new_cash_to_invest * (smart_allocations.get(asset, 0) / total_smart_weight)
            new_avg = calculate_new_avg(data['total_cost'], data['amount'], smart_buy, stats['price'])
            strict_str = f"${strict_buy:.2f}"
            smart_str = f"${smart_buy:.2f}"
            new_avg_str = f"${new_avg:.2f}"
        else:
            strict_str = "N/A"
            smart_str = "N/A"
            new_avg_str = f"${stats['avg_price']:.2f}"

        unrealized_str = f"{stats['pnl_usd']:+.2f}$ ({stats['pnl_pct']:+.2f}%)"
        realized_str = f"{stats['realized_pnl']:+.2f}$ ({stats['realized_return_pct']:+.2f}%)" if stats["realized_cost_basis"] > 0 else f"{stats['realized_pnl']:+.2f}$"
        lifetime_return_pct = (
            (stats['pnl_usd'] + stats['realized_pnl']) / data.get('gross_buy_cost', 0.0) * 100
            if data.get('gross_buy_cost', 0.0) > 0 else 0.0
        )
        lifetime_return_str = (
            f"{lifetime_return_pct:+.2f}%" if data.get('gross_buy_cost', 0.0) > 0 else "—"
        )
        slug = data.get("cmc_slug", asset.lower())
        cmc_url = f"https://coinmarketcap.com/currencies/{slug}/"

        table_data.append({
            "Coin": cmc_url,
            "Asset": asset,
            "Invested_Numeric": data['total_cost'],
            "Holdings": f"{data['amount']:.6f} (${stats['current_val']:,.2f})",
            "Avg Price": f"${stats['avg_price']:.2f}",
            "New Avg": new_avg_str,
            "Current Price": f"${stats['price']:.2f}",
            "RSI (14)": f"{stats['rsi']:.1f}",
            "Unrealized PnL": unrealized_str,
            "Realized PnL": realized_str,
            "Lifetime Return": lifetime_return_str,
            "Strict Buy": strict_str,
            "Smart Buy": smart_str
        })

    df_metrics = pd.DataFrame(table_data)
    if not df_metrics.empty:
        df_metrics = df_metrics.sort_values(by="Invested_Numeric", ascending=False).drop(columns=["Invested_Numeric"])
        df_metrics.index = range(1, len(df_metrics) + 1)
    
    def _pnl_style(value):
        text = str(value).strip()
        if text.startswith('+'):
            return 'color: #22c55e; font-weight: 600'
        if text.startswith('-'):
            return 'color: #ef4444; font-weight: 600'
        return ''

    styled_metrics = df_metrics.style.map(
        _pnl_style, subset=["Unrealized PnL", "Realized PnL", "Lifetime Return"]
    )

    st.dataframe(
        styled_metrics,
        width='stretch',
        column_config={
            "Coin": st.column_config.LinkColumn("Coin Link", display_text=r"https://coinmarketcap.com/currencies/(.*?)/"),
            "Asset": None
        }
    )

    # Separate technical dashboard: informational only and independent from
    # Strict Buy / Smart Buy allocation calculations.
    with st.expander("Technical Analysis — Trend & Momentum", expanded=False):
        st.caption(
            "Technical indicators are informational only. They do not change Strict Buy or Smart Buy. "
            "Trend compares the current CMC price with the 50-day moving average; momentum is calculated from daily Yahoo Finance closes."
        )
        technical_rows = []
        for asset, data in portfolio_data.items():
            if data["amount"] <= 1e-4 or asset not in current_values:
                continue
            stats = current_values[asset]
            price = stats["price"]
            has_sma = stats.get("has_sma_50", False)
            has_bb = stats.get("has_bollinger", False)
            sma = stats.get("sma_50")
            rsi_val = stats.get("rsi")
            m24 = stats.get("momentum_24h")
            m7 = stats.get("momentum_7d")

            if has_sma and sma and sma > 0:
                trend = "ABOVE SMA 50" if price >= sma else "BELOW SMA 50"
                trend_numeric = 1 if price >= sma else -1
            else:
                trend = "N/A"
                trend_numeric = 0

            if has_bb:
                if price <= stats["bb_lower"]:
                    bb_status = "Near/below lower"
                elif price >= stats["bb_upper"]:
                    bb_status = "Near/above upper"
                elif price < stats["bb_mid"]:
                    bb_status = "Lower half"
                else:
                    bb_status = "Upper half"
            else:
                bb_status = "N/A"

            # Simple transparent summary, not a trading instruction.
            bullish_points = int(trend_numeric == 1) + int(m7 is not None and m7 > 0) + int(rsi_val >= 50)
            bearish_points = int(trend_numeric == -1) + int(m7 is not None and m7 < 0) + int(rsi_val < 50)
            if not has_sma and m7 is None:
                signal = "INSUFFICIENT DATA"
            elif bullish_points >= bearish_points + 2:
                signal = "BULLISH"
            elif bearish_points >= bullish_points + 2:
                signal = "BEARISH"
            else:
                signal = "NEUTRAL"

            technical_rows.append({
                "Coin": asset,
                "RSI (14)": f"{rsi_val:.1f}" if rsi_val is not None else "N/A",
                "SMA 50": f"${sma:,.4f}" if has_sma and sma is not None else "N/A",
                "Trend": trend,
                "Bollinger Bands": bb_status,
                "24h Momentum": f"{m24:+.2f}%" if m24 is not None else "N/A",
                "7d Momentum": f"{m7:+.2f}%" if m7 is not None else "N/A",
                "Signal Summary": signal
            })

        if technical_rows:
            technical_df = pd.DataFrame(technical_rows)
            def _technical_style(value):
                value = str(value)
                if value in {"BULLISH", "ABOVE SMA 50"}:
                    return "color: #22c55e; font-weight: 600"
                if value in {"BEARISH", "BELOW SMA 50"}:
                    return "color: #ef4444; font-weight: 600"
                if value == "NEUTRAL":
                    return "color: #f59e0b; font-weight: 600"
                return ""
            technical_styled = technical_df.style.map(
                _technical_style, subset=["Trend", "Signal Summary"]
            )
            st.dataframe(technical_styled, width="stretch", hide_index=True)
        else:
            st.info("No active positions with available technical data.")

# --- TAB 2: ANALYTICS ---
with tab2:
    st.markdown("##### Capital Invested & Portfolio Value Timeline")
    if not raw_df_initial.empty:
        try:
            date_col = next((c for c in raw_df_initial.columns if 'date' in c.lower()), None)
            cost_col = next((c for c in raw_df_initial.columns if 'cost' in c.lower() or 'usd' in c.lower()), None)
            
            if date_col and cost_col:
                raw_tx_df = raw_df_initial.copy()
                asset_col = next((c for c in raw_tx_df.columns if 'asset' in c.lower()), None)
                amount_col = next((c for c in raw_tx_df.columns if 'amount' in c.lower()), None)
                raw_tx_df[date_col] = pd.to_datetime(raw_tx_df[date_col], errors='coerce')
                raw_tx_df = raw_tx_df.dropna(subset=[date_col])
                
                daily_costs = raw_tx_df.groupby(date_col)[cost_col].sum().reset_index().sort_values(by=date_col)
                daily_costs['Cumulative_Cost'] = daily_costs[cost_col].cumsum()
                
                full_calendar = pd.date_range(start=daily_costs[date_col].min(), end=pd.to_datetime(datetime.now().strftime("%Y-%m-%d")))
                timeline_df = pd.merge(pd.DataFrame({date_col: full_calendar}), daily_costs[[date_col, 'Cumulative_Cost']], on=date_col, how='left')
                timeline_df['Cumulative_Cost'] = timeline_df['Cumulative_Cost'].ffill().fillna(0)
                
                # Build a real historical portfolio value instead of interpolating
                # a straight line between the first and current values.
                timeline_df['Portfolio_Value'] = 0.0
                timeline_dates = timeline_df[date_col].dt.normalize()
                asset_list = sorted(set(str(a).upper().strip() for a in raw_tx_df[asset_col].dropna()))

                # Replay the ledger day by day to get holdings as they actually existed.
                tx_work = raw_tx_df[[date_col, asset_col, amount_col]].copy()
                tx_work[asset_col] = tx_work[asset_col].astype(str).str.upper().str.strip()
                tx_work[amount_col] = pd.to_numeric(tx_work[amount_col], errors='coerce').fillna(0.0)
                tx_work['_day'] = tx_work[date_col].dt.normalize()
                daily_changes = tx_work.groupby(['_day', asset_col])[amount_col].sum().unstack(fill_value=0.0)
                daily_changes = daily_changes.reindex(timeline_dates, fill_value=0.0).fillna(0.0)
                historical_holdings = daily_changes.cumsum()

                start_date = timeline_dates.min()
                end_date = timeline_dates.max() + pd.Timedelta(days=1)

                for asset in asset_list:
                    if asset not in historical_holdings.columns:
                        continue
                    ticker_str = "HYPE32196-USD" if asset == "HYPE" else f"{asset}-USD"
                    try:
                        hist = fetch_asset_history(
                            asset,
                            start_date.strftime("%Y-%m-%d"),
                            end_date.strftime("%Y-%m-%d")
                        )
                        if hist.empty:
                            continue
                        hist.index = pd.to_datetime(hist.index).tz_localize(None).normalize()
                        prices = hist['Close'].groupby(hist.index).last()
                        prices = prices.reindex(timeline_dates).ffill().bfill()
                        holdings = historical_holdings[asset].clip(lower=0.0)
                        timeline_df['Portfolio_Value'] += holdings.to_numpy() * prices.to_numpy()
                    except Exception:
                        # If an asset has no Yahoo Finance history, keep the other assets
                        # in the real timeline rather than fabricating a straight line.
                        continue

                fig_timeline = go.Figure()
                fig_timeline.add_trace(go.Scatter(x=timeline_df[date_col], y=timeline_df['Cumulative_Cost'], mode='lines', name='Active Net Cost ($)', line=dict(color='#71717a', width=1.5)))
                fig_timeline.add_trace(go.Scatter(x=timeline_df[date_col], y=timeline_df['Portfolio_Value'], mode='lines', name='Market Value ($)', line=dict(color='#3b82f6', width=2), fill='tonexty', fillcolor='rgba(59, 130, 246, 0.05)'))
                fig_timeline.update_layout(paper_bgcolor="#09090b", plot_bgcolor="#121215", font_color="#f4f4f5", hovermode="x unified", xaxis=dict(gridcolor='#27272a'), yaxis=dict(gridcolor='#27272a'))
                st.plotly_chart(fig_timeline, width='stretch')
        except Exception:
            pass

    col_chart1, col_chart2 = st.columns(2)
    with col_chart1:
        if current_values:
            fig_pie = px.pie(names=list(current_values.keys()), values=[info["current_val"] for info in current_values.values()], title="Asset Weight Distribution", hole=0.45)
            fig_pie.update_layout(paper_bgcolor="#09090b", plot_bgcolor="#121215", font_color="#f4f4f5")
            st.plotly_chart(fig_pie, width='stretch')
        
    with col_chart2:
        if current_values:
            assets_list = list(current_values.keys())
            net_pnls = [info["pnl_usd"] + info["realized_pnl"] for info in current_values.values()]
            colors = ['#10b981' if v >= 0 else '#ef4444' for v in net_pnls]
            fig_bar = go.Figure(data=[go.Bar(x=assets_list, y=net_pnls, marker_color=colors)])
            fig_bar.update_layout(title="Total Net PnL (Unrealized + Realized) ($)", paper_bgcolor="#09090b", plot_bgcolor="#121215", font_color="#f4f4f5", xaxis=dict(gridcolor='#27272a'), yaxis=dict(gridcolor='#27272a'))
            st.plotly_chart(fig_bar, width='stretch')

# --- TAB 6: PROFIT TAKING & REBALANCING ---
with tab6:
    st.markdown("### Profit Taking & Rebalance")
    st.caption("Ξεχωριστό εργαλείο για κατοχύρωση κερδών και επαναφορά των βαρών του portfolio. Δεν αλλάζει το Overview ή τα Strict/Smart Buy.")

    active_tool_assets = [
        a for a in current_values
        if a in portfolio_data and portfolio_data[a]["amount"] > 1e-8 and current_values[a]["price"] > 0
    ]

    if not active_tool_assets:
        st.info("Δεν υπάρχουν ενεργές θέσεις με διαθέσιμη τιμή για υπολογισμό.")
    else:
        coin_icons = {"BTC": "₿", "ETH": "◆", "SOL": "◎", "ZEC": "◈", "HYPE": "⬡", "BNB": "◆", "XRP": "✕", "ADA": "●", "DOGE": "Ð", "LTC": "Ł", "QNT": "◉"}
        if st.session_state.get("profit_rebalance_asset") not in active_tool_assets:
            st.session_state["profit_rebalance_asset"] = "ZEC" if "ZEC" in active_tool_assets else active_tool_assets[0]

        st.markdown("#### Select coin")
        # Compact, clearly highlighted coin buttons; selected coin uses Streamlit's primary style.
        button_cols = st.columns(min(5, len(active_tool_assets)))
        for i, asset in enumerate(active_tool_assets):
            col = button_cols[i % len(button_cols)]
            icon = coin_icons.get(asset, "●")
            with col:
                if st.button(
                    f"{icon}  {asset}",
                    key=f"profit_coin_{asset}",
                    type="primary" if st.session_state["profit_rebalance_asset"] == asset else "secondary",
                    use_container_width=True
                ):
                    st.session_state["profit_rebalance_asset"] = asset
                    st.rerun()

        selected_asset = st.session_state["profit_rebalance_asset"]
        selected_data = portfolio_data[selected_asset]
        selected_stats = current_values[selected_asset]
        holdings = float(selected_data["amount"])
        price_usd = float(selected_stats["price"])
        avg_price_usd = float(selected_stats.get("avg_price", 0.0) or 0.0)
        price_eur = price_usd * usd_to_eur
        holding_value_usd = float(selected_stats["current_val"])
        holding_value_eur = holding_value_usd * usd_to_eur
        current_weight = (holding_value_usd / total_current_portfolio * 100.0) if total_current_portfolio > 0 else 0.0

        st.markdown("---")
        metric_cols = st.columns(4)
        metric_cols[0].metric("Selected coin", selected_asset)
        metric_cols[1].metric("Holdings", f"{holdings:.8f}".rstrip("0").rstrip("."))
        metric_cols[2].metric("Current value", f"€{holding_value_eur:,.2f}", f"${holding_value_usd:,.2f}")
        metric_cols[3].metric("Portfolio weight", f"{current_weight:.2f}%")

        tool_mode = st.radio(
            "Choose action",
            ["💰 Take Profit", "⚖️ Rebalance"],
            horizontal=True,
            key="profit_rebalance_mode"
        )

        if tool_mode == "💰 Take Profit":
            st.markdown("#### Take profit calculator")
            st.caption("Υπολόγισε είτε πόσο κέρδος θέλεις να κατοχυρώσεις είτε πόση αξία θέλεις να πουλήσεις.")
            profit_mode = st.radio(
                "Calculation type",
                ["Target profit (€)", "Sell value (€)"],
                horizontal=True,
                key="profit_calc_mode"
            )
            target_eur = st.number_input(
                "Target amount (€)", min_value=0.01, value=40.0, step=5.0,
                key="profit_target_eur", help="Στο Target profit, είναι το εκτιμώμενο κέρδος. Στο Sell value, είναι η συνολική αξία πώλησης."
            )

            sell_qty = 0.0
            calculation_ok = False
            if profit_mode == "Target profit (€)":
                profit_per_coin_eur = (price_usd - avg_price_usd) * usd_to_eur
                if profit_per_coin_eur > 0 and holdings > 0:
                    sell_qty = target_eur / profit_per_coin_eur
                    calculation_ok = sell_qty <= holdings
                    if calculation_ok:
                        st.caption(f"Εκτιμώμενο κέρδος ανά {selected_asset}: €{profit_per_coin_eur:,.4f}, βάσει της μέσης τιμής κτήσης ${avg_price_usd:,.4f}.")
                    else:
                        st.warning(f"Για κέρδος €{target_eur:,.2f} θα χρειαζόταν να πουλήσεις περισσότερα από τα διαθέσιμα {selected_asset}.")
                else:
                    st.warning("Η τρέχουσα τιμή δεν είναι πάνω από τη μέση τιμή κτήσης, οπότε δεν μπορεί να υπολογιστεί θετικό κέρδος από πώληση.")
            else:
                sell_qty = target_eur / price_eur if price_eur > 0 else 0.0
                calculation_ok = sell_qty <= holdings
                if not calculation_ok:
                    st.warning("Η αξία πώλησης που επέλεξες υπερβαίνει τη συνολική αξία της θέσης.")

            if calculation_ok and sell_qty > 0:
                sell_qty = min(sell_qty, holdings)
                sell_usd = sell_qty * price_usd
                sell_eur = sell_usd * usd_to_eur
                sell_pct = sell_qty / holdings * 100.0 if holdings > 0 else 0.0
                estimated_profit_eur = (price_usd - avg_price_usd) * sell_qty * usd_to_eur
                remaining_qty = holdings - sell_qty
                result_cols = st.columns(3)
                result_cols[0].metric("Amount to sell", f"{sell_qty:.8f} {selected_asset}")
                result_cols[1].metric("% of this holding", f"{sell_pct:.2f}%")
                result_cols[2].metric("Sale value", f"€{sell_eur:,.2f}", f"${sell_usd:,.2f}")
                st.success(f"Μετά την πώληση θα σου μείνουν {remaining_qty:.8f} {selected_asset}.")
                if profit_mode == "Target profit (€)":
                    st.caption(f"Εκτιμώμενο κέρδος: €{estimated_profit_eur:,.2f} πριν από fees/spread. Η πραγματική καθαρή είσπραξη μπορεί να διαφέρει.")
                else:
                    st.caption(f"Εκτιμώμενο PnL στο ποσό που πουλάς: €{estimated_profit_eur:+,.2f} πριν από fees/spread.")
                st.info("Ο υπολογισμός είναι ενδεικτικός με βάση τη μέση τιμή κτήσης που εμφανίζει το portfolio. Δεν εκτελεί συναλλαγή.")

        else:
            st.markdown("#### Rebalance calculator")
            st.caption("Αν ένα coin ξεφύγει πάνω από το βάρος-στόχο, υπολογίζουμε πόσο να πουλήσεις για να επιστρέψει στο επιθυμητό ποσοστό.")
            configured_target_pct = float(selected_data.get("target_pct", 0.0) or 0.0) * 100.0
            default_target_pct = configured_target_pct if configured_target_pct > 0 else min(100.0, round(current_weight, 2))
            target_weight_pct = st.number_input(
                "Target portfolio weight (%)", min_value=0.0, max_value=100.0,
                value=float(default_target_pct), step=0.5, key=f"rebalance_target_{selected_asset}",
                help="Αν το coin έχει target weight στο DCA setup, αυτό χρησιμοποιείται ως αρχική τιμή. Μπορείς να τον αλλάξεις εδώ χωρίς να αλλάξεις τις ρυθμίσεις DCA."
            )
            target_value_usd = total_current_portfolio * (target_weight_pct / 100.0)
            excess_value_usd = holding_value_usd - target_value_usd
            if total_current_portfolio <= 0:
                st.warning("Δεν υπάρχει διαθέσιμη συνολική αξία portfolio για rebalance.")
            elif excess_value_usd > 0 and price_usd > 0:
                qty_to_sell = min(holdings, excess_value_usd / price_usd)
                value_to_sell_usd = qty_to_sell * price_usd
                value_to_sell_eur = value_to_sell_usd * usd_to_eur
                pct_to_sell = qty_to_sell / holdings * 100.0 if holdings > 0 else 0.0
                after_weight = ((holding_value_usd - value_to_sell_usd) / total_current_portfolio * 100.0)
                rb_cols = st.columns(3)
                rb_cols[0].metric("Amount to sell", f"{qty_to_sell:.8f} {selected_asset}")
                rb_cols[1].metric("Sell from holding", f"{pct_to_sell:.2f}%")
                rb_cols[2].metric("Estimated proceeds", f"€{value_to_sell_eur:,.2f}", f"${value_to_sell_usd:,.2f}")
                st.success(f"Βάρος μετά την πώληση: περίπου {after_weight:.2f}% (στόχος {target_weight_pct:.2f}%).")
                st.caption("Ο υπολογισμός κρατά σταθερή τη συνολική αξία του portfolio πριν από fees και μεταβολές τιμών. Δεν εκτελεί συναλλαγή.")
            elif excess_value_usd < 0:
                shortfall_usd = abs(excess_value_usd)
                st.info(f"Το {selected_asset} είναι κάτω από τον στόχο. Για να φτάσει το {target_weight_pct:.2f}% χρειάζονται περίπου ${shortfall_usd:,.2f} (€{shortfall_usd * usd_to_eur:,.2f}) αγοράς, όχι πώληση.")
            else:
                st.success(f"Το {selected_asset} είναι ήδη στο βάρος-στόχο ({target_weight_pct:.2f}%). Δεν απαιτείται rebalance.")


# --- TAB 3: LEDGERS & EXPORT ---
with tab3:
    st.markdown("##### Raw Transaction Ledger & Data Export")
    
    col_exp1, col_exp2 = st.columns(2)
    
    with col_exp1:
        if not raw_df_initial.empty:
            csv_ledger = raw_df_initial.to_csv(index=False).encode('utf-8')
            st.download_button(
                label="Download Transaction Ledger (CSV)",
                data=csv_ledger,
                file_name=f"crypto_ledger_{datetime.now().strftime('%Y%m%d')}.csv",
                mime="text/csv"
            )

    with col_exp2:
        if not df_metrics.empty:
            csv_summary = df_metrics.to_csv(index=False).encode('utf-8')
            st.download_button(
                label="Download Portfolio Summary (CSV)",
                data=csv_summary,
                file_name=f"portfolio_summary_{datetime.now().strftime('%Y%m%d')}.csv",
                mime="text/csv"
            )

    st.markdown("---")
    if not raw_df_initial.empty:
        display_df = raw_df_initial.copy()
        display_df.index = display_df.index + 1
        st.dataframe(display_df, width='stretch')

# --- TAB 4: SMART ADVISOR ---
with tab4:
    col_adv_1, col_adv_2 = st.columns(2)
    with col_adv_1:
        st.markdown("##### Smart DCA Engine")
        st.caption(f"Fear & Greed Index: {fng_value}/100 ({fng_label})")
        selected_dca_asset = st.selectbox("Select Asset to Evaluate:", list(current_values.keys()) if current_values else ["BTC"])
        
        if selected_dca_asset and selected_dca_asset in current_values:
            stats = current_values[selected_dca_asset]
            score = stats["score"]
            st.markdown(f"#### Score: `{score} / 100`")
            if score >= 70:
                st.success("Strong Accumulation Zone (High Dip Potential)")
            elif score >= 45:
                st.info("Neutral Market Conditions (Standard DCA)")
            else:
                st.warning("Overbought / Hold Cash Zone")
                    
    with col_adv_2:
        st.markdown("##### Target Profit Extractor")
        target_profit_goal = st.number_input("Desired Profit Extraction ($)", value=200.0, step=50.0)
        if total_unrealized_pnl > 0:
            profitable_assets = {k: v for k, v in current_values.items() if v["pnl_usd"] > 0}
            if profitable_assets:
                total_prof_sum = sum(v["pnl_usd"] for v in profitable_assets.values())
                extract_data = []
                for asset, stats in profitable_assets.items():
                    dollar_to_pull = target_profit_goal * (stats["pnl_usd"] / total_prof_sum)
                    amount_to_sell = dollar_to_pull / stats["price"] if stats["price"] > 0 else 0
                    holding_amt = portfolio_data[asset]["amount"]
                    pct_of_holding = (amount_to_sell / holding_amt * 100) if holding_amt > 0 else 0
                    
                    extract_data.append({
                        "Asset": asset,
                        "Sell Amount": f"{amount_to_sell:.6f} {asset}",
                        "% of Holding": f"{pct_of_holding:.1f}%",
                        "Cash Proceeds": f"${dollar_to_pull:,.2f}"
                    })
                st.table(pd.DataFrame(extract_data))

# --- TAB 5: RISK & EXIT LADDERING ---
with tab5:
    st.markdown("##### Take-Profit Laddering Strategy")
    st.caption("Ορίστε σταδιακά επίπεδα πωλήσεων (Laddering) για να κλειδώνετε κέρδη με βάση το πλάνο σας.")

    active_assets_list = [a for a in current_values.keys() if current_values[a]["current_val"] > 0]
    
    if active_assets_list:
        tp_asset = st.selectbox("Select Asset for Take-Profit Plan:", active_assets_list)
        asset_stats = current_values[tp_asset]
        current_holdings = portfolio_data[tp_asset]["amount"]
        current_price = asset_stats["price"]
        
        col_l1, col_l2, col_l3 = st.columns(3)
        
        with col_l1:
            st.markdown("**Tier 1**")
            tp1_gain = st.number_input("Target 1 Gain %", value=30.0, step=5.0, key="tp1_g")
            tp1_sell_pct = st.number_input("Sell % of Holdings (T1)", value=25.0, step=5.0, key="tp1_s")
            
        with col_l2:
            st.markdown("**Tier 2**")
            tp2_gain = st.number_input("Target 2 Gain %", value=70.0, step=5.0, key="tp2_g")
            tp2_sell_pct = st.number_input("Sell % of Holdings (T2)", value=35.0, step=5.0, key="tp2_s")

        with col_l3:
            st.markdown("**Tier 3**")
            tp3_gain = st.number_input("Target 3 Gain %", value=150.0, step=10.0, key="tp3_g")
            tp3_sell_pct = st.number_input("Sell % of Holdings (T3)", value=40.0, step=5.0, key="tp3_s")

        ladders = [
            ("Tier 1", tp1_gain, tp1_sell_pct),
            ("Tier 2", tp2_gain, tp2_sell_pct),
            ("Tier 3", tp3_gain, tp3_sell_pct)
        ]
        
        ladder_results = []
        rem_coins = current_holdings
        
        for name, gain, sell_p in ladders:
            target_p = current_price * (1 + gain / 100.0)
            coins_to_sell = current_holdings * (sell_p / 100.0)
            usd_proceeds = coins_to_sell * target_p
            rem_coins -= coins_to_sell
            
            ladder_results.append({
                "Level": name,
                "Target Price ($)": f"${target_p:,.2f} (+{gain:.0f}%)",
                "Coins to Sell": f"{coins_to_sell:.6f} {tp_asset}",
                "Cash Out ($)": f"${usd_proceeds:,.2f}",
                "Remaining Balance": f"{max(0, rem_coins):.6f} {tp_asset}"
            })
            
        st.markdown("###### Laddering Execution Schedule")
        st.table(pd.DataFrame(ladder_results))

    st.markdown("---")
    st.markdown("##### Standard Stop Loss & Take Profit Thresholds")
    calc_basis = st.radio("Basis:", ["Current Price", "Average Cost"], horizontal=True)
    
    for asset, data in portfolio_data.items():
        if data["amount"] <= 1e-4 or asset not in current_values:
            continue
        stats = current_values[asset]
        base_price = stats['price'] if "Current" in calc_basis else stats['avg_price']
        
        c_left, c_mid, c_right = st.columns([1.2, 2.4, 2.4])
        with c_left:
            st.markdown(f"**{asset}** | Price: `${stats['price']:,.2f}`")
        with c_mid:
            sl_pct = st.slider(f"SL % {asset}", -50.0, -1.0, -10.0, step=1.0, key=f"sl_{asset}", label_visibility="collapsed")
            sl_price = base_price * (1 + sl_pct / 100.0)
            st.markdown(f"SL: `${sl_price:,.2f}` ({sl_pct}%)")
        with c_right:
            tp_pct = st.slider(f"TP % {asset}", 5.0, 300.0, 50.0, step=5.0, key=f"tp_{asset}", label_visibility="collapsed")
            tp_price = base_price * (1 + tp_pct / 100.0)
            st.markdown(f"TP: `${tp_price:,.2f}` (+{tp_pct}%)")
