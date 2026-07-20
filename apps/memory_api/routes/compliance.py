import structlog

from fastapi import APIRouter, Depends, HTTPException, Query, Request

from apps.memory_api.dependencies import get_audit_service, get_compliance_service
from apps.memory_api.models.dashboard_models import (
    ComplianceArea,
    GetAuditTrailRequest,
    GetAuditTrailResponse,
    GetComplianceMetricsRequest,
    GetComplianceMetricsResponse,
    GetComplianceReportRequest,
    GetComplianceReportResponse,
    GetRiskRegisterRequest,
    GetRiskRegisterResponse,
    RiskLevel,
)
from apps.memory_api.services.audit_service import AuditService
from apps.memory_api.services.compliance_service import ComplianceService

logger = structlog.get_logger(__name__)

router = APIRouter(tags=["Compliance"])


@router.post(
    "/compliance/report",
    response_model=GetComplianceReportResponse,
    summary="Get ISO 42001 Compliance Report",
)
async def get_compliance_report(
    request: GetComplianceReportRequest,
    compliance_service: ComplianceService = Depends(get_compliance_service),
):
    """
    Get comprehensive ISO/IEC 42001 compliance report.
    """
    try:
        logger.info(
            "compliance_report_requested",
            tenant_id=request.tenant_id,
            project=request.project,
            report_type=request.report_type,
        )

        compliance_report = await compliance_service.generate_compliance_report(
            tenant_id=request.tenant_id,
            project=request.project,
            report_type=request.report_type,
            compliance_area=request.compliance_area,
        )

        rls_status = None
        if request.include_audit_trail:
            rls_status = await compliance_service.verify_rls_status(
                tenant_id=request.tenant_id
            )

        logger.info(
            "compliance_report_generated",
            tenant_id=request.tenant_id,
            overall_score=compliance_report.overall_compliance_score,
            status=compliance_report.overall_status,
        )

        return GetComplianceReportResponse(
            compliance_report=compliance_report,
            rls_status=rls_status,
            message=f"Compliance report generated successfully. Overall score: {compliance_report.overall_compliance_score:.1f}%",
        )

    except Exception as e:
        logger.error(
            "compliance_report_failed",
            tenant_id=request.tenant_id,
            error=str(e),
            exc_info=True,
        )
        raise HTTPException(
            status_code=500, detail=f"Failed to generate compliance report: {str(e)}"
        ) from e


@router.post(
    "/compliance/metrics",
    response_model=GetComplianceMetricsResponse,
    summary="Get Compliance Metrics by Area",
)
async def get_compliance_metrics(
    request: GetComplianceMetricsRequest,
    compliance_service: ComplianceService = Depends(get_compliance_service),
):
    """
    Get compliance metrics filtered by area.
    """
    try:
        full_report = await compliance_service.generate_compliance_report(
            tenant_id=request.tenant_id,
            project=request.project,
            report_type="area_specific" if request.compliance_area else "full",
            compliance_area=request.compliance_area,
        )

        metrics = []
        if request.compliance_area:
            area_map = {
                ComplianceArea.GOVERNANCE: full_report.governance_metrics,
                ComplianceArea.RISK_MANAGEMENT: full_report.risk_management_metrics,
                ComplianceArea.DATA_MANAGEMENT: full_report.data_management_metrics,
                ComplianceArea.TRANSPARENCY: full_report.transparency_metrics,
                ComplianceArea.HUMAN_OVERSIGHT: full_report.human_oversight_metrics,
                ComplianceArea.SECURITY_PRIVACY: full_report.security_privacy_metrics,
            }
            metrics = area_map.get(request.compliance_area, [])
        else:
            metrics = (
                full_report.governance_metrics
                + full_report.risk_management_metrics
                + full_report.data_management_metrics
                + full_report.transparency_metrics
                + full_report.human_oversight_metrics
                + full_report.security_privacy_metrics
            )

        area_scores = {}
        for area in ComplianceArea:
            area_metrics = [m for m in metrics if m.compliance_area == area]
            if area_metrics:
                compliant = sum(
                    1 for m in area_metrics if m.status.value == "compliant"
                )
                area_scores[area.value] = compliant / len(area_metrics) * 100

        return GetComplianceMetricsResponse(
            metrics=metrics,
            area_scores=area_scores,
            overall_score=full_report.overall_compliance_score,
            message=f"Retrieved {len(metrics)} compliance metrics",
        )

    except Exception as e:
        logger.error(
            "compliance_metrics_failed",
            tenant_id=request.tenant_id,
            error=str(e),
            exc_info=True,
        )
        raise HTTPException(
            status_code=500, detail=f"Failed to get compliance metrics: {str(e)}"
        ) from e


