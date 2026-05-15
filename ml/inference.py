import time
import logging
from typing import List

import ddtrace
from ddtrace import tracer
from ddtrace.contrib.asgi import TraceMiddleware
import ddtrace.auto  # noqa: F401 — auto-instruments requests, logging, etc.

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse

from ml.model import predict
from ml.schemas import PredictionInput, PredictionOutput, BatchPredictionInput, BatchPredictionOutput

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("ml_service")

app = FastAPI(title="AirKube Inference Service")
app.add_middleware(TraceMiddleware, service="airkube-api")

@app.get("/health")
def health_check():
    return {"status": "healthy", "service": "ml-inference"}

@app.post("/predict", response_model=PredictionOutput)
def predict_single(input_data: PredictionInput):
    logger.info(f"Received prediction request: {input_data.dict()}")
    with tracer.trace("ml.predict", service="airkube-api", resource="predict_single"):
        try:
            result_dict = predict(input_data.data)
            return PredictionOutput(result=result_dict.get("result"), model_version="v2.1-iris")
        except Exception as e:
            logger.error(f"Prediction failed: {e}")
            tracer.current_span().error = 1
            raise HTTPException(status_code=500, detail=str(e))

@app.post("/batch-predict", response_model=BatchPredictionOutput)
def predict_batch(batch_input: BatchPredictionInput):
    logger.info(f"Received batch prediction request with {len(batch_input.inputs)} items")
    with tracer.trace("ml.batch_predict", service="airkube-api", resource="predict_batch"):
        try:
            results = [
                PredictionOutput(result=predict(item.data)["result"], model_version="v2.1-iris")
                for item in batch_input.inputs
            ]
            return BatchPredictionOutput(results=results, processed_count=len(results))
        except Exception as e:
            logger.error(f"Batch prediction failed: {e}")
            tracer.current_span().error = 1
            raise HTTPException(status_code=500, detail="Batch processing failed")

# ---------------------------------------------------------
# Knowledge Graph API Endpoints (MLOps)
# ---------------------------------------------------------
from ml.kg_utils import get_connector

@app.get("/model/{name}/details")
def get_model_details(name: str):
    """
    Retrieve details for a specific model from the Knowledge Graph.
    """
    connector = get_connector()
    query = """
    MATCH (m:Model {name: $name})
    OPTIONAL MATCH (m)-[:PRODUCED_BY]->(r:Run)
    RETURN m, r
    """
    try:
        data = connector.run_query(query, {"name": name})
        if not data:
            raise HTTPException(status_code=404, detail="Model not found in Knowledge Graph")
        return {"model": name, "details": data}
    except Exception as e:
        logger.error(f"KG Query failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        connector.close()

@app.get("/deployment/{deployment_id}/status")
def get_deployment_status(deployment_id: str):
    """
    Check status of a deployment and its connected services.
    """
    connector = get_connector()
    query = """
    MATCH (d:Deployment {id: $id})-[:SERVES]->(m:Model)
    RETURN d, m
    """
    try:
        data = connector.run_query(query, {"id": deployment_id})
        if not data:
            raise HTTPException(status_code=404, detail="Deployment not found")
        return {"deployment_id": deployment_id, "status": data}
    except Exception as e:
        logger.error(f"KG Query failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        connector.close()
