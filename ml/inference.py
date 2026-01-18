import time
import logging
from typing import List

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST

from ml.model import predict
from ml.schemas import PredictionInput, PredictionOutput, BatchPredictionInput, BatchPredictionOutput

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
    method = request.method
    endpoint = request.url.path
    
    start_time = time.time()
    
    try:
        response = await call_next(request)
        status_code = response.status_code
        REQUEST_COUNT.labels(method=method, endpoint=endpoint, status=status_code).inc()
        return response
    except Exception as e:
        REQUEST_COUNT.labels(method=method, endpoint=endpoint, status=500).inc()
        raise e
    finally:
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
        # Simulate processing logic
        result_dict = predict(input_data.data)
        result_value = result_dict.get("result")
        
        if result_value is None:
             raise ValueError("Model returned no result")

        return PredictionOutput(result=result_value, model_version="v2.1")
        
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
            results.append(PredictionOutput(result=res["result"], model_version="v2.1"))
            
        return BatchPredictionOutput(
            results=results,
            processed_count=len(results)
        )
    except Exception as e:
        logger.error(f"Batch prediction failed: {e}")
        MODEL_PREDICTION_ERROR.inc()
        raise HTTPException(status_code=500, detail="Batch processing failed")
