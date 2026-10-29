import sys
import os
from unittest.mock import MagicMock

sys.path.append(os.getcwd())

import pytest
from ml import kg_ingestion
from ml.kg_schemas import ExtractionResult, Relationship


@pytest.mark.parametrize("bad", [
    "FOO}] DETACH DELETE t //", "belongs_to", "BELONGS_TO`", "", "UNKNOWN", "A B",
])
def test_safe_rel_type_rejects(bad):
    with pytest.raises(ValueError):
        kg_ingestion.safe_rel_type(bad)


def test_safe_rel_type_accepts_and_escapes():
    assert kg_ingestion.safe_rel_type("SERVES") == "`SERVES`"


def test_ingest_skips_injected_relationship(monkeypatch):
    conn = MagicMock()
    monkeypatch.setattr(kg_ingestion, "get_connector", lambda: conn)
    result = ExtractionResult(relationships=[
        Relationship(source_id="a", target_id="b", type="FOO}] DETACH DELETE t //"),
        Relationship(source_id="a", target_id="b", type="SERVES"),
    ])
    kg_ingestion.ingest_graph(result)
    queries = [c.args[0] for c in conn.run_write_query.call_args_list]
    assert len(queries) == 1
    assert "`SERVES`" in queries[0]
    assert not any("DETACH" in q for q in queries)


@pytest.mark.parametrize("rel_type,src_label,tgt_label", [
    ("BELONGS_TO", "Run", "Experiment"),
    ("PRODUCED_BY", "Model", "Run"),
    ("SERVES", "Deployment", "Model"),
])
def test_ingest_relationship_scopes_match_by_label(monkeypatch, rel_type, src_label, tgt_label):
    """
    Regression test for #16: the MATCH for each relationship type must be
    scoped by the expected source/target labels, not a bare {id: ...} match
    that could span every node type sharing that id.
    """
    conn = MagicMock()
    monkeypatch.setattr(kg_ingestion, "get_connector", lambda: conn)
    result = ExtractionResult(relationships=[
        Relationship(source_id="a", target_id="b", type=rel_type),
    ])
    kg_ingestion.ingest_graph(result)
    queries = [c.args[0] for c in conn.run_write_query.call_args_list]
    assert len(queries) == 1
    query = queries[0]
    assert f"(s:{src_label} {{id: $source_id}})" in query
    assert f"(t:{tgt_label} {{id: $target_id}})" in query


def test_rel_type_labels_cover_all_allowed_types():
    """Every allowlisted relationship type must have a label mapping, or
    ingestion would silently skip valid relationships."""
    assert kg_ingestion.ALLOWED_REL_TYPES <= set(kg_ingestion.REL_TYPE_LABELS.keys())


# ── #13: record_deployment write-path helper ────────────────────────────────

def test_record_deployment_success(monkeypatch):
    conn = MagicMock()
    conn.run_write_query.return_value = [{"deployment_id": "resnet50_v2_prod", "model_id": "resnet50_v2"}]
    monkeypatch.setattr(kg_ingestion, "get_connector", lambda: conn)

    result = kg_ingestion.record_deployment("resnet50", "v2", "prod", "registry/resnet50:v2", 3)

    assert result == {"status": "ok", "deployment_id": "resnet50_v2_prod", "model_id": "resnet50_v2"}
    query, params = conn.run_write_query.call_args.args
    assert "MATCH (m:Model {name: $model_name, version: $model_version})" in query
    assert "MERGE (d:Deployment {id: $deployment_id})" in query
    assert "MERGE (d)-[r:SERVES]->(m)" in query
    assert params["model_name"] == "resnet50"
    assert params["model_version"] == "v2"
    assert params["cluster"] == "prod"
    assert params["image"] == "registry/resnet50:v2"
    assert params["replicas"] == 3
    conn.close.assert_called_once()


def test_record_deployment_missing_model_returns_error(monkeypatch):
    conn = MagicMock()
    conn.run_write_query.return_value = []  # MATCH found no Model
    monkeypatch.setattr(kg_ingestion, "get_connector", lambda: conn)

    result = kg_ingestion.record_deployment("ghost", "v1", "prod", "registry/ghost:v1", 1)

    assert result["status"] == "error"
    assert "ghost" in result["message"]
    conn.close.assert_called_once()


def test_slugify_produces_stable_lowercase_id():
    assert kg_ingestion._slugify("ResNet50", "v2", "prod") == "resnet50_v2_prod"
    assert kg_ingestion._slugify("My Model!!", "1.0") == "my_model_1_0"

# ── #24: ingest_graph connector cleanup ─────────────────────────────────────

def test_ingest_graph_closes_connector_on_success(monkeypatch):
    conn = MagicMock()
    monkeypatch.setattr(kg_ingestion, "get_connector", lambda: conn)

    result = ExtractionResult(relationships=[
        Relationship(source_id="a", target_id="b", type="SERVES"),
    ])

    kg_ingestion.ingest_graph(result)
    conn.close.assert_called_once()


def test_ingest_graph_closes_connector_on_write_error(monkeypatch):
    """Regression test for #24: connector.close() must run even if run_write_query raises."""
    conn = MagicMock()
    conn.run_write_query.side_effect = RuntimeError("Neo4j write error")
    monkeypatch.setattr(kg_ingestion, "get_connector", lambda: conn)

    result = ExtractionResult(relationships=[
        Relationship(source_id="a", target_id="b", type="SERVES"),
    ])

    with pytest.raises(RuntimeError, match="Neo4j write error"):
        kg_ingestion.ingest_graph(result)

    conn.close.assert_called_once()

