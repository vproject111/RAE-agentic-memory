# RAE Documentation Overhaul v2.0 - Detailed Implementation Plan

**Status:** Ready for Implementation
**Created:** 2025-12-08
**Source:** docs/RAE_Documentation_Overhaul_Plan_v2-0.md
**Model:** Claude Opus 4.5

---

## Executive Summary

This plan provides a pragmatic, iterative roadmap for implementing the RAE Documentation Overhaul v2.0 as specified in `docs/RAE_Documentation_Overhaul_Plan_v2-0.md`.

### Current State Analysis

**What Exists:**
- 225 markdown files in docs/ (8 auto-generated, 217 manual)
- Functional `docs_automator.py` updating 4-8 files automatically
- Modular generator system in `scripts/docs_generators/`
- CI/CD via `.github/workflows/docs.yml` (triggers on CI success)
- Validation script: `scripts/validate_docs.py`
- Templates directory: `docs/templates/` with 3 templates
- Contributing guide: `docs/CONTRIBUTING_DOCS.md`
- Previous reorganization plan exists: `docs/project-design/DOCS-REORGANIZATION-PLAN.md`
- Documentation Executive Summary tracks iterations 1-3 as completed

**What Is Missing (from v2.0 Plan):**
- Doc Fragments system (`<!-- RAE_DOC_FRAGMENT:name -->`) - only mentioned in plan, not implemented
- `autodoc_checker.py` - AI worker for consistency checks
- `docs/autodoc/` directory with reference_schema.json and doc_fragments/
- STYLE_GUIDE.md with formal style definitions
- Proposed architecture structure:
  - `/docs/architecture/` (currently empty references exist)
  - `/docs/api/` (exists in `.auto-generated/api/`)
  - `/docs/design/` (partially in `project-design/`)
- Intelligent cross-linking validation in CI
- Code-to-docs consistency checking pipeline

**Key Gaps:**
1. No fragment synchronization system
2. No AI-powered consistency checker
3. No STYLE_GUIDE.md
4. Structure differs from proposed architecture
5. No zero-drift docs policy enforcement

---

## Iteration 1: Foundation & Quick Wins (Week 1-2)

### Goals
Establish the foundation for automated documentation with minimal disruption to existing workflows.

### Deliverables

#### 1.1 Create STYLE_GUIDE.md
**Location:** `docs/STYLE_GUIDE.md`

**Acceptance Criteria:**
- [ ] Document naming conventions (file names, anchors)
- [ ] Define icon usage (existing icons from README.md)
- [ ] Specify section templates (Overview -> Architecture -> API -> Examples -> Edge Cases)
- [ ] Define linking rules (relative paths, anchor requirements)
- [ ] Include code block language requirements
- [ ] Define Polish language usage scope (JST-specific only)

**Effort:** 0.5 person-days

#### 1.2 Create Doc Fragments Directory Structure
**Location:** `docs/autodoc/`

**Files to Create:**
```
docs/autodoc/
├── reference_schema.json     # JSON schema for doc validation
├── doc_fragments/
│   ├── README.md             # How fragments work
│   ├── memory_layers_overview.md
│   ├── math_layers_summary.md
│   ├── hybrid_search_core.md
│   └── architecture_diagram.md
└── fragment_mapping.yaml     # Maps fragments to documents
```

**Acceptance Criteria:**
- [ ] Directory structure exists
- [ ] README.md explains fragment concept
- [ ] At least 4 core fragments extracted from existing docs
- [ ] fragment_mapping.yaml lists all fragment locations

**Effort:** 1 person-day

#### 1.3 Extract Initial Fragments from Existing Documentation
**Source Files to Extract From:**
- `README.md` (lines 78-163 - architecture descriptions)
- `docs/reference/README.md`

**Fragment Candidates:**
1. `memory_layers_overview.md` - 4-layer memory system description
2. `math_layers_summary.md` - 3-tier mathematical foundation
3. `hybrid_search_core.md` - Hybrid search engine description
4. `architecture_diagram.md` - ASCII architecture diagram

**Acceptance Criteria:**
- [ ] Fragments are standalone and reusable
- [ ] Each fragment has clear boundary markers
- [ ] Original documents reference fragments via markers

**Effort:** 1 person-day

#### 1.4 Add CI Docs Consistency Check (Basic)
**File to Modify:** `.github/workflows/ci.yml`

