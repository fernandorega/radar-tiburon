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
    page_title="🦈 Radar Tiburón Cava Pro — Roboadvisor & 3 Dianas",
    page_icon="🦈",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Estilos CSS de diseño profesional de alto contraste
st.markdown("""
<style>
    .stAlert { border-radius: 8px; font-weight: 500; }
    div[data-testid="stMetricValue"] { font-size: 1.35rem; font-weight: 700; }
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
    .card-orden {
        background-color: #0f172a;
        border: 1px solid #1e293b;
        border-left: 6px solid #3b82f6;
        padding: 16px;
        border-radius: 10px;
        margin-bottom: 12px;
    }
</style>
""", unsafe_allow_html=True)

# ==================== RUTAS Y PERSISTENCIA JSON ====================
BASE_DIR = os.path.dirname(os.path.abspath(__file__)) if "__file__" in locals() else "."
F_SALDOS = os.path.join(BASE_DIR, "saldos_cartera_cava.json")

def cargar_json(p, d):
    if os.path.exists(p):
        try:
            with open(p, "r", encoding="utf-8") as f:
                data = json.load(f)
                for k, v in d.items():
                    if k not in data:
                        data[k] = v
                return data
        except Exception:
            return d
    return d

def guardar_json(p, d):
    try:
        with open(p, "w", encoding="utf-8") as f:
            json.dump(d, f, indent=4, ensure_ascii=False)
        return True
    except Exception:
        return False

# ==================== CONFIGURACIÓN PATRIMONIAL MAESTRA ====================
CAPITAL_RADAR_DEFAULT = 60000.0
COLCHON_EMERGENCIAS_DEFAULT = 10000.0
DCA_MENSUAL_DEFAULT = 1000.0

ISIN_MONETARIO_NODRIZA = "FR0000447823"
NOMBRE_MONETARIO_NODRIZA = "AXA Trésor Court Terme C (FR0000447823)"

