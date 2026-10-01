# 🎓 CampusIQ — Next-Gen Student Operating System & Automation Hub

> **State-of-the-Art Intelligence Infrastructure for GGSIPU & Affiliated Colleges (MAIT, USICT, MSIT, BVCOE, BPIT)**  
> Engineered for ATLAS (Automated Technologies & Logical Applications Society).

---

## ⚡ Quickstart

Launch the complete full-stack web application (frontend + backend + real-time scrapers) with a single command:

```bash
cd CampusIQ
./run.sh
```

Then open your browser at:  
👉 **`http://localhost:5000`**

---

## 🏗️ What is CampusIQ?

CampusIQ completely eliminates the fragmented, friction-heavy legacy university experience for engineering students:

1. **📢 AI-Categorized Real-Time Noticeboard**:
   - Ingests circulars every 30 minutes from **GGSIPU Central**, **GGSIPU Examination Division**, and **MAIT Campus Notices** via the active Render n8n workflow (`ezMMNBQLsuepJCiy`).
   - Automatically segments notices into 7 academic streams (`Examinations & Datesheets`, `Results & Evaluations`, `Fees & Accounts`, `Scholarships & Welfare`, `Placements & Careers`, `Admissions`, `General Circulars`).
   - Flags critical deadlines (`🔴 HIGH PRIORITY`, `🟡 NOTICE`, `🟢 INFO`).
   - **Dual Action View**: View the high-impact "Pretty Typeset Card" or jump straight to the "Official University Circular".
   - **1-Click Broadcast**: Instant copy button for WhatsApp, Discord, and Telegram announcements.

2. **💎 CampusIQ Academic Study Resource Vault**:
   - Indexed catalog of **231 university documents** and **52 publication-grade typeset PYQ master papers** in the academic vault (`assets/vault`).
   - Complete coverage for all Semester 3 core subjects:
     - Computational Methods (`ES-201`)
     - Discrete Mathematics (`CIC-205`)
     - Digital Logic & Computer Design (`ECC-207`)
     - Data Structures (`CIC-209`)
     - Object Oriented Programming in C++ (`CIC-211`)
   - Built-in **In-Browser PDF Viewer** modal for instant preview with zero download friction.

3. **📊 GGSIPU ExamWeb Marksheet Engine & Analytics**:
   - Direct integration with official GGSIPU ExamWeb portal (`examweb.ggsipu.ac.in`).
   - Generates authentic official-style GGSIPU Grade Card Marksheets with Internal, External, Total Marks, Grade, and verified credits (Semester 1 = 21, Semester 2 = 23 credits).
   - In-app Captcha solver and live session manager.
   - Comprehensive multi-semester progression tracking with SGPA & cumulative CGPA.
   - Privacy-respecting grade security with optional public/private visibility.

4. **💎 CampusIQ Hierarchical Study Vault**:
   - Multi-tier structured hierarchy: **Semester ➔ Subject ➔ Category (Notes, Books, PYQs, Lab Manuals)**.
   - Omnisearch filter instantly locates resources by paper title, subject code, or keyword across 231+ files.
   - Built-in in-browser PDF preview.

5. **👤 Student Profile Segregation & Peer Directory**:
   - Google account authentication with personalized student profiles.
   - Granular privacy controls: toggle visibility of CGPA, GitHub, LinkedIn, bio, practical group, and branch.
   - Verified student badges with document verification hash.
   - Campus Peer Directory to discover classmates and study groups.

6. **🎯 Interactive SGPA Forecaster & Simulator**:
   - Grade simulation modal using official university grading criteria to plan target scores for upcoming Mid-Sem and End-Sem exams.

---

## 🏛️ REST API Endpoints

The built-in backend server (`server.py`) provides fast JSON APIs:

| Endpoint | Method | Description |
| :--- | :---: | :--- |
| `/api/notices` | `GET` | Live multi-college notices with AI summaries. Query params: `college`, `category`, `urgency`, `search`, `limit`. |
| `/api/resources` | `GET` | Academic study vault catalog. Query params: `semester`, `subject`, `category`, `typeset`, `search`. |
| `/api/resources/tree` | `GET` | 3-tier hierarchical study vault taxonomy tree. |
| `/api/resources/view` | `GET` | In-browser PDF stream preview. Query param: `path`. |
| `/api/examweb/session` | `GET` | Initiates official ExamWeb session and fetches live captcha image. |
| `/api/examweb/login` | `POST` | Authenticates with ExamWeb, extracts marksheet, and syncs student database. |
| `/api/students/directory`| `GET` | Public peer directory of student profiles with privacy segregation. |
| `/api/students/profile` | `GET/POST`| Fetch or update individual student profile details and privacy toggles. |
| `/api/colleges` | `GET` | Metadata mapping of GGSIPU colleges and programme codes. |
| `/api/stats` | `GET` | Real-time system operational metrics and catalog counts. |

---

## 📁 Repository Structure

```
CampusIQ/
├── run.sh                          # One-click platform launcher
├── server.py                       # High-speed HTTP & REST API server
├── campusiq_examweb.py             # ExamWeb portal client & marksheet parser
├── campusiq_results_extractor.py   # PyMuPDF tabulation sheet parser & scraper
├── campusiq_cataloguer.py          # Academic study resource indexer
├── render.yaml                     # Render Infrastructure as Code blueprint
├── requirements.txt                # Python production dependencies
├── sample_result.pdf               # Local benchmark result tabulation sheet
├── data/
│   ├── catalog_cache.json          # Pre-indexed cloud catalog of 231+ academic resources
│   └── students_database.json      # Persistent student profiles with privacy controls
├── public/
│   ├── index.html                  # Single Page Web Application
│   ├── app.js                      # Reactive frontend controller
│   └── style.css                   # Obsidian dark-mode design system
└── README.md                       # Complete documentation
```

---

## 🚀 Deployment (Render)

CampusIQ is ready for 1-click deployment on Render:

- **Runtime**: Python 3
- **Build Command**: `pip install -r requirements.txt`
- **Start Command**: `python3 server.py`
- **Region**: Singapore (`singapore`)
- **Plan**: Free / Starter
- **Environment Variables**:
  - `PORT`: (Provided automatically by Render)
  - `N8N_WEBHOOK_URL`: (Optional webhook URL for notice alerts)

