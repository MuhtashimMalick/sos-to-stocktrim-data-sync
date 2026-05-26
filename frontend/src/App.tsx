import React, { useState, useEffect } from "react";

// ─── Types ────────────────────────────────────────────────────────────────────
type LogLevel = "Success" | "Info" | "Error";

interface LogEntry {
  id: string;
  timestamp: string;
  actionType: string;
  actionVariant: string;
  status: LogLevel;
  message: string;
}

type SyncFrequency = "Hourly" | "Every 6 Hours" | "Daily" | "Weekly";

type SyncKey =
  | "all"
  | "locations"
  | "suppliers"
  | "customers"
  | "products"
  | "purchase_orders"
  | "sales_orders";

// ─── Sync Button Configs ──────────────────────────────────────────────────────
const INDIVIDUAL_SYNCS: {
  key: SyncKey;
  label: string;
  endpoint: string;
  method: "POST" | "PUT";
  startMsg: string;
  successMsg: string;
}[] = [
  {
    key: "locations",
    label: "Sync Locations",
    endpoint: "http://localhost:8000/api/v1/location/create-location",
    method: "POST",
    startMsg: "Syncing locations...",
    successMsg: "Locations synced successfully.",
  },
  {
    key: "suppliers",
    label: "Sync Suppliers",
    endpoint: "http://localhost:8000/api/v1/supplier/create-supplier",
    method: "POST",
    startMsg: "Syncing suppliers...",
    successMsg: "Suppliers synced successfully.",
  },
  {
    key: "customers",
    label: "Sync Customers",
    endpoint: "http://localhost:8000/api/v1/customer/create-customer",
    method: "PUT",
    startMsg: "Syncing customers...",
    successMsg: "Customers synced successfully.",
  },
  {
    key: "products",
    label: "Sync Products",
    endpoint: "http://localhost:8000/api/v1/stocktrim/create-item",
    method: "POST",
    startMsg: "Syncing products...",
    successMsg: "Products synced successfully.",
  },
  {
    key: "purchase_orders",
    label: "Sync Purchase Orders",
    endpoint: "http://localhost:8000/api/v1/purchaseorder/sync-from-sos",
    method: "POST",
    startMsg: "Syncing purchase orders...",
    successMsg: "Purchase orders synced successfully.",
  },
  {
    key: "sales_orders",
    label: "Sync Sales Orders",
    endpoint: "http://localhost:8000/api/v1/salesorder/create-sales-order",
    method: "POST",
    startMsg: "Syncing sales orders...",
    successMsg: "Sales orders synced successfully.",
  },
];

const COLLAPSED_COUNT = 5;

// Only these two endpoints support archived=true with from/to date params
const ARCHIVED_KEYS: SyncKey[] = ["purchase_orders", "sales_orders"];

// ─── Icons ────────────────────────────────────────────────────────────────────
const GearIcon = () => (
  <svg xmlns="http://www.w3.org/2000/svg" width="22" height="22" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.8}>
    <path strokeLinecap="round" strokeLinejoin="round" d="M9.594 3.94c.09-.542.56-.94 1.11-.94h2.593c.55 0 1.02.398 1.11.94l.213 1.281c.063.374.313.686.645.87.074.04.147.083.22.127.325.196.72.257 1.075.124l1.217-.456a1.125 1.125 0 0 1 1.37.49l1.296 2.247a1.125 1.125 0 0 1-.26 1.431l-1.003.827c-.293.241-.438.613-.43.992a7.723 7.723 0 0 1 0 .255c-.008.378.137.75.43.991l1.004.827c.424.35.534.955.26 1.43l-1.298 2.247a1.125 1.125 0 0 1-1.369.491l-1.217-.456c-.355-.133-.75-.072-1.076.124a6.47 6.47 0 0 1-.22.128c-.331.183-.581.495-.644.869l-.213 1.281c-.09.543-.56.94-1.11.94h-2.594c-.55 0-1.019-.398-1.11-.94l-.213-1.281c-.062-.374-.312-.686-.644-.87a6.52 6.52 0 0 1-.22-.127c-.325-.196-.72-.257-1.076-.124l-1.217.456a1.125 1.125 0 0 1-1.369-.49l-1.297-2.247a1.125 1.125 0 0 1 .26-1.431l1.004-.827c.292-.24.437-.613.43-.991a6.932 6.932 0 0 1 0-.255c.007-.38-.138-.751-.43-.992l-1.004-.827a1.125 1.125 0 0 1-.26-1.43l1.297-2.247a1.125 1.125 0 0 1 1.37-.491l1.216.456c.356.133.751.072 1.076-.124.072-.044.146-.086.22-.128.332-.183.582-.495.644-.869l.214-1.28Z" />
    <path strokeLinecap="round" strokeLinejoin="round" d="M15 12a3 3 0 1 1-6 0 3 3 0 0 1 6 0Z" />
  </svg>
);

const SyncIcon = () => (
  <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
    <path strokeLinecap="round" strokeLinejoin="round" d="M16.023 9.348h4.992v-.001M2.985 19.644v-4.992m0 0h4.992m-4.993 0 3.181 3.183a8.25 8.25 0 0 0 13.803-3.7M4.031 9.865a8.25 8.25 0 0 1 13.803-3.7l3.181 3.182m0-4.991v4.99" />
  </svg>
);

