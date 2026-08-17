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
<title>سامانه هوشمند پایش و هشدار جوی - مشهد</title>
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
.num {{ font-family: 'JetBrains Mono', 'Vazirmatn', monospace; }}
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
        <div class="brand">سامانه هوشمند پایش و هشدار جوی مشهد</div>
        <div class="time num">آخرین بروزرسانی: {generated_at} UTC</div>
    </div>
    
    <div class="main-content">
        <div class="panel gs-panel">
            <h2>پایشگر زنده جوی</h2>
            <div class="hero-grid" style="margin-top: 16px;">
                <div class="metric"><div class="metric-val num" id="val-temp">--°C</div><div class="metric-label">دما</div></div>
                <div class="metric"><div class="metric-val num" id="val-hum">--%</div><div class="metric-label">رطوبت</div></div>
                <div class="metric"><div class="metric-val num" id="val-wind">--</div><div class="metric-label">سرعت باد</div></div>
                <div class="metric"><div class="metric-val num" id="val-aqi">--</div><div class="metric-label">کیفیت هوا (AQI)</div></div>
            </div>
            
            <div id="map"></div>
            
            <div style="margin-top: 24px;">
                <h3>تحلیل روند ۲۴ ساعته</h3>
                <div class="timeline" id="timeline">
                    <!-- Bars generated via JS -->
                </div>
            </div>
        </div>
    </div>
    
    <div class="sidebar">
        <div class="panel gs-panel" style="margin-bottom: 24px;">
            <h3>شاخص ریسک</h3>
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
            <h3>گزارش هوش مصنوعی</h3>
            <p class="briefing" style="margin-top: 16px;">{ai_briefing}</p>
        </div>
        
        <div class="panel gs-panel">
            <h3 style="margin-bottom: 16px;">هشدارهای فعال</h3>
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


import re

