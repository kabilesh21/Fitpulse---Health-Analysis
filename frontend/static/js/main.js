// FitPulse — main.js
let reportHRChartObj = null;

const getThemeColors = () => {
  const isDark = document.documentElement.getAttribute("data-theme") === "dark";
  return {
    grid: isDark ? "rgba(255, 255, 255, 0.05)" : "rgba(15, 23, 42, 0.05)",
    text: isDark ? "#9ca3af" : "#475569",
    blue: "#0284c7",
    green: "#0d9488",
    red: "#e11d48"
  };
};

function handleLockedClick(e) {
  const currentSession = localStorage.getItem("fitpulse-session-id");
  const currentParams = new URLSearchParams(window.location.search);
  const currentPatId = currentParams.get('patient_id');
  if (currentSession || currentPatId) {
    return; // Allow navigation
  }
  e.preventDefault();
  showToast("⚠️ Access Locked: Please upload the CSV or Excel sheet file! 🩺", "error");
}

document.addEventListener("DOMContentLoaded", () => {
  checkProtocol();
  setupTheme();
  setupNavigation();
  checkNavigationLocks();
  syncSessionFromDatabase();
  setupGlobalChatWidget();

  // Page Refresh Dataset Clear Prompt
  const isReload = (window.performance && window.performance.navigation && window.performance.navigation.type === 1) ||
                    (window.performance && window.performance.getEntriesByType && window.performance.getEntriesByType('navigation')[0] && window.performance.getEntriesByType('navigation')[0].type === 'reload');
  if (isReload) {
    const hasSession = localStorage.getItem("fitpulse-session-id");
    const isDoctor = document.body.getAttribute('data-user-role') === 'doctor';
    if (hasSession && !isDoctor) {
      if (confirm("Can I clear the dataset?")) {
        const urlParams = new URLSearchParams(window.location.search);
        const patientId = urlParams.get('patient_id');
        const payload = {};
        if (patientId) payload.patient_id = patientId;
        
        fetch('/api/clear_data', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload)
        })
        .then(() => {
          localStorage.removeItem("fitpulse-session-id");
          localStorage.removeItem("fitpulse-filename");
          localStorage.removeItem("fitpulse-report");
          localStorage.removeItem("fitpulse-records");
          const cleanUrl = window.location.pathname + (patientId ? `?patient_id=${patientId}` : '');
          window.location.href = cleanUrl;
        });
      }
    }
  }

  // Intercept all logout clicks to prompt for dataset clearing
  document.querySelectorAll('a[href="/logout"]').forEach(el => {
    el.addEventListener('click', (e) => {
      const hasSession = localStorage.getItem("fitpulse-session-id");
      const isDoctor = document.body.getAttribute('data-user-role') === 'doctor';
      if (hasSession && !isDoctor) {
        e.preventDefault();
        if (confirm("Can I clear the dataset?")) {
          const urlParams = new URLSearchParams(window.location.search);
          const patientId = urlParams.get('patient_id');
          const payload = {};
          if (patientId) payload.patient_id = patientId;
          
          fetch('/api/clear_data', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
          })
          .finally(() => {
            localStorage.removeItem("fitpulse-session-id");
            localStorage.removeItem("fitpulse-filename");
            localStorage.removeItem("fitpulse-report");
            localStorage.removeItem("fitpulse-records");
            window.location.href = '/logout';
          });
        } else {
          localStorage.removeItem("fitpulse-session-id");
          localStorage.removeItem("fitpulse-filename");
          localStorage.removeItem("fitpulse-report");
          localStorage.removeItem("fitpulse-records");
          window.location.href = '/logout';
        }
      }
    });
  });
  
  // Route matching
  const path = window.location.pathname;
  if (path === "/" || path === "/index.html") {
    // Landing page effects
  } else if (path === "/upload" || path.endsWith("/upload")) {
    setupUploadPage();
  } else if (path === "/dashboard" || path.endsWith("/dashboard")) {
    setupDashboardPage();
  } else if (path === "/report" || path.endsWith("/report")) {
    setupReportPage();
  } else if (path === "/about" || path.endsWith("/about")) {
    setupAboutPage();
  }
});

function syncSessionFromDatabase() {
  const urlParams = new URLSearchParams(window.location.search);
  const patientId = urlParams.get('patient_id');
  
  const fetchUrl = patientId ? `/api/session_check?patient_id=${patientId}` : `/api/session_check`;
  
  fetch(fetchUrl)
    .then(res => res.json())
    .then(data => {
      if (data.logged_in && data.has_data) {
        localStorage.setItem("fitpulse-session-id", data.session_id);
        localStorage.setItem("fitpulse-filename", data.filename);
        localStorage.setItem("fitpulse-report", JSON.stringify(data.report));
        localStorage.setItem("fitpulse-records", JSON.stringify(data.records));
        
        checkNavigationLocks();
        
        const nameEl = document.getElementById("dash-patient-name");
        if (nameEl && data.username) {
          nameEl.textContent = data.username;
        }
        const linkEl = document.getElementById("btn-doc-report-link");
        if (linkEl && patientId) {
          linkEl.setAttribute("href", `/report?patient_id=${patientId}`);
        }
        const uploadEl = document.getElementById("btn-doc-upload-link");
        if (uploadEl && patientId) {
          uploadEl.setAttribute("href", `/upload?patient_id=${patientId}`);
        }
        
        const path = window.location.pathname;
        if (path === "/dashboard" || path.endsWith("/dashboard")) {
          setupDashboardPage();
        } else if (path === "/report" || path.endsWith("/report")) {
          setupReportPage();
        }
      } else {
        // No active session data from server — clear stale localStorage to re-lock the interface
        localStorage.clear();
        checkNavigationLocks();
      }
    })
    .catch(err => {
      console.error("Session sync failed:", err);
      checkNavigationLocks();
    });
}

/* ── PROTOCOL CHECKER ────────────────────────────────────────────────────── */
function checkProtocol() {
  if (window.location.protocol === "file:") {
    const warning = document.createElement("div");
    warning.className = "protocol-warning";
    warning.innerHTML = `
      <span>🏥 <strong>Vitals Link Error:</strong> You have opened this page directly as a local file (<code>file://</code> protocol). AJAX file transmissions are blocked by browser security. Please launch <strong>runproject.bat</strong> and go to <a href="http://127.0.0.1:5000" target="_blank">http://127.0.0.1:5000</a> to run the analysis! 💉</span>
    `;
    document.body.insertBefore(warning, document.body.firstChild);
    
    // Inject CSS warning style if not already parsed
    const style = document.createElement("style");
    style.innerHTML = `
      .protocol-warning {
        background: #ffedd5 !important;
        border-bottom: 2px solid #ea580c !important;
        color: #c2410c !important;
        padding: 14px 2rem !important;
        text-align: center !important;
        font-size: 14px !important;
        font-weight: 700 !important;
        display: flex !important;
        align-items: center !important;
        justify-content: center !important;
        gap: 10px !important;
        z-index: 99999 !important;
        position: relative !important;
      }
    `;
    document.head.appendChild(style);
  }
}

