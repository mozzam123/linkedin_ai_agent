from langchain_groq import ChatGroq

from app.core.config import settings


def get_llm():

    llm = ChatGroq(
        model=settings.GROQ_MODEL,
        api_key=settings.GROQ_API_KEY,
        temperature=0.7,
    )

    return llm