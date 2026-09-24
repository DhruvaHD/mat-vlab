import os
import sys

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
    get_quiz_questions, save_quiz_result,
    register_student, authenticate_student, is_student_id_available,
    validate_student_id, get_student_by_id, get_student_stats,
    get_all_students, get_admin_stats, delete_student_account
)
from calculations.tensile import (
    analyze_tensile_data, generate_simulation_data, calculate_cross_sectional_area
)
from reports.report_generator import generate_tensile_pdf

from werkzeug.middleware.proxy_fix import ProxyFix

app = Flask(__name__)
app.config.from_object(Config)

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

# Context processor to make student details available globally in all templates
@app.context_processor
def inject_student_context():
    student_id = session.get('student_id')
    student = None
    if student_id:
        student = get_student_by_id(student_id)
        if not student:
            session.pop('student_id', None)
            session.pop('student_name', None)
            session.pop('course', None)
            session.pop('university', None)
    return {
        'current_student': student,
        'is_logged_in': bool(student)
    }

# ==========================================
# STUDENT AUTHENTICATION & DASHBOARD ROUTES
# ==========================================

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        course = request.form.get('course', '').strip()
        university = request.form.get('university', '').strip()
        student_id = request.form.get('student_id', '').strip()

        try:
            student = register_student(name, course, university, student_id)
            session['student_id'] = student['student_id']
            session['student_name'] = student['name']
            session['course'] = student['course']
            session['university'] = student['university']
            flash(f"Welcome to MAT-VLAB, {student['name']}! Your student account has been created with ID: {student['student_id']}.", 'success')
            return redirect(url_for('dashboard'))
        except ValueError as e:
            flash(str(e), 'danger')
            return render_template(
                'register.html',
                active_page='register',
                form_data={'name': name, 'course': course, 'university': university, 'student_id': student_id}
            )

    # If already logged in, redirect to dashboard
    if session.get('student_id'):
        return redirect(url_for('dashboard'))
    return render_template('register.html', active_page='register', form_data={})

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        student_id = request.form.get('student_id', '').strip()
        university = request.form.get('university', '').strip()

        try:
            # Login only requires Student ID and University / College (NO name required)
            student = authenticate_student(student_id, university)
            session['student_id'] = student['student_id']
            session['student_name'] = student['name']
            session['course'] = student['course']
            session['university'] = student['university']
            flash(f"Welcome back, {student['name']}!", 'success')
            return redirect(url_for('dashboard'))
        except ValueError as e:
            flash(str(e), 'danger')
            return render_template(
                'login.html',
                active_page='login',
                form_data={'student_id': student_id, 'university': university}
            )

    # If already logged in, redirect to dashboard
    if session.get('student_id'):
        return redirect(url_for('dashboard'))
    return render_template('login.html', active_page='login', form_data={})

@app.route('/logout')
def logout():
    name = session.get('student_name')
    session.clear()
    flash(f"You have been successfully logged out. Have a productive day{', ' + name if name else ''}!", 'info')
    return redirect(url_for('login'))

@app.route('/dashboard')
def dashboard():
    student_id = session.get('student_id')
    if not student_id:
        flash("Please log in with your Student ID to access your personal dashboard.", "info")
        return redirect(url_for('login'))

    student = get_student_by_id(student_id)
    if not student:
        session.clear()
        return redirect(url_for('login'))

    stats = get_student_stats(student_id)
    student_exps = get_all_experiments(student_id=student_id)
    return render_template(
        'dashboard.html',
        active_page='dashboard',
        student=student,
        stats=stats,
        experiments=student_exps
    )

# ==========================================
# MAT-VLAB ADMIN & STUDENT ROSTER ROUTES
# ==========================================

@app.route('/admin')
@app.route('/admin/students')
def admin_dashboard():
    search_q = request.args.get('q', '').strip()
    selected_uni = request.args.get('university', '').strip()
    selected_course = request.args.get('course', '').strip()

    stats = get_admin_stats()
    students = get_all_students(
        search_query=search_q if search_q else None,
        university=selected_uni if selected_uni and selected_uni != 'ALL' else None,
        course=selected_course if selected_course and selected_course != 'ALL' else None
    )

    return render_template(
        'admin.html',
        active_page='admin',
        stats=stats,
        students=students,
        total_students=len(students),
        all_students_count=stats['total_students'],
        search_q=search_q,
        selected_uni=selected_uni,
        selected_course=selected_course
    )

