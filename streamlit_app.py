import streamlit as st
import sys
import os
import time

# ─── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="LinkedIn AI Agent",
    page_icon="💼",
    layout="centered",
)

# ─── Minimal CSS ───────────────────────────────────────────────────────────────
st.markdown("""
<style>
    .score-badge {
        display: inline-block;
        padding: 4px 14px;
        border-radius: 20px;
        font-size: 1.1rem;
        font-weight: 700;
    }
    .score-high   { background: #d4edda; color: #155724; }
    .score-medium { background: #fff3cd; color: #856404; }
    .score-low    { background: #f8d7da; color: #721c24; }
    .status-pill {
        display: inline-block;
        padding: 2px 10px;
        border-radius: 12px;
        font-size: 0.8rem;
        font-weight: 600;
        background: #e2e8f0;
        color: #4a5568;
    }
    /* Make read-only text areas look like plain readable boxes */
    textarea[disabled] {
        color: inherit !important;
        -webkit-text-fill-color: inherit !important;
        opacity: 1 !important;
    }
</style>
""", unsafe_allow_html=True)


# ─── Sidebar – config ──────────────────────────────────────────────────────────
with st.sidebar:
    st.image("https://upload.wikimedia.org/wikipedia/commons/c/ca/LinkedIn_logo_initials.png", width=40)
    st.title("LinkedIn AI Agent")
    st.markdown("---")

    st.subheader("⚙️ Configuration")
    groq_key = st.text_input("Groq API Key", type="password",
                              value=os.getenv("GROQ_API_KEY", ""),
                              help="Your Groq API key")
    groq_model = st.selectbox("Model", [
        "llama-3.3-70b-versatile",
        "llama-3.1-8b-instant",
        "gemma2-9b-it",
    ])

    st.markdown("---")
    st.caption("Workflow: Topic → Research → Draft → Critique → (Rewrite loop) → Review → Publish")


# ─── Session state defaults ────────────────────────────────────────────────────
defaults = {
    "stage": "idle",          # idle | running | review | approved | published
    "topic": "",
    "research_notes": "",
    "generated_post": "",
    "critique": "",
    "score": None,
    "iteration_count": 0,
    "errors": [],
    "edit_mode": False,
    "edited_post": "",
    "log": [],
    "publish_result": None,
}
for k, v in defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v


def log(msg):
    st.session_state.log.append(msg)


def reset():
    for k, v in defaults.items():
        st.session_state[k] = v


def score_class(score):
    if score is None:
        return "score-medium"
    if score >= 8:
        return "score-high"
    if score >= 5:
        return "score-medium"
    return "score-low"


