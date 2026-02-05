import logging
import random
from ml.kg_schemas import ExtractionResult, ValidationResult

logger = logging.getLogger("kg_validator")

def validate_extraction(extraction: ExtractionResult) -> ValidationResult:
    """
    Simulates a "Judge" LLM that reviews extracted triples for MLOps correctness.
    """
    logger.info("Validating extracted knowledge graph...")
    
    # In a real system, we iterate through relationships and ask an LLM to verify
    # For simulation, we'll implement a simple heuristic or random failure
    
    # Simulation: Fail if "Flux Capacitor" is found (hallucination test)
    for model in extraction.models:
        if "flux capacitor" in model.name.lower():
            logger.warning(f"Hallucination detected: {model.name}")
            return ValidationResult(
                is_valid=False, 
                reasoning="Detected non-existent model architecture 'Flux Capacitor'.",
                corrected_data=None
            )

    # Simulation: 95% Pass Rate
    if random.random() < 0.95:
        return ValidationResult(
            is_valid=True, 
            reasoning="All entities and relationships appear technically plausible and consistent with source text."
        )
    else:
        # Simulate a subtle error
        return ValidationResult(
            is_valid=False,
            reasoning="Relationship mismatch: 'ResNet50' linked to incompatible framework version.",
            corrected_data=None 
        )