**Tasks:**
- [ ] Add new job: `docs-consistency-check`
- [ ] Run `python scripts/validate_docs.py` as part of CI
- [ ] Fail build on broken links (errors only, not warnings)

**Acceptance Criteria:**
- [ ] CI job runs on every PR
- [ ] Broken internal links cause build failure
- [ ] Warnings logged but don't block

**Effort:** 0.5 person-days

### Iteration 1 Summary

| Task | Effort | Dependencies | Risk |
|------|--------|--------------|------|
| STYLE_GUIDE.md | 0.5 days | None | Low |
| Doc Fragments Structure | 1 day | None | Low |
| Extract Initial Fragments | 1 day | 1.2 | Medium (content selection) |
| CI Docs Check | 0.5 days | None | Low |
| **Total** | **3 person-days** | | |

**Risk Mitigation:**
- Fragment extraction may reveal inconsistencies - document but don't block
- Keep fragments focused and small initially
- Use existing `validate_docs.py` as foundation

---

## Iteration 2: Core Automation (Week 2-4)

### Goals
Build the core Doc Fragments system with automatic synchronization and basic AI-assisted checking.

### Deliverables

#### 2.1 Implement Fragment Injection System
**New File:** `scripts/docs_generators/fragment_injector.py`

**Functionality:**
```python
# Scan for markers like: <!-- RAE_DOC_FRAGMENT:math_layers_summary -->
# Replace with content from docs/autodoc/doc_fragments/math_layers_summary.md
# Preserve markers for re-injection on updates
```

**Acceptance Criteria:**
- [ ] Script finds all `<!-- RAE_DOC_FRAGMENT:name -->` markers
- [ ] Injects corresponding fragment content
- [ ] Preserves end markers for boundaries
- [ ] Reports fragments not found
- [ ] Logs all injections

**Effort:** 2 person-days

#### 2.2 Create autodoc_checker.py (Non-AI Version First)
**New File:** `docs/autodoc/autodoc_checker.py`

**Phase 1 Features (Non-AI):**
- [ ] Compare API function signatures in code vs documentation
- [ ] Detect duplicate content across documents
- [ ] Validate all internal links resolve
- [ ] Check fragment consistency (same content in all locations)
- [ ] Generate report in markdown format

**Acceptance Criteria:**
- [ ] Runs without LLM dependency
- [ ] Outputs `docs/autodoc/consistency_report.md`
- [ ] Exit code indicates pass/fail
- [ ] Can be run locally: `python docs/autodoc/autodoc_checker.py`

**Effort:** 2 person-days

#### 2.3 Integrate Fragment System with docs_automator.py
**File to Modify:** `scripts/docs_automator.py`

**Changes:**
```python
from docs_generators.fragment_injector import inject_fragments

def main():
    # ... existing generators ...
    inject_fragments()  # Add fragment injection step
```

**Acceptance Criteria:**
- [ ] Fragment injection runs as part of automation
- [ ] Works with existing CI workflow
- [ ] Logs fragment updates

**Effort:** 0.5 person-days

#### 2.4 Update CI to Run Consistency Checker
**File to Modify:** `.github/workflows/ci.yml`

**New Step:**
```yaml
- name: Run Documentation Consistency Check
  run: python docs/autodoc/autodoc_checker.py
  continue-on-error: false  # Block merge on inconsistencies
```

**Acceptance Criteria:**
- [ ] autodoc_checker.py runs in CI
- [ ] Build fails on critical inconsistencies
- [ ] Report uploaded as artifact

**Effort:** 0.5 person-days

#### 2.5 Restructure Documentation Directories (Partial)
Based on proposed structure, create missing directories:

**New Directories:**
```
docs/
├── architecture/     # Move relevant files from reference/architecture
│   ├── MEMORY_LAYERS.md
│   ├── MATH_LAYERS.md
│   └── HYBRID_SEARCH.md
├── design/           # Rename from project-design principles
│   ├── RAE_PRINCIPLES.md
│   ├── ZERO_WARNING_POLICY.md
│   └── MEMORY_CONTRACTS.md
```

**Note:** Keep existing structure working - add symlinks or redirects initially.

**Acceptance Criteria:**
- [ ] New directories exist
- [ ] Key files moved or linked
- [ ] No broken links in existing docs
- [ ] README.md updated with new paths

