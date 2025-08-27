# Footwear PLM (Light) – Stage 1

A lightweight Flask + SQLite app implementing Stage‑1 of your PLM:
PM input → NPD development → PM finalization → Sales catalog, with simple tracking.

## Deploy (quick options)
### Render.com
1. Push this folder to a new GitHub repo.
2. Create a new Web Service on Render → select the repo.
3. Build Command: `pip install -r requirements.txt`
4. Start Command: `gunicorn app:app`
5. Add environment variable: `FLASK_ENV=production`

### Railway.app / Heroku
- Similar steps: install requirements, start `gunicorn app:app`.

### Local run
```
pip install -r requirements.txt
export FLASK_ENV=development
python app.py
```
Open http://localhost:5000

## Notes
- Uses SQLite `plm.db` in app root.
- Image uploads go to `static/uploads/`. For production, use S3.
- Very simple auth (role switcher) for demo. Add real auth later.
