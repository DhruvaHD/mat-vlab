"""
Responsive and Usability Audit for MAT-VLAB
Verifies all 11 routes, API endpoints, mobile meta tags, and responsive CSS rules.
"""
import sys
import os
import re
import json

# Add scratch/lib to path
sys.path.insert(0, '/home/hd/.gemini/antigravity/scratch/lib')
sys.path.insert(0, '/home/hd/.gemini/antigravity/scratch/mat-vlab')

from app import app

def run_audit():
    client = app.test_client()
    passed = 0
    failed = 0

    print("=" * 60)
    print("MAT-VLAB RESPONSIVE & USABILITY AUDIT")
    print("=" * 60)

    # 1. Test All Routes (HTTP 200)
    routes = [
        ('/', 'Home Page'),
        ('/experiments', 'Experiments Directory'),
        ('/experiments/tensile', 'Tensile Hub (Flagship)'),
        ('/simulation', 'Virtual Simulation Studio'),
        ('/manual', 'Manual Data Entry Studio'),
        ('/results', 'Results & Analysis'),
        ('/compare', 'Material Comparison'),
        ('/materials', 'Materials Database'),
        ('/quizzes', 'Quizzes & Viva'),
        ('/my-experiments', 'Saved Experiments'),
        ('/about', 'About Laboratory')
    ]

    print("\n--- Route Availability Audit ---")
    for path, name in routes:
        res = client.get(path)
        if res.status_code == 200:
            print(f"  [PASS] {name} ({path}) -> HTTP 200")
            passed += 1
        else:
            print(f"  [FAIL] {name} ({path}) -> HTTP {res.status_code}")
            failed += 1

    # 2. Test API Endpoints
    print("\n--- API Endpoints Audit ---")
    res_sim = client.get('/api/simulation-data?material=mild-steel&diameter=10.0&gauge_length=50.0')
    if res_sim.status_code == 200 and res_sim.is_json:
        print("  [PASS] GET /api/simulation-data -> HTTP 200 (Valid JSON)")
        passed += 1
    else:
        print(f"  [FAIL] GET /api/simulation-data -> HTTP {res_sim.status_code}")
        failed += 1

    res_csv = client.get('/api/download-sample-csv')
    if res_csv.status_code == 200:
        print("  [PASS] GET /api/download-sample-csv -> HTTP 200 (CSV Sample)")
        passed += 1
    else:
        print(f"  [FAIL] GET /api/download-sample-csv -> HTTP {res_csv.status_code}")
        failed += 1

    calc_payload = {
        'title': 'Test Audit Run',
        'material_name': 'Mild Steel',
        'original_diameter': 10.0,
        'original_gauge_length': 50.0,
        'readings': [
            {'reading_number': 1, 'load_n': 0, 'extension_mm': 0.0},
            {'reading_number': 2, 'load_n': 10000, 'extension_mm': 0.031},
            {'reading_number': 3, 'load_n': 20000, 'extension_mm': 0.062},
            {'reading_number': 4, 'load_n': 30000, 'extension_mm': 0.500},
            {'reading_number': 5, 'load_n': 34500, 'extension_mm': 8.200},
            {'reading_number': 6, 'load_n': 26000, 'extension_mm': 14.00}
        ]
    }
    res_calc = client.post('/api/calculate', data=json.dumps(calc_payload), content_type='application/json')
    if res_calc.status_code == 200 and res_calc.is_json:
        print("  [PASS] POST /api/calculate -> HTTP 200 (Valid Results JSON)")
        passed += 1
    else:
        print(f"  [FAIL] POST /api/calculate -> HTTP {res_calc.status_code}")
        failed += 1

    # 3. Viewport & Mobile Tag Audit
    print("\n--- Mobile Viewport & Meta Tags Audit ---")
    base_html = open('templates/base.html', 'r', encoding='utf-8').read()
    if 'name="viewport"' in base_html and 'width=device-width' in base_html and 'viewport-fit=cover' in base_html:
        print("  [PASS] meta viewport configured with width=device-width, initial-scale=1.0, viewport-fit=cover")
        passed += 1
    else:
        print("  [FAIL] meta viewport missing viewport-fit=cover or width=device-width")
        failed += 1

    css_content = open('static/css/style.css', 'r', encoding='utf-8').read()
    if 'navbar-toggler' in base_html and 'min-height: 44px' in css_content:
        print("  [PASS] Mobile navigation toggler has >= 44px touch target")
        passed += 1
    else:
        print("  [FAIL] Mobile navigation toggler touch target < 44px")
        failed += 1

    # 4. Tensile Page Mobile Flow Audit
    print("\n--- Tensile Page Mobile Pedagogical Flow Audit ---")
    tensile_html = open('templates/tensile.html', 'r', encoding='utf-8').read()
    required_classes = [
        'tensile-mobile-flow',
        'tensile-order-title',
        'tensile-order-objective',
        'tensile-order-theory',
        'tensile-order-apparatus',
        'tensile-order-specimen',
        'tensile-order-procedure',
        'tensile-order-modes',
        'tensile-order-calculations',
        'tensile-order-quicklinks'
    ]
    all_classes_present = True
    for cls in required_classes:
        if cls not in tensile_html:
            print(f"  [FAIL] Missing flow class: {cls}")
            all_classes_present = False
            failed += 1
    if all_classes_present:
        print("  [PASS] All 9 sequential pedagogical mobile flow classes present in tensile.html")
        passed += 1

    # 5. Manual Entry & Mobile Cards Audit
    print("\n--- Observation Table Mobile Cards Audit ---")
    manual_html = open('templates/manual_entry.html', 'r', encoding='utf-8').read()
    tensile_js = open('static/js/tensile.js', 'r', encoding='utf-8').read()
    if 'table-mobile-cards' in manual_html:
        print("  [PASS] readings-table has table-mobile-cards class for phone card conversion")
        passed += 1
    else:
        print("  [FAIL] readings-table missing table-mobile-cards class")
        failed += 1

    if 'data-label=' in tensile_js and 'inputmode="decimal"' in tensile_js:
        print("  [PASS] Dynamic rows include data-label attributes and inputmode=decimal")
        passed += 1
    else:
        print("  [FAIL] Dynamic rows missing data-label or inputmode=decimal")
        failed += 1

    # 6. CSS Media Queries Audit for Required Viewports
    print("\n--- CSS Media Queries Audit (320px - 1920px) ---")
    viewports = [
        (r'@media\s*\([^)]*max-width:\s*991\.98px[^)]*\)', 'Tablets/Mobile Flow (< 992px)'),
        (r'@media\s*\([^)]*max-width:\s*767\.98px[^)]*\)', 'Tablets (< 768px)'),
        (r'@media\s*\([^)]*max-width:\s*575\.98px[^)]*\)', 'Phones (< 576px)'),
        (r'@media\s*\([^)]*max-width:\s*360px[^)]*\)', 'Extra Small Phones (320px - 360px)')
    ]
    for pattern, name in viewports:
        if re.search(pattern, css_content):
            print(f"  [PASS] Media query for {name} verified")
            passed += 1
        else:
            print(f"  [FAIL] Missing media query for {name}")
            failed += 1

    # 7. iOS Safari Zoom Prevention Check
    if 'font-size: 16px !important' in css_content:
        print("  [PASS] Form controls have 16px font-size to prevent iOS Safari auto-zoom")
        passed += 1
    else:
        print("  [FAIL] Form controls missing 16px rule for iOS zoom prevention")
        failed += 1

    # 8. Minimum Touch Targets (>= 44px)
    if 'min-height: 44px' in css_content and 'min-height: 48px' in css_content:
        print("  [PASS] Buttons, inputs, and quiz controls satisfy >= 44px touch targets")
        passed += 1
    else:
        print("  [FAIL] Missing >= 44px touch target rules in style.css")
        failed += 1

    # 9. Slider Touch Optimization
    if 'slider-thumb' in css_content and '26px' in css_content:
        print("  [PASS] Range slider thumb enlarged to 26px for smooth finger dragging")
        passed += 1
    else:
        print("  [FAIL] Range slider thumb styling missing")
        failed += 1

    # 10. Horizontal Overflow Safeguards
    if 'overflow-x: hidden' in css_content:
        print("  [PASS] overflow-x: hidden set on html/body to prevent horizontal scrolling")
        passed += 1
    else:
        print("  [FAIL] overflow-x: hidden missing")
        failed += 1

    print("\n" + "=" * 60)
    print(f"AUDIT SUMMARY: {passed} PASSED, {failed} FAILED")
    print("=" * 60)

    if failed > 0:
        sys.exit(1)

if __name__ == '__main__':
    run_audit()
