"use client";

import { useMemo, useState } from "react";
import { Activity, ArrowLeft, ArrowRight, Check, CircleHelp, Clock3, Globe2, LayoutDashboard, Menu, Network, Router, Search, ShieldCheck, Signal, Wifi, X, ScanSearch } from "lucide-react";

const brands = ["Tenda"];

type Step = "brand" | "connect";
const modules = [
  { name: "Overview", icon: LayoutDashboard, desc: "Tenda router status, uptime and network summary" },
  { name: "Connected Devices", icon: Network, desc: "View, block and manage connected devices" },
  { name: "Speed Limits", icon: Activity, desc: "Set upload and download limits per device" },
  { name: "Website Blocking", icon: ShieldCheck, desc: "Manage website and parental access rules" },
  { name: "Wi-Fi Settings", icon: Wifi, desc: "Change Wi-Fi name, password and guest access" },
  { name: "DNS & VPN", icon: Globe2, desc: "Configure Private DNS and VPN where supported" },
  { name: "Usage", icon: Signal, desc: "Monitor total upload and download usage" },
  { name: "Scheduled Restart", icon: Clock3, desc: "Schedule automatic router maintenance and restart" },
  { name: "Admin Settings", icon: Router, desc: "Change router administrator credentials" },
];

export default function Home() {
  const [step, setStep] = useState<Step>("brand");
  const [brand, setBrand] = useState("Tenda");
  const [ip, setIp] = useState("192.168.1.1");
  const [adminPassword, setAdminPassword] = useState("");
  const [routerData, setRouterData] = useState<any>(null);
  const [compatibility, setCompatibility] = useState<any>(null);
  const [routerError, setRouterError] = useState("");
  const [query, setQuery] = useState("");
  const [active, setActive] = useState("Overview");
  const [menuOpen, setMenuOpen] = useState(false);
  const [connector, setConnector] = useState<"idle" | "checking" | "offline" | "available">("idle");
  const [discovery, setDiscovery] = useState<{address:string;reachable:boolean;brand:string|null;model:string|null;login_url:string;message:string}|null>(null);
  const filtered = useMemo(() => brands.filter((b) => b.toLowerCase().includes(query.toLowerCase())), [query]);

  async function checkConnector() {
    setConnector("checking");
    setDiscovery(null);
    setRouterData(null);
    setCompatibility(null);
    setRouterError("");
    try {
      const health = await fetch("http://127.0.0.1:8765/health", {
        signal: AbortSignal.timeout(3500), credentials: "omit", mode: "cors",
      });
      if (!health.ok) throw new Error("Connector unavailable");

      let targetAddress = ip.trim();
      const gatewayResponse = await fetch("http://127.0.0.1:8765/api/v1/gateway", {
        signal: AbortSignal.timeout(3500), credentials: "omit", mode: "cors",
      });
      if (gatewayResponse.ok) {
        const gatewayData = await gatewayResponse.json();
        if (gatewayData.gateway) {
          targetAddress = gatewayData.gateway;
          setIp(targetAddress);
        }
      }

      const resultResponse = await fetch("http://127.0.0.1:8765/api/v1/discover", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ address: targetAddress }),
        signal: AbortSignal.timeout(9000),
        credentials: "omit",
        mode: "cors",
      });
      const result = await resultResponse.json();
      if (!resultResponse.ok) throw new Error(result.detail || "Router discovery failed");
      setDiscovery(result);
      if (result.brand && result.brand.toLowerCase() === "tenda") {
        const identifyResponse = await fetch("http://127.0.0.1:8765/api/v1/tenda/identify", {
          method: "POST", headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ address: targetAddress }),
          signal: AbortSignal.timeout(7000), credentials: "omit", mode: "cors",
        });
        const identifyPayload = await identifyResponse.json();
        if (identifyResponse.ok) setCompatibility(identifyPayload);
      }
      if (result.brand && result.brand.toLowerCase() === "tenda" && adminPassword && compatibility?.profile?.profile_id === "rtl-v15-ac10") {
        const api = await fetch("http://127.0.0.1:8765/api/v1/tenda/status", {
          method: "POST", headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ address: targetAddress, password: adminPassword }),
          signal: AbortSignal.timeout(12000), credentials: "omit", mode: "cors",
        });
        const payload = await api.json();
        if (!api.ok) throw new Error(payload.detail || "Tenda login failed");
        setRouterData(payload);
      } else if (result.brand && result.brand.toLowerCase() === "tenda" && adminPassword && compatibility?.profile?.profile_id === "f3-v12-legacy") {
        setRouterError("Tenda F3 detected. Its firmware-specific adapter is identified, but control APIs are still locked until validated against this exact F3 hardware and firmware.");
      } else if (result.brand && result.brand.toLowerCase() === "tenda" && adminPassword && compatibility?.profile?.profile_id !== "rtl-v15-ac10") {
        setRouterError("Tenda router detected. This model/firmware does not yet have a validated control adapter; no configuration commands were sent.");
      }
      if (!result.brand || result.brand.toLowerCase() !== "tenda") {
        setRouterError("Tenda router was not positively identified. Routerly only supports Tenda.");
      } else if (!adminPassword) {
        setRouterError("Enter the Tenda administrator password, then connect again.");
      }
      if (result.brand && !brand) setBrand("Tenda");
      setConnector("available");
    } catch (error) {
      setRouterError(error instanceof Error ? error.message : "Could not connect to Tenda router.");
      setConnector("offline");
    }
  }

  function chooseBrand(value: string) { setBrand("Tenda"); setStep("connect"); }
  function startAutoDetect() { setBrand("Tenda"); setStep("connect"); }
  function reset() { setStep("connect"); setBrand("Tenda"); setQuery(""); setConnector("idle"); setAdminPassword(""); setRouterData(null); setRouterError(""); }

  return (
    <main className="shell">
      <aside className={`sidebar ${menuOpen ? "sidebar-open" : ""}`}>
        <div className="brand-lockup"><div className="logo"><Router size={20}/></div><span>routerly</span><button className="mobile-close" onClick={() => setMenuOpen(false)} aria-label="Close menu"><X size={18}/></button></div>
        <div className="side-label">WORKSPACE</div>
        <button className={`nav-item ${active === "Overview" ? "selected" : ""}`} onClick={() => {setActive("Overview");setMenuOpen(false)}}><LayoutDashboard size={17}/> Overview</button>
        <div className="side-label nav-gap">MANAGEMENT</div>
        {modules.slice(1).map((item) => <button key={item.name} className={`nav-item ${active === item.name ? "selected" : ""}`} onClick={() => {setActive(item.name);setMenuOpen(false)}}><item.icon size={17}/> {item.name}</button>)}
        <div className="sidebar-bottom"><div className="connector-card"><div className="connector-title"><span className={`status-dot ${connector === "offline" || connector === "idle" ? "dot-muted" : ""}`}/><span>Local connector</span></div><p>{connector === "offline" ? "Not detected on this device" : connector === "available" ? "Connector is responding" : "Needed for local router access"}</p><button onClick={checkConnector} disabled={connector === "checking"}>{connector === "checking" ? "Checking…" : "Check connector"} <ArrowRight size={13}/></button></div><div className="profile"><div className="avatar">U</div><div><strong>Local workspace</strong><small>Personal network</small></div><button aria-label="Help"><CircleHelp size={17}/></button></div></div>
      </aside>

      <section className="main-area">
        <header className="topbar"><button className="mobile-menu" onClick={() => setMenuOpen(true)} aria-label="Open menu"><Menu size={20}/></button><div className="breadcrumb">Workspace <span>/</span> {active}</div><div className="top-actions"><span className="secure-label"><ShieldCheck size={14}/> Local-first</span><div className="avatar small-avatar">U</div></div></header>
        <div className="content">
          <div className="page-heading"><div><div className="eyebrow">NETWORK MANAGEMENT</div><h1>{active === "Overview" ? "Your network, simplified." : active}</h1><p>{active === "Overview" ? "Connect a router to get started. Manage your Tenda home network from one place." : modules.find(m => m.name === active)?.desc ?? "Manage your network from one place."}</p></div><div className="heading-status"><span className="status-dot dot-muted"/><span>No router connected</span></div></div>

          {active === "Overview" ? <>
            <div className="stats-grid"><div className="stat-card"><div className="stat-top"><span>Connection</span><Globe2 size={17}/></div><div className="stat-value muted-value">Not connected</div><div className="stat-foot">Connect a router to view status</div></div><div className="stat-card"><div className="stat-top"><span>Connected devices</span><Network size={17}/></div><div className="stat-value">—</div><div className="stat-foot">Device list appears here</div></div><div className="stat-card"><div className="stat-top"><span>Network activity</span><Activity size={17}/></div><div className="stat-value">—</div><div className="stat-foot">Live traffic when connected</div></div><div className="stat-card"><div className="stat-top"><span>Signal</span><Signal size={17}/></div><div className="stat-value">—</div><div className="stat-foot">Wireless signal information</div></div></div>
            <div className="connect-layout"><section className="panel connect-panel"><div className="panel-heading"><div><div className="eyebrow">GET STARTED</div><h2>Connect your router</h2><p>Connect your Tenda router. Routerly will identify the model and firmware where possible.</p></div><div className="panel-icon"><Router size={21}/></div></div>
              <div className="steps"><div className={`step ${step === "brand" ? "current" : "done"}`}><span>{step === "brand" ? "1" : <Check size={13}/>}</span> Router</div><div className="step-line"/><div className={`step ${step === "connect" ? "current" : ""}`}><span>2</span> Connect</div></div>
              {step === "brand" && <div className="wizard-content"><div className="auto-detect-card"><div className="auto-detect-icon"><ScanSearch size={22}/></div><div className="auto-detect-copy"><strong>Don't know your router brand?</strong><span>No problem. Let Routerly try to detect it.</span></div><button className="primary-button" onClick={startAutoDetect}>Auto detect <ArrowRight size={15}/></button></div><div className="or-divider"><span>OR SELECT BRAND (OPTIONAL)</span></div><label className="field-label" htmlFor="brand-search">Choose your router brand</label><div className="search-box"><Search size={17}/><input id="brand-search" value={query} onChange={e => setQuery(e.target.value)} placeholder="Search Tenda…" autoComplete="off"/></div><div className="brand-grid">{filtered.slice(0,12).map((b) => <button className="brand-option" key={b} onClick={() => chooseBrand(b)}><span className="brand-mark">{b.slice(0,1)}</span><span>{b}</span><ArrowRight size={14}/></button>)}</div><div className="results-note">Tenda router support</div></div>}
              {step === "connect" && <div className="wizard-content"><button className="back-link" onClick={() => setStep("brand")}><ArrowLeft size={14}/> Back</button><div className="selected-brand"><span className="brand-mark large-mark">{brand ? brand.slice(0,1) : <ScanSearch size={18}/>}</span><div><strong>{brand || "Automatic detection"}</strong><small>{brand ? "Selected brand · model detection is automatic" : "Router brand and model will be identified if supported"}</small></div></div><label className="field-label" htmlFor="router-ip">Router address</label><input className="text-input mono" id="router-ip" value={ip} onChange={e => setIp(e.target.value)} placeholder="192.168.1.1"/>
              <label className="field-label" htmlFor="tenda-admin-password" style={{marginTop:14}}>Tenda administrator password</label><input className="text-input" id="tenda-admin-password" type="password" autoComplete="current-password" value={adminPassword} onChange={e => setAdminPassword(e.target.value)} placeholder="Router admin password"/><p className="helper-text">This is a common router address. If yours is different, enter the gateway address shown in your device's Wi-Fi network details. Automatic gateway detection will be provided by the local connector.</p><div className="notice"><ShieldCheck size={17}/><p>Routerly currently targets Tenda routers. The admin password is sent to the local connector only; it is not sent to Routerly cloud.</p></div><button className="primary-button full-button" onClick={checkConnector} disabled={connector === "checking"}>{connector === "checking" ? "Checking local connector…" : "Check local connector"} <ArrowRight size={16}/></button>{connector === "offline" && <p className="error-note">Local connector not detected. Install and run the connector on a computer connected to this network.</p>}{routerError && <p className="error-note">{routerError}</p>}{connector === "available" && discovery && <div className="discovery-result"><div className="discovery-heading"><Check size={15}/><strong>{discovery.reachable ? "Router found" : "Connector ready"}</strong></div><p>{discovery.message}</p><div className="discovery-meta"><span>Address</span><strong className="mono">{discovery.address}</strong></div>{discovery.brand && <div className="discovery-meta"><span>Detected brand</span><strong>{discovery.brand}</strong></div>}{compatibility?.model && <div className="discovery-meta"><span>Model</span><strong>{compatibility.model}</strong></div>}
              {compatibility?.firmware && <div className="discovery-meta"><span>Firmware</span><strong>{compatibility.firmware}</strong></div>}
              {compatibility?.profile && <div className="discovery-meta"><span>Compatibility profile</span><strong>{compatibility.profile.label}</strong></div>}
              {compatibility?.message && <p className="small-note">{compatibility.message}</p>}{discovery.reachable && <a className="router-login-link" href={discovery.login_url} target="_blank" rel="noreferrer">Open router login page <ArrowRight size={14}/></a>}{routerData && <div className="success-note">Tenda API login successful. Router API responded. Exact model/firmware compatibility still needs verification.</div>}</div>}</div>}
              <div className="panel-foot"><ShieldCheck size={15}/> Tenda credentials are handled locally and are not stored by Routerly cloud.</div>
            </section>
            <aside className="right-column"><div className="panel info-panel"><div className="info-icon"><Wifi size={19}/></div><h3>Built for Tenda routers.</h3><p>Tenda-focused controls with compatibility checks for each model and firmware.</p><div className="mini-brand-list"><span>Tenda F3</span><span>Tenda N-series</span><span>Tenda AC-series</span><span>Tenda AX-series</span></div></div><div className="panel checklist-panel"><h3>What you can manage</h3>{["Wi-Fi & wireless settings","Connected devices","Internet & LAN","Security & access","Network performance","Diagnostics & logs"].map(x => <div className="check-row" key={x}><Check size={15}/>{x}</div>)}<p className="small-note">Availability depends on router model and firmware.</p></div></aside></div>
          </> : <div className="panel empty-module"><div className="empty-icon"><Router size={25}/></div><h2>Connect a router to continue</h2><p>{modules.find(m => m.name === active)?.desc}. Connect a supported Tenda router to check whether this feature is available on its firmware. No simulated controls are shown.</p><button className="primary-button" onClick={() => {setActive("Overview");reset()}}>Connect a router <ArrowRight size={15}/></button></div>}
          <footer className="footer"><span>Routerly <span className="footer-dot">·</span> Tenda router management</span><span><Clock3 size={13}/> Compatibility depends on model & firmware</span></footer>
        </div>
      </section>
    </main>
  );
}