# Catálogo unificado de los 11 vehículos (9 Fondos MyInvestor + Oro + BTC) con Semáforos y Tramos
ACTIVOS_RADAR = {
    # --- BLOQUE 1: FONDOS TRADICIONALES MYINVESTOR (DIANA 1) ---
    "AXA Trésor Court Terme C": {
        "diana": "FONDOS", "bloque": "Búnker / Pólvora Seca",
        "ticker": "^IRX", "es_monetario": True, "es_fondo": True,
        "isin": "FR0000447823", "hora_corte": 10, "ter": "0,05%",
        "vehiculo": "AXA Trésor Court Terme C (FR0000447823)", "plataforma": "MyInvestor",
        "peso_obj": 0.25, "saldo_default": 15000.0,
        "c1": -0.01, "c2": -0.02, "c3": -0.03,
        "v1": 0.10, "v2": 0.20, "v3": 0.30, "rsi_v1": 80, "rsi_v2": 85, "rsi_v3": 90,
        "r_2026": "+1,67%", "r_1a": "+2,25%", "r_3a": "+2,95%", "r_5a": "+2,28%",
        "vol_3a": "0,25%", "sharpe_3a": 3.74, "rating": "Monetario (€STR)",
        "top_holdings": "Deuda soberana Francia/España y depósitos €STR (< 60 días)",
        "rol_radar": "Base nodriza (€STR). Custodia la pólvora seca con 0% volatilidad y financia todos los tramos sin peaje fiscal."
    },
    "Fidelity S&P 500 Index P": {
        "diana": "FONDOS", "bloque": "Core USA (Crecimiento)",
        "ticker": "^GSPC", "es_monetario": False, "es_fondo": True,
        "isin": "IE00BYX5MX67", "hora_corte": 16, "ter": "0,06%",
        "vehiculo": "Fidelity S&P 500 Index P EUR Acc (IE00BYX5MX67)", "plataforma": "MyInvestor",
        "peso_obj": 0.25, "saldo_default": 15000.0,
        "c1": -0.04, "c2": -0.10, "c3": -0.20,
        "v1": 0.15, "v2": 0.25, "v3": 0.35, "rsi_v1": 70, "rsi_v2": 75, "rsi_v3": 80,
        "r_2026": "+16,24%", "r_1a": "+17,99%", "r_3a": "+22,17%", "r_5a": "+12,79%",
        "vol_3a": "12,84%", "sharpe_3a": 1.25, "rating": "★★★★",
        "top_holdings": "NVIDIA (7,7%), Apple (7,6%), Microsoft (5,9%), Amazon (3,6%), Alphabet",
        "rol_radar": "Motor principal de Wall Street. Recibe tramos en soportes clave y aportaciones periódicas DCA."
    },
    "Fidelity MSCI World Index P": {
        "diana": "FONDOS", "bloque": "Diversificación Core Global",
        "ticker": "URTH", "es_monetario": False, "es_fondo": True,
        "isin": "IE00BYX5NX33", "hora_corte": 16, "ter": "0,12%",
        "vehiculo": "Fidelity MSCI World Index P EUR Acc (IE00BYX5NX33)", "plataforma": "MyInvestor",
        "peso_obj": 0.10, "saldo_default": 6000.0,
        "c1": -0.04, "c2": -0.10, "c3": -0.18,
        "v1": 0.14, "v2": 0.22, "v3": 0.32, "rsi_v1": 70, "rsi_v2": 75, "rsi_v3": 80,
        "r_2026": "+15,54%", "r_1a": "+17,91%", "r_3a": "+21,17%", "r_5a": "+11,61%",
        "vol_3a": "11,43%", "sharpe_3a": 1.31, "rating": "★★★★",
        "top_holdings": "72,9% EE. UU., 15,3% Europa, 5,7% Japón, 3,4% Canadá (1.247 empresas)",
        "rol_radar": "Mayor Ratio Sharpe (1,31). Diversifica el Core global reduciendo la concentración exclusiva en EE. UU."
    },
    "MyInvestor Nasdaq 100 FI": {
        "diana": "FONDOS", "bloque": "Satélite Tech (IA)",
        "ticker": "^NDX", "es_monetario": False, "es_fondo": True,
        "isin": "ES0165265002", "hora_corte": 12, "ter": "0,38%",
        "vehiculo": "MyInvestor Nasdaq 100 FI (ES0165265002)", "plataforma": "MyInvestor",
        "peso_obj": 0.10, "saldo_default": 6000.0,
        "c1": -0.06, "c2": -0.15, "c3": -0.25,
        "v1": 0.18, "v2": 0.30, "v3": 0.45, "rsi_v1": 70, "rsi_v2": 75, "rsi_v3": 80,
        "r_2026": "+23,88%", "r_1a": "+19,53%", "r_3a": "+24,86%", "r_5a": "+10,31%",
        "vol_3a": "18,85%", "sharpe_3a": 1.09, "rating": "★★★",
        "top_holdings": "Réplica Nasdaq 100 Net Total Return EUR (60,3% Tecnología, 12,6% Comunicación)",
        "rol_radar": "Vehículo táctico para disparar los tramos de Zona 1 y Zona 2 de sobreventa tecnológica sin tributar."
    },
    "iShares Europe Equity Index A2": {
        "diana": "FONDOS", "bloque": "Refugio Europa Low-Cost",
        "ticker": "VGK", "es_monetario": False, "es_fondo": True,
        "isin": "LU0836512706", "hora_corte": 10, "ter": "0,12% (0,54% GC)",
        "vehiculo": "iShares Europe Equity Index A2 EUR (LU0836512706)", "plataforma": "MyInvestor",
        "peso_obj": 0.03, "saldo_default": 1800.0,
        "c1": -0.04, "c2": -0.09, "c3": -0.16,
        "v1": 0.12, "v2": 0.20, "v3": 0.28, "rsi_v1": 68, "rsi_v2": 73, "rsi_v3": 78,
        "r_2026": "+10,26%", "r_1a": "+16,13%", "r_3a": "+17,16%", "r_5a": "+9,30%",
        "vol_3a": "10,70%", "sharpe_3a": 1.06, "rating": "★★★★",
        "top_holdings": "ASML (5,1%), HSBC (2,5%), Roche (2,1%), Shell (2,0%), Novartis (1,9%), AstraZeneca, Nestlé",
        "rol_radar": "Rotación defensiva hacia Farmacia y Consumo europeo a bajo múltiplo cuando pinchan múltiplos de IA en EE. UU."
    },
    "Wellington Global Health Care D": {
        "diana": "FONDOS", "bloque": "Refugio Salud / Pharma USA",
        "ticker": "XLV", "es_monetario": False, "es_fondo": True,
        "isin": "IE00BF2ZVB54", "hora_corte": 12, "ter": "1,74%",
        "vehiculo": "Wellington Global Health Care D EUR Acc (IE00BF2ZVB54)", "plataforma": "MyInvestor",
        "peso_obj": 0.03, "saldo_default": 1800.0,
        "c1": -0.04, "c2": -0.09, "c3": -0.16,
        "v1": 0.14, "v2": 0.22, "v3": 0.30, "rsi_v1": 70, "rsi_v2": 75, "rsi_v3": 80,
        "r_2026": "+9,81%", "r_1a": "+28,44%", "r_3a": "+12,08%", "r_5a": "+4,26%",
        "vol_3a": "14,77%", "sharpe_3a": 0.36, "rating": "★★★",
        "top_holdings": "80,2% EE. UU.: Eli Lilly (9,3%), Merck (5,5%), J&J (5,0%), AstraZeneca (4,0%), UnitedHealth, AbbVie",
        "rol_radar": "Refugio de farmacia estadounidense (tesis Cava) y biotecnología para rotación defensiva ante caídas del Nasdaq."
    },
    "Guinness Global Energy D EUR": {
        "diana": "FONDOS", "bloque": "Refugio Energía / Inflación",
        "ticker": "XLE", "es_monetario": False, "es_fondo": True,
        "isin": "IE00B3CCJB88", "hora_corte": 14, "ter": "1,27%",
        "vehiculo": "Guinness Global Energy D EUR Acc (IE00B3CCJB88)", "plataforma": "MyInvestor",
        "peso_obj": 0.02, "saldo_default": 1200.0,
        "c1": -0.06, "c2": -0.14, "c3": -0.24,
        "v1": 0.18, "v2": 0.28, "v3": 0.40, "rsi_v1": 70, "rsi_v2": 75, "rsi_v3": 80,
        "r_2026": "+42,98%", "r_1a": "+60,63%", "r_3a": "+17,17%", "r_5a": "+18,17%",
        "vol_3a": "20,60%", "sharpe_3a": 0.52, "rating": "★★",
        "top_holdings": "ExxonMobil (5,3%), Chevron (4,7%), Shell (4,7%), Valero (4,7%), BP (4,5%), TotalEnergies",
        "rol_radar": "Cobertura táctica contra shocks petrolíferos, gas y tensiones geopolíticas que drenan liquidez."
    },
    "Vanguard Global Bond Hedged": {
        "diana": "FONDOS", "bloque": "Refugio Anticrisis (Duración)",
        "ticker": "BND", "es_monetario": False, "es_fondo": True,
        "isin": "IE00B18GC888", "hora_corte": 12, "ter": "0,15%",
        "vehiculo": "Vanguard Global Bond Index EUR Hedged (IE00B18GC888)", "plataforma": "MyInvestor",
        "peso_obj": 0.01, "saldo_default": 600.0,
        "c1": -0.03, "c2": -0.06, "c3": -0.10,
        "v1": 0.08, "v2": 0.14, "v3": 0.20, "rsi_v1": 68, "rsi_v2": 72, "rsi_v3": 76,
        "r_2026": "-3,38%", "r_1a": "-2,47%", "r_3a": "+2,78%", "r_5a": "-1,99%",
        "vol_3a": "4,50%", "sharpe_3a": -0.15, "rating": "★★★",
        "top_holdings": "16.967 bonos globales (64% Gubernamental, 24% Corporativo). Duración: 5,99 años",
        "rol_radar": "Seguro de recesión deflacionaria: se revaloriza cuando los bancos centrales recortan tipos con fuerza."
    },
    "Pictet - Nutrition P EUR": {
        "diana": "FONDOS", "bloque": "Refugio Cadena Alimentaria",
        "ticker": "XLP", "es_monetario": False, "es_fondo": True,
        "isin": "LU0366534344", "hora_corte": 12, "ter": "2,01%",
        "vehiculo": "Pictet - Nutrition P EUR (LU0366534344)", "plataforma": "MyInvestor",
        "peso_obj": 0.01, "saldo_default": 600.0,
        "c1": -0.04, "c2": -0.09, "c3": -0.16,
        "v1": 0.12, "v2": 0.20, "v3": 0.28, "rsi_v1": 68, "rsi_v2": 73, "rsi_v3": 78,
        "r_2026": "+5,72%", "r_1a": "+8,14%", "r_3a": "+2,77%", "r_5a": "-4,31%",
        "vol_3a": "12,07%", "sharpe_3a": -0.23, "rating": "★★",
        "top_holdings": "Deere & Co (7,4%), Ecolab (4,6%), Novonesis (4,5%), Danone (4,3%), Thermo Fisher",
        "rol_radar": "Cadena agroalimentaria. Vigilancia táctica (penalizado a largo plazo por su TER del 2,01%)."
    },

    # --- BLOQUE 2: ORO FÍSICO Y BITCOIN (DIANA 2) ---
    "Oro Físico (Refugio)": {
        "diana": "ORO_BTC", "bloque": "Refugio Monetario Físico",
        "ticker": "GC=F", "es_monetario": False, "es_fondo": False,
        "isin": "IE00B4ND3602", "hora_corte": 17, "ter": "0,12%",
        "vehiculo": "ETC iShares Physical Gold (IE00B4ND3602) / Monedas", "plataforma": "MyInvestor / Trade Republic",
        "peso_obj": 0.15, "saldo_default": 9000.0,
        "c1": -0.05, "c2": -0.10, "c3": -0.18,
        "v1": 0.15, "v2": 0.25, "v3": 0.35, "rsi_v1": 70, "rsi_v2": 75, "rsi_v3": 80,
        "r_2026": "+28,40%", "r_1a": "+34,10%", "r_3a": "+19,80%", "r_5a": "+14,20%",
        "vol_3a": "13,50%", "sharpe_3a": 1.18, "rating": "ETC Físico 1:1",
        "top_holdings": "Lingotes de oro físico asignados custodiados en JPMorgan Londres",
        "rol_radar": "Seguro contra degradación fiduciaria y crisis de deuda soberana. Sin stop loss automático."
    },
    "Bitcoin (Asimetría)": {
        "diana": "ORO_BTC", "bloque": "Asimetría y Liquidez Global",
        "ticker": "BTC-USD", "es_monetario": False, "es_fondo": False,
        "isin": "BTC-USD", "hora_corte": 24, "ter": "0,00%",
        "vehiculo": "Spot Cripto 24/7", "plataforma": "Trade Republic",
        "peso_obj": 0.05, "saldo_default": 3000.0,
        "c1": -0.15, "c2": -0.30, "c3": -0.50,
        "v1": 0.35, "v2": 0.65, "v3": 1.00, "rsi_v1": 75, "rsi_v2": 80, "rsi_v3": 85,
        "r_2026": "+45,00%", "r_1a": "+62,00%", "r_3a": "+58,00%", "r_5a": "+42,00%",
        "vol_3a": "52,00%", "sharpe_3a": 1.15, "rating": "Spot 24/7",
        "top_holdings": "Bitcoin nativo (termómetro de liquidez global según doctrina Cava)",
        "rol_radar": "Captura asimetría extrema en ciclos de expansión de liquidez. Riesgo acotado al 5% del Radar."
    }
}

