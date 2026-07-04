"""
Source Trust Service - ISO/IEC 42001 Compliance

Manages source trust scoring, verification, and provenance tracking
for knowledge sources in RAE memory system.

Key features:
- Source trust level assessment (high/medium/low/unverified)
- Automatic trust scoring based on source attributes
- Verification workflow support
- Trust decay over time (temporal validation)
- Audit trail for trust changes

ISO/IEC 42001 alignment:
- Section 6: Risk management (RISK-003: Halucynacje z błędnych kontekstów)
- Section 7: Data quality and provenance
- Section 8: Transparency and explainability
"""

import logging
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class SourceTrustLevel(str, Enum):
    """Trust level classification for knowledge sources"""

    HIGH = "high"  # Verified, authoritative (docs, verified experts, official APIs)
    MEDIUM = "medium"  # Generally reliable (team knowledge, tested code, known sources)
    LOW = "low"  # Unverified or questionable (external, user input, unverified)
    UNVERIFIED = "unverified"  # New sources pending verification


class SourceCategory(str, Enum):
    """Category of knowledge source for automatic trust scoring"""

    OFFICIAL_DOCUMENTATION = "official_documentation"
    VERIFIED_EXPERT = "verified_expert"
    TEAM_KNOWLEDGE = "team_knowledge"
    PRODUCTION_CODE = "production_code"
    TEST_CODE = "test_code"
    USER_INPUT = "user_input"
    EXTERNAL_API = "external_api"
    LLM_GENERATED = "llm_generated"
    UNSPECIFIED = "unspecified"


class TrustScore(BaseModel):
    """Trust score with rationale"""

    level: SourceTrustLevel
    confidence: float = Field(
        ge=0.0, le=1.0, description="Confidence in the trust level"
    )
    rationale: str = Field(description="Explanation for the trust level")
    factors: Dict[str, float] = Field(
        default_factory=dict, description="Contributing factors to trust score"
    )


