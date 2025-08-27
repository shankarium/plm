
import os
from flask import Flask, render_template, request, redirect, url_for, flash, send_from_directory, session
from flask import g
import sqlite3
from datetime import datetime
from werkzeug.utils import secure_filename

APP_ROOT = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(APP_ROOT, "plm.db")
UPLOAD_FOLDER = os.path.join(APP_ROOT, "static", "uploads")
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

ALLOWED_EXT = {"png","jpg","jpeg","gif","webp"}

def get_db():
    db = getattr(g, "_db", None)
    if db is None:
        db = g._db = sqlite3.connect(DB_PATH)
        db.row_factory = sqlite3.Row
    return db

def init_db():
    db = get_db()
    db.executescript("""
    CREATE TABLE IF NOT EXISTS market_briefs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        project_no TEXT,
        season TEXT,
        brand TEXT,
        subcategory TEXT,
        design TEXT,
        target_mrp REAL,
        market_focus TEXT,
        expected_sales_qty INTEGER,
        stateqty_kerala INTEGER, stateqty_tn INTEGER, stateqty_ka INTEGER,
        stateqty_ap INTEGER, stateqty_ts INTEGER, stateqty_mh INTEGER,
        stateqty_gj INTEGER, stateqty_rj INTEGER, stateqty_dl INTEGER,
        stateqty_wb INTEGER, stateqty_other INTEGER,
        sample_adaptation_pct INTEGER,
        color_requirements TEXT,
        pm_general_remarks TEXT,
        pm_reference_image_url TEXT,
        status TEXT DEFAULT 'Draft',
        created_by TEXT,
        created_at TEXT,
        updated_at TEXT
    );
    CREATE TABLE IF NOT EXISTS concepts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        brief_id INTEGER REFERENCES market_briefs(id),
        nd_no TEXT,
        proposed_mrp REAL,
        upper_material TEXT, lining TEXT, insole TEXT, outsole TEXT,
        construction TEXT,
        size_curve TEXT,
        colorways TEXT,
        article_image_url TEXT,
        brand_suggestion TEXT,
        npd_remarks TEXT,
        status TEXT DEFAULT 'In_Development',
        created_by TEXT,
        created_at TEXT,
        updated_at TEXT
    );
    CREATE TABLE IF NOT EXISTS sales_info (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        concept_id INTEGER REFERENCES concepts(id),
        margin_pct REAL,
        selling_story TEXT,
        sales_remarks TEXT,
        final_presentation_image_url TEXT,
        status TEXT DEFAULT 'Published',
        created_at TEXT
    );
    CREATE TABLE IF NOT EXISTS comments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        entity_type TEXT, -- BRIEF or CONCEPT
        entity_id INTEGER,
        author TEXT,
        body TEXT,
        created_at TEXT
    );
    """)
    db.commit()

def upload_file(fieldname):
    f = request.files.get(fieldname)
    if not f or f.filename == "":
        return None
    name = secure_filename(f.filename)
    ext = name.rsplit(".",1)[-1].lower() if "." in name else ""
    if ext not in ALLOWED_EXT:
        flash("Unsupported file type.", "warning")
        return None
    stamp = datetime.now().strftime("%Y%m%d%H%M%S")
    save_as = f"{stamp}_{name}"
    path = os.path.join(UPLOAD_FOLDER, save_as)
    f.save(path)
    return url_for("static", filename=f"uploads/{save_as}", _external=False)

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY","dev-secret")

@app.before_request
def before():
    init_db()

@app.teardown_appcontext
def teardown(exception):
    db = getattr(g, "_db", None)
    if db is not None:
        db.close()

# ---- Basic "role" switcher (demo) ----
@app.route("/login", methods=["GET","POST"])
def login():
    if request.method == "POST":
        role = request.form.get("role")
        session["role"] = role
        flash(f"Logged in as {role}", "success")
        return redirect(url_for("home"))
    return render_template("login.html", role=session.get("role"))

@app.route("/logout")
def logout():
    session.clear()
    flash("Logged out", "info")
    return redirect(url_for("home"))

@app.route("/")
def home():
    role = session.get("role")
    return render_template("index.html", role=role)