# ─── Run the agent workflow ────────────────────────────────────────────────────
def run_workflow():
    """Run the LangGraph workflow and populate session state."""
    # Key guard is handled at call site so the error renders in the right place

    # Inject env var so existing code picks it up
    os.environ["GROQ_API_KEY"] = groq_key
    os.environ["GROQ_MODEL"] = groq_model

    # Add project to path so imports work
    project_path = os.path.join(os.path.dirname(__file__),
                                "Linkedin AI Agent")
    if project_path not in sys.path:
        sys.path.insert(0, project_path)

    st.session_state.stage = "running"
    st.session_state.log = []
    st.session_state.errors = []

    progress = st.progress(0, text="Starting workflow…")

    try:
        from app.core.tracing import TraceCollector
        from app.workflows.graphs.linkedin_graph import workflow

        initial_state = {
            "topic": None,
            "research_notes": None,
            "generated_post": None,
            "critique": None,
            "score": None,
            "final_post": None,
            "status": "starting",
            "errors": [],
            "validation_errors": [],
            "is_valid": True,
            "iteration_count": 0,
            "trace": TraceCollector(),
            "ai_research": None,
            "startup_research": None,
            "tools_research": None,
        }

        steps = [
            "Generating topic…",
            "Researching topic…",
            "Drafting post…",
            "Critiquing draft…",
            "Rewriting / validating…",
            "Saving…",
        ]
        step_idx = 0

        for chunk in workflow.stream(initial_state):
            node_name = list(chunk.keys())[0]
            state = chunk[node_name]

            node_labels = {
                "topic_node":      "✅ Topic generated",
                "research_node":   "✅ Research complete",
                "draft_node":      "✅ Draft created",
                "critique_node":   "✅ Critique done",
                "rewrite_node":    "🔄 Rewriting…",
                "validation_node": "✅ Validated",
                "save_node":       "✅ Saved",
            }
            log(node_labels.get(node_name, f"→ {node_name}"))

            step_idx = min(step_idx + 1, len(steps) - 1)
            progress.progress(
                int((step_idx / len(steps)) * 100),
                text=steps[step_idx]
            )

            # Capture final values
            if state.get("topic"):
                st.session_state.topic = state["topic"]
            if state.get("research_notes"):
                st.session_state.research_notes = state["research_notes"]
            if state.get("generated_post"):
                st.session_state.generated_post = state["generated_post"]
                st.session_state.edited_post = state["generated_post"]
            if state.get("critique"):
                st.session_state.critique = state["critique"]
            if state.get("score") is not None:
                st.session_state.score = state["score"]
            if state.get("iteration_count") is not None:
                st.session_state.iteration_count = state["iteration_count"]
            if state.get("errors"):
                st.session_state.errors = state["errors"]

        progress.progress(100, text="Workflow complete!")
        time.sleep(0.4)
        progress.empty()

        st.session_state.stage = "review"
        st.session_state.edit_mode = False

    except Exception as e:
        progress.empty()
        st.session_state.stage = "idle"
        st.session_state.errors.append(str(e))
        st.error(f"Workflow failed: {e}")


# ─── Publish to LinkedIn ───────────────────────────────────────────────────────
def publish():
    project_path = os.path.join(os.path.dirname(__file__), "Linkedin AI Agent")
    if project_path not in sys.path:
        sys.path.insert(0, project_path)

    try:
        from app.automation.linkedin_publisher import publish_to_linkedin
        content = st.session_state.edited_post or st.session_state.generated_post
        publish_to_linkedin(content)
        st.session_state.stage = "published"
        st.session_state.publish_result = "success"
    except Exception as e:
        st.session_state.publish_result = f"error: {e}"


# ═══════════════════════════════════════════════════════════════════════════════
#  MAIN UI
# ═══════════════════════════════════════════════════════════════════════════════

st.title("💼 LinkedIn Post Agent")

stage = st.session_state.stage

# ── IDLE ───────────────────────────────────────────────────────────────────────
if stage == "idle":
    st.markdown("Generate, review, and publish a LinkedIn post — all in one place.")
    st.markdown("---")

    col1, col2 = st.columns([2, 1])
    with col1:
        st.markdown("#### How it works")
        st.markdown("""
1. **Topic** – AI picks a trending topic  
2. **Research** – Gathers context  
3. **Draft** – Writes the post  
4. **Critique** – Scores & gives feedback  
5. **Rewrite loop** – Improves until score ≥ 8  
6. **You review** – Edit, approve, publish
        """)
    with col2:
        st.markdown("&nbsp;")
        # 1. NEW: Static placeholder buffer created directly above the action button
        
        if st.button("🚀 Generate Post", use_container_width=True, type="primary"):
            key_error_placeholder = st.empty()
            if not groq_key:
                key_error_placeholder.error("⚠️ Please enter your Groq API Key in the sidebar first.")
                time.sleep(2) # Leave visible for 2 seconds
                key_error_placeholder.empty() # Clear out container
            else:
                run_workflow()
                st.rerun()

# ── RUNNING ────────────────────────────────────────────────────────────────────
elif stage == "running":
    st.info("Agent is working… please wait.")
    run_workflow()
    st.rerun()

