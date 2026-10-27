import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import json
import os
from datetime import datetime
import plotly.graph_objects as go

# ==================== CONFIGURACIÓN DE PÁGINA ====================
st.set_page_config(
    page_title="🦈 Radar Tiburón Cava Pro (60.000 €)",
    page_icon="🦈",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Estilos CSS de alto contraste y legibilidad institucional
st.markdown("""
<style>
    .stAlert { border-radius: 8px; font-weight: 500; }
    div[data-testid="stMetricValue"] { font-size: 1.45rem; font-weight: 700; }
    .stProgress > div > div > div > div { background-color: #3b82f6; }
</style>
""", unsafe_allow_html=True)

# ==================== RUTAS Y PERSISTENCIA ====================
BASE_DIR = os.path.dirname(os.path.abspath(__file__)) if "__file__" in locals() else "."
F_ALERTAS = os.path.join(BASE_DIR, "config_alertas_cava.json")

def cargar_json(p, d):
    if os.path.exists(p):
        try:
            with open(p, "r", encoding="utf-8") as f: return json.load(f)
        except: return d
    return d

def guardar_json(p, d):
    try:
        with open(p, "w", encoding="utf-8") as f: json.dump(d, f, indent=4, ensure_ascii=False)
    except: pass

config_alertas = cargar_json(F_ALERTAS, {
    "email_activo": False, "email_remitente": "", "email_password_app": "",
    "email_destino": "", "telegram_activo": False, "telegram_bot_token": "",
    "telegram_chat_id": "", "ultimas_alertas": {}
})

# ==================== CARTERA CAVA PATRIMONIAL (60.000 € + 10.000 € RESERVA) ====================
CAPITAL_RADAR = 60000
COLCHON_EMERGENCIAS = 10000

ASIGNACION = {
    "S&P 500 (Core)": {
        "ticker": "^GSPC", "peso": 0.40, "vehiculo": "Fondo Indexado Fidelity (IE00BYX5MX10)",
        "plataforma": "MyInvestor", "es_fondo": True,
        "c1": -0.04, "c2": -0.10, "c3": -0.20,
        "v1": 0.15, "v2": 0.25, "v3": 0.35, "rsi_v1": 70, "rsi_v2": 75, "rsi_v3": 80
    },
    "Nasdaq 100 (Satélite)": {
        "ticker": "^NDX", "peso": 0.15, "vehiculo": "Fondo MyInvestor Nasdaq 100 (ES0165265002)",
        "plataforma": "MyInvestor", "es_fondo": True,
        "c1": -0.06, "c2": -0.15, "c3": -0.25,
        "v1": 0.18, "v2": 0.30, "v3": 0.45, "rsi_v1": 70, "rsi_v2": 75, "rsi_v3": 80
    },
    "Oro Físico (Refugio)": {
        "ticker": "GC=F", "peso": 0.15, "vehiculo": "ETC iShares Physical Gold (IE00B4ND3602) / Monedas",
        "plataforma": "MyInvestor / Físico", "es_fondo": False,
        "c1": -0.05, "c2": -0.10, "c3": -0.18,
        "v1": 0.15, "v2": 0.25, "v3": 0.35, "rsi_v1": 70, "rsi_v2": 75, "rsi_v3": 80
    },
    "Bitcoin (Asimetría)": {
        "ticker": "BTC-USD", "peso": 0.05, "vehiculo": "Spot Cripto 24/7",
        "plataforma": "Trade Republic", "es_fondo": False,
        "c1": -0.15, "c2": -0.30, "c3": -0.50,
        "v1": 0.35, "v2": 0.65, "v3": 1.00, "rsi_v1": 75, "rsi_v2": 80, "rsi_v3": 85
    }
}
LIQUIDEZ_MONETARIO_PESO = 0.25 # 15.000 € en Fondo Monetario Puente

# ==================== MACRO Y ESTACIONALIDAD (DOCTRINA CAVA) ====================
def get_ciclo_presidencial():
    year = datetime.now().year
    ciclo = (year - 2024) % 4
    if ciclo == 0: return "Año de Elecciones (Históricamente Alcista)"
    elif ciclo == 1: return "Año Post-Elecciones (Transición y consolidación)"
    elif ciclo == 2: return "Año de Midterms (Suelos en Octubre - Ocasión Cava)"
    else: return "Año Pre-Electoral (¡El año más potente! Regala dinero)"

def get_estacionalidad():
    m = datetime.now().month
    if m == 10: return "Octubre: El mes de los grandes suelos históricos."
    elif m in [11, 12, 1]: return "Nov-Ene: Rally de fin de año. Fuerte viento de cola alcista."
    elif m in [2, 3, 4]: return "Feb-Abr: Tendencia madura previa al verano."
    else: return "Mayo-Sept: 'Sell in May'. Pautas planas y tomas de beneficios."

@st.cache_data(ttl=60)
def get_vix_data():
    try:
        h = yf.Ticker("^VIX").history(period="1mo")
        v_act = float(h['Close'].iloc[-1])
        sma10 = float(h['Close'].tail(10).mean())
        tension = (v_act / sma10) - 1.0
        return {"actual": v_act, "sma10": sma10, "tension": tension}
    except:
        return {"actual": 18.0, "sma10": 18.0, "tension": 0.0}

@st.cache_data(ttl=300)
def get_market_data(ticker):
    try:
        is_crypto = "BTC" in ticker or "ETH" in ticker
        h = yf.Ticker(ticker).history(period="2y")
        if len(h) < 200: return None
        
        lb = 365 if is_crypto else 252
        h52 = h.iloc[-lb:].copy() if len(h) >= lb else h.copy()
        
        p = float(h52['Close'].iloc[-1])
        mx = float(h52['High'].max())
        caida = (p / mx - 1.0) if mx > 0 else 0.0
        sma200 = float(h['Close'].rolling(200).mean().iloc[-1])
        dist_sma200 = (p / sma200 - 1.0) if sma200 > 0 else 0.0
        
        # RSI Wilder 14
        delta = h52['Close'].diff()
        g = delta.clip(lower=0).ewm(alpha=1/14, adjust=False).mean()
        l = -delta.clip(upper=0).ewm(alpha=1/14, adjust=False).mean()
        rsi = float((100 - 100/(1 + g/l.replace(0, 1e-9))).iloc[-1])
        
        # MACD Semanal (Cava: Cruce de manos fuertes y tendencia)
        h_w = h.resample('W').agg({'Open':'first','High':'max','Low':'min','Close':'last','Volume':'sum'}).dropna()
        exp12 = h_w['Close'].ewm(span=12, adjust=False).mean()
        exp26 = h_w['Close'].ewm(span=26, adjust=False).mean()
        macd_line = exp12 - exp26
        signal_line = macd_line.ewm(span=9, adjust=False).mean()
        
        macd_val = float(macd_line.iloc[-1])
        sig_val = float(signal_line.iloc[-1])
        macd_cruce_alcista = bool(macd_val > sig_val)
        macd_sobre_cero = bool(macd_val > 0)
        
        # Estocástico Semanal (14, 3) - Para "La Bonita" de Cava
        low14 = h_w['Low'].rolling(14).min()
        high14 = h_w['High'].rolling(14).max()
        k_fast = 100 * ((h_w['Close'] - low14) / (high14 - low14).replace(0, 1e-9))
        d_slow = k_fast.rolling(3).mean()
        stoch_k = float(k_fast.iloc[-1])
        stoch_d = float(d_slow.iloc[-1])
        
        # Pauta Bonita Alcista: Manos fuertes alineadas + manos débiles saliendo de sobreventa
        la_bonita = bool((macd_cruce_alcista or macd_sobre_cero) and (stoch_k < 40 and stoch_k > stoch_d))
        
        # Break of Structure (BOS 10 sesiones diarias)
        max_10d = float(h52['High'].shift(1).rolling(10).max().iloc[-1])
        bos = bool(p > max_10d) if not pd.isna(max_10d) else False
        
        # Volumen institucional vs media de 20 días
        vol_ratio = 1.0
        if not ticker.startswith("^"):
            v20 = float(h52['Volume'].rolling(20).mean().iloc[-1])
            if v20 > 0: vol_ratio = float(h52['Volume'].iloc[-1] / v20)
            
        return {
            "precio": p, "max52": mx, "caida": caida, "sma200": sma200, "dist_sma": dist_sma200,
            "rsi": rsi, "macd_val": macd_val, "sig_val": sig_val,
            "macd_alcista": macd_cruce_alcista, "macd_cero": macd_sobre_cero,
            "stoch_k": stoch_k, "stoch_d": stoch_d, "la_bonita": la_bonita,
            "bos": bos, "max_10d": max_10d, "vol_ratio": vol_ratio, "hist": h
        }
    except Exception as e:
        return None

# ==================== FLUJO INSTITUCIONAL (OBV, A/D, VWAP) ====================
@st.cache_data(ttl=300)
def flujo_institucional(ticker):
    try:
        h = yf.Ticker(ticker).history(period="1y")
        if len(h) < 60: return None
        d = h.copy()
        
        vol_20 = float(d['Volume'].tail(20).sum())
        if vol_20 <= 0: vol_20 = 1.0

        dir_ = np.sign(d['Close'].diff()).fillna(0)
        d['OBV'] = (d['Volume'] * dir_).cumsum()
        obv_diff = float(d['OBV'].iloc[-1] - d['OBV'].iloc[-20])
        obv_s = obv_diff / vol_20
        obv_sig = "ALCISTA" if obv_s > 0.05 else "BAJISTA" if obv_s < -0.05 else "NEUTRAL"

        hl = (d['High'] - d['Low']).replace(0, 1e-9)
        d['AD'] = ((((d['Close']-d['Low']) - (d['High']-d['Close'])) / hl) * d['Volume']).cumsum()
        ad_diff = float(d['AD'].iloc[-1] - d['AD'].iloc[-20])
        ad_s = ad_diff / vol_20
        ad_sig = "ACUMULACIÓN" if ad_s > 0.05 else "DISTRIBUCIÓN" if ad_s < -0.05 else "NEUTRAL"

        da = d.loc[d['Low'].iloc[-min(252, len(d)):].idxmin():]
        vwap = float((da['Close']*da['Volume']).sum()/da['Volume'].sum()) if da['Volume'].sum() else float(d['Close'].iloc[-1])
        sma50, p = float(d['Close'].rolling(50).mean().iloc[-1]), float(d['Close'].iloc[-1])
        sma200 = float(d['Close'].rolling(200).mean().iloc[-1]) if len(d) >= 200 else sma50
        
        score = sum([
            1 if obv_sig=="ALCISTA" else -1 if obv_sig=="BAJISTA" else 0,
            1 if ad_sig=="ACUMULACIÓN" else -1 if ad_sig=="DISTRIBUCIÓN" else 0,
            1 if (p/vwap-1)>0 else -1,
            1 if p>sma50 else -1,
            1 if p>sma200 else -1
        ])
        return {"score": score, "obv": obv_s, "obv_sig": obv_sig, "ad": ad_s, "ad_sig": ad_sig, "vwap": vwap, "dist_vwap": (p/vwap-1)*100, "p": p}
    except: return None

# ==================== TEORÍA DE DOW ====================
@st.cache_data(ttl=300)
def dow_theory(hist, order=5):
    try:
        close = hist['Close'].tail(180)
        vals = close.values
        mx, mn = [], []
        for i in range(order, len(vals) - order):
            w = vals[i-order:i+order+1]
            if vals[i] == w.max(): mx.append(i)
            elif vals[i] == w.min(): mn.append(i)
        if len(mx) < 2 or len(mn) < 2: return None
        m1, m2, n1, n2 = mx[-2], mx[-1], mn[-2], mn[-1]
        if close.iloc[m2] > close.iloc[m1] and close.iloc[n2] > close.iloc[n1]: trend, det, color = "ALCISTA", "Máximos y Mínimos Crecientes", "🟢"
        elif close.iloc[m2] < close.iloc[m1] and close.iloc[n2] < close.iloc[n1]: trend, det, color = "BAJISTA", "Máximos y Mínimos Decrecientes", "🔴"
        else: trend, det, color = "LATERAL", "Estructura Mixta (Consolidación)", "⚪"
        return {"trend": trend, "det": det, "color": color, "close": close, "m1": m1, "m2": m2, "n1": n1, "n2": n2}
    except: return None

def grafico_dow(dow, nombre):
    close = dow["close"]
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=close.index, y=close.values, mode='lines', name='Precio', line=dict(color='#3b82f6', width=2)))
    fig.add_trace(go.Scatter(
        x=[close.index[dow["m1"]], close.index[dow["m2"]]],
        y=[close.iloc[dow["m1"]], close.iloc[dow["m2"]]],
        mode='markers+text', name='Techos',
        marker=dict(color='#ef4444', size=11, symbol='triangle-down'),
        text=[f"{close.iloc[dow['m1']]:.1f}", f"{close.iloc[dow['m2']]:.1f}"],
        textposition='top center'
    ))
    fig.add_trace(go.Scatter(
        x=[close.index[dow["n1"]], close.index[dow["n2"]]],
        y=[close.iloc[dow["n1"]], close.iloc[dow["n2"]]],
        mode='markers+text', name='Suelos',
        marker=dict(color='#22c55e', size=11, symbol='triangle-up'),
        text=[f"{close.iloc[dow['n1']]:.1f}", f"{close.iloc[dow['n2']]:.1f}"],
        textposition='bottom center'
    ))
    fig.update_layout(
        title=f"{nombre} — Estructura {dow['trend']} ({dow['det']})",
        height=380, margin=dict(l=20, r=20, t=40, b=20),
        hovermode='x unified', showlegend=False,
        template="plotly_dark"
    )
    return fig

