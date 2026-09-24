"""
MAT-VLAB Materials Testing Suite: Hardness Testing Calculation Engine
Covers:
1. Brinell Hardness Test (ASTM E10 / ISO 6506-1 / IS 1500)
2. Rockwell Hardness Test (ASTM E18 / ISO 6508-1 / IS 1586)
3. Hardness Statistical Analysis (multi-trial averaging, standard deviation, range)
4. Standard ASTM E140 Hardness Conversions and Tensile Strength Approximations
"""
import math
import random

# ==============================================================================
# 1. BRINELL HARDNESS TEST (HBW)
# ==============================================================================

# Standard P/D^2 ratios according to ASTM E10 / ISO 6506-1
BRINELL_LOAD_RATIOS = {
    'steels_cast_iron': 30.0,    # P/D^2 = 30 (e.g. 3000 kgf for 10mm ball, 750 kgf for 5mm)
    'copper_brass_bronze': 10.0, # P/D^2 = 10 (e.g. 1000 kgf for 10mm ball, 250 kgf for 5mm)
    'aluminium_alloys': 5.0,     # P/D^2 = 5 or 10 (e.g. 500 kgf for 10mm ball)
    'soft_metals': 2.5,          # P/D^2 = 2.5 (e.g. 250 kgf for 10mm ball for lead, tin)
    'bearing_alloys': 1.0        # P/D^2 = 1.0 (e.g. 100 kgf for 10mm ball)
}

# Standard material presets with realistic metallurgical reference values
BRINELL_MATERIAL_PRESETS = {
    'mild-steel': {
        'name': 'Mild Steel (IS 2062 / AISI 1018)',
        'category': 'Ferrous - Carbon Steel',
        'nominal_hbw': 130.0,
        'standard_ball_d': 10.0,
        'standard_load_kgf': 3000.0,
        'p_d2_ratio': 30.0,
        'dwell_sec': 12,
        'expected_d_mm': 5.18,
        'uts_approx_mpa': 440.0
    },
    'medium-carbon-steel': {
        'name': 'Medium Carbon Steel (AISI 1045 Normalized)',
        'category': 'Ferrous - Carbon Steel',
        'nominal_hbw': 190.0,
        'standard_ball_d': 10.0,
        'standard_load_kgf': 3000.0,
        'p_d2_ratio': 30.0,
        'dwell_sec': 12,
        'expected_d_mm': 4.35,
        'uts_approx_mpa': 650.0
    },
    'grey-cast-iron': {
        'name': 'Grey Cast Iron (FG 200 / ASTM A48)',
        'category': 'Ferrous - Cast Iron',
        'nominal_hbw': 210.0,
        'standard_ball_d': 10.0,
        'standard_load_kgf': 3000.0,
        'p_d2_ratio': 30.0,
        'dwell_sec': 15,
        'expected_d_mm': 4.15,
        'uts_approx_mpa': 220.0  # Cast iron does not follow 3.45 UTS ratio
    },
    'aluminium-6061-t6': {
        'name': 'Aluminium Alloy 6061-T6 (Precipitation Hardened)',
        'category': 'Non-Ferrous - Aluminium',
        'nominal_hbw': 95.0,
        'standard_ball_d': 10.0,
        'standard_load_kgf': 500.0,
        'p_d2_ratio': 5.0,
        'dwell_sec': 15,
        'expected_d_mm': 2.54,
        'uts_approx_mpa': 310.0
    },
    'cartridge-brass': {
        'name': 'Cartridge Brass (70Cu-30Zn Annealed)',
        'category': 'Non-Ferrous - Copper Alloy',
        'nominal_hbw': 60.0,
        'standard_ball_d': 10.0,
        'standard_load_kgf': 1000.0,
        'p_d2_ratio': 10.0,
        'dwell_sec': 15,
        'expected_d_mm': 4.42,
        'uts_approx_mpa': 330.0
    },
    'pure-copper': {
        'name': 'Electrolytic Tough Pitch (ETP) Copper',
        'category': 'Non-Ferrous - Copper',
        'nominal_hbw': 45.0,
        'standard_ball_d': 10.0,
        'standard_load_kgf': 500.0,
        'p_d2_ratio': 5.0,
        'dwell_sec': 15,
        'expected_d_mm': 3.66,
        'uts_approx_mpa': 220.0
    },
    'stainless-steel-304': {
        'name': 'Austenitic Stainless Steel (AISI 304)',
        'category': 'Ferrous - Stainless Steel',
        'nominal_hbw': 175.0,
        'standard_ball_d': 10.0,
        'standard_load_kgf': 3000.0,
        'p_d2_ratio': 30.0,
        'dwell_sec': 12,
        'expected_d_mm': 4.52,
        'uts_approx_mpa': 600.0
    }
}