/* ── THEME SWITCHER ──────────────────────────────────────────────────────── */
function setupTheme() {
  const themeToggle = document.getElementById("theme-toggle");
  const sunIcon = document.querySelector(".sun-icon");
  const moonIcon = document.querySelector(".moon-icon");
  
  // Hospital theme defaults to "light" mode for bright sterile aesthetic
  let currentTheme = localStorage.getItem("fitpulse-theme") || "light";
  document.documentElement.setAttribute("data-theme", currentTheme);
  updateThemeIcons(currentTheme);
  
  if (themeToggle) {
    themeToggle.addEventListener("click", () => {
      let targetTheme = document.documentElement.getAttribute("data-theme") === "dark" ? "light" : "dark";
      document.documentElement.setAttribute("data-theme", targetTheme);
      localStorage.setItem("fitpulse-theme", targetTheme);
      updateThemeIcons(targetTheme);
      
      // Dispatch event to redraw charts
      window.dispatchEvent(new Event("themechanged"));
    });
  }
  
  function updateThemeIcons(theme) {
    if (!sunIcon || !moonIcon) return;
    if (theme === "light") {
      sunIcon.classList.add("hidden");
      moonIcon.classList.remove("hidden");
    } else {
      sunIcon.classList.remove("hidden");
      moonIcon.classList.add("hidden");
    }
  }
}

/* ── NAVIGATION ──────────────────────────────────────────────────────────── */
function setupNavigation() {
  const hamburger = document.getElementById("nav-hamburger");
  const mobileMenu = document.getElementById("mobile-menu");
  
  if (hamburger && mobileMenu) {
    hamburger.addEventListener("click", () => {
      mobileMenu.classList.toggle("open");
    });
  }
  
  // Highlight active link
  const path = window.location.pathname;
  const navLinks = {
    "/": "nav-home",
    "/services": "nav-services",
    "/upload": "nav-upload",
    "/dashboard": "nav-dashboard",
    "/report": "nav-report",
    "/about": "nav-about"
  };
  
  Object.keys(navLinks).forEach(key => {
    if (path === key || path.endsWith(key)) {
      const activeEl = document.getElementById(navLinks[key]);
      if (activeEl) activeEl.classList.add("active");
    }
  });
}

/* ── NAVIGATION LOCKS & TOASTS ───────────────────────────────────────────── */
function checkNavigationLocks() {
  const urlParams = new URLSearchParams(window.location.search);
  const patientId = urlParams.get('patient_id');
  
  if (patientId) {
    document.querySelectorAll('.patient-context-link').forEach(el => {
      el.classList.remove('hidden');
      const link = el.querySelector('a');
      const id = link.getAttribute('id');
      if (id === 'nav-upload') link.setAttribute('href', `/upload?patient_id=${patientId}`);
      if (id === 'nav-dashboard') link.setAttribute('href', `/dashboard?patient_id=${patientId}`);
      if (id === 'nav-report') link.setAttribute('href', `/report?patient_id=${patientId}`);
    });
  }

  const sessionId = localStorage.getItem("fitpulse-session-id");
  const dashboardLink = document.getElementById("nav-dashboard");
  const reportLink = document.getElementById("nav-report");
  const clearBtn = document.getElementById("btn-clear-session");
  
  // Also get mobile menu links
  const mobileLinks = document.querySelectorAll(".mobile-link");
  let mobileDashLink = null;
  let mobileReportLink = null;
  
  mobileLinks.forEach(link => {
    const href = link.getAttribute("href");
    if (href === "/dashboard" || href.endsWith("/dashboard")) {
      mobileDashLink = link;
    }
    if (href === "/report" || href.endsWith("/report")) {
      mobileReportLink = link;
    }
  });

  const isUnlocked = !!(sessionId || patientId);

  if (isUnlocked) {
    if (dashboardLink) {
      dashboardLink.classList.remove("locked-link");
      dashboardLink.removeEventListener("click", handleLockedClick);
    }
    if (reportLink) {
      reportLink.classList.remove("locked-link");
      reportLink.removeEventListener("click", handleLockedClick);
    }
    if (mobileDashLink) {
      mobileDashLink.classList.remove("locked-link");
      mobileDashLink.removeEventListener("click", handleLockedClick);
    }
    if (mobileReportLink) {
      mobileReportLink.classList.remove("locked-link");
      mobileReportLink.removeEventListener("click", handleLockedClick);
    }

    if (clearBtn) {
      clearBtn.classList.remove("hidden");
      clearBtn.onclick = (e) => {
        e.preventDefault();
        if (!confirm("Are you sure you want to permanently clear this patient's records from the database?")) {
          return;
        }
        
        const payload = {};
        if (patientId) {
          payload.patient_id = patientId;
        }
        
        fetch('/api/clear_data', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload)
        })
        .then(res => res.json())
        .then(data => {
          if (data.success) {
            localStorage.removeItem("fitpulse-session-id");
            localStorage.removeItem("fitpulse-filename");
            localStorage.removeItem("fitpulse-report");
            localStorage.removeItem("fitpulse-records");
            
            showToast("🗑️ Patient Session Cleared: Vitals diagnostics locked! 🔒", "success");
            clearBtn.classList.add("hidden");
            
            setTimeout(() => {
              const redirectUrl = patientId ? `/upload?patient_id=${patientId}` : '/upload';
              window.location.href = redirectUrl;
            }, 800);
          } else {
            showToast("❌ Failed to clear database dataset.", "error");
          }
        })
        .catch(err => {
          console.error(err);
          showToast("❌ Connection error while clearing dataset.", "error");
        });
      };
    }
  } else {
    if (clearBtn) {
      clearBtn.classList.add("hidden");
    }

    if (dashboardLink) {
      dashboardLink.classList.add("locked-link");
      dashboardLink.addEventListener("click", handleLockedClick);
    }
    if (reportLink) {
      reportLink.classList.add("locked-link");
      reportLink.addEventListener("click", handleLockedClick);
    }
    if (mobileDashLink) {
      mobileDashLink.classList.add("locked-link");
      mobileDashLink.addEventListener("click", handleLockedClick);
    }
    if (mobileReportLink) {
      mobileReportLink.classList.add("locked-link");
      mobileReportLink.addEventListener("click", handleLockedClick);
    }
  }
}

function showToast(message, type = "info") {
  let container = document.querySelector(".toast-container");
  if (!container) {
    container = document.createElement("div");
    container.className = "toast-container";
    document.body.appendChild(container);
  }
  
  const toast = document.createElement("div");
  toast.className = `toast toast-${type}`;
  
  let icon = "💡";
  if (type === "error" || type === "warning") icon = "⚠️";
  else if (type === "success") icon = "✅";
  
  toast.innerHTML = `
    <span class="toast-icon" style="font-size: 20px;">${icon}</span>
    <span class="toast-message" style="font-weight: 700; font-size: 13.5px; line-height: 1.4;">${message}</span>
    <div class="toast-progress-bar"></div>
  `;
  
  container.appendChild(toast);
  
  // Slide out after 3.8s
  setTimeout(() => {
    toast.style.animation = "toast-out 0.4s cubic-bezier(0.175, 0.885, 0.32, 1.275) forwards";
    
    // Fallback style for toast-out animation if not in CSS
    const style = document.createElement("style");
    style.innerHTML = `
      @keyframes toast-out {
        from { transform: translateX(0) scale(1); opacity: 1; }
        to { transform: translateX(120%) scale(0.9); opacity: 0; }
      }
    `;
    document.head.appendChild(style);

    toast.addEventListener("animationend", () => {
      toast.remove();
      if (container.children.length === 0) {
        container.remove();
      }
    });
  }, 3800);
}

