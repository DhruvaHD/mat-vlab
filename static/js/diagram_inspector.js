/**
 * MAT-VLAB — Universal Interactive Equipment Diagram Inspector
 * Provides touch, mouse, and keyboard interaction for all laboratory equipment diagrams:
 * - Brinell Hardness Tester (ASTM E10)
 * - Rockwell Hardness Tester (ASTM E18)
 * - Universal Testing Machine (UTM ASTM E8)
 */

(function () {
  'use strict';

  // =========================================================================
  // 1. COMPREHENSIVE COMPONENT KNOWLEDGE BASES
  // =========================================================================

  const BRINELL_DATA = {
    'indenter': {
      title: 'Tungsten Carbide Ball Indenter (10 mm)',
      badge: 'INDENTER SYSTEM',
      category: 'Spherical Penetrator',
      specs: 'Sintered Tungsten Carbide (WC), Hardness \u2265 1500 HV10, Diameter D = 10.000 mm \u00b1 0.005 mm.',
      func: 'Pressed perpendicularly into the metallic test surface under high static normal force to produce a permanent spherical cap impression.',
      desc: 'Tungsten carbide balls (designated HBW) replaced older hardened steel balls (HBS) in ASTM E10 / ISO 6506 standards to eliminate indenter flattening on metals up to 650 HBW.',
      tip: 'Never test materials harder than 650 HBW with a Brinell ball; diamond penetrators (Rockwell C / Vickers) must be used instead to prevent ball deformation.'
    },
    'loading-mechanism': {
      title: 'Hydraulic & Deadweight Loading System',
      badge: 'LOAD APPLICATION',
      category: 'Force Generation Subsystem',
      specs: 'Precision hydraulic ram with calibrated lever ratio; test force range: 500 to 3000 kgf (4.903 to 29.42 kN).',
      func: 'Applies smooth, vibration-free normal force to the indenter spindle and maintains it during the prescribed dwell countdown (10 to 15 seconds).',
      desc: 'Automatic hydraulic loading eliminates operator inertia shock that could cause deeper impressions than the nominal static force dictates.',
      tip: 'The standard load-diameter ratio (P/D\u00b2 = 30 for steels, 10 for copper/brass, 5 for aluminum) must be maintained for geometric similarity.'
    },
    'specimen': {
      title: 'Ground Metallic Test Specimen',
      badge: 'TEST SPECIMEN',
      category: 'Material Sample',
      specs: 'Ground flat parallel faces, surface finish Ra \u2264 0.8 \u00b5m, thickness t \u2265 8h (minimum 6 mm for 3000 kgf).',
      func: 'The engineering alloy under evaluation. Receives the indenter penetration under perpendicular reaction support.',
      desc: 'Specimens must have parallel top and bottom faces, completely free of oxide scale, grease, and decarburized layers to ensure true plastic resistance.',
      tip: 'Inspect the specimen underside after testing: if an impression bulge appears on the bottom face, the specimen was too thin and readings are invalid.'
    },
    'anvil': {
      title: 'Precision Hardened Support Anvil',
      badge: 'SPECIMEN SUPPORT',
      category: 'Reaction Platen',
      specs: 'Case-hardened tool steel platen (\u2265 60 HRC), ground flat within 0.005 mm.',
      func: 'Provides rigid perpendicular reaction support directly beneath the specimen during the 3000 kgf indentation cycle.',
      desc: 'Flat platens are used for sheet and plate stock, while interchangeable 90\u00b0 V-groove anvils securely cradle cylindrical bars along their center axis.',
      tip: 'Ensure the anvil seating taper is wiped free of grinding grit and metal chips before testing to eliminate compliance errors.'
    },
    'elevating-screw': {
      title: 'Elevating Lead Screw & Handwheel',
      badge: 'HEIGHT ADJUSTMENT',
      category: 'Kinematics & Staging',
      specs: 'Precision Acme trapezoidal lead screw with heavy cast iron handwheel.',
      func: 'Rotated clockwise by the operator to raise the anvil and lift the specimen into gentle initial seating contact with the ball indenter.',
      desc: 'Enclosed within a heavy structural column with a telescoping shroud to protect screw threads from abrasive shop debris.',
      tip: 'Raise the specimen until light contact is established; do not overtighten manually prior to hydraulic loading.'
    },
    'dial-gauge': {
      title: 'Hydraulic Test Force Dial Gauge',
      badge: 'FORCE MONITOR',
      category: 'Pressure Instrumentation',
      specs: 'Bourdon tube hydraulic gauge calibrated in test force (kgf and kN), accuracy \u00b1 0.5%.',
      func: 'Displays instantaneous hydraulic cylinder pressure and verifies that full test force (e.g. 3000 kgf) has been achieved and sustained during dwell.',
      desc: 'Provides visual confirmation to the operator that hydraulic pressure has reached the calibrated test threshold.',
      tip: 'Calibrated annually according to ASTM E10 Annex A1 using certified proving rings or secondary load cells.'
    },
    'microscope': {
      title: 'Brinell Optical Measuring Microscope',
      badge: 'OPTICAL METROLOGY',
      category: 'Measurement Instrument',
      specs: '20\u00d7 magnification optical microscope with graduated reticle (0.05 mm scale divisions, \u00b10.02 mm resolution).',
      func: 'Measures the diameter of the spherical impression across two mutually perpendicular directions (d\u2081 and d\u2082).',
      desc: 'The arithmetic mean diameter d = (d\u2081 + d\u2082) / 2 is used in the Brinell formula. The two diameter readings must agree within 2% to ensure indentation circularity.',
      tip: 'Direct optical lighting across the indentation rim is crucial for accurate boundary identification.'
    },
    'frame': {
      title: 'Heavy Cast Iron C-Frame',
      badge: 'STRUCTURAL FRAME',
      category: 'Primary Machine Column',
      specs: 'Grade 35 heavy cast iron structural column (1200 kg), designed for < 0.01 mm deflection under 3000 kgf.',
      func: 'Main rigid housing that maintains collinear alignment between the elevating lead screw, anvil, and hydraulic indenter ram.',
      desc: 'High torsional and bending stiffness prevents frame flexing that could introduce non-perpendicular load components into the specimen.',
      tip: 'The throat depth of the C-frame dictates the maximum specimen diameter that can be centered beneath the indenter.'
    }
  };

  const ROCKWELL_DATA = {
    'indenter': {
      title: 'Diamond Spheroconical Indenter (Brale) / Carbide Ball',
      badge: 'INDENTER SYSTEM',
      category: 'Penetration Tool',
      specs: 'Scale C/A/D: 120\u00b0 spheroconical diamond with 0.200 mm spherical tip radius. Scale B/F: 1/16\u2033 (1.588 mm) carbide ball.',
      func: 'Penetrates the material under sequential minor (10 kgf) and major (60/100/150 kgf) forces to measure permanent indentation depth.',
      desc: 'The 120\u00b0 diamond brale is essential for testing hardened steels (HRC: 20 to 70), while carbide balls test softer non-ferrous alloys without cracking.',
      tip: 'Inspect diamond tip under a stereomicroscope periodically; chipped diamond penetrators produce false high hardness readings.'
    },
    'dial-display': {
      title: 'Direct-Reading Hardness Dial Gauge',
      badge: 'DEPTH DISPLAY',
      category: 'Differential Depth Sensor',
      specs: '100 circular divisions. Outer Black scale (HRC: 0\u2013100), Inner Red scale (HRB: 0\u2013130). 1 division = 0.002 mm (2 \u00b5m).',
      func: 'Translates vertical indenter displacement directly into Rockwell hardness numbers: HR = N - (e / 0.002).',
      desc: 'Measures net permanent penetration depth (e) after major load is released while maintaining minor load, eliminating machine frame compliance.',
      tip: 'Align the large needle with the SET mark (zero position) after the 10 kgf minor load is engaged before tripping the major load.'
    },
    'specimen': {
      title: 'Prepared Metallographic Test Sample',
      badge: 'TEST SPECIMEN',
      category: 'Material Sample',
      specs: 'Ground flat parallel faces, thickness t \u2265 10 \u00d7 permanent depth e, minimum thickness 1.5 mm for HRC.',
      func: 'The specimen subjected to differential depth indentation testing.',
      desc: 'Must be stably seated on the anvil. Any rocking or burrs on the bottom face introduce false displacement that degrades Rockwell readings.',
      tip: 'Keep tests spaced at least 3 indentation diameters apart and at least 2.5 diameters away from specimen edges.'
    },
    'anvil': {
      title: 'Hardened Specimen Support Anvil',
      badge: 'SPECIMEN ANCHOR',
      category: 'Support Platen',
      specs: 'Case-hardened steel platen (\u2265 62 HRC), ground flat within 0.002 mm.',
      func: 'Supports the specimen rigidly against normal test loads up to 150 kgf.',
      desc: 'Interchangeable platens include pedestal anvils for small parts, flat anvils for plates, and V-groove anvils for shafts.',
      tip: 'Wipe both the anvil seat and specimen underside before each reading to prevent mechanical compliance errors.'
    },
    'elevating-screw': {
      title: 'Elevating Lead Screw & Handwheel',
      badge: 'MANUAL ELEVATION',
      category: 'Height Positioning',
      specs: 'Precision Acme lead screw with heavy spoked handwheel and telescoping dust sleeve.',
      func: 'Raises the specimen to apply the 10 kgf minor preload until the dial indicator reaches the SET mark.',
      desc: 'Smooth rotational travel ensures sensitive minor load seating without impacting the specimen surface.',
      tip: 'Turn handwheel smoothly until the small pointer enters the minor load zone and the large needle rests on SET.'
    },
    'dashpot-lever': {
      title: 'Oil Dashpot Load Rate Regulator',
      badge: 'SPEED REGULATION',
      category: 'Hydraulic Damper Subsystem',
      specs: 'Adjustable viscous oil dashpot; calibrated descent time: 4 to 6 seconds.',
      func: 'Regulates the speed of major load application to ensure smooth, impact-free penetrator descent.',
      desc: 'A needle valve controls oil bypass. Prevents sudden load shock that would cause excessive penetrator depth and erroneous low hardness.',
      tip: 'Check dashpot oil viscosity seasonally to prevent temperature-induced variations in loading speed.'
    },
    'operating-lever': {
      title: 'Major Load Tripping & Reset Handle',
      badge: 'LOAD TRIGGER',
      category: 'Mechanism Actuator',
      specs: 'Spring-assisted release and manual reset lever linked to deadweight beam.',
      func: 'Pushed forward to trip major load application; pulled back smoothly to release major load while maintaining minor load.',
      desc: 'Releasing the major load allows elastic recovery of the test material, isolating true plastic depth (e).',
      tip: 'Do not jerk the operating lever during reset; pull backward smoothly with constant hand motion.'
    },
    'frame': {
      title: 'Rigid Heavy-Duty Structural Column',
      badge: 'MAIN STRUCTURAL COLUMN',
      category: 'Cast Iron Housing',
      specs: 'Fine-grained pearlitic cast iron housing engineered for zero deflection under 150 kgf load.',
      func: 'Houses the internal deadweight levers, dashpot damper, dial linkage, and elevating screw column.',
      desc: 'Rigid geometry guarantees that all vertical motion measured by the dial reflects specimen penetration rather than frame flexure.',
      tip: 'A sturdy vibration-isolated laboratory bench is required to prevent external floor vibrations from affecting dial stability.'
    }
  };

  const UTM_DATA = {
    'part-load-cell': {
      title: 'Precision Strain-Gauge Load Cell (50 kN)',
      badge: 'FORCE TRANSDUCER',
      category: 'Sensory & Transduction Subsystem',
      specs: 'Capacity: 50 kN | Accuracy: Class 0.5 (ISO 7500-1) | Non-linearity: \u00b10.25% Full Scale',
      func: 'Measures axial tensile force applied to the specimen with millivolt electrical precision via a Wheatstone bridge circuit.',
      desc: 'Internal elastic proof body deforms minutely under load. Foil strain gauges convert mechanical deformation into calibrated electrical force signals.',
      tip: 'Tare/Zero the load cell prior to clamping the specimen to prevent recording the dead weight of the upper grip assembly.'
    },
    'part-crosshead': {
      title: 'Movable Electromechanical Crosshead',
      badge: 'KINEMATICS DRIVE',
      category: 'Displacement Subsystem',
      specs: 'Crosshead speed: 0.001 to 500 mm/min | Maximum travel: 1100 mm | Rigidity: >200 kN/mm',
      func: 'Moves vertically with closed-loop servomotor precision to apply controlled strain rate or constant velocity tension.',
      desc: 'Guided symmetrically by twin ball screws. Ensures pure axial translation without bending moments or angular distortion.',
      tip: 'Set electronic travel limits before starting a test to prevent mechanical collision with the base or load cell.'
    },
    'part-upper-grip': {
      title: 'Upper Hydraulic Wedge Grip',
      badge: 'SPECIMEN CLAMPING',
      category: 'Gripping Subsystem',
      specs: 'Clamping pressure: 200 bar hydraulic | Serrated carbide jaws for round and flat specimens.',
      func: 'Secures the upper shouldered end of the tensile dogbone specimen without slippage under loads up to 50 kN.',
      desc: 'Uses self-tightening wedge action: as axial tension increases, tapered jaws clamp more tightly on the specimen shoulder.',
      tip: 'Always align the specimen along the exact center axis of the grip to avoid parasitic bending stresses.'
    },
    'part-specimen': {
      title: 'Standard Dogbone Tensile Specimen',
      badge: 'TEST SPECIMEN',
      category: 'Mechanical Test Subject',
      specs: 'ASTM E8 / ISO 6892-1: Gauge diameter d\u2080 = 10 mm (A\u2080 = 78.54 mm\u00b2), Gauge length L\u2080 = 50 mm, Fillet R \u2265 10 mm.',
      func: 'The standardized material specimen engineered for uniaxial tensile evaluation.',
      desc: 'Larger shouldered ends permit secure gripping while reduced gauge section ensures uniform uniaxial stress and localized fracture within gauge marks.',
      tip: 'Measure initial gauge diameter at three distinct locations with a micrometer and record average value before testing.'
    },
    'part-extensometer': {
      title: 'Clip-on Dual Averaging Extensometer',
      badge: 'STRAIN TRANSDUCER',
      category: 'High-Precision Instrumentation',
      specs: 'Gauge length L\u2080 = 50 mm | Measuring range: +25 mm / -2.5 mm | Classification: Class 0.5 (ASTM E83).',
      func: 'Directly measures true specimen elongation across gauge marks, bypassing machine frame compliance and grip seating deflection.',
      desc: 'Hardened knife-edges attach directly to the specimen gauge marks. Internal flexure elements with strain gauges measure micro-strain.',
      tip: 'Remove extensometer prior to violent fracture to protect delicate flexure springs from explosive release shock.'
    },
    'part-lower-grip': {
      title: 'Lower Stationary Reaction Grip',
      badge: 'SPECIMEN ANCHOR',
      category: 'Reaction Anchor',
      specs: 'Reaction capacity: 100 kN static | Concentricity tolerance: within 0.05 mm TIR along vertical axis.',
      func: 'Provides rigid lower reaction anchoring for the bottom shouldered end of the tensile specimen.',
      desc: 'Bolted to the machine base platen. Aligned coaxially with the upper grip to ensure pure tensile stress without torsional moments.',
      tip: 'Inspect jaw faces regularly for metal swarf accumulation to ensure uniform frictional contact.'
    },
    'part-lead-screws': {
      title: 'Twin Ball-Screw Drive Columns',
      badge: 'POWER TRANSMISSION',
      category: 'Mechanical Drive Subsystem',
      specs: 'Diameter: 40 mm | Pitch: 5 mm | Recirculating ball nut | Backlash: < 0.005 mm.',
      func: 'Transmits synchronized rotational torque from the drive motor into smooth, backlash-free linear crosshead motion.',
      desc: 'Hardened induction-treated ball screws provide ultra-high axial stiffness and mechanical efficiency (>90%).',
      tip: 'Keep protective telescopic bellows in place to prevent abrasive shop grit from compromising recirculating ball bearings.'
    },
    'part-control-panel': {
      title: 'Digital Data Acquisition & Telemetry Console',
      badge: 'DATA ACQUISITION',
      category: 'Digital Controller Subsystem',
      specs: 'Closed-loop DSP controller | 1 kHz sampling rate | 24-bit A/D resolution | Ethernet / USB 3.0 interface.',
      func: 'Digitizes load cell and extensometer signals simultaneously, streaming real-time stress, strain, and force curves to the software.',
      desc: 'Executes closed-loop PID control to maintain strict ASTM E8 strain rates during both elastic and plastic regimes.',
      tip: 'Ensure the prominent Emergency Stop (E-STOP) palm button is unobstructed and fully functional before test initiation.'
    }
  };

  // =========================================================================
  // 2. UNIVERSAL INSPECTOR CONTROLLER
  // =========================================================================

  function normalizeKey(str) {
    if (!str) return '';
    return str.toLowerCase().replace(/^part-/, '').replace(/^brinell-/, '').replace(/^rockwell-/, '').replace(/^utm-/, '').trim();
  }

  function getComponentInfo(diagramType, rawKey) {
    const key = normalizeKey(rawKey);

    if (diagramType === 'brinell') {
      if (BRINELL_DATA[key]) return BRINELL_DATA[key];
      // Fallback matching
      for (const k in BRINELL_DATA) {
        if (key.includes(k) || k.includes(key)) return BRINELL_DATA[k];
      }
    } else if (diagramType === 'rockwell') {
      if (ROCKWELL_DATA[key]) return ROCKWELL_DATA[key];
      // Map common synonyms
      if (key === 'dial' || key === 'gauge') return ROCKWELL_DATA['dial-display'];
      if (key === 'dashpot' || key === 'shock') return ROCKWELL_DATA['dashpot-lever'];
      if (key === 'lever' || key === 'handle') return ROCKWELL_DATA['operating-lever'];
      for (const k in ROCKWELL_DATA) {
        if (key.includes(k) || k.includes(key)) return ROCKWELL_DATA[k];
      }
    } else if (diagramType === 'tensile' || diagramType === 'utm') {
      if (UTM_DATA[rawKey]) return UTM_DATA[rawKey];
      if (UTM_DATA['part-' + key]) return UTM_DATA['part-' + key];
      for (const k in UTM_DATA) {
        if (k.includes(key) || key.includes(normalizeKey(k))) return UTM_DATA[k];
      }
    }
    return null;
  }

  function initDiagram(containerId, diagramType, cardId, defaultPart) {
    const container = document.getElementById(containerId);
    if (!container) return;

    // Check if SVG is already present inline
    let svg = container.querySelector('svg');

    function bindEvents(svgElement) {
      if (!svgElement) return;

      const interactiveParts = svgElement.querySelectorAll('.interactive-part, [data-part], [id^="part-"]');
      if (!interactiveParts || interactiveParts.length === 0) return;

      interactiveParts.forEach(el => {
        el.style.cursor = 'pointer';
        el.setAttribute('role', 'button');
        el.setAttribute('tabindex', '0');
        el.setAttribute('aria-label', el.getAttribute('data-part') || el.id || 'Equipment Component');

        // Helper to select this part
        const activate = (evt) => {
          if (evt) {
            evt.preventDefault();
            evt.stopPropagation();
          }
          const partKey = el.getAttribute('data-part') || el.id;
          selectPart(diagramType, partKey, svgElement, cardId);
        };

        // Desktop Mouse Click
        el.addEventListener('click', activate);

        // Mobile / Tablet Touch
        let touchStartX = 0;
        let touchStartY = 0;
        el.addEventListener('touchstart', (e) => {
          if (e.touches && e.touches[0]) {
            touchStartX = e.touches[0].clientX;
            touchStartY = e.touches[0].clientY;
          }
        }, { passive: true });

        el.addEventListener('touchend', (e) => {
          if (e.changedTouches && e.changedTouches[0]) {
            const dx = Math.abs(e.changedTouches[0].clientX - touchStartX);
            const dy = Math.abs(e.changedTouches[0].clientY - touchStartY);
            // Only trigger if it wasn't a scroll swipe
            if (dx < 12 && dy < 12) {
              activate(e);
            }
          }
        });

        // Keyboard Access (Enter or Spacebar)
        el.addEventListener('keydown', (e) => {
          if (e.key === 'Enter' || e.key === ' ') {
            activate(e);
          }
        });
      });

      // Select default component if specified
      if (defaultPart) {
        selectPart(diagramType, defaultPart, svgElement, cardId);
      }
    }

    if (svg) {
      bindEvents(svg);
    } else {
      // If SVG not inline (e.g. rendered as img or template load fallback), fetch and inline it
      const img = container.querySelector('img');
      const src = img ? img.getAttribute('src') : `/static/images/${diagramType}_tester.svg`;
      if (src) {
        fetch(src)
          .then(res => res.text())
          .then(svgText => {
            if (svgText.includes('<svg')) {
              container.innerHTML = svgText;
              const newSvg = container.querySelector('svg');
              if (newSvg) {
                newSvg.style.width = '100%';
                newSvg.style.height = 'auto';
                newSvg.style.maxHeight = '520px';
                bindEvents(newSvg);
              }
            }
          })
          .catch(err => {
            console.warn('[MAT-VLAB Diagram] Could not inline SVG:', err);
          });
      }
    }
  }

  function selectPart(diagramType, partKey, svgElement, cardId) {
    if (!partKey) return;
    const info = getComponentInfo(diagramType, partKey);
    if (!info) return;

    // 1. Highlight selected element in SVG
    if (svgElement) {
      svgElement.querySelectorAll('.interactive-part, [data-part], [id^="part-"]').forEach(el => {
        el.classList.remove('active-part');
      });

      const normKey = normalizeKey(partKey);
      let target = svgElement.querySelector(`[data-part="${partKey}"]`) ||
                   svgElement.querySelector(`[data-part="${normKey}"]`) ||
                   svgElement.getElementById(partKey) ||
                   svgElement.getElementById('part-' + normKey);

      if (target) {
        target.classList.add('active-part');
      }
    }

    // 2. Render Component Information into the card
    renderCard(cardId, info, partKey, diagramType, svgElement);
  }

  function renderCard(cardId, info, rawKey, diagramType, svgElement) {
    const card = document.getElementById(cardId);
    if (!card) return;

    card.innerHTML = `
      <div class="d-flex align-items-center justify-content-between mb-2">
        <div class="d-flex align-items-center gap-2">
          <span class="badge bg-primary px-2 py-1 font-mono small">${info.badge || 'COMPONENT'}</span>
          <span class="badge bg-light text-muted border font-mono small">${info.category || 'Apparatus Part'}</span>
        </div>
        <button type="button" class="btn btn-sm btn-outline-secondary py-0 px-2 rounded-circle" id="${cardId}-close-btn" title="Close Information Panel" aria-label="Close Inspector">
          &times;
        </button>
      </div>

      <h4 class="fw-bold text-navy mb-2 fs-5" id="${cardId}-title">${info.title}</h4>

      <div class="p-3 bg-light rounded border border-secondary border-opacity-25 mb-3 small">
        <div class="text-secondary fw-semibold mb-1">
          <i class="fas fa-cogs text-steel me-1"></i> Technical Specification:
        </div>
        <div class="text-dark font-mono">${info.specs}</div>
      </div>

      <div class="mb-3 small">
        <div class="text-secondary fw-semibold mb-1">
          <i class="fas fa-wrench text-steel me-1"></i> Working Principle &amp; Function:
        </div>
        <div class="text-secondary leading-relaxed">${info.func || info.principle || info.desc}</div>
      </div>

      ${info.desc && info.func ? `
      <div class="mb-3 small text-secondary leading-relaxed">
        ${info.desc}
      </div>` : ''}

      <div class="alert alert-info py-2 px-3 small d-flex align-items-center gap-2 mb-0">
        <i class="fas fa-lightbulb text-primary fs-5"></i>
        <div>${info.tip || info.safety || 'Click or tap any component on the schematic to inspect its technical details.'}</div>
      </div>
    `;

    // Bind Close Button
    const closeBtn = document.getElementById(`${cardId}-close-btn`);
    if (closeBtn) {
      closeBtn.addEventListener('click', (e) => {
        e.preventDefault();
        // Clear active SVG highlights
        if (svgElement) {
          svgElement.querySelectorAll('.active-part').forEach(el => el.classList.remove('active-part'));
        }
        // Show gentle placeholder
        card.innerHTML = `
          <div class="text-center py-5">
            <div class="mx-auto mb-3 d-flex align-items-center justify-content-center rounded-circle bg-light text-steel shadow-sm" style="width: 56px; height: 56px; font-size: 1.5rem;">
              <i class="fas fa-hand-pointer"></i>
            </div>
            <h5 class="fw-bold text-navy mb-2">Equipment Component Inspector</h5>
            <p class="text-secondary small mb-3">
              Click or tap any labeled component on the machine schematic to inspect its technical specifications, working principle, and materials testing role.
            </p>
            <div class="d-flex justify-content-center gap-2 flex-wrap">
              <span class="badge bg-light text-secondary border font-mono small">Interactive Schematic</span>
              <span class="badge bg-light text-secondary border font-mono small">ASTM Standards</span>
            </div>
          </div>
        `;
      });
    }

    // Synchronize external dropdown if present (e.g. Tensile UTM dropdown)
    const dropdown = document.getElementById('utm-component-select');
    if (dropdown && dropdown.value !== rawKey) {
      const matchOpt = dropdown.querySelector(`option[value="${rawKey}"]`) ||
                       dropdown.querySelector(`option[value="part-${rawKey}"]`);
      if (matchOpt) dropdown.value = matchOpt.value;
    }
  }

  // =========================================================================
  // 3. AUTO-DISCOVERY ON DOM CONTENT LOADED
  // =========================================================================

  document.addEventListener('DOMContentLoaded', function () {
    // 1. Brinell Machine Inspector
    if (document.getElementById('brinell-svg-container')) {
      initDiagram('brinell-svg-container', 'brinell', 'component-card', 'indenter');
    }

    // 2. Rockwell Machine Inspector
    if (document.getElementById('rockwell-svg-container')) {
      initDiagram('rockwell-svg-container', 'rockwell', 'r-component-card', 'dial-display');
    }

    // 3. Universal Testing Machine (Tensile UTM) Inspector
    if (document.getElementById('utm-svg-container')) {
      initDiagram('utm-svg-container', 'tensile', 'utm-component-card', 'part-load-cell');

      // Bind dropdown change for Tensile UTM
      const utmSelect = document.getElementById('utm-component-select');
      if (utmSelect) {
        utmSelect.addEventListener('change', function (e) {
          const container = document.getElementById('utm-svg-container');
          const svg = container ? container.querySelector('svg') : null;
          selectPart('tensile', e.target.value, svg, 'utm-component-card');
        });
      }
    }
  });

  // Expose global controller
  window.MatVLabDiagram = {
    selectPart: selectPart,
    initDiagram: initDiagram
  };

})();
