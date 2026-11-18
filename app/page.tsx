"use client";

import { useMemo, useState } from "react";
import { Activity, ArrowLeft, ArrowRight, Check, CircleHelp, Clock3, Globe2, LayoutDashboard, Menu, Network, Router, Search, ShieldCheck, Signal, Wifi, X, ScanSearch } from "lucide-react";

const brands = [
  "TP-Link","ASUS","NETGEAR","D-Link","Linksys","Tenda","Mercusys","Xiaomi","Huawei","ZTE","MikroTik","Ubiquiti","Synology","AVM (FRITZ!)","Edimax","Cisco","Juniper Networks","HPE Aruba Networking","Fortinet","Nokia","Ericsson","Cambium Networks","Extreme Networks","Peplink","DrayTek","Teltonika Networks","Allied Telesis","Zyxel","ADTRAN","Inseego","NetComm","Sierra Wireless","Cudy","Zowee","Ruijie Networks","Reyee","GL.iNet","TOTOLINK","Netis","Wavlink","TRENDnet","Belkin","Google Nest WiFi","Amazon eero","Buffalo","Keenetic","LANCOM Systems","Grandstream","H3C","FiberHome","Sagemcom","Sercomm","Arcadyan","ARRIS","Motorola","Planet Technology","Actiontec","Calix","Technicolor","CommScope","Askey","MitraStar","Zycom","Billion","EnGenius","Sophos","WatchGuard","Ruckus Networks","TP-Link Omada","Huawei eKit","Open Mesh","Razer","ASUS ROG","Edgecore Networks"
];

type Step = "brand" | "connect";
const modules = [
  { name: "Overview", icon: LayoutDashboard, desc: "Router health, uptime and connection summary" },
  { name: "Wi-Fi", icon: Wifi, desc: "Wireless networks, bands and security" },
  { name: "Devices", icon: Network, desc: "Connected clients and device details" },
  { name: "Internet", icon: Globe2, desc: "WAN, IP address and DNS configuration" },
  { name: "Security", icon: ShieldCheck, desc: "Firewall, access rules and protection" },
  { name: "Performance", icon: Activity, desc: "Traffic, bandwidth and quality of service" },
];

