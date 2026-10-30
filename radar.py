import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import json
import os
from datetime import datetime, timedelta
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# ==================== CONFIGURACIÓN ====================
st.set_page_config(page_title="🦈 Robot Avizor Cava — 4 Velocidades", page_icon="🦈", layout="wide")
DIAS_LIQUIDACION_FONDOS = 4
BONUS_BONITA = 0.90
SIZE_BONUS_BONITA = 1.20
VENTANAS_ZIGZAG = [3, 5, 7, 10, 14]

st.markdown("""
<style>
    div[data-testid="stMetricValue"] { font-size: 1.3rem; font-weight: 700; }
    .card-orden { background-color: #0f172a; border: 1px solid #1e293b; border-left: 6px solid #3b82f6; padding: 16px; border-radius: 10px; margin-bottom: 12px; }
    .semaforo-verde { background-color: #143320; border-left: 6px solid #22c55e; padding: 16px; border-radius: 10px; margin-bottom: 12px;}
    .semaforo-rojo { background-color: #371515; border-left: 6px solid #ef4444; padding: 16px; border-radius: 10px; margin-bottom: 12px;}
    .semaforo-amarillo { background-color: #332b14; border-left: 6px solid #eab308; padding: 16px; border-radius: 10px; margin-bottom: 12px;}
    .aviso-buffer { background-color: #332b14; border-left: 6px solid #eab308; padding: 12px; border-radius: 8px; font-size: 0.9rem; margin-top: 8px; }
    .diagnostico-bonita { font-size: 0.85rem; color: #9ca3af; background: #1f2937; padding: 8px; border-radius: 6px; margin-top: 5px; }
    
    /* NUEVO DISEÑO DCA */
    .dca-card {
        display: flex;
        align-items: center;
        padding: 16px;
        border-radius: 12px;
        margin-top: 15px;
        margin-bottom: 15px;
        border-left: 8px solid;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
    }
    .dca-icon { font-size: 2.5rem; margin-right: 20px; }
    .dca-content { flex-grow: 1; }
    .dca-title { font-weight: 800; font-size: 1.15rem; margin-bottom: 4px; letter-spacing: 0.5px; }
    .dca-text { font-size: 0.95rem; opacity: 0.9; line-height: 1.4; }
    .dca-mult { font-size: 1.5rem; font-weight: 900; margin-left: 20px; padding: 8px 16px; border-radius: 8px; background: rgba(0,0,0,0.3); }
</style>
""", unsafe_allow_html=True)

# ==================== PERSISTENCIA ====================
BASE_DIR = os.path.dirname(os.path.abspath(__file__)) if "__file__" in locals() else "."
F_SALDOS = os.path.join(BASE_DIR, "saldos_cartera_cava.json")

def cargar_json(p, d):
    if os.path.exists(p):
        try:
            with open(p, "r", encoding="utf-8") as f:
                data = json.load(f)
                for k, v in d.items():
                    if k not in data: data[k] = v
                return data
        except: return d
    return d

def guardar_json(p, d):
    try:
        with open(p, "w", encoding="utf-8") as f: json.dump(d, f, indent=4, ensure_ascii=False)
        return True
    except: return False

CAPITAL_RADAR_DEFAULT = 60000.0
COLCHON_EMERGENCIAS_DEFAULT = 10000.0
ISIN_MONETARIO_NODRIZA = "FR0000447823"