# ==================== MOTOR DE DECISIÓN CAVA (COMPRA Y VENTA) ====================
def evaluar_motor_cava(d, reglas, v_info, ticker):
    caida = d["caida"]
    v_act = v_info["actual"]
    v_tension = v_info["tension"]
    
    # 1. Determinar Zona Teórica por Caída
    if caida <= reglas["c3"]: zona_teorica = 3
    elif caida <= reglas["c2"]: zona_teorica = 2
    elif caida <= reglas["c1"]: zona_teorica = 1
    else: zona_teorica = 0
    
    # Si no hay descuento suficiente
    if zona_teorica == 0:
        dist_z1 = abs(caida - reglas["c1"])
        precio_z1 = d["max52"] * (1.0 + reglas["c1"])
        caida_dolares = d["precio"] - precio_z1
        return 0, "ESPERAR", f"Falta caída. Descuento actual: {caida:.2%}. A {dist_z1:.2%} de Zona 1 ({caida_dolares:,.2f} $)", dist_z1, precio_z1
    
    # 2. Filtro Anti-Cuchillo VIX Dinámico (Cava, pág. 61)
    if abs(caida) >= 0.25 and (v_act < 20.0 and v_tension < 0.10):
        return 0, "BLOQUEADO VIX", f"Caída profunda (-{abs(caida):.1%}) sin pánico real. VIX {v_act:.1f} < 20 y tensión {v_tension:+.1%}.", 0, 0
    
    # 3. Filtro BOS (Quiebre de Estructura de Suelo de Cava)
    if zona_teorica >= 2 and not d["bos"] and v_act < 25.0:
        p_bos = d["max_10d"]
        dist_bos = ((p_bos - d["precio"]) / d["precio"]) * 100.0
        return 0, "BLOQUEADO BOS", f"En soporte pero sin confirmación de giro. Requiere superar {p_bos:,.2f} $ (+{dist_bos:.1f}%) o VIX > 25.", 0, p_bos
        
    # 4. Filtro de Volumen Institucional (No synthetic)
    if not ticker.startswith("^") and d["vol_ratio"] < 0.85:
        return 0, "BLOQUEADO VOLUMEN", f"Volumen institucional débil ({d['vol_ratio']:.2f}x < 0.85x). Sin absorción.", 0, 0

    # 5. Señal de Entrada Validada
    pauta_txt = " (PAUTA BONITA CAVA)" if d["la_bonita"] else ""
    return zona_teorica, f"COMPRAR ZONA {zona_teorica}{pauta_txt}", f"Caída {caida:.2%}, VIX {v_act:.1f}, Vol {d['vol_ratio']:.2f}x. Condiciones alineadas.", 0, 0

