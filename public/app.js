/**
 * CampusIQ - Core Client Application Controller
 * High-performance reactive UI logic with localStorage profile synchronization,
 * live REST API integrations, and instant in-browser PDF previews.
 */

// Application State
const state = {
  profile: {
    college: "MAIT",
    branch: "CSE",
    semester: 3
  },
  activeTab: "notices",
  notices: [],
  noticeCategory: "",
  activeNotice: null,
  // Hierarchical Vault
  resources: [],
  vaultTree: null,
  vaultSemester: 3,
  vaultSubject: null,
  typesetOnly: false,
  // ExamWeb State
  resultMode: "examweb",
  examWebSession: null,
  examWebResult: null,
  examWebSelectedSem: "all",
  // Student Community & Profile Segregation
  activeCommunitySubView: "directory",
  sessionToken: localStorage.getItem("campusiq_session_token") || null,
  currentUser: null,
  currentStudent: null,
  googleClientId: "",
  authMode: "signin",
  directoryStudents: [],
  selectedPeer: null,
  directoryFilter: "all",
  uploadedProofBase64: null,
  uploadedProofName: "",
  // Faculty Admin
  adminStudents: [],
  adminFilteredStudents: []
};

// GGSIPU Grade to Point Mapping
const GRADE_POINTS = {
  "O": 10.0,
  "A+": 9.0,
  "A": 8.0,
  "B+": 7.0,
  "B": 6.0,
  "C": 5.0,
  "P": 4.0,
  "F": 0.0
};

// Core Sem 3 Subjects for Calculator
const SEM3_SUBJECTS = [
  { code: "ES-201", name: "Computational Methods", credits: 4, defaultGrade: "A" },
  { code: "CIC-205", name: "Discrete Mathematics", credits: 4, defaultGrade: "A+" },
  { code: "ECC-207", name: "Digital Logic & Computer Design", credits: 4, defaultGrade: "A" },
  { code: "CIC-209", name: "Data Structures", credits: 4, defaultGrade: "O" },
  { code: "CIC-211", name: "Object Oriented Programming (C++)", credits: 4, defaultGrade: "A+" },
  { code: "ES-251", name: "Computational Methods Lab", credits: 1, defaultGrade: "O" },
  { code: "ECC-257", name: "Digital Logic Lab", credits: 1, defaultGrade: "O" },
  { code: "CIC-259", name: "Data Structures Lab", credits: 1, defaultGrade: "A+" },
  { code: "CIC-261", name: "OOPs using C++ Lab", credits: 1, defaultGrade: "O" },
  { code: "ES-263", name: "Technical Writing / NUES", credits: 2, defaultGrade: "A" }
];

document.addEventListener("DOMContentLoaded", () => {
  loadStoredProfile();
  initCalculator();
  fetchNotices();
  fetchResourcesTree();
  fetchResources();
  fetchCurrentUser();
  loadAuthConfig();
  fetchDirectoryStudents();
  loadAdminRoster();
  fetchStats();
  initExamWebSession();
  lucide.createIcons();
});

// =============================================================================
// NAVIGATION & TABS
// =============================================================================

function switchTab(tabId) {
  state.activeTab = tabId;
  if (tabId === "results" && !state.examWebSession && !state.examWebResult) {
    initExamWebSession();
  }
  if (tabId === "admin") {
    loadAdminRoster();
  }
  if (tabId === "community") {
    initCommunityHub();
  }


  // Toggle nav buttons
  document.querySelectorAll(".tab-btn").forEach(btn => {
    btn.classList.remove("bg-blue-600", "text-white", "shadow-[0_0_12px_rgba(59,130,246,0.3)]");
    btn.classList.add("text-zinc-400");
  });
  const activeNav = document.getElementById(`nav-${tabId}`);
  if (activeNav) {
    activeNav.classList.add("bg-blue-600", "text-white", "shadow-[0_0_12px_rgba(59,130,246,0.3)]");
    activeNav.classList.remove("text-zinc-400");
  }

  // Toggle mobile buttons
  document.querySelectorAll(".mobile-tab-btn").forEach(btn => {
    btn.classList.remove("text-blue-400");
    btn.classList.add("text-zinc-400");
  });
  const activeMNav = document.getElementById(`m-nav-${tabId}`);
  if (activeMNav) {
    activeMNav.classList.add("text-blue-400");
    activeMNav.classList.remove("text-zinc-400");
  }

  // Toggle content panes
  document.querySelectorAll(".tab-pane").forEach(pane => {
    pane.classList.add("hidden");
    pane.classList.remove("block");
  });
  const activePane = document.getElementById(`tab-${tabId}`);
  if (activePane) {
    activePane.classList.remove("hidden");
    activePane.classList.add("block");
  }

  window.scrollTo({ top: 0, behavior: "smooth" });
  lucide.createIcons();
}

// =============================================================================
// PROFILE & COLLEGE ONBOARDING
// =============================================================================

function loadStoredProfile() {
  const saved = localStorage.getItem("campusiq_profile");
  if (saved) {
    try {
      state.profile = JSON.parse(saved);
    } catch (e) {}
  }
  updateProfileLabels();
}

function updateProfileLabels() {
  const colMap = {
    "MAIT": "MAIT (Rohini)",
    "USICT": "USICT (Dwarka)",
    "MSIT": "MSIT (Janakpuri)",
    "BVCOE": "BVCOE (Paschim Vihar)",
    "BPIT": "BPIT (Rohini)",
    "DTC": "DTC (Greater Noida)",
    "VIPS": "VIPS (Pitampura)"
  };
  const collegeName = colMap[state.profile.college] || state.profile.college;
  document.getElementById("active-college-label").innerText = collegeName;
  document.getElementById("active-branch-label").innerText = `${state.profile.branch} • Sem ${state.profile.semester}`;
}

function openProfileModal() {
  document.getElementById("modal-select-college").value = state.profile.college;
  document.getElementById("modal-select-branch").value = state.profile.branch;
  document.getElementById("modal-select-sem").value = state.profile.semester;
  document.getElementById("profile-modal").classList.add("open");
}

function closeProfileModal() {
  document.getElementById("profile-modal").classList.remove("open");
}

function closeProfileModalOnBackdrop(e) {
  closeProfileModal();
}

function saveProfile() {
  state.profile.college = document.getElementById("modal-select-college").value;
  state.profile.branch = document.getElementById("modal-select-branch").value;
  state.profile.semester = parseInt(document.getElementById("modal-select-sem").value);
  
  localStorage.setItem("campusiq_profile", JSON.stringify(state.profile));
  updateProfileLabels();
  closeProfileModal();
  showToast(`Profile updated: ${state.profile.college} - ${state.profile.branch}`);

  // Auto-refresh feeds
  fetchNotices(true);
  fetchResources();
}

// =============================================================================
// TAB 1: NOTICES
// =============================================================================

async function fetchNotices(force = false) {
  const grid = document.getElementById("notices-grid");
  if (force) {
    grid.innerHTML = `
      <div class="col-span-full py-16 text-center text-zinc-500">
        <i data-lucide="loader-2" class="w-6 h-6 animate-spin mx-auto mb-2 text-blue-500"></i>
        <p class="text-xs">Fetching real-time circulars from n8n engine...</p>
      </div>
    `;
    lucide.createIcons();
  }

  try {
    const res = await fetch(`/api/notices?college=all`);
    const data = await res.json();
    state.notices = data.notices || [];

    document.getElementById("stat-total-notices").innerText = data.total || state.notices.length;
    document.getElementById("stat-high-priority").innerText = data.high_priority_count || 0;

    filterNotices();
  } catch (e) {
    console.error("Notice fetch error:", e);
    grid.innerHTML = `<div class="col-span-full p-8 text-center text-red-400 text-xs">Error loading live notices. Please try again.</div>`;
  }
}

function setNoticeCategory(cat) {
  state.noticeCategory = cat;
  document.querySelectorAll(".notice-cat-btn").forEach(btn => {
    if (btn.getAttribute("data-cat") === cat) {
      btn.classList.add("bg-blue-600", "text-white");
      btn.classList.remove("bg-zinc-900", "text-zinc-400");
    } else {
      btn.classList.remove("bg-blue-600", "text-white");
      btn.classList.add("bg-zinc-900", "text-zinc-400");
    }
  });
  filterNotices();
}

function filterNotices() {
  const query = document.getElementById("notice-search").value.toLowerCase();
  const cat = state.noticeCategory.toLowerCase();

  const filtered = state.notices.filter(n => {
    const matchQuery = !query || n.title.toLowerCase().includes(query) || (n.category && n.category.toLowerCase().includes(query));
    const matchCat = !cat || (n.category && n.category.toLowerCase().includes(cat));
    return matchQuery && matchCat;
  });

  renderNotices(filtered);
}

function renderNotices(notices) {
  const grid = document.getElementById("notices-grid");
  if (!notices.length) {
    grid.innerHTML = `
      <div class="col-span-full py-16 text-center text-zinc-500">
        <i data-lucide="bell-off" class="w-8 h-8 mx-auto mb-2 text-zinc-600"></i>
        <p class="text-sm">No circulars matching current filters.</p>
      </div>
    `;
    lucide.createIcons();
    return;
  }

  const urgencyBadges = {
    "HIGH": `<span class="px-2 py-0.5 rounded text-[10px] font-mono font-bold bg-red-500/10 text-red-400 border border-red-500/20">🔴 HIGH URGENCY</span>`,
    "MEDIUM": `<span class="px-2 py-0.5 rounded text-[10px] font-mono font-bold bg-amber-500/10 text-amber-400 border border-amber-500/20">🟡 NOTICE</span>`,
    "LOW": `<span class="px-2 py-0.5 rounded text-[10px] font-mono font-bold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">🟢 INFO</span>`
  };

  grid.innerHTML = notices.map(n => {
    const badge = urgencyBadges[n.urgency] || urgencyBadges["LOW"];
    const sourceIcon = n.source === "MAIT" ? "building" : "university";
    return `
      <div class="p-5 rounded-2xl glass-card flex flex-col justify-between space-y-4">
        <div class="space-y-3">
          <div class="flex items-center justify-between gap-2">
            ${badge}
            <span class="text-[11px] font-mono text-zinc-400">${n.date || 'Recent'}</span>
          </div>
          <h3 class="text-sm font-semibold text-white leading-snug line-clamp-2 hover:text-blue-400 transition-all cursor-pointer" onclick="openNoticeModal('${n.notice_id}')">
            ${n.title}
          </h3>
          <div class="space-y-1 text-[11px] text-zinc-400 pt-1 border-t border-white/5">
            <div class="flex items-center justify-between">
              <span class="text-zinc-500">Source:</span>
              <span class="text-zinc-300">${n.source} (${n.college || 'Central'})</span>
            </div>
            <div class="flex items-center justify-between">
              <span class="text-zinc-500">Stream:</span>
              <span class="text-blue-400 font-medium">${n.category}</span>
            </div>
            <div class="flex items-center justify-between">
              <span class="text-zinc-500">Audience:</span>
              <span class="text-zinc-300">${n.target_audience || 'All Students'}</span>
            </div>
          </div>
        </div>

        <div class="pt-3 border-t border-white/5 flex items-center justify-between gap-2 text-xs">
          <button onclick="openNoticeModal('${n.notice_id}')" class="px-3 py-1.5 rounded-lg bg-zinc-900 hover:bg-zinc-800 text-zinc-300 hover:text-white font-medium flex items-center gap-1.5 transition-all">
            <i data-lucide="eye" class="w-3.5 h-3.5"></i>
            <span>Pretty Card</span>
          </button>
          <a href="${n.url}" target="_blank" class="px-3 py-1.5 rounded-lg bg-blue-600/90 hover:bg-blue-600 text-white font-medium flex items-center gap-1.5 transition-all">
            <span>Official Link</span>
            <i data-lucide="external-link" class="w-3 h-3"></i>
          </a>
        </div>
      </div>
    `;
  }).join("");

  lucide.createIcons();
}

function openNoticeModal(noticeId) {
  const n = state.notices.find(item => item.notice_id === noticeId);
  if (!n) return;
  state.activeNotice = n;

  document.getElementById("modal-notice-title").innerText = n.title;
  document.getElementById("modal-notice-source").innerText = `${n.source} • ${n.college || 'Central IPU'}`;
  document.getElementById("modal-notice-date").innerText = n.date || "Recent";
  
  const badgeElem = document.getElementById("modal-notice-badge");
  badgeElem.innerText = n.urgency ? `${n.urgency} URGENCY` : "NOTICE";
  if (n.urgency === "HIGH") {
    badgeElem.className = "px-2.5 py-0.5 rounded text-[10px] font-mono font-bold bg-red-500/10 text-red-400 border border-red-500/20";
  } else if (n.urgency === "MEDIUM") {
    badgeElem.className = "px-2.5 py-0.5 rounded text-[10px] font-mono font-bold bg-amber-500/10 text-amber-400 border border-amber-500/20";
  } else {
    badgeElem.className = "px-2.5 py-0.5 rounded text-[10px] font-mono font-bold bg-blue-500/10 text-blue-400 border border-blue-500/20";
  }

  // Structured Executive Summary & Actionable Details
  const summaryElem = document.getElementById("modal-notice-summary");
  if (summaryElem) {
    summaryElem.innerText = n.executive_summary || n.summary || "Official university notification regarding examination, academic schedule, or administrative instructions.";
  }

  const targetElem = document.getElementById("modal-notice-target");
  if (targetElem) {
    targetElem.innerText = n.target_audience || "B.Tech & Affiliated College Students";
  }

  const wingElem = document.getElementById("modal-notice-wing");
  if (wingElem) {
    wingElem.innerText = n.issuing_wing || "GGSIPU Examination & Conduct Division";
  }

  const actionElem = document.getElementById("modal-notice-action");
  if (actionElem) {
    actionElem.innerText = n.action_required || "Verify course codes and submit requisite forms before the designated deadline.";
  }

  // Important Dates Chips
  const datesBox = document.getElementById("modal-notice-dates");
  if (datesBox) {
    const dates = n.important_dates && n.important_dates.length > 0 ? n.important_dates : [n.date || "Current Session 2026"];
    datesBox.innerHTML = dates.map(d => `
      <span class="px-2.5 py-1 rounded-lg bg-zinc-900 border border-white/10 text-zinc-300 font-mono flex items-center gap-1.5">
        <i data-lucide="calendar" class="w-3 h-3 text-blue-400"></i>
        <span>${d}</span>
      </span>
    `).join("");
  }

  // Reset Document Preview Frame
  const pdfContainer = document.getElementById("modal-pdf-container");
  const pdfFrame = document.getElementById("modal-pdf-frame");
  const toggleBtnText = document.getElementById("modal-toggle-preview-text");
  if (pdfContainer) pdfContainer.classList.add("hidden");
  if (pdfFrame) pdfFrame.src = "about:blank";
  if (toggleBtnText) toggleBtnText.innerText = "Preview Document";

  // Official Link
  const linkElem = document.getElementById("modal-notice-link");
  if (linkElem) linkElem.href = n.url;

  document.getElementById("notice-modal").classList.add("open");
  lucide.createIcons();
}

