import json
import logging
import time
from ml.kg_schemas import ExtractionResult

logger = logging.getLogger("kg_extractor")

# Prompt Templates
SYSTEM_PROMPT = """
You are a strict Medical Knowledge Extraction Agent.
OBJECTIVE: Extract medical entities and relationships from the text below into the specified JSON format.
CONSTRAINTS:
1. Output MUST be valid JSON.
2. Only extract entities explicitly mentioned or strongly implied.
3. Map Anatomy terms to standard SNOMED-CT regions if possible.
4. Confidence scores (0.0-1.0) must reflect source ambiguity.
"""

def extract_entities_from_text(text: str) -> ExtractionResult:
    """
    Simulates sending text to an LLM (e.g., GPT-4) and parsing the JSON response.
    
    In a real production scenario, this function would:
    1. Construct a message payload with the `SYSTEM_PROMPT` and user text.
    2. Call `openai.ChatCompletion.create()` (or equivalent).
    3. Handle retries for rate limits or malformed JSON.
    """
    logger.info(f"Extracting knowledge from text segment ({len(text)} chars)...")
    
    # Simulate LLM processing latency
    time.sleep(1.5) 
    
    # MOCKED RESPONSE based on likely input text
    # In production, this comes from: response.choices[0].message.content
    
    mock_json = {
        "diseases": [
            {"id": "myocardial_infarction", "name": "Myocardial Infarction", "confidence_score": 0.95, "source_text": text[:20]}
        ],
        "symptoms": [
            {"id": "chest_pain", "name": "Chest Pain", "severity_grade": "Severe"},
            {"id": "shortness_of_breath", "name": "Shortness of Breath", "severity_grade": "Moderate"}
        ],
        "drugs": [
            {"id": "aspirin", "name": "Aspirin", "drug_class": "Antiplatelet"}
        ],
        "anatomy": [
            {"id": "heart", "name": "Heart", "system": "Cardiovascular"}
        ],
        "learning_objectives": [
            {"id": "lo_mi_diagnosis", "text": "Diagnose acute myocardial infarction based on clinical presentation.", "taxonomy_level": "Analysis"}
        ],
        "relationships": [
            {"source_id": "myocardial_infarction", "target_id": "chest_pain", "type": "HAS_SYMPTOM", "properties": {"frequency": "High"}},
            {"source_id": "myocardial_infarction", "target_id": "aspirin", "type": "TREATED_WITH", "properties": {"line_of_therapy": 1}},
            {"source_id": "lo_mi_diagnosis", "target_id": "myocardial_infarction", "type": "COVERS"},
            {"source_id": "myocardial_infarction", "target_id": "heart", "type": "AFFECTS"}
        ]
    }
    
    # Parse into Pydantic model to basic validation
    try:
        result = ExtractionResult(**mock_json)
        logger.info("Extraction successful and schema validated.")
        return result
    except Exception as e:
        logger.error(f"Failed to parse LLM output: {e}")
        raise e
