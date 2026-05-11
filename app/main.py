from fastapi import FastAPI

from app.workflows.graphs.linkedin_graph import workflow


app = FastAPI()



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