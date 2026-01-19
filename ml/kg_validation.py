import logging
import random
from ml.kg_schemas import ExtractionResult, ValidationResult

logger = logging.getLogger("kg_validator")

def validate_extraction(extraction: ExtractionResult) -> ValidationResult:
    """
    Simulates a "Judge" LLM that reviews extracted triples for medical correctness.
    """
    logger.info("Validating extracted knowledge graph...")
    
    # In a real system, we iterate through relationships and ask an LLM to verify
    # For simulation, we'll implement a simple heuristic or random failure
    
    # Simulation: Fail if "Magic Potion" is found (hallucination test)
    for drug in extraction.drugs:
        if "magic" in drug.name.lower():
            logger.warning(f"Hallucination detected: {drug.name}")
            return ValidationResult(
                is_valid=False, 
                reasoning="Detected non-medical entity 'Magic Potion'.",
                corrected_data=None
            )

    # Simulation: 95% Pass Rate
    if random.random() < 0.95:
        return ValidationResult(
            is_valid=True, 
            reasoning="All entities and relationships appear medically plausible and consistent with source text."
        )
    else:
        # Simulate a subtle medical error
        return ValidationResult(
            is_valid=False,
            reasoning="Relationship mismatch: 'Aspirin' treats 'Myocardial Infarction', but dosage details (not shown) seem incorrect for this context.",
            corrected_data=None 
        )
