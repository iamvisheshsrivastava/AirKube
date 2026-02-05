import json
import logging
import time
from ml.kg_schemas import ExtractionResult

logger = logging.getLogger("kg_extractor")

# Prompt Templates
SYSTEM_PROMPT = """
You are a strict MLOps Knowledge Extraction Agent.
OBJECTIVE: Extract MLOps entities (Models, Experiments, Runs, Deployments) and relationships from the text below.
CONSTRAINTS:
1. Output MUST be valid JSON matching the ExtractionResult schema.
2. Only extract entities explicitly mentioned.
3. Map status to standard values (active, completed, failed) if possible.
"""

def extract_entities_from_text(text: str) -> ExtractionResult:
    """
    Simulates sending text to an LLM (e.g., GPT-4) and parsing the JSON response.
    """
    logger.info(f"Extracting knowledge from text segment ({len(text)} chars)...")
    
    # Simulate LLM processing latency
    time.sleep(1.5) 
    
    # MOCKED RESPONSE based on MLOps domain
    mock_json = {
        "models": [
            {"id": "resnet50_v2", "name": "ResNet50", "version": "v2.0", "framework": "PyTorch", "description": "Image classification model trained on ImageNet."}
        ],
        "experiments": [
            {"id": "exp_vision_001", "name": "Vision Upgrade 2024", "status": "active"}
        ],
        "runs": [
            {"id": "run_101", "name": "Run #101", "status": "completed", "metrics": {"accuracy": 0.92, "loss": 0.21}, "parameters": {"lr": 0.001, "batch_size": 32}}
        ],
        "deployments": [
            {"id": "dep_prod_vision", "name": "Production Vision API", "cluster": "us-east-k8s", "image": "resnet50:v2", "replicas": 3}
        ],
        "relationships": [
            {"source_id": "resnet50_v2", "target_id": "run_101", "type": "PRODUCED_BY"},
            {"source_id": "run_101", "target_id": "exp_vision_001", "type": "BELONGS_TO"},
            {"source_id": "dep_prod_vision", "target_id": "resnet50_v2", "type": "SERVES"}
        ]
    }
    
    # Parse into Pydantic model to basic validation
    try:
        # Note: The Pydantic model might require specific fields like 'created_at' which have defaults,
        # so this should pass if schema is correct.
        result = ExtractionResult(**mock_json)
        logger.info("Extraction successful and schema validated.")
        return result
    except Exception as e:
        logger.error(f"Failed to parse LLM output: {e}")
        # Log the mock json to see what failed
        logger.error(f"Mock JSON: {mock_json}")
        raise e
