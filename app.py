from flask import Flask, render_template, request, redirect, session, send_file, flash, abort, jsonify
import csv, os, random, re, sqlite3
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from groq import Groq
from dotenv import load_dotenv
try:
    from openai import OpenAI
    OPENAI_IMPORTED = True
except Exception:
    OpenAI = None
    OPENAI_IMPORTED = False
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import inch
import secrets
import time

# ================= SETUP =================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(BASE_DIR, ".env"))
load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "dev_secret_key_change_me")

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.1-8b-instant")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

groq_client = None
openai_client = None
openai_enabled = False
if GROQ_API_KEY:
    try:
        groq_client = Groq(api_key=GROQ_API_KEY)
    except Exception:
        groq_client = None

if OPENAI_API_KEY and not groq_client and OPENAI_IMPORTED:
    try:
        openai_client = OpenAI(api_key=OPENAI_API_KEY)
        openai_enabled = True
    except Exception:
        openai_enabled = False

DB_DIR = os.path.join(BASE_DIR, "data")
DB_PATH = os.path.join(DB_DIR, "app.db")
QUESTIONS_CSV = os.path.join(BASE_DIR, "dataset", "interview_questions_dataset.csv")
TOTAL_QUESTIONS = 5

SUPPORTED_LANGUAGES = ['English', 'Bhojpuri', 'Maithili']
LANGUAGE_MAP = {
    'english': 'English',
    'en': 'English',
    'bhojpuri': 'Bhojpuri',
    'bho': 'Bhojpuri',
    'maithili': 'Maithili',
    'mai': 'Maithili',
}
LANGUAGE_STYLE_RULES = {
    'English': "Write only in clear professional English.",
    'Bhojpuri': "Write only in natural Bhojpuri using Devanagari script. Do not switch to English.",
    'Maithili': "Write only in natural Maithili using Devanagari script. Do not switch to English.",
}
LIVE_CHAT_QUESTION_BANK = {
    'English': {
        'hr': [
            "Tell me about yourself.",
            "Why do you want to join this company?",
            "What are your key strengths and one weakness you are improving?",
            "Where do you see yourself in the next five years?",
            "What motivates you to perform well at work?",
            "Describe an achievement you are proud of.",
            "How do you handle constructive feedback?",
        ],
        'technical': [
            "Explain a technical problem you solved recently.",
            "How do you debug an issue that is hard to reproduce?",
            "How do you prioritize technical tasks under tight deadlines?",
            "How do you ensure code quality before deployment?",
            "Describe your approach to learning a new technology quickly.",
            "How do you balance speed and correctness in engineering work?",
            "How do you explain technical tradeoffs to non-technical stakeholders?",
        ],
        'behavioral': [
            "Tell me about a time you handled conflict in a team.",
            "Describe a situation where you worked under pressure.",
            "Tell me about a mistake you made and what you learned.",
            "How do you respond when priorities suddenly change?",
            "Describe a time when you took ownership without being asked.",
            "How do you maintain collaboration in cross-functional teams?",
            "How do you manage stress during critical deadlines?",
        ],
    },
    'Bhojpuri': {
        'hr': [
            "अपने बारे में संक्षेप में बताईं।",
            "रउआ एह कंपनी में काम काहे करे चाहत बानी?",
            "रउआ के प्रमुख ताकत आ सुधार करे लायक कमजोरी का बा?",
            "अगिला पाँच बरिस में रउआ अपना के कहाँ देखत बानी?",
            "काम में अच्छा करे खातिर रउआ के सबसे बेसी का प्रेरित करेला?",
            "कवनो एक उपलब्धि बताईं, जइसन पर रउआ के गर्व बा।",
            "रउआ सुझाव आ फीडबैक के कइसे लेत बानी?",
        ],
        'technical': [
            "हाल के कवनो तकनीकी समस्या बताईं, जवन रउआ सफलतापूर्वक सुलझवनी।",
            "जवन बग बार-बार दोहरावल ना जा सके, ओकरा के रउआ कइसे डिबग करब?",
            "कम समय में कई तकनीकी काम होखे पर रउआ प्राथमिकता कइसे तय करेलें?",
            "डिप्लॉयमेंट से पहिले कोड क्वालिटी सुनिश्चित करे खातिर रउआ का-का करेलें?",
            "नयका तकनीक जल्दी सीखल खातिर रउआ के तरीका का बा?",
            "तेजी आ सही परिणाम के बीच संतुलन रउआ कइसे बनवेलें?",
            "नॉन-टेक्निकल टीम के तकनीकी विकल्प कइसे समझवेलें?",
        ],
        'behavioral': [
            "टीम में मतभेद होखे पर रउआ ओह स्थिति के कइसे संभालेलें?",
            "दबाव वाला स्थिति में काम करे के कवन अनुभव बा, बताईं।",
            "कवनो गलती से रउआ का सीखनी, एक उदाहरण दीं।",
            "काम के प्राथमिकता अचानक बदले त रउआ कइसे अपनावेनी?",
            "कवनो एहन स्थिति बताईं, जब बिना कहले जिम्मेदारी उठवनी।",
            "अलग-अलग टीम संगे बेहतर तालमेल बनावे खातिर रउआ का करेलें?",
            "कड़ा डेडलाइन में तनाव कइसे मैनेज करेलें?",
        ],
    },
    'Maithili': {
        'hr': [
            "अपने बारे में संक्षेप में बताउ।",
            "अहाँ एहि कंपनी में काज किएक करए चाहैत छी?",
            "अहाँक मुख्य ताकत आ सुधार योग्य कमजोरी की अछि?",
            "अगिला पाँच वर्ष में अपने के कतय देखैत छी?",
            "काज में उत्कृष्ट प्रदर्शन लेल अहाँके की प्रेरित करैत अछि?",
            "कोनो एक उपलब्धि बताउ, जाहि पर अहाँके गर्व अछि।",
            "फीडबैक के अहाँ केना स्वीकार करैत छी?",
        ],
        'technical': [
            "हालहि में सुलझाओल कोनो तकनीकी समस्या बारे बताउ।",
            "जे बग लगातार दोहरायल नहि जाए, ओहि के अहाँ केना डिबग करब?",
            "समय कम होए पर तकनीकी काजक प्राथमिकता अहाँ केना तय करैत छी?",
            "डिप्लॉयमेंट सँ पहिने कोड क्वालिटी सुनिश्चित करए लेल अहाँ की करैत छी?",
            "नव तकनीक जल्दी सीखए लेल अहाँक तरीका की अछि?",
            "गति आ शुद्धता बीच संतुलन अहाँ केना बनबैत छी?",
            "गैर-तकनीकी टीमके तकनीकी विकल्प अहाँ केना समझबैत छी?",
        ],
        'behavioral': [
            "टीम में मतभेद भेला पर अहाँ ओहि स्थिति केना सँभालैत छी?",
            "दबावपूर्ण परिस्थिति में काज के अनुभव सँ जुड़ल उदाहरण दिअ।",
            "कोनो गलती सँ अहाँ की सीखलहुँ, एक उदाहरण दिअ।",
            "जखन प्राथमिकता अचानक बदलि जाए, त अहाँ केना अनुकूलन करैत छी?",
            "कोनो एहन स्थिति बताउ, जतय बिना कहल जिम्मेदारी लेलहुँ।",
            "अलग-अलग टीम संग सहयोग बेहतर बनबए लेल अहाँ की करैत छी?",
            "कठिन डेडलाइन में तनाव के अहाँ केना प्रबंधित करैत छी?",
        ],
    },
}

