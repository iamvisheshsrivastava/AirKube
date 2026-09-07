import os
import time
import logging
from typing import List, Optional

import ddtrace
from ddtrace import tracer
from ddtrace.contrib.asgi import TraceMiddleware
import ddtrace.auto  # noqa: F401 — auto-instruments requests, logging, etc.

from fastapi import Depends, FastAPI, HTTPException, Request, Security
from fastapi.responses import JSONResponse
from fastapi.security import APIKeyHeader

from ml.model import predict
from ml.schemas import PredictionInput, PredictionOutput, BatchPredictionInput, BatchPredictionOutput

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("ml_service")

app = FastAPI(title="AirKube Inference Service")
# Service name is set via DD_SERVICE (see .env.example) rather than passed
# as a `service=` kwarg here: ddtrace 3.x removed that kwarg from
# TraceMiddleware.__init__, which made this call raise TypeError on any
# fresh install pulling ddtrace>=3 (requirements.txt has no upper bound).
os.environ.setdefault("DD_SERVICE", "airkube-api")
app.add_middleware(TraceMiddleware)

# ---------------------------------------------------------
# Optional shared-secret authentication
# ---------------------------------------------------------
# API_KEY is read once at process startup. When it is unset (the default for
# the public demo deployment), auth is disabled and every request is allowed
# through exactly as before this change. When it IS set (e.g. in a
# non-demo/production deployment), callers must send a matching `X-API-Key`
# header on the protected routes below, or they get a 401.
#
# No real key value is ever hardcoded here — it is only ever read from the
# environment via os.getenv().
API_KEY = os.getenv("API_KEY")

_api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


def require_api_key(provided_key: Optional[str] = Security(_api_key_header)) -> None:
    """FastAPI dependency enforcing the optional shared API key.

    - If API_KEY is not configured in the environment, this is a no-op
      (fully open, matching current/legacy behavior).
    - If API_KEY is configured, the request must include a matching
      `X-API-Key` header, otherwise a 401 is raised.
    """
    if API_KEY is None:
        return
    if provided_key != API_KEY:
        raise HTTPException(status_code=401, detail="Missing or invalid API key")


@app.get("/health")
def health_check():
    return {"status": "healthy", "service": "ml-inference"}

@app.post("/predict", response_model=PredictionOutput, dependencies=[Depends(require_api_key)])
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

@app.post("/batch-predict", response_model=BatchPredictionOutput, dependencies=[Depends(require_api_key)])
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

@app.get("/model/{name}/details", dependencies=[Depends(require_api_key)])
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

@app.get("/deployment/{deployment_id}/status", dependencies=[Depends(require_api_key)])
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
