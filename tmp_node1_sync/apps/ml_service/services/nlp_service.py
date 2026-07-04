"""
NLP Service - Natural Language Processing operations using spaCy.

This service handles keyword extraction, named entity recognition,
and other NLP tasks for the ML microservice.
"""

from typing import Any, Dict, List, cast

import structlog

logger = structlog.get_logger(__name__)


class NLPService:
    """
    Service for NLP operations using spaCy.

    Provides keyword extraction, NER, and other text processing capabilities.
    """

    _instance = None
    _nlp: Any = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self, language: str = "en"):
        """
        Initialize NLP service with spaCy model.

        Args:
            language: Language code (default: "en" for English)
        """
        if self._nlp is None:
            try:
                import spacy

                logger.info("loading_spacy_model", language=language)

                # Try to load language-specific model
                try:
                    if language == "en":
                        # Try large model first, fall back to medium/small
                        try:
                            self._nlp = spacy.load("en_core_web_lg")
                            logger.info("spacy_model_loaded", model="en_core_web_lg")
                        except OSError:
                            try:
                                self._nlp = spacy.load("en_core_web_md")
                                logger.info(
                                    "spacy_model_loaded", model="en_core_web_md"
                                )
                            except OSError:
                                self._nlp = spacy.load("en_core_web_sm")
                                logger.info(
                                    "spacy_model_loaded", model="en_core_web_sm"
                                )
                    else:
                        # For other languages, load the specified model
                        self._nlp = spacy.load(f"{language}_core_news_sm")
                        logger.info(
                            "spacy_model_loaded", model=f"{language}_core_news_sm"
                        )

                except OSError as e:
                    logger.warning(
                        "spacy_model_not_found",
                        language=language,
                        error=str(e),
                        fallback="blank",
                    )
                    # Fall back to blank spaCy model with basic tokenization
                    self._nlp = spacy.blank(language)

            except ImportError as e:
                logger.error("spacy_not_installed", error=str(e))
                raise RuntimeError(
                    "spaCy is not installed. Please install it: pip install spacy"
                )

    def extract_keywords(
        self, text: str, max_keywords: int = 10, language: str = "en"
    ) -> List[Dict[str, Any]]:
        """
        Extract keywords and key phrases from text.

        Uses spaCy's linguistic features to identify important terms:
        - Named entities
        - Noun chunks
        - Important tokens (nouns, proper nouns, etc.)

        Args:
            text: Input text to process
            max_keywords: Maximum number of keywords to return
            language: Language code

        Returns:
            List of keyword dictionaries with text, type, and score
        """
        if not text:
            return []

        logger.info("extracting_keywords", text_length=len(text), language=language)

        try:
            # Process text with spaCy
            doc = self._nlp(text)

            keywords = []

            # Extract named entities (high priority)
            for ent in doc.ents:
                keywords.append(
                    {
                        "text": ent.text,
                        "type": "entity",
                        "label": ent.label_,
                        "score": 1.0,  # Entities get highest score
                    }
                )

            # Extract noun chunks (medium priority)
            for chunk in doc.noun_chunks:
                # Skip if already in entities
                if not any(
                    cast(str, kw["text"]).lower() == chunk.text.lower()
                    and kw["type"] == "entity"
                    for kw in keywords
                ):
                    keywords.append(
                        {
                            "text": chunk.text,
                            "type": "noun_phrase",
                            "label": "NOUN_CHUNK",
                            "score": 0.7,
                        }
                    )

            # Extract important individual tokens (lower priority)
            for token in doc:
                # Skip if token is in stopwords, punctuation, or spaces
                if token.is_stop or token.is_punct or token.is_space:
                    continue

                # Focus on nouns, proper nouns, adjectives
                if token.pos_ in ["NOUN", "PROPN", "ADJ"]:
                    # Skip if already in keywords
                    if not any(
                        cast(str, kw["text"]).lower() == token.text.lower()
                        for kw in keywords
                    ):
                        keywords.append(
                            {
                                "text": token.text,
                                "type": "token",
                                "label": token.pos_,
                                "score": 0.5,
                            }
                        )

            # Sort by score (descending) and limit
            keywords.sort(key=lambda x: x["score"], reverse=True)
            keywords = keywords[:max_keywords]

            logger.info(
                "keywords_extracted", keyword_count=len(keywords), text_length=len(text)
            )

            return keywords

        except Exception as e:
            logger.exception("keyword_extraction_failed", error=str(e))
            return []

    def extract_entities(self, text: str) -> List[Dict[str, Any]]:
        """
        Extract named entities from text.

        Args:
            text: Input text to process

        Returns:
            List of entity dictionaries with text, label, and position
        """
        if not text:
            return []

        try:
            doc = self._nlp(text)

            entities = []
            for ent in doc.ents:
                entities.append(
                    {
                        "text": ent.text,
                        "label": ent.label_,
                        "start": ent.start_char,
                        "end": ent.end_char,
                    }
                )

            return entities

        except Exception as e:
            logger.exception("entity_extraction_failed", error=str(e))
            return []