def calculate_brinell_hardness(load_kgf, ball_diameter_mm, indent_diameter_mm):
    """
    Calculates Brinell Hardness Number (HBW) according to ISO 6506-1 / ASTM E10:
    
    HBW = (2 * P) / (pi * D * (D - sqrt(D^2 - d^2)))
    
    Parameters:
    - load_kgf (float): Applied normal load P in kgf (e.g. 3000, 1000, 500)
    - ball_diameter_mm (float): Diameter of tungsten carbide ball D in mm (e.g. 10.0, 5.0, 2.5)
    - indent_diameter_mm (float): Measured average indentation diameter d in mm
    
    Returns:
    - dict with:
        - 'hbw': Brinell Hardness Number rounded to 1 decimal place
        - 'depth_mm': Indentation depth h in mm
        - 'd_over_D_ratio': Ratio d/D (valid range 0.24 to 0.60)
        - 'is_valid_indent': Boolean whether d/D is within ASTM validity limits
        - 'min_specimen_thickness_mm': Minimum specimen thickness (8 * h)
        - 'min_edge_distance_mm': Minimum distance to specimen edge (2.5 * d)
        - 'min_spacing_mm': Minimum distance between adjacent indentations (3.0 * d)
        - 'uts_approx_mpa': Approximate tensile strength for carbon steels (3.45 * HBW)
    """
    P = float(load_kgf)
    D = float(ball_diameter_mm)
    d = float(indent_diameter_mm)

    if P <= 0:
        raise ValueError("Applied load must be greater than zero.")
    if D <= 0:
        raise ValueError("Indenter ball diameter must be greater than zero.")
    if d <= 0:
        raise ValueError("Indentation diameter must be greater than zero.")
    if d >= D:
        raise ValueError(f"Indentation diameter ({d:.2f} mm) cannot be greater than or equal to ball diameter ({D:.2f} mm).")

    term = D**2 - d**2
    if term < 0:
        raise ValueError("Mathematical root domain error: d must be strictly less than D.")

    sqrt_term = math.sqrt(term)
    denominator = math.pi * D * (D - sqrt_term)
    hbw = (2.0 * P) / denominator

    # Depth of spherical cap indentation: h = (D - sqrt(D^2 - d^2)) / 2
    h = (D - sqrt_term) / 2.0

    # ASTM E10 / ISO 6506-1 Geometric Similarity Criterion
    # Standard dictates 0.24 <= d/D <= 0.60 for valid spherical geometry
    ratio = d / D
    is_valid = (0.24 <= ratio <= 0.60)

    # Minimum specimen thickness to avoid "anvil effect": t >= 8 * h (or 10 * h for soft metals)
    min_thickness = round(8.0 * h, 3)

    # Minimum edge and spacing distances
    min_edge = round(2.5 * d, 2)
    min_spacing = round(3.0 * d, 2)

    # Approximate UTS for carbon steels: UTS (MPa) ~ 3.45 * HBW
    uts_approx = round(3.45 * hbw, 1)

    return {
        'hbw': round(hbw, 1),
        'depth_mm': round(h, 4),
        'd_over_D_ratio': round(ratio, 3),
        'is_valid_indent': is_valid,
        'validity_message': (
            f"Valid indentation geometry (d/D = {ratio:.2f} is within ASTM standard 0.24–0.60)"
            if is_valid else
            f"Caution: d/D = {ratio:.2f} is outside recommended ASTM 0.24–0.60 range. Adjust load or ball diameter."
        ),
        'min_specimen_thickness_mm': min_thickness,
        'min_edge_distance_mm': min_edge,
        'min_spacing_mm': min_spacing,
        'uts_approx_mpa': uts_approx
    }

