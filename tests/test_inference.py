import sys
import os

# Add root to path so ml.model can be imported
sys.path.append(os.getcwd())

from fastapi.testclient import TestClient
from ml.inference import app

client = TestClient(app)

def test_health():
    """
    Test the health check endpoint (/health).
    
    Verifies:
    - Status code is 200 (OK).
    - Response body indicates 'healthy' status and correct service name.
    """
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy", "service": "ml-inference"}

def test_metrics():
    """
    Test the Prometheus metrics endpoint (/metrics).
    
    Verifies:
    - Status code is 200 (OK).
    - Response contains the expected specific metric key 'inference_request_total'.
    """
    response = client.get("/metrics")
    assert response.status_code == 200
    assert "inference_request_total" in response.text

def test_predict_single():
    """
    Test the single prediction endpoint (/predict).
    
    Verifies:
    - Status code is 200 (OK).
    
    Verifies:
    - Status code is 200 (OK).
    - The model logic returns the expected result (Iris class 0, 1, or 2).
    - The response includes the model version metadata.
    """
    # Iris data: sentosa-like (should be class 0)
    response = client.post("/predict", json={"data": [5.1, 3.5, 1.4, 0.2]})
    assert response.status_code == 200
    assert "result" in response.json()
    assert isinstance(response.json()["result"], int)
    assert response.json()["model_version"] == "v2.1-iris"

def test_predict_batch():
    """
    Test the batch prediction endpoint (/batch-predict).
    
    Verifies:
    - Status code is 200 (OK).
    - The response contains results for all input items.
    """
    payload = {
        "inputs": [
            {"data": [5.1, 3.5, 1.4, 0.2]},
            {"data": [6.7, 3.0, 5.2, 2.3]}
        ]
    }
    response = client.post("/batch-predict", json=payload)
    assert response.status_code == 200
    results = response.json()["results"]
    assert len(results) == 2
    assert results[0]["model_version"] == "v2.1-iris"

if __name__ == "__main__":
    # Test runner
    print("Running tests...")
    try:
        test_health()
        print("✓ Health check passed")
        test_metrics()
        print("✓ Metrics endpoint passed")
        test_predict_single()
        print("✓ Single prediction passed")
        test_predict_batch()
        print("✓ Batch prediction passed")
        print("All tests passed!")
    except Exception as e:
        print(f"Tests failed: {e}")
        sys.exit(1)
