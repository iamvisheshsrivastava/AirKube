import os
import logging
import time
from ml.env import load_env

load_env()

logger = logging.getLogger("kg_utils")

# Try to import Neo4j, but handle environment where it's not installed yet
try:
    import neo4j
    from neo4j import GraphDatabase
    NEO4J_AVAILABLE = True
except ImportError:
    NEO4J_AVAILABLE = False
    logger.warning("neo4j library not found. KG operations will be simulated.")

NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "")

class Neo4jConnector:
    """
    Wrapper for Neo4j database connection.
    
    If the 'neo4j' python package is not installed or connection fails, 
    this class gracefully degrades to a 'Simulation Mode', logging queries 
    instead of executing them.
    """
    def __init__(self):
        self.driver = None
        if NEO4J_AVAILABLE:
            try:
                if not NEO4J_PASSWORD:
                    logger.warning("NEO4J_PASSWORD not set. KG operations will be simulated.")
                    return
                self.driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
            except Exception as e:
                logger.error(f"Failed to connect to Neo4j: {e}")
    
    def close(self):
        if self.driver:
            self.driver.close()
            
    def run_query(self, query, parameters=None):
        """
        Executes a Cypher query in a READ-ONLY transaction.

        This is the only query path exposed to the agent's `query_knowledge_graph`
        tool and the dashboard's KG Explorer, both of which may receive arbitrary
        (including attacker/prompt-injected) Cypher text. Using
        `session.execute_read` puts Neo4j's driver-level read-only transaction
        function in front of the query, which rejects write clauses
        (CREATE/MERGE/SET/DELETE/REMOVE/DROP, etc.) at the server/driver level
        rather than relying on string pattern matching. Callers that need to
        write to the graph (e.g. ingestion) must use `run_write_query` instead.
        """
        if not self.driver:
            logger.info(f"[SIMULATION] Executing read-only Cypher:\n{query}\nParams: {parameters}")
            return []

        def _read_tx(tx):
            result = tx.run(query, parameters)
            return [record.data() for record in result]

        with self.driver.session(default_access_mode=neo4j.READ_ACCESS) as session:
            return session.execute_read(_read_tx)

    def run_write_query(self, query, parameters=None):
        """
        Executes a Cypher query in a read-write transaction.

        This is reserved for trusted, code-defined write paths (e.g. the KG
        ingestion pipeline in `ml/kg_ingestion.py`). It must NEVER be used to
        execute Cypher text that originated from the LLM agent, chat input, or
        any other untrusted/user-controlled source.
        """
        if not self.driver:
            logger.info(f"[SIMULATION] Executing write Cypher:\n{query}\nParams: {parameters}")
            return []

        def _write_tx(tx):
            result = tx.run(query, parameters)
            return [record.data() for record in result]

        with self.driver.session(default_access_mode=neo4j.WRITE_ACCESS) as session:
            return session.execute_write(_write_tx)

def get_connector():
    return Neo4jConnector()