def analyze_brinell_trials(trials, ball_diameter_mm, load_kgf):
    """
    Analyzes multiple Brinell laboratory readings/trials.
    
    Each trial can have:
    - 'trial_number': int
    - 'd1_mm': float
    - 'd2_mm': float
    (or directly 'd_mm')
    
    Returns statistical summary including mean, std dev, range, and validated trials.
    """
    processed_trials = []
    hbw_values = []
    d_values = []

    for idx, t in enumerate(trials, start=1):
        d1 = float(t.get('d1_mm', t.get('d1', 0.0)))
        d2 = float(t.get('d2_mm', t.get('d2', d1)))
        d_mean = (d1 + d2) / 2.0 if d1 and d2 else float(t.get('d_mm', t.get('d', 0.0)))

        calc = calculate_brinell_hardness(load_kgf, ball_diameter_mm, d_mean)
        hbw = calc['hbw']

        trial_record = {
            'trial_number': t.get('trial_number', idx),
            'd1_mm': round(d1, 3),
            'd2_mm': round(d2, 3),
            'mean_d_mm': round(d_mean, 3),
            'depth_mm': calc['depth_mm'],
            'hbw': hbw,
            'is_valid': calc['is_valid_indent']
        }
        processed_trials.append(trial_record)
        hbw_values.append(hbw)
        d_values.append(d_mean)

    n = len(hbw_values)
    if n == 0:
        raise ValueError("No valid trials provided for Brinell analysis.")

    mean_hbw = sum(hbw_values) / n
    mean_d = sum(d_values) / n

    if n > 1:
        variance = sum((x - mean_hbw)**2 for x in hbw_values) / (n - 1)
        std_dev = math.sqrt(variance)
        cov_pct = (std_dev / mean_hbw) * 100.0 if mean_hbw > 0 else 0.0
    else:
        std_dev = 0.0
        cov_pct = 0.0

    return {
        'num_trials': n,
        'trials': processed_trials,
        'mean_hbw': round(mean_hbw, 1),
        'mean_d_mm': round(mean_d, 3),
        'min_hbw': round(min(hbw_values), 1),
        'max_hbw': round(max(hbw_values), 1),
        'hbw_range': round(max(hbw_values) - min(hbw_values), 1),
        'std_dev': round(std_dev, 2),
        'cov_pct': round(cov_pct, 2),
        'standard_notation': f"{round(mean_hbw)} HBW {int(ball_diameter_mm)}/{int(load_kgf)}",
        'uts_approx_mpa': round(3.45 * mean_hbw, 1)
    }

def generate_brinell_simulation_data(material_slug, ball_diameter_mm=10.0, load_kgf=3000.0, num_trials=3, ball_d_mm=None):
    """
    Generates realistic, physically-sound demonstration data for the Brinell virtual experiment.
    All data is clearly tagged as SIMULATION / DEMONSTRATION DATA.
    """
    if ball_d_mm is not None:
        ball_diameter_mm = ball_d_mm
    norm_slug = str(material_slug).replace('_', '-')
    preset = BRINELL_MATERIAL_PRESETS.get(norm_slug, BRINELL_MATERIAL_PRESETS.get(material_slug, BRINELL_MATERIAL_PRESETS['mild-steel']))
    target_hbw = preset['nominal_hbw']
    D = float(ball_diameter_mm)
    P = float(load_kgf)

    # Invert Brinell formula to compute theoretical d:
    # HBW = 2P / (pi * D * (D - sqrt(D^2 - d^2)))
    # -> D - sqrt(D^2 - d^2) = 2P / (pi * D * HBW)
    # -> sqrt(D^2 - d^2) = D - (2P / (pi * D * HBW))
    # -> d = sqrt(D^2 - (D - 2P / (pi * D * HBW))^2)
    bracket = D - (2.0 * P) / (math.pi * D * target_hbw)
    if bracket < 0 or bracket > D:
        # Fallback to realistic preset ratio
        bracket = D * 0.85
    base_d = math.sqrt(max(0.01, D**2 - bracket**2))

    trials = []
    # Deterministic seed variation based on slug and load for smooth repeatable animation
    random.seed(int(P * 10 + target_hbw))

    for i in range(1, num_trials + 1):
        # Slight realistic variance (+/- 0.02 - 0.05 mm) representing optical reticle reading tolerance
        var1 = (random.random() - 0.5) * 0.06
        var2 = (random.random() - 0.5) * 0.06
        d1 = round(max(0.1, base_d + var1), 3)
        d2 = round(max(0.1, base_d + var2), 3)
        trials.append({'trial_number': i, 'd1_mm': d1, 'd2_mm': d2})

    analysis = analyze_brinell_trials(trials, D, P)
    analysis['method'] = 'BRINELL'
    analysis['material'] = {'slug': material_slug, 'name': preset['name']}
    analysis['material_name'] = preset['name']
    analysis['data_origin'] = 'SIMULATION / DEMONSTRATION DATA'
    analysis['dwell_sec'] = preset['dwell_sec']
    analysis['readings'] = analysis['trials']
    analysis['summary'] = {'mean_hbw': analysis['mean_hbw'], 'std_dev': analysis['std_dev']}
    return analysis


