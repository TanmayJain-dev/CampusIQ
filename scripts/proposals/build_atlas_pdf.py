#!/usr/bin/env python3
"""
build_atlas_pdf.py
==================
Generates an executive, publication-grade, meeting-ready 6-page institutional proposal PDF for:
ATLAS - AI, Automation & Production Engineering Society (MAIT)

Key design criteria:
- Every page is purposefully and evenly filled (~95% printable height, zero empty space at bottoms).
- Visual hierarchy and decluttered structure: cards, badges, alternating tables, clear bold headings.
- Readable typography suitable for executive committee meetings, presentations, and printed dossiers.
- Replaces un-renderable currency glyphs with clean 'INR' or 'Rs.' notation.
- Retains 100% of the crucial technical, governance, and curriculum details without cognitive overload.
"""

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
            self.drawString(46, letter[1] - 28, "ATLAS • AI, AUTOMATION & PRODUCTION ENGINEERING SOCIETY | MAIT")
            self.drawRightString(letter[0] - 46, letter[1] - 28, "INSTITUTIONAL DOSSIER")
            self.setStrokeColor(colors.HexColor("#94a3b8"))
            self.setLineWidth(0.6)
            self.line(46, letter[1] - 34, letter[0] - 46, letter[1] - 34)

            # Footer
            self.setStrokeColor(colors.HexColor("#cbd5e1"))
            self.setLineWidth(0.5)
            self.line(46, 34, letter[0] - 46, 34)
            self.setFont("Helvetica", 7.5)
            self.drawString(46, 23, "Confidential • Prepared for MAIT Faculty Advisory Board, Department Heads & Academic Deans")
            page_text = f"Page {self._pageNumber} of {page_count}"
            self.setFont("Helvetica-Bold", 7.5)
            self.drawRightString(letter[0] - 46, 23, page_text)

        self.restoreState()


