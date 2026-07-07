from flask import Flask, render_template, request, redirect, url_for, session, jsonify, flash
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import json, os
from psycopg2cffi import compat
compat.register()
app = Flask(__name__)
app.secret_key = 'eps-ibt-portal-secret-key'
app.jinja_env.filters['from_json'] = json.loads
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///database.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

SUBJECTS  = ['English', 'Mathematics', 'Science', 'Reasoning']
GRADES    = ['Grade 3', 'Grade 4', 'Grade 5']
SECTIONS_BY_SUBJECT = {
    'English':     ['Reading Comprehension', 'Grammar', 'Spelling', 'Vocabulary', 'Punctuation'],
    'Mathematics': ['Number Operations', 'Algebra', 'Geometry', 'Measurement', 'Data & Statistics'],
    'Science':     ['Life Science', 'Physical Science', 'Earth Science', 'Scientific Inquiry'],
    'Reasoning':   ['Verbal Reasoning', 'Non-Verbal Reasoning', 'Logical Thinking', 'Pattern Recognition'],
}

# ── MODELS ───────────────────────────────────────────────────────────────────

class User(db.Model):
    id       = db.Column(db.Integer, primary_key=True)
    name     = db.Column(db.String(100), nullable=False)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    role     = db.Column(db.String(10), nullable=False)
    grade    = db.Column(db.String(20), nullable=True)
    section  = db.Column(db.String(10), nullable=True)
    created  = db.Column(db.DateTime, default=datetime.utcnow)
    results  = db.relationship('TestResult', backref='student', lazy=True, cascade='all,delete-orphan')

class MockTest(db.Model):
    id         = db.Column(db.Integer, primary_key=True)
    name       = db.Column(db.String(200), nullable=False)
    subject    = db.Column(db.String(50), nullable=False)
    grade      = db.Column(db.String(20), nullable=False)
    difficulty = db.Column(db.String(20), default='Medium')
    duration   = db.Column(db.Integer, default=40)
    status     = db.Column(db.String(10), default='draft')
    questions  = db.Column(db.Text, default='[]')
    created    = db.Column(db.DateTime, default=datetime.utcnow)
    results    = db.relationship('TestResult', backref='test', lazy=True, cascade='all,delete-orphan')

class TestResult(db.Model):
    id             = db.Column(db.Integer, primary_key=True)
    student_id     = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    test_id        = db.Column(db.Integer, db.ForeignKey('mock_test.id'), nullable=False)
    score          = db.Column(db.Integer, default=0)
    total          = db.Column(db.Integer, default=0)
    percent        = db.Column(db.Float, default=0.0)
    answers        = db.Column(db.Text, default='{}')
    section_scores = db.Column(db.Text, default='{}')
    time_taken     = db.Column(db.Integer, default=0)
    taken_at       = db.Column(db.DateTime, default=datetime.utcnow)

# ── HELPERS ──────────────────────────────────────────────────────────────────

