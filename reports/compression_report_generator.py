"""
MAT-VLAB Materials Testing Suite: Compression Test PDF Report Generator
Generates certified, publication-grade academic laboratory reports for:
- Uniaxial Metallic Compression Testing (ASTM E9 / ISO 13314 / IS 14329)
Theme: Cool Green Design System (#0f3d2e, #1b6b50, #2e9e76)
"""

import io
import os
import math
from datetime import datetime

# Matplotlib headless for plot generation
os.environ['MPLCONFIGDIR'] = '/tmp'
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image, HRFlowable, KeepTogether


def generate_compression_curve_chart(readings, yield_mpa=None, ec_gpa=None, material_name="Specimen"):
    """Generates an executive-level compressive stress-strain curve as an in-memory PNG."""
    fig, ax = plt.subplots(figsize=(6.5, 3.2), dpi=200)

    fig.patch.set_facecolor('#ffffff')
    ax.set_facecolor('#f5f9f6')

    if readings and len(readings) > 1:
        strains_pct = [r.get('strain_pct', (r.get('strain', 0.0) * 100.0)) for r in readings]
        stresses = [r.get('stress_mpa', 0.0) for r in readings]

        ax.plot(strains_pct, stresses, color='#1b6b50', linewidth=2.5, label='Engineering Stress-Strain σ_c')
        ax.scatter(strains_pct, stresses, color='#0f3d2e', s=16, alpha=0.7, zorder=3)

        # Plot 0.2% offset line if Ec and yield are available
        if ec_gpa and yield_mpa and ec_gpa > 0:
            offset_strain_pct = 0.2
            max_s = min(max(strains_pct), 5.0)
            line_strains = [offset_strain_pct, offset_strain_pct + (yield_mpa * 1.25) / (ec_gpa * 10.0)]
            line_stresses = [0.0, yield_mpa * 1.25]
            ax.plot(line_strains, line_stresses, color='#e11d48', linestyle='--', linewidth=1.5,
                    label=f'0.2% Offset Line (Ec={ec_gpa:.1f} GPa)')
            ax.scatter([offset_strain_pct + yield_mpa / (ec_gpa * 10.0)], [yield_mpa],
                       color='#e11d48', s=70, zorder=5, edgecolors='#ffffff',
                       label=f'σ_cy (0.2%) = {yield_mpa:.1f} MPa')

    ax.set_title(f"Compressive Stress-Strain Curve — {material_name} (ASTM E9)",
                 fontsize=10, fontweight='bold', color='#0f3d2e', pad=8)
    ax.set_xlabel("Compressive Strain ε_c (%)", fontsize=8.5, fontweight='bold', color='#11231b')
    ax.set_ylabel("Compressive Stress σ_c (MPa)", fontsize=8.5, fontweight='bold', color='#11231b')
    ax.grid(True, linestyle='--', alpha=0.5, color='#d6e5dc')
    ax.tick_params(axis='both', which='major', labelsize=8)
    ax.legend(loc='lower right', fontsize=7.5, framealpha=0.9)

    plt.tight_layout()
    img_buffer = io.BytesIO()
    fig.savefig(img_buffer, format='png', bbox_inches='tight')
    plt.close(fig)
    img_buffer.seek(0)
    return img_buffer