const LogsIcon = () => (
  <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.8}>
    <path strokeLinecap="round" strokeLinejoin="round" d="M9 12h3.75M9 15h3.75M9 18h3.75m3 .75H18a2.25 2.25 0 0 0 2.25-2.25V6.108c0-1.135-.845-2.098-1.976-2.192a48.424 48.424 0 0 0-1.123-.08m-5.801 0c-.065.21-.1.433-.1.664 0 .414.336.75.75.75h4.5a.75.75 0 0 0 .75-.75 2.25 2.25 0 0 0-.1-.664m-5.8 0A2.251 2.251 0 0 1 13.5 2.25H15c1.012 0 1.867.668 2.15 1.586m-5.8 0c-.376.023-.75.05-1.124.08C9.095 4.01 8.25 4.973 8.25 6.108V8.25m0 0H4.875c-.621 0-1.125.504-1.125 1.125v11.25c0 .621.504 1.125 1.125 1.125h9.75c.621 0 1.125-.504 1.125-1.125V9.375c0-.621-.504-1.125-1.125-1.125H8.25ZM6.75 12h.008v.008H6.75V12Zm0 3h.008v.008H6.75V15Zm0 3h.008v.008H6.75V18Z" />
  </svg>
);

const RefreshIcon = () => (
  <svg xmlns="http://www.w3.org/2000/svg" width="15" height="15" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.2}>
    <path strokeLinecap="round" strokeLinejoin="round" d="M16.023 9.348h4.992v-.001M2.985 19.644v-4.992m0 0h4.992m-4.993 0 3.181 3.183a8.25 8.25 0 0 0 13.803-3.7M4.031 9.865a8.25 8.25 0 0 1 13.803-3.7l3.181 3.182m0-4.991v4.99" />
  </svg>
);

const CheckCircleIcon = () => (
  <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}>
    <path strokeLinecap="round" strokeLinejoin="round" d="M9 12.75 11.25 15 15 9.75M21 12a9 9 0 1 1-18 0 9 9 0 0 1 18 0Z" />
  </svg>
);

const InfoCircleIcon = () => (
  <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}>
    <path strokeLinecap="round" strokeLinejoin="round" d="m11.25 11.25.041-.02a.75.75 0 0 1 1.063.852l-.708 2.836a.75.75 0 0 0 1.063.853l.041-.021M21 12a9 9 0 1 1-18 0 9 9 0 0 1 18 0Zm-9-3.75h.008v.008H12V8.25Z" />
  </svg>
);

const ErrorCircleIcon = () => (
  <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}>
    <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v3.75m9-.75a9 9 0 1 1-18 0 9 9 0 0 1 18 0Zm-9 3.75h.008v.008H12v-.008Z" />
  </svg>
);

const ChevronDownIcon = ({ open }: { open: boolean }) => (
  <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}
    style={{ transition: "transform 0.2s", transform: open ? "rotate(180deg)" : "rotate(0deg)" }}>
    <path strokeLinecap="round" strokeLinejoin="round" d="m19.5 8.25-7.5 7.5-7.5-7.5" />
  </svg>
);

const XIcon = () => (
  <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
    <path strokeLinecap="round" strokeLinejoin="round" d="M6 18 18 6M6 6l12 12" />
  </svg>
);

const ToastCheckIcon = () => (
  <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" fill="none" viewBox="0 0 24 24" stroke="#3B82F6" strokeWidth={2.5}>
    <path strokeLinecap="round" strokeLinejoin="round" d="M9 12.75 11.25 15 15 9.75M21 12a9 9 0 1 1-18 0 9 9 0 0 1 18 0Z" />
  </svg>
);

const ArchiveIcon = () => (
  <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
    <path strokeLinecap="round" strokeLinejoin="round" d="m20.25 7.5-.625 10.632a2.25 2.25 0 0 1-2.247 2.118H6.622a2.25 2.25 0 0 1-2.247-2.118L3.75 7.5M10 11.25h4M3.375 7.5h17.25c.621 0 1.125-.504 1.125-1.125v-1.5c0-.621-.504-1.125-1.125-1.125H3.375c-.621 0-1.125.504-1.125 1.125v1.5c0 .621.504 1.125 1.125 1.125Z" />
  </svg>
);

const CalendarIcon = () => (
  <svg xmlns="http://www.w3.org/2000/svg" width="15" height="15" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
    <path strokeLinecap="round" strokeLinejoin="round" d="M6.75 3v2.25M17.25 3v2.25M3 18.75V7.5a2.25 2.25 0 0 1 2.25-2.25h13.5A2.25 2.25 0 0 1 21 7.5v11.25m-18 0A2.25 2.25 0 0 0 5.25 21h13.5A2.25 2.25 0 0 0 21 18.75m-18 0v-7.5A2.25 2.25 0 0 1 5.25 9h13.5A2.25 2.25 0 0 1 21 11.25v7.5" />
  </svg>
);

// ─── Spinner ──────────────────────────────────────────────────────────────────
const Spinner = ({ size = 18, color = "#fff" }: { size?: number; color?: string }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg"
    style={{ animation: "spin 0.75s linear infinite", flexShrink: 0 }}>
    <circle cx="12" cy="12" r="10" stroke={color} strokeOpacity="0.25" strokeWidth="3" />
    <path d="M12 2a10 10 0 0 1 10 10" stroke={color} strokeWidth="3" strokeLinecap="round" />
  </svg>
);

