#!/usr/bin/env python3
"""
build_full_atlas_proposal.py
============================
Generates the comprehensive 35-page institutional presentation dossier for:
ATLAS - AI, Automation & Production Engineering Society (MAIT)

Structure:
- Cover Page (Page 1)
- 34 Topic/Slide Pages (Pages 2 to 35)

Fixes & Invariants Enforced:
1. Exact slide-by-slide structure matching the original document (35 pages).
2. De-duplicated redundancies while retaining complete technical depth and tables.
3. Slide 4: "Engineering Depth Meets Articulate Delivery / Presentation" (fixed from "production over presentation").
4. Slide 5: "Inconsistent Momentum in Self-Directed Learning" (fixed from "lacks weekly accountability").
5. Executive Leadership:
   - President: Garv Goyal
   - Vice President: Tanmay Jain
   (Never calling Tanmay lead).
6. Slide 24: Comprehensive CampusIQ feature breakdown (Attendance radar, Marksheets store, Security vault, Stealth admin).
7. Slide 29: Two-Server blast-radius isolation architecture (CampusIQ prod vs Coolify 256MB sandbox) & INR financial model.
8. Currency symbols properly rendered as 'INR' to prevent ReportLab font glyph errors.
"""

import os
import sys
import shutil
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, HRFlowable
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
        # Suppress header and footer on cover page (page 1)
        if self._pageNumber > 1:
            # Header
            self.setFont("Helvetica-Bold", 8)
            self.setFillColor(colors.HexColor("#475569"))
            self.drawString(40, 792 - 24, "ATLAS • AI, AUTOMATION & PRODUCTION ENGINEERING SOCIETY | MAIT")
            self.drawRightString(612 - 40, 792 - 24, "INSTITUTIONAL PROPOSAL")
            self.setStrokeColor(colors.HexColor("#cbd5e1"))
            self.setLineWidth(0.6)
            self.line(40, 792 - 28, 612 - 40, 792 - 28)

            # Footer
            self.setStrokeColor(colors.HexColor("#cbd5e1"))
            self.setLineWidth(0.6)
            self.line(40, 32, 612 - 40, 32)
            self.setFont("Helvetica", 7.5)
            self.drawString(40, 21, "Maharaja Agrasen Institute of Technology • Department of Computer Science & Engineering")
            page_text = f"Page {self._pageNumber} of {page_count}"
            self.setFont("Helvetica-Bold", 7.5)
            self.drawRightString(612 - 40, 21, page_text)

        self.restoreState()

