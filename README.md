# REMinder

A personal lucid dreaming journal built with Streamlit. Log dreams every morning, track patterns over time, and use AI-powered insights to improve dream recall and increase lucid dream frequency.

## Stack

- **Frontend + Backend** — Streamlit (single Python file, no auth required)
- **Database** — SQLite (single-user, WAL mode)
- **AI** — Anthropic Claude API (`claude-opus-4-8`)
- **Deployment** — Streamlit Community Cloud

## Features

### Core (Stage 1)

- **Dream journal** — date, title, content, dream type (Happy / Lucid / Nightmare / etc.)
- **AI analysis** — dream interpretation, recall detail score (0–10), recurring people / places / emotions extraction
- **Dashboard** — recall score trend, dream type distribution, lucid dream frequency chart

### Habit Tracking (Stage 2)

- **Technique log** — record WBTB, MILD, WILD, FILD, SSILD, reality checks used each night
- **Morning condition log** — sleep hours, alarm use, prior-day caffeine / alcohol
- **Partial recall prompts** — AI generates guided questions when you can't remember a dream
- **Streak tracker** — consecutive journaling days shown in the sidebar
- **Calendar heatmap** — GitHub-style activity grid + lucid dream occurrence calendar
- **Correlation charts** — technique vs. lucid rate, sleep hours vs. recall score, caffeine / alcohol effect, reality check count vs. lucid rate

### AI Analytics (Stage 3)

- **Dream sign clustering** — AI groups recurring elements into your personal Top 5 dream signs
- **Search** — keyword search across title / content / AI analysis; toggle AI semantic search ("show me dreams with the ocean")
- **Weekly report** — AI summarizes patterns and emotional shifts across the week's dreams
- **MILD intention generator** — produces a pre-sleep intention sentence based on your top dream signs

## Setup

**1. Clone and create a virtual environment**

```bash
git clone https://github.com/your-username/REMinder-re.git
cd REMinder-re
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

**2. Add your Anthropic API key**

```bash
cp .streamlit/secrets.toml.example .streamlit/secrets.toml
# edit .streamlit/secrets.toml and paste your key
```

`.streamlit/secrets.toml`:

```toml
ANTHROPIC_API_KEY = "sk-ant-..."
```

Get a key at [console.anthropic.com](https://console.anthropic.com).

**3. Run**

```bash
streamlit run app.py
```

## Deployment (Streamlit Community Cloud)

1. Push the repo to GitHub (`.streamlit/secrets.toml` and `*.db` are gitignored)
2. Go to [share.streamlit.io](https://share.streamlit.io) → **New app**
3. Select the repo, branch `main`, main file `app.py`
4. Open **Settings → Secrets** and paste your `ANTHROPIC_API_KEY`
5. Click **Deploy**

> The free tier sleeps after inactivity, and the SQLite database lives on ephemeral storage — data resets on redeploy. For persistent storage, mount the `.db` file to an external volume.

## Project Structure

```
REMinder-re/
├── app.py            # Streamlit UI (all pages and routing)
├── db.py             # SQLite schema, CRUD, and stats queries
├── llm.py            # Claude API calls (analysis, clustering, search, summary)
├── requirements.txt
├── .streamlit/
│   ├── secrets.toml          # API key (gitignored)
│   └── secrets.toml.example  # committed template
└── springboot/       # Original Spring Boot prototype (archived)
```
