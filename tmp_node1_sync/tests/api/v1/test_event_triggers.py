from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch
from uuid import UUID, uuid4

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from apps.memory_api.main import app
from apps.memory_api.models.event_models import (
    ActionConfig,
    ActionType,
    CreateTriggerRequest,
    CreateWorkflowRequest,
    EmitEventRequest,
    EventType,
    TriggerCondition,
    TriggerStatus,
    TriggerTemplate,
    UpdateTriggerRequest,
    Workflow,
    WorkflowStep,
)
from apps.memory_api.routes.event_triggers import (
    create_trigger,
    create_workflow,
    delete_trigger,
    disable_trigger,
    emit_event,
    enable_trigger,
    get_trigger,
    get_workflow,
    instantiate_template,
    list_triggers,
    update_trigger,
)

# --- Fixtures ---


@pytest.fixture
def mock_pool():
    return AsyncMock()


@pytest.fixture
def mock_trigger_repo():
    with patch("apps.memory_api.routes.event_triggers.TriggerRepository") as mock:
        repo = AsyncMock()
        mock.return_value = repo
        yield repo


@pytest.fixture
def mock_workflow_repo():
    with patch("apps.memory_api.routes.event_triggers.WorkflowRepository") as mock:
        repo = AsyncMock()
        mock.return_value = repo
        yield repo


@pytest.fixture
def mock_rules_engine():
    with patch("apps.memory_api.routes.event_triggers.RulesEngine") as mock:
        engine = AsyncMock()
        mock.return_value = engine
        yield engine


@pytest.fixture
def client_with_auth():
    with patch("apps.memory_api.security.auth.verify_token") as mock_auth:
        mock_auth.return_value = {"sub": "test-user", "role": "admin"}
        with TestClient(app) as client:
            yield client


# --- Trigger Management Tests ---


@pytest.mark.asyncio
async def test_create_trigger_success(mock_trigger_repo):
    """Test creating a new trigger"""
    trigger_id = uuid4()
    mock_trigger_repo.create_trigger.return_value = {"id": trigger_id}

    req = CreateTriggerRequest(
        tenant_id="t1",
        project_id="p1",
        rule_name="Test Trigger",
        condition=TriggerCondition(
            event_types=[EventType.MEMORY_CREATED], condition_group=None
        ),
        actions=[
            ActionConfig(
                action_type=ActionType.SEND_NOTIFICATION,
                config={"msg": "High importance"},
            )
        ],
        created_by="user1",
    )

    response = await create_trigger(req, mock_trigger_repo)

    assert response.trigger_id == trigger_id
    assert "Test Trigger" in response.message
    mock_trigger_repo.create_trigger.assert_called_once()


@pytest.mark.asyncio
async def test_create_trigger_failure(mock_trigger_repo):
    """Test trigger creation failure"""
    mock_trigger_repo.create_trigger.side_effect = Exception("DB Error")

    req = CreateTriggerRequest(
        tenant_id="t1",
        project_id="p1",
        rule_name="Test",
        condition=TriggerCondition(event_types=[EventType.MEMORY_CREATED]),
        actions=[ActionConfig(action_type=ActionType.SEND_NOTIFICATION)],
        created_by="u1",
    )

    with pytest.raises(HTTPException) as exc:
        await create_trigger(req, mock_trigger_repo)
    assert exc.value.status_code == 500


@pytest.mark.asyncio
async def test_get_trigger_success(mock_trigger_repo):
    """Test getting a trigger by ID"""
    trigger_id = uuid4()
    mock_data = {
        "trigger_id": trigger_id,
        "tenant_id": "t1",
        "project_id": "p1",
        "rule_name": "Test Trigger",
        "condition": TriggerCondition(event_types=[EventType.MEMORY_CREATED]),
        "actions": [],
        "created_by": "u1",
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc),
        "status": TriggerStatus.ACTIVE,
    }
    mock_trigger_repo.get_trigger.return_value = mock_data

    response = await get_trigger(str(trigger_id), mock_trigger_repo)
    assert response.trigger_id == trigger_id
    assert response.rule_name == "Test Trigger"


@pytest.mark.asyncio
async def test_get_trigger_not_found(mock_trigger_repo):
    """Test getting non-existent trigger"""
    mock_trigger_repo.get_trigger.return_value = None

    with pytest.raises(HTTPException) as exc:
        await get_trigger(str(uuid4()), mock_trigger_repo)
    assert exc.value.status_code == 404


@pytest.mark.asyncio
async def test_update_trigger_success(mock_trigger_repo):
    """Test updating a trigger"""
    trigger_id = uuid4()
    mock_trigger_repo.update_trigger.return_value = {"id": trigger_id}

    req = UpdateTriggerRequest(rule_name="Updated Name", status=TriggerStatus.INACTIVE)

    response = await update_trigger(str(trigger_id), req, mock_trigger_repo)

    assert response["trigger_id"] == str(trigger_id)
    mock_trigger_repo.update_trigger.assert_called_once()
    # Verify correct args passed
    call_args = mock_trigger_repo.update_trigger.call_args
    assert call_args[0][0] == trigger_id
    assert call_args[0][2]["rule_name"] == "Updated Name"
    assert call_args[0][2]["status"] == TriggerStatus.INACTIVE