# ==================== CATÁLOGOS ====================
FONDOS = {
    "AXA Trésor Court Terme C": {"ticker": "^IRX", "es_monetario": True, "isin": ISIN_MONETARIO_NODRIZA, "hora_corte": 10, "peso_obj": 0.25, "saldo_default": 15000.0, "c1": -0.01, "c2": -0.02, "c3": -0.03, "v1": 0.10, "v2": 0.20, "v3": 0.30, "rsi_v1": 80, "rsi_v2": 85, "rsi_v3": 90},
    "Fidelity S&P 500 Index P": {"ticker": "^GSPC", "es_monetario": False, "isin": "IE00BYX5MX67", "hora_corte": 16, "peso_obj": 0.25, "saldo_default": 15000.0, "c1": -0.04, "c2": -0.10, "c3": -0.20, "v1": 0.15, "v2": 0.25, "v3": 0.35, "rsi_v1": 70, "rsi_v2": 75, "rsi_v3": 80},
    "Fidelity MSCI World Index P": {"ticker": "URTH", "es_monetario": False, "isin": "IE00BYX5NX33", "hora_corte": 16, "peso_obj": 0.10, "saldo_default": 6000.0, "c1": -0.04, "c2": -0.10, "c3": -0.18, "v1": 0.14, "v2": 0.22, "v3": 0.32, "rsi_v1": 70, "rsi_v2": 75, "rsi_v3": 80},
    "MyInvestor Nasdaq 100 FI": {"ticker": "^NDX", "es_monetario": False, "isin": "ES0165265002", "hora_corte": 12, "peso_obj": 0.10, "saldo_default": 6000.0, "c1": -0.06, "c2": -0.15, "c3": -0.25, "v1": 0.18, "v2": 0.30, "v3": 0.45, "rsi_v1": 70, "rsi_v2": 75, "rsi_v3": 80},
    "iShares Europe Equity Index A2": {"ticker": "VGK", "es_monetario": False, "isin": "LU0836512706", "hora_corte": 10, "peso_obj": 0.03, "saldo_default": 1800.0, "c1": -0.04, "c2": -0.09, "c3": -0.16, "v1": 0.12, "v2": 0.20, "v3": 0.28, "rsi_v1": 68, "rsi_v2": 73, "rsi_v3": 78},
    "Wellington Global Health Care D": {"ticker": "XLV", "es_monetario": False, "isin": "IE00BF2ZVB54", "hora_corte": 12, "peso_obj": 0.03, "saldo_default": 1800.0, "c1": -0.04, "c2": -0.09, "c3": -0.16, "v1": 0.14, "v2": 0.22, "v3": 0.30, "rsi_v1": 70, "rsi_v2": 75, "rsi_v3": 80},
    "Guinness Global Energy D EUR": {"ticker": "XLE", "es_monetario": False, "isin": "IE00B3CCJB88", "hora_corte": 14, "peso_obj": 0.02, "saldo_default": 1200.0, "c1": -0.06, "c2": -0.14, "c3": -0.24, "v1": 0.18, "v2": 0.28, "v3": 0.40, "rsi_v1": 70, "rsi_v2": 75, "rsi_v3": 80},
    "Vanguard Global Bond Hedged": {"ticker": "BND", "es_monetario": False, "isin": "IE00B18GC888", "hora_corte": 12, "peso_obj": 0.01, "saldo_default": 600.0, "c1": -0.03, "c2": -0.06, "c3": -0.10, "v1": 0.08, "v2": 0.14, "v3": 0.20, "rsi_v1": 68, "rsi_v2": 72, "rsi_v3": 76},
    "Pictet - Nutrition P EUR": {"ticker": "XLP", "es_monetario": False, "isin": "LU0366534344", "hora_corte": 12, "peso_obj": 0.01, "saldo_default": 600.0, "c1": -0.04, "c2": -0.09, "c3": -0.16, "v1": 0.12, "v2": 0.20, "v3": 0.28, "rsi_v1": 68, "rsi_v2": 73, "rsi_v3": 78}
}
CORTOS_HOPLA = {"S&P 500 (Corto)": {"ticker": "^GSPC"}, "Nasdaq 100 (Corto)": {"ticker": "^NDX"}, "Oro (Corto)": {"ticker": "GC=F"}}
LARGO_PLAZO = {
    "Oro Físico (Largo)": {"ticker": "GC=F", "isin": "IE00B4ND3602", "peso_obj": 0.15, "saldo_default": 9000.0, "c1": -0.05, "c2": -0.10, "c3": -0.18, "v1": 0.15, "v2": 0.25, "v3": 0.35, "rsi_v1": 70, "rsi_v2": 75, "rsi_v3": 80},
    "Bitcoin (Largo)": {"ticker": "BTC-USD", "isin": "BTC-USD", "peso_obj": 0.05, "saldo_default": 3000.0, "c1": -0.15, "c2": -0.30, "c3": -0.50, "v1": 0.35, "v2": 0.65, "v3": 1.00, "rsi_v1": 75, "rsi_v2": 80, "rsi_v3": 85}
}
ACTIVOS_RADAR = {**FONDOS, **LARGO_PLAZO}

default_state = {"colchon_emergencias": COLCHON_EMERGENCIAS_DEFAULT, "saldos": {k: v["saldo_default"] for k, v in ACTIVOS_RADAR.items()}, "objetivos": {k: CAPITAL_RADAR_DEFAULT * v["peso_obj"] for k, v in ACTIVOS_RADAR.items()}, "ordenes_pendientes": []}
estado_cartera = cargar_json(F_SALDOS, default_state)
for k, v in ACTIVOS_RADAR.items():
    if k not in estado_cartera["saldos"]: estado_cartera["saldos"][k] = v["saldo_default"]
    if k not in estado_cartera["objetivos"]: estado_cartera["objetivos"][k] = CAPITAL_RADAR_DEFAULT * v["peso_obj"]

# ==================== DATA ====================
@st.cache_data(ttl=60)
def get_vix_data():
    try:
        h = yf.Ticker("^VIX").history(period="1mo")
        v = float(h['Close'].iloc[-1]); s10 = float(h['Close'].tail(10).mean())
        return {"actual": v, "sma10": s10, "tension": (v / s10) - 1.0}
    except: return {"actual": 18.0, "sma10": 18.0, "tension": 0.0}

