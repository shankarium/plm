# Footwear PLM (Light) – Auth + Admin

Includes username/password login with roles and an Admin panel to clear test data.

## Default Users (auto-seeded)
- admin / admin123 (Admin)
- pmuser / test123 (PM)
- npduser / test123 (NPD)
- pmfinal / test123 (PM-Final)
- salesuser / test123 (Sales)

## Deploy on Render
1) Push to GitHub.
2) New Web Service → Build: `pip install -r requirements.txt` → Start: `gunicorn app:app`
3) Add env var: `SECRET_KEY=<random>`
4) (Optional) Add a persistent disk mounted at `/opt/render/project/src` (for SQLite + uploads persistence).

## Local run
```
pip install -r requirements.txt
export FLASK_ENV=development
export SECRET_KEY=dev-secret
python app.py
```
