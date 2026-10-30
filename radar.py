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

# Estilos CSS de diseño profesional de alto contraste
st.markdown("""
<style>
    .stAlert { border-radius: 8px; font-weight: 500; }
    div[data-testid="stMetricValue"] { font-size: 1.40rem; font-weight: 700; }
    .stProgress > div > div > div > div { background-color: #2563eb; }
    .card-tactica {
        background-color: #111827;
        border: 1px solid #374151;
        padding: 18px;
        border-radius: 10px;
        margin-bottom: 12px;
    }
    .card-dca {
        padding: 16px;
        border-radius: 10px;
        margin-top: 15px;
        border-left: 5px solid;
    }
    .badge-corte-ok {
        background-color: #065f46;
        color: #6ee7b7;
        padding: 4px 10px;
        border-radius: 6px;
        font-weight: 700;
        font-size: 0.85rem;
    }
    .badge-corte-tarde {
        background-color: #7c2d12;
        color: #fdba74;
        padding: 4px 10px;
        border-radius: 6px;
        font-weight: 700;
        font-size: 0.85rem;
    }
</style>
""", unsafe_allow_html=True)

# ==================== RUTAS Y CONFIGURACIÓN ====================
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
ISIN_MONETARIO_NODRIZA = "FR0000447823"
NOMBRE_MONETARIO_NODRIZA = "AXA Trésor Court Terme C (FR0000447823)"

ASIGNACION = {
    "S&P 500 (Core)": {
        "ticker": "^GSPC", "peso": 0.40, "vehiculo": "Fidelity S&P 500 Index P EUR Acc (IE00BYX5MX67)",
        "isin": "IE00BYX5MX67", "hora_corte": 16, "ter": 0.0006,
        "plataforma": "MyInvestor", "es_fondo": True,
        "c1": -0.04, "c2": -0.10, "c3": -0.20,
        "v1": 0.15, "v2": 0.25, "v3": 0.35, "rsi_v1": 70, "rsi_v2": 75, "rsi_v3": 80
    },
    "Nasdaq 100 (Satélite)": {
        "ticker": "^NDX", "peso": 0.15, "vehiculo": "MyInvestor Nasdaq 100 FI (ES0165265002)",
        "isin": "ES0165265002", "hora_corte": 12, "ter": 0.0038,
        "plataforma": "MyInvestor", "es_fondo": True,
        "c1": -0.06, "c2": -0.15, "c3": -0.25,
        "v1": 0.18, "v2": 0.30, "v3": 0.45, "rsi_v1": 70, "rsi_v2": 75, "rsi_v3": 80
    },
    "Oro Físico (Refugio)": {
        "ticker": "GC=F", "peso": 0.15, "vehiculo": "ETC iShares Physical Gold (IE00B4ND3602) — 0,12% TER todo incluido",
        "isin": "IE00B4ND3602", "hora_corte": 17, "ter": 0.0012,
        "plataforma": "MyInvestor / Trade Republic", "es_fondo": False,
        "c1": -0.05, "c2": -0.10, "c3": -0.18,
        "v1": 0.15, "v2": 0.25, "v3": 0.35, "rsi_v1": 70, "rsi_v2": 75, "rsi_v3": 80
    },
    "Bitcoin (Asimetría)": {
        "ticker": "BTC-USD", "peso": 0.05, "vehiculo": "Spot Cripto 24/7",
        "isin": "BTC-USD", "hora_corte": 24, "ter": 0.0000,
        "plataforma": "Trade Republic", "es_fondo": False,
        "c1": -0.15, "c2": -0.30, "c3": -0.50,
        "v1": 0.35, "v2": 0.65, "v3": 1.00, "rsi_v1": 75, "rsi_v2": 80, "rsi_v3": 85
    }
}
LIQUIDEZ_MONETARIO_PESO = 0.25  # 15.000 € en AXA Trésor Court Terme C (FR0000447823)

