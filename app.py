import os
import sys
from functools import wraps

# Ensure local packages in scratch/lib are discovered
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
SCRATCH_LIB = os.path.abspath(os.path.join(BASE_DIR, '..', 'lib'))
if os.path.exists(SCRATCH_LIB) and SCRATCH_LIB not in sys.path:
    sys.path.insert(0, SCRATCH_LIB)

# Ensure matplotlib writes to writable directory
os.environ['MPLCONFIGDIR'] = '/tmp'

import io
import csv
from flask import Flask, render_template, request, jsonify, send_file, redirect, url_for, session, flash
from config import Config
from models.database import (
    init_db, get_all_materials, get_material_by_slug,
    save_experiment, get_experiment_by_id, get_all_experiments, delete_experiment,
    save_hardness_experiment, get_hardness_experiment_by_id,
    get_all_hardness_experiments, delete_hardness_experiment,
    save_impact_experiment, get_impact_experiment_by_id,
    get_all_impact_experiments, delete_impact_experiment,
    get_quiz_questions, save_quiz_result,
    register_student, authenticate_student, is_student_id_available,
    validate_student_id, get_student_by_id, get_student_stats,
    get_student_dashboard_stats, get_all_students, get_admin_stats,
    get_admin_dashboard_data, delete_student_account, log_activity,
    get_admin_credentials, verify_admin_login, update_admin_credentials,
    get_admin_usage_stats, get_admin_usage_records, get_admin_record_by_id
)
from calculations.tensile import (
    analyze_tensile_data, generate_simulation_data, calculate_cross_sectional_area
)
from calculations.hardness import (
    calculate_brinell, calculate_brinell_multiple,
    calculate_rockwell, calculate_rockwell_multiple,
    generate_brinell_simulation_data, generate_rockwell_simulation_data,
    astm_e140_convert, STANDARD_MATERIALS_HARDNESS
)
from calculations.impact import (
    analyze_impact_readings, generate_impact_simulation_data,
    calculate_absorbed_energy, calculate_impact_toughness,
    IMPACT_SPECIMEN_STANDARDS, IMPACT_MATERIAL_PRESETS
)
from calculations.compression import (
    analyze_compression_data, generate_compression_simulation_data,
    calculate_cylindrical_area, calculate_compressive_stress, calculate_compressive_strain,
    COMPRESSION_SPECIMEN_STANDARDS, COMPRESSION_MATERIAL_PRESETS
)
from reports.report_generator import generate_tensile_pdf
from reports.hardness_report_generator import generate_hardness_pdf
from reports.impact_report_generator import generate_impact_pdf
from reports.compression_report_generator import generate_compression_pdf

from werkzeug.middleware.proxy_fix import ProxyFix

app = Flask(__name__)
app.config.from_object(Config)

# Private Admin Credentials & Configuration
ADMIN_USERNAME = os.environ.get('ADMIN_USERNAME', 'admin')
ADMIN_PASSWORD = os.environ.get('ADMIN_PASSWORD', 'matvlab_admin_2024')
ADMIN_URL_PATH = os.environ.get('ADMIN_URL_PATH', '/portal-admin')

# Enable ProxyFix for HTTPS termination behind cloud reverse proxies/load balancers
if app.config.get('ENABLE_PROXY_FIX', True):
    app.wsgi_app = ProxyFix(
        app.wsgi_app,
        x_for=1,
        x_proto=1,
        x_host=1,
        x_prefix=1
    )

# Auto-initialize database on startup
with app.app_context():
    init_db()

# Access Control Decorators
def login_required(f):
    """Pass-through decorator; student-facing laboratory is open and requires no login."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    """Guards private administrative endpoints."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('is_admin'):
            return redirect(url_for('admin_login', next=request.path))
        return f(*args, **kwargs)
    return decorated_function

# Context processor to make student session & admin status available globally
@app.context_processor
def inject_student_context():
    name = session.get('student_name')
    university = session.get('university')
    student = None
    if name:
        student = {
            'name': name,
            'university': university or 'Engineering Institution',
            'session_id': session.get('session_id')
        }
    return {
        'current_student': student,
        'is_logged_in': True,  # Full laboratory navigation is permanently visible
        'is_admin': bool(session.get('is_admin'))
    }

# ==========================================
# HOME PAGE & CORE LABORATORY NAVIGATION
# ==========================================

@app.route('/')
def index():
    """
    Main Laboratory Home page:
    Directly opens the MAT-VLAB Home page without any login screen,
    account creation, or gatekeeping identification form.
    """
    return render_template('index.html', active_page='home')

@app.route('/home')
def home():
    """Alias for laboratory home page."""
    return render_template('index.html', active_page='home')

