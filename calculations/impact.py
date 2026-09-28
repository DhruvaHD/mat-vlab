"""
MAT-VLAB Materials Testing Suite: Impact Testing Calculation Engine
Standards:
- ASTM E23: Standard Test Methods for Notched Bar Impact Testing of Metallic Materials
- ISO 148-1: Metallic materials — Charpy pendulum impact test — Part 1: Test method
- ASTM A370: Mechanical Testing of Steel Products (Charpy V-Notch section)

Covers:
1. Charpy V-notch (CVN), Charpy U-notch, and Izod impact testing.
2. Absorbed energy calculation with friction & windage tare loss compensation:
   KV = E_initial - E_residual - L_friction
3. Notch impact toughness (impact strength):
   a_k = KV / A_0 (J/cm^2 or kJ/m^2)
4. Ductile-to-Brittle Transition Temperature (DBTT) curve modeling using hyperbolic tangent:
   KV(T) = A + B * tanh((T - T0) / C)
5. Fracture appearance transition temperature (FATT50) & percent shear fracture estimation.
6. Multi-trial laboratory readings analysis and statistical variance.
7. Physically realistic simulation generator for engineering alloys across temperatures.
"""

import math
import random
from typing import Dict, List, Optional, Any


# ==============================================================================
# 1. SPECIMEN GEOMETRIES & STANDARD DIMENSIONS
# ==============================================================================

IMPACT_SPECIMEN_STANDARDS = {
    'charpy_v': {
        'name': 'Standard Charpy V-Notch (ASTM E23 Type A / ISO 148)',
        'type': 'Charpy (Three-Point Simple Beam)',
        'width_mm': 10.0,
        'height_mm': 10.0,
        'length_mm': 55.0,
        'notch_depth_mm': 2.0,
        'notch_radius_mm': 0.25,
        'notch_angle_deg': 45.0,
        'net_cross_section_mm2': 80.0,  # 10mm x (10mm - 2mm)
        'net_cross_section_cm2': 0.80,
        'support_span_mm': 40.0
    },
    'charpy_u': {
        'name': 'Standard Charpy U-Notch (ASTM E23 Type B / ISO 148)',
        'type': 'Charpy (Three-Point Simple Beam)',
        'width_mm': 10.0,
        'height_mm': 10.0,
        'length_mm': 55.0,
        'notch_depth_mm': 5.0,
        'notch_radius_mm': 1.0,
        'notch_angle_deg': 0.0,
        'net_cross_section_mm2': 50.0,  # 10mm x (10mm - 5mm)
        'net_cross_section_cm2': 0.50,
        'support_span_mm': 40.0
    },
    'izod_v': {
        'name': 'Standard Izod V-Notch (ASTM E23 / ISO 180)',
        'type': 'Izod (Cantilever Beam)',
        'width_mm': 10.0,
        'height_mm': 10.0,
        'length_mm': 75.0,
        'notch_depth_mm': 2.0,
        'notch_radius_mm': 0.25,
        'notch_angle_deg': 45.0,
        'net_cross_section_mm2': 80.0,
        'net_cross_section_cm2': 0.80,
        'striking_distance_mm': 22.0  # distance from notch to striker line
    }
}


