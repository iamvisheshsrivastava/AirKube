from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime

class Entity(BaseModel):
    id: str = Field(..., description="Unique slugified ID")
    name: str
    type: str
    created_at: datetime = Field(default_factory=datetime.now)

class Model(Entity):
    type: str = "Model"
    version: str
    framework: str = "pytorch"
    description: Optional[str] = None

class Experiment(Entity):
    type: str = "Experiment"
    status: str = "active"

class Run(Entity):
    type: str = "Run"
    status: str = "completed"
    metrics: Dict[str, float] = Field(default_factory=dict)
    parameters: Dict[str, Any] = Field(default_factory=dict)

class Deployment(Entity):
    type: str = "Deployment"
    cluster: str = "local-k8s"
    replicas: int = 1
    image: str

class Relationship(BaseModel):
    source_id: str
    target_id: str
    type: str = Field(..., description="Relationship type e.g., BELONGS_TO_EXPERIMENT")
    properties: dict = Field(default_factory=dict)

class ExtractionResult(BaseModel):
    models: List[Model] = []
    experiments: List[Experiment] = []
    runs: List[Run] = []
    deployments: List[Deployment] = []
    relationships: List[Relationship] = []

class ValidationResult(BaseModel):
    is_valid: bool
    reasoning: str
    corrected_data: Optional[dict] = None