@st.cache_data(ttl=300)
def get_market_data(ticker):
    try:
        lb = 365 if "BTC" in ticker else 252
        h = yf.Ticker(ticker).history(period="2y")
        if len(h) < 200: return None
        h52 = h.iloc[-lb:].copy()
        p = float(h52['Close'].iloc[-1]); mx = float(h52['High'].max())
        sma200 = float(h['Close'].rolling(200).mean().iloc[-1])
        delta = h52['Close'].diff()
        g = delta.clip(lower=0).ewm(alpha=1/14, adjust=False).mean()
        l = -delta.clip(upper=0).ewm(alpha=1/14, adjust=False).mean()
        rsi = float((100 - 100/(1 + g/l.replace(0, 1e-9))).iloc[-1])
        
        h_w = h.resample('W').agg({'High':'max','Low':'min','Close':'last'}).dropna()
        macd = h_w['Close'].ewm(span=12).mean() - h_w['Close'].ewm(span=26).mean()
        sig = macd.ewm(span=9).mean()
        macd_alcista = bool(macd.iloc[-1] > sig.iloc[-1])
        macd_sobre_cero = bool(macd.iloc[-1] > 0)
        
        l14 = h_w['Low'].rolling(14).min(); h14 = h_w['High'].rolling(14).max()
        k = 100 * ((h_w['Close'] - l14) / (h14 - l14).replace(0, 1e-9))
        stoch_k, stoch_d = float(k.iloc[-1]), float(k.rolling(3).mean().iloc[-1])
        
        la_bonita = bool(macd_alcista and (stoch_k < 40 and stoch_k > stoch_d))
        
        max_10d = float(h52['High'].shift(1).rolling(10).max().iloc[-1])
        bos = bool(p > max_10d) if not pd.isna(max_10d) else False
        
        return {
            "precio": p, "max52": mx, "caida": (p/mx - 1.0) if mx > 0 else 0.0,
            "dist_sma": (p/sma200 - 1.0) if sma200 > 0 else 0.0, "rsi": rsi,
            "macd_alcista": macd_alcista, "macd_cero": macd_sobre_cero, "stoch_k": stoch_k, "stoch_d": stoch_d,
            "la_bonita": la_bonita, "bos": bos, "max_10d": max_10d, "hist": h
        }
    except: return None

# ==================== GRÁFICAS ====================
def graficar_activo(hist, nombre):
    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.05, row_heights=[0.7, 0.3], subplot_titles=(f"Precio y Medias - {nombre}", "RSI (14)"))
    fig.add_trace(go.Scatter(x=hist.index, y=hist['Close'], name='Precio', line=dict(color='#3b82f6', width=2)), row=1, col=1)
    fig.add_trace(go.Scatter(x=hist.index, y=hist['Close'].rolling(50).mean(), name='SMA 50', line=dict(color='#eab308', dash='dash')), row=1, col=1)
    fig.add_trace(go.Scatter(x=hist.index, y=hist['Close'].rolling(200).mean(), name='SMA 200', line=dict(color='#ef4444', dash='dot')), row=1, col=1)
    
    delta = hist['Close'].diff()
    gain = delta.clip(lower=0).ewm(alpha=1/14, adjust=False).mean()
    loss = -delta.clip(upper=0).ewm(alpha=1/14, adjust=False).mean()
    rsi_series = 100 - (100 / (1 + gain/loss.replace(0, 1e-9)))
    
    fig.add_trace(go.Scatter(x=hist.index, y=rsi_series, name='RSI', line=dict(color='#a855f7')), row=2, col=1)
    fig.add_hline(y=70, line_dash="dot", line_color="#ef4444", row=2, col=1)
    fig.add_hline(y=30, line_dash="dot", line_color="#22c55e", row=2, col=1)
    fig.update_layout(height=500, template="plotly_dark", margin=dict(l=20, r=20, t=40, b=20), hovermode="x unified")
    return fig

# ==================== BUFFER INTELIGENTE ====================
def calcular_factor_buffer(d, modo_buffer):
    if modo_buffer == "Exacto (sin buffer)": return 1.0, "Modo exacto: se espera al gatillo real."
    if modo_buffer == "Anticipado agresivo (25%)": return 0.75, "Modo agresivo: se anticipa un 25%."
    señales_reversion = []
    if d['rsi'] < 30: señales_reversion.append("RSI < 30")
    if d['la_bonita']: señales_reversion.append("Pauta Bonita")
    if d['dist_sma'] < -0.15: señales_reversion.append("Precio muy hundido")
    if señales_reversion: return 1.0, f"Buffer desactivado por señales de reversión: {', '.join(señales_reversion)}."
    if d['dist_sma'] < 0 and not d['macd_alcista']: return 0.85, "Buffer 15% activo: contexto bajista confirmado."
    return 1.0, "Contexto ambiguo: se espera al gatillo exacto."