# Índices y sectores para la Pestaña Diana 3: Bolsa e Índices
INDICES_BOLSA = {
    "S&P 500 (Wall Street Core)": {"ticker": "^GSPC", "c1": -0.04, "c2": -0.10, "c3": -0.20, "v1": 0.15, "v2": 0.25, "v3": 0.35, "rsi_v1": 70, "rsi_v2": 75, "rsi_v3": 80, "fondo_asociado": "Fidelity S&P 500 Index P (IE00BYX5MX67)"},
    "Nasdaq 100 (Tecnología / IA)": {"ticker": "^NDX", "c1": -0.06, "c2": -0.15, "c3": -0.25, "v1": 0.18, "v2": 0.30, "v3": 0.45, "rsi_v1": 70, "rsi_v2": 75, "rsi_v3": 80, "fondo_asociado": "MyInvestor Nasdaq 100 FI (ES0165265002)"},
    "MSCI World (Bolsa Global)": {"ticker": "URTH", "c1": -0.04, "c2": -0.10, "c3": -0.18, "v1": 0.14, "v2": 0.22, "v3": 0.32, "rsi_v1": 70, "rsi_v2": 75, "rsi_v3": 80, "fondo_asociado": "Fidelity MSCI World Index P (IE00BYX5NX33)"},
    "Europa (MSCI Europe / Stoxx)": {"ticker": "VGK", "c1": -0.04, "c2": -0.09, "c3": -0.16, "v1": 0.12, "v2": 0.20, "v3": 0.28, "rsi_v1": 68, "rsi_v2": 73, "rsi_v3": 78, "fondo_asociado": "iShares Europe Equity Index A2 (LU0836512706)"},
    "Sector Salud / Pharma USA (XLV)": {"ticker": "XLV", "c1": -0.04, "c2": -0.09, "c3": -0.16, "v1": 0.14, "v2": 0.22, "v3": 0.30, "rsi_v1": 70, "rsi_v2": 75, "rsi_v3": 80, "fondo_asociado": "Wellington Global Health Care D (IE00BF2ZVB54)"},
    "Sector Energía / Petróleo (XLE)": {"ticker": "XLE", "c1": -0.06, "c2": -0.14, "c3": -0.24, "v1": 0.18, "v2": 0.28, "v3": 0.40, "rsi_v1": 70, "rsi_v2": 75, "rsi_v3": 80, "fondo_asociado": "Guinness Global Energy D EUR (IE00B3CCJB88)"},
    "Sector Consumo Básico / Nutrición (XLP)": {"ticker": "XLP", "c1": -0.04, "c2": -0.09, "c3": -0.16, "v1": 0.12, "v2": 0.20, "v3": 0.28, "rsi_v1": 68, "rsi_v2": 73, "rsi_v3": 78, "fondo_asociado": "Pictet - Nutrition P EUR (LU0366534344)"},
    "Bonos Globales / Duración (BND)": {"ticker": "BND", "c1": -0.03, "c2": -0.06, "c3": -0.10, "v1": 0.08, "v2": 0.14, "v3": 0.20, "rsi_v1": 68, "rsi_v2": 72, "rsi_v3": 76, "fondo_asociado": "Vanguard Global Bond Hedged (IE00B18GC888)"}
}

# Cargar o inicializar saldos del usuario
default_state = {
    "colchon_emergencias": COLCHON_EMERGENCIAS_DEFAULT,
    "dca_mensual": DCA_MENSUAL_DEFAULT,
    "saldos": {k: v["saldo_default"] for k, v in ACTIVOS_RADAR.items()},
    "objetivos": {k: CAPITAL_RADAR_DEFAULT * v["peso_obj"] for k, v in ACTIVOS_RADAR.items()}
}
estado_cartera = cargar_json(F_SALDOS, default_state)
for k, v in ACTIVOS_RADAR.items():
    if k not in estado_cartera["saldos"]:
        estado_cartera["saldos"][k] = v["saldo_default"]
    if k not in estado_cartera["objetivos"]:
        estado_cartera["objetivos"][k] = CAPITAL_RADAR_DEFAULT * v["peso_obj"]

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

def estado_hora_corte(hora_limite):
    if hora_limite >= 24:
        return "🟢 Mercado 24/7 (Ejecución inmediata)", True
    ahora = datetime.now()
    if ahora.weekday() >= 5:
        return f"⏸️ Fin de semana (Corte L-V {hora_limite:02d}:00h)", False
    if ahora.hour < hora_limite:
        restante_min = (hora_limite - 1 - ahora.hour) * 60 + (60 - ahora.minute)
        horas_r = restante_min // 60
        mins_r = restante_min % 60
        return f"🟢 EN HORA HOY (Corte {hora_limite:02d}:00h — quedan {horas_r}h {mins_r}m)", True
    return f"🟠 PASA A MAÑANA (Superado corte {hora_limite:02d}:00h)", False

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
        height=360, margin=dict(l=20, r=20, t=40, b=20),
        hovermode='x unified', showlegend=False,
        template="plotly_dark"
    )
    return fig

# ==================== MOTOR DE DECISIÓN CAVA (COMPRA, VENTA Y DCA) ====================
def evaluar_motor_cava(d, reglas, v_info, ticker, cap_posicion):
    if reglas.get("es_monetario", False):
        return 0, "BÚNKER NODRIZA", "Fondo Monetario €STR activo. Custodia la liquidez sin volatilidad (0,25%) para financiar tramos.", 0.0, 0.0, 0, cap_posicion

    caida = d["caida"]
    v_act = v_info["actual"]
    v_tension = v_info["tension"]
    
    c1, c2, c3 = reglas["c1"], reglas["c2"], reglas["c3"]
    base_calc = max(cap_posicion, 1000.0)
    t1_eur = base_calc * 0.30
    t2_eur = base_calc * 0.30
    t3_eur = base_calc * 0.40

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
                  f"Falta un {dist_target:.2%} de retroceso (Gatillo: {precio_target:,.2f} | Faltan {caida_pts:,.2f})")
        return 0, "ESPERAR", motivo, dist_target, precio_target, target_zona, target_eur

    # Filtro Anti-Cuchillo VIX Dinámico
    if abs(caida) >= 0.25 and (v_act < 20.0 and v_tension < 0.10):
        motivo = (f"En ZONA {zona_actual} ({tramo_actual_nom}: `{tramo_actual_eur:,.0f} €`) pero BLOQUEADO VIX. "
                  f"Caída del {caida:.1%} sin pánico institucional (VIX actual: {v_act:.1f} < 20 y tensión {v_tension:+.1%}).")
        return 0, "BLOQUEADO VIX", motivo, 0.0, 0.0, zona_actual, tramo_actual_eur

    # Filtro BOS (Quiebre de Estructura de Suelo de Cava)
    if zona_actual >= 2 and not d["bos"] and v_act < 25.0:
        p_bos = d["max_10d"]
        dist_bos = ((p_bos - d["precio"]) / d["precio"]) * 100.0
        motivo = (f"En ZONA {zona_actual} ({tramo_actual_nom}: `{tramo_actual_eur:,.0f} €`) pero BLOQUEADO BOS. "
                  f"Requiere quiebre de suelo superando {p_bos:,.2f} (+{dist_bos:.1f}%) o VIX > 25.")
        return 0, "BLOQUEADO BOS", motivo, 0.0, p_bos, zona_actual, tramo_actual_eur

    # Filtro de Volumen Institucional
    if not ticker.startswith("^") and d["vol_ratio"] < 0.85:
        motivo = (f"En ZONA {zona_actual} ({tramo_actual_nom}: `{tramo_actual_eur:,.0f} €`) pero BLOQUEADO VOLUMEN. "
                  f"Volumen débil ({d['vol_ratio']:.2f}x < 0.85x). Sin absorción.")
        return 0, "BLOQUEADO VOLUMEN", motivo, 0.0, 0.0, zona_actual, tramo_actual_eur

    pauta_txt = " (PAUTA BONITA CAVA)" if d["la_bonita"] else ""
    motivo = (f"¡GATILLO ACTIVADO! Ejecutar ZONA {zona_actual}{pauta_txt} — {tramo_actual_nom}: `{tramo_actual_eur:,.0f} €`. "
              f"Descuento {caida:.2%} validado con estructura y volatilidad.")
    return zona_actual, f"COMPRAR ZONA {zona_actual}{pauta_txt}", motivo, 0.0, 0.0, zona_actual, tramo_actual_eur

