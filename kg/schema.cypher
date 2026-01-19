// ------------------------------
// Constraints (Uniqueness)
// ------------------------------

CREATE CONSTRAINT disease_id IF NOT EXISTS 
FOR (d:Disease) REQUIRE d.id IS UNIQUE;

CREATE CONSTRAINT symptom_id IF NOT EXISTS 
FOR (s:Symptom) REQUIRE s.id IS UNIQUE;

CREATE CONSTRAINT drug_id IF NOT EXISTS 
FOR (d:Drug) REQUIRE d.id IS UNIQUE;

CREATE CONSTRAINT anatomy_id IF NOT EXISTS 
FOR (a:Anatomy) REQUIRE a.id IS UNIQUE;

CREATE CONSTRAINT lo_id IF NOT EXISTS 
FOR (l:LearningObjective) REQUIRE l.id IS UNIQUE;

CREATE CONSTRAINT exam_id IF NOT EXISTS 
FOR (e:Exam) REQUIRE e.id IS UNIQUE;

// ------------------------------
// Indexes (Performance)
// ------------------------------

CREATE INDEX disease_name_idx IF NOT EXISTS 
FOR (d:Disease) ON (d.name);

CREATE INDEX symptom_name_idx IF NOT EXISTS 
FOR (s:Symptom) ON (s.name);

CREATE INDEX lo_text_idx IF NOT EXISTS 
FOR (l:LearningObjective) ON (l.text);

// ------------------------------
// Fulltext Indexes (Search)
// ------------------------------

CREATE FULLTEXT INDEX disease_search IF NOT EXISTS 
FOR (n:Disease) ON EACH [n.name, n.description];