def evaluar_venta_cava(d, reglas):
    ds = d["dist_sma"]
    rsi = d["rsi"]
    if ds >= reglas["v3"] and rsi >= reglas["rsi_v3"]:
        return 3, "VENTA ZONA 3 (RECOGIDA TOTAL)", "Extremo sobrecalentamiento. Traspasar entre 60% y 100% al Fondo Monetario."
    if ds >= reglas["v2"] and rsi >= reglas["rsi_v2"]:
        return 2, "VENTA ZONA 2 (RECOGIDA PARCIAL)", "Fuerte tensión alcista. Traspasar el 30% de la posición al Fondo Monetario."
    if ds >= reglas["v1"] and rsi >= reglas["rsi_v1"]:
        return 1, "VENTA ZONA 1 (VIGILANCIA)", "Tensión alcista inicial. Frenar nuevas compras y vigilar soporte de medias."
    return 0, "MANTENER", "Parámetros técnicos sanos. Mantener posición."

# ==================== CABECERA PRINCIPAL ====================
st.title("🦈 Radar Tiburón Cava Pro — Asignación 60.000 €")

v_info = get_vix_data()

c_m1, c_m2, c_m3, c_m4 = st.columns(4)
c_m1.info(f"🏛️ **Ciclo Presidencial:**\n{get_ciclo_presidencial()}")
c_m2.warning(f"📅 **Estacionalidad:**\n{get_estacionalidad()}")
c_m3.metric("VIX Actual", f"{v_info['actual']:.2f}", f"{v_info['tension']:+.1%} vs SMA10 ({v_info['sma10']:.1f})")
c_m4.success(f"🛡️ **Colchón Fuera:**\n{COLCHON_EMERGENCIAS:,.0f} € (Trade Republic 3%)")