# ================= HELPERS =================
def get_db():
    os.makedirs(DB_DIR, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db()
    cur = conn.cursor()
    cur.execute('''
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        email TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL,
        ai_feedback INTEGER DEFAULT 1,
        auto_next INTEGER DEFAULT 0,
        show_hints INTEGER DEFAULT 1,
        dark_mode INTEGER DEFAULT 0
    )
    ''')

    cur.execute('''
    CREATE TABLE IF NOT EXISTS records (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        language TEXT,
        round TEXT,
        avg_score INTEGER,
        status TEXT,
        date TEXT,
        details TEXT
    )
    ''')

    cur.execute('''
    CREATE TABLE IF NOT EXISTS questions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        language TEXT,
        round TEXT,
        question TEXT
    )
    ''')

    conn.commit()
    conn.close()


def load_questions_from_csv():
    conn = get_db()
    cur = conn.cursor()
    cur.execute('SELECT COUNT(1) as c FROM questions')
    c = cur.fetchone()['c']
    if c > 0:
        conn.close()
        return
    if os.path.exists(QUESTIONS_CSV):
        with open(QUESTIONS_CSV, encoding='utf-8') as f:
            reader = csv.DictReader(f)
            rows = [(r.get('language','').strip(), r.get('round','').strip(), r.get('question','').strip()) for r in reader]
            cur.executemany('INSERT INTO questions (language, round, question) VALUES (?, ?, ?)', rows)
            conn.commit()
    conn.close()


def fetch_questions(language, round_type):
    conn = get_db()
    cur = conn.cursor()
    cur.execute('SELECT question, language, round FROM questions WHERE lower(language)=? AND lower(round)=?', (language.lower(), round_type.lower()))
    rows = cur.fetchall()
    conn.close()
    return [dict(r) for r in rows]


def normalize_language(language_value):
    lang_key = str(language_value or '').strip().lower()
    return LANGUAGE_MAP.get(lang_key, 'English')


def language_style_rule(language):
    return LANGUAGE_STYLE_RULES.get(language, LANGUAGE_STYLE_RULES['English'])


def get_live_chat_questions(language, round_type):
    normalized_language = normalize_language(language)
    round_key = str(round_type or '').strip().lower() or 'hr'
    pool = LIVE_CHAT_QUESTION_BANK.get(normalized_language, {}).get(round_key, [])
    return [{'question': q, 'language': normalized_language, 'round': round_type or 'HR'} for q in pool]


def live_chat_greeting(language):
    normalized_language = normalize_language(language)
    greetings = {
        'English': "Hello! I am ready for real-time chat. Ask me anything.",
        'Bhojpuri': "नमस्ते! हम रियल-टाइम चैट खातिर तैयार बानी। रउआ कुछुओ पूछ सकत बानी।",
        'Maithili': "नमस्कार! हम रियल-टाइम चैट लेल तैयार छी। अहाँ किछुहो पूछ सकैत छी।",
    }
    return greetings.get(normalized_language, greetings['English'])


def generate_live_chat_reply(user_message, language, history=None):
    normalized_language = normalize_language(language)
    lang_rule = language_style_rule(normalized_language)

    system_prompt = (
        "You are an AI interview trainer and general assistant in live chat mode. "
        f"Language requirement: {lang_rule} "
        "Respond naturally like a real-time ChatGPT conversation. "
        "Do not repeat the same lines. Do not switch language. "
        "Be clear, practical, and concise unless the user asks for detail."
    )

    messages = [{"role": "system", "content": system_prompt}]
    for msg in (history or [])[-12:]:
        role = msg.get('role')
        content = msg.get('content')
        if role in ('user', 'assistant') and content:
            messages.append({"role": role, "content": str(content)})
    messages.append({"role": "user", "content": user_message})

    if groq_client:
        retries = 0
        while retries < 3:
            try:
                completion = groq_client.chat.completions.create(
                    model=GROQ_MODEL,
                    messages=messages,
                    temperature=0.45,
                    max_tokens=700
                )
                return (completion.choices[0].message.content or "").strip()
            except Exception as e:
                retries += 1
                print(f"Groq live chat failed (attempt {retries}):", e)
                time.sleep(1 + retries * 2)

    if openai_enabled and openai_client:
        retries = 0
        while retries < 3:
            try:
                completion = openai_client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=messages,
                    temperature=0.45,
                    max_tokens=700
                )
                return (completion.choices[0].message.content or "").strip()
            except Exception as e:
                retries += 1
                print(f"OpenAI live chat failed (attempt {retries}):", e)
                time.sleep(1 + retries * 2)

    return "AI live chat is unavailable right now."