def evaluar_venta_cava(d, reglas):
    if reglas.get("es_monetario", False):
        return 0, "LIQUIDEZ BASE", "El fondo monetario no se vende por sobrecompra; financia las compras de los demás bloques."
    ds = d["dist_sma"]
    rsi = d["rsi"]
    es_spot = not reglas.get("es_fondo", True)
    
    if es_spot:
        msg_z3 = "Extremo sobrecalentamiento macro. Vender del 50% al 80% de la posición a Euros / Efectivo para asegurar plusvalías."
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

def evaluar_dca_cava(d, es_monetario=False):
    if es_monetario:
        return "🟢", "#22c55e", "#143320", "#4ade80", "RECEPTOR DE AHORRO Y LIQUIDEZ", "Todo el ahorro mensual que no tenga señal clara en renta variable se acumula en el AXA Trésor Court Terme.", 1.0
    if d['stoch_k'] > 80:
        return "🔴", "#ef4444", "#371515", "#f87171", "APORTACIÓN MÍNIMA DE CALENDARIO (SIN EXTRAS)", "SOBRECOMPRA EXTREMA (%K > 80). Haz solo cuota mínima fija si es automática; PROHIBIDO gastar pólvora extra.", 0.5
    elif d['la_bonita']:
        return "🟢", "#22c55e", "#143320", "#4ade80", "¡LA BONITA CONFIRMADA! (ADELANTAR DCA + TRAMO EXTRA)", "MÁXIMA PROBABILIDAD ESTADÍSTICA (Cava, Cap. V). Estocástico semanal cortando al alza desde sobreventa con tendencia alcista.", 1.5
    elif d['macd_alcista']:
        return "🟡", "#eab308", "#332b14", "#facc15", "APORTACIÓN NORMAL DE CALENDARIO", "TENDENCIA MACRO ALCISTA SANA. El MACD semanal acompaña sin sobrecompra extrema. Ejecuta tu cuota mensual normal.", 1.0
    else:
        return "🔴", "#f97316", "#351e12", "#fb923c", "APORTACIÓN MÍNIMA (PRUDENCIA MACRO)", "TENDENCIA MACRO EN FASE CORRECTIVA. El MACD semanal no confirma impulso alcista. No comprometas reservas de liquidez.", 0.5

# Función reutilizable para renderizar una tarjeta completa de Semáforo y Tramos
def renderizar_tarjeta_semaforo(nombre, reglas, v_info, saldo_actual, cap_objetivo):
    es_mon = reglas.get("es_monetario", False)
    if es_mon:
        txt_corte, _ = estado_hora_corte(reglas["hora_corte"])
        desv = saldo_actual - cap_objetivo
        with st.expander(f"🛡️ **{nombre}** (`{reglas['isin']}`) | BÚNKER NODRIZA | Saldo Actual: **{saldo_actual:,.0f} €** (Objetivo Base: {cap_objetivo:,.0f} €)", expanded=True):
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Saldo Actual en AXA", f"{saldo_actual:,.0f} €", f"{desv:+,.0f} € vs Base")
            c2.metric("Rentabilidad 3A (Anual.)", reglas["r_3a"], f"TER: {reglas['ter']}")
            c3.metric("Volatilidad 3A", reglas["vol_3a"], f"Sharpe: {reglas['sharpe_3a']}")
            c4.metric("Hora Corte MyInvestor", f"{reglas['hora_corte']:02d}:00 CET", txt_corte)
            st.info(f"🏦 **Función en el Sistema:** {reglas['rol_radar']} Cartera: {reglas['top_holdings']}.")
        return

    d = get_market_data(reglas["ticker"])
    if not d:
        st.error(f"Error conectando con los datos de {nombre} ({reglas['ticker']})")
        return

    tramo_1 = max(cap_objetivo, 1000.0) * 0.30
    tramo_2 = max(cap_objetivo, 1000.0) * 0.30
    tramo_3 = max(cap_objetivo, 1000.0) * 0.40

    zona_c, estado_c, motivo_c, dist_target, precio_target, target_zona, target_eur = evaluar_motor_cava(
        d, reglas, v_info, reglas["ticker"], cap_objetivo
    )
    zona_v, estado_v, motivo_v = evaluar_venta_cava(d, reglas)

    if "COMPRAR" in estado_c: icon_c = "🟢"
    elif "BLOQUEADO" in estado_c: icon_c = "🛡️"
    elif zona_v > 0: icon_c = "🟡"
    else: icon_c = "⚪"

    badge_op = f"⏱️ Corte {reglas['hora_corte']:02d}:00h" if reglas.get("es_fondo", True) else "⚡ Spot 24/7"
    desv_eur = saldo_actual - cap_objetivo

    with st.expander(f"{icon_c} **{nombre}** (`{reglas['isin']}`) | {badge_op} | Saldo: **{saldo_actual:,.0f} €** / Obj: **{cap_objetivo:,.0f} €** | Compra: **{estado_c}** | Venta: **{estado_v}**", expanded=True):
        m1, m2, m3, m4, m5, m6 = st.columns(6)
        m1.metric("Saldo Actual vs Obj.", f"{saldo_actual:,.0f} €", f"{desv_eur:+,.0f} € (Obj: {cap_objetivo:,.0f} €)")
        m2.metric("Precio Proxy / Spot", f"{d['precio']:,.2f}", f"ATH: {d['caida']:.2%}")
        m3.metric("Línea Vital (SMA200)", f"{d['sma200']:,.2f}", f"{d['dist_sma']:+.2%}")
        m4.metric("MACD Semanal", "ALCISTA" if d['macd_alcista'] else "BAJISTA", "Sobre 0" if d['macd_cero'] else "Bajo 0")
        m5.metric("Estocástico (14w)", f"{d['stoch_k']:.1f}", "La Bonita" if d['la_bonita'] else f"RSI: {d['rsi']:.1f}")
        m6.metric("Coste TER / Sharpe", reglas.get("ter", "N/A"), f"3A: {reglas.get('r_3a', 'N/A')}")

        txt_corte, _ = estado_hora_corte(reglas["hora_corte"])
        st.markdown(f"**Vehículo:** `{reglas['vehiculo']}` en **{reglas['plataforma']}** | **Ventana hoy:** {txt_corte} | **Función:** {reglas.get('rol_radar', '')}")

        # --- SECCIÓN 1: PÓLVORA TÁCTICA (TRAMOS DE CAPITAL) ---
        st.markdown("---")
        st.markdown(f"#### 🎯 Despliegue Táctico por Tramos — {nombre}")

        if estado_c == "ESPERAR":
            st.info(f"⏳ **{motivo_c}**")
            progreso = max(0.0, min(1.0, 1.0 - (dist_target / abs(reglas['c1']))))
            st.progress(progreso, text=f"Proximidad a ZONA {target_zona} (Tramo {target_zona} = {target_eur:,.0f} €): Falta un {dist_target:.2%}")
        elif "BLOQUEADO" in estado_c:
            st.warning(f"#### 🛡️ {estado_c}\n{motivo_c}")
            st.markdown(f"""
            - **Tramo Táctico Retenido:** `{target_eur:,.0f} €` asignados a **Zona {target_zona}**.
            - **Protocolo Cava:** La munición permanece en `{NOMBRE_MONETARIO_NODRIZA}` hasta que el VIX supere 20 o se confirme quiebre de estructura (BOS).
            """)
        elif "COMPRAR" in estado_c:
            st.success(f"#### 🎯 {estado_c}\n{motivo_c}")
            st.markdown(f"""
            - **Tramo a Ejecutar AHORA:** `{target_eur:,.0f} €` (Zona {target_zona})
            - **Vehículo de Destino:** `{reglas['vehiculo']}` en **{reglas['plataforma']}**
            - **Procedimiento:** {"Ordenar traspaso desde el Monetario `" + NOMBRE_MONETARIO_NODRIZA + "` antes de las " + str(reglas['hora_corte']) + ":00h CET." if reglas.get("es_fondo", True) else "Ejecutar compra Spot en " + reglas['plataforma'] + "."}
            """)

        if zona_v > 0:
            importe_venta = saldo_actual * (0.80 if zona_v == 3 else 0.30 if zona_v == 2 else 0.0)
            st.warning(f"#### ⚠️ {estado_v} (Sobre tu saldo actual de {saldo_actual:,.0f} € -> Recoger `{importe_venta:,.0f} €`)\n{motivo_v}")

        st.caption(f"Estructura Táctica sobre Objetivo ({cap_objetivo:,.0f} €): Tramo 1 (30%): {tramo_1:,.0f} € | Tramo 2 (30%): {tramo_2:,.0f} € | Tramo 3 (40%): {tramo_3:,.0f} €")

        # --- SECCIÓN 2: SEMÁFORO DCA MENSUAL ---
        color_dca, border_color, bg_color, text_color, accion_dca, mensaje_dca, _ = evaluar_dca_cava(d, es_mon)
        st.markdown(f"""
        <div class="card-dca" style="background-color: {bg_color}; border-color: {border_color};">
            <div style="font-weight: 700; font-size: 1.02rem; color: {text_color}; margin-bottom: 6px;">
                {color_dca} SEMÁFORO DCA: {accion_dca}
            </div>
            <div style="color: #e5e7eb; font-size: 0.92rem; line-height: 1.4;">
                {mensaje_dca}
            </div>
        </div>
        """, unsafe_allow_html=True)