@router.post(
    "/compliance/risks",
    response_model=GetRiskRegisterResponse,
    summary="Get Risk Register Data",
)
async def get_risk_register(
    request: GetRiskRegisterRequest,
    compliance_service: ComplianceService = Depends(get_compliance_service),
):
    """
    Get risk register data with optional filtering.
    """
    try:
        risks = await compliance_service._get_active_risks(
            tenant_id=request.tenant_id, project=request.project
        )

        if request.risk_level:
            risks = [r for r in risks if r.risk_level == request.risk_level]

        if request.status:
            risks = [r for r in risks if r.status == request.status]

        if not request.include_closed:
            risks = [r for r in risks if r.status != "closed"]

        risk_summary = {}
        for level in RiskLevel:
            risk_summary[level.value] = sum(1 for r in risks if r.risk_level == level)

        high_priority_count = sum(
            1 for r in risks if r.risk_level in [RiskLevel.CRITICAL, RiskLevel.HIGH]
        )

        logger.info(
            "risk_register_retrieved",
            tenant_id=request.tenant_id,
            total_risks=len(risks),
            high_priority=high_priority_count,
        )

        return GetRiskRegisterResponse(
            risks=risks,
            risk_summary=risk_summary,
            high_priority_count=high_priority_count,
            message=f"Retrieved {len(risks)} risks from risk register",
        )

    except Exception as e:
        logger.error(
            "risk_register_failed",
            tenant_id=request.tenant_id,
            error=str(e),
            exc_info=True,
        )
        raise HTTPException(
            status_code=500, detail=f"Failed to get risk register: {str(e)}"
        ) from e


@router.post(
    "/compliance/audit-trail",
    response_model=GetAuditTrailResponse,
    summary="Get Audit Trail Entries",
)
async def get_audit_trail(
    request: GetAuditTrailRequest,
    req: Request,
    audit_service: AuditService = Depends(get_audit_service),
):
    """
    Get audit trail entries for compliance verification.
    """
    try:
        ip_address = req.client.host if req.client else None
        user_agent = req.headers.get("user-agent")

        result = await audit_service.get_audit_trail(
            tenant_id=request.tenant_id,
            project=request.project,
            start_time=request.start_time,
            end_time=request.end_time,
            event_types=request.event_types,
            actor_types=request.actor_types,
            limit=request.limit,
            offset=request.offset,
            request_user_id="compliance_auditor",
            ip_address=ip_address,
            user_agent=user_agent,
        )

        return GetAuditTrailResponse(
            entries=result["entries"],
            total_count=result["total_count"],
            completeness_percentage=result["completeness_percentage"],
            message=f"Retrieved {len(result['entries'])} audit trail entries",
        )

    except Exception as e:
        logger.error(
            "audit_trail_failed",
            tenant_id=request.tenant_id,
            error=str(e),
            exc_info=True,
        )
        raise HTTPException(
            status_code=500, detail=f"Failed to get audit trail: {str(e)}"
        ) from e


@router.get(
    "/compliance/rls-status",
    summary="Get RLS Verification Status",
)
async def get_rls_status(
    tenant_id: str = Query(..., description="Tenant ID"),
    compliance_service: ComplianceService = Depends(get_compliance_service),
):
    """
    Get Row-Level Security verification status.
    """
    try:
        rls_status = await compliance_service.verify_rls_status(tenant_id=tenant_id)

        logger.info(
            "rls_status_checked",
            tenant_id=tenant_id,
            verification_passed=rls_status.verification_passed,
            rls_percentage=rls_status.rls_enabled_percentage,
        )

        return {
            "tenant_id": tenant_id,
            "rls_status": rls_status,
            "message": (
                "RLS verification passed"
                if rls_status.verification_passed
                else "RLS verification failed - see issues"
            ),
        }

    except Exception as e:
        logger.error(
            "rls_status_check_failed",
            tenant_id=tenant_id,
            error=str(e),
            exc_info=True,
        )
        raise HTTPException(
            status_code=500, detail=f"Failed to verify RLS status: {str(e)}"
        ) from e
