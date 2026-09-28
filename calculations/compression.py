"""
MAT-VLAB Materials Testing Suite: Uniaxial Compression Testing Calculation Engine
Standards:
- ASTM E9: Standard Test Methods of Compression Testing of Metallic Materials at Room Temperature
- ISO 13314: Mechanical testing of metals — Ductility testing — Compression test for porous and cellular metals
- ASTM A370: Compression Testing of Metallic Products

Covers:
1. Cylindrical specimen geometry (short/medium/long slenderness ratio h0/d0).
2. Engineering compressive stress and compressive strain:
   sigma_c = F / A_0
   epsilon_c = Delta_h / h_0 = (h_0 - h) / h_0
3. True stress and true strain in compression:
   epsilon_true = ln(h_0 / h) = ln(1 / (1 - epsilon_c))
   sigma_true = F / A_inst = sigma_c * (1 - epsilon_c) [assuming constant volume]
4. Compressive modulus of elasticity (Ec) via linear least-squares regression.
5. 0.2% offset compressive yield strength (sigma_cy) according to ASTM E9.
6. Ultimate compressive strength (sigma_cu) for brittle materials (shear fracture along ~45 deg).
7. Flow stress at specified strains (sigma_10%, sigma_20%) for ductile barreling metals.
8. Barreling coefficient and platen interfacial friction evaluation:
   Barreling index B = (d_mid - d_end) / d_0
9. Physically grounded simulation datasets for brittle and ductile engineering metals.
"""

import math
import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Any, Tuple


# ==============================================================================
# 1. SPECIMEN STANDARDS & MATERIAL PRESETS
# ==============================================================================

COMPRESSION_SPECIMEN_STANDARDS = {
    'standard_medium': {
        'name': 'Standard Medium Cylindrical Specimen (ASTM E9)',
        'd0_mm': 15.0,
        'h0_mm': 30.0,
        'slenderness_ratio': 2.0,  # h0 / d0 = 2.0 (resists buckling while minimizing platen constraint)
        'area_mm2': 176.71,
        'volume_mm3': 5301.44
    },
    'short_cylinder': {
        'name': 'Short Cylindrical Specimen (ASTM E9 for Bearing Alloys)',
        'd0_mm': 15.0,
        'h0_mm': 15.0,
        'slenderness_ratio': 1.0,
        'area_mm2': 176.71,
        'volume_mm3': 2650.72
    },
    'small_cylinder': {
        'name': 'Compact Cylindrical Specimen (Universal Tooling)',
        'd0_mm': 10.0,
        'h0_mm': 20.0,
        'slenderness_ratio': 2.0,
        'area_mm2': 78.54,
        'volume_mm3': 1570.80
    }
}

