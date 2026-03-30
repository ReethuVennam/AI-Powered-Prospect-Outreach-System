# Cold Mail Generator

This project takes a job or careers page URL, extracts job details, matches them with portfolio items, and generates a cold outreach email using Groq + LangChain + Streamlit.
It also evaluates each run for extraction quality, portfolio relevance, and email usefulness, then saves recent evaluation history in a local SQLite database.

## What I fixed

- Made `.env` loading work from either the project root or the `app` folder.
- Added clear startup validation for a missing `GROQ_API_KEY`.
- Fixed the portfolio loader to use project-relative paths.
- Fixed Chroma insert payloads so documents and metadata are added in the expected format.
- Added a fallback portfolio matcher so the app can still work even if Chroma embedding download/setup fails.
- Cleaned up the Streamlit app flow and improved runtime error messages.
- Added `.env.example` for safer setup.
- Added an evaluation layer with automatic scoring and local run history.

## Recommended Python version

Use Python `3.11` or `3.12`.

Your current environment is on Python `3.14`, and parts of the LangChain stack warn that this version is not fully compatible yet.

## Setup

1. Install Python `3.11` or `3.12` if you do not already have it.
2. Open a terminal in the project root.
3. Create a virtual environment:

```powershell
py -3.11 -m venv .venv
```

4. Activate it:

```powershell
.venv\Scripts\Activate.ps1
```

5. Install dependencies:

```powershell
pip install -r requirements.txt
```

6. Create a `.env` file in the project root.
7. Copy the contents of `.env.example` into `.env`.
8. Set your Groq key:

```env
GROQ_API_KEY=your_actual_groq_key_here
GROQ_MODEL=llama-3.3-70b-versatile
```

9. Run the app:

```powershell
streamlit run app/main.py
```

## External things you must create

1. A Groq API key from https://console.groq.com/keys
2. A local `.env` file in the project root
3. A Python `3.11` or `3.12` virtual environment

## Notes

- The first run may still need internet access to read the job page URL you enter.
- If Chroma embedding setup is unavailable, the app now falls back to CSV-based portfolio matching instead of crashing.
