from flask import Flask, render_template, request, redirect, url_for
from datetime import date
from flask_sqlalchemy import SQLAlchemy
from dotenv import load_dotenv
import os

load_dotenv()

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URI', 'sqlite:///app.db')
app.config['SECRET_KEY'] = os.getenv('FLASK_SECRET_KEY', 'secret')

db = SQLAlchemy(app)

# Allow signups only until this date (exclusive)
SIGNUP_DEADLINE = date(2025, 10, 18)


@app.context_processor
def inject_year():
    """Provide the current year to all templates."""
    return {'current_year': date.today().year}

class Signup(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    callsign = db.Column(db.String(80))
    additional = db.Column(db.Integer, default=0)

    @property
    def persons(self):
        return 1 + (self.additional or 0)

def total_persons():
    result = db.session.query(db.func.sum(Signup.additional + 1)).scalar()
    return result or 0

def check_auth(username, password):
    return username == os.getenv('ADMIN_USERNAME') and password == os.getenv('ADMIN_PASSWORD')

def requires_auth(f):
    from functools import wraps
    from flask import request, Response
    @wraps(f)
    def decorated(*args, **kwargs):
        auth = request.authorization
        if not auth or not check_auth(auth.username, auth.password):
            return Response(
                'Authentication required', 401,
                {'WWW-Authenticate': 'Basic realm="Login Required"'}
            )
        return f(*args, **kwargs)
    return decorated


# Ensure tables are created when the application starts. The `before_first_request`
# decorator was removed in Flask 3, so we create the tables explicitly within an
# application context at import time.
with app.app_context():
    db.create_all()

@app.route('/', methods=['GET', 'POST'])
def index():
    message = None
    signup_allowed = date.today() < SIGNUP_DEADLINE
    if request.method == 'POST' and signup_allowed:
        name = request.form.get('name')
        callsign = request.form.get('callsign')
        additional = request.form.get('additional', '0')
        try:
            additional = int(additional)
        except ValueError:
            additional = 0
        additional = max(0, min(5, additional))
        if name:
            signup = Signup(name=name, callsign=callsign, additional=additional)
            db.session.add(signup)
            db.session.commit()
            message = f"Vielen Dank für deine Anmeldung für {signup.persons} Person{'en' if signup.persons != 1 else ''}!"
        else:
            message = 'Name ist erforderlich.'
    elif request.method == 'POST' and not signup_allowed:
        message = 'Die Anmeldefrist ist abgelaufen.'
    total = total_persons()
    return render_template('index.html', total_persons=total, message=message, signup_allowed=signup_allowed)

@app.route('/admin')
@requires_auth
def admin():
    signups = Signup.query.all()
    total = total_persons()
    return render_template('admin.html', signups=signups, total_persons=total)


@app.route('/admin/delete/<int:signup_id>', methods=['POST'])
@requires_auth
def delete_signup(signup_id: int):
    """Delete a signup entry."""
    signup = Signup.query.get_or_404(signup_id)
    db.session.delete(signup)
    db.session.commit()
    return redirect(url_for('admin'))


@app.route('/admin/edit/<int:signup_id>', methods=['GET', 'POST'])
@requires_auth
def edit_signup(signup_id: int):
    """Edit an existing signup."""
    signup = Signup.query.get_or_404(signup_id)
    if request.method == 'POST':
        signup.name = request.form.get('name')
        signup.callsign = request.form.get('callsign')
        additional = request.form.get('additional', '0')
        try:
            additional = int(additional)
        except ValueError:
            additional = 0
        signup.additional = max(0, min(5, additional))
        db.session.commit()
        return redirect(url_for('admin'))
    return render_template('edit.html', signup=signup)

if __name__ == '__main__':
    # Listen on all interfaces to make the application reachable from outside
    # the container or local machine. The port is changed to 8086 instead of
    # Flask's default 5000.
    app.run(debug=True, host='0.0.0.0', port=8086)