# ==================== SEMÁFORO DCA ====================
def evaluar_semaforo_dca(d):
    if d['stoch_k'] > 80:
        return {"bg": "#371515", "border": "#ef4444", "icon": "🛑", "title": "APORTACIÓN MÍNIMA (Sobrecarga)", "msg": "El estocástico semanal está en sobrecompra extrema (>80). Prohibido añadir extra; limita la aportación al mínimo mensual.", "mult": "0.5x", "color": "#f87171"}
    elif d['la_bonita']:
        return {"bg": "#143320", "border": "#22c55e", "icon": "🚀", "title": "APORTACIÓN EXTRA (Pauta Bonita)", "msg": "¡MACD alcista y estocástico girando desde sobreventa! Es el momento estadístico óptimo para inyectar más capital.", "mult": "1.5x", "color": "#4ade80"}
    elif d['macd_alcista']:
        return {"bg": "#332b14", "border": "#eab308", "icon": "✅", "title": "APORTACIÓN NORMAL (Tendencia Sana)", "msg": "El MACD semanal es alcista. El viento sopla a favor; mantén tu ritmo de aportación DCA habitual.", "mult": "1.0x", "color": "#facc15"}
    else:
        return {"bg": "#2d1b12", "border": "#f97316", "icon": "⚠️", "title": "APORTACIÓN MÍNIMA (Prudencia)", "msg": "El MACD semanal es bajista. El mercado está débil; mantén la pólvora seca en el monetario AXA.", "mult": "0.5x", "color": "#fb923c"}

# ==================== LÓGICA FONDOS ====================
def evaluar_fondo(d, reglas, v_info, cap_posicion, modo_buffer):
    if reglas.get("es_monetario"): return 0, "BÚNKER", "Fondo Monetario activo.", 0, 0, 0, cap_posicion, 0, 1.0, ""
    caida = d["caida"]; la_bonita = d.get("la_bonita", False)
    factor_buffer, motivo_buffer = calcular_factor_buffer(d, modo_buffer)
    factor = factor_buffer * (BONUS_BONITA if la_bonita else 1.0)
    c1_ef, c2_ef, c3_ef = reglas["c1"]*factor, reglas["c2"]*factor, reglas["c3"]*factor
    gatillo_teorico = d["max52"] * (1.0 + reglas["c1"]); gatillo_aplicado = d["max52"] * (1.0 + c1_ef)
    base_calc = max(cap_posicion, 1000.0); size_mult = SIZE_BONUS_BONITA if la_bonita else 1.0
    t1, t2, t3 = base_calc*0.30*size_mult, base_calc*0.30*size_mult, base_calc*0.40*size_mult
    if caida <= c3_ef: zona, nom, eur, nom_z = 3, "Tramo 3 (40%)", t3, "ZONA 3"
    elif caida <= c2_ef: zona, nom, eur, nom_z = 2, "Tramo 2 (30%)", t2, "ZONA 2"
    elif caida <= c1_ef: zona, nom, eur, nom_z = 1, "Tramo 1 (30%)", t1, "ZONA 1"
    else:
        dist = abs(caida - c1_ef); motivo = f"Falta {dist:.2%} para el gatillo aplicado ({gatillo_aplicado:,.2f}). Teórico: {gatillo_teorico:,.2f}."
        if la_bonita: motivo += " ⚠️ LA BONITA ACTIVA."
        return 0, "ESPERAR", motivo, dist, gatillo_aplicado, 1, t1, 0, factor, motivo_buffer
    if abs(caida) >= 0.25 and v_info["actual"] < 20.0: return 0, "BLOQUEADO VIX", "Caída sin pánico.", 0, 0, zona, eur, 0, factor, motivo_buffer
    motivo = f"¡GATILLO! Traspaso de {eur:,.0f} € ({nom})."
    if la_bonita: motivo += " ⚠️ PAUTA BONITA (+20%)."
    return zona, f"COMPRAR {nom_z}", motivo, 0, 0, zona, eur, size_mult, factor, motivo_buffer

def evaluar_venta_fondo(d, reglas):
    ds, rsi = d["dist_sma"], d["rsi"]
    if ds >= reglas["v3"] and rsi >= reglas["rsi_v3"]: return 3, "TRASPASAR A REFUGIO TOTAL", "Sobreextensión extrema. Traspasar 80% al monetario."
    if ds >= reglas["v2"] and rsi >= reglas["rsi_v2"]: return 2, "TRASPASAR A REFUGIO PARCIAL", "Fuerte tensión. Traspasar 30% al monetario."
    return 0, "MANTENER", "Parámetros sanos."

# ==================== LÓGICA HOPLA (CONSENSO) ====================
def detectar_swing_points(series, window=5):
    swings = []
    for i in range(window, len(series) - window):
        if series[i] == max(series[i-window:i+window+1]): swings.append(("max", i, series[i]))
        elif series[i] == min(series[i-window:i+window+1]): swings.append(("min", i, series[i]))
    filtrados = []
    for s in swings:
        if not filtrados or s[0] != filtrados[-1][0]: filtrados.append(s)
        elif (s[0] == "max" and s[2] > filtrados[-1][2]) or (s[0] == "min" and s[2] < filtrados[-1][2]): filtrados[-1] = s
    return filtrados