# ---- PM: create & manage briefs ----
@app.route("/pm/briefs")
def pm_briefs():
    db = get_db()
    rows = db.execute("SELECT * FROM market_briefs ORDER BY id DESC").fetchall()
    return render_template("pm_briefs_list.html", rows=rows)

@app.route("/pm/briefs/new", methods=["GET","POST"])
def pm_brief_new():
    if request.method == "POST":
        ref_url = upload_file("pm_reference_image_file") or request.form.get("pm_reference_image_url") or ""
        db = get_db()
        db.execute("""
            INSERT INTO market_briefs
            (project_no,season,brand,subcategory,design,target_mrp,market_focus,expected_sales_qty,
             stateqty_kerala,stateqty_tn,stateqty_ka,stateqty_ap,stateqty_ts,stateqty_mh,stateqty_gj,
             stateqty_rj,stateqty_dl,stateqty_wb,stateqty_other,
             sample_adaptation_pct,color_requirements,pm_general_remarks,pm_reference_image_url,status,
             created_by,created_at,updated_at)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        """, (
            request.form.get("project_no"),
            request.form.get("season"),
            request.form.get("brand"),
            request.form.get("subcategory"),
            request.form.get("design"),
            request.form.get("target_mrp") or None,
            request.form.get("market_focus"),
            request.form.get("expected_sales_qty") or None,
            request.form.get("stateqty_kerala") or None,
            request.form.get("stateqty_tn") or None,
            request.form.get("stateqty_ka") or None,
            request.form.get("stateqty_ap") or None,
            request.form.get("stateqty_ts") or None,
            request.form.get("stateqty_mh") or None,
            request.form.get("stateqty_gj") or None,
            request.form.get("stateqty_rj") or None,
            request.form.get("stateqty_dl") or None,
            request.form.get("stateqty_wb") or None,
            request.form.get("stateqty_other") or None,
            request.form.get("sample_adaptation_pct") or None,
            request.form.get("color_requirements"),
            request.form.get("pm_general_remarks"),
            ref_url,
            "Draft",
            request.form.get("created_by") or "pm_user",
            datetime.now().isoformat(timespec="seconds"),
            datetime.now().isoformat(timespec="seconds")
        ))
        db.commit()
        flash("Brief saved (Draft).", "success")
        return redirect(url_for("pm_briefs"))
    return render_template("pm_brief_new.html")

@app.route("/pm/briefs/submit/<int:id>", methods=["POST"])
def pm_brief_submit(id):
    db = get_db()
    db.execute("UPDATE market_briefs SET status='Submitted', updated_at=? WHERE id=?", (datetime.now().isoformat(timespec="seconds"), id))
    db.commit()
    flash("Brief submitted to NPD.", "success")
    return redirect(url_for("pm_briefs"))

@app.route("/brief/<int:id>")
def brief_detail(id):
    db = get_db()
    brief = db.execute("SELECT * FROM market_briefs WHERE id=?", (id,)).fetchone()
    concepts = db.execute("SELECT * FROM concepts WHERE brief_id=? ORDER BY id DESC", (id,)).fetchall()
    return render_template("brief_detail.html", brief=brief, concepts=concepts)

# ---- NPD: intake briefs, create concept ----
@app.route("/npd/briefs")
def npd_briefs():
    db = get_db()
    rows = db.execute("SELECT * FROM market_briefs WHERE status='Submitted' ORDER BY id DESC").fetchall()
    return render_template("npd_briefs.html", rows=rows)

