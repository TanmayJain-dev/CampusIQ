import sys
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

print(f"Letter page: {letter[0]} x {letter[1]} pt")
print(f"Usable width with 46pt margins: {letter[0] - 92} pt")
print(f"Usable height with 42pt margins: {letter[1] - 84} pt")