@app.route('/start-session', methods=['GET', 'POST'])
def start_session():
    """Optional session identification setter for laboratory reports; redirects directly to Home."""
    if request.method == 'POST':
        import secrets
        student_name = request.form.get('student_name', '').strip()
        university = request.form.get('university', '').strip()
        if student_name:
            session['student_name'] = student_name
        if university:
            session['university'] = university
        if not session.get('session_id'):
            session['session_id'] = secrets.token_hex(16)
    return redirect(url_for('index'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    """Student registration eliminated; redirect cleanly to Home page."""
    return redirect(url_for('index'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    """Student login eliminated; redirect cleanly to Home page."""
    return redirect(url_for('index'))

@app.route('/logout')
def logout():
    """Clears any optional session identifiers and redirects to Home."""
    session.pop('student_name', None)
    session.pop('university', None)
    session.pop('session_id', None)
    session.pop('student_id', None)
    return redirect(url_for('index'))

@app.route('/dashboard')
def dashboard():
    """Direct route to laboratory home."""
    return redirect(url_for('index'))

# ==========================================
# PRIVATE ADMIN SYSTEM (NON-OBVIOUS ROUTE)
# ==========================================

@app.route('/portal-admin/login', methods=['GET', 'POST'])
@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    """Dedicated private admin login page."""
    if session.get('is_admin'):
        return redirect(url_for('admin_dashboard'))

    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '').strip()

        success, message = verify_admin_login(username, password)
        if success:
            session['is_admin'] = True
            session['admin_username'] = username
            flash("Administrator session authenticated.", "success")
            next_url = request.args.get('next') or url_for('admin_dashboard')
            return redirect(next_url)
        else:
            flash(message, "danger")
            return render_template('admin_login.html', form_data={'username': username})

    return render_template('admin_login.html', form_data={})

@app.route('/portal-admin/logout')
@app.route('/admin/logout')
def admin_logout():
    session.pop('is_admin', None)
    session.pop('admin_username', None)
    flash("Administrator session terminated.", "info")
    return redirect(url_for('admin_login'))

@app.route('/portal-admin')
@app.route('/portal-admin/records')
@app.route('/admin')
@app.route('/admin/records')
@admin_required
def admin_dashboard():
    """Private Admin Dashboard with system telemetry and experiment usage records."""
    search_q = request.args.get('q', '').strip()
    selected_uni = request.args.get('university', '').strip()
    selected_type = request.args.get('type', '').strip()
    selected_mode = request.args.get('mode', '').strip()
    selected_date = request.args.get('date', '').strip()

    data = get_admin_dashboard_data(
        search_query=search_q if search_q else None,
        university=selected_uni if selected_uni and selected_uni != 'ALL' else None,
        exp_type=selected_type if selected_type and selected_type != 'ALL' else None,
        mode=selected_mode if selected_mode and selected_mode != 'ALL' else None,
        date_query=selected_date if selected_date else None
    )

    admin_creds = get_admin_credentials()

    return render_template(
        'admin.html',
        active_page='admin',
        stats=data,
        records=data['records'],
        total_records=data['total_records_count'],
        search_q=search_q,
        selected_uni=selected_uni,
        selected_type=selected_type,
        selected_mode=selected_mode,
        selected_date=selected_date,
        admin_creds=admin_creds
    )

@app.route('/portal-admin/record/<table_type>/<int:record_id>')
@app.route('/admin/record/<table_type>/<int:record_id>')
@admin_required
def admin_record_detail_json(table_type, record_id):
    """Returns experiment record JSON for admin modal inspection."""
    rec = get_admin_record_by_id(table_type, record_id)
    if not rec:
        return jsonify({'error': 'Record not found'}), 404
    return jsonify(rec)

@app.route('/portal-admin/update-credentials', methods=['POST'])
@app.route('/admin/update-credentials', methods=['POST'])
@admin_required
def admin_update_credentials_route():
    """Allows admin to update their username and password directly."""
    current_password = request.form.get('current_password', '').strip()
    new_username = request.form.get('new_username', '').strip()
    new_password = request.form.get('new_password', '').strip()
    confirm_password = request.form.get('confirm_password', '').strip()

    if not new_username:
        flash("Username cannot be empty.", "danger")
        return redirect(url_for('admin_dashboard'))

    if not new_password or len(new_password) < 4:
        flash("New password must be at least 4 characters.", "danger")
        return redirect(url_for('admin_dashboard'))

    if new_password != confirm_password:
        flash("New password and confirmation do not match.", "danger")
        return redirect(url_for('admin_dashboard'))

    success, msg = update_admin_credentials(new_username, new_password, current_password=current_password)
    if success:
        session['admin_username'] = new_username
        flash(f"Administrator credentials updated successfully! New login username: {new_username}", "success")
    else:
        flash(msg, "danger")

    return redirect(url_for('admin_dashboard'))

@app.route('/portal-admin/export-csv')
@app.route('/admin/export-csv')
@admin_required
def admin_export_csv():
    """Exports full experiment usage records to CSV."""
    records = get_admin_usage_records()
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['Record ID', 'Experiment Type', 'Title', 'Mode', 'Material', 'Student Name', 'University', 'Created At', 'Key Result', 'Readings Count'])
    for r in records:
        writer.writerow([
            r.get('id', ''),
            r.get('exp_type', ''),
            r.get('title', ''),
            r.get('mode', ''),
            r.get('material_name', ''),
            r.get('student_name', ''),
            r.get('university', ''),
            r.get('created_at', ''),
            r.get('key_result', ''),
            r.get('readings_count', 0)
        ])

    mem = io.BytesIO()
    mem.write(output.getvalue().encode('utf-8'))
    mem.seek(0)
    output.close()

    return send_file(
        mem,
        mimetype='text/csv',
        as_attachment=True,
        download_name='mat_vlab_experiment_usage_records.csv'
    )

@app.route('/portal-admin/student/<student_id>/delete', methods=['POST'])
@app.route('/admin/student/<student_id>/delete', methods=['POST'])
@admin_required
def admin_delete_student(student_id):
    success = delete_student_account(student_id)
    if success:
        flash(f"Student account '{student_id}' has been removed successfully.", "warning")
    else:
        flash(f"Failed to remove student account '{student_id}'.", "danger")
    return redirect(url_for('admin_dashboard'))

# ==========================================
# PROTECTED LABORATORY WEB PAGES
# ==========================================

@app.route('/experiments')
@login_required
def experiments():
    return render_template('experiments.html', active_page='experiments')

@app.route('/experiments/tensile')
@login_required
def tensile_hub():
    return render_template('tensile.html', active_page='tensile')

@app.route('/experiments/hardness')
@login_required
def hardness_hub():
    """Hardness Testing Hub & Method Selector (Brinell vs Rockwell)."""
    return render_template('hardness_hub.html', active_page='hardness')

@app.route('/experiments/hardness/brinell')
@app.route('/experiments/brinell')
@login_required
def hardness_brinell():
    """Brinell Hardness Testing Laboratory (13 structured pedagogical sections)."""
    questions = get_quiz_questions(experiment_type='brinell', limit=10)
    sid = session.get('student_id')
    if sid:
        log_activity(sid, 'EXPERIMENT_START', 'Brinell Hardness Lab')
    return render_template('brinell.html', active_page='brinell', questions=questions)

@app.route('/experiments/hardness/rockwell')
@app.route('/experiments/rockwell')
@login_required
def hardness_rockwell():
    """Rockwell Hardness Testing Laboratory (13 structured pedagogical sections)."""
    questions = get_quiz_questions(experiment_type='rockwell', limit=10)
    sid = session.get('student_id')
    if sid:
        log_activity(sid, 'EXPERIMENT_START', 'Rockwell Hardness Lab')
    return render_template('rockwell.html', active_page='rockwell', questions=questions)

@app.route('/experiments/hardness/compare')
@login_required
def hardness_compare():
    """Comparative Hardness & ASTM E140 Equivalence Tool."""
    sid = session.get('student_id')
    saved_list = get_all_hardness_experiments(student_id=sid)
    return render_template('hardness_compare.html', active_page='hardness_compare', saved_experiments=saved_list)

@app.route('/experiments/impact')
@login_required
def impact_hub():
    """Impact Testing Laboratory (ASTM E23 / ISO 148-1 Charpy & Izod)."""
    questions = get_quiz_questions(experiment_type='impact', limit=10)
    sid = session.get('student_id')
    if sid:
        log_activity(sid, 'EXPERIMENT_START', 'Charpy Impact Lab')
    return render_template('impact.html', active_page='impact', questions=questions)

app.add_url_rule('/experiments/impact', endpoint='impact_test', view_func=impact_hub)

@app.route('/experiments/compression')
@login_required
def compression_hub():
    """Uniaxial Compression Testing Laboratory (ASTM E9 / ISO 13314)."""
    questions = get_quiz_questions(experiment_type='compression', limit=10)
    sid = session.get('student_id')
    if sid:
        log_activity(sid, 'EXPERIMENT_START', 'Compression Testing Lab')
    return render_template('compression.html', active_page='compression', questions=questions)

app.add_url_rule('/experiments/compression', endpoint='compression_test', view_func=compression_hub)

@app.route('/simulation')
@login_required
def simulation():
    sid = session.get('student_id')
    if sid:
        log_activity(sid, 'EXPERIMENT_START', 'Virtual Simulation Mode')
    return render_template('simulation.html', active_page='simulation')

@app.route('/manual')
@login_required
def manual_entry():
    sid = session.get('student_id')
    if sid:
        log_activity(sid, 'EXPERIMENT_START', 'Manual Data Entry Mode')
    return render_template('manual_entry.html', active_page='manual')

@app.route('/results')
@login_required
def results():
    return render_template('results.html', active_page='results')

@app.route('/materials')
@login_required
def materials():
    mat_list = get_all_materials()
    return render_template('materials.html', active_page='materials', materials=mat_list)

@app.route('/compare')
@login_required
def compare():
    mat_list = get_all_materials()
    sess_id = session.get('session_id')
    s_name = session.get('student_name')
    saved_list = get_all_experiments(session_id=sess_id, student_name=s_name)
    return render_template('compare.html', active_page='compare', materials=mat_list, saved_experiments=saved_list)

@app.route('/my-experiments')
def my_experiments():
    sess_id = session.get('session_id')
    s_name = session.get('student_name')
    exp_list = get_all_experiments(session_id=sess_id, student_name=s_name)
    hardness_list = get_all_hardness_experiments(session_id=sess_id, student_name=s_name)
    return render_template(
        'my_experiments.html',
        active_page='my_experiments',
        experiments=exp_list,
        hardness_experiments=hardness_list
    )

@app.route('/experiments/<int:experiment_id>')
@login_required
def view_experiment(experiment_id):
    exp = get_experiment_by_id(experiment_id)
    if not exp:
        return redirect(url_for('my_experiments'))
    return render_template('results.html', active_page='results', preloaded_experiment=exp)

@app.route('/quizzes')
@app.route('/quiz')
@login_required
def quizzes():
    exp_type = request.args.get('type', 'tensile').lower()
    if exp_type not in ['tensile', 'brinell', 'rockwell']:
        exp_type = 'tensile'
    q_list = get_quiz_questions(experiment_type=exp_type, limit=10)
    return render_template('quizzes.html', active_page='quizzes', questions=q_list, experiment_type=exp_type)

@app.route('/about')
@login_required
def about():
    return render_template('about.html', active_page='about')

# ==========================================
# REST API ENDPOINTS
# ==========================================

@app.route('/api/calculate', methods=['POST'])
def api_calculate():
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'Missing JSON request payload.'}), 400

        d0 = data.get('original_diameter')
        l0 = data.get('original_gauge_length')
        readings = data.get('readings', [])
        lf = data.get('final_gauge_length')
        df = data.get('final_diameter')
        mat_name = data.get('material_name')

        analysis = analyze_tensile_data(
            original_diameter_mm=d0,
            original_gauge_length_mm=l0,
            readings=readings,
            final_gauge_length_mm=lf,
            final_diameter_mm=df,
            material_name=mat_name
        )
        return jsonify(analysis)
    except ValueError as ve:
        return jsonify({'error': str(ve)}), 400
    except Exception as e:
        return jsonify({'error': f'An unexpected calculation error occurred: {str(e)}'}), 500