# ── REVIEW ─────────────────────────────────────────────────────────────────────
elif stage == "review":
    # ── Topic & meta row
    col_a, col_b, col_c = st.columns([3, 1, 1])
    with col_a:
        st.markdown(f"**📌 Topic:** {st.session_state.topic or '—'}")
    with col_b:
        score = st.session_state.score
        label = f"{score:.1f} / 10" if score is not None else "—"
        css = score_class(score)
        st.markdown(f'<span class="score-badge {css}">⭐ {label}</span>',
                    unsafe_allow_html=True)
    with col_c:
        iters = st.session_state.iteration_count
        st.markdown(f'<span class="status-pill">🔄 {iters} rewrite(s)</span>',
                    unsafe_allow_html=True)

    st.markdown("---")

    # ── Critique
    if st.session_state.critique:
        with st.expander("🧠 AI Critique", expanded=True):
            st.text_area(
                "critique_display",
                value=st.session_state.critique,
                height=150,
                disabled=True,
                label_visibility="collapsed",
            )

    # ── Post preview / editor
    st.markdown("#### 📝 Post Draft")

    if st.session_state.edit_mode:
        edited = st.text_area(
            "Edit your post",
            value=st.session_state.edited_post,
            height=300,
            label_visibility="collapsed",
        )
        st.session_state.edited_post = edited

        col1, col2 = st.columns(2)
        with col1:
            if st.button("💾 Save edits", use_container_width=True):
                st.session_state.edit_mode = False
                st.rerun()
        with col2:
            if st.button("✖ Cancel", use_container_width=True):
                st.session_state.edited_post = st.session_state.generated_post
                st.session_state.edit_mode = False
                st.rerun()
    else:
        display_post = st.session_state.edited_post or st.session_state.generated_post
        st.text_area(
            "post_preview",
            value=display_post,
            height=300,
            disabled=True,
            label_visibility="collapsed",
        )

        char_count = len(display_post)
        col1, col2, col3 = st.columns([1, 1, 2])
        with col1:
            if st.button("✏️ Edit", use_container_width=True):
                st.session_state.edit_mode = True
                st.rerun()
        with col2:
            st.caption(f"{char_count} chars")

    st.markdown("---")

    # ── Action buttons
    col_approve, col_publish, col_restart = st.columns(3)

    with col_approve:
        if st.button("✅ Approve", use_container_width=True, type="primary"):
            st.session_state.stage = "approved"
            st.rerun()

    with col_publish:
        if st.button("🚀 Publish to LinkedIn", use_container_width=True):
            approve_error_placeholder = st.empty()
            approve_error_placeholder.warning("⚠️ Please **Approve** the content before publishing.")
            time.sleep(2) # Keep visible for 2 seconds
            approve_error_placeholder.empty() # Automatically wipe out text element

    with col_restart:
        if st.button("🔁 Start over", use_container_width=True):
            reset()
            st.rerun()

    # ── Workflow log (collapsed)
    if st.session_state.log:
        with st.expander("📋 Workflow log"):
            for entry in st.session_state.log:
                st.markdown(f"- {entry}")

    # ── Errors
    if st.session_state.errors:
        with st.expander("⚠️ Errors", expanded=True):
            for err in st.session_state.errors:
                st.error(err)

# ── APPROVED ───────────────────────────────────────────────────────────────────
elif stage == "approved":
    st.success("✅ Post approved! Ready to publish.")

    display_post = st.session_state.edited_post or st.session_state.generated_post
    st.text_area(
        "approved_post_preview",
        value=display_post,
        height=300,
        disabled=True,
        label_visibility="collapsed",
    )

    st.markdown("---")
    col1, col2 = st.columns(2)
    with col1:
        if st.button("🚀 Publish to LinkedIn", use_container_width=True, type="primary"):
            with st.spinner("Publishing to LinkedIn…"):
                publish()
            st.rerun()
    with col2:
        if st.button("← Back to review", use_container_width=True):
            st.session_state.stage = "review"
            st.rerun()

# ── PUBLISHED ──────────────────────────────────────────────────────────────────
elif stage == "published":
    result = st.session_state.publish_result

    if result == "success":
        st.balloons()
        st.success("🎉 Your post has been published to LinkedIn!")
    else:
        st.error(f"Publishing failed: {result}")

    display_post = st.session_state.edited_post or st.session_state.generated_post
    st.markdown("**Published content:**")
    st.text_area(
        "published_content",
        value=display_post,
        height=300,
        disabled=True,
        label_visibility="collapsed",
    )

    st.markdown("---")
    if st.button("🔁 Create another post", type="primary"):
        reset()
        st.rerun()