from app.db.session import engine, Base
from app.db.models.post_model import LinkedInPost
from app.db.models.discovered_post_model import DiscoveredPost    # noqa: F401
from app.db.models.generated_comment_model import GeneratedComment  # noqa: F401
from app.db.models.creator_profile_model import CreatorProfile


def init_db():
    Base.metadata.create_all(bind=engine)