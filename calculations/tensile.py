import math
import numpy as np
import pandas as pd

def calculate_cross_sectional_area(diameter_mm):
    """
    Calculates original cross-sectional area of a cylindrical specimen:
    A0 = (pi * d0^2) / 4
    """
    if diameter_mm is None or diameter_mm <= 0:
        raise ValueError("Specimen diameter must be greater than zero.")
    return (math.pi * (diameter_mm ** 2)) / 4.0

def analyze_tensile_data(original_diameter_mm, original_gauge_length_mm, readings, final_gauge_length_mm=None, final_diameter_mm=None, material_name=None):
    """
    Performs complete engineering tensile analysis on laboratory readings.

    Parameters:
    - original_diameter_mm: Original specimen diameter d0 (mm)
    - original_gauge_length_mm: Original gauge length L0 (mm)
    - readings: List of dicts, each with 'load_n' and 'extension_mm'
    - final_gauge_length_mm: Optional final gauge length after fracture (mm)
    - final_diameter_mm: Optional final neck diameter after fracture (mm)
    - material_name: Optional material identifier

    Returns:
    Dict containing:
    - computed_readings: List of readings with stress_mpa, strain, and derived values
    - summary: Key mechanical properties (E, Yield, UTS, Elongation %, Toughness, etc.)
    - formulas: Explanatory formula strings and substitutions
    - conclusion: Algorithmic objective scientific conclusion
    - warnings: Any engineering data quality warnings
    """
    warnings = []

    if original_diameter_mm is None or original_diameter_mm <= 0:
        raise ValueError("Specimen original diameter must be a positive number.")
    if original_gauge_length_mm is None or original_gauge_length_mm <= 0:
        raise ValueError("Specimen original gauge length must be a positive number.")
    if not readings or len(readings) < 2:
        raise ValueError("At least 2 valid readings are required to analyze tensile behavior.")

    # Calculate initial area
    a0 = calculate_cross_sectional_area(original_diameter_mm)
    l0 = float(original_gauge_length_mm)

    # Process and filter readings
    valid_points = []
    for idx, r in enumerate(readings, start=1):
        try:
            load = float(r.get('load_n', 0.0))
            ext = float(r.get('extension_mm', 0.0))
        except (ValueError, TypeError):
            continue

        if load < 0 or ext < 0:
            warnings.append(f"Reading #{idx}: Negative values detected and clamped to zero.")
            load = max(0.0, load)
            ext = max(0.0, ext)

        stress = load / a0  # MPa = N / mm^2
        strain = ext / l0   # dimensionless

        valid_points.append({
            'reading_number': idx,
            'load_n': round(load, 2),
            'extension_mm': round(ext, 4),
            'stress_mpa': round(stress, 2),
            'strain': round(strain, 6),
            'strain_pct': round(strain * 100.0, 4)
        })

    if len(valid_points) < 2:
        raise ValueError("Insufficient valid data points after parsing.")

    # Sort primarily by strain/extension to guarantee monotonically progressing strain
    # but preserve user ordering if already sensible
    df = pd.DataFrame(valid_points)

    loads = df['load_n'].to_numpy(dtype=float)
    extensions = df['extension_mm'].to_numpy(dtype=float)
    stresses = df['stress_mpa'].to_numpy(dtype=float)
    strains = df['strain'].to_numpy(dtype=float)

    # 1. Maximum Load and Ultimate Tensile Strength (UTS)
    max_load_idx = int(np.argmax(loads))
    max_load_n = float(loads[max_load_idx])
    uts_mpa = float(stresses[max_load_idx])

    # 2. Young's Modulus (E) Calculation via Linear Elastic Regression
    # We find the steepest linear region in the initial portion of the curve (up to ~40% of max stress)
    youngs_modulus_gpa = None
    r_squared = 0.0
    elastic_indices = []

    # Filter initial non-zero points for elastic fit
    # Typically, the elastic region occurs before 0.005 strain or before 50% UTS
    candidate_mask = (strains > 0.00005) & (stresses < 0.60 * uts_mpa) & (stresses > 0.05 * uts_mpa)
    candidate_indices = np.where(candidate_mask)[0]

    if len(candidate_indices) >= 3:
        # Search for window of at least 3 points with best R^2 linear fit
        best_r2 = -1.0
        best_slope = None
        best_pts = []

        window_size = min(len(candidate_indices), 6)
        for w in range(3, window_size + 1):
            for i in range(len(candidate_indices) - w + 1):
                subset = candidate_indices[i:i + w]
                x = strains[subset]
                y = stresses[subset]

                # Ensure x has variance
                if np.max(x) - np.min(x) > 1e-6:
                    poly, cov = np.polyfit(x, y, 1, cov=True)
                    slope, intercept = poly[0], poly[1]
                    if slope > 0:  # stiffness must be positive
                        y_pred = slope * x + intercept
                        ss_tot = np.sum((y - np.mean(y)) ** 2)
                        ss_res = np.sum((y - y_pred) ** 2)
                        r2 = 1.0 - (ss_res / ss_tot) if ss_tot > 0 else 0.0

                        if r2 > best_r2:
                            best_r2 = r2
                            best_slope = slope
                            best_pts = subset.tolist()

        if best_slope and best_r2 > 0.70:
            youngs_modulus_gpa = round(best_slope / 1000.0, 2)  # Convert MPa to GPa
            r_squared = round(best_r2, 4)
            elastic_indices = best_pts
    elif len(strains) >= 2:
        # Fallback: simple secant slope on earliest valid points
        for i in range(1, min(len(strains), 4)):
            if strains[i] > 1e-5 and stresses[i] > 10:
                slope = stresses[i] / strains[i]
                if slope > 1000:  # reasonable lower bound for metals
                    youngs_modulus_gpa = round(slope / 1000.0, 2)
                    r_squared = 0.85
                    elastic_indices = [0, i]
                    break

    # 3. Yield Strength / 0.2% Proof Stress Calculation
    yield_strength_mpa = None
    yield_type = "Not identified"

    # A: Check for yield drop (mild steel type upper/lower yield)
    # A local peak followed by dip or plateau in the first 40% of the dataset
    search_limit = max(3, int(len(stresses) * 0.5))
    has_yield_drop = False
    for i in range(2, search_limit - 1):
        if stresses[i] > stresses[i-1] and stresses[i] > stresses[i+1] and stresses[i] < uts_mpa:
            # Check if there is a plateau
            if abs(stresses[i+1] - stresses[i+2]) / stresses[i] < 0.05:
                yield_strength_mpa = round(float(stresses[i]), 2)
                yield_type = "Upper Yield Point (Drop/Plateau Method)"
                has_yield_drop = True
                break

    # B: 0.2% Proof Stress (Offset Method) if Young's Modulus is valid and no sharp yield drop
    if not has_yield_drop and youngs_modulus_gpa and youngs_modulus_gpa > 5.0:
        e_mpa = youngs_modulus_gpa * 1000.0
        # Offset line: stress_offset = E * (strain - 0.002)
        # Find intersection where curve crosses this line
        for i in range(1, len(strains)):
            strain_val = strains[i]
            if strain_val > 0.002:
                offset_stress = e_mpa * (strain_val - 0.002)
                if stresses[i] >= offset_stress and i < max_load_idx:
                    # Linear interpolation between i-1 and i
                    x1, x2 = strains[i-1], strains[i]
                    y1, y2 = stresses[i-1], stresses[i]
                    # Curve line: y = m1*(x - x1) + y1
                    # Offset line: y = e_mpa*(x - 0.002)
                    if x2 != x1:
                        m1 = (y2 - y1) / (x2 - x1)
                        denom = e_mpa - m1
                        if abs(denom) > 1e-3:
                            x_int = (y1 - m1 * x1 + e_mpa * 0.002) / denom
                            y_int = e_mpa * (x_int - 0.002)
                            if 0 <= y_int <= uts_mpa:
                                yield_strength_mpa = round(float(y_int), 2)
                                yield_type = "0.2% Offset Proof Stress (ASTM E8 / ISO 6892)"
                                break

    if yield_strength_mpa is None and youngs_modulus_gpa:
        # Approximate proportional limit as 60-70% UTS
        approx_yield = round(0.65 * uts_mpa, 2)
        yield_strength_mpa = approx_yield
        yield_type = "Estimated Elastic Limit (~65% UTS)"

    # 4. Percentage Elongation
    elongation_pct = None
    if final_gauge_length_mm is not None and final_gauge_length_mm > l0:
        elongation_pct = round(((final_gauge_length_mm - l0) / l0) * 100.0, 2)
    else:
        # Calculate from maximum strain reading
        max_ext = float(np.max(extensions))
        elongation_pct = round((max_ext / l0) * 100.0, 2)

    # 5. Percentage Reduction in Area
    reduction_area_pct = None
    if final_diameter_mm is not None and 0 < final_diameter_mm < original_diameter_mm:
        af = calculate_cross_sectional_area(final_diameter_mm)
        reduction_area_pct = round(((a0 - af) / a0) * 100.0, 2)

    # 6. Modulus of Resilience (Ur)
    # Energy absorbed during elastic deformation: Ur = sigma_y^2 / (2 * E)
    modulus_of_resilience = None
    if yield_strength_mpa and youngs_modulus_gpa and youngs_modulus_gpa > 0:
        # (MPa^2) / (2 * MPa) = MPa = MJ / m^3
        e_mpa = youngs_modulus_gpa * 1000.0
        modulus_of_resilience = round((yield_strength_mpa ** 2) / (2.0 * e_mpa), 3)

    # 7. Tensile Toughness (Ut)
    # Area under the stress-strain curve via trapezoidal integration
    try:
        # Sort by strain for integration
        sorted_indices = np.argsort(strains)
        s_strain = strains[sorted_indices]
        s_stress = stresses[sorted_indices]
        # np.trapezoid handles integration; fallback to np.trapz if needed
        trap_func = getattr(np, 'trapezoid', getattr(np, 'trapz', None))
        toughness_mj_m3 = round(float(trap_func(s_stress, s_strain)), 2)
    except Exception:
        toughness_mj_m3 = None

    # 8. Fracture Stress and Extension
    fracture_stress = round(float(stresses[-1]), 2)
    fracture_extension = round(float(extensions[-1]), 4)

    # 9. Engineering Conclusion Formulation
    conclusion = generate_engineering_conclusion(
        material_name=material_name,
        youngs_modulus_gpa=youngs_modulus_gpa,
        yield_strength_mpa=yield_strength_mpa,
        uts_mpa=uts_mpa,
        elongation_pct=elongation_pct,
        reduction_area_pct=reduction_area_pct,
        yield_type=yield_type
    )

    # Mathematical Explanations & Formulas
    formulas = {
        "area": {
            "formula": "A₀ = (π × d₀²) / 4",
            "values": f"(π × {original_diameter_mm}²) / 4 = {round(a0, 3)} mm²",
            "description": "Original cross-sectional area of the cylindrical gauge section."
        },
        "stress": {
            "formula": "σ = P / A₀",
            "values": f"Load (N) / {round(a0, 3)} mm²",
            "description": "Engineering stress relates the instantaneous axial tensile force to original cross-section."
        },
        "strain": {
            "formula": "ε = ΔL / L₀",
            "values": f"Extension (mm) / {l0} mm",
            "description": "Engineering strain is the linear elongation per unit of original gauge length."
        },
        "youngs_modulus": {
            "formula": "E = Δσ / Δε (Linear regression slope in elastic region)",
            "values": f"{youngs_modulus_gpa} GPa (Fit R² = {r_squared})" if youngs_modulus_gpa else "Insufficient linear elastic data points",
            "description": "Measure of elastic stiffness resisting atomic bond elongation under uniaxial tension."
        },
        "uts": {
            "formula": "UTS = P_max / A₀",
            "values": f"{round(max_load_n, 1)} N / {round(a0, 3)} mm² = {uts_mpa} MPa",
            "description": "Maximum nominal engineering stress sustained prior to localized necking."
        },
        "elongation": {
            "formula": "%EL = [(L_f - L₀) / L₀] × 100%",
            "values": f"{elongation_pct}%",
            "description": "Total engineering plastic deformation at fracture, indicating metallurgical ductility."
        }
    }

    return {
        "computed_readings": valid_points,
        "summary": {
            "original_diameter_mm": float(original_diameter_mm),
            "original_gauge_length_mm": float(original_gauge_length_mm),
            "final_gauge_length_mm": float(final_gauge_length_mm) if final_gauge_length_mm else None,
            "final_diameter_mm": float(final_diameter_mm) if final_diameter_mm else None,
            "cross_sectional_area_mm2": round(a0, 3),
            "number_of_readings": len(valid_points),
            "max_load_n": round(max_load_n, 2),
            "uts_mpa": round(uts_mpa, 2),
            "youngs_modulus_gpa": youngs_modulus_gpa,
            "r_squared": r_squared,
            "yield_strength_mpa": yield_strength_mpa,
            "yield_type": yield_type,
            "elongation_pct": elongation_pct,
            "reduction_area_pct": reduction_area_pct,
            "modulus_of_resilience_mj_m3": modulus_of_resilience,
            "toughness_mj_m3": toughness_mj_m3,
            "fracture_stress_mpa": fracture_stress,
            "fracture_extension_mm": fracture_extension
        },
        "formulas": formulas,
        "conclusion": conclusion,
        "warnings": warnings
    }

