# MAT-VLAB — Interactive Virtual Materials Testing & Analysis Laboratory

> **"Developed as an educational Materials Science and Technology project."**  
> *Targeted for B.Tech Materials Science, Metallurgical, and Mechanical Engineering students.*

---

## 1. Project Title & Overview
**MAT-VLAB** is a full-featured, image-based, interactive web application built to simulate an authentic materials testing and mechanical characterization laboratory. Rather than functioning as a standard database CRUD portal, MAT-VLAB provides an immersive virtual laboratory experience that bridges the pedagogical gap between fundamental solid mechanics theory and physical workshop practice.

Students can explore testing machine anatomy via interactive vector schematics, run parametric physics-based constitutive simulations, manually input observation data from their physical university laboratories, automatically calculate mechanical properties with step-by-step formula substitutions, visualize responsive engineering stress-strain curves, compare alloys, assess their knowledge via quizzes, and export certified PDF experiment reports.

---

## 2. Problem Statement
Universal Testing Machines (UTM), high-temperature creep apparatuses, and Charpy impact pendulums are capital-intensive, high-maintenance experimental facilities. In academic engineering programs, student access to these machines is frequently constrained by:
1. Limited hands-on machine hours per student.
2. Large batch sizes in college laboratory sections where students passively observe rather than operate equipment.
3. Lack of immediate data reduction and validation tools during post-laboratory report preparation.
4. The high risk of equipment damage or specimen slippage if machine operation principles are not mastered beforehand.

MAT-VLAB overcomes these limitations by functioning as an accessible, browser-based pre-lab preparation and post-lab analysis hub.

---

## 3. Educational Objectives
- **Understand Testing Anatomy**: Inspect sensory transducers (strain gauge load cells), drive systems (twin ball-screw crossheads), and gripping mechanisms (hydraulic wedge jaws).
- **Master ASTM / ISO Standards**: Learn standard proportional specimen geometry and test methods according to **ASTM E8 / E8M** and **ISO 6892-1**.
- **Distinguish Data Origins**: Enforce academic integrity by strictly segregating **SIMULATION DATA**, **USER-ENTERED EXPERIMENTAL DATA**, and **HANDBOOK REFERENCE VALUES**.
- **Automate Engineering Calculations**: Compute Young's Modulus ($E$), 0.2% offset proof stress, Ultimate Tensile Strength (UTS), percentage elongation (%EL), percentage reduction in area (%RA), and tensile toughness ($U_t$) without spreadsheets.
- **Synthesize Scientific Conclusions**: Generate objective metallurgical interpretations based strictly on computed mechanical properties.

---

## 4. Key Features

### 🔬 Dual Experimentation Modes (Tensile Testing)
1. **Mode 1: Virtual Simulation Mode**
   - Parametric constitutive modeling of standard engineering alloys (Mild Steel AISI 1018, Aluminium 6061-T6, Copper C11000, Cartridge Brass C26000, Stainless Steel 304).
   - Interactive crosshead controls: Auto-run test, single-step increment, pause, or direct load slider.
   - Synchronized visual machinery state: Crosshead travels upward, specimen stretches, pinches into localized necking, and separates into classic cup-and-cone shear lips.
   - Real-time digital telemetry: Load ($N$ and $kN$), Extension ($\Delta L$ in $mm$), Stress ($\sigma$ in $MPa$), Strain ($\epsilon$).
   - Progressive Plotly.js stress-strain curve tracing synchronously with machine displacement.
   - Clearly labeled: **"SIMULATION DATA — Generated for Demonstration"**.

2. **Mode 2: Real Laboratory Manual Data Entry**
   - Input physical specimen dimensions: Original diameter ($d_0$), original gauge length ($L_0$), final gauge length ($L_f$), and final neck diameter ($d_f$).
   - Instant calculation of original cross-sectional area: $A_0 = \frac{\pi d_0^2}{4}$.
   - Dynamic observation table with row addition, row deletion, and clear controls.
   - **CSV Import**: Drag-and-drop or file upload for machine logs.
   - **Sample CSV Export & Preload**: Single-click access to standard test datasets.
   - Client and server-side validation preventing negative loads or formatted errors.

### 📐 Interactive Equipment & Specimen Inspection
- **Universal Testing Machine (UTM)**: Interactive high-detail SVG diagram featuring clickable components:
  - Precision Strain-Gauge Load Cell (50 kN Wheatstone bridge transducer)
  - Movable Crosshead (servo-controlled displacement)
  - Upper and Lower Hydraulic Wedge Grips (serrated carbide jaws)
  - ASTM Dogbone Tensile Specimen (gauge length $L_0 = 50\text{ mm}$, $d_0 = 10\text{ mm}$)
  - Clip-on Axial Extensometer (knife-edge strain measurement)
  - Twin Ball-Screw Drive Columns (high-rigidity transmission)
  - Digital Data Acquisition & Control Console (1 kHz closed-loop telemetry)
