from fastapi import APIRouter
from app.db.session import SessionLocal
from app.db.models.post_model import LinkedInPost
from app.services.publish_service import publish_post
from app.automation.linkedin_publisher import publish_to_linkedin
from fastapi.concurrency import run_in_threadpool

router = APIRouter()


# Endpoint to get all pending posts for review
@router.get("/pending-posts")
async def get_pending_posts():

    db = SessionLocal()

    posts = db.query(LinkedInPost).filter(
        LinkedInPost.status == "under_review"
    ).all()

    total_count = len(posts)

    formatted_posts = []

    for post in posts:

        formatted_posts.append({
            "id": post.id,
            "topic": post.topic,
            # "generated_post": post.generated_post,
            "critique": post.critique,
            "score": post.score,
            "status": post.status,
        })

    return {
        "total": total_count,
        "posts": formatted_posts
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



# Endpoint to publish a post
@router.post("/publish-post/{post_id}")

async def publish_linkedin_post(post_id: int):

    db = SessionLocal()

    post = db.query(LinkedInPost).filter(

        LinkedInPost.id == post_id

    ).first()

    if not post:

        return {"error": "Post not found"}

    if post.status != "approved":

        return {

            "error": "Post must be approved before publishing"

        }

    await run_in_threadpool(

        publish_to_linkedin,

        post.generated_post

    )

    post.status = "published"

    db.commit()

    db.close()

    return {

        "message": "Post published successfully"

    }