@app.route('/api/simulation-data', methods=['GET'])
def api_simulation_data():
    try:
        material_slug = request.args.get('material', 'mild-steel')
        diameter = float(request.args.get('diameter', 10.0))
        gauge_length = float(request.args.get('gauge_length', 50.0))

        sim = generate_simulation_data(
            material_slug=material_slug,
            diameter_mm=diameter,
            gauge_length_mm=gauge_length
        )
        return jsonify(sim)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# ==========================================
# STUDENT REST API ENDPOINTS
# ==========================================

@app.route('/api/student/check-id', methods=['GET'])
def api_check_student_id():
    sid = request.args.get('student_id') or request.args.get('id', '')
    is_avail, message = is_student_id_available(sid)
    return jsonify({
        'available': is_avail,
        'message': message,
        'student_id': sid
    })

@app.route('/api/student/register', methods=['POST'])
def api_student_register():
    try:
        data = request.get_json() or {}
        name = data.get('name', '').strip()
        course = data.get('course', '').strip()
        university = data.get('university', '').strip()
        student_id = data.get('student_id', '').strip()
        pin = data.get('pin', '').strip()

        student = register_student(name, course, university, student_id, pin)
        return jsonify({'success': True, 'student': student})
    except ValueError as ve:
        return jsonify({'success': False, 'error': str(ve)}), 400
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/student/login', methods=['POST'])
def api_student_login():
    try:
        data = request.get_json() or {}
        student_id = data.get('student_id', '').strip()
        pin = data.get('pin', '').strip()
        university = data.get('university', '').strip()

        student = authenticate_student(
            student_id=student_id,
            pin=pin if pin else None,
            university=university if not pin else None,
            ip_address=request.remote_addr,
            user_agent=request.user_agent.string
        )
        session['student_id'] = student['student_id']
        session['student_name'] = student['name']
        session['course'] = student['course']
        session['university'] = student['university']
        return jsonify({'success': True, 'student': student})
    except ValueError as ve:
        return jsonify({'success': False, 'error': str(ve)}), 400
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/student/me', methods=['GET'])
def api_student_me():
    student_id = session.get('student_id')
    if not student_id:
        return jsonify({'logged_in': False, 'student': None})
    student = get_student_by_id(student_id)
    if not student:
        return jsonify({'logged_in': False, 'student': None})
    return jsonify({'logged_in': True, 'student': student})