def detectar_trampa_techo_falso_single(hist, window=5):
    cierres = hist['Close'].values; swings = detectar_swing_points(cierres, window=window)
    if len(swings) < 5: return None, "Insuficientes swings."
    maximos = [s for s in swings if s[0] == "max"]
    if len(maximos) < 2: return None, "No hay dos máximos."
    max1, max2 = maximos[-2], maximos[-1]
    if not (0.985 <= max2[2] / max1[2] <= 1.015): return None, "Dilatación no válida."
    min_entre = [s for s in swings if s[0] == "min" and max1[1] < s[1] < max2[1]]
    if not min_entre: return None, "No valle central."
    valle = min_entre[-1]; precio_actual = cierres[-1]
    if precio_actual >= valle[2]: return None, "Precio no rompe valle."
    swing_post = [s for s in swings if s[1] > valle[1]]
    if not swing_post: return None, "No Onda B."
    onda_b = next((s for s in swing_post if s[0] == "max" and s[2] < max2[2]), None)
    if not onda_b: return None, "No Onda B válida."
    stop_loss = max(max1[2], max2[2]) * 1.01
    return {"señal": "SHORT_HOPLA", "entrada": precio_actual, "stop_loss": stop_loss, "objetivo": valle[2] * 0.95, "motivo": f"Trampa confirmada. Techo {max2[2]:.2f} barrió stops. Ruptura valle {valle[2]:.2f}."}, "Señal HOPLA"

def detectar_trampa_consenso(d, hist):
    if not d.get('macd_alcista', False): 
        return None, "MACD semanal bajista. No hay tendencia alcista que agotar.", {}
    
    resultados = {}
    for w in VENTANAS_ZIGZAG:
        señal, msg = detectar_trampa_techo_falso_single(hist, window=w)
        resultados[w] = señal is not None
    
    ventanas_activas = [w for w, activa in resultados.items() if activa]
    num_activas = len(ventanas_activas)
    
    if num_activas >= 3:
        señal_principal, _ = detectar_trampa_techo_falso_single(hist, window=ventanas_activas[0])
        return señal_principal, f"Señal ROBUSTA ({num_activas}/{len(VENTANAS_ZIGZAG)} ventanas). Ventanas activas: {ventanas_activas}", resultados
    elif num_activas > 0:
        señal_principal, _ = detectar_trampa_techo_falso_single(hist, window=ventanas_activas[0])
        return señal_principal, f"Señal DÉBIL ({num_activas}/{len(VENTANAS_ZIGZAG)} ventanas). Posible artefacto del gráfico. Ventanas activas: {ventanas_activas}", resultados
    else:
        return None, "Ninguna ventana detecta la trampa HOPLA.", resultados

# ==================== LARGO PLAZO ====================
def evaluar_largo_plazo(d, reglas, v_info, cap_posicion):
    caida = d["caida"]; v_act = v_info["actual"]
    c1, c2, c3 = reglas["c1"], reglas["c2"], reglas["c3"]
    base_calc = max(cap_posicion, 1000.0); t1, t2, t3 = base_calc*0.3, base_calc*0.3, base_calc*0.4
    if caida <= c3: zona, nom, eur = 3, "Tramo 3 (40%)", t3
    elif caida <= c2: zona, nom, eur = 2, "Tramo 2 (30%)", t2
    elif caida <= c1: zona, nom, eur = 1, "Tramo 1 (30%)", t1
    else:
        dist = abs(caida - c1); target = d["max52"] * (1.0 + c1)
        return 0, "ESPERAR", f"Falta {dist:.2%} (Gatillo: {target:,.2f})", dist, target, 1, t1
    if abs(caida) >= 0.25 and v_act < 20.0: return 0, "BLOQUEADO VIX", f"Caída del {caida:.1%} sin pánico (VIX {v_act:.1f} < 20). El mercado puede seguir cayendo.", 0, 0, zona, eur
    return zona, f"COMPRAR ZONA {zona}", f"¡Gatillo! Comprar {eur:,.0f} € en Spot. Sin stop loss.", 0, 0, zona, eur

def evaluar_venta_largo_plazo(d, reglas):
    ds, rsi = d["dist_sma"], d["rsi"]
    if ds >= reglas["v3"] and rsi >= reglas["rsi_v3"]: return 3, "RECOGER BENEFICIOS (80%)", "Sobreextensión extrema. Vender 80% a efectivo."
    if ds >= reglas["v2"] and rsi >= reglas["rsi_v2"]: return 2, "RECOGER BENEFICIOS (30%)", "Fuerte tensión. Vender 30% a efectivo."
    return 0, "MANTENER", "Parámetros sanos."

