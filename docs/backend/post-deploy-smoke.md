# Post-deploy smoke

Run after deployment (T+5m and T+15m checkpoints):

```bash
cd /Users/alanzeng/Desktop/Projects/Haven
python scripts/run_post_deploy_smoke.py \
  --base-url "https://<your-haven-domain>" \
  --output /tmp/post-deploy-smoke-summary.json
```

Required checks:

- `/health` responds `200`
- `/health/slo` responds `200` with:
  - `sli.notification_runtime`
  - `sli.dynamic_content_runtime`
  - `checks.notification_outbox_depth`
- domain probes:
  - auth
  - journal
  - card
  - memory
  - notification