# ==================== BARRA LATERAL: SALDOS ACTUALES Y PARÁMETROS ====================
st.sidebar.header("💼 Mis Saldos Reales en Cartera")
st.sidebar.caption("Introduce tu saldo actual en cada fondo/activo. Se guarda automáticamente para calcular todos los traspasos y compras del Roboadvisor CAVA.")

with st.sidebar.expander("⚙️ Editar Saldos Actuales (€)", expanded=False):
    nuevo_colchon = st.number_input("🛡️ Colchón Emergencias Fuera (€)", min_value=0.0, value=float(estado_cartera.get("colchon_emergencias", 10000.0)), step=500.0)
    nuevo_dca = st.number_input("💶 Presupuesto DCA Mensual (€)", min_value=0.0, value=float(estado_cartera.get("dca_mensual", 1000.0)), step=100.0)
    st.markdown("---")
    st.markdown("**Saldos Actuales en Fondos y Spot (€):**")
    nuevos_saldos = {}
    for nombre, info in ACTIVOS_RADAR.items():
        val_actual = float(estado_cartera["saldos"].get(nombre, info["saldo_default"]))
        nuevos_saldos[nombre] = st.number_input(
            f"{nombre} ({info['isin']})",
            min_value=0.0, value=val_actual, step=100.0, key=f"sb_saldo_{info['isin']}"
        )
    if st.button("💾 Guardar Mis Saldos", use_container_width=True):
        estado_cartera["colchon_emergencias"] = nuevo_colchon
        estado_cartera["dca_mensual"] = nuevo_dca
        estado_cartera["saldos"] = nuevos_saldos
        guardar_json(F_SALDOS, estado_cartera)
        st.success("¡Saldos guardados correctamente!")
        st.rerun()

total_radar_actual = sum(estado_cartera["saldos"].values())
saldo_axa_actual = estado_cartera["saldos"].get("AXA Trésor Court Terme C", 15000.0)
colchon_actual = estado_cartera.get("colchon_emergencias", 10000.0)
dca_mensual_actual = estado_cartera.get("dca_mensual", 1000.0)

st.sidebar.markdown(f"**Patrimonio Total en Radar:** `{total_radar_actual:,.0f} €`")
st.sidebar.markdown(f"**Pólvora en AXA (`{ISIN_MONETARIO_NODRIZA}`):** `{saldo_axa_actual:,.0f} €`")
st.sidebar.markdown(f"**Aportación DCA Mensual:** `{dca_mensual_actual:,.0f} €`")
st.sidebar.markdown(f"**Colchón Reserva Fuera:** `{colchon_actual:,.0f} €`")
st.sidebar.markdown("---")
st.sidebar.markdown(f"⏰ **Hora actual (CET):** `{datetime.now().strftime('%H:%M')}`")
st.sidebar.caption("Cortes MyInvestor: **10:00h** (AXA / iShares Eur) | **12:00h** (Nasdaq / Well. / Vang. / Pictet) | **14:00h** (Guinness) | **16:00h** (Fidelity S&P / World).")

if st.sidebar.button("🔄 Actualizar Cotizaciones en Vivo", use_container_width=True):
    st.cache_data.clear()
    st.rerun()

# ==================== CABECERA PRINCIPAL ====================
st.title("🦈 Radar Tiburón Cava Pro — Roboadvisor & 3 Dianas")

v_info = get_vix_data()

c_m1, c_m2, c_m3, c_m4 = st.columns(4)
c_m1.info(f"🏛️ **Ciclo Presidencial:**\n{get_ciclo_presidencial()}")
c_m2.warning(f"📅 **Estacionalidad:**\n{get_estacionalidad()}")
c_m3.metric("VIX Actual (Filtro Cava)", f"{v_info['actual']:.2f}", f"{v_info['tension']:+.1%} vs SMA10 ({v_info['sma10']:.1f})")
c_m4.metric("Patrimonio Total Radar + Colchón", f"{total_radar_actual + colchon_actual:,.0f} €", f"AXA Liquidez: {saldo_axa_actual:,.0f} €")

# ==================== LAS 5 PESTAÑAS ESTRATÉGICAS ====================
tab_roboadvisor, tab_diana_fondos, tab_diana_oro_btc, tab_diana_bolsa, tab_manual = st.tabs([
    "🤖 Roboadvisor CAVA (Ejecución & Saldos)",
    "🎯 Diana 1: Fondos MyInvestor (9 Semáforos)",
    "🎯 Diana 2: Oro y BTC (Spot & Físico)",
    "🎯 Diana 3: Bolsa, Flujo & Dow",
    "📖 Manual y Fichas Auditadas"
])