**Effort:** 1.5 person-days

### Iteration 2 Summary

| Task | Effort | Dependencies | Risk |
|------|--------|--------------|------|
| Fragment Injector | 2 days | Iter 1.2, 1.3 | Medium (edge cases) |
| autodoc_checker.py | 2 days | None | Low |
| Integrate with automator | 0.5 days | 2.1 | Low |
| CI Integration | 0.5 days | 2.2 | Low |
| Directory Restructure | 1.5 days | None | Medium (link breakage) |
| **Total** | **6.5 person-days** | | |

**Risk Mitigation:**
- Fragment injector: Start with simple regex, add complexity if needed
- Directory restructure: Use symlinks first, migrate gradually
- Test all changes locally before CI integration

---

## Iteration 3: AI-Powered Consistency & Intelligent Linking (Week 4-6)

### Goals
Add AI-powered consistency checking and implement intelligent cross-linking between documents.

### Deliverables

#### 3.1 Add AI Capabilities to autodoc_checker.py
**File to Modify:** `docs/autodoc/autodoc_checker.py`

**New Features:**
- [ ] LLM comparison of API descriptions vs implementation
- [ ] Semantic similarity check for duplicate detection
- [ ] Automatic fix suggestions (not auto-apply)
- [ ] Support for local LLMs (Ollama) for privacy

**Acceptance Criteria:**
- [ ] Works with OpenAI, Anthropic, or Ollama
- [ ] Generates PR with suggested fixes
- [ ] Can run in offline mode (no-LLM fallback)
- [ ] Cost-aware (uses cheapest model for batch operations)

**Effort:** 3 person-days

#### 3.2 Implement Intelligent Cross-Linking Validator
**New File:** `scripts/docs_generators/cross_link_analyzer.py`

**Functionality:**
- [ ] Build document relationship graph
- [ ] Identify missing links (related topics not connected)
- [ ] Suggest new links based on content analysis
- [ ] Validate all anchors exist

**Acceptance Criteria:**
- [ ] Generates `docs/autodoc/link_suggestions.md`
- [ ] Reports orphan documents (no incoming links)
- [ ] Validates anchor references

**Effort:** 2 person-days

#### 3.3 Create Glossary Auto-Generator
**New File:** `scripts/docs_generators/glossary_generator.py`

**Output:** `docs/GLOSSARY.md`

**Functionality:**
- [ ] Extract technical terms from all docs
- [ ] Generate alphabetized glossary
- [ ] Link each term to first occurrence

**Acceptance Criteria:**
- [ ] Auto-generated on docs.yml trigger
- [ ] Contains all RAE-specific terms
- [ ] Hyperlinked to source documents

**Effort:** 1.5 person-days

#### 3.4 Implement Code-to-Docs Pipeline
**New Workflow:** `.github/workflows/docs-sync.yml`

**Pipeline:**
```
Code Change (apps/memory_api/**)
    → AI Autodoc Worker analyzes change
    → Updates relevant doc fragments
    → Creates PR "docs sync"
    → Reviewer approves
    → Auto-merge to develop
```

**Acceptance Criteria:**
- [ ] Triggers only on code changes (not docs changes)
- [ ] Creates separate PR for doc updates
- [ ] Includes diff of doc changes
- [ ] Can be disabled via commit message `[skip docs]`

**Effort:** 2.5 person-days

### Iteration 3 Summary

| Task | Effort | Dependencies | Risk |
|------|--------|--------------|------|
| AI autodoc_checker | 3 days | Iter 2.2 | Medium (LLM reliability) |
| Cross-link Analyzer | 2 days | Iter 2.5 | Low |
| Glossary Generator | 1.5 days | None | Low |
| Code-to-Docs Pipeline | 2.5 days | Iter 2.3, 3.1 | High (complexity) |
| **Total** | **9 person-days** | | |

**Risk Mitigation:**
- AI features: Always have non-AI fallback
- Code-to-docs pipeline: Start with notifications, add auto-PR later
- Cost control: Set LLM budget limits in config

---

## Iteration 4: Polish & Advanced Features (Week 6-8)

### Goals
Complete the documentation overhaul with advanced features and polish.

### Deliverables

