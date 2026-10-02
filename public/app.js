/**
 * CampusIQ - Core Client Application Controller
 * High-performance reactive UI logic with localStorage profile synchronization,
 * live REST API integrations, and instant in-browser PDF previews.
 */

// Universal HTML sanitizer for XSS prevention
function escapeHtml(str) {
  if (str === null || str === undefined) return "";
  return String(str)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
}

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
  vaultCategoryFilter: "all",
  vaultSubjectFilter: "",
  typesetOnly: false,
  // ExamWeb State
  resultMode: "examweb",
  examWebSession: null,
  examWebResult: null,
  examWebSelectedSem: "all",
  // Student Community & Profile Segregation
  activeCommunitySubView: "directory",
  sessionToken: localStorage.getItem("campusiq_session_token") || null,
  currentUser: (() => {
    try {
      const u = localStorage.getItem("campusiq_cached_user");
      return u ? JSON.parse(u) : null;
    } catch (e) { return null; }
  })(),
  currentStudent: (() => {
    try {
      const s = localStorage.getItem("campusiq_cached_student");
      return s ? JSON.parse(s) : null;
    } catch (e) { return null; }
  })(),
  googleClientId: "",
  authMode: "signin",
  directoryStudents: [],
  selectedPeer: null,
  directoryFilter: "all",
  uploadedProofBase64: null,
  uploadedProofName: "",
  // Faculty Admin
  adminStudents: [],
  adminFilteredStudents: [],
  // Edumarshal Attendance & Interactive Calendar
  attendanceData: null,
  attendanceView: "courses",
  calendarData: null,
  currentCalYear: 2026,
  currentCalMonth: 9
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
  if (state.currentUser) {
    closeSignInGatekeeper();
    renderHeaderAuth(state.currentUser, state.currentStudent);
    populateMyProfileUI(state.currentUser, state.currentStudent);
  }
  fetchNotices();
  fetchResourcesTree();
  fetchResources();
  fetchCurrentUser();
  loadAuthConfig();
  fetchDirectoryStudents();
  if (isAdminAuthenticated()) {
    loadAdminRoster();
  }
  checkAdminHashRoute();
  fetchStats();
  initExamWebSession();
  lucide.createIcons();
});

// =============================================================================
// NAVIGATION & TABS
// =============================================================================

function switchTab(tabId) {
  state.activeTab = tabId;
  if (tabId === "resources") {
    if (!state.vaultTree) {
      fetchResourcesTree();
    } else {
      renderVaultHierarchy();
    }
  }
  if (tabId === "results" && !state.examWebSession && !state.examWebResult) {
    initExamWebSession();
  }
  if (tabId === "admin") {
    if (!isAdminAuthenticated()) {
      openAdminAuthModal();
      return;
    }
    loadAdminRoster();
  }
  if (tabId === "community") {
    initCommunityHub();
  }
  if (tabId === "attendance") {
    if (!state.currentUser) {
      openSignInGatekeeper();
      return;
    }
    const chip = document.getElementById("att-student-chip");
    if (chip && state.currentUser) {
      chip.innerText = state.currentUser.roll_number
        ? `${state.currentUser.roll_number} (${state.currentUser.name || 'Student'})`
        : `${state.currentUser.name || 'Student'} (Unverified)`;
    }
    const unlinkedAlert = document.getElementById("att-unlinked-alert");
    if (unlinkedAlert) {
      if (state.currentUser && (state.currentUser.is_verified || state.currentUser.has_edumarshal)) {
        unlinkedAlert.classList.add("hidden");
      } else {
        unlinkedAlert.classList.remove("hidden");
        openEdumarshalVerifyModal();
      }
    }
    fetchAttendance();
    fetchAttendanceCalendar();
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
    grid.innerHTML = renderCustomErrorCard({
      icon: "wifi-off",
      title: "Notice Feed Interrupted",
      message: "Unable to establish live connection with university circular feeds. Please verify network access or retry synchronization.",
      actionText: "Retry Notice Sync",
      actionFn: "fetchNotices(true)"
    });
    if (window.lucide && typeof window.lucide.createIcons === "function") {
      window.lucide.createIcons();
    }
    showToast("Unable to load latest notices", "error", "Noticeboard Offline");
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
    const matchQuery = !query ||
      n.title.toLowerCase().includes(query) ||
      (n.category && n.category.toLowerCase().includes(query)) ||
      (n.source && n.source.toLowerCase().includes(query));
    
    let matchCat = true;
    if (cat === "mait") {
      matchCat = (n.source && n.source.toLowerCase() === "mait") || (n.college && n.college.toLowerCase().includes("mait"));
    } else if (cat) {
      matchCat = n.category && n.category.toLowerCase().includes(cat);
    }
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

    // Update global vault header counters
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
    const res = await fetch("/api/resources?semester=all");
    const data = await res.json();
    state.resources = data.resources || [];

    // Calculate Akash and Notes totals across all resources
    const akashTotal = state.resources.filter(r => r.category === 'Akash Solved Question Banks' || (r.tags && r.tags.includes('Akash')) || (r.title && /akash/i.test(r.title))).length;
    const notesTotal = state.resources.filter(r => r.category === 'Lecture Notes & Theory' || (r.tags && r.tags.includes('Notes'))).length;
    const pyqTotal = state.resources.filter(r => (r.category && (r.category.includes('Paper') || r.category.includes('PYQ')))).length;

    const totEl = document.getElementById("stat-total-resources");
    if (totEl) totEl.innerText = state.resources.length;
    const akashEl = document.getElementById("stat-akash-count");
    if (akashEl) akashEl.innerText = akashTotal;
    const notesEl = document.getElementById("stat-notes-count");
    if (notesEl) notesEl.innerText = notesTotal;
  } catch (e) {
    console.error("Flat resource fetch error:", e);
  }
}

function setVaultSemester(sem) {
  state.vaultSemester = sem;
  state.vaultSubject = null;
  state.vaultCategoryFilter = 'all';
  renderVaultHierarchy();
}

function setVaultSubject(subjKey) {
  state.vaultSubject = subjKey;
  renderVaultResourceDeck();
  renderVaultSubjectRail();
}

function setVaultCategoryFilter(cat) {
  state.vaultCategoryFilter = cat;
  
  const pillIds = {
    all: "v-cat-all",
    akash: "v-cat-akash",
    notes: "v-cat-notes",
    pyqs: "v-cat-pyqs",
    practicals: "v-cat-practicals"
  };

  Object.entries(pillIds).forEach(([key, id]) => {
    const el = document.getElementById(id);
    if (!el) return;
    if (key === cat) {
      el.className = "vault-cat-pill px-3.5 py-1.5 rounded-lg text-white bg-emerald-600 font-semibold shadow-sm transition-all whitespace-nowrap flex items-center gap-1.5";
    } else {
      el.className = "vault-cat-pill px-3.5 py-1.5 rounded-lg text-zinc-400 hover:text-zinc-200 transition-all flex items-center gap-1.5 whitespace-nowrap hover:bg-zinc-800/60";
    }
  });

  renderVaultResourceDeck();
}

function toggleTypesetOnlyFilter() {
  state.typesetOnly = !state.typesetOnly;
  const btn = document.getElementById("btn-quick-typeset");
  if (btn) {
    if (state.typesetOnly) {
      btn.className = "px-2.5 py-1 rounded-lg bg-emerald-500/20 text-emerald-300 border border-emerald-500/40 font-semibold transition-all flex items-center gap-1.5";
    } else {
      btn.className = "px-2.5 py-1 rounded-lg bg-zinc-900 hover:bg-zinc-800 text-zinc-400 hover:text-white border border-white/10 font-medium transition-all flex items-center gap-1.5";
    }
  }

  const searchContainer = document.getElementById("vault-search-results-container");
  if (searchContainer && !searchContainer.classList.contains("hidden")) {
    handleUniversalResourceSearch();
  } else {
    renderVaultResourceDeck();
  }
}

function filterVaultSubjects() {
  const input = document.getElementById("vault-subject-filter-input");
  state.vaultSubjectFilter = input ? input.value.trim().toLowerCase() : "";
  renderVaultSubjectRail();
}

function renderVaultHierarchy() {
  if (!state.vaultTree || !state.vaultTree.semesters) return;

  const currentSem = state.vaultSemester || 3;
  const semContainer = document.getElementById("vault-semester-tabs");
  
  // 1. Render all 8 Semesters Dynamically
  if (semContainer) {
    const semButtonsHtml = [1, 2, 3, 4, 5, 6, 7, 8].map(s => {
      const sData = state.vaultTree.semesters[s];
      let sCount = 0;
      if (sData && sData.subjects) {
        sCount = Object.values(sData.subjects).reduce((acc, subj) => {
          return acc + Object.values(subj.categories || {}).reduce((cacc, arr) => cacc + arr.length, 0);
        }, 0);
      }
      const isActive = s === currentSem;
      const activeClass = isActive
        ? "bg-emerald-600 text-white font-bold shadow-[0_0_15px_rgba(16,185,129,0.35)]"
        : "bg-zinc-900 border border-white/5 text-zinc-400 hover:text-white font-medium hover:bg-zinc-800/80";

      return `
        <button onclick="setVaultSemester(${s})" class="px-3.5 py-2 rounded-xl text-xs flex items-center gap-2 shrink-0 transition-all ${activeClass}">
          <span>Sem ${s}</span>
          <span class="px-1.5 py-0.5 rounded text-[10px] font-mono ${isActive ? 'bg-black/30 text-white' : 'bg-zinc-800 text-zinc-400'}">${sCount}</span>
        </button>
      `;
    }).join("");
    semContainer.innerHTML = semButtonsHtml;
  }

  // 2. Update Semester Badge and Category Counters for Active Semester
  const semData = state.vaultTree.semesters[currentSem];
  const subjectsObj = semData ? (semData.subjects || {}) : {};
  
  let semTotal = 0;
  let semAkash = 0;
  let semNotes = 0;
  let semPyqs = 0;
  let semPracticals = 0;

  Object.values(subjectsObj).forEach(subj => {
    Object.entries(subj.categories || {}).forEach(([catName, arr]) => {
      semTotal += arr.length;
      if (catName.includes("Akash") || arr.some(i => (i.tags && i.tags.includes("Akash")) || /akash/i.test(i.title))) {
        semAkash += arr.length;
      } else if (catName.includes("Notes") || catName.includes("General")) {
        semNotes += arr.length;
      } else if (catName.includes("Paper") || catName.includes("PYQ")) {
        semPyqs += arr.length;
      } else if (catName.includes("Practical") || catName.includes("Lab")) {
        semPracticals += arr.length;
      }
    });
  });

  const semStatBadge = document.getElementById("active-sem-stat-badge");
  if (semStatBadge) semStatBadge.innerText = `Semester ${currentSem} • ${semTotal} Resources`;

  const akashCountEl = document.getElementById("sem-akash-count");
  if (akashCountEl) akashCountEl.innerText = semAkash;
  const notesCountEl = document.getElementById("sem-notes-count");
  if (notesCountEl) notesCountEl.innerText = semNotes;
  const pyqCountEl = document.getElementById("sem-pyq-count");
  if (pyqCountEl) pyqCountEl.innerText = semPyqs;
  const practCountEl = document.getElementById("sem-practicals-count");
  if (practCountEl) practCountEl.innerText = semPracticals;

  // 3. Render Subject Rail & Resource Deck
  renderVaultSubjectRail();
  renderVaultResourceDeck();
}

function renderVaultSubjectRail() {
  const currentSem = state.vaultSemester || 3;
  const semData = state.vaultTree?.semesters?.[currentSem];
  const subjectsObj = semData ? (semData.subjects || {}) : {};
  let subjectKeys = Object.keys(subjectsObj);

  // Filter subjects by query
  const query = state.vaultSubjectFilter || "";
  if (query) {
    subjectKeys = subjectKeys.filter(k => {
      const s = subjectsObj[k];
      return k.toLowerCase().includes(query) || (s.name && s.name.toLowerCase().includes(query)) || (s.code && s.code.toLowerCase().includes(query));
    });
  }

  // Maintain active subject selection
  if (!state.vaultSubject || !subjectsObj[state.vaultSubject]) {
    state.vaultSubject = subjectKeys[0] || null;
  }

  const railCount = document.getElementById("rail-subjects-count");
  if (railCount) railCount.innerText = Object.keys(subjectsObj).length;
  const railSemTag = document.getElementById("rail-semester-tag");
  if (railSemTag) railSemTag.innerText = `Sem ${currentSem}`;

  const listContainer = document.getElementById("vault-subject-list");
  if (!listContainer) return;

  if (subjectKeys.length === 0) {
    listContainer.innerHTML = `
      <div class="p-6 text-center text-xs text-zinc-500">
        ${query ? 'No matching subjects.' : (currentSem === 8 ? 'Semester 8 is Capstone Major Internship & Project semester.' : 'No subjects indexed for this semester yet.')}
      </div>
    `;
    return;
  }

  listContainer.innerHTML = subjectKeys.map(k => {
    const subj = subjectsObj[k];
    const totalDocs = Object.values(subj.categories || {}).reduce((acc, arr) => acc + arr.length, 0);
    const hasAkash = Object.entries(subj.categories || {}).some(([cname, arr]) => 
      cname.includes("Akash") || arr.some(i => (i.tags && i.tags.includes("Akash")) || /akash/i.test(i.title))
    );
    const isActive = k === state.vaultSubject;
    const activeClass = isActive
      ? "bg-gradient-to-r from-emerald-950/60 to-zinc-900 border-emerald-500/50 shadow-sm"
      : "bg-zinc-900/60 hover:bg-zinc-900 border-white/5 hover:border-white/15";

    return `
      <div onclick="setVaultSubject('${escapeHtml(k)}')" class="p-2.5 rounded-xl border transition-all cursor-pointer flex items-center justify-between gap-2 group ${activeClass}">
        <div class="overflow-hidden space-y-0.5">
          <div class="flex items-center gap-1.5">
            <span class="text-xs font-semibold ${isActive ? 'text-emerald-300 font-bold' : 'text-zinc-200 group-hover:text-white'} truncate max-w-[160px]">
              ${escapeHtml(subj.name || k)}
            </span>
            ${hasAkash ? '<span class="px-1.5 py-0.2 rounded text-[9px] font-mono font-bold bg-amber-500/10 text-amber-400 border border-amber-500/20 shrink-0">📚 Akash</span>' : ''}
          </div>
          <div class="text-[10px] font-mono text-zinc-500 flex items-center gap-1.5">
            <span>${escapeHtml(subj.code || 'CODE')}</span>
          </div>
        </div>
        <span class="px-2 py-0.5 rounded text-[10px] font-mono ${isActive ? 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/30 font-bold' : 'bg-zinc-800 text-zinc-400'} shrink-0">
          ${totalDocs}
        </span>
      </div>
    `;
  }).join("");
}

