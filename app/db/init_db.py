from app.db.session import engine, Base

from app.db.models.post_model import LinkedInPost


def init_db():

    Base.metadata.create_all(bind=engine)