#### 4.1 Complete User-Specific Documentation Portals
Based on existing `docs/project-design/active/DOCUMENTATION_AUTOMATION_PLAN.md` Iteration 4:

**Files to Create:**
```
docs/guides/
├── developers/INDEX.md      # Developer portal
├── administracja/INDEX.md   # Administration portal (Polish)
├── enterprise/INDEX.md      # Enterprise portal
├── uslugi/INDEX.md          # Professional services (Polish)
└── researchers/INDEX.md     # Research portal
```

**Acceptance Criteria:**
- [ ] Each INDEX.md provides complete navigation for audience
- [ ] Polish content for JST sections
- [ ] Quick-start paths for each role
- [ ] Links to relevant sections

**Effort:** 2 person-days

#### 4.2 Complete Directory Structure Migration
**Complete proposed structure from v2.0 plan:**

```
docs/
├── architecture/
│   ├── MEMORY_LAYERS.md
│   ├── MATH_LAYERS.md
│   ├── HYBRID_SEARCH.md
│   ├── ORCHESTRATION.md
│   ├── DEPLOYMENT_LOCAL_CLUSTER.md
│   ├── SECURITY_ISO42001.md
│   └── OPEN_TELEMETRY.md
├── api/
│   ├── MEMORY_API.md
│   ├── SEARCH_API.md
│   ├── REFLECTION_ENGINE_API.md
│   └── LLM_ORCHESTRATOR_API.md
├── guides/
│   ├── GETTING_STARTED.md
│   ├── BENCHMARKING_GUIDE.md
│   ├── RAE_FOR_RESEARCH.md
│   ├── RAE_FOR_ENTERPRISE.md
│   └── RAE_FOR_LOCAL_AI.md
├── design/
│   ├── RAE_PRINCIPLES.md
│   ├── ZERO_WARNING_POLICY.md
│   └── MEMORY_CONTRACTS.md
└── autodoc/
    ├── reference_schema.json
    └── doc_fragments/
```

**Acceptance Criteria:**
- [ ] All files in final locations
- [ ] Redirects/symlinks for old paths
- [ ] All internal links updated
- [ ] validate_docs.py passes

**Effort:** 2 person-days

#### 4.3 Create reference_schema.json for Doc Validation
**New File:** `docs/autodoc/reference_schema.json`

**Schema Contents:**
- Required sections per document type
- Metadata requirements (Last Updated, Author)
- Cross-reference validation rules
- Fragment marker format

**Acceptance Criteria:**
- [ ] JSON Schema validates doc structure
- [ ] Integrated with validate_docs.py
- [ ] Documents failing schema fail CI

**Effort:** 1 person-day

#### 4.4 Implement Fragment Version Control
**Enhancement to fragment system:**

- [ ] Track fragment versions
- [ ] Detect stale fragments (not updated with source)
- [ ] Generate diff reports for fragment changes
- [ ] Support fragment branching (language variants)

**Acceptance Criteria:**
- [ ] fragment_versions.yaml tracks all versions
- [ ] CI warns on stale fragments
- [ ] Polish variants supported

**Effort:** 1.5 person-days

#### 4.5 Final README Update as Navigation Hub
**File:** `README.md`

**Updates:**
- [ ] Clear "Start Here" section
- [ ] Links to 5 audience portals
- [ ] Updated architecture diagram
- [ ] Glossary link
- [ ] Documentation status badge

**Acceptance Criteria:**
- [ ] No dead links
- [ ] All 5 core features prominently linked
- [ ] Clear paths for each audience

**Effort:** 0.5 person-days

### Iteration 4 Summary

| Task | Effort | Dependencies | Risk |
|------|--------|--------------|------|
| User Portals | 2 days | Iter 2.5 | Low |
| Directory Migration | 2 days | Iter 2.5 | Medium (link breakage) |
| reference_schema.json | 1 day | Iter 2.2 | Low |
| Fragment Versioning | 1.5 days | Iter 2.1 | Medium |
| README Update | 0.5 days | All | Low |
| **Total** | **7 person-days** | | |

**Risk Mitigation:**
- Migration: Keep old paths working via redirects
- Run full link validation before merge
- Test portal navigation manually

---

## Success Metrics

### Documentation Quality
- [ ] 100% internal links valid (via CI)
- [ ] All documents follow STYLE_GUIDE.md
- [ ] All dynamic content uses fragments
- [ ] Zero duplicated content (except fragments)

