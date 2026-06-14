# Grafana

Default login: admin / admin (override via GF_SECURITY_ADMIN_PASSWORD).

Add Prometheus as a data source (URL: http://prometheus:9090), then build
panels on the metrics exposed by the API:

- `signals_generated_total`
- `orders_submitted_total`
- `orders_rejected_total`
- `open_positions`
- `market_data_latency_seconds`
