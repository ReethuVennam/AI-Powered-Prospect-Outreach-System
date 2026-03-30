import os
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent

if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

os.environ.setdefault("USER_AGENT", "cold-mail-generator/1.0")

try:
    from .chains import Chain
    from .evaluation import EvaluationStore, Evaluator
    from .portfolio import Portfolio
    from .utils import clean_text
except ImportError:
    from chains import Chain
    from evaluation import EvaluationStore, Evaluator
    from portfolio import Portfolio
    from utils import clean_text

import streamlit as st
from langchain_community.document_loaders import WebBaseLoader


def inject_styles():
    st.markdown(
        """
        <style>
            :root {
                --bg: #f4efe7;
                --panel: #fffaf2;
                --panel-strong: #f8e7cf;
                --ink: #1f2a1f;
                --muted: #5f6b63;
                --line: #dfd3bf;
                --accent: #d26a32;
                --accent-dark: #8f3f19;
                --success: #2f7a4e;
            }

            .stApp {
                background:
                    radial-gradient(circle at top left, rgba(210, 106, 50, 0.15), transparent 30%),
                    radial-gradient(circle at top right, rgba(47, 122, 78, 0.14), transparent 24%),
                    linear-gradient(180deg, #f6f1e9 0%, #efe5d7 100%);
                color: var(--ink);
            }

            .block-container {
                padding-top: 2rem;
                padding-bottom: 3rem;
                max-width: 1180px;
            }

            .hero {
                background: linear-gradient(135deg, rgba(255, 250, 242, 0.92), rgba(248, 231, 207, 0.96));
                border: 1px solid var(--line);
                border-radius: 24px;
                padding: 1.6rem 1.7rem;
                box-shadow: 0 18px 40px rgba(78, 52, 28, 0.08);
                margin-bottom: 1rem;
            }

            .hero-kicker {
                display: inline-block;
                color: var(--accent-dark);
                background: rgba(210, 106, 50, 0.12);
                border: 1px solid rgba(210, 106, 50, 0.2);
                border-radius: 999px;
                padding: 0.3rem 0.7rem;
                font-size: 0.8rem;
                letter-spacing: 0.04em;
                text-transform: uppercase;
            }

            .hero h1 {
                font-size: 2.6rem;
                line-height: 1.05;
                margin: 0.9rem 0 0.7rem 0;
                color: var(--ink);
            }

            .hero p {
                color: var(--muted);
                font-size: 1rem;
                margin: 0;
                max-width: 760px;
            }

            .stat-card {
                background: rgba(255, 250, 242, 0.9);
                border: 1px solid var(--line);
                border-radius: 18px;
                padding: 1rem 1.1rem;
                min-height: 112px;
            }

            .stat-label {
                color: var(--muted);
                font-size: 0.8rem;
                text-transform: uppercase;
                letter-spacing: 0.05em;
            }

            .stat-value {
                font-size: 1.8rem;
                color: var(--ink);
                margin-top: 0.35rem;
                font-weight: 700;
            }

            .stat-subtext {
                color: var(--muted);
                font-size: 0.9rem;
                margin-top: 0.35rem;
            }

            .section-card {
                background: rgba(255, 250, 242, 0.88);
                border: 1px solid var(--line);
                border-radius: 22px;
                padding: 1.25rem;
                box-shadow: 0 12px 28px rgba(78, 52, 28, 0.05);
                margin-bottom: 1rem;
            }

            .job-card {
                background: rgba(255, 250, 242, 0.95);
                border: 1px solid var(--line);
                border-radius: 24px;
                padding: 1.25rem;
                box-shadow: 0 16px 30px rgba(78, 52, 28, 0.06);
                margin: 1rem 0 1.4rem 0;
            }

            .job-title {
                font-size: 1.35rem;
                font-weight: 700;
                color: var(--ink);
                margin: 0;
            }

            .job-meta {
                color: var(--muted);
                margin-top: 0.25rem;
                font-size: 0.95rem;
            }

            .pill-row {
                display: flex;
                flex-wrap: wrap;
                gap: 0.5rem;
                margin: 0.8rem 0 0.4rem 0;
            }

            .pill {
                padding: 0.35rem 0.75rem;
                border-radius: 999px;
                background: rgba(47, 122, 78, 0.08);
                border: 1px solid rgba(47, 122, 78, 0.16);
                color: #24563a;
                font-size: 0.88rem;
            }

            .score-strip {
                background: linear-gradient(90deg, rgba(210, 106, 50, 0.1), rgba(47, 122, 78, 0.08));
                border: 1px solid var(--line);
                border-radius: 18px;
                padding: 0.9rem 1rem;
                margin-bottom: 0.8rem;
            }

            .panel-title {
                font-size: 0.9rem;
                letter-spacing: 0.05em;
                text-transform: uppercase;
                color: var(--muted);
                margin-bottom: 0.4rem;
            }

            .history-card {
                background: rgba(255, 250, 242, 0.85);
                border: 1px solid var(--line);
                border-radius: 16px;
                padding: 0.8rem 0.9rem;
                margin-bottom: 0.7rem;
            }

            .history-title {
                color: var(--ink);
                font-weight: 700;
                margin-bottom: 0.2rem;
            }

            .history-meta {
                color: var(--muted);
                font-size: 0.82rem;
                line-height: 1.35;
            }
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_hero():
    st.markdown(
        """
        <div class="hero">
            <span class="hero-kicker">AI Prospecting Studio</span>
            <h1>Turn live hiring pages into contract-staffing outreach.</h1>
            <p>
                Analyze public careers pages, identify active hiring needs, match them with your delivery capability,
                and generate polished outreach emails with built-in evaluation scores.
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_overview_cards(store):
    recent_runs = store.get_recent_evaluations(limit=25)
    run_count = len(recent_runs)
    avg_score = round(
        sum(run["overall_score"] for run in recent_runs) / run_count, 1
    ) if run_count else 0

    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown(
            f"""
            <div class="stat-card">
                <div class="stat-label">Recent Runs</div>
                <div class="stat-value">{run_count}</div>
                <div class="stat-subtext">Saved evaluation snapshots from recent analyses.</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with col2:
        st.markdown(
            f"""
            <div class="stat-card">
                <div class="stat-label">Average Score</div>
                <div class="stat-value">{avg_score}</div>
                <div class="stat-subtext">Overall quality across the latest evaluated jobs.</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with col3:
        st.markdown(
            """
            <div class="stat-card">
                <div class="stat-label">Coverage</div>
                <div class="stat-value">Career + Job URLs</div>
                <div class="stat-subtext">Supports direct job posts, listing pages, and many public careers pages.</div>
            </div>
            """,
            unsafe_allow_html=True,
        )


def render_recent_evaluations(store):
    with st.sidebar:
        st.markdown("## Recent Runs")
        recent_runs = store.get_recent_evaluations()
        if not recent_runs:
            st.caption("No evaluation history yet. Run the app once to build your review trail.")
            return

        for run in recent_runs:
            st.markdown(
                f"""
                <div class="history-card">
                    <div class="history-title">{run['job_title']}</div>
                    <div class="history-meta">Score: {run['overall_score']}</div>
                    <div class="history-meta">{run['created_at']}</div>
                    <div class="history-meta">{run['source_url']}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )


def render_evaluation(evaluation):
    st.markdown('<div class="score-strip">', unsafe_allow_html=True)
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Overall", f"{evaluation['overall_score']}/100")
    col2.metric("Extraction", f"{evaluation['extraction']['score']}/100")
    col3.metric("Relevance", f"{evaluation['relevance']['score']}/100")
    col4.metric("Email", f"{evaluation['email_usefulness']['score']}/100")
    st.markdown("</div>", unsafe_allow_html=True)

    details_tab, feedback_tab = st.tabs(["Performance", "Feedback"])

    with details_tab:
        st.write("Automatic quality scoring for extraction, portfolio matching, and message usefulness.")

    with feedback_tab:
        col_a, col_b, col_c = st.columns(3)
        with col_a:
            st.markdown("**Extraction Quality**")
            for item in evaluation["extraction"]["feedback"]:
                st.write(f"- {item}")
        with col_b:
            st.markdown("**Portfolio Relevance**")
            for item in evaluation["relevance"]["feedback"]:
                st.write(f"- {item}")
        with col_c:
            st.markdown("**Email Usefulness**")
            for item in evaluation["email_usefulness"]["feedback"]:
                st.write(f"- {item}")


def render_job_result(index, job, links, email, evaluation):
    job_title = job.get("role") or f"Untitled Job {index}"
    experience = job.get("experience") or "Experience not specified"
    skills = job.get("skills") or []
    description = job.get("description") or "No structured description was extracted."

    st.markdown('<div class="job-card">', unsafe_allow_html=True)
    st.markdown(f'<p class="job-title">{job_title}</p>', unsafe_allow_html=True)
    st.markdown(f'<div class="job-meta">{experience}</div>', unsafe_allow_html=True)

    if skills:
        skill_html = "".join(f'<span class="pill">{skill}</span>' for skill in skills[:10])
        st.markdown(f'<div class="pill-row">{skill_html}</div>', unsafe_allow_html=True)

    summary_tab, email_tab, evidence_tab = st.tabs(["Job Snapshot", "Generated Email", "Portfolio Evidence"])

    with summary_tab:
        st.markdown("**Extracted Summary**")
        st.write(description)
        render_evaluation(evaluation)

    with email_tab:
        st.markdown("**Outreach Draft**")
        st.code(email, language="markdown")

    with evidence_tab:
        if links:
            st.markdown("**Matched Portfolio Links**")
            for link in links:
                st.write(f"- {link}")
        else:
            st.info("No portfolio links were matched for this job.")

    st.markdown("</div>", unsafe_allow_html=True)


def create_streamlit_app(llm, portfolio, evaluator, evaluation_store, text_cleaner):
    inject_styles()
    render_recent_evaluations(evaluation_store)
    render_hero()
    render_overview_cards(evaluation_store)

    st.markdown('<div class="section-card">', unsafe_allow_html=True)
    st.markdown("### Analyze A Hiring Page")
    st.caption(
        "Paste any public company careers page, job listings page, or direct job post URL. The app will extract jobs, generate outreach, and score the result."
    )

    url_input = st.text_input(
        "Careers or job page URL",
        value="https://jobs.nike.com/job/R-33460",
        placeholder="Try Google Careers results, Nike, Nykaa, Ford, Greenhouse, Lever, or other public job pages.",
    )

    col_a, col_b = st.columns([3, 1])
    with col_a:
        st.caption("Best results usually come from direct job posts or listing pages that visibly contain job cards.")
    with col_b:
        submit_button = st.button("Generate Outreach", use_container_width=True)
    st.markdown("</div>", unsafe_allow_html=True)

    if not submit_button:
        return

    if not url_input.strip():
        st.warning("Please enter a valid careers page or job posting URL.")
        return

    with st.spinner("Analyzing careers page, extracting jobs, matching portfolio evidence, and drafting outreach..."):
        try:
            loader = WebBaseLoader([url_input.strip()])
            documents = loader.load()
            if not documents:
                st.warning("No page content could be loaded from that URL.")
                return

            data = text_cleaner(documents[0].page_content)
            jobs = llm.extract_jobs(data, url_input.strip())

            if not jobs:
                st.warning(
                    "No jobs were detected on that page. Try a direct job listing page or a careers page that visibly shows open roles."
                )
                return

            st.markdown("### Outreach Results")
            st.caption(f"Detected {len(jobs)} job opportunity{'ies' if len(jobs) != 1 else 'y'} from the supplied page.")

            for index, job in enumerate(jobs, start=1):
                if not isinstance(job, dict):
                    continue

                skills = job.get("skills") or []
                job_title = job.get("role") or f"Untitled Job {index}"
                matches = portfolio.query_matches(skills)
                links = [match["link"] for match in matches]
                email = llm.write_mail(job, links, url_input.strip())
                evaluation = evaluator.evaluate(job, matches, email)
                evaluation_store.save_evaluation(url_input.strip(), job_title, evaluation)
                render_job_result(index, job, links, email, evaluation)
        except Exception as exc:
            st.error(f"An error occurred: {exc}")


if __name__ == "__main__":
    st.set_page_config(layout="wide", page_title="AI Prospecting Studio", page_icon="📧")
    try:
        chain = Chain()
        portfolio = Portfolio()
        evaluator = Evaluator()
        evaluation_store = EvaluationStore()
        create_streamlit_app(chain, portfolio, evaluator, evaluation_store, clean_text)
    except Exception as exc:
        st.error(f"Startup failed: {exc}")
        st.info("Add your Groq API key to a .env file, then restart the app.")