# Reference metallurgical properties for Charpy V-Notch impact
IMPACT_MATERIAL_PRESETS = {
    'mild-steel': {
        'name': 'Mild Steel (AISI 1018 / IS 2062)',
        'structure': 'BCC (Ferritic-Pearlitic)',
        'has_dbtt': True,
        'dbtt_celsius': -15.0,
        'upper_shelf_energy_j': 165.0,
        'lower_shelf_energy_j': 8.0,
        'transition_slope_c': 28.0,
        'nominal_room_temp_energy_j': 145.0,
        'lateral_expansion_mm': 1.65,
        'room_temp_pct_shear': 85.0,
        'notes': 'Prominent ductile-to-brittle transition due to temperature-sensitive Peierls-Nabarro stress in BCC lattice.'
    },
    'medium-carbon-steel': {
        'name': 'Medium Carbon Steel (AISI 1045 Normalized)',
        'structure': 'BCC (Pearlitic)',
        'has_dbtt': True,
        'dbtt_celsius': 25.0,
        'upper_shelf_energy_j': 75.0,
        'lower_shelf_energy_j': 6.0,
        'transition_slope_c': 35.0,
        'nominal_room_temp_energy_j': 42.0,
        'lateral_expansion_mm': 0.70,
        'room_temp_pct_shear': 45.0,
        'notes': 'Higher carbon content shifts DBTT above room temperature with moderate upper-shelf toughness.'
    },
    'alloy-steel-4140': {
        'name': 'Alloy Steel (AISI 4140 Quenched & Tempered)',
        'structure': 'BCC/BCT (Tempered Martensite)',
        'has_dbtt': True,
        'dbtt_celsius': -40.0,
        'upper_shelf_energy_j': 110.0,
        'lower_shelf_energy_j': 12.0,
        'transition_slope_c': 22.0,
        'nominal_room_temp_energy_j': 98.0,
        'lateral_expansion_mm': 1.30,
        'room_temp_pct_shear': 90.0,
        'notes': 'Fine tempered martensitic microstructure provides high strength and excellent sub-zero toughness.'
    },
    'stainless-steel-304': {
        'name': 'Austenitic Stainless Steel (AISI 304)',
        'structure': 'FCC (Austenitic)',
        'has_dbtt': False,
        'upper_shelf_energy_j': 240.0,
        'lower_shelf_energy_j': 180.0,
        'nominal_room_temp_energy_j': 235.0,
        'lateral_expansion_mm': 2.10,
        'room_temp_pct_shear': 100.0,
        'notes': 'Face-Centered Cubic (FCC) lattice has 12 slip systems active even at cryogenic temperatures; NO DBTT.'
    },
    'aluminium-6061-t6': {
        'name': 'Aluminium Alloy (6061-T6)',
        'structure': 'FCC (Precipitation Hardened)',
        'has_dbtt': False,
        'upper_shelf_energy_j': 32.0,
        'lower_shelf_energy_j': 28.0,
        'nominal_room_temp_energy_j': 30.0,
        'lateral_expansion_mm': 0.55,
        'room_temp_pct_shear': 100.0,
        'notes': 'FCC aluminium maintains uniform toughness from -196 deg C to room temperature without brittle cleavage transition.'
    },
    'grey-cast-iron': {
        'name': 'Grey Cast Iron (FG 200 / ASTM A48)',
        'structure': 'Graphitic Flake Matrix',
        'has_dbtt': False,
        'upper_shelf_energy_j': 4.5,
        'lower_shelf_energy_j': 3.0,
        'nominal_room_temp_energy_j': 4.0,
        'lateral_expansion_mm': 0.05,
        'room_temp_pct_shear': 0.0,
        'notes': 'Graphite flakes act as internal sharp stress concentrations, causing brittle cleavage fracture under minimal impact energy.'
    },
    'structural-steel-is2062': {
        'name': 'Structural Steel Grade E250 (IS 2062)',
        'structure': 'BCC (Structural Ferrite)',
        'has_dbtt': True,
        'dbtt_celsius': -20.0,
        'upper_shelf_energy_j': 150.0,
        'lower_shelf_energy_j': 9.0,
        'transition_slope_c': 25.0,
        'nominal_room_temp_energy_j': 135.0,
        'lateral_expansion_mm': 1.50,
        'room_temp_pct_shear': 88.0,
        'notes': 'Complies with IS 2062 Charpy V-notch mandatory impact energy of >= 27 J at -20 deg C.'
    }
}


# ==============================================================================
# 2. CORE IMPACT CALCULATIONS
# ==============================================================================

