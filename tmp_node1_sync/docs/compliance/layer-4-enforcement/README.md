# Layer 4: Policy Enforcement

This layer provides runtime enforcement mechanisms that ensure compliance policies are actually followed during system operation.

## 🎯 Purpose

**Runtime enforcement layer** that intercepts requests and applies policy packs from Layer 3.

**Key principle:** Policies aren't just documentation - they're executable rules that the system enforces automatically.

## 🏗️ Architecture

```
User Request
    ↓
[API Endpoint]
    ↓
[Policy Engine] ← Loads Layer 3 policy packs
    ↓
[Enforcement Components]
    ├── Guardrails (input/output validation)
    ├── Cost Controllers (budget enforcement)
    └── Risk Controllers (risk-based throttling)
    ↓
[Core Services]
    ↓
[Audit Logging]
    ↓
Response
```

## 📂 Components

### 1. Guardrails
**Location:** `guardrails/`

Input and output validators that enforce policy constraints.

**Types:**
- **Input Guardrails**: Validate incoming data
  - PII detection and scrubbing
  - Content filtering (toxic, inappropriate)
  - Schema validation
  - Rate limiting per tenant

- **Output Guardrails**: Validate outgoing data
  - PII leakage prevention
  - Sensitive data filtering
  - Response formatting compliance
  - Disclosure controls

**Example (HIPAA PHI Detection):**
```python
class PHIDetectionGuardrail(Guardrail):
    async def validate(self, content: str) -> ValidationResult:
        # Detect PHI patterns
        phi_patterns = {
            "ssn": r"\b\d{3}-\d{2}-\d{4}\b",
            "mrn": r"\bMRN[:-]?\s*\d+\b",
        }

        violations = []
        for pattern_name, regex in phi_patterns.items():
            if re.search(regex, content):
                violations.append(f"Detected {pattern_name}")

        if violations:
            return ValidationResult(
                valid=False,
                violations=violations,
                action="scrub"  # or "reject" depending on policy
            )

        return ValidationResult(valid=True)
```

---

### 2. Cost Controllers
**Location:** `cost-controllers/`

Budget and spend limits to prevent runaway costs.

**Features:**
- **Per-tenant budgets**: Daily/monthly spending caps
- **Per-operation limits**: Max cost per LLM call
- **Budget alerts**: Notifications at thresholds (50%, 80%, 95%)
- **Automatic throttling**: Slow down when approaching limits

**Example:**
```python
class TenantBudgetController(CostController):
    async def check_budget(self, tenant_id: str, estimated_cost: float) -> BudgetResult:
        # Get current spend
        current_spend = await cost_repo.get_total_cost(tenant_id, period="month")

        # Check against limit
        budget_limit = await get_tenant_budget(tenant_id)

        if current_spend + estimated_cost > budget_limit:
            return BudgetResult(
                allowed=False,
                reason=f"Would exceed monthly budget: ${current_spend + estimated_cost:.2f} > ${budget_limit:.2f}",
                action="reject"
            )

        return BudgetResult(allowed=True)
```

**Integration:**
```python
# Before LLM call
budget_check = await cost_controller.check_budget(tenant_id, estimated_cost)
if not budget_check.allowed:
    raise BudgetExceededError(budget_check.reason)

# Proceed with LLM call
```

---

### 3. Risk Controllers
**Location:** `risk-controllers/`

Risk-based throttling and decision routing.

**Features:**
- **Risk classification**: Low / Medium / High / Critical
- **Auto-approval**: Low-risk operations proceed automatically
- **Human-in-the-loop**: High-risk requires human approval
- **Multi-approver**: Critical requires 2+ approvals

**Risk levels:**
| Risk Level | Description | Action |
|------------|-------------|--------|
| **Low** | Routine operations | Auto-approve |
| **Medium** | Moderate impact | Log + proceed |
| **High** | Significant impact | Require 1 approval (24h timeout) |
| **Critical** | Major consequences | Require 2 approvals (72h timeout) |

**Example:**
```python
class RiskBasedApprovalController(RiskController):
    async def check_approval(self, operation: str, risk_level: RiskLevel) -> ApprovalResult:
        if risk_level == RiskLevel.LOW:
            return ApprovalResult(approved=True, reason="Low risk auto-approved")

        if risk_level == RiskLevel.HIGH:
            # Check if approval exists
            approval = await approval_service.get_pending_approval(operation)
            if approval and approval.status == "approved":
                return ApprovalResult(approved=True)

            # Create approval request
            await approval_service.request_approval(
                operation=operation,
                risk_level=risk_level,
                required_approvers=1,
                timeout_hours=24
            )

            return ApprovalResult(
                approved=False,
                reason="Awaiting human approval",
                action="defer"
            )

        # ... similar for CRITICAL
```

## 🔌 Policy Engine Integration

The Policy Engine (`apps/memory_api/services/policy_engine.py`) coordinates all enforcement components.

### Initialization