def create_user(name, email, hashed, ai_feedback=1, auto_next=0, show_hints=1, dark_mode=0):
    conn = get_db()
    cur = conn.cursor()
    cur.execute('INSERT INTO users (name,email,password,ai_feedback,auto_next,show_hints,dark_mode) VALUES (?,?,?,?,?,?,?)',
                (name,email,hashed,ai_feedback,auto_next,show_hints,dark_mode))
    conn.commit()
    uid = cur.lastrowid
    conn.close()
    return uid


def get_user_by_email(email):
    conn = get_db()
    cur = conn.cursor()
    cur.execute('SELECT * FROM users WHERE email=?', (email,))
    row = cur.fetchone()
    conn.close()
    return dict(row) if row else None


def get_user_by_id(uid):
    conn = get_db()
    cur = conn.cursor()
    cur.execute('SELECT * FROM users WHERE id=?', (uid,))
    row = cur.fetchone()
    conn.close()
    return dict(row) if row else None


def update_user(uid, fields: dict):
    if not fields:
        return
    conn = get_db()
    cur = conn.cursor()
    sets = ','.join([f"{k}=?" for k in fields.keys()])
    vals = list(fields.values())
    vals.append(uid)
    cur.execute(f'UPDATE users SET {sets} WHERE id=?', vals)
    conn.commit()
    conn.close()