function renderResourceCardHtml(r) {
  const isAkash = r.category === 'Akash Solved Question Banks' || (r.tags && r.tags.includes('Akash')) || (r.title && /akash/i.test(r.title));
  const isNotes = r.category === 'Lecture Notes & Theory' || (r.tags && r.tags.includes('Notes')) || /notes|unit|handwritten/i.test(r.title);
  const isPyq = (r.category && (r.category.includes('Paper') || r.category.includes('PYQ'))) || /mid sem|end sem|pyq/i.test(r.title);
  const isPract = (r.category && (r.category.includes('Practical') || r.category.includes('Lab')));

  const typesetBadge = r.is_typeset
    ? `<span class="px-2 py-0.5 rounded text-[9px] font-mono font-bold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">💎 OFFICIAL MASTER</span>`
    : (isAkash
      ? `<span class="px-2 py-0.5 rounded text-[9px] font-mono font-bold bg-amber-500/10 text-amber-400 border border-amber-500/20">📚 AKASH GUIDE</span>`
      : (isNotes
        ? `<span class="px-2 py-0.5 rounded text-[9px] font-mono font-medium text-cyan-400 bg-cyan-500/10 border border-cyan-500/20">📝 LECTURE NOTE</span>`
        : (isPract
          ? `<span class="px-2 py-0.5 rounded text-[9px] font-mono font-medium text-teal-400 bg-teal-500/10 border border-teal-500/20">🧪 LAB MANUAL</span>`
          : `<span class="px-2 py-0.5 rounded text-[9px] font-mono text-zinc-400 bg-zinc-800 border border-white/5">📄 PYQ / PAPER</span>`)));

  const cleanTitle = (r.title || '').replace(/^\[typeset\]\s*/i, '').replace(/^typeset\s*[-:]?\s*/i, '').replace(/_Typeset$/i, '').trim();
  const safeTitle = cleanTitle.replace(/'/g, "\'");
  const encodedPath = encodeURIComponent(r.relative_path || '');
  const driveId = r.drive_file_id || '';
  const viewUrl = driveId ? `/api/resources/view?id=${encodeURIComponent(driveId)}&path=${encodedPath}` : `/api/resources/view?path=${encodedPath}`;

  return `
    <div class="p-4 rounded-xl bg-zinc-900/90 border border-white/10 hover:border-emerald-500/30 transition-all flex flex-col justify-between space-y-3">
      <div class="space-y-2">
        <div class="flex items-center justify-between gap-1.5">
          ${typesetBadge}
          <span class="text-[10px] font-mono text-zinc-500">${r.exam_session || 'Official'}</span>
        </div>
        <h4 class="text-xs font-semibold text-white leading-snug line-clamp-2 hover:text-emerald-400 transition-colors cursor-pointer" onclick="openPdfPreview('${safeTitle}', '${r.relative_path}', '${driveId}')">
          ${cleanTitle}
        </h4>
        <div class="flex items-center justify-between text-[10px] font-mono text-zinc-500 pt-1 border-t border-white/5">
          <span>${r.subject_code || 'CODE'}</span>
          <span>${r.size_kb ? r.size_kb + ' KB' : 'PDF'}</span>
        </div>
      </div>

      <div class="flex items-center gap-2 pt-1 border-t border-white/5 text-xs">
        <button onclick="openPdfPreview('${safeTitle}', '${r.relative_path}', '${driveId}')" class="flex-1 py-2 sm:py-1.5 min-h-[38px] rounded-lg bg-zinc-950 hover:bg-zinc-800 text-zinc-300 hover:text-white font-medium flex items-center justify-center gap-1.5 transition-all active:scale-95">
          <i data-lucide="eye" class="w-3.5 h-3.5"></i>
          <span>Preview</span>
        </button>
        <a href="${viewUrl}" download="${r.filename || 'document.pdf'}" class="px-3.5 py-2 sm:py-1.5 min-h-[38px] rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white font-medium flex items-center justify-center gap-1.5 transition-all active:scale-95" title="Direct Download">
          <i data-lucide="download" class="w-3.5 h-3.5"></i>
        </a>
      </div>
    </div>
  `;
}

function renderVaultResourceDeck() {
  const currentSem = state.vaultSemester || 3;
  const semData = state.vaultTree?.semesters?.[currentSem];
  const subjectsObj = semData ? (semData.subjects || {}) : {};
  const activeSubj = state.vaultSubject ? subjectsObj[state.vaultSubject] : null;

  const deckTitle = document.getElementById("deck-subject-title");
  const deckCode = document.getElementById("deck-subject-code");
  const deckSemBadge = document.getElementById("deck-semester-badge");
  const deckAkashBadge = document.getElementById("deck-akash-badge");
  const deckCountBadge = document.getElementById("deck-items-count-badge");
  const gridContainer = document.getElementById("vault-deck-cards-grid");
  const emptyContainer = document.getElementById("vault-deck-empty");

  if (!activeSubj) {
    if (deckTitle) deckTitle.innerText = currentSem === 8 ? "Capstone Major Project & Internship" : `Semester ${currentSem} Overview`;
    if (deckCode) deckCode.innerText = `SEM-${currentSem}`;
    if (deckSemBadge) deckSemBadge.innerText = `Semester ${currentSem}`;
    if (deckAkashBadge) deckAkashBadge.classList.add("hidden");
    if (gridContainer) gridContainer.innerHTML = "";
    if (emptyContainer) {
      emptyContainer.classList.remove("hidden");
      const emptyH4 = emptyContainer.querySelector("h4");
      const emptyP = emptyContainer.querySelector("p");
      if (emptyH4) emptyH4.innerText = currentSem === 8 ? "Semester 8 Capstone Term" : "No materials found";
      if (emptyP) emptyP.innerText = currentSem === 8 ? "GGSIPU 8th Semester consists of the full-time Major Industry Project/Internship with no theoretical exams." : "No uploaded materials for this subject yet.";
    }
    return;
  }

  // Update header details
  if (deckTitle) deckTitle.innerText = activeSubj.name || state.vaultSubject;
  if (deckCode) deckCode.innerText = activeSubj.code || `SEM-${currentSem}`;
  if (deckSemBadge) deckSemBadge.innerText = `Semester ${currentSem}`;

  // Check if subject has an Akash guide
  const hasAkash = Object.entries(activeSubj.categories || {}).some(([cname, arr]) => 
    cname.includes("Akash") || arr.some(i => (i.tags && i.tags.includes("Akash")) || /akash/i.test(i.title))
  );
  if (deckAkashBadge) {
    if (hasAkash) deckAkashBadge.classList.remove("hidden");
    else deckAkashBadge.classList.add("hidden");
  }

  // Collect and filter items
  let allItems = [];
  Object.values(activeSubj.categories || {}).forEach(arr => {
    allItems = allItems.concat(arr);
  });

  const catFilter = state.vaultCategoryFilter || 'all';
  let filtered = allItems.filter(r => {
    const isAkashItem = r.category === 'Akash Solved Question Banks' || (r.tags && r.tags.includes('Akash')) || (r.title && /akash/i.test(r.title));
    const isNotesItem = r.category === 'Lecture Notes & Theory' || (r.tags && r.tags.includes('Notes')) || /notes|unit|handwritten/i.test(r.title);
    const isPyqItem = (r.category && (r.category.includes('Paper') || r.category.includes('PYQ'))) || /mid sem|end sem|pyq|exam/i.test(r.title);
    const isPractItem = (r.category && (r.category.includes('Practical') || r.category.includes('Lab') || r.category.includes('General')));

    if (catFilter === 'akash') return isAkashItem;
    if (catFilter === 'notes') return isNotesItem;
    if (catFilter === 'pyqs') return isPyqItem;
    if (catFilter === 'practicals') return isPractItem;
    return true;
  });

  if (state.typesetOnly) {
    filtered = filtered.filter(i => i.is_typeset);
  }

  if (deckCountBadge) deckCountBadge.innerText = `${filtered.length} Materials`;

  if (filtered.length === 0) {
    if (gridContainer) gridContainer.innerHTML = "";
    if (emptyContainer) {
      emptyContainer.classList.remove("hidden");
      const emptyH4 = emptyContainer.querySelector("h4");
      const emptyP = emptyContainer.querySelector("p");
      if (emptyH4) emptyH4.innerText = "No materials found in this category";
      if (emptyP) emptyP.innerText = "Try switching category filters or check back shortly as more documents are synced.";
    }
  } else {
    if (emptyContainer) emptyContainer.classList.add("hidden");
    if (gridContainer) {
      gridContainer.innerHTML = filtered.map(r => renderResourceCardHtml(r)).join("");
    }
  }

  lucide.createIcons();
}

function applyVaultSearchSuggestion(tag) {
  const searchInput = document.getElementById("resource-search");
  if (!searchInput) return;
  searchInput.value = tag;
  searchInput.focus();
  handleUniversalResourceSearch();
}

function handleUniversalResourceSearch() {
  const searchInput = document.getElementById("resource-search");
  const query = searchInput ? searchInput.value.trim().toLowerCase() : "";
  const clearBtn = document.getElementById("resource-search-clear");
  const countBadge = document.getElementById("resource-search-count-badge");
  const summarySpan = document.getElementById("search-results-summary");
  const searchContainer = document.getElementById("vault-search-results-container");
  const gridContainer = document.getElementById("vault-search-results-grid");
  const hierarchyContainer = document.getElementById("vault-hierarchical-container");

  if (!query) {
    clearResourceSearch();
    return;
  }

  if (clearBtn) clearBtn.classList.remove("hidden");
  if (hierarchyContainer) hierarchyContainer.classList.add("hidden");
  if (searchContainer) searchContainer.classList.remove("hidden");

  const typesetOnly = state.typesetOnly;
  const filtered = (state.resources || []).filter(r => {
    const matchQuery =
      (r.title && r.title.toLowerCase().includes(query)) ||
      (r.subject && r.subject.toLowerCase().includes(query)) ||
      (r.subject_code && r.subject_code.toLowerCase().includes(query)) ||
      (r.category && r.category.toLowerCase().includes(query)) ||
      (r.exam_session && r.exam_session.toLowerCase().includes(query)) ||
      (r.tags && r.tags.some(t => t.toLowerCase().includes(query)));
    const matchType = !typesetOnly || r.is_typeset;
    return matchQuery && matchType;
  });

  if (countBadge) countBadge.innerText = `${filtered.length} matches`;
  if (summarySpan) summarySpan.innerText = `Showing ${filtered.length} match(es) for "${query}" across all 8 semesters`;

  if (gridContainer) {
    if (filtered.length === 0) {
      gridContainer.innerHTML = `
        <div class="col-span-full py-16 text-center text-zinc-500 rounded-2xl glass-card border border-white/5 space-y-3">
          <i data-lucide="file-x" class="w-8 h-8 mx-auto text-zinc-600"></i>
          <p class="text-sm">No documents found matching "${escapeHtml(query)}".</p>
          <button onclick="clearResourceSearch()" class="mt-2 px-3.5 py-1.5 rounded-lg bg-zinc-800 text-xs text-zinc-300 hover:text-white transition-all">Clear Search</button>
        </div>
      `;
    } else {
      gridContainer.innerHTML = filtered.map(r => renderResourceCardHtml(r)).join("");
    }
  }

  lucide.createIcons();
}

function clearResourceSearch() {
  const searchInput = document.getElementById("resource-search");
  if (searchInput) searchInput.value = "";
  const clearBtn = document.getElementById("resource-search-clear");
  if (clearBtn) clearBtn.classList.add("hidden");
  const searchContainer = document.getElementById("vault-search-results-container");
  if (searchContainer) searchContainer.classList.add("hidden");
  const hierarchyContainer = document.getElementById("vault-hierarchical-container");
  if (hierarchyContainer) hierarchyContainer.classList.remove("hidden");
}


function openPdfPreview(title, relPath, driveId = '') {
  document.getElementById("pdf-modal-title").innerText = title;
  const encodedPath = encodeURIComponent(relPath || '');
  const streamUrl = driveId
    ? `/api/resources/view?id=${encodeURIComponent(driveId)}&path=${encodedPath}`
    : `/api/resources/view?path=${encodedPath}`;
  document.getElementById("pdf-iframe").src = streamUrl;
  document.getElementById("pdf-download-btn").href = streamUrl;
  const extBtn = document.getElementById("pdf-external-btn");
  if (extBtn) extBtn.href = streamUrl;
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
      statusDiv.className = "text-xs p-3.5 rounded-2xl bg-red-950/30 text-red-300 border border-red-500/30 shadow-[0_4px_20px_rgba(239,68,68,0.15)] flex items-start gap-2.5 text-left";
      statusDiv.innerHTML = `
        <div class="w-5 h-5 rounded-md bg-red-500/20 text-red-400 border border-red-500/30 flex items-center justify-center shrink-0 mt-0.5">
          <i data-lucide="alert-circle" class="w-3.5 h-3.5"></i>
        </div>
        <div class="space-y-0.5">
          <div class="font-bold text-red-300 text-xs">ExamWeb Login Failed</div>
          <div class="text-[11px] text-red-400/90 leading-relaxed">${escapeHtml(data.message || 'Please check enrollment number, password, and captcha.')}</div>
        </div>
      `;
      refreshExamWebCaptcha();
      showToast(data.message || "ExamWeb authentication failed", "error", "ExamWeb Error");
    }
  } catch (err) {
    statusDiv.className = "text-xs p-3.5 rounded-2xl bg-red-950/30 text-red-300 border border-red-500/30 shadow-[0_4px_20px_rgba(239,68,68,0.15)] flex items-start gap-2.5 text-left";
    statusDiv.innerHTML = `
      <div class="w-5 h-5 rounded-md bg-red-500/20 text-red-400 border border-red-500/30 flex items-center justify-center shrink-0 mt-0.5">
        <i data-lucide="wifi-off" class="w-3.5 h-3.5"></i>
      </div>
      <div class="space-y-0.5">
        <div class="font-bold text-red-300 text-xs">Backend Communication Error</div>
        <div class="text-[11px] text-red-400/90 leading-relaxed">Could not reach the university examination portal. Please try again.</div>
      </div>
    `;
    showToast("Communication error with examination server", "error", "Portal Error");
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
// TAB: EDUMARSHAL ATTENDANCE RADAR
// =============================================================================

async function fetchAttendance(force = false) {
  const grid = document.getElementById("attendance-grid");
  if (!grid) return;

  if (state.attendanceData && !force) {
    renderAttendance(state.attendanceData);
    return;
  }

  state.isAttendanceLoading = true;
  grid.innerHTML = `
    <div class="col-span-full py-16 text-center text-zinc-500">
      <i data-lucide="loader-2" class="w-6 h-6 animate-spin mx-auto mb-2 text-emerald-400"></i>
      <p class="text-xs">Authenticating with Edumarshal Cloud & syncing attendance logs...</p>
    </div>
  `;
  lucide.createIcons();

  try {
    const res = await fetch(`/api/edumarshal/attendance?force=${force}`, {
      headers: state.sessionToken ? { "Authorization": `Bearer ${state.sessionToken}` } : {}
    });
    const data = await res.json();
    if (data.status === "error") {
      throw new Error(data.message || "Failed to load attendance");
    }

    state.attendanceData = data;
    state.isAttendanceLoading = false;
    renderAttendance(data);
  } catch (err) {
    console.error("Attendance fetch error:", err);
    state.isAttendanceLoading = false;
    const isCredIssue = err.message && (
      err.message.toLowerCase().includes("credential") || 
      err.message.toLowerCase().includes("password") || 
      err.message.toLowerCase().includes("login") || 
      err.message.toLowerCase().includes("auth") ||
      err.message.toLowerCase().includes("linked")
    );

    grid.innerHTML = renderCustomErrorCard({
      icon: isCredIssue ? "shield-alert" : "cloud-off",
      title: isCredIssue ? "Edumarshal Authentication Required" : "Attendance Synchronization Interrupted",
      message: err.message || "Failed to communicate with Edumarshal student portal.",
      actionText: isCredIssue ? "Verify Edumarshal" : "Retry Sync",
      actionFn: isCredIssue ? "openEdumarshalVerifyModal()" : "fetchAttendance(true)",
      secondaryText: isCredIssue ? "Retry Sync" : null,
      secondaryFn: isCredIssue ? "fetchAttendance(true)" : null
    });
    if (window.lucide && typeof window.lucide.createIcons === "function") {
      window.lucide.createIcons();
    }
    showToast(err.message || "Failed to load attendance records", "error", "Attendance Error");
  }
}

function renderAttendance(data) {
  const overall = data.overall || {};
  const pct = overall.percentage != null ? overall.percentage : 0;
  const present = overall.present != null ? overall.present : 0;
  const total = overall.total != null ? overall.total : 0;
  const missed = overall.absent != null ? overall.absent : (total - present);

  let bunkBuffer = 0;
  let statusText = "Eligible (≥ 75%)";
  let statusClass = "text-emerald-400";
  let bufferText = "+0";

  if (pct >= 75.0) {
    bunkBuffer = Math.floor(present / 0.75) - total;
    bufferText = `+${Math.max(0, bunkBuffer)}`;
    statusText = "Safe & Eligible (≥ 75%)";
    statusClass = "text-emerald-400";
  } else {
    const needed = Math.ceil((0.75 * total - present) / 0.25);
    bufferText = `-${needed}`;
    statusText = `Warning: Need ${needed} classes to reach 75%`;
    statusClass = "text-amber-400";
  }

  // Update top banner
  const pctElem = document.getElementById("att-overall-pct");
  if (pctElem) {
    pctElem.innerText = `${pct.toFixed(1)}%`;
    pctElem.className = `text-xl font-bold ${pct >= 75 ? 'text-emerald-400' : 'text-amber-400'}`;
  }

  const marginElem = document.getElementById("att-bunk-margin");
  if (marginElem) {
    marginElem.innerText = bufferText;
    marginElem.className = `text-xl font-bold ${bunkBuffer >= 0 ? 'text-blue-400' : 'text-red-400'}`;
  }

  const lectElem = document.getElementById("att-lectures-stat");
  if (lectElem) lectElem.innerText = `${present} / ${total} Attended`;

  const missedElem = document.getElementById("att-missed-stat");
  if (missedElem) missedElem.innerText = `${missed} Lectures`;

  const eligElem = document.getElementById("att-eligibility-stat");
  if (eligElem) {
    eligElem.innerText = statusText;
    eligElem.className = `font-semibold font-mono mt-0.5 block ${statusClass}`;
  }

  const countElem = document.getElementById("att-subjects-count");
  if (countElem) countElem.innerText = `${data.subjects ? data.subjects.length : 0} Enrolled Courses`;

  const grid = document.getElementById("attendance-grid");
  if (!grid) return;

  const subjects = data.subjects || [];
  if (!subjects.length) {
    grid.innerHTML = `
      <div class="col-span-full py-16 text-center text-zinc-500">
        <i data-lucide="calendar-x" class="w-8 h-8 mx-auto mb-2 text-zinc-600"></i>
        <p class="text-sm">No course records found in this Edumarshal term.</p>
      </div>
    `;
    lucide.createIcons();
    return;
  }

  grid.innerHTML = subjects.map(s => {
    const sPct = s.percentage != null ? s.percentage : 0;
    const isLab = s.name.toLowerCase().includes("lab");
    
    let badgeClass = "bg-emerald-500/10 text-emerald-400 border-emerald-500/20";
    let barColor = "bg-gradient-to-r from-emerald-500 to-teal-400";
    let advice = "";

    if (sPct >= 75.0) {
      const canMiss = Math.floor(s.present / 0.75) - s.total;
      badgeClass = "bg-emerald-500/10 text-emerald-400 border-emerald-500/20";
      barColor = "bg-gradient-to-r from-emerald-500 to-teal-400";
      advice = canMiss > 0 ? `Can safely miss ${canMiss} more lecture${canMiss > 1 ? 's' : ''}` : `Right on threshold (0 misses left)`;
    } else if (sPct >= 60.0) {
      const need = Math.ceil((0.75 * s.total - s.present) / 0.25);
      badgeClass = "bg-amber-500/10 text-amber-400 border-amber-500/20";
      barColor = "bg-gradient-to-r from-amber-500 to-yellow-400";
      advice = `Attend next ${need} class${need > 1 ? 'es' : ''} continuously to reach 75%`;
    } else {
      const need = Math.ceil((0.75 * s.total - s.present) / 0.25);
      badgeClass = "bg-red-500/10 text-red-400 border-red-500/20";
      barColor = "bg-gradient-to-r from-red-500 to-rose-400";
      advice = `Critical shortage: Need ${need} class${need > 1 ? 'es' : ''} to reach 75%`;
    }

    return `
      <div class="p-5 rounded-2xl glass-card flex flex-col justify-between space-y-4 hover:border-white/15 transition-all">
        <div class="space-y-3">
          <div class="flex items-center justify-between gap-2">
            <span class="px-2 py-0.5 rounded text-[10px] font-mono font-bold border ${badgeClass}">
              ${s.status.toUpperCase()}
            </span>
            <span class="text-xs font-mono font-bold text-white">${sPct}%</span>
          </div>

          <div>
            <h3 class="text-sm font-semibold text-white leading-snug line-clamp-2">
              ${s.name}
            </h3>
            <span class="text-[11px] font-mono text-zinc-500 mt-0.5 block">${s.code || 'CORE'} ${isLab ? '• Practical' : '• Theory'}</span>
          </div>

          <!-- Progress Bar -->
          <div class="space-y-1.5 pt-1">
            <div class="w-full h-2 rounded-full bg-zinc-800 overflow-hidden">
              <div class="h-full rounded-full transition-all duration-500 ${barColor}" style="width: ${Math.min(100, Math.max(0, sPct))}%"></div>
            </div>
            <div class="flex items-center justify-between text-[11px] text-zinc-400 font-mono">
              <span>${s.present} of ${s.total} attended</span>
              <span class="text-zinc-500">${s.absent} missed</span>
            </div>
          </div>
        </div>

        <div class="pt-3 border-t border-white/5 text-[11px] text-zinc-400 flex items-center justify-between gap-2">
          <span class="truncate text-zinc-400 flex items-center gap-1.5">
            <i data-lucide="info" class="w-3.5 h-3.5 shrink-0 text-zinc-500"></i>
            <span class="truncate">${advice}</span>
          </span>
          <span class="shrink-0 px-2 py-0.5 rounded bg-zinc-900 text-zinc-300 font-mono text-[10px]">
            Target 75%
          </span>
        </div>
      </div>
    `;
  }).join("");

  lucide.createIcons();
}

function switchAttendanceSubView(view) {
  state.attendanceView = view;
  const btnCourses = document.getElementById("btn-att-tab-courses");
  const btnCal = document.getElementById("btn-att-tab-calendar");
  const viewCourses = document.getElementById("att-view-courses");
  const viewCal = document.getElementById("att-view-calendar");
  const meta = document.getElementById("att-view-meta");

  if (view === "courses") {
    if (btnCourses) {
      btnCourses.className = "px-4 py-1.5 rounded-lg font-semibold text-white bg-blue-600 shadow transition-all flex items-center gap-1.5";
    }
    if (btnCal) {
      btnCal.className = "px-4 py-1.5 rounded-lg font-medium text-zinc-400 hover:text-white transition-all flex items-center gap-1.5";
    }
    if (viewCourses) viewCourses.classList.remove("hidden");
    if (viewCal) viewCal.classList.add("hidden");
    if (meta && state.attendanceData && state.attendanceData.subjects) {
      meta.innerText = `${state.attendanceData.subjects.length} Enrolled Courses`;
    }
  } else {
    if (btnCourses) {
      btnCourses.className = "px-4 py-1.5 rounded-lg font-medium text-zinc-400 hover:text-white transition-all flex items-center gap-1.5";
    }
    if (btnCal) {
      btnCal.className = "px-4 py-1.5 rounded-lg font-semibold text-white bg-blue-600 shadow transition-all flex items-center gap-1.5";
    }
    if (viewCourses) viewCourses.classList.add("hidden");
    if (viewCal) viewCal.classList.remove("hidden");
    if (meta && state.calendarData) {
      meta.innerText = `${state.calendarData.total_days_logged || 36} Academic Days Logged`;
    }
    if (!state.calendarData) {
      fetchAttendanceCalendar();
    } else {
      renderAttendanceCalendar(state.currentCalYear, state.currentCalMonth);
    }
  }
  lucide.createIcons();
}

async function fetchAttendanceCalendar(force = false) {
  const grid = document.getElementById("calendar-days-grid");
  if (!grid) return;

  if (state.calendarData && !force) {
    renderAttendanceCalendar(state.currentCalYear, state.currentCalMonth);
    return;
  }

  try {
    const res = await fetch(`/api/edumarshal/calendar?force=${force}`, {
      headers: state.sessionToken ? { "Authorization": `Bearer ${state.sessionToken}` } : {}
    });
    const data = await res.json();
    if (data.status === "error") {
      throw new Error(data.message || "Failed to load calendar records");
    }

    state.calendarData = data;
    
    // Auto-select latest recorded month with data
    if (data.dates && Object.keys(data.dates).length > 0) {
      const dates = Object.keys(data.dates).sort();
      const lastDate = dates[dates.length - 1]; // e.g. "2026-09-25"
      const parts = lastDate.split("-");
      state.currentCalYear = parseInt(parts[0], 10);
      state.currentCalMonth = parseInt(parts[1], 10);
    }

    renderAttendanceCalendar(state.currentCalYear, state.currentCalMonth);
  } catch (err) {
    console.error("Calendar fetch error:", err);
    grid.innerHTML = `
      <div class="col-span-7">
        ${renderCustomErrorCard({
          icon: "calendar-x-2",
          title: "Calendar Records Unavailable",
          message: err.message || "Unable to extract daily attendance lecture timestamps from Edumarshal.",
          actionText: "Retry Calendar Sync",
          actionFn: "fetchAttendanceCalendar(true)"
        })}
      </div>
    `;
    if (window.lucide && typeof window.lucide.createIcons === "function") {
      window.lucide.createIcons();
    }
    showToast(err.message || "Failed to load calendar records", "error", "Calendar Sync Error");
  }
}

function prevCalendarMonth() {
  if (state.currentCalMonth === 1) {
    state.currentCalMonth = 12;
    state.currentCalYear -= 1;
  } else {
    state.currentCalMonth -= 1;
  }
  renderAttendanceCalendar(state.currentCalYear, state.currentCalMonth);
}

function nextCalendarMonth() {
  if (state.currentCalMonth === 12) {
    state.currentCalMonth = 1;
    state.currentCalYear += 1;
  } else {
    state.currentCalMonth += 1;
  }
  renderAttendanceCalendar(state.currentCalYear, state.currentCalMonth);
}

const CALENDAR_MONTH_NAMES = [
  "January", "February", "March", "April", "May", "June",
  "July", "August", "September", "October", "November", "December"
];

function renderAttendanceCalendar(year, month) {
  const grid = document.getElementById("calendar-days-grid");
  const monthTitle = document.getElementById("cal-month-title");
  if (!grid) return;

  if (monthTitle) {
    monthTitle.innerText = `${CALENDAR_MONTH_NAMES[month - 1]} ${year}`;
  }

  const allDates = (state.calendarData && state.calendarData.dates) || {};

  // Days in month
  const daysInMonth = new Date(year, month, 0).getDate();
  // Day of week of 1st day (0 = Sunday, 1 = Monday, ..., 6 = Saturday)
  const firstDayObj = new Date(year, month - 1, 1);
  let firstDayOfWeek = firstDayObj.getDay();
  // Adjust to Monday = 0, Sunday = 6
  let leadBlanks = (firstDayOfWeek === 0) ? 6 : (firstDayOfWeek - 1);

  // Filter dates for this month
  const monthPrefix = `${year}-${String(month).padStart(2, '0')}`;
  let monthAcademicDays = 0;
  let monthFullDays = 0;
  let monthPartialDays = 0;
  let monthMissedLectures = 0;

  for (let d = 1; d <= daysInMonth; d++) {
    const ds = `${monthPrefix}-${String(d).padStart(2, '0')}`;
    if (allDates[ds]) {
      const rec = allDates[ds];
      monthAcademicDays++;
      if (rec.percentage >= 100) monthFullDays++;
      else if (rec.percentage > 0) monthPartialDays++;
      monthMissedLectures += (rec.absent_count || 0);
    }
  }

  // Update KPI counters
  const kpiDays = document.getElementById("cal-kpi-days");
  const kpiFull = document.getElementById("cal-kpi-full");
  const kpiPartial = document.getElementById("cal-kpi-partial");
  const kpiMissed = document.getElementById("cal-kpi-missed");

  if (kpiDays) kpiDays.innerText = monthAcademicDays;
  if (kpiFull) kpiFull.innerText = monthFullDays;
  if (kpiPartial) kpiPartial.innerText = monthPartialDays;
  if (kpiMissed) kpiMissed.innerText = monthMissedLectures;

  let html = "";

  // Render blank placeholders before 1st of the month
  for (let i = 0; i < leadBlanks; i++) {
    html += `<div class="min-h-[85px] sm:min-h-[105px] p-2 rounded-xl bg-zinc-950/30 border border-white/[0.02] opacity-25"></div>`;
  }

  // Render day tiles
  for (let d = 1; d <= daysInMonth; d++) {
    const dateStr = `${monthPrefix}-${String(d).padStart(2, '0')}`;
    const dayData = allDates[dateStr];

    // Day of week for current date (0 = Mon, ..., 6 = Sun)
    const currentDayOfWeek = (leadBlanks + d - 1) % 7;
    const isWeekend = (currentDayOfWeek === 5 || currentDayOfWeek === 6);

    if (dayData) {
      const pct = dayData.percentage != null ? dayData.percentage : 100;
      const isFull = pct >= 100;
      const isAbsent = pct === 0;
      const isPartial = !isFull && !isAbsent;

      let cardBorder = isFull
        ? "border-emerald-500/30 hover:border-emerald-500/60 bg-emerald-950/20"
        : (isPartial
            ? "border-amber-500/40 hover:border-amber-500/70 bg-amber-950/20"
            : "border-rose-500/40 hover:border-rose-500/70 bg-rose-950/20");

      let badgeColor = isFull
        ? "bg-emerald-500/20 text-emerald-300 border-emerald-500/30"
        : (isPartial
            ? "bg-amber-500/20 text-amber-300 border-amber-500/30 font-bold"
            : "bg-rose-500/20 text-rose-300 border-rose-500/30 font-bold");

      let statusLabel = isFull
        ? `${dayData.present_count}/${dayData.total_lectures} Present`
        : (isPartial
            ? `${dayData.present_count}/${dayData.total_lectures} • Missed ${dayData.absent_count}`
            : `All ${dayData.total_lectures} Missed`);

      html += `
        <div onclick="openDayInspectionModal('${dateStr}')" class="min-h-[85px] sm:min-h-[105px] p-2 sm:p-2.5 rounded-xl border ${cardBorder} flex flex-col justify-between cursor-pointer transition-all hover:scale-[1.02] group shadow-sm">
          <div class="flex items-center justify-between">
            <span class="font-mono font-bold text-xs sm:text-sm text-white group-hover:text-blue-400 transition-colors">${d}</span>
            <span class="w-2 h-2 rounded-full ${isFull ? 'bg-emerald-400' : (isPartial ? 'bg-amber-400 animate-pulse' : 'bg-rose-400')}"></span>
          </div>
          <div class="mt-1 space-y-1">
            <span class="block px-1.5 py-0.5 rounded text-[9px] sm:text-[10px] font-mono border ${badgeColor} text-center truncate">
              ${statusLabel}
            </span>
            <span class="text-[9px] text-zinc-400 group-hover:text-zinc-200 hidden sm:block text-right">
              Inspect →
            </span>
          </div>
        </div>
      `;
    } else {
      // Non-class or weekend day
      const tileBg = isWeekend ? "bg-zinc-950/40 border-white/[0.04]" : "bg-zinc-900/30 border-white/[0.04]";
      html += `
        <div class="min-h-[85px] sm:min-h-[105px] p-2 sm:p-2.5 rounded-xl ${tileBg} border flex flex-col justify-between">
          <span class="font-mono text-xs sm:text-sm text-zinc-600">${d}</span>
          <span class="text-[9px] text-zinc-700 font-mono text-center">
            ${isWeekend ? 'Weekend' : 'Off'}
          </span>
        </div>
      `;
    }
  }

  grid.innerHTML = html;
  lucide.createIcons();
}

function openDayInspectionModal(dateStr) {
  const modal = document.getElementById("day-inspection-modal");
  if (!modal || !state.calendarData || !state.calendarData.dates) return;

  const dayData = state.calendarData.dates[dateStr];
  if (!dayData) return;

  const badgeElem = document.getElementById("day-modal-badge");
  const dateElem = document.getElementById("day-modal-date");
  const sumElem = document.getElementById("day-modal-summary");
  const listElem = document.getElementById("day-modal-lectures");

  const dt = new Date(dateStr + "T00:00:00");
  const formattedDate = dt.toLocaleDateString("en-US", { weekday: "long", year: "numeric", month: "long", day: "numeric" });

  if (dateElem) dateElem.innerText = formattedDate;

  const pct = dayData.percentage != null ? dayData.percentage : 100;
  const isFull = pct >= 100;
  const isAbsent = pct === 0;

  if (badgeElem) {
    if (isFull) {
      badgeElem.className = "inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-[10px] font-mono font-bold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 mb-1";
      badgeElem.innerText = "FULL ATTENDANCE (100%)";
    } else if (isAbsent) {
      badgeElem.className = "inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-[10px] font-mono font-bold bg-rose-500/10 text-rose-400 border border-rose-500/20 mb-1";
      badgeElem.innerText = "ALL LECTURES MISSED (0%)";
    } else {
      badgeElem.className = "inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-[10px] font-mono font-bold bg-amber-500/10 text-amber-400 border border-amber-500/20 mb-1";
      badgeElem.innerText = `PARTIAL ATTENDANCE (${pct.toFixed(0)}%)`;
    }
  }

  if (sumElem) {
    sumElem.innerText = `${dayData.present_count} of ${dayData.total_lectures} Lectures Attended • ${dayData.absent_count} Missed`;
  }

  if (listElem) {
    const lecs = dayData.lectures || [];
    if (!lecs.length) {
      listElem.innerHTML = `<div class="p-3 text-center text-zinc-500 text-xs">No lecture logs found for this date.</div>`;
    } else {
      listElem.innerHTML = lecs.map((lec, idx) => {
        const isPresent = lec.status === "P";
        const badgeClass = isPresent
          ? "bg-emerald-500/10 text-emerald-400 border-emerald-500/20"
          : "bg-rose-500/10 text-rose-400 border-rose-500/20 font-bold";
        const statusLabel = isPresent ? "✓ PRESENT" : "✕ ABSENT (MISSED)";

        return `
          <div class="p-3 rounded-xl bg-zinc-900 border ${isPresent ? 'border-white/5' : 'border-rose-500/30'} flex items-center justify-between gap-3">
            <div class="flex items-center gap-2.5 min-w-0">
              <span class="w-6 h-6 rounded-lg bg-zinc-800 text-zinc-400 text-[10px] font-mono flex items-center justify-center shrink-0">
                #${idx + 1}
              </span>
              <div class="min-w-0">
                <span class="font-semibold text-white text-xs block truncate">${lec.subject || 'Course Lecture'}</span>
                <span class="text-[10px] text-zinc-500 font-mono">Slot Period ${idx + 1}</span>
              </div>
            </div>
            <span class="px-2.5 py-1 rounded-lg text-[10px] font-mono border ${badgeClass} shrink-0">
              ${statusLabel}
            </span>
          </div>
        `;
      }).join("");
    }
  }

  modal.classList.add("open");
  lucide.createIcons();
}

function closeDayInspectionModal() {
  const modal = document.getElementById("day-inspection-modal");
  if (modal) modal.classList.remove("open");
}

function closeDayInspectionModalOnBackdrop(e) {
  if (e.target.id === "day-inspection-modal") {
    closeDayInspectionModal();
  }
}

// =============================================================================
// STEALTH ADMIN COMMAND CENTER & STUDENT RECORDS LIVE EDITOR
// =============================================================================

let adminSecretClickCount = 0;
let adminSecretClickTimer = null;
let currentEditingStudent = null;
let currentEditingStudentRoll = null;

function isAdminAuthenticated() {
  return !!sessionStorage.getItem("campusiq_admin_token");
}

function getAdminToken() {
  return sessionStorage.getItem("campusiq_admin_token") || "";
}

function getAdminAuthHeaders() {
  const token = getAdminToken();
  const headers = { "Content-Type": "application/json" };
  if (token) {
    headers["X-Admin-Token"] = token;
    headers["Authorization"] = `Bearer ${token}`;
  }
  return headers;
}

// 1. Stealth Access Triggers
function handleSecretAdminTrigger() {
  adminSecretClickCount++;
  clearTimeout(adminSecretClickTimer);
  adminSecretClickTimer = setTimeout(() => {
    adminSecretClickCount = 0;
  }, 1200);

  if (adminSecretClickCount >= 3) {
    adminSecretClickCount = 0;
    triggerAdminPanelAccess();
  }
}

function triggerAdminPanelAccess() {
  if (isAdminAuthenticated()) {
    switchTab("admin");
    showToast("Master Admin Console Active", "success", "Security Clearance");
  } else {
    openAdminAuthModal();
  }
}

function checkAdminHashRoute() {
  if (window.location.hash === "#admin" || window.location.hash === "#admin-console") {
    triggerAdminPanelAccess();
  }
}

window.addEventListener("hashchange", checkAdminHashRoute);

window.addEventListener("keydown", (e) => {
  if ((e.ctrlKey || e.metaKey) && e.shiftKey && (e.key === "A" || e.key === "a")) {
    e.preventDefault();
    triggerAdminPanelAccess();
  }
  // Universal search keyboard shortcut '/' when not typing in an input
  if (e.key === "/" && document.activeElement.tagName !== "INPUT" && document.activeElement.tagName !== "TEXTAREA") {
    if (state.activeTab === "resources") {
      e.preventDefault();
      const s = document.getElementById("resource-search");
      if (s) {
        s.focus();
        s.select();
      }
    }
  }
  // Escape clears search
  if (e.key === "Escape" && document.activeElement && document.activeElement.id === "resource-search") {
    clearResourceSearch();
    document.activeElement.blur();
  }
});

// Console backdoor access for power-users
window.openAdminPanel = triggerAdminPanelAccess;

// 2. Authentication Clearance Modal
function openAdminAuthModal() {
  const modal = document.getElementById("admin-auth-modal");
  const input = document.getElementById("admin-passcode-input");
  const err = document.getElementById("admin-auth-error");
  if (err) err.classList.add("hidden");
  if (input) input.value = "";
  if (modal) modal.classList.remove("hidden");
  setTimeout(() => { if (input) input.focus(); }, 100);
}

function closeAdminAuthModal() {
  const modal = document.getElementById("admin-auth-modal");
  if (modal) modal.classList.add("hidden");
}

function togglePasscodeVisibility() {
  const input = document.getElementById("admin-passcode-input");
  const eye = document.getElementById("admin-passcode-eye");
  if (!input) return;
  if (input.type === "password") {
    input.type = "text";
    if (eye) eye.setAttribute("data-lucide", "eye-off");
  } else {
    input.type = "password";
    if (eye) eye.setAttribute("data-lucide", "eye");
  }
  lucide.createIcons();
}

async function submitAdminPasscode(event) {
  if (event) event.preventDefault();
  const input = document.getElementById("admin-passcode-input");
  const btn = document.getElementById("btn-admin-auth-submit");
  const err = document.getElementById("admin-auth-error");
  const passcode = input ? input.value.trim() : "";

  if (!passcode) return;

  if (btn) {
    btn.disabled = true;
    btn.innerHTML = `<i data-lucide="loader-2" class="w-3.5 h-3.5 animate-spin"></i><span>Verifying...</span>`;
    lucide.createIcons();
  }
  if (err) err.classList.add("hidden");

  try {
    const res = await fetch("/api/admin/auth", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ passcode })
    });
    const data = await res.json();

    const adminToken = data.token || data.admin_token;
    if (res.ok && data.status === "success" && adminToken) {
      sessionStorage.setItem("campusiq_admin_token", adminToken);
      closeAdminAuthModal();
      switchTab("admin");
      loadAdminRoster(true);
      showToast("Security clearance verified. Master admin console unlocked.", "success", "Clearance Granted");
    } else {
      if (err) {
        err.textContent = data.message || "Invalid master security passcode. Clearance rejected.";
        err.classList.remove("hidden");
      }
      showToast("Invalid administrative credentials.", "error", "Security Breach Attempt");
    }
  } catch (e) {
    console.error("Admin auth failed:", e);
    if (err) {
      err.textContent = "Authentication server unreachable. Verify network connection.";
      err.classList.remove("hidden");
    }
  } finally {
    if (btn) {
      btn.disabled = false;
      btn.innerHTML = `<i data-lucide="key" class="w-3.5 h-3.5"></i><span>Unlock Console</span>`;
      lucide.createIcons();
    }
  }
}