class SourceTrustService:
    """
    Service for managing source trust scoring and verification

    Provides automatic trust assessment and verification workflow
    """

    # Trust scoring rules based on source category
    CATEGORY_TRUST_MAPPING = {
        SourceCategory.OFFICIAL_DOCUMENTATION: (SourceTrustLevel.HIGH, 0.95),
        SourceCategory.VERIFIED_EXPERT: (SourceTrustLevel.HIGH, 0.90),
        SourceCategory.TEAM_KNOWLEDGE: (SourceTrustLevel.MEDIUM, 0.80),
        SourceCategory.PRODUCTION_CODE: (SourceTrustLevel.MEDIUM, 0.85),
        SourceCategory.TEST_CODE: (SourceTrustLevel.MEDIUM, 0.75),
        SourceCategory.USER_INPUT: (SourceTrustLevel.LOW, 0.50),
        SourceCategory.EXTERNAL_API: (SourceTrustLevel.LOW, 0.60),
        SourceCategory.LLM_GENERATED: (SourceTrustLevel.LOW, 0.55),
        SourceCategory.UNSPECIFIED: (SourceTrustLevel.UNVERIFIED, 0.30),
    }

    # Trust decay configuration (days before trust level degrades)
    TRUST_DECAY_THRESHOLDS = {
        SourceTrustLevel.HIGH: 365,  # 1 year for high trust
        SourceTrustLevel.MEDIUM: 180,  # 6 months for medium trust
        SourceTrustLevel.LOW: 90,  # 3 months for low trust
        SourceTrustLevel.UNVERIFIED: 30,  # 1 month for unverified
    }

    def __init__(self, settings: Optional[Any] = None):
        self.settings = settings
        self.logger = logging.getLogger(__name__)

    def assess_source_trust(
        self,
        source: Optional[str] = None,
        source_category: Optional[SourceCategory] = None,
        source_owner: Optional[str] = None,
        extraction_confidence: Optional[float] = None,
        tags: Optional[List[str]] = None,
    ) -> TrustScore:
        """
        Automatically assess trust level for a source

        Args:
            source: Source identifier/name
            source_category: Category of source
            source_owner: Owner/responsible party
            extraction_confidence: Confidence from extraction process
            tags: Tags associated with the memory

        Returns:
            TrustScore with level, confidence, and rationale
        """
        factors = {}

        # Start with category-based trust
        if source_category:
            base_level, base_confidence = self.CATEGORY_TRUST_MAPPING.get(
                source_category, (SourceTrustLevel.UNVERIFIED, 0.3)
            )
        else:
            # Infer category from source string
            inferred_category = self._infer_source_category(source, tags)
            base_level, base_confidence = self.CATEGORY_TRUST_MAPPING[inferred_category]
            source_category = inferred_category

        factors["base_category"] = base_confidence

        # Adjust confidence based on source owner (verified owner = higher trust)
        if source_owner:
            if "@" in source_owner:  # Email = verified identity
                factors["verified_owner"] = 0.1
                base_confidence = min(1.0, base_confidence + 0.1)
            else:
                factors["has_owner"] = 0.05
                base_confidence = min(1.0, base_confidence + 0.05)

        # Adjust based on extraction confidence (high confidence extraction = more trust)
        if extraction_confidence is not None:
            extraction_factor = (extraction_confidence - 0.5) * 0.2  # -0.1 to +0.1
            factors["extraction_confidence"] = extraction_factor
            base_confidence = max(0.0, min(1.0, base_confidence + extraction_factor))

        # Adjust based on tags (certain tags indicate higher quality)
        if tags:
            trusted_tags = {"verified", "official", "documentation", "expert"}
            untrusted_tags = {"experimental", "draft", "unverified", "todo"}

            trust_boost = len(set(tags) & trusted_tags) * 0.05
            trust_penalty = len(set(tags) & untrusted_tags) * 0.05

            if trust_boost > 0:
                factors["trusted_tags"] = trust_boost
            if trust_penalty > 0:
                factors["untrusted_tags"] = -trust_penalty

            base_confidence = max(
                0.0, min(1.0, base_confidence + trust_boost - trust_penalty)
            )

        # Generate rationale
        rationale = self._generate_rationale(
            source_category, source_owner, extraction_confidence, factors
        )

        return TrustScore(
            level=base_level,
            confidence=base_confidence,
            rationale=rationale,
            factors=factors,
        )

    def _infer_source_category(
        self, source: Optional[str], tags: Optional[List[str]]
    ) -> SourceCategory:
        """Infer source category from source string and tags"""

        if not source:
            return SourceCategory.UNSPECIFIED

        source_lower = source.lower()

        # Check for official documentation patterns
        if any(
            keyword in source_lower
            for keyword in ["docs", "documentation", "official", "readme", "spec"]
        ):
            return SourceCategory.OFFICIAL_DOCUMENTATION

        # Check for code patterns
        if any(ext in source_lower for ext in [".py", ".js", ".ts", ".go", ".java"]):
            if "test" in source_lower:
                return SourceCategory.TEST_CODE
            return SourceCategory.PRODUCTION_CODE

        # Check for API patterns
        if any(
            keyword in source_lower for keyword in ["api", "endpoint", "http", "rest"]
        ):
            return SourceCategory.EXTERNAL_API

        # Check for user input patterns
        if any(
            keyword in source_lower
            for keyword in ["user", "input", "chat", "conversation", "message"]
        ):
            return SourceCategory.USER_INPUT

        # Check for LLM generation patterns
        if any(
            keyword in source_lower for keyword in ["llm", "generated", "gpt", "claude"]
        ):
            return SourceCategory.LLM_GENERATED

        # Check tags
        if tags:
            tags_lower = [tag.lower() for tag in tags]
            if any(
                tag in tags_lower for tag in ["expert", "verified", "authoritative"]
            ):
                return SourceCategory.VERIFIED_EXPERT
            if any(tag in tags_lower for tag in ["team", "internal", "knowledge"]):
                return SourceCategory.TEAM_KNOWLEDGE

        return SourceCategory.UNSPECIFIED

    def _generate_rationale(
        self,
        category: SourceCategory,
        source_owner: Optional[str],
        extraction_confidence: Optional[float],
        factors: Dict[str, float],
    ) -> str:
        """Generate human-readable rationale for trust score"""

        rationale_parts = [f"Category: {category.value}"]

        if source_owner:
            rationale_parts.append(f"Owner: {source_owner}")

        if extraction_confidence is not None:
            rationale_parts.append(
                f"Extraction confidence: {extraction_confidence:.2f}"
            )

        if factors:
            factor_desc = ", ".join([f"{k}={v:+.2f}" for k, v in factors.items()])
            rationale_parts.append(f"Factors: {factor_desc}")

        return " | ".join(rationale_parts)

    def check_trust_decay(
        self, trust_level: SourceTrustLevel, last_verified_at: Optional[datetime]
    ) -> tuple[SourceTrustLevel, str]:
        """
        Check if trust level should decay based on time since last verification

        Returns:
            (new_trust_level, reason) - new level may be same or degraded
        """

        if not last_verified_at:
            # Never verified - should remain unverified or degrade to unverified
            if trust_level != SourceTrustLevel.UNVERIFIED:
                return (
                    SourceTrustLevel.UNVERIFIED,
                    "No verification timestamp - degraded to unverified",
                )
            return (trust_level, "Never verified")

        days_since_verification = (datetime.now(timezone.utc) - last_verified_at).days
        decay_threshold = self.TRUST_DECAY_THRESHOLDS[trust_level]

        if days_since_verification > decay_threshold:
            # Degrade trust level
            degraded_level = self._degrade_trust_level(trust_level)
            return (
                degraded_level,
                f"Trust decayed after {days_since_verification} days (threshold: {decay_threshold})",
            )

        return (trust_level, f"Verified {days_since_verification} days ago")

    def _degrade_trust_level(self, current_level: SourceTrustLevel) -> SourceTrustLevel:
        """Degrade trust level by one step"""

        degradation_chain = [
            SourceTrustLevel.HIGH,
            SourceTrustLevel.MEDIUM,
            SourceTrustLevel.LOW,
            SourceTrustLevel.UNVERIFIED,
        ]

        try:
            current_index = degradation_chain.index(current_level)
            if current_index < len(degradation_chain) - 1:
                return degradation_chain[current_index + 1]
        except ValueError:
            pass

        return SourceTrustLevel.UNVERIFIED

    def verify_source(
        self,
        current_level: SourceTrustLevel,
        verified_by: str,
        notes: Optional[str] = None,
    ) -> dict:
        """
        Mark a source as verified

        Args:
            current_level: Current trust level
            verified_by: Who verified the source
            notes: Verification notes

        Returns:
            dict with verification metadata
        """

        verification_time = datetime.now(timezone.utc)

        return {
            "last_verified_at": verification_time,
            "verified_by": verified_by,
            "verification_notes": notes or f"Verified by {verified_by}",
            "previous_trust_level": current_level.value,
        }

    def get_trust_filter_weights(
        self, query_requires_high_trust: bool = False
    ) -> Dict[SourceTrustLevel, float]:
        """
        Get weights for filtering/ranking memories by trust level

        Args:
            query_requires_high_trust: If True, heavily penalize low trust sources

        Returns:
            dict of trust level to weight multiplier
        """

        if query_requires_high_trust:
            # High-risk scenarios - heavily favor verified sources
            return {
                SourceTrustLevel.HIGH: 1.0,
                SourceTrustLevel.MEDIUM: 0.5,
                SourceTrustLevel.LOW: 0.1,
                SourceTrustLevel.UNVERIFIED: 0.05,
            }
        else:
            # Normal scenarios - moderate preference for trusted sources
            return {
                SourceTrustLevel.HIGH: 1.0,
                SourceTrustLevel.MEDIUM: 0.8,
                SourceTrustLevel.LOW: 0.5,
                SourceTrustLevel.UNVERIFIED: 0.3,
            }
