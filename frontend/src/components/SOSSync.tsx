// @ts-nocheck
import { useState, useEffect } from "react";

const initialLogs = [
  { id: 1, type: "success", message: "Sync completed successfully",    time: "2023-10-27 14:30:15" },
  { id: 2, type: "info",    message: "Fetching data from StockTrim...", time: "2023-10-27 14:28:45" },
  { id: 3, type: "error",   message: "Error: Connection timeout",       time: "2023-10-27 14:25:12" },
  { id: 4, type: "info",    message: "Validating API credentials",      time: "2023-10-27 14:22:10" },
  { id: 5, type: "success", message: "Inventory schema mapped",         time: "2023-10-27 14:20:01" },
  { id: 6, type: "info",    message: "Connecting to SOS Inventory...",  time: "2023-10-27 14:18:30" },
  { id: 7, type: "success", message: "Authentication successful",       time: "2023-10-27 14:17:05" },
  { id: 8, type: "error",   message: "Rate limit exceeded, retrying",   time: "2023-10-27 14:15:44" },
];

const FREQUENCIES = ["Every 15 minutes", "Every 30 minutes", "Hourly", "Every 6 hours", "Daily"];

// ── Design tokens from design system ──────────────────────────────────────
const C = {
  primary:   "#1E293B",   // dark navy
  secondary: "#3B82F6",   // blue
  tertiary:  "#64748B",   // slate
  neutral:   "#787878",   // gray
  white:     "#FFFFFF",
  bg:        "#F8FAFC",   // very light slate background
  border:    "#E2E8F0",   // light slate border
  cardBg:    "#FFFFFF",
  errorBg:   "#FEF2F2",
  errorFg:   "#DC2626",
  errorBd:   "#FECACA",
  successBg: "#F0FDF4",
  successFg: "#16A34A",
  successBd: "#BBF7D0",
  infoBg:    "#EFF6FF",
  infoFg:    "#3B82F6",
  infoBd:    "#BFDBFE",
};

