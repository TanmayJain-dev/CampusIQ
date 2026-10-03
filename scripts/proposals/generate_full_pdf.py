import sys
import os

code = """#!/usr/bin/env python3
import os
import sys
import shutil
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, KeepTogether, HRFlowable
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.pdfgen import canvas

PDF_PATH = "/home/tanmay/Workspaces/Projects/CampusIQ/ATLAS_MAIT_Proposal.pdf"
ARTIFACT_PATH = "/home/tanmay/.gemini/antigravity-cli/brain/89ca3f0c-6cac-404d-96d8-2e775c23413c/ATLAS_MAIT_Proposal.pdf"

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
        self.setFont("Helvetica-Bold", 8)
        self.setFillColor(colors.HexColor("#475569"))

        # Skip running header/footer on cover page (page 1)
        if self._pageNumber > 1:
            # Header
            self.drawString(44, letter[1] - 26, "ATLAS • AI, AUTOMATION & PRODUCTION ENGINEERING SOCIETY | MAIT")
            self.drawRightString(letter[0] - 44, letter[1] - 26, "INSTITUTIONAL PROPOSAL")
            self.setStrokeColor(colors.HexColor("#94a3b8"))
            self.setLineWidth(0.6)
            self.line(44, letter[1] - 31, letter[0] - 44, letter[1] - 31)

            # Footer
            self.setStrokeColor(colors.HexColor("#cbd5e1"))
            self.setLineWidth(0.5)
            self.line(44, 31, letter[0] - 44, 31)
            self.setFont("Helvetica", 7.5)
            self.drawString(44, 21, "Maharaja Agrasen Institute of Technology • Department of Computer Science & Engineering")
            page_text = f"Page {self._pageNumber} of {page_count}"
            self.setFont("Helvetica-Bold", 7.5)
            self.drawRightString(letter[0] - 44, 21, page_text)

        self.restoreState()
"""

print("Base script setup ready")
