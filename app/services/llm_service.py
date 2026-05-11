from langchain_groq import ChatGroq

from app.core.config import settings


def get_llm():

    llm = ChatGroq(
        model="llama-3.3-70b-versatile",
        api_key=settings.GROQ_API_KEY,
        temperature=0.7,
    )

    return llm