/* ── UPLOAD PAGE LOGIC ───────────────────────────────────────────────────── */
function setupUploadPage() {
  const dropzone = document.getElementById("dropzone");
  const fileInput = document.getElementById("file-input");
  const filePreview = document.getElementById("file-preview-card");
  const fpName = document.getElementById("fp-name");
  const fpSize = document.getElementById("fp-size");
  const fpRemove = document.getElementById("fp-remove");
  const progressWrapper = document.getElementById("progress-wrapper");
  const progressBar = document.getElementById("progress-bar");
  const progressPercent = document.getElementById("progress-percent");
  const errorAlert = document.getElementById("error-alert");
  const errorMessage = document.getElementById("error-message");
  const btnAnalyze = document.getElementById("btn-analyze");

  // Dropzone events
  if (dropzone) {
    dropzone.addEventListener("click", () => fileInput.click());
    
    dropzone.addEventListener("dragover", (e) => {
      e.preventDefault();
      dropzone.classList.add("dragover");
    });
    
    dropzone.addEventListener("dragleave", () => {
      dropzone.classList.remove("dragover");
    });
    
    dropzone.addEventListener("drop", (e) => {
      e.preventDefault();
      dropzone.classList.remove("dragover");
      if (e.dataTransfer.files.length) {
        handleFileSelection(e.dataTransfer.files[0]);
      }
    });
  }
  
  if (fileInput) {
    fileInput.addEventListener("change", () => {
      if (fileInput.files.length) {
        handleFileSelection(fileInput.files[0]);
      }
    });
  }
  
  if (fpRemove) {
    fpRemove.addEventListener("click", (e) => {
      e.stopPropagation();
      resetUploadState();
    });
  }
  
  function handleFileSelection(file) {
    errorAlert.classList.add("hidden");
    const name = file.name;
    const sizeKB = (file.size / 1024).toFixed(1);
    
    const ext = name.split(".").pop().toLowerCase();
    if (!["csv", "xlsx", "xls"].includes(ext)) {
      showError("Invalid file type. Please upload a CSV or Excel spreadsheet.");
      return;
    }
    
    fpName.textContent = name;
    fpSize.textContent = `${sizeKB} KB`;
    
    dropzone.classList.add("hidden");
    filePreview.classList.remove("hidden");
    btnAnalyze.classList.remove("hidden");
    
    btnAnalyze.onclick = () => uploadFile(file);
  }
  
  function showError(msg) {
    errorMessage.innerHTML = msg;
    errorAlert.classList.remove("hidden");
    resetUploadState();
  }
  
  function resetUploadState() {
    fileInput.value = "";
    if (dropzone) dropzone.classList.remove("hidden");
    filePreview.classList.add("hidden");
    progressWrapper.classList.add("hidden");
    btnAnalyze.classList.add("hidden");
    progressBar.style.width = "0%";
    progressPercent.textContent = "0%";
  }
  
  function uploadFile(file) {
    progressWrapper.classList.remove("hidden");
    btnAnalyze.classList.add("hidden");
    fpRemove.classList.add("hidden");
    
    if (window.location.protocol === "file:") {
      // Direct crash prevention for local open
      setTimeout(() => {
        showError("⚠️ <strong>Upload Blocked:</strong> You are currently running the page under <code>file://</code> protocol. Browser security blocks local file transmission. Please execute the <strong>runproject.bat</strong> runner and access <a href='http://127.0.0.1:5000'>http://127.0.0.1:5000</a> to test analysis!");
      }, 500);
      return;
    }
    
    const formData = new FormData();
    formData.append("file", file);
    
    const selectedDoc = document.getElementById("selected-doctor-input") ? document.getElementById("selected-doctor-input").value : "Dr. K. Albert";
    formData.append("selected_doctor", selectedDoc);
    
    const urlParams = new URLSearchParams(window.location.search);
    const patientId = urlParams.get('patient_id');
    if (patientId) {
      formData.append("patient_id", patientId);
    }
    
    const xhr = new XMLHttpRequest();
    xhr.open("POST", "/api/upload", true);
    
    xhr.upload.onprogress = (e) => {
      if (e.lengthComputable) {
        const pct = Math.round((e.loaded / e.total) * 100);
        progressBar.style.width = `${pct * 0.9}%`;
        progressPercent.textContent = `${Math.round(pct * 0.9)}%`;
      }
    };
    
    xhr.onload = () => {
      if (xhr.status === 200) {
        progressBar.style.width = "100%";
        progressPercent.textContent = "100%";
        
        try {
          const res = JSON.parse(xhr.responseText);
          
          localStorage.setItem("fitpulse-session-id", res.session_id);
          localStorage.setItem("fitpulse-filename", res.filename);
          localStorage.setItem("fitpulse-report", JSON.stringify(res.report));
          localStorage.setItem("fitpulse-records", JSON.stringify(res.records));
          
          setTimeout(() => {
            const redirectUrl = patientId ? `/dashboard?patient_id=${patientId}` : '/dashboard';
            window.location.href = redirectUrl;
          }, 600);
        } catch (err) {
          showError("Failed to parse analysis response from server.");
        }
      } else {
        try {
          const errRes = JSON.parse(xhr.responseText);
          showError(errRes.error || "A server error occurred during data analysis.");
        } catch (e) {
          showError(`Analysis failed: HTTP ${xhr.status}`);
        }
        fpRemove.classList.remove("hidden");
      }
    };
    
    xhr.onerror = () => {
      showError("⚠️ <strong>Network Error:</strong> AJAX transmission was closed. Ensure your local Python server is running by double-clicking <strong>runproject.bat</strong> and loading the app at <a href='http://127.0.0.1:5000'>http://127.0.0.1:5000</a>.");
      fpRemove.classList.remove("hidden");
    };
    
    xhr.send(formData);
  }
}