COMPRESSION_MATERIAL_PRESETS = {
    'grey-cast-iron': {
        'name': 'Grey Cast Iron (FG 200 / ASTM A48)',
        'category': 'Brittle Ferrous',
        'is_brittle': True,
        'E_GPa': 110.0,
        'compressive_yield_mpa': 220.0,
        'ultimate_compressive_mpa': 680.0,
        'fracture_strain_pct': 14.5,
        'fracture_angle_deg': 45.0,
        'fracture_mode': 'Brittle Shear Fracture along ~45° Maximum Shear Plane',
        'notes': 'Significantly stronger in compression (~680 MPa) than tension (~200 MPa) due to graphite flake blunting in compression.'
    },
    'mild-steel': {
        'name': 'Mild Steel (AISI 1018 / IS 2062)',
        'category': 'Ductile Ferrous',
        'is_brittle': False,
        'E_GPa': 205.0,
        'compressive_yield_mpa': 255.0,
        'flow_stress_10pct_mpa': 460.0,
        'flow_stress_20pct_mpa': 590.0,
        'flow_stress_30pct_mpa': 720.0,
        'max_strain_pct': 45.0,
        'barreling_index': 0.22,
        'fracture_mode': 'Ductile Barreling & Plastic Flattening (No Discrete Fracture)',
        'notes': 'Undergoes continuous plastic strain hardening with barreling due to frictional shear constraint at platen interfaces.'
    },
    'aluminium-6061-t6': {
        'name': 'Aluminium Alloy (6061-T6)',
        'category': 'Ductile Non-Ferrous',
        'is_brittle': False,
        'E_GPa': 69.0,
        'compressive_yield_mpa': 275.0,
        'flow_stress_10pct_mpa': 330.0,
        'flow_stress_20pct_mpa': 385.0,
        'flow_stress_30pct_mpa': 430.0,
        'max_strain_pct': 40.0,
        'barreling_index': 0.18,
        'fracture_mode': 'Ductile Barreling with High Plastic Resistance',
        'notes': 'Stable compressive flow with lower work hardening compared to steel; friction lubrication is essential.'
    },
    'cartridge-brass': {
        'name': 'Cartridge Brass (70Cu-30Zn Annealed)',
        'category': 'Ductile Non-Ferrous',
        'is_brittle': False,
        'E_GPa': 110.0,
        'compressive_yield_mpa': 135.0,
        'flow_stress_10pct_mpa': 340.0,
        'flow_stress_20pct_mpa': 480.0,
        'flow_stress_30pct_mpa': 580.0,
        'max_strain_pct': 50.0,
        'barreling_index': 0.24,
        'fracture_mode': 'Extensive Plastic Flow & Barreling',
        'notes': 'High strain-hardening capacity leads to rapid increase in compressive flow resistance.'
    },
    'pure-copper': {
        'name': 'Electrolytic Tough Pitch (ETP) Copper',
        'category': 'Ductile Non-Ferrous',
        'is_brittle': False,
        'E_GPa': 117.0,
        'compressive_yield_mpa': 75.0,
        'flow_stress_10pct_mpa': 210.0,
        'flow_stress_20pct_mpa': 285.0,
        'flow_stress_30pct_mpa': 340.0,
        'max_strain_pct': 55.0,
        'barreling_index': 0.26,
        'fracture_mode': 'Massive Plastic Flattening without Fracture',
        'notes': 'Very low initial yield strength progressing into high work hardening.'
    }
}


def _sanitize_for_json(val: Any) -> Any:
    """Recursively converts NumPy scalar types and arrays to standard Python types for JSON serialization."""
    if isinstance(val, dict):
        return {k: _sanitize_for_json(v) for k, v in val.items()}
    elif isinstance(val, (list, tuple)):
        return [_sanitize_for_json(v) for v in val]
    elif isinstance(val, (np.bool_, bool)):
        return bool(val)
    elif isinstance(val, (np.integer, int)):
        return int(val)
    elif isinstance(val, (np.floating, float)):
        return float(val)
    elif isinstance(val, np.ndarray):
        return val.tolist()
    return val


def get_compression_preset(slug: str) -> Dict[str, Any]:
    norm = (slug or '').lower().replace('_', '-').strip()
    if norm in COMPRESSION_MATERIAL_PRESETS:
        return COMPRESSION_MATERIAL_PRESETS[norm]
    if 'cast-iron' in norm or 'grey' in norm or 'ci' in norm:
        return COMPRESSION_MATERIAL_PRESETS['grey-cast-iron']
    if 'aluminium' in norm or 'aluminum' in norm or 'al' in norm:
        return COMPRESSION_MATERIAL_PRESETS['aluminium-6061-t6']
    if 'brass' in norm:
        return COMPRESSION_MATERIAL_PRESETS['cartridge-brass']
    if 'copper' in norm:
        return COMPRESSION_MATERIAL_PRESETS['pure-copper']
    return COMPRESSION_MATERIAL_PRESETS['mild-steel']


# ==============================================================================
# 2. CORE MATHEMATICAL FORMULAS
# ==============================================================================

def calculate_cylindrical_area(diameter_mm: float) -> float:
    """Calculates cross-sectional area of cylindrical specimen: A0 = (pi * d0^2) / 4"""
    if diameter_mm <= 0:
        raise ValueError("Specimen diameter must be greater than zero.")
    return (math.pi * (diameter_mm ** 2)) / 4.0


def calculate_compressive_stress(load_n: float, initial_area_mm2: float) -> float:
    """Engineering compressive stress: sigma_c = F / A_0 (MPa = N/mm^2)"""
    return load_n / initial_area_mm2


def calculate_compressive_strain(delta_h_mm: float, initial_height_mm: float) -> float:
    """Engineering compressive strain: epsilon_c = Delta_h / h_0 = (h_0 - h) / h_0"""
    return delta_h_mm / initial_height_mm