function lockAdminPanel() {
  sessionStorage.removeItem("campusiq_admin_token");
  if (window.location.hash === "#admin" || window.location.hash === "#admin-console") {
    history.replaceState(null, "", " ");
  }
  switchTab("results");
  showToast("Master administrative terminal locked and session cleared.", "info", "Console Locked");
}

// 3. Admin Roster Loader & Filtering
async function loadAdminRoster(force = false) {
  const grid = document.getElementById("admin-students-grid");
  const emptyState = document.getElementById("admin-empty-state");
  if (!grid) return;

  if (!isAdminAuthenticated()) {
    openAdminAuthModal();
    return;
  }

  grid.innerHTML = `
    <div class="col-span-full py-16 text-center text-zinc-500 flex flex-col items-center justify-center gap-3">
      <i data-lucide="loader-2" class="w-6 h-6 animate-spin text-red-500"></i>
      <span class="font-mono text-xs text-zinc-400">Querying database registry and decrypting student dossiers...</span>
    </div>
  `;
  lucide.createIcons();

  try {
    const res = await fetch("/api/admin/students", {
      headers: getAdminAuthHeaders()
    });

    if (res.status === 401) {
      sessionStorage.removeItem("campusiq_admin_token");
      openAdminAuthModal();
      return;
    }

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
      grid.innerHTML = renderCustomErrorCard({
        icon: "users",
        title: "Academic Roster Unavailable",
        message: "Failed to load student dossiers from registry. Please verify database connection or retry.",
        actionText: "Reload Roster",
        actionFn: "loadAdminRoster(true)"
      });
      lucide.createIcons();
      showToast("Failed to load academic dossiers", "error", "Roster Error");
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
      (s.email && s.email.toLowerCase().includes(query)) ||
      (s.programme_name && s.programme_name.toLowerCase().includes(query)) ||
      (s.branch && s.branch.toLowerCase().includes(query))
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
      <div class="p-5 rounded-3xl glass-card border border-white/10 hover:border-red-500/40 transition-all flex flex-col justify-between space-y-4 shadow-lg group">
        
        <!-- Header: Student Avatar & Info -->
        <div class="flex items-start gap-3.5">
          <div class="w-14 h-16 rounded-2xl bg-zinc-900 border border-white/15 overflow-hidden shrink-0 flex items-center justify-center shadow-md">
            ${s.photo_base64 ? `
              <img src="${s.photo_base64}" alt="${s.name}" class="w-full h-full object-cover">
            ` : `
              <span class="text-xl font-bold font-mono text-zinc-400 group-hover:text-red-400 transition-colors">${initial}</span>
            `}
          </div>

          <div class="overflow-hidden flex-1 min-w-0">
            <div class="flex items-center gap-1.5 flex-wrap">
              <span class="font-mono font-bold text-xs text-red-400 tracking-wider">${s.roll_number}</span>
              ${isClean ? `
                <span class="px-1.5 py-0.5 rounded text-[9px] font-mono bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 font-bold">GOOD STANDING</span>
              ` : `
                <span class="px-1.5 py-0.5 rounded text-[9px] font-mono bg-red-500/10 text-red-400 border border-red-500/20 font-bold">${s.backlogs_count} BACKLOG(S)</span>
              `}
              ${s.is_verified ? `
                <span class="px-1.5 py-0.5 rounded text-[9px] font-mono bg-blue-500/10 text-blue-400 border border-blue-500/20">VERIFIED</span>
              ` : ''}
            </div>
            <h3 class="text-sm font-bold text-white truncate mt-0.5">${s.name}</h3>
            <p class="text-[11px] text-zinc-400 truncate">${s.programme_name || 'B.Tech (CSE)'}</p>
            <p class="text-[10px] text-zinc-500 truncate">${s.institution_name || 'MAIT'} • Sem ${s.semester || 3}</p>
          </div>
        </div>

        <!-- Academic & Attendance Metrics -->
        <div class="grid grid-cols-3 gap-2 p-2.5 rounded-xl bg-zinc-950/70 border border-white/5 text-center">
          <div>
            <span class="block text-[10px] font-mono text-zinc-500 uppercase">CGPA</span>
            <span class="text-sm font-black font-mono text-blue-400">${(s.cgpa || 0).toFixed(2)}</span>
          </div>
          <div>
            <span class="block text-[10px] font-mono text-zinc-500 uppercase">Agg. %</span>
            <span class="text-sm font-bold font-mono text-emerald-400">${(s.percentage || 0).toFixed(1)}%</span>
          </div>
          <div>
            <span class="block text-[10px] font-mono text-zinc-500 uppercase">Semesters</span>
            <span class="text-sm font-bold font-mono text-zinc-300">${s.total_semesters || s.semester || 1}</span>
          </div>
        </div>

        <!-- Action Buttons -->
        <div class="grid grid-cols-2 gap-2 pt-1">
          <button onclick="openAdminStudentEditor('${s.roll_number}')" class="py-2.5 px-3 rounded-xl bg-red-500/10 hover:bg-red-500/20 border border-red-500/30 text-red-400 hover:text-white font-semibold text-xs transition-all flex items-center justify-center gap-1.5 shadow-sm">
            <i data-lucide="edit-3" class="w-3.5 h-3.5"></i>
            <span>Live Edit</span>
          </button>
          <button onclick="inspectStudentDossier('${s.roll_number}')" class="py-2.5 px-3 rounded-xl bg-zinc-900 hover:bg-zinc-800 border border-white/10 text-zinc-300 hover:text-white font-semibold text-xs transition-all flex items-center justify-center gap-1.5 shadow-sm">
            <i data-lucide="file-text" class="w-3.5 h-3.5 text-blue-400"></i>
            <span>Marksheet</span>
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
    const res = await fetch(`/api/admin/students/${roll}`, {
      headers: getAdminAuthHeaders()
    });
    const data = await res.json();
    if (data.status === "success" && data.student) {
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

// 4. Deep Multi-Tab Student Editor Controller
async function openAdminStudentEditor(roll) {
  showToast(`Opening editor for ${roll}...`, "info", "Student Editor");
  currentEditingStudentRoll = roll;

  try {
    const res = await fetch(`/api/admin/students/${roll}/full`, {
      headers: getAdminAuthHeaders()
    });

    if (res.status === 401) {
      sessionStorage.removeItem("campusiq_admin_token");
      openAdminAuthModal();
      return;
    }

    const data = await res.json();
    if (!res.ok || data.status !== "success" || !data.student) {
      showToast(data.message || `Failed to fetch ground truth for ${roll}`, "error", "Editor Error");
      return;
    }

    currentEditingStudent = data.student;

    // Header updates
    const titleEl = document.getElementById("admin-editor-title");
    const badgeEl = document.getElementById("admin-editor-roll-badge");
    if (titleEl) titleEl.textContent = `Editing: ${currentEditingStudent.name || 'Student'}`;
    if (badgeEl) badgeEl.textContent = roll;

    // Populate Tab 1: Profile & Identity
    const sObj = currentEditingStudent.student || currentEditingStudent;
    document.getElementById("admin-edit-roll").value = roll;
    document.getElementById("admin-edit-name").value = sObj.name || "";
    document.getElementById("admin-edit-father").value = sObj.father_name || "";
    document.getElementById("admin-edit-email").value = currentEditingStudent.email || "";
    document.getElementById("admin-edit-branch").value = currentEditingStudent.branch || sObj.branch || "CSE";
    document.getElementById("admin-edit-programme").value = sObj.programme_name || "";
    document.getElementById("admin-edit-semester").value = currentEditingStudent.semester || sObj.semester || 3;
    document.getElementById("admin-edit-batch").value = sObj.batch || "2023-2027";
    document.getElementById("admin-edit-institution").value = sObj.institution_name || "MAHARAJA AGRASEN INSTITUTE OF TECHNOLOGY";
    
    const verifiedCheckbox = document.getElementById("admin-edit-is-verified");
    if (verifiedCheckbox) {
      verifiedCheckbox.checked = !!(currentEditingStudent.is_verified || (data.user && data.user.is_verified));
    }

    // Populate Tab 2: Results & Marksheet
    const ov = currentEditingStudent.overall || {};
    document.getElementById("admin-edit-cgpa").value = (ov.cgpa !== undefined ? ov.cgpa : 8.5).toFixed(2);
    document.getElementById("admin-edit-percentage").value = (ov.percentage !== undefined ? ov.percentage : 80.0).toFixed(1);
    document.getElementById("admin-edit-backlogs").value = (currentEditingStudent.backlogs || []).length;
    document.getElementById("admin-edit-credits").value = ov.total_credits || 50;

    renderAdminEditorSemesters();

    // Populate Tab 3: Attendance Radar
    const att = currentEditingStudent.attendance || {};
    const attOv = att.overall || {};
    document.getElementById("admin-edit-att-pct").value = (attOv.percentage !== undefined ? attOv.percentage : 85.0).toFixed(1);
    document.getElementById("admin-edit-att-present").value = attOv.present !== undefined ? attOv.present : 85;
    document.getElementById("admin-edit-att-total").value = attOv.total !== undefined ? attOv.total : 100;
    document.getElementById("admin-edit-att-margin").value = attOv.bunk_buffer !== undefined ? attOv.bunk_buffer : 5;

    renderAdminEditorCourses();

    // Populate Tab 4: Raw JSON
    const jsonArea = document.getElementById("admin-edit-raw-json");
    if (jsonArea) {
      jsonArea.value = JSON.stringify(currentEditingStudent, null, 2);
    }

    // Reset to profile tab
    switchAdminEditorTab("profile");

    // Open Modal
    const modal = document.getElementById("admin-student-editor-modal");
    if (modal) modal.classList.remove("hidden");
    lucide.createIcons();

  } catch (err) {
    console.error("Open admin student editor failed:", err);
    showToast("Error opening student editor.", "error", "Editor Exception");
  }
}

function closeAdminStudentEditorModal() {
  const modal = document.getElementById("admin-student-editor-modal");
  if (modal) modal.classList.add("hidden");
  currentEditingStudent = null;
  currentEditingStudentRoll = null;
}

function switchAdminEditorTab(tabName) {
  const tabs = ["profile", "results", "attendance", "json"];
  
  // Sync changes if switching to or from json
  if (tabName === "json") {
    syncAdminEditorFieldsToMemory();
    const jsonArea = document.getElementById("admin-edit-raw-json");
    if (jsonArea && currentEditingStudent) {
      jsonArea.value = JSON.stringify(currentEditingStudent, null, 2);
    }
  }

  tabs.forEach(t => {
    const btn = document.getElementById(`admin-tab-btn-${t}`);
    const pane = document.getElementById(`admin-pane-${t}`);
    if (btn) {
      if (t === tabName) {
        btn.classList.add("active");
      } else {
        btn.classList.remove("active");
      }
    }
    if (pane) {
      if (t === tabName) {
        pane.classList.add("active");
      } else {
        pane.classList.remove("active");
      }
    }
  });

  lucide.createIcons();
}

function syncAdminEditorFieldsToMemory() {
  if (!currentEditingStudent) return;
  const sObj = currentEditingStudent.student || currentEditingStudent;

  // Profile
  currentEditingStudent.name = document.getElementById("admin-edit-name").value.trim();
  sObj.name = currentEditingStudent.name;
  currentEditingStudent.father_name = document.getElementById("admin-edit-father").value.trim();
  sObj.father_name = currentEditingStudent.father_name;
  currentEditingStudent.email = document.getElementById("admin-edit-email").value.trim();
  currentEditingStudent.branch = document.getElementById("admin-edit-branch").value.trim();
  sObj.branch = currentEditingStudent.branch;
  currentEditingStudent.programme_name = document.getElementById("admin-edit-programme").value.trim();
  sObj.programme_name = currentEditingStudent.programme_name;
  currentEditingStudent.semester = parseInt(document.getElementById("admin-edit-semester").value, 10) || 1;
  sObj.semester = currentEditingStudent.semester;
  currentEditingStudent.batch = document.getElementById("admin-edit-batch").value.trim();
  sObj.batch = currentEditingStudent.batch;
  currentEditingStudent.institution_name = document.getElementById("admin-edit-institution").value.trim();
  sObj.institution_name = currentEditingStudent.institution_name;
  currentEditingStudent.is_verified = document.getElementById("admin-edit-is-verified").checked;

  // Results
  if (!currentEditingStudent.overall) currentEditingStudent.overall = {};
  currentEditingStudent.overall.cgpa = parseFloat(document.getElementById("admin-edit-cgpa").value) || 0.0;
  currentEditingStudent.overall.percentage = parseFloat(document.getElementById("admin-edit-percentage").value) || 0.0;
  currentEditingStudent.overall.total_credits = parseInt(document.getElementById("admin-edit-credits").value, 10) || 0;

  // Attendance
  if (!currentEditingStudent.attendance) currentEditingStudent.attendance = { overall: {}, courses: [] };
  if (!currentEditingStudent.attendance.overall) currentEditingStudent.attendance.overall = {};
  currentEditingStudent.attendance.overall.percentage = parseFloat(document.getElementById("admin-edit-att-pct").value) || 0.0;
  currentEditingStudent.attendance.overall.present = parseInt(document.getElementById("admin-edit-att-present").value, 10) || 0;
  currentEditingStudent.attendance.overall.total = parseInt(document.getElementById("admin-edit-att-total").value, 10) || 0;
  currentEditingStudent.attendance.overall.bunk_buffer = parseInt(document.getElementById("admin-edit-att-margin").value, 10) || 0;
}

// 5. Semester & Paper Breakdown Renderers
function renderAdminEditorSemesters() {
  const container = document.getElementById("admin-editor-semesters-list");
  if (!container || !currentEditingStudent) return;

  const semesters = currentEditingStudent.semesters || [];

  if (!semesters.length) {
    container.innerHTML = `
      <div class="p-6 text-center rounded-2xl bg-zinc-900/40 border border-white/5 space-y-2">
        <p class="text-xs text-zinc-400">No semester results recorded yet.</p>
        <button type="button" onclick="addAdminEditorSemester()" class="px-3 py-1.5 rounded-lg bg-blue-600 text-white text-xs font-semibold">
          Add Semester 1
        </button>
      </div>
    `;
    return;
  }

  container.innerHTML = semesters.map((sem, semIdx) => {
    const semNum = sem.semester_number || sem.semester || (semIdx + 1);
    const sgpa = (sem.sgpa !== undefined ? sem.sgpa : 0.0).toFixed(2);
    const credits = sem.credits_secured || sem.credits || 25;
    const papers = sem.papers || [];

    return `
      <div class="p-4 sm:p-5 rounded-2xl bg-zinc-900/60 border border-white/10 space-y-4">
        <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-3 border-b border-white/5">
          <div class="flex items-center gap-3">
            <span class="px-2.5 py-1 rounded-lg bg-blue-500/10 text-blue-400 border border-blue-500/20 text-xs font-mono font-bold">
              Semester ${semNum}
            </span>
            <div class="flex items-center gap-2">
              <span class="text-xs text-zinc-400 font-mono">SGPA:</span>
              <input type="number" step="0.01" min="0" max="10" value="${sgpa}" onchange="updateSemesterSgpa(${semIdx}, this.value)" class="w-20 px-2 py-1 rounded-lg bg-zinc-950 border border-white/10 text-xs font-mono font-bold text-blue-400 focus:outline-none focus:border-red-500">
            </div>
            <div class="flex items-center gap-2">
              <span class="text-xs text-zinc-400 font-mono">Credits:</span>
              <input type="number" min="0" max="40" value="${credits}" onchange="updateSemesterCredits(${semIdx}, this.value)" class="w-16 px-2 py-1 rounded-lg bg-zinc-950 border border-white/10 text-xs font-mono font-bold text-white focus:outline-none focus:border-red-500">
            </div>
          </div>

          <div class="flex items-center gap-2">
            <button type="button" onclick="addAdminEditorSubject(${semIdx})" class="px-2.5 py-1 rounded-lg bg-zinc-800 hover:bg-zinc-700 text-zinc-200 text-xs font-medium flex items-center gap-1 transition-all">
              <i data-lucide="plus" class="w-3 h-3 text-emerald-400"></i>
              <span>Add Subject</span>
            </button>
            <button type="button" onclick="removeAdminEditorSemester(${semIdx})" class="p-1 rounded-lg text-zinc-400 hover:text-red-400 transition-all" title="Delete Semester">
              <i data-lucide="trash-2" class="w-3.5 h-3.5"></i>
            </button>
          </div>
        </div>

        <!-- Papers Table -->
        <div class="overflow-x-auto scrollbar-none">
          <table class="w-full text-left text-xs">
            <thead>
              <tr class="text-[10px] font-mono uppercase text-zinc-500 border-b border-white/5">
                <th class="pb-2 font-medium">Code</th>
                <th class="pb-2 font-medium">Paper Name</th>
                <th class="pb-2 font-medium text-center">Credits</th>
                <th class="pb-2 font-medium text-center">Marks</th>
                <th class="pb-2 font-medium text-center">Grade</th>
                <th class="pb-2 font-medium text-center">Status</th>
                <th class="pb-2 text-right">Action</th>
              </tr>
            </thead>
            <tbody class="divide-y divide-white/5">
              ${papers.map((p, pIdx) => `
                <tr class="hover:bg-white/[0.02]">
                  <td class="py-2 pr-2">
                    <input type="text" value="${p.paper_code || ''}" onchange="updatePaperField(${semIdx}, ${pIdx}, 'paper_code', this.value)" class="w-24 px-2 py-1 rounded-lg bg-zinc-950 border border-white/10 text-[11px] font-mono text-emerald-400">
                  </td>
                  <td class="py-2 pr-2">
                    <input type="text" value="${p.paper_title || p.paper_name || ''}" onchange="updatePaperField(${semIdx}, ${pIdx}, 'paper_title', this.value)" class="w-full min-w-[160px] px-2 py-1 rounded-lg bg-zinc-950 border border-white/10 text-[11px] text-zinc-200">
                  </td>
                  <td class="py-2 px-2 text-center">
                    <input type="number" min="0" max="10" value="${p.credits || 4}" onchange="updatePaperField(${semIdx}, ${pIdx}, 'credits', parseInt(this.value, 10))" class="w-12 px-1.5 py-1 text-center rounded-lg bg-zinc-950 border border-white/10 text-[11px] font-mono text-zinc-300">
                  </td>
                  <td class="py-2 px-2 text-center">
                    <input type="number" min="0" max="100" value="${p.total_marks || p.total || 80}" onchange="updatePaperField(${semIdx}, ${pIdx}, 'total_marks', parseFloat(this.value))" class="w-14 px-1.5 py-1 text-center rounded-lg bg-zinc-950 border border-white/10 text-[11px] font-mono font-bold text-white">
                  </td>
                  <td class="py-2 px-2 text-center">
                    <input type="text" value="${p.grade || 'A'}" onchange="updatePaperField(${semIdx}, ${pIdx}, 'grade', this.value.toUpperCase())" class="w-12 px-1.5 py-1 text-center rounded-lg bg-zinc-950 border border-white/10 text-[11px] font-mono font-bold text-blue-400">
                  </td>
                  <td class="py-2 px-2 text-center">
                    <select onchange="updatePaperField(${semIdx}, ${pIdx}, 'status', this.value)" class="px-2 py-1 rounded-lg bg-zinc-950 border border-white/10 text-[10px] font-mono text-zinc-300">
                      <option value="PASS" ${(p.status || 'PASS') === 'PASS' ? 'selected' : ''}>PASS</option>
                      <option value="FAIL" ${(p.status) === 'FAIL' ? 'selected' : ''}>FAIL</option>
                    </select>
                  </td>
                  <td class="py-2 text-right">
                    <button type="button" onclick="removeAdminEditorSubject(${semIdx}, ${pIdx})" class="p-1 text-zinc-500 hover:text-red-400 transition-all">
                      <i data-lucide="x" class="w-3.5 h-3.5"></i>
                    </button>
                  </td>
                </tr>
              `).join("")}
            </tbody>
          </table>
        </div>
      </div>
    `;
  }).join("");

  lucide.createIcons();
}

function updateSemesterSgpa(semIdx, val) {
  if (!currentEditingStudent || !currentEditingStudent.semesters) return;
  currentEditingStudent.semesters[semIdx].sgpa = parseFloat(val) || 0.0;
}

function updateSemesterCredits(semIdx, val) {
  if (!currentEditingStudent || !currentEditingStudent.semesters) return;
  currentEditingStudent.semesters[semIdx].credits_secured = parseInt(val, 10) || 0;
}

function updatePaperField(semIdx, pIdx, field, val) {
  if (!currentEditingStudent || !currentEditingStudent.semesters) return;
  const paper = currentEditingStudent.semesters[semIdx].papers[pIdx];
  if (!paper) return;
  paper[field] = val;
  if (field === 'paper_title') paper.paper_name = val;
}

function addAdminEditorSemester() {
  if (!currentEditingStudent) return;
  if (!currentEditingStudent.semesters) currentEditingStudent.semesters = [];
  const nextNum = currentEditingStudent.semesters.length + 1;
  currentEditingStudent.semesters.push({
    semester_number: nextNum,
    sgpa: 8.5,
    credits_secured: 25,
    papers: [
      { paper_code: `CS-${nextNum}01`, paper_title: "Core Subject 1", credits: 4, minor_marks: 20, major_marks: 60, total_marks: 80, grade: "A", status: "PASS" }
    ]
  });
  renderAdminEditorSemesters();
}

function removeAdminEditorSemester(semIdx) {
  if (!currentEditingStudent || !currentEditingStudent.semesters) return;
  currentEditingStudent.semesters.splice(semIdx, 1);
  renderAdminEditorSemesters();
}

function addAdminEditorSubject(semIdx) {
  if (!currentEditingStudent || !currentEditingStudent.semesters) return;
  const sem = currentEditingStudent.semesters[semIdx];
  if (!sem) return;
  if (!sem.papers) sem.papers = [];
  sem.papers.push({
    paper_code: `SUB-${sem.papers.length + 1}`,
    paper_title: "New Subject Course",
    credits: 4,
    minor_marks: 20,
    major_marks: 60,
    total_marks: 80,
    grade: "A",
    status: "PASS"
  });
  renderAdminEditorSemesters();
}

function removeAdminEditorSubject(semIdx, pIdx) {
  if (!currentEditingStudent || !currentEditingStudent.semesters) return;
  const sem = currentEditingStudent.semesters[semIdx];
  if (!sem || !sem.papers) return;
  sem.papers.splice(pIdx, 1);
  renderAdminEditorSemesters();
}

// 6. Course-wise Attendance Overrides
function renderAdminEditorCourses() {
  const container = document.getElementById("admin-editor-courses-list");
  if (!container || !currentEditingStudent) return;

  const att = currentEditingStudent.attendance || {};
  const courses = att.courses || [];

  if (!courses.length) {
    container.innerHTML = `
      <div class="p-6 text-center rounded-2xl bg-zinc-900/40 border border-white/5 space-y-2">
        <p class="text-xs text-zinc-400">No subject course attendance overrides recorded.</p>
        <button type="button" onclick="addAdminEditorCourse()" class="px-3 py-1.5 rounded-lg bg-emerald-600 text-white text-xs font-semibold">
          Add Subject Attendance
        </button>
      </div>
    `;
    return;
  }

  container.innerHTML = courses.map((c, idx) => `
    <div class="p-3.5 rounded-xl bg-zinc-900/60 border border-white/10 flex flex-col sm:flex-row sm:items-center justify-between gap-3">
      <div class="flex-1 min-w-0">
        <input type="text" value="${c.name || ''}" placeholder="Course Name" onchange="updateCourseField(${idx}, 'name', this.value)" class="w-full px-2.5 py-1.5 rounded-lg bg-zinc-950 border border-white/10 text-xs text-white">
      </div>

      <div class="flex items-center gap-2.5">
        <div class="flex items-center gap-1.5">
          <span class="text-[10px] font-mono text-zinc-400">Attended:</span>
          <input type="number" min="0" value="${c.present !== undefined ? c.present : 30}" onchange="updateCoursePresent(${idx}, this.value)" class="w-16 px-2 py-1 text-center rounded-lg bg-zinc-950 border border-white/10 text-xs font-mono font-bold text-white">
        </div>

        <div class="flex items-center gap-1.5">
          <span class="text-[10px] font-mono text-zinc-400">Total:</span>
          <input type="number" min="1" value="${c.total !== undefined ? c.total : 35}" onchange="updateCourseTotal(${idx}, this.value)" class="w-16 px-2 py-1 text-center rounded-lg bg-zinc-950 border border-white/10 text-xs font-mono font-bold text-zinc-300">
        </div>

        <div class="flex items-center gap-1.5">
          <span class="text-[10px] font-mono text-zinc-400">%</span>
          <input type="number" step="0.1" min="0" max="100" id="admin-course-pct-${idx}" value="${(c.percentage !== undefined ? c.percentage : 85.0).toFixed(1)}" onchange="updateCourseField(${idx}, 'percentage', parseFloat(this.value))" class="w-16 px-2 py-1 text-center rounded-lg bg-zinc-950 border border-white/10 text-xs font-mono font-bold text-emerald-400">
        </div>

        <button type="button" onclick="removeAdminEditorCourse(${idx})" class="p-1.5 text-zinc-400 hover:text-red-400 transition-all" title="Delete Course">
          <i data-lucide="trash-2" class="w-3.5 h-3.5"></i>
        </button>
      </div>
    </div>
  `).join("");

  lucide.createIcons();
}

function updateCourseField(idx, field, val) {
  if (!currentEditingStudent || !currentEditingStudent.attendance || !currentEditingStudent.attendance.courses) return;
  const course = currentEditingStudent.attendance.courses[idx];
  if (!course) return;
  course[field] = val;
}

function updateCoursePresent(idx, val) {
  if (!currentEditingStudent || !currentEditingStudent.attendance || !currentEditingStudent.attendance.courses) return;
  const course = currentEditingStudent.attendance.courses[idx];
  if (!course) return;
  course.present = parseInt(val, 10) || 0;
  if (course.total > 0) {
    course.percentage = parseFloat(((course.present / course.total) * 100).toFixed(1));
    const pctInput = document.getElementById(`admin-course-pct-${idx}`);
    if (pctInput) pctInput.value = course.percentage;
  }
}

function updateCourseTotal(idx, val) {
  if (!currentEditingStudent || !currentEditingStudent.attendance || !currentEditingStudent.attendance.courses) return;
  const course = currentEditingStudent.attendance.courses[idx];
  if (!course) return;
  course.total = parseInt(val, 10) || 1;
  if (course.total > 0) {
    course.percentage = parseFloat(((course.present / course.total) * 100).toFixed(1));
    const pctInput = document.getElementById(`admin-course-pct-${idx}`);
    if (pctInput) pctInput.value = course.percentage;
  }
}

function addAdminEditorCourse() {
  if (!currentEditingStudent) return;
  if (!currentEditingStudent.attendance) currentEditingStudent.attendance = { overall: {}, courses: [] };
  if (!currentEditingStudent.attendance.courses) currentEditingStudent.attendance.courses = [];
  currentEditingStudent.attendance.courses.push({
    name: "New Course Subject",
    code: "CIC-999",
    percentage: 85.0,
    present: 34,
    total: 40
  });
  renderAdminEditorCourses();
}

function removeAdminEditorCourse(idx) {
  if (!currentEditingStudent || !currentEditingStudent.attendance || !currentEditingStudent.attendance.courses) return;
  currentEditingStudent.attendance.courses.splice(idx, 1);
  renderAdminEditorCourses();
}

// 7. Format JSON & Save Changes
function formatAdminJsonEditor() {
  const jsonArea = document.getElementById("admin-edit-raw-json");
  if (!jsonArea) return;
  try {
    const parsed = JSON.parse(jsonArea.value);
    jsonArea.value = JSON.stringify(parsed, null, 2);
    currentEditingStudent = parsed;
    showToast("JSON formatted and validated successfully", "success", "JSON Valid");
  } catch (e) {
    showToast("Invalid JSON syntax: " + e.message, "error", "JSON Parse Error");
  }
}

async function saveAdminStudentChanges() {
  if (!currentEditingStudent || !currentEditingStudentRoll) return;

  const btn = document.getElementById("btn-admin-save-student");
  if (btn) {
    btn.disabled = true;
    btn.innerHTML = `<i data-lucide="loader-2" class="w-3.5 h-3.5 animate-spin"></i><span>Saving to Database...</span>`;
    lucide.createIcons();
  }

  // If active tab is raw JSON, parse it
  const activeTab = document.querySelector(".admin-editor-tab-btn.active");
  const isJsonTab = activeTab && activeTab.id === "admin-tab-btn-json";

  if (isJsonTab) {
    try {
      const jsonText = document.getElementById("admin-edit-raw-json").value;
      currentEditingStudent = JSON.parse(jsonText);
    } catch (err) {
      showToast("Invalid JSON syntax: " + err.message, "error", "JSON Parse Error");
      if (btn) {
        btn.disabled = false;
        btn.innerHTML = `<i data-lucide="save" class="w-3.5 h-3.5"></i><span>Save & Apply Changes</span>`;
        lucide.createIcons();
      }
      return;
    }
  } else {
    syncAdminEditorFieldsToMemory();
  }

  currentEditingStudent.roll_number = currentEditingStudentRoll;

  try {
    const res = await fetch("/api/admin/student/update", {
      method: "POST",
      headers: getAdminAuthHeaders(),
      body: JSON.stringify(currentEditingStudent)
    });
    const data = await res.json();

    if (res.ok && data.status === "success") {
      showToast(`Student ${currentEditingStudentRoll} record updated in database!`, "success", "Database Synchronized");
      
      // Update local user state if this student is currently active
      if (state.currentStudent && state.currentStudent.student && state.currentStudent.student.roll_number === currentEditingStudentRoll) {
        state.currentStudent = data.student;
        if (state.activeTab === "results") {
          renderOfficialMarksheet(data.student, "all");
        }
      }
      if (state.currentUser && state.currentUser.roll_number === currentEditingStudentRoll) {
        if (currentEditingStudent.name) state.currentUser.name = currentEditingStudent.name;
        if (currentEditingStudent.is_verified !== undefined) state.currentUser.is_verified = currentEditingStudent.is_verified;
      }

      closeAdminStudentEditorModal();
      loadAdminRoster(true);
    } else {
      showToast(data.message || "Failed to save student changes.", "error", "Database Error");
    }
  } catch (err) {
    console.error("Save student error:", err);
    showToast("Network error while saving changes.", "error", "Save Failure");
  } finally {
    if (btn) {
      btn.disabled = false;
      btn.innerHTML = `<i data-lucide="save" class="w-3.5 h-3.5"></i><span>Save & Apply Changes</span>`;
      lucide.createIcons();
    }
  }
}

async function deleteAdminStudentRecord() {
  if (!currentEditingStudentRoll) return;

  const confirmed = confirm(`Are you sure you want to permanently delete student ${currentEditingStudentRoll}? This action cannot be undone.`);
  if (!confirmed) return;

  try {
    const res = await fetch("/api/admin/student/delete", {
      method: "POST",
      headers: getAdminAuthHeaders(),
      body: JSON.stringify({ roll_number: currentEditingStudentRoll })
    });
    const data = await res.json();

    if (res.ok && data.status === "success") {
      showToast(`Student ${currentEditingStudentRoll} deleted from database.`, "info", "Record Removed");
      closeAdminStudentEditorModal();
      loadAdminRoster(true);
    } else {
      showToast(data.message || "Failed to delete student record.", "error", "Delete Error");
    }
  } catch (err) {
    console.error("Delete student error:", err);
    showToast("Network error while deleting student.", "error", "Delete Failure");
  }
}

// 8. Create Student Modal Controller
function openCreateStudentModal() {
  const modal = document.getElementById("admin-create-student-modal");
  if (modal) modal.classList.remove("hidden");
}

function closeCreateStudentModal() {
  const modal = document.getElementById("admin-create-student-modal");
  if (modal) modal.classList.add("hidden");
}

async function submitCreateStudent(event) {
  if (event) event.preventDefault();
  const roll = document.getElementById("admin-create-roll").value.trim();
  const name = document.getElementById("admin-create-name").value.trim();
  const father = document.getElementById("admin-create-father").value.trim();
  const email = document.getElementById("admin-create-email").value.trim();
  const branch = document.getElementById("admin-create-branch").value.trim();
  const semester = parseInt(document.getElementById("admin-create-semester").value, 10) || 3;
  const cgpa = parseFloat(document.getElementById("admin-create-cgpa").value) || 8.5;
  const attendance = parseFloat(document.getElementById("admin-create-attendance").value) || 85.0;

  if (!roll || !name) {
    showToast("Enrollment number and name are required.", "error", "Validation Error");
    return;
  }

  const btn = document.getElementById("btn-admin-create-submit");
  if (btn) {
    btn.disabled = true;
    btn.innerHTML = `<i data-lucide="loader-2" class="w-3.5 h-3.5 animate-spin"></i><span>Creating...</span>`;
    lucide.createIcons();
  }

  const payload = {
    roll_number: roll,
    name: name,
    father_name: father || "N/A",
    email: email,
    branch: branch,
    semester: semester,
    overall: {
      cgpa: cgpa,
      percentage: cgpa * 9.5,
      total_credits: 50
    },
    attendance: {
      overall: {
        percentage: attendance,
        present: Math.round(attendance),
        total: 100,
        bunk_buffer: 5
      },
      courses: [
        { name: `${branch} Core Engineering`, percentage: attendance, present: Math.round(attendance * 0.4), total: 40 }
      ]
    }
  };

  try {
    const res = await fetch("/api/admin/student/create", {
      method: "POST",
      headers: getAdminAuthHeaders(),
      body: JSON.stringify(payload)
    });
    const data = await res.json();

    if (res.ok && data.status === "success") {
      showToast(`Student ${name} (${roll}) created successfully!`, "success", "Student Registered");
      closeCreateStudentModal();
      loadAdminRoster(true);
    } else {
      showToast(data.message || "Failed to create student.", "error", "Registration Error");
    }
  } catch (err) {
    console.error("Create student error:", err);
    showToast("Network error creating student record.", "error", "Creation Failure");
  } finally {
    if (btn) {
      btn.disabled = false;
      btn.innerHTML = `<i data-lucide="check" class="w-3.5 h-3.5"></i><span>Create Student</span>`;
      lucide.createIcons();
    }
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

function openSignInGatekeeper() {
  const overlay = document.getElementById("signin-gatekeeper-overlay");
  if (overlay) {
    overlay.classList.remove("hidden");
    lucide.createIcons();
  }
}

function closeSignInGatekeeper() {
  const overlay = document.getElementById("signin-gatekeeper-overlay");
  if (overlay) {
    overlay.classList.add("hidden");
  }
}

async function fetchCurrentUser() {
  try {
    const headers = {};
    if (state.sessionToken) {
      headers["Authorization"] = `Bearer ${state.sessionToken}`;
    }

    const res = await fetch("/api/auth/me", {
      credentials: "same-origin",
      headers: headers
    });

    if (res.status === 401) {
      console.warn("Session expired after 30 days inactivity (HTTP 401). Clearing session.");
      clearClientSession();
      return;
    }

    if (!res.ok) {
      // 500, 502, 503, etc.: Server cold start or transient glitch.
      // Do NOT log the student out!
      console.warn(`Auth check returned HTTP ${res.status}; preserving cached session.`);
      return;
    }

    const data = await res.json();
    if (data.status === "success" && data.is_authenticated && data.user) {
      state.currentUser = data.user;
      state.currentStudent = data.student;
      if (data.user.session_token) {
        state.sessionToken = data.user.session_token;
        localStorage.setItem("campusiq_session_token", data.user.session_token);
      }
      localStorage.setItem("campusiq_cached_user", JSON.stringify(data.user));
      if (data.student) {
        localStorage.setItem("campusiq_cached_student", JSON.stringify(data.student));
      }
      closeSignInGatekeeper();
      renderHeaderAuth(data.user, data.student);
      populateMyProfileUI(data.user, data.student);
    } else {
      clearClientSession();
    }
  } catch (err) {
    console.warn("Auth check network error (offline or server waking up); preserving local session:", err);
    if (!state.currentUser) {
      openSignInGatekeeper();
    }
  }
}

function clearClientSession() {
  localStorage.removeItem("campusiq_session_token");
  localStorage.removeItem("campusiq_cached_user");
  localStorage.removeItem("campusiq_cached_student");
  state.sessionToken = null;
  state.currentUser = null;
  state.currentStudent = null;
  renderHeaderAuth(null, null);
  populateMyProfileUI(null, null);
  openSignInGatekeeper();
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

  const avatarSrc = user.avatar_url || (student && student.profile && student.profile.avatar_url) || `https://api.dicebear.com/7.x/bottts/svg?seed=${encodeURIComponent(user.name)}`;
  if (avatar) avatar.src = avatarSrc;
  if (name) name.innerText = user.name;
  if (email) email.innerText = user.email;

  const verifiedBanner = document.getElementById("my-profile-verified-banner");
  const unlinkedBanner = document.getElementById("my-profile-unlinked-banner");
  const rollDisplay = document.getElementById("profile-verified-roll-display");

  const isVerified = Boolean((user.is_verified || (student && student.roll_number)) && (user.roll_number || (student && student.roll_number)));
  const rollNum = user.roll_number || (student && student.roll_number);

  if (isVerified && rollNum) {
    if (verifiedBanner) verifiedBanner.classList.remove("hidden");
    if (unlinkedBanner) unlinkedBanner.classList.add("hidden");
    if (rollDisplay) rollDisplay.innerText = rollNum;
    if (sub) sub.innerText = `Roll: ${rollNum} • MAIT ${user.branch || (student && student.programme_name ? student.programme_name.split(' ')[0] : 'CSE')}`;
  } else {
    if (verifiedBanner) verifiedBanner.classList.add("hidden");
    if (unlinkedBanner) unlinkedBanner.classList.remove("hidden");
    if (sub) sub.innerText = "Roll Number Not Verified";
  }

  if (student) {
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

      closeSignInGatekeeper();
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

      closeSignInGatekeeper();
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

// Switch between Auth Tabs (Deprecated - Google Sign-In Only)
function switchAuthTab(tab) {
  // Pure Google Sign-In enforced
}

// Handle Form Submission: Password Auth Disabled
async function handleAuthSubmit(e) {
  if (e) e.preventDefault();
  showToast("ID & password sign-in is disabled. Please continue with Google Sign-In.");
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

  clearClientSession();
  showToast("You have been signed out successfully.", "info", "Signed Out");
}

function handleLinkRollNumber() {
  openEdumarshalVerifyModal();
}

function openEdumarshalVerifyModal() {
  const modal = document.getElementById("edumarshal-verify-modal");
  if (!modal) return;
  const errBox = document.getElementById("edu-verify-error");
  if (errBox) errBox.classList.add("hidden");
  modal.classList.add("open");
  lucide.createIcons();
}

function closeEdumarshalVerifyModal() {
  const modal = document.getElementById("edumarshal-verify-modal");
  if (modal) modal.classList.remove("open");
}

function closeEdumarshalVerifyModalOnBackdrop(e) {
  if (e.target.id === "edumarshal-verify-modal") {
    closeEdumarshalVerifyModal();
  }
}

async function submitEdumarshalVerification(e) {
  if (e) e.preventDefault();
  const uInput = document.getElementById("edu-input-username");
  const pInput = document.getElementById("edu-input-password");
  const errBox = document.getElementById("edu-verify-error");
  const errMsg = document.getElementById("edu-verify-error-msg");
  const btn = document.getElementById("btn-submit-edu-verify");
  const btnText = document.getElementById("btn-edu-verify-text");

  const username = uInput ? uInput.value.trim() : "";
  const password = pInput ? pInput.value.trim() : "";

  if (!username || !password) {
    if (errBox && errMsg) {
      errMsg.innerText = "Please provide both Edumarshal username and password.";
      errBox.classList.remove("hidden");
    }
    return;
  }

  if (errBox) errBox.classList.add("hidden");
  if (btn) btn.disabled = true;
  if (btnText) btnText.innerHTML = `<i data-lucide="loader-2" class="w-4 h-4 animate-spin inline-block mr-1"></i> Verifying with Edumarshal ERP...`;
  lucide.createIcons();

  try {
    const res = await fetch("/api/edumarshal/verify-and-link", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "Authorization": `Bearer ${state.sessionToken}`
      },
      body: JSON.stringify({ username, password })
    });
    const data = await res.json();

    if (data.status === "success") {
      showToast(`🎉 Identity verified! Roll Number ${data.roll_number} auto-filled and locked.`);
      closeEdumarshalVerifyModal();
      
      if (state.currentUser) {
        state.currentUser.is_verified = true;
        state.currentUser.roll_number = data.roll_number;
        state.currentUser.has_edumarshal = true;
      }

      await fetchCurrentUser();
      await fetchAttendance(true);
      await fetchAttendanceCalendar(true);
    } else {
      if (errBox && errMsg) {
        errMsg.innerText = data.message || "Edumarshal verification failed. Please check your credentials.";
        errBox.classList.remove("hidden", "toast-shake");
        void errBox.offsetWidth;
        errBox.classList.add("toast-shake");
        if (window.lucide && typeof window.lucide.createIcons === "function") {
          window.lucide.createIcons();
        }
      }
      showToast(data.message || "Edumarshal verification failed", "error", "Verification Rejected");
    }
  } catch (err) {
    if (errBox && errMsg) {
      errMsg.innerText = err.message || "Network error communicating with verification backend.";
      errBox.classList.remove("hidden", "toast-shake");
      void errBox.offsetWidth;
      errBox.classList.add("toast-shake");
      if (window.lucide && typeof window.lucide.createIcons === "function") {
        window.lucide.createIcons();
      }
    }
    showToast("Network error during verification", "error", "Connection Failed");
  } finally {
    if (btn) btn.disabled = false;
    if (btnText) btnText.innerText = "Verify & Auto-Fill Enrollment";
    lucide.createIcons();
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

let toastTimeout = null;

function showToast(msgOrOpts, type = "info", title = null, duration = 3500) {
  let message = "";
  if (typeof msgOrOpts === "object" && msgOrOpts !== null) {
    message = msgOrOpts.message || "";
    type = msgOrOpts.type || type || "info";
    title = msgOrOpts.title || title;
    duration = msgOrOpts.duration || duration || 3500;
  } else {
    message = String(msgOrOpts || "");
  }

  // Auto-detect alert type if default "info" was provided
  const lowerMsg = message.toLowerCase();
  if (type === "info") {
    if (lowerMsg.includes("fail") || lowerMsg.includes("error") || lowerMsg.includes("rejected") || lowerMsg.includes("denied") || lowerMsg.includes("disabled") || lowerMsg.includes("could not") || lowerMsg.includes("invalid") || message.includes("❌")) {
      type = "error";
    } else if (lowerMsg.includes("warning") || lowerMsg.includes("caution") || lowerMsg.includes("reconnecting") || lowerMsg.includes("wait") || lowerMsg.includes("timeout") || message.includes("⚠️")) {
      type = "warning";
    } else if (lowerMsg.includes("success") || lowerMsg.includes("verified") || lowerMsg.includes("approved") || lowerMsg.includes("saved") || lowerMsg.includes("loaded") || lowerMsg.includes("generated") || message.includes("✅") || message.includes("🎉") || message.includes("⚡")) {
      type = "success";
    }
  }

  // Auto-infer title if omitted
  if (!title) {
    switch (type) {
      case "error":
        title = "Action Failed";
        break;
      case "warning":
        title = "Attention Required";
        break;
      case "success":
        title = "Operation Successful";
        break;
      default:
        title = "CampusIQ Notification";
        break;
    }
  }

  const toast = document.getElementById("toast");
  const msgEl = document.getElementById("toast-msg");
  const titleEl = document.getElementById("toast-title");
  const iconWrap = document.getElementById("toast-icon-wrap");
  if (!toast || !msgEl) return;

  msgEl.innerText = message;
  if (titleEl) titleEl.innerText = title;

  // Reset classes
  toast.classList.remove("toast-error", "toast-warning", "toast-success", "toast-info", "toast-shake");
  void toast.offsetWidth; // Trigger reflow

  // Configure theme & Lucide icon
  if (type === "error") {
    toast.classList.add("toast-error", "toast-shake");
    if (iconWrap) {
      iconWrap.className = "shrink-0 w-7 h-7 rounded-xl flex items-center justify-center bg-red-500/15 text-red-400 border border-red-500/30";
      iconWrap.innerHTML = `<i data-lucide="alert-circle" class="w-4 h-4"></i>`;
    }
  } else if (type === "warning") {
    toast.classList.add("toast-warning");
    if (iconWrap) {
      iconWrap.className = "shrink-0 w-7 h-7 rounded-xl flex items-center justify-center bg-amber-500/15 text-amber-400 border border-amber-500/30";
      iconWrap.innerHTML = `<i data-lucide="alert-triangle" class="w-4 h-4"></i>`;
    }
  } else if (type === "success") {
    toast.classList.add("toast-success");
    if (iconWrap) {
      iconWrap.className = "shrink-0 w-7 h-7 rounded-xl flex items-center justify-center bg-emerald-500/15 text-emerald-400 border border-emerald-500/30";
      iconWrap.innerHTML = `<i data-lucide="check-circle-2" class="w-4 h-4"></i>`;
    }
  } else {
    toast.classList.add("toast-info");
    if (iconWrap) {
      iconWrap.className = "shrink-0 w-7 h-7 rounded-xl flex items-center justify-center bg-blue-500/15 text-blue-400 border border-blue-500/30";
      iconWrap.innerHTML = `<i data-lucide="info" class="w-4 h-4"></i>`;
    }
  }

  if (window.lucide && typeof window.lucide.createIcons === "function") {
    window.lucide.createIcons();
  }

  toast.classList.add("show");

  if (toastTimeout) clearTimeout(toastTimeout);
  toastTimeout = setTimeout(() => {
    dismissToast();
  }, duration);
}

function dismissToast() {
  const toast = document.getElementById("toast");
  if (toast) {
    toast.classList.remove("show");
  }
}

// Reusable Dark Obsidian Linear Error Card
function renderCustomErrorCard(options) {
  const {
    icon = "alert-triangle",
    title = "Data Retrieval Interrupted",
    message = "An unexpected error occurred while communicating with the service.",
    actionText = "Try Again",
    actionFn = null,
    secondaryText = null,
    secondaryFn = null
  } = options || {};

  return `
    <div class="col-span-full p-8 text-center rounded-3xl custom-error-card space-y-4 my-2">
      <div class="w-12 h-12 mx-auto rounded-2xl bg-red-500/10 border border-red-500/20 text-red-400 flex items-center justify-center shadow-[0_0_20px_rgba(239,68,68,0.2)]">
        <i data-lucide="${escapeHtml(icon)}" class="w-6 h-6"></i>
      </div>
      <div class="max-w-md mx-auto space-y-1.5">
        <h4 class="text-sm font-bold text-white tracking-tight">${escapeHtml(title)}</h4>
        <p class="text-xs text-zinc-400 leading-relaxed">${escapeHtml(message)}</p>
      </div>
      ${(actionText && actionFn) || (secondaryText && secondaryFn) ? `
        <div class="flex items-center justify-center gap-2 pt-2">
          ${actionText && actionFn ? `
            <button onclick="${escapeHtml(actionFn)}" class="px-4 py-2 rounded-xl bg-red-500/20 hover:bg-red-500/30 text-red-300 border border-red-500/30 font-semibold text-xs transition-all flex items-center gap-1.5 shadow-[0_0_12px_rgba(239,68,68,0.2)]">
              <i data-lucide="rotate-cw" class="w-3.5 h-3.5"></i>
              <span>${escapeHtml(actionText)}</span>
            </button>
          ` : ""}
          ${secondaryText && secondaryFn ? `
            <button onclick="${escapeHtml(secondaryFn)}" class="px-4 py-2 rounded-xl bg-zinc-900 hover:bg-zinc-800 text-zinc-300 border border-white/10 font-semibold text-xs transition-all flex items-center gap-1.5">
              <span>${escapeHtml(secondaryText)}</span>
            </button>
          ` : ""}
        </div>
      ` : ""}
    </div>
  `;
}