# ==================== CATÁLOGO MAESTRO DE 9 FONDOS MYINVESTOR AUDITADOS ====================
CATALOGO_FONDOS_MY = [
    {
        "bloque": "Búnker / Pólvora Seca",
        "nombre": "AXA Trésor Court Terme C",
        "isin": "FR0000447823",
        "hora_corte": 10,
        "ter": "0,05%",
        "ter_num": 0.0005,
        "r_2026": "+1,67%",
        "r_1a": "+2,25%",
        "r_3a": "+2,95%",
        "r_5a": "+2,28%",
        "vol_3a": "0,25%",
        "sharpe_3a": 3.74,
        "rating": "Monetario (€STR)",
        "top_holdings": "Deuda soberana Francia/España y depósitos €STR (< 60 días)",
        "rol_radar": "Base nodriza. Custodia la liquidez con 0% volatilidad y financia los tramos sin peaje fiscal.",
        "estado_calidad": "🟢 BÚNKER NODRIZA",
        "ticker_proxy": "^IRX"
    },
    {
        "bloque": "Core USA (Crecimiento)",
        "nombre": "Fidelity S&P 500 Index P EUR Acc",
        "isin": "IE00BYX5MX67",
        "hora_corte": 16,
        "ter": "0,06%",
        "ter_num": 0.0006,
        "r_2026": "+16,24%",
        "r_1a": "+17,99%",
        "r_3a": "+22,17%",
        "r_5a": "+12,79%",
        "vol_3a": "12,84%",
        "sharpe_3a": 1.25,
        "rating": "★★★★",
        "top_holdings": "NVIDIA (7,7%), Apple (7,6%), Microsoft (5,9%), Amazon (3,6%), Alphabet",
        "rol_radar": "Motor principal de Wall Street. Recibe tramos en soportes clave y ahorro sistemático (DCA).",
        "estado_calidad": "🟢 CORE IMBATIBLE",
        "ticker_proxy": "^GSPC"
    },
    {
        "bloque": "Diversificación Core",
        "nombre": "Fidelity MSCI World Index P EUR Acc",
        "isin": "IE00BYX5NX33",
        "hora_corte": 16,
        "ter": "0,12%",
        "ter_num": 0.0012,
        "r_2026": "+15,54%",
        "r_1a": "+17,91%",
        "r_3a": "+21,17%",
        "r_5a": "+11,61%",
        "vol_3a": "11,43%",
        "sharpe_3a": 1.31,
        "rating": "★★★★",
        "top_holdings": "72,9% EE. UU., 15,3% Europa, 5,7% Japón, 3,4% Canadá (1.247 valores)",
        "rol_radar": "Mayor Ratio Sharpe (1,31). Reduce concentración en EE. UU. incorporando Europa, Japón y Canadá.",
        "estado_calidad": "🟢 MÁXIMO SHARPE",
        "ticker_proxy": "URTH"
    },
    {
        "bloque": "Satélite Tech (IA)",
        "nombre": "MyInvestor Nasdaq 100 FI",
        "isin": "ES0165265002",
        "hora_corte": 12,
        "ter": "0,38% (0,45% GC)",
        "ter_num": 0.0038,
        "r_2026": "+23,88%",
        "r_1a": "+19,53%",
        "r_3a": "+24,86%",
        "r_5a": "+10,31%",
        "vol_3a": "18,85%",
        "sharpe_3a": 1.09,
        "rating": "★★★",
        "top_holdings": "Réplica Nasdaq 100 Net Total Return EUR (60% Tecnología, 13% Comunicación)",
        "rol_radar": "Vehículo para disparar los tramos de Zona 1 y Zona 2 de sobreventa tecnológica sin pasar por Hacienda.",
        "estado_calidad": "🟢 SATÉLITE TÁCTICO",
        "ticker_proxy": "^NDX"
    },
    {
        "bloque": "Refugio Europa Low-Cost",
        "nombre": "iShares Europe Equity Index A2 EUR",
        "isin": "LU0836512706",
        "hora_corte": 10,
        "ter": "0,12% (0,54% GC)",
        "ter_num": 0.0012,
        "r_2026": "+10,26%",
        "r_1a": "+16,13%",
        "r_3a": "+17,16%",
        "r_5a": "+9,30%",
        "vol_3a": "10,70%",
        "sharpe_3a": 1.06,
        "rating": "★★★★",
        "top_holdings": "ASML (5,1%), HSBC (2,5%), Roche (2,1%), Shell (2,0%), Novartis (1,9%), AstraZeneca, Nestlé",
        "rol_radar": "Rotación defensiva cuando el flujo institucional abandona múltiplos caros de IA buscando Pharma + Consumo.",
        "estado_calidad": "🟢 REFUGIO DEFENSIVO",
        "ticker_proxy": "VGK"
    },
    {
        "bloque": "Refugio Salud / Pharma USA",
        "nombre": "Wellington Global Health Care D EUR Acc",
        "isin": "IE00BF2ZVB54",
        "hora_corte": 12,
        "ter": "1,74%",
        "ter_num": 0.0174,
        "r_2026": "+9,81%",
        "r_1a": "+28,44%",
        "r_3a": "+12,08%",
        "r_5a": "+4,26%",
        "vol_3a": "14,77%",
        "sharpe_3a": 0.36,
        "rating": "★★★",
        "top_holdings": "80,2% EE. UU.: Eli Lilly (9,3%), Merck (5,5%), J&J (5,0%), AstraZeneca (4,0%), UnitedHealth, AbbVie",
        "rol_radar": "Refugio de farmacia estadounidense (tesis Cava) y biotecnología para rotación defensiva acotada (5%-10%).",
        "estado_calidad": "🟡 TÁCTICO SALUD USA",
        "ticker_proxy": "XLV"
    },
    {
        "bloque": "Refugio Energía / Inflación",
        "nombre": "Guinness Global Energy D EUR Acc",
        "isin": "IE00B3CCJB88",
        "hora_corte": 14,
        "ter": "1,27%",
        "ter_num": 0.0127,
        "r_2026": "+42,98%",
        "r_1a": "+60,63%",
        "r_3a": "+17,17%",
        "r_5a": "+18,17%",
        "vol_3a": "20,60%",
        "sharpe_3a": 0.52,
        "rating": "★★",
        "top_holdings": "ExxonMobil (5,3%), Chevron (4,7%), Shell (4,7%), Valero (4,7%), BP (4,5%), TotalEnergies",
        "rol_radar": "Cobertura táctica ante shocks de oferta de petróleo, gas y tensiones geopolíticas que drenen liquidez.",
        "estado_calidad": "🟡 TÁCTICO ENERGÍA",
        "ticker_proxy": "XLE"
    },
    {
        "bloque": "Refugio Anticrisis (Duración)",
        "nombre": "Vanguard Global Bond Index EUR Hedged",
        "isin": "IE00B18GC888",
        "hora_corte": 12,
        "ter": "0,15%",
        "ter_num": 0.0015,
        "r_2026": "-3,38%",
        "r_1a": "-2,47%",
        "r_3a": "+2,78%",
        "r_5a": "-1,99%",
        "vol_3a": "4,50%",
        "sharpe_3a": -0.15,
        "rating": "★★★",
        "top_holdings": "16.967 bonos globales (64% Gubernamental, 24% Corporativo). Duración efectiva: 5,99 años",
        "rol_radar": "Seguro de recesión deflacionaria: solo se activa cuando los bancos centrales recortan tipos agresivamente.",
        "estado_calidad": "⚪ SOLO EN RECESIÓN",
        "ticker_proxy": "BND"
    },
    {
        "bloque": "Refugio Cadena Alimentaria",
        "nombre": "Pictet - Nutrition P EUR",
        "isin": "LU0366534344",
        "hora_corte": 12,
        "ter": "2,01%",
        "ter_num": 0.0201,
        "r_2026": "+5,72%",
        "r_1a": "+8,14%",
        "r_3a": "+2,77%",
        "r_5a": "-4,31%",
        "vol_3a": "12,07%",
        "sharpe_3a": -0.23,
        "rating": "★★",
        "top_holdings": "Deere & Co (7,4%), Ecolab (4,6%), Novonesis (4,5%), Danone (4,3%), Thermo Fisher",
        "rol_radar": "Cadena agroalimentaria. Penalizado por su TER del 2,01% (Sharpe -0,23); preferible cubrir consumo vía iShares Europe.",
        "estado_calidad": "🔴 EVITAR POR TER (2,01%)",
        "ticker_proxy": "XLP"
    }
]

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
    except Exception:
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
    except Exception:
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
    except Exception:
        return None

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
    except Exception:
        return None

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
def evaluar_motor_cava(d, reglas, v_info, ticker, cap_posicion):
    caida = d["caida"]
    v_act = v_info["actual"]
    v_tension = v_info["tension"]
    
    c1, c2, c3 = reglas["c1"], reglas["c2"], reglas["c3"]
    t1_eur = cap_posicion * 0.30
    t2_eur = cap_posicion * 0.30
    t3_eur = cap_posicion * 0.40

    # 1. Determinar en qué Zona de Descuento nos encontramos
    if caida <= c3:
        zona_actual = 3
        tramo_actual_nom = "Tramo 3 (40%)"
        tramo_actual_eur = t3_eur
        target_zona = 3
        target_eur = t3_eur
        dist_target = 0.0
        precio_target = d["max52"] * (1.0 + c3)
    elif caida <= c2:
        zona_actual = 2
        tramo_actual_nom = "Tramo 2 (30%)"
        tramo_actual_eur = t2_eur
        target_zona = 2
        target_eur = t2_eur
        dist_target = 0.0
        precio_target = d["max52"] * (1.0 + c2)
    elif caida <= c1:
        zona_actual = 1
        tramo_actual_nom = "Tramo 1 (30%)"
        tramo_actual_eur = t1_eur
        target_zona = 1
        target_eur = t1_eur
        dist_target = 0.0
        precio_target = d["max52"] * (1.0 + c1)
    else:
        zona_actual = 0
        target_zona = 1
        target_eur = t1_eur
        dist_target = abs(caida - c1)
        precio_target = d["max52"] * (1.0 + c1)
        caida_pts = d["precio"] - precio_target
        motivo = (f"Esperando ZONA 1 — Tramo 1 (30%): `{t1_eur:,.0f} €`. "
                  f"Falta un {dist_target:.2%} de retroceso (Gatillo: {precio_target:,.2f} $ | Faltan {caida_pts:,.2f} $)")
        return 0, "ESPERAR", motivo, dist_target, precio_target, target_zona, target_eur

    # 2. Filtro Anti-Cuchillo VIX Dinámico (Cava, pág. 61)
    if abs(caida) >= 0.25 and (v_act < 20.0 and v_tension < 0.10):
        motivo = (f"En ZONA {zona_actual} ({tramo_actual_nom}: `{tramo_actual_eur:,.0f} €`) pero BLOQUEADO VIX. "
                  f"Caída del {caida:.1%} sin pánico institucional (VIX actual: {v_act:.1f} < 20 y tensión {v_tension:+.1%}).")
        return 0, "BLOQUEADO VIX", motivo, 0.0, 0.0, zona_actual, tramo_actual_eur

    # 3. Filtro BOS (Quiebre de Estructura de Suelo de Cava)
    if zona_actual >= 2 and not d["bos"] and v_act < 25.0:
        p_bos = d["max_10d"]
        dist_bos = ((p_bos - d["precio"]) / d["precio"]) * 100.0
        motivo = (f"En ZONA {zona_actual} ({tramo_actual_nom}: `{tramo_actual_eur:,.0f} €`) pero BLOQUEADO BOS. "
                  f"Requiere quiebre de suelo superando {p_bos:,.2f} $ (+{dist_bos:.1f}%) o VIX > 25.")
        return 0, "BLOQUEADO BOS", motivo, 0.0, p_bos, zona_actual, tramo_actual_eur

    # 4. Filtro de Volumen Institucional
    if not ticker.startswith("^") and d["vol_ratio"] < 0.85:
        motivo = (f"En ZONA {zona_actual} ({tramo_actual_nom}: `{tramo_actual_eur:,.0f} €`) pero BLOQUEADO VOLUMEN. "
                  f"Volumen débil ({d['vol_ratio']:.2f}x < 0.85x). Sin absorción.")
        return 0, "BLOQUEADO VOLUMEN", motivo, 0.0, 0.0, zona_actual, tramo_actual_eur

    # 5. Señal de Entrada Validada
    pauta_txt = " (PAUTA BONITA CAVA)" if d["la_bonita"] else ""
    motivo = (f"¡GATILLO ACTIVADO! Ejecutar ZONA {zona_actual}{pauta_txt} — {tramo_actual_nom}: `{tramo_actual_eur:,.0f} €`. "
              f"Descuento {caida:.2%} validado con estructura y volatilidad.")
    return zona_actual, f"COMPRAR ZONA {zona_actual}{pauta_txt}", motivo, 0.0, 0.0, zona_actual, tramo_actual_eur

