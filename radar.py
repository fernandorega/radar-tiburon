import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import json
import os
import smtplib
import requests
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
import plotly.graph_objects as go

st.set_page_config(page_title="🦈 Radar Tiburón Pro (Cartera Cava)", page_icon="🦈", layout="wide")

st.markdown("""
<style>
    .stAlert { border-radius: 8px; font-weight: 500; }
    div[data-testid="stMetricValue"] { font-size: 1.6rem; }
</style>
""", unsafe_allow_html=True)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
F_ALERTAS = os.path.join(BASE_DIR, "config_alertas.json")

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

# ==================== CONFIGURACIÓN DE TU CARTERA (CAVA) ====================
# Basado en 61.100€ (60.000 + 1.100 del fondo actual)
CAPITAL_TOTAL = 61100
ASIGNACION = {
    "S&P 500": {"ticker": "^GSPC", "peso": 0.40, "vehiculo": "Fondo Indexado", "c1": -0.04, "c2": -0.10, "c3": -0.20, "v1": 0.15, "v2": 0.30, "v3": 0.40, "rsi_v1": 70, "rsi_v2": 75, "rsi_v3": 80},
    "MSCI World": {"ticker": "URTH", "peso": 0.20, "vehiculo": "Fondo Indexado", "c1": -0.04, "c2": -0.09, "c3": -0.18, "v1": 0.12, "v2": 0.25, "v3": 0.35, "rsi_v1": 70, "rsi_v2": 75, "rsi_v3": 80},
    "Oro": {"ticker": "GC=F", "peso": 0.15, "vehiculo": "ETC 4GLD (o físico)", "c1": -0.04, "c2": -0.08, "c3": -0.12, "v1": 0.12, "v2": 0.22, "v3": 0.25, "rsi_v1": 70, "rsi_v2": 75, "rsi_v3": 80},
    "NASDAQ 100": {"ticker": "^NDX", "peso": 0.10, "vehiculo": "ETF QQQ", "c1": -0.06, "c2": -0.15, "c3": -0.25, "v1": 0.18, "v2": 0.35, "v3": 0.45, "rsi_v1": 70, "rsi_v2": 75, "rsi_v3": 80},
    "Bitcoin": {"ticker": "BTC-USD", "peso": 0.05, "vehiculo": "ETF IBIT / ETP", "c1": -0.15, "c2": -0.30, "c3": -0.50, "v1": 0.30, "v2": 0.60, "v3": 1.00, "rsi_v1": 75, "rsi_v2": 80, "rsi_v3": 85},
}
LIQUIDEZ_PESO = 0.10 # 10% en Fondo Monetario

st.sidebar.header("🛡️ Gestión de Capital")
st.sidebar.markdown(f"**Capital Total:** {CAPITAL_TOTAL:,.0f} €")
st.sidebar.markdown(f"**Liquidez Táctica (10%):** {CAPITAL_TOTAL * LIQUIDEZ_PESO:,.0f} € en Fondo Monetario")
st.sidebar.info("Regla de oro: Arriesga máximo el 1-2% de tu capital por operación. Usa el Stop Loss calculado por ATR.")

def get_ciclo_presidencial():
    year = datetime.now().year
    ciclo = (year - 2024) % 4 
    if ciclo == 0: return "Año de Elecciones (Históricamente Alcista)"
    elif ciclo == 1: return "Año Post-Elecciones (Históricamente Mixto)"
    elif ciclo == 2: return "Año de Midterms (Históricamente Bajista - ¡Ojo!)"
    else: return "Año Pre-Electoral (¡Históricamente muy Alcista!)"

def get_estacionalidad():
    mes = datetime.now().month
    if mes == 10: return "Octubre: El mes de los grandes suelos."
    elif mes in [11, 12, 1]: return "Nov-Ene: Fuerte viento de cola estacional."
    elif mes in [5, 6, 7, 8, 9]: return "Mayo-Septiembre: 'Sell in May'. Viento en contra."
    else: return "Febrero-Abril: Transición."

@st.cache_data(ttl=60)
def vix():
    try: return float(yf.Ticker("^VIX").history(period="5d")['Close'].iloc[-1])
    except: return 18.0

