import json
import re
import sqlite3
from datetime import datetime
from pathlib import Path


class EvaluationStore:
    def __init__(self, db_path=None):
        base_dir = Path(__file__).resolve().parent
        self.db_path = Path(db_path) if db_path else base_dir.parent / "app_data.db"
        self._ensure_tables()

    def _connect(self):
        return sqlite3.connect(self.db_path)

    def _ensure_tables(self):
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS evaluation_runs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    created_at TEXT NOT NULL,
                    source_url TEXT NOT NULL,
                    job_title TEXT NOT NULL,
                    extraction_score REAL NOT NULL,
                    relevance_score REAL NOT NULL,
                    email_score REAL NOT NULL,
                    overall_score REAL NOT NULL,
                    evaluation_json TEXT NOT NULL
                )
                """
            )

    def save_evaluation(self, source_url, job_title, evaluation):
        payload = json.dumps(evaluation, ensure_ascii=True)
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO evaluation_runs (
                    created_at,
                    source_url,
                    job_title,
                    extraction_score,
                    relevance_score,
                    email_score,
                    overall_score,
                    evaluation_json
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    datetime.utcnow().isoformat(timespec="seconds"),
                    source_url,
                    job_title,
                    evaluation["extraction"]["score"],
                    evaluation["relevance"]["score"],
                    evaluation["email_usefulness"]["score"],
                    evaluation["overall_score"],
                    payload,
                ),
            )

    def get_recent_evaluations(self, limit=10):
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT created_at, source_url, job_title, overall_score
                FROM evaluation_runs
                ORDER BY id DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()
        return [
            {
                "created_at": row[0],
                "source_url": row[1],
                "job_title": row[2],
                "overall_score": row[3],
            }
            for row in rows
        ]


class Evaluator:
    CALL_TO_ACTION_PATTERNS = (
        "schedule",
        "connect",
        "call",
        "discussion",
        "meeting",
        "explore",
        "conversation",
    )

    CONTRACT_TERMS = (
        "contract",
        "flexible",
        "onboard",
        "hiring",
        "scale",
        "managed delivery",
        "staffing",
    )

    def evaluate(self, job, matches, email):
        extraction = self._score_extraction(job)
        relevance = self._score_relevance(job, matches)
        email_usefulness = self._score_email(job, matches, email)
        overall = round(
            (extraction["score"] + relevance["score"] + email_usefulness["score"]) / 3,
            1,
        )
        return {
            "extraction": extraction,
            "relevance": relevance,
            "email_usefulness": email_usefulness,
            "overall_score": overall,
        }

    def _score_extraction(self, job):
        role_present = bool(job.get("role"))
        description_present = len(job.get("description", "").split()) >= 20
        skills = job.get("skills") or []
        enough_skills = len(skills) >= 2
        experience_present = bool(job.get("experience"))

        passed = sum([role_present, description_present, enough_skills, experience_present])
        score = round((passed / 4) * 100, 1)
        feedback = []
        if not role_present:
            feedback.append("Role title is missing.")
        if not description_present:
            feedback.append("Job description is too short for reliable extraction.")
        if not enough_skills:
            feedback.append("Very few skills were extracted.")
        if not experience_present:
            feedback.append("Experience details are missing.")
        if not feedback:
            feedback.append("Extraction includes the main fields needed for email generation.")

        return {"score": score, "feedback": feedback}

    def _score_relevance(self, job, matches):
        skills = {skill.lower() for skill in (job.get("skills") or []) if str(skill).strip()}
        if not matches:
            return {"score": 0.0, "feedback": ["No portfolio links were matched to this job."]}

        overlap_scores = []
        feedback = []
        for match in matches:
            techstack = {
                item.strip().lower()
                for item in str(match.get("techstack", "")).split(",")
                if item.strip()
            }
            overlap = skills & techstack
            ratio = len(overlap) / max(len(skills), 1)
            overlap_scores.append(ratio)
            if overlap:
                feedback.append(
                    f"{match.get('link', 'Portfolio link')} matches: {', '.join(sorted(overlap))}."
                )

        if not feedback:
            feedback.append("Portfolio links were found, but skill overlap looks weak.")

        score = round((sum(overlap_scores) / len(overlap_scores)) * 100, 1)
        return {"score": score, "feedback": feedback}

    def _score_email(self, job, matches, email):
        lowered_email = email.lower()
        skills = [skill.lower() for skill in (job.get("skills") or [])]
        skill_hits = sum(1 for skill in skills if skill and skill in lowered_email)
        skill_score = min(skill_hits / max(len(skills), 1), 1.0)

        role_score = 1.0 if job.get("role", "").lower() in lowered_email else 0.0
        cta_score = 1.0 if any(term in lowered_email for term in self.CALL_TO_ACTION_PATTERNS) else 0.0
        contract_score = 1.0 if any(term in lowered_email for term in self.CONTRACT_TERMS) else 0.0
        links = [match.get("link", "") for match in matches]
        link_score = 1.0 if any(link.lower() in lowered_email for link in links if link) else 0.0

        word_count = len(re.findall(r"\w+", email))
        length_score = 1.0 if 80 <= word_count <= 220 else 0.5

        raw_score = (
            role_score
            + skill_score
            + cta_score
            + contract_score
            + link_score
            + length_score
        ) / 6
        score = round(raw_score * 100, 1)

        feedback = []
        if role_score:
            feedback.append("Email mentions the target role.")
        else:
            feedback.append("Email does not clearly mention the target role.")
        if cta_score:
            feedback.append("Email includes a call to action.")
        else:
            feedback.append("Email is missing a clear call to action.")
        if contract_score:
            feedback.append("Email communicates the contract-based engagement model.")
        else:
            feedback.append("Email should emphasize the contract staffing value proposition more clearly.")
        if not link_score:
            feedback.append("Email does not explicitly reference a portfolio link.")

        return {"score": score, "feedback": feedback}