function closeNoticeModal() {
  document.getElementById("notice-modal").classList.remove("open");
  const pdfFrame = document.getElementById("modal-pdf-frame");
  if (pdfFrame) pdfFrame.src = "about:blank";
}

function closeNoticeModalOnBackdrop(e) {
  if (e.target.id === "notice-modal") closeNoticeModal();
}

function toggleNoticePdfPreview() {
  const container = document.getElementById("modal-pdf-container");
  const frame = document.getElementById("modal-pdf-frame");
  const label = document.getElementById("modal-toggle-preview-text");
  if (!container || !frame || !state.activeNotice) return;

  if (container.classList.contains("hidden")) {
    container.classList.remove("hidden");
    const rawUrl = state.activeNotice.url || "";
    const proxyUrl = `/api/notices/proxy?url=${encodeURIComponent(rawUrl)}`;
    frame.src = proxyUrl;
    if (label) label.innerText = "Hide Preview";
  } else {
    container.classList.add("hidden");
    frame.src = "about:blank";
    if (label) label.innerText = "Preview Document";
  }
}

function copyModalAlert() {
  if (!state.activeNotice) return;
  const n = state.activeNotice;
  const text = `📢 *IPU CIRCULAR ALERT*\n\n📌 *${n.title}*\n🎯 *Audience:* ${n.target_audience || 'All Students'}\n🏛️ *Wing:* ${n.issuing_wing || 'GGSIPU'}\n⚡ *Action Required:* ${n.action_required || 'Refer to official link'}\n📅 *Dates:* ${n.important_dates ? n.important_dates.join(', ') : n.date || 'Recent'}\n🔗 *Official Notice:* ${n.url}\n\n_Shared via CampusIQ_`;
  navigator.clipboard.writeText(text).then(() => {
    showToast("📋 Formatted circular alert copied to clipboard!");
  });
}

// =============================================================================
// TAB 2: CAMPUSIQ HIERARCHICAL ACADEMIC STUDY VAULT & UNIVERSAL SEARCH
// =============================================================================

async function fetchResourcesTree() {
  try {
    const res = await fetch("/api/resources/tree");
    const json = await res.json();
    const data = json.tree || json;
    state.vaultTree = data;

    // Update semester subject counts on pills
    const sem3Count = document.getElementById("sem3-count");
    const sem2Count = document.getElementById("sem2-count");
    const sem1Count = document.getElementById("sem1-count");
    if (sem3Count && data.semesters?.[3]) {
      sem3Count.innerText = `${Object.keys(data.semesters[3].subjects || {}).length} Subjects`;
    }
    if (sem2Count && data.semesters?.[2]) {
      sem2Count.innerText = `${Object.keys(data.semesters[2].subjects || {}).length} Subjects`;
    }
    if (sem1Count && data.semesters?.[1]) {
      sem1Count.innerText = `${Object.keys(data.semesters[1].subjects || {}).length} Subjects`;
    }

    if (data.total_items || data.total) {
      const totEl = document.getElementById("stat-total-resources");
      if (totEl) totEl.innerText = data.total_items || data.total;
    }
    if (data.typeset_count) {
      const typeEl = document.getElementById("stat-typeset-count");
      if (typeEl) typeEl.innerText = data.typeset_count;
    }

    renderVaultHierarchy();
  } catch (e) {
    console.error("Resource tree fetch error:", e);
  }
}

async function fetchResources() {
  try {
    // Fetch all resources across all semesters for universal instant search
    const res = await fetch("/api/resources?semester=all");
    const data = await res.json();
    state.resources = data.resources || [];
  } catch (e) {
    console.error("Flat resource fetch error:", e);
  }
}

function setVaultSemester(sem) {
  state.vaultSemester = sem;
  state.vaultSubject = null; // Reset to default first subject of that semester
  renderVaultHierarchy();
}

function setVaultSubject(subjKey) {
  state.vaultSubject = subjKey;
  renderVaultHierarchy();
}

function toggleTypesetOnlyFilter() {
  const toggle = document.getElementById("typeset-only-toggle");
  state.typesetOnly = toggle ? toggle.checked : false;
  renderVaultHierarchy();
  const searchContainer = document.getElementById("vault-search-results-container");
  if (searchContainer && !searchContainer.classList.contains("hidden")) {
    handleUniversalResourceSearch();
  }
}

function renderVaultHierarchy() {
  if (!state.vaultTree || !state.vaultTree.semesters) return;

  const currentSem = state.vaultSemester;
  const semData = state.vaultTree.semesters[currentSem];
  if (!semData) return;

  // 1. Update Semester Selector Button Styles
  [1, 2, 3].forEach(s => {
    const btn = document.getElementById(`vault-sem-btn-${s}`);
    if (!btn) return;
    if (s === currentSem) {
      btn.className = "vault-sem-btn px-4 py-2 rounded-xl bg-emerald-600 text-white font-semibold flex items-center gap-2 transition-all shadow-[0_0_12px_rgba(16,185,129,0.3)]";
    } else {
      btn.className = "vault-sem-btn px-4 py-2 rounded-xl bg-zinc-900 border border-white/5 text-zinc-400 hover:text-white font-semibold flex items-center gap-2 transition-all";
    }
  });

  const subjectsObj = semData.subjects || {};
  const semCount = Object.values(subjectsObj).reduce((acc, s) => {
    return acc + Object.values(s.categories || {}).reduce((cacc, arr) => cacc + arr.length, 0);
  }, 0);

  const semLabel = document.getElementById("active-sem-label");
  if (semLabel) semLabel.innerText = `Semester ${currentSem} Curriculum (${semCount} Documents)`;

  // 2. Populate Subject Explorer Pills
  const subjectKeys = Object.keys(subjectsObj);

  if (!state.vaultSubject || !subjectsObj[state.vaultSubject]) {
    state.vaultSubject = subjectKeys[0] || null;
  }

  const pillsContainer = document.getElementById("vault-subject-pills");
  if (pillsContainer) {
    pillsContainer.innerHTML = subjectKeys.map(k => {
      const subj = subjectsObj[k];
      const subjCount = Object.values(subj.categories || {}).reduce((acc, arr) => acc + arr.length, 0);
      const isActive = k === state.vaultSubject;
      const activeClass = isActive
        ? "bg-emerald-600 text-white shadow-[0_0_12px_rgba(16,185,129,0.3)] font-bold"
        : "bg-zinc-900 border border-white/5 text-zinc-400 hover:text-white font-medium";
      return `
        <button onclick="setVaultSubject('${k}')" class="px-3.5 py-2 rounded-xl text-xs transition-all flex items-center gap-2 ${activeClass}">
          <span>${subj.name}</span>
          <span class="px-1.5 py-0.5 rounded text-[10px] font-mono ${isActive ? 'bg-black/30 text-white' : 'bg-zinc-800 text-zinc-400'}">${subjCount}</span>
        </button>
      `;
    }).join("");
  }

  // 3. Render Categorized Trays for Active Subject
  const traysContainer = document.getElementById("vault-category-trays");
  if (!traysContainer) return;

  if (!state.vaultSubject || !subjectsObj[state.vaultSubject]) {
    traysContainer.innerHTML = `
      <div class="p-12 text-center text-zinc-500">
        <i data-lucide="folder-open" class="w-8 h-8 mx-auto mb-2 text-zinc-600"></i>
        <p class="text-sm">Select a subject to view categorized resources.</p>
      </div>
    `;
    lucide.createIcons();
    return;
  }

  const activeSubjData = subjectsObj[state.vaultSubject];
  const categories = [
    { title: "Lecture Notes & Theory", aliases: ["Lecture Notes & Theory", "Notes", "General Academic Materials"], icon: "book-open", color: "blue", desc: "Handwritten and typed classroom lecture transcriptions" },
    { title: "Reference Books & Guides", aliases: ["Reference Books & Guides", "Books"], icon: "library", color: "indigo", desc: "Standard textbooks and reference handbooks" },
    { title: "Mid-Term Question Papers (Minor PYQs)", aliases: ["Mid-Term Papers & PYQs", "Mid-Term Question Papers", "mid_sem"], icon: "file-question", color: "amber", desc: "Typeset class tests and internal assessment question papers" },
    { title: "End-Term Question Papers (Major PYQs)", aliases: ["End-Term Papers & PYQs", "End-Term Question Papers", "end_sem"], icon: "file-check", color: "emerald", desc: "End-semester university question papers with complete solutions" },
    { title: "Practical Files & Lab Manuals", aliases: ["Practical Files & Lab Manuals", "Lab Manuals", "practicals"], icon: "flask-conical", color: "cyan", desc: "Laboratory codes, observations, and viva voce reference files" },
    { title: "Official Scheme & Syllabus", aliases: ["Official Syllabus & Blueprints", "Official Syllabus", "syllabus"], icon: "file-text", color: "purple", desc: "Authorized University syllabus, scheme of examinations, and course outcomes" }
  ];

  traysContainer.innerHTML = categories.map(cat => {
    let items = [];
    cat.aliases.forEach(alias => {
      if (activeSubjData.categories && activeSubjData.categories[alias]) {
        items = items.concat(activeSubjData.categories[alias]);
      }
    });

    if (state.typesetOnly) {
      items = items.filter(i => i.is_typeset);
    }

    const colorClasses = {
      blue: "text-blue-400 bg-blue-500/10 border-blue-500/20",
      indigo: "text-indigo-400 bg-indigo-500/10 border-indigo-500/20",
      amber: "text-amber-400 bg-amber-500/10 border-amber-500/20",
      emerald: "text-emerald-400 bg-emerald-500/10 border-emerald-500/20",
      cyan: "text-cyan-400 bg-cyan-500/10 border-cyan-500/20",
      purple: "text-purple-400 bg-purple-500/10 border-purple-500/20"
    };

    const headerBadge = colorClasses[cat.color] || colorClasses.blue;

    let itemsGridHtml = "";
    if (items.length === 0) {
      itemsGridHtml = `
        <div class="p-6 rounded-xl bg-zinc-950/40 border border-white/5 text-center text-xs text-zinc-500 flex items-center justify-center gap-2">
          <i data-lucide="info" class="w-4 h-4 text-zinc-600"></i>
          <span>${state.typesetOnly ? 'No typeset masters available in this category.' : 'No uploaded materials for this category yet.'}</span>
        </div>
      `;
    } else {
      itemsGridHtml = `
        <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
          ${items.map(r => renderResourceCardHtml(r)).join("")}
        </div>
      `;
    }

    return `
      <div class="p-5 rounded-2xl glass-card border border-white/5 space-y-3">
        <div class="flex items-center justify-between pb-3 border-b border-white/5">
          <div class="flex items-center gap-2.5">
            <div class="w-8 h-8 rounded-lg ${headerBadge} border flex items-center justify-center">
              <i data-lucide="${cat.icon}" class="w-4 h-4"></i>
            </div>
            <div>
              <h3 class="text-sm font-bold text-white flex items-center gap-2">
                <span>${cat.title}</span>
                <span class="px-2 py-0.5 rounded-full text-[10px] font-mono ${headerBadge} border">${items.length}</span>
              </h3>
              <p class="text-[11px] text-zinc-500">${cat.desc}</p>
            </div>
          </div>
        </div>
        ${itemsGridHtml}
      </div>
    `;
  }).join("");

  lucide.createIcons();
}