// ─── Badge ────────────────────────────────────────────────────────────────────
const Badge = ({ level }: { level: LogLevel }) => {
  const config: Record<LogLevel, { bg: string; text: string; icon: React.ReactElement; label: string }> = {
    Success: { bg: "rgba(34,197,94,0.12)",  text: "#16a34a", icon: <CheckCircleIcon />, label: "Success" },
    Info:    { bg: "rgba(59,130,246,0.12)", text: "#2563eb", icon: <InfoCircleIcon />,  label: "Info"    },
    Error:   { bg: "rgba(239,68,68,0.12)",  text: "#dc2626", icon: <ErrorCircleIcon />, label: "Error"   },
  };
  const { bg, text, icon, label } = config[level] ?? config["Info"];
  return (
    <span style={{ display: "inline-flex", alignItems: "center", gap: 5, background: bg, color: text, padding: "3px 10px", borderRadius: 6, fontSize: 13, fontWeight: 600, whiteSpace: "nowrap", minWidth: 82 }}>
      {icon} {label}
    </span>
  );
};

// ─── Settings Modal ────────────────────────────────────────────────────────────
const frequencyToMinutes: Record<SyncFrequency, number> = {
  Hourly: 60, "Every 6 Hours": 360, Daily: 1440, Weekly: 10080,
};

const minutesToFrequency = (mins: number): SyncFrequency => {
  if (mins === 360) return "Every 6 Hours";
  if (mins === 1440) return "Daily";
  if (mins === 10080) return "Weekly";
  return "Hourly";
};

const SettingsModal = ({ onClose }: { onClose: () => void }) => {
  const [frequency, setFrequency] = useState<SyncFrequency>("Hourly");
  const [autoSync, setAutoSync] = useState(true);
  const [dropdownOpen, setDropdownOpen] = useState(false);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);

  const frequencies: SyncFrequency[] = ["Hourly", "Every 6 Hours", "Daily", "Weekly"];

  useEffect(() => {
    const loadPreferences = async () => {
      try {
        const response = await fetch("http://localhost:8000/api/v1/users/me/preference");
        if (!response.ok) throw new Error("Failed to load preferences");
        const data = await response.json();
        setFrequency(minutesToFrequency(data.sync_after_mins));
        setAutoSync(data.enable_auto_sync);
      } catch (error) {
        console.error("Error loading preferences:", error);
      } finally {
        setLoading(false);
      }
    };
    loadPreferences();
  }, []);

  const handleSave = async () => {
    try {
      setSaving(true);
      const response = await fetch("http://localhost:8000/api/v1/users/me/preference", {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ sync_after_mins: frequencyToMinutes[frequency], enable_auto_sync: autoSync }),
      });
      if (!response.ok) throw new Error("Failed to save preferences");
      onClose();
    } catch (error) {
      console.error("Error saving preferences:", error);
    } finally {
      setSaving(false);
    }
  };

  return (
    <div
      style={{ position: "fixed", inset: 0, zIndex: 50, background: "rgba(30,41,59,0.45)", backdropFilter: "blur(4px)", display: "flex", alignItems: "center", justifyContent: "center", animation: "fadeIn 0.15s ease" }}
      onClick={(e) => { if (e.target === e.currentTarget) onClose(); }}
    >
      <div style={{ background: "#fff", borderRadius: 14, width: "100%", maxWidth: 560, margin: "0 16px", boxShadow: "0 20px 60px rgba(30,41,59,0.18)", animation: "slideUp 0.2s ease", overflow: "hidden" }}>
        {/* Header */}
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", padding: "22px 28px", borderBottom: "1px solid #f1f5f9" }}>
          <h2 style={{ margin: 0, fontSize: 20, fontWeight: 700, color: "#1E293B" }}>Sync Settings</h2>
          <button onClick={onClose} style={{ background: "none", border: "none", cursor: "pointer", color: "#64748B", padding: 4, borderRadius: 6, display: "flex", alignItems: "center", transition: "color 0.15s" }} onMouseEnter={(e) => (e.currentTarget.style.color = "#1E293B")} onMouseLeave={(e) => (e.currentTarget.style.color = "#64748B")}>
            <XIcon />
          </button>
        </div>

        {/* Body */}
        <div style={{ padding: "28px 28px 0" }}>
          {loading ? (
            <div style={{ paddingBottom: 28, fontSize: 14, color: "#64748B" }}>Loading settings...</div>
          ) : (
            <>
              <label style={{ display: "block", fontSize: 14, fontWeight: 600, color: "#1E293B", marginBottom: 10 }}>Set Sync Frequency</label>
              <div style={{ position: "relative", marginBottom: 8 }}>
                <button onClick={() => setDropdownOpen((o) => !o)} style={{ width: "100%", display: "flex", alignItems: "center", justifyContent: "space-between", padding: "12px 16px", border: "1.5px solid #e2e8f0", borderRadius: 8, background: "#fff", cursor: "pointer", fontSize: 15, color: "#1E293B", fontFamily: "Inter, sans-serif", transition: "border-color 0.15s" }} onFocus={(e) => (e.currentTarget.style.borderColor = "#3B82F6")} onBlur={(e) => (e.currentTarget.style.borderColor = "#e2e8f0")}>
                  <span>{frequency}</span>
                  <ChevronDownIcon open={dropdownOpen} />
                </button>
                {dropdownOpen && (
                  <div style={{ position: "absolute", top: "calc(100% + 4px)", left: 0, right: 0, background: "#fff", border: "1.5px solid #e2e8f0", borderRadius: 8, boxShadow: "0 8px 24px rgba(30,41,59,0.12)", zIndex: 10, overflow: "hidden" }}>
                    {frequencies.map((f) => (
                      <button key={f} onClick={() => { setFrequency(f); setDropdownOpen(false); }} style={{ display: "block", width: "100%", textAlign: "left", padding: "11px 16px", background: f === frequency ? "#eff6ff" : "#fff", border: "none", cursor: "pointer", fontSize: 14, color: f === frequency ? "#3B82F6" : "#1E293B", fontFamily: "Inter, sans-serif", fontWeight: f === frequency ? 600 : 400, transition: "background 0.1s" }} onMouseEnter={(e) => { if (f !== frequency) e.currentTarget.style.background = "#f8fafc"; }} onMouseLeave={(e) => { if (f !== frequency) e.currentTarget.style.background = "#fff"; }}>
                        {f}
                      </button>
                    ))}
                  </div>
                )}
              </div>
              <p style={{ margin: "0 0 28px", fontSize: 13, color: "#64748B" }}>Updates will be pulled from SOS and pushed to StockTrim automatically.</p>
              <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 28 }}>
                <div>
                  <div style={{ fontSize: 13, fontWeight: 500, color: "#64748B", marginBottom: 2 }}>Auto-Sync Control</div>
                  <div style={{ fontSize: 15, fontWeight: 600, color: "#1E293B" }}>Enable Auto-Sync</div>
                </div>
                <button onClick={() => setAutoSync((v) => !v)} role="switch" aria-checked={autoSync} style={{ width: 52, height: 28, borderRadius: 999, border: "none", cursor: "pointer", background: autoSync ? "#3B82F6" : "#cbd5e1", position: "relative", transition: "background 0.2s", flexShrink: 0 }}>
                  <span style={{ position: "absolute", top: 3, left: autoSync ? 27 : 3, width: 22, height: 22, borderRadius: "50%", background: "#fff", boxShadow: "0 1px 4px rgba(0,0,0,0.2)", transition: "left 0.2s" }} />
                </button>
              </div>
            </>
          )}
        </div>

        {/* Footer */}
        <div style={{ display: "flex", justifyContent: "flex-end", gap: 12, padding: "18px 28px", background: "#f8fafc", borderTop: "1px solid #f1f5f9" }}>
          <button onClick={onClose} style={{ padding: "10px 22px", borderRadius: 8, border: "1.5px solid #e2e8f0", background: "#fff", color: "#1E293B", fontSize: 14, fontWeight: 600, cursor: "pointer", fontFamily: "Inter, sans-serif", transition: "border-color 0.15s" }} onMouseEnter={(e) => (e.currentTarget.style.borderColor = "#cbd5e1")} onMouseLeave={(e) => (e.currentTarget.style.borderColor = "#e2e8f0")}>
            Cancel
          </button>
          <button onClick={handleSave} disabled={saving || loading} style={{ padding: "10px 22px", borderRadius: 8, border: "none", background: saving ? "#93c5fd" : "#3B82F6", color: "#fff", fontSize: 14, fontWeight: 600, cursor: saving || loading ? "not-allowed" : "pointer", fontFamily: "Inter, sans-serif", transition: "background 0.15s", opacity: saving || loading ? 0.8 : 1 }} onMouseEnter={(e) => { if (!saving) e.currentTarget.style.background = "#2563eb"; }} onMouseLeave={(e) => { if (!saving) e.currentTarget.style.background = "#3B82F6"; }}>
            {saving ? "Saving..." : "Save Changes"}
          </button>
        </div>
      </div>
    </div>
  );
};

