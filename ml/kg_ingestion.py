import logging
from ml.kg_schemas import ExtractionResult
from ml.kg_utils import get_connector

logger = logging.getLogger("kg_ingestion")

def ingest_graph(extraction: ExtractionResult, model_version: str):
    """
    Ingests the validated extraction result into Neo4j using idempotent MERGE queries.
    
    This function takes an ExtractionResult object containing structured entities (Diseases, 
    Symptoms, Drugs, etc.) and relationships, and persists them into a Neo4j graph database.
    
    Args:
        extraction (ExtractionResult): The Pydantic model containing extracted graph data.
        model_version (str): The version of the model that performed the extraction, used for provenance.
    """
    connector = get_connector()
    
    # 1. Ingest Nodes
    logger.info("Ingesting nodes...")
    
    # Parametrized Cypher for Diseases
    disease_query = """
    UNWIND $batch AS mapped
    MERGE (d:Disease {id: mapped.id})
    SET d.name = mapped.name,
        d.confidence_score = mapped.confidence_score,
        d.source_text = mapped.source_text,
        d.last_updated = datetime()
    """
    diseases_data = [d.dict() for d in extraction.diseases]
    if diseases_data:
        connector.run_query(disease_query, {"batch": diseases_data})

    # Symptoms
    # Query uses UNWIND to process batch insertions efficiently.
    # MERGE ensures nodes are created only if they don't exist (idempotency).
    symptom_query = """
    UNWIND $batch AS mapped
    MERGE (s:Symptom {id: mapped.id})
    SET s.name = mapped.name,
        s.severity = mapped.severity
    """
    symptoms_data = [s.dict() for s in extraction.symptoms]
    if symptoms_data:
        connector.run_query(symptom_query, {"batch": symptoms_data})
        
    # Drugs
    drug_query = """
    UNWIND $batch AS mapped
    MERGE (d:Drug {id: mapped.id})
    SET d.name = mapped.name
    """
    drugs_data = [d.dict() for d in extraction.drugs]
    if drugs_data:
        connector.run_query(drug_query, {"batch": drugs_data})
        
    # Anatomy
    anatomy_query = """
    UNWIND $batch AS mapped
    MERGE (a:Anatomy {id: mapped.id})
    SET a.name = mapped.name,
        a.system = mapped.system
    """
    anatomy_data = [a.dict() for a in extraction.anatomy]
    if anatomy_data:
        connector.run_query(anatomy_query, {"batch": anatomy_data})
        
    # Learning Objectives
    lo_query = """
    UNWIND $batch AS mapped
    MERGE (l:LearningObjective {id: mapped.id})
    SET l.text = mapped.text,
        l.taxonomy_level = mapped.taxonomy_level
    """
    lo_data = [l.dict() for l in extraction.learning_objectives]
    if lo_data:
        connector.run_query(lo_query, {"batch": lo_data})

    # 2. Ingest Relationships
    logger.info("Ingesting relationships...")
    
    # Generic relationship ingestion using APOC-style logic or explicit MATCH-MERGE
    # We iterate over relationships and construct a specific MERGE query for the relationship type.
    # Note: Dynamic construction of Cypher queries (f-strings) should typically be avoided for user input,
    # but here 'rel.type' comes from a controlled/trusted schema (ExtractionResult), reducing injection risk.
    # Standard parametrization is used for all property values.
    
    # Since Cypher can't assign dynamic types in MERGE easily without APOC:
    # We will loop in python or use specific queries for expected types.
    # Allowing dynamic types for extensibility here:
    
    for rel in extraction.relationships:
        query = f"""
        MATCH (s {{id: $source_id}}), (t {{id: $target_id}})
        MERGE (s)-[r:{rel.type}]->(t)
        SET r += $props,
            r.confidence = $confidence,
            r.extracted_by = $model,
            r.ingested_at = datetime()
        """
        connector.run_query(query, {
            "source_id": rel.source_id,
            "target_id": rel.target_id,
            "props": rel.properties,
            "confidence": rel.confidence,
            "model": model_version
        })
    
    logger.info("Ingestion complete.")
    connector.close()