function renderResourceCardHtml(r) {
  const typesetBadge = r.is_typeset
    ? `<span class="px-2 py-0.5 rounded text-[9px] font-mono font-bold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">💎 TYPESET MASTER</span>`
    : `<span class="px-2 py-0.5 rounded text-[9px] font-mono text-zinc-400 bg-zinc-800 border border-white/5">📄 REFERENCE</span>`;

  const safeTitle = (r.title || '').replace(/'/g, "\\'");
  const encodedPath = encodeURIComponent(r.relative_path || '');

  return `
    <div class="p-4 rounded-xl bg-zinc-900/90 border border-white/10 hover:border-emerald-500/30 transition-all flex flex-col justify-between space-y-3">
      <div class="space-y-2">
        <div class="flex items-center justify-between gap-1.5">
          ${typesetBadge}
          <span class="text-[10px] font-mono text-zinc-500">${r.exam_session || 'Official'}</span>
        </div>
        <h4 class="text-xs font-semibold text-white leading-snug line-clamp-2 hover:text-emerald-400 transition-colors cursor-pointer" onclick="openPdfPreview('${safeTitle}', '${r.relative_path}')">
          ${r.title}
        </h4>
        <div class="flex items-center justify-between text-[10px] font-mono text-zinc-500 pt-1 border-t border-white/5">
          <span>${r.subject_code || 'CODE'}</span>
          <span>${r.size_kb || 0} KB</span>
        </div>
      </div>

      <div class="flex items-center gap-2 pt-1 border-t border-white/5 text-xs">
        <button onclick="openPdfPreview('${safeTitle}', '${r.relative_path}')" class="flex-1 py-1.5 rounded-lg bg-zinc-950 hover:bg-zinc-800 text-zinc-300 hover:text-white font-medium flex items-center justify-center gap-1.5 transition-all">
          <i data-lucide="eye" class="w-3.5 h-3.5"></i>
          <span>Preview</span>
        </button>
        <a href="/api/resources/view?path=${encodedPath}" download="${r.filename || 'document.pdf'}" class="px-3 py-1.5 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white font-medium flex items-center gap-1.5 transition-all" title="Direct Download">
          <i data-lucide="download" class="w-3.5 h-3.5"></i>
        </a>
      </div>
    </div>
  `;
}

function handleUniversalResourceSearch() {
  const searchInput = document.getElementById("resource-search");
  const query = searchInput ? searchInput.value.trim().toLowerCase() : "";
  const clearBtn = document.getElementById("resource-search-clear");
  const statusDiv = document.getElementById("resource-search-status");
  const countSpan = document.getElementById("resource-search-count");
  const searchContainer = document.getElementById("vault-search-results-container");
  const gridContainer = document.getElementById("vault-search-results-grid");
  const hierarchyContainer = document.getElementById("vault-hierarchical-container");
  const summarySpan = document.getElementById("search-results-summary");

  if (!query) {
    clearResourceSearch();
    return;
  }

  if (clearBtn) clearBtn.classList.remove("hidden");
  if (statusDiv) statusDiv.classList.remove("hidden");
  if (hierarchyContainer) hierarchyContainer.classList.add("hidden");
  if (searchContainer) searchContainer.classList.remove("hidden");

  const typesetOnly = state.typesetOnly;
  const filtered = (state.resources || []).filter(r => {
    const matchQuery =
      (r.title && r.title.toLowerCase().includes(query)) ||
      (r.subject && r.subject.toLowerCase().includes(query)) ||
      (r.subject_code && r.subject_code.toLowerCase().includes(query)) ||
      (r.category && r.category.toLowerCase().includes(query)) ||
      (r.exam_session && r.exam_session.toLowerCase().includes(query));
    const matchType = !typesetOnly || r.is_typeset;
    return matchQuery && matchType;
  });

  if (countSpan) countSpan.innerText = `${filtered.length} matching documents found`;
  if (summarySpan) summarySpan.innerText = `Showing ${filtered.length} match(es) for "${query}"`;

  if (gridContainer) {
    if (filtered.length === 0) {
      gridContainer.innerHTML = `
        <div class="col-span-full py-16 text-center text-zinc-500">
          <i data-lucide="file-x" class="w-8 h-8 mx-auto mb-2 text-zinc-600"></i>
          <p class="text-sm">No documents found matching "${query}".</p>
          <button onclick="clearResourceSearch()" class="mt-3 px-3 py-1.5 rounded-lg bg-zinc-800 text-xs text-zinc-300 hover:text-white">Clear Search</button>
        </div>
      `;
    } else {
      gridContainer.innerHTML = filtered.map(r => {
        const safeTitle = (r.title || '').replace(/'/g, "\\'");
        const encodedPath = encodeURIComponent(r.relative_path || '');
        const typesetBadge = r.is_typeset
          ? `<span class="px-2 py-0.5 rounded text-[9px] font-mono font-bold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">💎 TYPESET MASTER</span>`
          : `<span class="px-2 py-0.5 rounded text-[9px] font-mono text-zinc-400 bg-zinc-800 border border-white/5">📄 REFERENCE</span>`;

        return `
          <div class="p-4 rounded-xl glass-card border border-white/10 hover:border-emerald-500/30 transition-all flex flex-col justify-between space-y-3">
            <div class="space-y-2">
              <div class="flex items-center justify-between gap-1.5">
                ${typesetBadge}
                <span class="text-[10px] font-mono text-emerald-400">Sem ${r.semester || 3}</span>
              </div>
              <div class="text-[10px] text-zinc-400 font-mono flex items-center gap-1 truncate">
                <span>${r.subject}</span>
                <span>•</span>
                <span>${r.category}</span>
              </div>
              <h4 class="text-xs font-semibold text-white leading-snug line-clamp-2 hover:text-emerald-400 transition-colors cursor-pointer" onclick="openPdfPreview('${safeTitle}', '${r.relative_path}')">
                ${r.title}
              </h4>
              <div class="flex items-center justify-between text-[10px] font-mono text-zinc-500 pt-1 border-t border-white/5">
                <span>${r.subject_code || 'CODE'}</span>
                <span>${r.size_kb || 0} KB</span>
              </div>
            </div>

            <div class="flex items-center gap-2 pt-1 border-t border-white/5 text-xs">
              <button onclick="openPdfPreview('${safeTitle}', '${r.relative_path}')" class="flex-1 py-1.5 rounded-lg bg-zinc-950 hover:bg-zinc-800 text-zinc-300 hover:text-white font-medium flex items-center justify-center gap-1.5 transition-all">
                <i data-lucide="eye" class="w-3.5 h-3.5"></i>
                <span>Preview</span>
              </button>
              <a href="/api/resources/view?path=${encodedPath}" download="${r.filename || 'document.pdf'}" class="px-3 py-1.5 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white font-medium flex items-center gap-1.5 transition-all" title="Direct Download">
                <i data-lucide="download" class="w-3.5 h-3.5"></i>
              </a>
            </div>
          </div>
        `;
      }).join("");
    }
  }

  lucide.createIcons();
}

function clearResourceSearch() {
  const searchInput = document.getElementById("resource-search");
  if (searchInput) searchInput.value = "";
  const clearBtn = document.getElementById("resource-search-clear");
  if (clearBtn) clearBtn.classList.add("hidden");
  const statusDiv = document.getElementById("resource-search-status");
  if (statusDiv) statusDiv.classList.add("hidden");
  const searchContainer = document.getElementById("vault-search-results-container");
  if (searchContainer) searchContainer.classList.add("hidden");
  const hierarchyContainer = document.getElementById("vault-hierarchical-container");
  if (hierarchyContainer) hierarchyContainer.classList.remove("hidden");
}

function openPdfPreview(title, relPath) {
  document.getElementById("pdf-modal-title").innerText = title;
  const encodedPath = encodeURIComponent(relPath);
  const streamUrl = `/api/resources/view?path=${encodedPath}`;
  document.getElementById("pdf-iframe").src = streamUrl;
  document.getElementById("pdf-download-btn").href = streamUrl;
  document.getElementById("pdf-modal").classList.add("open");
}

function closePdfModal() {
  document.getElementById("pdf-iframe").src = "about:blank";
  document.getElementById("pdf-modal").classList.remove("open");
}

function closePdfModalOnBackdrop(e) {
  closePdfModal();
}

// =============================================================================
// TAB 3: GGSIPU EXAMWEB & MARKSHEET MODULE
// =============================================================================

async function initExamWebSession() {
  const wrapper = document.getElementById("captcha-image-wrapper");
  if (!wrapper) return;
  wrapper.innerHTML = `<span class="text-xs text-zinc-400 animate-pulse font-mono">Loading CAPTCHA...</span>`;
  
  try {
    const res = await fetch("/api/examweb/session");
    const data = await res.json();

    if (data.status === "success" && data.session_id) {
      state.examWebSession = data;
      wrapper.innerHTML = `<img src="${data.captcha_base64}" alt="ExamWeb Captcha" class="h-8 max-h-[36px] object-contain rounded">`;
      
      const ocrContainer = document.getElementById("ocr-suggestion-container");
      const ocrText = document.getElementById("ocr-suggestion-text");
      if (data.ocr_suggestion && data.ocr_suggestion.length >= 4) {
        ocrText.innerText = data.ocr_suggestion;
        ocrContainer.classList.remove("hidden");
      } else {
        ocrContainer.classList.add("hidden");
      }
    } else {
      wrapper.innerHTML = `
        <div class="flex items-center gap-2">
          <span class="text-xs text-amber-400 font-mono">Captcha Timeout</span>
          <button type="button" onclick="initExamWebSession()" class="text-xs text-blue-400 hover:text-blue-300 underline font-semibold flex items-center gap-1">
            <i data-lucide="refresh-cw" class="w-3 h-3"></i> Retry
          </button>
        </div>
      `;
      lucide.createIcons();
    }
  } catch (err) {
    console.error("ExamWeb Session init failed:", err);
    wrapper.innerHTML = `
      <div class="flex items-center gap-2">
        <span class="text-xs text-red-400 font-mono">Connection Retry</span>
        <button type="button" onclick="initExamWebSession()" class="text-xs text-blue-400 hover:text-blue-300 underline font-semibold flex items-center gap-1">
          <i data-lucide="refresh-cw" class="w-3 h-3"></i> Retry
        </button>
      </div>
    `;
    lucide.createIcons();
  }
}

function refreshExamWebCaptcha() {
  const capInput = document.getElementById("examweb-captcha");
  if (capInput) capInput.value = "";
  initExamWebSession();
  showToast("🔄 Captcha refreshed from GGSIPU portal");
}

function applyOcrSuggestion() {
  if (state.examWebSession && state.examWebSession.ocr_suggestion) {
    const input = document.getElementById("examweb-captcha");
    input.value = state.examWebSession.ocr_suggestion;
    input.focus();
    showToast("✨ Auto-suggested CAPTCHA applied");
  }
}

function togglePasswordVisibility(id) {
  const input = document.getElementById(id);
  if (input.type === "password") {
    input.type = "text";
  } else {
    input.type = "password";
  }
}

async function handleExamWebLogin(e) {
  e.preventDefault();
  const username = document.getElementById("examweb-username").value.trim();
  const password = document.getElementById("examweb-password").value.trim();
  const captcha = document.getElementById("examweb-captcha").value.trim();
  const submitBtn = document.getElementById("btn-examweb-submit");
  const statusDiv = document.getElementById("examweb-status");

  if (!state.examWebSession || !state.examWebSession.session_id) {
    showToast("⚠️ Initializing ExamWeb session, please wait...");
    await initExamWebSession();
    return;
  }

  submitBtn.disabled = true;
  submitBtn.innerHTML = `
    <i data-lucide="loader-2" class="w-4 h-4 animate-spin"></i>
    <span>Connecting to GGSIPU ExamWeb...</span>
  `;
  lucide.createIcons();

  statusDiv.classList.remove("hidden");
  statusDiv.className = "text-xs text-center p-3 rounded-xl bg-blue-500/10 text-blue-400 border border-blue-500/20 animate-pulse";
  statusDiv.innerHTML = `<span>🔐 Salting SHA-256 password & authenticating session...</span>`;

  try {
    const res = await fetch("/api/examweb/login", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        session_id: state.examWebSession.session_id,
        username: username,
        password: password,
        captcha: captcha
      })
    });

    const data = await res.json();

    if (res.ok && data.status === "success") {
      state.examWebResult = data;
      statusDiv.className = "text-xs text-center p-3 rounded-xl bg-emerald-500/10 text-emerald-400 border border-emerald-500/20";
      statusDiv.innerHTML = `<span>🎉 Authentication successful! Extracted ${data.semesters.length} semesters and photo.</span>`;
      
      showToast("🎉 Marksheet generated successfully!");
      renderOfficialMarksheet(data);
    } else {
      statusDiv.className = "text-xs text-center p-3 rounded-xl bg-red-500/10 text-red-400 border border-red-500/20";
      statusDiv.innerHTML = `<span>❌ ${data.message || 'Login failed. Please check credentials and captcha.'}</span>`;
      refreshExamWebCaptcha();
    }
  } catch (err) {
    statusDiv.className = "text-xs text-center p-3 rounded-xl bg-red-500/10 text-red-400 border border-red-500/20";
    statusDiv.innerHTML = `<span>❌ Communication error with CampusIQ backend.</span>`;
  } finally {
    submitBtn.disabled = false;
    submitBtn.innerHTML = `
      <i data-lucide="sparkles" class="w-4 h-4"></i>
      <span>Fetch Result & Generate Official Marksheet</span>
    `;
    lucide.createIcons();
  }
}

async function loadExamWebDemo() {
  const statusDiv = document.getElementById("examweb-status");
  statusDiv.classList.remove("hidden");
  statusDiv.className = "text-xs text-center p-3 rounded-xl bg-indigo-500/10 text-indigo-400 border border-indigo-500/20 animate-pulse";
  statusDiv.innerHTML = `<span>⚡ Loading verified official student record...</span>`;

  try {
    const res = await fetch("/api/examweb/demo");
    const data = await res.json();
    if (data.status === "success") {
      state.examWebResult = data;
      showToast("⚡ Verified official marksheet loaded!");
      renderOfficialMarksheet(data);
    } else {
      statusDiv.innerHTML = `<span>Error: ${data.message}</span>`;
    }
  } catch (err) {
    console.error("Demo load error:", err);
  }
}

