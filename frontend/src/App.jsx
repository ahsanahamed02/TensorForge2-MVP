import { useEffect, useMemo, useRef, useState } from "react";
import "./App.css";

const API_URL = import.meta.env.PROD
  ? "/api"
  : (import.meta.env.VITE_API_URL || "http://localhost:8000").replace(/\/$/, "");
const API_KEY = import.meta.env.DEV ? import.meta.env.VITE_API_KEY || "" : "";
const MODEL_VERSION = "v1.2";
const MAX_BATCH = 100;

const ICONS = {
  dashboard: "M3 3h7v9H3zM14 3h7v5h-7zM14 12h7v9h-7zM3 16h7v5H3z",
  single: "M4 5h16v11H9l-5 4z",
  batch: "M12 3l9 5-9 5-9-5zM3 13l9 5 9-5",
  insights: "M4 20V10M10 20V4M16 20v-7M22 20H2",
  status: "M3 12h4l3-8 4 16 3-8h4",
  send: "M22 2L11 13M22 2l-7 20-4-9-9-4z",
  route: "M6 17a2 2 0 1 0 0 4 2 2 0 0 0 0-4M18 3a2 2 0 1 0 0 4 2 2 0 0 0 0-4M8 19h7a3 3 0 0 0 0-6H9a3 3 0 0 1 0-6h7",
  alert: "M12 3l10 18H2zM12 10v5M12 18h.01",
  download: "M12 3v12M7 10l5 5 5-5M4 21h16",
  check: "M5 12l5 5L20 7",
  x: "M6 6l12 12M18 6L6 18",
  payment_refund: "M2 5h20v14H2zM2 10h20M6 15h4",
  order_missing_wrong: "M21 8l-9-5-9 5v8l9 5 9-5zM3 8l9 5 9-5M12 13v8",
  delivery_delay: "M3 6h11v10H3zM14 10h4l3 3v3h-7M7 16a2 2 0 1 0 0 4 2 2 0 0 0 0-4M17 16a2 2 0 1 0 0 4 2 2 0 0 0 0-4",
  food_quality: "M4 11h16a8 8 0 0 1-16 0zM9 4c0 1.5 1 1.5 1 3M14 4c0 1.5 1 1.5 1 3",
  app_technical: "M7 2h10v20H7zM11 18h2",
  account_promo: "M12 4a4 4 0 1 0 0 8 4 4 0 0 0 0-8M4 21a8 8 0 0 1 16 0",
  lost_item: "M11 4a7 7 0 1 0 0 14 7 7 0 0 0 0-14M21 21l-5-5",
  ride_trip_issue: "M5 17h14v-5l-2-5H7l-2 5zM5 12h14M8 15.5h.01M16 15.5h.01",
  safety_conduct: "M12 3l8 3v6c0 5-3.5 8-8 9-4.5-1-8-4-8-9V6z",
  general_inquiry: "M4 5h16v11H9l-5 4z",
  spam_irrelevant: "M12 3a9 9 0 1 0 0 18 9 9 0 0 0 0-18M5.6 5.6l12.8 12.8",
};

const NAV = [
  ["dashboard", "Dashboard", "Support routing dashboard"],
  ["single", "Single ticket", "Single ticket analysis"],
  ["batch", "Batch analysis", "Batch ticket analysis"],
  ["insights", "Insights & evaluation", "Insights & live evaluation"],
  ["status", "System status", "System status"],
];

const SAMPLES = [
  ["English", "Duplicate payment", "I was charged twice for my order and need a refund today."],
  ["Sinhala", "", "මගේ ඇණවුම තවම ලැබුණේ නැහැ, ඉක්මනින් බලන්න."],
  ["Tamil", "", "என் ஆர்டர் இன்னும் வரவில்லை, தயவு செய்து உதவுங்கள்."],
  ["Singlish", "", "Order eka innum deliver una na, driver call karanna one."],
  ["Safety", "", "The driver behaved inappropriately and I felt unsafe."],
  ["App bug", "", "App crashes after the latest update when I open my orders."],
];

