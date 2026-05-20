from flask import Flask, render_template, request, redirect, url_for, flash
from datetime import date
from flask_sqlalchemy import SQLAlchemy
from dotenv import load_dotenv
from sqlalchemy import inspect, text
import os

load_dotenv()

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URI', 'sqlite:///app.db')
app.config['SECRET_KEY'] = os.getenv('FLASK_SECRET_KEY', 'secret')

db = SQLAlchemy(app)

DEFAULT_DINNER_DATE = date(2025, 12, 12)
DEFAULT_SIGNUP_DEADLINE = date(2025, 10, 17)
GERMAN_WEEKDAYS = (
    'Montag',
    'Dienstag',
    'Mittwoch',
    'Donnerstag',
    'Freitag',
    'Samstag',
    'Sonntag',
)


@app.context_processor
def inject_year():
    """Provide the current year to all templates."""
    return {'current_year': date.today().year}


@app.template_filter('datum')
def format_date(value):
    """Formatiere ein Datum im deutschen Kurzformat."""
    if not value:
        return ''
    return value.strftime('%d.%m.%Y')


@app.template_filter('datum_lang')
def format_date_long(value):
    """Formatiere ein Datum mit deutschem Wochentag."""
    if not value:
        return ''
    return f'{GERMAN_WEEKDAYS[value.weekday()]}, {format_date(value)}'


class Signup(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    callsign = db.Column(db.String(80))
    additional = db.Column(db.Integer, default=0)

    @property
    def persons(self):
        return 1 + (self.additional or 0)


class EventSettings(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    dinner_date = db.Column(db.Date, nullable=False, default=lambda: DEFAULT_DINNER_DATE)
    signup_deadline = db.Column(db.Date, nullable=False, default=lambda: DEFAULT_SIGNUP_DEADLINE)
    signup_enabled = db.Column(db.Boolean, nullable=False, default=True, server_default='1')


def ensure_event_settings_schema():
    inspector = inspect(db.engine)
    if not inspector.has_table(EventSettings.__tablename__):
        return

    columns = {column['name'] for column in inspector.get_columns(EventSettings.__tablename__)}
    if 'signup_enabled' in columns:
        return

    default_value = 'TRUE'
    if db.engine.dialect.name == 'sqlite':
        default_value = '1'

    db.session.execute(
        text(
            f'ALTER TABLE {EventSettings.__tablename__} '
            f'ADD COLUMN signup_enabled BOOLEAN NOT NULL DEFAULT {default_value}'
        )
    )
    db.session.commit()


def get_event_settings():
    settings = db.session.get(EventSettings, 1)
    if settings:
        return settings

    settings = EventSettings(
        id=1,
        dinner_date=DEFAULT_DINNER_DATE,
        signup_deadline=DEFAULT_SIGNUP_DEADLINE,
        signup_enabled=True,
    )
    db.session.add(settings)
    db.session.commit()
    return settings


def parse_date_field(field_name, fallback):
    value = request.form.get(field_name, '').strip()
    if not value:
        return fallback
    try:
        return date.fromisoformat(value)
    except ValueError:
        return None


def total_persons():
    result = db.session.query(db.func.sum(Signup.additional + 1)).scalar()
    return result or 0


def get_signup_status(settings):
    if not settings.signup_enabled:
        return {
            'allowed': False,
            'label': 'Anmeldung deaktiviert',
            'message': 'Die Anmeldung wurde im Adminbereich deaktiviert.',
        }

    if date.today() > settings.signup_deadline:
        return {
            'allowed': False,
            'label': 'Anmeldung geschlossen',
            'message': 'Die Anmeldefrist ist abgelaufen.',
        }

    return {
        'allowed': True,
        'label': 'Anmeldung offen',
        'message': '',
    }

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
    ensure_event_settings_schema()
    get_event_settings()

@app.route('/', methods=['GET', 'POST'])
def index():
    settings = get_event_settings()
    signup_status = get_signup_status(settings)
    signup_allowed = signup_status['allowed']
    show_hint = request.args.get('show_hint') == '1'

    if request.method == 'POST':
        if signup_allowed:
            name = request.form.get('name')
            callsign = request.form.get('callsign')
            additional = request.form.get('additional', '0')
            try:
                additional = int(additional)
            except ValueError:
                additional = 0
            additional = max(0, min(5, additional))
            if name:
                query = Signup.query.filter_by(name=name)
                if callsign:
                    query = query.filter_by(callsign=callsign)
                existing = query.first()
                if existing:
                    flash('Name oder Rufzeichen ist bereits angemeldet.')
                else:
                    signup = Signup(name=name, callsign=callsign, additional=additional)
                    db.session.add(signup)
                    db.session.commit()
                    flash(f"Vielen Dank für deine Anmeldung für {signup.persons} Person{'en' if signup.persons != 1 else ''}!")
                    return redirect(url_for('index', show_hint=1))
            else:
                flash('Name ist erforderlich.')
        else:
            flash(signup_status['message'])
        return redirect(url_for('index'))

    total = total_persons()
    return render_template('index.html', total_persons=total,
                           signup_allowed=signup_allowed, show_hint=show_hint,
                           settings=settings, signup_status=signup_status)

@app.route('/admin')
@requires_auth
def admin():
    signups = Signup.query.all()
    total = total_persons()
    settings = get_event_settings()
    return render_template('admin.html', signups=signups, total_persons=total,
                           settings=settings)


@app.route('/admin/settings', methods=['POST'])
@requires_auth
def update_settings():
    """Speichere die Termineinstellungen."""
    settings = get_event_settings()
    dinner_date = parse_date_field('dinner_date', settings.dinner_date)
    signup_deadline = parse_date_field('signup_deadline', settings.signup_deadline)

    if not dinner_date or not signup_deadline:
        flash('Bitte gültige Datumswerte eingeben.')
        return redirect(url_for('admin'))

    if signup_deadline > dinner_date:
        flash('Der Anmeldeschluss darf nicht nach dem Weihnachtsessen liegen.')
        return redirect(url_for('admin'))

    settings.dinner_date = dinner_date
    settings.signup_deadline = signup_deadline
    settings.signup_enabled = request.form.get('signup_enabled') == '1'
    db.session.commit()
    flash('Termineinstellungen wurden gespeichert.')
    return redirect(url_for('admin'))


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