// ─── Toast ────────────────────────────────────────────────────────────────────
const Toast = ({ message, onClose }: { message: string; onClose: () => void }) => (
  <div style={{ position: "fixed", bottom: 28, right: 28, zIndex: 100, display: "flex", alignItems: "center", gap: 12, background: "#1E293B", color: "#fff", padding: "14px 18px", borderRadius: 10, boxShadow: "0 8px 32px rgba(30,41,59,0.28)", fontSize: 14, fontWeight: 500, animation: "slideUp 0.25s ease", maxWidth: 340 }}>
    <ToastCheckIcon />
    <span style={{ flex: 1 }}>{message}</span>
    <button onClick={onClose} style={{ background: "none", border: "none", cursor: "pointer", color: "#94a3b8", padding: 0, display: "flex", alignItems: "center", transition: "color 0.15s" }} onMouseEnter={(e) => (e.currentTarget.style.color = "#fff")} onMouseLeave={(e) => (e.currentTarget.style.color = "#94a3b8")}>
      <XIcon />
    </button>
  </div>
);

// ─── Archived Filter Bar ───────────────────────────────────────────────────────
interface ArchivedFilterProps {
  archived: boolean;
  onArchivedChange: (val: boolean) => void;
  fromDate: string;
  toDate: string;
  onFromDateChange: (val: string) => void;
  onToDateChange: (val: string) => void;
  dateError: string | null;
}