```python
class PolicyEngine:
    def __init__(self):
        self.modules = []
        self.guardrails = []
        self.cost_controllers = []
        self.risk_controllers = []

    def load_modules(self, module_list: List[str]):
        """Load policy packs from Layer 3."""
        for module_name in module_list:
            module = PolicyPackLoader.load(module_name)
            self.modules.append(module)

            # Register enforcement components
            self.guardrails.extend(module.guardrails)
            self.cost_controllers.extend(module.cost_controllers)
            self.risk_controllers.extend(module.risk_controllers)
```

### Request Interception

```python
@router.post("/v1/memory/store")
async def store_memory(request: MemoryStoreRequest):
    # 1. Apply guardrails
    validation = await policy_engine.validate_input(request.content)
    if not validation.valid:
        raise ValidationError(validation.violations)

    # 2. Check cost budget
    estimated_cost = cost_controller.estimate(request.content)
    budget_check = await policy_engine.check_budget(request.tenant_id, estimated_cost)
    if not budget_check.allowed:
        raise BudgetExceededError(budget_check.reason)

    # 3. Check risk approval
    risk_level = risk_controller.classify(request.operation)
    approval_check = await policy_engine.check_approval(request.operation, risk_level)
    if not approval_check.approved:
        # Defer to approval queue
        return {"status": "pending_approval", "approval_id": approval_check.approval_id}

    # 4. Proceed with operation
    memory_id = await memory_service.store(request.content, request.metadata)

    # 5. Audit logging (automatic)
    await policy_engine.log_operation("memory.store", memory_id, request.tenant_id)

    return {"memory_id": memory_id}
```

## 🧪 Testing Enforcement

```bash
# Test guardrails
pytest apps/memory_api/tests/test_guardrails.py

# Test cost controllers
pytest apps/memory_api/tests/test_cost_controller.py

# Test risk controllers
pytest apps/memory_api/tests/test_risk_controller.py

# Test full policy engine
pytest apps/memory_api/tests/test_policy_engine.py
```

## 📊 Monitoring & Observability

Enforcement actions are logged and monitored:

**Metrics:**
- `guardrail_violations_total` - Count of policy violations
- `cost_budget_exceeded_total` - Budget limit hits
- `risk_approval_pending_total` - Operations awaiting approval
- `policy_enforcement_latency_ms` - Overhead of enforcement

**Dashboards:**
- Guardrail violation trends
- Budget utilization per tenant
- Approval queue status
- Policy engine performance

**Alerts:**
- High guardrail violation rate
- Budget approaching limit (80%, 95%)
- Approval backlog growing
- Policy engine errors

## 🔐 Fail-Safe Mechanisms

What happens if enforcement fails?

### Circuit Breaker Pattern

```python
class PolicyEngineCircuitBreaker:
    def __init__(self):
        self.failure_threshold = 5
        self.timeout = 60  # seconds
        self.state = "CLOSED"  # CLOSED | OPEN | HALF_OPEN

    async def call(self, operation):
        if self.state == "OPEN":
            # Fail-safe: Allow operation but log warning
            logger.warning("Policy engine circuit OPEN, allowing operation")
            return {"allowed": True, "warning": "Circuit breaker active"}

        try:
            result = await operation()
            self.reset_failures()
            return result
        except Exception as e:
            self.record_failure()
            if self.failures >= self.failure_threshold:
                self.state = "OPEN"
            raise
```

**Fail-safe modes:**
- **Enforcement fails**: Log error, allow operation (with warning)
- **Database down**: Cache recent decisions, proceed
- **High latency**: Timeout and allow (for non-critical policies)

## 📚 Related Documentation

- **Layer 1 (Foundation)**: `docs/compliance/layer-1-foundation/`
- **Layer 2 (Mapping)**: `docs/compliance/layer-2-mapping/`
- **Layer 3 (Policy Packs)**: `docs/compliance/layer-3-modules/`
- **Policy Engine Code**: `apps/memory_api/services/policy_engine.py`
- **Cost Controller**: `apps/memory_api/services/cost_controller_v2.py`
- **Human Approval**: `apps/memory_api/services/human_approval_service.py`

## 🚀 Extending Enforcement

To add a new enforcement component:

1. Create class inheriting from base:
   - `Guardrail` for input/output validation
   - `CostController` for budget enforcement
   - `RiskController` for risk-based routing

2. Implement required methods:
   ```python
   class MyCustomGuardrail(Guardrail):
       async def validate(self, content: str) -> ValidationResult:
           # Your validation logic
           pass
   ```

3. Register with policy engine:
   ```python
   policy_engine.register_guardrail(MyCustomGuardrail())
   ```

4. Add tests:
   ```python
   def test_my_custom_guardrail():
       guardrail = MyCustomGuardrail()
       result = await guardrail.validate("test content")
       assert result.valid
   ```

---

**Status:** ✅ Core framework implemented
**Last Updated:** 2025-12-03
**Next Steps:** Expand guardrail library for Layer 3 policy packs