@app.route('/api/save', methods=['POST'])
def api_save():
    try:
        import secrets
        data = request.get_json()
        if not data:
            return jsonify({'error': 'Missing payload to save.'}), 400

        if not session.get('session_id'):
            session['session_id'] = secrets.token_hex(16)

        student_id = data.get('student_id') or session.get('student_id')
        student_name = data.get('student_name') or session.get('student_name') or 'Student Investigator'
        university = data.get('university') or session.get('university') or 'Materials Testing Laboratory'
        session_id = data.get('session_id') or session.get('session_id')

        experiment_id = save_experiment(
            data,
            student_id=student_id,
            student_name=student_name,
            university=university,
            session_id=session_id
        )
        log_activity(
            student_id=student_id,
            activity_type='EXPERIMENT_SAVE',
            details=f"Experiment #{experiment_id} saved ({data.get('material_name', 'Tensile')})",
            student_name=student_name,
            university=university,
            session_id=session_id
        )
        return jsonify({'success': True, 'experiment_id': experiment_id})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/experiment/<int:experiment_id>', methods=['GET', 'DELETE'])
def api_experiment_detail(experiment_id):
    if request.method == 'DELETE':
        student_id = session.get('student_id')
        success = delete_experiment(experiment_id, student_id=student_id)
        return jsonify({'success': success})

    exp = get_experiment_by_id(experiment_id)
    if not exp:
        return jsonify({'error': 'Experiment not found'}), 404
    return jsonify(exp)

@app.route('/api/hardness/quiz/submit', methods=['POST'])
@app.route('/api/quiz/submit', methods=['POST'])
def api_quiz_submit():
    try:
        data = request.get_json()
        exp_type = data.get('experiment_type', 'tensile')
        score = int(data.get('score', 0))
        total = int(data.get('total_questions', 10))
        exp_id = data.get('experiment_id')
        sid = session.get('student_id')
        s_name = session.get('student_name') or data.get('student_name')
        uni = session.get('university') or data.get('university')
        sess_id = session.get('session_id') or data.get('session_id')

        res_id = save_quiz_result(
            exp_id, exp_type, score, total,
            student_id=sid,
            student_name=s_name,
            university=uni,
            session_id=sess_id
        )
        log_activity(
            student_id=sid,
            activity_type='QUIZ_ATTEMPT',
            details=f"Quiz {exp_type}: Score {score}/{total}",
            student_name=s_name,
            university=uni,
            session_id=sess_id
        )
        return jsonify({'success': True, 'result_id': res_id})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# ==========================================
