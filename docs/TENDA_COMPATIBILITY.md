# Routerly Tenda compatibility

Routerly is now scoped to Tenda routers only. The first protocol target is the
Tenda AC10 V1.0 running firmware `V15.03.06.50_multi`. The AC10 web API is
undocumented and reverse-engineered; other Tenda models/firmware must be
detected and tested independently.

## Requested feature support

| Feature | AC10 API evidence | Routerly status |
|---|---|---|
| Connected-device list | `getOnlineList` | Read-only adapter required |
| Block / unblock device | `setBlackRule`, `delBlackRule` | Endpoint format verified |
| Per-device speed limit | `GetNetControlList`, `SetNetControlList` | Endpoint format verified; list replacement must preserve existing rules |
| Website blocking | `saveParentControlInfo`, `delParentalRule` | Endpoint format verified; per-device parental rule |
| Scheduled reboot | `GetSysAutoRebbotCfg`, `SetSysAutoRebbotCfg` | Endpoint format verified |
| Wi-Fi SSID/password | `WifiBasicGet/Set` | Setter documented but not live-tested; disruptive change |
| Admin password | `SysToolpassword`, `SysToolChangePwd` | Native form flow; not yet implemented |
| Private DNS | WAN DNS fields `dnsAuto`, `dns1`, `dns2` | Manual WAN DNS is documented; router-wide encrypted Private DNS/DoH/DoT is not established |
| VPN | PPTP/L2TP client/server endpoints | Available in some firmware; PPTP is obsolete/insecure and must not be presented as a recommended secure VPN |
| Total usage | `GetRouterStatus` exposes current upload/download rates | Cumulative historical usage is not established; do not infer it from instantaneous speed |

## Safety and implementation rules

- Never assume every Tenda router shares the AC10 API.
- Detect and display model/firmware before enabling writes.
- Keep router admin credentials only in the local connector process; never send
  them to the cloud relay or store them in browser local storage.
- Use a short-lived local session; clear it on disconnect and provide logout.
- Read current list-valued settings before modifying them because Tenda setters
  replace the entire list.
- Require explicit confirmation for Wi-Fi changes, admin-password changes and
  scheduled/instant reboots.
- Never issue a reboot as a GET request except the exact documented Tenda
  reboot endpoint after explicit confirmation.
- Return a truthful unsupported result when the detected firmware lacks a
  feature. Do not simulate successful configuration.
- No public WAN admin exposure or router port forwarding is required.

## Evidence boundary

The initial protocol reference is the reverse-engineered Tenda AC10 API
reference in `bluescorpian/tendactl` (MIT licensed). It reports live-tested
formats for device blocking, bandwidth control, parental rules and automatic
maintenance, but explicitly notes that some disruptive setters were not
tested. Routerly must independently validate its implementation before
advertising a control as operational.
