from pydantic import BaseModel, Field
from typing import List, Optional

class PredictionInput(BaseModel):
    data: int = Field(..., description="Input data for prediction")

class PredictionOutput(BaseModel):
    result: int
    model_version: str = "v1"

class BatchPredictionInput(BaseModel):
    inputs: List[PredictionInput]

class BatchPredictionOutput(BaseModel):
    results: List[PredictionOutput]
    processed_count: int
