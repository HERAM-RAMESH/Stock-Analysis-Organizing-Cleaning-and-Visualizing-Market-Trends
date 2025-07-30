import streamlit as st
import pandas as pd
from sqlalchemy import create_engine
import os
from dotenv import load_dotenv
import seaborn as sns
import matplotlib.pyplot as plt

st.set_page_config(page_title="Nifty 50 Stock Dashboard", layout="wide")

# Load environment variables
load_dotenv()

# Database credentials
host = os.getenv("DB_HOST")
port = int(os.getenv("DB_PORT"))
user = os.getenv("DB_USER")
password = os.getenv("DB_PASSWORD")
database = os.getenv("DB_NAME")

def get_data():
    db_url = f"mysql+pymysql://{user}:{password}@{host}:{port}/{database}"
    engine = create_engine(db_url)
    query = "SELECT * FROM stock_prices"
    df = pd.read_sql(query, engine)
    return df

# Load data
df = get_data()

st.title("📈 Nifty 50 Stock Analysis Dashboard")

# Sidebar filters
st.sidebar.header("Filter Options")
symbols = df["symbol"].unique().tolist()
dates = df["date"].sort_values().unique().tolist()

selected_symbol = st.sidebar.selectbox("Select Stock Symbol", symbols)
selected_date = st.sidebar.selectbox("Select Date", dates[::-1])

# Filtered Data
filtered_df = df[(df["symbol"] == selected_symbol) & (df["date"] == selected_date)]
st.subheader(f"Latest Records for {selected_symbol} on {selected_date}")
st.dataframe(filtered_df)

# Show top 10 recent records
df_sorted = df[df["symbol"] == selected_symbol].sort_values("date", ascending=False)
st.subheader(f"Recent Records for {selected_symbol}")
st.dataframe(df_sorted.head(10))

# ---- Visualizations ---- #
def market_summary(df):
    st.subheader("Market Summary")

    # Get latest available data for each stock
    latest_df = df.sort_values("date").groupby("symbol").last().reset_index()

    # Green vs Red
    latest_df["color"] = latest_df.apply(lambda row: "Green" if row["close"] > row["open"] else "Red", axis=1)
    green_count = (latest_df["color"] == "Green").sum()
    red_count = (latest_df["color"] == "Red").sum()

    # Average closing price and volume
    avg_price = latest_df["close"].mean()
    avg_volume = latest_df["volume"].mean()

    # Summary Table
    summary_df = df.groupby("symbol").agg({"open": "first", "close": "last"})
    summary_df["return %"] = ((summary_df["close"] - summary_df["open"]) / summary_df["open"]) * 100

    # Show metrics
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("🟢 Green Stocks", green_count)
        st.metric("🔴 Red Stocks", red_count)
    with col2:
        st.metric("💰 Avg. Close Price", f"{avg_price:.2f}")
    with col3:
        st.metric("📊 Avg. Volume", f"{avg_volume:,.0f}")

    # Show Return % Table
    st.write("**Stock Returns (%):**")
    st.dataframe(summary_df.sort_values("return %", ascending=False).reset_index(), use_container_width=True)


def gainers_losers(df):
    st.subheader("Top 10 Gainers and  Top 10 Losers")
    
    daily = df.groupby("symbol").agg({"open": "first", "close": "last"})
    daily["change %"] = ((daily["close"] - daily["open"]) / daily["open"]) * 100
    

    gainers = daily.sort_values("change %", ascending=False).head(10)
    losers = daily[daily["change %"] < 0].sort_values("change %").head(10)
    #losers = daily.sort_values("change %").head(10)


    col1, col2 = st.columns(2)
    with col1:
        st.write("🔼 **Top 10 Gainers**")
        st.bar_chart(gainers["change %"])
        st.dataframe(gainers.reset_index(), use_container_width=True)

    with col2:
        st.write("🔽 **Top 10 Losers**")
        st.bar_chart(losers["change %"])
        st.dataframe(losers.reset_index(), use_container_width=True)

def plot_volatility():
    st.subheader(" Stock Volatility")
    vol_df = df.copy()
    vol_df["volatility"] = vol_df["high"] - vol_df["low"]
    latest = vol_df.groupby("symbol")["volatility"].mean().sort_values(ascending=False)
    st.bar_chart(latest)

def cumulative_return(df):
    st.subheader("Cumulative Return")
    cum_df = df.copy()
    cum_df.sort_values(["symbol", "date"], inplace=True)
    cum_df["daily_return"] = cum_df.groupby("symbol")["close"].pct_change()
    cum_df["cumulative_return"] = (1 + cum_df["daily_return"]).groupby(cum_df["symbol"]).cumprod()
    selected = st.multiselect("Select stocks for cumulative return", df["symbol"].unique().tolist(), default=["RELIANCE", "INFY"])
    chart_df = cum_df[cum_df["symbol"].isin(selected)].pivot(index="date", columns="symbol", values="cumulative_return")
    st.line_chart(chart_df)

def sector_performance(df):
    st.subheader("Sector Performance ")
    if os.path.exists("sector_mapping.csv"):
        sector_map = pd.read_csv("sector_mapping.csv")
        merged = pd.merge(df, sector_map, on="symbol")
        daily = merged.groupby(["sector", "symbol"]).agg({"open": "first", "close": "last"})
        daily["return %"] = ((daily["close"] - daily["open"]) / daily["open"]) * 100
        sector_perf = daily.groupby("sector")["return %"].mean().sort_values(ascending=False)
        st.bar_chart(sector_perf)
    else:
        st.info("No sector_mapping.csv file found for sector-wise performance.")

def correlation_heatmap(df):
    st.subheader(" Correlation Heatmap of Closing Prices")
    pivot_df = df.pivot(index="date", columns="symbol", values="close")
    corr = pivot_df.corr()
    fig, ax = plt.subplots(figsize=(10, 8))
    sns.heatmap(corr, annot=False, cmap="coolwarm", ax=ax)
    st.pyplot(fig)

# Month wise Top 5 Gainers and Losers
def monthly_gainers_losers(df):
    st.subheader(" Monthly Top 5 Gainers and Losers")

    df["date"] = pd.to_datetime(df["date"])
    df["month"] = df["date"].dt.to_period("M")

    monthly = df.sort_values("date").groupby(["symbol", "month"]).agg({"open": "first", "close": "last"})
    monthly["return %"] = ((monthly["close"] - monthly["open"]) / monthly["open"]) * 100
    monthly = monthly.reset_index()

    unique_months = sorted(monthly["month"].unique(), reverse=True)

    for month in unique_months:
        st.markdown(f"###  {month}")
        month_data = monthly[monthly["month"] == month]
        gainers = month_data.sort_values("return %", ascending=False).head(5)
        losers = month_data.sort_values("return %").head(5)

        col1, col2 = st.columns(2)
        with col1:
            st.write("🔼 Top 5 Gainers")
            st.bar_chart(data=gainers.set_index("symbol")["return %"])
            st.dataframe(gainers[["symbol", "return %"]].reset_index(drop=True), use_container_width=True)

        with col2:
            st.write("🔽 Top 5 Losers")
            st.bar_chart(data=losers.set_index("symbol")["return %"])
            st.dataframe(losers[["symbol", "return %"]].reset_index(drop=True), use_container_width=True)



# 🔽 Call all functions
market_summary(df)
gainers_losers(df)
plot_volatility()
cumulative_return(df)
sector_performance(df)
correlation_heatmap(df)
monthly_gainers_losers(df) 
