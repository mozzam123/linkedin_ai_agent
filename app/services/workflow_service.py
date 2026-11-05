import json

from app.db.session import SessionLocal
from app.db.models.workflow_run_model import WorkflowRun


def save_workflow_run(state):

    db = SessionLocal()

    try:
        run = WorkflowRun(
            topic=state.get("topic"),
            status=state.get("status", "unknown"),
            final_score=state.get("score"),
        )

        db.add(run)
        db.commit()

        return run
    finally:
        db.close()