@st.cache_data(ttl=300)
def datos(ticker):
    try:
        h = yf.Ticker(ticker).history(period="2y")
        if len(h) < 200: return None
        dias_lookback = 365 if ("BTC" in ticker or "ETH" in ticker) else 252
        h52 = h.iloc[-dias_lookback:].copy() if len(h) >= dias_lookback else h.copy()
        p = float(h52['Close'].iloc[-1])
        mx = float(h52['High'].max())
        caida = (p/mx - 1) if mx > 0 else 0.0
        sma200 = float(h['Close'].rolling(200).mean().iloc[-1])
        dist_sma = (p/sma200 - 1) if sma200 > 0 else 0.0
        
        delta = h52['Close'].diff()
        g = delta.clip(lower=0).ewm(alpha=1/14, adjust=False).mean()
        l = -delta.clip(upper=0).ewm(alpha=1/14, adjust=False).mean()
        rsi = float((100 - 100/(1 + g/l.replace(0,1e-9))).iloc[-1])
        
        tr = pd.concat([h['High'] - h['Low'], (h['High'] - h['Close'].shift()).abs(), (h['Low'] - h['Close'].shift()).abs()], axis=1).max(axis=1)
        atr = float(tr.ewm(alpha=1/14, adjust=False).mean().iloc[-1])
        
        h_week = h.resample('W').agg({'Open': 'first', 'High': 'max', 'Low': 'min', 'Close': 'last', 'Volume': 'sum'}).dropna()
        exp1 = h_week['Close'].ewm(span=12, adjust=False).mean()
        exp2 = h_week['Close'].ewm(span=26, adjust=False).mean()
        macd_line = exp1 - exp2
        signal_line = macd_line.ewm(span=9, adjust=False).mean()
        macd_alcista = bool((macd_line.iloc[-1] > signal_line.iloc[-1]) and (macd_line.iloc[-1] > 0))

        max_10d_prev = h52['High'].shift(1).rolling(10).max().iloc[-1]
        bos = bool(p > max_10d_prev) if not pd.isna(max_10d_prev) else False
        
        return {
            "precio": p, "caida": caida, "sma200": sma200, "dist_sma": dist_sma,
            "rsi": rsi if not pd.isna(rsi) else 50.0, "atr": atr, "macd_alcista": macd_alcista, "bos": bos, "hist": h
        }
    except: return None

def decidir_compra(d, reglas, v):
    caida = d["caida"]
    if caida <= reglas["c3"]: zona = 3
    elif caida <= reglas["c2"]: zona = 2
    elif caida <= reglas["c1"]: zona = 1
    else: return 0, "ESPERAR"
    
    if zona == 3 and v < 20.0: return 0, "BLOQUEADO VIX"
    if not d["macd_alcista"]: return 0, "BLOQUEADO MACD"
    if zona >= 2 and not d["bos"] and v < 25: return 0, "BLOQUEADO BOS"
    return zona, f"COMPRAR ZONA {zona}"

st.title("🦈 Radar Cartera Cava (61.100€)")

col1, col2, col3 = st.columns([2, 2, 1])
with col1: st.info(f"🏛️ **Ciclo:** {get_ciclo_presidencial()}")
with col2: st.warning(f"📅 **Estacionalidad:** {get_estacionalidad()}")
with col3: st.metric("VIX", f"{vix():.2f}")

v = vix()

for cat, reglas in ASIGNACION.items():
    d = datos(reglas["ticker"])
    if not d: continue
    
    zona, dec = decidir_compra(d, reglas, v)
    importe_asignado = CAPITAL_TOTAL * reglas["peso"]
    importe_liquidez = CAPITAL_TOTAL * LIQUIDEZ_PESO
    
    with st.expander(f"**{cat}** | Peso: {reglas['peso']:.0%} ({importe_asignado:,.0f}€) | Vehículo: {reglas['vehiculo']} | {dec}"):
        c1, c2, c3 = st.columns(3)
        c1.metric("Precio", f"{d['precio']:,.2f}")
        c2.metric("Caída 52w", f"{d['caida']:.2%}")
        c3.metric("MACD Semanal", "ALCISTA" if d['macd_alcista'] else "BAJISTA")
        
        if zona > 0:
            # Calcular tramo de entrada
            if zona == 1: pct_tramo = 0.30
            elif zona == 2: pct_tramo = 0.30
            else: pct_tramo = 0.40
            
            importe_tramo = importe_asignado * pct_tramo
            stop_loss = d['precio'] - (2 * d['atr'])
            riesgo_por_unidad = d['precio'] - stop_loss
            unidades = int((importe_tramo * 0.02) / riesgo_por_unidad) if riesgo_por_unidad > 0 else 0
            
            st.success(f"### {dec}")
            st.markdown(f"""
            - **Invertir ahora:** `{importe_tramo:,.0f} €` ({pct_tramo:.0%} del peso asignado)
            - **Stop Loss (2x ATR):** `{stop_loss:,.2f}`
            - **Riesgo por unidad:** `{riesgo_por_unidad:,.2f}`
            - **Unidades sugeridas (riesgo 2%):** `{unidades}`
            """)
        elif "BLOQUEADO" in dec:
            st.error(f"🛡️ {dec}. El radar te protege de comprar contra la tendencia macro o sin pánico.")
        else:
            st.info("⏳ Esperando señal de compra. Mantén la liquidez en el Fondo Monetario.")
