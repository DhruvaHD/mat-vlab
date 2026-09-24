import os
import sys

# Ensure local packages in scratch/lib are discovered
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
SCRATCH_LIB = os.path.abspath(os.path.join(BASE_DIR, '..', 'lib'))
if os.path.exists(SCRATCH_LIB) and SCRATCH_LIB not in sys.path:
    sys.path.insert(0, SCRATCH_LIB)

# Ensure matplotlib writes to writable directory
os.environ['MPLCONFIGDIR'] = '/tmp'

from flask import Flask, render_template, request, jsonify, send_file, redirect, url_for
from config import Config
from models.database import (
    init_db, get_all_materials, get_material_by_slug,
    save_experiment, get_experiment_by_id, get_all_experiments, delete_experiment,
    get_quiz_questions, save_quiz_result
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

@app.route('/api/save', methods=['POST'])
def api_save():
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'Missing payload to save.'}), 400

        experiment_id = save_experiment(data)
        return jsonify({'success': True, 'experiment_id': experiment_id})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/experiment/<int:experiment_id>', methods=['GET', 'DELETE'])
def api_experiment_detail(experiment_id):
    if request.method == 'DELETE':
        success = delete_experiment(experiment_id)
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
