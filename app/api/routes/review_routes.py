from fastapi import APIRouter
from app.db.session import SessionLocal
from app.db.models.post_model import LinkedInPost

router = APIRouter()


# Endpoint to get all pending posts for review
@router.get("/pending-posts")
async def get_pending_posts():

    db = SessionLocal()

    posts = db.query(LinkedInPost).filter(
        LinkedInPost.status == "under_review"
    ).all()

    total_count = len(posts)

    db.close()

    return {
        "total_count": total_count,
        "posts": posts
    }


# Endpoint to approve a post
@router.post("/approve-post/{post_id}")
async def approve_post(post_id: int):

    db = SessionLocal()

    post = db.query(LinkedInPost).filter(
        LinkedInPost.id == post_id
    ).first()

    if not post:
        return {"error": "Post not found"}

    post.status = "approved"

    db.commit()

    db.close()

    return {"message": "Post approved"}