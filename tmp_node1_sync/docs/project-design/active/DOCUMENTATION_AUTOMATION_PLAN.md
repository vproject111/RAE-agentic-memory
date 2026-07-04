# RAE Documentation Automation Plan

**Created:** 2025-12-06
**Status:** Active
**Owner:** Automation Team

## Executive Summary

This document outlines a comprehensive, iterative plan to automate RAE documentation, ensuring it remains accurate, complete, and useful for diverse audiences (developers, government agencies, industry, researchers).

## Current State Analysis

### ✅ What Works
- **docs_automator.py**: Updates 4 files (CHANGELOG, STATUS, TODO, TESTING_STATUS)
- **GitHub Actions**: `.github/workflows/docs.yml` triggers on CI success
- **Conventional Commits**: Git history properly formatted
- **Test Coverage**: XML/JUnit reports available for metrics

### ❌ Problems Identified

1. **Duplicate Locations**: Files exist in both root and `docs/.auto-generated/`
2. **Limited Scope**: Only 4 files auto-updated (out of 172+ markdown files)
3. **No API Docs**: OpenAPI spec not auto-generated
4. **No Code Metrics**: radon, lizard, complexity not tracked
5. **No User Guides**: No automatic generation for specific audiences
6. **Manual Maintenance**: Most docs require manual updates
7. **No Polish Content**: JST (local government) docs only in README mentions
8. **Unclear Structure**: Users getting lost (per user feedback)

## Goals

1. **Full Automation**: All dynamic content auto-generated
2. **User-Specific Views**: Tailored docs for 4 audiences
3. **Single Source of Truth**: Eliminate duplication
4. **Workflow Integration**: Auto-update on every relevant change
5. **Self-Documenting**: Clear guides on how to add new docs
6. **Real-Time Metrics**: Live badges, dashboards, API health

## Target Audiences

### 1. Developers
**Needs:** API docs, code examples, architecture, testing guides
**Files:** REST API, SDK reference, integration guides

### 2. Administracja (Administration)
**Needs:** Compliance, GDPR/RODO, deployment, Polish language, security policies
**Files:** Compliance guides, ISO 42001, security policies, deployment guides
**Note:** Includes government agencies (JST - Jednostki Samorządu Terytorialnego)

### 3. Industry (Enterprises)
**Needs:** ROI, scalability, security, production deployment
**Files:** Enterprise guides, Kubernetes, cost optimization

### 4. Usługi (Professional Services)
**Needs:** Knowledge isolation, multi-tenancy, audit trails, compliance reporting
**Files:** Legal/audit guides, tenant isolation, data governance, compliance reports
**Note:** Lawyers, auditors, accountants - requires strict data isolation

### 5. Researchers
**Needs:** Mathematical foundations, benchmarks, reproducibility
**Files:** Mathematical formalization, evaluation suite, papers

## Iteration Plan

### Iteration 1: Core Documentation Audit (This File + Inventory)
**Duration:** 1 session
**Status:** ✅ COMPLETED
**Deliverables:**
- [x] Complete documentation inventory (all 172 files)
- [x] Identify auto-updatable content
- [x] Map file relationships and dependencies
- [x] Create DOCUMENTATION_INVENTORY.md

### Iteration 2: Enhanced Auto-Documentation System
**Duration:** 1 session
**Status:** ✅ COMPLETED
**Deliverables:**
- [x] Extend docs_automator.py with:
  - OpenAPI export (from FastAPI app)
  - Code metrics (radon, lizard)
  - API endpoint list
  - Module index
  - Test coverage per module
- [x] Consolidate duplicate files (root vs docs/.auto-generated/)
- [x] Add docs/.auto-generated/api/, docs/.auto-generated/metrics/
- [x] Update GitHub Actions workflow

### Iteration 3: Workflow Integration & Self-Documentation
**Duration:** 1 session
**Status:** ✅ COMPLETED
**Deliverables:**
- [x] Pre-commit hook for API docs (`scripts/generate_api_docs.py` + `.pre-commit-config.yaml`)
- [x] Weekly cron for code metrics (`.github/workflows/code-metrics.yml`)
- [x] Add CONTRIBUTING_DOCS.md guide (already exists)
- [x] Create documentation templates (`docs/templates/` - guide, reference, architecture)
- [x] Add doc validation (`scripts/validate_docs.py` + `make docs-validate`)
- [x] Update .cursorrules with doc guidelines (already updated in Iteration 2)

### Iteration 4: User-Specific Documentation Portals
**Duration:** 1 session
**Deliverables:**
- [ ] Generate 5 user-specific landing pages:
  - docs/guides/developers/INDEX.md
  - docs/guides/administracja/INDEX.md (with Polish content for government)
  - docs/guides/enterprise/INDEX.md
  - docs/guides/uslugi/INDEX.md (professional services: lawyers, auditors, accountants)
  - docs/guides/researchers/INDEX.md
- [ ] Add audience-specific quick starts
- [ ] Create role-based navigation paths
- [ ] Add Polish translations for Administracja and Usługi docs
- [ ] Add knowledge isolation guides for professional services

## File Structure (Target)

