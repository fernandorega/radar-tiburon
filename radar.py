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
st.set_page_config(page_title="🦈 Robot Avizor Cava — Gestor Pro", page_icon="🦈", layout="wide")
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
    
    .dca-card { display: flex; align-items: center; padding: 16px; border-radius: 12px; margin-top: 15px; margin-bottom: 15px; border-left: 8px solid; box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1); }
    .dca-icon { font-size: 2.5rem; margin-right: 20px; }
    .dca-content { flex-grow: 1; }
    .dca-title { font-weight: 800; font-size: 1.15rem; margin-bottom: 4px; letter-spacing: 0.5px; }
    .dca-text { font-size: 0.95rem; opacity: 0.9; line-height: 1.4; }
    .dca-mult { font-size: 1.5rem; font-weight: 900; margin-left: 20px; padding: 8px 16px; border-radius: 8px; background: rgba(0,0,0,0.3); }

    /* PANEL DE INDICADORES */
    .indicator-panel { display: flex; justify-content: space-between; background-color: #1e1e24; padding: 10px; border-radius: 8px; margin-bottom: 15px; border: 1px solid #3f3f46; }
    .indicator-box { text-align: center; flex: 1; border-right: 1px solid #3f3f46; }
    .indicator-box:last-child { border-right: none; }
    .ind-title { font-size: 0.75rem; color: #a1a1aa; text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 5px; }
    .ind-value { font-size: 1.1rem; font-weight: 700; }
    .ind-desc { font-size: 0.7rem; color: #71717a; margin-top: 2px; }
    
    .aviso-mercado { background-color: #1e1e24; border: 1px solid #3f3f46; padding: 8px 12px; border-radius: 8px; font-size: 0.85rem; color: #d4d4d8; margin-bottom: 10px; }
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
    "AXA Trésor Court Terme C": {"ticker": "^IRX", "es_monetario": True, "isin": ISIN_MONETARIO_NODRIZA, "hora_corte": 10, "peso_obj": 0.25, "saldo_default": 15000.0, "c1": -0.01, "c2": -0.02, "c3": -0.03},
    "Fidelity S&P 500 Index P": {"ticker": "^GSPC", "es_monetario": False, "isin": "IE00BYX5MX67", "hora_corte": 16, "peso_obj": 0.25, "saldo_default": 15000.0, "c1": -0.04, "c2": -0.10, "c3": -0.20},
    "Fidelity MSCI World Index P": {"ticker": "URTH", "es_monetario": False, "isin": "IE00BYX5NX33", "hora_corte": 16, "peso_obj": 0.10, "saldo_default": 6000.0, "c1": -0.04, "c2": -0.10, "c3": -0.18},
    "MyInvestor Nasdaq 100 FI": {"ticker": "^NDX", "es_monetario": False, "isin": "ES0165265002", "hora_corte": 12, "peso_obj": 0.10, "saldo_default": 6000.0, "c1": -0.06, "c2": -0.15, "c3": -0.25},
    "iShares Europe Equity Index A2": {"ticker": "VGK", "es_monetario": False, "isin": "LU0836512706", "hora_corte": 10, "peso_obj": 0.03, "saldo_default": 1800.0, "c1": -0.04, "c2": -0.09, "c3": -0.16},
    "Wellington Global Health Care D": {"ticker": "XLV", "es_monetario": False, "isin": "IE00BF2ZVB54", "hora_corte": 12, "peso_obj": 0.03, "saldo_default": 1800.0, "c1": -0.04, "c2": -0.09, "c3": -0.16},
    "Guinness Global Energy D EUR": {"ticker": "XLE", "es_monetario": False, "isin": "IE00B3CCJB88", "hora_corte": 14, "peso_obj": 0.02, "saldo_default": 1200.0, "c1": -0.06, "c2": -0.14, "c3": -0.24},
    "Vanguard Global Bond Hedged": {"ticker": "BND", "es_monetario": False, "isin": "IE00B18GC888", "hora_corte": 12, "peso_obj": 0.01, "saldo_default": 600.0, "c1": -0.03, "c2": -0.06, "c3": -0.10},
    "Pictet - Nutrition P EUR": {"ticker": "XLP", "es_monetario": False, "isin": "LU0366534344", "hora_corte": 12, "peso_obj": 0.01, "saldo_default": 600.0, "c1": -0.04, "c2": -0.09, "c3": -0.16}
}
CORTOS_HOPLA = {"S&P 500 (Corto)": {"ticker": "^GSPC"}, "Nasdaq 100 (Corto)": {"ticker": "^NDX"}, "Oro (Corto)": {"ticker": "GC=F"}}
LARGO_PLAZO = {
    "Oro Físico (Largo)": {"ticker": "GC=F", "isin": "IE00B4ND3602", "peso_obj": 0.15, "saldo_default": 9000.0, "c1": -0.05, "c2": -0.10, "c3": -0.18},
    "Bitcoin (Largo)": {"ticker": "BTC-USD", "isin": "BTC-USD", "peso_obj": 0.05, "saldo_default": 3000.0, "c1": -0.15, "c2": -0.30, "c3": -0.50}
}
ACTIVOS_RADAR = {**FONDOS, **LARGO_PLAZO}

default_state = {"colchon_emergencias": COLCHON_EMERGENCIAS_DEFAULT, "cuenta_my": 0.0, "cuenta_trade": 0.0, "saldos": {k: v["saldo_default"] for k, v in ACTIVOS_RADAR.items()}, "objetivos": {k: CAPITAL_RADAR_DEFAULT * v["peso_obj"] for k, v in ACTIVOS_RADAR.items()}, "ordenes_pendientes": [], "historial_compras": []}
estado_cartera = cargar_json(F_SALDOS, default_state)
for k, v in ACTIVOS_RADAR.items():
    if k not in estado_cartera["saldos"]: estado_cartera["saldos"][k] = v["saldo_default"]
    if k not in estado_cartera["objetivos"]: estado_cartera["objetivos"][k] = CAPITAL_RADAR_DEFAULT * v["peso_obj"]

# ==================== UTILIDAD MERCADO ====================
def es_fin_de_semana(): return datetime.now().weekday() >= 5

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
        
        # RSI
        delta = h52['Close'].diff()
        g = delta.clip(lower=0).ewm(alpha=1/14, adjust=False).mean()
        l = -delta.clip(upper=0).ewm(alpha=1/14, adjust=False).mean()
        rsi = float((100 - 100/(1 + g/l.replace(0, 1e-9))).iloc[-1])
        
        # MACD Semanal
        h_w = h.resample('W').agg({'High':'max','Low':'min','Close':'last'}).dropna()
        macd = h_w['Close'].ewm(span=12).mean() - h_w['Close'].ewm(span=26).mean()
        sig = macd.ewm(span=9).mean()
        macd_alcista = bool(macd.iloc[-1] > sig.iloc[-1])
        
        # Estocástico Semanal
        l14 = h_w['Low'].rolling(14).min(); h14 = h_w['High'].rolling(14).max()
        k = 100 * ((h_w['Close'] - l14) / (h14 - l14).replace(0, 1e-9))
        stoch_k, stoch_d = float(k.iloc[-1]), float(k.rolling(3).mean().iloc[-1])
        
        # La Bonita
        la_bonita = bool(macd_alcista and (stoch_k < 40 and stoch_k > stoch_d))
        
        # BOS (Break of Structure) - Máximo de los últimos 10 días
        max_10d = float(h52['High'].shift(1).rolling(10).max().iloc[-1])
        bos = bool(p > max_10d) if not pd.isna(max_10d) else False
        
        return {"precio": p, "max52": mx, "caida": (p/mx - 1.0) if mx > 0 else 0.0, "dist_sma": (p/sma200 - 1.0) if sma200 > 0 else 0.0, "rsi": rsi, "macd_alcista": macd_alcista, "stoch_k": stoch_k, "la_bonita": la_bonita, "bos": bos, "hist": h}
    except: return None

# ==================== GRÁFICAS ====================
def graficar_activo(hist, nombre):
    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.05, row_heights=[0.7, 0.3], subplot_titles=(f"Precio - {nombre}", "RSI (14)"))
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
    fig.update_layout(height=400, template="plotly_dark", margin=dict(l=10, r=10, t=30, b=10), showlegend=False)
    return fig

# ==================== RENDERIZADOR DE INDICADORES ====================
def render_indicadores(d):
    # Estocástico
    if d['stoch_k'] > 80: stoch_color = "#f87171"; stoch_txt = f"Sobrecarga ({d['stoch_k']:.0f})"
    elif d['stoch_k'] < 20: stoch_color = "#4ade80"; stoch_txt = f"Sobreventa ({d['stoch_k']:.0f})"
    else: stoch_color = "#facc15"; stoch_txt = f"Neutro ({d['stoch_k']:.0f})"
        
    # La Bonita
    bonita_color = "#4ade80" if d['la_bonita'] else "#71717a"
    bonita_txt = "¡ACTIVA!" if d['la_bonita'] else "Inactiva"
    
    # BOS
    bos_color = "#4ade80" if d['bos'] else "#71717a"
    bos_txt = "Roto 🟢" if d['bos'] else "No roto 🔴"
    
    st.markdown(f"""
    <div class="indicator-panel">
        <div class="indicator-box">
            <div class="ind-title">Estocástico (14w)</div>
            <div class="ind-value" style="color: {stoch_color};">{stoch_txt}</div>
            <div class="ind-desc">Termómetro de ímpetu</div>
        </div>
        <div class="indicator-box">
            <div class="ind-title">Pauta Bonita</div>
            <div class="ind-value" style="color: {bonita_color};">{bonita_txt}</div>
            <div class="ind-desc">MACD + Estocástico</div>
        </div>
        <div class="indicator-box">
            <div class="ind-title">BOS (10d)</div>
            <div class="ind-value" style="color: {bos_color};">{bos_txt}</div>
            <div class="ind-desc">Ruptura de estructura</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

# ==================== LÓGICA DCA Y EVALUACIÓN ====================
def evaluar_semaforo_dca(d):
    if d['stoch_k'] > 80: return {"bg": "#371515", "border": "#ef4444", "icon": "🛑", "title": "APORTACIÓN MÍNIMA (Sobrecarga)", "msg": "Estocástico en sobrecompra. Prohibido añadir extra.", "mult": "0.5x", "color": "#f87171"}
    elif d['la_bonita']: return {"bg": "#143320", "border": "#22c55e", "icon": "🚀", "title": "APORTACIÓN EXTRA (Pauta Bonita)", "msg": "¡Momento estadístico óptimo! Inyecta más capital.", "mult": "1.5x", "color": "#4ade80"}
    elif d['macd_alcista']: return {"bg": "#332b14", "border": "#eab308", "icon": "✅", "title": "APORTACIÓN NORMAL", "msg": "Tendencia sana. Mantén tu ritmo DCA.", "mult": "1.0x", "color": "#facc15"}
    else: return {"bg": "#2d1b12", "border": "#f97316", "icon": "⚠️", "title": "APORTACIÓN MÍNIMA (Prudencia)", "msg": "Mercado débil. Mantén la pólvora seca.", "mult": "0.5x", "color": "#fb923c"}

def calcular_factor_buffer(d, modo_buffer):
    if modo_buffer == "Exacto (sin buffer)": return 1.0
    if modo_buffer == "Anticipado agresivo (25%)": return 0.75
    if d['rsi'] < 30 or d['la_bonita'] or d['dist_sma'] < -0.15: return 1.0
    if d['dist_sma'] < 0 and not d['macd_alcista']: return 0.85
    return 1.0

def evaluar_fondo(d, info, modo_buffer):
    if info.get("es_monetario"): return "BÚNKER"
    caida = d["caida"]; factor = calcular_factor_buffer(d, modo_buffer)
    if d['la_bonita']: factor *= BONUS_BONITA
    if caida <= info["c3"]*factor: return "COMPRAR ZONA 3"
    if caida <= info["c2"]*factor: return "COMPRAR ZONA 2"
    if caida <= info["c1"]*factor: return "COMPRAR ZONA 1"
    return "ESPERAR"

def evaluar_largo_plazo(d, info, v_info):
    caida = d["caida"]
    if abs(caida) >= 0.25 and v_info["actual"] < 20.0: return "BLOQUEADO VIX"
    if caida <= info["c3"]: return "COMPRAR ZONA 3"
    if caida <= info["c2"]: return "COMPRAR ZONA 2"
    if caida <= info["c1"]: return "COMPRAR ZONA 1"
    return "ESPERAR"

# ==================== LÓGICA HOPLA ====================
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
    if len(swings) < 5: return None
    maximos = [s for s in swings if s[0] == "max"]
    if len(maximos) < 2: return None
    max1, max2 = maximos[-2], maximos[-1]
    if not (0.985 <= max2[2] / max1[2] <= 1.015): return None
    min_entre = [s for s in swings if s[0] == "min" and max1[1] < s[1] < max2[1]]
    if not min_entre: return None
    valle = min_entre[-1]
    if cierres[-1] >= valle[2]: return None
    swing_post = [s for s in swings if s[1] > valle[1]]
    onda_b = next((s for s in swing_post if s[0] == "max" and s[2] < max2[2]), None) if swing_post else None
    if not onda_b: return None
    stop_loss = max(max1[2], max2[2]) * 1.01
    return {"entrada": cierres[-1], "stop_loss": stop_loss, "objetivo": valle[2] * 0.95, "motivo": f"Trampa confirmada."}

def detectar_trampa_consenso(d, hist):
    if not d.get('macd_alcista', False): return None, "MACD bajista.", {}
    resultados = {w: detectar_trampa_techo_falso_single(hist, w) is not None for w in VENTANAS_ZIGZAG}
    activas = [w for w, act in resultados.items() if act]
    if len(activas) >= 3: return detectar_trampa_techo_falso_single(hist, activas[0]), f"ROBUSTA ({len(activas)}/5)", resultados
    elif len(activas) > 0: return detectar_trampa_techo_falso_single(hist, activas[0]), f"DÉBIL ({len(activas)}/5)", resultados
    return None, "Sin señal.", resultados

# ==================== LEDGER Y REGISTROS ====================
def registrar_orden(nombre, importe, precio, ticker):
    saldo_axa = estado_cartera["saldos"].get("AXA Trésor Court Terme C", 0.0)
    if saldo_axa < importe: st.error(f"❌ Saldo insuficiente en AXA ({saldo_axa:,.2f} €)."); return
    f_ord = datetime.now(); f_liq = f_ord + timedelta(days=DIAS_LIQUIDACION_FONDOS)
    estado_cartera["ordenes_pendientes"].append({"id": f"{nombre}_{f_ord.strftime('%H%M%S')}", "fecha_orden": f_ord.isoformat(), "fecha_liq": f_liq.isoformat(), "activo": nombre, "importe": importe, "precio_ord": precio, "ticker": ticker, "estado": "pendiente"})
    guardar_json(F_SALDOS, estado_cartera)
    st.success(f"✅ Orden registrada.")

def liquidar_orden(id_orden):
    for o in estado_cartera["ordenes_pendientes"]:
        if o["id"] == id_orden and o["estado"] == "pendiente":
            o["estado"] = "liquidada"
            estado_cartera["saldos"][o["activo"]] = estado_cartera["saldos"].get(o["activo"], 0) + o["importe"]
            estado_cartera["saldos"]["AXA Trésor Court Terme C"] -= o["importe"]
            estado_cartera["historial_compras"].append({"activo": o["activo"], "fecha": datetime.now().isoformat(), "importe": o["importe"], "precio": o["precio_ord"]})
            guardar_json(F_SALDOS, estado_cartera)
            st.rerun()

# ==================== INTERFAZ PRINCIPAL ====================
with st.sidebar:
    st.header("💼 Mi Patrimonio Real")
    with st.expander("💵 Cuentas y Efectivo", expanded=True):
        colchon = st.number_input("🛡️ Colchón (Trade)", value=float(estado_cartera.get("colchon_emergencias", 10000.0)), step=500.0)
        c_my = st.number_input("🟢 Cuenta MY (2%)", value=float(estado_cartera.get("cuenta_my", 0.0)), step=500.0)
        c_tr = st.number_input("🔵 Cuenta Trade (3%)", value=float(estado_cartera.get("cuenta_trade", 0.0)), step=500.0)
        if st.button("💾 Guardar Efectivo", use_container_width=True):
            estado_cartera["colchon_emergencias"] = colchon; estado_cartera["cuenta_my"] = c_my; estado_cartera["cuenta_trade"] = c_tr
            guardar_json(F_SALDOS, estado_cartera); st.rerun()
            
    with st.expander("📈 Saldos Invertidos", expanded=False):
        nuevos_saldos = {}
        for nombre, info in ACTIVOS_RADAR.items():
            val = float(estado_cartera["saldos"].get(nombre, info["saldo_default"]))
            nuevos_saldos[nombre] = st.number_input(f"{nombre}", value=val, step=100.0)
        if st.button("💾 Guardar Inversiones", use_container_width=True):
            estado_cartera["saldos"] = nuevos_saldos; guardar_json(F_SALDOS, estado_cartera); st.rerun()
            
    st.markdown("---")
    st.markdown("### ⚙️ Modo de Ejecución")
    modo_buffer = st.radio("Buffer de anticipación (T+4):", ["Smart Buffer (recomendado)", "Exacto (sin buffer)", "Anticipado agresivo (25%)"], index=0)

total_invertido = sum(estado_cartera["saldos"].get(k, 0) for k in ACTIVOS_RADAR.keys())
total_efectivo = estado_cartera.get("colchon_emergencias", 0) + estado_cartera.get("cuenta_my", 0) + estado_cartera.get("cuenta_trade", 0)
patrimonio_total = total_invertido + total_efectivo

st.title("🦈 Robot Avizor Cava — Gestor Pro de Patrimonio")
v_info = get_vix_data()
st.info(f"**VIX:** {v_info['actual']:.2f} | **Tensión:** {v_info['tension']:+.1%} | **Patrimonio Total:** {patrimonio_total:,.0f} € | **Liquidez AXA:** {estado_cartera['saldos'].get('AXA Trésor Court Terme C', 0):,.0f} €")

if es_fin_de_semana():
    st.warning("📅 **Fin de semana:** Los mercados tradicionales (Fondos, S&P, Nasdaq, Oro) están cerrados. Los precios mostrados son el cierre del viernes. Los indicadores (BOS, RSI, MACD) no cambiarán hasta el lunes. **Solo Bitcoin cotiza 24/7.**")

t_cartera, t_fondos, t_cortos, t_largo, t_ordenes = st.tabs([
    "📊 Mi Cartera Global", 
    "🏦 1. Fondos Lentos (T+4)", 
    "⚡ 2. Cortos HOPLA", 
    "🥇 3. Oro y BTC", 
    "📦 4. Órdenes en Tránsito"
])

# --- PESTAÑA 0: CARTERA GLOBAL ---
with t_cartera:
    st.subheader("📊 Dashboard Consolidado de tu Riqueza")
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Patrimonio Total", f"{patrimonio_total:,.0f} €")
    m2.metric("Total Invertido", f"{total_invertido:,.0f} €")
    m3.metric("Total Efectivo", f"{total_efectivo:,.0f} €")
    
    pnl_global_eur = 0.0
    historial = estado_cartera.get("historial_compras", [])
    filas_rentabilidad = []
    
    for nombre, info in ACTIVOS_RADAR.items():
        if info.get("es_monetario"): continue
        d = get_market_data(info["ticker"])
        if not d: continue
        compras_act = [c for c in historial if c["activo"] == nombre]
        if compras_act:
            cap_invertido = sum(c["importe"] for c in compras_act)
            participaciones = sum(c["importe"] / c["precio"] for c in compras_act)
            precio_medio_compra = cap_invertido / participaciones if participaciones > 0 else 0
            valor_actual = participaciones * d["precio"]
            pnl_eur = valor_actual - cap_invertido
            pnl_pct = (pnl_eur / cap_invertido) * 100 if cap_invertido > 0 else 0
            pnl_global_eur += pnl_eur
            filas_rentabilidad.append({"Activo": nombre, "Capital Invertido": cap_invertido, "Valor Actual": valor_actual, "P&L (€)": pnl_eur, "P&L (%)": pnl_pct, "Precio Medio Compra": precio_medio_compra, "Precio Actual": d["precio"]})
        else:
            saldo_actual = estado_cartera["saldos"].get(nombre, 0)
            if saldo_actual > 0:
                filas_rentabilidad.append({"Activo": nombre, "Capital Invertido": saldo_actual, "Valor Actual": saldo_actual, "P&L (€)": 0.0, "P&L (%)": 0.0, "Precio Medio Compra": d["precio"], "Precio Actual": d["precio"]})
                
    m4.metric("P&L Global (Market)", f"{pnl_global_eur:+,.0f} €", delta_color="normal")
    
    col_g1, col_g2 = st.columns([1, 1])
    with col_g1:
        st.markdown("#### 🍩 Distribución del Patrimonio")
        fig_pie = go.Figure(data=[go.Pie(
            labels=["Fondos Indexados", "Oro/BTC", "Cuentas Efectivo"],
            values=[total_invertido - sum(estado_cartera["saldos"].get(k, 0) for k in LARGO_PLAZO.keys()), sum(estado_cartera["saldos"].get(k, 0) for k in LARGO_PLAZO.keys()), total_efectivo],
            hole=.4, marker_colors=["#3b82f6", "#f59e0b", "#10b981"]
        )])
        fig_pie.update_layout(template="plotly_dark", height=300, margin=dict(l=10, r=10, t=10, b=10))
        st.plotly_chart(fig_pie, use_container_width=True)
        
    with col_g2:
        st.markdown("#### 💰 Ganancia / Pérdida por Activo (€)")
        if filas_rentabilidad:
            df_pnl = pd.DataFrame(filas_rentabilidad)
            df_pnl = df_pnl[df_pnl["Capital Invertido"] > 0]
            fig_bar = go.Figure(go.Bar(x=df_pnl["P&L (€)"], y=df_pnl["Activo"], orientation='h', marker_color=np.where(df_pnl["P&L (€)"] > 0, '#22c55e', '#ef4444')))
            fig_bar.update_layout(template="plotly_dark", height=300, margin=dict(l=10, r=10, t=10, b=10))
            st.plotly_chart(fig_bar, use_container_width=True)
            
    st.markdown("#### 📋 Detalle de Rendimiento Real (PMC)")
    if filas_rentabilidad:
        st.dataframe(pd.DataFrame(filas_rentabilidad).style.format({"Capital Invertido": "{:,.2f} €", "Valor Actual": "{:,.2f} €", "P&L (€)": "{:+,.2f} €", "P&L (%)": "{:+.2f}%", "Precio Medio Compra": "{:,.2f}", "Precio Actual": "{:,.2f}"}), use_container_width=True, hide_index=True)

# --- PESTAÑA 1: FONDOS ---
with t_fondos:
    st.subheader("Fondos MyInvestor: Traspasos T+4")
    for nombre, info in FONDOS.items():
        if info.get("es_monetario"): continue
        d = get_market_data(info["ticker"])
        if not d: continue
        o_act = float(estado_cartera["objetivos"].get(nombre, CAPITAL_RADAR_DEFAULT * info["peso_obj"]))
        est_c = evaluar_fondo(d, info, modo_buffer)
        dca = evaluar_semaforo_dca(d)
        
        with st.expander(f"{'🟢' if 'COMPRAR' in est_c else '⚪'} **{nombre}** | {est_c}"):
            # PANEL DE INDICADORES
            render_indicadores(d)
            
            # TARJETA DCA
            st.markdown(f"""
            <div class="dca-card" style="background-color: {dca['bg']}; border-left-color: {dca['border']};">
                <div class="dca-icon">{dca['icon']}</div>
                <div class="dca-content"><div class="dca-title" style="color: {dca['color']};">{dca['title']}</div><div class="dca-text">{dca['msg']}</div></div>
                <div class="dca-mult" style="color: {dca['color']};">{dca['mult']}</div>
            </div>
            """, unsafe_allow_html=True)
            
            c1, c2, c3 = st.columns(3)
            c1.metric("Caída (ATH)", f"{d['caida']:.2%}")
            c2.metric("Gatillo Teórico (Z1)", f"{d['max52']*(1+info['c1']):,.2f}")
            c3.metric("Gatillo con Buffer", f"{d['max52']*(1+info['c1']*calcular_factor_buffer(d, modo_buffer)):,.2f}")
            
            if "COMPRAR" in est_c:
                teur = max(o_act, 1000)*0.3
                if st.button(f"📦 Registrar Traspaso de {teur:,.0f} €", key=f"btn_{nombre}"): 
                    registrar_orden(nombre, teur, d["precio"], info["ticker"]); st.rerun()
            st.plotly_chart(graficar_activo(d["hist"], nombre), use_container_width=True)

# --- PESTAÑA 2: CORTOS HOPLA ---
with t_cortos:
    st.subheader("Playbook HOPLA: Consenso Automático")
    for nombre, info in CORTOS_HOPLA.items():
        d = get_market_data(info["ticker"])
        if not d: continue
        señal, msg, ventanas = detectar_trampa_consenso(d, d["hist"])
        
        st.markdown(f"#### ⚡ {nombre}")
        render_indicadores(d) # Mostramos el panel aquí también
        
        if ventanas:
            v_cols = st.columns(len(ventanas))
            for i, (w, act) in enumerate(ventanas.items()): v_cols[i].metric(f"Ventana {w}", "✅" if act else "❌")
            
        if señal and "ROBUSTA" in msg:
            st.markdown(f'<div class="semaforo-rojo"><b>🎯 CORTO ACTIVO</b><br>{msg}<br>Entrada: {señal["entrada"]:.2f} | Stop: {señal["stop_loss"]:.2f}</div>', unsafe_allow_html=True)
        elif señal and "DÉBIL" in msg:
            st.markdown(f'<div class="semaforo-amarillo"><b>⚠️ SEÑAL DÉBIL</b><br>{msg}</div>', unsafe_allow_html=True)
        else:
            st.info(f"⏳ Esperando: {msg}")
        st.plotly_chart(graficar_activo(d["hist"], nombre), use_container_width=True)

# --- PESTAÑA 3: ORO Y BTC ---
with t_largo:
    st.subheader("Oro y BTC: Acumulación Spot")
    for nombre, info in LARGO_PLAZO.items():
        d = get_market_data(info["ticker"])
        if not d: continue
        o_act = float(estado_cartera["objetivos"].get(nombre, CAPITAL_RADAR_DEFAULT * info["peso_obj"]))
        
        est_c = evaluar_largo_plazo(d, info, v_info)
        dca = evaluar_semaforo_dca(d)
        
        with st.expander(f"{'🟢' if 'COMPRAR' in est_c else '🔴' if 'BLOQUEADO' in est_c else '⚪'} **{nombre}** | {est_c}"):
            # PANEL DE INDICADORES
            render_indicadores(d)
            
            # TARJETA DCA
            st.markdown(f"""
            <div class="dca-card" style="background-color: {dca['bg']}; border-left-color: {dca['border']};">
                <div class="dca-icon">{dca['icon']}</div>
                <div class="dca-content"><div class="dca-title" style="color: {dca['color']};">{dca['title']}</div><div class="dca-text">{dca['msg']}</div></div>
                <div class="dca-mult" style="color: {dca['color']};">{dca['mult']}</div>
            </div>
            """, unsafe_allow_html=True)
            
            c1, c2, c3 = st.columns(3)
            c1.metric("Caída (ATH)", f"{d['caida']:.2%}")
            c2.metric("Próximo Gatillo", f"{d['max52']*(1+info['c1']):,.2f}")
            c3.metric("RSI", f"{d['rsi']:.1f}")
            
            if "BLOQUEADO VIX" in est_c:
                st.error(f"🛡️ **BLOQUEADO POR PÁNICO:** Caída del {d['caida']:.1%} pero VIX en {v_info['actual']:.1f} (por debajo de 20). El mercado no tiene pánico institucional. Cava dice: NO COMPRES AÚN.")
            elif "COMPRAR" in est_c:
                teur = max(o_act, 1000)*0.3
                if st.button(f"🛒 Registrar Compra de {teur:,.0f} €", key=f"btn_{nombre}"): 
                    registrar_orden(nombre, teur, d["precio"], info["ticker"]); st.rerun()
                    
            if "BTC" in info["ticker"]:
                st.markdown('<div class="aviso-mercado">₿ <b>Bitcoin cotiza 24/7.</b> Los indicadores pueden cambiar durante el fin de semana.</div>', unsafe_allow_html=True)
            else:
                st.markdown('<div class="aviso-mercado">🥇 <b>Oro cerrado en fin de semana.</b> El precio mostrado es el cierre del viernes.</div>', unsafe_allow_html=True)
                    
            st.plotly_chart(graficar_activo(d["hist"], nombre), use_container_width=True)

# --- PESTAÑA 4: ÓRDENES ---
with t_ordenes:
    st.subheader("📦 Órdenes de Traspaso en Tránsito")
    pend = [o for o in estado_cartera.get("ordenes_pendientes", []) if o["estado"] == "pendiente"]
    if not pend: st.info("Ninguna orden en tránsito.")
    for o in pend:
        d_liq = datetime.fromisoformat(o["fecha_liq"])
        d_merc = get_market_data(o["ticker"])
        p_act = d_merc["precio"] if d_merc else o["precio_ord"]
        pnl = (p_act / o["precio_ord"] - 1) * 100
        st.markdown(f"""<div class="card-orden"><b>{o['activo']}</b> | Importe: {o['importe']:,.0f} €<br>Liquidación: <b>{d_liq.strftime('%d/%m')}</b><br>P&L Estimado: <b>{pnl:+.2f}%</b></div>""", unsafe_allow_html=True)
        if st.button(f"✅ Marcar como Liquidada (Registrar PMC)", key=f"liq_{o['id']}"):
            liquidar_orden(o["id"])
