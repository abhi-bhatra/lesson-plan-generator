import json
import os
import re
from dataclasses import dataclass
from typing import Any

import streamlit as st
from dotenv import load_dotenv
from openai import OpenAI


load_dotenv()


@dataclass
class Generated:
    title: str
    elevator_pitch: str
    lesson_md: str
    mermaid: str
    quiz: list[dict[str, Any]]
    next_steps: list[str]


SYSTEM_PROMPT = """You are a brilliant teaching assistant.
You create beginner-friendly explanations that are accurate, concrete, and engaging.

Output must be VALID JSON ONLY (no markdown fences, no extra commentary).
Follow the schema exactly.

Schema:
{
  "title": string,
  "elevator_pitch": string,
  "lesson_md": string,              // markdown allowed
  "mermaid": string,                // a mermaid diagram (flowchart or sequenceDiagram). Must start with 'flowchart' or 'sequenceDiagram'
  "quiz": [
    {
      "question": string,
      "options": [string, string, string, string],
      "answer_index": 0|1|2|3,
      "explanation": string
    }
  ],
  "next_steps": [string, string, string]
}
"""


def _extract_json(text: str) -> str | None:
    """
    Best-effort extraction if the model wraps JSON in extra text.
    We still prefer strict JSON in the prompt, but this makes the demo resilient.
    """
    text = text.strip()
    if text.startswith("{") and text.endswith("}"):
        return text

    # Find the first top-level {...} block (best-effort).
    m = re.search(r"\{[\s\S]*\}", text)
    return m.group(0) if m else None


def _parse_generated(text: str) -> tuple[Generated | None, str | None]:
    raw = _extract_json(text) or text
    try:
        obj = json.loads(raw)
    except Exception as e:
        return None, f"Couldn't parse JSON output. Error: {e}"

    try:
        g = Generated(
            title=str(obj["title"]),
            elevator_pitch=str(obj["elevator_pitch"]),
            lesson_md=str(obj["lesson_md"]),
            mermaid=str(obj["mermaid"]),
            quiz=list(obj["quiz"]),
            next_steps=list(obj["next_steps"]),
        )
    except Exception as e:
        return None, f"JSON parsed, but didn't match expected schema. Error: {e}"

    if not (g.mermaid.strip().startswith("flowchart") or g.mermaid.strip().startswith("sequenceDiagram")):
        g.mermaid = "flowchart LR\n  A[Mermaid diagram failed validation] --> B[Ask the model to start with flowchart or sequenceDiagram]"

    return g, None


def render_mermaid(mermaid_code: str) -> None:
    # Mermaid render via CDN in an isolated HTML component.
    html = f"""
<div class="mermaid">
{mermaid_code}
</div>
<script type="module">
  import mermaid from "https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.esm.min.mjs";
  mermaid.initialize({{ startOnLoad: true, theme: "default" }});
</script>
"""
    st.components.v1.html(html, height=360, scrolling=True)


def main() -> None:
    st.set_page_config(page_title="One Call GenAI Lesson Lab", page_icon="✨", layout="wide")

    st.title("One Call GenAI Lesson Lab")
    st.caption("Type a topic → get a mini-lesson + diagram + quiz from a single OpenAI API call.")

    with st.sidebar:
        st.subheader("Settings")
        model = st.text_input("Model", value=os.getenv("OPENAI_MODEL", "gpt-4o-mini"))
        temperature = st.slider("Creativity (temperature)", 0.0, 1.0, 0.4, 0.05)
        max_output_tokens = st.slider("Max output tokens", 512, 4096, 1400, 64)
        st.divider()
        st.write("Auth via environment variable:")
        st.code("export OPENAI_API_KEY='...'", language="bash")

    col_a, col_b = st.columns([1.2, 1])

    with col_a:
        topic = st.text_input("Topic", placeholder="e.g., Transformers, Kubernetes, Gradient Descent, SQL Joins")
        audience = st.selectbox("Audience", ["High school", "College", "Bootcamp", "Working professionals"])
        style = st.selectbox("Style", ["Clear & practical", "Fun & analogy-driven", "Exam focused", "Story-based"])
        include_demo = st.checkbox("Include a tiny example/demo in the lesson", value=True)

        go = st.button("Generate (one API call)", type="primary", use_container_width=True, disabled=not topic.strip())

    with col_b:
        st.subheader("What you'll get")
        st.markdown(
            "- **Mini-lesson** (markdown)\n"
            "- **Mermaid diagram** (auto-rendered)\n"
            "- **5-question quiz** (interactive)\n"
            "- **Next steps** (3 items)"
        )
        st.info(
            "Teaching moment: show students how prompt + structure = an app.\n"
            "Everything here comes from one model response."
        )

    if not go:
        st.divider()
        st.write("Try a fun prompt:")
        st.code("Topic: Backpropagation\nAudience: Bootcamp\nStyle: Fun & analogy-driven", language="text")
        return

    client = OpenAI()

    user_prompt = f"""
Create content for:
- topic: {topic}
- audience: {audience}
- style: {style}
- include_demo: {include_demo}

Guidelines:
- Keep the lesson under ~450 words.
- Prefer concrete examples over jargon.
- Mermaid: keep it simple and readable (<= 12 nodes).
- Quiz: 5 questions, 4 options each, one correct answer.
"""

    with st.spinner("Thinking..."):
        resp = client.responses.create(
            model=model,
            input=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            temperature=temperature,
            max_output_tokens=max_output_tokens,
        )

    raw_text = getattr(resp, "output_text", None) or ""
    if not raw_text.strip():
        st.error("Model returned an empty response.")
        st.stop()

    generated, err = _parse_generated(raw_text)
    if err or not generated:
        st.error(err or "Unknown parsing error.")
        with st.expander("Raw model output"):
            st.code(raw_text)
        st.stop()

    st.divider()
    st.subheader(generated.title)
    st.write(generated.elevator_pitch)

    left, right = st.columns([1.25, 1])

    with left:
        st.markdown("### Mini-lesson")
        st.markdown(generated.lesson_md)

        st.markdown("### Next steps")
        for i, item in enumerate(generated.next_steps, start=1):
            st.write(f"{i}. {item}")

    with right:
        st.markdown("### Diagram")
        render_mermaid(generated.mermaid)

    st.markdown("### Quiz")
    score = 0
    for idx, q in enumerate(generated.quiz):
        st.markdown(f"**Q{idx + 1}. {q.get('question', '').strip()}**")
        options = q.get("options", ["", "", "", ""])
        answer_index = int(q.get("answer_index", 0))
        explanation = str(q.get("explanation", "")).strip()

        choice = st.radio(
            label=f"q_{idx}_radio",
            options=list(range(4)),
            format_func=lambda i: options[i],
            index=None,
            horizontal=False,
            label_visibility="collapsed",
            key=f"q_{idx}",
        )
        if choice is None:
            continue

        if choice == answer_index:
            st.success("Correct")
            score += 1
        else:
            st.warning(f"Not quite. Correct answer: {options[answer_index]}")
        if explanation:
            st.caption(explanation)
        st.divider()

    answered = sum(1 for i in range(len(generated.quiz)) if st.session_state.get(f"q_{i}") is not None)
    st.info(f"Score: {score}/{len(generated.quiz)} (answered {answered}/{len(generated.quiz)})")

    with st.expander("Show the exact JSON the model produced"):
        extracted = _extract_json(raw_text) or raw_text
        st.code(extracted, language="json")


if __name__ == "__main__":
    main()

