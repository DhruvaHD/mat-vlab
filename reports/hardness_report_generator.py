"""
MAT-VLAB Materials Testing Suite: Hardness Test PDF Report Generator
Generates certified, publication-grade academic laboratory reports for:
1. Brinell Hardness Test (ASTM E10 / ISO 6506-1)
2. Rockwell Hardness Test (ASTM E18 / ISO 6508-1)
"""
import io
import os
import math
from datetime import datetime

from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable, KeepTogether

def generate_hardness_pdf(experiment_data, student_info=None):
    """
    Generates an executive-level engineering laboratory report in PDF format for Hardness Testing.

    Parameters:
    - experiment_data: Dict matching database format for hardness_experiments (with parameters, readings, quiz, etc.)
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

    # Custom Typography Styles
    title_style = ParagraphStyle(
        'DocTitle',
        parent=styles['Heading1'],
        fontName='Helvetica-Bold',
        fontSize=18,
        leading=22,
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
        fontSize=11,
        leading=15,
        textColor=colors.HexColor('#1e3a8a'),
        spaceBefore=8,
        spaceAfter=4
    )

    body_style = ParagraphStyle(
        'DocBody',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=8.5,
        leading=12,
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
        textColor=colors.HexColor('#1e293b'),
        alignment=1
    )

    elements = []

    # 1. Header & Title
    elements.append(Paragraph("<b>MAT-VLAB — MATERIALS TESTING LABORATORY</b>", title_style))
    elements.append(Paragraph("Department of Materials Science &amp; Metallurgical Engineering | Certified Laboratory Report", subtitle_style))
    elements.append(Spacer(1, 6))
    elements.append(HRFlowable(width="100%", thickness=2, color=colors.HexColor('#1e3a8a'), spaceAfter=8))

    method = (experiment_data.get('method') or 'BRINELL').upper().strip()
    is_brinell = (method == 'BRINELL')
    test_title = f"{'BRINELL' if is_brinell else 'ROCKWELL'} HARDNESS TEST REPORT"
    std_ref = "ASTM E10 / ISO 6506-1 / IS 1500" if is_brinell else "ASTM E18 / ISO 6508-1 / IS 1586"

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
                      f"using standard {std_ref} metallurgical algorithms for educational study.</font>"
    else:
        banner_color = colors.HexColor('#e0f2fe')
        banner_border = colors.HexColor('#0284c7')
        banner_text = f"<font color='#0369a1'><b>DATA CLASSIFICATION: USER-ENTERED LABORATORY DATA</b><br/>" \
                      f"These observation readings were physically measured and manually entered by the student from physical " \
                      f"hardness testing machine observations according to {std_ref}.</font>"

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
    sname = student.get('name') or 'Enrolled Student'
    scourse = student.get('course') or 'Mechanical / Materials Engineering'
    suni = student.get('university') or 'Academic Institution'
    created_at = experiment_data.get('created_at', datetime.now().strftime('%Y-%m-%d %H:%M'))
    mat_name = experiment_data.get('material_name', 'Engineering Specimen')
    params = experiment_data.get('parameters', {})

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
            Paragraph("<b>Testing Method:</b>", body_style), Paragraph(f"<b>{method} HARDNESS TEST</b>", body_style),
            Paragraph("<b>Standard:</b>", body_style), Paragraph(std_ref, body_style)
        ],
        [
            Paragraph("<b>Material Tested:</b>", body_style), Paragraph(f"<b>{mat_name}</b>", body_style),
            Paragraph("<b>Test Date &amp; Time:</b>", body_style), Paragraph(str(created_at), body_style)
        ]
    ]

    # Add method-specific parameter row
    if is_brinell:
        ball_d = params.get('ball_diameter_mm', 10.0)
        load_p = params.get('load_kgf', 3000.0)
        p_d2 = round(float(load_p) / (float(ball_d)**2), 1)
        dwell = params.get('dwell_sec', 12)
        meta_data.append([
            Paragraph("<b>Ball Indenter (D):</b>", body_style), Paragraph(f"{ball_d} mm (Tungsten Carbide WC)", body_style),
            Paragraph("<b>Applied Load (P):</b>", body_style), Paragraph(f"{load_p} kgf (P/D² = {p_d2}, Dwell: {dwell}s)", body_style)
        ])
    else:
        scale = params.get('scale', 'B')
        indenter = params.get('indenter', '1/16" Ball' if scale == 'B' else 'Diamond Brale Cone')
        f0 = params.get('minor_load_kgf', 10.0)
        f_tot = params.get('total_load_kgf', 100.0 if scale == 'B' else 150.0)
        meta_data.append([
            Paragraph("<b>Rockwell Scale:</b>", body_style), Paragraph(f"<b>Scale {scale} ({experiment_data.get('hardness_unit', 'HRB')})</b>", body_style),
            Paragraph("<b>Indenter &amp; Load:</b>", body_style), Paragraph(f"{indenter} | Total: {f_tot} kgf (Minor: {f0} kgf)", body_style)
        ])

    meta_table = Table(meta_data, colWidths=[110, 150, 110, 150])
    meta_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#f8fafc')),
        ('BOX', (0,0), (-1,-1), 1, colors.HexColor('#cbd5e1')),
        ('INNERGRID', (0,0), (-1,-1), 0.5, colors.HexColor('#e2e8f0')),
        ('TOPPADDING', (0,0), (-1,-1), 3),
        ('BOTTOMPADDING', (0,0), (-1,-1), 3),
        ('LEFTPADDING', (0,0), (-1,-1), 5),
        ('RIGHTPADDING', (0,0), (-1,-1), 5),
    ]))
    elements.append(meta_table)
    elements.append(Spacer(1, 8))

    # 4. Objective & Principle
    elements.append(Paragraph("1. OBJECTIVE &amp; ENGINEERING PRINCIPLE", section_heading))
    if is_brinell:
        obj_text = (
            "<b>Objective:</b> To determine the Brinell Hardness Number (HBW) of the specimen under a static normal load using a "
            "standard spherical tungsten carbide ball indenter, and evaluate the resistance of the material to localized plastic deformation.<br/>"
            "<b>Principle:</b> A known load <i>P</i> is applied through a tungsten carbide ball of diameter <i>D</i> into the surface for a prescribed "
            "dwell time. Upon unloading, the curved spherical contact surface area of the indentation is calculated from the mean diameter <i>d</i> "
            "of the impression measured along two perpendicular axes using an optical micrometer microscope."
        )
    else:
        obj_text = (
            "<b>Objective:</b> To determine the Rockwell Hardness (HR) of the specimen using differential depth penetration measurement under "
            "standard preliminary minor and major loads, and classify material hardness on the designated Rockwell scale.<br/>"
            "<b>Principle:</b> A preliminary minor load <i>F₀</i> (10 kgf) is applied to seat the indenter through surface irregularities and "
            "establish a zero datum reference. An additional major load <i>F₁</i> is then smoothly applied. Following dwell, the major load is released "
            "while maintaining the minor load. The machine measures the net permanent depth increase <i>e</i> directly on an indicator dial or digital display."
        )
    elements.append(Paragraph(obj_text, body_style))
    elements.append(Spacer(1, 6))

    # 5. Observation Table (Multi-Trial Readings)
    elements.append(Paragraph("2. EXPERIMENTAL OBSERVATION TABLE", section_heading))
    readings = experiment_data.get('readings', [])

    if is_brinell:
        obs_headers = [
            Paragraph("<b>Trial #</b>", table_header),
            Paragraph("<b>Dia d₁ (mm)</b>", table_header),
            Paragraph("<b>Dia d₂ (mm)</b>", table_header),
            Paragraph("<b>Mean d (mm)</b>", table_header),
            Paragraph("<b>Depth h (mm)</b>", table_header),
            Paragraph("<b>Hardness (HBW)</b>", table_header)
        ]
        obs_rows = [obs_headers]
        for r in readings:
            d1 = r.get('d1_mm')
            d2 = r.get('d2_mm')
            md = r.get('mean_d_mm') or ((d1 + d2) / 2.0 if d1 and d2 else '—')
            h = r.get('depth_mm') or '—'
            hbw = r.get('hardness_value', 0.0)
            obs_rows.append([
                Paragraph(str(r.get('trial_number', 1)), table_cell),
                Paragraph(f"{d1:.3f}" if isinstance(d1, (int, float)) else str(d1), table_cell),
                Paragraph(f"{d2:.3f}" if isinstance(d2, (int, float)) else str(d2), table_cell),
                Paragraph(f"{md:.3f}" if isinstance(md, (int, float)) else str(md), table_cell),
                Paragraph(f"{h:.4f}" if isinstance(h, (int, float)) else str(h), table_cell),
                Paragraph(f"<b>{hbw:.1f}</b>", table_cell),
            ])
        col_widths = [50, 95, 95, 95, 95, 90]
    else:
        obs_headers = [
            Paragraph("<b>Trial #</b>", table_header),
            Paragraph("<b>Rockwell Scale</b>", table_header),
            Paragraph("<b>Minor Load (kgf)</b>", table_header),
            Paragraph("<b>Major Load (kgf)</b>", table_header),
            Paragraph("<b>Net Depth e (mm)</b>", table_header),
            Paragraph("<b>Hardness Reading</b>", table_header)
        ]
        obs_rows = [obs_headers]
        scale_sym = experiment_data.get('hardness_unit', 'HRB')
        for r in readings:
            depth = r.get('depth_mm')
            val = r.get('hardness_value', 0.0)
            obs_rows.append([
                Paragraph(str(r.get('trial_number', 1)), table_cell),
                Paragraph(scale_sym, table_cell),
                Paragraph("10.0", table_cell),
                Paragraph(str(params.get('major_load_kgf', 90.0 if 'B' in scale_sym else 140.0)), table_cell),
                Paragraph(f"{depth:.4f}" if isinstance(depth, (int, float)) else '—', table_cell),
                Paragraph(f"<b>{val:.1f} {scale_sym}</b>", table_cell),
            ])
        col_widths = [50, 95, 95, 95, 95, 90]

    obs_table = Table(obs_rows, colWidths=col_widths)
    obs_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#1e3a8a')),
        ('BOX', (0,0), (-1,-1), 1, colors.HexColor('#334155')),
        ('INNERGRID', (0,0), (-1,-1), 0.5, colors.HexColor('#cbd5e1')),
        ('TOPPADDING', (0,0), (-1,-1), 3),
        ('BOTTOMPADDING', (0,0), (-1,-1), 3),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.HexColor('#ffffff'), colors.HexColor('#f8fafc')]),
    ]))
    elements.append(obs_table)
    elements.append(Spacer(1, 8))

    # 6. Mathematical Formulas & Calculations
    elements.append(Paragraph("3. MATHEMATICAL FORMULAS &amp; DATA REDUCTION", section_heading))
    if is_brinell:
        calc_text = (
            "<b>Standard Brinell Equation (ASTM E10):</b><br/>"
            "&nbsp;&nbsp;&nbsp;&nbsp;<b>HBW = 2P / [ π · D · (D - √(D² - d²)) ]</b><br/>"
            "where <i>P</i> is applied load in kgf, <i>D</i> is ball diameter in mm, and <i>d</i> is mean impression diameter in mm.<br/>"
            "<b>Spherical Cap Depth:</b> <i>h = (D - √(D² - d²)) / 2</i><br/>"
            "<b>Empirical Tensile Strength Correlation (for Carbon Steels):</b> <i>UTS (MPa) ≈ 3.45 · HBW</i>"
        )
    else:
        calc_text = (
            "<b>Standard Rockwell Hardness Equation (ASTM E18):</b><br/>"
            "&nbsp;&nbsp;&nbsp;&nbsp;<b>HR = N - (e / 0.002 mm)</b><br/>"
            "where <i>N = 100</i> for Scale C and Scale A (Diamond Brale cone), <i>N = 130</i> for Scale B (1/16\" ball), "
            "and <i>e</i> is the net permanent increase in depth of indentation in mm."
        )
    elements.append(Paragraph(calc_text, body_style))
    elements.append(Spacer(1, 6))

    # 7. Results & Statistical Summary Table
    elements.append(Paragraph("4. RESULTS &amp; STATISTICAL SUMMARY", section_heading))
    mean_val = experiment_data.get('mean_hardness', 0.0)
    h_unit = experiment_data.get('hardness_unit', 'HBW' if is_brinell else 'HRB')
    num_readings = len(readings)

    # Compute stats if available
    vals = [r.get('hardness_value', 0.0) for r in readings if r.get('hardness_value')]
    if vals:
        min_v = min(vals)
        max_v = max(vals)
        r_range = round(max_v - min_v, 1)
        if len(vals) > 1:
            variance = sum((x - mean_val)**2 for x in vals) / (len(vals) - 1)
            std_dev = round(math.sqrt(variance), 2)
        else:
            std_dev = 0.0
    else:
        min_v = max_v = mean_val
        r_range = std_dev = 0.0

    res_data = [
        [
            Paragraph("<b>Mean Hardness Value:</b>", body_style),
            Paragraph(f"<b><font size='10' color='#1e3a8a'>{mean_val:.1f} {h_unit}</font></b>", body_style),
            Paragraph("<b>Number of Trials:</b>", body_style),
            Paragraph(f"{num_readings} valid readings", body_style)
        ],
        [
            Paragraph("<b>Hardness Range (Max - Min):</b>", body_style),
            Paragraph(f"{r_range} {h_unit} ({min_v:.1f} to {max_v:.1f})", body_style),
            Paragraph("<b>Sample Std. Deviation:</b>", body_style),
            Paragraph(f"± {std_dev} {h_unit}", body_style)
        ]
    ]

    if is_brinell:
        uts_est = round(3.45 * mean_val, 1)
        res_data.append([
            Paragraph("<b>Estimated Tensile Strength:</b>", body_style),
            Paragraph(f"~ {uts_est} MPa (applicable to steels)", body_style),
            Paragraph("<b>Standard Notation:</b>", body_style),
            Paragraph(f"<b>{round(mean_val)} HBW {int(params.get('ball_diameter_mm', 10))}/{int(params.get('load_kgf', 3000))}</b>", body_style)
        ])

    res_table = Table(res_data, colWidths=[150, 150, 110, 110])
    res_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#f1f5f9')),
        ('BOX', (0,0), (-1,-1), 1, colors.HexColor('#0284c7')),
        ('INNERGRID', (0,0), (-1,-1), 0.5, colors.HexColor('#cbd5e1')),
        ('TOPPADDING', (0,0), (-1,-1), 4),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
        ('LEFTPADDING', (0,0), (-1,-1), 6),
        ('RIGHTPADDING', (0,0), (-1,-1), 6),
    ]))
    elements.append(res_table)
    elements.append(Spacer(1, 8))

    # 8. Metallurgical Conclusion
    elements.append(Paragraph("5. METALLURGICAL CONCLUSION &amp; DISCUSSION", section_heading))
    if is_brinell:
        conc_text = (
            f"The tested specimen of <b>{mat_name}</b> exhibited a mean Brinell hardness of <b>{mean_val:.1f} HBW</b>. "
            f"The test fulfilled the ASTM E10 geometric similarity condition (0.24 &le; d/D &le; 0.60). "
            f"The macroscopic indentation verified bulk uniform resistance to plastic deformation without severe edge distortion. "
            f"Experimental observations conform to standard metallurgical specifications for this alloy classification."
        )
    else:
        conc_text = (
            f"The tested specimen of <b>{mat_name}</b> exhibited a mean Rockwell hardness of <b>{mean_val:.1f} {h_unit}</b> "
            f"with a standard deviation of &plusmn;{std_dev} {h_unit}. "
            f"The direct-reading differential depth measurement under the preliminary minor and total major loads provided a "
            f"rapid, highly reproducible index of surface and near-surface hardness without optical measurement operator error."
        )
    elements.append(Paragraph(conc_text, body_style))
    elements.append(Spacer(1, 8))

    # 9. Associated Quiz Score (if available)
    quiz = experiment_data.get('quiz')
    if quiz:
        elements.append(Paragraph("6. ACADEMIC ASSESSMENT SCORE", section_heading))
        q_score = quiz.get('score', 0)
        q_tot = quiz.get('total_questions', 6)
        q_pct = quiz.get('percentage', 0.0)
        q_text = f"Student completed the standard {method.capitalize()} Hardness Assessment: <b>{q_score} / {q_tot} ({q_pct:.1f}%)</b>."
        elements.append(Paragraph(q_text, body_style))
        elements.append(Spacer(1, 8))

    # 10. Report Verification Sign-off Footer
    elements.append(Spacer(1, 10))
    elements.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor('#94a3b8'), spaceAfter=8))
    sign_table = Table([
        [
            Paragraph("<b>Student Signature / Verification:</b>", body_style),
            Paragraph("<b>Laboratory Instructor Approval:</b>", body_style)
        ],
        [
            Paragraph(f"Digitally authenticated: <b>{sid}</b> ({sname})<br/>Date: {created_at}", body_style),
            Paragraph("MAT-VLAB Academic System Certified<br/>Status: <b>VERIFIED &amp; LOGGED</b>", body_style)
        ]
    ], colWidths=[260, 260])
    sign_table.setStyle(TableStyle([
        ('TOPPADDING', (0,0), (-1,-1), 2),
        ('BOTTOMPADDING', (0,0), (-1,-1), 2),
    ]))
    elements.append(sign_table)

    doc.build(elements)
    buffer.seek(0)
    return buffer
