import { useEffect, useMemo, useRef, useState } from "react";
import "./styles.css";

const DEFAULT_API = "http://127.0.0.1:8003";

const scenarios = [
  { value: "OPERATION_TO_WEAR", label: "Operation → Wear", desc: "Linked operator + machine signals" },
  { value: "OPERATOR_RISK", label: "Operator Risk", desc: "Behaviour and safety signals" },
  { value: "NORMAL", label: "Normal", desc: "Signals within baseline" },
];

function detail(data, signal) {
  return (data?.evidence_detail || []).find((x) => x.signal === signal);
}

function healthScore(health) {
  if (health === "OK") return 90;
  if (health === "WARNING") return 68;
  if (health === "CRITICAL") return 48;
  return 0;
}

function severityClass(value) {
  return String(value || "").toLowerCase();
}

function systemState(data, signal) {
  const item = detail(data, signal);
  if (!item) return ["ok", "✓", "Normal"];
  if (signal === "hydraulic_pressure" || signal === "vibration") {
    return item.ratio >= 2.2 ? ["crit", "⚠", "Attention"] : ["warn", "⚠", "Elevated"];
  }
  if (signal === "safety_event") return ["crit", "⚠", "Attention"];
  return ["ok", "✓", "Monitored"];
}

function Wave() {
  return <div className="wave" aria-hidden="true">{Array.from({ length: 12 }, (_, i) => <i key={i} style={{ height: `${6 + Math.abs(Math.sin(i * 0.9)) * 30}px` }} />)}</div>;
}

function MicIcon() {
  return <svg width="30" height="30" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7"><rect x="9" y="3" width="6" height="11" rx="3" /><path d="M6 11a6 6 0 0 0 12 0M12 17v3" strokeLinecap="round" /></svg>;
}

function Sparkline({ values = [], label, unit = "" }) {
  const clean = values.map(Number).filter(Number.isFinite);
  if (!clean.length) return <div className="empty-chart">Waiting for live telemetry…</div>;
  const min = Math.min(...clean), max = Math.max(...clean), range = max - min || 1;
  const points = clean.map((v, i) => `${(i / Math.max(1, clean.length - 1)) * 100},${92 - ((v - min) / range) * 80}`).join(" ");
  return <div className="spark-wrap"><div className="spark-head"><b>{label}</b><span>{clean.at(-1)?.toFixed?.(2)}{unit}</span></div><svg className="spark" viewBox="0 0 100 100" preserveAspectRatio="none"><polyline points={points} fill="none" vectorEffect="non-scaling-stroke" /></svg><div className="spark-foot"><span>min {min.toFixed(2)}</span><span>max {max.toFixed(2)}</span></div></div>;
}

function Chip({ name, icon, big, small, sub, primary, yellow, action }) {
  return <div className={`chip${primary ? " primary" : ""}`}>
    <div className="c-top"><span className="c-name">{name}</span><span className={`c-ic ${icon === "check" ? "good" : ""}`}>{icon === "check" ? "✓" : icon === "action" ? "↗" : "📈"}</span></div>
    {action ? <div className="c-sub action-sub">{sub}</div> : <><div className="c-big" style={yellow ? { color: "var(--yellow)" } : undefined}>{big}<small>{small}</small></div><div className={`c-sub${primary ? " rise" : ""}`}>{primary ? "↑ " : ""}{sub}</div></>}
  </div>;
}

