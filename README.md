# LinkedIn AI Agent

An autonomous AI agent that generates, critiques, and refines LinkedIn posts using a multi-step LangGraph workflow — with a human-in-the-loop review step before anything gets published.

## Overview

This project automates the end-to-end process of creating high-quality LinkedIn content for a technical/AI engineering niche. Instead of a single LLM call producing a post, the system runs a structured pipeline where a topic is generated, researched, drafted, critiqued against a scoring rubric, and iteratively rewritten until it meets a quality bar — all before a human ever sees it for approval.

The project also includes an automation module for discovering and engaging with relevant posts on LinkedIn (comment generation and posting), built on Playwright.

## Workflow

Topic → Research → Draft → Critique → (Rewrite loop) → Validation → Save → Human Review → Publish


- **Topic Node** — selects a topic direction and post goal (Impressions / Comments / Saves), avoiding recently used topics.
- **Research Node** — gathers concrete, technical talking points to ground the post in specifics rather than generic AI commentary.
- **Draft Node** — writes the first version of the post, matching a defined voice/style guide.
- **Critique Node** — scores the draft (hook, specificity, human feel, goal alignment, dwell time) and returns a priority fix.
- **Rewrite Node** — applies the critique and regenerates the post, looping back to Critique until the score threshold is met or the iteration cap is reached.
- **Validation Node** — checks the final draft against platform constraints (length, hashtag spam, formatting).
- **Save Node** — persists the post and workflow run for human review.
- **Review & Publish** — a reviewer approves or edits the post via API/Streamlit before it's published to LinkedIn.

## Tech Stack

| Layer | Technology |
|---|---|
| Language | Python 3.11+ |
| Web Framework | FastAPI + Uvicorn |
| Agent Orchestration | LangGraph |
| LLM Framework | LangChain (`langchain-groq`) |
| LLM Provider | Groq |
| Database | SQLite (via SQLAlchemy ORM) |
| Data Validation | Pydantic |
| Browser Automation | Playwright |
| UI | Streamlit |
| Config Management | python-dotenv |
| Dependency Management | Poetry |

## Project Structure

```text
app/
├── api/routes/           # FastAPI endpoints (review, approve, publish)
├── automation/           # Playwright-based LinkedIn scraping & publishing
├── core/                 # Config, logging, tracing
├── db/                   # SQLAlchemy models & session management
├── prompts/              # Prompt templates for each workflow stage
├── schemas/              # Pydantic schemas
├── services/             # LLM, post, workflow, validation, publish services
├── tools/                # Standalone tools (e.g. research)
├── utils/                # Helper utilities (style loading, etc.)
├── workflows/
│   ├── graphs/           # LangGraph graph definitions
│   ├── nodes/            # Individual workflow nodes
│   └── state/            # Workflow state schemas
├── style_examples/       # Voice/style reference examples
└── main.py               # FastAPI application entry point
```


## Getting Started

### Prerequisites

- Python 3.11+
- [Poetry](https://python-poetry.org/) for dependency management
- A [Groq API key](https://console.groq.com/)

### Installation

```bash
git clone <repository-url>
cd linkedin-ai-agent
poetry install
```

### Environment Variables

Create a `.env` file in the project root:

```env
GROQ_API_KEY=your_groq_api_key
GROQ_MODEL=llama-3.3-70b-versatile
```

### Running the API

```bash
poetry run uvicorn app.main:app --reload
```

The API will be available at `http://localhost:8000`.

### Running the Streamlit UI

```bash
poetry run streamlit run streamlit_app.py
```

## API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| GET | `/run-workflow` | Triggers the content generation workflow |
| GET | `/pending-posts` | Lists posts awaiting human review |
| POST | `/approve-post/{post_id}` | Approves a reviewed post |
| POST | `/publish-post/{post_id}` | Publishes an approved post to LinkedIn |

## Configuration

Key tunables live in `app/core/config.py`, including:

- Rate limits for automated commenting (daily caps, cooldowns)
- Relevance and quality score thresholds
- Niche topic definitions used for content relevance scoring
- Voice examples used to match generated content to your personal tone

## Roadmap / Known Limitations

- Human review is currently required before any post is published — full autonomy is a future consideration.
- The commenting automation module operates independently of the content generation pipeline.
- Test coverage is being actively expanded.

## License

Specify your license here.
