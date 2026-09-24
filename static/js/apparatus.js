/**
 * MAT-VLAB — Interactive UTM Apparatus Inspector
 */

const UTM_COMPONENTS = {
  "part-load-cell": {
    name: "Precision Strain-Gauge Load Cell",
    category: "Sensory & Transduction System",
    role: "Axial Force Measurement Transducer",
    principle: "Consists of an elastic metallic proof body bonded with foil strain gauges in a full Wheatstone bridge configuration. Under applied tensile tension, minuscule elastic strain alters resistance, producing a proportional millivolt electrical signal calibrated directly to force.",
    specs: "Capacity: 50 kN | Accuracy: Class 0.5 (ISO 7500-1) | Non-linearity: ±0.25% Full Scale | Thermal drift compensation: -10°C to +50°C",
    safety: "Never exceed rated load capacity (overload limit: 150%). Tare/Zero the load cell reading prior to gripping the specimen to prevent recording tare grip weight."
  },
  "part-crosshead": {
    name: "Movable Electromechanical Crosshead",
    category: "Drive & Kinematics Subsystem",
    role: "Strain-Rate Controlled Axial Displacement",
    principle: "Driven symmetrically by synchronized twin precision pre-loaded recirculating ball screws connected to a brushless AC servomotor. Moves with micro-step precision to maintain constant crosshead velocity or closed-loop strain rate.",
    specs: "Speed range: 0.001 to 500 mm/min | Maximum travel: 1100 mm | Crosshead rigidity: >200 kN/mm | Position resolution: 0.05 µm",
    safety: "Ensure crosshead travel limits (hardware limit switches) are securely set before starting test to prevent mechanical collision with base or load cell."
  },
  "part-upper-grip": {
    name: "Upper Hydraulic Wedge Grip",
    category: "Specimen Clamping Subsystem",
    role: "Positive Friction Clamping & Axial Alignment",
    principle: "Utilizes self-tightening wedge action where applied tensile force pulls serrated carbide jaws deeper into the tapered grip body, exponentially increasing transverse gripping clamping force to prevent specimen slippage under high loads.",
    specs: "Clamping pressure: 200 bar hydraulic | Jaw types: Serrated V-jaw for round bars (Ø4–Ø20 mm), flat cross-hatched jaws for strip specimens | Grip body: High-tensile forged alloy steel",
    safety: "Inspect jaw serrations for metallic debris or wear. Never grip specimen outside the designated parallel shoulder length to prevent premature grip-induced stress concentrations."
  },
  "part-specimen": {
    name: "Standard Tensile Dogbone Specimen",
    category: "Test Sample Geometry",
    role: "Standardized Subject of Uniaxial Mechanical Evaluation",
    principle: "Engineered with larger shouldered ends for secure gripping and a reduced central gauge section (d₀ = 10 mm, L₀ = 50 mm). The smooth transition fillet (R ≥ 10 mm) prevents stress concentration at the shoulders, ensuring uniform uniaxial tension and failure strictly inside the calibrated gauge length.",
    specs: "Standard: ASTM E8 / ISO 6892-1 Proportional | Gauge length: 50 mm | Gauge diameter: 10 mm (A₀ = 78.54 mm²) | Surface finish: Ra < 0.8 µm",
    safety: "Measure initial gauge diameter at three distinct locations with a precision vernier micrometer and record average value before test."
  },
  "part-extensometer": {
    name: "Clip-on Axial Extensometer",
    category: "High-Precision Strain Instrumentation",
    role: "Direct True Specimen Elongation Measurement",
    principle: "Clips directly onto the specimen gauge marks using hardened knife-edges. Internal flexure elements with strain gauges measure true specimen elongation directly, bypassing machine frame compliance, grip deflection, and load string settling.",
    specs: "Gauge length (L₀): 50 mm | Measuring range: +25 mm / -2.5 mm | Classification: Class 0.5 (ASTM E83 / ISO 9513) | Knife-edge hardness: 62 HRC",
    safety: "Remove extensometer before ultimate fracture if specimen exhibits violent snapping to prevent damaging delicate flexure mechanisms, or use non-contact video extensometer."
  },
  "part-lower-grip": {
    name: "Lower Stationary Grip Assembly",
    category: "Specimen Clamping Subsystem",
    role: "Fixed Reaction Anchor for Uniaxial Tension",
    principle: "Securely anchored to the lower crosshead bed of the UTM frame. Maintains rigid axial collinearity with the upper grip to ensure pure uniaxial tensile loading without bending or twisting moments.",
    specs: "Reaction capacity: 100 kN static | Concentricity tolerance: within 0.05 mm TIR along vertical axis | Hardened alloy tool steel jaws",
    safety: "Check vertical plumb and alignment using an alignment cylinder and dial indicator before commencing high-accuracy testing."
  },
  "part-lead-screws": {
    name: "Twin Ball-Screw Drive Columns",
    category: "Mechanical Transmission Subsystem",
    role: "High-Rigidity Linear Power Transmission",
    principle: "Hardened steel screws featuring recirculating ball bearings between screw threads and nut. Provides extremely high mechanical efficiency (>90%), zero backlash, smooth silent linear motion, and ultra-high frame stiffness under maximum load.",
    specs: "Diameter: 40 mm | Pitch: 5 mm | Dynamic load rating: 80 kN | Surface hardness: 60 HRC induction hardened | Backlash: < 0.005 mm",
    safety: "Keep protective telescopic bellows in place. Inspect regularly for proper synthetic lithium grease lubrication."
  },
  "part-control-panel": {
    name: "Digital Data Acquisition & Control Console",
    category: "Control & Processing Subsystem",
    role: "Real-time Closed-Loop Telemetry & Operator Interface",
    principle: "High-speed DSP (Digital Signal Processor) running closed-loop PID control algorithms at 1 kHz. Digitizes load cell and extensometer signals simultaneously with 24-bit resolution, streaming real-time stress, strain, and force readings to computer interface.",
    specs: "Sampling rate: up to 1000 Hz | A/D resolution: 24-bit | Interface: High-speed Ethernet / USB 3.0 | Emergency Stop: Category 0 fail-safe hardware cutoff",
    safety: "Ensure Emergency Stop (E-STOP) button is unobstructed and operational before every testing session."
  }
};