function renderOfficialMarksheet(data, selectedView = "all") {
  state.examWebSelectedSem = selectedView;
  state.examWebResult = data;
  const container = document.getElementById("examweb-marksheet-container");
  const loginCard = document.getElementById("examweb-login-card");

  loginCard.classList.add("hidden");
  container.classList.remove("hidden");

  const st = data.student;
  const ov = data.overall;
  const backlogs = data.backlogs || st.private_backlogs || [];

  // 1. Private Academic Alert Banner (Zero Public Shaming, strictly for the student)
  let backlogAlertHtml = "";
  if (backlogs.length > 0) {
    backlogAlertHtml = `
      <div class="p-4 rounded-2xl bg-amber-500/10 border border-amber-500/30 text-amber-200 text-xs space-y-2 no-print">
        <div class="flex items-center justify-between">
          <div class="flex items-center gap-2 font-bold text-amber-300">
            <i data-lucide="shield-alert" class="w-4 h-4 text-amber-400"></i>
            <span>Confidential Academic Backlog Advisory</span>
          </div>
          <span class="px-2.5 py-0.5 rounded-full text-[10px] font-mono font-bold bg-amber-500/20 text-amber-300 border border-amber-500/30">
            ${backlogs.length} Paper(s) Requiring Attention
          </span>
        </div>
        <p class="text-zinc-300 text-[11px] leading-relaxed">
          🔒 Private Invariant: Public IPU result lists contain re-appear candidates. CampusIQ suppresses public failure leaderboards and securely delivers this alert strictly to your authenticated session.
        </p>
        <div class="grid grid-cols-1 sm:grid-cols-2 gap-2 pt-1">
          ${backlogs.map(b => `
            <div class="p-2.5 rounded-xl bg-zinc-950/80 border border-amber-500/20 flex items-center justify-between font-mono text-xs">
              <div>
                <span class="font-bold text-white">${b.paper_code}</span>: <span class="text-zinc-300">${b.paper_title}</span>
                <div class="text-[10px] text-zinc-500">Sem ${b.semester} • Credits Lost: ${b.credits_lost || 3}</div>
              </div>
              <div class="text-right">
                <span class="px-1.5 py-0.5 rounded text-[10px] bg-red-500/20 text-red-300 font-bold">Grade ${b.grade} (${b.total_marks}/100)</span>
                <div class="text-[9px] text-zinc-400 mt-0.5">${b.reappear_session || 'Next Exam Cycle'}</div>
              </div>
            </div>
          `).join("")}
        </div>
      </div>
    `;
  } else {
    backlogAlertHtml = `
      <div class="p-3.5 rounded-2xl bg-emerald-500/10 border border-emerald-500/20 text-emerald-300 text-xs flex flex-col sm:flex-row items-start sm:items-center justify-between gap-2 no-print">
        <div class="flex items-center gap-2 font-medium">
          <i data-lucide="check-circle" class="w-4 h-4 text-emerald-400 shrink-0"></i>
          <span>Academic Record in Good Standing • 0 Active Backlogs Detected</span>
        </div>
        <span class="px-2.5 py-0.5 rounded-full text-[10px] font-mono bg-emerald-500/20 text-emerald-300 border border-emerald-500/30 font-bold">
          100% Credits Secured (${ov.credits_earned}/${ov.total_credits} Credits)
        </span>
      </div>
    `;
  }

  // 2. View Tab Navigation Buttons
  const viewTabs = `
    <div class="flex items-center gap-1.5 overflow-x-auto pb-1 scrollbar-none text-xs">
      <button onclick="renderOfficialMarksheet(state.examWebResult, 'all')" class="px-3.5 py-1.5 rounded-lg font-medium transition-all ${selectedView === 'all' ? 'bg-blue-600 text-white shadow' : 'bg-zinc-900 text-zinc-400 hover:text-white'}">
        All 4 Pages (Full Dossier & Print)
      </button>
      <button onclick="renderOfficialMarksheet(state.examWebResult, 'page1')" class="px-3.5 py-1.5 rounded-lg font-medium transition-all ${selectedView === 'page1' ? 'bg-blue-600 text-white shadow' : 'bg-zinc-900 text-zinc-400 hover:text-white'}">
        Page 1: Consolidated Record
      </button>
      ${data.semesters.map((s, idx) => `
        <button onclick="renderOfficialMarksheet(state.examWebResult, 'sem${s.semester}')" class="px-3.5 py-1.5 rounded-lg font-medium transition-all ${selectedView === 'sem' + s.semester ? 'bg-blue-600 text-white shadow' : 'bg-zinc-900 text-zinc-400 hover:text-white'}">
          Page ${idx + 2}: Sem ${s.semester} Grade Sheet (SGPA: ${s.sgpa.toFixed(2)})
        </button>
      `).join("")}
      <button onclick="renderOfficialMarksheet(state.examWebResult, 'page4')" class="px-3.5 py-1.5 rounded-lg font-medium transition-all ${selectedView === 'page4' ? 'bg-blue-600 text-white shadow' : 'bg-zinc-900 text-zinc-400 hover:text-white'}">
        Page 4: Schema of Evaluation
      </button>
    </div>
  `;

  // 3. PAGE 1: Consolidated Performance Record
  const page1Html = `
    <div class="marksheet-page">
      <div class="official-watermark"></div>
      
      <!-- University Header -->
      <div class="text-center space-y-1 pb-4 border-b-2 border-slate-800 relative">
        <div class="flex items-center justify-center gap-4">
          <img src="https://examweb.ggsipu.ac.in/web/images/ggsipulogo.png" alt="GGSIPU" class="w-14 h-14 object-contain" onerror="this.src='/web/images/ggsipulogo.png'">
          <div>
            <h1 class="text-xl sm:text-2xl font-black text-slate-900 marksheet-header-title uppercase tracking-tight">
              Guru Gobind Singh Indraprastha University, Delhi
            </h1>
            <h2 class="text-xs sm:text-sm font-bold text-slate-800 tracking-wider uppercase mt-0.5">
              CONSOLIDATED PERFORMANCE RECORD
            </h2>
            <p class="text-[11px] font-semibold text-slate-600 uppercase">
              ${st.programme_name}
            </p>
          </div>
        </div>
      </div>

      <!-- Student Particulars -->
      <div class="my-5 p-4 border border-slate-300 rounded bg-slate-50/70">
        <div class="grid grid-cols-2 gap-y-2.5 gap-x-6 text-xs">
          <div>
            <span class="font-bold text-slate-600">Student Name:</span>
            <span class="font-bold text-slate-900 ml-2">${st.name}</span>
          </div>
          <div>
            <span class="font-bold text-slate-600">Enrollment No.:</span>
            <span class="font-mono font-bold text-slate-900 ml-2">${st.roll_number}</span>
          </div>
          <div>
            <span class="font-bold text-slate-600">Institution:</span>
            <span class="font-semibold text-slate-800 ml-2">${st.institution_name}</span>
          </div>
          <div>
            <span class="font-bold text-slate-600">Admission Year:</span>
            <span class="font-mono font-semibold text-slate-800 ml-2">${st.admission_year || st.batch || 2025}</span>
          </div>
        </div>
      </div>

      <!-- Consolidated Summary Table -->
      <div class="my-6">
        <table class="w-full text-center border-collapse border border-slate-400 text-xs">
          <thead class="bg-slate-100 font-bold uppercase text-[11px] text-slate-800">
            <tr>
              <th class="p-2.5 border border-slate-300">SEMESTER</th>
              <th class="p-2.5 border border-slate-300">SGPA</th>
              <th class="p-2.5 border border-slate-300">PERCENTAGE (%)</th>
              <th class="p-2.5 border border-slate-300">TOTAL CREDITS</th>
              <th class="p-2.5 border border-slate-300">CREDITS EARNED</th>
              <th class="p-2.5 border border-slate-300">RESULT STATUS</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-slate-200 font-mono text-slate-800">
            ${data.semesters.map(s => `
              <tr>
                <td class="p-2.5 border border-slate-300 font-bold">SEM ${s.semester}</td>
                <td class="p-2.5 border border-slate-300 font-bold text-blue-800">${s.sgpa.toFixed(2)}</td>
                <td class="p-2.5 border border-slate-300 font-semibold">${s.percentage.toFixed(2)}</td>
                <td class="p-2.5 border border-slate-300">${s.total_credits}</td>
                <td class="p-2.5 border border-slate-300 font-bold text-emerald-700">${s.credits_earned}</td>
                <td class="p-2.5 border border-slate-300 font-bold ${s.result_status === 'PASSED' ? 'text-emerald-700' : 'text-red-600'}">${s.result_status}</td>
              </tr>
            `).join("")}
          </tbody>
        </table>
      </div>

      <!-- Highlights Box -->
      <div class="my-6 p-4 border-2 border-slate-800 rounded bg-slate-100/90 flex items-center justify-around text-center">
        <div>
          <span class="block text-[11px] font-bold text-slate-600 uppercase tracking-wider">CUMULATIVE CGPA</span>
          <span class="text-3xl font-black font-mono text-blue-900">${ov.cgpa.toFixed(2)}</span>
        </div>
        <div class="h-12 border-r-2 border-slate-300"></div>
        <div>
          <span class="block text-[11px] font-bold text-slate-600 uppercase tracking-wider">OVERALL PERCENTAGE</span>
          <span class="text-3xl font-black font-mono text-slate-900">${ov.exact_percentage || (ov.percentage.toFixed(3) + ' %')}</span>
        </div>
      </div>

      <!-- Footer Notes -->
      <div class="mt-8 pt-4 border-t border-slate-300 text-[10.5px] text-slate-600 space-y-1">
        <p><strong>Note:</strong> Percentage shown is computed from total marks (subject-wise totals out of 100).</p>
        <p class="text-slate-500 italic">Disclaimer: Official consolidated record verified against GGSIPU ExamWeb examination server.</p>
      </div>

      <div class="mt-12 pt-6 border-t border-slate-300 flex items-end justify-between text-xs text-slate-600 font-mono">
        <div>
          <div>Report Generated On: ${new Date().toLocaleDateString('en-GB', { day: '2-digit', month: 'short', year: 'numeric' })}</div>
          <div class="text-[9.5px] text-slate-400">CampusIQ Relay • examweb.ggsipu.ac.in</div>
        </div>
        <div class="stamp-seal">
          <span>GGSIPU</span>
          <span>EXAMINATION</span>
          <span>DIVISION</span>
        </div>
        <div class="text-right">
          <div class="font-bold uppercase text-slate-800 text-[10px]">Controller of Examinations</div>
          <div class="text-[9px] text-slate-500">Page 1 of 4</div>
        </div>
      </div>
    </div>
  `;

  // 4. PAGES 2 & 3: Semester Grade Sheets
  const semesterPagesHtml = data.semesters.map((sem, sIdx) => {
    return `
      <div class="marksheet-page">
        <div class="official-watermark"></div>
        
        <!-- Header -->
        <div class="text-center space-y-1 pb-4 border-b-2 border-slate-800 relative">
          <div class="flex items-center justify-center gap-4">
            <img src="https://examweb.ggsipu.ac.in/web/images/ggsipulogo.png" alt="GGSIPU" class="w-12 h-12 object-contain" onerror="this.src='/web/images/ggsipulogo.png'">
            <div>
              <h1 class="text-lg sm:text-xl font-black text-slate-900 marksheet-header-title uppercase tracking-tight">
                Guru Gobind Singh Indraprastha University, Delhi
              </h1>
              <h2 class="text-xs sm:text-sm font-bold text-slate-800 tracking-wider uppercase mt-0.5">
                SEMESTER GRADE SHEET
              </h2>
              <p class="text-[11px] font-semibold text-slate-600 uppercase">
                ${st.programme_name}
              </p>
            </div>
          </div>
        </div>

        <!-- Student Particulars + Photo -->
        <div class="my-4 p-3 border border-slate-300 rounded bg-slate-50 flex items-center justify-between gap-4">
          <div class="flex-1 grid grid-cols-2 gap-y-1.5 gap-x-4 text-xs">
            <div><span class="font-bold text-slate-600">Name:</span> <span class="font-bold text-slate-900 ml-1.5">${st.name}</span></div>
            <div><span class="font-bold text-slate-600">Enrollment No.:</span> <span class="font-mono font-bold text-slate-900 ml-1.5">${st.roll_number}</span></div>
            <div><span class="font-bold text-slate-600">Year/Semester:</span> <span class="font-bold text-slate-800 ml-1.5">${sem.semester_name || ('SEMESTER ' + sem.semester)}</span></div>
            <div><span class="font-bold text-slate-600">Examination:</span> <span class="font-mono text-slate-800 ml-1.5">${sem.examination}</span></div>
            <div><span class="font-bold text-slate-600">School/Institution:</span> <span class="text-slate-800 font-semibold ml-1.5 text-[11px]">${st.institution_name}</span></div>
            <div><span class="font-bold text-slate-600">Declared Date:</span> <span class="font-mono text-slate-800 ml-1.5">${sem.declared_date || 'Declared'}</span></div>
          </div>
          <div class="flex flex-col items-center shrink-0">
            <div class="photo-box flex items-center justify-center overflow-hidden">
              ${st.photo_base64 ? `<img src="${st.photo_base64}" alt="${st.name}" class="w-full h-full object-cover">` : `<div class="text-[9px] text-slate-400 text-center font-mono">AFFIX PHOTO</div>`}
            </div>
            <span class="text-[8px] font-mono text-slate-500 mt-0.5 uppercase">Official Photo</span>
          </div>
        </div>

        <!-- Grade Sheet Table with INT, EXT, Total, CS, Grade, GP -->
        <table class="w-full marksheet-grades-table">
          <thead>
            <tr>
              <th style="width: 14%;">Paper Code</th>
              <th style="width: 38%;">Paper</th>
              <th style="width: 7%;" class="text-center">Credit</th>
              <th style="width: 7%;" class="text-center">INT</th>
              <th style="width: 7%;" class="text-center">EXT</th>
              <th style="width: 7%;" class="text-center">Total</th>
              <th style="width: 6%;" class="text-center">CS</th>
              <th style="width: 7%;" class="text-center">Grade</th>
              <th style="width: 7%;" class="text-center">GP</th>
            </tr>
          </thead>
          <tbody>
            ${sem.subjects.map(s => {
              const gradeColor = s.grade === "O" ? "#047857" : (s.grade === "A+" || s.grade === "A" ? "#1d4ed8" : (s.grade === "F" ? "#b91c1c" : "#334155"));
              return `
                <tr>
                  <td class="font-mono font-bold">${s.paper_code}</td>
                  <td class="font-medium text-[11px]">${s.paper_title || s.subject_name}</td>
                  <td class="text-center font-mono">${s.credits}</td>
                  <td class="text-center font-mono">${s.internal_marks || '-'}</td>
                  <td class="text-center font-mono">${s.external_marks || '-'}</td>
                  <td class="text-center font-mono font-bold">${s.total_marks}</td>
                  <td class="text-center font-mono font-bold">${s.credits_secured !== undefined ? s.credits_secured : s.credits}</td>
                  <td class="text-center font-bold" style="color: ${gradeColor};">${s.grade}</td>
                  <td class="text-center font-mono font-semibold">${s.grade_point}</td>
                </tr>
              `;
            }).join("")}
          </tbody>
        </table>

        <!-- Semester & Cumulative Record Footers -->
        <div class="mt-4 p-3 border-2 border-slate-700 rounded bg-slate-50 grid grid-cols-2 gap-4 text-xs font-mono font-bold text-slate-900">
          <div>
            CURRENT SEMESTER RECORD: CREDITS EARNED = <span class="text-blue-800">${sem.credits_earned}</span> &nbsp;&nbsp; SGPA = <span class="text-blue-800">${sem.sgpa.toFixed(2)}</span>
          </div>
          <div class="text-right">
            CUMULATIVE RECORD: CREDITS EARNED = <span class="text-slate-900">${sem.cumulative_credits}</span> &nbsp;&nbsp; CGPA = <span class="text-slate-900">${sem.cumulative_cgpa.toFixed(2)}</span>
          </div>
        </div>

        <div class="mt-4 pt-2 border-t border-slate-300 text-[10px] text-slate-600 font-mono flex items-center justify-between">
          <div>INT: Internal Marks; EXT: External Marks; CS: Credits Secured; GP: Grade Point.</div>
          <div>Page ${sIdx + 2} of 4</div>
        </div>
      </div>
    `;
  });

  // 5. PAGE 4: Schema of Evaluation
  const page4Html = `
    <div class="marksheet-page">
      <div class="official-watermark"></div>
      
      <div class="text-center space-y-1 pb-4 border-b-2 border-slate-800 relative">
        <h1 class="text-xl font-black text-slate-900 marksheet-header-title uppercase tracking-wider">
          SCHEMA OF EVALUATION
        </h1>
        <p class="text-xs font-semibold text-slate-700 tracking-wider">
          Guru Gobind Singh Indraprastha University, Delhi • Statutory Evaluation Framework
        </p>
      </div>

      <div class="my-6 space-y-5 text-xs text-slate-800">
        <div class="space-y-2">
          <h3 class="font-bold text-sm text-slate-900 border-b border-slate-300 pb-1">Credit & Marks:</h3>
          <ul class="space-y-1.5 list-none pl-1">
            <li><strong>(a)</strong> One credit is equal to one hour lecture or two hours of laboratory work per week.</li>
            <li><strong>(b)</strong> The maximum marks in each paper is 100. Minimum passing marks in each paper is 40.</li>
            <li><strong>(c)</strong> Full credits are awarded after passing in a course; otherwise no credits are awarded.</li>
            <li><strong>(d)</strong> Grade point is based on the course total as per the grading system below.</li>
          </ul>
        </div>

        <div class="space-y-2">
          <h3 class="font-bold text-sm text-slate-900 border-b border-slate-300 pb-1">Grading System:</h3>
          <table class="w-full text-center border-collapse border border-slate-400 text-xs">
            <thead class="bg-slate-100 font-bold text-slate-800 uppercase text-[11px]">
              <tr>
                <th class="p-2 border border-slate-300">Marks</th>
                <th class="p-2 border border-slate-300">Grade</th>
                <th class="p-2 border border-slate-300">Grade Point</th>
              </tr>
            </thead>
            <tbody class="divide-y divide-slate-200 font-mono text-slate-800">
              <tr><td class="p-1.5 border border-slate-300">90 - 100</td><td class="p-1.5 border border-slate-300 font-bold text-emerald-700">O</td><td class="p-1.5 border border-slate-300 font-bold">10</td></tr>
              <tr><td class="p-1.5 border border-slate-300">75 - 89</td><td class="p-1.5 border border-slate-300 font-bold text-blue-700">A+</td><td class="p-1.5 border border-slate-300 font-bold">9</td></tr>
              <tr><td class="p-1.5 border border-slate-300">65 - 74</td><td class="p-1.5 border border-slate-300 font-bold text-blue-600">A</td><td class="p-1.5 border border-slate-300 font-bold">8</td></tr>
              <tr><td class="p-1.5 border border-slate-300">55 - 64</td><td class="p-1.5 border border-slate-300 font-bold text-slate-700">B+</td><td class="p-1.5 border border-slate-300 font-bold">7</td></tr>
              <tr><td class="p-1.5 border border-slate-300">50 - 54</td><td class="p-1.5 border border-slate-300 font-bold text-slate-700">B</td><td class="p-1.5 border border-slate-300 font-bold">6</td></tr>
              <tr><td class="p-1.5 border border-slate-300">45 - 49</td><td class="p-1.5 border border-slate-300 font-bold text-slate-700">C</td><td class="p-1.5 border border-slate-300 font-bold">5</td></tr>
              <tr><td class="p-1.5 border border-slate-300">40 - 44</td><td class="p-1.5 border border-slate-300 font-bold text-slate-700">P</td><td class="p-1.5 border border-slate-300 font-bold">4</td></tr>
              <tr><td class="p-1.5 border border-slate-300">Less than 40 or absent</td><td class="p-1.5 border border-slate-300 font-bold text-red-700">F</td><td class="p-1.5 border border-slate-300 font-bold">0</td></tr>
            </tbody>
          </table>
        </div>

        <div class="space-y-2">
          <h3 class="font-bold text-sm text-slate-900 border-b border-slate-300 pb-1">Averages are given below:</h3>
          <div class="grid grid-cols-2 gap-4 font-mono text-xs bg-slate-50 p-4 border border-slate-300 rounded">
            <div>
              <p class="font-bold text-slate-700">Semester Grade Point Average:</p>
              <p class="text-sm font-bold text-blue-900 my-1">SGPA = &Sigma;(Ci * Gi) / &Sigma;Ci</p>
            </div>
            <div>
              <p class="font-bold text-slate-700">Cumulative Grade Point Average:</p>
              <p class="text-sm font-bold text-blue-900 my-1">CGPA = &Sigma;(Ci * Gi) / &Sigma;Ci</p>
            </div>
          </div>
          <div class="text-[11px] text-slate-600 font-mono pt-1">
            Where:<br>
            • Ci = number of credits in the i-th course of the semester.<br>
            • Gi = grade points of the i-th course of the semester.
          </div>
        </div>
      </div>

      <div class="mt-8 pt-4 border-t border-slate-300 text-[10px] text-slate-500 font-mono flex items-center justify-between">
        <div>Date of Download: ${new Date().toLocaleDateString('en-GB', { day: '2-digit', month: 'short', year: 'numeric' })} • GGSIPU ExamWeb Scraper Relay</div>
        <div>Page 4 of 4</div>
      </div>
    </div>
  `;

  // Filter content based on selectedView
  let displayedPagesHtml = "";
  if (selectedView === "all") {
    displayedPagesHtml = page1Html + semesterPagesHtml.join("") + page4Html;
  } else if (selectedView === "page1") {
    displayedPagesHtml = page1Html;
  } else if (selectedView.startsWith("sem")) {
    const semNum = parseInt(selectedView.replace("sem", ""));
    const foundIndex = data.semesters.findIndex(s => s.semester === semNum);
    displayedPagesHtml = foundIndex >= 0 ? semesterPagesHtml[foundIndex] : page1Html;
  } else if (selectedView === "page4") {
    displayedPagesHtml = page4Html;
  } else {
    displayedPagesHtml = page1Html + semesterPagesHtml.join("") + page4Html;
  }

  container.innerHTML = `
    <!-- Action Toolbar (Hidden during print) -->
    <div class="p-4 rounded-2xl glass-card border border-white/10 flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-3 no-print">
      ${viewTabs}
      <div class="flex items-center gap-2">
        <button onclick="printOfficialMarksheet()" class="px-4 py-2 rounded-xl bg-blue-600 hover:bg-blue-500 text-white font-semibold text-xs transition-all flex items-center gap-1.5 shadow-md">
          <i data-lucide="printer" class="w-4 h-4"></i>
          <span>Print / Export PDF</span>
        </button>
        <button onclick="resetExamWebSession()" class="px-3.5 py-2 rounded-xl bg-zinc-900 hover:bg-zinc-800 border border-white/10 text-zinc-300 hover:text-white font-medium text-xs transition-all flex items-center gap-1.5">
          <i data-lucide="log-out" class="w-4 h-4"></i>
          <span>Exit / New Login</span>
        </button>
      </div>
    </div>

    <!-- Private Backlog Alert Banner -->
    ${backlogAlertHtml}

    <!-- Official Authentic Marksheet Canvas (Printed on A4) -->
    <div id="printable-marksheet" class="official-marksheet-wrapper">
      ${displayedPagesHtml}
    </div>
  `;

  lucide.createIcons();
  window.scrollTo({ top: 0, behavior: "smooth" });
}

