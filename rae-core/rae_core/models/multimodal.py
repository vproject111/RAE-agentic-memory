"""Multimodal artifact models for visual evidence retrieval."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from rae_core.models.envelope import ContextEnvelope


class MultimodalArtifact(BaseModel):
    """Visual or multimodal evidence item (screenshot, architecture diagram, PDF page)."""

    model_config = ConfigDict(extra="forbid")

    artifact_id: str
    artifact_type: str = Field(
        description="screenshot | architecture_diagram | pdf_page"
    )
    image_uri: str
    ocr_extracted_text: str | None = None
    visual_embedding: list[float] | None = None  # CLIP / SigLIP
    text_embedding: list[float] | None = None
    envelope: ContextEnvelope | None = None