def calculate_potential_energy(mass_kg: float, radius_m: float, angle_deg: float, g: float = 9.80665) -> float:
    """
    Calculates initial potential energy of the pendulum before release:
    E0 = m * g * h0 = m * g * R * (1 - cos(beta))
    """
    if mass_kg <= 0 or radius_m <= 0:
        raise ValueError("Pendulum mass and effective arm length must be positive.")
    rad = math.radians(angle_deg)
    return mass_kg * g * radius_m * (1.0 - math.cos(rad))


def calculate_absorbed_energy(initial_energy_j: float,
                              residual_energy_j: float,
                              friction_loss_j: float = 0.0) -> float:
    """
    Calculates net energy absorbed by specimen:
    KV = E0 - E1 - L_f
    """
    if initial_energy_j < 0:
        raise ValueError("Initial pendulum energy cannot be negative.")
    if residual_energy_j < 0:
        residual_energy_j = 0.0
    if friction_loss_j < 0:
        friction_loss_j = 0.0

    absorbed = initial_energy_j - residual_energy_j - friction_loss_j
    return max(0.0, round(absorbed, 2))


def calculate_impact_toughness(absorbed_energy_j: float,
                               net_area_cm2: float = 0.80) -> Dict[str, float]:
    """
    Calculates notch impact strength / toughness ak:
    ak (J/cm^2) = KV / A0_net
    ak (kJ/m^2) = (KV / A0_net_mm2) * 1000 = ak (J/cm^2) * 10
    """
    if net_area_cm2 <= 0:
        raise ValueError("Specimen net cross-sectional area must be positive.")

    ak_j_cm2 = absorbed_energy_j / net_area_cm2
    ak_kj_m2 = ak_j_cm2 * 10.0  # 1 J/cm^2 = 10 kJ/m^2

    return {
        'ak_j_cm2': round(ak_j_cm2, 2),
        'ak_kj_m2': round(ak_kj_m2, 2)
    }


def estimate_shear_fracture_pct(absorbed_energy_j: float,
                                lower_shelf_j: float,
                                upper_shelf_j: float) -> float:
    """
    Estimates the percentage of ductile fibrous shear fracture on the fracture surface
    based on the energy position between lower and upper shelves:
    % Shear = ((KV - Lower) / (Upper - Lower)) * 100
    Clamped to [0.0, 100.0].
    """
    if upper_shelf_j <= lower_shelf_j:
        return 0.0
    pct = ((absorbed_energy_j - lower_shelf_j) / (upper_shelf_j - lower_shelf_j)) * 100.0
    return max(0.0, min(100.0, round(pct, 1)))


def calculate_dbtt_model_energy(temperature_c: float,
                                lower_shelf_j: float,
                                upper_shelf_j: float,
                                dbtt_c: float,
                                slope_c: float) -> float:
    """
    Standard hyperbolic tangent (tanh) formulation for Charpy impact DBTT transition curve:
    KV(T) = A + B * tanh((T - DBTT) / C)
    where:
      A = (Upper + Lower) / 2
      B = (Upper - Lower) / 2
      C = Transition temperature range parameter (slope)
    """
    a = (upper_shelf_j + lower_shelf_j) / 2.0
    b = (upper_shelf_j - lower_shelf_j) / 2.0
    c = max(1.0, slope_c)
    val = a + b * math.tanh((temperature_c - dbtt_c) / c)
    return max(lower_shelf_j, min(upper_shelf_j, val))


# ==============================================================================
# 3. COMPLETE IMPACT LABORATORY ANALYSIS
# ==============================================================================