function printOfficialMarksheet() {
  window.print();
}

function resetExamWebSession() {
  state.examWebResult = null;
  const container = document.getElementById("examweb-marksheet-container");
  const loginCard = document.getElementById("examweb-login-card");
  container.classList.add("hidden");
  loginCard.classList.remove("hidden");
  refreshExamWebCaptcha();
}




// =============================================================================
// TAB 6: FACULTY ADMIN ROSTER & CONFIDENTIAL STUDENT DOSSIERS
// =============================================================================

async function loadAdminRoster() {
  const grid = document.getElementById("admin-students-grid");
  const emptyState = document.getElementById("admin-empty-state");
  if (!grid) return;

  grid.innerHTML = `
    <div class="col-span-full py-12 text-center text-zinc-500 flex items-center justify-center gap-2">
      <i data-lucide="loader-2" class="w-5 h-5 animate-spin text-emerald-400"></i>
      <span>Loading student academic dossiers...</span>
    </div>
  `;
  lucide.createIcons();

  try {
    const res = await fetch("/api/admin/students");
    const data = await res.json();
    const students = data.students || [];
    state.adminStudents = students;

    // Update KPI summary cards
    const totalEl = document.getElementById("admin-kpi-total");
    const avgCgpaEl = document.getElementById("admin-kpi-avg-cgpa");
    const cleanEl = document.getElementById("admin-kpi-clean");
    const backlogsEl = document.getElementById("admin-kpi-backlogs");

    if (totalEl) totalEl.textContent = students.length;
    if (avgCgpaEl) {
      const avg = students.length > 0 
        ? (students.reduce((acc, s) => acc + (s.cgpa || 0), 0) / students.length).toFixed(2)
        : "0.00";
      avgCgpaEl.textContent = avg;
    }
    if (cleanEl) cleanEl.textContent = students.filter(s => (s.backlogs_count || 0) === 0).length;
    if (backlogsEl) backlogsEl.textContent = students.filter(s => (s.backlogs_count || 0) > 0).length;

    filterAdminRoster();
  } catch (err) {
    console.error("Admin roster load error:", err);
    if (grid) {
      grid.innerHTML = `
        <div class="col-span-full py-8 text-center text-red-400 text-xs">
          Failed to load student dossiers from local registry.
        </div>
      `;
    }
  }
}

function filterAdminRoster() {
  const searchInput = document.getElementById("admin-search-input");
  const statusFilter = document.getElementById("admin-filter-status");
  const query = searchInput ? searchInput.value.toLowerCase().trim() : "";
  const filter = statusFilter ? statusFilter.value : "all";

  let filtered = state.adminStudents || [];

  if (query) {
    filtered = filtered.filter(s => 
      (s.name && s.name.toLowerCase().includes(query)) ||
      (s.roll_number && s.roll_number.toLowerCase().includes(query)) ||
      (s.programme_name && s.programme_name.toLowerCase().includes(query))
    );
  }

  if (filter === "clean") {
    filtered = filtered.filter(s => (s.backlogs_count || 0) === 0);
  } else if (filter === "backlog") {
    filtered = filtered.filter(s => (s.backlogs_count || 0) > 0);
  }

  renderAdminStudents(filtered);
}

function renderAdminStudents(students) {
  const grid = document.getElementById("admin-students-grid");
  const emptyState = document.getElementById("admin-empty-state");
  if (!grid) return;

  if (!students.length) {
    grid.innerHTML = "";
    if (emptyState) emptyState.classList.remove("hidden");
    return;
  }

  if (emptyState) emptyState.classList.add("hidden");

  grid.innerHTML = students.map(s => {
    const isClean = (s.backlogs_count || 0) === 0;
    const initial = s.name ? s.name.charAt(0).toUpperCase() : "S";

    return `
      <div class="p-5 rounded-2xl glass-card border border-white/10 hover:border-emerald-500/30 transition-all flex flex-col justify-between space-y-4 shadow-lg group">
        
        <!-- Header: Student Avatar & Info -->
        <div class="flex items-start gap-3.5">
          <div class="w-14 h-16 rounded-xl bg-zinc-900 border border-white/15 overflow-hidden shrink-0 flex items-center justify-center shadow-md">
            ${s.photo_base64 ? `
              <img src="${s.photo_base64}" alt="${s.name}" class="w-full h-full object-cover">
            ` : `
              <span class="text-xl font-bold font-mono text-zinc-400 group-hover:text-emerald-400 transition-colors">${initial}</span>
            `}
          </div>

          <div class="overflow-hidden flex-1 min-w-0">
            <div class="flex items-center gap-1.5 flex-wrap">
              <span class="font-mono font-bold text-xs text-emerald-400 tracking-wider">${s.roll_number}</span>
              ${isClean ? `
                <span class="px-1.5 py-0.2 rounded text-[9px] font-mono bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">GOOD STANDING</span>
              ` : `
                <span class="px-1.5 py-0.2 rounded text-[9px] font-mono bg-red-500/10 text-red-400 border border-red-500/20 font-bold">${s.backlogs_count} BACKLOG(S)</span>
              `}
            </div>
            <h3 class="text-sm font-bold text-white truncate mt-0.5">${s.name}</h3>
            <p class="text-[11px] text-zinc-400 truncate">${s.programme_name || 'B.Tech (CSE)'}</p>
            <p class="text-[10px] text-zinc-500 truncate">${s.institution_name || 'MAIT'} • Batch ${s.batch || 2025}</p>
          </div>
        </div>

        <!-- Academic Metrics -->
        <div class="grid grid-cols-3 gap-2 p-2.5 rounded-xl bg-zinc-950/70 border border-white/5 text-center">
          <div>
            <span class="block text-[10px] font-mono text-zinc-500 uppercase">CGPA</span>
            <span class="text-sm font-black font-mono text-blue-400">${(s.cgpa || 0).toFixed(2)}</span>
          </div>
          <div>
            <span class="block text-[10px] font-mono text-zinc-500 uppercase">Agg. %</span>
            <span class="text-sm font-bold font-mono text-white">${(s.percentage || 0).toFixed(1)}%</span>
          </div>
          <div>
            <span class="block text-[10px] font-mono text-zinc-500 uppercase">Sems</span>
            <span class="text-sm font-bold font-mono text-zinc-300">${s.total_semesters || 2}</span>
          </div>
        </div>

        <!-- Action Button -->
        <div class="pt-1">
          <button onclick="inspectStudentDossier('${s.roll_number}')" class="w-full py-2.5 px-4 rounded-xl bg-zinc-900 hover:bg-emerald-600/20 hover:border-emerald-500/40 border border-white/10 text-zinc-300 hover:text-white font-semibold text-xs transition-all flex items-center justify-center gap-1.5 shadow-sm">
            <i data-lucide="file-text" class="w-3.5 h-3.5 text-emerald-400"></i>
            <span>Inspect Full Dossier</span>
          </button>
        </div>

      </div>
    `;
  }).join("");

  lucide.createIcons();
}

async function inspectStudentDossier(roll) {
  showToast(`Loading academic dossier for ${roll}...`);
  try {
    const res = await fetch(`/api/admin/students/${roll}`);
    const data = await res.json();
    if (data.status === "success" && data.student) {
      // Switch to results tab & render official marksheet
      switchTab("results");
      switchResultMode("examweb");
      renderOfficialMarksheet(data.student, "all");
      showToast(`Dossier loaded: ${data.student.student.name} (${roll})`);
    } else {
      showToast(`Student record for ${roll} could not be retrieved.`);
    }
  } catch (err) {
    console.error("Dossier inspection error:", err);
    showToast("Error inspecting student dossier.");
  }
}




// =============================================================================
// ON-DEMAND SGPA / GPA FORECASTER MODAL
// =============================================================================

function openGpaModal() {
  const modal = document.getElementById("gpa-modal");
  if (modal) {
    modal.classList.add("open");
    initCalculator();
    lucide.createIcons();
  }
}

function closeGpaModal() {
  const modal = document.getElementById("gpa-modal");
  if (modal) modal.classList.remove("open");
}

function closeGpaModalOnBackdrop(e) {
  if (e.target.id === "gpa-modal") closeGpaModal();
}

function initCalculator() {
  const container = document.getElementById("calculator-rows");
  if (!container) return;

  container.innerHTML = SEM3_SUBJECTS.map((sub, idx) => `
    <div class="p-3 rounded-xl bg-zinc-900/60 border border-white/5 flex items-center justify-between gap-3">
      <div class="overflow-hidden">
        <span class="text-[10px] font-mono text-cyan-400">${sub.code}</span>
        <h4 class="text-xs font-semibold text-white truncate">${sub.name}</h4>
      </div>
      <div class="flex items-center gap-6 shrink-0">
        <span class="font-mono text-xs text-zinc-400">${sub.credits} cr</span>
        <select onchange="calculateForecast()" class="calc-grade-select p-1.5 rounded-lg bg-zinc-950 border border-white/10 text-xs font-mono text-white focus:outline-none focus:border-cyan-500 w-24 text-center">
          ${Object.keys(GRADE_POINTS).map(g => `<option value="${g}" ${g === sub.defaultGrade ? 'selected' : ''}>${g}</option>`).join("")}
        </select>
      </div>
    </div>
  `).join("");

  calculateForecast();
}

