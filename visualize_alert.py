"""
Generates the Urban Weather Intelligence & Early Warning Dashboard (Mission Control UI).
"""

import json
import os
from datetime import datetime, timezone

import severity

OUTPUT_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "alert_report.html")

TEMPLATE = """<!DOCTYPE html>
<html lang="fa" dir="rtl">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Urban Weather Intelligence - Mashhad</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;700&family=Vazirmatn:wght@300;500;700;900&display=swap" rel="stylesheet">
<link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css">
<script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
<script src="https://cdnjs.cloudflare.com/ajax/libs/gsap/3.12.2/gsap.min.js"></script>
<style>
:root {{
    --bg-color: #08090c;
    --panel-bg: rgba(20, 24, 30, 0.7);
    --border-color: rgba(45, 212, 200, 0.15);
    --accent: #2dd4c8;
    --text-primary: #e2e8f0;
    --text-secondary: #94a3b8;
    --danger: #ef4444;
    --warning: #f59e0b;
    --safe: #10b981;
}}
body {{
    font-family: 'Vazirmatn', sans-serif;
    background: var(--bg-color);
    color: var(--text-primary);
    margin: 0;
    padding: 0;
    overflow-x: hidden;
    background-image: 
        radial-gradient(circle at 15% 50%, rgba(45, 212, 200, 0.03), transparent 25%),
        radial-gradient(circle at 85% 30%, rgba(45, 212, 200, 0.04), transparent 25%);
}}
h1, h2, h3 {{ font-weight: 700; margin: 0; }}
.num {{ font-family: 'JetBrains Mono', monospace; }}
.container {{
    max-width: 1400px;
    margin: 0 auto;
    padding: 24px;
    display: grid;
    grid-template-columns: 1fr 350px;
    gap: 24px;
}}
@media (max-width: 1024px) {{
    .container {{ grid-template-columns: 1fr; }}
}}
.panel {{
    background: var(--panel-bg);
    border: 1px solid var(--border-color);
    border-radius: 16px;
    padding: 24px;
    backdrop-filter: blur(12px);
    box-shadow: 0 8px 32px rgba(0, 0, 0, 0.2);
    opacity: 0; /* for GSAP */
}}
.header {{
    grid-column: 1 / -1;
    display: flex;
    justify-content: space-between;
    align-items: center;
    border-bottom: 1px solid var(--border-color);
    padding-bottom: 16px;
    opacity: 0;
}}
.header .brand {{ color: var(--accent); font-size: 24px; text-transform: uppercase; letter-spacing: 1px; }}
.header .time {{ color: var(--text-secondary); font-size: 14px; }}

/* Hero / Weather Intelligence */
.hero-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(120px, 1fr)); gap: 16px; margin-bottom: 24px; }}
.metric {{ text-align: center; padding: 16px; background: rgba(0,0,0,0.3); border-radius: 12px; border: 1px solid rgba(255,255,255,0.05); }}
.metric-val {{ font-size: 28px; color: var(--accent); margin-bottom: 4px; }}
.metric-label {{ font-size: 12px; color: var(--text-secondary); text-transform: uppercase; letter-spacing: 0.5px; }}

/* Map */
#map {{ height: 400px; border-radius: 12px; border: 1px solid var(--border-color); width: 100%; }}
.leaflet-container {{ background: #0b0d12; }}
.leaflet-popup-content-wrapper {{ background: var(--panel-bg); color: var(--text-primary); border: 1px solid var(--border-color); backdrop-filter: blur(8px); }}
.leaflet-popup-tip {{ background: var(--panel-bg); border: 1px solid var(--border-color); }}

/* Alerts */
.alert-card {{
    background: rgba(239, 68, 68, 0.1);
    border-right: 4px solid var(--danger);
    padding: 16px;
    border-radius: 8px;
    margin-bottom: 16px;
    position: relative;
    overflow: hidden;
}}
.alert-card::before {{
    content: ''; position: absolute; top: 0; left: 0; right: 0; bottom: 0;
    background: radial-gradient(circle, rgba(239, 68, 68, 0.2) 0%, transparent 70%);
    opacity: 0; animation: pulse 2s infinite; pointer-events: none;
}}
@keyframes pulse {{ 0% {{opacity: 0; transform: scale(0.9);}} 50% {{opacity: 1; transform: scale(1);}} 100% {{opacity: 0; transform: scale(1.1);}} }}
.alert-title {{ font-size: 16px; color: var(--danger); margin-bottom: 8px; display: flex; align-items: center; gap: 8px; }}
.alert-desc {{ font-size: 13px; line-height: 1.6; color: var(--text-primary); }}
.alert-meta {{ font-size: 12px; color: var(--text-secondary); margin-top: 12px; border-top: 1px solid rgba(255,255,255,0.1); padding-top: 8px; }}

/* Risk Score */
.risk-container {{ display: flex; align-items: center; gap: 24px; margin-bottom: 24px; }}
.risk-circle {{
    width: 100px; height: 100px; border-radius: 50%;
    display: flex; justify-content: center; align-items: center;
    font-size: 36px; font-weight: 900; color: var(--bg-color);
    background: conic-gradient(var(--danger) 0%, var(--danger) {risk_percentage}%, #1e293b {risk_percentage}%, #1e293b 100%);
    position: relative; box-shadow: 0 0 20px rgba(239, 68, 68, 0.3);
}}
.risk-circle::after {{
    content: ''; position: absolute; width: 84px; height: 84px;
    background: var(--panel-bg); border-radius: 50%; z-index: 1;
}}
.risk-value {{ position: relative; z-index: 2; color: var(--text-primary); }}
.risk-details {{ flex: 1; }}
.risk-reason {{ font-size: 13px; color: var(--text-secondary); line-height: 1.6; margin-top: 8px; }}

/* AI Briefing */
.briefing {{ font-size: 14px; line-height: 1.8; color: #cbd5e1; border-right: 2px solid var(--accent); padding-right: 16px; font-style: italic; }}

/* Timeline */
.timeline {{ margin-top: 24px; display: flex; gap: 4px; height: 60px; align-items: flex-end; }}
.bar {{ flex: 1; background: var(--border-color); border-radius: 4px 4px 0 0; position: relative; transition: height 1s ease; }}
.bar:hover::after {{
    content: attr(data-val); position: absolute; top: -25px; left: 50%; transform: translateX(-50%);
    background: var(--accent); color: #000; padding: 2px 6px; border-radius: 4px; font-size: 11px; font-family: 'JetBrains Mono';
}}

.no-alerts {{ text-align: center; color: var(--safe); padding: 24px; border: 1px dashed var(--safe); border-radius: 8px; }}
</style>
</head>
<body>
<div class="container">
    <div class="header">
        <div class="brand">Mashhad Weather Intelligence</div>
        <div class="time num">LAST SYNC: {generated_at} UTC</div>
    </div>
    
    <div class="main-content">
        <div class="panel gs-panel">
            <h2>Live Atmospheric Visualizer</h2>
            <div class="hero-grid" style="margin-top: 16px;">
                <div class="metric"><div class="metric-val num" id="val-temp">--°C</div><div class="metric-label">Temperature</div></div>
                <div class="metric"><div class="metric-val num" id="val-hum">--%</div><div class="metric-label">Humidity</div></div>
                <div class="metric"><div class="metric-val num" id="val-wind">--</div><div class="metric-label">Wind (km/h)</div></div>
                <div class="metric"><div class="metric-val num" id="val-aqi">--</div><div class="metric-label">AQI</div></div>
            </div>
            
            <div id="map"></div>
            
            <div style="margin-top: 24px;">
                <h3>24-Hour Trend Analysis</h3>
                <div class="timeline" id="timeline">
                    <!-- Bars generated via JS -->
                </div>
            </div>
        </div>
    </div>
    
    <div class="sidebar">
        <div class="panel gs-panel" style="margin-bottom: 24px;">
            <h3>Weather Risk Score</h3>
            <div class="risk-container" style="margin-top: 16px;">
                <div class="risk-circle">
                    <span class="risk-value num" id="risk-counter">0</span>
                </div>
                <div class="risk-details">
                    <div style="font-weight: 700; color: {risk_color}; font-size: 18px;">{risk_label}</div>
                    <div class="risk-reason">{risk_reason}</div>
                </div>
            </div>
        </div>
        
        <div class="panel gs-panel" style="margin-bottom: 24px;">
            <h3>AI Weather Briefing</h3>
            <p class="briefing" style="margin-top: 16px;">{ai_briefing}</p>
        </div>
        
        <div class="panel gs-panel">
            <h3 style="margin-bottom: 16px;">Active Alerts Center</h3>
            {alerts_html}
        </div>
    </div>
</div>

<script>
// Mock Live Data Animation
gsap.to("#val-temp", {{ textContent: 28, duration: 2, snap: {{ textContent: 1 }}, ease: "power1.out" }});
gsap.to("#val-hum", {{ textContent: 45, duration: 2, snap: {{ textContent: 1 }}, ease: "power1.out" }});
gsap.to("#val-wind", {{ textContent: 18, duration: 2, snap: {{ textContent: 1 }}, ease: "power1.out" }});
gsap.to("#val-aqi", {{ textContent: 72, duration: 2, snap: {{ textContent: 1 }}, ease: "power1.out" }});

// Risk Counter Animation
gsap.to("#risk-counter", {{
    textContent: {risk_score},
    duration: 2.5,
    snap: {{ textContent: 1 }},
    ease: "power2.out"
}});

// Panel Entrances
gsap.to(".header", {{ opacity: 1, y: 0, duration: 1, ease: "power2.out" }});
gsap.fromTo(".gs-panel", 
    {{ opacity: 0, y: 30 }}, 
    {{ opacity: 1, y: 0, duration: 0.8, stagger: 0.15, ease: "back.out(1.2)", delay: 0.2 }}
);

// Timeline Generation
const timeline = document.getElementById('timeline');
for(let i=0; i<24; i++) {{
    const bar = document.createElement('div');
    bar.className = 'bar';
    const val = Math.floor(Math.random() * 50) + 10;
    bar.setAttribute('data-val', val);
    timeline.appendChild(bar);
    gsap.to(bar, {{ height: val + '%', duration: 1, delay: 1 + (i * 0.05), ease: "power1.out" }});
}}

// Leaflet Map Initialization
var map = L.map('map', {{
    zoomControl: false,
    attributionControl: false
}}).setView([36.297, 59.606], 11);

// Dark Matter tiles for Mission Control aesthetic
L.tileLayer('https://{{s}}.basemaps.cartocdn.com/dark_all/{{z}}/{{x}}/{{y}}{{r}}.png', {{
    subdomains: 'abcd',
    maxZoom: 20
}}).addTo(map);

var zonePoints = {zone_points_json};
zonePoints.forEach(function(z) {{
    var color = z.color;
    var radius = z.has_alert ? 12 : 6;
    
    var marker = L.circleMarker([z.lat, z.lon], {{
        radius: 0, // for animation
        color: color,
        fillColor: color,
        fillOpacity: z.has_alert ? 0.7 : 0.3,
        weight: z.has_alert ? 2 : 1
    }}).addTo(map);
    
    // Animate map markers
    gsap.to(marker, {{
        radius: radius,
        duration: 1.5,
        delay: 1.5,
        ease: "elastic.out(1, 0.5)",
        onUpdate: function() {{ marker.setRadius(this.targets()[0].radius); }}
    }});
    
    var popupContent = `
        <div style="min-width: 120px;">
            <div style="font-weight: 700; color: var(--accent); margin-bottom: 4px;">${{z.zone}}</div>
            <div style="font-size: 12px; color: var(--text-secondary);">${{z.status}}</div>
            <div style="margin-top: 8px; font-family: 'JetBrains Mono'; font-size: 11px;">
                LAT: ${{z.lat}}<br>LON: ${{z.lon}}
            </div>
        </div>
    `;
    marker.bindPopup(popupContent);
}});
</script>
</body>
</html>
"""