- **Metallurgical Fracture Mechanics**: 5-stage SVG graphic illustrating elastic deformation, uniform plastic strain hardening, localized necking onset at UTS, internal void coalescence, and final cup-and-cone shear rupture.

### 📊 Scientific Calculations & Visualization
- **Young's Modulus ($E$)**: Automated least-squares linear regression on the proportional elastic region ($R^2 \ge 0.95$).
- **Yield Strength / 0.2% Proof Stress**: Drop/plateau detection for mild steels; 0.2% (0.002 strain) offset slope intersection for continuous-yielding alloys (aluminium, copper, stainless steel).
- **Ultimate Tensile Strength (UTS)**: $\sigma_{UTS} = \max(\sigma) = \frac{P_{max}}{A_0}$.
- **Toughness & Resilience**: Trapezoidal numerical integration of the stress-strain curve area ($\int \sigma \, d\epsilon$).
- **Interactive Plotly Graph**: Pan, zoom, hover tooltips, and high-resolution PNG export.

### 📑 Automated PDF Experiment Report Generator
- Multi-section publication-quality PDF report rendered using ReportLab and headless Matplotlib.
- Institutional header, experiment metadata, and prominent data origin banner.
- Formatted specimen dimension and observation tables.
- High-resolution embedded stress-strain curve.
- Step-by-step mathematical formulas and substitution records.
- Automated metallurgical conclusion and student quiz score.
- Academic disclaimer footer.

### 🗄️ Material Database & Comparison Tool
- Handbook reference properties for structural alloys with ASTM standard citations.
- Multivariate comparison tool with interactive comparative bar charts (Stiffness, Strength, Ductility, Specific Strength).
- Ability to compare saved student laboratory runs against standard handbook benchmarks.

### 🧠 Knowledge Assessment System (Quiz)
- Interactive MCQ testing station covering Hooke's law, UTM load cells, necking mechanics, 0.2% offset conventions, and true vs engineering stress.
- Immediate feedback highlighting correct/incorrect choices with in-depth scientific explanations.
- Automatic percentage scoring and grade classification.

---

## 5. Technology Stack

| Layer | Technologies |
| :--- | :--- |
| **Frontend** | HTML5, CSS3 (Laboratory Dark Theme), JavaScript (ES6+), Bootstrap 5.3, Plotly.js, FontAwesome 6 |
| **Backend** | Python 3.12, Flask 3.1, Jinja2, Werkzeug |
| **Data Processing** | NumPy 2.5, Pandas 3.0 |
| **Graphics & Schematics** | Custom Scalable Vector Graphics (SVG), Matplotlib 3.11 (headless `Agg`) |
| **PDF Generation** | ReportLab 5.0 |
| **Database** | SQLite3 |

---

## 6. System Architecture

```
mat-vlab/
├── app.py                      # Flask routing, view controllers, REST API endpoints
├── config.py                   # App configuration & constraints
├── requirements.txt            # Python dependencies manifest
├── README.md                   # Full documentation manual
├── materials.db                # SQLite database (auto-seeded on first run)
│
├── models/
│   ├── __init__.py
│   └── database.py             # Schema, migrations, CRUD helpers, seeds
│
├── calculations/
│   ├── __init__.py
│   └── tensile.py              # Physics engine, ASTM calculations, simulation models
│
├── reports/
│   ├── __init__.py
│   └── report_generator.py     # ReportLab PDF generator with embedded curves
│
├── data/
│   ├── sample_tensile_data.csv # Authentic mild steel observation dataset
│   └── materials_seed.json     # Reference material properties from ASTM/ISO
│
├── templates/
│   ├── base.html               # Master layout with responsive navbar & footer
│   ├── index.html              # Home landing page with hero & feature cards
│   ├── experiments.html        # Experiment catalog with filter tags
│   ├── tensile.html            # Tensile hub (Objective, Theory, Apparatus, SOP)
│   ├── simulation.html         # Virtual simulation mode (UTM animation & curve)
│   ├── manual_entry.html       # Manual data entry mode (tables & CSV import)
│   ├── results.html            # Results dashboard (cards, Plotly, formulas, PDF)
│   ├── materials.html          # Reference Material Database
│   ├── compare.html            # Material & experiment comparison tool
│   ├── my_experiments.html     # Saved experiments repository
│   ├── quizzes.html            # Interactive MCQ assessment with explanations
│   └── about.html              # Academic context, ASTM citations & disclaimer
│
├── static/
│   ├── css/
│   │   └── style.css           # Scientific laboratory dark theme styling
│   ├── js/
│   │   ├── main.js             # Global utilities, toasts, sample CSV downloader
│   │   ├── apparatus.js        # Interactive UTM component inspector logic
│   │   ├── tensile.js          # Dynamic observation table & CSV parsing
│   │   ├── simulation.js       # Live simulation physics & machine animation
│   │   └── quiz.js             # Quiz scoring & instant feedback
│   └── images/
│       ├── utm_diagram.svg     # Universal Testing Machine vector schematic
│       ├── specimen_diagram.svg# ASTM E8 standard dogbone specimen schematic
│       ├── necking_stages.svg  # 5 progressive stages of tensile fracture
│       └── lab_hero.svg        # Modern laboratory vector artwork
│
└── tests/
    └── test_tensile.py         # Automated unit test suite
```