function calculateForecast() {
  const selects = document.querySelectorAll(".calc-grade-select");
  let totalCredits = 0;
  let weightedPoints = 0.0;

  selects.forEach((sel, idx) => {
    const sub = SEM3_SUBJECTS[idx];
    if (!sub) return;
    const grade = sel.value;
    const gp = GRADE_POINTS[grade] || 0.0;
    totalCredits += sub.credits;
    weightedPoints += (sub.credits * gp);
  });

  const sgpa = totalCredits > 0 ? (weightedPoints / totalCredits) : 0.0;
  const percent = sgpa * 10.0; // Standard IPU CGPA-to-Percentage conversion

  const sgpaEl = document.getElementById("forecast-sgpa");
  const crEl = document.getElementById("forecast-credits");
  const pctEl = document.getElementById("forecast-percent");
  const divEl = document.getElementById("forecast-division");

  if (sgpaEl) sgpaEl.innerText = sgpa.toFixed(2);
  if (crEl) crEl.innerText = totalCredits;
  if (pctEl) pctEl.innerText = `${percent.toFixed(1)}%`;

  let division = "Pass";
  if (sgpa >= 8.5) division = "First Class with Distinction";
  else if (sgpa >= 7.5) division = "First Class";
  else if (sgpa >= 6.0) division = "Second Class";

  if (divEl) divEl.innerText = division;
}

// =============================================================================
// TAB 4: STUDENT COMMUNITY & PROFILE SEGREGATION
// =============================================================================

function initCommunityHub() {
  if (!state.currentUser) {
    fetchCurrentUser();
  }
  fetchDirectoryStudents();
}

function switchCommunitySubView(subview) {
  state.activeCommunitySubView = subview;

  // Toggle subnav button styles
  const navBtns = {
    directory: document.getElementById("subnav-directory"),
    myprofile: document.getElementById("subnav-myprofile"),
    verify: document.getElementById("subnav-verify")
  };

  Object.keys(navBtns).forEach(k => {
    const btn = navBtns[k];
    if (!btn) return;
    if (k === subview) {
      btn.className = "px-3.5 py-1.5 rounded-lg bg-indigo-600 text-white font-semibold flex items-center gap-1.5 transition-all shadow-[0_0_10px_rgba(99,102,241,0.3)]";
    } else {
      btn.className = "px-3.5 py-1.5 rounded-lg text-zinc-400 hover:text-white font-medium flex items-center gap-1.5 transition-all";
    }
  });

  // Toggle subviews
  const views = {
    directory: document.getElementById("subview-directory"),
    myprofile: document.getElementById("subview-myprofile"),
    verify: document.getElementById("subview-verify")
  };

  Object.keys(views).forEach(k => {
    const v = views[k];
    if (!v) return;
    if (k === subview) {
      v.classList.remove("hidden");
    } else {
      v.classList.add("hidden");
    }
  });

  if (subview === "myprofile" && state.currentUser) {
    populateMyProfileUI(state.currentUser);
  } else if (subview === "verify" && state.currentUser) {
    renderMyVerifications(state.currentUser.verifications || []);
  }

  lucide.createIcons();
}

async function fetchCurrentUser() {
  if (!state.sessionToken) {
    state.currentUser = null;
    state.currentStudent = null;
    renderHeaderAuth(null, null);
    populateMyProfileUI(null, null);
    return;
  }

  try {
    const res = await fetch("/api/auth/me", {
      headers: {
        "Authorization": `Bearer ${state.sessionToken}`
      }
    });
    const data = await res.json();
    if (data.status === "success" && data.is_authenticated && data.user) {
      state.currentUser = data.user;
      state.currentStudent = data.student;
      renderHeaderAuth(data.user, data.student);
      populateMyProfileUI(data.user, data.student);
    } else {
      localStorage.removeItem("campusiq_session_token");
      state.sessionToken = null;
      state.currentUser = null;
      state.currentStudent = null;
      renderHeaderAuth(null, null);
      populateMyProfileUI(null, null);
    }
  } catch (err) {
    console.error("Failed to fetch current user session:", err);
    renderHeaderAuth(null, null);
    populateMyProfileUI(null, null);
  }
}

function renderHeaderAuth(user, student) {
  const container = document.getElementById("header-auth-container");
  if (!container) return;

  if (!user) {
    container.innerHTML = `
      <button onclick="openGoogleAuthModal()" class="flex items-center gap-2 px-3 py-1.5 rounded-xl bg-blue-600 hover:bg-blue-500 text-white transition-all text-xs font-semibold shadow-[0_0_12px_rgba(59,130,246,0.3)]">
        <svg class="w-3.5 h-3.5" viewBox="0 0 24 24">
          <path fill="#ffffff" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"/>
          <path fill="#ffffff" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"/>
          <path fill="#ffffff" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.06H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.94l2.85-2.22.81-.63z"/>
          <path fill="#ffffff" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.06l3.66 2.84c.87-2.6 3.3-4.52 6.16-4.52z"/>
        </svg>
        <span>Sign In</span>
      </button>
    `;
    return;
  }

  const rollText = user.roll_number ? `Roll: ${user.roll_number}` : "Google Verified";
  const avatarSrc = user.avatar_url || (student && student.profile && student.profile.avatar_url) || `https://api.dicebear.com/7.x/bottts/svg?seed=${encodeURIComponent(user.name)}`;

  container.innerHTML = `
    <div class="relative">
      <button onclick="toggleUserDropdown(event)" class="flex items-center gap-2 px-2.5 py-1.5 rounded-xl bg-zinc-900 border border-white/10 hover:border-indigo-500/50 hover:bg-zinc-800 transition-all text-xs text-zinc-200">
        <img src="${avatarSrc}" class="w-6 h-6 rounded-full border border-indigo-500/40 bg-zinc-800 object-cover" />
        <div class="text-left hidden sm:block">
          <span class="font-semibold block leading-tight text-white text-[11px]">${user.name}</span>
          <span class="text-[9px] text-emerald-400 font-mono flex items-center gap-1">
            <span class="w-1.5 h-1.5 rounded-full bg-emerald-400"></span>
            ${rollText}
          </span>
        </div>
        <i data-lucide="chevron-down" class="w-3 h-3 text-zinc-400 ml-0.5"></i>
      </button>

      <div id="user-dropdown-menu" class="hidden absolute right-0 mt-2 w-48 py-1 rounded-xl bg-zinc-900 border border-white/10 shadow-2xl z-50 text-xs">
        <div class="px-3 py-2 border-b border-white/5">
          <p class="font-bold text-white truncate">${user.name}</p>
          <p class="text-[10px] text-zinc-400 font-mono truncate">${user.email}</p>
        </div>
        <button onclick="switchTab('community'); switchCommunitySubView('myprofile'); toggleUserDropdown(null, false);" class="w-full text-left px-3 py-2 text-zinc-300 hover:bg-zinc-800 hover:text-white flex items-center gap-2">
          <i data-lucide="user" class="w-3.5 h-3.5 text-indigo-400"></i>
          <span>My Profile & Privacy</span>
        </button>
        <button onclick="switchTab('results'); toggleUserDropdown(null, false);" class="w-full text-left px-3 py-2 text-zinc-300 hover:bg-zinc-800 hover:text-white flex items-center gap-2">
          <i data-lucide="award" class="w-3.5 h-3.5 text-blue-400"></i>
          <span>ExamWeb Results</span>
        </button>
        <div class="border-t border-white/5 mt-1 pt-1">
          <button onclick="handleSignOut(); toggleUserDropdown(null, false);" class="w-full text-left px-3 py-2 text-red-400 hover:bg-red-500/10 flex items-center gap-2">
            <i data-lucide="log-out" class="w-3.5 h-3.5"></i>
            <span>Sign Out</span>
          </button>
        </div>
      </div>
    </div>
  `;
  lucide.createIcons();
}

function toggleUserDropdown(e, forceState) {
  if (e) e.stopPropagation();
  const menu = document.getElementById("user-dropdown-menu");
  if (!menu) return;
  if (typeof forceState === "boolean") {
    menu.classList.toggle("hidden", !forceState);
  } else {
    menu.classList.toggle("hidden");
  }
}

document.addEventListener("click", () => {
  toggleUserDropdown(null, false);
});

function populateMyProfileUI(user, student) {
  const guestCard = document.getElementById("my-profile-guest-card");
  const content = document.getElementById("my-profile-content");

  if (!user) {
    if (guestCard) guestCard.classList.remove("hidden");
    if (content) content.classList.add("hidden");
    return;
  }

  if (guestCard) guestCard.classList.add("hidden");
  if (content) content.classList.remove("hidden");

  const avatar = document.getElementById("my-profile-avatar");
  const name = document.getElementById("my-profile-name");
  const sub = document.getElementById("my-profile-sub");
  const email = document.getElementById("my-profile-email");
  const unlinkedBanner = document.getElementById("my-profile-unlinked-banner");

  const avatarSrc = user.avatar_url || (student && student.profile && student.profile.avatar_url) || `https://api.dicebear.com/7.x/bottts/svg?seed=${encodeURIComponent(user.name)}`;
  if (avatar) avatar.src = avatarSrc;
  if (name) name.innerText = user.name;
  if (email) email.innerText = user.email;

  if (student) {
    if (sub) sub.innerText = `Roll: ${student.roll_number} • ${student.institution_name || 'MAIT'} ${student.programme_name ? student.programme_name.split(' ')[0] : 'CSE'}`;
    if (unlinkedBanner) unlinkedBanner.classList.add("hidden");

    const p = student.profile || {};
    const priv = p.privacy_settings || student.privacy_settings || student.privacy || {};
    const setCheck = (id, val) => {
      const el = document.getElementById(id);
      if (el) el.checked = val !== false;
    };
    setCheck("priv-public-profile", priv.public_profile !== false && priv.is_public !== false);
    setCheck("priv-show-cgpa", priv.show_cgpa);
    setCheck("priv-show-class", priv.show_class_details);
    setCheck("priv-show-socials", priv.show_socials);
    setCheck("priv-show-exp", priv.show_experience);

    const setVal = (id, val) => {
      const el = document.getElementById(id);
      if (el) el.value = val || "";
    };
    setVal("edit-class-section", p.class_section || student.class_section);
    setVal("edit-practical-group", p.practical_group || student.practical_group);
    setVal("edit-bio", p.bio || student.bio);

    const socials = p.socials || student.socials || {};
    setVal("edit-github", socials.github);
    setVal("edit-linkedin", socials.linkedin);
    setVal("edit-portfolio", socials.portfolio);

    const rawVerifs = p.verifications || student.verifications || {};
    const verifList = Array.isArray(rawVerifs)
      ? rawVerifs
      : Object.entries(rawVerifs).map(([f, v]) => ({
          field: f,
          claim: v.badge || v.claim || f,
          status: v.status || "VERIFIED",
          document_name: v.proof_file || v.proof_type || "Verified Audit",
          verified_at: v.verified_at || "Active"
        }));
    renderMyVerifications(verifList);
  } else {
    if (sub) sub.innerText = user.roll_number ? `Roll: ${user.roll_number}` : "Roll Number Not Linked";
    if (unlinkedBanner) unlinkedBanner.classList.remove("hidden");
    renderMyVerifications([]);
  }

  lucide.createIcons();
}

function renderMyVerifications(verifications) {
  const container = document.getElementById("my-verifications-list");
  if (!container) return;

  if (!verifications.length) {
    container.innerHTML = `
      <div class="col-span-full p-4 rounded-xl bg-zinc-950 border border-white/5 text-center text-zinc-500">
        No field verifications yet. Submit proof below to earn verified badges.
      </div>
    `;
    return;
  }

  const badgeIcons = {
    cgpa: "graduation-cap",
    class_group: "shield",
    experience: "briefcase"
  };

  container.innerHTML = verifications.map(v => `
    <div class="p-3.5 rounded-xl bg-zinc-950 border border-emerald-500/20 space-y-1.5">
      <div class="flex items-center justify-between">
        <span class="text-[10px] font-mono text-emerald-400 font-bold uppercase flex items-center gap-1">
          <i data-lucide="${badgeIcons[v.field] || 'award'}" class="w-3 h-3"></i>
          <span>${v.field.replace('_', ' ')}</span>
        </span>
        <span class="px-1.5 py-0.2 rounded text-[9px] font-mono bg-emerald-500/10 text-emerald-400 border border-emerald-500/30">
          ${v.status.toUpperCase()}
        </span>
      </div>
      <p class="text-xs font-bold text-white">${v.claim}</p>
      <div class="flex items-center justify-between text-[10px] text-zinc-500 font-mono pt-1 border-t border-white/5">
        <span>Proof: ${v.document_name || 'Verified Record'}</span>
        <span>${v.verified_at || 'Active'}</span>
      </div>
    </div>
  `).join("");

  lucide.createIcons();
}

async function fetchDirectoryStudents() {
  try {
    const res = await fetch("/api/students/directory");
    const data = await res.json();
    state.directoryStudents = data.students || [];
    filterDirectoryPeers();
  } catch (err) {
    console.error("Directory fetch error:", err);
  }
}

function setDirectoryFilter(filter) {
  state.directoryFilter = filter;
  document.querySelectorAll(".dir-filter-btn").forEach(btn => {
    if (btn.getAttribute("data-filter") === filter) {
      btn.className = "dir-filter-btn px-3 py-1.5 rounded-lg bg-indigo-600 text-white font-medium whitespace-nowrap shadow-sm";
    } else {
      btn.className = "dir-filter-btn px-3 py-1.5 rounded-lg bg-zinc-900 text-zinc-400 hover:text-white font-medium whitespace-nowrap";
    }
  });
  filterDirectoryPeers();
}

function filterDirectoryPeers() {
  const searchInput = document.getElementById("directory-search");
  const query = searchInput ? searchInput.value.trim().toLowerCase() : "";
  const filter = state.directoryFilter;

  let list = state.directoryStudents || [];

  if (query) {
    list = list.filter(s =>
      (s.name && s.name.toLowerCase().includes(query)) ||
      (s.roll_number && s.roll_number.toLowerCase().includes(query)) ||
      (s.class_section && s.class_section.toLowerCase().includes(query)) ||
      (s.practical_group && s.practical_group.toLowerCase().includes(query))
    );
  }

  if (filter === "CSE-2") {
    list = list.filter(s => s.class_section === "CSE-2");
  } else if (filter === "Group 2") {
    list = list.filter(s => s.practical_group && (s.practical_group.includes("Group 2") || s.practical_group.includes("P2")));
  } else if (filter === "verified_cgpa") {
    list = list.filter(s => {
      const v = s.verifications || {};
      return Array.isArray(v) ? v.some(i => i.field === "cgpa") : Boolean(v.cgpa);
    });
  }

  renderDirectoryGrid(list);
}