function selectUtmPart(partId) {
  // Clear previous active styling on SVG
  document.querySelectorAll('.interactive-part').forEach(el => {
    el.classList.remove('active-part');
  });

  const partSvg = document.getElementById(partId);
  if (partSvg) {
    partSvg.classList.add('active-part');
  }

  const info = UTM_COMPONENTS[partId];
  if (!info) return;

  const cardTitle = document.getElementById('inspector-title');
  const cardCat = document.getElementById('inspector-category');
  const cardRole = document.getElementById('inspector-role');
  const cardPrinciple = document.getElementById('inspector-principle');
  const cardSpecs = document.getElementById('inspector-specs');
  const cardSafety = document.getElementById('inspector-safety');

  if (cardTitle) cardTitle.textContent = info.name;
  if (cardCat) cardCat.textContent = info.category;
  if (cardRole) cardRole.textContent = info.role;
  if (cardPrinciple) cardPrinciple.textContent = info.principle;
  if (cardSpecs) cardSpecs.textContent = info.specs;
  if (cardSafety) cardSafety.textContent = info.safety;

  // Sync dropdown selector if present
  const selectDropdown = document.getElementById('utm-component-select');
  if (selectDropdown && selectDropdown.value !== partId) {
    selectDropdown.value = partId;
  }
}

document.addEventListener('DOMContentLoaded', () => {
  // Bind click handlers to all SVG parts
  Object.keys(UTM_COMPONENTS).forEach(partId => {
    const el = document.getElementById(partId);
    if (el) {
      el.addEventListener('click', () => {
        selectUtmPart(partId);
      });
    }
  });

  // Bind dropdown change
  const selectDropdown = document.getElementById('utm-component-select');
  if (selectDropdown) {
    selectDropdown.addEventListener('change', (e) => {
      selectUtmPart(e.target.value);
    });
  }

  // Select load cell by default
  selectUtmPart('part-load-cell');
});