---

## 7. Installation & Setup

### Prerequisites
- Python 3.10+ (tested on Python 3.12)
- Modern web browser (Chrome, Firefox, Edge, Safari)

### Step 1: Clone or Navigate to the Project
```bash
cd /path/to/mat-vlab
```

### Step 2: Install Dependencies
```bash
pip install -r requirements.txt
```
*(Dependencies: `flask`, `numpy`, `pandas`, `reportlab`, `matplotlib`)*

### Step 3: Run the Flask Application
```bash
python app.py
```
By default, the server will start on `http://127.0.0.1:5000`.

---

## 8. Running the Automated Test Suite

To verify calculation precision, database operations, PDF generation, and all Flask endpoints:
```bash
python -m unittest discover -s tests -p "test_*.py"
```

---

## 9. How the Tensile Test Works (Physics & ASTM Methods)

1. **Original Cross-Sectional Area ($A_0$)**:
   $$\text{For cylindrical specimens: } A_0 = \frac{\pi d_0^2}{4}$$
2. **Engineering Stress ($\sigma$)**:
   $$\sigma = \frac{P}{A_0} \quad [\text{MPa or N/mm}^2]$$
3. **Engineering Strain ($\epsilon$)**:
   $$\epsilon = \frac{\Delta L}{L_0} = \frac{L - L_0}{L_0} \quad [\text{dimensionless or } \%]$$
4. **Young's Modulus ($E$)**:
   $$E = \frac{\Delta \sigma}{\Delta \epsilon} \quad [\text{in GPa}]$$
   *Calculated via linear least-squares regression over the proportional limit elastic range ($R^2 \ge 0.95$).*
5. **0.2% Offset Proof Stress ($\sigma_{0.2\%}$)**:
   For continuous yielding materials (such as aluminium and austenitic stainless steel), an offset line is constructed:
   $$\sigma_{\text{offset}} = E \cdot (\epsilon - 0.002)$$
   The intersection of this line with the experimental stress-strain curve defines the yield strength.
6. **Ultimate Tensile Strength (UTS)**:
   $$\sigma_{UTS} = \frac{P_{\max}}{A_0}$$
7. **Percentage Elongation (%EL)**:
   $$\%EL = \left(\frac{L_f - L_0}{L_0}\right) \times 100\%$$
8. **Percentage Reduction in Area (%RA)**:
   $$\%RA = \left(\frac{A_0 - A_f}{A_0}\right) \times 100\%$$
9. **Tensile Toughness ($U_t$)**:
   $$U_t = \int_0^{\epsilon_f} \sigma \, d\epsilon \quad [\text{MJ/m}^3]$$
   *Integrated numerically using the trapezoidal rule over the full stress-strain curve.*

---

## 10. Future Expansion Roadmap

The architecture of MAT-VLAB is intentionally modular to enable rapid integration of subsequent materials testing modules:
- **Phase 2 Modules**:
  - Uniaxial Compression Test (ASTM E9) with platen friction barreling modeling.
  - Indentation Hardness Testing (Brinell HBW, Rockwell HRC/HRB, Vickers HV).
  - Charpy V-Notch & Izod Dynamic Impact Testing (ASTM E23) with DBTT curve modeling.
- **Phase 3 Modules**:
  - Rotating Bending Fatigue & Wöhler S-N Curve Formulation (ASTM E466).
  - High-Temperature Creep & Stress-Rupture Modeling (ASTM E139).
  - Non-Destructive Testing (Ultrasonic flaw detection, Magnetic Particle Inspection).

---

## 11. Academic Disclaimer

> **Academic Disclaimer:**  
> MAT-VLAB is an educational virtual simulation and data analysis platform developed for instructional purposes in undergraduate Materials Science and Technology programs. It is designed to reinforce conceptual understanding when physical machine access is constrained.  
> **It does not replace certified physical laboratory testing.** Real-world laboratory experience—including hands-on machine calibration, physical specimen preparation, safety interlocks, and physical fracture examination—remains essential to professional engineering accreditation.
