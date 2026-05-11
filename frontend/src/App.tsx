import React, { useState, useEffect } from "react";

// ─── Types ────────────────────────────────────────────────────────────────────
type LogLevel = "success" | "info" | "error";

interface LogEntry {
  id: number;
  level: LogLevel;
  message: string;
  timestamp: string;
}

type SyncFrequency = "Hourly" | "Every 6 Hours" | "Daily" | "Weekly";

// ─── Sample Data ──────────────────────────────────────────────────────────────
const ALL_LOGS: LogEntry[] = [
  { id: 1, level: "success", message: "Sync completed successfully",     timestamp: "2023-10-27 14:30:15" },
  { id: 2, level: "info",    message: "Fetching data from StockTrim...", timestamp: "2023-10-27 14:28:45" },
  { id: 3, level: "error",   message: "Error: Connection timeout",       timestamp: "2023-10-27 14:25:12" },
  { id: 4, level: "info",    message: "Validating API credentials",      timestamp: "2023-10-27 14:22:10" },
  { id: 5, level: "success", message: "Inventory schema mapped",         timestamp: "2023-10-27 14:20:01" },
  { id: 6, level: "info",    message: "Connecting to SOS endpoint...",   timestamp: "2023-10-27 14:18:33" },
  { id: 7, level: "success", message: "Authentication successful",       timestamp: "2023-10-27 14:17:05" },
  { id: 8, level: "error",   message: "Error: Rate limit exceeded",      timestamp: "2023-10-27 14:10:44" },
];

const COLLAPSED_COUNT = 5;

// ─── Icons ────────────────────────────────────────────────────────────────────
const GearIcon = () => (
  <svg xmlns="http://www.w3.org/2000/svg" width="22" height="22" fill="none" viewBox="0 0 24 24"
    stroke="currentColor" strokeWidth={1.8}>
    <path strokeLinecap="round" strokeLinejoin="round"
      d="M9.594 3.94c.09-.542.56-.94 1.11-.94h2.593c.55 0 1.02.398 1.11.94l.213 1.281c.063.374.313.686.645.87.074.04.147.083.22.127.325.196.72.257 1.075.124l1.217-.456a1.125 1.125 0 0 1 1.37.49l1.296 2.247a1.125 1.125 0 0 1-.26 1.431l-1.003.827c-.293.241-.438.613-.43.992a7.723 7.723 0 0 1 0 .255c-.008.378.137.75.43.991l1.004.827c.424.35.534.955.26 1.43l-1.298 2.247a1.125 1.125 0 0 1-1.369.491l-1.217-.456c-.355-.133-.75-.072-1.076.124a6.47 6.47 0 0 1-.22.128c-.331.183-.581.495-.644.869l-.213 1.281c-.09.543-.56.94-1.11.94h-2.594c-.55 0-1.019-.398-1.11-.94l-.213-1.281c-.062-.374-.312-.686-.644-.87a6.52 6.52 0 0 1-.22-.127c-.325-.196-.72-.257-1.076-.124l-1.217.456a1.125 1.125 0 0 1-1.369-.49l-1.297-2.247a1.125 1.125 0 0 1 .26-1.431l1.004-.827c.292-.24.437-.613.43-.991a6.932 6.932 0 0 1 0-.255c.007-.38-.138-.751-.43-.992l-1.004-.827a1.125 1.125 0 0 1-.26-1.43l1.297-2.247a1.125 1.125 0 0 1 1.37-.491l1.216.456c.356.133.751.072 1.076-.124.072-.044.146-.086.22-.128.332-.183.582-.495.644-.869l.214-1.28Z" />
    <path strokeLinecap="round" strokeLinejoin="round" d="M15 12a3 3 0 1 1-6 0 3 3 0 0 1 6 0Z" />
  </svg>
);

const SyncIcon = () => (
  <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" fill="none" viewBox="0 0 24 24"
    stroke="currentColor" strokeWidth={2}>
    <path strokeLinecap="round" strokeLinejoin="round"
      d="M16.023 9.348h4.992v-.001M2.985 19.644v-4.992m0 0h4.992m-4.993 0 3.181 3.183a8.25 8.25 0 0 0 13.803-3.7M4.031 9.865a8.25 8.25 0 0 1 13.803-3.7l3.181 3.182m0-4.991v4.99" />
  </svg>
);