# ==================== PESTAÑA 1: ROBOADVISOR CAVA (HOJA DE RUTA DE EJECUCIÓN) ====================
with tab_roboadvisor:
    st.subheader("🤖 Roboadvisor CAVA — Editor de Saldos Reales y Hoja de Órdenes a Ejecutar Hoy")
    st.caption("Actualiza tus saldos reales en la tabla inferior y pulsa Guardar: el motor Cava cruzará tu cartera con el VIX, la estructura de precios, el MACD semanal y las horas de corte para dictarte todas las órdenes exactas de compra, aportación DCA, traspaso o venta.")

    # --- 1. TABLA INTERACTIVA DE SALDOS ACTUALES Y OBJETIVOS ---
    st.markdown("#### 💰 1. Mis Saldos Actuales vs. Asignación Objetivo por Fondo y Activo")
    df_edicion_input = pd.DataFrame([
        {
            "Activo / Fondo": nombre,
            "Diana": "🏦 Fondos MyInvestor" if info["diana"] == "FONDOS" else "🪙 Oro & BTC",
            "ISIN / Ticker": info["isin"],
            "Corte CET": f"{info['hora_corte']:02d}:00h" if info["hora_corte"] < 24 else "24/7",
            "TER": info["ter"],
            "Saldo Actual (€)": float(estado_cartera["saldos"].get(nombre, info["saldo_default"])),
            "Asignación Objetivo (€)": float(estado_cartera["objetivos"].get(nombre, CAPITAL_RADAR_DEFAULT * info["peso_obj"])),
        }
        for nombre, info in ACTIVOS_RADAR.items()
    ])

    df_editado = st.data_editor(
        df_edicion_input,
        column_config={
            "Activo / Fondo": st.column_config.TextColumn("Fondo / Activo", disabled=True),
            "Diana": st.column_config.TextColumn("Bloque Diana", disabled=True),
            "ISIN / Ticker": st.column_config.TextColumn("ISIN / Ticker", disabled=True),
            "Corte CET": st.column_config.TextColumn("Hora Corte", disabled=True),
            "TER": st.column_config.TextColumn("Coste TER", disabled=True),
            "Saldo Actual (€)": st.column_config.NumberColumn("✏️ Mi Saldo Actual (€)", min_value=0.0, step=100.0, format="%.2f €"),
            "Asignación Objetivo (€)": st.column_config.NumberColumn("🎯 Objetivo Ideal (€)", min_value=0.0, step=100.0, format="%.2f €"),
        },
        use_container_width=True,
        hide_index=True,
        key="editor_principal_saldos"
    )

    col_btn1, col_btn2, col_btn3 = st.columns([2, 2, 2])
    with col_btn1:
        dca_input_main = st.number_input("💶 Aportación Mensual DCA a repartir hoy (€):", min_value=0.0, value=float(dca_mensual_actual), step=100.0, key="dca_main_input")
    with col_btn2:
        colchon_input_main = st.number_input("🛡️ Colchón de Emergencias Fuera del Radar (€):", min_value=0.0, value=float(colchon_actual), step=500.0, key="colchon_main_input")
    with col_btn3:
        st.write("")
        if st.button("💾 Guardar Cambios de Saldos y Recalcular Órdenes", type="primary", use_container_width=True):
            for _, row in df_editado.iterrows():
                nom = row["Activo / Fondo"]
                estado_cartera["saldos"][nom] = float(row["Saldo Actual (€)"])
                estado_cartera["objetivos"][nom] = float(row["Asignación Objetivo (€)"])
            estado_cartera["dca_mensual"] = float(dca_input_main)
            estado_cartera["colchon_emergencias"] = float(colchon_input_main)
            guardar_json(F_SALDOS, estado_cartera)
            st.success("✅ Saldos y objetivos actualizados. Hoja de órdenes recalculada.")
            st.rerun()

    # --- 2. MOTOR CENTRAL ROBOADVISOR CAVA: GENERACIÓN DE TODAS LAS ÓRDENES ---
    st.markdown("---")
    st.markdown("#### ⚡ 2. Panel de Ejecución Roboadvisor CAVA — Movimientos Exactos a Realizar")

    ordenes_traspaso_compra = []
    ordenes_venta_recogida = []
    ordenes_rotacion_crisis = []
    ordenes_dca_mensual = []

    datos_mercado_cache = {}
    for nombre, info in ACTIVOS_RADAR.items():
        if not info.get("es_monetario", False):
            datos_mercado_cache[nombre] = get_market_data(info["ticker"])

    d_sp = datos_mercado_cache.get("Fidelity S&P 500 Index P")
    d_ndx = datos_mercado_cache.get("MyInvestor Nasdaq 100 FI")
    v_act = v_info["actual"]
    saldo_axa_disp = float(estado_cartera["saldos"].get("AXA Trésor Court Terme C", 0.0))

    # A) Evaluar Régimen Macro / Rotación de Crisis
    alerta_panico_liquidez = False
    alerta_rotacion_ia = False
    if d_sp and d_ndx:
        bajo_sma_sp = d_sp["dist_sma"] < 0
        bajo_sma_ndx = d_ndx["dist_sma"] < 0
        divergencia_ia = (d_ndx["caida"] - d_sp["caida"]) <= -0.05

        if v_act >= 25.0 or (bajo_sma_sp and bajo_sma_ndx and v_act >= 20.0):
            alerta_panico_liquidez = True
            st.error(
                f"🚨 **MODO BÚNKER ACTIVADO (Pánico de Liquidez — VIX {v_act:.1f}):** "
                f"El S&P 500, MSCI World y Nasdaq caen juntos bajo presión de liquidez. "
                f"**Prohibido rotar a bolsa europea.** El protocolo Cava ordena proteger rentabilidades en **AXA Trésor Court Terme (`{ISIN_MONETARIO_NODRIZA}`)** y retener compras hasta señal de suelo validada."
            )
        elif divergencia_ia or (bajo_sma_ndx and not bajo_sma_sp):
            alerta_rotacion_ia = True
            st.warning(
                f"🔄 **ALERTA DE ROTACIÓN SECTORIAL (Pinchazo Múltiplos Tech — Nasdaq {d_ndx['caida']:.1%} vs S&P {d_sp['caida']:.1%}):** "
                f"Debilidad concentrada en tecnología sin pánico sistémico (VIX {v_act:.1f}). "
                f"Se habilita rotación defensiva hacia Farmacia USA (**Wellington Health Care `IE00BF2ZVB54`**) y Europa Defensiva (**iShares Europe `LU0836512706`**)."
            )
        else:
            st.success(
                f"🟢 **RÉGIMEN MACRO NORMALIZADO (VIX {v_act:.1f} | S&P {d_sp['caida']:.1%} | Nasdaq {d_ndx['caida']:.1%}):** "
                f"Sin estrés sistémico de liquidez. Se ejecutan tramos tácticos en activos que toquen Zona 1/2/3 y aportaciones DCA según semáforo."
            )

    # B) Recorrer todos los activos para generar órdenes de Compra por Tramos, Venta/Traspaso y DCA
    pesos_dca_candidatos = {}

    for nombre, info in ACTIVOS_RADAR.items():
        if info.get("es_monetario", False):
            continue
        d = datos_mercado_cache.get(nombre)
        if not d:
            continue

        saldo_act = float(estado_cartera["saldos"].get(nombre, 0.0))
        obj_act = float(estado_cartera["objetivos"].get(nombre, CAPITAL_RADAR_DEFAULT * info["peso_obj"]))
        deficit_obj = max(0.0, obj_act - saldo_act)

        zona_c, estado_c, motivo_c, dist_target, precio_target, target_zona, target_eur = evaluar_motor_cava(
            d, info, v_info, info["ticker"], obj_act
        )
        zona_v, estado_v, motivo_v = evaluar_venta_cava(d, info)
        color_dca, _, _, _, accion_dca, _, mult_dca = evaluar_dca_cava(d, False)
        txt_corte, _ = estado_hora_corte(info["hora_corte"])

        # 1. Órdenes de Compra por Tramos / Traspaso desde AXA
        if "COMPRAR" in estado_c:
            importe_orden = min(target_eur, saldo_axa_disp) if info["es_fondo"] else target_eur
            tipo_mov = "🔄 TRASPASO DE ENTRADA (Desde AXA Monetario)" if info["es_fondo"] else "⚡ COMPRA SPOT A MERCADO"
            origen_mov = NOMBRE_MONETARIO_NODRIZA if info["es_fondo"] else "Liquidez Trade Republic / MyInvestor"
            ordenes_traspaso_compra.append({
                "Prioridad": f"🟢 {estado_c}",
                "Tipo de Operación": tipo_mov,
                "Origen": origen_mov,
                "Destino": f"{nombre} ({info['isin']})",
                "Importe a Ejecutar": f"{importe_orden:,.2f} €",
                "Tu Saldo Actual / Obj.": f"{saldo_act:,.0f} € / {obj_act:,.0f} €",
                "Ventana de Corte": txt_corte,
                "Justificación Técnica Cava": motivo_c
            })
        elif "BLOQUEADO" in estado_c:
            ordenes_traspaso_compra.append({
                "Prioridad": f"🛡️ {estado_c} (NO DISPARAR AÚN)",
                "Tipo de Operación": "⏸️ RETENER EN AXA MONETARIO",
                "Origen": NOMBRE_MONETARIO_NODRIZA,
                "Destino": f"{nombre} ({info['isin']})",
                "Importe a Ejecutar": f"0,00 € (Retenidos {target_eur:,.0f} €)",
                "Tu Saldo Actual / Obj.": f"{saldo_act:,.0f} € / {obj_act:,.0f} €",
                "Ventana de Corte": txt_corte,
                "Justificación Técnica Cava": motivo_c
            })

        # 2. Órdenes de Venta / Recogida de Beneficios
        if zona_v >= 2 and saldo_act > 0:
            pct_recogida = 0.70 if zona_v == 3 else 0.30
            imp_venta = saldo_act * pct_recogida
            tipo_v = "🔄 TRASPASO RECOGIDA BENEFICIOS (0% IRPF)" if info["es_fondo"] else "💰 VENTA PARCIAL SPOT A EFECTIVO"
            destino_v = NOMBRE_MONETARIO_NODRIZA if info["es_fondo"] else "Cuenta Efectivo EUR (Trade Republic / MyInvestor)"
            ordenes_venta_recogida.append({
                "Señal": f"⚠️ {estado_v}",
                "Operación": tipo_v,
                "Desde (Origen)": f"{nombre} ({info['isin']})",
                "Hacia (Destino)": destino_v,
                "Importe a Recoger": f"{imp_venta:,.2f} € ({pct_recogida*100:.0f}% de tu saldo)",
                "Hora Límite": txt_corte,
                "Motivo": motivo_v
            })

        # 3. Órdenes de Rotación en Crisis / Ajuste Sectorial
        if alerta_rotacion_ia and nombre in ["Wellington Global Health Care D", "iShares Europe Equity Index A2"] and deficit_obj > 0:
            imp_rot = min(deficit_obj, max(600.0, obj_act * 0.50), saldo_axa_disp)
            ordenes_rotacion_crisis.append({
                "Estrategia": "🔄 ROTACIÓN DEFENSIVA ANTI-IA",
                "Operación": "Traspaso Interno MyInvestor (0% Peaje Fiscal)",
                "Origen": f"AXA Monetario ({ISIN_MONETARIO_NODRIZA}) o Exceso en Nasdaq",
                "Destino": f"{nombre} ({info['isin']})",
                "Importe Sugerido": f"{imp_rot:,.2f} €",
                "Ventana Corte": txt_corte,
                "Razón Macro Cava": f"Fuerza relativa defensiva mientras corrigen múltiplos tecnológicos. Cubre tu déficit de {deficit_obj:,.0f} €."
            })

        # 4. Ponderación para el reparto del DCA mensual
        if obj_act > 0:
            peso_rel = obj_act * mult_dca
            pesos_dca_candidatos[nombre] = {
                "peso_pond": peso_rel,
                "color": color_dca,
                "accion": accion_dca,
                "isin": info["isin"],
                "corte": txt_corte,
                "es_fondo": info["es_fondo"],
                "stoch_k": d["stoch_k"],
                "la_bonita": d["la_bonita"]
            }

    # Mostrar Bloques de Órdenes Ejecutables
    st.markdown("##### 🎯 A. Órdenes Tácticas por Tramos (Compras / Traspasos desde AXA y Bloqueos de Seguridad)")
    if ordenes_traspaso_compra:
        st.dataframe(pd.DataFrame(ordenes_traspaso_compra), use_container_width=True, hide_index=True)
    else:
        st.info("⏳ **Ningún activo se encuentra hoy en Zona 1, 2 o 3 de descuento.** Toda la pólvora táctica permanece rindiendo al tipo €STR en **AXA Trésor Court Terme C (`FR0000447823`)** esperando retrocesos a soporte.")

    st.markdown("##### 💰 B. Órdenes de Venta / Traspaso de Recogida de Beneficios y Rotaciones Defensivas")
    if ordenes_venta_recogida or ordenes_rotacion_crisis:
        if ordenes_venta_recogida:
            st.dataframe(pd.DataFrame(ordenes_venta_recogida), use_container_width=True, hide_index=True)
        if ordenes_rotacion_crisis:
            st.dataframe(pd.DataFrame(ordenes_rotacion_crisis), use_container_width=True, hide_index=True)
    else:
        st.success("✅ **Sin señales de venta por sobreextensión ni rotaciones de emergencia hoy.** Mantener posiciones actuales en cartera.")

    st.markdown(f"##### 🚦 C. Distribución Exacta de tu Aportación Mensual DCA (`{dca_input_main:,.2f} €`) según Semáforo Cava")
    if dca_input_main > 0 and pesos_dca_candidatos:
        suma_pesos_dca = sum(v["peso_pond"] for v in pesos_dca_candidatos.values())
        for nom_d, dat_d in pesos_dca_candidatos.items():
            cuota_eur = (dca_input_main * (dat_d["peso_pond"] / suma_pesos_dca)) if suma_pesos_dca > 0 else 0.0
            if alerta_panico_liquidez:
                destino_final = f"AXA Trésor Court Terme C ({ISIN_MONETARIO_NODRIZA}) [Refugio por VIX alto]"
                operativa_dca = "Aportar al Monetario Nodriza hasta que pase el pánico"
            else:
                destino_final = f"{nom_d} ({dat_d['isin']})"
                operativa_dca = "Aportación directa o traspaso desde AXA" if dat_d["es_fondo"] else "Compra periódica Spot"
            ordenes_dca_mensual.append({
                "Semáforo": f"{dat_d['color']} {dat_d['accion']}",
                "Destino de la Cuota": destino_final,
                "Importe Exacto a Aportar": f"{cuota_eur:,.2f} €",
                "Vía de Ejecución": operativa_dca,
                "Estocástico Semanal %K": f"{dat_d['stoch_k']:.1f}" + (" (¡LA BONITA!)" if dat_d["la_bonita"] else ""),
                "Hora Límite Hoy": dat_d["corte"]
            })
        st.dataframe(pd.DataFrame(ordenes_dca_mensual), use_container_width=True, hide_index=True)

    # --- 3. TABLA DE REBALANCEO ESTRUCTURAL (SALDO ACTUAL VS OBJETIVO) ---
    st.markdown("##### ⚖️ D. Mapa de Desviación Patrimonial (Tu Saldo Actual vs. Cartera Objetivo)")
    filas_desv = []
    for nombre, info in ACTIVOS_RADAR.items():
        s_act = float(estado_cartera["saldos"].get(nombre, 0.0))
        o_act = float(estado_cartera["objetivos"].get(nombre, 0.0))
        dif = s_act - o_act
        pct_act = (s_act / total_radar_actual * 100.0) if total_radar_actual > 0 else 0.0
        if abs(dif) < 100:
            acc_reb = "✅ En objetivo exacto"
        elif dif < 0:
            acc_reb = f"📥 Faltan {abs(dif):,.0f} € (Cubrir en próximos tramos/DCA)"
        else:
            acc_reb = f"📤 Exceso de +{dif:,.0f} € (Disponible para traspasar si salta señal)"
        filas_desv.append({
            "Activo / Fondo": nombre,
            "ISIN": info["isin"],
            "Mi Saldo Actual (€)": f"{s_act:,.2f} €",
            "Peso Real (%)": f"{pct_act:.1f}%",
            "Objetivo (€)": f"{o_act:,.2f} €",
            "Diferencia (€)": f"{dif:+,.2f} €",
            "Diagnóstico de Cartera": acc_reb
        })
    st.dataframe(pd.DataFrame(filas_desv), use_container_width=True, hide_index=True)

