import sys
import os

# Add root to path so ml.model can be imported
sys.path.append(os.getcwd())

import importlib

import pytest

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


class _FakeKgConnector:
    """
    Minimal stand-in for ml.kg_utils.Neo4jConnector used by the KG-backed
    endpoints in ml.inference. Records every run_query call and whether
    close() was reached, so tests can assert both the HTTP contract and
    connector cleanup.
    """

    def __init__(self, result=None, error=None):
        self._result = result
        self._error = error
        self.run_query_calls = []
        self.closed = False

    def run_query(self, query, parameters=None):
        self.run_query_calls.append((query, parameters))
        if self._error is not None:
            raise self._error
        return self._result

    def close(self):
        self.closed = True


def _patch_kg_connector(monkeypatch, *, result=None, error=None):
    """Monkeypatch ml.inference.get_connector and return the fake instance."""
    connector = _FakeKgConnector(result=result, error=error)
    monkeypatch.setattr(inference_module, "get_connector", lambda: connector)
    return connector


def _assert_connector_used_and_closed(connector):
    assert connector.closed is True, "connector.close() must always run"
    assert len(connector.run_query_calls) == 1


# ---------------------------------------------------------
# KG-backed endpoint coverage: /model/{name}/details and
# /deployment/{deployment_id}/status (issue #25)
# ---------------------------------------------------------

@pytest.mark.parametrize(
    "url,identifier_key,identifier_value,response_key",
    [
        ("/model/iris-model/details", "model", "iris-model", "details"),
        ("/deployment/dep-42/status", "deployment_id", "dep-42", "status"),
    ],
)
def test_kg_endpoint_returns_200_with_expected_shape(
    monkeypatch, url, identifier_key, identifier_value, response_key
):
    """
    When the KG query returns rows, both endpoints answer 200 and echo the
    queried identifier plus the raw rows under their response key.
    """
    kg_rows = [{"m": {"name": "iris-model", "version": "v2.1"}, "r": {"run_id": "run-1"}}]
    connector = _patch_kg_connector(monkeypatch, result=kg_rows)

    response = client.get(url)

    assert response.status_code == 200
    body = response.json()
    assert body[identifier_key] == identifier_value
    assert body[response_key] == kg_rows
    _assert_connector_used_and_closed(connector)


@pytest.mark.parametrize(
    "url,expected_detail",
    [
        ("/model/ghost/details", "Model not found in Knowledge Graph"),
        ("/deployment/ghost/status", "Deployment not found"),
    ],
)
def test_kg_endpoint_returns_404_when_query_has_no_rows(monkeypatch, url, expected_detail):
    """
    An empty result set must surface as a clean 404, not as the generic 500
    produced when the HTTPException was swallowed by the except block.
    """
    connector = _patch_kg_connector(monkeypatch, result=[])

    response = client.get(url)

    assert response.status_code == 404
    assert response.json()["detail"] == expected_detail
    _assert_connector_used_and_closed(connector)


@pytest.mark.parametrize(
    "url",
    [
        "/model/iris-model/details",
        "/deployment/dep-42/status",
    ],
)
def test_kg_endpoint_returns_500_when_connector_raises(monkeypatch, url):
    """
    A connector failure (e.g. Neo4j unreachable) must still map to a 500 with
    the exception message, and close() must run even on that path.
    """
    connector = _patch_kg_connector(monkeypatch, error=RuntimeError("boom"))

    response = client.get(url)

    assert response.status_code == 500
    assert response.json()["detail"] == "boom"
    _assert_connector_used_and_closed(connector)


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