def add_record(user_id, language, round_type, avg, status, date_str, details):
    conn = get_db()
    cur = conn.cursor()
    cur.execute('INSERT INTO records (user_id,language,round,avg_score,status,date,details) VALUES (?,?,?,?,?,?,?)',
                (user_id, language, round_type, avg, status, date_str, details))
    conn.commit()
    conn.close()


def get_records_for_user(user_id):
    conn = get_db()
    cur = conn.cursor()
    cur.execute('SELECT * FROM records WHERE user_id=? ORDER BY id DESC', (user_id,))
    rows = cur.fetchall()
    conn.close()
    return [dict(r) for r in rows]


def delete_user(uid):
    conn = get_db()
    cur = conn.cursor()
    cur.execute('DELETE FROM users WHERE id=?', (uid,))
    conn.commit()
    conn.close()


def delete_records_for_user(uid):
    conn = get_db()
    cur = conn.cursor()
    cur.execute('DELETE FROM records WHERE user_id=?', (uid,))
    conn.commit()
    conn.close()


def logged_in():
    return "user_id" in session


def get_status(score):
    return "Passed" if score >= 70 else "Average" if score >= 40 else "Failed"


# ================= AI FEEDBACK =================
def calculate_ai_feedback(question, user_answer, language=None):
    """Call configured AI provider (Groq) to get feedback. Returns (score:int, text:str).
    language may be 'English', 'Bhojpuri', or 'Maithili' to instruct the model."""

    normalized_language = normalize_language(language)
    lang_rule = language_style_rule(normalized_language)
    prompt = f"""
You are a professional interviewer.
Language requirement: {lang_rule}

Question: {question}
Candidate Answer: {user_answer}

Give:
Ideal Answer
Comparison
Score out of 100
Strengths
Improvements
Final Feedback

Important:
- Follow the language requirement strictly.
- Keep the response natural for native speakers.
- Keep "Score out of 100" as a numeric value.
"""

    if groq_client:
        retries = 0
        while retries < 3:
            try:
                completion = groq_client.chat.completions.create(
                    model=GROQ_MODEL,
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.4,
                    max_tokens=600
                )
                result = completion.choices[0].message.content
                m = re.search(r"Score[:\s]+(\d{1,3})", result)
                score = int(m.group(1)) if m else 0
                score = max(0, min(100, score))
                return score, result
            except Exception as e:
                retries += 1
                print(f"Groq call failed (attempt {retries}):", e)
                time.sleep(1 + retries * 2)
        return 0, "AI evaluation unavailable (Groq errors)."
    # OpenAI fallback (if configured)
    if openai_enabled and openai_client:
        retries = 0
        while retries < 3:
            try:
                completion = openai_client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.4,
                    max_tokens=600
                )
                result = completion.choices[0].message.content or ""
                m = re.search(r"Score[:\s]+(\d{1,3})", result)
                score = int(m.group(1)) if m else 0
                score = max(0, min(100, score))
                return score, result
            except Exception as e:
                retries += 1
                print(f"OpenAI call failed (attempt {retries}):", e)
                time.sleep(1 + retries * 2)
        return 0, "AI evaluation unavailable (OpenAI errors)."
    return 0, "AI evaluation unavailable. No API key configured."