# ==================== REGISTRO ÓRDENES ====================
def registrar_orden(nombre, importe, precio, ticker):
    saldo_axa = estado_cartera["saldos"].get("AXA Trésor Court Terme C", 0.0)
    if saldo_axa < importe: st.error(f"❌ Saldo insuficiente en AXA ({saldo_axa:,.2f} €)."); return
    f_ord = datetime.now(); f_liq = f_ord + timedelta(days=DIAS_LIQUIDACION_FONDOS)
    estado_cartera["ordenes_pendientes"].append({"id": f"{nombre}_{f_ord.strftime('%H%M%S')}", "fecha_orden": f_ord.isoformat(), "fecha_liq": f_liq.isoformat(), "activo": nombre, "importe": importe, "precio_ord": precio, "ticker": ticker, "estado": "pendiente"})
    guardar_json(F_SALDOS, estado_cartera)
    st.success(f"✅ Orden registrada. Se descontarán {importe:,.0f} € de AXA.")

# ==================== INTERFAZ ====================
with st.sidebar:
    st.header("💼 Mis Saldos Reales")
    with st.expander("⚙️ Actualizar Saldos", expanded=False):
        nuevos_saldos = {}
        for nombre, info in ACTIVOS_RADAR.items():
            val = float(estado_cartera["saldos"].get(nombre, info["saldo_default"]))
            nuevos_saldos[nombre] = st.number_input(f"{nombre}", value=val, step=100.0)
        if st.button("💾 Guardar", use_container_width=True):
            estado_cartera["saldos"] = nuevos_saldos; guardar_json(F_SALDOS, estado_cartera); st.rerun()
    st.metric("Patrimonio Total", f"{sum(estado_cartera['saldos'].values()):,.0f} €")
    st.metric("Pólvora AXA", f"{estado_cartera['saldos'].get('AXA Trésor Court Terme C', 0):,.0f} €")
    st.markdown("---")
    st.markdown("### ⚙️ Modo de Ejecución")
    modo_buffer = st.radio("Buffer de anticipación (T+4):", ["Smart Buffer (recomendado)", "Exacto (sin buffer)", "Anticipado agresivo (25%)"], index=0)

st.title("🦈 Robot Avizor Cava — 4 Velocidades")
v_info = get_vix_data()
st.info(f"**VIX:** {v_info['actual']:.2f} | **Tensión:** {v_info['tension']:+.1%} | **Liquidez AXA:** {estado_cartera['saldos'].get('AXA Trésor Court Terme C', 0):,.0f} € | **Modo:** {modo_buffer}")

t_fondos, t_cortos, t_largo, t_backtest, t_ordenes = st.tabs([
    "🏦 1. Fondos Lentos (T+4)", 
    "⚡ 2. Cortos HOPLA (Consenso Auto)", 
    "🥇 3. Oro y BTC (Largo Plazo)", 
    "🔬 4. Backtest Histórico (Auditoría)",
    "📦 5. Órdenes en Tránsito"
])

# --- PESTAÑA 1: FONDOS ---
with t_fondos:
    st.subheader("Fondos MyInvestor: Traspasos T+4 y Semáforo DCA")
    for nombre, info in FONDOS.items():
        if info.get("es_monetario"): continue
        d = get_market_data(info["ticker"])
        if not d: continue
        o_act = float(estado_cartera["objetivos"].get(nombre, CAPITAL_RADAR_DEFAULT * info["peso_obj"]))
        z_c, est_c, mot_c, d_t, p_t, tz, teur, smult, factor, motivo_buffer = evaluar_fondo(d, info, v_info, o_act, modo_buffer)
        z_v, est_v, mot_v = evaluar_venta_fondo(d, info)
        
        # Obtener datos del semáforo DCA
        dca = evaluar_semaforo_dca(d)
        
        with st.expander(f"{'🟢' if 'COMPRAR' in est_c else '⚪'} **{nombre}** | {est_c} | Venta: {est_v}"):
            
            # 1. Tarjeta DCA (Lo primero que ve el ojo)
            st.markdown(f"""
            <div class="dca-card" style="background-color: {dca['bg']}; border-left-color: {dca['border']};">
                <div class="dca-icon">{dca['icon']}</div>
                <div class="dca-content">
                    <div class="dca-title" style="color: {dca['color']};">{dca['title']}</div>
                    <div class="dca-text">{dca['msg']}</div>
                </div>
                <div class="dca-mult" style="color: {dca['color']};">{dca['mult']}</div>
            </div>
            """, unsafe_allow_html=True)
            
            # 2. Lógica de Compra / Venta
            st.write(mot_c)
            if d["caida"] > info["c1"]:
                st.markdown(f'<div class="aviso-buffer"><b>📊 Gatillos Zona 1:</b> Teórico <b>{d["max52"]*(1+info["c1"]):,.2f}</b> | Aplicado <b>{d["max52"]*(1+info["c1"]*factor):,.2f}</b><br><i>⚠️ {motivo_buffer}</i></div>', unsafe_allow_html=True)
            
            if "COMPRAR" in est_c:
                st.markdown(f'<div class="semaforo-verde">🛒 <b>ORDEN:</b> Traspaso de <b>{teur:,.0f} €</b> desde AXA.</div>', unsafe_allow_html=True)
                if st.button(f"📦 Registrar Traspaso T+{DIAS_LIQUIDACION_FONDOS}", key=f"btn_{nombre}"): registrar_orden(nombre, teur, d["precio"], info["ticker"]); st.rerun()
            
            if z_v >= 2: 
                st.markdown(f'<div class="semaforo-rojo">⚠️ <b>{est_v}:</b> {mot_v}</div>', unsafe_allow_html=True)
            
            # 3. Gráfico
            st.plotly_chart(graficar_activo(d["hist"], nombre), use_container_width=True)

