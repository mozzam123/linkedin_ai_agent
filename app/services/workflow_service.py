import json

from app.db.session import SessionLocal
from app.db.models.workflow_run_model import WorkflowRun


def save_workflow_run(state):

    db = SessionLocal()

    run = WorkflowRun(
        topic=state["topic"],
        status="completed",
        final_score=state.get("score"),
        duration_seconds=state["trace"].get_duration(),
        trace=state["trace"].get_trace()
    )

    db.add(run)
    db.commit()
    db.close()