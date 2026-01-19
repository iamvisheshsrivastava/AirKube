import os
import logging
import time

logger = logging.getLogger("kg_utils")

# Try to import Neo4j, but handle environment where it's not installed yet
try:
    from neo4j import GraphDatabase
    NEO4J_AVAILABLE = True
except ImportError:
    NEO4J_AVAILABLE = False
    logger.warning("neo4j library not found. KG operations will be simulated.")

NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "password")

class Neo4jConnector:
    def __init__(self):
        self.driver = None
        if NEO4J_AVAILABLE:
            try:
                self.driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
            except Exception as e:
                logger.error(f"Failed to connect to Neo4j: {e}")
    
    def close(self):
        if self.driver:
            self.driver.close()
            
    def run_query(self, query, parameters=None):
        if not self.driver:
            logger.info(f"[SIMULATION] Executing Cypher:\n{query}\nParams: {parameters}")
            return []
            
        with self.driver.session() as session:
            result = session.run(query, parameters)
            return [record.data() for record in result]

def get_connector():
    return Neo4jConnector()
