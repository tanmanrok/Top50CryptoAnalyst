"""
Time Series Analysis Module
Functions for analyzing trends, returns, and volatility in cryptocurrency data
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from scipy import stats as sp_stats


def calculate_returns(crypto_data):
    """
    Calculate daily, weekly, and monthly returns for each cryptocurrency.
    
    Parameters:
    -----------
    crypto_data : dict
        Dictionary of DataFrames containing cryptocurrency data
    
    Returns:
    --------
    dict
        Updated crypto_data dictionary with return columns added
    """
    for crypto_name, df in crypto_data.items():
        # Daily returns (percentage change)
        df['Daily_Return'] = df['Close'].pct_change() * 100
        
        # Weekly returns (every 7 days)
        df['Weekly_Return'] = df['Close'].pct_change(7) * 100
        
        # Monthly returns (every 30 days)
        df['Monthly_Return'] = df['Close'].pct_change(30) * 100
    
    return crypto_data


def calculate_volatility(crypto_data, window=30):
    """
    Calculate rolling volatility (standard deviation of returns).
    
    Parameters:
    -----------
    crypto_data : dict
        Dictionary of DataFrames containing cryptocurrency data
    window : int, default=30
        Rolling window size in days
    
    Returns:
    --------
    dict
        Updated crypto_data dictionary with volatility columns added
    """
    for crypto_name, df in crypto_data.items():
        df[f'Volatility_{window}'] = df['Daily_Return'].rolling(window=window).std()
    
    return crypto_data


def get_volatility_summary(crypto_data, window=30):
    """
    Generate summary statistics for volatility across all cryptocurrencies.
    
    Parameters:
    -----------
    crypto_data : dict
        Dictionary of DataFrames containing cryptocurrency data
    window : int, default=30
        Rolling window size in days
    
    Returns:
    --------
    pd.DataFrame
        Volatility summary statistics sorted by mean volatility
    """
    volatility_col = f'Volatility_{window}'
    volatility_summary = {}
    
    for crypto_name, df in crypto_data.items():
        volatility_summary[crypto_name] = {
            'Mean_Volatility': df[volatility_col].mean(),
            'Max_Volatility': df[volatility_col].max(),
            'Min_Volatility': df[volatility_col].min(),
            'Current_Volatility': df[volatility_col].iloc[-1]
        }
    
    volatility_df = pd.DataFrame(volatility_summary).T
    return volatility_df.sort_values('Mean_Volatility', ascending=False)


def calculate_trend_analysis(crypto_data):
    """
    Calculate trend using linear regression for each cryptocurrency.
    
    Parameters:
    -----------
    crypto_data : dict
        Dictionary of DataFrames containing cryptocurrency data
    
    Returns:
    --------
    dict
        Trend analysis statistics including slope, direction, and returns
    """
    trend_analysis = {}
    
    for crypto_name, df in crypto_data.items():
        # Prepare data (remove NaN values)
        df_clean = df[df['Daily_Return'].notna()].copy()
        if len(df_clean) == 0:
            continue
            
        X = np.arange(len(df_clean)).reshape(-1, 1)
        y = df_clean['Close'].values
        
        # Linear regression
        slope, intercept, r_value, p_value, std_err = sp_stats.linregress(X.flatten(), y)
        
        # Determine trend
        trend_direction = "Uptrend" if slope > 0 else "Downtrend"
        
        trend_analysis[crypto_name] = {
            'Slope': slope,
            'Trend': trend_direction,
            'R_squared': r_value ** 2,
            'Start_Price': df['Close'].iloc[0],
            'End_Price': df['Close'].iloc[-1],
            'Total_Return_%': ((df['Close'].iloc[-1] - df['Close'].iloc[0]) / df['Close'].iloc[0]) * 100
        }
    
    return pd.DataFrame(trend_analysis).T.sort_values('Slope', ascending=False)


def get_returns_summary(crypto_data):
    """
    Generate comprehensive returns summary statistics.
    
    Parameters:
    -----------
    crypto_data : dict
        Dictionary of DataFrames containing cryptocurrency data
    
    Returns:
    --------
    pd.DataFrame
        Returns summary with Sharpe ratio and win rate
    """
    returns_summary = {}
    
    for crypto_name, df in crypto_data.items():
        df_clean = df[df['Daily_Return'].notna()]
        if len(df_clean) == 0:
            continue
            
        daily_std = df_clean['Daily_Return'].std()
        sharpe = (df_clean['Daily_Return'].mean() / daily_std) if daily_std > 0 else 0
        
        returns_summary[crypto_name] = {
            'Mean_Daily_Return_%': df_clean['Daily_Return'].mean(),
            'Std_Daily_Return_%': daily_std,
            'Max_Daily_Return_%': df_clean['Daily_Return'].max(),
            'Min_Daily_Return_%': df_clean['Daily_Return'].min(),
            'Sharpe_Ratio': sharpe,
            'Positive_Days_%': (df_clean['Daily_Return'] > 0).sum() / len(df_clean) * 100
        }
    
    return pd.DataFrame(returns_summary).T


def plot_price_and_volatility(crypto_data, crypto_name, trend_analysis=None):
    """
    Plot price trend and rolling volatility for a single cryptocurrency.
    
    Parameters:
    -----------
    crypto_data : dict
        Dictionary of DataFrames containing cryptocurrency data
    crypto_name : str
        Name of the cryptocurrency to plot
    trend_analysis : pd.DataFrame, optional
        Trend analysis results for adding trend line
    
    Returns:
    --------
    None (displays plots)
    """
    if crypto_name not in crypto_data:
        print(f"Cryptocurrency {crypto_name} not found")
        return
    
    df = crypto_data[crypto_name]
    df_clean = df[df['Daily_Return'].notna()].copy()
    
    fig, axes = plt.subplots(2, 1, figsize=(14, 10))
    
    # Plot 1: Price with trend line
    ax1 = axes[0]
    ax1.plot(df_clean['Date'], df_clean['Close'], label='Close Price', linewidth=2, color='blue', alpha=0.7)
    
    if trend_analysis is not None and crypto_name in trend_analysis.index:
        X = np.arange(len(df_clean))
        slope = trend_analysis.loc[crypto_name, 'Slope']
        start_price = df_clean['Close'].iloc[0]
        trend_line = slope * X + start_price
        ax1.plot(df_clean['Date'], trend_line, 'r--', label=f"Trend (slope={slope:.2f})", linewidth=2)
    
    ax1.set_title(f"{crypto_name.upper()} - Price Trend Analysis")
    ax1.set_ylabel("Price ($)")
    ax1.legend()
    ax1.grid(True, alpha=0.3)
    
    # Plot 2: Volatility over time
    ax2 = axes[1]
    volatility_col = 'Volatility_30'
    if volatility_col in df_clean.columns:
        ax2.plot(df_clean['Date'], df_clean[volatility_col], label='30-day Rolling Volatility', linewidth=2, color='orange')
        ax2.fill_between(df_clean['Date'], df_clean[volatility_col], alpha=0.3, color='orange')
    
    ax2.set_title(f"{crypto_name.upper()} - Volatility Over Time")
    ax2.set_xlabel("Date")
    ax2.set_ylabel("Volatility (Std Dev %)")
    ax2.legend()
    ax2.grid(True, alpha=0.3)
    
    plt.tight_layout()
    plt.show()


def plot_returns_distribution(crypto_data, num_cryptos=10):
    """
    Plot daily returns distribution for multiple cryptocurrencies.
    
    Parameters:
    -----------
    crypto_data : dict
        Dictionary of DataFrames containing cryptocurrency data
    num_cryptos : int, default=10
        Number of cryptocurrencies to plot
    
    Returns:
    --------
    None (displays plots)
    """
    fig, axes = plt.subplots(5, 2, figsize=(14, 12))
    axes = axes.flatten()
    
    for idx, (crypto_name, df) in enumerate(list(crypto_data.items())[:num_cryptos]):
        df_clean = df[df['Daily_Return'].notna()]
        
        axes[idx].hist(df_clean['Daily_Return'], bins=50, edgecolor='black', alpha=0.7, color='skyblue')
        mean_return = df_clean['Daily_Return'].mean()
        axes[idx].axvline(mean_return, color='red', linestyle='--', linewidth=2, label=f"Mean: {mean_return:.2f}%")
        axes[idx].set_title(f"{crypto_name.upper()} - Daily Returns Distribution")
        axes[idx].set_xlabel("Daily Return (%)")
        axes[idx].set_ylabel("Frequency")
        axes[idx].legend(fontsize=8)
    
    plt.tight_layout()
    plt.show()