/* ── DASHBOARD PAGE LOGIC ────────────────────────────────────────────────── */
function setupDashboardPage() {
  const sessionId = localStorage.getItem("fitpulse-session-id");
  const reportDataStr = localStorage.getItem("fitpulse-report");
  const recordsDataStr = localStorage.getItem("fitpulse-records");
  
  const noSessionContent = document.getElementById("no-session-content");
  const dashboardContent = document.getElementById("dashboard-content");
  const headerActions = document.getElementById("dash-header-actions");
  
  if (!sessionId || !reportDataStr || !recordsDataStr) {
    if (noSessionContent) noSessionContent.classList.remove("hidden");
    if (dashboardContent) dashboardContent.classList.add("hidden");
    if (headerActions) headerActions.classList.add("hidden");
    return;
  }
  
  if (noSessionContent) noSessionContent.classList.add("hidden");
  if (dashboardContent) dashboardContent.classList.remove("hidden");
  if (headerActions) headerActions.classList.remove("hidden");
  
  const report = JSON.parse(reportDataStr);
  const records = JSON.parse(recordsDataStr);
  
  document.getElementById("kpi-records").textContent = report.statistics.total_records;
  document.getElementById("kpi-avg-hr").textContent = Math.round(report.statistics.avg_heart_rate);
  document.getElementById("kpi-avg-steps").textContent = Math.round(report.statistics.avg_steps).toLocaleString();
  
  // Advanced Vitals KPIs
  const kpiAvgSpo2 = document.getElementById("kpi-avg-spo2");
  if (kpiAvgSpo2) {
    kpiAvgSpo2.textContent = Math.round(report.statistics.avg_spo2 || 98);
  }
  const kpiAvgCalories = document.getElementById("kpi-avg-calories");
  if (kpiAvgCalories) {
    kpiAvgCalories.textContent = Math.round(report.statistics.avg_calories || 2000).toLocaleString();
  }

  // Health Risk Score KPI Card
  const kpiRiskVal = document.getElementById("kpi-risk-value");
  const kpiRiskLvl = document.getElementById("kpi-risk-level");
  if (kpiRiskVal && kpiRiskLvl) {
    const risk = report.statistics.latest_risk || 0;
    const lvl = report.statistics.latest_anomaly === "Yes" && risk < 40 ? "Medium" : (risk >= 60 ? "High" : risk >= 30 ? "Medium" : "Low");
    kpiRiskVal.textContent = Math.round(risk) + " / 100";
    kpiRiskLvl.textContent = lvl.toUpperCase();
    kpiRiskLvl.className = "risk-meter-level risk-level-" + lvl.toLowerCase();
  }

  // Early Warning Alert Banner
  const banner = document.getElementById("early-warning-banner");
  const bannerText = document.getElementById("early-warning-text");
  if (banner && bannerText) {
    // Check if there is an early warning or deviation in the insights
    const warningInsight = report.insights.find(ins => ins.type === "danger" || ins.title.includes("Warning") || ins.title.includes("Deviations"));
    if (warningInsight) {
      banner.classList.remove("hidden");
      bannerText.innerHTML = `<strong>${warningInsight.title}:</strong> ${warningInsight.detail}`;
    } else {
      banner.classList.add("hidden");
    }
  }
  
  const anomCount = report.anomaly_stats.anomaly_count;
  const anomPct = report.anomaly_stats.anomaly_pct;
  document.getElementById("kpi-anom-count").textContent = anomCount;
  document.getElementById("kpi-anom-pct").textContent = `(${anomPct}%)`;
  
  const anomCard = document.getElementById("kpi-anom-card");
  if (anomCount > 0) {
    anomCard.classList.add("kpi-danger");
  } else {
    anomCard.classList.remove("kpi-danger");
  }
  
  document.getElementById("mc-clinical").textContent = report.anomaly_stats.clinical_flags;
  document.getElementById("mc-zscore").textContent = report.anomaly_stats.z_score_flags;
  document.getElementById("mc-iqr").textContent = report.anomaly_stats.iqr_flags;
  document.getElementById("mc-iforest").textContent = report.anomaly_stats.iforest_flags;
  
  const logsList = document.getElementById("process-logs-list");
  if (logsList) {
    logsList.innerHTML = "";
    report.processing_log.forEach(log => {
      const li = document.createElement("li");
      li.className = "log-item";
      li.textContent = log;
      logsList.appendChild(li);
    });
  }
  
  renderDashboardCharts(records, report);
  setupCalorieBurner(report);
}

let trendChartObj = null;
let scatterChartObj = null;

function renderDashboardCharts(records, report) {
  const canvasTrend = document.getElementById("chart-trends");
  const canvasScatter = document.getElementById("chart-scatter");
  if (!canvasTrend || !canvasScatter) return;
  
  const ctxTrend = canvasTrend.getContext("2d");
  const ctxScatter = canvasScatter.getContext("2d");
  
  const labels = records.map((_, i) => i + 1);
  const hrData = records.map(r => r.HeartRate || r.heart_rate || 72);
  const stepsData = records.map(r => r.Steps || r.steps || 0);
  

  
  let colors = getThemeColors();
  
  const trendConfig = {
    type: "line",
    data: {
      labels: labels,
      datasets: [
        {
          label: "Heart Rate (bpm)",
          data: hrData,
          borderColor: colors.blue,
          borderWidth: 2,
          pointRadius: 0,
          pointHoverRadius: 4,
          tension: 0.35,
          yAxisID: "y-hr"
        },
        {
          label: "Steps Count",
          data: stepsData,
          borderColor: colors.green,
          borderWidth: 2,
          pointRadius: 0,
          pointHoverRadius: 4,
          tension: 0.35,
          yAxisID: "y-steps"
        }
      ]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      interaction: {
        mode: "index",
        intersect: false
      },
      plugins: {
        legend: {
          labels: { color: colors.text, font: { family: "Plus Jakarta Sans", weight: 600 } }
        }
      },
      scales: {
        x: {
          grid: { display: false },
          ticks: { color: colors.text }
        },
        "y-hr": {
          type: "linear",
          display: true,
          position: "left",
          grid: { color: colors.grid },
          ticks: { color: colors.text },
          title: { display: true, text: "Heart Rate (bpm)", color: colors.text, font: { weight: 700 } }
        },
        "y-steps": {
          type: "linear",
          display: true,
          position: "right",
          grid: { drawOnChartArea: false },
          ticks: { color: colors.text },
          title: { display: true, text: "Steps", color: colors.text, font: { weight: 700 } }
        }
      }
    }
  };
  
  if (trendChartObj) trendChartObj.destroy();
  trendChartObj = new Chart(ctxTrend, trendConfig);
  
  const scatterNormal = [];
  const scatterAnomaly = [];
  
  records.forEach(r => {
    const point = { x: r.Steps || r.steps || 0, y: r.HeartRate || r.heart_rate || 72 };
    if (r.Anomaly === "Yes" || r.anomaly === "Yes") {
      scatterAnomaly.push(point);
    } else {
      scatterNormal.push(point);
    }
  });
  
  const scatterConfig = {
    type: "scatter",
    data: {
      datasets: [
        {
          label: "Normal Logs",
          data: scatterNormal,
          backgroundColor: "rgba(2, 132, 199, 0.4)",
          borderColor: colors.blue,
          borderWidth: 1.5,
          pointRadius: 5,
          pointHoverRadius: 7
        },
        {
          label: "Anomaly Outliers",
          data: scatterAnomaly,
          backgroundColor: "rgba(225, 29, 72, 0.8)",
          borderColor: colors.red,
          borderWidth: 2,
          pointRadius: 6,
          pointHoverRadius: 8,
          showLine: false
        }
      ]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: {
          labels: { color: colors.text, font: { family: "Plus Jakarta Sans", weight: 600 } }
        }
      },
      scales: {
        x: {
          grid: { color: colors.grid },
          ticks: { color: colors.text },
          title: { display: true, text: "Steps", color: colors.text, font: { weight: 700 } }
        },
        y: {
          grid: { color: colors.grid },
          ticks: { color: colors.text },
          title: { display: true, text: "Heart Rate (bpm)", color: colors.text, font: { weight: 700 } }
        }
      }
    }
  };
  
  if (scatterChartObj) scatterChartObj.destroy();
  scatterChartObj = new Chart(ctxScatter, scatterConfig);
  
  window.addEventListener("themechanged", () => {
    const newColors = getThemeColors();
    
    if (trendChartObj) {
      trendChartObj.options.plugins.legend.labels.color = newColors.text;
      trendChartObj.options.scales.x.ticks.color = newColors.text;
      trendChartObj.options.scales["y-hr"].grid.color = newColors.grid;
      trendChartObj.options.scales["y-hr"].ticks.color = newColors.text;
      trendChartObj.options.scales["y-hr"].title.color = newColors.text;
      trendChartObj.options.scales["y-steps"].ticks.color = newColors.text;
      trendChartObj.options.scales["y-steps"].title.color = newColors.text;
      trendChartObj.update();
    }
    
    if (scatterChartObj) {
      scatterChartObj.options.plugins.legend.labels.color = newColors.text;
      scatterChartObj.options.scales.x.grid.color = newColors.grid;
      scatterChartObj.options.scales.x.ticks.color = newColors.text;
      scatterChartObj.options.scales.x.title.color = newColors.text;
      scatterChartObj.options.scales.y.grid.color = newColors.grid;
      scatterChartObj.options.scales.y.ticks.color = newColors.text;
      scatterChartObj.options.scales.y.title.color = newColors.text;
      scatterChartObj.update();
    }
  });
}