def calculate_overall_feedback(transcript, language=None):
    normalized_language = normalize_language(language)
    lang_rule = language_style_rule(normalized_language)
    prompt = f"""
You are a professional interviewer and coach.
Language requirement: {lang_rule}

Review the following interview transcript and provide:
- A single numeric score out of 100 representing overall performance
- A concise summary of strengths
- Specific, actionable improvements
- Final feedback paragraph

Transcript:
{transcript}

Present the score in a line that starts with "Score:" followed by the numeric value.
Follow the language requirement strictly.
"""
    if groq_client:
        retries = 0
        while retries < 3:
            try:
                completion = groq_client.chat.completions.create(
                    model=GROQ_MODEL,
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.3,
                    max_tokens=900
                )
                result = completion.choices[0].message.content
                m = re.search(r"Score[:\s]+(\d{1,3})", result)
                score = int(m.group(1)) if m else 0
                score = max(0, min(100, score))
                return score, result
            except Exception as e:
                retries += 1
                print(f"Groq overall call failed (attempt {retries}):", e)
                time.sleep(1 + retries * 2)
        return 0, "AI overall evaluation unavailable (Groq errors)."
    # OpenAI fallback (if configured)
    if openai_enabled and openai_client:
        retries = 0
        while retries < 3:
            try:
                completion = openai_client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.3,
                    max_tokens=900
                )
                result = completion.choices[0].message.content or ""
                m = re.search(r"Score[:\s]+(\d{1,3})", result)
                score = int(m.group(1)) if m else 0
                score = max(0, min(100, score))
                return score, result
            except Exception as e:
                retries += 1
                print(f"OpenAI overall call failed (attempt {retries}):", e)
                time.sleep(1 + retries * 2)
        return 0, "AI overall evaluation unavailable (OpenAI errors)."
    return 0, "AI overall evaluation unavailable. No API key configured."


# ================= PDF =================
def generate_pdf(username, avg_score, details):
    filepath = os.path.join(BASE_DIR, f"{username}_report.pdf")
    doc = SimpleDocTemplate(filepath)
    styles = getSampleStyleSheet()
    elements = [
        Paragraph(f"Interview Report - {username}", styles["Heading1"]),
        Spacer(1, 0.3 * inch),
        Paragraph(f"Average Score: {avg_score}", styles["Normal"]),
        Spacer(1, 0.3 * inch),
        Paragraph(details.replace("\n", "<br/>"), styles["Normal"])
    ]
    doc.build(elements)
    return filepath


# ================= MISC =================
@app.before_request
def ensure_csrf_token():
    if 'csrf_token' not in session:
        session['csrf_token'] = secrets.token_urlsafe(16)


def validate_csrf():
    if request.method == 'POST':
        token = request.form.get('csrf_token') or request.headers.get('X-CSRF-Token')
        if not token or token != session.get('csrf_token'):
            abort(400, 'CSRF token missing or invalid')


@app.context_processor
def inject_globals():
    provider = 'none'
    if groq_client:
        provider = 'groq'
    elif openai_enabled:
        provider = 'openai'
    return {'groq_enabled': bool(groq_client), 'ai_provider': provider}


# ================= ROUTES =================
@app.route('/')
def home():
    return redirect('/login')


@app.route('/register', methods=['GET','POST'])
def register():
    if request.method == 'POST':
        validate_csrf()
        name = request.form.get('name', '').strip()
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        confirm = request.form.get('confirm_password', '')
        if not name or not email or not password:
            flash('Name, email and password are required.', 'error')
            return render_template('register.html')
        if password != confirm:
            flash('Passwords do not match', 'error')
            return render_template('register.html')
        if get_user_by_email(email):
            flash('Email already exists', 'error')
            return render_template('register.html')
        hashed = generate_password_hash(password)
        uid = create_user(name, email, hashed)
        flash('Account created successfully. Please login.', 'success')
        return redirect('/login')
    return render_template('register.html')


@app.route('/login', methods=['GET','POST'])
def login():
    if request.method == 'POST':
        validate_csrf()
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        user = get_user_by_email(email)
        if user and check_password_hash(user['password'], password):
            session.clear()
            session['user_id'] = str(user['id'])
            session['user_name'] = user['name']
            flash('Logged in successfully.', 'success')
            return redirect('/dashboard')
        flash('Invalid credentials', 'error')
        return render_template('login.html', error='Invalid credentials')
    return render_template('login.html')


@app.route('/dashboard')
def dashboard():
    if not logged_in():
        return redirect('/login')
    user_id = session.get('user_id')
    user_records = get_records_for_user(user_id)
    avg = 0
    if user_records:
        avg = sum(int(r['avg_score']) for r in user_records) // len(user_records)
    return render_template('dashboard.html', records=user_records, avg_score=avg)


@app.route('/records')
def records():
    if not logged_in():
        return redirect('/login')
    user_id = session.get('user_id')
    user_records = get_records_for_user(user_id)
    avg_score = 0
    if user_records:
        avg_score = sum(int(r['avg_score']) for r in user_records) // len(user_records)
    return render_template('records.html', records=user_records, avg_score=avg_score)