@app.route('/admin/export-csv')
def admin_export_csv():
    students = get_all_students()
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['Student ID', 'Name', 'Course', 'University', 'Registration Date', 'Experiments Count'])
    for s in students:
        writer.writerow([
            s.get('student_id', ''),
            s.get('name', ''),
            s.get('course', ''),
            s.get('university', ''),
            s.get('created_at', ''),
            s.get('experiment_count', 0)
        ])

    mem = io.BytesIO()
    mem.write(output.getvalue().encode('utf-8'))
    mem.seek(0)
    output.close()

    return send_file(
        mem,
        mimetype='text/csv',
        as_attachment=True,
        download_name='mat_vlab_students_roster.csv'
    )

@app.route('/admin/student/<student_id>/delete', methods=['POST'])
def admin_delete_student(student_id):
    success = delete_student_account(student_id)
    if success:
        flash(f"Student account '{student_id}' has been removed successfully.", "warning")
    else:
        flash(f"Failed to remove student account '{student_id}'.", "danger")
    return redirect(url_for('admin_dashboard'))

# ==========================================
# WEB PAGE ROUTES
# ==========================================

@app.route('/')
def index():
    return render_template('index.html', active_page='index')

@app.route('/experiments')
def experiments():
    return render_template('experiments.html', active_page='experiments')

@app.route('/experiments/tensile')
def tensile_hub():
    return render_template('tensile.html', active_page='tensile')

@app.route('/simulation')
def simulation():
    return render_template('simulation.html', active_page='simulation')

@app.route('/manual')
def manual_entry():
    return render_template('manual_entry.html', active_page='manual')

@app.route('/results')
def results():
    return render_template('results.html', active_page='results')

@app.route('/materials')
def materials():
    mat_list = get_all_materials()
    return render_template('materials.html', active_page='materials', materials=mat_list)

@app.route('/compare')
def compare():
    mat_list = get_all_materials()
    saved_list = get_all_experiments()
    return render_template('compare.html', active_page='compare', materials=mat_list, saved_experiments=saved_list)

@app.route('/my-experiments')
def my_experiments():
    student_id = session.get('student_id')
    if student_id:
        return redirect(url_for('dashboard'))
    exp_list = get_all_experiments()
    return render_template('my_experiments.html', active_page='my_experiments', experiments=exp_list)

@app.route('/experiments/<int:experiment_id>')
def view_experiment(experiment_id):
    exp = get_experiment_by_id(experiment_id)
    if not exp:
        return redirect(url_for('my_experiments'))
    # Load into results view via template context or client-side storage
    return render_template('results.html', active_page='results', preloaded_experiment=exp)

@app.route('/quizzes')
def quizzes():
    q_list = get_quiz_questions(experiment_type='tensile', limit=10)
    return render_template('quizzes.html', active_page='quizzes', questions=q_list)

@app.route('/about')
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

        student = register_student(name, course, university, student_id)
        session['student_id'] = student['student_id']
        session['student_name'] = student['name']
        session['course'] = student['course']
        session['university'] = student['university']
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
        university = data.get('university', '').strip()

        student = authenticate_student(student_id, university)
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
        data = request.get_json()
        if not data:
            return jsonify({'error': 'Missing payload to save.'}), 400

        student_id = session.get('student_id') or data.get('student_id')
        experiment_id = save_experiment(data, student_id=student_id)
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

@app.route('/api/quiz/submit', methods=['POST'])
def api_quiz_submit():
    try:
        data = request.get_json()
        exp_type = data.get('experiment_type', 'tensile')
        score = int(data.get('score', 0))
        total = int(data.get('total_questions', 10))
        exp_id = data.get('experiment_id')

        res_id = save_quiz_result(exp_id, exp_type, score, total)
        return jsonify({'success': True, 'result_id': res_id})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/download-report/<int:experiment_id>')
def download_report_by_id(experiment_id):
    exp = get_experiment_by_id(experiment_id)
    if not exp:
        return "Experiment not found", 404

    # Attach student profile if available
    sid = exp.get('student_id') or session.get('student_id')
    if sid:
        st = get_student_by_id(sid)
        if st:
            exp['student_name'] = st['name']
            exp['student_id'] = st['student_id']
            exp['student_course'] = st['course']
            exp['student_university'] = st['university']

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

        sid = data.get('student_id') or session.get('student_id')
        if sid:
            st = get_student_by_id(sid)
            if st:
                data['student_name'] = st['name']
                data['student_id'] = st['student_id']
                data['student_course'] = st['course']
                data['student_university'] = st['university']

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

if __name__ == '__main__':
    host = os.environ.get('HOST', '0.0.0.0')
    port = int(os.environ.get('PORT', 5000))
    debug = os.environ.get('FLASK_DEBUG', 'true').lower() in ('1', 'true', 'yes')
    app.run(host=host, port=port, debug=debug)