### Automation
- [ ] Code changes trigger doc sync PRs
- [ ] Fragment updates propagate automatically
- [ ] CI blocks on doc inconsistencies
- [ ] Weekly consistency reports generated

### User Experience
- [ ] 5 audience-specific portals exist
- [ ] README provides clear navigation
- [ ] Glossary with 50+ terms
- [ ] Polish content for JST sections

### Maintenance
- [ ] autodoc_checker.py catches 90%+ issues
- [ ] CONTRIBUTING_DOCS.md enables self-service
- [ ] New docs follow templates
- [ ] Metrics tracked in `.auto-generated/metrics/`

---

## Resource Requirements

### Team Size: 1-3 Engineers

**Optimal Configuration:**
- 1 engineer: 25.5 person-days over 6-8 weeks
- 2 engineers: 13 calendar days (parallelizable tasks)
- 3 engineers: 9 calendar days (maximum parallelism)

### Technical Requirements
- Python 3.11+
- Access to LLM API (OpenAI, Anthropic, or Ollama)
- GitHub Actions with secrets configured
- Local RAE development environment

### Budget Considerations
- LLM costs for AI checker: ~$5-20/month (using cheap models)
- Can run fully local with Ollama (zero cost)
- No additional infrastructure required

---

## Risk Assessment & Mitigation

### High Risk
| Risk | Impact | Probability | Mitigation |
|------|--------|-------------|------------|
| Link breakage during migration | High | Medium | Symlinks + redirects, gradual migration |
| AI checker unreliable | Medium | Medium | Always have non-AI fallback |
| Scope creep | Medium | High | Stick to iteration deliverables |

### Medium Risk
| Risk | Impact | Probability | Mitigation |
|------|--------|-------------|------------|
| Fragment complexity | Medium | Medium | Start simple, iterate |
| CI time increase | Low | High | Parallelize, cache dependencies |
| Team availability | High | Low | Prioritize iterations, defer if needed |

### Low Risk
| Risk | Impact | Probability | Mitigation |
|------|--------|-------------|------------|
| Template adoption | Low | Low | Clear examples, enforcement via PR reviews |
| Glossary incompleteness | Low | Medium | Iterative additions |

---

## Timeline Summary

| Iteration | Duration | Person-Days | Cumulative |
|-----------|----------|-------------|------------|
| 1: Foundation | Week 1-2 | 3 days | 3 days |
| 2: Core Automation | Week 2-4 | 6.5 days | 9.5 days |
| 3: AI & Linking | Week 4-6 | 9 days | 18.5 days |
| 4: Polish | Week 6-8 | 7 days | 25.5 days |

**Total: 25.5 person-days over 6-8 weeks**

---

## Critical Files for Implementation

### Existing Files to Modify
- `scripts/docs_automator.py` - Core automation script to extend with fragment injection
- `.github/workflows/docs.yml` - CI workflow to add consistency checks
- `scripts/validate_docs.py` - Existing validator to integrate with new checks
- `docs/CONTRIBUTING_DOCS.md` - Self-service guide to update with fragment usage
- `docs/project-design/active/DOCUMENTATION_AUTOMATION_PLAN.md` - Existing plan to align with

### New Files to Create
- `docs/STYLE_GUIDE.md` - Documentation style guidelines
- `docs/autodoc/autodoc_checker.py` - Consistency checker
- `scripts/docs_generators/fragment_injector.py` - Fragment injection system
- `scripts/docs_generators/cross_link_analyzer.py` - Link validation
- `scripts/docs_generators/glossary_generator.py` - Auto-glossary
- `.github/workflows/docs-sync.yml` - Code-to-docs pipeline
- `docs/autodoc/reference_schema.json` - Validation schema
- `docs/GLOSSARY.md` - Auto-generated glossary

---

## Next Steps

1. **Review this plan** with team and stakeholders
2. **Start Iteration 1** with STYLE_GUIDE.md and fragment structure
3. **Set up tracking** in TODO.md or project management tool
4. **Assign owner** for each iteration
5. **Schedule reviews** at end of each iteration

---

**Generated by:** Claude Opus 4.5
**Date:** 2025-12-08
**Source Plan:** docs/RAE_Documentation_Overhaul_Plan_v2-0.md
