"""Role profiles and the small role-specific question bank."""

from typing import Dict, List


ROLE_PROFILES: Dict[str, List[str]] = {
    "Frontend Developer": ["HTML", "CSS", "JavaScript", "TypeScript", "React", "React Hooks", "REST APIs", "Browser/Web fundamentals", "Git", "Testing", "Performance"],
    "Backend Developer": ["Python", "Java", "Node.js", "REST APIs", "Databases", "SQL", "Authentication & Authorization", "API design", "Backend architecture", "Caching", "Error handling", "Testing", "Git"],
    "Software Engineer": ["Programming fundamentals", "Data Structures", "Algorithms", "OOP", "Problem solving", "SQL", "Operating Systems", "Computer Networks", "DBMS", "System Design", "Git", "Testing"],
    "Data Analyst": ["Python", "SQL", "Excel", "Pandas", "NumPy", "Data Cleaning", "EDA", "Statistics", "Data Visualization", "Power BI/Tableau", "Business interpretation"],
    "Data Scientist": ["Python", "Pandas", "NumPy", "Statistics", "Probability", "SQL", "Machine Learning", "Feature Engineering", "Feature Selection", "Model Evaluation", "Data Preprocessing", "Data Visualization", "NLP basics"],
    "Machine Learning Engineer": ["Python", "Machine Learning", "Deep Learning", "Feature Engineering", "Model Evaluation", "Model Deployment", "APIs", "MLOps", "Docker", "Model Monitoring", "Data Pipelines", "Cloud/Deployment"],
}

ROLE_QUESTION_BANK = [
    ("Frontend Developer", "HTML", "How would you make a semantic HTML page accessible to keyboard and screen-reader users?", "Use meaningful landmarks and elements, labels, heading order, alt text, keyboard focus, and test with a screen reader.", "technical"),
    ("Frontend Developer", "React", "When would you move state up in a React application, and how would you avoid unnecessary re-renders?", "Lift shared state to the nearest common owner, keep state local where possible, and use stable boundaries and derived values carefully.", "technical"),
    ("Frontend Developer", "JavaScript", "Explain event bubbling and one practical use for event delegation.", "Events travel from the target toward ancestors; delegation attaches one handler to a stable parent and inspects the target.", "technical"),
    ("Backend Developer", "REST APIs", "Design an idempotent endpoint for updating a user's profile and describe its error handling.", "Use PUT with a stable resource URI, validate input, return appropriate 4xx errors, and make retries produce the same final state.", "technical"),
    ("Backend Developer", "Authentication & Authorization", "What is the difference between authentication and authorization in an API?", "Authentication establishes identity; authorization checks whether that identity may perform the requested action.", "technical"),
    ("Backend Developer", "Caching", "Where could you cache a read-heavy API response, and how would you handle invalidation?", "Use a bounded TTL cache at the service or edge, define cache keys, and invalidate on writes or accept a documented staleness window.", "technical"),
    ("Software Engineer", "System Design", "How would you approach designing a service that must handle traffic spikes gracefully?", "Define limits and SLOs, add stateless horizontal scaling, queues, caching, backpressure, observability, and failure recovery.", "technical"),
    ("Software Engineer", "Programming fundamentals", "Tell me about a difficult debugging problem and how you narrowed down its cause.", "Explain the hypothesis-driven process, evidence gathered, smallest reproduction, fix, and regression test.", "behavioral"),
    ("Software Engineer", "Data Structures", "How would you choose between a hash map and a balanced search tree for lookups?", "A hash map usually gives average constant-time lookup without ordering; a balanced tree gives logarithmic lookup and sorted traversal.", "technical"),
    ("Data Analyst", "SQL", "How would you find customers whose latest order was within the last 30 days?", "Use a window function or grouped MAX order date, then filter the resulting latest date against the 30-day boundary.", "technical"),
    ("Data Analyst", "Data Cleaning", "How do you decide whether an outlier is an error or a meaningful business signal?", "Check provenance and collection rules, compare with domain expectations, segment the data, and document whether it is corrected, excluded, or retained.", "technical"),
    ("Data Analyst", "Business interpretation", "Describe how you would communicate a surprising dashboard result to a non-technical stakeholder.", "Lead with the business impact, explain the evidence and uncertainty plainly, check definitions, and propose a focused next action.", "behavioral"),
    ("Data Scientist", "Machine Learning", "How would you detect and prevent target leakage during model development?", "Define the prediction timestamp, audit feature availability, split data temporally when appropriate, and build leakage checks into validation.", "technical"),
    ("Data Scientist", "Model Evaluation", "Which evaluation choices change when the positive class is rare?", "Accuracy becomes weak evidence; inspect precision, recall, PR-AUC, calibration, and choose a threshold based on business costs.", "technical"),
    ("Data Scientist", "Communication", "How would you explain model uncertainty to a product stakeholder?", "Use a concrete prediction interval or probability example, explain calibration and limits, and connect uncertainty to the decision threshold.", "behavioral"),
    ("Machine Learning Engineer", "Model Deployment", "What checks belong in a production model deployment pipeline?", "Validate the artifact and schema, run offline and integration tests, scan dependencies, use a staged rollout, and keep rollback and monitoring ready.", "technical"),
    ("Machine Learning Engineer", "MLOps", "What would you monitor after deploying a machine learning model?", "Track service health, data and concept drift, prediction quality when labels arrive, latency, cost, and alert thresholds tied to action.", "technical"),
    ("Machine Learning Engineer", "Data Pipelines", "How would you make a training data pipeline reproducible?", "Version code, data references, schemas, transformations, and environment; record lineage and deterministic configuration for each run.", "technical"),
]


def get_role_skills(role: str) -> List[str]:
    return ROLE_PROFILES.get(role, ROLE_PROFILES["Software Engineer"])


def get_role_questions(role: str, interview_type: str = "Technical") -> List[dict]:
    mode = interview_type.lower()
    questions = [
        {"role": item[0], "skill": item[1], "question": item[2], "ideal_answer": item[3], "style": item[4]}
        for item in ROLE_QUESTION_BANK
        if item[0] == role and (mode == "mixed" or item[4] == mode or (mode == "technical" and item[4] == "technical"))
    ]
    return questions