# HARDNESS TESTING REST API & PDF ROUTES
# ==========================================

@app.route('/api/hardness/simulation-data')
def api_hardness_simulation_data():
    """
    Returns realistic physics-based simulation trials for Brinell or Rockwell.
    Query parameters:
      - method: 'brinell' or 'rockwell'
      - material: material slug
      - ball_diameter / ball_d_mm: for brinell (default 10.0)
      - load / load_kgf: for brinell (default 3000.0)
      - scale: for rockwell ('HRC', 'HRB', 'HRA', default 'HRC')
      - num_trials: number of indentations (default 3)
    """
    try:
        method = request.args.get('method', 'brinell').lower()
        material = request.args.get('material', 'mild_steel')
        num_trials = int(request.args.get('num_trials', 3))

        if method == 'brinell':
            ball_d = float(request.args.get('ball_diameter') or request.args.get('ball_d_mm') or 10.0)
            load = float(request.args.get('load') or request.args.get('load_kgf') or 3000.0)
            data = generate_brinell_simulation_data(material_slug=material, ball_d_mm=ball_d, load_kgf=load, num_trials=num_trials)
            resp = dict(data)
            resp['success'] = True
            resp['data'] = data
            return jsonify(resp)
        elif method == 'rockwell':
            scale = request.args.get('scale', 'HRC').upper()
            data = generate_rockwell_simulation_data(material_slug=material, scale=scale, num_trials=num_trials)
            resp = dict(data)
            resp['success'] = True
            resp['data'] = data
            return jsonify(resp)
        else:
            return jsonify({'error': f'Unsupported hardness method: {method}', 'success': False}), 400
    except Exception as e:
        return jsonify({'error': str(e), 'success': False}), 500

@app.route('/api/hardness/calculate', methods=['POST'])
def api_hardness_calculate():
    """Direct calculation engine for Brinell and Rockwell multi-trial readings."""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'Missing calculation payload'}), 400

        method = data.get('method', 'BRINELL').upper()
        readings = data.get('readings', [])

        if method == 'BRINELL':
            load = float(data.get('load_kgf', 3000.0))
            ball_d = float(data.get('ball_d_mm', 10.0))
            result = calculate_brinell_multiple(load, ball_d, readings)
            return jsonify({'success': True, 'result': result})
        elif method == 'ROCKWELL':
            scale = data.get('scale', 'HRC').upper()
            result = calculate_rockwell_multiple(scale, readings)
            return jsonify({'success': True, 'result': result})
        else:
            return jsonify({'error': f'Unknown method {method}'}), 400
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/hardness/save', methods=['POST'])
def api_hardness_save():
    """Persists a Brinell or Rockwell experiment to the database."""
    try:
        import secrets
        data = request.get_json()
        if not data:
            return jsonify({'error': 'Missing payload to save.'}), 400

        if not session.get('session_id'):
            session['session_id'] = secrets.token_hex(16)

        student_id = data.get('student_id') or session.get('student_id')
        student_name = data.get('student_name') or session.get('student_name') or 'Student Investigator'
        university = data.get('university') or session.get('university') or 'Materials Testing Laboratory'
        session_id = data.get('session_id') or session.get('session_id')

        exp_id = save_hardness_experiment(
            data,
            student_id=student_id,
            student_name=student_name,
            university=university,
            session_id=session_id
        )
        return jsonify({'success': True, 'experiment_id': exp_id})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/hardness/experiment/<int:experiment_id>', methods=['GET', 'DELETE'])
def api_hardness_experiment_detail(experiment_id):
    """Fetch or delete a saved hardness experiment."""
    if request.method == 'DELETE':
        student_id = session.get('student_id')
        success = delete_hardness_experiment(experiment_id, student_id=student_id)
        return jsonify({'success': success})

    exp = get_hardness_experiment_by_id(experiment_id)
    if not exp:
        return jsonify({'error': 'Hardness experiment not found'}), 404
    return jsonify(exp)

@app.route('/hardness/report/<int:experiment_id>')
@app.route('/api/hardness/download-report/<int:experiment_id>')
def download_hardness_report_by_id(experiment_id):
    """Generates and serves the certified PDF laboratory report for a hardness experiment."""
    exp = get_hardness_experiment_by_id(experiment_id)
    if not exp:
        return "Hardness experiment not found", 404

    exp['student_name'] = exp.get('student_name') or session.get('student_name') or 'Materials Science Student'
    exp['student_university'] = exp.get('university') or session.get('university') or 'Engineering Institute'
    exp['student_course'] = exp.get('course') or session.get('course') or 'Materials Testing Laboratory'
    exp['student_id'] = exp.get('student_id') or 'Session'

    log_activity(
        student_id=exp.get('student_id'),
        activity_type='REPORT_DOWNLOAD',
        details=f"Downloaded PDF for Hardness Exp #{experiment_id}",
        student_name=exp['student_name'],
        university=exp['student_university'],
        session_id=session.get('session_id')
    )

    pdf_buffer = generate_hardness_pdf(exp)
    clean_mat = (exp.get('material_name', 'metal')).replace(' ', '_').replace('/', '_')
    filename = f"MAT_VLAB_{exp.get('method', 'HARDNESS')}_Exp{experiment_id}_{clean_mat}.pdf"
    return send_file(
        pdf_buffer,
        mimetype='application/pdf',
        as_attachment=True,
        download_name=filename
    )

