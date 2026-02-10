import time
import logging
from typing import List

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST

from ml.model import predict
from ml.schemas import PredictionInput, PredictionOutput, BatchPredictionInput, BatchPredictionOutput

"""
AirKube Inference Service

This module provides the FastAPI application for:
1. Model Inference: Serving real-time and batch predictions.
2. Observability: Exposing Prometheus metrics (request counts, latency) and health checks.
3. Knowledge Graph Access: Querying the Neo4j database for medical entity relationships.

It uses a middleware to auto-instrument all incoming HTTP requests for monitoring.
"""

# Configure Structured Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("ml_service")

app = FastAPI(title="AirKube Inference Service")

# Prometheus Metrics
REQUEST_COUNT = Counter(
    'inference_request_total', 
    'Total number of inference requests', 
    ['method', 'endpoint', 'status']
)

REQUEST_LATENCY = Histogram(
    'inference_request_latency_seconds', 
    'Latency of inference requests in seconds',
    ['endpoint']
)

MODEL_PREDICTION_ERROR = Counter(
    'model_prediction_errors_total',
    'Total number of errors during model prediction'
)

@app.middleware("http")
async def monitor_requests(request: Request, call_next):
    """
    Middleware to intercept, log, and time every request.
    
    - Captures request method and endpoint.
    - Measures execution time (latency).
    - Updates Prometheus counters (requests total) and histograms (latency).
    - Handles exceptions by incrementing 500 status counters appropriately.
    """
    method = request.method
    endpoint = request.url.path
    
    start_time = time.time()
    
    try:
        response = await call_next(request)
        
        # Access the route template if available (e.g., /disease/{name}/graph) to avoid high cardinality
        route = request.scope.get("route")
        if route:
            endpoint = route.path
            
        status_code = response.status_code
        REQUEST_COUNT.labels(method=method, endpoint=endpoint, status=status_code).inc()
        return response
    except Exception as e:
        REQUEST_COUNT.labels(method=method, endpoint=endpoint, status=500).inc()
        raise e
    finally:
        # Also update route for latency if possible (though scope might be updated after response)
        # Note: request.scope['route'] is only available after routing. 
        # For middleware, it's often available after call_next returns if the app matched it.
        if request.scope.get("route"):
             endpoint = request.scope["route"].path
             
        duration = time.time() - start_time
        REQUEST_LATENCY.labels(endpoint=endpoint).observe(duration)

@app.get("/health")
def health_check():
    """Health check endpoint for Kubernetes liveness/readiness probes."""
    return {"status": "healthy", "service": "ml-inference"}

@app.get("/metrics")
def metrics():
    """Expose Prometheus metrics."""
    return JSONResponse(
        content=generate_latest().decode('utf-8'),
        media_type=CONTENT_TYPE_LATEST
    )

@app.post("/predict", response_model=PredictionOutput)
def predict_single(input_data: PredictionInput):
    """Single inference endpoint."""
    logger.info(f"Received prediction request: {input_data.dict()}")
    
    try:
        # Real Model Logic
        result_dict = predict(input_data.data)
        result_value = result_dict.get("result")
        
        return PredictionOutput(result=result_value, model_version="v2.1-iris")
        
    except Exception as e:
        logger.error(f"Prediction failed: {e}")
        MODEL_PREDICTION_ERROR.inc()
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/batch-predict", response_model=BatchPredictionOutput)
def predict_batch(batch_input: BatchPredictionInput):
    """Batch inference endpoint."""
    logger.info(f"Received batch prediction request with {len(batch_input.inputs)} items")
    
    results = []
    
    try:
        for item in batch_input.inputs:
            res = predict(item.data)
            results.append(PredictionOutput(result=res["result"], model_version="v2.1-iris"))
            
        return BatchPredictionOutput(
            results=results,
            processed_count=len(results)
        )
    except Exception as e:
        logger.error(f"Batch prediction failed: {e}")
        MODEL_PREDICTION_ERROR.inc()
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