# --- PESTAÑA 2: CORTOS HOPLA ---
with t_cortos:
    st.subheader("Playbook HOPLA: Consenso Automático de Ventanas")
    for nombre, info in CORTOS_HOPLA.items():
        d = get_market_data(info["ticker"])
        if not d: continue
        señal, msg_consenso, resultados_ventanas = detectar_trampa_consenso(d, d["hist"])
        
        st.markdown(f"#### ⚡ {nombre}")
        c1, c2, c3, c4, c5 = st.columns(5)
        c1.metric("Precio", f"{d['precio']:,.2f}")
        c2.metric("RSI", f"{d['rsi']:.1f}")
        c3.metric("MACD Semanal", "🟢 Alcista" if d['macd_alcista'] else "🔴 Bajista")
        c4.metric("Estocástico", f"{d['stoch_k']:.1f}")
        c5.metric("BOS (10d)", "🟢 Roto" if d['bos'] else "🔴 No")
        
        if resultados_ventanas:
            cols_ventanas = st.columns(len(VENTANAS_ZIGZAG))
            for idx, (w, activa) in enumerate(resultados_ventanas.items()):
                with cols_ventanas[idx]:
                    st.metric(f"Ventana {w}", "✅" if activa else "❌")
        
        if señal:
            if "ROBUSTA" in msg_consenso:
                st.markdown(f'<div class="semaforo-rojo"><b>🎯 {señal["señal"]}</b><br>{msg_consenso}<br>{señal["motivo"]}</div>', unsafe_allow_html=True)
                c1.metric("Entrada (Corto)", f"{señal['entrada']:,.2f}")
                c2.metric("Stop Loss", f"{señal['stop_loss']:,.2f}")
                c3.metric("Objetivo", f"{señal['objetivo']:,.2f}")
            elif "DÉBIL" in msg_consenso:
                st.markdown(f'<div class="semaforo-amarillo"><b>⚠️ SEÑAL DÉBIL - PRECAUCIÓN</b><br>{msg_consenso}<br>Mejor esperar a que más ventanas confirmen.</div>', unsafe_allow_html=True)
        else:
            st.info(f"⏳ **Esperando:** {msg_consenso}")
            
        st.plotly_chart(graficar_activo(d["hist"], nombre), use_container_width=True)

# --- PESTAÑA 3: LARGO PLAZO (ORO Y BTC) ---
with t_largo:
    st.subheader("Oro y BTC: Acumulación Spot a Largo Plazo")
    for nombre, info in LARGO_PLAZO.items():
        d = get_market_data(info["ticker"])
        if not d: continue
        o_act = float(estado_cartera["objetivos"].get(nombre, CAPITAL_RADAR_DEFAULT * info["peso_obj"]))
        z_c, est_c, mot_c, d_t, p_t, tz, teur = evaluar_largo_plazo(d, info, v_info, o_act)
        z_v, est_v, mot_v = evaluar_venta_largo_plazo(d, info)
        dca = evaluar_semaforo_dca(d) # También aplicamos DCA aquí
        
        with st.expander(f"{'🟢' if 'COMPRAR' in est_c else '⚪'} **{nombre}** | {est_c} | Venta: {est_v}"):
            
            # Tarjeta DCA
            st.markdown(f"""
            <div class="dca-card" style="background-color: {dca['bg']}; border-left-color: {dca['border']};">
                <div class="dca-icon">{dca['icon']}</div>
                <div class="dca-content">
                    <div class="dca-title" style="color: {dca['color']};">{dca['title']}</div>
                    <div class="dca-text">{dca['msg']}</div>
                </div>
                <div class="dca-mult" style="color: {dca['color']};">{dca['mult']}</div>
            </div>
            """, unsafe_allow_html=True)
            
            c1, c2, c3, c4, c5 = st.columns(5)
            c1.metric("Precio", f"{d['precio']:,.2f}")
            c2.metric("Caída", f"{d['caida']:.2%}")
            c3.metric("RSI", f"{d['rsi']:.1f}")
            c4.metric("MACD", "🟢" if d['macd_alcista'] else "🔴")
            c5.metric("BOS (10d)", "🟢" if d['bos'] else "🔴")
            
            st.write(mot_c)
            if "COMPRAR" in est_c:
                st.markdown(f'<div class="semaforo-verde">🛒 <b>ORDEN:</b> Comprar <b>{teur:,.0f} €</b> en Spot.</div>', unsafe_allow_html=True)
            if z_v >= 2:
                st.markdown(f'<div class="semaforo-rojo">⚠️ <b>{est_v}:</b> {mot_v}</div>', unsafe_allow_html=True)
            st.plotly_chart(graficar_activo(d["hist"], nombre), use_container_width=True)