@app.route("/npd/concepts/new/<int:brief_id>", methods=["GET","POST"])
def concept_new(brief_id):
    if request.method == "POST":
        article_url = upload_file("article_image_file") or request.form.get("article_image_url") or ""
        db = get_db()
        db.execute("""
            INSERT INTO concepts
            (brief_id, nd_no, proposed_mrp, upper_material, lining, insole, outsole, construction,
             size_curve, colorways, article_image_url, brand_suggestion, npd_remarks, status, created_by, created_at, updated_at)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        """, (
            brief_id,
            request.form.get("nd_no"),
            request.form.get("proposed_mrp") or None,
            request.form.get("upper_material"),
            request.form.get("lining"),
            request.form.get("insole"),
            request.form.get("outsole"),
            request.form.get("construction"),
            request.form.get("size_curve"),
            request.form.get("colorways"),
            article_url,
            request.form.get("brand_suggestion"),
            request.form.get("npd_remarks"),
            "Ready_for_PM",
            request.form.get("created_by") or "npd_user",
            datetime.now().isoformat(timespec="seconds"),
            datetime.now().isoformat(timespec="seconds")
        ))
        # also mark brief to In_Development → then back to Submitted doesn't matter; keep simple
        get_db().execute("UPDATE market_briefs SET status='Submitted', updated_at=? WHERE id=?", (datetime.now().isoformat(timespec="seconds"), brief_id))
        get_db().commit()
        flash("Concept created and sent to PM (Ready for PM).", "success")
        return redirect(url_for("npd_concepts"))
    db = get_db()
    brief = db.execute("SELECT * FROM market_briefs WHERE id=?", (brief_id,)).fetchone()
    return render_template("concept_new.html", brief=brief)

@app.route("/npd/concepts")
def npd_concepts():
    db = get_db()
    rows = db.execute("SELECT * FROM concepts ORDER BY id DESC").fetchall()
    return render_template("npd_concepts.html", rows=rows)

# ---- PM finalization (sales-facing) ----
@app.route("/pm/finalize")
def pm_finalize_list():
    db = get_db()
    rows = db.execute("SELECT c.*, b.project_no FROM concepts c LEFT JOIN market_briefs b ON b.id=c.brief_id WHERE c.status='Ready_for_PM' ORDER BY c.id DESC").fetchall()
    return render_template("pm_finalize_list.html", rows=rows)

@app.route("/pm/finalize/<int:concept_id>", methods=["GET","POST"])
def pm_finalize(concept_id):
    db = get_db()
    concept = db.execute("SELECT * FROM concepts WHERE id=?", (concept_id,)).fetchone()
    if request.method == "POST":
        final_url = upload_file("final_image_file") or request.form.get("final_presentation_image_url") or ""
        db.execute("""
            INSERT INTO sales_info (concept_id, margin_pct, selling_story, sales_remarks, final_presentation_image_url, status, created_at)
            VALUES (?,?,?,?,?,?,?)
        """, (
            concept_id,
            request.form.get("margin_pct") or None,
            request.form.get("selling_story"),
            request.form.get("sales_remarks"),
            final_url,
            "Published",
            datetime.now().isoformat(timespec="seconds")
        ))
        db.execute("UPDATE concepts SET status='Ready_for_Sales', updated_at=? WHERE id=?", (datetime.now().isoformat(timespec="seconds"), concept_id))
        db.commit()
        flash("Sales info saved. Concept is Ready for Sales.", "success")
        return redirect(url_for("sales_catalog"))
    return render_template("pm_finalize.html", concept=concept)

# ---- Sales catalog ----
@app.route("/sales/catalog")
def sales_catalog():
    db = get_db()
    rows = db.execute("""
        SELECT c.*, b.project_no, b.season, s.margin_pct, s.selling_story, s.sales_remarks, s.final_presentation_image_url
        FROM concepts c
        LEFT JOIN market_briefs b ON b.id=c.brief_id
        LEFT JOIN sales_info s ON s.concept_id=c.id
        WHERE c.status='Ready_for_Sales'
        ORDER BY c.id DESC
    """).fetchall()
    return render_template("sales_catalog.html", rows=rows)

@app.route("/concept/<int:id>")
def concept_view(id):
    db = get_db()
    c = db.execute("""
        SELECT c.*, b.project_no, b.season, b.brand, b.subcategory, b.design, b.target_mrp
        FROM concepts c LEFT JOIN market_briefs b ON b.id=c.brief_id
        WHERE c.id=?
    """, (id,)).fetchone()
    s = db.execute("SELECT * FROM sales_info WHERE concept_id=? ORDER BY id DESC LIMIT 1", (id,)).fetchone()
    return render_template("concept_view.html", c=c, s=s)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