/* ── REPORT PAGE LOGIC ───────────────────────────────────────────────────── */
function setupReportPage() {
  const sessionId = localStorage.getItem("fitpulse-session-id");
  const filename = localStorage.getItem("fitpulse-filename");
  const reportDataStr = localStorage.getItem("fitpulse-report");
  const recordsDataStr = localStorage.getItem("fitpulse-records");
  
  const noSessionContent = document.getElementById("no-session-content");
  const reportContent = document.getElementById("report-content");
  const headerActions = document.getElementById("report-header-actions");
  
  if (!sessionId || !reportDataStr || !recordsDataStr) {
    if (noSessionContent) noSessionContent.classList.remove("hidden");
    if (reportContent) reportContent.classList.add("hidden");
    if (headerActions) headerActions.classList.add("hidden");
    return;
  }
  
  if (noSessionContent) noSessionContent.classList.add("hidden");
  if (reportContent) reportContent.classList.remove("hidden");
  if (headerActions) headerActions.classList.remove("hidden");
  
  const report = JSON.parse(reportDataStr);
  const records = JSON.parse(recordsDataStr);
  
  document.getElementById("report-meta").textContent = `Generated: ${report.generated_at} | Dataset File: ${filename}`;
  
  document.getElementById("rep-total").textContent = report.statistics.total_records;
  document.getElementById("rep-avg-hr").textContent = `${Math.round(report.statistics.avg_heart_rate)} bpm`;
  if (document.getElementById("rep-avg-spo2")) {
    document.getElementById("rep-avg-spo2").textContent = `${Math.round(report.statistics.avg_spo2 || 98)}%`;
  }
  if (document.getElementById("rep-avg-sleep")) {
    document.getElementById("rep-avg-sleep").textContent = `${(report.statistics.avg_sleep || 8.0).toFixed(1)}h`;
  }
  if (document.getElementById("rep-avg-stress")) {
    document.getElementById("rep-avg-stress").textContent = `${(report.statistics.avg_stress || 3.0).toFixed(1)} / 10`;
  }
  document.getElementById("rep-avg-steps").textContent = Math.round(report.statistics.avg_steps).toLocaleString();
  
  const normalPct = report.anomaly_stats.normal_count > 0 ? (100 - report.anomaly_stats.anomaly_pct) : 100;
  const anomPct = report.anomaly_stats.anomaly_pct;
  document.getElementById("rep-normal-pct").textContent = normalPct;
  document.getElementById("rep-anom-pct").textContent = anomPct;
  document.getElementById("ab-fill-normal").style.width = `${normalPct}%`;
  document.getElementById("ab-fill-anomaly").style.width = `${anomPct}%`;
  
  document.getElementById("rep-am-clinical").textContent = report.anomaly_stats.clinical_flags;
  document.getElementById("rep-am-zscore").textContent = report.anomaly_stats.z_score_flags;
  document.getElementById("rep-am-iqr").textContent = report.anomaly_stats.iqr_flags;
  document.getElementById("rep-am-iforest").textContent = report.anomaly_stats.iforest_flags;
  
  const insightsContainer = document.getElementById("insights-list-container");
  if (insightsContainer) {
    insightsContainer.innerHTML = "";
    report.insights.forEach(ins => {
      const card = document.createElement("div");
      card.className = `insight-card insight-${ins.type}`;
      
      let icon = "⚙️";
      if (ins.type === "success") icon = "🟢";
      else if (ins.type === "warning") icon = "🟡";
      else if (ins.type === "danger") icon = "🔴";
      else if (ins.type === "info") icon = "🔵";
      
      card.innerHTML = `
        <span class="ic-icon">${icon}</span>
        <div>
          <strong>${ins.title}</strong>
          <p>${ins.detail}</p>
        </div>
      `;
      insightsContainer.appendChild(card);
    });
  }

  // ── Severe Causes & Remedies Parser ──
  const remedyContainer = document.getElementById("remedy-list-container");
  if (remedyContainer) {
    remedyContainer.innerHTML = "";
    
    const avgHR = report.statistics.avg_heart_rate || 72;
    const avgSpO2 = report.statistics.avg_spo2 || 98;
    const avgStress = report.statistics.avg_stress || 3.0;
    
    let maxSys = 120;
    let minSpO2 = 100;
    let maxTemp = 36.6;
    records.forEach(r => {
      const sys = r.systolic_bp || r.SystolicBP || 120;
      if (sys > maxSys) maxSys = sys;
      const o2 = r.spo2 || r.SpO2 || 98;
      if (o2 < minSpO2) minSpO2 = o2;
      const temp = r.temperature || r.Temperature || 36.6;
      if (temp > maxTemp) maxTemp = temp;
    });

    const alerts = [];

    if (avgHR > 100) {
      alerts.push({
        title: "Tachycardia Detected (Elevated Heart Rate)",
        cause: "Mean resting heart rate is abnormally high (" + Math.round(avgHR) + " bpm). This can be caused by dehydration, acute anxiety, physical exhaustion, or underlying strain.",
        remedy: "Sit down immediately. Take slow, deep diaphragmatic breaths (inhale for 4s, hold for 4s, exhale for 6s). Drink cool water, avoid caffeine, and stimulate the vagus nerve. Seek medical attention if accompanied by chest pain."
      });
    } else if (avgHR < 60) {
      alerts.push({
        title: "Bradycardia Detected (Low Heart Rate)",
        cause: "Mean resting heart rate is below normal boundaries (" + Math.round(avgHR) + " bpm). While common in trained athletes, it can indicate conduction system delays or thyroid imbalances in others.",
        remedy: "Avoid sudden standing to prevent orthostatic hypotension. Lie down and raise your feet slightly. If feeling lightheaded or dizzy, seek clinical evaluation."
      });
    }

    if (minSpO2 < 95) {
      alerts.push({
        title: "Mild Hypoxemia / Oxygen Deprivation",
        cause: "Oxygen levels dropped below safe limits (" + Math.round(minSpO2) + "%). Potential causes include poor room ventilation, respiratory obstruction, or lung function issues.",
        remedy: "Immediately sit upright (do not lie flat) to maximize lung expansion. Open windows to improve fresh air circulation. Perform pursed-lip breathing. Access supplemental oxygen if prescribed."
      });
    }

    if (maxSys > 140) {
      alerts.push({
        title: "Hypertension / Elevated Blood Pressure",
        cause: "Systolic blood pressure peaked at " + Math.round(maxSys) + " mmHg. This causes acute vascular wall stress and increases cardiovascular risk.",
        remedy: "Rest in a quiet, dark environment for 15-20 minutes. Practice mindfulness and slow box-breathing. Take prescribed anti-hypertensive drugs. Seek immediate emergency care if BP exceeds 180/120 mmHg or if you experience severe headaches."
      });
    }

    if (maxTemp > 38.0) {
      alerts.push({
        title: "Pyrexia (High Fever)",
        cause: "Body temperature peaked at " + maxTemp.toFixed(1) + "°C. This suggests an active immune response to an infection or heat exhaustion.",
        remedy: "Stay hydrated by sipping room-temperature water. Rest in a cool room. Apply cool, damp washcloths to the forehead, armpits, and groin. Take antipyretics like paracetamol if prescribed."
      });
    }

    if (avgStress > 7.0) {
      alerts.push({
        title: "High Psychological Stress Outliers",
        cause: "Prolonged elevated stress scores (" + avgStress.toFixed(1) + "/10) trigger persistent cortisol release and elevated arterial resistance.",
        remedy: "Step away from digital screens and workspace triggers. Engage in a 5-minute guided meditation, perform light progressive muscle relaxation, or drink warm chamomile tea."
      });
    }

    if (alerts.length > 0) {
      alerts.forEach(item => {
        const cardHtml = `
          <div style="background: rgba(225, 29, 72, 0.04); border: 1.5px solid rgba(225, 29, 72, 0.25); border-radius: 16px; padding: 20px; margin-bottom: 15px; display: flex; flex-direction: column; gap: 10px;">
            <div style="display: flex; align-items: center; gap: 10px;">
              <span style="font-size: 22px;">🚨</span>
              <strong style="font-size: 15px; color: #e11d48; font-family: 'Outfit', sans-serif;">${item.title}</strong>
            </div>
            <div style="font-size: 13.5px; line-height: 1.5; color: var(--text);">
              <b style="color: var(--text-2);">Possible Cause:</b> ${item.cause}
            </div>
            <div style="font-size: 13.5px; line-height: 1.5; color: var(--text); border-top: 1px dashed rgba(225, 29, 72, 0.15); padding-top: 10px;">
              <b style="color: #ea580c; display: flex; align-items: center; gap: 4px;">💊 Instant Remedy:</b> ${item.remedy}
            </div>
          </div>
        `;
        remedyContainer.insertAdjacentHTML("beforeend", cardHtml);
      });
    } else {
      remedyContainer.innerHTML = `
        <div style="background: rgba(16, 185, 129, 0.04); border: 1.5px solid rgba(16, 185, 129, 0.25); border-radius: 16px; padding: 20px; display: flex; align-items: center; gap: 12px;">
          <span style="font-size: 24px;">🟢</span>
          <div>
            <strong style="font-size: 15px; color: #10b981; font-family: 'Outfit', sans-serif; display: block;">All Vitals Stable</strong>
            <p style="font-size: 13px; color: var(--text-2); margin: 4px 0 0 0;">No severe diagnostics conditions detected in your vital records. Stay active, drink plenty of water, and maintain consistent sleep patterns!</p>
          </div>
        </div>
      `;
    }
  }

  const recsContainer = document.getElementById("recommendations-container");
  if (recsContainer) {
    recsContainer.innerHTML = "";
    report.recommendations.forEach(rec => {
      const card = document.createElement("div");
      card.className = "rec-card";
      card.innerHTML = `
        <span class="rc-icon">${rec.icon || "💡"}</span>
        <div>
          <strong>${rec.title}</strong>
          <p>${rec.detail}</p>
        </div>
      `;
      recsContainer.appendChild(card);
    });
  }
  
  // Render Dynamic Doctor Names & Signatures
  const latestRec = records[records.length - 1];
  const docName = latestRec ? (latestRec.selected_doctor || "Dr. K. Albert") : "Dr. K. Albert";
  const docTitle = docName.includes("Suganya") ? "Lead Diagnostics Analyst" : "Chief Cardiologist";
  
  if (document.getElementById("rep-doctor-header")) document.getElementById("rep-doctor-header").textContent = docName;
  if (document.getElementById("rep-doctor-board")) document.getElementById("rep-doctor-board").textContent = docName;
  if (document.getElementById("rep-doctor-name")) document.getElementById("rep-doctor-name").textContent = docName;
  if (document.getElementById("rep-doctor-title")) document.getElementById("rep-doctor-title").textContent = docTitle;

  // Render report heart rate bar chart diagram
  const ctxHRBar = document.getElementById("rep-heartrate-bar-chart");
  if (ctxHRBar) {
    const hrData = records.map(r => r.heart_rate || r.HeartRate || 72).slice(-30);
    const hrLabels = records.map((r, idx) => {
      const ts = r.timestamp || "";
      return ts.includes(" ") ? ts.split(" ")[1] : `Log #${idx+1}`;
    }).slice(-30);
    
    const colors = getThemeColors();
    const hrConfig = {
      type: "bar",
      data: {
        labels: hrLabels,
        datasets: [{
          label: "Heart Rate (bpm)",
          data: hrData,
          backgroundColor: hrData.map(v => v > 100 || v < 60 ? "rgba(225, 29, 72, 0.75)" : "rgba(2, 132, 199, 0.75)"),
          borderColor: hrData.map(v => v > 100 || v < 60 ? colors.red : colors.blue),
          borderWidth: 1
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: { display: false }
        },
        scales: {
          x: { ticks: { color: colors.text, font: { size: 9 } }, grid: { color: colors.grid } },
          y: { min: 40, max: 160, ticks: { color: colors.text }, grid: { color: colors.grid } }
        }
      }
    };
    if (reportHRChartObj) reportHRChartObj.destroy();
    reportHRChartObj = new Chart(ctxHRBar, hrConfig);
  }

  const pdfBtn = document.getElementById("btn-download-pdf");
  if (pdfBtn) {
    pdfBtn.onclick = () => {
      // Force all tab-content sections visible before printing
      const tabContents = document.querySelectorAll('.tab-content');
      tabContents.forEach(el => {
        el.dataset.prevDisplay = el.style.display;
        el.style.display = 'block';
      });
      window.print();
      // Restore original display after print dialog closes
      setTimeout(() => {
        tabContents.forEach(el => {
          el.style.display = el.dataset.prevDisplay || '';
        });
      }, 1000);
    };
  }
  
  setupAnomaliesTable(records);
}

function setupAnomaliesTable(records) {
  const anomalies = records.filter(r => r.Anomaly === "Yes" || r.anomaly === "Yes");
  const tableBody = document.getElementById("anomalies-table-body");
  const tableSection = document.getElementById("outliers-table-section");
  
  if (!tableBody || !tableSection) return;
  
  if (anomalies.length === 0) {
    tableSection.classList.add("hidden");
    return;
  }
  
  tableSection.classList.remove("hidden");
  
  let currentPage = 1;
  const rowsPerPage = 10;
  const totalAnom = anomalies.length;
  const totalPages = Math.ceil(totalAnom / rowsPerPage);
  
  const prevBtn = document.getElementById("btn-prev-page");
  const nextBtn = document.getElementById("btn-next-page");
  const pageInfo = document.getElementById("table-page-info");
  
  function renderTablePage(page) {
    tableBody.innerHTML = "";
    const start = (page - 1) * rowsPerPage;
    const end = Math.min(start + rowsPerPage, totalAnom);
    
    const pageRows = anomalies.slice(start, end);
    
    pageRows.forEach((row, idx) => {
      const tr = document.createElement("tr");
      
      const hr = row.HeartRate || row.heart_rate || 72;
      const spo2 = row.SpO2 || row.spo2 || 98;
      const stress = row.StressLevel || row.stress_level || 3;
      const reason = row.Anomaly_Reason || row.anomaly_reason || "—";
      const rowId = row.RowID || row.id || (start + idx + 1);

      tr.innerHTML = `
        <td>#${rowId}</td>
        <td>${row.Gender || row.gender || 'Unknown'}</td>
        <td style="font-weight:700;">${hr} bpm</td>
        <td>${spo2}%</td>
        <td>${stress} / 10</td>
        <td class="reason-cell">${reason}</td>
      `;
      tableBody.appendChild(tr);
    });
    
    pageInfo.textContent = `Showing ${start + 1} to ${end} of ${totalAnom} anomalies (Page ${page} of ${totalPages})`;
    prevBtn.disabled = (page === 1);
    nextBtn.disabled = (page === totalPages);
  }
  
  prevBtn.onclick = () => {
    if (currentPage > 1) {
      currentPage--;
      renderTablePage(currentPage);
    }
  };
  
  nextBtn.onclick = () => {
    if (currentPage < totalPages) {
      currentPage++;
      renderTablePage(currentPage);
    }
  };
  
  renderTablePage(currentPage);
}

/* ── CALORIE BURN CALCULATOR WIDGET ──────────────────────────────────────── */
function setupCalorieBurner(report) {
  const calcHR = document.getElementById("calc-hr");
  const calcDuration = document.getElementById("calc-duration");
  const calcAge = document.getElementById("calc-age");
  const calcGender = document.getElementById("calc-gender");
  const calcResult = document.getElementById("calc-result");
  const calcBtn = document.getElementById("btn-calc-calories");
  
  if (!calcHR || !calcDuration || !calcAge || !calcGender || !calcResult || !calcBtn) return;
  
  // Initialize inputs from dataset averages if available
  if (report && report.statistics) {
    calcHR.value = Math.round(report.statistics.avg_heart_rate) || 76;
  }
  
  function calculate() {
    const hr = parseFloat(calcHR.value);
    const duration = parseFloat(calcDuration.value);
    const age = parseFloat(calcAge.value);
    const gender = calcGender.value;
    
    let kcal = 0;
    if (gender === "Male") {
      kcal = ((-55.0969 + (0.6309 * hr) + (0.1988 * 75) + (0.2017 * age)) / 4.184) * duration;
    } else {
      kcal = ((-20.4022 + (0.4472 * hr) - (0.1263 * 65) + (0.0740 * age)) / 4.184) * duration;
    }
    
    kcal = Math.max(0, Math.round(kcal));
    calcResult.innerHTML = `${kcal} <small style="font-size:14px; color:var(--text-3); font-weight:600;">kcal</small>`;
  }
  
  calcBtn.addEventListener("click", calculate);
  calculate();
}

/* ── DAILY WATER TRACKER WIDGET ──────────────────────────────────────────── */
function setupWaterTracker() {
  const cups = document.querySelectorAll(".water-cup");
  const progressLabel = document.getElementById("water-progress-label");
  const resetBtn = document.getElementById("btn-water-reset");
  
  if (!cups.length || !progressLabel || !resetBtn) return;
  
  let waterState = JSON.parse(localStorage.getItem("fitpulse-water-intake")) || [false, false, false, false, false, false, false, false];
  
  function updateUI() {
    let count = 0;
    cups.forEach((cup, index) => {
      if (waterState[index]) {
        cup.innerHTML = "💧";
        cup.style.opacity = "1";
        cup.style.transform = "scale(1.2)";
        cup.style.transition = "transform 0.2s ease";
        count++;
      } else {
        cup.innerHTML = "🥤";
        cup.style.opacity = "0.4";
        cup.style.transform = "scale(1)";
      }
    });
    
    const percent = Math.round((count / 8) * 100);
    progressLabel.textContent = `Hydration Target: ${count} / 8 Cups (${percent}%)`;
    if (percent === 100) {
      progressLabel.innerHTML = `🌟 Hydration Target Achieved! 💧 (100%)`;
      progressLabel.style.color = "var(--green)";
    } else {
      progressLabel.style.color = "";
    }
  }
  
  cups.forEach((cup, index) => {
    cup.addEventListener("click", () => {
      waterState[index] = !waterState[index];
      localStorage.setItem("fitpulse-water-intake", JSON.stringify(waterState));
      updateUI();
    });
  });
  
  resetBtn.addEventListener("click", () => {
    waterState = [false, false, false, false, false, false, false, false];
    localStorage.setItem("fitpulse-water-intake", JSON.stringify(waterState));
    updateUI();
  });
  
  updateUI();
}

/* ── ABOUT PAGE CHECKLIST & TEAM WIGGLES ─────────────────────────────────── */
function setupAboutPage() {
  const docCard = document.getElementById("team-doctor");
  const nurseCard = document.getElementById("team-nurse");
  
  function wiggle(el) {
    el.style.transform = "rotate(2deg) scale(1.05)";
    setTimeout(() => { el.style.transform = "rotate(-2deg) scale(1.05)"; }, 80);
    setTimeout(() => { el.style.transform = "rotate(1deg) scale(1.05)"; }, 160);
    setTimeout(() => { el.style.transform = "rotate(-1deg) scale(1.05)"; }, 240);
    setTimeout(() => { el.style.transform = "rotate(0deg) scale(1.05)"; }, 320);
  }
  
  if (docCard) {
    docCard.addEventListener("mouseenter", () => wiggle(docCard));
    docCard.addEventListener("mouseleave", () => docCard.style.transform = "");
  }
  if (nurseCard) {
    nurseCard.addEventListener("mouseenter", () => wiggle(nurseCard));
    nurseCard.addEventListener("mouseleave", () => nurseCard.style.transform = "");
  }
  
  // Checklist logic
  const items = document.querySelectorAll(".admission-item");
  const progressLabel = document.getElementById("admission-progress-label");
  const resetBtn = document.getElementById("btn-admission-reset");
  
  if (!items.length || !progressLabel || !resetBtn) return;
  
  let checklistState = JSON.parse(localStorage.getItem("fitpulse-admission-checklist")) || [false, false, false, false];
  
  function updateUI() {
    let count = 0;
    items.forEach((item, index) => {
      const checkbox = item.querySelector(".admission-checkbox");
      if (checklistState[index]) {
        checkbox.textContent = "✅";
        item.style.color = "var(--green)";
        item.style.opacity = "1";
        count++;
      } else {
        checkbox.textContent = "⬜";
        item.style.color = "";
        item.style.opacity = "0.7";
      }
    });
    
    const percent = Math.round((count / 4) * 100);
    progressLabel.textContent = `Prep Progress: ${count} / 4 Items (${percent}%)`;
    if (percent === 100) {
      progressLabel.innerHTML = `🌟 Hospital Ward Admission Prepared! (100%)`;
      progressLabel.style.color = "var(--green)";
    } else {
      progressLabel.style.color = "";
    }
  }
  
  items.forEach((item, index) => {
    item.addEventListener("click", () => {
      checklistState[index] = !checklistState[index];
      localStorage.setItem("fitpulse-admission-checklist", JSON.stringify(checklistState));
      updateUI();
    });
  });
  
  resetBtn.addEventListener("click", () => {
    checklistState = [false, false, false, false];
    localStorage.setItem("fitpulse-admission-checklist", JSON.stringify(checklistState));
    updateUI();
  });
  
  updateUI();
}

function setupGlobalChatWidget() {
  const chatToggle = document.getElementById("ai-chat-toggle");
  const chatDrawer = document.getElementById("ai-chat-drawer");
  const chatClose = document.getElementById("ai-chat-close");
  
  if (chatToggle && chatDrawer && chatClose) {
    chatToggle.onclick = (e) => {
      e.stopPropagation();
      const isHidden = chatDrawer.style.display === "none" || !chatDrawer.style.display;
      chatDrawer.style.display = isHidden ? "flex" : "none";
    };
    chatClose.onclick = (e) => {
      e.stopPropagation();
      chatDrawer.style.display = "none";
    };
    
    // Close on click outside
    document.addEventListener("click", (e) => {
      if (!chatDrawer.contains(e.target) && e.target !== chatToggle) {
        chatDrawer.style.display = "none";
      }
    });
    
    const chatForm = document.getElementById("ai-chat-form");
    const chatInput = document.getElementById("ai-chat-input");
    const chatMessages = document.getElementById("ai-chat-messages");
    
    if (chatForm && chatInput && chatMessages) {
      chatForm.onsubmit = (e) => {
        e.preventDefault();
        const msg = chatInput.value.trim();
        if (!msg) return;
        
        const userDiv = document.createElement("div");
        userDiv.className = "chat-message user";
        userDiv.style.background = "var(--blue)";
        userDiv.style.color = "white";
        userDiv.style.alignSelf = "flex-end";
        userDiv.style.padding = "10px 14px";
        userDiv.style.borderRadius = "12px 12px 2px 12px";
        userDiv.style.maxWidth = "85%";
        userDiv.style.textAlign = "left";
        userDiv.innerText = msg;
        chatMessages.appendChild(userDiv);
        
        chatInput.value = "";
        chatMessages.scrollTop = chatMessages.scrollHeight;
        
        const urlParams = new URLSearchParams(window.location.search);
        const patientId = urlParams.get('patient_id');
        
        const payload = { message: msg };
        if (patientId) {
          payload.patient_id = patientId;
        }
        
        fetch("/api/chat", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(payload)
        })
        .then(res => res.json())
        .then(data => {
          const assistantDiv = document.createElement("div");
          assistantDiv.className = "chat-message assistant";
          assistantDiv.style.background = "var(--bg-3)";
          assistantDiv.style.color = "var(--text)";
          assistantDiv.style.alignSelf = "flex-start";
          assistantDiv.style.padding = "10px 14px";
          assistantDiv.style.borderRadius = "12px 12px 12px 2px";
          assistantDiv.style.maxWidth = "85%";
          assistantDiv.style.textAlign = "left";
          assistantDiv.innerHTML = data.reply;
          chatMessages.appendChild(assistantDiv);
          chatMessages.scrollTop = chatMessages.scrollHeight;
        })
        .catch(err => {
          console.error(err);
          const assistantDiv = document.createElement("div");
          assistantDiv.className = "chat-message assistant";
          assistantDiv.style.background = "var(--bg-3)";
          assistantDiv.style.color = "var(--text)";
          assistantDiv.style.alignSelf = "flex-start";
          assistantDiv.style.padding = "10px 14px";
          assistantDiv.style.borderRadius = "12px 12px 12px 2px";
          assistantDiv.style.maxWidth = "85%";
          assistantDiv.style.textAlign = "left";
          assistantDiv.innerText = "Error: Failed to fetch AI response.";
          chatMessages.appendChild(assistantDiv);
        });
      };
    }
  }
}