export default function Home() {
  const [step, setStep] = useState<Step>("brand");
  const [brand, setBrand] = useState("");
  const [ip, setIp] = useState("192.168.1.1");
  const [query, setQuery] = useState("");
  const [active, setActive] = useState("Overview");
  const [menuOpen, setMenuOpen] = useState(false);
  const [connector, setConnector] = useState<"idle" | "checking" | "offline" | "available">("idle");
  const filtered = useMemo(() => brands.filter((b) => b.toLowerCase().includes(query.toLowerCase())), [query]);

  async function checkConnector() {
    setConnector("checking");
    try {
      const response = await fetch("http://127.0.0.1:8765/health", { signal: AbortSignal.timeout(1800) });
      if (!response.ok) throw new Error("Connector unavailable");
      setConnector("available");
    } catch { setConnector("offline"); }
  }

  function chooseBrand(value: string) { setBrand(value); setStep("connect"); }
  function startAutoDetect() { setBrand(""); setStep("connect"); }
  function reset() { setStep("brand"); setBrand(""); setQuery(""); setConnector("idle"); }

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
          <div className="page-heading"><div><div className="eyebrow">NETWORK MANAGEMENT</div><h1>{active === "Overview" ? "Your network, simplified." : active}</h1><p>{active === "Overview" ? "Connect a router to get started. One simple place for your network." : modules.find(m => m.name === active)?.desc ?? "Manage your network from one place."}</p></div><div className="heading-status"><span className="status-dot dot-muted"/><span>No router connected</span></div></div>

          {active === "Overview" ? <>
            <div className="stats-grid"><div className="stat-card"><div className="stat-top"><span>Connection</span><Globe2 size={17}/></div><div className="stat-value muted-value">Not connected</div><div className="stat-foot">Connect a router to view status</div></div><div className="stat-card"><div className="stat-top"><span>Connected devices</span><Network size={17}/></div><div className="stat-value">—</div><div className="stat-foot">Device list appears here</div></div><div className="stat-card"><div className="stat-top"><span>Network activity</span><Activity size={17}/></div><div className="stat-value">—</div><div className="stat-foot">Live traffic when connected</div></div><div className="stat-card"><div className="stat-top"><span>Signal</span><Signal size={17}/></div><div className="stat-value">—</div><div className="stat-foot">Wireless signal information</div></div></div>
            <div className="connect-layout"><section className="panel connect-panel"><div className="panel-heading"><div><div className="eyebrow">GET STARTED</div><h2>Connect your router</h2><p>No need to know your router model. Routerly will try to identify it automatically.</p></div><div className="panel-icon"><Router size={21}/></div></div>
              <div className="steps"><div className={`step ${step === "brand" ? "current" : "done"}`}><span>{step === "brand" ? "1" : <Check size={13}/>}</span> Router</div><div className="step-line"/><div className={`step ${step === "connect" ? "current" : ""}`}><span>2</span> Connect</div></div>
              {step === "brand" && <div className="wizard-content"><div className="auto-detect-card"><div className="auto-detect-icon"><ScanSearch size={22}/></div><div className="auto-detect-copy"><strong>Don't know your router brand?</strong><span>No problem. Let Routerly try to detect it.</span></div><button className="primary-button" onClick={startAutoDetect}>Auto detect <ArrowRight size={15}/></button></div><div className="or-divider"><span>OR SELECT BRAND (OPTIONAL)</span></div><label className="field-label" htmlFor="brand-search">Choose your router brand</label><div className="search-box"><Search size={17}/><input id="brand-search" value={query} onChange={e => setQuery(e.target.value)} placeholder="Search 70+ brands…" autoComplete="off"/></div><div className="brand-grid">{filtered.slice(0,12).map((b) => <button className="brand-option" key={b} onClick={() => chooseBrand(b)}><span className="brand-mark">{b.slice(0,1)}</span><span>{b}</span><ArrowRight size={14}/></button>)}</div><div className="results-note">Showing {Math.min(filtered.length,12)} of {filtered.length} matching brands</div></div>}
              {step === "connect" && <div className="wizard-content"><button className="back-link" onClick={() => setStep("brand")}><ArrowLeft size={14}/> Back</button><div className="selected-brand"><span className="brand-mark large-mark">{brand ? brand.slice(0,1) : <ScanSearch size={18}/>}</span><div><strong>{brand || "Automatic detection"}</strong><small>{brand ? "Selected brand · model detection is automatic" : "Router brand and model will be identified if supported"}</small></div></div><label className="field-label" htmlFor="router-ip">Router address</label><input className="text-input mono" id="router-ip" value={ip} onChange={e => setIp(e.target.value)} placeholder="192.168.1.1"/><p className="helper-text">This is a common router address. If yours is different, enter the gateway address shown in your device's Wi-Fi network details. Automatic gateway detection will be provided by the local connector.</p><div className="notice"><ShieldCheck size={17}/><p>Routerly does not need your router model to start. The local connector will attempt device identification. Admin credentials are only needed if the router requires authentication.</p></div><button className="primary-button full-button" onClick={checkConnector} disabled={connector === "checking"}>{connector === "checking" ? "Checking local connector…" : "Check local connector"} <ArrowRight size={16}/></button>{connector === "offline" && <p className="error-note">Local connector not detected. Install and run the connector on a computer connected to this network.</p>}{connector === "available" && <p className="success-note">Local connector is responding. Router discovery and login are not yet enabled in this release.</p>}</div>}
              <div className="panel-foot"><ShieldCheck size={15}/> Your router credentials stay on your device.</div>
            </section>
            <aside className="right-column"><div className="panel info-panel"><div className="info-icon"><Wifi size={19}/></div><h3>One dashboard. Many brands.</h3><p>Manage supported routers through a consistent, easy-to-use interface.</p><div className="mini-brand-list"><span>TP-Link</span><span>ASUS</span><span>MikroTik</span><span>Ubiquiti</span><span>+ 70 brands</span></div></div><div className="panel checklist-panel"><h3>What you can manage</h3>{["Wi-Fi & wireless settings","Connected devices","Internet & LAN","Security & access","Network performance","Diagnostics & logs"].map(x => <div className="check-row" key={x}><Check size={15}/>{x}</div>)}<p className="small-note">Availability depends on router model and firmware.</p></div></aside></div>
          </> : <div className="panel empty-module"><div className="empty-icon"><Router size={25}/></div><h2>Connect a router to continue</h2><p>{modules.find(m => m.name === active)?.desc}. This section becomes available when a compatible router is connected.</p><button className="primary-button" onClick={() => {setActive("Overview");reset()}}>Connect a router <ArrowRight size={15}/></button></div>}
          <footer className="footer"><span>Routerly <span className="footer-dot">·</span> Local-first router management</span><span><Clock3 size={13}/> Compatibility depends on model & firmware</span></footer>
        </div>
      </section>
    </main>
  );
}