# ==================== PESTAÑA 2: DIANA 1 — FONDOS MYINVESTOR (LOS 9 FONDOS) ====================
with tab_diana_fondos:
    st.subheader("🎯 Diana 1: Fondos Tradicionales en MyInvestor (Semáforos, Tramos y Horas de Corte)")
    st.caption("Incluye los 9 fondos auditados de tu catálogo en MyInvestor con su saldo actual, tramos 30%/30%/40%, semáforo DCA y ventana horaria CET.")

    # Monitor rápido de cortes CET
    c_h1, c_h2, c_h3, c_h4 = st.columns(4)
    c_h1.metric("Corte 10:00 CET", "AXA / iShares Eur", estado_hora_corte(10)[0])
    c_h2.metric("Corte 12:00 CET", "Nasdaq / Well. / Vang. / Pictet", estado_hora_corte(12)[0])
    c_h3.metric("Corte 14:00 CET", "Guinness Energy", estado_hora_corte(14)[0])
    c_h4.metric("Corte 16:00 CET", "Fidelity S&P / World", estado_hora_corte(16)[0])
    st.markdown("---")

    for nombre, info in ACTIVOS_RADAR.items():
        if info["diana"] == "FONDOS":
            s_act = float(estado_cartera["saldos"].get(nombre, 0.0))
            o_act = float(estado_cartera["objetivos"].get(nombre, CAPITAL_RADAR_DEFAULT * info["peso_obj"]))
            renderizar_tarjeta_semaforo(nombre, info, v_info, s_act, o_act)

