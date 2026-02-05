import logging
import json
from ml.kg_schemas import ExtractionResult
from ml.kg_utils import get_connector

logger = logging.getLogger("kg_ingestion")

def ingest_graph(extraction: ExtractionResult, model_version: str = "unknown"):
    """
    Ingests the validated MLOps extraction result into Neo4j.
    """
    connector = get_connector()
    
    # 1. Ingest Nodes
    logger.info("Ingesting nodes...")
    
    # Models
    model_query = """
    UNWIND $batch AS mapped
    MERGE (m:Model {id: mapped.id})
    SET m.name = mapped.name,
        m.version = mapped.version,
        m.framework = mapped.framework,
        m.description = mapped.description,
        m.last_updated = datetime()
    """
    models_data = [d.dict() for d in extraction.models]
    if models_data:
        connector.run_query(model_query, {"batch": models_data})

    # Experiments
    experiment_query = """
    UNWIND $batch AS mapped
    MERGE (e:Experiment {id: mapped.id})
    SET e.name = mapped.name,
        e.status = mapped.status,
        e.created_at = datetime()
    """
    experiments_data = [e.dict() for e in extraction.experiments]
    if experiments_data:
        connector.run_query(experiment_query, {"batch": experiments_data})
        
    # Runs
    # Metrics and Parameters are stored as JSON strings or properties
    run_query = """
    UNWIND $batch AS mapped
    MERGE (r:Run {id: mapped.id})
    SET r.name = mapped.name,
        r.status = mapped.status,
        r.metrics = mapped.metrics,  
        r.parameters = mapped.parameters
    """
    # Note: Neo4j can store maps directly if using APOC, but standard cypher handles simple maps or needs serialization.
    # For now we assume standard driver map support.
    runs_data = [r.dict() for r in extraction.runs]
    if runs_data:
        connector.run_query(run_query, {"batch": runs_data})
        
    # Deployments
    deployment_query = """
    UNWIND $batch AS mapped
    MERGE (d:Deployment {id: mapped.id})
    SET d.name = mapped.name,
        d.cluster = mapped.cluster,
        d.image = mapped.image,
        d.replicas = mapped.replicas
    """
    deployments_data = [d.dict() for d in extraction.deployments]
    if deployments_data:
        connector.run_query(deployment_query, {"batch": deployments_data})

    # 2. Ingest Relationships
    logger.info("Ingesting relationships...")
    
    for rel in extraction.relationships:
        query = f"""
        MATCH (s {{id: $source_id}}), (t {{id: $target_id}})
        MERGE (s)-[r:{rel.type}]->(t)
        SET r += $props,
            r.ingested_at = datetime()
        """
        connector.run_query(query, {
            "source_id": rel.source_id,
            "target_id": rel.target_id,
            "props": rel.properties
        })
    
    logger.info("Ingestion complete.")
    connector.close()

