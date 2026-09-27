"""
MAT-VLAB Global Mathematical Formula Rendering Verification Suite
Tests KaTeX integration, delimiter validity across templates, dynamic math scripts, and clean PDF generation.
"""

import unittest
import os
import sys
import re

# Ensure pathing for test environment
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
for lib_path in ['/home/hd/.gemini/antigravity/scratch/lib', os.path.abspath(os.path.join(BASE_DIR, '..', 'lib'))]:
    if os.path.exists(lib_path) and lib_path not in sys.path:
        sys.path.insert(0, lib_path)
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

os.environ['MPLCONFIGDIR'] = '/tmp'

from app import app
from models.database import init_db
from reports.report_generator import generate_tensile_pdf
from reports.hardness_report_generator import generate_hardness_pdf


class MathematicalRenderingTests(unittest.TestCase):

    def setUp(self):
        init_db()
        from models.database import register_student, is_student_id_available
        avail, _ = is_student_id_available('MathTester01')
        if avail:
            register_student('Dhruva H D', 'B.Tech Materials Science', 'Pondicherry University', 'MathTester01', '1234')

        self.client = app.test_client()
        self.client.testing = True

        # Logged-in session for testing protected views
        with self.client.session_transaction() as sess:
            sess['student_id'] = 'MathTester01'
            sess['student_name'] = 'Dhruva H D'
            sess['course'] = 'B.Tech Materials Science'
            sess['university'] = 'Pondicherry University'

    # =========================================================================
    # 1. BASE TEMPLATE & ASSETS INTEGRITY
    # =========================================================================

    def test_base_html_includes_mathjax_assets(self):
        """Verify templates/base.html loads MathJax 3 configuration and engine."""
        base_path = os.path.join(BASE_DIR, 'templates', 'base.html')
        self.assertTrue(os.path.exists(base_path), "base.html must exist")
        with open(base_path, 'r', encoding='utf-8') as f:
            content = f.read()

        self.assertIn('window.MathJax =', content, "MathJax 3 configuration must be defined in base.html")
        self.assertIn('inlineMath', content, "MathJax inlineMath must be configured in base.html")
        self.assertIn('displayMath', content, "MathJax displayMath must be configured in base.html")
        self.assertIn('tex-svg.js', content, "MathJax 3 SVG engine script must be loaded in base.html")
        self.assertIn('math_render.js', content, "math_render.js must be loaded in base.html")

    def test_math_render_js_exists_and_configured(self):
        """Verify static/js/math_render.js contains MathJax 3 typesetPromise and mutation observer."""
        js_path = os.path.join(BASE_DIR, 'static', 'js', 'math_render.js')
        self.assertTrue(os.path.exists(js_path), "math_render.js must exist")
        with open(js_path, 'r', encoding='utf-8') as f:
            js = f.read()

        self.assertIn('typesetPromise', js, "Must configure typesetPromise for MathJax 3")
        self.assertIn('MutationObserver', js, "Must configure MutationObserver for dynamic DOM changes")
        self.assertIn('window.renderMath', js, "Must expose global window.renderMath helper")

    def test_style_css_includes_mathjax_responsiveness(self):
        """Verify static/css/style.css contains responsive overflow styling for MathJax SVG."""
        css_path = os.path.join(BASE_DIR, 'static', 'css', 'style.css')
        with open(css_path, 'r', encoding='utf-8') as f:
            css = f.read()

        self.assertIn('mjx-container', css)
        self.assertIn('overflow-x: auto', css, "MathJax display math must have horizontal overflow handling")

    # =========================================================================
    # 2. TEMPLATE MATHEMATICAL NOTATION & DELIMITER INTEGRITY
    # =========================================================================

    def test_key_templates_have_balanced_delimiters(self):
        """Verify math expressions in key templates have balanced delimiters without broken syntax."""
        templates_to_check = [
            'brinell.html',
            'rockwell.html',
            'tensile.html',
            'manual_entry.html',
            'hardness_hub.html',
            'hardness_compare.html',
            'experiments.html',
            'quizzes.html'
        ]

        for tmpl_name in templates_to_check:
            tmpl_path = os.path.join(BASE_DIR, 'templates', tmpl_name)
            self.assertTrue(os.path.exists(tmpl_path), f"{tmpl_name} must exist")
            with open(tmpl_path, 'r', encoding='utf-8') as f:
                content = f.read()

            # Remove Jinja blocks and script tags before delimiter checking
            cleaned = re.sub(r'\{%.*?%\}', '', content, flags=re.DOTALL)
            cleaned = re.sub(r'\{\{.*?\}\}', '', cleaned, flags=re.DOTALL)
            cleaned = re.sub(r'<script.*?>.*?</script>', '', cleaned, flags=re.DOTALL)

            # Check that double dollars $$ are paired
            double_dollars = cleaned.count('$$')
            self.assertEqual(
                double_dollars % 2, 0,
                f"Unmatched display math delimiter $$ in {tmpl_name} (count={double_dollars})"
            )

    def test_brinell_formulas_validity(self):
        """Verify Brinell template contains correct ASTM E10 formula."""
        tmpl_path = os.path.join(BASE_DIR, 'templates', 'brinell.html')
        with open(tmpl_path, 'r', encoding='utf-8') as f:
            content = f.read()

        self.assertIn('HBW', content)
        self.assertIn(r'\frac{2P}{\pi D', content, "Brinell formula must contain 2P / pi*D")
        self.assertIn(r'\sqrt{D^2 - d^2}', content, "Brinell formula must contain sqrt(D^2 - d^2)")

    def test_rockwell_formulas_validity(self):
        """Verify Rockwell template contains correct ASTM E18 formula."""
        tmpl_path = os.path.join(BASE_DIR, 'templates', 'rockwell.html')
        with open(tmpl_path, 'r', encoding='utf-8') as f:
            content = f.read()

        self.assertIn(r'HR = N - \frac{e}{0.002', content, "Rockwell formula must contain HR = N - e/0.002")

    def test_tensile_formulas_validity(self):
        """Verify Tensile template contains correct ASTM E8 formulas."""
        tmpl_path = os.path.join(BASE_DIR, 'templates', 'tensile.html')
        with open(tmpl_path, 'r', encoding='utf-8') as f:
            content = f.read()

        self.assertIn(r'A_0 = \frac{\pi d_0^2}{4}', content)
        self.assertIn(r'\sigma = \frac{P}{A_0}', content)
        self.assertIn(r'\epsilon = \frac{\Delta L}{L_0}', content)
        self.assertIn(r'E = \frac{\Delta \sigma}{\Delta \epsilon}', content)

    # =========================================================================
    # 3. HTTP ENDPOINT RENDERING OF MATH
    # =========================================================================

    def test_rendered_pages_contain_mathjax_assets(self):
        """Verify rendered HTTP responses deliver MathJax resources to the browser."""
        endpoints = [
            '/experiments/hardness/brinell',
            '/experiments/hardness/rockwell',
            '/experiments/hardness/compare',
            '/experiments/tensile',
            '/manual',
            '/experiments',
            '/quizzes'
        ]

        for url in endpoints:
            res = self.client.get(url)
            self.assertEqual(res.status_code, 200, f"Endpoint {url} failed with status {res.status_code}")
            html = res.data.decode('utf-8')
            self.assertIn('window.MathJax =', html, f"Endpoint {url} missing MathJax config")
            self.assertIn('tex-svg.js', html, f"Endpoint {url} missing MathJax JS")
            self.assertIn('math_render.js', html, f"Endpoint {url} missing math_render.js")

    # =========================================================================
    # 4. CERTIFIED PDF GENERATION CLEANLINESS (ZERO RAW LATEX IN PDF)
    # =========================================================================

    def test_tensile_pdf_report_contains_no_raw_latex(self):
        """Verify generated Tensile PDF does not contain unparsed LaTeX syntax strings."""
        test_exp_data = {
            'id': 101,
            'title': 'Tensile Test - AISI 1020',
            'material_name': 'AISI 1020 Steel',
            'mode': 'VIRTUAL_SIMULATION',
            'created_at': '2026-09-24 10:00:00',
            'specimen': {
                'original_diameter_mm': 10.0,
                'original_gauge_length_mm': 50.0,
                'final_diameter_mm': 6.8,
                'final_gauge_length_mm': 64.0,
                'cross_sectional_area_mm2': 78.54
            },
            'results': {
                'youngs_modulus_gpa': 205.0,
                'yield_strength_mpa': 295.0,
                'uts_mpa': 445.0,
                'elongation_pct': 28.0,
                'reduction_area_pct': 53.8,
                'toughness_mj_m3': 95.4,
                'modulus_of_resilience_mj_m3': 0.21,
                'conclusion': 'Tested specimen conforms with ASTM A36 / AISI 1020 tensile ductility specifications.'
            },
            'readings': [
                {'reading_number': 1, 'load_n': 0, 'extension_mm': 0, 'stress_mpa': 0, 'strain': 0},
                {'reading_number': 2, 'load_n': 10000, 'extension_mm': 0.031, 'stress_mpa': 127.3, 'strain': 0.00062},
                {'reading_number': 3, 'load_n': 23150, 'extension_mm': 0.072, 'stress_mpa': 295.0, 'strain': 0.00144},
                {'reading_number': 4, 'load_n': 35000, 'extension_mm': 2.500, 'stress_mpa': 445.0, 'strain': 0.05000}
            ]
        }
        student_info = {
            'name': 'Dhruva H D',
            'student_id': 'MathTester01',
            'course': 'B.Tech Materials',
            'university': 'Pondicherry University'
        }

        pdf_io = generate_tensile_pdf(test_exp_data)
        pdf_bytes = pdf_io.getvalue()
        self.assertGreater(len(pdf_bytes), 1000, "PDF must not be empty")

        # Verify binary PDF contains no unparsed TeX markup
        self.assertNotIn(b'\\frac', pdf_bytes, "PDF must not leak raw LaTeX \\frac")
        self.assertNotIn(b'\\sqrt', pdf_bytes, "PDF must not leak raw LaTeX \\sqrt")
        self.assertNotIn(b'\\left(', pdf_bytes, "PDF must not leak raw LaTeX \\left(")
        self.assertNotIn(b'\\right)', pdf_bytes, "PDF must not leak raw LaTeX \\right)")

    def test_brinell_pdf_report_contains_no_raw_latex(self):
        """Verify generated Brinell PDF report uses clean typography with no raw LaTeX strings."""
        test_exp_data = {
            'id': 201,
            'title': 'Brinell Hardness Test - Mild Steel',
            'method': 'brinell',
            'mode': 'VIRTUAL_SIMULATION',
            'material_name': 'Mild Steel (IS 2062 / AISI 1018)',
            'created_at': '2026-09-24 11:00:00',
            'parameters': {
                'ball_diameter_mm': 10.0,
                'load_kgf': 3000.0,
                'dwell_time_s': 12.0
            },
            'readings': [
                {'trial_number': 1, 'd1_mm': 5.18, 'd2_mm': 5.20, 'mean_d_mm': 5.19, 'hardness_value': 131.8, 'depth_mm': 0.725},
                {'trial_number': 2, 'd1_mm': 5.15, 'd2_mm': 5.17, 'mean_d_mm': 5.16, 'hardness_value': 133.5, 'depth_mm': 0.716}
            ],
            'mean_hardness': 132.65,
            'hardness_unit': 'HBW',
            'notes': 'Specimen exhibited clean circular indentation without edge deformation.'
        }
        student_info = {
            'name': 'Dhruva H D',
            'student_id': 'MathTester01',
            'course': 'B.Tech Materials',
            'university': 'Pondicherry University'
        }

        pdf_io = generate_hardness_pdf(test_exp_data, student_info)
        pdf_bytes = pdf_io.getvalue()
        self.assertGreater(len(pdf_bytes), 1000, "PDF must not be empty")

        self.assertNotIn(b'\\frac', pdf_bytes, "PDF must not leak raw LaTeX \\frac")
        self.assertNotIn(b'\\sqrt', pdf_bytes, "PDF must not leak raw LaTeX \\sqrt")
        self.assertNotIn(b'\\left(', pdf_bytes, "PDF must not leak raw LaTeX \\left(")

    def test_rockwell_pdf_report_contains_no_raw_latex(self):
        """Verify generated Rockwell PDF report uses clean typography with no raw LaTeX strings."""
        test_exp_data = {
            'id': 202,
            'title': 'Rockwell Hardness Test - AISI 1045 Carbon Steel',
            'method': 'rockwell',
            'mode': 'VIRTUAL_SIMULATION',
            'material_name': 'Medium Carbon Steel (AISI 1045)',
            'created_at': '2026-09-24 11:30:00',
            'parameters': {
                'scale': 'C',
                'indenter_type': 'Diamond Cone (Brale 120°)',
                'minor_load_kgf': 10.0,
                'major_load_kgf': 150.0,
                'dwell_time_s': 5.0
            },
            'readings': [
                {'trial_number': 1, 'dial_reading': 48.5, 'hardness_value': 48.5, 'indent_depth_mm': 0.1030},
                {'trial_number': 2, 'dial_reading': 49.0, 'hardness_value': 49.0, 'indent_depth_mm': 0.1020}
            ],
            'mean_hardness': 48.75,
            'hardness_unit': 'HRC',
            'notes': 'Scale C diamond indenter utilized; no surface slippage observed.'
        }
        student_info = {
            'name': 'Dhruva H D',
            'student_id': 'MathTester01',
            'course': 'B.Tech Materials',
            'university': 'Pondicherry University'
        }

        pdf_io = generate_hardness_pdf(test_exp_data, student_info)
        pdf_bytes = pdf_io.getvalue()
        self.assertGreater(len(pdf_bytes), 1000, "PDF must not be empty")

        self.assertNotIn(b'\\frac', pdf_bytes, "PDF must not leak raw LaTeX \\frac")
        self.assertNotIn(b'\\sqrt', pdf_bytes, "PDF must not leak raw LaTeX \\sqrt")
        self.assertNotIn(b'\\left(', pdf_bytes, "PDF must not leak raw LaTeX \\left(")


if __name__ == '__main__':
    unittest.main()