# ==============================================================================
# 2. ROCKWELL HARDNESS TEST (HR)
# ==============================================================================

# Standard Rockwell Scales (ASTM E18 / ISO 6508-1)
ROCKWELL_SCALES = {
    'B': {
        'scale': 'B',
        'symbol': 'HRB',
        'indenter': '1/16" (1.588 mm) Tungsten Carbide / Steel Ball',
        'indenter_type': 'ball',
        'ball_diameter_mm': 1.5875,
        'minor_load_kgf': 10.0,
        'major_load_kgf': 90.0,
        'total_load_kgf': 100.0,
        'dial_scale': 'Red',
        'dial_constant_N': 130.0,
        'unit_depth_mm': 0.002,  # 1 HR unit = 0.002 mm (2 microns)
        'typical_materials': 'Aluminium alloys, brass, bronze, soft/annealed steels, ductile iron',
        'useful_range': '20 to 100 HRB'
    },
    'C': {
        'scale': 'C',
        'symbol': 'HRC',
        'indenter': '120° Spheroconical Diamond Brale Cone (0.2 mm tip radius)',
        'indenter_type': 'diamond_cone',
        'cone_angle_deg': 120.0,
        'tip_radius_mm': 0.200,
        'minor_load_kgf': 10.0,
        'major_load_kgf': 140.0,
        'total_load_kgf': 150.0,
        'dial_scale': 'Black',
        'dial_constant_N': 100.0,
        'unit_depth_mm': 0.002,
        'typical_materials': 'Hardened steels, quenched & tempered alloys, hard cast iron, tool steels',
        'useful_range': '20 to 70 HRC'
    },
    'A': {
        'scale': 'A',
        'symbol': 'HRA',
        'indenter': '120° Spheroconical Diamond Brale Cone',
        'indenter_type': 'diamond_cone',
        'cone_angle_deg': 120.0,
        'tip_radius_mm': 0.200,
        'minor_load_kgf': 10.0,
        'major_load_kgf': 50.0,
        'total_load_kgf': 60.0,
        'dial_scale': 'Black',
        'dial_constant_N': 100.0,
        'unit_depth_mm': 0.002,
        'typical_materials': 'Cemented tungsten carbides, thin steel sheets, shallow case-hardened layers',
        'useful_range': '60 to 88 HRA'
    }
}
ROCKWELL_SCALES['HRC'] = ROCKWELL_SCALES['C']
ROCKWELL_SCALES['HRB'] = ROCKWELL_SCALES['B']
ROCKWELL_SCALES['HRA'] = ROCKWELL_SCALES['A']

