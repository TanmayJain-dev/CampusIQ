# CampusIQ

<div align="center">

### 🎓 Your Academic Journey, Simplified.

A modern academic analytics platform that transforms university result portals into a fast, beautiful, and insightful experience.

**Built with:** Next.js • TypeScript • Prisma • PostgreSQL • Auth.js • Tailwind CSS

![Next.js](https://img.shields.io/badge/Next.js-15-black)
![TypeScript](https://img.shields.io/badge/TypeScript-5.0-blue)
![License](https://img.shields.io/badge/License-MIT-green)
![Status](https://img.shields.io/badge/Status-Active%20Development-orange)

</div>

---

## 🚀 About

CampusIQ is a modern academic platform designed to help university students securely access, visualize, and track their academic performance.

Instead of navigating outdated university portals, students get a clean dashboard with meaningful analytics, historical performance tracking, and future-ready features like notifications and AI-powered academic insights.

The platform is built around a provider-based architecture, allowing support for multiple universities without changing the core application.

---

## ✨ Vision

Our goal is simple:

> Make checking university results as seamless as checking your bank account or email.

CampusIQ aims to become the academic companion for every university student.

---

# Current Development Status

## ✅ Completed

- Project Architecture
- Next.js Foundation
- Provider-based University Integration
- Academic Synchronization Engine
- Modular Infrastructure
- Project Documentation
- GitHub Repository Setup

---

## 🚧 In Progress

- Marketing Website
- Authentication
- Dashboard UI
- University Result Integration

---

## 📅 Planned

- Interactive Analytics Dashboard
- CGPA & SGPA Trends
- Automatic Result Notifications
- Multi-University Support
- Placement Eligibility Tracker
- AI Academic Insights
- Mobile Optimization
- Progressive Web App (PWA)

---

# Features

### 📊 Academic Analytics

Visualize semester performance through interactive charts and dashboards.

---

### 🔄 Result Synchronization

Secure synchronization engine that fetches academic records from supported university portals.

---

### 🔐 Secure Authentication

Google OAuth and secure session management powered by Auth.js.

---

### 🏛 Multi-University Ready

Provider-based architecture makes adding new universities simple without modifying the core platform.

---

### 📈 Performance Tracking

Track your academic growth semester by semester.

---

### 🔔 Smart Notifications *(Planned)*

Receive alerts whenever new results become available.

---

# Architecture

CampusIQ follows a modular, scalable architecture inspired by modern SaaS platforms.

```
User
   │
   ▼
Frontend (Next.js)

   │
   ▼

Academic Service

   │
   ▼

University Provider Interface

   │
   ├── IPU Provider
   ├── DU Provider (Planned)
   ├── AKTU Provider (Planned)
   └── More...

   │
   ▼

Synchronization Engine

   │
   ▼

PostgreSQL Database
```

---

# Tech Stack

## Frontend

- Next.js (App Router)
- React
- TypeScript
- Tailwind CSS

## Backend

- Prisma ORM
- PostgreSQL
- Auth.js

## Infrastructure

- Provider Pattern
- Modular Synchronization Engine
- Dependency Injection
- Feature-Based Architecture

---

# Project Structure

```
src/
│
├── app/
├── components/
├── features/
├── infrastructure/
├── lib/
├── providers/
├── services/
└── types/
```

---

# Getting Started

Clone the repository

```bash
git clone https://github.com/TanmayJain-dev/CampusIQ.git
```

Install dependencies

```bash
npm install
```

Run the development server

```bash
npm run dev
```

---

# Environment Variables

Create a `.env.local` file.

```env
DATABASE_URL=

AUTH_SECRET=

AUTH_GOOGLE_ID=

AUTH_GOOGLE_SECRET=

NEXT_PUBLIC_APP_URL=
```

---

# Roadmap

### Version 0.1

- [x] Architecture
- [x] Synchronization Engine
- [x] Provider Framework

---

### Version 0.2

- [ ] Landing Page
- [ ] Authentication
- [ ] Database Integration

---

### Version 0.3

- [ ] Result Viewer
- [ ] Dashboard
- [ ] Charts

---

### Version 0.4

- [ ] Notifications
- [ ] Historical Tracking
- [ ] Mobile Support

---

### Version 1.0

- [ ] Multi-University Support
- [ ] AI Insights
- [ ] Public Launch

---

# Contributing

Contributions, feature suggestions, and bug reports are welcome.

Please read the `CONTRIBUTING.md` guide before opening a pull request.

---

# License

This project is licensed under the MIT License.

---

# Author

**Tanmay Jain**

Computer Science Student • Software Engineer

GitHub:

https://github.com/TanmayJain-dev

---

<div align="center">

### ⭐ If you like this project, consider giving it a star!

Building the future of academic analytics, one university at a time.

</div>
