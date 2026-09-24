import unittest
import os
import sys
import io

# Setup paths
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
SCRATCH_LIB = os.path.abspath(os.path.join(BASE_DIR, '..', 'lib'))
if os.path.exists(SCRATCH_LIB) and SCRATCH_LIB not in sys.path:
    sys.path.insert(0, SCRATCH_LIB)
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

os.environ['MPLCONFIGDIR'] = '/tmp'

from calculations.tensile import (
    calculate_cross_sectional_area, analyze_tensile_data, generate_simulation_data
)
from models.database import (
    init_db, get_all_materials, save_experiment, get_experiment_by_id, delete_experiment,
    get_quiz_questions
)
from reports.report_generator import generate_tensile_pdf
from app import app

class TensileLaboratoryTests(unittest.TestCase):

    def setUp(self):
        init_db()
        self.app = app.test_client()
        self.app.testing = True
        with self.app.session_transaction() as sess:
            sess['student_id'] = 'TestDhruva01'
            sess['student_name'] = 'Dhruva H D'
            sess['course'] = 'B.Tech'
            sess['university'] = 'Pondicherry University'

    def test_cross_sectional_area(self):
        # 10 mm diameter -> pi * 25 = 78.5398 mm^2
        area = calculate_cross_sectional_area(10.0)
        self.assertAlmostEqual(area, 78.5398, places=3)

        with self.assertRaises(ValueError):
            calculate_cross_sectional_area(0)
        with self.assertRaises(ValueError):
            calculate_cross_sectional_area(-5.0)

    def test_tensile_analysis_mild_steel(self):
        # Sample tensile dataset on 10mm specimen, 50mm gauge length
        readings = [
            {"reading_number": 1, "load_n": 0, "extension_mm": 0.000},
            {"reading_number": 2, "load_n": 5000, "extension_mm": 0.016},
            {"reading_number": 3, "load_n": 10000, "extension_mm": 0.031},
            {"reading_number": 4, "load_n": 15000, "extension_mm": 0.047},
            {"reading_number": 5, "load_n": 19500, "extension_mm": 0.061},
            {"reading_number": 6, "load_n": 19800, "extension_mm": 0.085},
            {"reading_number": 7, "load_n": 19400, "extension_mm": 0.180},
            {"reading_number": 8, "load_n": 25000, "extension_mm": 2.000},
            {"reading_number": 9, "load_n": 34500, "extension_mm": 8.000},
            {"reading_number": 10, "load_n": 28000, "extension_mm": 13.500}
        ]

        result = analyze_tensile_data(
            original_diameter_mm=10.0,
            original_gauge_length_mm=50.0,
            readings=readings,
            material_name="Mild Steel"
        )

        self.assertIn("summary", result)
        self.assertIn("formulas", result)
        self.assertIn("conclusion", result)

        summary = result["summary"]
        self.assertAlmostEqual(summary["uts_mpa"], 439.27, places=0)
        self.assertGreater(summary["youngs_modulus_gpa"], 150.0)
        self.assertLess(summary["youngs_modulus_gpa"], 230.0)
        self.assertGreater(summary["elongation_pct"], 20.0)
        self.assertIsNotNone(summary["yield_strength_mpa"])

    def test_simulation_data_generation(self):
        materials = ["mild-steel", "aluminium-6061-t6", "copper-c11000", "brass-c26000", "stainless-steel-304"]
        for mat in materials:
            sim = generate_simulation_data(mat, diameter_mm=10.0, gauge_length_mm=50.0)
            self.assertEqual(sim["material_slug"], mat)
            self.assertGreater(len(sim["readings"]), 15)
            # Verify stress values start at 0 and have positive UTS
            self.assertEqual(sim["readings"][0]["stress_mpa"], 0.0)
            max_stress = max(r["stress_mpa"] for r in sim["readings"])
            self.assertGreater(max_stress, 150.0)

    def test_database_operations(self):
        # Check pre-seeded materials
        materials = get_all_materials()
        self.assertGreaterEqual(len(materials), 5)
        slugs = [m["slug"] for m in materials]
        self.assertIn("mild-steel", slugs)
        self.assertIn("aluminium-6061-t6", slugs)

        # Check pre-seeded quiz questions
        questions = get_quiz_questions('tensile')
        self.assertGreaterEqual(len(questions), 8)

        # Test experiment insert and retrieval
        test_exp = {
            "title": "Unit Test Experiment Run",
            "experiment_type": "tensile",
            "mode": "MANUAL_ENTRY",
            "material_name": "Mild Steel",
            "original_diameter": 10.0,
            "original_gauge_length": 50.0,
            "readings": [
                {"load_n": 0, "extension_mm": 0, "stress_mpa": 0, "strain": 0},
                {"load_n": 30000, "extension_mm": 5.0, "stress_mpa": 381.97, "strain": 0.10}
            ],
            "results": {
                "cross_sectional_area": 78.54,
                "youngs_modulus_gpa": 200.0,
                "yield_strength_mpa": 250.0,
                "uts_mpa": 381.97,
                "max_load_n": 30000.0,
                "elongation_pct": 20.0,
                "conclusion": "Test conclusion text."
            }
        }

        exp_id = save_experiment(test_exp)
        self.assertIsNotNone(exp_id)

        retrieved = get_experiment_by_id(exp_id)
        self.assertIsNotNone(retrieved)
        self.assertEqual(retrieved["title"], "Unit Test Experiment Run")
        self.assertEqual(len(retrieved["readings"]), 2)

        # Test delete
        delete_experiment(exp_id)
        self.assertIsNone(get_experiment_by_id(exp_id))

    def test_pdf_report_generation(self):
        exp_data = {
            "title": "Laboratory Validation PDF Run",
            "material_name": "Mild Steel (AISI 1018)",
            "mode": "VIRTUAL_SIMULATION",
            "original_diameter": 10.0,
            "original_gauge_length": 50.0,
            "created_at": "2026-09-22 12:00:00",
            "readings": [
                {"reading_number": 1, "load_n": 0, "extension_mm": 0.0, "stress_mpa": 0.0, "strain": 0.0},
                {"reading_number": 2, "load_n": 10000, "extension_mm": 0.03, "stress_mpa": 127.3, "strain": 0.0006},
                {"reading_number": 3, "load_n": 20000, "extension_mm": 0.10, "stress_mpa": 254.6, "strain": 0.0020},
                {"reading_number": 4, "load_n": 34000, "extension_mm": 8.00, "stress_mpa": 432.9, "strain": 0.1600}
            ],
            "results": {
                "youngs_modulus_gpa": 205.0,
                "yield_strength_mpa": 250.0,
                "uts_mpa": 432.9,
                "elongation_pct": 25.0,
                "reduction_area_pct": 45.0,
                "toughness_mj_m3": 55.4,
                "conclusion": "Specimen demonstrated classic ductile behavior."
            }
        }

        pdf_buffer = generate_tensile_pdf(exp_data)
        self.assertIsInstance(pdf_buffer, io.BytesIO)
        pdf_bytes = pdf_buffer.getvalue()
        # PDF files must start with %PDF- header
        self.assertTrue(pdf_bytes.startswith(b'%PDF-'))
        self.assertGreater(len(pdf_bytes), 10000)

    def test_flask_routes(self):
        routes = [
            '/',
            '/experiments',
            '/experiments/tensile',
            '/simulation',
            '/manual',
            '/results',
            '/materials',
            '/compare',
            '/my-experiments',
            '/quizzes',
            '/about'
        ]

        for r in routes:
            response = self.app.get(r, follow_redirects=True)
            self.assertEqual(response.status_code, 200, f"Route {r} failed with status {response.status_code}")

    def test_api_calculate_endpoint(self):
        payload = {
            "original_diameter": 10.0,
            "original_gauge_length": 50.0,
            "readings": [
                {"load_n": 0, "extension_mm": 0},
                {"load_n": 10000, "extension_mm": 0.03},
                {"load_n": 25000, "extension_mm": 2.5},
                {"load_n": 34000, "extension_mm": 7.0}
            ]
        }
        response = self.app.post('/api/calculate', json=payload)
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertIn("summary", data)
        self.assertIn("formulas", data)

    def test_api_simulation_data_endpoint(self):
        response = self.app.get('/api/simulation-data?material=aluminium-6061-t6&diameter=10.0&gauge_length=50.0')
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertEqual(data["material_slug"], "aluminium-6061-t6")
        self.assertGreater(len(data["readings"]), 10)

if __name__ == '__main__':
    unittest.main()