@app.route('/settings', methods=['GET','POST'])
def settings():
    if not logged_in():
        return redirect('/login')
    current_user = get_user_by_id(session.get('user_id'))
    if request.method == 'POST':
        validate_csrf()
        fields = {}
        name = request.form.get('name', '').strip()
        email = request.form.get('email', '').strip().lower()
        if name: fields['name'] = name
        if email: fields['email'] = email
        if request.form.get('password'):
            fields['password'] = generate_password_hash(request.form.get('password'))
        fields['ai_feedback'] = 1 if request.form.get('ai_feedback') else 0
        fields['auto_next'] = 1 if request.form.get('auto_next') else 0
        fields['show_hints'] = 1 if request.form.get('show_hints') else 0
        fields['dark_mode'] = 1 if request.form.get('dark_mode') else 0
        update_user(current_user['id'], fields)
        session['user_name'] = fields.get('name', current_user['name'])
        flash('Settings updated.', 'success')
        return redirect('/settings')
    return render_template('settings.html', user=current_user)


@app.route('/help')
def help_page():
    if not logged_in():
        return redirect('/login')
    return render_template('help.html')


@app.route('/download_report')
def download_report():
    if not logged_in():
        return redirect('/login')
    user_id = session.get('user_id')
    user_records = get_records_for_user(user_id)
    if not user_records:
        flash('No reports found to download.', 'error')
        return redirect('/dashboard')
    latest = user_records[0]
    filepath = generate_pdf(session['user_name'], latest['avg_score'], latest['details'])
    return send_file(filepath, as_attachment=True)


@app.route('/delete-account', methods=['POST'])
def delete_account():
    validate_csrf()
    if not logged_in():
        return redirect('/login')
    uid = session.get('user_id')
    delete_user(uid)
    delete_records_for_user(uid)
    session.clear()
    flash('Account deleted.', 'success')
    return redirect('/register')


@app.route('/interview', methods=['GET','POST'])
def interview():
    validate_csrf() if request.method == 'POST' else None
    if not logged_in():
        return redirect('/login')
    if request.method == 'GET' and ('language' in request.args or 'round' in request.args):
        for k in ('remaining','asked','total_score','details','language','round'):
            session.pop(k, None)
    if 'remaining' not in session:
        language = request.args.get('language', 'Bhojpuri')
        round_type = request.args.get('round', 'HR')
        filtered_questions = fetch_questions(language, round_type)
        if len(filtered_questions) < TOTAL_QUESTIONS:
            return f"Not enough questions for {language} - {round_type}"
        session['remaining'] = random.sample(filtered_questions, TOTAL_QUESTIONS)
        session['asked'] = 0
        session['total_score'] = 0
        session['details'] = []
        session['language'] = language
        session['round'] = round_type
    if request.method == 'POST':
        if request.form.get('action') == 'stop':
            session.pop('remaining', None)
            return redirect('/dashboard')
        qdata = session['remaining'].pop(0)
        answer = request.form.get('answer', '').strip()
        elapsed = int(request.form.get('elapsed') or 0)
        qa_entry = f"Q: {qdata['question']}\nA: {answer}\nTime: {elapsed}s"
        session.setdefault('qa_pairs', [])
        session.setdefault('per_question_details', [])
        session['qa_pairs'].append(qa_entry)
        session['per_question_details'].append(f"Q: {qdata['question']}\nTime: {elapsed}s")
        session['asked'] += 1
        if session['asked'] >= TOTAL_QUESTIONS:
            transcript = "\n\n".join(session.get('qa_pairs', []))
            score, feedback = calculate_overall_feedback(transcript, session.get('language'))
            avg = score
            details = []
            details.extend(session.get('per_question_details', []))
            details.append("\n--- AI Overall Feedback ---\n")
            details.append(feedback)
            add_record(session['user_id'], session['language'], session['round'], avg, get_status(avg), datetime.now().strftime("%d %b %Y %I:%M %p"), "\n\n".join(details))
            for k in ('remaining','asked','total_score','details','language','round','qa_pairs','per_question_details'):
                session.pop(k, None)
            return redirect('/dashboard')
        return redirect('/interview')
    current = session['remaining'][0]
    return render_template('interview.html', question=current['question'], current_q=session['asked'] + 1, total_q=TOTAL_QUESTIONS, language=session['language'], round_type=session['round'])


