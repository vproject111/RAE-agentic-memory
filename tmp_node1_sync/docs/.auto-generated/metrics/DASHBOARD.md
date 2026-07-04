# 📊 Documentation Automation Dashboard

**Real-time metrics for documentation CI health**

> **⚠️ AUTO-GENERATED** - This file is updated automatically by CI. Do not edit manually.

## 🟢 Current Status

![Status](https://img.shields.io/badge/status-success-brightgreen)
![Files Generated](https://img.shields.io/badge/files-8-blue)
![Success Rate](https://img.shields.io/badge/success_rate-100%25-brightgreen)
![Duration](https://img.shields.io/badge/duration-3.2s-blue)

**Last Run:** 2025-12-06 11:57:03
**Branch:** `develop`
**Commit:** [`9686b4881`](../../commit/9686b4881)

---

## 📈 Latest Run Metrics

| Metric | Value |
|--------|-------|
| **Run ID** | 20251206-115703 |
| **Duration** | 0.0s |
| **Files Generated** | 4 |
| **Errors** | 0 |
| **Warnings** | 0 |
| **Success Rate** | 100.0% |

---

## 📝 Files Generated (Latest Run)

| File | Generator | Timestamp |
|------|-----------|-----------|
| CHANGELOG.md | update_changelog | 2025-12-06 11:57:03 |
| STATUS.md | update_status | 2025-12-06 11:57:03 |
| TODO.md | update_todo | 2025-12-06 11:57:03 |
| TESTING_STATUS.md | update_testing_status | 2025-12-06 11:57:03 |

---

## 📊 Historical Trends (Last 50 Runs)

See [`automation-health-history.json`](./automation-health-history.json) for complete history.

**Quick Stats:**
- Average duration: ~3.5s
- Success rate: 100%
- Total runs tracked: 50

---

## 🔍 How to Use This Dashboard

### For Developers
- **Green status?** → Documentation CI is healthy, all generators working
- **Red status?** → Check errors section, investigate failing generator
- **Warnings?** → Non-critical issues, review but won't fail CI

### For CI/CD Monitoring
```bash
# Check latest metrics
cat docs/.auto-generated/metrics/automation-health.json | jq '.status'

# Alert if failed
if [ "$(cat docs/.auto-generated/metrics/automation-health.json | jq -r '.status')" == "failed" ]; then
  echo "❌ Documentation automation failed!"
  exit 1
fi
```

### For Admins
- Track duration trends to detect performance degradation
- Monitor success rate for reliability
- Review errors/warnings for maintenance needs

---

## 🛠️ Troubleshooting

### Dashboard not updating?
1. Check GitHub Actions: `gh run list --workflow=docs.yml`
2. Verify metrics tracker is running: `python scripts/metrics_tracker.py`
3. Check file permissions: `ls -la docs/.auto-generated/metrics/`

### Errors showing?
1. Review error details in `automation-health.json`
2. Check generator logs in GitHub Actions
3. Test generator locally: `python scripts/docs_automator.py`

---

## 📚 Related Documentation

- **Metrics Tracker:** [`scripts/metrics_tracker.py`](../../../scripts/metrics_tracker.py)
- **Automation Plan:** [`docs/project-design/active/DOCUMENTATION_AUTOMATION_PLAN.md`](../../project-design/active/DOCUMENTATION_AUTOMATION_PLAN.md)
- **Contributing Guide:** [`docs/CONTRIBUTING_DOCS.md`](../../CONTRIBUTING_DOCS.md)

---

**Last Updated:** Auto-generated on every CI run
**Source:** `docs/.auto-generated/metrics/automation-health.json`
**Maintained by:** GitHub Actions `.github/workflows/docs.yml`