# Barra lateral
st.sidebar.header("💼 Arquitectura de Cartera")
st.sidebar.markdown(f"**Capital Radar:** `{CAPITAL_RADAR:,.0f} €`")
st.sidebar.markdown(f"**Monetario Puente (25%):** `{CAPITAL_RADAR * LIQUIDEZ_MONETARIO_PESO:,.0f} €`")
st.sidebar.markdown(f"**Colchón Emergencias:** `{COLCHON_EMERGENCIAS:,.0f} €`")
st.sidebar.markdown("---")
st.sidebar.caption("Doctrina Cava: Comprar en tramos tras confirmación. Sin stops en fondos indexados; la liquidez en monetario es tu escudo protector.")

if st.sidebar.button("🔄 Forzar Datos en Vivo"):
    st.cache_data.clear()
    st.rerun()

# Pestañas principales
tab_senales, tab_flujo, tab_dow, tab_guia = st.tabs([
    "🎯 Semáforo y Tramos", "🏛️ Rayos X de Flujo", "📰 Diario (Teoría de Dow)", "📖 Manual Operativo Cava"
])

# ==================== PESTAÑA 1: SEÑALES Y TRAMOS ====================
with tab_senales:
    st.subheader("Semáforo Cuantitativo Institucional")
    
    for nombre, reglas in ASIGNACION.items():
        d = get_market_data(reglas["ticker"])
        if not d:
            st.error(f"Error conectando con los datos de {nombre}")
            continue
            
        zona_c, estado_c, motivo_c, dist_z1, precio_z1 = evaluar_motor_cava(d, reglas, v_info, reglas["ticker"])
        zona_v, estado_v, motivo_v = evaluar_venta_cava(d, reglas)
        
        cap_posicion = CAPITAL_RADAR * reglas["peso"]
        tramo_1 = cap_posicion * 0.30
        tramo_2 = cap_posicion * 0.30
        tramo_3 = cap_posicion * 0.40
        
        if "COMPRAR" in estado_c: icon_c = "🟢"
        elif "BLOQUEADO" in estado_c: icon_c = "🛡️"
        elif zona_v > 0: icon_c = "🟡"
        else: icon_c = "⚪"
        
        badge_op = "⏱️ TRASPASO FONDO" if reglas["es_fondo"] else "⚡ INMEDIATO (Spot)"
        
        with st.expander(f"{icon_c} **{nombre}** | {badge_op} | Compra: **{estado_c}** | Venta: **{estado_v}**", expanded=True):
            m1, m2, m3, m4, m5 = st.columns(5)
            m1.metric("Precio Spot", f"{d['precio']:,.2f} $")
            m2.metric("Descuento (ATH)", f"{d['caida']:.2%}")
            m3.metric("Línea Vital (SMA200)", f"{d['sma200']:,.2f} $", f"{d['dist_sma']:+.2%}")
            m4.metric("MACD Semanal", "ALCISTA" if d['macd_alcista'] else "BAJISTA", "Sobre 0" if d['macd_cero'] else "Bajo 0")
            m5.metric("Estocástico (14w)", f"{d['stoch_k']:.1f}", "La Bonita" if d['la_bonita'] else "Neutro")
            
            st.markdown(f"**Vehículo:** `{reglas['vehiculo']}` en **{reglas['plataforma']}** (Asignación total: **{cap_posicion:,.0f} €**)")

            # ==================== SEMÁFORO DCA (FILOSOFÍA CAVA) ====================
            st.markdown("---")
            st.markdown("#### 🚦 Semáforo DCA Mensual")
            
            if d['stoch_k'] > 80:
                color_dca = "🔴"
                mensaje_dca = "SOBRECOMPRA EXTREMA. El estocástico semanal está por encima de 80. Si puedes, retrasa tu DCA unos días. Si no, haz tu aportación normal pero NO añadas dinero extra."
                accion_dca = "ESPERAR / APORTACIÓN MÍNIMA"
            elif d['la_bonita']:
                color_dca = "🟢"
                mensaje_dca = "¡LA BONITA! El estocástico ha girado al alza desde zona de sobreventa con el MACD alcista. Es el momento de mayor probabilidad. Adelanta tu DCA y añade un extra de tu pólvora de tramos."
                accion_dca = "COMPRA CON LA BONITA (ADELANTAR + EXTRA)"
            elif d['macd_alcista']:
                color_dca = "🟡"
                mensaje_dca = "MERCADO NEUTRO. El MACD está alcista pero el estocástico no ha dado señal de giro desde sobreventa. Ejecuta tu DCA mensual según tu calendario habitual."
                accion_dca = "COMPRA NORMAL (CALENDARIO)"
            else:
                color_dca = "🔴"
                mensaje_dca = "TENDENCIA MACRO BAJISTA. El MACD semanal no está alcista. No es momento de comprar con fuerza. Si tu calendario te obliga, haz tu DCA normal, pero NO añadas extra."
                accion_dca = "ESPERAR / APORTACIÓN MÍNIMA"
            
            st.markdown(f"""
            <div style="background-color: {'#1a472a' if color_dca == '🟢' else '#4a4a1a' if color_dca == '🟡' else '#4a1a1a'}; padding: 15px; border-radius: 10px; margin: 10px 0;">
                <h4 style="margin: 0; color: {'#4ade80' if color_dca == '🟢' else '#facc15' if color_dca == '🟡' else '#f87171'};">
                    {color_dca} {accion_dca}
                </h4>
                <p style="margin: 10px 0 0 0; color: #e5e7eb;">{mensaje_dca}</p>
            </div>
            """, unsafe_allow_html=True)
            
            st.caption(f"Estocástico %K: {d['stoch_k']:.1f} | %D: {d['stoch_d']:.1f} | MACD Alcista: {'Sí' if d['macd_alcista'] else 'No'} | La Bonita: {'Sí' if d['la_bonita'] else 'No'}")
            st.markdown("---")
            # ======================================================================

            # --- EVALUACIÓN DE COMPRA ---
            if estado_c == "ESPERAR":
                st.info(f"⏳ **{motivo_c}**")
                progreso = max(0.0, min(1.0, 1.0 - (dist_z1 / abs(reglas['c1']))))
                st.progress(progreso, text=f"Proximidad a Zona 1: Falta {dist_z1:.2%} de retroceso para entrar a {precio_z1:,.2f} $")
            elif "BLOQUEADO" in estado_c:
                st.warning(f"#### 🛡️ {estado_c}\n{motivo_c}")
                st.info("El algoritmo te protege de atrapar un cuchillo en caída libre. No hay compras hasta confirmación.")
            elif "COMPRAR" in estado_c:
                st.success(f"#### 🎯 {estado_c}\n{motivo_c}")
                st.markdown(f"""
                - **Tramo a Ejecutar:** `{tramo_1:,.0f} €` (Tramo 1 = 30% del bloque)
                - **Procedimiento de Traspaso:** Si estás en MyInvestor, traspasa desde el Fondo Monetario (`FR0001028830`).
                - **Munición en Reserva:** Conserva `{cap_posicion - tramo_1:,.0f} €` en liquidez para Zona 2 y 3.
                """)
                
            # --- EVALUACIÓN DE VENTA / TRASPASO AL MONETARIO ---
            if zona_v > 0:
                st.warning(f"#### ⚠️ {estado_v}\n{motivo_v}")
                if reglas["es_fondo"]:
                    st.markdown("👉 **Acción Recomendada:** Ordenar **traspaso hacia el Fondo Monetario** (`FR0001028830`) en MyInvestor para blindar plusvalías con 0 € de IRPF.")
                else:
                    st.markdown("👉 **Acción Recomendada:** Venta parcial a cuenta de efectivo. Ten en cuenta que tributa al 19% en la base del ahorro.")

            st.caption(f"Estructura Táctica: Tramo 1 (30%): {tramo_1:,.0f} € | Tramo 2 (30%): {tramo_2:,.0f} € | Tramo 3 (40%): {tramo_3:,.0f} €")

