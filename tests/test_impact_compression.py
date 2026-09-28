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

from calculations.impact import (
    calculate_potential_energy,
    calculate_absorbed_energy,
    calculate_impact_toughness,
    estimate_shear_fracture_pct,
    calculate_dbtt_model_energy,
    analyze_impact_readings,
    generate_impact_simulation_data,
    IMPACT_SPECIMEN_STANDARDS,
    IMPACT_MATERIAL_PRESETS
)
from calculations.compression import (
    calculate_cylindrical_area,
    calculate_compressive_stress,
    calculate_compressive_strain,
    calculate_barreling_index,
    analyze_compression_data,
    generate_compression_simulation_data,
    COMPRESSION_MATERIAL_PRESETS
)
from models.database import (
    init_db,
    save_impact_experiment,
    get_impact_experiment_by_id,
    get_all_impact_experiments,
    delete_impact_experiment,
    save_experiment,
    get_experiment_by_id,
    get_quiz_questions
)
from reports.impact_report_generator import generate_impact_pdf
from reports.compression_report_generator import generate_compression_pdf
from app import app


class ImpactCompressionLaboratoryTests(unittest.TestCase):

    def setUp(self):
        init_db()
        self.app = app.test_client()
        self.app.testing = True

    # ========================================================
    # 1. IMPACT TEST CALCULATION PHYSICS & VALIDATION (ASTM E23)
    # ========================================================

    def test_impact_potential_and_absorbed_energy(self):
        """Test ASTM E23 potential energy and absorbed energy subtraction with friction."""
        # Machine with pendulum mass 20.4 kg, radius 0.8 m, release angle 140 deg
        e0 = calculate_potential_energy(mass_kg=20.4, radius_m=0.8, angle_deg=140.0)
        self.assertGreater(e0, 250.0)
        self.assertLess(e0, 320.0)

        # Absorbed energy: E0 = 300 J, residual E1 = 160 J, tare loss = 1.5 J
        kv = calculate_absorbed_energy(initial_energy_j=300.0, residual_energy_j=160.0, friction_loss_j=1.5)
        self.assertAlmostEqual(kv, 138.5, places=2)

    def test_impact_toughness_and_fracture_appearance(self):
        """Test impact toughness ak and shear fracture percentage."""
        # Standard Charpy V-notch: 10x10 mm with 2 mm notch -> A0 = 80 mm2 = 0.80 cm2
        toughness = calculate_impact_toughness(absorbed_energy_j=120.0, net_area_cm2=0.80)
        self.assertAlmostEqual(toughness['ak_j_cm2'], 150.0, places=1)
        self.assertAlmostEqual(toughness['ak_kj_m2'], 1500.0, places=1)

        # Shear percentage on transition: KV = 90 J, lower shelf = 15 J, upper shelf = 165 J
        pct_shear = estimate_shear_fracture_pct(absorbed_energy_j=90.0, lower_shelf_j=15.0, upper_shelf_j=165.0)
        self.assertAlmostEqual(pct_shear, 50.0, places=1)

    def test_impact_dbtt_model_energy(self):
        """Test hyperbolic tangent transition curve behavior."""
        # Below DBTT (-60°C when DBTT is -15°C) -> near lower shelf (15 J)
        e_cold = calculate_dbtt_model_energy(temperature_c=-60.0, lower_shelf_j=15.0, upper_shelf_j=165.0, dbtt_c=-15.0, slope_c=25.0)
        self.assertLess(e_cold, 35.0)

        # At DBTT (-15°C) -> exact midpoint ((15 + 165) / 2 = 90 J)
        e_dbtt = calculate_dbtt_model_energy(temperature_c=-15.0, lower_shelf_j=15.0, upper_shelf_j=165.0, dbtt_c=-15.0, slope_c=25.0)
        self.assertAlmostEqual(e_dbtt, 90.0, places=1)

        # Above DBTT (+60°C) -> near upper shelf (165 J)
        e_hot = calculate_dbtt_model_energy(temperature_c=60.0, lower_shelf_j=15.0, upper_shelf_j=165.0, dbtt_c=-15.0, slope_c=25.0)
        self.assertGreater(e_hot, 150.0)

    def test_impact_analyze_readings(self):
        """Test multi-trial laboratory readings analysis."""
        readings = [
            {'absorbed_energy_j': 95.0, 'lateral_expansion_mm': 1.1},
            {'absorbed_energy_j': 98.0, 'lateral_expansion_mm': 1.15},
            {'absorbed_energy_j': 92.0, 'lateral_expansion_mm': 1.05}
        ]
        result = analyze_impact_readings(
            readings=readings,
            specimen_type='charpy_v',
            material_name='Mild Steel',
            test_temperature_c=23.0
        )
        self.assertIn('summary', result)
        self.assertAlmostEqual(result['summary']['mean_absorbed_energy_j'], 95.0, places=1)
        self.assertGreater(result['summary']['mean_ak_j_cm2'], 100.0)
        self.assertEqual(result['summary']['num_trials'], 3)
        self.assertIn('formulas', result)

    def test_impact_simulation_generator(self):
        """Test realistic physics simulation generator for Charpy."""
        sim = generate_impact_simulation_data(material_slug='mild-steel', temperature_c=23.0, num_trials=3)
        self.assertEqual(sim['material_slug'], 'mild-steel')
        self.assertTrue(sim['has_dbtt'])
        self.assertEqual(len(sim['readings']), 3)
        self.assertGreater(len(sim['temperature_sweep']), 10)
        self.assertIn('summary', sim)

    # ========================================================
    # 2. COMPRESSION TEST CALCULATION PHYSICS (ASTM E9)
    # ========================================================

    def test_compression_area_stress_strain(self):
        """Test cylindrical area, compressive stress and strain formulas."""
        area = calculate_cylindrical_area(diameter_mm=15.0)
        # pi * 7.5^2 = 176.7146 mm2
        self.assertAlmostEqual(area, 176.715, places=2)

        # 50 kN load on 176.715 mm2 -> 50000 / 176.715 = 282.94 MPa
        stress = calculate_compressive_stress(load_n=50000.0, initial_area_mm2=area)
        self.assertAlmostEqual(stress, 282.94, places=1)

        # delta_h = 0.6 mm on h0 = 30 mm -> strain = 0.02 (2%)
        strain = calculate_compressive_strain(delta_h_mm=0.6, initial_height_mm=30.0)
        self.assertAlmostEqual(strain, 0.02, places=4)

    def test_compression_barreling_index(self):
        """Test ASTM E9 barreling index calculation due to platen friction."""
        # Initial d0 = 15.0 mm, final expanded mid diameter df = 17.5 mm, end = 15.5 mm
        # B = (17.5 - 15.5) / 15.0 = 2.0 / 15.0 = 0.1333
        b_idx = calculate_barreling_index(final_mid_diameter_mm=17.5, final_end_diameter_mm=15.5, initial_diameter_mm=15.0)
        self.assertAlmostEqual(b_idx, 0.1333, places=3)

    def test_compression_analyze_data(self):
        """Test full compression data reduction from load-stroke observation points."""
        readings = [
            {'load_kn': 0.0, 'stroke_mm': 0.0},
            {'load_kn': 15.0, 'stroke_mm': 0.04},
            {'load_kn': 35.0, 'stroke_mm': 0.09},
            {'load_kn': 55.0, 'stroke_mm': 0.14},
            {'load_kn': 70.0, 'stroke_mm': 0.25},
            {'load_kn': 85.0, 'stroke_mm': 0.60},
            {'load_kn': 105.0, 'stroke_mm': 1.50},
            {'load_kn': 120.0, 'stroke_mm': 2.80}
        ]
        result = analyze_compression_data(
            original_diameter_mm=15.0,
            original_height_mm=30.0,
            readings=readings,
            final_height_mm=27.2,
            final_mid_diameter_mm=16.8,
            final_end_diameter_mm=15.4,
            material_name='Aluminium 6061-T6'
        )
        self.assertIn('summary', result)
        self.assertIsNotNone(result['summary']['elastic_modulus_gpa'])
        self.assertGreater(result['summary']['elastic_modulus_gpa'], 40.0)
        self.assertGreater(result['summary']['compressive_yield_mpa'], 180.0)
        self.assertIn('computed_readings', result)
        self.assertEqual(len(result['computed_readings']), len(readings))

    def test_compression_simulation_generator(self):
        """Test compression simulation curve generator for cast iron vs ductile metal."""
        sim_ci = generate_compression_simulation_data(material_slug='grey-cast-iron', diameter_mm=15.0, height_mm=30.0)
        self.assertEqual(sim_ci['material_slug'], 'grey-cast-iron')
        self.assertTrue(sim_ci['is_brittle'])
        self.assertGreater(len(sim_ci['readings']), 15)

        sim_al = generate_compression_simulation_data(material_slug='aluminium-6061-t6', diameter_mm=15.0, height_mm=30.0)
        self.assertFalse(sim_al['is_brittle'])

    # ========================================================
    # 3. DATABASE PERSISTENCE & QUIZ RETRIEVAL
    # ========================================================

    def test_impact_db_crud(self):
        """Test database persistence for Impact experiments."""
        exp_id = save_impact_experiment(
            data={
                'student_name': 'Dhruva Test Student',
                'material_name': 'AISI 1020 Steel',
                'specimen_type': 'charpy_v',
                'method': 'CHARPY',
                'mode': 'MANUAL_ENTRY',
                'test_temperature_c': 20.0,
                'machine_capacity_j': 300.0,
                'readings': [
                    {'temperature_c': 20.0, 'initial_energy_j': 300.0, 'residual_energy_j': 210.0,
                     'friction_loss_j': 0.5, 'absorbed_energy_j': 89.5, 'mean_ak_j_cm2': 111.88,
                     'lateral_expansion_mm': 1.1, 'pct_shear_fracture': 60.0}
                ],
                'summary': {
                    'mean_absorbed_energy_j': 89.5,
                    'std_dev_j': 0.0,
                    'mean_ak_j_cm2': 111.88,
                    'mean_lateral_expansion_mm': 1.1
                }
            }
        )
        self.assertIsNotNone(exp_id)

        exp = get_impact_experiment_by_id(exp_id)
        self.assertIsNotNone(exp)
        self.assertEqual(exp['material_name'], 'AISI 1020 Steel')
        self.assertEqual(len(exp['readings']), 1)

        all_exp = get_all_impact_experiments()
        self.assertTrue(any(e['id'] == exp_id for e in all_exp))

        deleted = delete_impact_experiment(exp_id)
        self.assertTrue(deleted)
        self.assertIsNone(get_impact_experiment_by_id(exp_id))

    def test_compression_and_impact_quiz_questions(self):
        """Test that ASTM E23 and ASTM E9 quiz questions are seeded in the database."""
        impact_q = get_quiz_questions('impact')
        self.assertGreaterEqual(len(impact_q), 6)
        compression_q = get_quiz_questions('compression')
        self.assertGreaterEqual(len(compression_q), 6)

    # ========================================================
    # 4. HTTP ROUTES & REST APIS
    # ========================================================

    def test_http_impact_page_and_apis(self):
        """Test GET /experiments/impact and its simulation/calc endpoints."""
        resp = self.app.get('/experiments/impact')
        self.assertEqual(resp.status_code, 200)
        self.assertIn(b'Impact Test', resp.data)

        # Simulation API
        sim_resp = self.app.post('/api/impact/simulate', json={
            'material_slug': 'mild-steel',
            'specimen_type': 'charpy_v',
            'temperature_c': 23.0
        })
        self.assertEqual(sim_resp.status_code, 200)
        sim_data = json.loads(sim_resp.data)
        self.assertTrue(sim_data['success'])
        self.assertIn('summary', sim_data['data'])

        # Multi-trial Calculation API
        calc_resp = self.app.post('/api/impact/calculate', json={
            'material_name': 'Test Steel',
            'specimen_type': 'charpy_v',
            'readings': [
                {'absorbed_energy_j': 90.0, 'lateral_expansion_mm': 1.05},
                {'absorbed_energy_j': 94.0, 'lateral_expansion_mm': 1.10}
            ]
        })
        self.assertEqual(calc_resp.status_code, 200)
        calc_data = json.loads(calc_resp.data)
        self.assertTrue(calc_data['success'])
        self.assertIn('summary', calc_data['result'])

    def test_http_compression_page_and_apis(self):
        """Test GET /experiments/compression and its simulation/calc endpoints."""
        resp = self.app.get('/experiments/compression')
        self.assertEqual(resp.status_code, 200)
        self.assertIn(b'Compression Test', resp.data)

        # Simulation API
        sim_resp = self.app.post('/api/compression/simulate', json={
            'material_slug': 'aluminium-6061',
            'diameter_mm': 15.0,
            'height_mm': 30.0
        })
        self.assertEqual(sim_resp.status_code, 200)
        sim_data = json.loads(sim_resp.data)
        self.assertTrue(sim_data['success'])
        self.assertIn('readings', sim_data['data'])

        # Calculation API
        calc_resp = self.app.post('/api/compression/calculate', json={
            'material_name': 'Test Specimen',
            'original_diameter_mm': 15.0,
            'original_height_mm': 30.0,
            'readings': [
                {'load_kn': 0.0, 'stroke_mm': 0.0},
                {'load_kn': 20.0, 'stroke_mm': 0.05},
                {'load_kn': 45.0, 'stroke_mm': 0.12},
                {'load_kn': 70.0, 'stroke_mm': 0.35}
            ]
        })
        self.assertEqual(calc_resp.status_code, 200)
        calc_data = json.loads(calc_resp.data)
        self.assertTrue(calc_data['success'])
        self.assertIn('summary', calc_data['result'])

    # ========================================================
    # 5. CERTIFIED PDF REPORT GENERATION
    # ========================================================

    def test_impact_pdf_generator(self):
        """Verify certified PDF report generation for Charpy impact testing with DBTT plot."""
        readings = [
            {'trial_number': 1, 'temperature_c': 23.0, 'initial_energy_j': 300.0, 'residual_energy_j': 210.0,
             'absorbed_energy_j': 89.5, 'lateral_expansion_mm': 1.1, 'pct_shear_fracture': 60.0},
            {'trial_number': 2, 'temperature_c': 23.0, 'initial_energy_j': 300.0, 'residual_energy_j': 208.0,
             'absorbed_energy_j': 91.5, 'lateral_expansion_mm': 1.15, 'pct_shear_fracture': 62.0}
        ]
        results_summary = {
            'mean_absorbed_energy_j': 90.5,
            'mean_ak_j_cm2': 113.1,
            'mean_lateral_expansion_mm': 1.12,
            'mean_shear_fracture_pct': 61.0,
            'dbtt_celsius': -15.0,
            'fracture_behavior': 'Ductile high-energy tearing'
        }
        pdf_buffer = generate_impact_pdf(
            experiment_data={
                'student_name': 'Dhruva H D',
                'material_name': 'AISI 1020 Structural Steel',
                'specimen_type': 'charpy_v',
                'test_type': 'Charpy',
                'test_temperature_c': 23.0,
                'initial_energy_j': 300.0,
                'friction_loss_j': 0.5,
                'created_at': '2026-09-28 12:00:00',
                'readings': readings,
                'summary': results_summary,
                'temp_sweep': [
                    {'temperature_c': -60, 'energy_j': 18.0},
                    {'temperature_c': -20, 'energy_j': 75.0},
                    {'temperature_c': 0, 'energy_j': 120.0},
                    {'temperature_c': 23, 'energy_j': 155.0},
                    {'temperature_c': 60, 'energy_j': 165.0}
                ]
            },
            student_info={'name': 'Dhruva H D', 'student_id': 'Admin', 'university': 'Pondicherry University'}
        )
        pdf_bytes = pdf_buffer.getvalue()
        self.assertIsInstance(pdf_bytes, bytes)
        self.assertGreater(len(pdf_bytes), 1000)
        self.assertTrue(pdf_bytes.startswith(b'%PDF'))

    def test_compression_pdf_generator(self):
        """Verify certified PDF report generation for compression testing with stress-strain curve."""
        readings = [
            {'load_kn': 0.0, 'stroke_mm': 0.0, 'stress_mpa': 0.0, 'strain': 0.0},
            {'load_kn': 20.0, 'stroke_mm': 0.05, 'stress_mpa': 113.2, 'strain': 0.00167},
            {'load_kn': 45.0, 'stroke_mm': 0.11, 'stress_mpa': 254.6, 'strain': 0.00367},
            {'load_kn': 65.0, 'stroke_mm': 0.28, 'stress_mpa': 367.8, 'strain': 0.00933},
            {'load_kn': 80.0, 'stroke_mm': 0.95, 'stress_mpa': 452.7, 'strain': 0.03167}
        ]
        results = {
            'elastic_modulus_gpa': 68.5,
            'compressive_yield_mpa': 285.0,
            'max_stress_mpa': 452.7,
            'final_strain_pct': 3.17,
            'slenderness_ratio': 2.0,
            'barreling_index': 0.12,
            'buckling_risk': False
        }
        pdf_buffer = generate_compression_pdf(
            experiment_data={
                'student_name': 'Dhruva H D',
                'material_name': 'Aluminium 6061-T6',
                'original_diameter_mm': 15.0,
                'original_height_mm': 30.0,
                'final_mid_diameter_mm': 16.8,
                'final_height_mm': 28.5,
                'created_at': '2026-09-28 12:00:00',
                'readings': readings,
                'summary': results
            },
            student_info={'name': 'Dhruva H D', 'student_id': 'Admin', 'university': 'Pondicherry University'}
        )
        pdf_bytes = pdf_buffer.getvalue()
        self.assertIsInstance(pdf_bytes, bytes)
        self.assertGreater(len(pdf_bytes), 1000)
        self.assertTrue(pdf_bytes.startswith(b'%PDF'))


if __name__ == '__main__':
    unittest.main()
