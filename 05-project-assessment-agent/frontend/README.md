# Frontend — Slack-faithful demo + dashboard (Block 4)

A single static page (vanilla JS + Tailwind CDN + Chart.js CDN, no build step)
that drives the Block 3 FastAPI backend. Four tabs:

1. **#spec-channel** — run `/spec` on a seeded transcript; see the draft + Slack
   summary, the "needs human review" badge, the expandable draft spec, and (on a
   duplicate) the three resume options.
2. **#spec-review** — specs sent to review; **Approve** (green) / **Reject** (red).
3. **#deal-tracking** — the opportunity bubbles that approvals create.
4. **Dashboard** — three-pillar analytics from `GET /dashboard-data`.

All state is in memory (no localStorage). Every API call goes through a single
const at the top of `app.js`:

```js
const API_BASE = "http://127.0.0.1:8000"; // swap to retarget the backend
```

## Files

```
frontend/
├── index.html       app shell + tabs (loads the CDNs)
├── styles.css       Slack-faithful panes + Activation Labs burgundy/cream chrome
├── app.js           all logic: API calls, Slack-payload rendering, charts
├── transcripts.js   the two seeded transcripts, embedded as JS constants
└── README.md        this file
```

## Enable CORS (paste this into backend/app.py yourself)

The browser calls the backend cross-origin (from `file://` or another port), so
FastAPI must send CORS headers. **Add this to `backend/app.py`** — right after
`app = FastAPI(...)` is created:

```python
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],          # demo only; tighten for any real deployment
    allow_credentials=False,      # must be False when allow_origins=["*"]
    allow_methods=["*"],
    allow_headers=["*"],
)
```

`allow_origins=["*"]` (with `allow_credentials=False`) also covers the `null`
origin a `file://` page sends, so opening `index.html` directly works.

## How I run it

1. **Start the backend** (from `backend/`, after Blocks 1–3 are applied/seeded):
   ```bash
   cd 05-project-assessment-agent/backend
   uvicorn app:app --reload     # serves http://127.0.0.1:8000
   ```
2. **Add the CORS snippet above** to `backend/app.py` and let `--reload` restart
   (or restart uvicorn). Confirm `http://127.0.0.1:8000/docs` loads.
3. **Open the frontend** — either is fine:
   - Double-click `frontend/index.html` (opens via `file://`), **or**
   - Serve it: `cd 05-project-assessment-agent/frontend && python3 -m http.server 5500`
     then open `http://127.0.0.1:5500`.
4. **Run the demo:** in **#spec-channel**, pick *Meridian Synth (clean)* → **Run
   /spec** → expand the draft → **Send to review** → in **#spec-review**,
   **Approve** → watch the opportunity post to **#deal-tracking** → open
   **Dashboard**. Then try *Cedarbrook Health (edge case)* to see the
   ⚠️ needs-human-review badge and the red escalation; run it twice to trigger
   the duplicate-pause with the three resume options.

> If the page shows "Can't reach the API at http://127.0.0.1:8000", the backend
> isn't running or CORS isn't enabled — see steps 1–2.