def analyze_impact_readings(readings: List[Dict[str, Any]],
                            specimen_type: str = 'charpy_v',
                            material_name: Optional[str] = None,
                            test_temperature_c: float = 23.0,
                            initial_energy_capacity_j: float = 300.0,
                            friction_loss_j: float = 0.5) -> Dict[str, Any]:
    """
    Analyzes multiple trial readings from an impact testing session.

    Parameters:
    - readings: List of dicts, each with either 'absorbed_energy_j' OR 'residual_energy_j'
    - specimen_type: 'charpy_v', 'charpy_u', or 'izod_v'
    - material_name: Optional material label
    - test_temperature_c: Test temperature in Celsius (room temp 23 C)
    - initial_energy_capacity_j: Machine capacity (300 J Charpy, 168 J Izod)
    - friction_loss_j: Tare friction & windage loss calibration

    Returns:
    Dict containing:
    - processed_readings: List of detailed results for each trial
    - summary: Mean KV, standard deviation, impact toughness, fracture mode
    - formulas: Scientific formula expressions and substitutions
    - conclusion: Engineering evaluation against standards
    """
    if not readings or len(readings) == 0:
        raise ValueError("At least 1 valid reading is required to analyze impact test data.")

    spec = IMPACT_SPECIMEN_STANDARDS.get(specimen_type, IMPACT_SPECIMEN_STANDARDS['charpy_v'])
    net_area_cm2 = spec['net_cross_section_cm2']
    net_area_mm2 = spec['net_cross_section_mm2']

    processed = []
    absorbed_energies = []
    lateral_expansions = []

    for idx, r in enumerate(readings, start=1):
        if 'absorbed_energy_j' in r and r['absorbed_energy_j'] is not None:
            kv = float(r['absorbed_energy_j'])
            e_res = max(0.0, initial_energy_capacity_j - kv - friction_loss_j)
        elif 'residual_energy_j' in r and r['residual_energy_j'] is not None:
            e_res = float(r['residual_energy_j'])
            kv = calculate_absorbed_energy(initial_energy_capacity_j, e_res, friction_loss_j)
        else:
            continue

        lat_exp = float(r.get('lateral_expansion_mm', 0.0) or 0.0)
        pct_shear = float(r.get('pct_shear_fracture', 0.0) or 0.0)

        # Toughness calculations
        toughness = calculate_impact_toughness(kv, net_area_cm2)

        processed.append({
            'trial_number': idx,
            'initial_energy_j': initial_energy_capacity_j,
            'residual_energy_j': round(e_res, 2),
            'friction_loss_j': friction_loss_j,
            'absorbed_energy_j': round(kv, 2),
            'ak_j_cm2': toughness['ak_j_cm2'],
            'ak_kj_m2': toughness['ak_kj_m2'],
            'lateral_expansion_mm': round(lat_exp, 2),
            'pct_shear_fracture': round(pct_shear, 1)
        })
        absorbed_energies.append(kv)
        if lat_exp > 0:
            lateral_expansions.append(lat_exp)

    if not processed:
        raise ValueError("No valid impact readings found in submission.")

    n = len(absorbed_energies)
    mean_kv = sum(absorbed_energies) / n
    variance = sum((x - mean_kv) ** 2 for x in absorbed_energies) / n if n > 1 else 0.0
    std_dev = math.sqrt(variance)

    mean_ak = calculate_impact_toughness(mean_kv, net_area_cm2)
    mean_lat_exp = (sum(lateral_expansions) / len(lateral_expansions)) if lateral_expansions else 0.0

    # Classify fracture appearance based on absorbed energy and material type
    if mean_kv >= 100.0:
        fracture_type = "Ductile Fibrous (Dull Matte Grey)"
        fracture_class = "High Toughness / Plastic Deformation"
    elif mean_kv >= 35.0:
        fracture_type = "Mixed Mode (Fibrous Rim + Crystalline Cleavage Center)"
        fracture_class = "Moderate Toughness / Transitional"
    else:
        fracture_type = "Brittle Cleavage (Bright Faceted Crystalline)"
        fracture_class = "Low Toughness / Cleavage Fracture"

    # Engineering conclusion
    conclusion = generate_impact_conclusion(
        material_name=material_name or "Test Specimen",
        specimen_type=spec['name'],
        temperature_c=test_temperature_c,
        mean_kv=mean_kv,
        std_dev=std_dev,
        ak_j_cm2=mean_ak['ak_j_cm2'],
        fracture_type=fracture_type
    )

    formulas = {
        'absorbed_energy': {
            'latex': r'K_V = E_0 - E_1 - L_f',
            'plain': f'KV = {initial_energy_capacity_j:.1f} - E_res - {friction_loss_j:.1f} = {mean_kv:.2f} J',
            'meaning': 'Absorbed Energy = Initial Potential Energy - Residual Swing Energy - Friction Loss'
        },
        'notch_toughness': {
            'latex': r'a_k = \frac{K_V}{A_0}',
            'plain': f'a_k = {mean_kv:.2f} J / {net_area_cm2:.2f} cm² = {mean_ak["ak_j_cm2"]:.2f} J/cm² ({mean_ak["ak_kj_m2"]:.1f} kJ/m²)',
            'meaning': 'Impact Toughness = Absorbed Energy divided by Net Cross-Sectional Area below Notch'
        },
        'net_area': {
            'latex': r'A_0 = W \times (W - a)',
            'plain': f'A0 = {spec["width_mm"]} mm × ({spec["height_mm"]} mm - {spec["notch_depth_mm"]} mm) = {net_area_mm2:.1f} mm² ({net_area_cm2:.2f} cm²)',
            'meaning': 'Net cross-sectional area of unnotched ligament'
        }
    }

    return {
        'specimen': spec,
        'processed_readings': processed,
        'summary': {
            'num_trials': n,
            'mean_absorbed_energy_j': round(mean_kv, 2),
            'std_dev_j': round(std_dev, 2),
            'min_energy_j': round(min(absorbed_energies), 2),
            'max_energy_j': round(max(absorbed_energies), 2),
            'mean_ak_j_cm2': mean_ak['ak_j_cm2'],
            'mean_ak_kj_m2': mean_ak['ak_kj_m2'],
            'mean_lateral_expansion_mm': round(mean_lat_exp, 2),
            'temperature_celsius': test_temperature_c,
            'fracture_type': fracture_type,
            'fracture_class': fracture_class
        },
        'formulas': formulas,
        'conclusion': conclusion
    }