export default function SOSSync() {
  const [logs, setLogs]               = useState(initialLogs.slice(0, 5));
  const [showAll, setShowAll]         = useState(false);
  const [showModal, setShowModal]     = useState(false);
  const [syncing, setSyncing]         = useState(false);
  const [toast, setToast]             = useState(false);
  const [frequency, setFrequency]     = useState("Hourly");
  const [autoSync, setAutoSync]       = useState(true);
  const [pendingFreq, setPendingFreq] = useState("Hourly");
  const [pendingAuto, setPendingAuto] = useState(true);
  const [liveFeed, setLiveFeed]       = useState(false);

  const displayedLogs = showAll ? logs : logs.slice(0, 5);

  function openModal() {
    setPendingFreq(frequency);
    setPendingAuto(autoSync);
    setShowModal(true);
  }

  function saveSettings() {
    setFrequency(pendingFreq);
    setAutoSync(pendingAuto);
    setShowModal(false);
  }

  function handleSync() {
    if (syncing) return;
    setSyncing(true);
    setToast(true);
    setTimeout(() => setToast(false), 3500);
    const newEntries = [
      { id: Date.now(),     type: "info",    message: "Sync initiated...",           time: nowStr() },
      { id: Date.now() + 1, type: "info",    message: "Fetching SOS inventory...",   time: nowStr() },
      { id: Date.now() + 2, type: "success", message: "Sync completed successfully", time: nowStr() },
    ];
    let i = 0;
    const interval = setInterval(() => {
      if (i >= newEntries.length) { clearInterval(interval); setSyncing(false); return; }
      setLogs(prev => [newEntries[i], ...prev]);
      i++;
    }, 900);
  }

  function nowStr() {
    return new Date().toISOString().replace("T", " ").slice(0, 19);
  }

  useEffect(() => {
    const handler = (e) => { if (e.key === "Escape") setShowModal(false); };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, []);

  const badge = (type) => {
    const map = {
      success: { bg: C.successBg, color: C.successFg, border: C.successBd, icon: "✓" },
      info:    { bg: C.infoBg,    color: C.infoFg,    border: C.infoBd,    icon: "i" },
      error:   { bg: C.errorBg,   color: C.errorFg,   border: C.errorBd,   icon: "!" },
    };
    return map[type] || map.info;
  };

  return (
    <div style={s.root}>
      {/* ── Navbar ── */}
      <nav style={s.navbar}>
        <span style={s.navBrand}>SOS Sync</span>
        <button style={s.gearBtn} onClick={openModal} title="Sync Settings">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
            <circle cx="12" cy="12" r="3"/>
            <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83-2.83l.06-.06A1.65 1.65 0 0 0 4.68 15a1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 2.83-2.83l.06.06A1.65 1.65 0 0 0 9 4.68a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 2.83l-.06.06A1.65 1.65 0 0 0 19.4 9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z"/>
          </svg>
        </button>
      </nav>

      <div style={s.navDivider} />

      {/* ── Hero ── */}
      <div style={s.hero}>
        <h1 style={s.heroTitle}>Operational Synchronization</h1>
        <p style={s.heroSub}>
          Ensure your SOS and StockTrim systems are perfectly aligned with real-time inventory
          <br />and supply chain data updates.
        </p>
        <button
          style={{...s.syncBtn, opacity: syncing ? 0.8 : 1}}
          onClick={handleSync}
          disabled={syncing}
        >
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round"
            style={{animation: syncing ? "spin 1s linear infinite" : "none"}}>
            <polyline points="1 4 1 10 7 10"/>
            <polyline points="23 20 23 14 17 14"/>
            <path d="M20.49 9A9 9 0 0 0 5.64 5.64L1 10m22 4l-4.64 4.36A9 9 0 0 1 3.51 15"/>
          </svg>
          {syncing ? "Syncing..." : "SOS → StockTrim Sync"}
        </button>
        {autoSync && (
          <p style={s.autoSyncBadge}>
            <span style={s.greenDot} /> Auto-sync enabled · {frequency}
          </p>
        )}
      </div>

      {/* ── Sync Logs ── */}
      <div style={s.card}>
        <div style={s.cardHeader}>
          <div style={s.cardTitle}>
            <svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke={C.tertiary} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" style={{marginRight: 8}}>
              <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
              <polyline points="14 2 14 8 20 8"/>
              <line x1="16" y1="13" x2="8" y2="13"/>
              <line x1="16" y1="17" x2="8" y2="17"/>
              <polyline points="10 9 9 9 8 9"/>
            </svg>
            Sync Logs
          </div>
          <button
            style={{
              ...s.liveFeedBtn,
              background: liveFeed ? C.secondary : "#F1F5F9",
              color: liveFeed ? C.white : C.tertiary,
              border: `1px solid ${liveFeed ? C.secondary : C.border}`,
            }}
            onClick={() => setLiveFeed(v => !v)}
          >
            {liveFeed && <span style={s.liveDot} />}
            Live Feed
          </button>
        </div>

        <div style={s.divider} />

        <div>
          {displayedLogs.map((log, i) => {
            const b = badge(log.type);
            return (
              <div key={log.id} style={{...s.logRow, animationDelay: `${i * 0.04}s`}}>
                <span style={{...s.badge, background: b.bg, color: b.color, border: `1px solid ${b.border}`}}>
                  <span style={s.badgeIcon}>{b.icon}</span>
                  {log.type.charAt(0).toUpperCase() + log.type.slice(1)}
                </span>
                <span style={{...s.logMsg, fontWeight: log.type === "error" ? 600 : 400, color: log.type === "error" ? C.errorFg : C.primary}}>
                  {log.message}
                </span>
                <span style={s.logTime}>{log.time}</span>
              </div>
            );
          })}
        </div>

        {logs.length > 5 && (
          <>
            <div style={s.divider} />
            <button style={s.seeMoreBtn} onClick={() => setShowAll(v => !v)}>
              {showAll ? "Show Less ∧" : "See More ∨"}
            </button>
          </>
        )}
      </div>

      {/* ── Settings Modal ── */}
      {showModal && (
        <div style={s.overlay} onClick={() => setShowModal(false)}>
          <div style={s.modal} onClick={e => e.stopPropagation()}>
            <div style={s.modalHeader}>
              <span style={s.modalTitle}>Sync Settings</span>
              <button style={s.closeBtn} onClick={() => setShowModal(false)}>✕</button>
            </div>

            <div style={s.modalBody}>
              <label style={s.label}>Set Sync Frequency</label>
              <div style={s.selectWrap}>
                <select
                  style={s.select}
                  value={pendingFreq}
                  onChange={e => setPendingFreq(e.target.value)}
                >
                  {FREQUENCIES.map(f => <option key={f}>{f}</option>)}
                </select>
                <svg style={s.selectArrow} width="15" height="15" viewBox="0 0 24 24" fill="none" stroke={C.tertiary} strokeWidth="2.5">
                  <polyline points="6 9 12 15 18 9"/>
                </svg>
              </div>
              <p style={s.hint}>Updates will be pulled from SOS and pushed to StockTrim automatically.</p>

              <div style={s.toggleRow}>
                <div>
                  <div style={s.toggleLabel}>Auto-Sync Control</div>
                  <div style={s.toggleSub}>Enable Auto-Sync</div>
                </div>
                <button
                  style={{...s.toggle, background: pendingAuto ? C.secondary : "#CBD5E1"}}
                  onClick={() => setPendingAuto(v => !v)}
                >
                  <span style={{...s.toggleKnob, transform: pendingAuto ? "translateX(22px)" : "translateX(2px)"}} />
                </button>
              </div>
            </div>

            <div style={s.modalFooter}>
              <button style={s.cancelBtn} onClick={() => setShowModal(false)}>Cancel</button>
              <button style={s.saveBtn} onClick={saveSettings}>Save Changes</button>
            </div>
          </div>
        </div>
      )}

      {/* ── Toast ── */}
      {toast && (
        <div style={s.toast}>
          <span style={s.toastIcon}>✓</span>
          Sync started successfully
          <button style={s.toastClose} onClick={() => setToast(false)}>✕</button>
        </div>
      )}

      <style>{`
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
        @keyframes spin    { to { transform: rotate(360deg); } }
        @keyframes fadeUp  { from { opacity:0; transform:translateY(6px); } to { opacity:1; transform:translateY(0); } }
        @keyframes slideIn { from { opacity:0; transform:translateY(20px) scale(.98); } to { opacity:1; transform:translateY(0) scale(1); } }
        @keyframes toastIn { from { opacity:0; transform:translateX(40px); } to { opacity:1; transform:translateX(0); } }
      `}</style>
    </div>
  );
}

const s = {
  root: {
    minHeight: "100vh",
    background: "#F8FAFC",
    fontFamily: "'Inter', sans-serif",
    color: "#1E293B",
  },

  // ── Navbar
  navbar: {
    display: "flex",
    alignItems: "center",
    justifyContent: "space-between",
    padding: "0 32px",
    height: 56,
    background: "#1E293B",        // primary
  },
  navBrand: {
    fontSize: 16,
    fontWeight: 700,
    letterSpacing: "-0.2px",
    color: "#FFFFFF",
  },
  navDivider: {
    height: 1,
    background: "#E2E8F0",
  },
  gearBtn: {
    background: "none",
    border: "none",
    cursor: "pointer",
    color: "#94A3B8",             // lighter slate on dark navbar
    display: "flex",
    alignItems: "center",
    padding: 6,
    borderRadius: 8,
  },

  // ── Hero
  hero: {
    textAlign: "center",
    padding: "64px 24px 48px",
  },
  heroTitle: {
    fontSize: 32,
    fontWeight: 700,
    letterSpacing: "-0.5px",
    margin: "0 0 14px",
    color: "#1E293B",             // primary
  },
  heroSub: {
    fontSize: 15,
    color: "#64748B",             // tertiary
    lineHeight: 1.75,
    margin: "0 0 32px",
  },
  syncBtn: {
    display: "inline-flex",
    alignItems: "center",
    gap: 10,
    background: "#3B82F6",        // secondary
    color: "#FFFFFF",
    border: "none",
    borderRadius: 8,
    padding: "13px 28px",
    fontSize: 15,
    fontWeight: 600,
    cursor: "pointer",
    letterSpacing: "-0.1px",
    boxShadow: "0 1px 3px rgba(59,130,246,.4)",
  },
  autoSyncBadge: {
    marginTop: 14,
    fontSize: 13,
    color: "#64748B",             // tertiary
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    gap: 6,
  },
  greenDot: {
    display: "inline-block",
    width: 8,
    height: 8,
    borderRadius: "50%",
    background: "#22C55E",
  },

  // ── Card
  card: {
    maxWidth: 860,
    margin: "0 auto 48px",
    background: "#FFFFFF",
    borderRadius: 12,
    border: "1px solid #E2E8F0",
    overflow: "hidden",
    boxShadow: "0 1px 3px rgba(0,0,0,.06)",
  },
  cardHeader: {
    display: "flex",
    alignItems: "center",
    justifyContent: "space-between",
    padding: "18px 24px",
  },
  cardTitle: {
    fontSize: 15,
    fontWeight: 700,
    color: "#1E293B",             // primary
    display: "flex",
    alignItems: "center",
  },
  divider: {
    height: 1,
    background: "#F1F5F9",
  },
  liveFeedBtn: {
    display: "inline-flex",
    alignItems: "center",
    gap: 6,
    borderRadius: 6,
    padding: "5px 12px",
    fontSize: 12,
    fontWeight: 500,
    cursor: "pointer",
    transition: "all .15s",
  },
  liveDot: {
    display: "inline-block",
    width: 6,
    height: 6,
    borderRadius: "50%",
    background: "#22C55E",
  },

  // ── Log rows
  logRow: {
    display: "flex",
    alignItems: "center",
    gap: 14,
    padding: "14px 24px",
    borderBottom: "1px solid #F8FAFC",
    animation: "fadeUp .22s ease both",
  },
  badge: {
    display: "inline-flex",
    alignItems: "center",
    gap: 5,
    padding: "3px 10px",
    borderRadius: 20,
    fontSize: 11,
    fontWeight: 600,
    whiteSpace: "nowrap",
    minWidth: 72,
    justifyContent: "center",
    letterSpacing: "0.2px",
  },
  badgeIcon: {
    fontSize: 10,
    fontWeight: 700,
  },
  logMsg: {
    flex: 1,
    fontSize: 13.5,
  },
  logTime: {
    fontSize: 11.5,
    color: "#787878",             // neutral
    whiteSpace: "nowrap",
    fontFamily: "'Inter', monospace",
    letterSpacing: "0.1px",
  },
  seeMoreBtn: {
    width: "100%",
    background: "none",
    border: "none",
    padding: "14px",
    fontSize: 13,
    fontWeight: 600,
    color: "#3B82F6",             // secondary
    cursor: "pointer",
    textAlign: "center",
    letterSpacing: "-0.1px",
  },

  // ── Modal
  overlay: {
    position: "fixed",
    inset: 0,
    background: "rgba(15,23,42,.5)",  // primary-tinted overlay
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    zIndex: 1000,
  },
  modal: {
    background: "#FFFFFF",
    borderRadius: 14,
    width: "100%",
    maxWidth: 500,
    margin: 16,
    boxShadow: "0 24px 64px rgba(15,23,42,.2)",
    animation: "slideIn .2s ease",
    overflow: "hidden",
  },
  modalHeader: {
    display: "flex",
    alignItems: "center",
    justifyContent: "space-between",
    padding: "20px 24px 18px",
    borderBottom: "1px solid #F1F5F9",
  },
  modalTitle: {
    fontSize: 17,
    fontWeight: 700,
    color: "#1E293B",             // primary
  },
  closeBtn: {
    background: "none",
    border: "none",
    fontSize: 15,
    color: "#94A3B8",
    cursor: "pointer",
    padding: 4,
    lineHeight: 1,
  },
  modalBody: {
    padding: "22px 24px",
  },
  label: {
    display: "block",
    fontSize: 12,
    fontWeight: 600,
    color: "#64748B",             // tertiary
    marginBottom: 8,
    textTransform: "uppercase",
    letterSpacing: "0.5px",
  },
  selectWrap: {
    position: "relative",
    marginBottom: 8,
  },
  select: {
    width: "100%",
    padding: "10px 36px 10px 12px",
    border: "1px solid #E2E8F0",
    borderRadius: 8,
    fontSize: 14,
    color: "#1E293B",             // primary
    background: "#F8FAFC",
    appearance: "none",
    cursor: "pointer",
    outline: "none",
    fontFamily: "'Inter', sans-serif",
  },
  selectArrow: {
    position: "absolute",
    right: 11,
    top: "50%",
    transform: "translateY(-50%)",
    pointerEvents: "none",
  },
  hint: {
    fontSize: 12,
    color: "#64748B",             // tertiary
    margin: "6px 0 22px",
    lineHeight: 1.6,
  },
  toggleRow: {
    display: "flex",
    alignItems: "center",
    justifyContent: "space-between",
    background: "#F8FAFC",
    border: "1px solid #E2E8F0",
    borderRadius: 10,
    padding: "14px 16px",
  },
  toggleLabel: {
    fontSize: 11,
    fontWeight: 600,
    color: "#64748B",             // tertiary
    marginBottom: 2,
    textTransform: "uppercase",
    letterSpacing: "0.4px",
  },
  toggleSub: {
    fontSize: 14,
    fontWeight: 500,
    color: "#1E293B",             // primary
  },
  toggle: {
    position: "relative",
    width: 46,
    height: 25,
    borderRadius: 13,
    border: "none",
    cursor: "pointer",
    transition: "background .2s",
    flexShrink: 0,
  },
  toggleKnob: {
    position: "absolute",
    top: 3,
    width: 19,
    height: 19,
    borderRadius: "50%",
    background: "#FFFFFF",
    boxShadow: "0 1px 3px rgba(0,0,0,.2)",
    transition: "transform .2s",
    display: "block",
  },
  modalFooter: {
    display: "flex",
    justifyContent: "flex-end",
    gap: 10,
    padding: "14px 24px 20px",
    background: "#F8FAFC",
    borderTop: "1px solid #F1F5F9",
  },
  cancelBtn: {
    padding: "9px 20px",
    background: "none",
    border: "1px solid #E2E8F0",
    borderRadius: 8,
    fontSize: 13,
    fontWeight: 600,
    color: "#64748B",             // tertiary
    cursor: "pointer",
    fontFamily: "'Inter', sans-serif",
  },
  saveBtn: {
    padding: "9px 20px",
    background: "#3B82F6",        // secondary
    border: "none",
    borderRadius: 8,
    fontSize: 13,
    fontWeight: 600,
    color: "#FFFFFF",
    cursor: "pointer",
    fontFamily: "'Inter', sans-serif",
    boxShadow: "0 1px 2px rgba(59,130,246,.4)",
  },

  // ── Toast
  toast: {
    position: "fixed",
    bottom: 24,
    right: 24,
    background: "#1E293B",        // primary
    color: "#FFFFFF",
    borderRadius: 10,
    padding: "13px 18px",
    fontSize: 13.5,
    fontWeight: 500,
    display: "flex",
    alignItems: "center",
    gap: 10,
    boxShadow: "0 8px 32px rgba(15,23,42,.25)",
    animation: "toastIn .25s ease",
    zIndex: 2000,
    fontFamily: "'Inter', sans-serif",
  },
  toastIcon: {
    display: "inline-flex",
    alignItems: "center",
    justifyContent: "center",
    width: 20,
    height: 20,
    borderRadius: "50%",
    background: "#22C55E",
    fontSize: 11,
    fontWeight: 700,
    color: "#FFFFFF",
    flexShrink: 0,
  },
  toastClose: {
    background: "none",
    border: "none",
    color: "#64748B",             // tertiary
    cursor: "pointer",
    fontSize: 12,
    padding: 0,
    marginLeft: 4,
  },
};