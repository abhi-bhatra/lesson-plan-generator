# One Call GenAI Lesson Lab

A tiny Streamlit app that makes **one OpenAI API call** and turns it into:

- a mini-lesson (markdown)
- a rendered Mermaid diagram
- a 5-question quiz
- 3 next steps

This is designed to **wow beginners**: “Wait… the API returned all of that in one response?”

## Setup

### 1) Create a virtual env (recommended)

```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 2) Install dependencies

```bash
pip install -r requirements.txt
```

### 3) Set your OpenAI key

```bash
export OPENAI_API_KEY="YOUR_KEY"
```

Optional (default is `gpt-4o-mini`):

```bash
export OPENAI_MODEL="YOUR_MODEL_NAME"
```

### 4) Run

```bash
streamlit run app.py
```

## CI/CD (GitHub Actions)

The repo includes a workflow (`.github/workflows/deploy-cloudrun.yml`) that deploys to **Google Cloud Run** on every push to `main`, using project `kk-lab-dev` and service `kk-ai-lesson-plan-generator`.

**Required GitHub secrets:**

| Secret         | Description |
|----------------|-------------|
| `GCP_SA_KEY`   | JSON key for a GCP service account that can deploy to Cloud Run (Cloud Run Admin, Service Account User, and optionally Storage for build). |
| `OPENAI_API_KEY` | Your OpenAI API key; passed to the Cloud Run service as an env var. |

Create the service account in [GCP IAM](https://console.cloud.google.com/iam-admin/serviceaccounts) (project `kk-lab-dev`), grant **Cloud Run Admin** and **Service Account User**, create a key, and paste the JSON into the `GCP_SA_KEY` secret. Add `OPENAI_API_KEY` in repo **Settings → Secrets and variables → Actions**.

## Teaching notes (quick talking points)

- The prompt forces a **structured JSON schema** → you can parse it and build UI.
- One response can contain **multiple “products”**: explanation + diagram + quiz.
- Rendering Mermaid makes the output feel like a real app, not “just text”.

## Troubleshooting

- If the app says it “couldn’t parse JSON”, reduce temperature (e.g. 0.2) and regenerate.
- If Mermaid fails to render, regenerate; diagrams are intentionally small (<= 12 nodes).