def build_pdf():
    doc = SimpleDocTemplate(
        PDF_PATH,
        pagesize=letter,
        leftMargin=40,
        rightMargin=40,
        topMargin=40,
        bottomMargin=40
    )

    styles = getSampleStyleSheet()

    # Custom styles
    style_crumb = ParagraphStyle(
        'SlideCrumb',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=8,
        leading=10,
        textColor=colors.HexColor('#2563eb'),
        textTransform='uppercase'
    )

    style_title = ParagraphStyle(
        'SlideTitle',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=15,
        leading=18,
        textColor=colors.HexColor('#0f172a'),
        spaceAfter=4
    )

    style_h2 = ParagraphStyle(
        'SlideH2',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=10.5,
        leading=13,
        textColor=colors.HexColor('#1e293b'),
        spaceBefore=4,
        spaceAfter=3
    )

    style_body = ParagraphStyle(
        'SlideBody',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=8.5,
        leading=11.5,
        textColor=colors.HexColor('#334155')
    )

    style_body_bold = ParagraphStyle(
        'SlideBodyBold',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=8.5,
        leading=11.5,
        textColor=colors.HexColor('#0f172a')
    )

    style_table_header = ParagraphStyle(
        'TableHeader',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=8,
        leading=10.5,
        textColor=colors.HexColor('#ffffff')
    )

    style_table_cell = ParagraphStyle(
        'TableCell',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=7.8,
        leading=10.2,
        textColor=colors.HexColor('#334155')
    )

    style_table_cell_bold = ParagraphStyle(
        'TableCellBold',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=7.8,
        leading=10.2,
        textColor=colors.HexColor('#0f172a')
    )

    style_callout = ParagraphStyle(
        'SlideCallout',
        parent=styles['Normal'],
        fontName='Helvetica-Oblique',
        fontSize=8.5,
        leading=12,
        textColor=colors.HexColor('#1e293b')
    )

    def header_block(q_num, q_title, full_title):
        crumb_text = f"QUESTION {q_num:02d} OF 34 • {q_title}"
        return [
            Paragraph(crumb_text, style_crumb),
            Paragraph(full_title, style_title),
            HRFlowable(width="100%", thickness=1.5, color=colors.HexColor("#2563eb"), spaceAfter=8, spaceBefore=2)
        ]

    def callout_box(text, bg_color="#f8fafc", border_color="#2563eb"):
        p = Paragraph(text, style_callout)
        t = Table([[p]], colWidths=[532])
        t.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,-1), colors.HexColor(bg_color)),
            ('BOX', (0,0), (-1,-1), 0.5, colors.HexColor("#cbd5e1")),
            ('LINEBEFORE', (0,0), (0,-1), 3.5, colors.HexColor(border_color)),
            ('TOPPADDING', (0,0), (-1,-1), 5),
            ('BOTTOMPADDING', (0,0), (-1,-1), 5),
            ('LEFTPADDING', (0,0), (-1,-1), 8),
            ('RIGHTPADDING', (0,0), (-1,-1), 8),
        ]))
        return t

    def create_table(header_row, data_rows, col_widths, custom_styles=None):
        formatted_data = []
        # Header
        formatted_header = [
            Paragraph(cell, style_table_header) if isinstance(cell, str) else cell 
            for cell in header_row
        ]
        formatted_data.append(formatted_header)
        
        # Rows
        for r_idx, row in enumerate(data_rows):
            formatted_row = []
            for c_idx, cell in enumerate(row):
                if isinstance(cell, str):
                    s = style_table_cell_bold if c_idx == 0 else style_table_cell
                    formatted_row.append(Paragraph(cell, s))
                else:
                    formatted_row.append(cell)
            formatted_data.append(formatted_row)

        t = Table(formatted_data, colWidths=col_widths)
        t_style = [
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1e293b')),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#e2e8f0')),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
            ('LEFTPADDING', (0, 0), (-1, -1), 5),
            ('RIGHTPADDING', (0, 0), (-1, -1), 5),
        ]
        # Alternating background colors
        for i in range(1, len(formatted_data)):
            bg = '#ffffff' if i % 2 == 1 else '#f8fafc'
            t_style.append(('BACKGROUND', (0, i), (-1, i), colors.HexColor(bg)))

        if custom_styles:
            t_style.extend(custom_styles)

        t.setStyle(TableStyle(t_style))
        return t

    story = []

    # =========================================================================
    # PAGE 1: COVER PAGE
    # =========================================================================
    cover_top = [
        Spacer(1, 15),
        Paragraph("<font color='#2563eb'><b>MAHARAJA AGRASEN INSTITUTE OF TECHNOLOGY</b></font>", ParagraphStyle('CoverDept', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=10, leading=13, alignment=1, textColor=colors.HexColor('#2563eb'))),
        Paragraph("DEPARTMENT OF COMPUTER SCIENCE & ENGINEERING", ParagraphStyle('CoverSubDept', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=9, leading=12, alignment=1, textColor=colors.HexColor('#475569'))),
        Spacer(1, 28),
        Paragraph("ATLAS", ParagraphStyle('CoverTitle', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=38, leading=42, alignment=1, textColor=colors.HexColor('#0f172a'))),
        Spacer(1, 6),
        Paragraph("AI, AUTOMATION & PRODUCTION ENGINEERING SOCIETY", ParagraphStyle('CoverSubtitle', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=13, leading=17, alignment=1, textColor=colors.HexColor('#2563eb'))),
        Spacer(1, 10),
        callout_box("<b>MOTTO:</b> AUTOMATE THE MUNDANE. ENGINEER THE FUTURE.<br/><i>A student-led technical society designed to establish a structured, self-sustaining pipeline from foundational AI education to resilient software engineering, production deployments, and continuous project ownership.</i>", bg_color="#eff6ff", border_color="#2563eb"),
        Spacer(1, 22),
        Paragraph("OFFICIAL INSTITUTIONAL CHARTER & STRATEGIC PROPOSAL", ParagraphStyle('CoverDocTitle', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=12, leading=15, alignment=1, textColor=colors.HexColor('#0f172a'))),
        Paragraph("Comprehensive 34-Slide Architecture & Operational Blueprint", ParagraphStyle('CoverDocSub', parent=styles['Normal'], fontName='Helvetica', fontSize=9, leading=12, alignment=1, textColor=colors.HexColor('#64748b'))),
        Spacer(1, 18),
    ]
    story.extend(cover_top)

    meta_data = [
        ["Document Type", "Institutional Technical Society Proposal & Charter"],
        ["Institution", "Maharaja Agrasen Institute of Technology (MAIT), Rohini, Delhi"],
        ["Affiliated Body", "Department of Computer Science & Engineering (CSE)"],
        ["Society President", "Garv Goyal"],
        ["Vice President", "Tanmay Jain"],
        ["Faculty Advisor", "Senior CSE Faculty / Nominated by Head of Department"],
        ["Technical Scope", "Generative AI, LLM Systems, Autonomous Agents, Workflow Automation, Production Web Engineering, Linux Infrastructure"],
        ["Structural Framework", "34 Strategic Topic Inquiries, 12 Core Systems, 12 Operating Departments, Two-Tier Activity Model (Open vs Labs)"],
        ["Flagship Case Study", "CampusIQ (Automated Attendance Radar, Relational Marksheet Vault, AES-256 Auth, Stealth Admin)"],
        ["Deployment Model", "Two-Server Blast-Radius Isolation (Hetzner Production Node + Coolify Student Sandbox Node)"],
    ]
    meta_table = create_table(
        ["Governance Dimension", "Institutional Specification"],
        meta_data,
        col_widths=[150, 382]
    )
    story.append(meta_table)
    story.append(Spacer(1, 14))
    story.append(callout_box("<b>Notice of Presentation:</b> This document contains the full architectural, operational, and financial framework of ATLAS for formal review by college leadership, faculty coordinators, and student technical stakeholders.", bg_color="#f8fafc", border_color="#64748b"))
    story.append(PageBreak())

    # =========================================================================
    # SLIDE 1 (Page 2): WHO WE ARE
    # =========================================================================
    story.extend(header_block(1, "WHO WE ARE", "Identity, Mission & Core Values of ATLAS"))
    story.append(Paragraph("ATLAS is proposed as a dedicated <b>AI, Automation & Production Engineering Society</b> at Maharaja Agrasen Institute of Technology (MAIT). It is engineered around an urgent observation: while modern AI tooling is rapidly advancing, students need an institutional ecosystem where emerging technologies are not merely discussed, but mastered through disciplined, end-to-end software engineering.", style_body))
    story.append(Spacer(1, 5))

    story.append(Paragraph("What is ATLAS?", style_h2))
    who_data = [
        ["Dedicated AI & Systems Domain", "Focuses specifically on Applied Artificial Intelligence, Large Language Models (LLMs), AI Agents, API Integrations, Workflow Automation, and Production Web Engineering."],
        ["Structured Learning Pipeline", "Provides a weekly curated curriculum, hands-on implementation challenges, code review checkpoints, and verifiable skill progression tracking."],
        ["Post-Hackathon Project Lifecycle", "Moves student prototypes past hackathon judging tables into testing, hardening, CI/CD, cloud deployment, and multi-semester maintenance."],
        ["Responsible Industry & Client Conduit", "Provides vetted, capable student engineers with opportunities to execute legitimate, scoped client automation problems under institutional oversight."]
    ]
    story.append(create_table(["Core Functional Pillar", "Operational Reality & Mechanism"], who_data, col_widths=[160, 372]))
    story.append(Spacer(1, 5))

    story.append(Paragraph("The 5 Core Mission Pillars", style_h2))
    pillars_data = [
        ["LEARN", "Structured education in AI, LLMs, autonomous agents, modern workflow automation, and distributed systems."],
        ["BUILD", "Convert theoretical understanding into usable student utilities, internal productivity tools, and full-stack applications."],
        ["DELIVER", "Expose advanced student squads to real-world requirements, commercial client pipelines, and production SLAs."],
        ["MAINTAIN", "Overcome the disposable prototype mindset through continuous iteration, issue tracking, and multi-year project ownership."],
        ["CONTRIBUTE", "Foster competitive hackathon excellence, high-impact open-source contributions, and faculty-guided research papers."]
    ]
    story.append(create_table(["Pillar", "Strategic Mandate"], pillars_data, col_widths=[90, 442]))
    story.append(Spacer(1, 5))
    story.append(callout_box("<b>Core Values:</b> <b>Practicality:</b> Learn by building real systems • <b>Ownership:</b> True responsibility for code continuity • <b>Curiosity:</b> Relentless exploration of frontier tech • <b>Discipline:</b> Automated testing and PR reviews • <b>Responsible AI:</b> Absolute data privacy and ethics.", bg_color="#eff6ff", border_color="#2563eb"))
    story.append(PageBreak())

    # =========================================================================
    # SLIDE 2 (Page 3): WHY DOES MAIT NEED ATLAS?
    # =========================================================================
    story.extend(header_block(2, "INSTITUTIONAL NEED", "Bridging the Two Visible Gaps in the Student Technical Ecosystem"))
    story.append(Paragraph("The case for establishing ATLAS begins with two undeniable, structural bottlenecks in our current campus environment:", style_body))
    story.append(Spacer(1, 6))

    gaps_data = [
        ["Gap 1: The Practical Project Continuity Void", 
         "<b>The Status Quo:</b> Students dedicate immense intellectual energy to 24–36 hour hackathons and semester academic evaluations.<br/>"
         "<b>The Structural Failure:</b> The moment the demo or pitch concludes, 95%+ of codebases are permanently abandoned. There is zero defined post-event ownership, zero maintenance infrastructure, no documentation, and no deployment roadmap.<br/>"
         "<b>Institutional Loss:</b> Tremendous student engineering output evaporates into unused GitHub repositories rather than serving as foundational campus assets."],
        ["Gap 2: The Modern AI & Automation Education Vacuum", 
         "<b>The Status Quo:</b> Students encounter AI through disjointed YouTube tutorials, isolated theoretical courses, or shallow ChatGPT chat prompting.<br/>"
         "<b>The Structural Failure:</b> Students miss the entire domain of <i>Production AI Engineering</i>: tool calling, structured JSON output validation, evals, vector databases, multi-agent state machines, API rate limits, and latency budgets.<br/>"
         "<b>Institutional Loss:</b> MAIT students graduate with theoretical knowledge but struggle to clear production-level software and AI engineering interviews."]
    ]
    story.append(create_table(["Identified Institutional Bottleneck", "Analysis of Causes & Resulting Educational Loss"], gaps_data, col_widths=[160, 372]))
    story.append(Spacer(1, 8))

    story.append(Paragraph("The Strategic Opportunity for MAIT", style_h2))
    story.append(Paragraph("ATLAS occupies the crucial space between a traditional student club and a professional engineering organization. By establishing a continuous bridge—<b>Curriculum → Hands-on Sprints → Code Review → Deployment → Long-Term Maintenance</b>—ATLAS ensures that student effort produces tangible intellectual property, verified student skills, and genuine institutional prestige.", style_body))
    story.append(Spacer(1, 8))
    story.append(callout_box("<b>Summary Takeaway:</b> ATLAS does not compete with existing campus societies; it operates as an advanced engineering accelerator that elevates the overall quality, resilience, and deployability of student software at MAIT.", bg_color="#f8fafc", border_color="#2563eb"))
    story.append(PageBreak())

    # =========================================================================
    # SLIDE 3 (Page 4): WHAT IS THE HIDDEN ENGINEERING GAP?
    # =========================================================================
    story.extend(header_block(3, "THE ENGINEERING REALITY", "Hobbyist Prototyping vs. Production Engineering"))
    story.append(Paragraph("To understand why student software rarely survives in the real world, we must examine the hidden engineering gap separating a hackathon demo from a production-grade system:", style_body))
    story.append(Spacer(1, 5))

    eng_gap_data = [
        ["Engineering Aspect", "Typical Student Hackathon Project", "The ATLAS Production Engineering Standard"],
        ["Development Lifecycle", "Idea → Quick Prototype → Presentation Deck → Abandoned", "Problem → Specs → Architecture → Build → Review → Deploy → Maintain"],
        ["The 'Finish Line'", "The 3-minute hackathon pitch to the judging panel", "The first real user, active production logs, and bug resolution"],
        ["Learning Cadence", "Fragmented, self-directed, tutorial-driven cramming", "Weekly sequential curriculum with enforced milestone deliverables"],
        ["AI Output Handling", "Blind acceptance and copy-pasting of LLM-generated code", "Rigorous schema validation (Zod/Pydantic), evals, and unit tests"],
        ["System Architecture", "Monolithic, hardcoded secrets, brittle localhost ports", "Containerized microservices (Docker), reverse proxies, secure envs"],
        ["Long-Term Ownership", "Disbands immediately after event winners are announced", "Explicit maintainer assignment, issue tracking, and junior succession"],
        ["Portfolio Proof", "Screenshots, UI mockups, and pitch decks", "Live production URLs, uptime monitoring, test coverage, and clean Git commits"]
    ]
    story.append(create_table(eng_gap_data[0], eng_gap_data[1:], col_widths=[110, 205, 217]))
    story.append(Spacer(1, 6))

    story.append(Paragraph("Why This Distinction Matters Institutionally", style_h2))
    story.append(Paragraph("The objective is not to criticize hackathons—they provide vital energy and creative velocity. However, hackathons only teach <b>Stage 1 (Prototyping)</b>. ATLAS provides the missing institutional infrastructure for <b>Stages 2 through 7 (Hardening, Deployment, Security, Observability, and Maintenance)</b>. A working demo proves what is possible; disciplined engineering proves what is reliable.", style_body))
    story.append(Spacer(1, 5))
    story.append(callout_box("<b>Key Invariant:</b> A portfolio built on deployed systems with real uptime metrics outclasses a portfolio of shallow, abandoned hackathon repos by orders of magnitude.", bg_color="#eff6ff", border_color="#2563eb"))
    story.append(PageBreak())

    # =========================================================================
    # SLIDE 4 (Page 5): WHAT IS THE ATLAS PHILOSOPHY?
    # =========================================================================
    story.extend(header_block(4, "FOUNDATIONAL PHILOSOPHY", "The 6 Core Operating Beliefs of ATLAS"))
    story.append(callout_box("<b>Our Core Axiom:</b> Students do not become software engineers merely by consuming video tutorials. They develop engineering judgment by repeatedly learning, architecting, breaking, fixing, reviewing, documenting, and shipping working software.", bg_color="#f8fafc", border_color="#2563eb"))
    story.append(Spacer(1, 5))

    philo_data = [
        ["1. Engineering Depth Meets Articulate Delivery", 
         "A resilient backend that cannot be communicated fails to reach users; conversely, a flashy pitch without software architecture collapses in production. ATLAS rigorously pairs deep, reliable software engineering with storytelling, pitching, UI polish, and demo choreography."],
        ["2. Learning by Building", 
         "Every abstract concept must culminate in a functional codebase. Theory without immediate implementation is quickly forgotten. Members build live utilities from Week 1."],
        ["3. AI with Verification", 
         "AI dramatically accelerates developer velocity, but the human engineer owns 100% of the output. Blind prompt copying is banned; rigorous testing and validation are mandatory."],
        ["4. Ownership Over Transient Participation", 
         "Members do not simply attend lectures; they take active architectural responsibility for specific components, services, or campus utility modules."],
        ["5. Peer Learning & Code Reviews", 
         "Senior members mentor juniors through strict pull-request reviews. No code enters the main branch without passing automated CI linting and peer inspection."],
        ["6. Continuity Over Event Cycles", 
         "Valuable ideas are preserved and supported across academic semesters, building cumulative, institutional intellectual property for MAIT."]
    ]
    story.append(create_table(["Operating Belief", "Institutional Standard & Practice"], philo_data, col_widths=[160, 372]))
    story.append(Spacer(1, 5))

    story.append(Paragraph("What ATLAS is Deliberately NOT", style_h2))
    not_data = [
        ["NOT a Workshop-Only Club", "We do not host isolated 2-hour seminars that leave students with nothing built."],
        ["NOT a Certificate-Farming Org", "Value is derived from public code commits and deployed software, not paper badges."],
        ["NOT a Theory-Only Group", "We prioritize deployable systems over abstract academic slides."],
        ["NOT an Unrealistic Incubator", "We do not claim every student hackathon idea will become a venture-backed startup."]
    ]
    story.append(create_table(["Anti-Pattern", "ATLAS Boundary"], not_data, col_widths=[160, 372]))
    story.append(PageBreak())

    # =========================================================================
    # SLIDE 5 (Page 6): WHAT PROBLEM ARE WE ACTUALLY SOLVING?
    # =========================================================================
    story.extend(header_block(5, "PROBLEM DECOMPOSITION", "Systemic Root Causes vs. ATLAS Structural Interventions"))
    story.append(Paragraph("ATLAS addresses a chained series of structural problems in student technical development rather than treating superficial symptoms:", style_body))
    story.append(Spacer(1, 5))

    problem_matrix = [
        ["Identified Problem", "Underlying Structural Root Cause", "ATLAS Structural Intervention"],
        ["Fragmented AI Exposure", "Tutorials focus on chat prompts without software integration context", "Standardized 4-track curriculum covering LLM APIs, evals, and agents"],
        ["Post-Hackathon Abandonment", "Zero servers, zero funding, and no post-event institutional incentive", "Post-Hackathon Continuation Review & dedicated staging server hosting"],
        ["Absence of Systems Thinking", "Students learn isolated languages without databases, auth, or CI/CD", "Full-stack architecture tracks emphasizing Docker, PostgreSQL, and Linux"],
        ["Inconsistent Momentum in Self-Directed Learning", "Solo self-study lacks peer cadence and support, causing high dropouts", "Weekly structured tracks, peer build jams, and verifiable Git milestones"],
        ["Zero Real-World Exposure", "Projects are toy todo-apps with no real users or stakes", "Vetted external client pipelines and live campus utilities (CampusIQ)"],
        ["Prompting-Only Mindset", "Treating AI as a magical black box rather than an API component", "Rigorous schema validation, tool calling, latency analysis, and guardrails"],
        ["Siloed Student Efforts", "Students work alone or with the same small group repeatedly", "Cross-functional department squads (AI + Frontend + Systems + Product)"],
        ["Knowledge Loss on Graduation", "Graduating seniors take codebase context with them, resetting progress", "Centralized monorepo, comprehensive docs, and formalized junior handover"]
    ]
    story.append(create_table(problem_matrix[0], problem_matrix[1:], col_widths=[130, 195, 207]))
    story.append(Spacer(1, 6))
    story.append(callout_box("<b>Key Takeaway:</b> By addressing the underlying operational and educational root causes, ATLAS creates a predictable, self-sustaining pipeline that turns average student coders into production-ready engineers.", bg_color="#eff6ff", border_color="#2563eb"))
    story.append(PageBreak())

    # =========================================================================
    # SLIDE 6 (Page 7): OUR APPROACH — HOW DO WE SOLVE IT?
    # =========================================================================
    story.extend(header_block(6, "THE OPERATING PIPELINE", "The 8-Stage Learning-to-Engineering Pipeline"))
    story.append(callout_box("<b>The Core Paradigm Shift:</b><br/><b>FROM:</b> Learn passively → Build a fragile hackathon demo → Present slides → Abandon project.<br/><b>TO:</b> Learn fundamentals → Build modularly → Peer review → Deploy to cloud → Maintain & monitor → Contribute back.", bg_color="#eff6ff", border_color="#2563eb"))
    story.append(Spacer(1, 5))

    pipeline_stages = [
        ["1. Selection", "Screen for intellectual curiosity, logical fundamentals, and consistent execution drive rather than prior buzzword familiarity."],
        ["2. Foundation", "Immerse cohort in Python, TypeScript, modern APIs, Git collaboration, and Linux/Docker fundamentals."],
        ["3. Practice", "Enforce weekly hands-on implementation challenges with strict automated linting and unit testing gates."],
        ["4. Code Review", "Conduct rigorous peer reviews evaluating modularity, edge-case handling, secret management, and performance."],
        ["5. Build Squads", "Form multi-disciplinary squads (AI, Product, Systems) tackling vetted campus or client problem statements."],
        ["6. Cloud Deploy", "Deploy hardened applications to isolated staging and production servers with automated SSL and domain routing."],
        ["7. Maintenance", "Establish issue trackers, error observability (Sentry), uptime alerts, and user feedback triage."],
        ["8. Scale & Open Source", "Package reusable utilities as open-source libraries or submit technical papers to academic conferences."]
    ]
    story.append(create_table(["Pipeline Stage", "Operational Execution & Engineering Standards"], pipeline_stages, col_widths=[120, 412]))
    story.append(Spacer(1, 6))
    story.append(Paragraph("Continuous Feedback Loops", style_h2))
    story.append(Paragraph("This pipeline is not a one-way street. Feedback from deployment (monitoring, bug reports, user feedback) directly informs the next cycle's learning tracks, ensuring that curriculum updates remain aligned with production realities.", style_body))
    story.append(PageBreak())

    # =========================================================================
    # SLIDE 7 (Page 8): WHAT ARE THE PRINCIPLES, OUTCOMES & IMPACT?
    # =========================================================================
    story.extend(header_block(7, "GUIDING PRINCIPLES", "Five Architectural Guardrails & Life-Cycle Rigor"))
    story.append(Paragraph("To ensure long-term integrity and engineering excellence, ATLAS enforces five non-negotiable principles:", style_body))
    story.append(Spacer(1, 5))

    principles_data = [
        ["1. Learning Over Hype", "Technology is deeply understood before it is marketed. We study latency, cost per token, and failure modes before adopting any frontier tool."],
        ["2. Execution Over Intention", "A task is only marked complete when working code is committed, tested, reviewed, and deployed. Intentions do not count as deliverables."],
        ["3. Review Over Assumption", "Code and AI-generated outputs are systematically checked before being merged. Never assume an LLM's output is bug-free or secure."],
        ["4. Ownership Over Certificates", "Members are evaluated on code quality, uptime reliability, and team contributions—not on vanity certificates of completion."],
        ["5. Continuity Over Short-Term Wins", "Useful software deserves long-term maintenance. We build software meant to outlast any single graduating batch."]
    ]
    story.append(create_table(["Guiding Principle", "Institutional Mandate"], principles_data, col_widths=[140, 392]))
    story.append(Spacer(1, 5))

    story.append(Paragraph("The High Cost of Inaction (Without ATLAS)", style_h2))
    cost_data = [
        ["Knowledge Fragmentation", "Every student cohort reinvents identical basic prototypes without building cumulative depth."],
        ["Wasted Effort", "Hundreds of hours invested in hackathon prototypes vanish into dead GitHub accounts."],
        ["Unverified AI Adoption", "Students use generative AI blindly, failing technical interviews that probe system internals."],
        ["Missing Campus Utilities", "Institutional friction points persist because no student group builds and maintains campus tools."]
    ]
    story.append(create_table(["Negative Consequence", "Impact on MAIT Ecosystem"], cost_data, col_widths=[140, 392]))
    story.append(Spacer(1, 5))
    story.append(callout_box("<b>The Complete Lifecycle:</b> Learn → Implement → Review → Iterate → Deploy → Maintain → Document → Transfer.", bg_color="#f8fafc", border_color="#64748b"))
    story.append(PageBreak())

    # =========================================================================
    # SLIDE 8 (Page 9): WHAT DOES ATLAS IMPACT?
    # =========================================================================
    story.extend(header_block(8, "STRATEGIC IMPACT", "Multi-Tier Value Creation for Students and MAIT"))
    story.append(Paragraph("ATLAS is intentionally engineered to deliver measurable value to both the individual student and the broader institution:", style_body))
    story.append(Spacer(1, 5))

    impact_matrix = [
        ["Impact Domain", "Student Value & Career Acceleration", "Institutional Value for MAIT"],
        ["Technical Capability", "Production-grade AI, LLMs, Docker, CI/CD, and DB skills", "Recognized regional hub for applied AI engineering excellence"],
        ["Project Depth", "End-to-end deployed systems with live URLs and user metrics", "Portfolio of student-built digital utilities serving campus needs"],
        ["Engineering Rigor", "Hands-on experience with code review, git hygiene, and testing", "Significantly higher placement averages and tier-1 product hires"],
        ["Competitive Edge", "Trained hackathon squads equipped with battle-tested templates", "Substantially increased national and international hackathon wins"],
        ["Open Source / Research", "Public GitHub contributions and authored research papers", "Enhanced NIRF / NAAC innovation and research rating metrics"],
        ["Leadership & Succession", "Experience leading project squads and managing sprint backlogs", "Permanent technical assets and culture immune to senior graduation"],
        ["Client & Problem Exposure", "Experience solving real-world requirements for external users", "Strengthened industry alliances and commercial project credibility"]
    ]
    story.append(create_table(impact_matrix[0], impact_matrix[1:], col_widths=[110, 210, 212]))
    story.append(Spacer(1, 6))
    story.append(callout_box("<b>Empirical Accountability:</b> ATLAS measures actual outputs rather than claiming impact in advance. Year-one numbers represent verified operational targets to be systematically audited at the close of each semester.", bg_color="#eff6ff", border_color="#2563eb"))
    story.append(PageBreak())

    # =========================================================================
    # SLIDE 9 (Page 10): WHAT MODELS DOES ATLAS LEARN FROM?
    # =========================================================================
    story.extend(header_block(9, "BENCHMARK ARCHITECTURES", "Synthesizing the Best Elements of Proven Ecosystems"))
    story.append(Paragraph("ATLAS does not attempt to reinvent organizational dynamics from scratch. Instead, it systematically extracts the most effective mechanisms from four proven institutional models, synthesizing them into a framework tailored for MAIT:", style_body))
    story.append(Spacer(1, 5))

    models_data = [
        ["Institutional Model", "Core Strengths Extracted", "ATLAS Institutional Synthesis"],
        ["Premier Technical Student Societies", "Vibrant community culture, accessible onboarding, peer learning workshops, and energetic technical events.", "Provides the entry-level welcoming funnel (Tier 1: Open ATLAS) for all interested MAIT students across all branches."],
        ["Open-Source Software Communities", "Asynchronous pull-request reviews, public issue trackers, exhaustive documentation, and multi-year project continuity.", "Establishes institutional monorepos, maintainer progression tiers, and transparent code contribution standards."],
        ["High-Velocity Engineering Squads", "Agile weekly sprints, scoped PRDs, automated CI/CD pipelines, strict code quality gates, and SLA ownership.", "Directs advanced project squads (Tier 2: ATLAS Labs) tackling client contracts and campus utilities."],
        ["Competitive Hackathon Culture", "Extreme time-bounded execution, intense creative pressure, multi-disciplinary teamwork, and rapid pitching.", "Acts as the spark for ideation, with high-potential hacks immediately fed into the post-event engineering pipeline."]
    ]
    story.append(create_table(models_data[0], models_data[1:], col_widths=[120, 200, 212]))
    story.append(Spacer(1, 6))
    story.append(Paragraph("The Unique ATLAS Synthesis", style_h2))
    story.append(Paragraph("Most collegiate bodies pick only one: they are either pure event clubs (lots of buzz, little depth) or isolated project teams (high depth, zero community). ATLAS bridges both through its structured two-tier architecture.", style_body))
    story.append(Spacer(1, 5))
    story.append(callout_box("<b>Architectural Result:</b> A welcoming community at the front, powered by a disciplined production engineering engine in the core.", bg_color="#f8fafc", border_color="#2563eb"))
    story.append(PageBreak())

    # =========================================================================
    # SLIDE 10 (Page 11): HOW WILL ATLAS WORK — 12 CORE SYSTEMS?
    # =========================================================================
    story.extend(header_block(10, "OPERATIONAL ARCHITECTURE", "The 12 Core Operating Systems of ATLAS"))
    story.append(Paragraph("To guarantee that the society operates smoothly without chaotic ad-hoc management, ATLAS is structured around 12 modular operating systems:", style_body))
    story.append(Spacer(1, 4))

    systems_data = [
        ["1. Weekly Learning System", "Every week features a defined topic, curated readings, a coding task, and a hard deadline."],
        ["2. Practical Task System", "Members prove mastery through working GitHub pull requests rather than passive attendance."],
        ["3. Technical Review System", "Structured peer code reviews evaluating correctness, edge cases, security, and clean code."],
        ["4. AI Verification System", "Mandatory schema validation (Zod/Pydantic), evals, and unit tests for all AI model outputs."],
        ["5. Automation Lab", "Building high-impact workflow pipelines using webhooks, APIs, and headless integrations."],
        ["6. Project Incubator", "Vetting raw concepts, defining functional PRDs, and assembling multi-disciplinary squads."],
        ["7. Campus Utility Lab", "Designing, deploying, and maintaining digital tools that enhance MAIT student life (CampusIQ)."],
        ["8. Client Project Pipeline", "Sourcing, scoping, and executing legitimate external software and automation contracts."],
        ["9. Hackathon War Room", "Specialized training, boilerplate preparation, and simulation for national hackathons."],
        ["10. Post-Hackathon Continuation", "Structured post-mortem review deciding whether to archive, open-source, or deploy prototypes."],
        ["11. Open-Source & Research Track", "Guiding contributions to global repositories and authoring academic research papers."],
        ["12. Knowledge Transfer System", "Comprehensive documentation and maintainer handovers preventing knowledge rot on graduation."]
    ]
    story.append(create_table(["Operating System", "Functional Mandate & Concrete Mechanism"], systems_data, col_widths=[150, 382]))
    story.append(Spacer(1, 5))
    story.append(callout_box("<b>Operational Decoupling:</b> Each system operates semi-autonomously under designated department leads, ensuring the society never halts if one leader is busy with exams.", bg_color="#eff6ff", border_color="#2563eb"))
    story.append(PageBreak())

    # =========================================================================
    # SLIDE 11 (Page 12): WHAT IS THE ATLAS LEARNING CURRICULUM?
    # =========================================================================
    story.extend(header_block(11, "TECHNICAL SYLLABUS", "The 4-Track Applied Engineering Curriculum"))
    story.append(Paragraph("The ATLAS curriculum is divided into four progressive, production-oriented tracks designed to take students from baseline coders to full-stack AI engineers:", style_body))
    story.append(Spacer(1, 4))

    curr_data = [
        ["Track 1: AI & Modern Foundations", 
         "<b>Core Topics:</b> Python 3.12+ async patterns, modern TypeScript, RESTful API architecture, Git branching conventions, and Docker containerization fundamentals.<br/>"
         "<b>Milestone Deliverable:</b> A containerized RESTful API with automated GitHub Actions CI, unit tests, and OpenAPI documentation."],
        ["Track 2: Applied LLM Engineering", 
         "<b>Core Topics:</b> Token economics, prompt engineering, structured JSON output validation (Pydantic/Zod), function calling, vector embeddings, RAG architectures, and local SLM execution (Ollama).<br/>"
         "<b>Milestone Deliverable:</b> A domain-specific RAG search engine with hybrid dense/sparse retrieval and automated hallucination evaluation benchmarks."],
        ["Track 3: Autonomous AI Agents & Workflows", 
         "<b>Core Topics:</b> State machine agent orchestration (LangGraph), sandboxed tool execution, short/long-term memory, headless browser automation (Playwright), and webhook integration.<br/>"
         "<b>Milestone Deliverable:</b> An autonomous agent capable of monitoring external data feeds, synthesizing summaries, and triggering verified actions."],
        ["Track 4: Production Software Engineering", 
         "<b>Core Topics:</b> Relational database modeling (PostgreSQL), Redis caching, JWT/OAuth authentication, Nginx/Traefik reverse proxies, Linux server administration, and cgroup quotas.<br/>"
         "<b>Milestone Deliverable:</b> A hardened, production-deployed web application running on a public domain with SSL, rate limiting, and uptime observability."]
    ]
    story.append(create_table(["Curriculum Track", "Core Syllabus & Concrete Milestone Deliverable"], curr_data, col_widths=[150, 382]))
    story.append(Spacer(1, 5))
    story.append(callout_box("<b>Strict Pedagogical Standard:</b> Every track concludes with a mandatory, peer-reviewed milestone project. Advancing to subsequent tracks requires a passing grade on the milestone PR.", bg_color="#f8fafc", border_color="#2563eb"))
    story.append(PageBreak())

    # =========================================================================
    # SLIDE 12 (Page 13): HOW WILL HIRING WORK?
    # =========================================================================
    story.extend(header_block(12, "TALENT ACQUISITION", "Merit-Based, Skill-First Recruitment Process"))
    story.append(callout_box("<b>Recruitment Philosophy:</b> ATLAS does not expect first-year applicants to already know advanced AI. We evaluate candidates for <b>logical problem-solving, foundational programming, intellectual curiosity, and demonstrated execution consistency.</b>", bg_color="#eff6ff", border_color="#2563eb"))
    story.append(Spacer(1, 5))

    hiring_funnel = [
        ["1. Expression of Interest", "Open digital application capturing technical interests, problem-solving mindset, and links to existing work."],
        ["2. Algorithmic Logic Screen", "Short aptitude evaluation assessing fundamental logical reasoning, algorithmic thinking, and clarity of thought."],
        ["3. Practical Take-Home Task", "A 72-hour scoped coding challenge (e.g. build a simple script or API) testing independent research ability."],
        ["4. Technical & Culture Interview", "A 20-minute conversation probing candidate's approach to the task, teachability, and passion for engineering."],
        ["5. Merit-Based Selection", "Candidates scored objectively against standardized rubrics across technical and non-technical domains."],
        ["6. Department Allocation", "Matching accepted candidates to one of 12 specialized departments based on demonstrated aptitude."],
        ["7. 4-Week Onboarding Sprint", "New recruits execute basic curriculum tasks alongside senior mentors to establish consistent work habits."],
        ["8. Formal Confirmation", "Full society membership confirmed upon successful completion of the onboarding sprint and first merged PR."]
    ]
    story.append(create_table(["Funnel Stage", "Screening Objective & Operational Standard"], hiring_funnel, col_widths=[140, 392]))
    story.append(Spacer(1, 5))

    story.append(Paragraph("Evaluated Competencies", style_h2))
    story.append(Paragraph("<b>Technical Tracks:</b> Logical problem solving • Core programming fundamentals • Ability to read documentation • Git familiarity • Curiosity.<br/><b>Non-Technical Tracks:</b> Organizational discipline • Articulate written/verbal communication • Design sense • Execution speed.", style_body))
    story.append(PageBreak())

    # =========================================================================
    # SLIDE 13 (Page 14): HOW DOES A MEMBER PROGRESS?
    # =========================================================================
    story.extend(header_block(13, "TALENT LIFECYCLE", "The 8-Stage Member Progression Framework"))
    story.append(Paragraph("ATLAS enforces a transparent, merit-based career progression for every enrolled student. Seniority does not grant status; tangible technical contribution and leadership reliability do:", style_body))
    story.append(Spacer(1, 5))

    prog_data = [
        ["Progression Stage", "Role & Responsibility", "Verifiable Evidence / Exit Gate"],
        ["1. Select", "Recruit undergoing onboarding and baseline orientation", "Passed recruitment screen and onboarding task"],
        ["2. Learn", "Active student in weekly curriculum and practice tasks", "Consistent weekly code submissions in personal repo"],
        ["3. Build", "Contributing modular code to internal society tools", "First functional pull request merged into ATLAS monorepo"],
        ["4. Review", "Conducting peer reviews and writing unit test cases", "Documented code review comments and refactoring PRs"],
        ["5. Project", "Assigned to a dedicated multi-disciplinary project squad", "Ownership of a specific microservice or frontend module"],
        ["6. Deliver", "Deploying features to staging/production cloud servers", "Live deployed feature running with zero critical bugs"],
        ["7. Maintain", "Monitoring production logs, fixing bugs, and triaging issues", "Active resolution of GitHub issues and performance patches"],
        ["8. Lead", "Mentoring junior cohorts and leading project squads", "Appointed Squad Lead or Department Head by Executive Board"]
    ]
    story.append(create_table(prog_data[0], prog_data[1:], col_widths=[90, 222, 220]))
    story.append(Spacer(1, 6))
    story.append(Paragraph("Meritocratic Progression Invariants", style_h2))
    story.append(Paragraph("Every stage has unambiguous exit criteria. If a student demonstrates extraordinary engineering velocity, they can advance rapidly from <i>Learn</i> to <i>Project</i> without bureaucratic delays. Conversely, inactive members are placed on probation regardless of their academic batch.", style_body))
    story.append(Spacer(1, 5))
    story.append(callout_box("<b>Transformation Goal:</b> Student Coder → Disciplined Builder → Production Engineer → Project Maintainer → Technical Mentor.", bg_color="#eff6ff", border_color="#2563eb"))
    story.append(PageBreak())

    # =========================================================================
    # SLIDE 14 (Page 15): WHAT ARE THE CORE DEPARTMENTS?
    # =========================================================================
    story.extend(header_block(14, "ORGANIZATIONAL STRUCTURE", "The 12 Specialized Operating Departments"))
    story.append(Paragraph("ATLAS operates across 12 focused functional departments, dividing technical specialization and operational execution cleanly:", style_body))
    story.append(Spacer(1, 4))

    dept_data = [
        ["1. AI & LLM Engineering", "Model evaluation, prompt engineering, RAG pipelines, fine-tuning, vector stores, and local SLMs."],
        ["2. Automation & Integrations", "Workflow automation, webhooks, n8n/make pipelines, API bridges, and headless browser bots."],
        ["3. Product & Software Eng.", "Full-stack development (Next.js, FastAPI, PostgreSQL), component libraries, and clean architecture."],
        ["4. Systems & Deployment", "Linux server management, Docker containerization, Traefik routing, Coolify, and server security."],
        ["5. Projects & Campus Utilities", "Scoping campus friction points into production utilities; continuous maintenance of CampusIQ."],
        ["6. Business & Client Relations", "Sourcing legitimate external client leads, drafting requirement specs, and managing client delivery."],
        ["7. Research & Open Source", "Benchmarking frontier AI models, authoring conference papers, and contributing to global OSS."],
        ["8. Hackathons & Comp. Eng.", "Hackathon war room drills, reusable boilerplate maintenance, and competitive programming prep."],
        ["9. Learning & Development", "Curating weekly curriculum, grading technical tasks, and running peer doubt-clearing sessions."],
        ["10. Creative & Communications", "UI/UX design systems, brand guidelines, technical documentation, video demos, and social media."],
        ["11. Finance & Sponsorship", "Managing society server budgets, tracking operational expenses, and securing corporate sponsorships."],
        ["12. HR & Operations", "Member attendance tracking, scheduling build sessions, internal communications, and team welfare."]
    ]
    story.append(create_table(["Department Name", "Core Technical / Operational Mandate"], dept_data, col_widths=[150, 382]))
    story.append(Spacer(1, 5))
    story.append(callout_box("<b>Cross-Functional Collaboration:</b> Real projects are never built by single departments. A project squad pulls engineers from AI, Product, Systems, and Creative to build complete systems.", bg_color="#f8fafc", border_color="#2563eb"))
    story.append(PageBreak())

    # =========================================================================
    # SLIDE 15 (Page 16): GOVERNANCE & EXECUTIVE LEADERSHIP
    # =========================================================================
    story.extend(header_block(15, "GOVERNANCE & LEADERSHIP", "Institutional Oversight & Executive Leadership Structure"))
    story.append(Paragraph("The governance framework balances academic oversight from faculty with agile, disciplined student execution. Executive roles are assigned strictly based on proven leadership and technical capability:", style_body))
    story.append(Spacer(1, 5))

    gov_data = [
        ["Governance Layer", "Designation", "Appointed Leader / Body", "Primary Responsibility"],
        ["Advisory", "Faculty Advisor", "Senior CSE Faculty (HOD Nominee)", "Institutional compliance, policy oversight, and administrative liaison."],
        ["Advisory", "Faculty Coordinator", "CSE Department Representative", "Event approvals, campus venue coordination, and official institute liaison."],
        ["Executive Board", "Society President", "Garv Goyal", "Overall strategic vision, society representation, external partnerships, and executive leadership."],
        ["Executive Board", "Vice President", "Tanmay Jain", "Operational execution, cross-departmental coordination, engineering standards, and project delivery."],
        ["Operations", "General Secretary", "Operations Lead", "Official documentation, meeting minutes, scheduling, and compliance records."],
        ["Technical", "Technical Director", "Technical Lead", "Engineering standards, architecture reviews, CI/CD gates, and security audits."],
        ["Divisional", "Department Heads", "12 Appointed Student Leads", "Day-to-day execution, weekly task grading, and sprint backlog management."]
    ]
    story.append(create_table(gov_data[0], gov_data[1:], col_widths=[85, 100, 140, 207]))
    story.append(Spacer(1, 6))

    story.append(Paragraph("Checks, Balances & Administrative Prerogative", style_h2))
    story.append(Paragraph("• <b>Faculty Veto Authority:</b> The Faculty Advisor retains full oversight and veto power over all external client engagements, public communications, and financial decisions.<br/>• <b>Constitutional Term Limits:</b> Student executive terms are fixed for one academic year, with mandatory successor grooming.<br/>• <b>Transparent Audit Trails:</b> All society finances, server costs, and project milestones are logged in open digital records.", style_body))
    story.append(Spacer(1, 5))
    story.append(callout_box("<b>Leadership Commitment:</b> The executive board operates with total transparency, serving as stewards of MAIT's engineering prestige.", bg_color="#eff6ff", border_color="#2563eb"))
    story.append(PageBreak())

    # =========================================================================
    # SLIDE 16 (Page 17): WHY A PRODUCTION-FIRST AI SOCIETY?
    # =========================================================================
    story.extend(header_block(16, "PEDAGOGICAL DIFFERENTIATOR", "Tutorial Prompters vs. Production AI Engineers"))
    story.append(Paragraph("Industry hiring has shifted dramatically. Companies no longer seek students who can merely prompt chat models. They seek engineers who understand how to build reliable, fault-tolerant software around AI components:", style_body))
    story.append(Spacer(1, 5))

    prod_matrix = [
        ["Technical Dimension", "Conventional Student AI Club", "The ATLAS Production Engineering Standard"],
        ["Prompt Engineering", "Vague chat prompts with unpredictable, brittle outputs", "Few-shot templates with strict Pydantic/Zod schema enforcement"],
        ["AI Agents", "Toy scripts calling LLM APIs without tools or guardrails", "Stateful agent graphs (LangGraph) with retry loops and circuit breakers"],
        ["Workflow Automation", "Static screenshots of no-code automation builders", "Headless webhooks, asynchronous queues, and error-handled bridges"],
        ["Code Verification", "Blindly accepting and pasting AI-generated boilerplate", "Mandatory unit tests, deterministic type checks, and security audits"],
        ["Deployment", "Localhost port running on an individual laptop", "Containerized Docker microservices running behind Traefik SSL on cloud VPS"],
        ["Error Handling", "App crashes silently when an API hits a rate limit or 500 error", "Exponential backoff retries, fallback models, and cached responses"],
        ["Knowledge Retention", "Individual experiments forgotten after a semester", "Centralized monorepo, versioned architecture docs, and maintainer runbooks"]
    ]
    story.append(create_table(prod_matrix[0], prod_matrix[1:], col_widths=[110, 205, 217]))
    story.append(Spacer(1, 6))
    story.append(callout_box("<b>The Core Realization:</b> The barrier to writing code has collapsed; the barrier to verifying, securing, and maintaining code has skyrocketed. ATLAS trains engineers who thrive in this new reality.", bg_color="#eff6ff", border_color="#2563eb"))
    story.append(PageBreak())

    # =========================================================================
    # SLIDE 17 (Page 18): HOW WILL REAL CLIENT PROJECTS WORK?
    # =========================================================================
    story.extend(header_block(17, "PROFESSIONAL ENGAGEMENT", "The 10-Step Scoped Client Project Pipeline"))
    story.append(Paragraph("To give advanced students legitimate real-world software engineering experience, ATLAS operates a disciplined, 10-step client engagement pipeline governed by strict institutional guardrails:", style_body))
    story.append(Spacer(1, 4))

    client_steps = [
        ["1. Lead Discovery", "Business & Client Relations identifies genuine workflow automation bottlenecks in external SMEs or startups."],
        ["2. Scoping Interview", "Technical leads conduct structured interviews to define unambiguous functional requirements and constraints."],
        ["3. PRD & Specification", "A formal Product Requirements Document (PRD) is drafted, outlining exact deliverables, tech stack, and timeline."],
        ["4. Feasibility & Safety Audit", "Systems team reviews data security, compliance, and privacy constraints to guarantee zero institutional liability."],
        ["5. Faculty Approval", "Project charter and scope submitted to Faculty Advisor for formal institutional authorization."],
        ["6. Squad Allocation", "A dedicated 3–4 person project squad is assembled under an experienced Technical Lead."],
        ["7. Sprint Execution", "Development executed in 1-week agile sprints with continuous Git progress and staged client demos."],
        ["8. Security & Testing Audit", "Comprehensive end-to-end integration tests, secret sanitization, and stress testing before release."],
        ["9. Handover & Deployment", "Deploying software to client-owned infrastructure alongside comprehensive documentation and user training."],
        ["10. Post-Delivery SLA", "30-day bug-fix warranty window followed by formal project sign-off and retrospective documentation."]
    ]
    story.append(create_table(["Pipeline Step", "Execution Rigor & Operational Standard"], client_steps, col_widths=[130, 402]))
    story.append(Spacer(1, 5))

    story.append(Paragraph("Non-Negotiable Institutional Boundaries", style_h2))
    story.append(Paragraph("• <b>Zero Unauthorized Access:</b> ATLAS will never interact with systems or data without formal written consent.<br/>• <b>Privacy First:</b> No client data is ever stored on personal devices; all secrets reside in secure cloud vaults.<br/>• <b>Institutional Primacy:</b> Client projects must never interfere with students' academic obligations or exams.", style_body))
    story.append(PageBreak())

    # =========================================================================
    # SLIDE 18 (Page 19): WHAT HAPPENS TO HACKATHON PROJECTS AFTER THE EVENT?
    # =========================================================================
    story.extend(header_block(18, "POST-EVENT CONTINUITY", "The Post-Hackathon Continuation Review"))
    story.append(Paragraph("Thousands of hours of brilliant student development are lost every year because hackathons end at the podium. ATLAS introduces the <b>Post-Hackathon Continuation Review</b> to salvage high-potential codebases:", style_body))
    story.append(Spacer(1, 5))

    hackathon_review = [
        ["Diagnostic Question", "Evaluation Metric", "Resulting Action Pipeline"],
        ["1. Problem Authenticity", "Does the prototype address a genuine, persistent friction point?", "YES → Advance to Scoping; NO → Archive with post-mortem notes"],
        ["2. Stakeholder Demand", "Is there an identifiable campus or external group that needs this?", "CAMPUS → Route to Campus Utility Lab; EXTERNAL → Client exploration"],
        ["3. Code Health", "Is the architecture salvageable, or is it disposable hackathon glue?", "CLEAN → Refactor & test; SPAGHETTI → 1-week rewrite sprint"],
        ["4. Deployment Feasibility", "Can it run reliably within low-cost, sandboxed server limits?", "FEASIBLE → Provision staging subdomain on Coolify sandbox"],
        ["5. Team Commitment", "Does the student team commit to maintaining it for 60+ days?", "COMMITTED → Assign maintainer title; UNCOMMITTED → Handover to juniors"],
        ["6. Long-Term Value", "Does it offer open-source, research, or commercial viability?", "HIGH → Package for GitHub release or draft conference paper"]
    ]
    story.append(create_table(hackathon_review[0], hackathon_review[1:], col_widths=[120, 202, 210]))
    story.append(Spacer(1, 6))

    story.append(Paragraph("Possible Post-Event Pathways", style_h2))
    story.append(Paragraph("<b>1. Official Campus Utility:</b> Hardened and deployed for MAIT students (e.g. CampusIQ).<br/><b>2. Open-Source Package:</b> Published to GitHub/NPM/PyPI as a reusable developer library.<br/><b>3. Research Paper:</b> Expanded into an empirical study with benchmarks for academic conference submission.<br/><b>4. Portfolio Deep-Dive:</b> Cleaned up and documented as a standout case study for placement interviews.", style_body))
    story.append(Spacer(1, 5))
    story.append(callout_box("<b>Culture Shift:</b> Hackathons at MAIT will no longer be graveyards of half-built demos; they will be the inception points for durable software.", bg_color="#eff6ff", border_color="#2563eb"))
    story.append(PageBreak())

    # =========================================================================
    # SLIDE 19 (Page 20): HOW WILL ATLAS MEASURE IMPACT & PROVE CONCEPT?
    # =========================================================================
    story.extend(header_block(19, "ACCOUNTABILITY & METRICS", "Objective, Data-Driven Performance Scorecard"))
    story.append(Paragraph("ATLAS rejects vanity metrics like social media likes or seminar headcounts. We hold ourselves accountable to verifiable, data-driven engineering key performance indicators (KPIs):", style_body))
    story.append(Spacer(1, 5))

    kpi_data = [
        ["Performance Dimension", "Target Year-One Metric", "Verifiable Audit Trail & Evidence"],
        ["Curriculum Completion", "85%+ completion across enrolled cohorts", "Public GitHub task repositories with passing automated CI test suites"],
        ["Software Repositories", "10+ hardened, production-grade repositories", "Active commit histories, merged pull requests, and peer review threads"],
        ["Project Longevity", "4+ projects actively maintained 6+ months post-build", "Live public uptime status pages, incident changelogs, and release tags"],
        ["Infrastructure Reliability", "99.5%+ uptime on all deployed campus utilities", "Real-time health check dashboards and automated uptime monitoring"],
        ["Competition Excellence", "5+ podium finishes in major external hackathons", "Official hackathon certificates, prize citations, and project repositories"],
        ["Open-Source Contribution", "1+ published open-source tool or upstream PR", "GitHub release tags, documentation websites, and community downloads"],
        ["Campus Utility Adoption", "1,000+ active MAIT student users on utilities", "Anonymized platform access logs, user query counts, and feedback ratings"],
        ["Member Placement Impact", "100% of graduating senior leads placed in core tech", "Placement records in high-tier product engineering and AI startup roles"]
    ]
    story.append(create_table(kpi_data[0], kpi_data[1:], col_widths=[115, 175, 242]))
    story.append(Spacer(1, 6))
    story.append(callout_box("<b>Semi-Annual Transparency Report:</b> At the end of each semester, ATLAS will submit a comprehensive audit report to the Head of Department, documenting every project, budget line, and student milestone.", bg_color="#f8fafc", border_color="#2563eb"))
    story.append(PageBreak())

    # =========================================================================
    # SLIDE 20 (Page 21): WHAT IS THE TWO-TIER ACTIVITY MODEL?
    # =========================================================================
    story.extend(header_block(20, "MEMBERSHIP ARCHITECTURE", "Balancing Broad Accessibility with Deep Technical Focus"))
    story.append(Paragraph("A major flaw in university societies is choosing between being an exclusive club (alienating the majority) or a chaotic open group (preventing serious engineering). ATLAS resolves this tension through a <b>Two-Tier Membership Model</b>:", style_body))
    story.append(Spacer(1, 5))

    tiers_data = [
        ["Architectural Dimension", "Tier 1: Open ATLAS (Community Track)", "Tier 2: ATLAS Labs (Core Engineering Squad)"],
        ["Target Audience", "Open to all MAIT students across all engineering branches", "Vetted, highly committed student builders (15–30 members)"],
        ["Barrier to Entry", "Zero prerequisites; open digital registration", "Rigorous application, coding challenge, and technical interview"],
        ["Core Activities", "Interactive workshops, AI build nights, hackathon war rooms", "Production sprints, client contracts, cloud deployments, research"],
        ["Time Commitment", "2–4 hours/week (flexible, event-based participation)", "8–12 hours/week (mandatory sprint deliverables and reviews)"],
        ["Pedagogical Focus", "Foundations: Python basics, API calls, prompting, tools", "Systems: Docker, LangGraph, databases, CI/CD, cgroup security"],
        ["Infrastructure Access", "Community Discord, public repositories, workshop notebooks", "Cloud server access, deployment keys, private repos, staging URLs"],
        ["Expected Deliverable", "Personal portfolio utilities and enhanced technical awareness", "Production-grade campus utilities and maintained client software"]
    ]
    story.append(create_table(tiers_data[0], tiers_data[1:], col_widths=[110, 210, 212]))
    story.append(Spacer(1, 6))
    story.append(Paragraph("The Symbiotic Talent Flywheel", style_h2))
    story.append(Paragraph("Tier 1 operates as the continuous talent identification funnel. Active participants who shine in Open ATLAS build nights and complete beginner challenges are fast-tracked into Tier 2. In return, Tier 2 engineers mentor Tier 1 newcomers, creating a self-sustaining cycle.", style_body))
    story.append(Spacer(1, 5))
    story.append(callout_box("<b>Institutional Result:</b> Massive campus-wide educational impact without compromising elite production software engineering.", bg_color="#eff6ff", border_color="#2563eb"))
    story.append(PageBreak())

    # =========================================================================
    # SLIDE 21 (Page 22): TIER 1 ACTIVITIES — PART 1
    # =========================================================================
    story.extend(header_block(21, "COMMUNITY EVENTS (PART 1)", "Tier 1: Hands-On Educational Workshops & Build Nights"))
    story.append(Paragraph("Open ATLAS activities are engineered to be 100% practical. We ban passive slideshow lectures in favor of real-time coding sprints where every attendee leaves with working software:", style_body))
    story.append(Spacer(1, 5))

    t1_p1_data = [
        ["Event Format", "Operational Cadence & Methodology", "Tangible Student Deliverable"],
        ["1. AI Zero-to-One", 
         "<b>Duration:</b> 2 Hours | <b>Cadence:</b> Monthly<br/>"
         "Demystifies LLM fundamentals: tokens, temperature, context windows, and API authentication. Zero slides; attendees write Python scripts making authenticated API calls in VS Code.",
         "A working Python application that queries frontier LLMs with structured parameters and handles API errors gracefully."],
        ["2. Prompt-to-Product", 
         "<b>Duration:</b> 3 Hours | <b>Cadence:</b> Bi-Monthly<br/>"
         "Takes students from an empty directory to a deployed web utility. Combines modern UI primitives (shadcn), Next.js, and free-tier AI APIs (Gemini/Groq) to build interactive AI apps.",
         "A fully functional, mobile-responsive web app deployed to a public Vercel URL that attendees can showcase immediately."],
        ["3. Automation Build Night", 
         "<b>Duration:</b> 3 Hours (Friday Evening) | <b>Cadence:</b> Bi-Monthly<br/>"
         "Hands-on sprint focused on workflow automation. Attendees connect webhooks, Google Sheets, Discord bots, and email triggers using self-hosted n8n and Python scripts.",
         "An active automation pipeline that listens for live events, processes data automatically, and dispatches formatted alerts."]
    ]
    story.append(create_table(t1_p1_data[0], t1_p1_data[1:], col_widths=[120, 230, 182]))
    story.append(Spacer(1, 6))
    story.append(callout_box("<b>Strict Pedagogical Rule:</b> If an attendee cannot run the code on their own machine by the end of the session, the workshop is considered a failure. We measure success by working local environments.", bg_color="#f8fafc", border_color="#2563eb"))
    story.append(PageBreak())

    # =========================================================================
    # SLIDE 22 (Page 23): TIER 1 ACTIVITIES — PART 2
    # =========================================================================
    story.extend(header_block(22, "COMMUNITY EVENTS (PART 2)", "Tier 1: Competitions, Quality Audits & Career Prep"))
    story.append(Paragraph("The second cluster of Tier 1 activities focuses on competitive engineering, code quality, and professional readiness:", style_body))
    story.append(Spacer(1, 5))

    t1_p2_data = [
        ["Event Format", "Operational Cadence & Methodology", "Tangible Student Deliverable"],
        ["4. Hackathon War Room", 
         "<b>Duration:</b> 48-Hour Weekend Sprint | <b>Cadence:</b> Pre-Major Hackathons<br/>"
         "Rigorous simulation drill before national events (SIH, internal hackathons). Teams practice rapid architectural scoping, battle-tested boilerplates, and pitching choreography.",
         "A fully initialized, production-ready codebase with auth, database, and UI scaffolding operational in under 3 hours."],
        ["5. Campus Bug Bash", 
         "<b>Duration:</b> 4 Hours | <b>Cadence:</b> Pre-Release Cycle<br/>"
         "Gamified campus-wide stress-testing of ATLAS internal utilities. Students compete to discover edge cases, security flaws, UI breaks, and API rate-limit vulnerabilities.",
         "Formatted bug reports logged directly in GitHub Issues with reproducible steps, helping harden campus software."],
        ["6. Portfolio Autopsy", 
         "<b>Duration:</b> 2 Hours | <b>Cadence:</b> Semester End<br/>"
         "Line-by-line, constructive code audit of student GitHub profiles and resumes by senior leads. We dismantle tutorial clutter and help students highlight real engineering metrics.",
         "An actionable refactoring checklist transforming low-signal GitHub repos into high-impact engineering case studies."]
    ]
    story.append(create_table(t1_p2_data[0], t1_p2_data[1:], col_widths=[120, 230, 182]))
    story.append(Spacer(1, 6))
    story.append(callout_box("<b>Industry Alignment:</b> Portfolio Autopsies directly reflect the criteria used by tier-1 tech recruiters, helping MAIT students stand out in off-campus hiring funnels.", bg_color="#eff6ff", border_color="#2563eb"))
    story.append(PageBreak())

    # =========================================================================
    # SLIDE 23 (Page 24): TIER 2 — ATLAS LABS & FLAGSHIP PROGRAMS
    # =========================================================================
    story.extend(header_block(23, "ADVANCED ENGINEERING", "Tier 2: ATLAS Labs Specialized Innovation Incubators"))
    story.append(Paragraph("ATLAS Labs represents the core production engine of the society. It brings together vetted, dedicated student engineers across three specialized technical incubators:", style_body))
    story.append(Spacer(1, 5))

    labs_data = [
        ["Specialized Lab", "Core Technical Mandate & Tooling", "Flagship Benchmark Output"],
        ["1. AI & Automation Lab", 
         "Orchestrating autonomous multi-agent state machines, local SLM inference (Ollama), headless browser automations (Playwright), vector search, and custom tool-calling agents.",
         "Automated syllabus analysis and timetable conflict resolution assistant with verified document citations."],
        ["2. Campus Utilities Lab", 
         "Architecting, hardening, and maintaining production software that directly serves MAIT students and faculty. Enforces strict full-stack patterns: Next.js, PostgreSQL, and Redis.",
         "<b>CampusIQ:</b> The unified academic intelligence suite featuring attendance tracking, marksheet vaults, and stealth admin."],
        ["3. Systems & Infrastructure Lab", 
         "Managing Linux production servers, Traefik reverse proxies, Docker container orchestration, SSL certificates, automated database backups, and cgroup resource quotas.",
         "Self-hosted PaaS (Coolify) providing isolated staging environments and 256MB sandboxes for all student projects."]
    ]
    story.append(create_table(labs_data[0], labs_data[1:], col_widths=[125, 235, 172]))
    story.append(Spacer(1, 6))

    story.append(Paragraph("Tier 2 Operating Standards", style_h2))
    story.append(Paragraph("• <b>Mandatory Sprint Cycles:</b> 2-week agile sprints with bi-weekly sprint demos and code reviews.<br/>• <b>Production CI/CD:</b> All code must pass linting, TypeScript typing, and automated unit tests before merge.<br/>• <b>On-Call Rotation:</b> Dedicated student maintainers monitor uptime and handle critical bugs for live services.", style_body))
    story.append(Spacer(1, 5))
    story.append(callout_box("<b>Excellence Invariant:</b> Code developed in ATLAS Labs must be good enough to deploy to real users with real uptime guarantees.", bg_color="#f8fafc", border_color="#2563eb"))
    story.append(PageBreak())

    # =========================================================================
    # SLIDE 24 (Page 25): WHAT IS THE FLAGSHIP CAMPUS PROJECT MODEL? (CampusIQ)
    # =========================================================================
    story.extend(header_block(24, "FLAGSHIP PROJECT CASE STUDY", "CampusIQ: The Unified MAIT Academic & Attendance Intelligence Suite"))
    story.append(callout_box("<b>Case Study Benchmark:</b> CampusIQ serves as the gold-standard reference implementation of the ATLAS engineering philosophy—solving real student pain-points through secure, resilient, and beautiful software.", bg_color="#eff6ff", border_color="#2563eb"))
    story.append(Spacer(1, 5))

    campusiq_data = [
        ["Subsystem Module", "Underlying Software Architecture", "Practical Student & Admin Value"],
        ["Edumarshal Attendance Radar", 
         "Headless automated session synchronization with college portal. Calculates real-time percentages, safe-bunk limits, and critical attendance alerts without storing plain passwords.",
         "Eliminates slow, frustrating portal logins; provides instant mobile-friendly attendance tracking and schedule alerts."],
        ["ExamWeb Relational Marksheets Store", 
         "High-performance relational schema indexing historical semester grades, internal assessment marks, and backlogs. Enables instant GPA/CGPA projections and distribution curves.",
         "Replaces sluggish, fragmented university portals with sub-50ms instant cached transcript lookups and performance analytics."],
        ["AES-256 Security & Session Vault", 
         "Zero plaintext credential storage. Hardware-isolated AES-256-GCM encryption for student tokens, automated session rotation, 30-day persistent login, and strict CSRF protection.",
         "Enterprise-grade security ensuring absolute student data privacy, protecting against credential theft or leakage."],
        ["Stealth Master Admin Panel", 
         "Role-based access control (RBAC) dashboard hidden from public navigation. Real-time student search, aggregate attendance trends, system load metrics, and sync override controls.",
         "Empowers authorized faculty and administrators to audit system health, monitor trends, and assist students efficiently."]
    ]
    story.append(create_table(campusiq_data[0], campusiq_data[1:], col_widths=[125, 235, 172]))
    story.append(Spacer(1, 5))
    story.append(Paragraph("Engineering Invariants Proven by CampusIQ", style_h2))
    story.append(Paragraph("CampusIQ proves that MAIT students can build enterprise-tier software. It features sub-second load times, 30-day persistent sessions, zero password leaks, and graceful degradation during portal downtimes.", style_body))
    story.append(PageBreak())

    # =========================================================================
    # SLIDE 25 (Page 26): WHAT IS THE ATLAS BUILD CYCLE?
    # =========================================================================
    story.extend(header_block(25, "ENGINEERING LIFECYCLE", "The 7-Stage Rigorous Software Development Lifecycle"))
    story.append(Paragraph("A project is never deemed complete simply because it runs once on localhost. ATLAS enforces a 7-stage software development lifecycle (SDLC) with strict exit gates at every milestone:", style_body))
    story.append(Spacer(1, 5))

    sdlc_data = [
        ["SDLC Phase", "Engineering Actions & Methodologies", "Mandatory Quality Exit Gate"],
        ["1. Identify", "Discover genuine campus or business friction through user interviews and data analysis.", "Written 1-page Problem Statement approved by Project Lead"],
        ["2. Specify", "Define functional user stories, edge cases, system constraints, and acceptance criteria.", "Formal Product Requirements Document (PRD) & wireframes"],
        ["3. Architect", "Select stack, design PostgreSQL schemas, evaluate latency, and map API contracts.", "Architecture diagram & Zod/OpenAPI contract specification"],
        ["4. Build", "Implement modular code in feature branches with strict Git commit hygiene.", "Clean codebase with passing local builds, linters, and unit tests"],
        ["5. Review", "Mandatory 2-person peer code review probing security, edge cases, and typing.", "Formal approval from Technical Lead on GitHub Pull Request"],
        ["6. Deploy", "Automated CI/CD container build pushing to staging, running smoke tests, then prod.", "Zero-downtime deployment with verified health-check endpoint"],
        ["7. Maintain", "Monitor server logs, error tracking (Sentry), uptime metrics, and user bug tickets.", "Bi-weekly patch releases and bug resolution within SLA targets"]
    ]
    story.append(create_table(sdlc_data[0], sdlc_data[1:], col_widths=[90, 242, 200]))
    story.append(Spacer(1, 6))
    story.append(callout_box("<b>The ATLAS Definition of Done:</b> A feature is NOT done when the code is written. It is done when it is tested, reviewed, deployed behind SSL, monitored with alerts, and documented.", bg_color="#eff6ff", border_color="#2563eb"))
    story.append(PageBreak())

    # =========================================================================
    # SLIDE 26 (Page 27): WHAT IS THE WEEKLY OPERATING SYSTEM?
    # =========================================================================
    story.extend(header_block(26, "OPERATIONAL RHYTHM", "The 7-Day Synchronized Engineering Rhythm"))
    story.append(Paragraph("Consistency is the cornerstone of engineering excellence. ATLAS operates on a predictable 7-day heartbeat that synchronizes learning, coding, reviewing, and deployment:", style_body))
    story.append(Spacer(1, 5))

    weekly_cadence = [
        ["Day / Window", "Synchronized Operational Activity", "Responsible Lead & Deliverable"],
        ["Monday Morning", "Weekly Sprint Kickoff — New curriculum module, readings, and coding challenge released.", "Learning & Development Head (Module Release)"],
        ["Tue – Wed", "Deep Work & Implementation — Members build tasks independently and collaborate in squads.", "Department Leads (Async Code Guidance)"],
        ["Thursday Evening", "Mid-Sprint Office Hours — Live hands-on debugging, architectural Q&A, and unblocking.", "Technical Director (Technical Unblocking)"],
        ["Friday Midnight", "Hard Submission Deadline — Pull requests opened against official society repositories.", "HR & Operations (Submission Tracking)"],
        ["Saturday Afternoon", "Technical Review & Showcase — Live peer code reviews, architectural feedback, and demos.", "Executive Board (Live Demos & Feedback)"],
        ["Sunday", "Retrospective & System Reset — Staging deployments, leaderboard update, and syllabus prep.", "President & Vice President (Sprint Closeout)"]
    ]
    story.append(create_table(weekly_cadence[0], weekly_cadence[1:], col_widths=[110, 242, 180]))
    story.append(Spacer(1, 6))

    story.append(Paragraph("The Central ATLAS Digital Portal", style_h2))
    story.append(Paragraph("All weekly operations are managed through a centralized digital workspace displaying: Active Sprint Week • Learning Resources • Task Briefs & Deadlines • Automated PR Grading Status • Project Uptime Monitors • Departmental Leaderboards.", style_body))
    story.append(Spacer(1, 5))
    story.append(callout_box("<b>Predictability:</b> By standardizing deadlines on Friday midnight and reviews on Saturday, members plan their academic and society work with zero scheduling friction.", bg_color="#f8fafc", border_color="#2563eb"))
    story.append(PageBreak())

    # =========================================================================
    # SLIDE 27 (Page 28): WHAT DOES ATLAS OFFER MEMBERS?
    # =========================================================================
    story.extend(header_block(27, "STUDENT VALUE PROPOSITION", "The Comprehensive Value Proposition for Enrolled Members"))
    story.append(Paragraph("ATLAS provides members with an unmatched competitive advantage, transforming them from passive students into elite software engineers:", style_body))
    story.append(Spacer(1, 5))

    member_offers = [
        ["1. Frontier AI & LLM Mastery", "Deep practical experience with agents, embeddings, RAG, and vector databases beyond superficial prompt engineering."],
        ["2. Production Systems Fluency", "Hands-on mastery of Docker, Linux VPS administration, CI/CD pipelines, reverse proxies, and database indexing."],
        ["3. Verifiable Public Portfolio", "Live web applications with real users and public GitHub commit histories, replacing generic clone projects."],
        ["4. Structured Peer Cadence", "Overcoming self-study dropouts through synchronized weekly sprints, office hours, and active mentorship."],
        ["5. Hackathon Supremacy", "Access to production-tested boilerplates, rapid design primitives, and war room drills that maximize win rates."],
        ["6. Real-World Client Exposure", "Opportunities to work on scoped commercial projects for external clients, gaining client-facing experience."],
        ["7. Rigorous Code Review", "Direct, constructive line-by-line feedback on coding conventions, security patterns, and software modularity."],
        ["8. Open-Source Contributions", "Guided upstream contributions to global open-source libraries, building international developer credibility."],
        ["9. Technical Leadership", "Experience managing sprint backlogs, leading cross-functional project squads, and conducting technical screens."],
        ["10. The Transformation Pipeline", "A clear developmental path: Learner → Builder → Production Engineer → Project Maintainer → Technical Mentor."]
    ]
    story.append(create_table(["Student Benefit", "Detailed Practical Advantage"], member_offers, col_widths=[150, 382]))
    story.append(Spacer(1, 5))
    story.append(callout_box("<b>Career Impact:</b> ATLAS alumni will not graduate wondering if they can pass technical interviews—they will enter interviews with deployed systems, verified commits, and proven architectural judgment.", bg_color="#eff6ff", border_color="#2563eb"))
    story.append(PageBreak())

    # =========================================================================
    # SLIDE 28 (Page 29): WHAT DOES ATLAS OFFER MAIT?
    # =========================================================================
    story.extend(header_block(28, "INSTITUTIONAL VALUE", "Strategic Institutional ROI for Maharaja Agrasen Institute of Technology"))
    story.append(Paragraph("ATLAS directly advances MAIT's strategic educational mission, prestige, and institutional capabilities:", style_body))
    story.append(Spacer(1, 5))

    mait_offers = [
        ["Strategic Institutional Asset", "Operational Mechanism", "Tangible Value Delivered to MAIT"],
        ["Center of AI Excellence", 
         "Establishes a recognized, student-led hub for modern AI, automation, and full-stack software engineering on campus.",
         "Enhances institutional prestige in technical rankings, NBA/NAAC accreditations, and media coverage."],
        ["Sustainable Campus Utilities", 
         "Student squads build and maintain high-utility internal tools (like CampusIQ) that solve campus friction.",
         "Saves departmental software procurement costs while streamlining student information access."],
        ["Elevated Placement Outcomes", 
         "Graduates possess verified production deployments, live domains, and enterprise-grade architecture skills.",
         "Attracts Tier-1 tech recruiters, driving up average salary packages and elite off-campus placements."],
        ["National Competition Laurels", 
         "Coordinated hackathon squads represent MAIT at Smart India Hackathon and prestigious national hackathons.",
         "Brings high-profile trophies, cash prizes, and institutional acclaim back to the college."],
        ["Zero-Cost Innovation Engine", 
         "Self-funded operational model requiring zero initial capital outlay from the college administration.",
         "Generates immense intellectual property and student skill development with maximum capital efficiency."],
        ["Permanent Technical Continuity", 
         "Centralized monorepos and successor documentation prevent student knowledge from vanishing upon graduation.",
         "Ensures institutional codebases remain active and maintained across successive academic batches."]
    ]
    story.append(create_table(mait_offers[0], mait_offers[1:], col_widths=[125, 205, 202]))
    story.append(Spacer(1, 6))
    story.append(callout_box("<b>Win-Win Partnership:</b> ATLAS asks for institutional guidance and permission; in return, it delivers cutting-edge software, student accolades, and permanent technical infrastructure.", bg_color="#f8fafc", border_color="#2563eb"))
    story.append(PageBreak())

    # =========================================================================
    # SLIDE 29 (Page 30): WHAT IS THE ROI & IMPLEMENTATION MODEL? (Infrastructure & Financials)
    # =========================================================================
    story.extend(header_block(29, "INFRASTRUCTURE & ROI", "Two-Server Blast-Radius Isolation Architecture & Operating Budget"))
    story.append(callout_box("<b>Strict Architectural Blast-Radius Isolation:</b> To ensure that experimental student code can never crash critical production campus utilities, ATLAS enforces a physical two-server isolation model.", bg_color="#eff6ff", border_color="#2563eb"))
    story.append(Spacer(1, 5))

    infra_data = [
        ["Server Node", "Hardware Specifications & Tooling", "Workload & Blast-Radius Protection Guarantee"],
        ["Server 1: Production Core Node", 
         "<b>Hetzner CX22:</b> 2 vCPU AMD, 4 GB ECC RAM, 40 GB NVMe SSD, 20 TB Bandwidth, Ubuntu 24.04 LTS.<br/>"
         "Docker Compose, Traefik reverse proxy, Let's Encrypt SSL, automated offsite PostgreSQL backups.",
         "Dedicated strictly to <b>CampusIQ</b> and mission-critical campus tools. <b>Zero student sandbox code allowed.</b> 99.9% uptime guarantee with isolated network routing."],
        ["Server 2: Student Sandbox Node", 
         "<b>Hetzner CPX31:</b> 4 vCPU AMD, 8 GB RAM, 80 GB NVMe SSD, 20 TB Bandwidth, Coolify PaaS platform.<br/>"
         "Automated branch previews, git-push deployments, staging subdomains, automated SSL routing.",
         "Dedicated to student hackathon prototypes, staging apps, and experiments. <b>Strict Docker cgroup limits: Max 256MB RAM & 0.5 CPU per container</b> to prevent memory leaks from affecting others."]
    ]
    story.append(create_table(infra_data[0], infra_data[1:], col_widths=[120, 215, 197]))
    story.append(Spacer(1, 5))

    story.append(Paragraph("Financial Sustainability Models", style_h2))
    fin_data = [
        ["Operating Model", "Infrastructure Setup & Costs", "Financial Implication for MAIT"],
        ["Model A: Self-Funded (Default)", 
         "Both servers rented on Hetzner Cloud.<br/>"
         "Combined Cost: Approx. EUR 15–18/mo (~<b>INR 1,700 / month</b> total).",
         "<b>Funded 100% internally by ATLAS executive pool / student sponsorships.</b> Requires <b>INR 0</b> from college budget."],
        ["Model B: College Lab Supported", 
         "MAIT allocates an unused desktop machine (Core i5/i7, 16GB RAM) in a college lab with a static local IP and UPS backup.",
         "<b>Zero cloud expenditure (INR 0 / month).</b> Repurposes existing institutional hardware for immense educational ROI."]
    ]
    story.append(create_table(fin_data[0], fin_data[1:], col_widths=[120, 255, 157]))
    story.append(PageBreak())

    # =========================================================================
    # SLIDE 30 (Page 31): WHY WILL THIS STRUCTURE WORK?
    # =========================================================================
    story.extend(header_block(30, "STRUCTURAL RESILIENCE", "Engineered for Permanence: Avoiding the Common Traps of Student Clubs"))
    story.append(Paragraph("Most collegiate technical societies collapse within 2–3 years due to predictable organizational failures. ATLAS is deliberately engineered with structural safeguards against every failure mode:", style_body))
    story.append(Spacer(1, 5))

    safeguards_data = [
        ["Common Society Failure Mode", "Underlying Structural Vulnerability", "ATLAS Architectural Invariant"],
        ["Single-Person Dependency", "Club relies on one charismatic founder; dies when they graduate", "Decentralized 12-department executive board with clear mandates"],
        ["Event-Only Focus", "Activity completely halts when no workshop or seminar is scheduled", "Weekly synchronized curriculum and persistent sprint deliverables"],
        ["Abandoned Codebases", "Prototypes rot on student laptops after hackathons conclude", "Post-Hackathon Continuation Review & shared cloud staging servers"],
        ["High Junior Dropout Rate", "Solo self-study leads to isolation, frustration, and dropout", "Synchronized weekly sprints, mid-week office hours, and peer PR reviews"],
        ["Unverified AI Code", "Copy-pasting hallucinations leads to broken, embarrassing demos", "Automated CI testing, schema validation, and technical review gates"],
        ["Knowledge Fragmentation", "Solutions and boilerplates are reinvented from scratch each year", "Centralized monorepo, versioned documentation, and maintainer handovers"],
        ["Lack of Focus", "Societies wander aimlessly between unrelated technologies", "Strict 4-track curriculum focused specifically on applied AI & software"],
        ["Institutional Friction", "Unapproved activities risk conflict with college administration", "Faculty Advisor oversight, written charters, and data privacy guardrails"]
    ]
    story.append(create_table(safeguards_data[0], safeguards_data[1:], col_widths=[115, 205, 212]))
    story.append(Spacer(1, 6))
    story.append(callout_box("<b>Permanence Guarantee:</b> ATLAS is not built around a single person or batch. It is built as an institutional system that outlasts its creators.", bg_color="#eff6ff", border_color="#2563eb"))
    story.append(PageBreak())

    # =========================================================================
    # SLIDE 31 (Page 32): CODE OF CONDUCT & RESPONSIBILITY
    # =========================================================================
    story.extend(header_block(31, "ETHICS & INTEGRITY", "Institutional Ethics, Security Guardrails & Data Privacy"))
    story.append(Paragraph("Because ATLAS engineers work with advanced AI models, webhooks, and institutional tools, we hold every member to the highest standards of professional ethics and data integrity:", style_body))
    story.append(Spacer(1, 5))

    ethics_data = [
        ["Ethical Category", "Core Code of Conduct Rule", "Institutional Safety Standard"],
        ["Institutional Primacy", "Absolute compliance with MAIT rules and guidelines", "Zero activities conducted without proper faculty approvals and departmental liaison."],
        ["Authorized Access Only", "Zero unauthorized testing or scraping of external systems", "Interact only with software, APIs, and portals where explicit authorization has been granted."],
        ["Data Privacy & Vaults", "Absolute confidentiality of student credentials and grades", "Hardware-isolated AES-256 encryption; zero plain passwords logged or stored anywhere."],
        ["Production Candor", "Honest communication regarding software maturity", "Never present an experimental mock or fragile hack as a production-ready system."],
        ["Intellectual Property", "Respect open-source licenses and collaborative credit", "Proper attribution for all third-party code; strict adherence to MIT/Apache OSS licenses."],
        ["Secret Hygiene", "Zero hardcoded credentials in codebases", "API keys and tokens stored exclusively in environment variables, never committed to Git."],
        ["Responsible AI", "Safety guardrails and rate limits on LLM workflows", "Implement content validation, rate limiters, and evaluation checks on all model pipelines."],
        ["Professional Demeanor", "Highest standards of decorum in client discovery", "All client engagements conducted with professionalism, transparent scopes, and faculty visibility."],
        ["Documentation Duty", "Mandatory documentation of all production code", "Every deployed feature must be documented to enable seamless succession and peer maintenance."]
    ]
    story.append(create_table(ethics_data[0], ethics_data[1:], col_widths=[105, 195, 232]))
    story.append(Spacer(1, 5))
    story.append(callout_box("<b>Zero Tolerance Policy:</b> Violations of data privacy, academic integrity, or institutional trust result in immediate expulsion from ATLAS and referral to department authorities.", bg_color="#f8fafc", border_color="#dc2626"))
    story.append(PageBreak())

    # =========================================================================
    # SLIDE 32 (Page 33): WHAT IS THE YEAR-ONE ROADMAP?
    # =========================================================================
    story.extend(header_block(32, "STRATEGIC ROADMAP", "The 8-Phase Year-One Operational Execution Plan"))
    story.append(Paragraph("ATLAS will execute its inaugural year through eight disciplined, sequential phases designed to build momentum systematically:", style_body))
    story.append(Spacer(1, 5))

    roadmap_data = [
        ["Operational Phase", "Target Timeline", "Primary Execution Focus", "Concrete Milestone Deliverable"],
        ["Phase 1: Foundation", "Months 1–2", "Faculty advisor appointment, charter ratification, core board setup.", "Official institutional approval and infrastructure provisioning."],
        ["Phase 2: Selection", "Month 3", "Open recruitment call, logic screen, take-home tasks, interviews.", "Induction of 25 core technical members across 12 departments."],
        ["Phase 3: Baseline Track", "Months 3–4", "Execution of Track 1 & 2 curriculum (Python, APIs, LLMs, Docker).", "100% of cohort passing baseline tasks with passing CI test suites."],
        ["Phase 4: Campus Launch", "Months 5–6", "Deployment of CampusIQ attendance radar and marksheet tools.", "Production rollout to 500+ active MAIT student users."],
        ["Phase 5: Competition", "Months 7–8", "Hackathon War Rooms, internal hackathon, national team submissions.", "3+ squads entering Smart India Hackathon and national events."],
        ["Phase 6: Client Pilot", "Months 9–10", "Scoping workflow automation problems for vetted external partners.", "2 successful client automation pilots delivered under faculty review."],
        ["Phase 7: OSS & Research", "Months 11–12", "Packaging internal utilities as open source; drafting research papers.", "1 published open-source package and 1 conference paper draft."],
        ["Phase 8: Succession", "Month 12", "Annual retrospective review, board elections, maintainer transition.", "Seamless executive handover to junior leadership for Year Two."]
    ]
    story.append(create_table(roadmap_data[0], roadmap_data[1:], col_widths=[95, 80, 190, 167]))
    story.append(Spacer(1, 6))
    story.append(callout_box("<b>Execution Discipline:</b> Each phase builds directly on the technical foundation established in the prior phase, ensuring sustainable, compounding growth without burnout.", bg_color="#eff6ff", border_color="#2563eb"))
    story.append(PageBreak())

    # =========================================================================
    # SLIDE 33 (Page 34): WHAT DOES SUCCESS LOOK LIKE?
    # =========================================================================
    story.extend(header_block(33, "SUCCESS EVALUATION", "Concrete Success Criteria at the Close of Year One"))
    story.append(Paragraph("At the end of Year One, ATLAS will evaluate its success not by subjective impressions, but by answering eight definitive questions:", style_body))
    story.append(Spacer(1, 5))

    success_q = [
        ["Evaluation Question", "Diagnostic Success Standard", "Institutional Proof"],
        ["1. Practical Competency", "Did 25+ students progress from tutorial consumers to independent software engineers?", "Verifiable student GitHub portfolios with live deployed URLs"],
        ["2. Sustained Momentum", "Did the society maintain unbroken weekly curriculum sprints and reviews across two semesters?", "Continuous weekly submission records and sprint retrospective logs"],
        ["3. Production Longevity", "Did flagship utilities like CampusIQ maintain 99%+ uptime and actively serve real student needs?", "Live status dashboards and active monthly student user metrics"],
        ["4. Hackathon Continuation", "Were at least 3 hackathon prototypes refactored, hardened, and moved into production environments?", "Active staging and production URLs for adopted hackathon projects"],
        ["5. Institutional Trust", "Did ATLAS earn the unreserved trust of MAIT faculty by acting with absolute integrity and compliance?", "Formal faculty advisor endorsements and positive departmental reviews"],
        ["6. External Delivery", "Did members successfully deliver scoped automation solutions to external stakeholders?", "Signed client completion testimonials and documented project handovers"],
        ["7. Knowledge Capture", "Is the society's collective knowledge documented in reusable repos, PRDs, and runbooks?", "Centralized Notion/GitHub wiki with zero single-person dependency"],
        ["8. Frictionless Succession", "Can graduating leads step aside with total confidence that the next batch will accelerate?", "Trained junior leads successfully running sprint cycles in Month 12"]
    ]
    story.append(create_table(success_q[0], success_q[1:], col_widths=[110, 222, 200]))
    story.append(Spacer(1, 6))
    story.append(callout_box("<b>The Ultimate Test of Success:</b> Not the number of certificates printed or workshop selfies posted. The ultimate proof is the quality, integrity, and independence of the engineers we forge.", bg_color="#eff6ff", border_color="#2563eb"))
    story.append(PageBreak())

    # =========================================================================
    # SLIDE 34 (Page 35): THE ATLAS PROMISE
    # =========================================================================
    story.extend(header_block(34, "THE INSTITUTIONAL COMMITMENT", "Our Lasting Commitment to MAIT Engineering"))
    story.append(Spacer(1, 8))

    promise_box = (
        "<b>ATLAS is established to fill a vital void in the technical fabric of Maharaja Agrasen Institute of Technology.</b><br/><br/>"
        "We are not simply creating another student club that hosts occasional seminars. "
        "We are building an <b>institutional engine</b> that systematically discovers curious minds, trains them in modern AI, automation, and full-stack software discipline, "
        "and empowers them to deploy tools that elevate the entire college community.<br/><br/>"
        "By bridging the gap between hackathons and production software, ATLAS ensures that student creativity creates permanent, institutional value."
    )
    story.append(callout_box(promise_box, bg_color="#eff6ff", border_color="#2563eb"))
    story.append(Spacer(1, 14))

    story.append(Paragraph("The Complete ATLAS Paradigm Summary", style_h2))
    paradigm_data = [
        ["LEARN", "Structured weekly education in modern AI, LLM systems, agents, APIs, and Linux software engineering."],
        ["BUILD", "Transforming theoretical understanding into functional, modular codebases and live student utilities."],
        ["REVIEW", "Demanding rigorous code quality, security audits, schema validation, and peer accountability on every PR."],
        ["DEPLOY", "Shipping containerized services to high-reliability cloud servers behind SSL and reverse proxies."],
        ["MAINTAIN", "Committing to multi-semester uptime, continuous issue resolution, and permanent project ownership."],
        ["CONTRIBUTE", "Giving back to MAIT and the global developer community through open-source tools and research papers."]
    ]
    story.append(create_table(["Paradigm Pillar", "Operational Reality"], paradigm_data, col_widths=[100, 432]))
    story.append(Spacer(1, 16))

    signoff_table = Table([
        [
            Paragraph("<b>Submitted by Executive Leadership:</b><br/><br/>"
                      "<b>Garv Goyal</b><br/>Society President<br/>ATLAS, MAIT", style_body),
            Paragraph("<br/><br/><b>Tanmay Jain</b><br/>Vice President<br/>ATLAS, MAIT", style_body),
            Paragraph("<b>Departmental Endorsement:</b><br/><br/>"
                      "<b>Department of Computer Science & Engineering</b><br/>"
                      "Maharaja Agrasen Institute of Technology, Rohini, Delhi", style_body)
        ]
    ], colWidths=[170, 160, 202])
    signoff_table.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('LEFTPADDING', (0,0), (-1,-1), 0),
        ('RIGHTPADDING', (0,0), (-1,-1), 0),
    ]))
    story.append(signoff_table)
    story.append(Spacer(1, 20))
    story.append(Paragraph("<font color='#2563eb'><b>AUTOMATE THE MUNDANE. ENGINEER THE FUTURE.</b></font>", ParagraphStyle('CloseMotto', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=12, leading=15, alignment=1, textColor=colors.HexColor('#2563eb'))))

    # Build the document
    print(f"Building document to {PDF_PATH}...")
    doc.build(story, canvasmaker=NumberedCanvas)
    print("Build complete!")

    # Copy to artifact path
    os.makedirs(os.path.dirname(ARTIFACT_PATH), exist_ok=True)
    shutil.copyfile(PDF_PATH, ARTIFACT_PATH)
    print(f"Copied to artifact path: {ARTIFACT_PATH}")

if __name__ == '__main__':
    build_pdf()