# ==================== PESTAÑA 2: RAYOS X INSTITUCIONAL ====================
with tab_flujo:
    st.subheader("Rayos X de Flujo Institucional (Manos Fuertes vs. Débiles)")
    st.caption("Mide si las grandes instituciones están acumulando en silencio o distribuyendo papel a la masa.")
    
    for nombre, reglas in ASIGNACION.items():
        fl = flujo_institucional(reglas["ticker"])
        if not fl: continue
        ic_fl = "🟢" if fl['score'] >= 2 else "⚪" if fl['score'] >= 0 else "🔴"
        with st.expander(f"{ic_fl} **{nombre}** — Puntuación Institucional: {fl['score']:+d}", expanded=True):
            f1, f2, f3 = st.columns(3)
            f1.metric("Presión de Volumen (OBV)", f"{fl['obv']:+.1%}", fl['obv_sig'])
            f2.metric("Acumulación / Distribución (A/D)", f"{fl['ad']:+.1%}", fl['ad_sig'])
            f3.metric("Precio VWAP Institucional", f"{fl['vwap']:,.2f} $", f"{fl['dist_vwap']:+.2f}% vs Spot")

# ==================== PESTAÑA 3: TEORÍA DE DOW ====================
with tab_dow:
    st.subheader("Estructura de Tendencia (Teoría de Dow)")
    st.caption("Cava (Cap. I): Una tendencia alcista exige techos y suelos crecientes. Sin confirmación, no hay cambio de sesgo.")
    
    for nombre, reglas in ASIGNACION.items():
        d = get_market_data(reglas["ticker"])
        if not d: continue
        dow = dow_theory(d["hist"])
        if not dow: continue
        with st.expander(f"{dow['color']} **{nombre}** — Estructura {dow['trend']}", expanded=True):
            st.plotly_chart(grafico_dow(dow, nombre), use_container_width=True)

