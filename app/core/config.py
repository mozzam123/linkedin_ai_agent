from dotenv import load_dotenv
import os

load_dotenv()

class Settings:

    # ── Existing LLM settings ──────────────────────────────────────────────
    GROQ_API_KEY = os.getenv("GROQ_API_KEY")
    GROQ_MODEL   = os.getenv("GROQ_MODEL")

    # ── Playwright session ─────────────────────────────────────────────────
    # Single-account setup: one fixed session folder, no multi-account support
    PLAYWRIGHT_SESSION_DIR = "./playwright_user_data"

    # Headful is the default for scraping (less bot-like, and you can see it
    # working). Set SCRAPER_HEADLESS=true for scheduled/unattended runs.
    SCRAPER_HEADLESS = os.getenv("SCRAPER_HEADLESS", "false").strip().lower() in (
        "1", "true", "yes", "on",
    )

    # ── Rate limiting ──────────────────────────────────────────────────────
    MAX_COMMENTS_PER_DAY             = 5    # hard ceiling, never exceed
    MIN_HOURS_BETWEEN_COMMENTS       = 2    # minimum gap between any two posted comments
    MAX_COMMENTS_PER_CREATOR_PER_48H = 1   # cooldown per creator
    MIN_POST_WORD_COUNT              = 5   # skip posts shorter than this
    RELEVANCE_SCORE_THRESHOLD        = 6.5  # skip posts scoring below this
    COMMENT_SELF_SCORE_THRESHOLD     = 7.0  # reject comments scoring below this
    MAX_COMMENT_GENERATION_ATTEMPTS  = 3    # rewrite loop limit per post
    MAX_POSTS_TO_SCRAPE_PER_RUN      = 20   # feed posts to collect per scheduler run
    MAX_COMMENTS_TO_POST_PER_RUN     = 3    # approved comments to post per scheduler run

    # Without permalinks an old post can no longer be found in the feed.
    # Comments older than this are marked expired instead of retried forever.
    MAX_COMMENT_AGE_HOURS            = 24

    # ── Discovery pre-filter ───────────────────────────────────────────────
    # Posts containing none of these words are dropped before any LLM call,
    # so the scorer never spends a token on HR posts or internship ads.
    SCRAPER_KEYWORD_PREFILTER = os.getenv("SCRAPER_KEYWORD_PREFILTER", "true").strip().lower() in (
        "1", "true", "yes", "on",
    )
    NICHE_KEYWORDS = (
        "ai", "llm", "llms", "agent", "agents", "agentic", "rag", "mlops",
        "llmops", "model", "models", "prompt", "prompts", "prompting",
        "embedding", "embeddings", "vector", "vectors", "retrieval",
        "fine-tuning", "finetune", "transformer", "transformers", "gpt",
        "claude", "gemini", "openai", "anthropic", "langchain", "langgraph",
        "fastapi", "python", "inference", "token", "tokens", "eval", "evals",
        "evaluation", "hallucination", "hallucinations", "chatbot", "neural",
        "machine learning", "deep learning", "dataset", "datasets", "api",
        "api", "apis", "context window", "copilot", "coding agent",
        "genai", "generative ai", "artificial intelligence", "nlp",
        "data science", "computer vision",
    )
    SCHEDULER_INTERVAL_HOURS         = 5    # base interval between discovery runs
    SCHEDULER_JITTER_SECONDS         = 3600 # randomize run time ±1 hour

    # ── Niche definition (used in relevance scoring prompt) ────────────────
    NICHE_TOPICS = [
        "AI engineering",
        "LLMs",
        "large language models",
        "LangChain",
        "LangGraph",
        "AI agents",
        "FastAPI",
        "developer productivity",
        "MLOps",
        "vector databases",
        "RAG",
        "retrieval augmented generation",
        "AI startups",
        "open source AI",
        "prompt engineering",
        "Python backend",
        "production AI",
    ]

    NICHE_SKIP_SIGNALS = [
        "motivational quote",
        "sports",
        "politics",
        "personal life milestone",
        "wedding",
        "birthday",
        "vacation",
        "sales pitch",
        "discount offer",
        "job referral program",
    ]

    # ── Your voice examples (used in comment generation prompt) ────────────
    # IMPORTANT: Replace these placeholders with your own real LinkedIn
    # comments before running the comment workflow for the first time.
    # The more authentic and representative these are, the better the
    # generated comments will match your actual tone and style.
    VOICE_EXAMPLES = [
        "Interesting take — I've been seeing similar patterns when building with LangGraph. The state management complexity really adds up fast.",
        "most people don’t lack ideas, they just overlook their everyday experiences",
        "balancing business and parenting is never easy",
    ]


settings = Settings()