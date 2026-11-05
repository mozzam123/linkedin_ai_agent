from app.db.session import SessionLocal
from app.db.models.post_model import LinkedInPost


def save_post(state):
    db = SessionLocal()

    try:
        # Prefer the highest-scoring version; fall back to the last draft
        final_content = (
            state.get("best_post")
            or state.get("final_post")
            or state.get("generated_post")
        )

        # iteration_count tracks how many rewrites happened (starts at 0)
        rewrite_count = state.get("iteration_count", 0)

        post = LinkedInPost(
            topic=state.get("topic"),
            research_notes=state.get("research_notes"),   # Written by research_node
            generated_post=state.get("generated_post"),   # Original draft
            critique=state.get("critique"),
            score=state.get("score"),
            final_post=final_content,                     # Best version after rewrites
            status=state.get("status"),
            review_comments=f"Rewrite loops: {rewrite_count}",
        )

        db.add(post)
        db.commit()
        db.refresh(post)

        return post
    finally:
        db.close()