# Standard Rockwell Material Presets
ROCKWELL_MATERIAL_PRESETS = {
    'mild-steel': {
        'name': 'Mild Steel (IS 2062 / AISI 1018)',
        'scale': 'B',
        'nominal_hr': 75.0,
        'symbol': 'HRB',
        'description': 'Normalized hot-rolled mild structural steel'
    },
    'medium-carbon-steel-hardened': {
        'name': 'Medium Carbon Steel (AISI 1045 Quenched & Tempered)',
        'scale': 'C',
        'nominal_hr': 48.0,
        'symbol': 'HRC',
        'description': 'Water-quenched and tempered at 300°C'
    },
    'tool-steel': {
        'name': 'AISI O1 Tool Steel (Quenched & Tempered)',
        'scale': 'C',
        'nominal_hr': 56.5,
        'symbol': 'HRC',
        'description': 'Martensitic tool steel hardened and tempered'
    },
    'tool-steel-h13': {
        'name': 'H13 Tool Steel (Air Hardened & Double Tempered)',
        'scale': 'C',
        'nominal_hr': 54.0,
        'symbol': 'HRC',
        'description': 'Hot-work tool steel for injection molds & extrusion dies'
    },
    'case-hardened-steel': {
        'name': 'Carburized & Case Hardened Alloy Steel',
        'scale': 'C',
        'nominal_hr': 62.0,
        'symbol': 'HRC',
        'description': 'Surface case depth 1.2 mm, martensitically hardened'
    },
    'aluminium-6061-t6': {
        'name': 'Aluminium Alloy 6061-T6',
        'scale': 'B',
        'nominal_hr': 60.0,
        'symbol': 'HRB',
        'description': 'Solution heat treated and artificially aged'
    },
    'cartridge-brass': {
        'name': 'Cartridge Brass (70Cu-30Zn Quarter Hard)',
        'scale': 'B',
        'nominal_hr': 70.0,
        'symbol': 'HRB',
        'description': 'Cold-rolled commercial copper-zinc brass'
    },
    'cemented-carbide': {
        'name': 'Cemented Tungsten Carbide (WC-Co Cutting Insert)',
        'scale': 'A',
        'nominal_hr': 86.0,
        'symbol': 'HRA',
        'description': 'Sintered tungsten carbide insert tested under 60 kgf'
    }
}

def calculate_rockwell_hardness(scale, hardness_reading=None, depth_e_mm=None):
    """
    Calculates or validates Rockwell Hardness according to ASTM E18 / ISO 6508-1.
    
    Formula:
    HR = N - (e / 0.002)
    where:
    - N = 100 for Scale C and Scale A
    - N = 130 for Scale B
    - e = net permanent increase in indentation depth under minor load after major load release (mm)
    - 0.002 mm = depth represented by 1 dial indicator division
    
    If hardness_reading is given, computes the corresponding net indentation depth e.
    If depth_e_mm is given, computes the hardness number.
    """
    scale_raw = str(scale).upper().strip()
    scale_clean = scale_raw.replace('HR', '').strip()
    if scale_clean in ROCKWELL_SCALES:
        scale_key = scale_clean
    elif scale_raw in ROCKWELL_SCALES:
        scale_key = scale_raw
    else:
        raise ValueError(f"Unsupported Rockwell scale '{scale}'. Supported scales are A, B, C.")

    scale_info = ROCKWELL_SCALES[scale_key]
    N = scale_info['dial_constant_N']
    unit_depth = scale_info['unit_depth_mm']

    if hardness_reading is not None:
        hr = float(hardness_reading)
        # e = (N - HR) * 0.002 mm
        e_mm = (N - hr) * unit_depth
    elif depth_e_mm is not None:
        e = float(depth_e_mm)
        if e < 0:
            raise ValueError("Permanent indentation depth cannot be negative.")
        hr = N - (e / unit_depth)
        e_mm = e
    else:
        raise ValueError("Either hardness_reading or depth_e_mm must be provided.")

    # Validity checks according to ASTM E18
    is_valid = True
    warning_msg = None

    if scale_key == 'C':
        if hr < 20.0:
            is_valid = False
            warning_msg = "Reading below 20 HRC: Diamond cone penetration too deep; use Rockwell B or Brinell."
        elif hr > 70.0:
            is_valid = False
            warning_msg = "Reading above 70 HRC: Danger of diamond indenter tip spalling; verify calibration."
    elif scale_key == 'B':
        if hr < 20.0:
            is_valid = False
            warning_msg = "Reading below 20 HRB: Material too soft; danger of anvil effect or ball deformation."
        elif hr > 100.0:
            is_valid = False
            warning_msg = "Reading above 100 HRB: Ball indenter may undergo plastic deformation; use Rockwell C."
    elif scale_key == 'A':
        if hr < 60.0 or hr > 90.0:
            is_valid = False
            warning_msg = f"Reading {hr:.1f} HRA is outside conventional range (60–88 HRA)."

    # Minimum specimen thickness: at least 10 * permanent indentation depth e
    min_thickness = round(max(0.2, 10.0 * e_mm), 3)

    return {
        'scale': scale_key,
        'symbol': scale_info['symbol'],
        'hardness_value': round(hr, 1),
        'depth_e_mm': round(e_mm, 4),
        'depth_e_microns': round(e_mm * 1000.0, 1),
        'dial_constant_N': N,
        'minor_load_kgf': scale_info['minor_load_kgf'],
        'major_load_kgf': scale_info['major_load_kgf'],
        'total_load_kgf': scale_info['total_load_kgf'],
        'indenter': scale_info['indenter'],
        'min_specimen_thickness_mm': min_thickness,
        'is_valid': is_valid,
        'warning_msg': warning_msg
    }

