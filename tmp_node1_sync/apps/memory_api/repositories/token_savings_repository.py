from datetime import datetime, timedelta
from typing import List, Optional

import asyncpg
import structlog

from apps.memory_api.models.token_savings import SavingsSummary, TokenSavingsEntry

logger = structlog.get_logger(__name__)


class TokenSavingsRepository:
    """
    Repository for tracking and querying token savings metrics.
    """

    def __init__(self, pool: asyncpg.Pool):
        self.pool = pool

    async def log_savings(self, entry: TokenSavingsEntry) -> None:
        """
        Log a token savings event to the database.
        """
        query = """
            INSERT INTO token_savings_log (
                tenant_id,
                project_id,
                request_id,
                predicted_tokens,
                real_tokens,
                saved_tokens,
                estimated_cost_saved_usd,
                savings_type,
                model,
                timestamp
            ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, COALESCE($10, NOW()))
        """
        try:
            await self.pool.execute(
                query,
                entry.tenant_id,
                entry.project_id,
                entry.request_id,
                entry.predicted_tokens,
                entry.real_tokens,
                entry.saved_tokens,
                entry.estimated_cost_saved_usd,
                entry.savings_type,
                entry.model,
                entry.timestamp,
            )
        except Exception as e:
            logger.error(
                "failed_to_log_savings", error=str(e), entry=entry.model_dump()
            )
            # We don't raise here to avoid breaking the main request flow
            # Metrics loss is acceptable vs request failure

    async def get_savings_summary(
        self,
        tenant_id: str,
        project_id: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> SavingsSummary:
        """
        Calculate aggregated savings for a given period.
        """
        if not start_date:
            start_date = datetime.now() - timedelta(days=30)
        if not end_date:
            end_date = datetime.now()

        conditions = ["tenant_id = $1", "timestamp BETWEEN $2 AND $3"]
        params = [tenant_id, start_date, end_date]

        if project_id:
            params.append(project_id)
            conditions.append(f"project_id = ${len(params)}")

        where_clause = " AND ".join(conditions)

        # Aggregation query
        query = f"""
            SELECT
                COALESCE(SUM(saved_tokens), 0) as total_tokens,
                COALESCE(SUM(estimated_cost_saved_usd), 0) as total_usd,
                savings_type,
                SUM(saved_tokens) as type_tokens
            FROM token_savings_log
            WHERE {where_clause}
            GROUP BY savings_type
        """  # nosec
        rows = await self.pool.fetch(query, *params)

        total_tokens = 0
        total_usd = 0.0
        by_type = {}

        # Process grouped results
        for row in rows:
            # Note: total_tokens/usd are partial sums here if multiple types exist,
            # but usually we want the grand total.
            # Actually, GROUP BY savings_type means we get one row per type.
            # We need to sum them up in python or use window functions/ROLLUP.
            # Simpler to sum in python here.
            t_tokens = row["type_tokens"] or 0

            by_type[row["savings_type"]] = t_tokens
            total_tokens += t_tokens
            # Assuming total_usd comes from sum of individual rows
            # But since we grouped, we can't just take total_usd from first column easily
            # unless we do window function.
            # Let's adjust query logic:
            # The query sums saved_tokens and cost PER GROUP.
            # So we sum these groups to get grand total.
            total_usd += float(row["total_usd"] or 0.0)

        return SavingsSummary(
            total_saved_tokens=total_tokens,
            total_saved_usd=total_usd,
            savings_by_type=by_type,
            period_start=start_date,
            period_end=end_date,
        )

    async def get_timeseries(
        self,
        tenant_id: str,
        interval: str = "day",
        limit: int = 30,  # 'hour', 'day'
    ) -> List[dict]:
        """
        Get savings over time for charting.
        """
        trunc = "hour" if interval == "hour" else "day"

        query = """
            SELECT
                date_trunc($2, timestamp) as bucket,
                SUM(saved_tokens) as saved_tokens,
                SUM(estimated_cost_saved_usd) as saved_usd
            FROM token_savings_log
            WHERE tenant_id = $1
            GROUP BY bucket
            ORDER BY bucket DESC
            LIMIT $3
        """

        rows = await self.pool.fetch(query, tenant_id, trunc, limit)
        return [dict(row) for row in rows]