def evaluar_venta_cava(d, reglas):
    ds = d["dist_sma"]
    rsi = d["rsi"]
    es_spot = not reglas["es_fondo"]
    
    # Mensaje específico para Spot (Oro / Bitcoin) vs Fondos
    if es_spot:
        msg_z3 = "Extremo sobrecalentamiento macro. Vender del 50% al 80% de la posición a Euros / Efectivo para asegurar plusvalías históricas."
        msg_z2 = "Fuerte tensión alcista. Recoger beneficios parciales vendiendo el 30% de la posición a cuenta de efectivo."
        msg_z1 = "Tensión alcista en madurez. Frenar compras adicionales y vigilar divergencias de RSI."
    else:
        msg_z3 = f"Extremo sobrecalentamiento. Traspasar entre 60% y 100% al Fondo Monetario {NOMBRE_MONETARIO_NODRIZA} (0 € peaje fiscal)."
        msg_z2 = f"Fuerte tensión alcista. Traspasar el 30% de la posición al Fondo Monetario {NOMBRE_MONETARIO_NODRIZA} (0 € peaje fiscal)."
        msg_z1 = "Tensión alcista inicial. Frenar nuevas compras y vigilar soporte de medias."
        
    if ds >= reglas["v3"] and rsi >= reglas["rsi_v3"]:
        return 3, "VENTA ZONA 3 (RECOGIDA TOTAL)", msg_z3
    if ds >= reglas["v2"] and rsi >= reglas["rsi_v2"]:
        return 2, "VENTA ZONA 2 (RECOGIDA PARCIAL)", msg_z2
    if ds >= reglas["v1"] and rsi >= reglas["rsi_v1"]:
        return 1, "VENTA ZONA 1 (VIGILANCIA)", msg_z1
    return 0, "MANTENER", "Parámetros técnicos sanos. Mantener posición."