const LogsIcon = () => (
  <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" fill="none" viewBox="0 0 24 24"
    stroke="currentColor" strokeWidth={1.8}>
    <path strokeLinecap="round" strokeLinejoin="round"
      d="M9 12h3.75M9 15h3.75M9 18h3.75m3 .75H18a2.25 2.25 0 0 0 2.25-2.25V6.108c0-1.135-.845-2.098-1.976-2.192a48.424 48.424 0 0 0-1.123-.08m-5.801 0c-.065.21-.1.433-.1.664 0 .414.336.75.75.75h4.5a.75.75 0 0 0 .75-.75 2.25 2.25 0 0 0-.1-.664m-5.8 0A2.251 2.251 0 0 1 13.5 2.25H15c1.012 0 1.867.668 2.15 1.586m-5.8 0c-.376.023-.75.05-1.124.08C9.095 4.01 8.25 4.973 8.25 6.108V8.25m0 0H4.875c-.621 0-1.125.504-1.125 1.125v11.25c0 .621.504 1.125 1.125 1.125h9.75c.621 0 1.125-.504 1.125-1.125V9.375c0-.621-.504-1.125-1.125-1.125H8.25ZM6.75 12h.008v.008H6.75V12Zm0 3h.008v.008H6.75V15Zm0 3h.008v.008H6.75V18Z" />
  </svg>
);

const CheckCircleIcon = () => (
  <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" fill="none" viewBox="0 0 24 24"
    stroke="currentColor" strokeWidth={2.5}>
    <path strokeLinecap="round" strokeLinejoin="round" d="M9 12.75 11.25 15 15 9.75M21 12a9 9 0 1 1-18 0 9 9 0 0 1 18 0Z" />
  </svg>
);

const InfoCircleIcon = () => (
  <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" fill="none" viewBox="0 0 24 24"
    stroke="currentColor" strokeWidth={2.5}>
    <path strokeLinecap="round" strokeLinejoin="round" d="m11.25 11.25.041-.02a.75.75 0 0 1 1.063.852l-.708 2.836a.75.75 0 0 0 1.063.853l.041-.021M21 12a9 9 0 1 1-18 0 9 9 0 0 1 18 0Zm-9-3.75h.008v.008H12V8.25Z" />
  </svg>
);

const ErrorCircleIcon = () => (
  <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" fill="none" viewBox="0 0 24 24"
    stroke="currentColor" strokeWidth={2.5}>
    <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v3.75m9-.75a9 9 0 1 1-18 0 9 9 0 0 1 18 0Zm-9 3.75h.008v.008H12v-.008Z" />
  </svg>
);

const ChevronDownIcon = ({ open }: { open: boolean }) => (
  <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="none" viewBox="0 0 24 24"
    stroke="currentColor" strokeWidth={2.5}
    style={{ transition: "transform 0.2s", transform: open ? "rotate(180deg)" : "rotate(0deg)" }}>
    <path strokeLinecap="round" strokeLinejoin="round" d="m19.5 8.25-7.5 7.5-7.5-7.5" />
  </svg>
);

const XIcon = () => (
  <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" fill="none" viewBox="0 0 24 24"
    stroke="currentColor" strokeWidth={2}>
    <path strokeLinecap="round" strokeLinejoin="round" d="M6 18 18 6M6 6l12 12" />
  </svg>
);

const ToastCheckIcon = () => (
  <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" fill="none" viewBox="0 0 24 24"
    stroke="#3B82F6" strokeWidth={2.5}>
    <path strokeLinecap="round" strokeLinejoin="round" d="M9 12.75 11.25 15 15 9.75M21 12a9 9 0 1 1-18 0 9 9 0 0 1 18 0Z" />
  </svg>
);

