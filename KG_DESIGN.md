# AirKube Knowledge Graph Design & Implementation

## Part 1: Knowledge Graph Schema (Neo4j)

### Schema Design
The schema is designed to map the medical curriculum by linking clinical entities (Diseases, Symptoms, Drugs) to pedagogical structures (Learning Objectives, Exams).

#### Nodes
*   `Disease` (`id`, `name`, `icd_code`, `source`, `confidence_score`)
*   `Symptom` (`id`, `name`, `severity_grade`)
*   `Drug` (`id`, `name`, `drug_class`)
*   `Anatomy` (`id`, `name`, `system`)
*   `LearningObjective` (`id`, `text`, `taxonomy_level`)
*   `Exam` (`id`, `name`, `year`)

#### Relationships
*   `(:Disease)-[:HAS_SYMPTOM {frequency: 'string', evidence: 'string'}]->(:Symptom)`
*   `(:Disease)-[:TREATED_WITH {line_of_therapy: 'int'}]->(:Drug)`
*   `(:Disease)-[:AFFECTS {mechanism: 'string'}]->(:Anatomy)`
*   `(:LearningObjective)-[:COVERS {depth: 'string'}]->(:Disease)`
*   `(:LearningObjective)-[:ASSESSED_IN {question_id: 'string'}]->(:Exam)`

### Cypher Constraints & Indexes
See `kg/schema.cypher` for the implementation.

---

## Part 2: LLM Extraction Prompts

### Extraction Prompt Template
```text
SYSTEM: You are a strict Medical Knowledge Extraction Agent.
OBJECTIVE: Extract medical entities and relationships from the text below into the specified JSON format.
CONSTRAINTS:
1. Output MUST be valid JSON.
2. Only extract entities explicitly mentioned or strongly implied.
3. Map Anatomy terms to standard SNOMED-CT regions if possible.
4. Confidence scores (0.0-1.0) must reflect source ambiguity.

JSON SCHEMA:
{
  "diseases": [{"id": "str", "name": "str", "confidence": float}],
  "symptoms": [{"id": "str", "name": "str"}],
  "relationships": [
    {"source_id": "str", "target_id": "str", "type": "HAS_SYMPTOM" | "TREATED_WITH", "properties": {}}
  ]
}

TEXT TO PROCESS:
{input_text}
```

---

## Part 4: Validation / Judge Loop

### Validator Prompt
```text
SYSTEM: You are a Senior Medical Editor and Logic Validator.
TASK: Review the following extracted Knowledge Graph triple.
TRIPLE: ({source_name}) -[{rel_type}]-> ({target_name})

CRITERIA:
1. Medical Plausibility: Is this relationship medically accurate?
2. Contextual Correctness: Does the source text support this?
3. Formatting: Are the names canonical (e.g., "Myocardial Infarction" vs "Heart Attack")?

OUTPUT FORMAT (JSON):
{
  "status": "PASS" | "FAIL" | "WARN",
  "reasoning": "string",
  "suggested_correction": "string | null"
}
```

---

## Part 5: Evaluation Framework

### Metrics
1.  **Extraction Precision**: `% of extracted triples marked PASS by Validator`.
2.  **Schema Compliance**: `% of output JSONs matching Pydantic models`.
3.  **Hallucination Rate**: `% of relationships not found in ground truth (if available) or rejected by Validator`.
4.  **Curriculum Coverage**: `(Count of Diseases linked to LearningObjectives) / (Total Diseases)`.

### MLflow Integration
*   Log `param`: `model_version` (e.g., gpt-4-turbo).
*   Log `metric`: `validation_pass_rate`.
*   Log `artifact`: `failed_validations.json` for manual review.

---

## Part 7: Resume Mapping

| Skill Area | Implementation / Architecture Feature |
| :--- | :--- |
| **Neo4j/Cypher Skills** | `kg/schema.cypher`: Defines constraints, indexes, and normalized schema. <br> `ml/kg_ingestion.py`: Demonstrates `MERGE` strategies, confident upserts, and provenance tracking properties. |
| **LLM/Prompt Engineering** | `ml/kg_extraction.py`: Shows strict JSON schema enforcement, few-shot prompting patterns, and system instructions for medical accuracy. |
| **Validation & Eval** | `ml/kg_validation.py`: Implements the "Judge" loop pattern to auto-reject hallucinations. <br> `dags/kg_pipeline.py`: Orchestrates the `Extract -> Validate -> Ingest` flow with metrics logging. |
| **Lecturio Requirements** | **Medical Domain Modeling**: Mapping Symptoms/Diseases/Exams. <br> **Production API**: `ml/inference.py` extensions for KG traversal. <br> **Educational Alignment**: Explicit `LearningObjective` entity modeling. |