def analyze_rockwell_trials(trials, scale='B'):
    """
    Analyzes multiple Rockwell laboratory readings/trials.
    
    Each trial has:
    - 'trial_number': int
    - 'hardness_reading': float
    
    Returns statistical summary including mean, range, and standard deviation.
    """
    scale_raw = str(scale).upper().strip()
    scale_clean = scale_raw.replace('HR', '').strip()
    if scale_clean in ROCKWELL_SCALES:
        scale_key = scale_clean
    elif scale_raw in ROCKWELL_SCALES:
        scale_key = scale_raw
    else:
        raise ValueError(f"Unsupported Rockwell scale '{scale}'.")

    processed = []
    values = []
    depths = []

    for idx, t in enumerate(trials, start=1):
        if 'hardness_reading' in t or 'value' in t or 'hr' in t:
            val = float(t.get('hardness_reading', t.get('value', t.get('hr', 0.0))))
            res = calculate_rockwell_hardness(scale_key, hardness_reading=val)
        elif 'depth_e_mm' in t or 'depth_mm' in t or 'depth' in t:
            depth = float(t.get('depth_e_mm', t.get('depth_mm', t.get('depth', 0.0))))
            res = calculate_rockwell_hardness(scale_key, depth_e_mm=depth)
            val = res['hardness_value']
        else:
            val = 0.0
            res = calculate_rockwell_hardness(scale_key, hardness_reading=val)

        trial_record = {
            'trial_number': t.get('trial_number', idx),
            'hardness_reading': round(val, 1),
            'hr_value': round(val, 1),
            'depth_e_mm': res['depth_e_mm'],
            'depth_e_microns': res['depth_e_microns'],
            'is_valid': res['is_valid']
        }
        processed.append(trial_record)
        values.append(val)
        depths.append(res['depth_e_mm'])

    n = len(values)
    if n == 0:
        raise ValueError("No valid trials provided for Rockwell analysis.")

    mean_hr = sum(values) / n
    mean_depth = sum(depths) / n

    if n > 1:
        variance = sum((x - mean_hr)**2 for x in values) / (n - 1)
        std_dev = math.sqrt(variance)
        val_range = max(values) - min(values)
    else:
        std_dev = 0.0
        val_range = 0.0

    scale_info = ROCKWELL_SCALES[scale_key]

    return {
        'num_trials': n,
        'scale': scale_key,
        'symbol': scale_info['symbol'],
        'trials': processed,
        'mean_hardness': round(mean_hr, 1),
        'mean_depth_mm': round(mean_depth, 4),
        'min_hardness': round(min(values), 1),
        'max_hardness': round(max(values), 1),
        'hardness_range': round(val_range, 1),
        'std_dev': round(std_dev, 2),
        'standard_notation': f"{round(mean_hr, 1)} {scale_info['symbol']}",
        'indenter': scale_info['indenter'],
        'total_load_kgf': scale_info['total_load_kgf']
    }

