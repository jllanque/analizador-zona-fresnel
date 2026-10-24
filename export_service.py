"""
export_service.py
=================

Servicio para generar informes PDF con los resultados del análisis.
Utiliza reportlab.platypus para una apariencia profesional.
"""

import datetime
import os
import tempfile

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.lib.utils import ImageReader
from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer, Table,
                                TableStyle, Image, PageBreak)


class ExportService:
    @staticmethod
    def _scaled_image(path, max_width, max_height):
        """Imagen escalada conservando la relación de aspecto."""
        img_w, img_h = ImageReader(path).getSize()
        scale = min(max_width / img_w, max_height / img_h)
        img = Image(path, width=img_w * scale, height=img_h * scale)
        img.hAlign = 'CENTER'
        return img

    @staticmethod
    def _build_styles():
        styles = getSampleStyleSheet()
        styles['Title'].fontSize = 16
        styles['Title'].leading = 20
        styles['Title'].alignment = TA_CENTER
        styles['Title'].spaceAfter = 12
        styles['Title'].fontName = 'Helvetica-Bold'

        if 'Subtitle' not in styles:
            styles.add(ParagraphStyle(name='Subtitle', parent=styles['Normal']))
        styles['Subtitle'].fontSize = 12
        styles['Subtitle'].leading = 14
        styles['Subtitle'].alignment = TA_CENTER
        styles['Subtitle'].textColor = colors.grey
        styles['Subtitle'].spaceAfter = 20

        if 'SectionTitle' not in styles:
            styles.add(ParagraphStyle(name='SectionTitle', parent=styles['Normal']))
        styles['SectionTitle'].fontSize = 14
        styles['SectionTitle'].leading = 16
        styles['SectionTitle'].alignment = TA_LEFT
        styles['SectionTitle'].spaceAfter = 10
        styles['SectionTitle'].spaceBefore = 10
        styles['SectionTitle'].fontName = 'Helvetica-Bold'
        return styles

    @staticmethod
    def generate_report(results_data, figure_2d, filepath, figure_3d=None):
        """
        Genera un informe técnico en PDF utilizando platypus.

        Args:
            results_data: dict con los parámetros y resultados del enlace.
            figure_2d: figura matplotlib 2D.
            filepath: ruta del PDF a escribir.
            figure_3d: figura matplotlib 3D opcional.
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_2d = os.path.join(tmpdir, "fig2d.png")
            figure_2d.savefig(tmp_2d, dpi=150, bbox_inches='tight')
            tmp_3d = None
            if figure_3d is not None:
                tmp_3d = os.path.join(tmpdir, "fig3d.png")
                figure_3d.savefig(tmp_3d, dpi=150, bbox_inches='tight')

            doc = SimpleDocTemplate(filepath, pagesize=A4,
                                    rightMargin=2 * cm, leftMargin=2 * cm,
                                    topMargin=2 * cm, bottomMargin=2 * cm)
            styles = ExportService._build_styles()
            story = []

            margin_dB = results_data['margen']
            viable = margin_dB >= 0
            estado = "VIABLE" if viable else "NO VIABLE"
            state_color = colors.green if viable else colors.red

            # ---- Título y fecha ----
            story.append(Paragraph("Reporte de Análisis de Enlace - Fresnel Simulator", styles['Title']))
            story.append(Spacer(1, 0.2 * cm))
            story.append(Paragraph(
                f"Generado el: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
                styles['Subtitle']))
            story.append(Spacer(1, 0.5 * cm))

            # ---- Resumen destacado ----
            resumen_text = (
                f"<b>Resumen:</b> Distancia {results_data['distancia']:.0f} m | "
                f"Frecuencia {results_data['frecuencia']:.2f} GHz | "
                f"Margen {margin_dB:.1f} dB | Enlace {estado}")
            resumen_table = Table([[Paragraph(resumen_text, styles['Normal'])]],
                                  colWidths=[doc.width])
            resumen_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, -1), colors.lightgrey),
                ('BOX', (0, 0), (-1, -1), 0.5, colors.black),
                ('PADDING', (0, 0), (-1, -1), 6),
            ]))
            story.append(resumen_table)
            story.append(Spacer(1, 0.5 * cm))

            # ---- Parámetros del enlace ----
            story.append(Paragraph("Parámetros del Enlace", styles['SectionTitle']))
            params_data = [
                [f"Frecuencia: {results_data['frecuencia']:.2f} GHz",
                 f"Longitud de onda: {results_data['wavelength']:.4f} m"],
                [f"Distancia total: {results_data['distancia']:.0f} m",
                 f"Radio máximo 1ª zona Fresnel: {results_data['fresnel_radius']:.2f} m"],
            ]
            params_table = Table(params_data, colWidths=[doc.width / 2 - 10, doc.width / 2 - 10])
            params_table.setStyle(TableStyle([
                ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 0), (-1, -1), 10),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('LEFTPADDING', (0, 0), (-1, -1), 5),
                ('RIGHTPADDING', (0, 0), (-1, -1), 5),
            ]))
            story.append(params_table)
            story.append(Spacer(1, 0.3 * cm))

            # ---- Alturas de las estaciones ----
            story.append(Paragraph("Alturas de las Estaciones", styles['SectionTitle']))
            alturas_data = [
                [f"TX: edificio = {results_data['tx_building']:.1f} m, "
                 f"antena = {results_data['tx_antenna_extra']:.1f} m, "
                 f"total = {results_data['tx_total']:.1f} m"],
                [f"RX: edificio = {results_data['rx_building']:.1f} m, "
                 f"antena = {results_data['rx_antenna_extra']:.1f} m, "
                 f"total = {results_data['rx_total']:.1f} m"],
            ]
            alturas_table = Table(alturas_data, colWidths=[doc.width])
            alturas_table.setStyle(TableStyle([
                ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 0), (-1, -1), 10),
                ('LEFTPADDING', (0, 0), (-1, -1), 5),
            ]))
            story.append(alturas_table)
            story.append(Spacer(1, 0.3 * cm))

            # ---- Link Budget ----
            story.append(Paragraph("Link Budget", styles['SectionTitle']))
            estado_style = ParagraphStyle(
                name='EstadoCell', parent=styles['Normal'], fontName='Helvetica-Bold',
                fontSize=10, alignment=TA_RIGHT, textColor=state_color)
            lb_data = [
                ["Potencia TX:", f"{results_data['tx_power']:.2f} dBm"],
                ["Ganancia antena TX:", f"{results_data['tx_gain']:.2f} dBi"],
                ["Ganancia antena RX:", f"{results_data['rx_gain']:.2f} dBi"],
                ["Pérdida en espacio libre (FSL):", f"{results_data['fsl']:.2f} dB"],
                ["Pérdida total por difracción:", f"{results_data['total_diff_loss']:.2f} dB"],
                ["Factor por reflexión:", f"{results_data.get('reflection_factor_db', 0):+.2f} dB"],
                ["Potencia recibida:", f"{results_data['potencia_recibida']:.2f} dBm"],
                ["Sensibilidad del receptor:", f"{results_data['rx_sensitivity']:.1f} dBm"],
                ["Margen:", f"{margin_dB:.2f} dB"],
                ["Estado:", Paragraph(estado, estado_style)],
            ]
            margin_row = len(lb_data) - 2
            estado_row = len(lb_data) - 1
            lb_table = Table(lb_data, colWidths=[doc.width * 0.6, doc.width * 0.4])
            lb_table.setStyle(TableStyle([
                ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 0), (-1, -1), 10),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('LEFTPADDING', (0, 0), (-1, -1), 5),
                ('RIGHTPADDING', (0, 0), (-1, -1), 5),
                ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
                ('FONTNAME', (1, margin_row), (1, margin_row), 'Helvetica-Bold'),
                ('TEXTCOLOR', (1, margin_row), (1, margin_row), state_color),
            ]))
            story.append(lb_table)
            story.append(Spacer(1, 0.3 * cm))

            # ---- Obstáculos ----
            if results_data.get('obstaculos'):
                story.append(Paragraph("Obstáculos", styles['SectionTitle']))
                table_data = [["Nombre", "Pos (m)", "Alt (m)", "Despeje (r1)", "Estado", "Pérd (dB)"]]
                for obs in results_data['obstaculos']:
                    nombre = obs.name[:17] + "..." if len(obs.name) > 20 else obs.name
                    ratio = obs.clearance_ratio
                    ratio_txt = "inf" if ratio in (float("inf"), float("-inf")) else f"{ratio:.2f}"
                    table_data.append([nombre, f"{obs.position:.1f}", f"{obs.height:.1f}",
                                       ratio_txt, obs.state, f"{obs.diffraction_loss_db:.1f}"])
                col_widths = [doc.width * 0.28, doc.width * 0.12, doc.width * 0.12,
                              doc.width * 0.16, doc.width * 0.16, doc.width * 0.16]
                obst_table = Table(table_data, colWidths=col_widths, repeatRows=1)
                obst_table.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                    ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                    ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                    ('ALIGN', (0, 0), (0, -1), 'LEFT'),
                    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                    ('FONTSIZE', (0, 0), (-1, 0), 10),
                    ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
                    ('FONTSIZE', (0, 1), (-1, -1), 9),
                    ('BOTTOMPADDING', (0, 0), (-1, 0), 6),
                    ('TOPPADDING', (0, 0), (-1, 0), 6),
                    ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
                    ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.lightgrey]),
                ]))
                story.append(obst_table)
                story.append(Spacer(1, 0.5 * cm))

            # ---- Gráficas ----
            story.append(PageBreak())
            story.append(Paragraph("Gráficas del Enlace", styles['SectionTitle']))
            story.append(Spacer(1, 0.2 * cm))

            max_h = 11 * cm
            story.append(ExportService._scaled_image(tmp_2d, doc.width, max_h))
            story.append(Spacer(1, 0.2 * cm))
            story.append(Paragraph("Figura 1: Perfil del enlace y zonas de Fresnel (vista 2D)",
                                   styles['Subtitle']))
            story.append(Spacer(1, 0.5 * cm))

            if tmp_3d:
                story.append(ExportService._scaled_image(tmp_3d, doc.width, max_h))
                story.append(Spacer(1, 0.2 * cm))
                story.append(Paragraph("Figura 2: Vista 3D del radioenlace", styles['Subtitle']))

            # El PDF se construye dentro del with: las imágenes temporales aún existen
            doc.build(story)