const ArchivedFilter = ({
  archived,
  onArchivedChange,
  fromDate,
  toDate,
  onFromDateChange,
  onToDateChange,
  dateError,
}: ArchivedFilterProps) => {
  const today = new Date().toISOString().split("T")[0];

  return (
    <div
      style={{
        maxWidth: 640,
        margin: "0 auto 20px",
        background: archived ? "#eff6ff" : "#f8fafc",
        border: `1.5px solid ${archived ? "#bfdbfe" : "#e2e8f0"}`,
        borderRadius: 10,
        padding: "14px 18px",
        transition: "all 0.2s ease",
      }}
    >
      {/* Checkbox row */}
      <div style={{ display: "flex", alignItems: "center", gap: 10, cursor: "pointer" }} onClick={() => onArchivedChange(!archived)}>
        {/* Custom checkbox */}
        <div
          style={{
            width: 18,
            height: 18,
            borderRadius: 5,
            border: `2px solid ${archived ? "#3B82F6" : "#cbd5e1"}`,
            background: archived ? "#3B82F6" : "#fff",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            flexShrink: 0,
            transition: "all 0.15s",
          }}
        >
          {archived && (
            <svg width="11" height="11" viewBox="0 0 12 12" fill="none">
              <path d="M2 6l3 3 5-5" stroke="#fff" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
            </svg>
          )}
        </div>
        <span style={{ color: archived ? "#1d4ed8" : "#64748B", fontWeight: 600, fontSize: 14, userSelect: "none", display: "flex", alignItems: "center", gap: 7 }}>
          <span style={{ color: archived ? "#3B82F6" : "#94a3b8" }}><ArchiveIcon /></span>
          Sync Archived Data
          <span style={{ fontSize: 11, fontWeight: 500, color: archived ? "#60a5fa" : "#94a3b8" }}>
            — Sales &amp; Purchase Orders only
          </span>
        </span>
        {/* {archived && (
          <span style={{ marginLeft: "auto", fontSize: 12, fontWeight: 500, color: "#3B82F6", background: "#dbeafe", padding: "2px 8px", borderRadius: 4, whiteSpace: "nowrap" }}>
            archived=true
          </span>
        )} */}
      </div>

      {/* Date range — only shown when archived is checked */}
      {archived && (
        <div style={{ marginTop: 14, animation: "slideUp 0.18s ease" }}>
          <div style={{ height: 1, background: "#bfdbfe", marginBottom: 14, opacity: 0.5 }} />
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}>
            {/* From */}
            <div>
              <label style={{ display: "flex", alignItems: "center", gap: 5, fontSize: 12, fontWeight: 600, color: "#2563eb", marginBottom: 6 }}>
                <CalendarIcon /> From Date
              </label>
              <input
                type="date"
                value={fromDate}
                max={toDate || today}
                onChange={(e) => onFromDateChange(e.target.value)}
                style={{
                  width: "100%",
                  padding: "9px 12px",
                  border: `1.5px solid ${dateError ? "#fca5a5" : "#93c5fd"}`,
                  borderRadius: 7,
                  fontSize: 13,
                  color: "#1E293B",
                  background: "#fff",
                  fontFamily: "Inter, sans-serif",
                  outline: "none",
                  cursor: "pointer",
                  transition: "border-color 0.15s",
                }}
                onFocus={(e) => (e.currentTarget.style.borderColor = "#3B82F6")}
                onBlur={(e) => (e.currentTarget.style.borderColor = dateError ? "#fca5a5" : "#93c5fd")}
                onClick={(e) => { try { (e.currentTarget as any).showPicker(); } catch { /* unsupported */ } }}
              />
            </div>

            {/* To */}
            <div>
              <label style={{ display: "flex", alignItems: "center", gap: 5, fontSize: 12, fontWeight: 600, color: "#2563eb", marginBottom: 6 }}>
                <CalendarIcon /> To Date
              </label>
              <input
                type="date"
                value={toDate}
                min={fromDate || undefined}
                max={today}
                onChange={(e) => onToDateChange(e.target.value)}
                style={{
                  width: "100%",
                  padding: "9px 12px",
                  border: `1.5px solid ${dateError ? "#fca5a5" : "#93c5fd"}`,
                  borderRadius: 7,
                  fontSize: 13,
                  color: "#1E293B",
                  background: "#fff",
                  fontFamily: "Inter, sans-serif",
                  outline: "none",
                  cursor: "pointer",
                  transition: "border-color 0.15s",
                }}
                onFocus={(e) => (e.currentTarget.style.borderColor = "#3B82F6")}
                onBlur={(e) => (e.currentTarget.style.borderColor = dateError ? "#fca5a5" : "#93c5fd")}
                onClick={(e) => { try { (e.currentTarget as any).showPicker(); } catch { /* unsupported */ } }}
              />
            </div>
          </div>

          {/* Validation error */}
          {dateError && (
            <p style={{ margin: "8px 0 0", fontSize: 12, color: "#dc2626", display: "flex", alignItems: "center", gap: 4 }}>
              <ErrorCircleIcon />
              {dateError}
            </p>
          )}

          {/* Helper text when both dates are set */}
          {!dateError && fromDate && toDate && (
            <p style={{ margin: "8px 0 0", fontSize: 12, color: "#2563eb", fontWeight: 500 }}>
              Syncing archived data from <strong>{fromDate}</strong> to <strong>{toDate}</strong>
            </p>
          )}
          {!dateError && (!fromDate || !toDate) && (
            <p style={{ margin: "8px 0 0", fontSize: 12, color: "#64748B" }}>
              Both dates are required to sync archived data.
            </p>
          )}
        </div>
      )}
    </div>
  );
};