def generate_rockwell_simulation_data(material_slug, scale='B', num_trials=3):
    """
    Generates realistic, physically-sound demonstration data for the Rockwell virtual experiment.
    All data is clearly tagged as SIMULATION / DEMONSTRATION DATA.
    """
    norm_slug = str(material_slug).replace('_', '-')
    preset = ROCKWELL_MATERIAL_PRESETS.get(norm_slug, ROCKWELL_MATERIAL_PRESETS.get(material_slug, ROCKWELL_MATERIAL_PRESETS['mild-steel']))
    
    scale_clean = str(scale).upper().replace('HR', '').strip() if scale else ''
    if scale_clean in ['A', 'B', 'C']:
        used_scale = scale_clean
    else:
        used_scale = preset.get('scale', 'B').upper().replace('HR', '')

    if used_scale != preset.get('scale'):
        if used_scale == 'C':
            nominal = 56.5 if 'tool' in str(material_slug) else 45.0
        elif used_scale == 'B':
            nominal = 75.0
        else:
            nominal = 84.0
    else:
        nominal = preset['nominal_hr']

    random.seed(int(nominal * 13))
    trials = []

    for i in range(1, num_trials + 1):
        # Realistic dial variation: +/- 0.5 to 1.2 units
        var = (random.random() - 0.5) * 1.6
        val = round(nominal + var, 1)
        trials.append({'trial_number': i, 'hardness_reading': val})

    analysis = analyze_rockwell_trials(trials, used_scale)
    analysis['method'] = 'ROCKWELL'
    analysis['material'] = {'slug': material_slug, 'name': preset['name']}
    scale_sym = f"HR{used_scale}" if not used_scale.startswith('HR') else used_scale
    analysis['scale'] = {'scale': scale_sym}
    analysis['data_origin'] = 'SIMULATION / DEMONSTRATION DATA'
    analysis['description'] = preset['description']
    analysis['readings'] = analysis['trials']
    analysis['summary'] = {'mean_hr': analysis['mean_hardness'], 'std_dev': analysis['std_dev']}
    return analysis


# ==============================================================================
# 3. ASTM E140 HARDNESS CONVERSION & COMPARISON UTILITIES
# ==============================================================================

# ASTM E140 Table 1 Standard Reference Points (HRC <-> HBW) for non-austenitic steels
ASTM_E140_HRC_HBW = [
    (20.0, 226.0), (22.0, 237.0), (24.0, 247.0), (25.0, 253.0),
    (28.0, 271.0), (30.0, 286.0), (32.0, 301.0), (35.0, 327.0),
    (38.0, 353.0), (40.0, 371.0), (42.0, 390.0), (45.0, 421.0),
    (48.0, 455.0), (50.0, 481.0), (52.0, 512.0), (55.0, 560.0),
    (58.0, 615.0), (60.0, 654.0), (62.0, 688.0), (65.0, 739.0),
    (68.0, 780.0)
]

# ASTM E140 Table 1 Standard Reference Points (HRB <-> HBW)
ASTM_E140_HRB_HBW = [
    (40.0, 75.0), (50.0, 88.0), (60.0, 105.0), (65.0, 114.0),
    (70.0, 125.0), (75.0, 137.0), (80.0, 150.0), (85.0, 165.0),
    (90.0, 185.0), (95.0, 207.0), (100.0, 240.0)
]

def _interp_hardness(x, pts, in_idx, out_idx):
    if x <= pts[0][in_idx]:
        return pts[0][out_idx]
    if x >= pts[-1][in_idx]:
        return pts[-1][out_idx]
    for i in range(len(pts) - 1):
        x1, y1 = pts[i][in_idx], pts[i][out_idx]
        x2, y2 = pts[i+1][in_idx], pts[i+1][out_idx]
        if x1 <= x <= x2:
            return y1 + ((x - x1) / (x2 - x1)) * (y2 - y1)
    return pts[-1][out_idx]