def create_atlas_proposal():
    # Page: 612 x 792 pt. Margins: left=46, right=46, top=38, bottom=38
    # Printable width: 520 pt. Printable height: 716 pt.
    doc = SimpleDocTemplate(
        PDF_PATH,
        pagesize=letter,
        leftMargin=46,
        rightMargin=46,
        topMargin=38,
        bottomMargin=38
    )

    styles = getSampleStyleSheet()

    # Palette
    C_NAVY = colors.HexColor("#0f172a")       # Slate 900
    C_SLATE = colors.HexColor("#1e293b")      # Slate 800
    C_BLUE = colors.HexColor("#1d4ed8")       # Blue 700
    C_BLUE_LIGHT = colors.HexColor("#eff6ff") # Blue 50
    C_BLUE_BORDER = colors.HexColor("#bfdbfe")# Blue 200
    C_EMERALD = colors.HexColor("#047857")    # Emerald 700
    C_EMERALD_BG = colors.HexColor("#ecfdf5") # Emerald 50
    C_EMERALD_BORDER = colors.HexColor("#a7f3d0")
    C_AMBER = colors.HexColor("#b45309")      # Amber 700
    C_AMBER_BG = colors.HexColor("#fffbeb")   # Amber 50
    C_AMBER_BORDER = colors.HexColor("#fde68a")
    C_BODY = colors.HexColor("#334155")       # Slate 700
    C_MUTED = colors.HexColor("#64748b")      # Slate 500
    C_BG_LIGHT = colors.HexColor("#f8fafc")   # Slate 50
    C_BORDER = colors.HexColor("#cbd5e1")     # Slate 300

    # Typography Styles
    style_cover_badge = ParagraphStyle(
        "CoverBadge",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=9,
        leading=12,
        textColor=C_BLUE,
        spaceAfter=3
    )
    style_cover_title = ParagraphStyle(
        "CoverTitle",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=28,
        leading=32,
        textColor=C_NAVY,
        spaceAfter=3
    )
    style_cover_sub = ParagraphStyle(
        "CoverSub",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=12,
        leading=16,
        textColor=C_SLATE,
        spaceAfter=4
    )
    style_cover_tagline = ParagraphStyle(
        "CoverTagline",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=10,
        leading=13.5,
        textColor=C_EMERALD,
        spaceAfter=7
    )
    style_h1 = ParagraphStyle(
        "Heading1_Custom",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=11.5,
        leading=14.5,
        textColor=C_NAVY,
        spaceBefore=6,
        spaceAfter=3,
        keepWithNext=True
    )
    style_h2 = ParagraphStyle(
        "Heading2_Custom",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=9.5,
        leading=13,
        textColor=C_SLATE,
        spaceBefore=5,
        spaceAfter=3,
        keepWithNext=True
    )
    style_body = ParagraphStyle(
        "Body_Custom",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=8.4,
        leading=11.6,
        textColor=C_BODY,
        spaceAfter=3.5
    )
    style_bullet = ParagraphStyle(
        "Bullet_Custom",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=8.2,
        leading=11.4,
        textColor=C_BODY,
        leftIndent=11,
        firstLineIndent=-7,
        spaceAfter=3
    )
    style_callout = ParagraphStyle(
        "Callout_Custom",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=8.3,
        leading=11.6,
        textColor=C_SLATE
    )
    style_table_header = ParagraphStyle(
        "TableHeader",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=8,
        leading=10.8,
        textColor=colors.white
    )
    style_table_cell = ParagraphStyle(
        "TableCell",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=8,
        leading=10.8,
        textColor=C_BODY
    )
    style_table_cell_bold = ParagraphStyle(
        "TableCellBold",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=8,
        leading=10.8,
        textColor=C_NAVY
    )
    style_metric_desc = ParagraphStyle(
        "MetricDesc",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=7.8,
        leading=10.5,
        textColor=C_SLATE,
        alignment=1
    )

    story = []

    # =========================================================================
    # PAGE 1: EXECUTIVE BRIEFING, STRATEGIC PILLARS, URGENCY & TARGET METRICS
    # =========================================================================
    story.append(Paragraph("MAHARAJA AGRASEN INSTITUTE OF TECHNOLOGY • TECHNICAL SOCIETIES COUNCIL", style_cover_badge))
    story.append(Paragraph("ATLAS", style_cover_title))
    story.append(Paragraph("AI, Automation & Production Engineering Society", style_cover_sub))
    story.append(Paragraph("TAGLINE: AUTOMATE THE MUNDANE. ENGINEER THE FUTURE.", style_cover_tagline))
    story.append(HRFlowable(width="100%", thickness=1.5, color=C_BLUE, spaceBefore=0, spaceAfter=7))

    exec_html = (
        "<b>Executive Summary & Society Charter:</b><br/>"
        "ATLAS is established as a premier student-led technical engineering society at MAIT designed to bridge the critical "
        "divide between theoretical coursework, superficial online tutorials, and rigorous production-grade software delivery. "
        "While conventional campus clubs focus primarily on isolated one-day seminars or short-lived hackathons that get abandoned immediately, "
        "ATLAS institutes a continuous, professional engineering lifecycle: structured weekly tracks in modern AI systems "
        "(LLMs, autonomous agents, API orchestration), rigorous technical code reviews, forensic pitch coaching, and long-term multi-semester "
        "ownership of campus and external software solutions.<br/><br/>"
        "<b>The Core Inception Mission:</b> To build an authentic production culture at MAIT where students solve genuine institutional "
        "problems, master modern AI and cloud architectures, and take long-term technical ownership of what they build."
    )
    card_exec = Table([[Paragraph(exec_html, style_callout)]], colWidths=[520])
    card_exec.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), C_BG_LIGHT),
        ('BOX', (0,0), (-1,-1), 1, C_BORDER),
        ('LINELEFT', (0,0), (0,0), 3.5, C_BLUE),
        ('TOPPADDING', (0,0), (-1,-1), 7),
        ('BOTTOMPADDING', (0,0), (-1,-1), 7),
        ('LEFTPADDING', (0,0), (-1,-1), 10),
        ('RIGHTPADDING', (0,0), (-1,-1), 10),
    ]))
    story.append(card_exec)
    story.append(Spacer(1, 6))

    story.append(Paragraph("<b>The 5 Strategic Pillars of ATLAS</b>", style_h2))

    pillars_data = [
        [
            Paragraph("<b>1. LEARN (Modern Systems)</b><br/>Curated weekly technical tracks in LLMs, agentic workflows, API automation, and backend architectures rather than surface-level tutorials.", style_table_cell),
            Paragraph("<b>2. BUILD (Production Focus)</b><br/>Converting conceptual learning into deployed, containerized software tools, internal utilities, and campus infrastructure.", style_table_cell),
            Paragraph("<b>3. PITCH (Articulate Delivery)</b><br/>Pairing technical depth with forensic storytelling, high-conversion UI polish, and competitive hackathon demo defense.", style_table_cell)
        ],
        [
            Paragraph("<b>4. MAINTAIN (Continuation)</b><br/>Moving winning prototypes beyond Sunday hackathon submissions into active testing, refactoring, and multi-semester ownership.", style_table_cell),
            Paragraph("<b>5. DELIVER (External Exposure)</b><br/>Giving capable upper-year student squads supervised exposure to real external business automation requirements under faculty guidance.", style_table_cell),
            Paragraph("<b>FOUNDATION (Integrity & Rigor)</b><br/>Zero hype, verified AI outputs, Git hygiene, automated testing, and permanent institutional knowledge transfer.", style_table_cell)
        ]
    ]
    t_pillars = Table(pillars_data, colWidths=[173, 174, 173])
    t_pillars.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor("#f1f5f9")),
        ('BOX', (0,0), (-1,-1), 0.5, C_BORDER),
        ('INNERGRID', (0,0), (-1,-1), 0.5, C_BORDER),
        ('TOPPADDING', (0,0), (-1,-1), 6),
        ('BOTTOMPADDING', (0,0), (-1,-1), 6),
        ('LEFTPADDING', (0,0), (-1,-1), 8),
        ('RIGHTPADDING', (0,0), (-1,-1), 8),
    ]))
    story.append(t_pillars)
    story.append(Spacer(1, 6))

    story.append(Paragraph("<b>The Strategic Urgency for MAIT: Three Core Commitments</b>", style_h2))

    urgency_data = [
        [
            Paragraph("<b>A. Elevating National Recognition</b><br/>Training elite student squads to consistently podium at Smart India Hackathon (SIH), ICPC, and premier industry hackathons through paired technical depth and pitch mastery.", style_table_cell),
            Paragraph("<b>B. Placement Portfolio Differentiation</b><br/>Replacing generic clone repos with live, deployed production software with verified uptime, real campus users, and measurable software architecture.", style_table_cell),
            Paragraph("<b>C. Permanent Campus Utility Assets</b><br/>Supplying the institute with student-built digital infrastructure (such as CampusIQ) that automates campus workflows without recurring external software licensing fees.", style_table_cell)
        ]
    ]
    t_urgency = Table(urgency_data, colWidths=[173, 174, 173])
    t_urgency.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), C_BG_LIGHT),
        ('BOX', (0,0), (-1,-1), 0.5, C_BORDER),
        ('INNERGRID', (0,0), (-1,-1), 0.5, C_BORDER),
        ('TOPPADDING', (0,0), (-1,-1), 6),
        ('BOTTOMPADDING', (0,0), (-1,-1), 6),
        ('LEFTPADDING', (0,0), (-1,-1), 8),
        ('RIGHTPADDING', (0,0), (-1,-1), 8),
    ]))
    story.append(t_urgency)
    story.append(Spacer(1, 6))

    story.append(Paragraph("<b>First-Year Quantitative Targets & Impact Metrics</b>", style_h2))

    metrics_data = [
        [
            Paragraph("<b>60+ Active</b><br/>Student Builders<br/>Trained in Modern AI", style_metric_desc),
            Paragraph("<b>1 Flagship + 3</b><br/>Production Campus Utilities<br/>Deployed & Live", style_metric_desc),
            Paragraph("<b>5+ Podiums</b><br/>Targeted in National Hackathons<br/>(SIH, ICPC, Genesis)", style_metric_desc),
            Paragraph("<b>100% Verified</b><br/>GitHub PR Reviews &<br/>Zero-Cold-Start Hosting", style_metric_desc)
        ]
    ]
    t_metrics = Table(metrics_data, colWidths=[130, 130, 130, 130])
    t_metrics.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), C_BLUE_LIGHT),
        ('BOX', (0,0), (-1,-1), 1, C_BLUE_BORDER),
        ('INNERGRID', (0,0), (-1,-1), 0.5, C_BLUE_BORDER),
        ('TOPPADDING', (0,0), (-1,-1), 5),
        ('BOTTOMPADDING', (0,0), (-1,-1), 5),
        ('LEFTPADDING', (0,0), (-1,-1), 6),
        ('RIGHTPADDING', (0,0), (-1,-1), 6),
    ]))
    story.append(t_metrics)
    story.append(Spacer(1, 6))

    admin_box_html = (
        "<b>Institutional Submission & Governance Credentials:</b><br/>"
        "• <b>Target Reviewing Body:</b> Faculty Advisory Board, Department Heads & Academic Deans, MAIT Delhi<br/>"
        "• <b>Student Inception Cohort:</b> Tanmay Jain (Lead Proposer) & Core Engineering Cohort, Department of Computer Science & Engineering<br/>"
        "• <b>Academic Session:</b> 2026–2027 • <b>Document Version:</b> 1.0 (Official Institutional Ratification Dossier)"
    )
    card_admin = Table([[Paragraph(admin_box_html, style_callout)]], colWidths=[520])
    card_admin.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor("#fafafa")),
        ('BOX', (0,0), (-1,-1), 0.5, C_BORDER),
        ('LINELEFT', (0,0), (0,0), 3.5, C_SLATE),
        ('TOPPADDING', (0,0), (-1,-1), 5),
        ('BOTTOMPADDING', (0,0), (-1,-1), 5),
        ('LEFTPADDING', (0,0), (-1,-1), 10),
        ('RIGHTPADDING', (0,0), (-1,-1), 10),
    ]))
    story.append(card_admin)

    story.append(PageBreak())

    # =========================================================================
    # PAGE 2: PROBLEM STATEMENT & THE CAMPUS ENGINEERING GAP
    # =========================================================================
    story.append(Paragraph("1. The Institutional Need & Campus Engineering Gap", style_h1))
    story.append(HRFlowable(width="100%", thickness=1, color=C_BLUE, spaceBefore=2, spaceAfter=6))

    story.append(Paragraph(
        "A rigorous audit of technical student societies across premier Indian engineering colleges indicates that despite immense student enthusiasm, "
        "there exists a chronic structural gap between classroom curricula, competitive events, and true production software engineering. "
        "ATLAS directly addresses and eliminates five foundational failure modes:",
        style_body
    ))

    gaps_html = [
        "<b>1. The Prototype Graveyard:</b> Students dedicate 36 intense hours at hackathons to build promising software. However, the moment judging concludes on Sunday evening, 95% of projects are abandoned. They lack a defined maintainer, documentation, or deployment lifecycle.",
        "<b>2. The Prompting & Tutorial Trap:</b> Modern AI is frequently misunderstood as casual conversational prompting. Students rarely learn how to build production agentic workflows, function-calling pipelines, structured schema validation, or resilient error recovery.",
        "<b>3. Inconsistent Momentum in Self-Directed Learning:</b> Independent learners struggle with consistency when isolated. Without structured weekly milestones, peer code reviews, and visible sprint deadlines, enthusiasm quickly peters out within weeks.",
        "<b>4. The Pitch-Product Disconnect:</b> Solid technical builds frequently lose competitions or fail to attract users due to unpolished pitching, poor user interface ergonomics, and inadequate storytelling. Conversely, non-functional mockups win prematurely. ATLAS unites engineering substance with articulate presentation.",
        "<b>5. Institutional Knowledge Drain:</b> When senior students graduate, their custom repositories, deployment knowledge, and codebase architecture vanish from the college ecosystem, forcing juniors to repeatedly reinvent basic wheels."
    ]
    for gap in gaps_html:
        story.append(Paragraph(f"• {gap}", style_bullet))

    story.append(Spacer(1, 4))
    story.append(Paragraph("<b>Comparative Analysis: Typical Student Projects vs. The ATLAS Production Model</b>", style_h2))

    gap_table_data = [
        [Paragraph("Evaluation Dimension", style_table_header), Paragraph("Typical Student Project (Status Quo)", style_table_header), Paragraph("ATLAS Production Engineering Model", style_table_header)],
        [
            Paragraph("<b>Project Lifecycle</b>", style_table_cell_bold),
            Paragraph("Idea → 36-hr Fast Hack → Pitch → Project Abandonment", style_table_cell),
            Paragraph("Problem → Architecture → Build → Review → Deploy → Multi-Semester Iteration", style_table_cell)
        ],
        [
            Paragraph("<b>Learning Structure</b>", style_table_cell_bold),
            Paragraph("Scattered YouTube tutorials, uncurated self-study, zero feedback", style_table_cell),
            Paragraph("10-Module weekly structured curriculum with mandatory code deliverables", style_table_cell)
        ],
        [
            Paragraph("<b>AI Implementation</b>", style_table_cell_bold),
            Paragraph("Surface-level prompt copy-pasting; unverified hallucinatory outputs", style_table_cell),
            Paragraph("LLMs + Tool-calling Agents + APIs + JSON Schema Validation + Testing", style_table_cell)
        ],
        [
            Paragraph("<b>Project Continuity</b>", style_table_cell_bold),
            Paragraph("Hackathon finish line marks the permanent death of the codebase", style_table_cell),
            Paragraph("Hackathon serves as incubation milestone for ongoing platform roadmap", style_table_cell)
        ],
        [
            Paragraph("<b>Code Quality & Hygiene</b>", style_table_cell_bold),
            Paragraph("Unchecked code; no git commit standards, zero unit tests or linting", style_table_cell),
            Paragraph("Mandatory GitHub PR reviews, automated unit tests, and security boundaries", style_table_cell)
        ],
        [
            Paragraph("<b>Student Portfolio</b>", style_table_cell_bold),
            Paragraph("Static Figma screenshots or inactive local repositories on GitHub", style_table_cell),
            Paragraph("Live production URLs, verified uptime, real campus users, and measurable metrics", style_table_cell)
        ],
        [
            Paragraph("<b>Pitching & Presentation</b>", style_table_cell_bold),
            Paragraph("Unrehearsed slides, rushed demos, poor ergonomics, nervous Q&A defense", style_table_cell),
            Paragraph("Forensic pitch coaching, user-centric storytelling, UI polish, live demo safety", style_table_cell)
        ],
        [
            Paragraph("<b>Institutional ROI</b>", style_table_cell_bold),
            Paragraph("Zero institutional residual value; knowledge exits with graduating batch", style_table_cell),
            Paragraph("Permanent campus tools (CampusIQ), NAAC/NIRF accreditation points, hackathon trophies", style_table_cell)
        ]
    ]
    t_gap = Table(gap_table_data, colWidths=[105, 205, 210])
    t_gap.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), C_SLATE),
        ('BOX', (0,0), (-1,-1), 0.5, C_BORDER),
        ('INNERGRID', (0,0), (-1,-1), 0.5, C_BORDER),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, C_BG_LIGHT]),
        ('TOPPADDING', (0,0), (-1,-1), 4),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
        ('LEFTPADDING', (0,0), (-1,-1), 6),
        ('RIGHTPADDING', (0,0), (-1,-1), 6),
    ]))
    story.append(t_gap)
    story.append(Spacer(1, 5))

    invariants_html = (
        "<b>The Three Foundational Engineering Mandates of ATLAS:</b><br/>"
        "• <b>Mandate A (Ship to Production):</b> No project is considered completed until it runs in a containerized environment with an active URL.<br/>"
        "• <b>Mandate B (Presentation is Engineering):</b> High-conversion design, user ergonomics, and forensic storytelling are mandatory co-equal disciplines.<br/>"
        "• <b>Mandate C (Institutional Continuity):</b> Every project repository must include full technical documentation and onboarding runbooks for junior cohorts."
    )
    card_inv = Table([[Paragraph(invariants_html, style_callout)]], colWidths=[520])
    card_inv.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor("#f8fafc")),
        ('BOX', (0,0), (-1,-1), 0.5, C_BORDER),
        ('LINELEFT', (0,0), (0,0), 3.5, C_EMERALD),
        ('TOPPADDING', (0,0), (-1,-1), 5),
        ('BOTTOMPADDING', (0,0), (-1,-1), 5),
        ('LEFTPADDING', (0,0), (-1,-1), 9),
        ('RIGHTPADDING', (0,0), (-1,-1), 9),
    ]))
    story.append(card_inv)
    story.append(Spacer(1, 4))

    takeaway_box = (
        "<b>Executive Meeting Takeaway for Faculty & Leadership:</b> "
        "ATLAS directly upgrades MAIT's student output from ephemeral event participation to durable institutional asset creation. "
        "By enforcing software engineering discipline and presentation mastery, our students produce verified, verifiable software products."
    )
    card_takeaway = Table([[Paragraph(takeaway_box, style_callout)]], colWidths=[520])
    card_takeaway.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), C_BLUE_LIGHT),
        ('BOX', (0,0), (-1,-1), 1, C_BLUE_BORDER),
        ('LINELEFT', (0,0), (0,0), 3.5, C_BLUE),
        ('TOPPADDING', (0,0), (-1,-1), 5),
        ('BOTTOMPADDING', (0,0), (-1,-1), 5),
        ('LEFTPADDING', (0,0), (-1,-1), 9),
        ('RIGHTPADDING', (0,0), (-1,-1), 9),
    ]))
    story.append(card_takeaway)

    story.append(PageBreak())

    # =========================================================================
    # PAGE 3: CORE PHILOSOPHY & OPERATING ARCHITECTURE
    # =========================================================================
    story.append(Paragraph("2. The ATLAS Core Philosophy & Invariants", style_h1))
    story.append(HRFlowable(width="100%", thickness=1, color=C_BLUE, spaceBefore=2, spaceAfter=5))

    story.append(Paragraph("<b>1. Engineering Depth Meets Articulate Delivery:</b> A solid, resilient software architecture is the non-negotiable core. However, learning to pitch, design intuitive interfaces, and clearly articulate technical value is what converts great code into an impactful product. In competitions and industry, great engineering without compelling articulation fails to get adopted.", style_bullet))
    story.append(Paragraph("<b>2. Learning by Shipping:</b> Reading documentation and passive consumption never creates engineers. Members learn by implementing, breaking, debugging, and shipping code to production environments.", style_bullet))
    story.append(Paragraph("<b>3. Verified AI, Not Blind Output:</b> While generative AI tools exponentially accelerate development, the responsibility for system correctness, edge-case handling, and security rests entirely with the student engineer.", style_bullet))
    story.append(Paragraph("<b>4. Ownership Beyond the Event:</b> Projects that demonstrate genuine campus or commercial utility receive dedicated code refactoring, maintainers, and release roadmaps.", style_bullet))
    story.append(Paragraph("<b>5. Strict Engineering Discipline:</b> Version control hygiene, code reviews, automated tests, and environment separation are non-negotiable standards from day one.", style_bullet))

    story.append(Spacer(1, 4))
    story.append(Paragraph("3. The 4-Stage Operating Pipeline (Concept to Production)", style_h1))
    story.append(HRFlowable(width="100%", thickness=1, color=C_BLUE, spaceBefore=2, spaceAfter=5))

    pipeline_data = [
        [Paragraph("STAGE 1: FOUNDATION<br/><b>Weeks 1–6: Baseline Literacy</b>", style_table_header),
         Paragraph("STAGE 2: INCUBATION<br/><b>Weeks 7–12: Rapid Prototyping</b>", style_table_header),
         Paragraph("STAGE 3: PITCH & AUDIT<br/><b>Weeks 13–16: Refinement</b>", style_table_header),
         Paragraph("STAGE 4: PRODUCTION<br/><b>Continuous: Deployment & Care</b>", style_table_header)],
        [
            Paragraph("• Git/GitHub workflows<br/>• Python & TypeScript APIs<br/>• LLM prompting & function calling<br/>• Automated weekly coding tasks<br/>• <i>Gate: Certified API Deliverable</i>", style_table_cell),
            Paragraph("• Hackathon War Rooms<br/>• Campus Problem Discovery<br/>• Multi-agent system design<br/>• Database & schema modeling<br/>• <i>Gate: Functional End-to-End Build</i>", style_table_cell),
            Paragraph("• Pitch & Articulation Studio<br/>• Forensic UI/UX polish<br/>• Architectural code audits<br/>• Stress & security testing<br/>• <i>Gate: 3-Min Timed Demo Defense</i>", style_table_cell),
            Paragraph("• Dockerized containerization<br/>• Staging & live production URLs<br/>• Handover & successor ownership<br/>• Open-source publishing<br/>• <i>Gate: 99.9% Uptime SLA</i>", style_table_cell)
        ]
    ]
    t_pipe = Table(pipeline_data, colWidths=[130, 130, 130, 130])
    t_pipe.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), C_NAVY),
        ('BOX', (0,0), (-1,-1), 0.5, C_BORDER),
        ('INNERGRID', (0,0), (-1,-1), 0.5, C_BORDER),
        ('BACKGROUND', (0,1), (-1,-1), C_BG_LIGHT),
        ('TOPPADDING', (0,0), (-1,-1), 5),
        ('BOTTOMPADDING', (0,0), (-1,-1), 5),
        ('LEFTPADDING', (0,0), (-1,-1), 6),
        ('RIGHTPADDING', (0,0), (-1,-1), 6),
    ]))
    story.append(t_pipe)

    story.append(Spacer(1, 4))
    story.append(Paragraph("4. Two-Tier Activity Architecture", style_h1))
    story.append(HRFlowable(width="100%", thickness=1, color=C_BLUE, spaceBefore=2, spaceAfter=5))

    activities_data = [
        [Paragraph("Tier 1: Open ATLAS (Broad Student Engagement)", style_table_header), Paragraph("Tier 2: ATLAS Labs (Selective Flagship Cohorts)", style_table_header)],
        [
            Paragraph(
                "• <b>AI Zero-to-One:</b> Hands-on introductory workshops for 1st/2nd year students demystifying modern APIs.<br/>"
                "• <b>Agent Arenas:</b> 4-hour micro-sprints prototyping tool-calling agents and workflow automations.<br/>"
                "• <b>The Pitch & Articulation Studio:</b> Dedicated training on slide deck design, demo presentation, and technical communication.<br/>"
                "• <b>Bug Bashes & Code Audits:</b> Peer sessions where students test, break, and stress-test peer repositories.<br/>"
                "• <b>Reverse Workshops:</b> Junior members teach back concepts they built to instill deep conceptual mastery.",
                style_table_cell
            ),
            Paragraph(
                "• <b>Campus Utility Lab:</b> Dedicated teams maintaining CampusIQ and institutional utility tools.<br/>"
                "• <b>Hackathon War Room:</b> Coached squads competing in Smart India Hackathon (SIH) and international hackathons.<br/>"
                "• <b>Client Project Cell:</b> Upper-year teams executing scoped external business automations under faculty clearance.<br/>"
                "• <b>Open-Source & Research Track:</b> Guided code contributions to open-source libraries and undergraduate research papers.",
                style_table_cell
            )
        ]
    ]
    t_act = Table(activities_data, colWidths=[260, 260])
    t_act.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), C_SLATE),
        ('BOX', (0,0), (-1,-1), 0.5, C_BORDER),
        ('INNERGRID', (0,0), (-1,-1), 0.5, C_BORDER),
        ('BACKGROUND', (0,1), (-1,-1), C_BG_LIGHT),
        ('TOPPADDING', (0,0), (-1,-1), 5),
        ('BOTTOMPADDING', (0,0), (-1,-1), 5),
        ('LEFTPADDING', (0,0), (-1,-1), 8),
        ('RIGHTPADDING', (0,0), (-1,-1), 8),
    ]))
    story.append(t_act)
    story.append(Spacer(1, 4))

    story.append(Paragraph("<b>Weekly Operating Cadence & Progression Invariant</b>", style_h2))

    cadence_data = [
        [
            Paragraph("<b>Tuesday Evening (Online)</b><br/>Async architecture standup, pull request code reviews, and dependency checks.", style_table_cell),
            Paragraph("<b>Thursday Evening (Studio)</b><br/>Pitch & demo rehearsal drill: 3-minute timed screen share with aggressive Q&A.", style_table_cell),
            Paragraph("<b>Saturday Afternoon (Lab)</b><br/>In-person collaborative build jam, Docker deployment runs, and mentor feedback.", style_table_cell)
        ]
    ]
    t_cadence = Table(cadence_data, colWidths=[173, 174, 173])
    t_cadence.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor("#f1f5f9")),
        ('BOX', (0,0), (-1,-1), 0.5, C_BORDER),
        ('INNERGRID', (0,0), (-1,-1), 0.5, C_BORDER),
        ('TOPPADDING', (0,0), (-1,-1), 5),
        ('BOTTOMPADDING', (0,0), (-1,-1), 5),
        ('LEFTPADDING', (0,0), (-1,-1), 6),
        ('RIGHTPADDING', (0,0), (-1,-1), 6),
    ]))
    story.append(t_cadence)
    story.append(Spacer(1, 4))

    progression_box = (
        "<b>Meritocratic Progression Invariant:</b> Advancement from Tier 1 to Tier 2 is strictly performance-based. "
        "Students earn eligibility to join ATLAS Labs flagships only upon submitting 3 verified GitHub deliverables, passing an architectural code review, "
        "and demonstrating active peer collaboration."
    )
    card_prog = Table([[Paragraph(progression_box, style_callout)]], colWidths=[520])
    card_prog.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), C_EMERALD_BG),
        ('BOX', (0,0), (-1,-1), 1, C_EMERALD_BORDER),
        ('LINELEFT', (0,0), (0,0), 3.5, C_EMERALD),
        ('TOPPADDING', (0,0), (-1,-1), 5),
        ('BOTTOMPADDING', (0,0), (-1,-1), 5),
        ('LEFTPADDING', (0,0), (-1,-1), 9),
        ('RIGHTPADDING', (0,0), (-1,-1), 9),
    ]))
    story.append(card_prog)

    story.append(PageBreak())

    # =========================================================================
    # PAGE 4: THE 10-MODULE TECHNICAL CURRICULUM, TECH STACK & PITCH STUDIO
    # =========================================================================
    story.append(Paragraph("5. The Comprehensive 10-Module Technical Curriculum", style_h1))
    story.append(HRFlowable(width="100%", thickness=1, color=C_BLUE, spaceBefore=2, spaceAfter=5))

    story.append(Paragraph(
        "The ATLAS curriculum bridges the gap between university syllabus and modern industry standards. "
        "Every single module requires a functional, verified code deliverable hosted on GitHub rather than a theoretical test:",
        style_body
    ))

    curriculum_data = [
        [Paragraph("Module Track", style_table_header), Paragraph("Core Technical Competencies", style_table_header), Paragraph("Practical Implementation Deliverable", style_table_header)],
        [
            Paragraph("<b>1. AI Foundations</b>", style_table_cell_bold),
            Paragraph("Tokenization, model context limits, latency/cost tradeoffs, responsible AI", style_table_cell),
            Paragraph("Benchmark report comparing models across speed, cost, and accuracy", style_table_cell)
        ],
        [
            Paragraph("<b>2. LLM Engineering</b>", style_table_cell_bold),
            Paragraph("Prompt structures, few-shot patterns, JSON schemas, function-calling", style_table_cell),
            Paragraph("Structured data extractor converting messy PDFs into validated JSON", style_table_cell)
        ],
        [
            Paragraph("<b>3. AI Agent Systems</b>", style_table_cell_bold),
            Paragraph("Autonomous tool-calling, multi-agent coordination, memory & planning", style_table_cell),
            Paragraph("Research assistant agent capable of browsing web and compiling dossiers", style_table_cell)
        ],
        [
            Paragraph("<b>4. Workflow Automation</b>", style_table_cell_bold),
            Paragraph("Webhooks, REST APIs, triggers/actions, n8n orchestration", style_table_cell),
            Paragraph("Automated event notification bridge connecting Google Sheets to WhatsApp", style_table_cell)
        ],
        [
            Paragraph("<b>5. Software Engineering</b>", style_table_cell_bold),
            Paragraph("Branch management, semantic commits, PR reviews, documentation", style_table_cell),
            Paragraph("Multi-contributor GitHub repo with linting, formatting & PR checks", style_table_cell)
        ],
        [
            Paragraph("<b>6. Backend & APIs</b>", style_table_cell_bold),
            Paragraph("FastAPI, Express/Node.js, JWT session auth, rate limiting, CORS", style_table_cell),
            Paragraph("Authenticated REST API service with schema validation & tests", style_table_cell)
        ],
        [
            Paragraph("<b>7. Data & Retrieval (RAG)</b>", style_table_cell_bold),
            Paragraph("Vector embeddings, semantic search, chunking, PostgreSQL/pgvector", style_table_cell),
            Paragraph("Semantic search Q&A engine querying college syllabi & past papers", style_table_cell)
        ],
        [
            Paragraph("<b>8. Cloud & Deployment</b>", style_table_cell_bold),
            Paragraph("Docker containers, Linux VPS, Nginx reverse proxy, Cloudflare CDN", style_table_cell),
            Paragraph("Deployed web application with custom domain, SSL, and zero cold starts", style_table_cell)
        ],
        [
            Paragraph("<b>9. Product & UI Polish</b>", style_table_cell_bold),
            Paragraph("Linear-tier dark aesthetics, typography scales, accessibility, responsive UI", style_table_cell),
            Paragraph("High-conversion dashboard interface built on modern CSS primitives", style_table_cell)
        ],
        [
            Paragraph("<b>10. Pitching & Articulation</b>", style_table_cell_bold),
            Paragraph("Hackathon storytelling, slide design, live demo choreography, Q&A defense", style_table_cell),
            Paragraph("Recorded 3-minute forensic product demo pitch under timed pressure", style_table_cell)
        ]
    ]
    t_curr = Table(curriculum_data, colWidths=[105, 235, 180])
    t_curr.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), C_SLATE),
        ('BOX', (0,0), (-1,-1), 0.5, C_BORDER),
        ('INNERGRID', (0,0), (-1,-1), 0.5, C_BORDER),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, C_BG_LIGHT]),
        ('TOPPADDING', (0,0), (-1,-1), 3.5),
        ('BOTTOMPADDING', (0,0), (-1,-1), 3.5),
        ('LEFTPADDING', (0,0), (-1,-1), 6),
        ('RIGHTPADDING', (0,0), (-1,-1), 6),
    ]))
    story.append(t_curr)
    story.append(Spacer(1, 4))

    story.append(Paragraph("<b>Modern Industry Tooling & Production Tech Stack Matrix</b>", style_h2))

    stack_data = [
        [Paragraph("Category", style_table_header), Paragraph("Production Industry Technologies Mastered", style_table_header)],
        [
            Paragraph("<b>Languages & Core</b>", style_table_cell_bold),
            Paragraph("Python 3.12, TypeScript / JavaScript, SQL (PostgreSQL), Bash / Linux Shell scripting", style_table_cell)
        ],
        [
            Paragraph("<b>AI & Agent Systems</b>", style_table_cell_bold),
            Paragraph("OpenAI / Gemini SDKs, Groq Inference, LangChain, LlamaIndex, n8n Orchestration, Ollama (Local LLMs)", style_table_cell)
        ],
        [
            Paragraph("<b>Backend & Databases</b>", style_table_cell_bold),
            Paragraph("FastAPI, Express/Node.js, PostgreSQL 16 with pgvector, Redis Cache, AES-256 Crypto, JWT Sessions", style_table_cell)
        ],
        [
            Paragraph("<b>DevOps & Hosting</b>", style_table_cell_bold),
            Paragraph("Docker Containers, Coolify Multi-Tenancy, Hetzner Linux VPS, Cloudflare CDN & WAF, GitHub Actions CI", style_table_cell)
        ],
        [
            Paragraph("<b>Product & Articulation</b>", style_table_cell_bold),
            Paragraph("Tailwind CSS, Radix UI Primitives, Lucide Icons, Figma Design Tokens, Forensic Hackathon Slide Frameworks", style_table_cell)
        ]
    ]
    t_stack = Table(stack_data, colWidths=[125, 395])
    t_stack.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), C_NAVY),
        ('BOX', (0,0), (-1,-1), 0.5, C_BORDER),
        ('INNERGRID', (0,0), (-1,-1), 0.5, C_BORDER),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, C_BG_LIGHT]),
        ('TOPPADDING', (0,0), (-1,-1), 3),
        ('BOTTOMPADDING', (0,0), (-1,-1), 3),
        ('LEFTPADDING', (0,0), (-1,-1), 6),
        ('RIGHTPADDING', (0,0), (-1,-1), 6),
    ]))
    story.append(t_stack)
    story.append(Spacer(1, 4))

    story.append(Paragraph("<b>Deep Dive: The Pitch & Articulation Studio Framework</b>", style_h2))

    pitch_cols = [
        [
            Paragraph("<b>Pillar 1: The 60-Second Hook</b><br/>Framing user pain points immediately with zero corporate jargon. Grabbing judge attention before touching code.", style_table_cell),
            Paragraph("<b>Pillar 2: Demo Choreography</b><br/>Designing fail-safe live demo flows with pre-cached fallbacks, eliminating live network crashes during judging.", style_table_cell)
        ],
        [
            Paragraph("<b>Pillar 3: Visual Ergonomics</b><br/>Clean typography, high-contrast dark themes, and intuitive navigation that make software look $10,000-grade.", style_table_cell),
            Paragraph("<b>Pillar 4: Hostile Q&A Defense</b><br/>Training students to articulate system latency, cost per token, concurrency limits, and security trade-offs calmly.", style_table_cell)
        ]
    ]
    t_pitch_grid = Table(pitch_cols, colWidths=[260, 260])
    t_pitch_grid.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), C_BLUE_LIGHT),
        ('BOX', (0,0), (-1,-1), 1, C_BLUE_BORDER),
        ('INNERGRID', (0,0), (-1,-1), 0.5, C_BLUE_BORDER),
        ('TOPPADDING', (0,0), (-1,-1), 4.5),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4.5),
        ('LEFTPADDING', (0,0), (-1,-1), 8),
        ('RIGHTPADDING', (0,0), (-1,-1), 8),
    ]))
    story.append(t_pitch_grid)
    story.append(Spacer(1, 4))

    curr_box = (
        "<b>Curriculum Quality Mandate:</b> Students are not graded on multiple-choice theory. "
        "A module is marked complete only when the pull request is merged with passing CI tests and the live preview URL is demonstrated."
    )
    card_curr = Table([[Paragraph(curr_box, style_callout)]], colWidths=[520])
    card_curr.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor("#fafafa")),
        ('BOX', (0,0), (-1,-1), 0.5, C_BORDER),
        ('LINELEFT', (0,0), (0,0), 3.5, C_AMBER),
        ('TOPPADDING', (0,0), (-1,-1), 4),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
        ('LEFTPADDING', (0,0), (-1,-1), 9),
        ('RIGHTPADDING', (0,0), (-1,-1), 9),
    ]))
    story.append(card_curr)

    story.append(PageBreak())

    # =========================================================================
    # PAGE 5: FLAGSHIP CASE STUDY & PRODUCTION ARCHITECTURE
    # =========================================================================
    story.append(Paragraph("6. Flagship Proof-of-Concept: CampusIQ", style_h1))
    story.append(HRFlowable(width="100%", thickness=1, color=C_BLUE, spaceBefore=2, spaceAfter=5))

    story.append(Paragraph(
        "To prove that ATLAS is grounded in immediate execution rather than speculative theory, the founding team has already designed, "
        "built, and verified our flagship campus platform: <b>CampusIQ</b> (<i>The Intelligent MAIT Student & Academic Operations Hub</i>).",
        style_body
    ))

    campusiq_features = [
        [Paragraph("Feature Component", style_table_header), Paragraph("Engineering Architecture", style_table_header), Paragraph("Institutional Impact for MAIT", style_table_header)],
        [
            Paragraph("<b>Edumarshal Attendance Radar</b>", style_table_cell_bold),
            Paragraph("Automated background sync, interactive calendar audits, predictive bunk/margin calculators.", style_table_cell),
            Paragraph("Eliminates student attendance anxiety and manual percentage calculation mistakes.", style_table_cell)
        ],
        [
            Paragraph("<b>Official ExamWeb Marksheets</b>", style_table_cell_bold),
            Paragraph("ACID relational store, PDF generation, SGPA/CGPA auditing, retroactive result reconciliation.", style_table_cell),
            Paragraph("Provides instant, verified academic marksheet access during placement drives.", style_table_cell)
        ],
        [
            Paragraph("<b>Institutional Security Vault</b>", style_table_cell_bold),
            Paragraph("AES-256-GCM hardware encryption, zero plaintext passwords, 30-day sliding sessions, SSRF proxy.", style_table_cell),
            Paragraph("Bank-grade credential security; strict compliance with university IT norms.", style_table_cell)
        ],
        [
            Paragraph("<b>Stealth Master Admin Panel</b>", style_table_cell_bold),
            Paragraph("Role-gated clearance, omni-search student roster, live marksheet/attendance overrides.", style_table_cell),
            Paragraph("Empowers faculty/administrators to audit student records with sub-second lookups.", style_table_cell)
        ]
    ]
    t_ciq = Table(campusiq_features, colWidths=[120, 215, 185])
    t_ciq.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), C_NAVY),
        ('BOX', (0,0), (-1,-1), 0.5, C_BORDER),
        ('INNERGRID', (0,0), (-1,-1), 0.5, C_BORDER),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, C_BG_LIGHT]),
        ('TOPPADDING', (0,0), (-1,-1), 4),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
        ('LEFTPADDING', (0,0), (-1,-1), 6),
        ('RIGHTPADDING', (0,0), (-1,-1), 6),
    ]))
    story.append(t_ciq)
    story.append(Spacer(1, 4))

    ciq_metrics = [
        [
            Paragraph("<b>Sub-120ms</b><br/>API Response Latency<br/>via Caching Layer", style_metric_desc),
            Paragraph("<b>100% Server-Side</b><br/>Session Validation &<br/>Sliding Expirations", style_metric_desc),
            Paragraph("<b>AES-256-GCM</b><br/>Hardware-Grade Data<br/>Encryption at Rest", style_metric_desc),
            Paragraph("<b>Zero Plaintext</b><br/>Password Storage or<br/>Logging in Database", style_metric_desc)
        ]
    ]
    t_ciq_metrics = Table(ciq_metrics, colWidths=[130, 130, 130, 130])
    t_ciq_metrics.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), C_BG_LIGHT),
        ('BOX', (0,0), (-1,-1), 0.5, C_BORDER),
        ('INNERGRID', (0,0), (-1,-1), 0.5, C_BORDER),
        ('TOPPADDING', (0,0), (-1,-1), 5),
        ('BOTTOMPADDING', (0,0), (-1,-1), 5),
        ('LEFTPADDING', (0,0), (-1,-1), 6),
        ('RIGHTPADDING', (0,0), (-1,-1), 6),
    ]))
    story.append(t_ciq_metrics)
    story.append(Spacer(1, 4))

    story.append(Paragraph("7. Production Infrastructure & Resource Isolation Architecture", style_h1))
    story.append(HRFlowable(width="100%", thickness=1, color=C_BLUE, spaceBefore=2, spaceAfter=5))

    story.append(Paragraph(
        "A critical engineering requirement for ATLAS is ensuring that experimental student projects never threaten campus-critical utilities. "
        "We implement an isolated, two-tier infrastructure architecture that guarantees high availability and zero cold starts:",
        style_body
    ))

    infra_cols = [
        [
            Paragraph(
                "<b>Tier 1: Dedicated Production Server (CampusIQ)</b><br/>"
                "• <b>Host:</b> Isolated Linux cloud VPS (Hetzner CX22: 2 vCPU, 4GB RAM).<br/>"
                "• <b>Edge CDN:</b> Cloudflare CDN edge caching 90% of assets in Delhi, absorbing traffic spikes during result announcements.<br/>"
                "• <b>Database:</b> Dedicated PostgreSQL 16 ACID store with automated daily backups.<br/>"
                "• <b>SLA:</b> 99.9% uptime with zero experimental student code sharing resources.",
                style_table_cell
            ),
            Paragraph(
                "<b>Tier 2: ATLAS Labs Incubator (Student Sandbox)</b><br/>"
                "• <b>Host:</b> Isolated Linux VPS running <b>Coolify container orchestration</b>.<br/>"
                "• <b>Blast Radius Firewall:</b> Every student app runs in an isolated Docker container with strict Cgroup limits (max 256MB RAM, 0.5 CPU).<br/>"
                "• <b>Failure Containment:</b> If a student writes a memory leak or crash loop, only their container restarts; CampusIQ remains 100% unaffected.",
                style_table_cell
            )
        ]
    ]
    t_infra_grid = Table(infra_cols, colWidths=[260, 260])
    t_infra_grid.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), C_BG_LIGHT),
        ('BOX', (0,0), (-1,-1), 0.5, C_BORDER),
        ('INNERGRID', (0,0), (-1,-1), 0.5, C_BORDER),
        ('TOPPADDING', (0,0), (-1,-1), 5),
        ('BOTTOMPADDING', (0,0), (-1,-1), 5),
        ('LEFTPADDING', (0,0), (-1,-1), 8),
        ('RIGHTPADDING', (0,0), (-1,-1), 8),
    ]))
    story.append(t_infra_grid)
    story.append(Spacer(1, 4))

    story.append(Paragraph("<b>Security Boundaries & Blast Radius Containment Specifications</b>", style_h2))

    firewall_data = [
        [Paragraph("Security Layer", style_table_header), Paragraph("Isolation Mechanism & SLA Enforcement", style_table_header)],
        [
            Paragraph("<b>Container Resource Quotas</b>", style_table_cell_bold),
            Paragraph("Strict Linux cgroups quota: hard cap of 256MB RAM and 50% single CPU core per student project. Runaway scripts terminate instantly without server disruption.", style_table_cell)
        ],
        [
            Paragraph("<b>Network & Database Isolation</b>", style_table_cell_bold),
            Paragraph("Production database (PostgreSQL 16) is isolated on a private VPC network. Student sandbox containers possess zero network bridge to production credentials.", style_table_cell)
        ],
        [
            Paragraph("<b>Automated SSL & Routing</b>", style_table_cell_bold),
            Paragraph("Reverse-proxied through Nginx/Traefik with automated Let's Encrypt wildcard SSL certificates per project subdomain (e.g., student-app.labs.atlas.mait.ac.in).", style_table_cell)
        ]
    ]
    t_firewall = Table(firewall_data, colWidths=[140, 380])
    t_firewall.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), C_SLATE),
        ('BOX', (0,0), (-1,-1), 0.5, C_BORDER),
        ('INNERGRID', (0,0), (-1,-1), 0.5, C_BORDER),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, C_BG_LIGHT]),
        ('TOPPADDING', (0,0), (-1,-1), 3),
        ('BOTTOMPADDING', (0,0), (-1,-1), 3),
        ('LEFTPADDING', (0,0), (-1,-1), 6),
        ('RIGHTPADDING', (0,0), (-1,-1), 6),
    ]))
    story.append(t_firewall)
    story.append(Spacer(1, 4))

    cost_box_html = (
        "<b>Compute Strategy & Long-Term Financial Sustainability:</b><br/>"
        "• <b>Hybrid AI Compute:</b> Lightweight cloud APIs (Groq, Gemini Flash) power production web apps, while heavy fine-tuning and local models (Ollama/Llama-3) run on physical college lab workstations with NVIDIA RTX GPUs, keeping cloud bills minimal.<br/>"
        "• <b>Sustainability Options:</b> Self-funded via society micro-pool (~INR 1,700/mo total for both VPS tiers) or <b>INR 0 Ongoing Cost</b> if MAIT IT allocates an on-premise static IP / internal rack VM for campus utilities."
    )
    card_cost = Table([[Paragraph(cost_box_html, style_callout)]], colWidths=[520])
    card_cost.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), C_EMERALD_BG),
        ('BOX', (0,0), (-1,-1), 1, C_EMERALD_BORDER),
        ('LINELEFT', (0,0), (0,0), 3.5, C_EMERALD),
        ('TOPPADDING', (0,0), (-1,-1), 5),
        ('BOTTOMPADDING', (0,0), (-1,-1), 5),
        ('LEFTPADDING', (0,0), (-1,-1), 10),
        ('RIGHTPADDING', (0,0), (-1,-1), 10),
    ]))
    story.append(card_cost)

    story.append(PageBreak())

    # =========================================================================
    # PAGE 6: GOVERNANCE, ROADMAP & INSTITUTIONAL ROI
    # =========================================================================
    story.append(Paragraph("8. Governance & Streamlined Department Architecture", style_h1))
    story.append(HRFlowable(width="100%", thickness=1, color=C_BLUE, spaceBefore=2, spaceAfter=5))

    dept_data = [
        [Paragraph("Division", style_table_header), Paragraph("Key Functional Responsibilities", style_table_header), Paragraph("Leadership & Staffing", style_table_header)],
        [
            Paragraph("<b>AI & Systems Engineering</b>", style_table_cell_bold),
            Paragraph("LLM orchestration, multi-agent systems, backend APIs, databases, Docker containerization, and VPS infrastructure.", style_table_cell),
            Paragraph("Technical Director + Core AI Engineers", style_table_cell)
        ],
        [
            Paragraph("<b>Product, Design & Pitching</b>", style_table_cell_bold),
            Paragraph("Frontend UI/UX design, linear-tier visual styling, product requirement specs, demo pitch training, and hackathon decks.", style_table_cell),
            Paragraph("Product Head + UI/Pitch Coaches", style_table_cell)
        ],
        [
            Paragraph("<b>Operations & Growth</b>", style_table_cell_bold),
            Paragraph("Weekly sprint logistics, attendance tracking, member onboarding, brand communications, and hackathon registrations.", style_table_cell),
            Paragraph("General Secretary + Operations Leads", style_table_cell)
        ],
        [
            Paragraph("<b>Labs & External Relations</b>", style_table_cell_bold),
            Paragraph("Campus utilities maintenance (CampusIQ), open-source tracking, supervised client project scoping, and faculty liaison.", style_table_cell),
            Paragraph("Labs Head + Client Liaison Officer", style_table_cell)
        ]
    ]
    t_dept = Table(dept_data, colWidths=[115, 260, 145])
    t_dept.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), C_NAVY),
        ('BOX', (0,0), (-1,-1), 0.5, C_BORDER),
        ('INNERGRID', (0,0), (-1,-1), 0.5, C_BORDER),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, C_BG_LIGHT]),
        ('TOPPADDING', (0,0), (-1,-1), 3.5),
        ('BOTTOMPADDING', (0,0), (-1,-1), 3.5),
        ('LEFTPADDING', (0,0), (-1,-1), 6),
        ('RIGHTPADDING', (0,0), (-1,-1), 6),
    ]))
    story.append(t_dept)

    story.append(Spacer(1, 4))
    story.append(Paragraph("9. Institutional Safeguards, Compliance & Ethics Charter", style_h1))
    story.append(HRFlowable(width="100%", thickness=1, color=C_BLUE, spaceBefore=2, spaceAfter=5))

    story.append(Paragraph("• <b>Zero Unauthorized Access:</b> Strict prohibition against unauthorized scraping or security probing of college portals. Tools interact solely with legitimate APIs, published notices, or user-consented credentials.", style_bullet))
    story.append(Paragraph("• <b>Mandatory Faculty Clearance:</b> All public-facing campus tools, external client engagements, or formal event sponsorships require written clearance from the Faculty Advisor and Department Coordinator.", style_bullet))
    story.append(Paragraph("• <b>Academic Priority Invariant:</b> Regular academic schedules, class attendance, and university semester exams strictly take precedence over society hackathons and sprint milestones.", style_bullet))

    story.append(Spacer(1, 4))
    story.append(Paragraph("10. Year-One Roadmap & Institutional ROI for MAIT", style_h1))
    story.append(HRFlowable(width="100%", thickness=1, color=C_BLUE, spaceBefore=2, spaceAfter=5))

    roi_data = [
        [Paragraph("Quarter / Phase", style_table_header), Paragraph("Key Milestones & Deliverables", style_table_header), Paragraph("Measurable Institutional ROI for MAIT", style_table_header)],
        [
            Paragraph("<b>Q1: Foundation<br/>(Months 1–3)</b>", style_table_cell_bold),
            Paragraph("Faculty ratification, selection of 25 core builders, launch of 10-module curriculum, public rollout of CampusIQ.", style_table_cell),
            Paragraph("Automated notice categorization and verified attendance tool live for MAIT students (NAAC Criterion 2: IT Infrastructure).", style_table_cell)
        ],
        [
            Paragraph("<b>Q2: Sprints<br/>(Months 4–6)</b>", style_table_cell_bold),
            Paragraph("Launch of Open ATLAS workshops, Pitch & Articulation Studio, and first cohort of internal campus utilities.", style_table_cell),
            Paragraph("Trained student squads entering Smart India Hackathon (SIH) with vetted prototypes and pitch decks (NAAC Criterion 5: Progression).", style_table_cell)
        ],
        [
            Paragraph("<b>Q3: Deployment<br/>(Months 7–9)</b>", style_table_cell_bold),
            Paragraph("First supervised industry client automation cohort; deployment of 2 additional campus tools; open-source contributions.", style_table_cell),
            Paragraph("Published case studies and concrete engineering portfolios enhancing placement outcomes (NAAC Criterion 3: Industry Linkages).", style_table_cell)
        ],
        [
            Paragraph("<b>Q4: Succession<br/>(Months 10–12)</b>", style_table_cell_bold),
            Paragraph("Annual Hackathon build summit, architectural code handovers, documentation audits, and executive election.", style_table_cell),
            Paragraph("Self-sustaining society infrastructure with multi-year code continuity and zero institutional brain drain.", style_table_cell)
        ]
    ]
    t_roi = Table(roi_data, colWidths=[95, 230, 195])
    t_roi.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), C_SLATE),
        ('BOX', (0,0), (-1,-1), 0.5, C_BORDER),
        ('INNERGRID', (0,0), (-1,-1), 0.5, C_BORDER),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, C_BG_LIGHT]),
        ('TOPPADDING', (0,0), (-1,-1), 4),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
        ('LEFTPADDING', (0,0), (-1,-1), 6),
        ('RIGHTPADDING', (0,0), (-1,-1), 6),
    ]))
    story.append(t_roi)

    story.append(Spacer(1, 5))
    story.append(Paragraph("<b>Faculty Advisory Steering Committee & Institutional Oversight</b>", style_h2))

    steering_html = (
        "<b>Governance Structure:</b> ATLAS operates under the permanent stewardship of a Department Faculty Advisor and an Advisory Steering Committee "
        "comprising senior professors from Computer Science and Information Technology. The committee meets quarterly to review project roadmaps, "
        "audit data compliance, grant clearances for external industry automations, and evaluate student progress."
    )
    card_steering = Table([[Paragraph(steering_html, style_callout)]], colWidths=[520])
    card_steering.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), C_BG_LIGHT),
        ('BOX', (0,0), (-1,-1), 0.5, C_BORDER),
        ('LINELEFT', (0,0), (0,0), 3.5, C_BLUE),
        ('TOPPADDING', (0,0), (-1,-1), 5),
        ('BOTTOMPADDING', (0,0), (-1,-1), 5),
        ('LEFTPADDING', (0,0), (-1,-1), 8),
        ('RIGHTPADDING', (0,0), (-1,-1), 8),
    ]))
    story.append(card_steering)
    story.append(Spacer(1, 5))

    story.append(Paragraph("<b>Official Endorsement & Institutional Approval Block</b>", style_h2))

    sig_data = [
        [
            Paragraph("<b>Tanmay Jain</b><br/>Lead Student Proposer<br/>Dept. of CSE, MAIT", style_metric_desc),
            Paragraph("<b>Faculty Advisor</b><br/>ATLAS Society<br/>MAIT, Delhi", style_metric_desc),
            Paragraph("<b>Head of Department</b><br/>Dept. of Computer Science<br/>MAIT, Delhi", style_metric_desc),
            Paragraph("<b>Dean / Director</b><br/>Academic Affairs<br/>MAIT, Delhi", style_metric_desc)
        ],
        [
            Paragraph("<font color='#94a3b8'>Signature: __________________<br/>Date: ____ / ____ / 2026<br/>[Official Verification]</font>", style_metric_desc),
            Paragraph("<font color='#94a3b8'>Signature: __________________<br/>Date: ____ / ____ / 2026<br/>[Faculty Recommendation]</font>", style_metric_desc),
            Paragraph("<font color='#94a3b8'>Signature: __________________<br/>Date: ____ / ____ / 2026<br/>[Department Approval]</font>", style_metric_desc),
            Paragraph("<font color='#94a3b8'>Signature: __________________<br/>Date: ____ / ____ / 2026<br/>[Institutional Seal & Ratification]</font>", style_metric_desc)
        ]
    ]
    t_sig = Table(sig_data, colWidths=[130, 130, 130, 130])
    t_sig.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor("#f8fafc")),
        ('BOX', (0,0), (-1,-1), 0.5, C_BORDER),
        ('INNERGRID', (0,0), (-1,-1), 0.5, C_BORDER),
        ('TOPPADDING', (0,0), (-1,-1), 4),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
        ('LEFTPADDING', (0,0), (-1,-1), 4),
        ('RIGHTPADDING', (0,0), (-1,-1), 4),
    ]))
    story.append(t_sig)

    # Build the document
    doc.build(story, canvasmaker=NumberedCanvas)
    print(f"Successfully generated: {PDF_PATH}")

    # Copy to artifact path
    os.makedirs(os.path.dirname(ARTIFACT_PATH), exist_ok=True)
    shutil.copyfile(PDF_PATH, ARTIFACT_PATH)
    print(f"Copied to artifact: {ARTIFACT_PATH}")

if __name__ == "__main__":
    create_atlas_proposal()
