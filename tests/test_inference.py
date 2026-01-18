from fastapi.testclient import TestClient
from ml.inference import app
import sys
import os

# Add root to path so ml.model can be imported
sys.path.append(os.getcwd())

client = TestClient(app)

def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy", "service": "ml-inference"}

def test_metrics():
    response = client.get("/metrics")
    assert response.status_code == 200
    assert "inference_request_total" in response.text

def test_predict_single():
    response = client.post("/predict", json={"data": 5})
    assert response.status_code == 200
    assert response.json()["result"] == 10
    assert response.json()["model_version"] == "v2.1"

def test_predict_batch():
    payload = {
        "inputs": [
            {"data": 2},
            {"data": 3}
        ]
    }
    response = client.post("/batch-predict", json=payload)
    assert response.status_code == 200
    results = response.json()["results"]
    assert len(results) == 2
    assert results[0]["result"] == 4
    assert results[1]["result"] == 6

if __name__ == "__main__":
    # Simple runner if pytest is not available
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