// ─── Badge Component ───────────────────────────────────────────────────────────
const Badge = ({ level }: { level: LogLevel }) => {
  const config: Record<LogLevel, { bg: string; text: string; icon: React.ReactElement; label: string }> = {
    success: { bg: "rgba(34,197,94,0.12)", text: "#16a34a", icon: <CheckCircleIcon />, label: "Success" },
    info:    { bg: "rgba(59,130,246,0.12)", text: "#2563eb", icon: <InfoCircleIcon />,  label: "Info"    },
    error:   { bg: "rgba(239,68,68,0.12)",  text: "#dc2626", icon: <ErrorCircleIcon />, label: "Error"   },
  };
  const { bg, text, icon, label } = config[level];
  return (
    <span style={{
      display: "inline-flex", alignItems: "center", gap: 5,
      background: bg, color: text,
      padding: "3px 10px", borderRadius: 6, fontSize: 13, fontWeight: 600,
      whiteSpace: "nowrap", minWidth: 82,
    }}>
      {icon} {label}
    </span>
  );
};

// ─── Settings Modal ────────────────────────────────────────────────────────────
const SettingsModal = ({ onClose }: { onClose: () => void }) => {
  const [frequency, setFrequency] = useState<SyncFrequency>("Hourly");
  const [autoSync, setAutoSync] = useState(true);
  const [dropdownOpen, setDropdownOpen] = useState(false);
  const frequencies: SyncFrequency[] = ["Hourly", "Every 6 Hours", "Daily", "Weekly"];

  const handleSave = () => {
    console.log("Save Changes clicked", { frequency, autoSync });
    onClose();
  };

  return (
    <div style={{
      position: "fixed", inset: 0, zIndex: 50,
      background: "rgba(30,41,59,0.45)", backdropFilter: "blur(4px)",
      display: "flex", alignItems: "center", justifyContent: "center",
      animation: "fadeIn 0.15s ease",
    }}
      onClick={(e) => { if (e.target === e.currentTarget) onClose(); }}
    >
      <div style={{
        background: "#fff", borderRadius: 14, width: "100%", maxWidth: 560,
        margin: "0 16px", boxShadow: "0 20px 60px rgba(30,41,59,0.18)",
        animation: "slideUp 0.2s ease",
        overflow: "hidden",
      }}>
        {/* Header */}
        <div style={{
          display: "flex", alignItems: "center", justifyContent: "space-between",
          padding: "22px 28px", borderBottom: "1px solid #f1f5f9",
        }}>
          <h2 style={{ margin: 0, fontSize: 20, fontWeight: 700, color: "#1E293B" }}>
            Sync Settings
          </h2>
          <button onClick={onClose} style={{
            background: "none", border: "none", cursor: "pointer",
            color: "#64748B", padding: 4, borderRadius: 6,
            display: "flex", alignItems: "center",
            transition: "color 0.15s",
          }}
            onMouseEnter={e => (e.currentTarget.style.color = "#1E293B")}
            onMouseLeave={e => (e.currentTarget.style.color = "#64748B")}
          >
            <XIcon />
          </button>
        </div>

        {/* Body */}
        <div style={{ padding: "28px 28px 0" }}>
          {/* Frequency */}
          <label style={{ display: "block", fontSize: 14, fontWeight: 600, color: "#1E293B", marginBottom: 10 }}>
            Set Sync Frequency
          </label>
          <div style={{ position: "relative", marginBottom: 8 }}>
            <button
              onClick={() => setDropdownOpen(o => !o)}
              style={{
                width: "100%", display: "flex", alignItems: "center", justifyContent: "space-between",
                padding: "12px 16px", border: "1.5px solid #e2e8f0", borderRadius: 8,
                background: "#fff", cursor: "pointer", fontSize: 15, color: "#1E293B", fontFamily: "Inter, sans-serif",
                transition: "border-color 0.15s",
              }}
              onFocus={e => (e.currentTarget.style.borderColor = "#3B82F6")}
              onBlur={e => (e.currentTarget.style.borderColor = "#e2e8f0")}
            >
              <span>{frequency}</span>
              <ChevronDownIcon open={dropdownOpen} />
            </button>

            {dropdownOpen && (
              <div style={{
                position: "absolute", top: "calc(100% + 4px)", left: 0, right: 0,
                background: "#fff", border: "1.5px solid #e2e8f0", borderRadius: 8,
                boxShadow: "0 8px 24px rgba(30,41,59,0.12)", zIndex: 10,
                overflow: "hidden",
              }}>
                {frequencies.map(f => (
                  <button key={f}
                    onClick={() => { setFrequency(f); setDropdownOpen(false); }}
                    style={{
                      display: "block", width: "100%", textAlign: "left",
                      padding: "11px 16px", background: f === frequency ? "#eff6ff" : "#fff",
                      border: "none", cursor: "pointer", fontSize: 14,
                      color: f === frequency ? "#3B82F6" : "#1E293B",
                      fontFamily: "Inter, sans-serif", fontWeight: f === frequency ? 600 : 400,
                      transition: "background 0.1s",
                    }}
                    onMouseEnter={e => { if (f !== frequency) e.currentTarget.style.background = "#f8fafc"; }}
                    onMouseLeave={e => { if (f !== frequency) e.currentTarget.style.background = "#fff"; }}
                  >
                    {f}
                  </button>
                ))}
              </div>
            )}
          </div>
          <p style={{ margin: "0 0 28px", fontSize: 13, color: "#64748B" }}>
            Updates will be pulled from SOS and pushed to StockTrim automatically.
          </p>

          {/* Auto-Sync */}
          <div style={{
            display: "flex", alignItems: "center", justifyContent: "space-between",
            marginBottom: 28,
          }}>
            <div>
              <div style={{ fontSize: 13, fontWeight: 500, color: "#64748B", marginBottom: 2 }}>
                Auto-Sync Control
              </div>
              <div style={{ fontSize: 15, fontWeight: 600, color: "#1E293B" }}>Enable Auto-Sync</div>
            </div>
            <button
              onClick={() => setAutoSync(v => !v)}
              role="switch" aria-checked={autoSync}
              style={{
                width: 52, height: 28, borderRadius: 999, border: "none", cursor: "pointer",
                background: autoSync ? "#3B82F6" : "#cbd5e1",
                position: "relative", transition: "background 0.2s", flexShrink: 0,
              }}
            >
              <span style={{
                position: "absolute", top: 3,
                left: autoSync ? 27 : 3,
                width: 22, height: 22, borderRadius: "50%", background: "#fff",
                boxShadow: "0 1px 4px rgba(0,0,0,0.2)",
                transition: "left 0.2s",
              }} />
            </button>
          </div>
        </div>

        {/* Footer */}
        <div style={{
          display: "flex", justifyContent: "flex-end", gap: 12,
          padding: "18px 28px", background: "#f8fafc", borderTop: "1px solid #f1f5f9",
        }}>
          <button
            onClick={() => { console.log("Cancel clicked"); onClose(); }}
            style={{
              padding: "10px 22px", borderRadius: 8, border: "1.5px solid #e2e8f0",
              background: "#fff", color: "#1E293B", fontSize: 14, fontWeight: 600,
              cursor: "pointer", fontFamily: "Inter, sans-serif", transition: "border-color 0.15s, background 0.15s",
            }}
            onMouseEnter={e => (e.currentTarget.style.borderColor = "#cbd5e1")}
            onMouseLeave={e => (e.currentTarget.style.borderColor = "#e2e8f0")}
          >
            Cancel
          </button>
          <button
            onClick={handleSave}
            style={{
              padding: "10px 22px", borderRadius: 8, border: "none",
              background: "#3B82F6", color: "#fff", fontSize: 14, fontWeight: 600,
              cursor: "pointer", fontFamily: "Inter, sans-serif", transition: "background 0.15s",
            }}
            onMouseEnter={e => (e.currentTarget.style.background = "#2563eb")}
            onMouseLeave={e => (e.currentTarget.style.background = "#3B82F6")}
          >
            Save Changes
          </button>
        </div>
      </div>
    </div>
  );
};

