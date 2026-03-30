import os
import re
import time
from pathlib import Path
from urllib.parse import urlparse

from langchain_groq import ChatGroq
from dotenv import load_dotenv
from langchain_core.exceptions import OutputParserException
from langchain_core.output_parsers import JsonOutputParser
from langchain_core.prompts import PromptTemplate

BASE_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = BASE_DIR.parent

load_dotenv(PROJECT_ROOT / ".env")
load_dotenv(BASE_DIR / ".env")

class Chain:
    def __init__(self):
        groq_api_key = os.getenv("GROQ_API_KEY")
        if not groq_api_key:
            raise ValueError(
                "Missing GROQ_API_KEY. Add it to a .env file in the project root or in the app folder."
            )

        primary_model = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
        fallback_models = [
            model.strip()
            for model in os.getenv(
                "GROQ_FALLBACK_MODELS",
                "openai/gpt-oss-20b,llama-3.1-8b-instant",
            ).split(",")
            if model.strip()
        ]
        self.model_candidates = [primary_model]
        for model in fallback_models:
            if model not in self.model_candidates:
                self.model_candidates.append(model)

        self.llms = {
            model_name: ChatGroq(
                temperature=0,
                groq_api_key=groq_api_key,
                model_name=model_name,
            )
            for model_name in self.model_candidates
        }

    def extract_jobs(self, cleaned_text, source_url=""):
        prompt_extract = PromptTemplate.from_template(
            """
            ### SOURCE URL:
            {source_url}
            ### SCRAPED TEXT FROM WEBSITE:
            {page_data}
            ### INSTRUCTION:
            The scraped text is from a public careers page, job listing page, or individual job page.
            Extract all clear job postings you can identify from the page.
            Return JSON using this structure:
            [
              {{
                "role": "job title",
                "experience": "experience requirement if available",
                "skills": ["skill 1", "skill 2"],
                "description": "short job summary"
              }}
            ]
            If the page is a single job page, return a list with one job.
            If the page contains multiple jobs, return a list with multiple jobs.
            Do not invent jobs that are not clearly present on the page.
            Only return the valid JSON.
            ### VALID JSON (NO PREAMBLE):
            """
        )
        res = self._invoke_with_fallback(
            prompt_extract,
            {"page_data": cleaned_text, "source_url": source_url},
        )
        try:
            json_parser = JsonOutputParser()
            res = json_parser.parse(res.content)
        except OutputParserException as exc:
            raise OutputParserException(
                "Unable to parse jobs from the page. Try a cleaner careers page URL or a shorter listing page."
            ) from exc
        jobs = res if isinstance(res, list) else [res]
        normalized_jobs = []
        for job in jobs:
            normalized_job = self._normalize_job(job)
            if normalized_job:
                normalized_jobs.append(normalized_job)
        return normalized_jobs

    def write_mail(self, job, links, source_url=""):
        company_name = self._extract_company_name(source_url)
        prompt_email = PromptTemplate.from_template(
            """
            ### JOB DESCRIPTION:
            {job_description}

            ### SOURCE COMPANY:
            {company_name}

            ### INSTRUCTION:
            You are Mohan, a business development executive at AtliQ, an AI, software, and engineering services company.
            AtliQ works like a contract staffing and managed delivery partner for enterprise clients similar to TCS or Infosys.
            The client company is {company_name}.
            The client has an open job requirement. Your goal is to write a persuasive cold email to the hiring manager explaining that,
            instead of going through the full-time hiring process, they can quickly onboard experienced contract-based engineers or a delivery team from AtliQ.
            Emphasize these benefits when relevant:
            - faster hiring and onboarding
            - lower recruitment and training overhead
            - flexible contract-based engagement
            - ability to scale the team up or down based on project demand
            - strong delivery capability aligned to the job requirements
            Use the role, skills, and description from the job to make the email specific and relevant.
            Also add the most relevant items from the following portfolio links to showcase AtliQ's credibility: {link_list}
            Keep the email professional, concise, and business-focused.
            Remember you are Mohan, BDE at AtliQ.
            Do not provide a preamble.
            ### EMAIL (NO PREAMBLE):

            """
        )
        res = self._invoke_with_fallback(
            prompt_email,
            {
                "job_description": str(job),
                "link_list": links,
                "company_name": company_name,
            },
        )
        return res.content

    def _invoke_with_fallback(self, prompt, payload):
        last_exception = None

        for model_index, model_name in enumerate(self.model_candidates):
            llm = self.llms[model_name]
            chain = prompt | llm

            for attempt in range(3):
                try:
                    return chain.invoke(payload)
                except Exception as exc:
                    last_exception = exc
                    message = str(exc).lower()
                    is_retryable = any(
                        token in message
                        for token in ("503", "over capacity", "service unavailable", "rate limit", "429")
                    )
                    if not is_retryable:
                        raise

                    if attempt < 2:
                        time.sleep(2 ** attempt)
                        continue
                    break

            if model_index < len(self.model_candidates) - 1:
                time.sleep(1)

        raise RuntimeError(
            "Groq is temporarily overloaded for all configured models. Try again in a moment or switch the model in your .env file."
        ) from last_exception

    @staticmethod
    def _extract_company_name(source_url):
        if not source_url:
            return "the client"

        hostname = urlparse(source_url).netloc.lower()
        hostname = hostname.replace("www.", "")
        ignored_parts = {"com", "org", "net", "jobs", "careers", "career"}
        parts = [part for part in hostname.split(".") if part and part not in ignored_parts]
        if not parts:
            return "the client"

        company = parts[0].replace("-", " ").replace("_", " ").strip()
        if len(parts) > 1 and company in {"apply", "boards", "greenhouse", "lever"}:
            company = parts[1].replace("-", " ").replace("_", " ").strip()
        company = re.sub(r"\s+", " ", company)
        return company.title() if company else "the client"

    @staticmethod
    def _normalize_job(job):
        if job is None:
            return None

        if isinstance(job, str):
            return {
                "role": "Unknown Role",
                "experience": "",
                "skills": [],
                "description": job.strip(),
            }

        if not isinstance(job, dict):
            return {
                "role": "Unknown Role",
                "experience": "",
                "skills": [],
                "description": str(job),
            }

        skills = job.get("skills", [])
        if skills is None:
            normalized_skills = []
        elif isinstance(skills, str):
            normalized_skills = [item.strip() for item in skills.split(",") if item.strip()]
        elif isinstance(skills, (list, tuple, set)):
            normalized_skills = [str(item).strip() for item in skills if item and str(item).strip()]
        else:
            normalized_skills = [str(skills).strip()]

        return {
            "role": str(job.get("role") or "Unknown Role").strip(),
            "experience": str(job.get("experience") or "").strip(),
            "skills": normalized_skills,
            "description": str(job.get("description") or "").strip(),
        }

if __name__ == "__main__":
    print(os.getenv("GROQ_API_KEY"))
