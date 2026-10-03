#!/usr/bin/env python3
"""
generate_atlas_pdf.py
=====================
Generates the publication-grade, detailed institutional proposal PDF for:
ATLAS - AI, Automation & Production Engineering Society (MAIT)
"""

import os
import sys
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, KeepTogether, HRFlowable
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.pdfgen import canvas

class NumberedCanvas(canvas.Canvas):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_page_decorations(num_pages)
            super().showPage()
        super().save()

    def draw_page_decorations(self, page_count):
        self.saveState()
        self.setFont("Helvetica", 8)
        self.setFillColor(colors.HexColor("#64748b"))

        # Skip running header/footer on cover page (page 1)
        if self._pageNumber > 1:
            # Running Header
            self.drawString(54, letter[1] - 36, "ATLAS • AI, Automation & Production Engineering Society | MAIT Proposal")
            self.setStrokeColor(colors.HexColor("#e2e8f0"))
            self.setLineWidth(0.5)
            self.line(54, letter[1] - 42, letter[0] - 54, letter[1] - 42)

            # Running Footer
            self.line(54, 45, letter[0] - 54, 45)
            self.drawString(54, 32, "Confidential • For Institutional & Faculty Review Only")
            page_text = f"Page {self._pageNumber} of {page_count}"
            self.drawRightString(letter[0] - 54, 32, page_text)

        self.restoreState()

print("Canvas helper defined successfully")