function renderDirectoryGrid(students) {
  const grid = document.getElementById("directory-grid");
  if (!grid) return;

  if (!students.length) {
    grid.innerHTML = `
      <div class="col-span-full py-16 text-center text-zinc-500">
        <i data-lucide="users" class="w-8 h-8 mx-auto mb-2 text-zinc-600"></i>
        <p class="text-sm">No students match current search or section filter.</p>
      </div>
    `;
    lucide.createIcons();
    return;
  }

  grid.innerHTML = students.map(s => {
    // Normalize verifications
    const rawVerifs = s.verifications || {};
    const verifList = Array.isArray(rawVerifs)
      ? rawVerifs
      : Object.entries(rawVerifs).map(([f, v]) => ({
          field: f,
          claim: v.badge || v.claim || f
        }));
    const hasCgpaBadge = verifList.some(v => v.field === "cgpa");

    // CGPA display logic respecting privacy segregation
    let cgpaPill = "";
    if (s.cgpa_hidden) {
      cgpaPill = `
        <div class="flex items-center justify-between text-xs p-2 rounded-xl bg-zinc-950/80 border border-white/5">
          <span class="text-[11px] text-zinc-500 font-mono">ACADEMIC CGPA</span>
          <span class="text-zinc-500 font-mono text-[11px] flex items-center gap-1">
            <i data-lucide="lock" class="w-3 h-3 text-zinc-500"></i> Private
          </span>
        </div>
      `;
    } else {
      cgpaPill = `
        <div class="flex items-center justify-between text-xs p-2 rounded-xl bg-zinc-950/80 border border-white/5">
          <span class="text-[11px] text-zinc-400 font-mono">ACADEMIC CGPA</span>
          <div class="flex items-center gap-1.5 font-mono">
            <span class="font-black text-emerald-400">${(s.cgpa || 0).toFixed(2)}</span>
            ${hasCgpaBadge ? `<span title="Verified by Marksheet" class="text-emerald-400">✅</span>` : ''}
          </div>
        </div>
      `;
    }

    // Class & Group pills
    let classPills = "";
    if (s.class_section || s.practical_group) {
      classPills = `
        <div class="flex items-center gap-1.5 flex-wrap text-[11px] font-mono">
          ${s.class_section ? `<span class="px-2 py-0.5 rounded bg-blue-500/10 text-blue-400 border border-blue-500/20">${s.class_section}</span>` : ''}
          ${s.practical_group ? `<span class="px-2 py-0.5 rounded bg-indigo-500/10 text-indigo-400 border border-indigo-500/20">${s.practical_group}</span>` : ''}
        </div>
      `;
    } else {
      classPills = `<span class="text-[11px] text-zinc-500 font-mono">🔒 Section Private</span>`;
    }

    // Badges
    const badgesHtml = verifList.map(v => {
      return `<span class="px-2 py-0.5 rounded text-[9px] font-mono bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 font-bold">${v.claim || v.field}</span>`;
    }).join("");

    const avatarSrc = s.avatar_url || s.avatar || `https://api.dicebear.com/7.x/bottts/svg?seed=${s.name}`;

    return `
      <div class="p-5 rounded-2xl glass-card border border-white/10 hover:border-indigo-500/30 transition-all flex flex-col justify-between space-y-4 shadow-lg group">
        <div class="space-y-3">
          <div class="flex items-start gap-3.5">
            <div class="relative shrink-0">
              <img src="${avatarSrc}" class="w-12 h-12 rounded-xl border border-white/15 bg-zinc-900 object-cover" />
              <span class="absolute -bottom-1 -right-1 w-3 h-3 rounded-full bg-emerald-500 border border-zinc-900"></span>
            </div>
            <div class="overflow-hidden flex-1 min-w-0">
              <div class="flex items-center gap-1.5 flex-wrap">
                <span class="font-mono font-bold text-xs text-indigo-400">${s.roll_number}</span>
                ${s.is_verified || verifList.length > 0 ? `<span class="px-1.5 py-0.2 rounded text-[9px] font-mono bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">VERIFIED</span>` : ''}
              </div>
              <h3 class="text-sm font-bold text-white truncate mt-0.5">${s.name}</h3>
              <p class="text-[11px] text-zinc-400 truncate">${s.programme_name || 'B.Tech CSE'} • ${s.institution_name || 'MAIT'}</p>
            </div>
          </div>

          ${classPills}

          <p class="text-xs text-zinc-300 line-clamp-2 leading-relaxed">
            ${s.bio || 'CampusIQ Verified Member • Learning and building together.'}
          </p>

          ${cgpaPill}

          ${badgesHtml ? `<div class="flex flex-wrap gap-1.5 pt-1">${badgesHtml}</div>` : ''}
        </div>

        <div class="pt-2 border-t border-white/5">
          <button onclick="openPeerModal('${s.roll_number}')" class="w-full py-2 px-3 rounded-xl bg-zinc-900 hover:bg-indigo-600/20 hover:border-indigo-500/40 border border-white/10 text-zinc-300 hover:text-white font-semibold text-xs transition-all flex items-center justify-center gap-1.5">
            <i data-lucide="user" class="w-3.5 h-3.5 text-indigo-400"></i>
            <span>View Student Dossier</span>
          </button>
        </div>
      </div>
    `;
  }).join("");

  lucide.createIcons();
}

async function updatePrivacySettings() {
  if (!state.currentUser) return;
  const priv = {
    is_public: document.getElementById("priv-public-profile").checked,
    public_profile: document.getElementById("priv-public-profile").checked,
    show_cgpa: document.getElementById("priv-show-cgpa").checked,
    show_class_details: document.getElementById("priv-show-class").checked,
    show_socials: document.getElementById("priv-show-socials").checked,
    show_experience: document.getElementById("priv-show-exp").checked
  };

  try {
    const res = await fetch("/api/profile/update", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        ...(state.sessionToken ? { "Authorization": `Bearer ${state.sessionToken}` } : {})
      },
      body: JSON.stringify({
        roll_number: state.currentUser.roll_number,
        privacy: priv,
        privacy_settings: priv
      })
    });
    const data = await res.json();
    if (data.status === "success") {
      showToast("🔒 Privacy segregation rules updated live");
      fetchDirectoryStudents();
    }
  } catch (err) {
    console.error("Privacy update error:", err);
  }
}


async function saveProfileDetails(e) {
  e.preventDefault();
  if (!state.currentUser) return;

  const payload = {
    roll_number: state.currentUser.roll_number,
    class_section: document.getElementById("edit-class-section").value.trim(),
    practical_group: document.getElementById("edit-practical-group").value.trim(),
    bio: document.getElementById("edit-bio").value.trim(),
    socials: {
      github: document.getElementById("edit-github").value.trim(),
      linkedin: document.getElementById("edit-linkedin").value.trim(),
      portfolio: document.getElementById("edit-portfolio").value.trim()
    }
  };

  try {
    const res = await fetch("/api/profile/update", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        ...(state.sessionToken ? { "Authorization": `Bearer ${state.sessionToken}` } : {})
      },
      body: JSON.stringify(payload)
    });
    const data = await res.json();
    if (data.status === "success") {
      state.currentUser = data.student;
      showToast("✅ Profile information saved successfully!");
      fetchDirectoryStudents();
    }
  } catch (err) {
    console.error("Profile save error:", err);
    showToast("Error saving profile details.");
  }
}

function handleProofFileSelected(e) {
  const file = e.target.files[0];
  if (!file) return;
  state.uploadedProofName = file.name;
  const nameEl = document.getElementById("verify-file-name");
  if (nameEl) {
    nameEl.innerText = `Selected document: ${file.name} (${(file.size / 1024).toFixed(1)} KB)`;
    nameEl.classList.remove("hidden");
  }

  const reader = new FileReader();
  reader.onload = (uploadEvent) => {
    state.uploadedProofBase64 = uploadEvent.target.result;
  };
  reader.readAsDataURL(file);
}

async function submitVerificationProof(e) {
  e.preventDefault();
  if (!state.currentUser) return;

  const field = document.getElementById("verify-field").value;
  const claim = document.getElementById("verify-claim").value.trim();
  const docName = state.uploadedProofName || `${field}_proof_document.pdf`;

  try {
    const res = await fetch("/api/profile/verify", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        roll_number: state.currentUser.roll_number,
        field: field,
        claim: claim,
        document_name: docName
      })
    });
    const data = await res.json();
    if (data.status === "success") {
      state.currentUser = data.student;
      showToast(`🎉 Verification approved! Badge issued for ${field}`);
      populateMyProfileUI(data.student);
      fetchDirectoryStudents();
      // Clear claim input
      document.getElementById("verify-claim").value = "";
    }
  } catch (err) {
    console.error("Proof verification error:", err);
    showToast("Error submitting verification proof.");
  }
}

function openPeerModal(roll) {
  const p = (state.directoryStudents || []).find(s => s.roll_number === roll);
  if (!p) return;

  state.selectedPeer = p;

  document.getElementById("peer-modal-batch").innerText = `Batch ${p.batch || 2025}`;
  document.getElementById("peer-modal-name").innerText = p.name;
  document.getElementById("peer-modal-roll").innerText = `${p.roll_number} • ${p.institution_name || 'MAIT'}`;
  document.getElementById("peer-modal-avatar").src = p.avatar || `https://api.dicebear.com/7.x/bottts/svg?seed=${p.name}`;
  document.getElementById("peer-modal-program").innerText = p.programme_name || "B.Tech Computer Science";

  const verifiedChip = document.getElementById("peer-modal-verified-chip");
  if (p.is_verified) {
    verifiedChip.classList.remove("hidden");
  } else {
    verifiedChip.classList.add("hidden");
  }

  // Class & Group Box
  const classBox = document.getElementById("peer-modal-class-box");
  if (p.class_section || p.practical_group) {
    classBox.innerHTML = `
      ${p.class_section ? `<span class="px-2.5 py-1 rounded-lg bg-blue-500/10 text-blue-400 border border-blue-500/20 font-mono font-semibold">Section: ${p.class_section}</span>` : ''}
      ${p.practical_group ? `<span class="px-2.5 py-1 rounded-lg bg-indigo-500/10 text-indigo-400 border border-indigo-500/20 font-mono font-semibold">Practical: ${p.practical_group}</span>` : ''}
    `;
  } else {
    classBox.innerHTML = `<span class="text-zinc-500 text-xs font-mono">🔒 Class section & practical group kept private</span>`;
  }

  // Bio
  document.getElementById("peer-modal-bio").innerText = p.bio || "No public bio provided.";

  // CGPA Display
  const cgpaDisplay = document.getElementById("peer-modal-cgpa-display");
  const auditStatus = document.getElementById("peer-modal-cgpa-audit");
  if (p.cgpa_hidden) {
    auditStatus.innerText = "Privacy Protected";
    auditStatus.className = "text-zinc-500 font-mono";
    cgpaDisplay.innerHTML = `
      <div class="p-3 rounded-xl bg-zinc-900 border border-white/5 text-zinc-400 text-xs flex items-center gap-2">
        <i data-lucide="lock" class="w-4 h-4 text-zinc-500"></i>
        <span>Cumulative Grade Point Average is kept private by student.</span>
      </div>
    `;
  } else {
    auditStatus.innerText = "ExamWeb Audited";
    auditStatus.className = "text-emerald-400 font-mono";
    cgpaDisplay.innerHTML = `
      <div class="flex items-baseline justify-between">
        <div>
          <span class="text-3xl font-black text-white font-mono">${(p.cgpa || 0).toFixed(2)}</span>
          <span class="text-xs text-zinc-400 ml-1.5 font-mono">CGPA (${(p.percentage || 0).toFixed(1)}%)</span>
        </div>
        <span class="px-2 py-0.5 rounded text-[10px] font-mono bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 font-bold">
          VERIFIED RECORD ✅
        </span>
      </div>
    `;
  }

  // Verifications
  const verifBox = document.getElementById("peer-modal-verifications");
  const rawVerifs = p.verifications || {};
  const verifList = Array.isArray(rawVerifs)
    ? rawVerifs
    : Object.entries(rawVerifs).map(([f, v]) => ({
        field: f,
        claim: v.badge || v.claim || f
      }));

  if (verifList.length > 0) {
    verifBox.innerHTML = verifList.map(v => `
      <div class="p-2.5 rounded-xl bg-zinc-900 border border-emerald-500/20 flex items-center justify-between">
        <span class="font-mono text-zinc-300 text-[11px] font-bold">${v.claim || v.field}</span>
        <span class="text-[10px] font-mono text-emerald-400">VERIFIED ✅</span>
      </div>
    `).join("");
  } else {
    verifBox.innerHTML = `<span class="text-zinc-500 text-xs">No active verification badges.</span>`;
  }

  // Experiences
  const expContainer = document.getElementById("peer-modal-experiences");
  const expBox = document.getElementById("peer-modal-exp-box");
  if (p.experiences && p.experiences.length > 0) {
    expBox.classList.remove("hidden");
    expContainer.innerHTML = p.experiences.map(e => `
      <div class="p-3 rounded-xl bg-zinc-900 border border-white/5 space-y-1">
        <div class="flex items-center justify-between">
          <h4 class="font-bold text-white">${e.role}</h4>
          <span class="text-[10px] font-mono text-zinc-400">${e.duration || '2025'}</span>
        </div>
        <p class="text-xs text-indigo-400">${e.company}</p>
        <p class="text-[11px] text-zinc-400">${e.description || ''}</p>
      </div>
    `).join("");
  } else {
    expBox.classList.add("hidden");
  }

  // Socials
  const socBox = document.getElementById("peer-modal-socials-box");
  let socLinks = [];
  if (p.socials?.github) {
    socLinks.push(`<a href="${p.socials.github}" target="_blank" class="px-3 py-1.5 rounded-lg bg-zinc-900 hover:bg-zinc-800 text-zinc-300 hover:text-white border border-white/5 font-mono text-xs flex items-center gap-1.5"><i data-lucide="github" class="w-3.5 h-3.5"></i> GitHub</a>`);
  }
  if (p.socials?.linkedin) {
    socLinks.push(`<a href="${p.socials.linkedin}" target="_blank" class="px-3 py-1.5 rounded-lg bg-blue-600/10 hover:bg-blue-600/20 text-blue-400 border border-blue-500/20 font-mono text-xs flex items-center gap-1.5"><i data-lucide="linkedin" class="w-3.5 h-3.5"></i> LinkedIn</a>`);
  }
  if (p.socials?.portfolio) {
    socLinks.push(`<a href="${p.socials.portfolio}" target="_blank" class="px-3 py-1.5 rounded-lg bg-emerald-600/10 hover:bg-emerald-600/20 text-emerald-400 border border-emerald-500/20 font-mono text-xs flex items-center gap-1.5"><i data-lucide="globe" class="w-3.5 h-3.5"></i> Portfolio</a>`);
  }

  socBox.innerHTML = socLinks.length > 0 ? socLinks.join("") : `<span class="text-zinc-500 text-xs font-mono">No social links shared.</span>`;

  document.getElementById("peer-modal").classList.add("open");
  lucide.createIcons();
}