@pytest.mark.asyncio
async def test_delete_trigger_success(mock_trigger_repo):
    """Test deleting a trigger"""
    trigger_id = uuid4()
    mock_trigger_repo.delete_trigger.return_value = True

    response = await delete_trigger(str(trigger_id), mock_trigger_repo)

    assert response["trigger_id"] == str(trigger_id)
    mock_trigger_repo.delete_trigger.assert_called_once()


@pytest.mark.asyncio
async def test_enable_disable_trigger(mock_pool):
    """Test enable/disable endpoints"""
    trigger_id = str(uuid4())

    # Test enable
    with patch("apps.memory_api.routes.event_triggers.logger"):
        resp_enable = await enable_trigger(trigger_id, mock_pool)
        assert resp_enable["status"] == TriggerStatus.ACTIVE

        resp_disable = await disable_trigger(trigger_id, mock_pool)
        assert resp_disable["status"] == TriggerStatus.INACTIVE


@pytest.mark.asyncio
async def test_list_triggers(mock_trigger_repo):
    """Test listing triggers"""
    mock_triggers = [
        {"id": uuid4(), "rule_name": "T1"},
        {"id": uuid4(), "rule_name": "T2"},
    ]
    mock_trigger_repo.list_triggers.return_value = mock_triggers

    response = await list_triggers("t1", "p1", limit=10, repo=mock_trigger_repo)

    assert response["total_count"] == 2
    assert len(response["triggers"]) == 2


# --- Event Emission Tests ---


@pytest.mark.asyncio
async def test_emit_event_success(mock_pool, mock_rules_engine):
    """Test emitting an event"""
    event_id = uuid4()
    mock_rules_engine.process_event.return_value = {
        "triggers_matched": 2,
        "actions_executed": 3,
    }

    req = EmitEventRequest(
        event_type=EventType.MEMORY_CREATED,
        tenant_id="t1",
        project_id="p1",
        payload={"data": "test"},
        user_id="u1",
    )

    with patch("apps.memory_api.routes.event_triggers.uuid4", return_value=event_id):
        response = await emit_event(req, mock_pool)

    assert response.event_id == event_id
    assert response.triggers_matched == 2
    assert response.actions_queued == 3
    mock_rules_engine.process_event.assert_called_once()


# --- Workflow Tests ---


@pytest.mark.asyncio
async def test_create_workflow_success(mock_workflow_repo):
    """Test creating a workflow"""
    workflow_id = uuid4()
    mock_workflow_repo.create_workflow.return_value = {"id": workflow_id}

    step1 = WorkflowStep(
        step_id="s1",
        step_name="Step 1",
        order=1,
        action=ActionConfig(action_type=ActionType.SEND_NOTIFICATION, config={}),
    )

    req = CreateWorkflowRequest(
        tenant_id="t1",
        project_id="p1",
        workflow_name="WF1",
        steps=[step1],
        created_by="u1",
    )

    response = await create_workflow(req, mock_workflow_repo)
    assert response.workflow_id == workflow_id


@pytest.mark.asyncio
async def test_get_workflow_success(mock_workflow_repo):
    """Test getting a workflow"""
    workflow_id = uuid4()
    mock_wf = Workflow(
        workflow_id=workflow_id,
        workflow_name="WF1",
        steps=[
            WorkflowStep(
                step_id="s1",
                step_name="Step 1",
                order=1,
                action=ActionConfig(
                    action_type=ActionType.SEND_NOTIFICATION, config={}
                ),
            )
        ],
        created_by="u1",
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    mock_workflow_repo.get_workflow.return_value = mock_wf

    response = await get_workflow(str(workflow_id), mock_workflow_repo)
    assert response["workflow"] == mock_wf


# --- Template Tests ---


@pytest.mark.asyncio
async def test_instantiate_template_success(mock_pool):
    """Test creating trigger from template"""
    template_id = "test_tpl"

    with patch.dict(
        "apps.memory_api.routes.event_triggers.DEFAULT_TEMPLATES",
        {
            template_id: TriggerTemplate(
                template_id=template_id,
                template_name="Test",
                description="Desc",
                category="test",
                parameters={},
                required_parameters=["p1"],
                use_cases=[],
                default_condition=TriggerCondition(
                    event_types=[EventType.MEMORY_CREATED]
                ),
                default_actions=[
                    ActionConfig(action_type=ActionType.SEND_NOTIFICATION)
                ],
            )
        },
    ):
        req_params = {"p1": "value"}
        response = await instantiate_template(
            template_id, "t1", "p1", "New Rule", req_params, "u1", mock_pool
        )

        assert isinstance(response.trigger_id, UUID)
        assert "from template 'Test'" in response.message


@pytest.mark.asyncio
async def test_instantiate_template_missing_param(mock_pool):
    """Test template instantiation validation"""
    template_id = "test_tpl"

    with patch.dict(
        "apps.memory_api.routes.event_triggers.DEFAULT_TEMPLATES",
        {
            template_id: TriggerTemplate(
                template_id=template_id,
                template_name="Test",
                description="Desc",
                category="test",
                parameters={},
                required_parameters=["p1"],
                use_cases=[],
                default_condition=TriggerCondition(
                    event_types=[EventType.MEMORY_CREATED]
                ),
                default_actions=[
                    ActionConfig(action_type=ActionType.SEND_NOTIFICATION)
                ],
            )
        },
    ):
        with pytest.raises(HTTPException) as exc:
            await instantiate_template(
                template_id, "t1", "p1", "New Rule", {}, "u1", mock_pool
            )
        assert exc.value.status_code == 400
        assert "Required parameter 'p1' missing" in exc.value.detail
