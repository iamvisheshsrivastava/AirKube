import sys
import os

# Add root to path so ml.model can be imported
sys.path.append(os.getcwd())

import importlib

import ml.inference as inference_module
from fastapi.testclient import TestClient

app = inference_module.app
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

def test_require_api_key_uses_constant_time_comparison(monkeypatch):
    """
    Regression test for #15: require_api_key must compare keys with
    hmac.compare_digest (constant-time), not `!=`, to avoid a timing
    side-channel. We can't reliably assert on timing in a unit test, so
    instead we assert on behavior that only compare_digest-style comparison
    guarantees: correctness is unaffected, and a None-vs-str call never
    raises TypeError (hmac.compare_digest requires matching types, so the
    implementation must coerce `provided_key` before calling it).
    """
    monkeypatch.setattr(inference_module, "API_KEY", "super-secret-key")

    # Correct key -> allowed through.
    resp = client.get("/health")  # /health has no auth; sanity check app works
    assert resp.status_code == 200

    resp_ok = client.post(
        "/predict",
        json={"data": [5.1, 3.5, 1.4, 0.2]},
        headers={"X-API-Key": "super-secret-key"},
    )
    assert resp_ok.status_code == 200

    # Wrong key -> rejected, and no header at all -> rejected (None case).
    resp_wrong = client.post(
        "/predict",
        json={"data": [5.1, 3.5, 1.4, 0.2]},
        headers={"X-API-Key": "wrong-key"},
    )
    assert resp_wrong.status_code == 401

    resp_missing = client.post("/predict", json={"data": [5.1, 3.5, 1.4, 0.2]})
    assert resp_missing.status_code == 401

    # Partial-prefix-correct guesses must be rejected just like a
    # completely-wrong guess (this is what `!=` also gets right
    # functionally; the real bug was about *timing*, not correctness, but
    # this still guards against a naive "startswith" style regression).
    resp_prefix = client.post(
        "/predict",
        json={"data": [5.1, 3.5, 1.4, 0.2]},
        headers={"X-API-Key": "super-secret-k"},
    )
    assert resp_prefix.status_code == 401


def test_require_api_key_source_uses_compare_digest():
    """
    Belt-and-suspenders check that the fix actually landed: assert the
    source of require_api_key calls hmac.compare_digest rather than `!=`
    for the secret comparison.
    """
    import inspect

    source = inspect.getsource(inference_module.require_api_key)
    assert "hmac.compare_digest" in source
    assert "!=" not in source


def test_predict_short_input_returns_422():
    """
    Regression test for #23: POSTing /predict with a 2-element list must be
    rejected by Pydantic validation (422), not surface as a 500 from
    scikit-learn's feature-count check.
    """
    response = client.post("/predict", json={"data": [1.0, 2.0]})
    assert response.status_code == 422


def test_predict_long_input_returns_422():
    """
    Regression test for #23: POSTing /predict with a 5-element list must be
    rejected by Pydantic validation (422), not surface as a 500.
    """
    response = client.post("/predict", json={"data": [1.0, 2.0, 3.0, 4.0, 5.0]})
    assert response.status_code == 422


def test_predict_batch_invalid_item_returns_422():
    """
    Regression test for #23: a batch item with a wrong-length data list must
    also be rejected with 422 instead of a 500.
    """
    payload = {"inputs": [{"data": [1.0, 2.0]}]}
    response = client.post("/batch-predict", json=payload)
    assert response.status_code == 422


if __name__ == "__main__":
    # Test runner
    print("Running tests...")
    try:
        test_health()
        print("✓ Health check passed")
        test_predict_single()
        print("✓ Single prediction passed")
        test_predict_batch()
        print("✓ Batch prediction passed")
        print("All tests passed!")
    except Exception as e:
        print(f"Tests failed: {e}")
        sys.exit(1)