def generate_compression_pdf(experiment_data, student_info=None):
    """
    Generates an executive-level engineering laboratory report in PDF format for Compression Testing.

    Parameters:
    - experiment_data: Dict matching database format for compression experiments
    - student_info: Optional dict with name, student_id, course, university

    Returns:
    - io.BytesIO containing the generated PDF binary stream.
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

    # Cool Green Typography Styles
    title_style = ParagraphStyle(
        'DocTitle',
        parent=styles['Heading1'],
        fontName='Helvetica-Bold',
        fontSize=18,
        leading=22,
        textColor=colors.HexColor('#0f3d2e'),
        alignment=1
    )

    subtitle_style = ParagraphStyle(
        'DocSubtitle',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=10,
        leading=14,
        textColor=colors.HexColor('#375345'),
        alignment=1
    )

    section_heading = ParagraphStyle(
        'SectionHeading',
        parent=styles['Heading2'],
        fontName='Helvetica-Bold',
        fontSize=11,
        leading=15,
        textColor=colors.HexColor('#0f3d2e'),
        spaceBefore=8,
        spaceAfter=4
    )

    body_style = ParagraphStyle(
        'DocBody',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=8.5,
        leading=12,
        textColor=colors.HexColor('#11231b')
    )

    callout_text = ParagraphStyle(
        'CalloutText',
        parent=body_style,
        fontName='Helvetica-Bold',
        fontSize=8.5,
        leading=12,
        alignment=1
    )

    table_header = ParagraphStyle(
        'TableHeader',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=8,
        leading=10,
        textColor=colors.HexColor('#ffffff'),
        alignment=1
    )

    table_cell = ParagraphStyle(
        'TableCell',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=8,
        leading=10,
        textColor=colors.HexColor('#11231b'),
        alignment=1
    )

    elements = []

    # 1. Header & Title
    elements.append(Paragraph("<b>MAT-VLAB — MATERIALS TESTING LABORATORY</b>", title_style))
    elements.append(Paragraph("Department of Materials Science &amp; Metallurgical Engineering | Certified Laboratory Report", subtitle_style))
    elements.append(Spacer(1, 6))
    elements.append(HRFlowable(width="100%", thickness=2, color=colors.HexColor('#0f3d2e'), spaceAfter=8))

    std_ref = "ASTM E9 / ISO 13314 / IS 14329"

    # 2. Mode Distinction Banner
    mode = experiment_data.get('mode', 'MANUAL_ENTRY')
    data_origin = experiment_data.get('data_origin')
    if not data_origin:
        data_origin = 'SIMULATION / DEMONSTRATION DATA' if mode == 'VIRTUAL_SIMULATION' else 'USER-ENTERED LABORATORY DATA'

    if 'SIMULATION' in data_origin.upper():
        banner_color = colors.HexColor('#fef3c7')
        banner_border = colors.HexColor('#d97706')
        banner_text = f"<font color='#92400e'><b>DATA CLASSIFICATION: SIMULATION / DEMONSTRATION DATA</b><br/>" \
                      f"These experimental observations were generated within the interactive MAT-VLAB virtual laboratory simulation " \
                      f"using standard {std_ref} constitutive plasticity and friction barreling algorithms for educational study.</font>"
    else:
        banner_color = colors.HexColor('#e8f5ef')
        banner_border = colors.HexColor('#1b6b50')
        banner_text = f"<font color='#0f3d2e'><b>DATA CLASSIFICATION: USER-ENTERED LABORATORY DATA</b><br/>" \
                      f"These observation readings were physically measured and manually entered by the student from physical " \
                      f"universal testing machine compression platen observations according to {std_ref}.</font>"

    banner_table = Table([[Paragraph(banner_text, callout_text)]], colWidths=[520])
    banner_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), banner_color),
        ('BOX', (0,0), (-1,-1), 1.5, banner_border),
        ('TOPPADDING', (0,0), (-1,-1), 5),
        ('BOTTOMPADDING', (0,0), (-1,-1), 5),
        ('LEFTPADDING', (0,0), (-1,-1), 8),
        ('RIGHTPADDING', (0,0), (-1,-1), 8),
    ]))
    elements.append(banner_table)
    elements.append(Spacer(1, 8))

    # 3. Student & Specimen Metadata Table
    student = student_info or {}
    sid = student.get('student_id') or experiment_data.get('student_id') or 'N/A'
    sname = student.get('name') or experiment_data.get('student_name') or 'Enrolled Student'
    scourse = student.get('course') or experiment_data.get('student_course') or 'Mechanical / Materials Engineering'
    suni = student.get('university') or experiment_data.get('student_university') or 'Academic Institution'
    created_at = experiment_data.get('created_at', datetime.now().strftime('%Y-%m-%d %H:%M'))
    mat_name = experiment_data.get('material_name', 'Metallic Specimen')

    spec = experiment_data.get('specimen', {})
    d0 = spec.get('original_diameter_mm', experiment_data.get('original_diameter', 15.0))
    h0 = spec.get('original_height_mm', experiment_data.get('original_gauge_length', 30.0))
    slenderness = round(h0 / d0 if d0 > 0 else 2.0, 2)
    a0 = round((math.pi * (d0**2)) / 4.0, 2)

    meta_data = [
        [
            Paragraph("<b>Student Name:</b>", body_style), Paragraph(sname, body_style),
            Paragraph("<b>Student ID:</b>", body_style), Paragraph(f"<b>{sid}</b>", body_style)
        ],
        [
            Paragraph("<b>Degree Program:</b>", body_style), Paragraph(scourse, body_style),
            Paragraph("<b>Institution:</b>", body_style), Paragraph(suni, body_style)
        ],
        [
            Paragraph("<b>Testing Method:</b>", body_style), Paragraph("<b>UNIAXIAL COMPRESSION TEST</b>", body_style),
            Paragraph("<b>Standard:</b>", body_style), Paragraph(std_ref, body_style)
        ],
        [
            Paragraph("<b>Material Tested:</b>", body_style), Paragraph(f"<b>{mat_name}</b>", body_style),
            Paragraph("<b>Test Date &amp; Time:</b>", body_style), Paragraph(str(created_at), body_style)
        ],
        [
            Paragraph("<b>Original Dimensions:</b>", body_style), Paragraph(f"d₀ = {d0:.2f} mm, h₀ = {h0:.2f} mm (A₀ = {a0:.2f} mm²)", body_style),
            Paragraph("<b>Slenderness Ratio:</b>", body_style), Paragraph(f"h₀ / d₀ = {slenderness:.2f} (ASTM E9 Medium)", body_style)
        ]
    ]

    meta_table = Table(meta_data, colWidths=[110, 160, 110, 140])
    meta_table.setStyle(TableStyle([
        ('BOX', (0,0), (-1,-1), 1, colors.HexColor('#d6e5dc')),
        ('INNERGRID', (0,0), (-1,-1), 0.5, colors.HexColor('#e8f5ef')),
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#ffffff')),
        ('TOPPADDING', (0,0), (-1,-1), 3),
        ('BOTTOMPADDING', (0,0), (-1,-1), 3),
        ('LEFTPADDING', (0,0), (-1,-1), 6),
        ('RIGHTPADDING', (0,0), (-1,-1), 6),
    ]))
    elements.append(meta_table)
    elements.append(Spacer(1, 8))

    # 4. Mechanical Properties Summary Table
    summary = experiment_data.get('summary', {})
    ec_gpa = summary.get('elastic_modulus_gpa')
    sig_cy = summary.get('compressive_yield_mpa')
    sig_max = summary.get('max_stress_mpa', 0.0)
    max_load_kn = summary.get('max_load_kn', 0.0)
    max_strain = summary.get('final_strain_pct', 0.0)
    barreling = summary.get('barreling_index', 0.0)
    behavior = summary.get('behavior_mode', 'Compressive Deformation')

    elements.append(Paragraph("<b>1. Mechanical Property Summary &amp; Compressive Characteristics</b>", section_heading))

    metrics_data = [
        [
            Paragraph("<b>Elastic Modulus in Comp. (E_c):</b>", body_style),
            Paragraph(f"<font color='#0f3d2e'><b>{ec_gpa if ec_gpa else 'N/A'} GPa</b></font>", body_style),
            Paragraph("<b>0.2% Offset Yield (σ_cy):</b>", body_style),
            Paragraph(f"<font color='#1b6b50'><b>{sig_cy if sig_cy else 'N/A'} MPa</b></font>", body_style)
        ],
        [
            Paragraph("<b>Max / Ultimate Comp. Stress:</b>", body_style),
            Paragraph(f"<b>{sig_max:.2f} MPa</b> (Max Load: {max_load_kn:.2f} kN)", body_style),
            Paragraph("<b>Final Compressive Strain:</b>", body_style),
            Paragraph(f"<b>{max_strain:.2f} %</b>", body_style)
        ],
        [
            Paragraph("<b>Deformation Mode:</b>", body_style),
            Paragraph(f"<b>{behavior}</b>", body_style),
            Paragraph("<b>Barreling Index (B):</b>", body_style),
            Paragraph(f"<b>{barreling:.3f}</b>", body_style)
        ]
    ]

    metrics_table = Table(metrics_data, colWidths=[140, 130, 130, 120])
    metrics_table.setStyle(TableStyle([
        ('BOX', (0,0), (-1,-1), 1, colors.HexColor('#1b6b50')),
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#f5f9f6')),
        ('INNERGRID', (0,0), (-1,-1), 0.5, colors.HexColor('#d6e5dc')),
        ('TOPPADDING', (0,0), (-1,-1), 4),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
        ('LEFTPADDING', (0,0), (-1,-1), 6),
        ('RIGHTPADDING', (0,0), (-1,-1), 6),
    ]))
    elements.append(metrics_table)
    elements.append(Spacer(1, 8))

    # 5. Embed Stress-Strain Curve
    readings = experiment_data.get('readings', [])
    try:
        chart_buf = generate_compression_curve_chart(readings, yield_mpa=sig_cy, ec_gpa=ec_gpa, material_name=mat_name)
        img = Image(chart_buf, width=500, height=210)
        elements.append(img)
        elements.append(Spacer(1, 6))
    except Exception as e:
        pass

    # 6. Sample Laboratory Readings (up to 12 representative points)
    elements.append(Paragraph("<b>2. Representative Laboratory Compression Readings</b>", section_heading))

    readings_sample = readings
    if len(readings) > 12:
        step = max(1, len(readings) // 10)
        readings_sample = [readings[0]] + readings[1:-1:step] + [readings[-1]]

    rows = [[
        Paragraph("Pt #", table_header),
        Paragraph("Load (kN)", table_header),
        Paragraph("Δh (mm)", table_header),
        Paragraph("Eng. Stress σ_c (MPa)", table_header),
        Paragraph("Eng. Strain ε_c (%)", table_header),
        Paragraph("True Stress (MPa)", table_header),
        Paragraph("True Strain", table_header)
    ]]

    for r in readings_sample:
        p_no = r.get('reading_number', 1)
        l_kn = r.get('load_kn', (r.get('load_n', 0.0) / 1000.0))
        dh = r.get('delta_h_mm', 0.0)
        sig = r.get('stress_mpa', 0.0)
        eps_pct = r.get('strain_pct', (r.get('strain', 0.0) * 100.0))
        t_sig = r.get('true_stress_mpa', sig)
        t_eps = r.get('true_strain', eps_pct / 100.0)

        rows.append([
            Paragraph(str(p_no), table_cell),
            Paragraph(f"{l_kn:.2f}", table_cell),
            Paragraph(f"{dh:.3f}", table_cell),
            Paragraph(f"<b>{sig:.2f}</b>", table_cell),
            Paragraph(f"{eps_pct:.2f}%", table_cell),
            Paragraph(f"{t_sig:.2f}", table_cell),
            Paragraph(f"{t_eps:.4f}", table_cell)
        ])

    table_obs = Table(rows, colWidths=[40, 70, 70, 100, 90, 80, 70])
    table_obs.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#0f3d2e')),
        ('BOX', (0,0), (-1,-1), 1, colors.HexColor('#0f3d2e')),
        ('INNERGRID', (0,0), (-1,-1), 0.5, colors.HexColor('#d6e5dc')),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.HexColor('#ffffff'), colors.HexColor('#f5f9f6')]),
        ('TOPPADDING', (0,0), (-1,-1), 2.5),
        ('BOTTOMPADDING', (0,0), (-1,-1), 2.5),
    ]))
    elements.append(table_obs)
    elements.append(Spacer(1, 8))

    # 7. Governing Scientific Formulas
    elements.append(Paragraph("<b>3. Governing ASTM E9 Engineering Equations</b>", section_heading))
    formula_text = (
        f"<b>1. Compressive Stress:</b> σ_c = F / A₀ = F / ({a0:.2f} mm²) | Max σ_c = <b>{sig_max:.2f} MPa</b><br/>"
        f"<b>2. Compressive Strain:</b> ε_c = Δh / h₀ = Δh / {h0:.2f} mm | Final ε_c = <b>{max_strain:.2f}%</b><br/>"
        f"<b>3. Modulus of Elasticity:</b> E_c = Δσ_c / Δε_c = <b>{ec_gpa if ec_gpa else 0.0:.2f} GPa</b><br/>"
        f"<b>4. 0.2% Proof Stress:</b> σ_cy (0.2% offset) = <b>{sig_cy if sig_cy else 'N/A'} MPa</b>"
    )
    formula_table = Table([[Paragraph(formula_text, body_style)]], colWidths=[520])
    formula_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#e8f5ef')),
        ('BOX', (0,0), (-1,-1), 1, colors.HexColor('#2e9e76')),
        ('PADDING', (0,0), (-1,-1), 6)
    ]))
    elements.append(formula_table)
    elements.append(Spacer(1, 8))

    # 8. Metallurgical Conclusion
    conclusion = experiment_data.get('conclusion') or (
        f"Uniaxial compression testing of {mat_name} demonstrated {behavior}. "
        f"Maximum test stress reached {sig_max:.2f} MPa with {max_strain:.2f}% compressive strain."
    )
    elements.append(Paragraph("<b>4. Metallurgical Conclusion &amp; Standards Compliance</b>", section_heading))
    concl_table = Table([[Paragraph(f"<b>ENGINEERING ASSESSMENT:</b> {conclusion}", body_style)]], colWidths=[520])
    concl_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#ffffff')),
        ('BOX', (0,0), (-1,-1), 1, colors.HexColor('#0f3d2e')),
        ('PADDING', (0,0), (-1,-1), 6)
    ]))
    elements.append(concl_table)
    elements.append(Spacer(1, 10))

    # 9. Verification & Stamp Footer
    footer_text = f"Report Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} UTC | MAT-VLAB Engineering Verification Platform"
    elements.append(Paragraph(footer_text, subtitle_style))

    doc.build(elements)
    buffer.seek(0)
    return buffer