const label = (v) => (v ? String(v).replaceAll("_", " ").replace(/\b\w/g, (c) => c.toUpperCase()) : "None");
const pct = (v) => Math.round((v || 0) * 100);
const band = (v) => (pct(v) >= 70 ? "High" : pct(v) >= 30 ? "Medium" : "Low");
const review = (v) => pct(v) < 30;
const bandCls = { High: "hi", Medium: "md", Low: "lo" };
const uid = () => `${Date.now()}-${Math.random().toString(36).slice(2, 7)}`;

const store = {
  get: (k, d) => { try { return JSON.parse(localStorage.getItem(k)) ?? d; } catch { return d; } },
  set: (k, v) => { try { localStorage.setItem(k, JSON.stringify(v)); } catch { /* ignore */ } },
};

const headers = () => ({ "Content-Type": "application/json", ...(API_KEY ? { "X-API-Key": API_KEY } : {}) });
const api = async (path, opts) => {
  const r = await fetch(`${API_URL}${path}`, opts);
  if (!r.ok) {
    let m = "Request failed.";
    try { const d = await r.json(); m = typeof d.detail === "string" ? d.detail : d?.error?.message || d?.detail?.message || m; } catch { /* ignore */ }
    throw new Error(m);
  }
  return r.json();
};
const post = (p, b) => api(p, { method: "POST", headers: headers(), body: JSON.stringify(b) });

function Icon({ name, size = 18 }) {
  return (
    <svg className="ico" width={size} height={size} viewBox="0 0 24 24" aria-hidden="true">
      <path d={ICONS[name] || ICONS.general_inquiry} />
    </svg>
  );
}

const Panel = ({ label: l, title, chip, children, className = "", i = 0 }) => (
  <section className={`panel ${className}`} style={{ animationDelay: `${i * 70}ms` }}>
    {(l || title || chip) && (
      <div className="ph">
        <div>{l && <p className="label">{l}</p>}{title && <h2>{title}</h2>}</div>
        {chip}
      </div>
    )}
    {children}
  </section>
);

const Stat = ({ label: l, value, note, i = 0 }) => (
  <div className="stat" style={{ animationDelay: `${i * 70}ms` }}>
    <span>{l}</span><strong>{value}</strong><small>{note}</small>
  </div>
);

const Empty = ({ title, text }) => (
  <div className="empty"><Icon name="route" size={26} /><h3>{title}</h3><p>{text}</p></div>
);

const Meter = ({ value }) => (
  <div className={`meter ${bandCls[band(value)]}`} role="progressbar" aria-valuenow={pct(value)}>
    <i style={{ width: `${pct(value)}%` }} />
  </div>
);

function Ring({ value = 0 }) {
  return (
    <div className="ring">
      <svg viewBox="0 0 120 120">
        <circle cx="60" cy="60" r="50" className="t" />
        <circle cx="60" cy="60" r="50" className="v" stroke={`var(--${value >= 0.7 ? "ok" : value >= 0.3 ? "warn" : "bad"})`}
          style={{ "--o": 314 - 314 * Math.min(1, Math.max(0, value)) }} />
      </svg>
      <div><strong>{pct(value)}%</strong><span>confidence</span></div>
    </div>
  );
}

function Feedback({ item, onMark }) {
  if (!item) return null;
  return (
    <div className="fb">
      Was this routing correct?
      <button className={`btn sm ${item.ok === true ? "sel-ok" : ""}`} onClick={() => onMark(item._id, true)}><Icon name="check" size={14} />Yes</button>
      <button className={`btn sm ${item.ok === false ? "sel-no" : ""}`} onClick={() => onMark(item._id, false)}><Icon name="x" size={14} />No</button>
    </div>
  );
}

