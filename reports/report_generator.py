import io
import os
import math

# Configure matplotlib for headless generation
os.environ['MPLCONFIGDIR'] = '/tmp'
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

from reportlab.lib.pagesizes import letter, A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image, HRFlowable, KeepTogether
from reportlab.lib.units import inch

def generate_tensile_pdf(experiment_data):
    """
    Generates an executive-level engineering laboratory report in PDF format.

    Parameters:
    - experiment_data: Dict matching database format with experiment metadata,
      readings, results, and quiz info.

    Returns:
    - io.BytesIO containing the generated PDF binary.
    """
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=36,
        leftMargin=36,
        topMargin=36,
        bottomMargin=36
    )

    styles = getSampleStyleSheet()

    # Custom styles
    title_style = ParagraphStyle(
        'DocTitle',
        parent=styles['Heading1'],
        fontName='Helvetica-Bold',
        fontSize=20,
        leading=24,
        textColor=colors.HexColor('#0f172a'),
        alignment=1  # Center
    )

    subtitle_style = ParagraphStyle(
        'DocSubtitle',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=10,
        leading=14,
        textColor=colors.HexColor('#475569'),
        alignment=1
    )

    section_heading = ParagraphStyle(
        'SectionHeading',
        parent=styles['Heading2'],
        fontName='Helvetica-Bold',
        fontSize=12,
        leading=16,
        textColor=colors.HexColor('#1e3a8a'),
        spaceBefore=10,
        spaceAfter=4
    )

    body_style = ParagraphStyle(
        'DocBody',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=9,
        leading=13,
        textColor=colors.HexColor('#1e293b')
    )

    body_bold = ParagraphStyle(
        'DocBodyBold',
        parent=body_style,
        fontName='Helvetica-Bold'
    )

    callout_text = ParagraphStyle(
        'CalloutText',
        parent=body_style,
        fontName='Helvetica-Bold',
        fontSize=9,
        leading=13,
        alignment=1
    )

    elements = []

    # 1. Header & Institutional Crest
    elements.append(Paragraph("<b>MAT-VLAB — MATERIALS TESTING LABORATORY</b>", title_style))
    elements.append(Paragraph("Department of Materials Science & Metallurgical Engineering | Virtual Lab Report", subtitle_style))
    elements.append(Spacer(1, 8))
    elements.append(HRFlowable(width="100%", thickness=2, color=colors.HexColor('#1e3a8a'), spaceAfter=8))

    # 2. Mode Distinction Banner
    mode = experiment_data.get('mode', 'MANUAL_ENTRY')
    if mode == 'VIRTUAL_SIMULATION':
        banner_color = colors.HexColor('#fef3c7')
        banner_border = colors.HexColor('#d97706')
        banner_text = "<font color='#92400e'><b>MODE: SIMULATION / DEMONSTRATION DATA</b><br/>" \
                      "These test values were generated using parametric constitutive equations (ASTM E8 reference model). " \
                      "This data is intended for pedagogical instruction and simulation study.</font>"
    else:
        banner_color = colors.HexColor('#e0f2fe')
        banner_border = colors.HexColor('#0284c7')
        banner_text = "<font color='#0369a1'><b>MODE: USER-ENTERED EXPERIMENTAL DATA</b><br/>" \
                      "These readings were manually entered by the student from physical Universal Testing Machine (UTM) " \
                      "laboratory observations.</font>"

    banner_table = Table([[Paragraph(banner_text, callout_text)]], colWidths=[520])
    banner_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), banner_color),
        ('BOX', (0,0), (-1,-1), 1.5, banner_border),
        ('TOPPADDING', (0,0), (-1,-1), 6),
        ('BOTTOMPADDING', (0,0), (-1,-1), 6),
        ('LEFTPADDING', (0,0), (-1,-1), 10),
        ('RIGHTPADDING', (0,0), (-1,-1), 10),
    ]))
    elements.append(banner_table)
    elements.append(Spacer(1, 10))

    # 3. Experiment Metadata Table
    title = experiment_data.get('title', 'Tensile Test Experiment')
    exp_date = experiment_data.get('created_at', '2026-09-22')
    material_name = experiment_data.get('material_name', 'Mild Steel')
    d0 = experiment_data.get('original_diameter', 10.0)
    l0 = experiment_data.get('original_gauge_length', 50.0)
    lf = experiment_data.get('final_gauge_length', 'N/A')
    df_val = experiment_data.get('final_diameter', 'N/A')
    area = round((math.pi * (float(d0) ** 2)) / 4.0, 2)

    meta_data = [
        [
            Paragraph("<b>Experiment Title:</b>", body_style), Paragraph(str(title), body_style),
            Paragraph("<b>Date & Time:</b>", body_style), Paragraph(str(exp_date), body_style)
        ],
        [
            Paragraph("<b>Material Tested:</b>", body_style), Paragraph(str(material_name), body_style),
            Paragraph("<b>Standard SOP:</b>", body_style), Paragraph("ASTM E8 / ISO 6892-1", body_style)
        ],
        [
            Paragraph("<b>Original Diameter (d₀):</b>", body_style), Paragraph(f"{d0} mm", body_style),
            Paragraph("<b>Original Gauge Length (L₀):</b>", body_style), Paragraph(f"{l0} mm", body_style)
        ],
        [
            Paragraph("<b>Original Area (A₀):</b>", body_style), Paragraph(f"{area} mm²", body_style),
            Paragraph("<b>Final Dimensions (L_f / d_f):</b>", body_style), Paragraph(f"{lf} mm / {df_val} mm", body_style)
        ]
    ]

    meta_table = Table(meta_data, colWidths=[130, 130, 130, 130])
    meta_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#f8fafc')),
        ('BOX', (0,0), (-1,-1), 1, colors.HexColor('#cbd5e1')),
        ('INNERGRID', (0,0), (-1,-1), 0.5, colors.HexColor('#e2e8f0')),
        ('TOPPADDING', (0,0), (-1,-1), 4),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
        ('LEFTPADDING', (0,0), (-1,-1), 6),
        ('RIGHTPADDING', (0,0), (-1,-1), 6),
    ]))
    elements.append(meta_table)
    elements.append(Spacer(1, 10))

    # 4. Objective, Apparatus, & Theory Brief
    elements.append(Paragraph("1. EXPERIMENTAL OBJECTIVE & APPARATUS", section_heading))
    obj_text = "<b>Objective:</b> To evaluate uniaxial tensile properties of the specimen under quasi-static strain rate, determining Young's Modulus (E), Yield Strength (σ_y), Ultimate Tensile Strength (UTS), Percentage Elongation (%EL), and fracture characteristics according to ASTM E8 standard test methods.<br/>" \
               "<b>Apparatus:</b> Computer-controlled Universal Testing Machine (UTM) equipped with 50 kN load cell, hydraulic wedge grips, and dual averaging extensometer."
    elements.append(Paragraph(obj_text, body_style))
    elements.append(Spacer(1, 8))

    # 5. Stress-Strain Curve Plot (Generated with Matplotlib)
    readings = experiment_data.get('readings', [])
    if len(readings) >= 2:
        img_buffer = generate_plot_image(readings, mode, material_name)
        img = Image(img_buffer, width=6.8 * inch, height=3.2 * inch)
        elements.append(Paragraph("2. ENGINEERING STRESS-STRAIN CURVE", section_heading))
        elements.append(img)
        elements.append(Spacer(1, 8))

    # 6. Calculated Mechanical Properties Table
    res = experiment_data.get('results', {})
    elements.append(Paragraph("3. CALCULATED MECHANICAL PROPERTIES", section_heading))

    res_data = [
        [
            Paragraph("<b>Property</b>", body_bold),
            Paragraph("<b>Calculated Value</b>", body_bold),
            Paragraph("<b>Units</b>", body_bold),
            Paragraph("<b>Engineering Significance</b>", body_bold)
        ],
        [
            Paragraph("Young's Modulus (E)", body_style),
            Paragraph(f"{res.get('youngs_modulus_gpa', 'N/A')}", body_style),
            Paragraph("GPa", body_style),
            Paragraph("Measure of atomic bond stiffness in linear elastic region", body_style)
        ],
        [
            Paragraph("Yield Strength (σ_y)", body_style),
            Paragraph(f"{res.get('yield_strength_mpa', 'N/A')}", body_style),
            Paragraph("MPa", body_style),
            Paragraph("Onset of irreversible plastic deformation (0.2% offset / yield drop)", body_style)
        ],
        [
            Paragraph("Ultimate Tensile Strength (UTS)", body_style),
            Paragraph(f"{res.get('uts_mpa', 'N/A')}", body_style),
            Paragraph("MPa", body_style),
            Paragraph("Maximum nominal engineering stress before localized necking", body_style)
        ],
        [
            Paragraph("Percentage Elongation (%EL)", body_style),
            Paragraph(f"{res.get('elongation_pct', 'N/A')}%", body_style),
            Paragraph("%", body_style),
            Paragraph("Ductility and cumulative plastic deformation at fracture", body_style)
        ],
        [
            Paragraph("Tensile Toughness", body_style),
            Paragraph(f"{res.get('toughness_mj_m3', 'N/A')}", body_style),
            Paragraph("MJ / m³", body_style),
            Paragraph("Total strain energy absorption per unit volume up to rupture", body_style)
        ]
    ]

    if res.get('reduction_area_pct'):
        res_data.append([
            Paragraph("Reduction in Area (%RA)", body_style),
            Paragraph(f"{res.get('reduction_area_pct')}%", body_style),
            Paragraph("%", body_style),
            Paragraph("Cross-sectional shrinkage at fracture neck", body_style)
        ])

    res_table = Table(res_data, colWidths=[140, 90, 60, 230])
    res_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#e2e8f0')),
        ('BOX', (0,0), (-1,-1), 1, colors.HexColor('#94a3b8')),
        ('INNERGRID', (0,0), (-1,-1), 0.5, colors.HexColor('#cbd5e1')),
        ('TOPPADDING', (0,0), (-1,-1), 4),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
        ('LEFTPADDING', (0,0), (-1,-1), 6),
        ('RIGHTPADDING', (0,0), (-1,-1), 6),
    ]))
    elements.append(res_table)
    elements.append(Spacer(1, 8))

    # 7. Metallurgical Conclusion
    conclusion = res.get('conclusion', 'Analysis completed.')
    elements.append(Paragraph("4. ENGINEERING CONCLUSION", section_heading))
    elements.append(Paragraph(f"<i>{conclusion}</i>", body_style))
    elements.append(Spacer(1, 8))

    # 8. Quiz Assessment Score (if taken)
    quiz = experiment_data.get('quiz')
    if quiz:
        elements.append(Paragraph("5. STUDENT KNOWLEDGE ASSESSMENT", section_heading))
        q_text = f"Assessment Score: <b>{quiz.get('score')}/{quiz.get('total_questions')} ({quiz.get('percentage')}%)</b> | Completed on {quiz.get('completed_at', 'N/A')}"
        elements.append(Paragraph(q_text, body_style))
        elements.append(Spacer(1, 8))

    # 9. Observation Data Table (first 20 rows)
    if readings:
        elements.append(Paragraph(f"6. OBSERVATION DATA (Sample of {min(len(readings), 20)} of {len(readings)} readings)", section_heading))
        obs_header = [
            Paragraph("<b>#</b>", body_bold),
            Paragraph("<b>Load (N)</b>", body_bold),
            Paragraph("<b>Extension (mm)</b>", body_bold),
            Paragraph("<b>Stress (MPa)</b>", body_bold),
            Paragraph("<b>Strain</b>", body_bold)
        ]
        obs_rows = [obs_header]
        for r in readings[:20]:
            obs_rows.append([
                Paragraph(str(r.get('reading_number', '')), body_style),
                Paragraph(str(r.get('load_n', '')), body_style),
                Paragraph(str(r.get('extension_mm', '')), body_style),
                Paragraph(str(r.get('stress_mpa', 'N/A')), body_style),
                Paragraph(str(r.get('strain', 'N/A')), body_style)
            ])

        obs_table = Table(obs_rows, colWidths=[40, 120, 120, 120, 120])
        obs_table.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#f1f5f9')),
            ('BOX', (0,0), (-1,-1), 0.5, colors.HexColor('#94a3b8')),
            ('INNERGRID', (0,0), (-1,-1), 0.5, colors.HexColor('#e2e8f0')),
            ('TOPPADDING', (0,0), (-1,-1), 2),
            ('BOTTOMPADDING', (0,0), (-1,-1), 2),
            ('LEFTPADDING', (0,0), (-1,-1), 4),
            ('RIGHTPADDING', (0,0), (-1,-1), 4),
        ]))
        elements.append(obs_table)
        elements.append(Spacer(1, 10))

    # 10. Academic Disclaimer Footer
    disclaimer_text = "<b>Academic Disclaimer:</b> MAT-VLAB is an educational simulator and analysis tool developed for university engineering curricula. " \
                      "The results and calculations presented in this document are strictly for instructional purposes and must not be used for industrial safety-critical structural certification."
    elements.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor('#cbd5e1'), spaceBefore=6, spaceAfter=4))
    elements.append(Paragraph(f"<font color='#64748b' size='7'>{disclaimer_text}</font>", body_style))

    # Build document
    doc.build(elements)
    buffer.seek(0)
    return buffer

