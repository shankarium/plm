
import os
from functools import wraps
from flask import Flask, render_template, request, redirect, url_for, flash, session, g
import sqlite3
from datetime import datetime
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash

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
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE,
        password_hash TEXT,
        role TEXT CHECK(role in ('Admin','PM','NPD','PM-Final','Sales'))
    );
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
        entity_type TEXT,
        entity_id INTEGER,
        author TEXT,
        body TEXT,
        created_at TEXT
    );
    """)
    db.commit()
    # Seed users if empty
    cur = db.execute("SELECT COUNT(*) as c FROM users")
    if cur.fetchone()["c"] == 0:
        users = [
            ("admin", generate_password_hash("admin123"), "Admin"),
            ("pmuser", generate_password_hash("test123"), "PM"),
            ("npduser", generate_password_hash("test123"), "NPD"),
            ("pmfinal", generate_password_hash("test123"), "PM-Final"),
            ("salesuser", generate_password_hash("test123"), "Sales"),
        ]
        db.executemany("INSERT INTO users (username, password_hash, role) VALUES (?, ?, ?)", users)
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

def login_required(roles=None):
    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            if "user_id" not in session:
                flash("Please log in.", "warning")
                return redirect(url_for("login"))
            if roles:
                if session.get("role") not in roles:
                    flash("Access denied for your role.", "warning")
                    return redirect(url_for("home"))
            return fn(*args, **kwargs)
        return wrapper
    return decorator

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

# -------- Auth --------
@app.route("/login", methods=["GET","POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username","").strip()
        password = request.form.get("password","")
        db = get_db()
        row = db.execute("SELECT * FROM users WHERE username=?", (username,)).fetchone()
        if row and check_password_hash(row["password_hash"], password):
            session["user_id"] = row["id"]
            session["username"] = row["username"]
            session["role"] = row["role"]
            flash(f"Welcome {row['username']} ({row['role']})", "success")
            return redirect(url_for("home"))
        else:
            flash("Invalid credentials.", "warning")
    return render_template("login.html", role=session.get("role"))

@app.route("/logout")
def logout():
    session.clear()
    flash("Logged out", "info")
    return redirect(url_for("login"))

@app.route("/")
def home():
    role = session.get("role")
    return render_template("index.html", role=role, username=session.get("username"))

# -------- PM: Briefs --------
@app.route("/pm/briefs")
@login_required(roles=["PM","Admin"])
def pm_briefs():
    db = get_db()
    rows = db.execute("SELECT * FROM market_briefs ORDER BY id DESC").fetchall()
    return render_template("pm_briefs_list.html", rows=rows)

@app.route("/pm/briefs/new", methods=["GET","POST"])
@login_required(roles=["PM","Admin"])
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
            session.get("username","pm_user"),
            datetime.now().isoformat(timespec="seconds"),
            datetime.now().isoformat(timespec="seconds")
        ))
        db.commit()
        flash("Brief saved (Draft).", "success")
        return redirect(url_for("pm_briefs"))
    return render_template("pm_brief_new.html")

@app.route("/pm/briefs/submit/<int:id>", methods=["POST"])
@login_required(roles=["PM","Admin"])
def pm_brief_submit(id):
    db = get_db()
    db.execute("UPDATE market_briefs SET status='Submitted', updated_at=? WHERE id=?", (datetime.now().isoformat(timespec="seconds"), id))
    db.commit()
    flash("Brief submitted to NPD.", "success")
    return redirect(url_for("pm_briefs"))

@app.route("/brief/<int:id>")
@login_required(roles=["PM","NPD","PM-Final","Sales","Admin"])
def brief_detail(id):
    db = get_db()
    brief = db.execute("SELECT * FROM market_briefs WHERE id=?", (id,)).fetchone()
    concepts = db.execute("SELECT * FROM concepts WHERE brief_id=? ORDER BY id DESC", (id,)).fetchall()
    return render_template("brief_detail.html", brief=brief, concepts=concepts)

# -------- NPD: Concepts --------
@app.route("/npd/briefs")
@login_required(roles=["NPD","Admin"])
def npd_briefs():
    db = get_db()
    rows = db.execute("SELECT * FROM market_briefs WHERE status='Submitted' ORDER BY id DESC").fetchall()
    return render_template("npd_briefs.html", rows=rows)

@app.route("/npd/concepts/new/<int:brief_id>", methods=["GET","POST"])
@login_required(roles=["NPD","Admin"])
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
            session.get("username","npd_user"),
            datetime.now().isoformat(timespec="seconds"),
            datetime.now().isoformat(timespec="seconds")
        ))
        get_db().execute("UPDATE market_briefs SET status='Submitted', updated_at=? WHERE id=?", (datetime.now().isoformat(timespec="seconds"), brief_id))
        get_db().commit()
        flash("Concept created and sent to PM (Ready for PM).", "success")
        return redirect(url_for("npd_concepts"))
    db = get_db()
    brief = db.execute("SELECT * FROM market_briefs WHERE id=?", (brief_id,)).fetchone()
    return render_template("concept_new.html", brief=brief)

@app.route("/npd/concepts")
@login_required(roles=["NPD","Admin"])
def npd_concepts():
    db = get_db()
    rows = db.execute("SELECT * FROM concepts ORDER BY id DESC").fetchall()
    return render_template("npd_concepts.html", rows=rows)

# -------- PM Finalization --------
@app.route("/pm/finalize")
@login_required(roles=["PM-Final","Admin"])
def pm_finalize_list():
    db = get_db()
    rows = db.execute("SELECT c.*, b.project_no FROM concepts c LEFT JOIN market_briefs b ON b.id=c.brief_id WHERE c.status='Ready_for_PM' ORDER BY c.id DESC").fetchall()
    return render_template("pm_finalize_list.html", rows=rows)

@app.route("/pm/finalize/<int:concept_id>", methods=["GET","POST"])
@login_required(roles=["PM-Final","Admin"])
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

# -------- Sales --------
@app.route("/sales/catalog")
@login_required(roles=["Sales","PM-Final","PM","NPD","Admin"])
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
@login_required(roles=["Sales","PM-Final","PM","NPD","Admin"])
def concept_view(id):
    db = get_db()
    c = db.execute("""
        SELECT c.*, b.project_no, b.season, b.brand, b.subcategory, b.design, b.target_mrp
        FROM concepts c LEFT JOIN market_briefs b ON b.id=c.brief_id
        WHERE c.id=?
    """, (id,)).fetchone()
    s = db.execute("SELECT * FROM sales_info WHERE concept_id=? ORDER BY id DESC LIMIT 1", (id,)).fetchone()
    return render_template("concept_view.html", c=c, s=s)

# -------- Admin Panel --------
@app.route("/admin")
@login_required(roles=["Admin"])
def admin_home():
    db = get_db()
    counts = {
        "briefs": db.execute("SELECT COUNT(*) FROM market_briefs").fetchone()[0],
        "concepts": db.execute("SELECT COUNT(*) FROM concepts").fetchone()[0],
        "sales": db.execute("SELECT COUNT(*) FROM sales_info").fetchone()[0],
        "users": db.execute("SELECT COUNT(*) FROM users").fetchone()[0]
    }
    briefs = db.execute("SELECT * FROM market_briefs ORDER BY id DESC LIMIT 20").fetchall()
    concepts = db.execute("SELECT * FROM concepts ORDER BY id DESC LIMIT 20").fetchall()
    sales = db.execute("SELECT * FROM sales_info ORDER BY id DESC LIMIT 20").fetchall()
    users = db.execute("SELECT id, username, role FROM users ORDER BY id").fetchall()
    return render_template("admin.html", counts=counts, briefs=briefs, concepts=concepts, sales=sales, users=users)

@app.route("/admin/delete/brief/<int:id>", methods=["POST"])
@login_required(roles=["Admin"])
def admin_delete_brief(id):
    db = get_db()
    db.execute("DELETE FROM market_briefs WHERE id=?", (id,))
    db.commit()
    flash(f"Deleted brief {id}", "info")
    return redirect(url_for("admin_home"))

@app.route("/admin/delete/concept/<int:id>", methods=["POST"])
@login_required(roles=["Admin"])
def admin_delete_concept(id):
    db = get_db()
    db.execute("DELETE FROM concepts WHERE id=?", (id,))
    db.commit()
    flash(f"Deleted concept {id}", "info")
    return redirect(url_for("admin_home"))

@app.route("/admin/delete/sales/<int:id>", methods=["POST"])
@login_required(roles=["Admin"])
def admin_delete_sales(id):
    db = get_db()
    db.execute("DELETE FROM sales_info WHERE id=?", (id,))
    db.commit()
    flash(f"Deleted sales record {id}", "info")
    return redirect(url_for("admin_home"))

@app.route("/admin/clear_all", methods=["POST"])
@login_required(roles=["Admin"])
def admin_clear_all():
    db = get_db()
    db.executescript("""
        DELETE FROM sales_info;
        DELETE FROM concepts;
        DELETE FROM market_briefs;
    """)
    db.commit()
    flash("Cleared all briefs, concepts, and sales records.", "info")
    return redirect(url_for("admin_home"))

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