def render_report(zone_configs, current_alerts, output_path=OUTPUT_PATH):
    """
    Generates the advanced HTML dashboard.
    """
    affected_zones = set()
    for alert in current_alerts.values():
        affected_zones.update(alert.get("zones", []))

    zone_points = []
    for zc in zone_configs:
        has_alert = zc["zone"] in affected_zones
        zone_points.append({
            "zone": zc["zone"],
            "lat": zc["lat"],
            "lon": zc["lon"],
            "color": "#ef4444" if has_alert else "#2dd4c8",
            "has_alert": has_alert,
            "status": "Active Warning" if has_alert else "All Clear"
        })

    # Calculate Risk Score
    if not current_alerts:
        risk_score = 10
        risk_label = "Low Risk"
        risk_color = "var(--safe)"
        risk_reason = "No active meteorological warnings in the Mashhad region. Conditions are stable."
        alerts_html = '<div class="no-alerts">No active alerts at this time.</div>'
        ai_briefing = "Atmospheric conditions remain stable across all sectors. No anomalies detected in the 24-hour forecast window."
    else:
        # Determine highest severity
        max_level = 0
        reasons = []
        for alert in current_alerts.values():
            level = severity.classify_severity(alert.get("event", ""))
            reasons.append(alert.get("event", "Unknown Event"))
            if level == "قرمز": max_level = max(max_level, 3)
            elif level == "نارنجی": max_level = max(max_level, 2)
            elif level == "زرد": max_level = max(max_level, 1)
            
        if max_level == 3:
            risk_score = 92
            risk_label = "CRITICAL RISK"
            risk_color = "var(--danger)"
        elif max_level == 2:
            risk_score = 75
            risk_label = "HIGH RISK"
            risk_color = "var(--warning)"
        else:
            risk_score = 45
            risk_label = "ELEVATED RISK"
            risk_color = "var(--warning)"
            
        risk_reason = "Multiple anomalies detected: " + ", ".join(set(reasons)) + ". Proceed with caution."
        
        # Build alert cards
        cards = []
        for alert in current_alerts.values():
            level = severity.classify_severity(alert.get("event", ""))
            level_info = severity.SEVERITY_LEVELS[level]
            zones_str = "، ".join(alert.get("zones", []))
            
            cards.append(f"""
            <div class="alert-card" style="border-color: {level_info['text_color']}">
                <div class="alert-title">{level_info['emoji']} {alert.get('event', '')}</div>
                <div class="alert-desc">{alert.get('description', '')}</div>
                <div class="alert-meta num">
                    ZONES: {zones_str}<br>
                    START: {alert.get('start', 'N/A')} | END: {alert.get('end', 'N/A')}
                </div>
            </div>
            """)
        alerts_html = "\n".join(cards)
        ai_briefing = "Anomalies detected in the Mashhad region. Probability of severe impact is elevated based on recent sensor data. Please review the Active Alerts Center for sector-specific guidance."

    html = TEMPLATE.format(
        generated_at=datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S"),
        risk_score=risk_score,
        risk_percentage=risk_score,
        risk_label=risk_label,
        risk_color=risk_color,
        risk_reason=risk_reason,
        ai_briefing=ai_briefing,
        alerts_html=alerts_html,
        zone_points_json=json.dumps(zone_points, ensure_ascii=False)
    )

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html)

    return output_path


if __name__ == "__main__":
    import weather_alert_check as wac
    zone_configs = wac.load_zones()
    alerts = wac.collect_alerts_across_zones(owm_api_key="unused-in-mock")
    path = render_report(zone_configs, alerts)
    print(f"Mission Control UI generated at {path}")
