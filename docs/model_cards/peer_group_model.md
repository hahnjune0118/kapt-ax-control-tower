# K-APT Peer Group Model Card

## 1. Model Overview

- Model version: `peer-group-v1.0`
- Target apartment: 마곡현대아파트 (`A15784601`)
- Candidate peers: 49
- Selected peers: 30
- Effective sample size: 29.75
- Weighted structural similarity: 89.67%
- Model-ready cost categories: 6/6

## 2. Purpose

This model selects structurally comparable apartment complexes and calculates a weighted expected management-cost range.

The result is intended for advisory screening and prioritization. It is not proof of inefficient management or a guaranteed saving amount.

## 3. Similarity Weights

| Feature | Weight |
|---|---:|
| Household count | 25% |
| Approval year | 20% |
| Management area per household | 15% |
| Building count | 10% |
| City district | 10% |
| Heating type | 8% |
| Management type | 7% |
| Hall type | 3% |
| Sale type | 2% |

## 4. Peer Selection

- Core peer: suitability score of at least 75 with sufficient profile and cost data
- Supporting peer: suitability score of at least 60 with sufficient cost data
- Selected peers: maximum 30
- Fallback: top 15 peers when threshold-based selection is insufficient

## 5. Expected Cost Range

The expected range is calculated using weighted peer quantiles:

- Low: weighted 25th percentile
- Expected: weighted median
- High: weighted 75th percentile

## 6. Limitations

- Public K-APT data may contain missing or delayed disclosures.
- High cost does not by itself demonstrate inefficiency.
- Facility quality, security scope, outsourcing contracts, and service levels require additional review.
- Indicative excess cost is not a guaranteed saving amount.
- Missing values are not automatically treated as zero.

## 7. Human Review Requirement

Every high-cost signal must be reviewed with contract documents, service scope, budget data, and management-office explanations before an advisory conclusion is issued.
