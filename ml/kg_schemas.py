from typing import List, Optional
from pydantic import BaseModel, Field

class Entity(BaseModel):
    id: str = Field(..., description="Unique slugified ID")
    name: str
    type: str

class Disease(Entity):
    type: str = "Disease"
    confidence_score: float = Field(..., ge=0.0, le=1.0)
    source_text: Optional[str] = None

class Symptom(Entity):
    type: str = "Symptom"
    severity: Optional[str] = None

class Drug(Entity):
    type: str = "Drug"

class Anatomy(Entity):
    type: str = "Anatomy"

class LearningObjective(Entity):
    type: str = "LearningObjective"
    taxonomy_level: Optional[str] = "Bloom's Taxonomy Level"

class Relationship(BaseModel):
    source_id: str
    target_id: str
    type: str = Field(..., description="Relationship type e.g., HAS_SYMPTOM")
    properties: dict = Field(default_factory=dict)
    confidence: float = 1.0

class ExtractionResult(BaseModel):
    diseases: List[Disease] = []
    symptoms: List[Symptom] = []
    drugs: List[Drug] = []
    anatomy: List[Anatomy] = []
    learning_objectives: List[LearningObjective] = []
    relationships: List[Relationship] = []

class ValidationResult(BaseModel):
    is_valid: bool
    reasoning: str
    corrected_data: Optional[dict] = None