@app.route('/api/hardness/generate-pdf', methods=['POST'])
def api_hardness_generate_pdf():
    """Generates a certified Hardness PDF report on-the-fly from client data."""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'Missing data for PDF generation'}), 400

        data['student_name'] = data.get('student_name') or session.get('student_name') or 'Materials Science Student'
        data['student_university'] = data.get('university') or session.get('university') or 'Engineering Institute'
        data['student_course'] = data.get('course') or session.get('course') or 'Materials Testing Laboratory'
        data['student_id'] = data.get('student_id') or 'Session'

        log_activity(
            student_id=data.get('student_id'),
            activity_type='REPORT_DOWNLOAD',
            details=f"Generated Hardness PDF report for {data.get('material_name', 'Metal')}",
            student_name=data['student_name'],
            university=data['student_university'],
            session_id=session.get('session_id')
        )

        pdf_buffer = generate_hardness_pdf(data)
        clean_mat = (data.get('material_name', 'metal')).replace(' ', '_').replace('/', '_')
        filename = f"MAT_VLAB_{data.get('method', 'HARDNESS')}_{clean_mat}.pdf"
        return send_file(
            pdf_buffer,
            mimetype='application/pdf',
            as_attachment=True,
            download_name=filename
        )
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/download-report/<int:experiment_id>')
def download_report_by_id(experiment_id):
    exp = get_experiment_by_id(experiment_id)
    if not exp:
        return "Experiment not found", 404

    exp['student_name'] = exp.get('student_name') or session.get('student_name') or 'Materials Science Student'
    exp['student_university'] = exp.get('university') or session.get('university') or 'Engineering Institute'
    exp['student_course'] = exp.get('course') or session.get('course') or 'Materials Testing Laboratory'
    exp['student_id'] = exp.get('student_id') or 'Session'

    log_activity(
        student_id=exp.get('student_id'),
        activity_type='REPORT_DOWNLOAD',
        details=f"Downloaded PDF for Exp #{experiment_id}",
        student_name=exp['student_name'],
        university=exp['student_university'],
        session_id=session.get('session_id')
    )

    pdf_buffer = generate_tensile_pdf(exp)
    filename = f"MAT_VLAB_Report_Exp{experiment_id}_{(exp.get('material_name', 'tensile')).replace(' ', '_')}.pdf"
    return send_file(
        pdf_buffer,
        mimetype='application/pdf',
        as_attachment=True,
        download_name=filename
    )

@app.route('/api/generate-pdf', methods=['POST'])
def api_generate_pdf():
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'Missing data for PDF generation'}), 400

        data['student_name'] = data.get('student_name') or session.get('student_name') or 'Materials Science Student'
        data['student_university'] = data.get('university') or session.get('university') or 'Engineering Institute'
        data['student_course'] = data.get('course') or session.get('course') or 'Materials Testing Laboratory'
        data['student_id'] = data.get('student_id') or 'Session'

        log_activity(
            student_id=data.get('student_id'),
            activity_type='REPORT_DOWNLOAD',
            details=f"Generated PDF report for {data.get('material_name', 'Tensile')}",
            student_name=data['student_name'],
            university=data['student_university'],
            session_id=session.get('session_id')
        )

        pdf_buffer = generate_tensile_pdf(data)
        filename = f"MAT_VLAB_Report_{(data.get('material_name', 'tensile')).replace(' ', '_')}.pdf"
        return send_file(
            pdf_buffer,
            mimetype='application/pdf',
            as_attachment=True,
            download_name=filename
        )
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/download-sample-csv')
def download_sample_csv_endpoint():
    csv_path = os.path.join(BASE_DIR, 'data', 'sample_tensile_data.csv')
    return send_file(
        csv_path,
        mimetype='text/csv',
        as_attachment=True,
        download_name='mat_vlab_sample_tensile.csv'
    )

# ==========================================
# IMPACT TESTING REST API & PDF ROUTES
# ==========================================

@app.route('/api/impact/simulation-data', methods=['GET'])
@app.route('/api/impact/simulate', methods=['GET', 'POST'])
def api_impact_simulate():
    """Generates realistic physics-based Charpy / Izod simulation data across temperatures."""
    try:
        if request.method == 'POST':
            payload = request.get_json() or {}
        else:
            payload = request.args

        mat_slug = payload.get('material_slug', payload.get('material', 'mild-steel'))
        spec_type = payload.get('specimen_type', 'charpy_v')
        temp_c = float(payload.get('temperature_c', payload.get('temperature', 23.0)))
        num_trials = int(payload.get('num_trials', 3))
        cap_j = float(payload.get('machine_capacity_j', 300.0))

        data = generate_impact_simulation_data(
            material_slug=mat_slug,
            specimen_type=spec_type,
            temperature_c=temp_c,
            num_trials=num_trials,
            machine_capacity_j=cap_j
        )
        resp = dict(data)
        resp['success'] = True
        resp['data'] = data
        return jsonify(resp)
    except Exception as e:
        return jsonify({'error': str(e), 'success': False}), 500

