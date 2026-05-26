from langchain_groq import ChatGroq
from app.core.config import settings


def get_llm(temperature: float = 0.7):
    """
    Default temperature 0.7 for drafting and rewriting.
    Pass temperature=0.95 for topic generation to maximize variety.
    Pass temperature=0.3 for critique and validation where consistency matters.
    """
    llm = ChatGroq(
        model=settings.GROQ_MODEL,
        api_key=settings.GROQ_API_KEY,
        temperature=temperature,
    )
    return llm