# ==================== PESTAÑA 3: DIANA 2 — ORO FÍSICO Y BITCOIN ====================
with tab_diana_oro_btc:
    st.subheader("🎯 Diana 2: Oro Físico y Bitcoin (Activos Reales y Asimetría Spot)")
    st.caption("Gestión táctica por tramos sin Stop Loss automático en exchange: protección contra degradación monetaria (Oro `IE00B4ND3602`) y termómetro de liquidez global (Bitcoin `BTC-USD`).")

    for nombre, info in ACTIVOS_RADAR.items():
        if info["diana"] == "ORO_BTC":
            s_act = float(estado_cartera["saldos"].get(nombre, 0.0))
            o_act = float(estado_cartera["objetivos"].get(nombre, CAPITAL_RADAR_DEFAULT * info["peso_obj"]))
            renderizar_tarjeta_semaforo(nombre, info, v_info, s_act, o_act)

# ==================== PESTAÑA 4: DIANA 3 — BOLSA, FLUJO INSTITUCIONAL Y TEORÍA DE DOW ====================
with tab_diana_bolsa:
    st.subheader("🎯 Diana 3: Bolsa e Índices Globales — Semáforos, Rayos X de Flujo y Estructura Dow")
    st.caption("Visión institucional completa de los índices directores de Wall Street, Europa y sectores refugio (Salud, Energía, Consumo y Bonos) que gobiernan tus fondos.")

    subtab_ind, subtab_flujo, subtab_dow = st.tabs([
        "📊 Semáforo de Índices Bursátiles",
        "🏛️ Rayos X de Flujo Institucional (OBV, A/D, VWAP)",
        "📈 Gráficos Teoría de Dow (Techos y Suelos)"
    ])

    with subtab_ind:
        filas_bolsa = []
        for nom_idx, reg_idx in INDICES_BOLSA.items():
            d_i = get_market_data(reg_idx["ticker"])
            if not d_i:
                continue
            _, est_ci, mot_ci, dist_i, gat_i, _, _ = evaluar_motor_cava(d_i, reg_idx, v_info, reg_idx["ticker"], 10000.0)
            _, est_vi, _ = evaluar_venta_cava(d_i, {"es_fondo": True, **reg_idx})
            filas_bolsa.append({
                "Índice / Sector Bursátil": nom_idx,
                "Ticker": reg_idx["ticker"],
                "Cotización": f"{d_i['precio']:,.2f}",
                "Caída desde Máx (52s)": f"{d_i['caida']:.2%}",
                "Dist. SMA200": f"{d_i['dist_sma']:+.2%}",
                "RSI (14)": f"{d_i['rsi']:.1f}",
                "MACD Semanal": "🟢 ALCISTA" if d_i["macd_alcista"] else "🔴 BAJISTA",
                "Estocástico %K": f"{d_i['stoch_k']:.1f}" + (" (🔥 Bonita)" if d_i["la_bonita"] else ""),
                "Señal Compra Cava": est_ci,
                "Señal Venta": est_vi,
                "Fondo MyInvestor Asociado": reg_idx["fondo_asociado"]
            })
        st.dataframe(pd.DataFrame(filas_bolsa), use_container_width=True, hide_index=True)

    with subtab_flujo:
        st.markdown("#### 🏛️ Acumulación vs. Distribución Institucional")
        for nom_idx, reg_idx in INDICES_BOLSA.items():
            fl = flujo_institucional(reg_idx["ticker"])
            if not fl:
                continue
            ic_fl = "🟢" if fl['score'] >= 2 else "⚪" if fl['score'] >= 0 else "🔴"
            with st.expander(f"{ic_fl} **{nom_idx}** (`{reg_idx['ticker']}`) — Puntuación Flujo Institucional: {fl['score']:+d} | Fondo: `{reg_idx['fondo_asociado']}`", expanded=True):
                f1, f2, f3 = st.columns(3)
                f1.metric("Presión de Volumen (OBV)", f"{fl['obv']:+.1%}", fl['obv_sig'])
                f2.metric("Acumulación / Distribución (A/D)", f"{fl['ad']:+.1%}", fl['ad_sig'])
                f3.metric("Precio VWAP Institucional", f"{fl['vwap']:,.2f}", f"{fl['dist_vwap']:+.2f}% vs Spot")

    with subtab_dow:
        st.markdown("#### 📈 Estructura de Techos y Suelos (Teoría de Dow)")
        for nom_idx, reg_idx in INDICES_BOLSA.items():
            d_i = get_market_data(reg_idx["ticker"])
            if not d_i:
                continue
            dow = dow_theory(d_i["hist"])
            if not dow:
                continue
            with st.expander(f"{dow['color']} **{nom_idx}** — Estructura {dow['trend']} ({dow['det']})", expanded=False):
                st.plotly_chart(grafico_dow(dow, nom_idx), use_container_width=True)

# ==================== PESTAÑA 5: MANUAL OPERATIVO Y FICHAS AUDITADAS ====================
with tab_manual:
    st.subheader("📖 Catálogo Maestro Auditado (Fichas Morningstar / DFI) y Reglas de Rotación Cava")
    
    df_fichas = pd.DataFrame([
        {
            "Bloque Operativo": info["bloque"],
            "Vehículo / Fondo": nombre,
            "ISIN": info["isin"],
            "Corte CET": f"{info['hora_corte']:02d}:00h" if info["hora_corte"] < 24 else "24/7",
            "TER Neto": info["ter"],
            "Rent. 2026": info["r_2026"],
            "1 Año": info["r_1a"],
            "3 Años (Anual.)": info["r_3a"],
            "5 Años (Anual.)": info["r_5a"],
            "Volatilidad 3A": info["vol_3a"],
            "Sharpe 3A": info["sharpe_3a"],
            "Rating": info["rating"]
        }
        for nombre, info in ACTIVOS_RADAR.items()
    ])
    st.dataframe(df_fichas, use_container_width=True, hide_index=True)

    st.markdown(f"""
    ---
    ### Reglas Maestras del Roboadvisor Cava
    1. **Circuito Cerrado Fiscal en Fondos (`Art. 94 LIRPF`):**
       - El fondo **AXA Trésor Court Terme C (`{ISIN_MONETARIO_NODRIZA}`)** es la base nodriza. Todas las compras por tramos de fondos nacen como traspaso desde AXA y todas las recogidas de beneficios vuelven a AXA sin tributar un solo euro en el IRPF.
    2. **Cuándo traspasar a AXA Monetario vs. Cuándo rotar a Salud / Europa:**
       - **Crisis de liquidez sistémica (VIX > 25 o caída conjunta de S&P, World y Nasdaq):** Traspaso directo a **AXA Trésor (`{ISIN_MONETARIO_NODRIZA}`)**. En pánico de liquidez toda la bolsa cae; solo el monetario protege al 100%.
       - **Pinchazo exclusivo de múltiplos en IA / Tecnología:** Cuando el Nasdaq corrige con fuerza pero el mercado general no sufre pánico de liquidez, se rota tácticamente hacia **Wellington Global Health Care (`IE00BF2ZVB54`)** (80% farmacia EE. UU.: Eli Lilly, Merck, AbbVie) e **iShares Europe Equity Index (`LU0836512706`)** (farmacia y consumo europeo con 0,12% TER).
       - **Shock energético / Inflación de oferta:** Cobertura mediante **Guinness Global Energy (`IE00B3CCJB88`)**.
       - **Recesión deflacionaria con bajada de tipos:** Activar duración con **Vanguard Global Bond Hedged (`IE00B18GC888`)**.
    """)
