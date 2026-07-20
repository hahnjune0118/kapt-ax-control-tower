# K-APT Hybrid Anomaly Detection Model Card

## 1. Model Overview

- Model version: `hybrid-anomaly-v1.0`
- Monthly target observations: 72
- Assessed observations: 66
- Alert observations: 1
- High or critical cost categories: 0/6

## 2. Purpose

The model screens monthly apartment management costs for unusual cost patterns and prioritizes areas for human review.

It does not determine fraud, overbilling, or inefficient management.

## 3. Signals

| Signal | Weight | Description |
|---|---:|---|
| Peer deviation | 50% | Robust deviation from the weighted peer median |
| Expected-range excess | 25% | Distance above the weighted peer 75th percentile |
| Temporal increase | 15% | Increase from the prior three-month median |
| Persistent excess | 10% | Consecutive months above the expected range |

## 4. Severity Thresholds

| Score | Severity |
|---:|---|
| 80–100 | Critical |
| 60–79.99 | High |
| 40–59.99 | Medium |
| 0–39.99 | Low |

## 5. Confidence Adjustment

The raw anomaly score is adjusted using:

- Target source-data quality
- Effective peer sample size
- Available peer-model weight

## 6. Limitations

- A high score is a review signal, not proof of inefficiency.
- One-time repairs can generate legitimate cost spikes.
- Differences in service quality and contract scope may explain cost differences.
- Missing values are not treated as zero.
- Unusually low costs are separately flagged because they may indicate incomplete disclosure or classification differences.

## 7. Required Human Review

Before issuing an advisory conclusion, review:

- Service contracts and renewal terms
- Staffing and operating scope
- Repair and maintenance records
- Budget-versus-actual reports
- Management-office explanations