@app.route('/api/impact/calculate', methods=['POST'])
def api_impact_calculate():
    """Calculates absorbed energy, notch toughness, and statistics from user readings."""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'Missing calculation payload'}), 400

        readings = data.get('readings', [])
        spec_type = data.get('specimen_type', 'charpy_v')
        mat_name = data.get('material_name', 'Metallic Specimen')
        temp_c = float(data.get('test_temperature_c', data.get('temperature_c', 23.0)))
        cap_j = float(data.get('machine_capacity_j', 300.0))
        fl = float(data.get('friction_loss_j', 0.5))

        result = analyze_impact_readings(
            readings=readings,
            specimen_type=spec_type,
            material_name=mat_name,
            test_temperature_c=temp_c,
            initial_energy_capacity_j=cap_j,
            friction_loss_j=fl
        )
        return jsonify({'success': True, 'result': result, **result})
    except Exception as e:
        return jsonify({'error': str(e), 'success': False}), 500

@app.route('/api/impact/save', methods=['POST'])
def api_impact_save():
    """Persists an Impact experiment to the database."""
    try:
        import secrets
        data = request.get_json()
        if not data:
            return jsonify({'error': 'Missing payload to save.'}), 400

        if not session.get('session_id'):
            session['session_id'] = secrets.token_hex(16)

        student_id = data.get('student_id') or session.get('student_id')
        student_name = data.get('student_name') or session.get('student_name') or 'Student Investigator'
        university = data.get('university') or session.get('university') or 'Materials Testing Laboratory'
        session_id = data.get('session_id') or session.get('session_id')

        exp_id = save_impact_experiment(
            data,
            student_id=student_id,
            student_name=student_name,
            university=university,
            session_id=session_id
        )
        return jsonify({'success': True, 'experiment_id': exp_id})
    except Exception as e:
        return jsonify({'error': str(e), 'success': False}), 500

@app.route('/impact/report/<int:experiment_id>')
@app.route('/api/impact/download-report/<int:experiment_id>')
def download_impact_report_by_id(experiment_id):
    """Generates and serves the certified PDF report for an impact experiment."""
    exp = get_impact_experiment_by_id(experiment_id)
    if not exp:
        return "Impact experiment not found", 404

    exp['student_name'] = exp.get('student_name') or session.get('student_name') or 'Materials Science Student'
    exp['student_university'] = exp.get('university') or session.get('university') or 'Engineering Institute'
    exp['student_course'] = exp.get('course') or session.get('course') or 'Materials Testing Laboratory'
    exp['student_id'] = exp.get('student_id') or 'Session'

    log_activity(
        student_id=exp.get('student_id'),
        activity_type='REPORT_DOWNLOAD',
        details=f"Downloaded PDF for Impact Exp #{experiment_id}",
        student_name=exp['student_name'],
        university=exp['student_university'],
        session_id=session.get('session_id')
    )

    pdf_buffer = generate_impact_pdf(exp)
    clean_mat = (exp.get('material_name', 'metal')).replace(' ', '_').replace('/', '_')
    filename = f"MAT_VLAB_Impact_Exp{experiment_id}_{clean_mat}.pdf"
    return send_file(
        pdf_buffer,
        mimetype='application/pdf',
        as_attachment=True,
        download_name=filename
    )

@app.route('/api/impact/generate-pdf', methods=['POST'])
def api_impact_generate_pdf():
    """Generates a certified Impact PDF report on-the-fly from client payload."""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'Missing data for PDF generation'}), 400

        data['student_name'] = data.get('student_name') or session.get('student_name') or 'Materials Science Student'
        data['student_university'] = data.get('university') or session.get('university') or 'Engineering Institute'
        data['student_course'] = data.get('course') or session.get('course') or 'Materials Testing Laboratory'
        data['student_id'] = data.get('student_id') or 'Session'

        log_activity(
            student_id=data.get('student_id'),
            activity_type='REPORT_DOWNLOAD',
            details=f"Generated Impact PDF report for {data.get('material_name', 'Metal')}",
            student_name=data['student_name'],
            university=data['student_university'],
            session_id=session.get('session_id')
        )

        pdf_buffer = generate_impact_pdf(data)
        clean_mat = (data.get('material_name', 'metal')).replace(' ', '_').replace('/', '_')
        filename = f"MAT_VLAB_Impact_{clean_mat}.pdf"
        return send_file(
            pdf_buffer,
            mimetype='application/pdf',
            as_attachment=True,
            download_name=filename
        )
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# ==========================================
# COMPRESSION TESTING REST API & PDF ROUTES
# ==========================================

@app.route('/api/compression/simulation-data', methods=['GET'])
@app.route('/api/compression/simulate', methods=['GET', 'POST'])
def api_compression_simulate():
    """Generates realistic physics-based compression simulation data."""
    try:
        if request.method == 'POST':
            payload = request.get_json() or {}
        else:
            payload = request.args

        mat_slug = payload.get('material_slug', payload.get('material', 'mild-steel'))
        d0 = float(payload.get('diameter_mm', payload.get('original_diameter', 15.0)))
        h0 = float(payload.get('height_mm', payload.get('original_height', 30.0)))
        num_pts = int(payload.get('num_points', 35))

        data = generate_compression_simulation_data(
            material_slug=mat_slug,
            diameter_mm=d0,
            height_mm=h0,
            num_points=num_pts
        )
        resp = dict(data)
        resp['success'] = True
        resp['data'] = data
        return jsonify(resp)
    except Exception as e:
        return jsonify({'error': str(e), 'success': False}), 500