def estado_hora_corte(hora_limite):
    ahora = datetime.now()
    if ahora.weekday() >= 5:
        return f"⏸️ Fin de semana (Corte L-V {hora_limite:02d}:00h)", False
    if ahora.hour < hora_limite:
        restante_min = (hora_limite - 1 - ahora.hour) * 60 + (60 - ahora.minute)
        horas_r = restante_min // 60
        mins_r = restante_min % 60
        return f"🟢 EN HORA HOY (Corte {hora_limite:02d}:00h — quedan {horas_r}h {mins_r}m)", True
    return f"🟠 PASA A MAÑANA (Superado corte {hora_limite:02d}:00h)", False

# ==================== CABECERA PRINCIPAL ====================
st.title("🦈 Radar Tiburón Cava Pro — Asignación 60.000 €")

v_info = get_vix_data()

c_m1, c_m2, c_m3, c_m4 = st.columns(4)
c_m1.info(f"🏛️ **Ciclo Presidencial:**\n{get_ciclo_presidencial()}")
c_m2.warning(f"📅 **Estacionalidad:**\n{get_estacionalidad()}")
c_m3.metric("VIX Actual", f"{v_info['actual']:.2f}", f"{v_info['tension']:+.1%} vs SMA10 ({v_info['sma10']:.1f})")
c_m4.success(f"🛡️ **Colchón Fuera:**\n{COLCHON_EMERGENCIAS:,.0f} € (Trade Republic / MyInvestor)")

# Barra lateral
st.sidebar.header("💼 Arquitectura de Cartera")
st.sidebar.markdown(f"**Capital Radar:** `{CAPITAL_RADAR:,.0f} €`")
st.sidebar.markdown(f"**Búnker AXA ({ISIN_MONETARIO_NODRIZA}):** `{CAPITAL_RADAR * LIQUIDEZ_MONETARIO_PESO:,.0f} €` (25%)")
st.sidebar.markdown(f"**Colchón Emergencias:** `{COLCHON_EMERGENCIAS:,.0f} €`")
st.sidebar.markdown("---")
ahora_str = datetime.now().strftime("%H:%M")
st.sidebar.markdown(f"⏰ **Hora actual (CET):** `{ahora_str}`")
st.sidebar.caption("Cortes MyInvestor: **10:00h** (AXA / iShares Europe) | **12:00h** (MyInvestor Nasdaq / Wellington / Vanguard / Pictet) | **14:00h** (Guinness) | **16:00h** (Fidelity S&P / World).")
st.sidebar.markdown("---")
st.sidebar.caption("Doctrina Cava: Comprar en tramos tras confirmación. Sin stops en fondos indexados; la liquidez en monetario es tu escudo protector.")

if st.sidebar.button("🔄 Forzar Datos en Vivo"):
    st.cache_data.clear()
    st.rerun()

# Pestañas principales (5 pestañas con la nueva central de Fondos MyInvestor)
tab_senales, tab_fondos_my, tab_flujo, tab_dow, tab_guia = st.tabs([
    "🎯 Semáforo y Tramos",
    "🏦 Fondos MyInvestor (Traspasos & Refugios)",
    "🏛️ Rayos X de Flujo",
    "📰 Diario (Teoría de Dow)",
    "📖 Manual Operativo Cava"
])