def generate_impact_conclusion(material_name: str,
                               specimen_type: str,
                               temperature_c: float,
                               mean_kv: float,
                               std_dev: float,
                               ak_j_cm2: float,
                               fracture_type: str) -> str:
    """Generates an algorithmic objective metallurgical conclusion."""
    c = f"The {material_name} specimen was subjected to {specimen_type} testing at {temperature_c:.1f}°C. "
    c += f"The arithmetic mean energy absorbed was {mean_kv:.2f} J (±{std_dev:.2f} J), yielding a notch impact toughness of ak = {ak_j_cm2:.2f} J/cm² ({ak_j_cm2*10:.1f} kJ/m²). "

    if mean_kv >= 100.0:
        c += f"The high impact energy absorption and {fracture_type} indicate extensive plastic deformation and high crack-propagation resistance prior to shear separation, satisfying ASTM E23 structural criteria for dynamic shock loading."
    elif mean_kv >= 35.0:
        c += f"The specimen demonstrated intermediate energy absorption with a {fracture_type} appearance, indicating that the test temperature ({temperature_c:.1f}°C) lies within or near the transition regime."
    else:
        c += f"The low energy absorption and {fracture_type} reveal minimal plastic energy dissipation prior to rapid catastrophic crack propagation. This material should not be utilized in critical cold-climate or high-rate shock applications without suitable heat treatment."

    return c


# ==============================================================================
# 4. SIMULATION DATA & DBTT GENERATION
# ==============================================================================

