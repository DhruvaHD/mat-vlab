"""
MAT-VLAB Materials Testing Suite: Impact Test PDF Report Generator
Generates certified, publication-grade academic laboratory reports for:
- Charpy V-Notch / U-Notch Impact Test (ASTM E23 / ISO 148-1 / IS 1757)
- Izod Impact Test (ASTM E23 / ISO 180 / IS 1598)
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


def generate_dbtt_chart(temp_sweep, current_temp=None, current_energy=None, material_name="Mild Steel"):
    """Generates an executive-level Charpy DBTT transition curve as an in-memory PNG."""
    fig, ax = plt.subplots(figsize=(6.5, 3.2), dpi=200)

    # Style plot in cool green aesthetics
    fig.patch.set_facecolor('#ffffff')
    ax.set_facecolor('#f5f9f6')

    if temp_sweep and len(temp_sweep) > 2:
        temps = [pt['temperature_c'] for pt in temp_sweep]
        energies = [pt['energy_j'] for pt in temp_sweep]

        ax.plot(temps, energies, color='#1b6b50', linewidth=2.5, label=f'{material_name} DBTT Model')
        ax.scatter(temps, energies, color='#0f3d2e', s=25, zorder=4)

        # Mark current test condition if provided
        if current_temp is not None and current_energy is not None:
            ax.scatter([current_temp], [current_energy], color='#e11d48', s=90, zorder=5,
                       edgecolors='#ffffff', linewidth=1.5,
                       label=f'Tested: {current_temp:.0f}°C, {current_energy:.1f} J')
            ax.annotate(f'Tested Point ({current_temp:.0f}°C, {current_energy:.1f}J)',
                        xy=(current_temp, current_energy),
                        xytext=(current_temp + 8, current_energy + (max(energies)*0.08)),
                        arrowprops=dict(facecolor='#e11d48', shrink=0.08, width=1, headwidth=5),
                        fontsize=8, fontweight='bold', color='#881337',
                        bbox=dict(boxstyle="round,pad=0.3", fc="#ffe4e6", ec="#e11d48", lw=1))
    else:
        # Fallback dummy bar
        ax.bar(['Tested Condition'], [current_energy or 100.0], color='#1b6b50', width=0.4)

    ax.set_title("Charpy Impact Energy vs. Test Temperature (DBTT Transition)", fontsize=10, fontweight='bold', color='#0f3d2e', pad=8)
    ax.set_xlabel("Test Temperature (°C)", fontsize=8.5, fontweight='bold', color='#11231b')
    ax.set_ylabel("Absorbed Impact Energy KV (Joules)", fontsize=8.5, fontweight='bold', color='#11231b')
    ax.grid(True, linestyle='--', alpha=0.5, color='#d6e5dc')
    handles, labels = ax.get_legend_handles_labels()
    if handles:
        ax.legend(handles, labels, loc='upper left', fontsize=7.5, framealpha=0.9)

    plt.tight_layout()
    img_buffer = io.BytesIO()
    fig.savefig(img_buffer, format='png', bbox_inches='tight')
    plt.close(fig)
    img_buffer.seek(0)
    return img_buffer


def generate_impact_pdf(experiment_data, student_info=None):
    """
    Generates an executive-level engineering laboratory report in PDF format for Impact Testing.

    Parameters:
    - experiment_data: Dict matching database format for impact_experiments
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
        alignment=1  # Center
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

    specimen_type = (experiment_data.get('specimen_type') or 'charpy_v').lower()
    is_charpy = 'charpy' in specimen_type
    method_name = "CHARPY PENDULUM IMPACT TEST" if is_charpy else "IZOD CANTILEVER IMPACT TEST"
    std_ref = "ASTM E23 / ISO 148-1 / IS 1757" if is_charpy else "ASTM E23 / ISO 180 / IS 1598"

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
                      f"using standard {std_ref} dynamic fracture mechanics algorithms for educational study.</font>"
    else:
        banner_color = colors.HexColor('#e8f5ef')
        banner_border = colors.HexColor('#1b6b50')
        banner_text = f"<font color='#0f3d2e'><b>DATA CLASSIFICATION: USER-ENTERED LABORATORY DATA</b><br/>" \
                      f"These observation readings were physically measured and manually entered by the student from physical " \
                      f"pendulum impact machine observations according to {std_ref}.</font>"

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

    # 3. Student & Experiment Metadata Table
    student = student_info or {}
    sid = student.get('student_id') or experiment_data.get('student_id') or 'N/A'
    sname = student.get('name') or experiment_data.get('student_name') or 'Enrolled Student'
    scourse = student.get('course') or experiment_data.get('student_course') or 'Mechanical / Materials Engineering'
    suni = student.get('university') or experiment_data.get('student_university') or 'Academic Institution'
    created_at = experiment_data.get('created_at', datetime.now().strftime('%Y-%m-%d %H:%M'))
    mat_name = experiment_data.get('material_name', 'Engineering Metallic Specimen')
    temp_c = float(experiment_data.get('test_temperature_c', 23.0))

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
            Paragraph("<b>Testing Method:</b>", body_style), Paragraph(f"<b>{method_name}</b>", body_style),
            Paragraph("<b>Governing Standard:</b>", body_style), Paragraph(std_ref, body_style)
        ],
        [
            Paragraph("<b>Material Tested:</b>", body_style), Paragraph(f"<b>{mat_name}</b>", body_style),
            Paragraph("<b>Test Temperature:</b>", body_style), Paragraph(f"<b>{temp_c:.1f} °C</b>", body_style)
        ],
        [
            Paragraph("<b>Specimen Geometry:</b>", body_style), Paragraph("10 × 10 × 55 mm, 2 mm V-Notch (A₀ = 0.80 cm²)", body_style),
            Paragraph("<b>Machine Capacity:</b>", body_style), Paragraph("300 J Charpy / 168 J Izod", body_style)
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

    # 4. Multi-Trial Experimental Observations Table
    elements.append(Paragraph("<b>1. Experimental Observations &amp; Dynamic Fracture Readings</b>", section_heading))

    readings = experiment_data.get('readings', [])
    rows = [[
        Paragraph("Trial #", table_header),
        Paragraph("Temp (°C)", table_header),
        Paragraph("Initial E₀ (J)", table_header),
        Paragraph("Residual E₁ (J)", table_header),
        Paragraph("Absorbed K_V (J)", table_header),
        Paragraph("Toughness a_k (J/cm²)", table_header),
        Paragraph("Lat. Exp (mm)", table_header),
        Paragraph("Shear %", table_header)
    ]]

    for r in readings:
        t_no = r.get('trial_number', 1)
        t_c = r.get('temperature_celsius', temp_c)
        e0 = r.get('initial_energy_j', 300.0)
        e1 = r.get('residual_energy_j', 0.0)
        kv = r.get('absorbed_energy_j', 0.0)
        ak = r.get('ak_j_cm2', round(kv / 0.80, 2))
        lat = r.get('lateral_expansion_mm', 0.0)
        pct_sh = r.get('pct_shear_fracture', 0.0)

        rows.append([
            Paragraph(f"Trial {t_no}", table_cell),
            Paragraph(f"{t_c:.1f}", table_cell),
            Paragraph(f"{e0:.1f}", table_cell),
            Paragraph(f"{e1:.1f}", table_cell),
            Paragraph(f"<b>{kv:.2f}</b>", table_cell),
            Paragraph(f"<b>{ak:.2f}</b>", table_cell),
            Paragraph(f"{lat:.2f}" if lat else "—", table_cell),
            Paragraph(f"{pct_sh:.1f}%" if pct_sh else "—", table_cell)
        ])

    table_obs = Table(rows, colWidths=[55, 60, 65, 65, 80, 85, 60, 50])
    table_obs.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#0f3d2e')),
        ('BOX', (0,0), (-1,-1), 1, colors.HexColor('#0f3d2e')),
        ('INNERGRID', (0,0), (-1,-1), 0.5, colors.HexColor('#d6e5dc')),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.HexColor('#ffffff'), colors.HexColor('#f5f9f6')]),
        ('TOPPADDING', (0,0), (-1,-1), 3),
        ('BOTTOMPADDING', (0,0), (-1,-1), 3),
    ]))
    elements.append(table_obs)
    elements.append(Spacer(1, 8))

    # 5. Statistical Results & Metallurgical Assessment
    summary = experiment_data.get('summary', {})
    mean_kv = summary.get('mean_absorbed_energy_j', 0.0)
    std_dev = summary.get('std_dev_j', 0.0)
    mean_ak = summary.get('mean_ak_j_cm2', round(mean_kv / 0.80, 2))
    ak_kj = summary.get('mean_ak_kj_m2', mean_ak * 10.0)
    frac_mode = summary.get('fracture_type', 'Fibrous / Cleavage')

    elements.append(Paragraph("<b>2. Mechanical Property Evaluation &amp; Statistical Metrics</b>", section_heading))

    metrics_data = [
        [
            Paragraph("<b>Mean Absorbed Energy (K_V):</b>", body_style),
            Paragraph(f"<font color='#0f3d2e'><b>{mean_kv:.2f} J</b> (± {std_dev:.2f} J)</font>", body_style),
            Paragraph("<b>Notch Toughness (a_k):</b>", body_style),
            Paragraph(f"<font color='#1b6b50'><b>{mean_ak:.2f} J/cm²</b> ({ak_kj:.1f} kJ/m²)</font>", body_style)
        ],
        [
            Paragraph("<b>Fracture Appearance:</b>", body_style),
            Paragraph(f"<b>{frac_mode}</b>", body_style),
            Paragraph("<b>Mean Lateral Expansion:</b>", body_style),
            Paragraph(f"<b>{summary.get('mean_lateral_expansion_mm', 0.0):.2f} mm</b>", body_style)
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

    # 6. Embed Matplotlib DBTT Curve
    temp_sweep = experiment_data.get('temperature_sweep', [])
    try:
        chart_buf = generate_dbtt_chart(temp_sweep, current_temp=temp_c, current_energy=mean_kv, material_name=mat_name)
        img = Image(chart_buf, width=500, height=210)
        elements.append(img)
        elements.append(Spacer(1, 6))
    except Exception as e:
        pass

    # 7. Governing Scientific Formulas (Readable, Zero Raw LaTeX)
    elements.append(Paragraph("<b>3. Governing Engineering Equations &amp; Numerical Substitutions</b>", section_heading))
    formula_text = (
        f"<b>1. Specimen Net Area:</b> A₀ = W × (H - a) = 10 mm × (10 mm - 2 mm) = 80 mm² (0.80 cm²)<br/>"
        f"<b>2. Net Absorbed Energy:</b> K_V = E₀ - E₁ - L_f = 300.0 J - E₁ - 0.5 J = <b>{mean_kv:.2f} J</b><br/>"
        f"<b>3. Specific Impact Toughness:</b> a_k = K_V / A₀ = {mean_kv:.2f} J / 0.80 cm² = <b>{mean_ak:.2f} J/cm² ({ak_kj:.1f} kJ/m²)</b>"
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
        f"The {mat_name} specimen tested according to ASTM E23 exhibited an average absorbed impact energy of {mean_kv:.2f} J "
        f"with a notch toughness of {mean_ak:.2f} J/cm² at {temp_c:.1f}°C."
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
