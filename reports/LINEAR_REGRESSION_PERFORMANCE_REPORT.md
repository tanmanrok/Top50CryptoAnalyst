# Linear Regression Model - Performance Report

**Generated:** 2026-04-14 14:41:12

## Executive Summary
This report presents the comprehensive performance analysis of the Linear Regression model trained on 15 cryptocurrencies for price prediction using technical indicators and temporal features.

## Model Overview
- **Model Type:** Linear Regression (scikit-learn)
- **Training Date:** April 14, 2026
- **Cryptocurrencies:** 15 (avalanche, axie_infinity, binance_coin, bitcoin, chainlink, ethereum, fantom, injective, litecoin, maker, render, solana, the_graph, toncoin, tron)
- **Features:** 28 technical indicators and temporal features
- **Train/Test Split:** 80/20 temporal split
- **Cross-Validation:** TimeSeriesSplit (5-fold)

## Performance Metrics

### Definition of Key Metrics
- **R² Score:** Proportion of variance explained by model (0-1: higher is better)
- **MAPE (%):** Mean Absolute Percentage Error (lower is better)
- **MAE ($):** Mean Absolute Error in dollars (lower is better)
- **RMSE ($):** Root Mean Squared Error (lower is better)
- **Directional Accuracy (%):** Percentage of correct price movement predictions (higher is better)
- **Correlation:** Pearson correlation between actual and predicted prices