# ==================== PESTAÑA 1: SEÑALES Y TRAMOS ====================
with tab_senales:
    st.subheader("Semáforo Cuantitativo Institucional")
    
    for nombre, reglas in ASIGNACION.items():
        d = get_market_data(reglas["ticker"])
        if not d:
            st.error(f"Error conectando con los datos de {nombre}")
            continue
            
        cap_posicion = CAPITAL_RADAR * reglas["peso"]
        tramo_1 = cap_posicion * 0.30
        tramo_2 = cap_posicion * 0.30
        tramo_3 = cap_posicion * 0.40

        zona_c, estado_c, motivo_c, dist_target, precio_target, target_zona, target_eur = evaluar_motor_cava(
            d, reglas, v_info, reglas["ticker"], cap_posicion
        )
        zona_v, estado_v, motivo_v = evaluar_venta_cava(d, reglas)
        
        if "COMPRAR" in estado_c: icon_c = "🟢"
        elif "BLOQUEADO" in estado_c: icon_c = "🛡️"
        elif zona_v > 0: icon_c = "🟡"
        else: icon_c = "⚪"
        
        badge_op = f"⏱️ TRASPASO FONDO (Corte {reglas['hora_corte']}:00h)" if reglas["es_fondo"] else "⚡ INMEDIATO (Spot)"
        
        with st.expander(f"{icon_c} **{nombre}** | {badge_op} | Compra: **{estado_c}** | Venta: **{estado_v}**", expanded=True):
            m1, m2, m3, m4, m5 = st.columns(5)
            m1.metric("Precio Spot", f"{d['precio']:,.2f} $")
            m2.metric("Descuento (ATH)", f"{d['caida']:.2%}")
            m3.metric("Línea Vital (SMA200)", f"{d['sma200']:,.2f} $", f"{d['dist_sma']:+.2%}")
            m4.metric("MACD Semanal", "ALCISTA" if d['macd_alcista'] else "BAJISTA", "Sobre 0" if d['macd_cero'] else "Bajo 0")
            m5.metric("Estocástico (14w)", f"{d['stoch_k']:.1f}", "La Bonita" if d['la_bonita'] else "Neutro")
            
            txt_corte, en_hora = estado_hora_corte(reglas["hora_corte"])
            st.markdown(f"**Vehículo:** `{reglas['vehiculo']}` en **{reglas['plataforma']}** (Asignación total: **{cap_posicion:,.0f} €** | Ventana hoy: **{txt_corte}**)")

            # ==================== SECCIÓN 1: PÓLVORA TÁCTICA (TRAMOS DE CAPITAL) ====================
            st.markdown("---")
            st.markdown(f"#### 🎯 Despliegue Táctico por Tramos — {nombre}")
            
            # --- EVALUACIÓN DE COMPRA ---
            if estado_c == "ESPERAR":
                st.info(f"⏳ **{motivo_c}**")
                progreso = max(0.0, min(1.0, 1.0 - (dist_target / abs(reglas['c1']))))
                st.progress(progreso, text=f"Proximidad a ZONA {target_zona} (Tramo {target_zona} = {target_eur:,.0f} €): Falta un {dist_target:.2%}")
            elif "BLOQUEADO" in estado_c:
                st.warning(f"#### 🛡️ {estado_c}\n{motivo_c}")
                st.markdown(f"""
                - **Tramo Táctico Retenido:** `{target_eur:,.0f} €` asignados a **Zona {target_zona}**.
                - **Protocolo Cava:** La munición permanece en el Fondo Monetario `{NOMBRE_MONETARIO_NODRIZA}` o cuenta remunerada hasta que el VIX supere 20 o se confirme quiebre de estructura (BOS).
                """)
            elif "COMPRAR" in estado_c:
                st.success(f"#### 🎯 {estado_c}\n{motivo_c}")
                st.markdown(f"""
                - **Tramo a Ejecutar AHORA:** `{target_eur:,.0f} €` (Zona {target_zona})
                - **Vehículo de Destino:** `{reglas['vehiculo']}` en **{reglas['plataforma']}**
                - **Procedimiento:** Si es fondo (MyInvestor), ordenar traspaso desde el Monetario `{NOMBRE_MONETARIO_NODRIZA}` antes de las **{reglas['hora_corte']}:00h CET** (recuerda que AXA corta a las 10:00h). Si es spot, comprar a mercado.
                - **Munición Restante en Reserva:** `{cap_posicion - target_eur:,.0f} €` para siguientes tramos.
                """)
                
            # --- EVALUACIÓN DE VENTA / TRASPASO AL MONETARIO ---
            if zona_v > 0:
                st.warning(f"#### ⚠️ {estado_v}\n{motivo_v}")
                if reglas["es_fondo"]:
                    st.markdown(f"👉 **Acción Recomendada:** Ordenar **traspaso hacia el Fondo Monetario** `{NOMBRE_MONETARIO_NODRIZA}` en MyInvestor para blindar plusvalías con 0 € de IRPF.")
                else:
                    st.markdown(f"""
                    👉 **Acción Recomendada ({nombre}):** En activos al contado (Spot), **se recogen beneficios vendiendo a cuenta de efectivo** (o stablecoin respaldada en euros).
                    - **¿Por qué NO stop loss aquí?:** Un stop loss automático en exchange es barrido por mechas de volatilidad y te obliga a tributar por FIFO. La toma de beneficios se ejecuta en tramos cuando el radar alcanza estas zonas de sobreextensión.
                    - **Impacto Fiscal:** Plusvalía tributa en la base del ahorro (19% a 28%).
                    """)

            st.caption(f"Estructura Táctica de Tramos: Tramo 1 (30%): {tramo_1:,.0f} € | Tramo 2 (30%): {tramo_2:,.0f} € | Tramo 3 (40%): {tramo_3:,.0f} €")

            # ==================== SECCIÓN 2: SEMÁFORO DCA MENSUAL (AHORRO PERIÓDICO) ====================
            st.markdown("---")
            st.markdown("#### 🚦 Semáforo DCA Mensual (Ahorro Periódico Sistemático)")
            
            if d['stoch_k'] > 80:
                color_dca = "🔴"
                border_color = "#ef4444"
                bg_color = "#371515"
                text_color = "#f87171"
                accion_dca = "APORTACIÓN MÍNIMA DE CALENDARIO (SIN EXTRAS)"
                mensaje_dca = "SOBRECOMPRA EXTREMA (%K > 80). Si tu disciplina exige aportar este mes, haz tu cuota normal fija de calendario, pero queda TERMINANTEMENTEMENTE PROHIBIDO gastar pólvora extra o adelantar aportaciones. El mercado está extendido."
            elif d['la_bonita']:
                color_dca = "🟢"
                border_color = "#22c55e"
                bg_color = "#143320"
                text_color = "#4ade80"
                accion_dca = "¡LA BONITA CONFIRMADA! (ADELANTAR DCA + TRAMO EXTRA)"
                mensaje_dca = "MÁXIMA PROBABILIDAD ESTADÍSTICA (Cava, Cap. V). El estocástico semanal ha cortado al alza saliendo de sobreventa con la tendencia de fondo alcista. Adelanta la aportación mensual e inyecta un tramo extra de munición."
            elif d['macd_alcista']:
                color_dca = "🟡"
                border_color = "#eab308"
                bg_color = "#332b14"
                text_color = "#facc15"
                accion_dca = "APORTACIÓN NORMAL DE CALENDARIO"
                mensaje_dca = "TENDENCIA MACRO ALCISTA SANA. El MACD semanal acompaña sin sobrecompra extrema. Ejecuta tu DCA mensual habitual sin modificar importes."
            else:
                color_dca = "🔴"
                border_color = "#f97316"
                bg_color = "#351e12"
                text_color = "#fb923c"
                accion_dca = "APORTACIÓN MÍNIMA (PRUDENCIA MACRO)"
                mensaje_dca = "TENDENCIA MACRO EN FASE CORRECTIVA. El MACD semanal no confirma impulso alcista. Realiza solo la aportación fija si tu sistema es automático, pero no comprometas reservas de liquidez."
            
            st.markdown(f"""
            <div class="card-dca" style="background-color: {bg_color}; border-color: {border_color};">
                <div style="font-weight: 700; font-size: 1.05rem; color: {text_color}; margin-bottom: 6px;">
                    {color_dca} {accion_dca}
                </div>
                <div style="color: #e5e7eb; font-size: 0.95rem; line-height: 1.45;">
                    {mensaje_dca}
                </div>
            </div>
            """, unsafe_allow_html=True)

            # ==================== AVISOS DE DISCIPLINA OPERATIVA CAVA ====================
            if color_dca == "🟢" and reglas["es_fondo"]:
                st.warning(f"⏱️ **RECORDATORIO OPERATIVO (FONDOS T+2):** Has recibido la señal de 'La Bonita'. Ordena el traspaso desde el Monetario `{NOMBRE_MONETARIO_NODRIZA}`. Recuerda que la orden se liquidará a D+1 o D+2. **No canceles la orden si el precio oscila**, estás comprando valor con diferimiento fiscal (Art. 94 LIRPF).")
            
            if color_dca == "🟢" and not reglas["es_fondo"]:
                st.info(f"🛡️ **GESTIÓN DE RIESGO PATRIMONIAL ({nombre.upper()}):** En activos Spot (Trade Republic / MyInvestor) **NO se colocan Stop Loss automáticos**. Tu seguridad es el dimensionamiento ({reglas['peso']:.0%} de cartera = {cap_posicion:,.0f} €) y entrar en tramos (30%/30%/40%). La salida se realiza exclusivamente cuando el radar marque Venta Zona 2 o 3 por sobreextensión.")

            st.caption(f"Lecturas de Soporte DCA: Estocástico %K: {d['stoch_k']:.1f} | %D: {d['stoch_d']:.1f} | MACD Alcista: {'Sí' if d['macd_alcista'] else 'No'} | Pauta Bonita: {'Sí' if d['la_bonita'] else 'No'}")

