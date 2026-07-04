"""
Input Validation and Sanitization Module

Provides functions for validating and sanitizing user input.
"""

import re
from typing import List, Optional

import structlog
from fastapi import HTTPException, status

logger = structlog.get_logger(__name__)

# Constants
MAX_CONTENT_LENGTH = 50000  # 50KB
MAX_TAG_LENGTH = 50
MAX_TAGS_COUNT = 20
MAX_QUERY_LENGTH = 1000

# Patterns for validation
TAG_PATTERN = re.compile(r"^[a-zA-Z0-9_-]+$")
SAFE_STRING_PATTERN = re.compile(r"^[a-zA-Z0-9\s\-_.,!?()\'\"]+$")


def sanitize_input(text: str, max_length: Optional[int] = None) -> str:
    """
    Sanitize text input by removing potentially dangerous characters.

    Args:
        text: Input text to sanitize
        max_length: Maximum allowed length (optional)

    Returns:
        Sanitized text

    Raises:
        HTTPException: If input is invalid
    """
    if not text:
        return text

    # Check length
    if max_length and len(text) > max_length:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Input exceeds maximum length of {max_length} characters",
        )

    # Remove null bytes
    text = text.replace("\x00", "")

    # Remove control characters (except newlines and tabs)
    text = "".join(char for char in text if char.isprintable() or char in ["\n", "\t"])

    return text.strip()


def validate_content(content: str) -> str:
    """
    Validate memory content.

    Args:
        content: Memory content to validate

    Returns:
        Validated content

    Raises:
        HTTPException: If content is invalid
    """
    if not content or not content.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Content cannot be empty"
        )

    if len(content) > MAX_CONTENT_LENGTH:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Content exceeds maximum length of {MAX_CONTENT_LENGTH} characters",
        )

    # Check for potential XSS attempts
    dangerous_patterns = ["<script", "javascript:", "onerror=", "onclick="]
    content_lower = content.lower()

    for pattern in dangerous_patterns:
        if pattern in content_lower:
            logger.warning("potential_xss_attempt", pattern=pattern)
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Content contains potentially dangerous patterns",
            )

    return sanitize_input(content, MAX_CONTENT_LENGTH)


def validate_tags(tags: List[str]) -> List[str]:
    """
    Validate memory tags.

    Args:
        tags: List of tags to validate

    Returns:
        Validated list of tags

    Raises:
        HTTPException: If tags are invalid
    """
    if not tags:
        return []

    if len(tags) > MAX_TAGS_COUNT:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Maximum {MAX_TAGS_COUNT} tags allowed",
        )

    validated_tags = []

    for tag in tags:
        tag = tag.strip()

        if not tag:
            continue

        if len(tag) > MAX_TAG_LENGTH:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Tag '{tag[:20]}...' exceeds maximum length of {MAX_TAG_LENGTH} characters",
            )

        # Check for dangerous characters
        if "<" in tag or ">" in tag or ";" in tag or '"' in tag or "'" in tag:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Tag '{tag}' contains invalid characters",
            )

        # Validate tag pattern (alphanumeric, underscore, hyphen only)
        if not TAG_PATTERN.match(tag):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Tag '{tag}' must contain only alphanumeric characters, underscores, and hyphens",
            )

        validated_tags.append(tag.lower())

    return validated_tags


def validate_query(query: str) -> str:
    """
    Validate search query.

    Args:
        query: Search query to validate

    Returns:
        Validated query

    Raises:
        HTTPException: If query is invalid
    """
    if not query or not query.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Query cannot be empty"
        )

    if len(query) > MAX_QUERY_LENGTH:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Query exceeds maximum length of {MAX_QUERY_LENGTH} characters",
        )

    return sanitize_input(query, MAX_QUERY_LENGTH)


def validate_layer(layer: str) -> str:
    """
    Validate memory layer.

    Args:
        layer: Memory layer to validate

    Returns:
        Validated layer

    Raises:
        HTTPException: If layer is invalid
    """
    valid_layers = ["episodic", "working", "semantic", "ltm"]

    layer = layer.lower().strip()

    if layer not in valid_layers:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid memory layer. Must be one of: {', '.join(valid_layers)}",
        )

    return layer


def validate_tenant_id(tenant_id: Optional[str]) -> Optional[str]:
    """
    Validate tenant ID.

    Args:
        tenant_id: Tenant ID to validate

    Returns:
        Validated tenant ID or None

    Raises:
        HTTPException: If tenant ID is invalid
    """
    if not tenant_id:
        return None

    tenant_id = tenant_id.strip()

    if len(tenant_id) > 100:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Tenant ID too long"
        )

    # Allow alphanumeric, hyphens, underscores
    if not re.match(r"^[a-zA-Z0-9_-]+$", tenant_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Tenant ID contains invalid characters",
        )

    return tenant_id


def validate_project_id(project_id: Optional[str]) -> Optional[str]:
    """
    Validate project ID.

    Args:
        project_id: Project ID to validate

    Returns:
        Validated project ID or None

    Raises:
        HTTPException: If project ID is invalid
    """
    if not project_id:
        return None

    project_id = project_id.strip()

    if len(project_id) > 100:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Project ID too long"
        )

    # Allow alphanumeric, hyphens, underscores
    if not re.match(r"^[a-zA-Z0-9_-]+$", project_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Project ID contains invalid characters",
        )

    return project_id


def validate_limit(limit: Optional[int], max_limit: int = 100) -> int:
    """
    Validate query limit parameter.

    Args:
        limit: Requested limit
        max_limit: Maximum allowed limit

    Returns:
        Validated limit

    Raises:
        HTTPException: If limit is invalid
    """
    if limit is None:
        return 10  # Default limit

    if not isinstance(limit, int) or limit < 1:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Limit must be a positive integer",
        )

    if limit > max_limit:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Limit cannot exceed {max_limit}",
        )

    return limit
