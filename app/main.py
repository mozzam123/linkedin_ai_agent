from fastapi import FastAPI
from app.workflows.graphs.linkedin_graph import workflow
from app.db.init_db import init_db
from app.api.routes.review_routes import router as review_router

app = FastAPI()



app.include_router(review_router)

@app.get("/")
async def root():
    return {"message": "Running"}


@app.get("/run-workflow")
async def run_workflow():

    initial_state = {
        "topic": None,
        "research_notes": None,
        "generated_post": None,
        "critique": None,
        "score": None,
        "final_post": None,
        "status": None,
        "errors": [],
        "iteration_count": 0,
    }

    result = workflow.invoke(initial_state)

    return result


@app.on_event("startup")
async def startup_event():

    init_db()