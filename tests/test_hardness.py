import unittest
import os
import sys
import io
import json

# Setup paths
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
for lib_path in ['/home/hd/.gemini/antigravity/scratch/lib', os.path.abspath(os.path.join(BASE_DIR, '..', 'lib'))]:
    if os.path.exists(lib_path) and lib_path not in sys.path:
        sys.path.insert(0, lib_path)
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

os.environ['MPLCONFIGDIR'] = '/tmp'

from calculations.hardness import (
    calculate_brinell,
    calculate_brinell_multiple,
    calculate_rockwell,
    calculate_rockwell_multiple,
    generate_brinell_simulation_data,
    generate_rockwell_simulation_data,
    astm_e140_convert,
    STANDARD_MATERIALS_HARDNESS
)
from models.database import (
    init_db,
    save_hardness_experiment,
    get_hardness_experiment_by_id,
    get_all_hardness_experiments,
    delete_hardness_experiment,
    get_quiz_questions
)
from reports.hardness_report_generator import generate_hardness_pdf
from app import app

class HardnessTestingLaboratoryTests(unittest.TestCase):

    def setUp(self):
        init_db()
        from models.database import register_student, is_student_id_available
        avail, _ = is_student_id_available('HardnessTester01')
        if avail:
            register_student('Dhruva H D', 'B.Tech Materials', 'Pondicherry University', 'HardnessTester01', '1234')
        self.app = app.test_client()
        self.app.testing = True
        with self.app.session_transaction() as sess:
            sess['student_id'] = 'HardnessTester01'
            sess['student_name'] = 'Dhruva H D'
            sess['course'] = 'B.Tech Materials'
            sess['university'] = 'Pondicherry University'

    # ========================================================
    # 1. BRINELL HARDNESS CALCULATION PHYSICS & VALIDATION
    # ========================================================

    def test_brinell_standard_calculation(self):
        # P = 3000 kgf, D = 10 mm, d = 5.35 mm
        # Formula: HBW = 2P / [pi * D * (D - sqrt(D^2 - d^2))]
        res = calculate_brinell(load_kgf=3000.0, ball_d_mm=10.0, d1_mm=5.35, d2_mm=5.35)
        self.assertAlmostEqual(res['hbw'], 122.9, delta=0.5)
        self.assertTrue(res['is_valid_indentation'])
        self.assertGreater(res['depth_h_mm'], 0.5)
        self.assertGreater(res['min_thickness_mm'], 4.0)
        self.assertAlmostEqual(res['p_d2_ratio'], 30.0, places=1)
        self.assertGreater(res['estimated_uts_mpa'], 400.0)

    def test_brinell_anisotropic_diameters(self):
        # d1 = 4.2 mm, d2 = 4.4 mm -> mean d = 4.3 mm
        res = calculate_brinell(load_kgf=3000.0, ball_d_mm=10.0, d1_mm=4.2, d2_mm=4.4)
        self.assertAlmostEqual(res['mean_d_mm'], 4.3, places=2)
        self.assertAlmostEqual(res['hbw'], 196.2, delta=1.0)
        self.assertTrue(res['is_valid_indentation'])

    def test_brinell_invalid_indentation_geometry(self):
        # Indentation >= indenter diameter or <= 0
        with self.assertRaises(ValueError):
            calculate_brinell(load_kgf=3000.0, ball_d_mm=10.0, d1_mm=10.5, d2_mm=10.5)
        with self.assertRaises(ValueError):
            calculate_brinell(load_kgf=3000.0, ball_d_mm=10.0, d1_mm=0.0, d2_mm=0.0)
        with self.assertRaises(ValueError):
            calculate_brinell(load_kgf=-500.0, ball_d_mm=10.0, d1_mm=3.0, d2_mm=3.0)

    def test_brinell_out_of_bounds_ratio_warning(self):
        # d / D < 0.24 (e.g. d = 2.0 mm on 10 mm ball -> d/D = 0.20)
        res = calculate_brinell(load_kgf=3000.0, ball_d_mm=10.0, d1_mm=2.0, d2_mm=2.0)
        self.assertFalse(res['is_valid_indentation'])
        self.assertTrue("Caution" in res['validity_note'] or "Warning" in res['validity_note'])

    def test_brinell_multi_trial_averaging(self):
        trials = [
            {'d1_mm': 4.10, 'd2_mm': 4.12},
            {'d1_mm': 4.15, 'd2_mm': 4.18},
            {'d1_mm': 4.12, 'd2_mm': 4.14}
        ]
        multi = calculate_brinell_multiple(load_kgf=3000.0, ball_d_mm=10.0, trials=trials)
        self.assertEqual(multi['num_trials'], 3)
        self.assertGreater(multi['mean_hbw'], 200.0)
        self.assertLess(multi['mean_hbw'], 220.0)
        self.assertGreater(multi['std_dev'], 0.0)
        self.assertEqual(len(multi['trials_results']), 3)

    # ========================================================
    # 2. ROCKWELL HARDNESS CALCULATION PHYSICS & VALIDATION
    # ========================================================

    def test_rockwell_scale_c_calculation(self):
        # Scale C: N = 100, 150 kgf, Diamond Brale Cone
        # Formula: HRC = 100 - (e / 0.002)
        # For e = 0.080 mm -> HRC = 100 - 40 = 60.0
        res = calculate_rockwell(scale='HRC', depth_e_mm=0.080)
        self.assertAlmostEqual(res['hr_value'], 60.0, places=1)
        self.assertEqual(res['scale_code'], 'HRC')
        self.assertEqual(res['total_load_kgf'], 150.0)
        self.assertEqual(res['minor_load_kgf'], 10.0)
        self.assertIn('Diamond', res['indenter_type'])

    def test_rockwell_scale_b_calculation(self):
        # Scale B: N = 130, 100 kgf, 1/16" Ball
        # Formula: HRB = 130 - (e / 0.002)
        # For e = 0.100 mm -> HRB = 130 - 50 = 80.0
        res = calculate_rockwell(scale='HRB', depth_e_mm=0.100)
        self.assertAlmostEqual(res['hr_value'], 80.0, places=1)
        self.assertEqual(res['scale_code'], 'HRB')
        self.assertEqual(res['total_load_kgf'], 100.0)
        self.assertIn('Ball', res['indenter_type'])

    def test_rockwell_invalid_inputs(self):
        with self.assertRaises(ValueError):
            calculate_rockwell(scale='UNKNOWN_SCALE', depth_e_mm=0.05)
        with self.assertRaises(ValueError):
            calculate_rockwell(scale='HRC', depth_e_mm=-0.01)

    def test_rockwell_multi_trial_averaging(self):
        trials = [
            {'depth_e_mm': 0.082},
            {'depth_e_mm': 0.080},
            {'depth_e_mm': 0.084}
        ]
        multi = calculate_rockwell_multiple(scale='HRC', trials=trials)
        self.assertEqual(multi['num_trials'], 3)
        self.assertAlmostEqual(multi['mean_hr'], 59.0, delta=1.5)
        self.assertEqual(len(multi['trials_results']), 3)

    # ========================================================
    # 3. SIMULATION DATA ENGINE
    # ========================================================

    def test_brinell_simulation_engine(self):
        sim = generate_brinell_simulation_data(material_slug='mild_steel', ball_d_mm=10.0, load_kgf=3000.0, num_trials=3)
        self.assertEqual(sim['method'], 'BRINELL')
        self.assertEqual(sim['material']['slug'], 'mild_steel')
        self.assertEqual(len(sim['readings']), 3)
        for r in sim['readings']:
            self.assertGreater(r['d1_mm'], 0)
            self.assertGreater(r['d2_mm'], 0)
            self.assertGreater(r['hbw'], 100.0)
            self.assertLess(r['hbw'], 200.0)
        self.assertIn('mean_hbw', sim['summary'])

    def test_rockwell_simulation_engine(self):
        sim = generate_rockwell_simulation_data(material_slug='tool_steel', scale='HRC', num_trials=3)
        self.assertEqual(sim['method'], 'ROCKWELL')
        self.assertEqual(sim['scale']['scale'], 'HRC')
        self.assertEqual(len(sim['readings']), 3)
        for r in sim['readings']:
            self.assertGreater(r['depth_e_mm'], 0)
            self.assertGreater(r['hr_value'], 50.0) # hardened tool steel ~ 56 HRC
        self.assertIn('mean_hr', sim['summary'])

    # ========================================================
    # 4. ASTM E140 HARDNESS CONVERSION
    # ========================================================

    def test_astm_e140_conversion(self):
        # Convert 500 HBW to HRC -> approx 51.5 HRC
        conv = astm_e140_convert(value=500.0, from_scale='HBW', to_scale='HRC')
        self.assertAlmostEqual(conv['converted_value'], 51.5, delta=3.0)

        # Convert 60 HRC to HBW -> approx 654 HBW
        conv2 = astm_e140_convert(value=60.0, from_scale='HRC', to_scale='HBW')
        self.assertAlmostEqual(conv2['converted_value'], 654.0, delta=25.0)

    # ========================================================
    # 5. DATABASE OPERATIONS & QUIZ RETRIEVAL
    # ========================================================

    def test_database_save_and_retrieve_brinell(self):
        exp_data = {
            'title': 'Test Brinell Run on AISI 1020',
            'method': 'BRINELL',
            'mode': 'VIRTUAL_SIMULATION',
            'material_name': 'AISI 1020 Mild Steel',
            'data_origin': 'SIMULATION / DEMONSTRATION DATA',
            'parameters': {'load_kgf': 3000.0, 'ball_d_mm': 10.0, 'indenter_type': 'Tungsten Carbide Ball'},
            'readings': [
                {'trial_number': 1, 'd1_mm': 5.24, 'd2_mm': 5.28, 'mean_d_mm': 5.26, 'depth_mm': 0.74, 'hardness_value': 128.5},
                {'trial_number': 2, 'd1_mm': 5.20, 'd2_mm': 5.24, 'mean_d_mm': 5.22, 'depth_mm': 0.73, 'hardness_value': 130.8}
            ],
            'mean_hardness': 129.65,
            'hardness_unit': 'HBW 10/3000',
            'num_readings': 2,
            'notes': 'Uniform spherical indentation profiles observed.'
        }
        exp_id = save_hardness_experiment(exp_data, student_id='HardnessTester01')
        self.assertIsInstance(exp_id, int)
        self.assertGreater(exp_id, 0)

        fetched = get_hardness_experiment_by_id(exp_id)
        self.assertIsNotNone(fetched)
        self.assertEqual(fetched['method'], 'BRINELL')
        self.assertEqual(fetched['student_id'], 'HardnessTester01')
        self.assertEqual(len(fetched['readings']), 2)
        self.assertAlmostEqual(fetched['mean_hardness'], 129.65, places=2)

        # Cleanup
        del_ok = delete_hardness_experiment(exp_id, student_id='HardnessTester01')
        self.assertTrue(del_ok)
        self.assertIsNone(get_hardness_experiment_by_id(exp_id))

    def test_hardness_quiz_seeding(self):
        brinell_questions = get_quiz_questions(experiment_type='brinell', limit=10)
        self.assertGreaterEqual(len(brinell_questions), 6)
        self.assertTrue(any("HBW" in q['question'] or "ball" in q['question'].lower() or "brinell" in q['question'].lower() for q in brinell_questions))

        rockwell_questions = get_quiz_questions(experiment_type='rockwell', limit=10)
        self.assertGreaterEqual(len(rockwell_questions), 6)
        self.assertTrue(any("rockwell" in q['question'].lower() or "preload" in q['question'].lower() or "scale c" in q['question'].lower() for q in rockwell_questions))

    # ========================================================
    # 6. WEB ROUTES & PAGE RENDERING
    # ========================================================

    def test_hardness_web_routes(self):
        # 1. Hardness Hub
        res = self.app.get('/experiments/hardness')
        self.assertEqual(res.status_code, 200)
        self.assertIn(b'Hardness Testing Laboratory', res.data)
        self.assertIn(b'Brinell Hardness Test', res.data)
        self.assertIn(b'Rockwell Hardness Test', res.data)

        # 2. Brinell page & alias
        res_b1 = self.app.get('/experiments/hardness/brinell')
        self.assertEqual(res_b1.status_code, 200)
        self.assertIn(b'Brinell Hardness Test', res_b1.data)
        res_b2 = self.app.get('/experiments/brinell')
        self.assertEqual(res_b2.status_code, 200)

        # 3. Rockwell page & alias
        res_r1 = self.app.get('/experiments/hardness/rockwell')
        self.assertEqual(res_r1.status_code, 200)
        self.assertIn(b'Rockwell Hardness Test', res_r1.data)
        res_r2 = self.app.get('/experiments/rockwell')
        self.assertEqual(res_r2.status_code, 200)

        # 4. Compare page
        res_c = self.app.get('/experiments/hardness/compare')
        self.assertEqual(res_c.status_code, 200)
        self.assertIn(b'Compare Hardness', res_c.data)

        # 5. My Experiments page (shows Hardness tab)
        res_my = self.app.get('/my-experiments')
        self.assertEqual(res_my.status_code, 200)
        self.assertIn(b'Hardness Testing', res_my.data)

        # 6. Quizzes page for Brinell and Rockwell
        res_qb = self.app.get('/quizzes?type=brinell')
        self.assertEqual(res_qb.status_code, 200)
        self.assertIn(b'Brinell Hardness Testing Quiz', res_qb.data)

        res_qr = self.app.get('/quizzes?type=rockwell')
        self.assertEqual(res_qr.status_code, 200)
        self.assertIn(b'Rockwell Hardness Testing Quiz', res_qr.data)

    # ========================================================
    # 7. REST API ENDPOINTS
    # ========================================================

    def test_api_hardness_simulation_data(self):
        # Brinell API
        res = self.app.get('/api/hardness/simulation-data?method=brinell&material=mild_steel&ball_diameter=10&load=3000')
        self.assertEqual(res.status_code, 200)
        data = json.loads(res.data)
        self.assertTrue(data['success'])
        self.assertEqual(len(data['data']['readings']), 3)

        # Rockwell API
        res_r = self.app.get('/api/hardness/simulation-data?method=rockwell&material=tool_steel&scale=HRC')
        self.assertEqual(res_r.status_code, 200)
        data_r = json.loads(res_r.data)
        self.assertTrue(data_r['success'])
        self.assertEqual(len(data_r['data']['readings']), 3)

    def test_api_hardness_calculate(self):
        payload = {
            'method': 'BRINELL',
            'load_kgf': 3000.0,
            'ball_d_mm': 10.0,
            'readings': [
                {'d1_mm': 5.25, 'd2_mm': 5.25},
                {'d1_mm': 5.28, 'd2_mm': 5.30}
            ]
        }
        res = self.app.post('/api/hardness/calculate', json=payload)
        self.assertEqual(res.status_code, 200)
        data = json.loads(res.data)
        self.assertTrue(data['success'])
        self.assertIn('mean_hbw', data['result'])

    def test_api_hardness_save_and_delete(self):
        payload = {
            'title': 'API Test Rockwell Trial',
            'method': 'ROCKWELL',
            'mode': 'VIRTUAL_SIMULATION',
            'material_name': 'AISI O1 Tool Steel',
            'data_origin': 'SIMULATION / DEMONSTRATION DATA',
            'parameters': {'scale': 'HRC', 'indenter_type': 'Diamond Cone', 'total_load_kgf': 150.0},
            'readings': [
                {'trial_number': 1, 'depth_mm': 0.084, 'hardness_value': 58.0},
                {'trial_number': 2, 'depth_mm': 0.082, 'hardness_value': 59.0}
            ],
            'mean_hardness': 58.5,
            'hardness_unit': 'HRC',
            'num_readings': 2,
            'notes': 'Standard Rockwell API verification test.'
        }
        res = self.app.post('/api/hardness/save', json=payload)
        self.assertEqual(res.status_code, 200)
        data = json.loads(res.data)
        self.assertTrue(data['success'])
        exp_id = data['experiment_id']

        # Get experiment via API
        res_get = self.app.get(f'/api/hardness/experiment/{exp_id}')
        self.assertEqual(res_get.status_code, 200)
        exp_obj = json.loads(res_get.data)
        self.assertEqual(exp_obj['method'], 'ROCKWELL')

        # Delete experiment via API
        res_del = self.app.delete(f'/api/hardness/experiment/{exp_id}')
        self.assertEqual(res_del.status_code, 200)
        del_data = json.loads(res_del.data)
        self.assertTrue(del_data['success'])

    def test_api_hardness_quiz_submit(self):
        payload = {
            'experiment_type': 'brinell',
            'score': 6,
            'total_questions': 6
        }
        res = self.app.post('/api/hardness/quiz/submit', json=payload)
        self.assertEqual(res.status_code, 200)
        data = json.loads(res.data)
        self.assertTrue(data['success'])

    # ========================================================
    # 8. PDF REPORT GENERATION & DOWNLOAD
    # ========================================================

    def test_hardness_pdf_generation_brinell(self):
        exp_data = {
            'id': 101,
            'title': 'Brinell Hardness Test on Gray Cast Iron',
            'method': 'BRINELL',
            'mode': 'VIRTUAL_SIMULATION',
            'material_name': 'Gray Cast Iron Class 30',
            'data_origin': 'SIMULATION / DEMONSTRATION DATA',
            'parameters_json': json.dumps({'load_kgf': 3000.0, 'ball_d_mm': 10.0, 'indenter_type': '10 mm Tungsten Carbide Ball'}),
            'mean_hardness': 210.5,
            'hardness_unit': 'HBW 10/3000',
            'num_readings': 3,
            'created_at': '2026-09-24 15:30:00',
            'student_name': 'Dhruva H D',
            'student_id': 'Dhruva01',
            'student_course': 'B.Tech Materials Science',
            'student_university': 'Pondicherry University',
            'readings': [
                {'trial_number': 1, 'd1_mm': 4.15, 'd2_mm': 4.17, 'mean_d_mm': 4.16, 'depth_mm': 0.45, 'hardness_value': 210.8},
                {'trial_number': 2, 'd1_mm': 4.14, 'd2_mm': 4.18, 'mean_d_mm': 4.16, 'depth_mm': 0.45, 'hardness_value': 210.8},
                {'trial_number': 3, 'd1_mm': 4.16, 'd2_mm': 4.16, 'mean_d_mm': 4.16, 'depth_mm': 0.45, 'hardness_value': 210.8}
            ]
        }
        pdf_buf = generate_hardness_pdf(exp_data)
        self.assertIsInstance(pdf_buf, io.BytesIO)
        pdf_bytes = pdf_buf.getvalue()
        self.assertTrue(pdf_bytes.startswith(b'%PDF'))
        self.assertGreater(len(pdf_bytes), 1000)

    def test_hardness_pdf_generation_rockwell(self):
        exp_data = {
            'id': 102,
            'title': 'Rockwell C Hardness on AISI 4140',
            'method': 'ROCKWELL',
            'mode': 'MANUAL_ENTRY',
            'material_name': 'AISI 4140 Alloy Steel',
            'data_origin': 'USER-ENTERED LABORATORY DATA',
            'parameters_json': json.dumps({'scale': 'HRC', 'indenter_type': 'Diamond Brale Cone', 'total_load_kgf': 150.0}),
            'mean_hardness': 48.5,
            'hardness_unit': 'HRC',
            'num_readings': 3,
            'created_at': '2026-09-24 15:45:00',
            'student_name': 'Dhruva H D',
            'student_id': 'Dhruva01',
            'student_course': 'B.Tech Materials Science',
            'student_university': 'Pondicherry University',
            'readings': [
                {'trial_number': 1, 'depth_mm': 0.103, 'hardness_value': 48.5},
                {'trial_number': 2, 'depth_mm': 0.104, 'hardness_value': 48.0},
                {'trial_number': 3, 'depth_mm': 0.102, 'hardness_value': 49.0}
            ]
        }
        pdf_buf = generate_hardness_pdf(exp_data)
        self.assertIsInstance(pdf_buf, io.BytesIO)
        pdf_bytes = pdf_buf.getvalue()
        self.assertTrue(pdf_bytes.startswith(b'%PDF'))
        self.assertGreater(len(pdf_bytes), 1000)

    def test_hardness_report_download_endpoint(self):
        # Save a hardness experiment first
        exp_data = {
            'title': 'Download Report Test',
            'method': 'BRINELL',
            'mode': 'VIRTUAL_SIMULATION',
            'material_name': 'AISI 1020 Mild Steel',
            'data_origin': 'SIMULATION / DEMONSTRATION DATA',
            'parameters': {'load_kgf': 3000.0, 'ball_d_mm': 10.0, 'indenter_type': 'Tungsten Carbide Ball'},
            'readings': [{'trial_number': 1, 'd1_mm': 5.26, 'd2_mm': 5.26, 'mean_d_mm': 5.26, 'depth_mm': 0.74, 'hardness_value': 129.0}],
            'mean_hardness': 129.0,
            'hardness_unit': 'HBW 10/3000',
            'num_readings': 1,
            'notes': 'Download verification'
        }
        exp_id = save_hardness_experiment(exp_data, student_id='HardnessTester01')

        res = self.app.get(f'/hardness/report/{exp_id}')
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.mimetype, 'application/pdf')
        self.assertTrue(res.data.startswith(b'%PDF'))

        # Also test alias /api/hardness/download-report/<id>
        res_alias = self.app.get(f'/api/hardness/download-report/{exp_id}')
        self.assertEqual(res_alias.status_code, 200)
        self.assertEqual(res_alias.mimetype, 'application/pdf')

        # Cleanup
        delete_hardness_experiment(exp_id, student_id='HardnessTester01')

if __name__ == '__main__':
    unittest.main()
