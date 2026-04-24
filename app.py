import os
import sqlite3
from flask import Flask, render_template, request, redirect, url_for, flash, session, g
from functools import wraps

app = Flask(__name__)
app.secret_key = 'super_secret_flask_key' 

DATABASE = 'hw13.db'
SCHEMA = 'schema.sql'

# Database Setup & Helper Functions
def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect(DATABASE)
        db.row_factory = sqlite3.Row # Allows dictionary-like access to rows
        # Enforce foreign keys for cascading deletes
        db.execute('PRAGMA foreign_keys = ON')
    return db

@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()

# Initialize Database on Start if it doesn't exist
if not os.path.exists(DATABASE):
    with app.app_context():
        db = get_db()
        with app.open_resource(SCHEMA, mode='r') as f:
            db.cursor().executescript(f.read())
        db.commit()

# Authentication Decorator
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('logged_in'):
            flash("Error: You must be logged in to view this page.")
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

# Root Controller: Redirects to dashboard automatically
@app.route('/')
def index():
    return redirect(url_for('dashboard'))

# First Controller: Teacher Login
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        # Data Validation: Check credentials
        if username == 'admin' and password == 'password':
            session['logged_in'] = True
            flash("Success: Logged in successfully!")
            return redirect(url_for('dashboard'))
        else:
            flash("Error: Incorrect username or password.")
            return redirect(url_for('login'))
            
    return render_template('login.html')

# Logout Controller
@app.route('/logout')
def logout():
    session.pop('logged_in', None)
    flash("Success: Logged out successfully!")
    return redirect(url_for('login'))

# Second Controller: Dashboard (View Students & Quizzes)
@app.route('/dashboard')
@login_required
def dashboard():
    db = get_db()
    students = db.execute('SELECT * FROM students').fetchall()
    quizzes = db.execute('SELECT * FROM quizzes').fetchall()
    return render_template('dashboard.html', students=students, quizzes=quizzes)

# Third Controller: Add Students
@app.route('/student/add', methods=['GET', 'POST'])
@login_required
def add_student():
    if request.method == 'POST':
        first_name = request.form.get('first_name')
        last_name = request.form.get('last_name')
        
        # Data Validation
        if not first_name or not last_name:
            flash("Error: First and last name are required.")
            return render_template('add_student.html')
            
        db = get_db()
        db.execute('INSERT INTO students (first_name, last_name) VALUES (?, ?)', (first_name, last_name))
        db.commit()
        flash("Success: Student added successfully!")
        return redirect(url_for('dashboard'))
        
    return render_template('add_student.html')

# Fourth Controller: Add Quizzes
@app.route('/quiz/add', methods=['GET', 'POST'])
@login_required
def add_quiz():
    if request.method == 'POST':
        subject = request.form.get('subject')
        num_questions = request.form.get('num_questions')
        quiz_date = request.form.get('quiz_date')
        
        # Data Validation
        if not subject or not num_questions or not quiz_date:
            flash("Error: All fields are required to add a quiz.")
            return render_template('add_quiz.html')
            
        db = get_db()
        db.execute('INSERT INTO quizzes (subject, num_questions, quiz_date) VALUES (?, ?, ?)', 
                   (subject, num_questions, quiz_date))
        db.commit()
        flash("Success: Quiz added successfully!")
        return redirect(url_for('dashboard'))
        
    return render_template('add_quiz.html')

# Fifth Controller: View Quiz Results for a Specific Student
@app.route('/student/<int:id>')
@login_required
def student_results(id):
    db = get_db()
    student = db.execute('SELECT * FROM students WHERE id = ?', (id,)).fetchone()
    if student is None:
        flash("Error: Student not found.")
        return redirect(url_for('dashboard'))
        
    # Expand Results Output utilizing JOIN
    query = '''
        SELECT quizzes.id as quiz_id, quizzes.subject, quizzes.quiz_date, results.score 
        FROM results 
        JOIN quizzes ON results.quiz_id = quizzes.id 
        WHERE results.student_id = ?
    '''
    results = db.execute(query, (id,)).fetchall()
    return render_template('student_results.html', student=student, results=results)

# Sixth Controller: Add a Student's Quiz Result
@app.route('/results/add', methods=['GET', 'POST'])
@login_required
def add_result():
    db = get_db()
    
    if request.method == 'POST':
        student_id = request.form.get('student_id')
        quiz_id = request.form.get('quiz_id')
        score = request.form.get('score')
        
        # Data Validation
        if not student_id or not quiz_id or not score:
            flash("Error: All fields are required.")
        elif not score.isdigit() or not (0 <= int(score) <= 100):
            flash("Error: Score must be an integer between 0 and 100.")
        else:
            try:
                db.execute('INSERT INTO results (student_id, quiz_id, score) VALUES (?, ?, ?)', 
                           (student_id, quiz_id, score))
                db.commit()
                flash("Success: Quiz result added successfully!")
                return redirect(url_for('dashboard'))
            except sqlite3.IntegrityError:
                flash("Error: This student already has a recorded score for this quiz.")
                
    students = db.execute('SELECT * FROM students').fetchall()
    quizzes = db.execute('SELECT * FROM quizzes').fetchall()
    return render_template('add_result.html', students=students, quizzes=quizzes)

# Anonymous View of Quiz Results
@app.route('/quiz/<int:id>/results')
def quiz_results(id):
    db = get_db()
    quiz = db.execute('SELECT * FROM quizzes WHERE id = ?', (id,)).fetchone()
    
    if quiz is None:
        flash("Error: Quiz not found.")
        return redirect(url_for('dashboard') if session.get('logged_in') else url_for('login'))
        
    query = '''
        SELECT students.id as student_id, students.first_name, students.last_name, results.score 
        FROM results 
        JOIN students ON results.student_id = students.id 
        WHERE results.quiz_id = ?
    '''
    results = db.execute(query, (id,)).fetchall()
    return render_template('quiz_results.html', quiz=quiz, results=results)

# Deletions (Handles Students, Quizzes, and Results)
@app.route('/delete/<entity>/<int:id>', methods=['POST'])
@login_required
def delete(entity, id):
    db = get_db()
    if entity == 'student':
        db.execute('DELETE FROM students WHERE id = ?', (id,))
        flash("Success: Student deleted successfully!")
    elif entity == 'quiz':
        db.execute('DELETE FROM quizzes WHERE id = ?', (id,))
        flash("Success: Quiz deleted successfully!")
    
    db.commit()
    return redirect(url_for('dashboard'))

# Web App Setup
if __name__ == '__main__':
    app.run(debug=True)