def calculate_true_stress_strain(engineering_stress_mpa: float,
                                 engineering_strain: float) -> Tuple[float, float]:
    """
    Computes true compressive stress and true compressive strain:
    epsilon_true = ln(1 / (1 - epsilon_c))
    sigma_true = sigma_c * (1 - epsilon_c)
    """
    if engineering_strain >= 0.99:
        engineering_strain = 0.99
    eps_true = -math.log(max(0.01, 1.0 - engineering_strain))
    sig_true = engineering_stress_mpa * (1.0 - engineering_strain)
    return round(sig_true, 2), round(eps_true, 6)


def calculate_barreling_index(final_mid_diameter_mm: float,
                              final_end_diameter_mm: float,
                              initial_diameter_mm: float) -> float:
    """
    Barreling index B = (d_mid - d_end) / d_0
    Evaluates severity of frictional constraint at platen surfaces (ASTM E9).
    """
    if initial_diameter_mm <= 0:
        return 0.0
    return round((final_mid_diameter_mm - final_end_diameter_mm) / initial_diameter_mm, 4)


# ==============================================================================
# 3. COMPLETE LABORATORY ANALYSIS ENGINE
# ==============================================================================

def analyze_compression_data(original_diameter_mm: float,
                             original_height_mm: float,
                             readings: List[Dict[str, Any]],
                             final_height_mm: Optional[float] = None,
                             final_mid_diameter_mm: Optional[float] = None,
                             final_end_diameter_mm: Optional[float] = None,
                             material_name: Optional[str] = None) -> Dict[str, Any]:
    """
    Performs complete engineering compression analysis on laboratory readings according to ASTM E9.

    Parameters:
    - original_diameter_mm: d0 (mm)
    - original_height_mm: h0 (mm)
    - readings: List of dicts, each with 'load_kn' (or 'load_n') and 'delta_h_mm'
    - final_height_mm: Measured height after test (mm)
    - final_mid_diameter_mm: Bulge diameter at mid-height (mm)
    - final_end_diameter_mm: Contact diameter at platens (mm)
    - material_name: Optional material name

    Returns:
    Dict containing:
    - computed_readings: List with compressive stress, engineering strain, true stress, true strain
    - summary: E_c, Compressive Yield (0.2%), Ultimate/Max Strength, Max Strain %, Barreling Index
    - formulas: Scientific expressions with numerical substitutions
    - conclusion: Metallurgical assessment against ASTM E9
    """
    warnings = []

    if original_diameter_mm is None or original_diameter_mm <= 0:
        raise ValueError("Specimen original diameter must be a positive number.")
    if original_height_mm is None or original_height_mm <= 0:
        raise ValueError("Specimen original height must be a positive number.")
    if not readings or len(readings) < 2:
        raise ValueError("At least 2 valid readings are required to analyze compression behavior.")

    d0 = float(original_diameter_mm)
    h0 = float(original_height_mm)
    a0 = calculate_cylindrical_area(d0)
    slenderness = h0 / d0

    if slenderness > 3.0:
        warnings.append(f"Slenderness ratio h0/d0 = {slenderness:.2f} exceeds recommended ASTM E9 limit of 3.0; column buckling risk is elevated.")
    elif slenderness < 1.0:
        warnings.append(f"Slenderness ratio h0/d0 = {slenderness:.2f} is under 1.0; triaxial platen constraint will artificially elevate apparent strength.")

    # Parse and validate readings
    valid_points = []
    for idx, r in enumerate(readings, start=1):
        try:
            # support both load_kn and load_n
            if 'load_kn' in r and r['load_kn'] is not None:
                load_n = float(r['load_kn']) * 1000.0
            elif 'load_n' in r and r['load_n'] is not None:
                load_n = float(r['load_n'])
            else:
                continue

            dh = float(r.get('delta_h_mm') or r.get('stroke_mm') or r.get('displacement_mm') or 0.0)
        except (ValueError, TypeError):
            continue

        if load_n < 0:
            load_n = 0.0
        if dh < 0:
            dh = 0.0

        stress_mpa = calculate_compressive_stress(load_n, a0)
        strain = calculate_compressive_strain(dh, h0)
        true_sig, true_eps = calculate_true_stress_strain(stress_mpa, strain)

        valid_points.append({
            'reading_number': idx,
            'load_kn': round(load_n / 1000.0, 3),
            'load_n': round(load_n, 1),
            'delta_h_mm': round(dh, 4),
            'stress_mpa': round(stress_mpa, 2),
            'strain': round(strain, 6),
            'strain_pct': round(strain * 100.0, 3),
            'true_stress_mpa': true_sig,
            'true_strain': true_eps
        })

    if len(valid_points) < 2:
        raise ValueError("Insufficient valid compression data points after parsing.")

    df = pd.DataFrame(valid_points)
    loads_n = df['load_n'].to_numpy(dtype=float)
    stresses = df['stress_mpa'].to_numpy(dtype=float)
    strains = df['strain'].to_numpy(dtype=float)

    # 1. Peak / Ultimate Compressive Strength
    max_idx = int(np.argmax(loads_n))
    max_load_n = float(loads_n[max_idx])
    max_stress_mpa = float(stresses[max_idx])
    max_strain_pct = float(strains[-1] * 100.0)

    # 2. Young's Modulus in Compression (Ec) via linear elastic fit
    # Initial linear range: between 10% and 55% of peak stress
    candidate_mask = (stresses > 0.08 * max_stress_mpa) & (stresses < 0.55 * max_stress_mpa) & (strains > 0.0001)
    cand_indices = np.where(candidate_mask)[0]

    ec_gpa = None
    r_squared = 0.0
    if len(cand_indices) >= 3:
        fit_strains = strains[cand_indices]
        fit_stresses = stresses[cand_indices]
        slope, intercept = np.polyfit(fit_strains, fit_stresses, 1)
        ec_gpa = round(slope / 1000.0, 2)
        # Calculate R^2
        preds = slope * fit_strains + intercept
        ss_res = np.sum((fit_stresses - preds) ** 2)
        ss_tot = np.sum((fit_stresses - np.mean(fit_stresses)) ** 2)
        r_squared = round(1.0 - (ss_res / ss_tot) if ss_tot > 0 else 0.0, 4)
    else:
        # Fallback two-point slope
        p1 = valid_points[1]
        p2 = valid_points[min(4, len(valid_points) - 1)]
        d_eps = p2['strain'] - p1['strain']
        if d_eps > 0:
            ec_gpa = round((p2['stress_mpa'] - p1['stress_mpa']) / (d_eps * 1000.0), 2)
            r_squared = 0.95

    # 3. 0.2% Offset Compressive Yield Strength (sigma_cy)
    yield_strength_mpa = None
    offset_strain = 0.002  # 0.2%
    if ec_gpa and ec_gpa > 0:
        e_mpa = ec_gpa * 1000.0
        # Offset line: sigma_offset(strain) = E * (strain - 0.002)
        for i in range(1, len(strains)):
            eps = strains[i]
            sig = stresses[i]
            sig_offset = e_mpa * (eps - offset_strain)
            if eps > offset_strain and sig <= sig_offset:
                # Linear interpolation for precise intersection
                eps_prev = strains[i - 1]
                sig_prev = stresses[i - 1]
                sig_off_prev = e_mpa * (eps_prev - offset_strain)
                denom = (sig - sig_prev) - (sig_offset - sig_off_prev)
                if abs(denom) > 1e-6:
                    t = (sig_off_prev - sig_prev) / denom
                    inter_sig = sig_prev + t * (sig - sig_prev)
                    yield_strength_mpa = round(float(inter_sig), 2)
                else:
                    yield_strength_mpa = round(float(sig), 2)
                break

    if yield_strength_mpa is None:
        # Approximate 0.2% yield if offset didn't cross
        for pt in valid_points:
            if pt['strain'] >= 0.005:
                yield_strength_mpa = pt['stress_mpa']
                break
        if yield_strength_mpa is None:
            yield_strength_mpa = round(max_stress_mpa * 0.70, 2)

    # 4. Flow stresses at 10%, 20%, 30% strain
    flow_stresses = {}
    for target_pct in [10.0, 20.0, 30.0]:
        target_strain = target_pct / 100.0
        for pt in valid_points:
            if pt['strain'] >= target_strain:
                flow_stresses[f'sigma_{int(target_pct)}pct_mpa'] = pt['stress_mpa']
                break

    # 5. Barreling Analysis
    barreling_index = 0.0
    if final_mid_diameter_mm and final_end_diameter_mm:
        barreling_index = calculate_barreling_index(final_mid_diameter_mm, final_end_diameter_mm, d0)
    elif final_height_mm and final_height_mm < h0:
        # Theoretical constant-volume mid-bulge estimation
        # Assuming parabolic barreling profile
        delta_h = h0 - final_height_mm
        area_avg = (a0 * h0) / final_height_mm
        d_equiv = math.sqrt((4.0 * area_avg) / math.pi)
        barreling_index = round(max(0.05, (d_equiv - d0) / d0 * 0.65), 3)

    # Detect if material behaves as brittle or ductile
    # If stress dropped significantly (>20%) after peak, likely brittle shear fracture
    stress_drop = (max_stress_mpa - stresses[-1]) / max_stress_mpa if max_stress_mpa > 0 else 0
    is_brittle_behavior = (stress_drop > 0.25 and max_strain_pct < 20.0)

    if is_brittle_behavior:
        behavior_mode = "Brittle Shear Fracture (~45° failure plane)"
        strength_metric_name = "Ultimate Compressive Strength (σ_cu)"
    else:
        behavior_mode = "Ductile Plastic Flow with Progressive Barreling"
        strength_metric_name = "Peak Test Compressive Stress (σ_c,max)"

    # Engineering conclusion
    conclusion = generate_compression_conclusion(
        material_name=material_name or "Metallic Specimen",
        d0=d0,
        h0=h0,
        slenderness=slenderness,
        ec_gpa=ec_gpa,
        yield_mpa=yield_strength_mpa,
        max_stress_mpa=max_stress_mpa,
        max_strain_pct=max_strain_pct,
        barreling_index=barreling_index,
        behavior_mode=behavior_mode,
        is_brittle=is_brittle_behavior
    )

    formulas = {
        'compressive_stress': {
            'latex': r'\sigma_c = \frac{F}{A_0}',
            'plain': f'σ_c = F / ({a0:.2f} mm²) | Max σ_c = {max_stress_mpa:.2f} MPa',
            'meaning': 'Engineering Compressive Stress = Axial Compressive Force / Original Cross-Sectional Area'
        },
        'compressive_strain': {
            'latex': r'\varepsilon_c = \frac{\Delta h}{h_0}',
            'plain': f'ε_c = Δh / {h0:.2f} mm | Final ε_c = {max_strain_pct:.2f}%',
            'meaning': 'Engineering Compressive Strain = Height Reduction / Original Gauge Height'
        },
        'modulus_elasticity': {
            'latex': r'E_c = \frac{\Delta \sigma_c}{\Delta \varepsilon_c}',
            'plain': f'E_c = {ec_gpa if ec_gpa else 0.0:.2f} GPa (Linear regression R² = {r_squared:.4f})',
            'meaning': 'Compressive Modulus of Elasticity from initial linear slope'
        },
        'offset_yield': {
            'latex': r'\sigma_{cy} \text{ (0.2\% offset)}',
            'plain': f'σ_cy (0.2%) = {yield_strength_mpa:.2f} MPa',
            'meaning': '0.2% Proof Stress determined by shifting linear modulus line by 0.002 strain'
        }
    }

    return _sanitize_for_json({
        'specimen': {
            'original_diameter_mm': d0,
            'original_height_mm': h0,
            'slenderness_ratio': round(slenderness, 2),
            'original_area_mm2': round(a0, 2),
            'final_height_mm': round(final_height_mm if final_height_mm else h0 - df['delta_h_mm'].iloc[-1], 2),
            'barreling_index': barreling_index
        },
        'computed_readings': valid_points,
        'summary': {
            'num_readings': len(valid_points),
            'max_load_kn': round(max_load_n / 1000.0, 2),
            'max_stress_mpa': round(max_stress_mpa, 2),
            'strength_metric_name': strength_metric_name,
            'compressive_yield_mpa': round(yield_strength_mpa, 2),
            'elastic_modulus_gpa': ec_gpa,
            'final_strain_pct': round(max_strain_pct, 2),
            'barreling_index': barreling_index,
            'behavior_mode': behavior_mode,
            'is_brittle': is_brittle_behavior,
            'flow_stresses': flow_stresses
        },
        'formulas': formulas,
        'conclusion': conclusion,
        'warnings': warnings
    })