// ─── Toast ────────────────────────────────────────────────────────────────────
const Toast = ({ message, onClose }: { message: string; onClose: () => void }) => (
  <div style={{
    position: "fixed", bottom: 28, right: 28, zIndex: 100,
    display: "flex", alignItems: "center", gap: 12,
    background: "#1E293B", color: "#fff",
    padding: "14px 18px", borderRadius: 10,
    boxShadow: "0 8px 32px rgba(30,41,59,0.28)",
    fontSize: 14, fontWeight: 500,
    animation: "slideUp 0.25s ease",
    maxWidth: 340,
  }}>
    <ToastCheckIcon />
    <span style={{ flex: 1 }}>{message}</span>
    <button
      onClick={onClose}
      style={{
        background: "none", border: "none", cursor: "pointer",
        color: "#94a3b8", padding: 0, display: "flex", alignItems: "center",
        transition: "color 0.15s",
      }}
      onMouseEnter={e => (e.currentTarget.style.color = "#fff")}
      onMouseLeave={e => (e.currentTarget.style.color = "#94a3b8")}
    >
      <XIcon />
    </button>
  </div>
);

// ─── App ──────────────────────────────────────────────────────────────────────
export default function App() {
  const [settingsOpen, setSettingsOpen] = useState(false);
  const [showAll, setShowAll] = useState(false);
  const [toast, setToast] = useState<string | null>(null);

  const visibleLogs = showAll ? ALL_LOGS : ALL_LOGS.slice(0, COLLAPSED_COUNT);

  const handleSync = () => {
    console.log("SOS → StockTrim Sync button clicked");
    setToast("Sync started successfully");
  };

  useEffect(() => {
    if (toast) {
      const t = setTimeout(() => setToast(null), 4000);
      return () => clearTimeout(t);
    }
  }, [toast]);

  return (
    <>
      {/* Global styles */}
      <style>{`
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
        *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
        body { font-family: 'Inter', sans-serif; background: #f1f5f9; color: #1E293B; -webkit-font-smoothing: antialiased; }
        @keyframes fadeIn  { from { opacity: 0; } to { opacity: 1; } }
        @keyframes slideUp { from { opacity: 0; transform: translateY(12px); } to { opacity: 1; transform: translateY(0); } }
      `}</style>

      {/* Navbar */}
      <nav style={{
        position: "sticky", top: 0, zIndex: 40,
        background: "#fff", borderBottom: "1px solid #e2e8f0",
        display: "flex", alignItems: "center", justifyContent: "space-between",
        padding: "0 32px", height: 56,
      }}>
        <span style={{ fontWeight: 700, fontSize: 16, color: "#1E293B", letterSpacing: "-0.01em" }}>
          SOS Sync
        </span>
        <button
          onClick={() => { console.log("Settings gear icon clicked"); setSettingsOpen(true); }}
          title="Settings"
          style={{
            background: "none", border: "none", cursor: "pointer",
            color: "#64748B", display: "flex", alignItems: "center",
            padding: 6, borderRadius: 8, transition: "color 0.15s, background 0.15s",
          }}
          onMouseEnter={e => { e.currentTarget.style.color = "#1E293B"; e.currentTarget.style.background = "#f1f5f9"; }}
          onMouseLeave={e => { e.currentTarget.style.color = "#64748B"; e.currentTarget.style.background = "none"; }}
        >
          <GearIcon />
        </button>
      </nav>

      {/* Hero */}
      <main style={{ maxWidth: 900, margin: "0 auto", padding: "60px 24px 40px" }}>
        <div style={{ textAlign: "center", marginBottom: 48 }}>
          <h1 style={{
            fontSize: "clamp(28px, 4vw, 38px)", fontWeight: 700,
            color: "#1E293B", letterSpacing: "-0.025em", marginBottom: 16,
          }}>
            Operational Synchronization
          </h1>
          <p style={{ fontSize: 16, color: "#64748B", lineHeight: 1.6, maxWidth: 540, margin: "0 auto 32px" }}>
            Ensure your SOS and StockTrim systems are perfectly aligned with real-time inventory and supply chain data updates.
          </p>
          <button
            onClick={handleSync}
            style={{
              display: "inline-flex", alignItems: "center", gap: 10,
              background: "#3B82F6", color: "#fff",
              padding: "15px 36px", borderRadius: 10, border: "none",
              fontSize: 16, fontWeight: 600, cursor: "pointer",
              fontFamily: "Inter, sans-serif", letterSpacing: "-0.01em",
              boxShadow: "0 4px 16px rgba(59,130,246,0.30)",
              transition: "background 0.15s, transform 0.1s, box-shadow 0.15s",
            }}
            onMouseEnter={e => { e.currentTarget.style.background = "#2563eb"; e.currentTarget.style.boxShadow = "0 6px 20px rgba(59,130,246,0.38)"; }}
            onMouseLeave={e => { e.currentTarget.style.background = "#3B82F6"; e.currentTarget.style.boxShadow = "0 4px 16px rgba(59,130,246,0.30)"; }}
            onMouseDown={e  => (e.currentTarget.style.transform = "scale(0.98)")}
            onMouseUp={e    => (e.currentTarget.style.transform = "scale(1)")}
          >
            <SyncIcon />
            SOS → StockTrim Sync
          </button>
        </div>

        {/* Sync Logs Card */}
        <div style={{
          background: "#fff", borderRadius: 14,
          border: "1px solid #e2e8f0",
          boxShadow: "0 2px 12px rgba(30,41,59,0.06)",
          overflow: "hidden",
        }}>
          {/* Card Header */}
          <div style={{
            display: "flex", alignItems: "center", justifyContent: "space-between",
            padding: "20px 28px", borderBottom: "1px solid #f1f5f9",
          }}>
            <div style={{ display: "flex", alignItems: "center", gap: 10, fontWeight: 700, fontSize: 18, color: "#1E293B" }}>
              <span style={{ color: "#64748B" }}><LogsIcon /></span>
              Sync Logs
            </div>
            <span style={{
              fontSize: 12, fontWeight: 600, color: "#64748B",
              background: "#f1f5f9", padding: "5px 12px", borderRadius: 6,
              letterSpacing: "0.02em",
            }}>
              Live Feed
            </span>
          </div>

          {/* Log Entries */}
          <div style={{ padding: "8px 0" }}>
            {visibleLogs.map((log, i) => (
              <div key={log.id} style={{
                display: "flex", alignItems: "center", justifyContent: "space-between",
                padding: "16px 28px",
                borderBottom: i < visibleLogs.length - 1 ? "1px solid #f8fafc" : "none",
                gap: 16, flexWrap: "wrap",
                animation: "fadeIn 0.2s ease",
              }}>
                <div style={{ display: "flex", alignItems: "center", gap: 16, flex: 1, minWidth: 0 }}>
                  <Badge level={log.level} />
                  <span style={{
                    fontSize: 14, color: log.level === "error" ? "#1E293B" : "#374151",
                    fontWeight: log.level === "error" ? 600 : 400,
                    overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap",
                  }}>
                    {log.message}
                  </span>
                </div>
                <span style={{ fontSize: 13, color: "#94a3b8", whiteSpace: "nowrap", fontVariantNumeric: "tabular-nums" }}>
                  {log.timestamp}
                </span>
              </div>
            ))}
          </div>

          {/* See More / See Less */}
          {ALL_LOGS.length > COLLAPSED_COUNT && (
            <div style={{ borderTop: "1px solid #f1f5f9", padding: "16px 0", textAlign: "center" }}>
              <button
                onClick={() => { console.log("See More/Less toggled:", !showAll ? "expanded" : "collapsed"); setShowAll(v => !v); }}
                style={{
                  background: "none", border: "none", cursor: "pointer",
                  color: "#3B82F6", fontSize: 14, fontWeight: 600,
                  fontFamily: "Inter, sans-serif", display: "inline-flex", alignItems: "center", gap: 6,
                  padding: "4px 8px", borderRadius: 6, transition: "background 0.15s",
                }}
                onMouseEnter={e => (e.currentTarget.style.background = "#eff6ff")}
                onMouseLeave={e => (e.currentTarget.style.background = "none")}
              >
                {showAll ? "See Less" : "See More"}
                <ChevronDownIcon open={showAll} />
              </button>
            </div>
          )}
        </div>
      </main>

      {/* Settings Modal */}
      {settingsOpen && <SettingsModal onClose={() => setSettingsOpen(false)} />}

      {/* Toast */}
      {toast && <Toast message={toast} onClose={() => setToast(null)} />}
    </>
  );
}