export default function App() {
  const [endpoint, setEndpoint] = useState(DEFAULT_API);
  const [scenario, setScenario] = useState("OPERATION_TO_WEAR");
  const [connected, setConnected] = useState(false);
  const [data, setData] = useState(null);
  const [liveAnalysis, setLiveAnalysis] = useState(null);
  const [telemetry, setTelemetry] = useState(null);
  const [liveHistory, setLiveHistory] = useState([]);
  const [question, setQuestion] = useState("");
  const [prompt, setPrompt] = useState("How can I help?");
  const [loading, setLoading] = useState(false);
  const [banner, setBanner] = useState("");
  const [expanded, setExpanded] = useState(false);
  const [listening, setListening] = useState(false);
  const [autoLive, setAutoLive] = useState(true);
  const [liveInterval, setLiveInterval] = useState(2500);
  const [view, setView] = useState("dashboard");
  const [showExit, setShowExit] = useState(false);
  const recognitionRef = useRef(null);
  const base = endpoint.replace(/\/+$/, "");
  const analysis = liveAnalysis || data;

  useEffect(() => {
    let active = true;
    const ping = async () => {
      try { const r = await fetch(`${base}/health`, { cache: "no-store" }); if (active) setConnected(r.ok); }
      catch { if (active) setConnected(false); }
    };
    ping(); const timer = setInterval(ping, 5000);
    return () => { active = false; clearInterval(timer); };
  }, [base]);

  useEffect(() => {
    const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SR) return;
    const recognition = new SR();
    recognition.lang = "en-US"; recognition.interimResults = false; recognition.maxAlternatives = 1;
    recognition.onresult = (event) => ask(event.results[0][0].transcript);
    recognition.onend = () => setListening(false);
    recognition.onerror = () => setListening(false);
    recognitionRef.current = recognition;
    return () => { recognition.stop?.(); recognitionRef.current = null; };
  }, [base, scenario]);

  async function refreshLive() {
    try {
      const r = await fetch(`${base}/live/scenario/${encodeURIComponent(scenario)}`, { cache: "no-store" });
      if (!r.ok) throw new Error(`Live API returned ${r.status}`);
      const result = await r.json();
      setLiveAnalysis(result.analysis);
      setTelemetry(result.telemetry);
      setLiveHistory((old) => [...old, { ...result.telemetry, ml_anomaly_score: result.analysis.ml_anomaly_score }].slice(-40));
      setConnected(true);
    } catch (e) {
      setConnected(false);
      setBanner(`Live telemetry unavailable: ${e.message}`);
    }
  }

  useEffect(() => {
    if (!autoLive) return undefined;
    refreshLive();
    const timer = setInterval(refreshLive, liveInterval);
    return () => clearInterval(timer);
  }, [base, scenario, autoLive, liveInterval]);

  async function ask(text) {
    const cleanText = String(text ?? "").trim();
    if (!cleanText) return;
    setQuestion(cleanText); setPrompt("Analyzing…"); setLoading(true); setBanner("");
    try {
      const url = `${base}/copilot/scenario/${encodeURIComponent(scenario)}?${new URLSearchParams({ question: cleanText })}`;
      const response = await fetch(url, { method: "POST", cache: "no-store", headers: { Accept: "application/json" } });
      if (!response.ok) throw new Error(`AI Co-Pilot returned ${response.status}`);
      const result = await response.json();
      setData(result); setExpanded(Boolean(result.evidence_detail?.length)); setPrompt("How can I help?");
      if ("speechSynthesis" in window && result.message) {
        const utterance = new SpeechSynthesisUtterance(result.message); utterance.rate = 1.02;
        window.speechSynthesis.cancel(); window.speechSynthesis.speak(utterance);
      }
    } catch (error) { setBanner(`${error.message}. Check the backend services.`); setPrompt("How can I help?"); }
    finally { setLoading(false); }
  }

  function startVoice() {
    if (!recognitionRef.current) return setBanner("Voice recognition is not supported in this browser. Use Chrome or Edge.");
    try { setListening(true); recognitionRef.current.start(); } catch { setListening(false); }
  }

  const hyd = detail(analysis, "hydraulic_pressure");
  const vib = detail(analysis, "vibration");
  const cycles = detail(analysis, "load_cycles");
  const safety = detail(analysis, "safety_event");
  const score = healthScore(analysis?.health);

  const chips = useMemo(() => {
    if (!analysis) return [];
    return [
      hyd && { name: "Hydraulic Pressure", icon: "graph", big: `${hyd.ratio}×`, small: " baseline", sub: `Current ${Number(hyd.value).toFixed(1)} · baseline ${Number(hyd.baseline).toFixed(0)}`, primary: true },
      cycles && { name: "Harsh Load Cycles", icon: "graph", big: String(Math.round(cycles.value)), small: "", sub: `Baseline: ${Math.round(cycles.baseline)}` },
      safety && { name: "Safety Events", icon: "graph", big: String(Math.round(safety.value)), small: "", sub: "Recent window" },
      { name: "ML Anomaly", icon: analysis.ml_prediction === "ANOMALOUS" ? "graph" : "check", big: `${Math.round((analysis.ml_anomaly_score ?? 0) * 100)}%`, small: "", sub: `${analysis.ml_model || "IsolationForest"} · ${analysis.ml_prediction || "NORMAL"}`, yellow: analysis.ml_prediction === "ANOMALOUS" },
      { name: "Correlation Window", icon: "graph", big: analysis.correlation ? "LINKED" : "NONE", small: "", sub: analysis.correlation ? "operator + machine signals overlap" : "signals independent", yellow: analysis.correlation },
      { name: "Evidence Confidence", icon: "check", big: `${Math.round((analysis.confidence ?? 0) * 100)}%`, small: "", sub: "evidence-backed analysis" },
      { name: "Recommended Action", icon: "action", sub: analysis.action || "Continue current operation", action: true },
    ].filter(Boolean);
  }, [analysis, hyd, cycles, safety]);

  function Dashboard() {
    return <main className="center"><div className="stage">
      <div className="hello"><div className="brand">CATalyst</div><h2>{loading ? "Analyzing machine signals…" : prompt}</h2></div>
      <div className="live-strip"><span className="live-dot" /> LIVE TELEMETRY <span>{telemetry?.timestamp ? new Date(telemetry.timestamp).toLocaleTimeString() : "waiting"}</span><span className="model-badge">ML: {analysis?.ml_model || "IsolationForest"}</span></div>
      <div className="mic-wrap"><Wave /><button className={`mic-btn${listening ? " listening" : ""}`} onClick={startVoice} title="Tap to speak" disabled={loading}><MicIcon /></button><Wave /></div>
      <div className="convo">
        {question && <div className="turn op"><div className="who">OPERATOR</div><div className="said">{question}</div></div>}
        {data && <div className="turn cat"><div className="who">CATALYST</div><div className="said">{data.message}{data.action && <div className="ai-action"><strong>Recommended action</strong><br />{data.action}</div>}</div></div>}
      </div>
      <button className="cta" disabled={!analysis} onClick={() => { setExpanded(true); setView("dashboard"); document.getElementById("explain")?.scrollIntoView({ behavior: "smooth" }); }}>VIEW EVIDENCE</button>
      <div className="quick"><button onClick={() => ask("How am I doing today?")}>How am I doing today?</button><button onClick={() => ask("Is my machine okay?")}>Is my machine okay?</button><button onClick={() => ask("Why was I flagged?")}>Why was I flagged?</button><button onClick={() => ask("What about the rest of my day?")}>Rest of my day?</button></div>
    </div></main>;
  }

  function Analytics() {
    return <main className="content-view"><div className="view-title"><div><span>ANALYTICS</span><h2>Live machine intelligence</h2></div><b className="live-badge">● {autoLive ? "STREAMING" : "PAUSED"}</b></div>
      <div className="analytics-grid">
        <Sparkline label="Hydraulic pressure" unit=" bar" values={liveHistory.map(x => x.hydraulic_pressure)} />
        <Sparkline label="Vibration" unit="" values={liveHistory.map(x => x.vibration)} />
        <Sparkline label="Engine temperature" unit="°" values={liveHistory.map(x => x.engine_temp)} />
        <Sparkline label="ML anomaly score" unit="" values={liveHistory.map(x => x.ml_anomaly_score ?? 0)} />
      </div>
      <div className="metric-grid"><div><span>RPM</span><strong>{telemetry?.rpm ?? "—"}</strong></div><div><span>Hydraulic temp</span><strong>{telemetry?.hydraulic_temp ?? "—"}°</strong></div><div><span>Oil pressure</span><strong>{telemetry?.oil_pressure ?? "—"}</strong></div><div><span>Load</span><strong>{telemetry?.load ?? "—"}</strong></div></div>
    </main>;
  }

  function Maintenance() {
    const critical = analysis?.health === "CRITICAL";
    const warning = analysis?.health === "WARNING";
    return <main className="content-view"><div className="view-title"><div><span>MAINTENANCE</span><h2>Machine care plan</h2></div><span className={`health-badge ${severityClass(analysis?.health)}`}>{analysis?.health || "WAITING"}</span></div>
      <div className="maintenance-card"><div className="maint-icon">🔧</div><div><h3>{critical ? "Inspect before next high-load task" : warning ? "Schedule a machine inspection" : "Preventive maintenance on track"}</h3><p>{critical ? "Critical telemetry is present. Avoid treating the simulated alert as a real-world diagnosis; use the evidence panel to identify the contributing signals." : warning ? "One or more signals are outside the learned normal envelope. Review hydraulic, vibration and temperature trends." : "The current telemetry is inside the learned operating envelope. Continue routine checks."}</p></div></div>
      <div className="maintenance-list">{(analysis?.evidence || ["No maintenance evidence yet"]).slice(0, 6).map((e, i) => <div key={i}><span>{i + 1}</span><p>{e}</p></div>)}</div>
    </main>;
  }

  function Settings() {
    return <main className="content-view"><div className="view-title"><div><span>SETTINGS</span><h2>System configuration</h2></div></div>
      <div className="settings-card"><label>Module 3 endpoint<input value={endpoint} onChange={e => setEndpoint(e.target.value)} /></label><label>Scenario<select value={scenario} onChange={e => { setScenario(e.target.value); setLiveHistory([]); }} >{scenarios.map(s => <option value={s.value} key={s.value}>{s.label}</option>)}</select></label><label className="toggle"><input type="checkbox" checked={autoLive} onChange={e => setAutoLive(e.target.checked)} /><span>Live telemetry stream</span></label><label>Refresh interval<select value={liveInterval} onChange={e => setLiveInterval(Number(e.target.value))}><option value="1500">1.5 seconds</option><option value="2500">2.5 seconds</option><option value="5000">5 seconds</option></select></label><button className="save-btn" onClick={() => { setBanner("Settings applied"); setView("dashboard"); }}>APPLY SETTINGS</button></div>
    </main>;
  }

  function Help() {
    return <main className="content-view"><div className="view-title"><div><span>HELP</span><h2>CATalyst operator guide</h2></div></div><div className="help-grid"><div><b>Voice</b><p>Tap the microphone and ask a natural question. The transcript is routed to the Co-Pilot.</p></div><div><b>Live data</b><p>The simulator continuously generates stateful telemetry and Module 2 evaluates every new reading.</p></div><div><b>ML</b><p>An Isolation Forest learns a normal sensor envelope and flags unusual multivariate patterns.</p></div><div><b>Evidence</b><p>Use Explain This to inspect the signals behind a recommendation. Correlation is not treated as causation.</p></div></div></main>;
  }

  const renderedView = view === "analytics" ? <Analytics /> : view === "maintenance" ? <Maintenance /> : view === "settings" ? <Settings /> : view === "help" ? <Help /> : <Dashboard />;

  return <>
    <header><div className="cat-badge">CAT</div><div className="wordmark"><b>CAT</b>alyst</div><div className="subtitle">AI Operator Co-Pilot</div><div className="top-right"><span className="top-pill"><span className="avatar">M</span>Machine: <b>CAT 320 GC</b></span><span className="top-pill"><span className="avatar">AR</span>Operator: <b>Alex R.</b></span><span className="status-live">Status: <b>{connected ? "ACTIVE" : "OFFLINE"}</b></span></div></header>
    <div className="conn-strip"><span className={`cdot ${connected ? "live" : "down"}`} /><span>{connected ? "connected to AI Co-Pilot" : "offline"}</span><span className="live-source">LIVE SOURCE: Module 1 → Module 2 → Module 3</span><span style={{ color: "var(--muted-2)" }}>scenario:</span><select className="cendpoint scenario-select" value={scenario} onChange={e => { setScenario(e.target.value); setLiveHistory([]); }}>{scenarios.map(item => <option key={item.value} value={item.value}>{item.value}</option>)}</select></div>
    {banner && <div className="banner show" onClick={() => setBanner("")}>{banner} <b>×</b></div>}
    <div className="shell">
      <nav className="rail">
        <button className={view === "dashboard" ? "active" : ""} title="Dashboard" onClick={() => setView("dashboard")}>▦</button>
        <button className={view === "maintenance" ? "active" : ""} title="Maintenance" onClick={() => setView("maintenance")}>🔧</button>
        <button className={view === "settings" ? "active" : ""} title="Settings" onClick={() => setView("settings")}>⚙</button>
        <button className={view === "analytics" ? "active" : ""} title="Analytics" onClick={() => setView("analytics")}>📊</button>
        <div className="spacer" /><button className={view === "help" ? "active" : ""} title="Help" onClick={() => setView("help")}>?</button><button title="Exit" onClick={() => setShowExit(true)}>⏻</button>
      </nav>
      {renderedView}
      <aside className="status"><h3>Machine Status</h3><div className="grp-label">MACHINE HEALTH</div><div className="health-num"><span className="n">{analysis ? score : "—"}</span><span className="d">{analysis ? ` / 100 · ${analysis.health}` : " / 100"}</span></div><div className="health-track"><i style={{ width: `${score}%` }} /></div>
        <div style={{ marginTop: 16 }}>{[["Hydraulic System", "hydraulic_pressure"],["Engine", null],["Vibration", "vibration"],["Temperature", null]].map(([label, signal]) => { const [cls, ic, txt] = signal ? systemState(analysis, signal) : ["ok", "✓", "Monitored"]; return <div className="srow" key={label}><span className="k">{label}</span><span className={`v ${cls}`}><span className="ic">{analysis ? ic : "—"}</span>{analysis ? txt : "—"}</span></div>; })}</div>
        <div className="grp-label">OPERATION STATUS</div><div className="srow"><span className="k">Risk</span><span className={`v ${severityClass(analysis?.risk)}`}>{analysis?.risk || "—"}</span></div><div className="srow"><span className="k">ML</span><span className={`v ${analysis?.ml_prediction === "ANOMALOUS" ? "medium" : "ok"}`}>{analysis ? `${Math.round((analysis.ml_anomaly_score ?? 0) * 100)}%` : "—"}</span></div><div className="srow"><span className="k">Confidence</span><span className="v ok">{analysis ? `${Math.round((analysis.confidence ?? 0) * 100)}%` : "—"}</span></div>
      </aside>
    </div>
    <section className={`explain ${expanded ? "" : "collapsed"}`} id="explain"><button className="explain-head" onClick={() => setExpanded(x => !x)}><span className="ic">▣</span><h3>Explain This</h3><span className="chev">▾</span></button><div className="explain-body"><div className="why">WHY THIS RECOMMENDATION?</div><div className="chips">{chips.length ? chips.map((chip, i) => <Chip key={`${chip.name}-${i}`} {...chip} />) : <div className="chip"><div className="c-sub">Run an analysis to see the evidence.</div></div>}</div>{analysis?.correlation_note && <div className="disclaimer">{analysis.correlation_note}</div>}</div></section>
    {showExit && <div className="modal-backdrop"><div className="modal"><h3>Exit CATalyst demo?</h3><p>The local development server will keep running. Close this browser tab if you want to leave the dashboard.</p><button onClick={() => setShowExit(false)}>BACK TO DASHBOARD</button></div></div>}
  </>;
}