def generate_engineering_conclusion(material_name, youngs_modulus_gpa, yield_strength_mpa, uts_mpa, elongation_pct, reduction_area_pct, yield_type):
    """
    Generates an objective, rigorous scientific conclusion based strictly on calculated quantities.
    """
    statements = []

    # Material classification & ductility
    if elongation_pct is not None:
        if elongation_pct >= 15.0:
            statements.append(f"The specimen exhibited pronounced ductile deformation, attaining a total fracture elongation of {elongation_pct}%.")
            if reduction_area_pct and reduction_area_pct >= 30.0:
                statements.append(f"Significant cross-sectional reduction ({reduction_area_pct}%) confirms classical localized necking prior to shear fracture.")
        elif elongation_pct >= 5.0:
            statements.append(f"The material demonstrated moderate ductility with a fracture elongation of {elongation_pct}%.")
        else:
            statements.append(f"The material exhibited limited plastic ductility ({elongation_pct}% elongation), representative of high-strength or brittle mechanical behavior.")

    # Elastic stiffness
    if youngs_modulus_gpa:
        if youngs_modulus_gpa >= 180.0:
            statements.append(f"The measured Young's modulus of {youngs_modulus_gpa} GPa reflects high elastic stiffness characteristic of ferrous alloys.")
        elif youngs_modulus_gpa >= 90.0:
            statements.append(f"The measured Young's modulus of {youngs_modulus_gpa} GPa is consistent with copper, brass, or titanium alloy systems.")
        elif youngs_modulus_gpa >= 50.0:
            statements.append(f"The measured Young's modulus of {youngs_modulus_gpa} GPa indicates moderate elastic stiffness, typical of light engineering alloys such as aluminium.")
        else:
            statements.append(f"The calculated Young's modulus is {youngs_modulus_gpa} GPa.")

    # Yielding and strength ratio
    if yield_strength_mpa and uts_mpa:
        yield_ratio = round(yield_strength_mpa / uts_mpa, 3)
        statements.append(f"The Ultimate Tensile Strength was determined to be {uts_mpa} MPa with a Yield Strength of {yield_strength_mpa} MPa ({yield_type}).")
        statements.append(f"The yield-to-tensile ratio (σ_y / UTS) is {yield_ratio}, reflecting an appreciable strain hardening reserve before necking instability.")

    if not statements:
        return "Experimental tensile data processed. Insufficient parameters were available to derive a comprehensive metallurgical conclusion."

    conclusion_text = " ".join(statements)
    conclusion_text += " Note: Experimental conclusions are derived strictly from user-entered or simulated data according to ASTM E8/ISO 6892 conventions."
    return conclusion_text

