# Known Limitations & Risk Register

## Limitations
1. **Vertical Scaling Constraints**: HDBSCAN clustering happens entirely in memory. While fast, processing more than 100,000 alerts concurrently on a single container will risk an OOM Kill.
2. **Cold Start Penalty**: The first API request triggering `_ensure_loaded()` involves mounting `SentenceTransformers` from HuggingFace cache which takes ~15-20 seconds on CPU instances.

## Risk Register
1. **Risk ID 01: Concept Drift**
   - *Impact*: High. Over time, normal telemetry behaviors change, reducing the Isolation Forest accuracy.
   - *Mitigation*: MLOps cron jobs must be scheduled to re-fit the Anomaly models weekly.
2. **Risk ID 02: Redis Eviction**
   - *Impact*: Low. 
   - *Mitigation*: Ensure `maxmemory-policy allkeys-lru` is strictly set in production Redis configurations.
