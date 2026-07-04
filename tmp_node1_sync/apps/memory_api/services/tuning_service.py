"""
RAE Tuning Service - Phase 4 Self-improvement.

Orchestrates the Bayesian update cycle for tenant scoring weights.
"""

from typing import Dict, List, Optional
import structlog
from rae_core.math.tuning import BayesianPolicyTuner
from apps.memory_api.services.rae_core_service import RAECoreService

logger = structlog.get_logger(__name__)

class TuningService:
    def __init__(self, rae_service: RAECoreService):
        self.rae_service = rae_service
        self.tuner = BayesianPolicyTuner()

    async def tune_tenant_weights(self, tenant_id: str) -> Optional[Dict[str, float]]:
        """
        Runs a tuning cycle for a specific tenant based on their feedback history.
        """
        # 1. Fetch feedback history from DB
        sql = """
            SELECT query_text, score, weights_snapshot 
            FROM memory_feedback 
            WHERE tenant_id = $1 
            ORDER BY created_at DESC 
            LIMIT 50
        """
        feedback_rows = await self.rae_service.db.fetch(sql, tenant_id)
        
        if not feedback_rows:
            logger.info("tuning_skipped_no_feedback", tenant_id=tenant_id)
            return None

        # 2. Get current baseline weights
        current_weights_obj = await self.rae_service._get_tenant_weights(tenant_id)
        if current_weights_obj:
            current_weights = {
                "alpha": current_weights_obj.alpha,
                "beta": current_weights_obj.beta,
                "gamma": current_weights_obj.gamma
            }
        else:
            current_weights = {"alpha": 0.5, "beta": 0.3, "gamma": 0.2}

        # 3. Format data for tuner
        feedback_loop = []
        for row in feedback_rows:
            import json
            weights = row['weights_snapshot']
            if isinstance(weights, str):
                weights = json.loads(weights)
            
            feedback_loop.append({
                "score": row['score'],
                "weights": weights
            })

        # 4. Compute Bayes Posterior
        result = self.tuner.compute_posterior(current_weights, feedback_loop)
        
        logger.info(
            "tuning_cycle_complete",
            tenant_id=tenant_id,
            old_weights=current_weights,
            new_weights=result.new_weights,
            confidence=result.confidence
        )

        # 5. Persist to tenant config (Section 14.2)
        if result.confidence > 0.1: # Only update if we have a significant signal
            try:
                import json
                update_sql = """
                    UPDATE tenants 
                    SET config = jsonb_set(COALESCE(config, '{}'::jsonb), '{math_weights}', $1::jsonb)
                    WHERE id = $2
                """
                await self.rae_service.db.execute(
                    update_sql,
                    json.dumps(result.new_weights),
                    tenant_id
                )
                return result.new_weights
            except Exception as e:
                logger.error("tuning_persistence_failed", error=str(e))
        
        return None