/* ── PROFILE MODAL LOGIC ────────────────────────────────────────────────── */
function openProfileModal() {
  const modal = document.getElementById("profile-modal");
  const errorEl = document.getElementById("profile-error");
  if (!modal || !errorEl) return;
  
  errorEl.classList.add("hidden");
  errorEl.textContent = "";
  
  fetch('/api/profile_info')
    .then(res => res.json())
    .then(data => {
      if (data.error) {
        showToast(data.error, "error");
        return;
      }
      
      document.getElementById("prof-username").value = data.username || "";
      document.getElementById("prof-age").value = data.age || "30";
      document.getElementById("prof-gender").value = data.gender || "Male";
      document.getElementById("prof-purpose").value = data.purpose || "Routine Check";
      
      const purposeGroup = document.getElementById("prof-purpose-group");
      if (purposeGroup) {
        const label = purposeGroup.querySelector('label');
        if (data.role === 'doctor') {
          if (label) label.textContent = 'Physician Specialty / Role';
        } else {
          if (label) label.textContent = 'Clinical Purpose / Specialty';
        }
      }
      
      modal.style.display = "flex";
    })
    .catch(err => {
      console.error(err);
      showToast("Failed to fetch profile details.", "error");
    });
}

function closeProfileModal() {
  const modal = document.getElementById("profile-modal");
  if (modal) modal.style.display = "none";
}