function Palette({ actions, onClose }) {
  const [q, setQ] = useState("");
  const list = actions.filter((a) => a.name.toLowerCase().includes(q.toLowerCase()));
  const run = (a) => { a.run(); onClose(); };
  return (
    <div className="ov" onClick={onClose}>
      <div className="pal" role="dialog" aria-label="Command palette" onClick={(e) => e.stopPropagation()}>
        <input autoFocus placeholder="Type a command..." value={q} onChange={(e) => setQ(e.target.value)}
          onKeyDown={(e) => { if (e.key === "Enter" && list[0]) run(list[0]); if (e.key === "Escape") onClose(); }} />
        {list.map((a) => (<button key={a.name} onClick={() => run(a)}><Icon name={a.icon} size={16} />{a.name}</button>))}
        {!list.length && <p className="mute" style={{ padding: 12 }}>No matching command.</p>}
      </div>
    </div>
  );
}

export default function App() {
  const [view, setView] = useState("dashboard");
  const [health, setHealth] = useState(null);
  const [hLoading, setHLoading] = useState(false);
  const [hError, setHError] = useState("");
  const [channel, setChannel] = useState("email");
  const [subject, setSubject] = useState("");
  const [text, setText] = useState("");
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [batchText, setBatchText] = useState("");
  const [batchRes, setBatchRes] = useState([]);
  const [bLoading, setBLoading] = useState(false);
  const [filter, setFilter] = useState("all");
  const [q, setQ] = useState("");
  const [over, setOver] = useState(false);
  const [log, setLog] = useState(() => store.get("riq-log", []));
  const [toast, setToast] = useState(null);
  const [pal, setPal] = useState(false);
  const fileRef = useRef(null);

  const online = health?.status === "ok";
  const notify = (msg, kind = "ok") => { setToast({ msg, kind }); setTimeout(() => setToast(null), 3200); };

  useEffect(() => { store.set("riq-log", log.slice(0, 200)); }, [log]);

  const checkHealth = async () => {
    setHLoading(true); setHError("");
    try { setHealth(await api("/health")); }
    catch (e) { setHealth(null); setHError(e.message || "Unable to reach API."); }
    finally { setHLoading(false); }
  };
  useEffect(() => { checkHealth(); }, []);

  useEffect(() => {
    const onKey = (e) => { if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "k") { e.preventDefault(); setPal((p) => !p); } };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);

  const record = (items) => setLog((l) => [...items.map((i) => ({ ...i, ok: null, at: Date.now() })), ...l].slice(0, 200));
  const mark = (id, ok) => setLog((l) => l.map((x) => (x._id === id ? { ...x, ok: x.ok === ok ? null : ok } : x)));
  const cur = log.find((x) => x._id === result?._id);

  const analyze = async () => {
    if (!text.trim()) return notify("Ticket message is required.", "err");
    setLoading(true); setResult(null);
    const t0 = performance.now();
    try {
      const d = await post("/predict", { ticket_id: `WEB-${Date.now()}`, channel, subject: subject.trim(), text: text.trim() });
      const item = { ...d, _id: uid(), _text: text.trim(), _ms: Math.round(performance.now() - t0) };
      setResult(item); record([item]);
    } catch (e) { notify(e.message || "Unable to connect to API.", "err"); }
    finally { setLoading(false); }
  };

  const lines = useMemo(() => {
    const l = batchText.split("\n").map((x) => x.trim()).filter(Boolean);
    const f = (l[0] || "").toLowerCase();
    return f.includes("id") && f.includes("subject") && f.includes("text") ? l.slice(1) : l;
  }, [batchText]);

  const analyzeBatch = async () => {
    if (!lines.length) return notify("Enter at least one ticket.", "err");
    if (lines.length > MAX_BATCH) return notify(`Maximum ${MAX_BATCH} tickets per synchronous batch.`, "err");
    setBLoading(true); setBatchRes([]);
    try {
      const ts = Date.now();
      const d = await post("/predict/batch", { tickets: lines.map((t, i) => ({ ticket_id: `BATCH-${ts}-${i + 1}`, channel: "email", subject: "", text: t })) });
      const arr = (Array.isArray(d) ? d : d.predictions || d.results || []).map((r, i) => ({ ...r, _id: uid(), _text: lines[i] || "" }));
      setBatchRes(arr); record(arr); notify(`${arr.length} tickets routed.`);
    } catch (e) { notify(e.message || "Unable to run batch prediction.", "err"); }
    finally { setBLoading(false); }
  };

  const readFile = (file) => {
    if (!file) return;
    const r = new FileReader();
    r.onload = () => { setBatchText(String(r.result)); notify(`Loaded ${file.name}`); };
    r.readAsText(file);
  };

  const exportCsv = () => {
    const esc = (v) => `"${String(v ?? "").replaceAll('"', '""')}"`;
    const rows = [["text", "category", "team", "urgent", "confidence", "needs_review"],
      ...batchRes.map((r) => [r._text, r.category, r.team, r.is_urgent, pct(r.confidence), review(r.confidence)])];
    const url = URL.createObjectURL(new Blob([rows.map((r) => r.map(esc).join(",")).join("\n")], { type: "text/csv" }));
    Object.assign(document.createElement("a"), { href: url, download: "routeiq-results.csv" }).click();
    URL.revokeObjectURL(url);
  };

  const shown = batchRes.filter((r) =>
    (filter === "all" || (filter === "urgent" && r.is_urgent) || (filter === "review" && review(r.confidence))) &&
    (!q || `${r._text} ${r.category} ${r.team}`.toLowerCase().includes(q.toLowerCase())));

  const S = useMemo(() => {
    const n = log.length;
    const judged = log.filter((x) => x.ok !== null);
    const right = judged.filter((x) => x.ok).length;
    const cats = {};
    log.forEach((x) => { cats[x.category || "unknown"] = (cats[x.category || "unknown"] || 0) + 1; });
    return {
      n,
      urgent: log.filter((x) => x.is_urgent).length,
      rev: log.filter((x) => review(x.confidence)).length,
      avg: n ? pct(log.reduce((s, x) => s + (x.confidence || 0), 0) / n) : 0,
      hi: log.filter((x) => band(x.confidence) === "High").length,
      md: log.filter((x) => band(x.confidence) === "Medium").length,
      lo: log.filter((x) => band(x.confidence) === "Low").length,
      judged: judged.length,
      agree: judged.length ? Math.round((right / judged.length) * 100) : null,
      cats: Object.entries(cats).sort((a, b) => b[1] - a[1]),
      wrong: judged.filter((x) => !x.ok),
    };
  }, [log]);

  const go = (id) => () => setView(id);
  const actions = [
    ...NAV.map(([id, name]) => ({ name: `Go to ${name}`, icon: id, run: go(id) })),
    { name: "Clear session history", icon: "x", run: () => { setLog([]); notify("History cleared."); } },
    { name: "Refresh API health", icon: "status", run: checkHealth },
  ];

  const title = NAV.find(([id]) => id === view)?.[2] || "RouteIQ";

  const dashboard = (
    <>
      <div className="hero">
        <div>
          <span className="pill">AI Support Intelligence</span>
          <h1>AI Support Ticket <span>Classifier & Router</span></h1>
          <p>RouteIQ classifies multilingual support tickets, detects urgency, and routes each one to the right team. Low-confidence cases are flagged for human review instead of being trusted blindly.</p>
          <div className="row" style={{ marginTop: 22 }}>
            <button className="btn pri" onClick={go("single")}><Icon name="single" size={17} />Analyze one ticket</button>
            <button className="btn" onClick={go("batch")}><Icon name="batch" size={17} />Analyze batch</button>
            <span className="mute">Press <span className="kbd">Ctrl K</span> for commands</span>
          </div>
        </div>
        <div className="demo" aria-hidden="true">
          <div className="card"><span className="mute">Customer ticket</span><b>My Order Is Late</b></div>
          <div className="card"><span className="mute">AI classification</span><b>Delivery Delay</b></div>
          <div className="card live"><span className="mute">Routed team</span><b>Delivery Operations</b></div>
        </div>
      </div>
      <div className="grid4">
        <Stat i={0} label="Category macro F1" value="0.884" note="Validation split, 800 tickets" />
        <Stat i={1} label="Urgency accuracy" value="97.1%" note="Validation split" />
        <Stat i={2} label="Categories" value="11" note="Automated routing classes" />
        <Stat i={3} label="API" value={online ? "Healthy" : "Offline"} note="Live backend health" />
      </div>
      <div className="cols">
        <Panel i={4} label="How it works" title="From ticket to team in seconds">
          <div className="route">
            <span className="node">1 · Ticket input</span><i /><span className="node c">2 · Category + urgency</span><i /><span className="node t">3 · Team routing</span><i /><span className="node">4 · Human review if unsure</span>
          </div>
        </Panel>
        <Panel i={5} label="Languages" title="Multilingual support">
          <div className="row">{["English", "Sinhala", "Tamil", "Romanized & mixed"].map((l) => <span className="chip" key={l}>{l}</span>)}</div>
        </Panel>
      </div>
    </>
  );

  const single = (
    <>
      <div className="grid4">
        <Stat label="API" value={online ? "Healthy" : "Offline"} note="Live connection" />
        <Stat label="Model" value={health?.model_version || MODEL_VERSION} note="Active inference" />
        <Stat label="API round-trip" value={result ? `${result._ms} ms` : "-"} note="Last browser request" />
        <Stat label="Session accuracy" value={S.agree === null ? "-" : `${S.agree}%`} note={`${S.judged} reviewed by you`} />
      </div>
      <div className="cols">
        <Panel label="Single ticket" title="Analyze a support request" chip={<span className="chip ok">Live inference</span>}>
          <div className="row" style={{ marginBottom: 14 }}>
            <span className="mute">Try a sample:</span>
            {SAMPLES.map(([n, s, t]) => (<button key={n} className="chip btn-chip" onClick={() => { setSubject(s); setText(t); setResult(null); }}>{n}</button>))}
          </div>
          <div className="form">
            <div className="fg"><label htmlFor="ch">Channel</label>
              <select id="ch" value={channel} onChange={(e) => setChannel(e.target.value)}>
                <option value="email">Email</option><option value="chat">Chat</option><option value="call_transcript">Call transcript</option>
              </select></div>
            <div className="fg"><label htmlFor="sb">Subject</label>
              <input id="sb" value={subject} onChange={(e) => setSubject(e.target.value)} placeholder="Example: Duplicate payment" /></div>
            <div className="fg full"><label htmlFor="tx">Customer message</label>
              <textarea id="tx" value={text} onChange={(e) => setText(e.target.value)} placeholder="Paste the support ticket here..."
                onKeyDown={(e) => { if ((e.ctrlKey || e.metaKey) && e.key === "Enter") analyze(); }} /></div>
          </div>
          <div className="actions">
            <div><strong style={{ fontSize: 13 }}>{text.trim() ? "Ready to analyze" : "Waiting for ticket"}</strong><div className="mute">{text.length} characters · Ctrl+Enter to run</div></div>
            <div className="row">
              <button className="btn" onClick={() => { setSubject(""); setText(""); setResult(null); }}>Clear</button>
              <button className="btn pri" onClick={analyze} disabled={loading || !text.trim()}>
                {loading ? <span className="spin" /> : <Icon name="send" size={16} />}{loading ? "Analyzing..." : "Analyze ticket"}
              </button>
            </div>
          </div>
        </Panel>
        <Panel i={1} label="Prediction" title="Routing decision" chip={result?.model_version && <span className="chip">Model {result.model_version}</span>}>
          {loading ? (<><div className="skel" style={{ height: 90 }} /><div className="skel" /><div className="skel" style={{ width: "70%" }} /></>)
            : !result ? <Empty title="Ready for analysis" text="Category, urgency, confidence and the support team will appear here." />
            : (
              <div className="pred">
                <div className="ptop">
                  <Ring value={result.confidence} />
                  <div>
                    <span className="mute">Primary category</span>
                    <h3><Icon name={result.category} size={20} />{label(result.category)}</h3>
                    <div className="row">
                      {result.is_urgent && <span className="chip bad"><Icon name="alert" size={12} /> Urgent</span>}
                      <span className={`chip ${review(result.confidence) ? "warn" : "ok"}`}>{band(result.confidence)} confidence</span>
                      {review(result.confidence) && <span className="chip warn">Manual review recommended</span>}
                    </div>
                  </div>
                </div>
                <div className="route"><span className="node">Ticket</span><i /><span className="node c">{label(result.category)}</span><i /><span className="node t">{result.team}</span></div>
                <div className="kv">
                  <div><span>Assigned team</span><strong>{result.team || "-"}</strong></div>
                  <div><span>Urgency</span><strong className={result.is_urgent ? "bad-t" : "ok-t"}>{result.is_urgent ? "Urgent" : "Normal"}</strong></div>
                  <div><span>Secondary</span><strong>{label(result.secondary_category)}</strong></div>
                  <div><span>Model</span><strong>{result.model_version || MODEL_VERSION}</strong></div>
                </div>
                <Feedback item={cur} onMark={mark} />
                <p className="mute">Confidence is a decision-score indicator, not a calibrated probability.</p>
              </div>
            )}
        </Panel>
      </div>
    </>
  );

  const batch = (
    <>
      <Panel label="Batch analysis" title="Analyze multiple support tickets" chip={<span className="chip">/predict/batch</span>}>
        <div className={`fg drop ${over ? "over" : ""}`}
          onDragOver={(e) => { e.preventDefault(); setOver(true); }} onDragLeave={() => setOver(false)}
          onDrop={(e) => { e.preventDefault(); setOver(false); readFile(e.dataTransfer.files[0]); }}>
          <label htmlFor="bt">One ticket per line - or drop a .txt / .csv file</label>
          <textarea id="bt" rows="7" value={batchText} onChange={(e) => setBatchText(e.target.value)}
            placeholder={"Payment was charged twice.\nOrder innum deliver aagala.\nApp crashes after the latest update."} />
        </div>
        <div className="actions">
          <div><strong style={{ fontSize: 13 }}>{lines.length} ticket{lines.length === 1 ? "" : "s"} ready</strong>
            <div className={`mute ${lines.length > MAX_BATCH ? "bad-t" : ""}`}>Up to {MAX_BATCH} per synchronous request</div></div>
          <div className="row">
            <input ref={fileRef} type="file" accept=".txt,.csv" hidden onChange={(e) => readFile(e.target.files[0])} />
            <button className="btn" onClick={() => fileRef.current?.click()}>Upload file</button>
            <button className="btn" onClick={() => { setBatchText(""); setBatchRes([]); }}>Clear</button>
            <button className="btn pri" onClick={analyzeBatch} disabled={bLoading || !lines.length}>
              {bLoading ? <span className="spin" /> : <Icon name="send" size={16} />}{bLoading ? "Analyzing..." : "Run batch analysis"}
            </button>
          </div>
        </div>
      </Panel>
      <Panel className="mt" i={1} label="Results" title="Routing predictions"
        chip={batchRes.length > 0 && <button className="btn sm" onClick={exportCsv}><Icon name="download" size={14} />Export CSV</button>}>
        {bLoading ? (<><div className="skel" /><div className="skel" /><div className="skel" /></>)
          : !batchRes.length ? <Empty title="No batch results yet" text="Run batch analysis to see categories, urgency and routing." />
          : (
            <>
              <div className="row" style={{ marginBottom: 14 }}>
                {[["all", `All (${batchRes.length})`], ["urgent", `Urgent (${batchRes.filter((r) => r.is_urgent).length})`], ["review", `Needs review (${batchRes.filter((r) => review(r.confidence)).length})`]].map(([k, n]) => (
                  <button key={k} className={`chip btn-chip ${filter === k ? "sel" : ""}`} onClick={() => setFilter(k)}>{n}</button>))}
                <input className="search" placeholder="Search text, category, team..." value={q} onChange={(e) => setQ(e.target.value)} aria-label="Search results" />
              </div>
              <div className="tw">
                <table>
                  <thead><tr><th>#</th><th>Ticket</th><th>Category</th><th>Team</th><th>Urgency</th><th>Confidence</th><th>Correct?</th></tr></thead>
                  <tbody>
                    {shown.map((r, i) => {
                      const it = log.find((x) => x._id === r._id);
                      return (
                        <tr key={r._id}>
                          <td className="mute">{i + 1}</td>
                          <td><div className="snip" title={r._text}>{r._text}</div></td>
                          <td><span className="cell"><Icon name={r.category} size={15} />{label(r.category)}</span></td>
                          <td>{r.team}</td>
                          <td className={r.is_urgent ? "bad-t" : "ok-t"}>{r.is_urgent ? "Urgent" : "Normal"}</td>
                          <td style={{ minWidth: 120 }}><strong>{pct(r.confidence)}%</strong> <span className="mute">{band(r.confidence)}{review(r.confidence) ? " · Review" : ""}</span><Meter value={r.confidence} /></td>
                          <td><div className="row" style={{ gap: 4 }}>
                            <button className={`btn sm ${it?.ok === true ? "fb sel-ok" : ""}`} aria-label="Mark correct" onClick={() => mark(r._id, true)}><Icon name="check" size={13} /></button>
                            <button className={`btn sm ${it?.ok === false ? "fb sel-no" : ""}`} aria-label="Mark wrong" onClick={() => mark(r._id, false)}><Icon name="x" size={13} /></button>
                          </div></td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
              {!shown.length && <p className="mute" style={{ marginTop: 12 }}>No rows match this filter.</p>}
            </>
          )}
      </Panel>
    </>
  );

  const insights = (
    <>
      <div className="grid4">
        <Stat label="Tickets this session" value={S.n} note="Single + batch" />
        <Stat label="Urgent rate" value={`${S.n ? pct(S.urgent / S.n) : 0}%`} note={`${S.urgent} urgent`} />
        <Stat label="Review queue" value={S.rev} note="Confidence below 30%" />
        <Stat label="Reviewer agreement" value={S.agree === null ? "-" : `${S.agree}%`} note={`${S.judged} tickets reviewed`} />
      </div>
      <div className="cols">
        <Panel label="Evaluation" title="Model card" chip={<span className="chip">v1.2</span>}>
          <div className="kv">
            <div><span>Category macro F1</span><strong>0.884</strong></div>
            <div><span>Category validation score</span><strong>88.1%</strong></div>
            <div><span>Urgency validation accuracy</span><strong>97.1%</strong></div>
            <div><span>Validation set</span><strong>800 tickets · 11 classes</strong></div>
            <div className="full" style={{ gridColumn: "1/-1" }}><span>Category model</span><strong>Word + Character TF-IDF + LinearSVC</strong></div>
          </div>
          <p className="note">Offline metrics were measured on the 800-ticket project validation split. The category result is validation-tuned, so it should not be presented as independent test accuracy. Confidence is a decision-score indicator, not a calibrated probability.</p>
        </Panel>
        <Panel i={1} label="Live evaluation" title="Confidence bands">
          <div className="bars">
            {[["High · 70%+", S.hi, "hi"], ["Medium · 30-69%", S.md, "md"], ["Low · below 30%", S.lo, "lo"]].map(([n, c, k]) => (
              <div key={n}><div className="bh"><span>{n}</span><strong>{c}</strong></div>
                <div className={`meter ${k}`}><i style={{ width: `${S.n ? (c / S.n) * 100 : 0}%` }} /></div></div>))}
          </div>
          <p className="note">Mark predictions as correct or wrong in Single and Batch. Reviewer agreement is a live human-review signal for this session, not the model's offline validation accuracy.</p>
        </Panel>
      </div>
      <div className="cols mt">
        <Panel i={2} label="Categories" title="Ticket distribution">
          {!S.cats.length ? <Empty title="No data yet" text="Analyze tickets to see the distribution." />
            : (<div className="bars">{S.cats.map(([c, n]) => (
              <div key={c}><div className="bh"><span>{label(c)}</span><strong>{n} · {pct(n / S.n)}%</strong></div>
                <div className="meter"><i style={{ width: `${pct(n / S.n)}%` }} /></div></div>))}</div>)}
        </Panel>
        <Panel i={3} label="Error analysis" title="Marked wrong" chip={<span className="chip">{S.wrong.length}</span>}>
          {!S.wrong.length ? <Empty title="Nothing flagged" text="Wrong predictions you mark will be listed here for retraining." />
            : S.wrong.slice(0, 6).map((x) => (
              <p key={x._id} className="note" style={{ marginTop: 8 }}><strong>{label(x.category)}</strong> → {x.team}<br />{x._text}</p>))}
        </Panel>
      </div>
    </>
  );

  const status = (
    <Panel label="System" title="API & model health"
      chip={<button className="btn sm" onClick={checkHealth} disabled={hLoading}>{hLoading ? "Checking..." : "Refresh"}</button>}>
      {hError && <p className="note bad-t">{hError}</p>}
      <div className="grid4 mt">
        <Stat label="API status" value={online ? "Online" : "Offline"} note="Public /health" />
        <Stat label="Model" value={health?.model_version || "-"} note="Active version" />
        <Stat label="Model loaded" value={health ? (health.model_loaded ? "Yes" : "No") : "-"} note="Runtime availability" />
        <Stat label="Authentication" value="Enabled" note="Server-side protected" />
      </div>
      <div className="grid4">
        {[["Single prediction", "POST /predict"], ["Batch prediction", "POST /predict/batch"], ["Async jobs", "POST /batch/jobs"], ["Health", "GET /health"]].map(([l, e]) => (
          <div className="stat" key={l}><span>{l}</span><strong style={{ fontSize: 13 }}>{e}</strong></div>))}
      </div>
    </Panel>
  );

  return (
    <div className="app">
      <aside className="side">
        <div className="brand"><div className="logo"><Icon name="route" size={21} /></div><div><h2>RouteIQ</h2><p>Support Intelligence</p></div></div>
        <nav className="nav" aria-label="Main">
          {NAV.map(([id, l], i) => (
            <button key={id} className={view === id ? "on" : ""} aria-current={view === id ? "page" : undefined} onClick={go(id)}>
              <Icon name={id} size={17} />{l.split(" &")[0]}<kbd>{i + 1}</kbd>
            </button>))}
        </nav>
        <div className="foot">
          <div className="status"><span className={`dot ${online ? "on" : ""}`} /><div><strong>{online ? "API Online" : "API Offline"}</strong>
            <div className="mute">{health?.model_version ? `Model ${health.model_version}` : "Connection unavailable"}</div></div></div>
          <div className="row">
            <button className="btn sm" onClick={() => setPal(true)}>Commands <span className="kbd">Ctrl K</span></button>
          </div>
          <p className="mute" style={{ textAlign: "center" }}>Built by Team CodeXtreme</p>
        </div>
      </aside>
      <main className="main">
        {view !== "dashboard" && (
          <header className="top">
            <div><p className="eyebrow">TensorForge 2.0</p><h1>{title}</h1>
              <p className="mute" style={{ marginTop: 6 }}>Multilingual customer support classification and team routing</p></div>
            <span className={`chip ${online ? "ok" : "bad"}`}>{online ? "Live system" : "API offline"}</span>
          </header>
        )}
        <div className="view" key={view}>
          {{ dashboard, single, batch, insights, status }[view]}
        </div>
      </main>
      {pal && <Palette actions={actions} onClose={() => setPal(false)} />}
      {toast && <div className={`toast ${toast.kind}`} role="status">{toast.msg}</div>}
    </div>
  );
}