@app.route('/api/chat', methods=['POST'])
def api_chat():
    if request.content_type and 'application/json' not in request.content_type:
        return jsonify({'error': 'Content-Type must be application/json'}), 400
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return jsonify({'error': 'Invalid JSON payload'}), 400
    
    # Authentication check first
    if not logged_in():
        return jsonify({'error': 'Authentication required'}), 401
    
    action = data.get('action')
    language = data.get('language') or data.get('lang') or session.get('language', 'English')
    round_type = data.get('round') or data.get('round_type') or session.get('round', 'HR')
    language = normalize_language(language)

    if action in ('start', 'answer', 'next') and not (groq_client or (openai_enabled and openai_client)):
        return jsonify({'error': 'AI provider is not configured. Please check GROQ_API_KEY or OPENAI_API_KEY in .env.'}), 503

    if language not in SUPPORTED_LANGUAGES:
        return jsonify({'error': f'Unsupported language. Supported: {", ".join(SUPPORTED_LANGUAGES)}'}), 400

    if action == 'start':
        filtered_questions = get_live_chat_questions(language, round_type)
        if len(filtered_questions) < 1:
            filtered_questions = fetch_questions(language, round_type)
        if len(filtered_questions) < 1:
            return jsonify({'error': 'No questions available for this language/round'}), 400

        qlist = list(dict.fromkeys(q['question'] for q in filtered_questions if q.get('question')))
        random.shuffle(qlist)
        if not qlist:
            return jsonify({'error': 'No questions available for this language/round'}), 400

        session['chat_remaining'] = qlist[:TOTAL_QUESTIONS]
        session['chat_asked'] = 0
        session['chat_language'] = language
        session['chat_round'] = round_type
        session['chat_history'] = []
        first_q = session['chat_remaining'][0]
        return jsonify({
            'success': True,
            'data': {'reply': first_q, 'question': first_q, 'feedback': '', 'score': ''},
            'reply': first_q,
            'question': first_q,
            'feedback': '',
            'score': '',
            'message': ''
        }), 200

    if action == 'stop':
        for k in ('chat_remaining', 'chat_asked', 'chat_history', 'chat_language', 'chat_round'):
            session.pop(k, None)
        return jsonify({'ok': True})

    if action in ('answer', 'next'):
        if 'chat_remaining' not in session or not session['chat_remaining']:
            return jsonify({'error': 'No active interview. Start first.'}), 400

        language = normalize_language(session.get('chat_language', language))
        round_type = session.get('chat_round', round_type)
        question = session['chat_remaining'].pop(0)
        answer = (data.get('message') or data.get('answer') or '').strip()
        if not answer:
            return jsonify({'error': 'Empty answer'}), 400

        session.setdefault('chat_history', []).append({'question': question, 'answer': answer})
        session['chat_asked'] = session.get('chat_asked', 0) + 1
        score, feedback_text = calculate_ai_feedback(question, answer, language)

        next_question = ''
        if session.get('chat_asked', 0) >= TOTAL_QUESTIONS:
            transcript = "\n\n".join([f"Q: {h['question']}\nA: {h['answer']}" for h in session.get('chat_history', [])])
            overall_score, overall_feedback = calculate_overall_feedback(transcript, language)
            add_record(session['user_id'], language, round_type, overall_score, get_status(overall_score), datetime.now().strftime("%d %b %Y %I:%M %p"), overall_feedback)
            for k in ('chat_remaining', 'chat_asked', 'chat_history', 'chat_language', 'chat_round'):
                session.pop(k, None)
        else:
            next_question = session['chat_remaining'][0] if session.get('chat_remaining') else ''

        return jsonify({
            'success': True,
            'data': {'reply': feedback_text, 'question': next_question, 'feedback': feedback_text, 'score': score},
            'reply': feedback_text,
            'feedback': feedback_text,
            'question': next_question,
            'score': score,
            'message': ''
        }), 200

    return jsonify({'success': False, 'data': None, 'message': 'Invalid action'}), 400


@app.route('/logout', methods=['GET','POST'])
def logout():
    if request.method == 'POST':
        validate_csrf()
        session.clear()
        flash('Logged out', 'success')
        return redirect('/login')
    return redirect('/login')


if __name__ == '__main__':
    try:
        init_db()
        load_questions_from_csv()
    except Exception as e:
        print('Initialization error:', e)
    app.run(debug=True)