// Hook profile update form
document.addEventListener("DOMContentLoaded", () => {
  const profForm = document.getElementById("profile-form");
  if (profForm) {
    profForm.onsubmit = (e) => {
      e.preventDefault();
      
      const username = document.getElementById("prof-username").value.trim();
      const age = parseInt(document.getElementById("prof-age").value);
      const gender = document.getElementById("prof-gender").value;
      const purpose = document.getElementById("prof-purpose").value.trim();
      const errorEl = document.getElementById("profile-error");
      
      fetch('/api/update_profile', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username, age, gender, purpose })
      })
      .then(res => res.json())
      .then(data => {
        if (data.error) {
          errorEl.textContent = data.error;
          errorEl.classList.remove("hidden");
          return;
        }
        
        showToast("👤 Profile updated successfully!", "success");
        closeProfileModal();
        
        const nameEl = document.getElementById("nav-profile-username");
        if (nameEl) nameEl.textContent = data.username;
        
        const dashNameEl = document.getElementById("dash-patient-name");
        if (dashNameEl && document.body.getAttribute('data-user-role') !== 'doctor') {
          dashNameEl.textContent = data.username;
        }
        
        setTimeout(() => {
          window.location.href = window.location.pathname + window.location.search;
        }, 1000);
      })
      .catch(err => {
        console.error(err);
        errorEl.textContent = "An error occurred while updating profile.";
        errorEl.classList.remove("hidden");
      });
    };
  }
});