def convert_hardness_approx(value, from_scale, to_scale):
    """
    Empirical approximate hardness conversion for non-austenitic steels (ASTM E140 Table 1).
    Note: Standard cautions that exact conversion is not mathematically absolute due to
    strain-hardening differences across materials.
    """
    val = float(value)
    f_scale = from_scale.upper().strip()
    t_scale = to_scale.upper().strip()

    if f_scale == t_scale:
        return val

    # Convert from source to approximate HBW first
    hbw_approx = None
    if f_scale in ['HBW', 'HB', 'BRINELL']:
        hbw_approx = val
    elif f_scale in ['HRC', 'ROCKWELL_C', 'C']:
        hbw_approx = _interp_hardness(val, ASTM_E140_HRC_HBW, 0, 1)
    elif f_scale in ['HRB', 'ROCKWELL_B', 'B']:
        hbw_approx = _interp_hardness(val, ASTM_E140_HRB_HBW, 0, 1)

    if hbw_approx is None:
        return None

    # Now convert from HBW to target scale
    if t_scale in ['HBW', 'HB', 'BRINELL']:
        return round(hbw_approx, 1)
    elif t_scale in ['HRC', 'ROCKWELL_C', 'C']:
        return round(_interp_hardness(hbw_approx, ASTM_E140_HRC_HBW, 1, 0), 1)
    elif t_scale in ['HRB', 'ROCKWELL_B', 'B']:
        return round(_interp_hardness(hbw_approx, ASTM_E140_HRB_HBW, 1, 0), 1)
    elif t_scale in ['UTS_MPA', 'TENSILE_STRENGTH']:
        return round(3.45 * hbw_approx, 1)

    return None

# ==============================================================================
# CONVENIENCE INTERFACES & ALIASES
# ==============================================================================

def calculate_brinell(load_kgf, ball_d_mm, d1_mm=None, d2_mm=None, indent_d_mm=None):
    """Convenience wrapper for single Brinell indentation calculation."""
    if indent_d_mm is not None:
        mean_d = float(indent_d_mm)
    elif d1_mm is not None and d2_mm is not None:
        mean_d = (float(d1_mm) + float(d2_mm)) / 2.0
    elif d1_mm is not None:
        mean_d = float(d1_mm)
    else:
        raise ValueError("Must provide either indent_d_mm or d1_mm/d2_mm.")
    
    res = calculate_brinell_hardness(load_kgf, ball_d_mm, mean_d)
    res['mean_d_mm'] = round(mean_d, 3)
    res['depth_h_mm'] = res['depth_mm']
    res['min_thickness_mm'] = res['min_specimen_thickness_mm']
    res['p_d2_ratio'] = round(float(load_kgf) / (float(ball_d_mm) ** 2), 2)
    res['is_valid_indentation'] = res['is_valid_indent']
    res['estimated_uts_mpa'] = res['uts_approx_mpa']
    res['validity_note'] = res['validity_message']
    return res

def calculate_brinell_multiple(load_kgf, ball_d_mm, trials):
    """Convenience wrapper for multi-trial Brinell analysis."""
    res = analyze_brinell_trials(trials, ball_d_mm, load_kgf)
    res['trials_results'] = res['trials']
    return res

def calculate_rockwell(scale, depth_e_mm=None, hardness_reading=None):
    """Convenience wrapper for single Rockwell hardness calculation."""
    res = calculate_rockwell_hardness(scale, hardness_reading=hardness_reading, depth_e_mm=depth_e_mm)
    res['hr_value'] = res['hardness_value']
    res['scale_code'] = res['symbol']
    res['indenter_type'] = res['indenter']
    return res

def calculate_rockwell_multiple(scale, trials):
    """Convenience wrapper for multi-trial Rockwell analysis."""
    res = analyze_rockwell_trials(trials, scale=scale)
    res['trials_results'] = res['trials']
    res['mean_hr'] = res['mean_hardness']
    return res

def astm_e140_convert(value, from_scale, to_scale):
    """Convenience wrapper for ASTM E140 hardness conversions returning structured result."""
    conv_val = convert_hardness_approx(value, from_scale, to_scale)
    return {
        'original_value': value,
        'from_scale': from_scale,
        'to_scale': to_scale,
        'converted_value': conv_val,
        'standard': 'ASTM E140 Table 1'
    }

STANDARD_MATERIALS_HARDNESS = BRINELL_MATERIAL_PRESETS

