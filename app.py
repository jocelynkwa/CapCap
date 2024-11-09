

from flask import Flask, render_template, redirect, url_for, request, session
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from datetime import timedelta, datetime

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///lookaway_app.db'
app.config['SECRET_KEY'] = 'your_secret_key'  # Replace with a secure key
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(minutes=30)

db = SQLAlchemy(app)
bcrypt = Bcrypt(app)

@app.route('/')
def home():
    return "Welcome to the Lookaway App! Go to /register or /login to get started."

# Database Models
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), nullable=False, unique=True)
    password = db.Column(db.String(150), nullable=False)
    progress = db.relationship('Progress', backref='user', lazy=True)

class Progress(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    session_time = db.Column(db.Float, default=0)  # Store session time in seconds
    look_away_count = db.Column(db.Integer, default=0)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

# User Registration Route
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = bcrypt.generate_password_hash(request.form['password']).decode('utf-8')
        new_user = User(username=username, password=password)
        db.session.add(new_user)
        db.session.commit()
        return redirect(url_for('login'))
    return render_template('register.html')

# User Login Route
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username).first()
        if user and bcrypt.check_password_hash(user.password, password):
            session['user_id'] = user.id
            return redirect(url_for('dashboard'))
    return render_template('login.html')

# Dashboard Route
@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    user_progress = Progress.query.filter_by(user_id=session['user_id']).all()
    return render_template('dashboard.html', progress=user_progress)

# Route to start a new session
@app.route('/start_session')
def start_session():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    # Create a new session record
    new_session = Progress(
        session_time=0,
        look_away_count=0,
        user_id=session['user_id']
    )
    db.session.add(new_session)
    db.session.commit()
    
    # Store the session ID and start time in Flask session
    session['current_session_id'] = new_session.id
    session['session_start_time'] = datetime.now().timestamp()  # Track start time
    return redirect(url_for('dashboard'))

# Route to end the current session and save session time
@app.route('/end_session')
def end_session():
    if 'user_id' not in session or 'current_session_id' not in session:
        return redirect(url_for('login'))

    # Get the session data
    session_id = session['current_session_id']
    current_session = Progress.query.get(session_id)
    if current_session:
        # Calculate session duration
        session_duration = datetime.now().timestamp() - session['session_start_time']
        current_session.session_time = session_duration
        db.session.commit()

    # Clear session data
    session.pop('current_session_id', None)
    session.pop('session_start_time', None)
    
    return redirect(url_for('dashboard'))

# Route to update look-away counts (integrated with your detection script)
@app.route('/update_lookaway', methods=['POST'])
def update_lookaway():
    if 'user_id' not in session or 'current_session_id' not in session:
        return redirect(url_for('login'))

    # Get the current session
    session_id = session['current_session_id']
    current_session = Progress.query.get(session_id)
    if current_session:
        # Increment the look-away count
        current_session.look_away_count += 1
        db.session.commit()

    return 'Look-away updated', 200

# Run the app
if __name__ == '__main__':
    db.create_all()  # Initialize the database
    app.run(debug=True)
