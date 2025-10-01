# =========================================
# Mobile-Friendly NSE Options Dashboard (No API Keys)
# =========================================

import streamlit as st
import pandas as pd
import numpy as np
import requests
import talib as ta
from datetime import datetime
import time

st.set_page_config(page_title="Top Options Scan", layout="wide")

st.title("📱 Mobile-Friendly NSE Options Dashboard (No API Keys)")
REFRESH_INTERVAL = 30  # seconds
st.markdown(f"Refresh interval: {REFRESH_INTERVAL} seconds")

# List of stocks to scan (you can add more)
STOCKS = ["RELIANCE", "TCS", "INFY", "HINDUNILVR", "ICICIBANK"]

# Function to fetch NSE option chain
def fetch_option_chain(stock):
    url = f"https://www.nseindia.com/api/option-chain-equities?symbol={stock}"
    headers = {
        "User-Agent": "Mozilla/5.0",
        "Accept-Language": "en-US,en;q=0.9",
        "Accept-Encoding": "gzip, deflate, br"
    }
    session = requests.Session()
    session.get("https://www.nseindia.com", headers=headers)  # get cookies
    response = session.get(url, headers=headers)
    data = response.json()
    
    ce_list = data['records']['data']
    option_data = []
    
    for item in ce_list:
        if 'CE' in item:
            ce = item['CE']
            option_data.append({
                "Stock": stock,
                "Type": "CE",
                "Strike": ce['strikePrice'],
                "LTP": ce['lastPrice'],
                "OI": ce['openInterest'],
                "Volume": ce['totalTradedVolume']
            })
        if 'PE' in item:
            pe = item['PE']
            option_data.append({
                "Stock": stock,
                "Type": "PE",
                "Strike": pe['strikePrice'],
                "LTP": pe['lastPrice'],
                "OI": pe['openInterest'],
                "Volume": pe['totalTradedVolume']
            })
    return pd.DataFrame(option_data)

# Main execution
def run_scan():
    all_data = pd.DataFrame()
    
    for stock in STOCKS:
        try:
            df = fetch_option_chain(stock)
            all_data = pd.concat([all_data, df], ignore_index=True)
        except:
            continue

    # Calculate simple indicators
    for stock in STOCKS:
        stock_df = all_data[all_data["Stock"]==stock]
        prices = stock_df["LTP"].values
        if len(prices) > 10:
            all_data.loc[all_data["Stock"]==stock, "EMA_20"] = ta.EMA(prices, timeperiod=20)
            all_data.loc[all_data["Stock"]==stock, "SMA_50"] = ta.SMA(prices, timeperiod=50)
            all_data.loc[all_data["Stock"]==stock, "RSI_14"] = ta.RSI(prices, timeperiod=14)
            all_data.loc[all_data["Stock"]==stock, "ATR_14"] = ta.ATR(prices, prices, prices, timeperiod=14)
            # Support/Resistance (basic)
            all_data.loc[all_data["Stock"]==stock, "Support"] = pd.Series(prices).rolling(window=20).min().iloc[-1]
            all_data.loc[all_data["Stock"]==stock, "Resistance"] = pd.Series(prices).rolling(window=20).max().iloc[-1]

    # Generate signals
    def signal(row):
        if row["LTP"] > row.get("EMA_20",0) and row.get("RSI_14",50) < 70:
            return "Bullish"
        elif row["LTP"] < row.get("EMA_20",0) and row.get("RSI_14",50) > 30:
            return "Bearish"
        else:
            return "Neutral"

    all_data["Signal"] = all_data.apply(signal, axis=1)

    # Entry / Stop / Target
    all_data["Entry"] = all_data["LTP"]
    all_data["Stop_Loss"] = np.where(all_data["Signal"]=="Bullish", all_data["LTP"] - all_data.get("ATR_14",0), all_data["LTP"] + all_data.get("ATR_14",0))
    all_data["Target"] = np.where(all_data["Signal"]=="Bullish", all_data["LTP"] + all_data.get("ATR_14",0), all_data["LTP"] - all_data.get("ATR_14",0))
    all_data["Timestamp"] = datetime.now().strftime("%d-%m-%Y %H:%M:%S")

    # Top 5 bullish and bearish
    top_bullish = all_data[all_data["Signal"]=="Bullish"].sort_values(by="OI", ascending=False).head(5)
    top_bearish = all_data[all_data["Signal"]=="Bearish"].sort_values(by="OI", ascending=False).head(5)

    # Show results
    st.subheader("🐂 Top 5 Bullish Options")
    st.table(top_bullish[["Stock","Type","Strike","Entry","Stop_Loss","Target","Support","Resistance","Signal","OI","Volume","Timestamp"]])

    st.subheader("🐻 Top 5 Bearish Options")
    st.table(top_bearish[["Stock","Type","Strike","Entry","Stop_Loss","Target","Support","Resistance","Signal","OI","Volume","Timestamp"]])

    st.markdown(f"Last updated: {datetime.now().strftime('%d-%m-%Y %H:%M:%S')}")

# Run app
run_scan()
