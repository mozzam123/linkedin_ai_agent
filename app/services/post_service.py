from app.db.session import SessionLocal

from app.db.models.post_model import LinkedInPost


def save_post(state):

    db = SessionLocal()

    post = LinkedInPost(
        topic=state["topic"],
        research_notes=state["research_notes"],
        generated_post=state["generated_post"],
        critique=state["critique"],
        score=state["score"],
        final_post=state["final_post"],
        status=state["status"],
    )

    db.add(post)

    db.commit()

    db.refresh(post)

    db.close()

    return post