```
docs/
├── .auto-generated/           # All auto-generated content
│   ├── status/
│   │   ├── STATUS.md         # Live metrics
│   │   ├── TESTING_STATUS.md
│   │   └── CI_STATUS.md
│   ├── reports/
│   │   ├── CHANGELOG.md      # Git history
│   │   ├── CODE_METRICS.md   # radon, lizard
│   │   └── TODO.md           # Extracted TODOs
│   ├── api/
│   │   ├── openapi.json      # FastAPI export
│   │   ├── endpoints.md      # Endpoint list
│   │   └── sdk_reference.md  # SDK docs
│   └── metrics/
│       ├── coverage.md       # Per-module coverage
│       ├── complexity.md     # Cyclomatic complexity
│       └── dependencies.md   # Dependency graph
│
├── guides/                    # User-facing guides
│   ├── developers/
│   │   ├── INDEX.md          # Developer portal
│   │   ├── getting-started/
│   │   ├── api/
│   │   └── testing/
│   ├── administracja/         # Administration (government, JST)
│   │   ├── INDEX.md          # Administration portal (Polish)
│   │   ├── compliance/
│   │   ├── deployment/
│   │   └── gdpr-rodo/
│   ├── enterprise/
│   │   ├── INDEX.md          # Enterprise portal
│   │   ├── production/
│   │   ├── kubernetes/
│   │   └── security/
│   ├── uslugi/                # Professional Services
│   │   ├── INDEX.md          # Services portal (Polish)
│   │   ├── tenant-isolation/
│   │   ├── audit-trails/
│   │   └── data-governance/
│   └── researchers/
│       ├── INDEX.md          # Research portal
│       ├── mathematical/
│       ├── benchmarks/
│       └── publications/
│
├── reference/                 # Technical reference
│   ├── api/
│   ├── architecture/
│   ├── deployment/
│   └── services/
│
├── compliance/                # Compliance documentation
│   └── [existing structure]
│
└── project-design/            # Development planning
    ├── active/
    ├── completed/
    └── research/
```

## Auto-Update Rules

| File Pattern | Trigger | Frequency | Source |
|-------------|---------|-----------|--------|
| `status/*.md` | On push | Every commit | Git, pytest, coverage |
| `reports/CHANGELOG.md` | On push | Every commit | Git log |
| `reports/TODO.md` | On push | Every commit | Code scan (TODO/FIXME) |
| `api/*.json` | On code change | Pre-commit | FastAPI app |
| `api/*.md` | On code change | Pre-commit | OpenAPI parser |
| `metrics/*.md` | Scheduled | Weekly | radon, lizard, pytest |

## Implementation Strategy

### Phase 1: Audit (Iteration 1)
1. Scan all docs/ and generate DOCUMENTATION_INVENTORY.md
2. Identify which files can be auto-generated
3. Mark manual vs auto-generated sections

### Phase 2: Core Automation (Iteration 2)
1. Extend docs_automator.py with new generators
2. Consolidate file locations
3. Update GitHub Actions workflow
4. Test locally before committing

### Phase 3: Workflow Integration (Iteration 3)
1. Add pre-commit hooks
2. Add cron jobs for weekly metrics
3. Create CONTRIBUTING_DOCS.md
4. Add doc validation CI check

### Phase 4: User Portals (Iteration 4)
1. Generate 5 INDEX.md files (one per audience)
2. Add Polish translations for Administracja and Usługi
3. Create role-based quick starts (focus on knowledge isolation for Usługi)
4. Update main README with audience paths

## Success Metrics

- [ ] 100% of dynamic content auto-generated
- [ ] Zero duplicate files (single source of truth)
- [ ] Documentation updates require zero manual intervention
- [ ] 5 user-specific landing pages with clear paths
- [ ] Polish content for Administracja and Usługi audiences
- [ ] Knowledge isolation guides for professional services
- [ ] CONTRIBUTING_DOCS.md guide in place
- [ ] All auto-gen scripts documented
- [ ] CI validates docs on every PR

## Maintenance

### Adding New Auto-Generated Content
1. Create generator function in `scripts/docs_generators/*.py`
2. Add to `scripts/docs_automator.py` main loop
3. Add file pattern to `.github/workflows/docs.yml`
4. Update `docs/.auto-generated/README.md`
5. Test locally: `python scripts/docs_automator.py`

### Adding Manual Documentation
1. Create file in appropriate `docs/` subdirectory
2. Follow template in `docs/templates/`
3. Add to relevant INDEX.md file
4. Run doc validator: `make docs-validate`

## Timeline

- **Iteration 1**: Session 1 (this session)
- **Iteration 2**: Session 2 (next work session)
- **Iteration 3**: Session 3
- **Iteration 4**: Session 4
- **Total**: ~4 work sessions

## Related Documents

- `scripts/docs_automator.py` - Current automation script
- `.github/workflows/docs.yml` - GitHub Actions workflow
- `docs/.auto-generated/README.md` - Auto-gen docs index
- `CONTRIBUTING.md` - Contribution guidelines

## Notes

- Must maintain English as primary language (per requirement)
- Polish content only for JST-specific guides
- Preserve all existing documentation (no deletions)
- Iterative approach allows testing at each stage
- Each iteration is independently valuable

---

**Status:** 🟢 Active
**Next Action:** Complete documentation inventory (DOCUMENTATION_INVENTORY.md)