def generate_impact_simulation_data(material_slug: str = 'mild-steel',
                                    specimen_type: str = 'charpy_v',
                                    temperature_c: float = 23.0,
                                    num_trials: int = 3,
                                    machine_capacity_j: float = 300.0) -> Dict[str, Any]:
    """
    Generates realistic, physically grounded Charpy / Izod impact data for educational simulation.
    Includes physics variation across multi-trial repetitions and DBTT temperature sweep data.
    """
    preset = IMPACT_MATERIAL_PRESETS.get(material_slug, IMPACT_MATERIAL_PRESETS['mild-steel'])
    spec = IMPACT_SPECIMEN_STANDARDS.get(specimen_type, IMPACT_SPECIMEN_STANDARDS['charpy_v'])

    # Determine baseline energy at requested temperature
    if preset.get('has_dbtt', False):
        base_kv = calculate_dbtt_model_energy(
            temperature_c=temperature_c,
            lower_shelf_j=preset['lower_shelf_energy_j'],
            upper_shelf_j=preset['upper_shelf_energy_j'],
            dbtt_c=preset['dbtt_celsius'],
            slope_c=preset['transition_slope_c']
        )
    else:
        # FCC or Cast Iron (essentially flat across temperatures)
        base_kv = preset['nominal_room_temp_energy_j']
        # slight thermal softening at higher temps
        if temperature_c < -50:
            base_kv = max(preset['lower_shelf_energy_j'], base_kv * 0.92)

    friction_tare = 0.5  # standard windage and friction loss in J

    # Generate multi-trial repetitions with realistic Gaussian scatter (±4%)
    readings = []
    for i in range(1, num_trials + 1):
        scatter = random.gauss(1.0, 0.035)
        trial_kv = max(1.5, min(machine_capacity_j - 5.0, round(base_kv * scatter, 2)))
        e_res = round(max(0.0, machine_capacity_j - trial_kv - friction_tare), 2)

        # Estimate percent shear fracture
        if preset.get('has_dbtt', False):
            pct_shear = estimate_shear_fracture_pct(
                trial_kv, preset['lower_shelf_energy_j'], preset['upper_shelf_energy_j']
            )
        else:
            pct_shear = preset.get('room_temp_pct_shear', 100.0)

        # Estimate lateral expansion (ASTM E23 Annex A6)
        lat_exp = round(max(0.02, min(2.5, trial_kv * 0.011 * random.uniform(0.95, 1.05))), 2)

        readings.append({
            'trial_number': i,
            'temperature_celsius': temperature_c,
            'initial_energy_j': machine_capacity_j,
            'residual_energy_j': e_res,
            'friction_loss_j': friction_tare,
            'absorbed_energy_j': trial_kv,
            'lateral_expansion_mm': lat_exp,
            'pct_shear_fracture': pct_shear
        })

    # Generate full temperature transition curve points (-100°C to +120°C) for interactive charting
    temp_sweep = []
    temps = [-100, -80, -60, -40, -20, -10, 0, 10, 20, 23, 40, 60, 80, 100, 120]
    for t in temps:
        if preset.get('has_dbtt', False):
            e_t = calculate_dbtt_model_energy(
                t, preset['lower_shelf_energy_j'], preset['upper_shelf_energy_j'],
                preset['dbtt_celsius'], preset['transition_slope_c']
            )
            sh_t = estimate_shear_fracture_pct(e_t, preset['lower_shelf_energy_j'], preset['upper_shelf_energy_j'])
        else:
            e_t = preset['nominal_room_temp_energy_j']
            sh_t = preset.get('room_temp_pct_shear', 100.0)

        temp_sweep.append({
            'temperature_c': t,
            'energy_j': round(e_t, 2),
            'pct_shear': round(sh_t, 1)
        })

    # Run analysis
    analysis = analyze_impact_readings(
        readings=readings,
        specimen_type=specimen_type,
        material_name=preset['name'],
        test_temperature_c=temperature_c,
        initial_energy_capacity_j=machine_capacity_j,
        friction_loss_j=friction_tare
    )

    return {
        'material_slug': material_slug,
        'material_name': preset['name'],
        'crystal_structure': preset['structure'],
        'has_dbtt': preset.get('has_dbtt', False),
        'dbtt_celsius': preset.get('dbtt_celsius', None),
        'specimen': spec,
        'test_temperature_c': temperature_c,
        'readings': readings,
        'summary': analysis['summary'],
        'formulas': analysis['formulas'],
        'conclusion': analysis['conclusion'],
        'temperature_sweep': temp_sweep,
        'notes': preset.get('notes', '')
    }