# ==================== PESTAÑA 2: FONDOS MYINVESTOR (TRASPASOS & REFUGIOS) ====================
with tab_fondos_my:
    st.subheader("🏦 Catálogo Maestro Auditado — Fondos Tradicionales Traspasables en MyInvestor")
    st.caption("Circuito cerrado con diferimiento fiscal (Art. 94 LIRPF): todas las entradas tácticas salen del AXA Trésor Court Terme y todas las recogidas de beneficios o rotaciones defensivas regresan sin tributar en el IRPF.")

    # --- 1. MONITOR EN VIVO DE HORAS DE CORTE (CUT-OFF CET) ---
    st.markdown("#### ⏰ Monitor de Ventanas de Corte en MyInvestor (Horario CET)")
    c_h1, c_h2, c_h3, c_h4 = st.columns(4)
    txt_10, _ = estado_hora_corte(10)
    txt_12, _ = estado_hora_corte(12)
    txt_14, _ = estado_hora_corte(14)
    txt_16, _ = estado_hora_corte(16)
    c_h1.metric("Corte 10:00 CET", "AXA / iShares Eur", txt_10)
    c_h2.metric("Corte 12:00 CET", "Nasdaq / Well. / Vang.", txt_12)
    c_h3.metric("Corte 14:00 CET", "Guinness Energy", txt_14)
    c_h4.metric("Corte 16:00 CET", "Fidelity S&P / World", txt_16)

    # --- 2. MOTOR AUTOMÁTICO DE ROTACIÓN EN CRISIS (DOCTRINA CAVA) ---
    st.markdown("---")
    st.markdown("#### 🧭 Brújula de Rotación Defensiva en Crisis (¿AXA Monetario o Rotación Sectorial?)")
    
    d_sp = get_market_data("^GSPC")
    d_ndx = get_market_data("^NDX")
    v_act = v_info["actual"]

    if d_sp and d_ndx:
        caida_sp = d_sp["caida"]
        caida_ndx = d_ndx["caida"]
        bajo_sma_sp = d_sp["dist_sma"] < 0
        bajo_sma_ndx = d_ndx["dist_sma"] < 0
        divergencia_ia = (caida_ndx - caida_sp) <= -0.05  # Nasdaq cae >5% más que el S&P 500

        if v_act >= 25.0 or (bajo_sma_sp and bajo_sma_ndx and v_act >= 20.0):
            st.error(
                f"🚨 **ALERTA DE PÁNICO DE LIQUIDEZ SISTÉMICA (VIX: {v_act:.1f}):** "
                f"En crisis de liquidez o estrés crediticio (CDS), el MSCI World, S&P 500 y Nasdaq caen al unísono. "
                f"**NO rotes a renta variable europea.** El único refugio real es traspasar hacia el búnker monetario "
                f"**AXA Trésor Court Terme (`FR0000447823`)** con 0,25% de volatilidad y esperar suelo en Zona 2/3."
            )
        elif divergencia_ia or (bajo_sma_ndx and not bajo_sma_sp):
            st.warning(
                f"🔄 **ROTACIÓN SECTORIAL / PINCHAZO DE MÚLTIPLOS IA (Nasdaq {caida_ndx:.1%} vs S&P {caida_sp:.1%} con VIX {v_act:.1f}):** "
                f"Corrección concentrada en megacaps tecnológicas sin colapso sistémico de liquidez. "
                f"Escenario óptimo para rotar tácticamente hacia Farmacia USA (**Wellington Global Health Care `IE00BF2ZVB54`**) "
                f"o Farmacia/Consumo Europeo Low-Cost (**iShares Europe Equity Index `LU0836512706`**)."
            )
        else:
            st.success(
                f"✅ **ESTRUCTURA PRIMARIA ESTABLE (S&P {caida_sp:.1%} | Nasdaq {caida_ndx:.1%} | VIX {v_act:.1f}):** "
                f"Sin pánico de liquidez ni rotura simultánea de medias de 200 sesiones. "
                f"Mantener núcleo en **Fidelity S&P 500 (`IE00BYX5MX67`)** / **Fidelity MSCI World (`IE00BYX5NX33`)** "
                f"y custodiar la pólvora táctica en **AXA Trésor (`FR0000447823`)** para disparar en soportes."
            )

    # --- 3. TABLA MAESTRA DE LOS 9 FONDOS AUDITADOS (DATOS NETOS MORNINGSTAR / DFI) ---
    st.markdown("---")
    st.markdown("#### 📊 Auditoría de Calidad, Rentabilidad Neta (Gastos Incluidos) y Riesgo (Fichas Morningstar)")
    
    df_tabla = pd.DataFrame([
        {
            "Bloque Táctico": f["bloque"],
            "Fondo de Inversión": f["nombre"],
            "ISIN (Copiar)": f["isin"],
            "Corte CET": f"{f['hora_corte']:02d}:00 h",
            "TER Neto": f["ter"],
            "2026": f["r_2026"],
            "1 Año": f["r_1a"],
            "3 Años (Anual.)": f["r_3a"],
            "5 Años (Anual.)": f["r_5a"],
            "Volatilidad 3A": f["vol_3a"],
            "Sharpe 3A": f"{f['sharpe_3a']:.2f}",
            "Rating": f["rating"],
            "Veredicto": f["estado_calidad"]
        }
        for f in CATALOGO_FONDOS_MY
    ])
    st.dataframe(df_tabla, use_container_width=True, hide_index=True)

    # --- 4. FICHAS DETALLADAS Y BUSCADOR RÁPIDO DE ISIN PARA MYINVESTOR ---
    st.markdown("#### 🔍 Radiografía Individual de Cartera y Reglas de Traspaso por Fondo")
    col_f1, col_f2 = st.columns(2)
    for idx, f in enumerate(CATALOGO_FONDOS_MY):
        target_col = col_f1 if idx % 2 == 0 else col_f2
        with target_col:
            txt_c, _ = estado_hora_corte(f["hora_corte"])
            with st.expander(f"{f['estado_calidad']} | **{f['nombre']}** (`{f['isin']}`)", expanded=False):
                st.markdown(f"- **Código ISIN (pegar en lupa MyInvestor):** `{f['isin']}`")
                st.markdown(f"- **Bloque en el Radar:** {f['bloque']} | **Hora de corte:** `{f['hora_corte']:02d}:00 CET` ({txt_c})")
                st.markdown(f"- **Coste (TER) descontado en VL:** `{f['ter']}` | **Ratio Sharpe (3A):** `{f['sharpe_3a']:.2f}` | **Volatilidad (3A):** `{f['vol_3a']}`")
                st.markdown(f"- **Rentabilidades Netas:** 2026: `{f['r_2026']}` | 1 Año: `{f['r_1a']}` | 3 Años: `{f['r_3a']}` | 5 Años: `{f['r_5a']}`")
                st.markdown(f"- **Principales Posiciones:** {f['top_holdings']}")
                st.markdown(f"- **Función Estratégica Cava:** {f['rol_radar']}")

    # --- 5. COMPARATIVA DE EFICIENCIA: TU RADAR DIRECTO VS. CARTERA INDIE ROBOADVISOR ---
    st.markdown("---")
    st.markdown("#### 🛡️ Auditoría de Costes y Eficiencia: Tu Cartera Directa vs. Cartera Indie (Roboadvisor MyInvestor)")
    c_ef1, c_ef2, c_ef3 = st.columns(3)
    ter_ponderado_radar = (0.40 * 0.0006) + (0.15 * 0.0038) + (0.15 * 0.0012) + (0.25 * 0.0005)
    coste_anual_radar = CAPITAL_RADAR * ter_ponderado_radar
    coste_anual_indie = CAPITAL_RADAR * 0.0041
    ahorro_anual = coste_anual_indie - coste_anual_radar

    c_ef1.metric("Coste Anual Tu Radar (60.000 €)", f"{coste_anual_radar:.2f} € / año", f"TER medio: {ter_ponderado_radar*100:.3f}% (0% gestión/custodia)")
    c_ef2.metric("Coste Cartera Indie (0,41%)", f"{coste_anual_indie:.2f} € / año", "+0,30% extra de gestión y custodia Inversis", delta_color="inverse")
    c_ef3.metric("Ahorro Neto Directo", f"+{ahorro_anual:.2f} € / año", "Sin riesgo de bonos a +20 años (0,01 dur. en AXA)")

    st.info(
        "💡 **Nota sobre Oro Físico (`IE00B4ND3602`) vs. Xetra-Gold (`DE000A0S9GB0`):** "
        "El ETC **iShares Physical Gold (`IE00B4ND3602`)** cobra un **0,12% anual todo incluido** dentro del valor liquidativo (10,80 €/año sobre 9.000 €), "
        "mientras que Xetra-Gold arrastra un coste de custodia en Clearstream del ~0,30%-0,36% anual y carece de exención fiscal en España."
    )

