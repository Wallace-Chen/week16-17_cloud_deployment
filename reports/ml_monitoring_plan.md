# ML Monitoring Plan

## Scope

This service predicts next-day market direction from a compact feature payload. The production concern is not only whether the API is alive, but whether requests, predictions, feature distributions, and model behavior remain consistent with the training/reference population.

References used for this plan:

- Evidently AI data-drift concepts: data drift is a distribution shift in model inputs, and drift checks should compare current production data against a reference dataset.
- Arize ML monitoring concepts: useful monitors combine drift, data-quality, model-output, and performance checks instead of watching accuracy alone.

## What to Log Per Prediction

Each `/predict` request should create a structured audit event. The current implementation logs JSON to stdout and can optionally append a local CSV file when `MLOPS_PREDICTION_LOG_CSV` is set.

Recommended fields:

| Field | Purpose |
| --- | --- |
| `timestamp_utc` | Reconstruct event order and align with market/calendar windows. |
| `request_id` | Trace one API call through logs, alerts, and downstream systems. |
| `endpoint` | Separate prediction logs from future batch/metadata endpoints. |
| `ticker` | Segment behavior by instrument. |
| `model_version` | Preserve auditability and support rollback comparison. |
| `feature_count` | Detect malformed or schema-drifted requests. |
| `feature_mean`, `feature_std`, `feature_min`, `feature_max` | Compact input summary without storing full raw payloads. |
| `prediction` | Monitor class balance and abrupt output shifts. |
| `probability` | Monitor confidence distribution and calibration symptoms. |
| `latency_ms` | Detect service degradation. |
| `error_status` | Track success vs validation/model/runtime failures. |
| `error_message` | Debug validation failures without scraping stack traces. |

### Local CSV Logging

For local demos or offline analysis:

```bash
MLOPS_PREDICTION_LOG_CSV=logs/predictions.csv python scripts/run_local_api.py
python scripts/smoke_test_api.py
```

The service will create `logs/predictions.csv` with one row per prediction attempt. In production, the same event should be shipped to a logging backend such as CloudWatch, GCP Logging, Datadog, Grafana Loki, or OpenTelemetry collectors.

## Online Service Metrics

| Metric | Initial Threshold | Action |
| --- | ---: | --- |
| P50 latency | > 50 ms for 15 min | Check host load and dependency regressions. |
| P95 latency | > 200 ms for 15 min | Page/on-call in production; inspect recent deploys. |
| Error rate | > 1% over 15 min | Inspect validation failures and runtime exceptions. |
| 5xx rate | > 0.1% over 15 min | Roll back if tied to deployment. |
| Request volume | 3x baseline or near-zero unexpectedly | Check traffic source, outages, or client bugs. |

For this small FastAPI demo, these thresholds are intentionally conservative placeholders. In a real system they should be estimated from historical SLOs and business criticality.

## Data Quality Checks

Run these checks per rolling window, e.g. hourly for active traffic and daily for portfolio review:

1. **Missing/null rate:** alert if any required feature has nulls, NaNs, or non-numeric values.
2. **Range checks:** alert when a feature crosses hard business sanity bounds.
   - `volatility_20d < 0` is invalid.
   - absolute return features above a large threshold should be reviewed.
3. **Schema checks:** reject missing or unexpected feature keys at request time.
4. **Ticker segmentation:** track metrics separately for `SPY`, `NVDA`, `JPM`, etc. if more tickers are added.

## Drift Checks

Use the training/reference feature distribution as the baseline. For this demo, the model was trained from synthetic baseline data, so future improvement should save a real reference dataset summary under `models/reference_stats.json`.

### Feature Drift

For each feature, compare the current rolling production window against training/reference statistics:

- Mean shift: `abs(prod_mean - ref_mean) / ref_std`.
- Standard deviation ratio: `prod_std / ref_std`.
- Distribution test: Kolmogorov-Smirnov test for numeric features when enough samples exist.
- Population Stability Index (PSI) as a dashboard-friendly drift score.

Initial alert thresholds:

| Check | Warning | Critical |
| --- | ---: | ---: |
| Mean shift | > 2 reference std | > 3 reference std |
| Std ratio | < 0.5 or > 2.0 | < 0.25 or > 4.0 |
| PSI | > 0.10 | > 0.25 |
| KS p-value | < 0.05 | < 0.01 |

### Prediction Drift

Track output distribution even when labels are unavailable:

- Prediction class distribution: percentage of `prediction=1` vs `prediction=0`.
- Probability histogram: compare current distribution with reference inference distribution.
- Confidence extremes: share of predictions with `probability < 0.1` or `> 0.9`.

Initial alert thresholds:

| Check | Threshold |
| --- | ---: |
| Positive prediction rate shift | > 20 percentage points from reference |
| Mean probability shift | > 0.15 absolute |
| Probability std collapse | < 50% of reference std |

## Model Drift and Label-Based Monitoring

Financial labels arrive with delay. Once next-day outcomes are available, join requests with realized labels and monitor:

- Accuracy / balanced accuracy over rolling windows.
- Log loss or Brier score for probability quality.
- Confusion matrix by ticker and market regime.
- Calibration curve: predicted probability vs observed positive rate.
- Performance by volatility regime and volume regime.

Suggested retraining triggers:

1. Rolling balanced accuracy drops below a business-defined floor for two consecutive windows.
2. Log loss worsens by > 20% vs reference validation performance.
3. Critical feature drift persists for more than one trading day.
4. A market regime change invalidates the original training/reference period.

## Alert Routing

| Severity | Example | Response |
| --- | --- | --- |
| Info | Low request volume in demo | Log only. |
| Warning | PSI > 0.10 or P95 latency > 200 ms | Review dashboard and recent deploys. |
| Critical | 5xx spike, PSI > 0.25, severe accuracy drop | Roll back model/service or disable automated consumers. |

## Auditability and Compliance Notes

- Always log `model_version`; never overwrite a deployed artifact without changing metadata.
- Keep training code, artifact metadata, CI results, and monitoring reports tied to the same version.
- Avoid logging full raw features if they could contain sensitive client or account data; compact summaries are safer for routine service logs.
- For trading or finance use, prediction logs should be immutable enough to support post-trade review.

## Future Enhancements

1. Add `models/reference_stats.json` generated during training.
2. Add a scheduled monitoring script that reads `logs/predictions.csv` and emits drift metrics.
3. Export Prometheus/OpenTelemetry metrics from FastAPI middleware.
4. Store prediction logs in a durable database or object store partitioned by date.
5. Add a model registry workflow so deployment and rollback are versioned operations.