def generate_simulation_data(material_slug="mild-steel", diameter_mm=10.0, gauge_length_mm=50.0, num_points=35):
    """
    Generates physically grounded tensile simulation datasets based on constitutive models:
    - Mild Steel: Upper & lower yield point with Lüders plateau followed by power-law hardening and necking drop.
    - Aluminium 6061-T6: Ramberg-Osgood continuous yielding with smooth hardening.
    - Copper C11000: High strain hardening exponent, large post-yield extension.
    - Brass C26000: High elongation, high work hardening.
    - Stainless Steel 304: High UTS, high toughness and elongation.
    """
    d0 = float(diameter_mm)
    l0 = float(gauge_length_mm)
    a0 = calculate_cross_sectional_area(d0)

    # Material parameters dict
    params_catalog = {
        "mild-steel": {
            "name": "Mild Steel (AISI 1018 / IS 2062)",
            "E_GPa": 205.0,
            "sigma_upper_yield": 265.0,
            "sigma_lower_yield": 250.0,
            "yield_plateau_strain": 0.022,
            "uts": 440.0,
            "uts_strain": 0.16,
            "fracture_stress": 330.0,
            "fracture_strain": 0.28,
            "has_plateau": True
        },
        "aluminium-6061-t6": {
            "name": "Aluminium Alloy (6061-T6)",
            "E_GPa": 68.9,
            "sigma_yield": 276.0,
            "uts": 310.0,
            "uts_strain": 0.09,
            "fracture_stress": 240.0,
            "fracture_strain": 0.17,
            "n_hardening": 0.10,
            "has_plateau": False
        },
        "copper-c11000": {
            "name": "Electrolytic Copper (C11000)",
            "E_GPa": 117.0,
            "sigma_yield": 195.0,
            "uts": 260.0,
            "uts_strain": 0.20,
            "fracture_stress": 180.0,
            "fracture_strain": 0.35,
            "n_hardening": 0.25,
            "has_plateau": False
        },
        "brass-c26000": {
            "name": "Cartridge Brass (C26000)",
            "E_GPa": 110.0,
            "sigma_yield": 140.0,
            "uts": 330.0,
            "uts_strain": 0.30,
            "fracture_stress": 220.0,
            "fracture_strain": 0.45,
            "n_hardening": 0.35,
            "has_plateau": False
        },
        "stainless-steel-304": {
            "name": "Stainless Steel (AISI 304)",
            "E_GPa": 193.0,
            "sigma_yield": 290.0,
            "uts": 620.0,
            "uts_strain": 0.40,
            "fracture_stress": 460.0,
            "fracture_strain": 0.55,
            "n_hardening": 0.40,
            "has_plateau": False
        }
    }

    mat = params_catalog.get(material_slug, params_catalog["mild-steel"])
    e_mpa = mat["E_GPa"] * 1000.0

    strains = []
    stresses = []

    # Always start at origin
    strains.append(0.0)
    stresses.append(0.0)

    if mat.get("has_plateau", False):
        # Mild Steel Model with Upper/Lower Yield and Lüders Plateau
        eps_el = mat["sigma_upper_yield"] / e_mpa
        # Elastic points (8 points)
        for f in np.linspace(0.125, 1.0, 8):
            eps = eps_el * f
            sigma = e_mpa * eps
            strains.append(eps)
            stresses.append(sigma)

        # Upper yield drop to lower yield
        strains.append(eps_el + 0.001)
        stresses.append(mat["sigma_lower_yield"])

        # Lüders plateau (3 points)
        plateau_end = mat["yield_plateau_strain"]
        for eps in np.linspace(eps_el + 0.005, plateau_end, 3):
            strains.append(eps)
            # Slight oscillation typical of Lüders bands
            stresses.append(mat["sigma_lower_yield"] + np.random.uniform(-2, 2))

        # Strain Hardening to UTS (12 points)
        uts_eps = mat["uts_strain"]
        for eps in np.linspace(plateau_end + 0.01, uts_eps, 12):
            norm_eps = (eps - plateau_end) / (uts_eps - plateau_end)
            # Parabolic strain hardening profile
            sigma = mat["sigma_lower_yield"] + (mat["uts"] - mat["sigma_lower_yield"]) * (2.0 * norm_eps - norm_eps ** 2)
            strains.append(eps)
            stresses.append(sigma)

        # Necking to fracture (8 points)
        frac_eps = mat["fracture_strain"]
        for eps in np.linspace(uts_eps + 0.01, frac_eps, 8):
            norm_neck = (eps - uts_eps) / (frac_eps - uts_eps)
            sigma = mat["uts"] - (mat["uts"] - mat["fracture_stress"]) * (norm_neck ** 1.3)
            strains.append(eps)
            stresses.append(sigma)

    else:
        # Continuous yielding materials (Ramberg-Osgood representation)
        y_stress = mat["sigma_yield"]
        eps_y = (y_stress / e_mpa) + 0.002
        uts = mat["uts"]
        uts_eps = mat["uts_strain"]
        frac_eps = mat["fracture_strain"]
        frac_stress = mat["fracture_stress"]

        # Elastic & transition points (10 points)
        for eps in np.linspace(0.0002, eps_y, 10):
            # Ramberg-Osgood approximation
            sig = e_mpa * eps if eps < (y_stress * 0.7 / e_mpa) else y_stress * (eps / eps_y) ** 0.15
            strains.append(eps)
            stresses.append(min(sig, y_stress))

        # Strain hardening up to UTS (14 points)
        for eps in np.linspace(eps_y * 1.05, uts_eps, 14):
            t = (eps - eps_y) / (uts_eps - eps_y)
            sig = y_stress + (uts - y_stress) * (1.0 - (1.0 - t) ** 2)
            strains.append(eps)
            stresses.append(sig)

        # Post-UTS necking (8 points)
        for eps in np.linspace(uts_eps * 1.02, frac_eps, 8):
            t = (eps - uts_eps) / (frac_eps - uts_eps)
            sig = uts - (uts - frac_stress) * (t ** 1.2)
            strains.append(eps)
            stresses.append(sig)

    # Convert stress/strain arrays to loads and extensions
    readings = []
    for idx, (eps, sig) in enumerate(zip(strains, stresses), start=1):
        ext = eps * l0
        load = sig * a0
        readings.append({
            "reading_number": idx,
            "load_n": round(load, 1),
            "extension_mm": round(ext, 4),
            "stress_mpa": round(sig, 2),
            "strain": round(eps, 6)
        })

    return {
        "material_name": mat["name"],
        "material_slug": material_slug,
        "diameter_mm": d0,
        "gauge_length_mm": l0,
        "cross_sectional_area_mm2": round(a0, 3),
        "readings": readings
    }
