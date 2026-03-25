import json
import logging
import os
from ml.env import load_env

load_env()

import google.generativeai as genai
from ml.kg_schemas import ExtractionResult

logger = logging.getLogger("kg_extractor")

# Prompt Templates
SYSTEM_PROMPT = """
You are a strict MLOps Knowledge Extraction Agent.
OBJECTIVE: Extract MLOps entities (Models, Experiments, Runs, Deployments) and relationships from the text provided by the user.

CONSTRAINTS:
1. Output MUST be valid JSON matching the schema below.
2. Only extract entities explicitly mentioned in the text.
3. Map status to standard values (active, completed, failed) if possible.
4. Ensure all IDs are unique slugified strings (e.g., "resnet50_v2").

SCHEMA:
{
    "models": [{"id": str, "name": str, "version": str, "framework": str, "description": str}],
    "experiments": [{"id": str, "name": str, "status": str}],
    "runs": [{"id": str, "name": str, "status": str, "metrics": {str: float}, "parameters": {str: any}}],
    "deployments": [{"id": str, "name": str, "cluster": str, "image": str, "replicas": int}],
    "relationships": [{"source_id": str, "target_id": str, "type": str}] # Types: BELONGS_TO, PRODUCED_BY, SERVES
}
"""

def extract_entities_from_text(text: str) -> ExtractionResult:
    """
    Uses Gemini to extract structured MLOps entities from unstructured text.
    """
    logger.info(f"Extracting knowledge from text segment ({len(text)} chars)...")
    
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        logger.warning("GEMINI_API_KEY not set. Returning mock data due to missing credentials.")
        return _get_mock_data()

    try:
        # Initialize LLM
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel(os.getenv("GEMINI_MODEL", "gemini-2.5-flash"))

        prompt = (
            f"{SYSTEM_PROMPT}\n\n"
            f"Text to extract from:\n{text}\n\n"
            "Return only valid JSON matching the schema."
        )
        response = model.generate_content(prompt)
        raw_text = getattr(response, "text", "") or str(response)
        logger.debug(f"LLM Raw Output: {raw_text}")

        cleaned_text = raw_text.strip()
        if cleaned_text.startswith("```"):
            cleaned_text = cleaned_text.strip("`")
            if cleaned_text.startswith("json"):
                cleaned_text = cleaned_text[4:].strip()

        result_dict = json.loads(cleaned_text)

        # Parse and Validate with Pydantic
        extraction = ExtractionResult(**result_dict)
        logger.info(f"Extraction successful: {len(extraction.models)} Models, {len(extraction.runs)} Runs found.")
        return extraction

    except Exception as e:
        logger.error(f"LLM Extraction failed: {e}")
        # Fallback to mock if LLM fails (e.g., rate limit, parsing error)
        logger.warning("Falling back to mock data.")
        return _get_mock_data()

def _get_mock_data() -> ExtractionResult:
    """
    Fallback mock data if LLM is unavailable.
    """
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
    return ExtractionResult(**mock_json)