def login_required(role=None):
    from functools import wraps
    def decorator(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            if 'user_id' not in session:
                return redirect(url_for('login'))
            if role and session.get('role') != role:
                flash('Access denied.', 'error')
                return redirect(url_for('login'))
            return f(*args, **kwargs)
        return decorated
    return decorator

def safe_avg(lst):
    lst = [x for x in lst if x is not None]
    return round(sum(lst)/len(lst), 1) if lst else 0

def build_analytics():
    """Build full analytics data structure used by all analytics views."""
    students    = User.query.filter_by(role='student').all()
    all_results = TestResult.query.all()

    # ── Overall stats ─────────────────────────────────────────────────────────
    overall_avg = safe_avg([r.percent for r in all_results])
    above80     = sum(1 for r in all_results if r.percent >= 80)
    below60     = sum(1 for r in all_results if r.percent < 60)

    # ── Grade-wise ────────────────────────────────────────────────────────────
    grade_data = {}
    for g in GRADES:
        rs = [r for r in all_results if r.student.grade == g]
        grade_data[g] = {
            'avg': safe_avg([r.percent for r in rs]),
            'count': len(rs),
            'students': len([s for s in students if s.grade == g]),
        }

    # ── Subject-wise ──────────────────────────────────────────────────────────
    subject_data = {}
    for sub in SUBJECTS:
        rs = [r for r in all_results if r.test.subject == sub]
        subject_data[sub] = {
            'avg': safe_avg([r.percent for r in rs]),
            'count': len(rs),
        }

    # ── Grade + Subject cross-tab ─────────────────────────────────────────────
    grade_subject = {}
    for g in GRADES:
        grade_subject[g] = {}
        for sub in SUBJECTS:
            rs = [r for r in all_results if r.student.grade == g and r.test.subject == sub]
            grade_subject[g][sub] = safe_avg([r.percent for r in rs])

    # ── Section-wise (across all subjects) ───────────────────────────────────
    section_data = {}
    for r in all_results:
        try:
            secs = json.loads(r.section_scores or '{}')
            for sec, v in secs.items():
                if v['total'] > 0:
                    pct = round(v['correct']/v['total']*100, 1)
                    section_data.setdefault(sec, []).append(pct)
        except Exception:
            pass
    section_avgs = {sec: safe_avg(vals) for sec, vals in section_data.items()}

    # ── Per-student summary ───────────────────────────────────────────────────
    student_rows = []
    for s in students:
        rs = [r for r in all_results if r.student_id == s.id]
        sub_avgs = {sub: safe_avg([r.percent for r in rs if r.test.subject == sub]) for sub in SUBJECTS}
        student_rows.append({
            'id': s.id, 'name': s.name, 'grade': s.grade, 'section': s.section,
            'tests_taken': len(rs),
            'overall_avg': safe_avg([r.percent for r in rs]),
            'sub_avgs': sub_avgs,
        })
    student_rows.sort(key=lambda x: -x['overall_avg'])

    return dict(
        overall_avg=overall_avg, above80=above80, below60=below60,
        total_results=len(all_results), total_students=len(students),
        grade_data=grade_data, subject_data=subject_data,
        grade_subject=grade_subject, section_avgs=section_avgs,
        student_rows=student_rows, subjects=SUBJECTS, grades=GRADES,
    )

def seed_db():
    if User.query.filter_by(username='Resource_Manager').first():
        return
    db.session.add(User(name='Resource_Manager', username='Organizer',
        password=generate_password_hash('bk*123'), role='Resource_Manager'))
    for name, uname in [('Mrs. Sharma','teacher1'),('Mr. Verma','teacher2')]:
        db.session.add(User(name=name, username=uname,
            password=generate_password_hash('teacher123'), role='teacher'))
    sample = [
        ('Aarav Sharma','aarav','Grade 3','A'),('Priya Mehta','priya','Grade 3','A'),
        ('Rohan Gupta','rohan','Grade 4','B'),('Sneha Patel','sneha','Grade 4','A'),
        ('Vikram Joshi','vikram','Grade 5','A'),('Meera Singh','meera','Grade 5','B'),
        ('Arjun Kumar','arjun','Grade 3','B'),('Kavya Reddy','kavya','Grade 4','A'),
    ]
    for name, uname, grade, sec in sample:
        db.session.add(User(name=name, username=uname,
            password=generate_password_hash('student123'), role='student',
            grade=grade, section=sec))
    qs = json.dumps([
        {"id":1,"section":"Reading Comprehension","passage":"Keira asked her grandfather to read another story. He said it was time to sleep. But Keira wasn't sleepy — her toy bear Wilfred suddenly came alive!","question":"Where was Wilfred at the start?","options":["On a shelf","In bed","In a box","On the floor"],"answer":0},
        {"id":2,"section":"Reading Comprehension","passage":None,"question":"What made Wilfred open his eyes?","options":["Keira jumped","Another toy","Keira touched his foot","The light turned on"],"answer":2},
        {"id":3,"section":"Grammar","passage":"Holidays are ___ much fun. I wake up late and ___ the day playing.","question":"Best word for first blank?","options":["so","lots","such","most"],"answer":2},
        {"id":4,"section":"Grammar","passage":None,"question":"Best word for second blank?","options":["spending","spends","spend","spent"],"answer":0},
        {"id":5,"section":"Spelling","passage":"Our cat has a ___ with detective shows.","question":"Correctly spelt word?","options":["facination","fasination","facsination","fascination"],"answer":3},
        {"id":6,"section":"Vocabulary","passage":"Some people make truly beautiful cakes. I am convinced I could too if I had a good mentor.","question":"Best replacement for MENTOR?","options":["idea","skill","kitchen","teacher"],"answer":3},
    ])
    db.session.add(MockTest(name='IBT English Set 1', subject='English', grade='Grade 3', difficulty='Easy', duration=40, status='active', questions=qs))
    db.session.add(MockTest(name='IBT English Set 2', subject='English', grade='Grade 4', difficulty='Medium', duration=50, status='active', questions=qs))
    db.session.add(MockTest(name='IBT Maths Mock 1', subject='Mathematics', grade='Grade 5', difficulty='Hard', duration=45, status='draft', questions='[]'))
    db.session.add(MockTest(name='IBT Science Set 1', subject='Science', grade='Grade 3', difficulty='Easy', duration=35, status='draft', questions='[]'))
    db.session.add(MockTest(name='IBT Reasoning Set 1', subject='Reasoning', grade='Grade 4', difficulty='Medium', duration=30, status='draft', questions='[]'))
    db.session.commit()
    print("✅ Database seeded.")

# ── AUTH ──────────────────────────────────────────────────────────────────────

@app.route('/', methods=['GET','POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username','').strip()
        password = request.form.get('password','').strip()
        user = User.query.filter_by(username=username).first()
        if user and check_password_hash(user.password, password):
            session['user_id'] = user.id
            session['role']    = user.role
            session['name']    = user.name
            return redirect(url_for(f"{user.role}_dashboard"))
        flash('Invalid username or password.', 'error')
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

# ── ADMIN ─────────────────────────────────────────────────────────────────────

@app.route('/admin')
@login_required('admin')
def admin_dashboard():
    students  = User.query.filter_by(role='student').all()
    tests     = MockTest.query.all()
    results   = TestResult.query.all()
    avg_score = safe_avg([r.percent for r in results])
    recent    = sorted(results, key=lambda r: r.taken_at, reverse=True)[:8]
    return render_template('admin/dashboard.html',
        students=students, tests=tests, results=results,
        avg_score=avg_score, recent=recent, subjects=SUBJECTS, grades=GRADES)

@app.route('/admin/students', methods=['GET','POST'])
@login_required('admin')
def admin_students():
    if request.method == 'POST':
        action = request.form.get('action')
        if action == 'add':
            if User.query.filter_by(username=request.form['username']).first():
                flash('Username already exists.', 'error')
            else:
                db.session.add(User(
                    name=request.form['name'], username=request.form['username'],
                    password=generate_password_hash(request.form['password']),
                    role='student', grade=request.form['grade'], section=request.form.get('section','A')))
                db.session.commit()
                flash(f"Student {request.form['name']} added successfully.", 'success')
        elif action == 'delete':
            user = db.session.get(User, int(request.form['user_id']))
            if user:
                db.session.delete(user); db.session.commit()
                flash('Student removed.', 'success')
        elif action == 'edit':
            user = db.session.get(User, int(request.form['user_id']))
            if user:
                user.name = request.form['name']
                user.grade = request.form['grade']
                user.section = request.form.get('section','A')
                if request.form.get('password'):
                    user.password = generate_password_hash(request.form['password'])
                db.session.commit()
                flash('Student updated.', 'success')
    students = User.query.filter_by(role='student').order_by(User.grade, User.name).all()
    return render_template('admin/students.html', students=students, grades=GRADES)

@app.route('/admin/teachers', methods=['GET','POST'])
@login_required('admin')
def admin_teachers():
    if request.method == 'POST':
        action = request.form.get('action')
        if action == 'add':
            if User.query.filter_by(username=request.form['username']).first():
                flash('Username already exists.', 'error')
            else:
                db.session.add(User(name=request.form['name'], username=request.form['username'],
                    password=generate_password_hash(request.form['password']), role='teacher'))
                db.session.commit()
                flash('Teacher added.', 'success')
        elif action == 'delete':
            user = db.session.get(User, int(request.form['user_id']))
            if user: db.session.delete(user); db.session.commit()
            flash('Teacher removed.', 'success')
    teachers = User.query.filter_by(role='teacher').all()
    return render_template('admin/teachers.html', teachers=teachers)

@app.route('/admin/tests', methods=['GET','POST'])
@login_required('admin')
def admin_tests():
    if request.method == 'POST':
        action = request.form.get('action')
        if action == 'add':
            db.session.add(MockTest(
                name=request.form['name'], subject=request.form['subject'],
                grade=request.form['grade'], difficulty=request.form['difficulty'],
                duration=int(request.form['duration']), status=request.form['status']))
            db.session.commit()
            flash('Test created.', 'success')
        elif action == 'delete':
            t = db.session.get(MockTest, int(request.form['test_id']))
            if t: db.session.delete(t); db.session.commit()
            flash('Test deleted.', 'success')
        elif action == 'toggle':
            t = db.session.get(MockTest, int(request.form['test_id']))
            if t:
                t.status = 'active' if t.status == 'draft' else 'draft'
                db.session.commit()
    tests = MockTest.query.order_by(MockTest.created.desc()).all()
    return render_template('admin/tests.html', tests=tests, subjects=SUBJECTS, grades=GRADES)

@app.route('/admin/tests/<int:test_id>/questions', methods=['GET','POST'])
@login_required('admin')
def admin_questions(test_id):
    test = db.session.get(MockTest, test_id)
    if not test: flash('Test not found.','error'); return redirect(url_for('admin_tests'))
    subject_sections = SECTIONS_BY_SUBJECT.get(test.subject, ['General'])
    if request.method == 'POST':
        qs = json.loads(test.questions or '[]')
        qs.append({
            'id': max((q['id'] for q in qs), default=0) + 1,
            'section': request.form['section'],
            'passage': request.form.get('passage') or None,
            'question': request.form['question'],
            'options': [request.form.get(f'opt{i}','') for i in range(4)],
            'answer': int(request.form['answer'])
        })
        test.questions = json.dumps(qs)
        db.session.commit()
        flash('Question added.', 'success')
    questions = json.loads(test.questions or '[]')
    return render_template('admin/questions.html', test=test, questions=questions, subject_sections=subject_sections)

@app.route('/admin/questions/delete/<int:test_id>/<int:q_id>', methods=['POST'])
@login_required('admin')
def delete_question(test_id, q_id):
    test = db.session.get(MockTest, test_id)
    if test:
        qs = [q for q in json.loads(test.questions or '[]') if q['id'] != q_id]
        test.questions = json.dumps(qs)
        db.session.commit()
        flash('Question deleted.', 'success')
    return redirect(url_for('admin_questions', test_id=test_id))

@app.route('/admin/analytics')
@login_required('admin')
def admin_analytics():
    data = build_analytics()
    return render_template('admin/analytics.html', **data)

# ── TEACHER ───────────────────────────────────────────────────────────────────

@app.route('/teacher')
@login_required('teacher')
def teacher_dashboard():
    students = User.query.filter_by(role='student').all()
    results  = TestResult.query.all()
    tests    = MockTest.query.filter_by(status='active').all()
    avg_score = safe_avg([r.percent for r in results])
    recent    = sorted(results, key=lambda r: r.taken_at, reverse=True)[:6]
    return render_template('teacher/dashboard.html',
        students=students, results=results, tests=tests, avg_score=avg_score, recent=recent)

@app.route('/teacher/students')
@login_required('teacher')
def teacher_students():
    students = User.query.filter_by(role='student').order_by(User.grade, User.name).all()
    student_data = []
    for s in students:
        rs = list(s.results)
        student_data.append({
            'student': s, 'tests_taken': len(rs),
            'avg': safe_avg([r.percent for r in rs]),
        })
    return render_template('teacher/students.html', student_data=student_data)

@app.route('/teacher/analytics')
@login_required('teacher')
def teacher_analytics():
    data = build_analytics()
    return render_template('teacher/analytics.html', **data)

# ── STUDENT ───────────────────────────────────────────────────────────────────

@app.route('/student')
@login_required('student')
def student_dashboard():
    student = db.session.get(User, session['user_id'])
    results = sorted(student.results, key=lambda r: r.taken_at, reverse=True)
    tests   = MockTest.query.filter_by(status='active', grade=student.grade).all()
    avg_sc  = safe_avg([r.percent for r in results])
    return render_template('student/dashboard.html',
        student=student, results=results, tests=tests, avg_sc=avg_sc, subjects=SUBJECTS)

@app.route('/student/test/<int:test_id>')
@login_required('student')
def student_test(test_id):
    test = db.session.get(MockTest, test_id)
    if not test: return redirect(url_for('student_dashboard'))
    questions = json.loads(test.questions or '[]')
    return render_template('student/test.html', test=test, questions=questions)

@app.route('/student/submit/<int:test_id>', methods=['POST'])
@login_required('student')
def submit_test(test_id):
    test = db.session.get(MockTest, test_id)
    if not test: return jsonify({'error':'not found'}), 404
    questions  = json.loads(test.questions or '[]')
    data       = request.get_json() or {}
    answers    = data.get('answers', {})
    time_taken = data.get('time_taken', 0)
    score = 0
    section_scores = {}
    for q in questions:
        sec = q.get('section', 'General')
        section_scores.setdefault(sec, {'correct':0,'total':0})
        section_scores[sec]['total'] += 1
        if str(q['id']) in answers and answers[str(q['id'])] == q['answer']:
            score += 1
            section_scores[sec]['correct'] += 1
    total   = len(questions)
    percent = round(score/total*100, 1) if total else 0
    db.session.add(TestResult(
        student_id=session['user_id'], test_id=test_id,
        score=score, total=total, percent=percent,
        answers=json.dumps(answers), section_scores=json.dumps(section_scores),
        time_taken=time_taken))
    db.session.commit()
    return jsonify({'score':score,'total':total,'percent':percent,'section_scores':section_scores})

@app.route('/student/scores')
@login_required('student')
def student_scores():
    student = db.session.get(User, session['user_id'])
    results = sorted(student.results, key=lambda r: r.taken_at, reverse=True)
    return render_template('student/scores.html', student=student, results=results)

# ── API ───────────────────────────────────────────────────────────────────────

@app.route('/api/analytics')
@login_required('admin')
def api_analytics():
    results  = TestResult.query.all()
    by_grade = {}
    for r in results:
        g = r.student.grade or 'Unknown'
        by_grade.setdefault(g, []).append(r.percent)
    return jsonify({g: round(sum(v)/len(v),1) for g,v in by_grade.items()})

# ── MAIN ──────────────────────────────────────────────────────────────────────

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        seed_db()
    print("\n🎓 Eastern Public School — IBT Portal")
    print("   Running at → http://localhost:5000")
    print("   Admin    : admin / admin123")
    print("   Teacher  : teacher1 / teacher123")
    print("   Student  : aarav / student123\n")
    app.run(debug=True, host='0.0.0.0', port=5000)