@app.route('/api/compression/calculate', methods=['POST'])
def api_compression_calculate():
    """Calculates compressive stress, strain, modulus, and proof stress from readings."""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'Missing calculation payload'}), 400

        d0 = float(data.get('original_diameter_mm', data.get('original_diameter', 15.0)))
        h0 = float(data.get('original_height_mm', data.get('original_height', 30.0)))
        readings = data.get('readings', [])
        fh = float(data['final_height_mm']) if data.get('final_height_mm') else None
        f_mid_d = float(data['final_mid_diameter_mm']) if data.get('final_mid_diameter_mm') else None
        f_end_d = float(data['final_end_diameter_mm']) if data.get('final_end_diameter_mm') else None
        mat_name = data.get('material_name', 'Metallic Specimen')

        result = analyze_compression_data(
            original_diameter_mm=d0,
            original_height_mm=h0,
            readings=readings,
            final_height_mm=fh,
            final_mid_diameter_mm=f_mid_d,
            final_end_diameter_mm=f_end_d,
            material_name=mat_name
        )
        return jsonify({'success': True, 'result': result, **result})
    except Exception as e:
        return jsonify({'error': str(e), 'success': False}), 500

@app.route('/api/compression/save', methods=['POST'])
def api_compression_save():
    """Persists a Compression experiment to the database using polymorphic experiments table."""
    try:
        import secrets
        data = request.get_json()
        if not data:
            return jsonify({'error': 'Missing payload to save.'}), 400

        if not session.get('session_id'):
            session['session_id'] = secrets.token_hex(16)

        data['experiment_type'] = 'compression'
        student_id = data.get('student_id') or session.get('student_id')
        student_name = data.get('student_name') or session.get('student_name') or 'Student Investigator'
        university = data.get('university') or session.get('university') or 'Materials Testing Laboratory'
        session_id = data.get('session_id') or session.get('session_id')

        # Map compression fields to standard experiments schema
        if 'original_height_mm' in data and 'original_gauge_length' not in data:
            data['original_gauge_length'] = data['original_height_mm']
        if 'original_diameter_mm' in data and 'original_diameter' not in data:
            data['original_diameter'] = data['original_diameter_mm']

        exp_id = save_experiment(
            data,
            student_id=student_id,
            student_name=student_name,
            university=university,
            session_id=session_id
        )
        return jsonify({'success': True, 'experiment_id': exp_id})
    except Exception as e:
        return jsonify({'error': str(e), 'success': False}), 500

@app.route('/compression/report/<int:experiment_id>')
@app.route('/api/compression/download-report/<int:experiment_id>')
def download_compression_report_by_id(experiment_id):
    """Generates and serves the certified PDF report for a compression experiment."""
    exp = get_experiment_by_id(experiment_id)
    if not exp:
        return "Compression experiment not found", 404

    exp['student_name'] = exp.get('student_name') or session.get('student_name') or 'Materials Science Student'
    exp['student_university'] = exp.get('university') or session.get('university') or 'Engineering Institute'
    exp['student_course'] = exp.get('course') or session.get('course') or 'Materials Testing Laboratory'
    exp['student_id'] = exp.get('student_id') or 'Session'

    log_activity(
        student_id=exp.get('student_id'),
        activity_type='REPORT_DOWNLOAD',
        details=f"Downloaded PDF for Compression Exp #{experiment_id}",
        student_name=exp['student_name'],
        university=exp['student_university'],
        session_id=session.get('session_id')
    )

    pdf_buffer = generate_compression_pdf(exp)
    clean_mat = (exp.get('material_name', 'metal')).replace(' ', '_').replace('/', '_')
    filename = f"MAT_VLAB_Compression_Exp{experiment_id}_{clean_mat}.pdf"
    return send_file(
        pdf_buffer,
        mimetype='application/pdf',
        as_attachment=True,
        download_name=filename
    )

@app.route('/api/compression/generate-pdf', methods=['POST'])
def api_compression_generate_pdf():
    """Generates a certified Compression PDF report on-the-fly from client payload."""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'Missing data for PDF generation'}), 400

        data['student_name'] = data.get('student_name') or session.get('student_name') or 'Materials Science Student'
        data['student_university'] = data.get('university') or session.get('university') or 'Engineering Institute'
        data['student_course'] = data.get('course') or session.get('course') or 'Materials Testing Laboratory'
        data['student_id'] = data.get('student_id') or 'Session'

        log_activity(
            student_id=data.get('student_id'),
            activity_type='REPORT_DOWNLOAD',
            details=f"Generated Compression PDF report for {data.get('material_name', 'Metal')}",
            student_name=data['student_name'],
            university=data['student_university'],
            session_id=session.get('session_id')
        )

        pdf_buffer = generate_compression_pdf(data)
        clean_mat = (data.get('material_name', 'metal')).replace(' ', '_').replace('/', '_')
        filename = f"MAT_VLAB_Compression_{clean_mat}.pdf"
        return send_file(
            pdf_buffer,
            mimetype='application/pdf',
            as_attachment=True,
            download_name=filename
        )
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    host = os.environ.get('HOST', '0.0.0.0')
    port = int(os.environ.get('PORT', 5000))
    debug = os.environ.get('FLASK_DEBUG', 'true').lower() in ('1', 'true', 'yes')
    app.run(host=host, port=port, debug=debug)