# --- PESTAÑA 4: BACKTEST ---
with t_backtest:
    st.subheader("🔬 Auditoría Histórica del Algoritmo HOPLA")
    col_bt1, col_bt2 = st.columns(2)
    with col_bt1:
        ticker_bt = st.selectbox("Activo:", ["^GSPC (S&P 500)", "^NDX (Nasdaq)", "GC=F (Oro)", "BTC-USD (Bitcoin)"]).split(" ")[0]
    with col_bt2:
        lookforward_bt = st.slider("Días simulación:", 10, 30, 20)
    
    if st.button("🚀 Ejecutar Auditoría", type="primary"):
        with st.spinner("Ejecutando..."):
            resultados = []
            for w in VENTANAS_ZIGZAG:
                h = yf.Ticker(ticker_bt).history(period="2y")
                if len(h) < 200: continue
                closes, highs, lows = h['Close'].values, h['High'].values, h['Low'].values
                n, start = len(closes), max(200, w * 10)
                signals = []
                for i in range(start, n - lookforward_bt):
                    hist_up_to = h.iloc[:i+1]
                    try:
                        h_w = hist_up_to.resample('W').agg({'High':'max','Low':'min','Close':'last'}).dropna()
                        if len(h_w) < 26: continue
                        macd = h_w['Close'].ewm(span=12).mean() - h_w['Close'].ewm(span=26).mean()
                        sig = macd.ewm(span=9).mean()
                        if not (macd.iloc[-1] > sig.iloc[-1]): continue
                    except: continue
                    
                    sig_data, _ = detectar_trampa_techo_falso_single(hist_up_to, w)
                    if not sig_data: continue
                    
                    entry, stop, target = sig_data['entrada'], sig_data['stop_loss'], sig_data['objetivo']
                    res = None
                    for j in range(i+1, min(i+lookforward_bt, n)):
                        if highs[j] >= stop: res = -1.0; break
                        if lows[j] <= target: res = (entry - target) / entry; break
                    if res is None: res = (entry - closes[min(i+lookforward_bt, n-1)]) / entry
                    signals.append(res*100)
                
                if signals:
                    wins = sum(1 for s in signals if s > 0)
                    resultados.append({"window": w, "n": len(signals), "win_rate": wins/len(signals)*100, "avg": np.mean(signals)})
            
            if resultados:
                st.dataframe(pd.DataFrame(resultados), use_container_width=True, hide_index=True)
                fig = go.Figure(go.Bar(x=[r["window"] for r in resultados], y=[r["win_rate"] for r in resultados], marker_color="#3b82f6"))
                fig.update_layout(title="Win Rate Histórico por Ventana", template="plotly_dark", height=300)
                st.plotly_chart(fig, use_container_width=True)

# --- PESTAÑA 5: ÓRDENES ---
with t_ordenes:
    st.subheader("📦 Órdenes de Traspaso en Tránsito (T+4)")
    pend = [o for o in estado_cartera.get("ordenes_pendientes", []) if o["estado"] == "pendiente"]
    if not pend: st.info("Ninguna orden de traspaso en tránsito.")
    for o in pend:
        d_liq = datetime.fromisoformat(o["fecha_liq"])
        d_merc = get_market_data(o["ticker"])
        p_act = d_merc["precio"] if d_merc else o["precio_ord"]
        pnl = (p_act / o["precio_ord"] - 1) * 100
        st.markdown(f"""<div class="card-orden"><b>{o['activo']}</b> | Importe: {o['importe']:,.0f} €<br>Liquidación estimada: <b>{d_liq.strftime('%d/%m')}</b><br>P&L Estimado: <b>{pnl:+.2f}%</b></div>""", unsafe_allow_html=True)
        if st.button(f"✅ Marcar como liquidada", key=f"liq_{o['id']}"):
            o["estado"] = "liquidada"; estado_cartera["saldos"][o["activo"]] = estado_cartera["saldos"].get(o["activo"], 0) + o["importe"]
            estado_cartera["saldos"]["AXA Trésor Court Terme C"] -= o["importe"]; guardar_json(F_SALDOS, estado_cartera); st.rerun()