# ==================== PESTAÑA 4: GUÍA OPERATIVA CAVA ====================
with tab_guia:
    st.markdown("""
    ### Principios Rectores de José Luis Cava (*El Arte de Especular*)
    
    1. **Comprar tras la confirmación, nunca en caída libre:**
       - El aficionado intenta comprar el mínimo exacto y suele comprar un cuchillo.
       - El profesional espera a que el mercado frene, absorba la oferta y confirme un quiebre de estructura (BOS).
       
    2. **El Escudo de la Liquidez en Tramos (30% / 30% / 40%):**
       - **Tramo 1 (30%):** En el pullback inicial (Zona 1), para no perder el tren si rebota rápido.
       - **Tramo 2 (30%):** En el soporte mayor de la media de 200 sesiones (Zona 2).
       - **Tramo 3 (40%):** En capitulaciones con pánico extremo o roturas de suelo con gran volumen.
       
    3. **Cero Stop Loss en Fondos Indexados:**
       - No pongas órdenes de stop que malvendan tus fondos indexados en pánico. 
       - Tu stop loss es la asignación de activos: 10.000 € en colchón fuera, 15.000 € en monetario puente y entrar solo con tramos pequeños.
       
    4. **El Diferimiento Fiscal del Art. 94 LIRPF en España:**
       - Cuando el mercado se sobrecalienta (Venta Zona 2 o 3), nunca vendas a cuenta corriente.
       - Traspasa del fondo indexado al Fondo Monetario (`FR0001028830`). Tus ganancias quedan protegidas y el interés compuesto sigue trabajando con 0 € de tributación inmediata.
    """)
