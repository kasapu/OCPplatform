"""
Advanced Entity Extractor using spaCy NER and custom patterns

Extracts entities with higher accuracy than simple regex patterns:
- Named entities (PERSON, ORG, GPE, DATE, TIME, MONEY)
- Custom entities (account numbers, transaction IDs, amounts)
- Temporal expressions (dates, times, durations)
- Contextual entities based on conversation state
"""

import logging
import spacy
import re
from typing import List, Dict, Any, Optional
from datetime import datetime
import dateparser

logger = logging.getLogger(__name__)


class AdvancedEntityExtractor:
    """
    Advanced entity extraction with spaCy NER and custom patterns
    """

    def __init__(self, model_name: str = "en_core_web_lg"):
        """
        Initialize entity extractor

        Args:
            model_name: spaCy model (en_core_web_lg for best NER)
        """
        try:
            self.nlp = spacy.load(model_name)
            logger.info(f"Loaded spaCy model: {model_name}")
        except OSError:
            logger.warning(f"Model {model_name} not found. Downloading...")
            import subprocess
            subprocess.run(["python", "-m", "spacy", "download", model_name])
            self.nlp = spacy.load(model_name)

        # Add custom entity patterns
        self._add_custom_patterns()

    def _add_custom_patterns(self):
        """Add custom entity recognition patterns"""
        # Entity ruler for custom patterns
        if "entity_ruler" not in self.nlp.pipe_names:
            ruler = self.nlp.add_pipe("entity_ruler", before="ner")

            patterns = [
                # Account numbers
                {"label": "ACCOUNT_NUMBER", "pattern": [{"TEXT": {"REGEX": r"\d{4,12}"}}]},

                # Transaction IDs
                {"label": "TRANSACTION_ID", "pattern": [{"TEXT": {"REGEX": r"TXN\d+"}}]},

                # Email addresses
                {"label": "EMAIL", "pattern": [{"TEXT": {"REGEX": r"[\w\.-]+@[\w\.-]+\.\w+"}}]},

                # Phone numbers
                {"label": "PHONE", "pattern": [{"TEXT": {"REGEX": r"\+?\d{1,3}[-.\s]?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}"}}]},

                # Amounts with currency
                {"label": "MONEY", "pattern": [{"TEXT": {"REGEX": r"\$\d+(\.\d{2})?"}}]},
            ]

            ruler.add_patterns(patterns)

    def extract(
        self,
        text: str,
        context: Optional[Dict[str, Any]] = None,
        extract_temporal: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Extract entities from text

        Args:
            text: Input text
            context: Conversation context for contextual entity extraction
            extract_temporal: Whether to extract dates/times

        Returns:
            List of extracted entities with type, value, start, end
        """
        entities = []

        # Process with spaCy
        doc = self.nlp(text)

        # Extract named entities
        for ent in doc.ents:
            entity_dict = {
                "entity_type": ent.label_,
                "value": ent.text,
                "start": ent.start_char,
                "end": ent.end_char,
                "confidence": self._get_entity_confidence(ent)
            }

            # Parse specific entity types
            if ent.label_ == "MONEY":
                entity_dict["parsed_value"] = self._parse_money(ent.text)
            elif ent.label_ == "DATE" and extract_temporal:
                entity_dict["parsed_value"] = self._parse_date(ent.text)
            elif ent.label_ == "TIME" and extract_temporal:
                entity_dict["parsed_value"] = self._parse_time(ent.text)

            entities.append(entity_dict)

        # Extract custom entities with regex (amounts, account types, etc.)
        custom_entities = self._extract_custom_entities(text)
        entities.extend(custom_entities)

        # Deduplicate and sort by position
        entities = self._deduplicate_entities(entities)
        entities.sort(key=lambda x: x["start"])

        return entities

    def _extract_custom_entities(self, text: str) -> List[Dict[str, Any]]:
        """Extract domain-specific entities using regex patterns"""
        entities = []

        # Amount pattern (more flexible)
        amount_pattern = r'\b(\d{1,3}(?:,\d{3})*(?:\.\d{2})?|\d+(?:\.\d{2})?)\b'
        for match in re.finditer(amount_pattern, text):
            value = match.group(1).replace(',', '')
            try:
                amount = float(value)
                entities.append({
                    "entity_type": "AMOUNT",
                    "value": match.group(1),
                    "parsed_value": amount,
                    "start": match.start(),
                    "end": match.end(),
                    "confidence": 0.9
                })
            except ValueError:
                pass

        # Account type pattern
        account_types = [
            "checking", "savings", "credit", "debit",
            "current", "deposit", "loan", "mortgage"
        ]
        account_pattern = r'\b(' + '|'.join(account_types) + r')(?:\s+account)?\b'
        for match in re.finditer(account_pattern, text, re.IGNORECASE):
            entities.append({
                "entity_type": "ACCOUNT_TYPE",
                "value": match.group(0),
                "parsed_value": match.group(1).lower(),
                "start": match.start(),
                "end": match.end(),
                "confidence": 0.95
            })

        # Card type pattern
        card_types = ["visa", "mastercard", "amex", "discover", "american express"]
        card_pattern = r'\b(' + '|'.join(card_types) + r')\b'
        for match in re.finditer(card_pattern, text, re.IGNORECASE):
            entities.append({
                "entity_type": "CARD_TYPE",
                "value": match.group(0),
                "parsed_value": match.group(1).lower(),
                "start": match.start(),
                "end": match.end(),
                "confidence": 0.95
            })

        # Product names
        product_pattern = r'\b(pro|premium|basic|enterprise|standard|starter)\s+(plan|subscription|package)\b'
        for match in re.finditer(product_pattern, text, re.IGNORECASE):
            entities.append({
                "entity_type": "PRODUCT",
                "value": match.group(0),
                "start": match.start(),
                "end": match.end(),
                "confidence": 0.85
            })

        return entities

    def _parse_money(self, text: str) -> Optional[float]:
        """Parse money amount from text"""
        # Remove currency symbols and commas
        cleaned = re.sub(r'[$,£€¥]', '', text)
        try:
            return float(cleaned)
        except ValueError:
            return None

    def _parse_date(self, text: str) -> Optional[str]:
        """Parse date using dateparser"""
        try:
            parsed = dateparser.parse(text)
            if parsed:
                return parsed.isoformat()
        except Exception as e:
            logger.warning(f"Failed to parse date '{text}': {e}")
        return None

    def _parse_time(self, text: str) -> Optional[str]:
        """Parse time from text"""
        try:
            parsed = dateparser.parse(text)
            if parsed:
                return parsed.strftime("%H:%M:%S")
        except Exception:
            pass
        return None

    def _get_entity_confidence(self, ent) -> float:
        """
        Get confidence score for entity (based on various factors)

        spaCy doesn't provide confidence directly, so we estimate based on:
        - Entity type reliability
        - Entity length
        - Context
        """
        # Base confidence by entity type
        confidence_map = {
            "PERSON": 0.85,
            "ORG": 0.85,
            "GPE": 0.90,  # Geopolitical entity
            "MONEY": 0.95,
            "DATE": 0.90,
            "TIME": 0.90,
            "CARDINAL": 0.80,
            "EMAIL": 0.95,
            "PHONE": 0.95,
            "ACCOUNT_NUMBER": 0.90,
            "TRANSACTION_ID": 0.95
        }

        base_confidence = confidence_map.get(ent.label_, 0.75)

        # Adjust based on length (longer entities tend to be more reliable)
        if len(ent.text) > 15:
            base_confidence = min(0.99, base_confidence + 0.05)
        elif len(ent.text) < 3:
            base_confidence = max(0.60, base_confidence - 0.10)

        return base_confidence

    def _deduplicate_entities(self, entities: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Remove duplicate/overlapping entities, keeping the most confident ones
        """
        if not entities:
            return []

        # Sort by confidence (descending) then by position
        sorted_entities = sorted(
            entities,
            key=lambda x: (-x.get("confidence", 0), x["start"])
        )

        deduplicated = []
        used_spans = set()

        for entity in sorted_entities:
            span = (entity["start"], entity["end"])

            # Check if this span overlaps with any already used span
            overlaps = False
            for used_start, used_end in used_spans:
                if not (span[1] <= used_start or span[0] >= used_end):
                    overlaps = True
                    break

            if not overlaps:
                deduplicated.append(entity)
                used_spans.add(span)

        return deduplicated

    def extract_slot_values(
        self,
        text: str,
        required_slots: List[str],
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Extract specific slot values from text

        Args:
            text: Input text
            required_slots: List of slot names to extract
            context: Conversation context

        Returns:
            Dictionary of slot_name -> value
        """
        entities = self.extract(text, context)
        slots = {}

        # Map entity types to slots
        entity_to_slot_mapping = {
            "amount": ["MONEY", "AMOUNT", "CARDINAL"],
            "account_type": ["ACCOUNT_TYPE"],
            "account_number": ["ACCOUNT_NUMBER", "CARDINAL"],
            "date": ["DATE"],
            "time": ["TIME"],
            "person": ["PERSON"],
            "organization": ["ORG"],
            "location": ["GPE", "LOC"],
            "email": ["EMAIL"],
            "phone": ["PHONE"],
            "card_type": ["CARD_TYPE"],
            "product": ["PRODUCT"]
        }

        for slot_name in required_slots:
            # Find entities that match this slot
            matching_entity_types = entity_to_slot_mapping.get(slot_name, [slot_name.upper()])

            for entity in entities:
                if entity["entity_type"] in matching_entity_types:
                    # Use parsed value if available, otherwise raw value
                    slots[slot_name] = entity.get("parsed_value", entity["value"])
                    break

        return slots