def render_report(zone_configs, current_alerts, global_metrics=None, output_path=OUTPUT_PATH):
    """
    Dynamically updates the existing HTML dashboard using regex and string replacement.
    """
    if global_metrics is None:
        global_metrics = {
            "max_pop": 0.0, "max_wind": 0.0, "max_uvi": 0.0, "max_temp": -99.0,
            "current_temp_avg": 0.0, "current_hum_avg": 0.0, "zones_count": 0
        }

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
            "status": "هشدار فعال" if has_alert else "وضعیت سیستم: فعال"
        })

    # Calculate Risk Score
    if not current_alerts:
        risk_score = 10
        risk_label = "ریسک پایین"
        risk_color = "var(--safe)"
        risk_reason = "هیچ هشدار هواشناسی فعالی در منطقه مشهد وجود ندارد. شرایط پایدار است."
        alerts_html = '<div class="no-alerts">در حال حاضر هشدار فعالی وجود ندارد.</div>'
        ai_briefing = "شرایط جوی در تمام مناطق پایدار است. هیچ ناهنجاری در پنجره پیش‌بینی ۲۴ ساعته تشخیص داده نشده است."
    else:
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
            risk_label = "ریسک بحرانی"
            risk_color = "var(--danger)"
        elif max_level == 2:
            risk_score = 75
            risk_label = "ریسک بالا"
            risk_color = "var(--warning)"
        else:
            risk_score = 45
            risk_label = "ریسک فزاینده"
            risk_color = "var(--warning)"
            
        risk_reason = "ناهنجاری‌های متعددی تشخیص داده شد: " + "، ".join(set(reasons)) + ". با احتیاط عمل کنید."
        
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
                    مناطق: {zones_str}<br>
                    شروع: {alert.get('start', 'N/A')} | پایان: {alert.get('end', 'N/A')}
                </div>
            </div>
            """)
        alerts_html = "\n".join(cards)
        ai_briefing = "ناهنجاری‌هایی در منطقه مشهد تشخیص داده شده است. بر اساس داده‌های اخیر حسگرها، احتمال تأثیر شدید بالا است. لطفاً برای راهنمایی‌های خاص هر منطقه به مرکز هشدارهای فعال مراجعه کنید."

    # Read existing HTML
    with open(output_path, "r", encoding="utf-8") as f:
        html = f.read()

    generated_at = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")

    # Update Time
    html = re.sub(r'(آخرین بروزرسانی: ).*?( UTC)', rf'\g<1>{generated_at}\g<2>', html)

    # Update Live Visualizer Metrics (for script GSAP to animate to)
    # GSAP lines in script: gsap.to("#val-temp", { textContent: 28, ...
    temp_val = int(global_metrics.get("current_temp_avg", 0))
    hum_val = int(global_metrics.get("current_hum_avg", 0))
    wind_val = int(global_metrics.get("max_wind", 0))
    aqi_val = int(global_metrics.get("max_uvi", 0)) # Using UVI as proxy for AQI visually here
    
    html = re.sub(r'(gsap\.to\("#val-temp",\s*\{\s*textContent:\s*)\d+', rf'\g<1>{temp_val}', html)
    html = re.sub(r'(gsap\.to\("#val-hum",\s*\{\s*textContent:\s*)\d+', rf'\g<1>{hum_val}', html)
    html = re.sub(r'(gsap\.to\("#val-wind",\s*\{\s*textContent:\s*)\d+', rf'\g<1>{wind_val}', html)
    html = re.sub(r'(gsap\.to\("#val-aqi",\s*\{\s*textContent:\s*)\d+', rf'\g<1>{aqi_val}', html)

    # Update Risk Counter GSAP
    html = re.sub(r'(gsap\.to\("#risk-counter",\s*\{\s*textContent:\s*)\d+', rf'\g<1>{risk_score}', html)
    
    # Update Risk Circle Gradient
    html = re.sub(r'(conic-gradient\(var\(--danger\) 0%, var\(--danger\) )\d+(%, #1e293b )\d+(%,\s*#1e293b 100%\))', rf'\g<1>{risk_score}\g<2>{risk_score}\g<3>', html)

    # Update Risk Details using predictable structure matching
    html = re.sub(r'(<div style="font-weight: 700; color:\s*)[^;]+(; font-size: 18px;">)[^<]+(</div>)', rf'\g<1>{risk_color}\g<2>{risk_label}\g<3>', html)
    html = re.sub(r'(<div class="risk-reason">)[^<]+(</div>)', rf'\g<1>{risk_reason}\g<2>', html)

    # Update AI Briefing
    html = re.sub(r'(<p class="briefing" style="margin-top: 16px;">)[^<]+(</p>)', rf'\g<1>{ai_briefing}\g<2>', html)

    # Update Active Alerts HTML - This is trickier because it's a multiline block.
    # We will look for <h3 style="margin-bottom: 16px;">هشدارهای فعال</h3> and replace everything after it until the closing div.
    html = re.sub(
        r'(<h3 style="margin-bottom: 16px;">هشدارهای فعال</h3>\s*).*?(?=\s*</div>\s*</div>\s*</div>)', 
        rf'\g<1>{alerts_html}', 
        html, 
        flags=re.DOTALL
    )

    # Update zonePoints array
    zone_points_json = json.dumps(zone_points, ensure_ascii=False)
    html = re.sub(r'(var zonePoints = ).*?(;)', rf'\g<1>{zone_points_json}\g<2>', html)

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html)

    return output_path


if __name__ == "__main__":
    import weather_alert_check as wac
    zone_configs = wac.load_zones()
    alerts, _ = wac.collect_alerts_across_zones(owm_api_key="unused-in-mock")
    # mock metrics
    metrics = {
        "max_pop": 0.85, "max_wind": 16.5, "max_uvi": 8, "max_temp": 32,
        "current_temp_avg": 29.5, "current_hum_avg": 42.0, "zones_count": 10
    }
    path = render_report(zone_configs, alerts, metrics)
    print(f"Mission Control UI updated at {path}")