def generate_compression_conclusion(material_name: str,
                                    d0: float,
                                    h0: float,
                                    slenderness: float,
                                    ec_gpa: Optional[float],
                                    yield_mpa: float,
                                    max_stress_mpa: float,
                                    max_strain_pct: float,
                                    barreling_index: float,
                                    behavior_mode: str,
                                    is_brittle: bool) -> str:
    """Generates an algorithmic objective metallurgical compression conclusion."""
    c = f"Uniaxial compression testing of {material_name} (d₀ = {d0:.1f} mm, h₀ = {h0:.1f} mm, slenderness ratio h₀/d₀ = {slenderness:.2f}) "
    c += f"demonstrated {behavior_mode}. "

    if ec_gpa:
        c += f"The compressive elastic modulus was determined as E_c = {ec_gpa:.1f} GPa, with a 0.2% offset compressive yield strength of σ_cy = {yield_mpa:.1f} MPa. "

    if is_brittle:
        c += f"Catastrophic shear fracture occurred along the characteristic ~45° maximum shear plane at an ultimate compressive strength of σ_cu = {max_stress_mpa:.1f} MPa with limited compressive strain ({max_strain_pct:.1f}%). "
        c += "This behavior aligns with Coulomb-Mohr fracture criteria for brittle materials where compressive strength greatly exceeds tensile capacity."
    else:
        c += f"Under continued plastic deformation, the material exhibited continuous strain hardening up to a maximum applied stress of {max_stress_mpa:.1f} MPa at {max_strain_pct:.1f}% compressive strain. "
        c += f"Specimen barreling (barreling index B = {barreling_index:.3f}) was observed as interfacial friction between the sub-press platens and specimen ends constrained radial expansion, generating a localized triaxial stress state."

    return c