function closePeerModal() {
  document.getElementById("peer-modal").classList.remove("open");
}

function closePeerModalOnBackdrop(e) {
  if (e.target.id === "peer-modal") closePeerModal();
}

// Listen for postMessage from popup window (standard OAuth callback)
window.addEventListener("message", (event) => {
  if (event.data && event.data.type === "GOOGLE_AUTH_SUCCESS") {
    const data = event.data;
    if (data.session_token) {
      localStorage.setItem("campusiq_session_token", data.session_token);
      state.sessionToken = data.session_token;
      state.currentUser = data.user;
      state.currentStudent = data.student;

      renderHeaderAuth(data.user, data.student);
      populateMyProfileUI(data.user, data.student);
      closeGoogleAuthModal();
      showToast(`🎉 Verified & Signed In as ${data.user.name}!`);
      fetchDirectoryStudents();
    }
  }
});

function openGoogleAuthModal() {
  const modal = document.getElementById("google-auth-modal");
  if (!modal) return;
  modal.classList.add("open");
  lucide.createIcons();
  if (typeof initGoogleIdentity === "function") {
    initGoogleIdentity();
  }
}

function closeGoogleAuthModal() {
  const modal = document.getElementById("google-auth-modal");
  if (!modal) return;
  modal.classList.remove("open");
}

function closeGoogleAuthModalOnBackdrop(e) {
  if (e.target.id === "google-auth-modal") closeGoogleAuthModal();
}

// Load Auth Configuration (Google Client ID, etc.)
async function loadAuthConfig() {
  try {
    const res = await fetch("/api/auth/config");
    const data = await res.json();
    if (data.status === "success" && data.google_client_id) {
      state.googleClientId = data.google_client_id;
      initGoogleIdentity();
    }
  } catch (e) {
    console.error("Failed to load auth config:", e);
  }
}

// Initialize Google Identity Services (GIS)
function initGoogleIdentity() {
  if (typeof google === "undefined" || !google.accounts) {
    return;
  }
  if (!state.googleClientId) return;

  try {
    if (google.accounts.id) {
      google.accounts.id.initialize({
        client_id: state.googleClientId,
        callback: handleGoogleCredentialResponse,
        auto_select: false,
        cancel_on_tap_outside: true
      });

      const container = document.getElementById("g-signin-container");
      if (container) {
        container.innerHTML = "";
        google.accounts.id.renderButton(container, {
          theme: "filled_black",
          size: "large",
          shape: "rectangular",
          text: "signin_with",
          logo_alignment: "left",
          width: 320
        });
      }
    }
  } catch (err) {
    console.warn("Google Identity Services initialization:", err);
  }
}
window.initGoogleIdentity = initGoogleIdentity;

// Handler called when Google Identity Services completes authentication
async function handleGoogleCredentialResponse(response) {
  if (!response || !response.credential) {
    showToast("Google authentication did not return a valid credential.");
    return;
  }

  showToast("🔐 Verifying Google identity...");

  try {
    const res = await fetch("/api/auth/google/verify", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ credential: response.credential })
    });

    const data = await res.json();
    if (data.status === "success" && data.session_token) {
      localStorage.setItem("campusiq_session_token", data.session_token);
      state.sessionToken = data.session_token;
      state.currentUser = data.user;
      state.currentStudent = data.student;

      renderHeaderAuth(data.user, data.student);
      populateMyProfileUI(data.user, data.student);
      closeGoogleAuthModal();
      showToast(`🎉 Verified & Signed In as ${data.user.name}!`);
      fetchDirectoryStudents();
    } else {
      showToast(data.message || "Google sign-in verification failed.");
    }
  } catch (err) {
    console.error("Google sign in verification error:", err);
    showToast("Google sign in failed. Please try again.");
  }
}

// Handler called when Google access token is obtained via OAuth2 token client
async function handleGoogleAccessToken(accessToken) {
  showToast("🔐 Verifying Google access token...");
  try {
    const res = await fetch("/api/auth/google/access-token", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ access_token: accessToken })
    });

    const data = await res.json();
    if (data.status === "success" && data.session_token) {
      localStorage.setItem("campusiq_session_token", data.session_token);
      state.sessionToken = data.session_token;
      state.currentUser = data.user;
      state.currentStudent = data.student;

      renderHeaderAuth(data.user, data.student);
      populateMyProfileUI(data.user, data.student);
      closeGoogleAuthModal();
      showToast(`🎉 Verified & Signed In as ${data.user.name}!`);
      fetchDirectoryStudents();
    } else {
      showToast(data.message || "Google sign-in failed.");
    }
  } catch (err) {
    console.error("Google access token error:", err);
    showToast("Google sign in failed. Please try again.");
  }
}

// User clicked the "Sign in with Google" button
function handleGoogleSignInClick() {
  // Strategy 1: If GIS OAuth2 token client is supported, use it for direct in-browser popup
  if (state.googleClientId && typeof google !== "undefined" && google.accounts && google.accounts.oauth2) {
    try {
      const tokenClient = google.accounts.oauth2.initTokenClient({
        client_id: state.googleClientId,
        scope: "openid email profile",
        callback: async (resp) => {
          if (resp && resp.access_token) {
            await handleGoogleAccessToken(resp.access_token);
          } else if (resp && resp.error) {
            console.warn("Token client error:", resp);
            openGoogleOAuthPopup();
          }
        }
      });
      tokenClient.requestAccessToken({ prompt: "select_account" });
      return;
    } catch (e) {
      console.warn("Token client init failed, falling back to popup:", e);
    }
  }

  // Strategy 2: OAuth2 Server-side Code Exchange Popup
  if (state.googleClientId) {
    openGoogleOAuthPopup();
    return;
  }

  // Strategy 3: Not configured yet
  const msg = "To enable 1-click Google OAuth popup, please enter your Google Cloud OAuth Client ID (or set GOOGLE_CLIENT_ID on Render). Would you like to enter it now?";
  if (confirm(msg)) {
    promptConfigureGoogleClientId();
  } else {
    switchAuthTab("signin");
    fillTanmayCredentials();
  }
}

function openGoogleOAuthPopup() {
  const width = 500;
  const height = 650;
  const left = window.screenX + Math.max(0, (window.outerWidth - width) / 2);
  const top = window.screenY + Math.max(0, (window.outerHeight - height) / 2);
  const popup = window.open(
    "/api/auth/google/login",
    "google_oauth_popup",
    `width=${width},height=${height},left=${left},top=${top},status=0,toolbar=0,menubar=0,location=1`
  );
  if (!popup || popup.closed || typeof popup.closed === "undefined") {
    // Popup was blocked by browser, redirect current window
    window.location.href = "/api/auth/google/login";
  }
}

// Prompt to configure Google OAuth Client ID
async function promptConfigureGoogleClientId() {
  const current = state.googleClientId || "";
  const clientId = prompt(
    "Enter your Google Cloud OAuth 2.0 Client ID:\n(e.g., 1234567890-abcdef.apps.googleusercontent.com)\n\nFrom Google Cloud Console -> APIs & Services -> Credentials",
    current
  );

  if (clientId === null) return;
  const trimmed = clientId.trim();

  try {
    const res = await fetch("/api/auth/config", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ google_client_id: trimmed })
    });
    const data = await res.json();
    if (data.status === "success") {
      state.googleClientId = trimmed;
      showToast(trimmed ? "✅ Google Client ID saved!" : "Google Client ID cleared.");
      initGoogleIdentity();
    }
  } catch (e) {
    showToast("Failed to save auth configuration.");
  }
}

// Switch between "Sign In" and "Create Account"
function switchAuthTab(tab) {
  state.authMode = tab;
  const tabSignIn = document.getElementById("auth-tab-signin");
  const tabRegister = document.getElementById("auth-tab-register");
  const nameGroup = document.getElementById("auth-name-group");
  const rollGroup = document.getElementById("auth-roll-group");
  const submitText = document.getElementById("btn-submit-auth-text");
  const errAlert = document.getElementById("auth-error-alert");

  if (errAlert) errAlert.classList.add("hidden");

  if (tab === "signin") {
    if (tabSignIn) {
      tabSignIn.className = "flex-1 py-1.5 rounded-lg font-semibold text-white bg-zinc-800 shadow transition-all";
    }
    if (tabRegister) {
      tabRegister.className = "flex-1 py-1.5 rounded-lg font-medium text-zinc-400 hover:text-white transition-all";
    }
    if (nameGroup) nameGroup.classList.add("hidden");
    if (rollGroup) rollGroup.classList.add("hidden");
    if (submitText) submitText.innerText = "Sign In with Password";
  } else {
    if (tabSignIn) {
      tabSignIn.className = "flex-1 py-1.5 rounded-lg font-medium text-zinc-400 hover:text-white transition-all";
    }
    if (tabRegister) {
      tabRegister.className = "flex-1 py-1.5 rounded-lg font-semibold text-white bg-zinc-800 shadow transition-all";
    }
    if (nameGroup) nameGroup.classList.remove("hidden");
    if (rollGroup) rollGroup.classList.remove("hidden");
    if (submitText) submitText.innerText = "Create Account & Sign In";
  }
  lucide.createIcons();
}

// 1-Click Quick Fill Helper for Tanmay
function fillTanmayCredentials() {
  const emailInput = document.getElementById("signin-email");
  const pwdInput = document.getElementById("signin-password");
  const nameInput = document.getElementById("signin-name");
  const rollInput = document.getElementById("signin-roll");
  const errAlert = document.getElementById("auth-error-alert");

  if (errAlert) errAlert.classList.add("hidden");
  if (emailInput) emailInput.value = "tanmay.jain@ipu.ac.in";
  if (pwdInput) pwdInput.value = "Tanmay@2008";
  if (nameInput) nameInput.value = "Tanmay Jain";
  if (rollInput) rollInput.value = "08414802725";

  showToast("🔑 Populated credentials. Click Sign In to verify.");
}

// Handle Form Submission: Login with Password OR Create Account
async function handleAuthSubmit(e) {
  e.preventDefault();
  const errAlert = document.getElementById("auth-error-alert");
  const errMsg = document.getElementById("auth-error-msg");
  if (errAlert) errAlert.classList.add("hidden");

  const email = (document.getElementById("signin-email")?.value || "").trim();
  const password = (document.getElementById("signin-password")?.value || "").trim();
  const name = (document.getElementById("signin-name")?.value || "").trim();
  const roll = (document.getElementById("signin-roll")?.value || "").trim();

  if (!email || !password) {
    if (errAlert && errMsg) {
      errMsg.innerText = "Please provide both email and password.";
      errAlert.classList.remove("hidden");
    }
    return;
  }

  const submitBtn = document.getElementById("btn-submit-auth");
  const submitText = document.getElementById("btn-submit-auth-text");
  if (submitBtn) submitBtn.disabled = true;
  if (submitText) submitText.innerText = state.authMode === "register" ? "Creating Account..." : "Verifying Credentials...";

  try {
    const endpoint = state.authMode === "register" ? "/api/auth/register" : "/api/auth/login";
    const payload = state.authMode === "register"
      ? { email, password, name, roll_number: roll || null }
      : { email, password };

    const res = await fetch(endpoint, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });

    const data = await res.json();
    if (res.ok && data.status === "success" && data.session_token) {
      localStorage.setItem("campusiq_session_token", data.session_token);
      state.sessionToken = data.session_token;
      state.currentUser = data.user;
      state.currentStudent = data.student;

      renderHeaderAuth(data.user, data.student);
      populateMyProfileUI(data.user, data.student);
      closeGoogleAuthModal();
      showToast(`🎉 ${data.message || 'Authenticated successfully!'}`);
      fetchDirectoryStudents();
    } else {
      if (errAlert && errMsg) {
        errMsg.innerText = data.message || "Authentication failed. Please verify credentials.";
        errAlert.classList.remove("hidden");
      }
      showToast(`❌ ${data.message || 'Authentication error'}`);
    }
  } catch (err) {
    console.error("Auth error:", err);
    if (errAlert && errMsg) {
      errMsg.innerText = "Connection error. Please check your network.";
      errAlert.classList.remove("hidden");
    }
    showToast("Network error during authentication.");
  } finally {
    if (submitBtn) submitBtn.disabled = false;
    if (submitText) {
      submitText.innerText = state.authMode === "register" ? "Create Account & Sign In" : "Sign In with Password";
    }
  }
}

async function handleSignOut() {
  if (state.sessionToken) {
    try {
      await fetch("/api/auth/signout", {
        method: "POST",
        headers: {
          "Authorization": `Bearer ${state.sessionToken}`
        }
      });
    } catch (e) {}
  }

  localStorage.removeItem("campusiq_session_token");
  state.sessionToken = null;
  state.currentUser = null;
  state.currentStudent = null;

  renderHeaderAuth(null, null);
  populateMyProfileUI(null, null);
  showToast("👋 Signed out successfully");
}

async function handleLinkRollNumber() {
  const rollInput = document.getElementById("link-roll-input");
  if (!rollInput) return;
  const roll = rollInput.value.trim();
  if (!roll || roll.length !== 11) {
    showToast("Please enter a valid 11-digit GGSIPU roll number.");
    return;
  }

  try {
    const res = await fetch("/api/auth/link-roll", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "Authorization": `Bearer ${state.sessionToken}`
      },
      body: JSON.stringify({ roll_number: roll })
    });
    const data = await res.json();
    if (data.status === "success") {
      if (state.currentUser) state.currentUser.roll_number = roll;
      state.currentStudent = data.student;
      renderHeaderAuth(state.currentUser, state.currentStudent);
      populateMyProfileUI(state.currentUser, state.currentStudent);
      showToast(`✅ Linked Roll Number: ${roll}`);
      fetchDirectoryStudents();
    } else {
      showToast(data.message || "Failed to link roll number.");
    }
  } catch (err) {
    console.error("Link roll error:", err);
    showToast("Error linking roll number.");
  }
}

// =============================================================================
// STATS & TOAST
// =============================================================================

async function fetchStats() {
  try {
    const res = await fetch("/api/stats");
    const data = await res.json();
    if (data.stats) {
      // Background stats cached
    }
  } catch (e) {}
}

function showToast(msg) {
  const toast = document.getElementById("toast");
  if (!toast) return;
  document.getElementById("toast-msg").innerText = msg;
  toast.classList.add("show");
  setTimeout(() => {
    toast.classList.remove("show");
  }, 3200);
}