def generate_plot_image(readings, mode, material_name):
    """
    Renders high-quality stress-strain diagram using matplotlib.
    """
    strains = []
    stresses = []
    for r in readings:
        if r.get('strain') is not None and r.get('stress_mpa') is not None:
            strains.append(float(r['strain']))
            stresses.append(float(r['stress_mpa']))

    fig, ax = plt.subplots(figsize=(8, 3.8), dpi=200)

    # Style
    ax.plot(strains, stresses, color='#1e3a8a', linewidth=2.0, label='Engineering Stress-Strain', zorder=3)
    ax.scatter(strains, stresses, color='#2563eb', s=16, alpha=0.7, zorder=4)

    # Mark UTS
    if stresses:
        max_idx = stresses.index(max(stresses))
        ax.scatter([strains[max_idx]], [stresses[max_idx]], color='#dc2626', s=50, zorder=5, label=f'UTS ({round(stresses[max_idx], 1)} MPa)')
        ax.annotate(
            f'UTS: {round(stresses[max_idx], 1)} MPa',
            xy=(strains[max_idx], stresses[max_idx]),
            xytext=(strains[max_idx] * 0.9, stresses[max_idx] * 1.05),
            arrowprops=dict(facecolor='#dc2626', shrink=0.05, width=1, headwidth=4),
            fontsize=8, fontweight='bold', color='#dc2626'
        )

    # Title & Labeling
    tag_str = "SIMULATION DATA" if mode == 'VIRTUAL_SIMULATION' else "EXPERIMENTAL LAB DATA"
    ax.set_title(f"Engineering Stress-Strain Curve — {material_name} [{tag_str}]", fontsize=11, fontweight='bold', pad=8)
    ax.set_xlabel("Engineering Strain, ε (mm/mm)", fontsize=9, fontweight='bold')
    ax.set_ylabel("Engineering Stress, σ (MPa)", fontsize=9, fontweight='bold')

    ax.grid(True, linestyle='--', alpha=0.6, zorder=1)
    ax.legend(loc='lower right', fontsize=8)
    ax.set_xlim(left=0)
    ax.set_ylim(bottom=0)

    plt.tight_layout()

    img_buffer = io.BytesIO()
    plt.savefig(img_buffer, format='png', dpi=200)
    plt.close(fig)
    img_buffer.seek(0)
    return img_buffer