# ==============================================================================
# 4. SIMULATION DATASET GENERATOR
# ==============================================================================

def generate_compression_simulation_data(material_slug: str = 'mild-steel',
                                         diameter_mm: float = 15.0,
                                         height_mm: float = 30.0,
                                         num_points: int = 35) -> Dict[str, Any]:
    """
    Generates physically grounded compression stress-strain curve data based on constitutive models:
    - Grey Cast Iron: Brittle linear elastic, micro-crack coalescing, 45 deg shear fracture at ~680 MPa.
    - Mild Steel: Elastic slope E = 205 GPa, yield ~255 MPa, Luders plateau, power-law hardening up to 40% strain with barreling.
    - Aluminium 6061-T6: Ramberg-Osgood continuous yielding with smooth work hardening and barreling.
    - Brass C26000: High strain hardening exponent.
    - Pure Copper C11000: Extensive plastic flow.
    """
    d0 = float(diameter_mm)
    h0 = float(height_mm)
    a0 = calculate_cylindrical_area(d0)

    preset = get_compression_preset(material_slug)
    is_brittle = preset.get('is_brittle', False)
    e_mpa = preset['E_GPa'] * 1000.0

    strains = [0.0]
    stresses = [0.0]

    if is_brittle:
        # Cast Iron model: slight non-linearity leading to sudden shear fracture
        max_eps = preset['fracture_strain_pct'] / 100.0
        uts_c = preset['ultimate_compressive_mpa']

        # Linear elastic section (up to ~40% max stress)
        eps_el = (0.40 * uts_c) / e_mpa
        for f in np.linspace(0.1, 1.0, 8):
            eps = eps_el * f
            sig = e_mpa * eps
            strains.append(eps)
            stresses.append(sig)

        # Micro-crack progression curve to fracture
        remaining_eps = np.linspace(eps_el + 0.002, max_eps, num_points - 10)
        for eps in remaining_eps:
            xi = (eps - eps_el) / (max_eps - eps_el)
            # Power law transition to fracture peak
            sig = (0.40 * uts_c) + (0.60 * uts_c) * (xi ** 0.65)
            # Add slight physical measurement noise
            sig += np.random.uniform(-1.5, 1.5)
            strains.append(eps)
            stresses.append(sig)

        # Sudden fracture drop
        strains.append(max_eps + 0.002)
        stresses.append(uts_c * 0.15)
        strains.append(max_eps + 0.005)
        stresses.append(0.0)

    else:
        # Ductile Metals: Mild Steel / Aluminium / Brass / Copper
        max_eps = preset.get('max_strain_pct', 45.0) / 100.0
        sig_y = preset['compressive_yield_mpa']
        eps_y = sig_y / e_mpa

        # 1. Elastic points (7 points)
        for f in np.linspace(0.15, 1.0, 7):
            eps = eps_y * f
            sig = e_mpa * eps
            strains.append(eps)
            stresses.append(sig)

        # 2. Plastic regime with Luders plateau (for mild steel) or smooth hardening
        if material_slug == 'mild-steel':
            # Yield plateau
            strains.append(eps_y + 0.002)
            stresses.append(sig_y * 0.98)
            strains.append(eps_y + 0.008)
            stresses.append(sig_y * 0.99)
            strains.append(eps_y + 0.015)
            stresses.append(sig_y)

            # Power law strain hardening with barreling geometric stiffening
            plastic_strains = np.linspace(eps_y + 0.02, max_eps, num_points - 12)
            k_hardening = 780.0
            n_hardening = 0.28
            for eps in plastic_strains:
                eps_p = eps - eps_y
                # Friction barreling increases apparent stress by factor (1 + mu*d0 / (3*h))
                barreling_factor = 1.0 + 0.15 * (eps ** 1.2)
                sig = (sig_y + k_hardening * (eps_p ** n_hardening)) * barreling_factor
                sig += np.random.uniform(-1.8, 1.8)
                strains.append(eps)
                stresses.append(sig)
        else:
            # Ramberg-Osgood / Hollomon hardening
            plastic_strains = np.linspace(eps_y + 0.005, max_eps, num_points - 8)
            k_hardening = 550.0 if 'aluminium' in material_slug else 650.0
            n_hardening = 0.15 if 'aluminium' in material_slug else 0.35
            for eps in plastic_strains:
                eps_p = eps - eps_y
                barreling_factor = 1.0 + 0.12 * (eps ** 1.1)
                sig = (sig_y + k_hardening * (eps_p ** n_hardening)) * barreling_factor
                sig += np.random.uniform(-1.2, 1.2)
                strains.append(eps)
                stresses.append(sig)

    # Convert strains & stresses into discrete laboratory readings: load (kN) and delta_h (mm)
    sim_readings = []
    for idx, (eps, sig) in enumerate(zip(strains, stresses), start=1):
        if idx == 1:
            continue  # skip origin for readings list
        dh = eps * h0
        load_n = sig * a0
        sim_readings.append({
            'reading_number': len(sim_readings) + 1,
            'load_kn': round(load_n / 1000.0, 3),
            'load_n': round(load_n, 1),
            'delta_h_mm': round(dh, 3),
            'stress_mpa': round(sig, 2),
            'strain': round(eps, 5),
            'strain_pct': round(eps * 100.0, 3)
        })

    final_dh = sim_readings[-1]['delta_h_mm']
    final_h = round(h0 - final_dh, 2)
    # Estimate final mid diameter and end diameter
    b_idx = preset.get('barreling_index', 0.20) if not is_brittle else 0.02
    final_mid_d = round(d0 * (1.0 + b_idx + (final_dh / h0) * 0.5), 2)
    final_end_d = round(d0 * (1.0 + (final_dh / h0) * 0.3), 2)

    # Run analysis engine
    analysis = analyze_compression_data(
        original_diameter_mm=d0,
        original_height_mm=h0,
        readings=sim_readings,
        final_height_mm=final_h,
        final_mid_diameter_mm=final_mid_d,
        final_end_diameter_mm=final_end_d,
        material_name=preset['name']
    )

    return _sanitize_for_json({
        'material_slug': material_slug,
        'material_name': preset['name'],
        'category': preset['category'],
        'is_brittle': is_brittle,
        'specimen': analysis['specimen'],
        'readings': sim_readings,
        'summary': analysis['summary'],
        'formulas': analysis['formulas'],
        'conclusion': analysis['conclusion'],
        'notes': preset.get('notes', '')
    })