// ─── App ──────────────────────────────────────────────────────────────────────
export default function App() {
  const [settingsOpen, setSettingsOpen] = useState(false);
  const [showAll, setShowAll] = useState(false);
  const [toast, setToast] = useState<string | null>(null);
  const [syncingKey, setSyncingKey] = useState<SyncKey | null>(null);

  // ── Archived filter state ──
  const [archived, setArchived] = useState(false);
  const [fromDate, setFromDate] = useState("");
  const [toDate, setToDate] = useState("");
  const [dateError, setDateError] = useState<string | null>(null);

  // ── Log state ──
  const [logs, setLogs] = useState<LogEntry[]>([]);
  const [logsLoading, setLogsLoading] = useState(true);
  const [logsError, setLogsError] = useState<string | null>(null);

  const visibleLogs = showAll ? logs : logs.slice(0, COLLAPSED_COUNT);
  const isBusy = syncingKey !== null;

  // ── Validate dates whenever they change ──
  useEffect(() => {
    if (!archived) { setDateError(null); return; }
    if (fromDate && toDate && new Date(fromDate) > new Date(toDate)) {
      setDateError("\"From\" date must be before or equal to \"To\" date.");
    } else {
      setDateError(null);
    }
  }, [fromDate, toDate, archived]);

  // ── Validate before running an archived sync (only for supported keys) ──
  const archivedReady = (key: SyncKey): boolean => {
    if (!archived || !ARCHIVED_KEYS.includes(key)) return true;
    if (!fromDate || !toDate) {
      setToast("Please select both From and To dates for archived sync.");
      return false;
    }
    if (dateError) {
      setToast(dateError);
      return false;
    }
    return true;
  };

  // ── Build query string for archived requests ──
  const buildArchivedParams = (): string => {
    const params = new URLSearchParams({ archived: "true" });
    if (fromDate) params.set("from_date", fromDate);
    if (toDate) params.set("to_date", toDate);
    return params.toString();
  };

  // ── Fetch today's logs ──
  const fetchLogs = async () => {
    setLogsLoading(true);
    setLogsError(null);
    try {
      const res = await fetch("http://localhost:8000/api/v1/logs/today");
      if (!res.ok) throw new Error(`Failed to fetch logs (HTTP ${res.status})`);
      const data: LogEntry[] = await res.json();
      setLogs(data);
    } catch (err) {
      setLogsError(err instanceof Error ? err.message : "Could not load logs.");
    } finally {
      setLogsLoading(false);
    }
  };

  useEffect(() => { fetchLogs(); }, []);

  useEffect(() => {
    if (syncingKey === null) fetchLogs();
  }, [syncingKey]);

  useEffect(() => {
    const interval = setInterval(fetchLogs, 10_000);
    return () => clearInterval(interval);
  }, []);

  useEffect(() => {
    if (toast) {
      const t = setTimeout(() => setToast(null), 10000);
      return () => clearTimeout(t);
    }
  }, [toast]);

  // ── Generic sync helper ──
  const runSync = async (
    key: SyncKey,
    endpoint: string,
    method: "POST" | "PUT",
    startMsg: string,
    successMsg: string,
  ) => {
    if (isBusy) return;
    if (!archivedReady(key)) return;

    // Only append archived params for supported order endpoints
    const isArchivedSync = archived && ARCHIVED_KEYS.includes(key);
    const url = isArchivedSync ? `${endpoint}?${buildArchivedParams()}` : endpoint;

    setSyncingKey(key);
    setToast(startMsg);
    try {
      const response = await fetch(url, { method });
      if (!response.ok) {
        let errorMessage = `Sync failed (HTTP ${response.status})`;
        try {
          const errorData = await response.json();
          errorMessage = errorData?.detail || errorData?.message || errorMessage;
        } catch { /* body wasn't JSON */ }
        setToast(errorMessage);
        return;
      }
      setToast(successMsg);
    } catch (err) {
      const message = err instanceof Error ? err.message : "An unexpected error occurred.";
      setToast(message);
    } finally {
      setSyncingKey(null);
    }
  };

  const handleSync = () =>
    runSync(
      "all",
      "http://localhost:8000/api/v1/sos-stocktrim/sync-all-data-to-stocktrim/",
      "POST",
      "Syncing all data to StockTrim...",
      "All data synced to StockTrim successfully.",
    );

  return (
    <>
      <style>{`
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
        *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
        body { font-family: 'Inter', sans-serif; background: #f1f5f9; color: #1E293B; -webkit-font-smoothing: antialiased; }
        @keyframes fadeIn  { from { opacity: 0; } to { opacity: 1; } }
        @keyframes slideUp { from { opacity: 0; transform: translateY(12px); } to { opacity: 1; transform: translateY(0); } }
        @keyframes spin    { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }
        input[type="date"]::-webkit-calendar-picker-indicator { cursor: pointer; opacity: 0.6; }
        input[type="date"]::-webkit-calendar-picker-indicator:hover { opacity: 1; }
      `}</style>

      {/* Navbar */}
      <nav style={{ position: "sticky", top: 0, zIndex: 40, background: "#fff", borderBottom: "1px solid #e2e8f0", display: "flex", alignItems: "center", justifyContent: "space-between", padding: "0 32px", height: 56 }}>
        <span style={{ fontWeight: 700, fontSize: 16, color: "#1E293B", letterSpacing: "-0.01em" }}>SOS Sync</span>
        <button onClick={() => setSettingsOpen(true)} title="Settings" style={{ background: "none", border: "none", cursor: "pointer", color: "#64748B", display: "flex", alignItems: "center", padding: 6, borderRadius: 8, transition: "color 0.15s, background 0.15s" }} onMouseEnter={(e) => { e.currentTarget.style.color = "#1E293B"; e.currentTarget.style.background = "#f1f5f9"; }} onMouseLeave={(e) => { e.currentTarget.style.color = "#64748B"; e.currentTarget.style.background = "none"; }}>
          <GearIcon />
        </button>
      </nav>

      {/* Main */}
      <main style={{ maxWidth: 900, margin: "0 auto", padding: "60px 24px 40px" }}>

        {/* ── Buttons ── */}
        <div style={{ textAlign: "center", marginBottom: 48 }}>

          {/* Primary: Full sync — disabled in archived mode (archived only applies to specific order endpoints) */}
          <button
            onClick={handleSync}
            disabled={isBusy || archived}
            title={archived ? "Disabled in archived mode — use the Sales/Purchase Order buttons below" : undefined}
            style={{
              display: "inline-flex",
              alignItems: "center",
              gap: 10,
              background: syncingKey === "all" ? "#2563eb" : "#3B82F6",
              color: "#fff",
              padding: "15px 36px",
              borderRadius: 10,
              border: "none",
              fontSize: 16,
              fontWeight: 600,
              cursor: isBusy || archived ? "not-allowed" : "pointer",
              fontFamily: "Inter, sans-serif",
              letterSpacing: "-0.01em",
              boxShadow: "0 4px 16px rgba(59,130,246,0.30)",
              transition: "background 0.15s, transform 0.1s, box-shadow 0.15s",
              opacity: isBusy || archived ? 0.45 : 1,
            }}
            onMouseEnter={(e) => { if (!isBusy && !archived) { e.currentTarget.style.background = "#2563eb"; e.currentTarget.style.boxShadow = "0 6px 20px rgba(59,130,246,0.38)"; } }}
            onMouseLeave={(e) => { if (!isBusy && !archived) { e.currentTarget.style.background = "#3B82F6"; e.currentTarget.style.boxShadow = "0 4px 16px rgba(59,130,246,0.30)"; } }}
            onMouseDown={(e) => { if (!isBusy && !archived) e.currentTarget.style.transform = "scale(0.98)"; }}
            onMouseUp={(e) => { e.currentTarget.style.transform = "scale(1)"; }}
          >
            {syncingKey === "all" ? <Spinner size={20} color="#fff" /> : <SyncIcon />}
            {syncingKey === "all" ? "Syncing..." : "SOS → StockTrim Sync"}
          </button>

          {/* ── Archived filter bar ── */}
          <div style={{ marginTop: 20 }}>
            <ArchivedFilter
              archived={archived}
              onArchivedChange={(val) => {
                setArchived(val);
                if (!val) { setFromDate(""); setToDate(""); setDateError(null); }
              }}
              fromDate={fromDate}
              toDate={toDate}
              onFromDateChange={setFromDate}
              onToDateChange={setToDate}
              dateError={dateError}
            />
          </div>

          {/* Secondary: Individual sync buttons */}
          <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: 12, maxWidth: 640, margin: "0 auto 0" }}>
            {INDIVIDUAL_SYNCS.map(({ key, label, endpoint, method, startMsg, successMsg }) => {
              const isThisLoading = syncingKey === key;
              const supportsArchived = ARCHIVED_KEYS.includes(key);
              // In archived mode: non-order buttons are fully disabled; order buttons are active with archived styling
              const isDisabledByArchived = archived && !supportsArchived;
              const isDisabled = isBusy || isDisabledByArchived;
              const showArchivedStyle = archived && supportsArchived;

              return (
                <button
                  key={key}
                  onClick={() => runSync(key, endpoint, method, startMsg, successMsg)}
                  disabled={isDisabled}
                  title={isDisabledByArchived ? "Not available in archived mode" : undefined}
                  style={{
                    display: "inline-flex",
                    alignItems: "center",
                    justifyContent: "center",
                    gap: 7,
                    background: isThisLoading
                      ? "#f0f9ff"
                      : showArchivedStyle
                      ? "#eff6ff"
                      : "#fff",
                    color: isThisLoading || showArchivedStyle ? "#2563eb" : "#374151",
                    border: `1.5px solid ${
                      isThisLoading
                        ? "#93c5fd"
                        : showArchivedStyle
                        ? "#bfdbfe"
                        : "#e2e8f0"
                    }`,
                    padding: "11px 14px",
                    borderRadius: 9,
                    fontSize: 13,
                    fontWeight: 600,
                    cursor: isDisabled ? "not-allowed" : "pointer",
                    fontFamily: "Inter, sans-serif",
                    letterSpacing: "-0.01em",
                    transition: "all 0.15s",
                    opacity: isDisabledByArchived ? 0.35 : isBusy && !isThisLoading ? 0.45 : 1,
                    boxShadow: isThisLoading ? "0 0 0 3px rgba(59,130,246,0.12)" : "none",
                    whiteSpace: "nowrap",
                  }}
                  onMouseEnter={(e) => {
                    if (!isDisabled) {
                      e.currentTarget.style.borderColor = "#93c5fd";
                      e.currentTarget.style.background = "#f0f9ff";
                      e.currentTarget.style.color = "#2563eb";
                    }
                  }}
                  onMouseLeave={(e) => {
                    if (!isDisabled && !isThisLoading) {
                      e.currentTarget.style.borderColor = showArchivedStyle ? "#bfdbfe" : "#e2e8f0";
                      e.currentTarget.style.background = showArchivedStyle ? "#eff6ff" : "#fff";
                      e.currentTarget.style.color = showArchivedStyle ? "#2563eb" : "#374151";
                    }
                  }}
                >
                  {isThisLoading ? (
                    <Spinner size={14} color="#2563eb" />
                  ) : showArchivedStyle ? (
                    <ArchiveIcon />
                  ) : (
                    <SyncIcon />
                  )}
                  {isThisLoading
                    ? "Syncing..."
                    : showArchivedStyle
                    ? `${label} (Archived)`
                    : label}
                </button>
              );
            })}
          </div>
        </div>

        {/* ── Sync Logs Card ── */}
        <div style={{ background: "#fff", borderRadius: 14, border: "1px solid #e2e8f0", boxShadow: "0 2px 12px rgba(30,41,59,0.06)", overflow: "hidden" }}>

          {/* Card Header */}
          <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", padding: "20px 28px", borderBottom: "1px solid #f1f5f9" }}>
            <div style={{ display: "flex", alignItems: "center", gap: 10, fontWeight: 700, fontSize: 18, color: "#1E293B" }}>
              <span style={{ color: "#64748B" }}><LogsIcon /></span>
              Sync Logs
              <span style={{ fontSize: 12, fontWeight: 500, color: "#94a3b8", marginLeft: 2 }}>
                {new Date().toLocaleDateString([], { day: "2-digit", month: "short", year: "numeric" })}
              </span>
            </div>
            <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
              {!logsLoading && logs.length > 0 && (
                <span style={{ fontSize: 12, fontWeight: 600, color: "#64748B", background: "#f1f5f9", padding: "5px 12px", borderRadius: 6 }}>
                  {logs.length} {logs.length === 1 ? "entry" : "entries"}
                </span>
              )}
              <button
                onClick={fetchLogs}
                disabled={logsLoading}
                title="Refresh logs"
                style={{ display: "flex", alignItems: "center", gap: 6, background: "none", border: "1.5px solid #e2e8f0", borderRadius: 7, padding: "5px 12px", cursor: logsLoading ? "not-allowed" : "pointer", color: "#64748B", fontSize: 13, fontWeight: 600, fontFamily: "Inter, sans-serif", transition: "all 0.15s", opacity: logsLoading ? 0.5 : 1 }}
                onMouseEnter={(e) => { if (!logsLoading) { e.currentTarget.style.borderColor = "#cbd5e1"; e.currentTarget.style.color = "#1E293B"; } }}
                onMouseLeave={(e) => { e.currentTarget.style.borderColor = "#e2e8f0"; e.currentTarget.style.color = "#64748B"; }}
              >
                <span style={{ animation: logsLoading ? "spin 0.75s linear infinite" : "none", display: "flex" }}>
                  <RefreshIcon />
                </span>
                Refresh
              </button>
            </div>
          </div>

          {/* Log Entries */}
          <div style={{ padding: "8px 0" }}>
            {logsLoading ? (
              <div style={{ padding: "32px 28px", display: "flex", alignItems: "center", gap: 10, color: "#64748B", fontSize: 14 }}>
                <Spinner size={16} color="#64748B" /> Loading today's logs...
              </div>
            ) : logsError ? (
              <div style={{ padding: "24px 28px", color: "#dc2626", fontSize: 14 }}>{logsError}</div>
            ) : logs.length === 0 ? (
              <div style={{ padding: "32px 28px", color: "#94a3b8", fontSize: 14, textAlign: "center" }}>
                No log entries for today yet.
              </div>
            ) : (
              visibleLogs.map((log, i) => (
                <div
                  key={log.id}
                  style={{ display: "flex", alignItems: "center", justifyContent: "space-between", padding: "16px 28px", borderBottom: i < visibleLogs.length - 1 ? "1px solid #f8fafc" : "none", gap: 16, flexWrap: "wrap", animation: "fadeIn 0.2s ease" }}
                >
                  <div style={{ display: "flex", alignItems: "center", gap: 16, flex: 1, minWidth: 0 }}>
                    <Badge level={log.status} />
                    <div style={{ minWidth: 0 }}>
                      <div style={{ fontSize: 12, color: "#94a3b8", marginBottom: 3, fontWeight: 500 }}>
                        {log.actionType}
                      </div>
                      <div style={{ fontSize: 14, color: log.status === "Error" ? "#1E293B" : "#374151", fontWeight: log.status === "Error" ? 600 : 400, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                        {log.message}
                      </div>
                    </div>
                  </div>
                  <span style={{ fontSize: 13, color: "#94a3b8", whiteSpace: "nowrap", fontVariantNumeric: "tabular-nums", flexShrink: 0 }}>
                    {new Date(log.timestamp).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" })}
                  </span>
                </div>
              ))
            )}
          </div>

          {/* See More / See Less */}
          {logs.length > COLLAPSED_COUNT && (
            <div style={{ borderTop: "1px solid #f1f5f9", padding: "16px 0", textAlign: "center" }}>
              <button
                onClick={() => setShowAll((v) => !v)}
                style={{ background: "none", border: "none", cursor: "pointer", color: "#3B82F6", fontSize: 14, fontWeight: 600, fontFamily: "Inter, sans-serif", display: "inline-flex", alignItems: "center", gap: 6, padding: "4px 8px", borderRadius: 6, transition: "background 0.15s" }}
                onMouseEnter={(e) => (e.currentTarget.style.background = "#eff6ff")}
                onMouseLeave={(e) => (e.currentTarget.style.background = "none")}
              >
                {showAll ? "See Less" : `See All ${logs.length} Entries`}
                <ChevronDownIcon open={showAll} />
              </button>
            </div>
          )}
        </div>
      </main>

      {settingsOpen && <SettingsModal onClose={() => setSettingsOpen(false)} />}
      {toast && <Toast message={toast} onClose={() => setToast(null)} />}
    </>
  );
}