# ==================== PESTAÑA 3: RAYOS X INSTITUCIONAL ====================
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

# ==================== PESTAÑA 4: TEORÍA DE DOW ====================
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

# ==================== PESTAÑA 5: GUÍA OPERATIVA CAVA ====================
with tab_guia:
    st.markdown(f"""
    ### Principios Rectores de José Luis Cava (*El Arte de Especular*)
    
    1. **Comprar tras la confirmación, nunca en caída libre:**
       - El aficionado intenta comprar el mínimo exacto y suele comprar un cuchillo.
       - El profesional espera a que el mercado frene, absorba la oferta y confirme un quiebre de estructura (BOS).
       
    2. **El Escudo de la Liquidez en Tramos (30% / 30% / 40%):**
       - **Tramo 1 (30%):** En el pullback inicial (Zona 1), para no perder el tren si rebota rápido.
       - **Tramo 2 (30%):** En el soporte mayor de la media de 200 sesiones (Zona 2).
       - **Tramo 3 (40%):** En capitulaciones con pánico extremo o roturas de suelo con gran volumen.
       
    3. **¿Stop Loss en Bitcoin y Oro Spot? NUNCA:**
       - Colocar un stop automático en el exchange/broker regala tus participaciones a los creadores de mercado en barridas de volatilidad y te fuerza a tributar en el IRPF (19%-28%).
       - Tu stop loss es el **dimensionamiento patrimonial**: 5% en Bitcoin (3.000 €) y 15% en Oro (9.000 € en `IE00B4ND3602`), respaldados por 10.000 € en colchón y 15.000 € en monetario.
       
    4. **Protocolo de Rotación en Crisis (Fondos Tradicionales en MyInvestor):**
       - **Pánico sistémico de liquidez / VIX > 25:** Cuando caen a la vez el MSCI World, el S&P 500 y el Nasdaq por drenaje de liquidez o tensión en CDS, se traspasa al búnker monetario **AXA Trésor Court Terme (`{ISIN_MONETARIO_NODRIZA}`)** con volatilidad del 0,25%.
       - **Ajuste sectorial de múltiplos en IA (sin recesión general):** Cuando el dinero institucional huye de las tecnológicas caras hacia sectores de demanda inelástica, se rota sin peaje fiscal hacia **Wellington Global Health Care (`IE00BF2ZVB54`)** (80% farmacia EE. UU.: Eli Lilly, Merck, AbbVie) o **iShares Europe Equity Index (`LU0836512706`)** (Novo Nordisk, Novartis, Roche, Nestlé con 0,12% TER).
       - **Shock de oferta energética / inflación geopolítica:** Cobertura táctica acotada (5%-10%) mediante **Guinness Global Energy (`IE00B3CCJB88`)**.
       - **Recesión deflacionaria con recortes de tipos:** Activar duración mediante **Vanguard Global Bond Index EUR Hedged (`IE00B18GC888`)**.
       
    5. **El Diferimiento Fiscal del Art. 94 LIRPF en España:**
       - Para el S&P 500 (`IE00BYX5MX67`), MSCI World (`IE00BYX5NX33`) y Nasdaq 100 (`ES0165265002`), la recogida de beneficios y las entradas por tramos se ejecutan vía **traspaso interno desde/hacia el Fondo Monetario AXA (`{ISIN_MONETARIO_NODRIZA}`)**. Tus ganancias quedan protegidas y el interés compuesto sigue trabajando con 0 € de tributación inmediata.
    """)
