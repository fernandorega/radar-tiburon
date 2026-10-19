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

st.set_page_config(page_title="🦈 Radar Tiburón Pro", page_icon="🦈", layout="wide")

# ==================== ESTILOS VISUALES (CONTRASTE) ====================
st.markdown("""
<style>
    .stAlert { border-radius: 8px; font-weight: 500; }
    div[data-testid="stMetricValue"] { font-size: 1.6rem; }
</style>
""", unsafe_allow_html=True)

# ==================== RUTAS ====================
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
    "email_activo": False,
    "email_remitente": "",
    "email_password_app": "",
    "email_destino": "",
    "telegram_activo": False,
    "telegram_bot_token": "",
    "telegram_chat_id": "",
    "ultimas_alertas": {}
})

# ==================== REGLAS CALIBRADAS ====================
REGLAS = {
    "S&P 500": {"ticker": "^GSPC", "c1": -0.04, "c2": -0.10, "c3": -0.20, "v1": 0.15, "v2": 0.30, "v3": 0.40, "rsi_v1": 70, "rsi_v2": 75, "rsi_v3": 80},
    "Nasdaq 100": {"ticker": "^NDX", "c1": -0.06, "c2": -0.15, "c3": -0.25, "v1": 0.18, "v2": 0.35, "v3": 0.45, "rsi_v1": 70, "rsi_v2": 75, "rsi_v3": 80},
    "Oro": {"ticker": "GC=F", "c1": -0.04, "c2": -0.08, "c3": -0.12, "v1": 0.12, "v2": 0.22, "v3": 0.25, "rsi_v1": 70, "rsi_v2": 75, "rsi_v3": 80},
    "Bitcoin": {"ticker": "BTC-USD", "c1": -0.15, "c2": -0.30, "c3": -0.50, "v1": 0.30, "v2": 0.60, "v3": 1.00, "rsi_v1": 75, "rsi_v2": 80, "rsi_v3": 85},
}

# ==================== CACHÉ Y EXTRACCIÓN ====================
@st.cache_data(ttl=60)
def vix():
    try: return float(yf.Ticker("^VIX").history(period="5d")['Close'].iloc[-1])
    except: return 18.0

@st.cache_data(ttl=300)
def datos(ticker):
    try:
        h = yf.Ticker(ticker).history(period="2y")
        if len(h) < 200: return None
        
        # Corrección matemática de ventana: 365 días reales para Cripto, 252 sesiones para el resto
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
        
        # Break of Structure (BOS): Cierre actual supera el máximo de las 10 sesiones anteriores
        max_10d_prev = h52['High'].shift(1).rolling(10).max().iloc[-1]
        bos = bool(p > max_10d_prev) if not pd.isna(max_10d_prev) else False
        
        # Corrección blindada contra KeyError por índice temporal (uso de iloc y get_loc)
        idx_mx = h52['High'].idxmax()
        dias_mx = (h52.index[-1] - idx_mx).days
        pos_mx = h52.index.get_loc(idx_mx)
        mn = float(h52['Close'].iloc[pos_mx:].min())
        
        return {
            "precio": p, "caida": caida, "sma200": sma200, "dist_sma": dist_sma,
            "rsi": rsi if not pd.isna(rsi) else 50.0, "max_52w": mx, "dias_desde_max": dias_mx,
            "rebote": (p/mn - 1) if mn > 0 else 0.0, "hist": h, "bos": bos
        }
    except Exception as e:
        return None

@st.cache_data(ttl=300)
def flujo(ticker):
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
        else: trend, det, color = "LATERAL", "Estructura Mixta (Incertidumbre)", "⚪"
        return {"trend": trend, "det": det, "color": color, "close": close, "m1": m1, "m2": m2, "n1": n1, "n2": n2}
    except: return None

def grafico_dow(dow, nombre):
    close = dow["close"]
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=close.index, y=close.values, mode='lines', name='Precio', line=dict(color='#3b82f6', width=2)))
    fig.add_trace(go.Scatter(
        x=[close.index[dow["m1"]], close.index[dow["m2"]]],
        y=[close.iloc[dow["m1"]], close.iloc[dow["m2"]]],
        mode='markers+text',
        name='Máximos',
        marker=dict(color='#ef4444', size=13, symbol='triangle-down'),
        text=[f"{close.iloc[dow['m1']]:.2f}", f"{close.iloc[dow['m2']]:.2f}"],
        textposition='top center',
        textfont=dict(size=12, color='#ef4444')
    ))
    fig.add_trace(go.Scatter(
        x=[close.index[dow["n1"]], close.index[dow["n2"]]],
        y=[close.iloc[dow["n1"]], close.iloc[dow["n2"]]],
        mode='markers+text',
        name='Mínimos',
        marker=dict(color='#22c55e', size=13, symbol='triangle-up'),
        text=[f"{close.iloc[dow['n1']]:.2f}", f"{close.iloc[dow['n2']]:.2f}"],
        textposition='bottom center',
        textfont=dict(size=12, color='#22c55e')
    ))
    fig.update_layout(
        title=f"{nombre} — Estructura {dow['trend']}",
        height=420,
        margin=dict(l=25, r=25, t=50, b=25),
        hovermode='x unified',
        showlegend=False,
        yaxis=dict(autorange=True, fixedrange=False)
    )
    return fig

# ==================== TIMING Y VOLUMEN ====================
def calcular_adx(hist):
    try:
        df = hist.copy()
        df['TR1'] = df['High'] - df['Low']
        df['TR2'] = (df['High'] - df['Close'].shift(1)).abs()
        df['TR3'] = (df['Low'] - df['Close'].shift(1)).abs()
        df['TR'] = df[['TR1', 'TR2', 'TR3']].max(axis=1)

        df['+DM'] = np.where((df['High'] - df['High'].shift(1)) > (df['Low'].shift(1) - df['Low']), np.maximum(df['High'] - df['High'].shift(1), 0), 0)
        df['-DM'] = np.where((df['Low'].shift(1) - df['Low']) > (df['High'] - df['High'].shift(1)), np.maximum(df['Low'].shift(1) - df['Low'], 0), 0)

        tr_s = df['TR'].ewm(alpha=1/14, adjust=False).mean()
        pdm_s = df['+DM'].ewm(alpha=1/14, adjust=False).mean()
        mdm_s = df['-DM'].ewm(alpha=1/14, adjust=False).mean()

        df['+DI'] = 100 * pdm_s / tr_s.replace(0, 1e-9)
        df['-DI'] = 100 * mdm_s / tr_s.replace(0, 1e-9)
        df['DX'] = 100 * (df['+DI'] - df['-DI']).abs() / (df['+DI'] + df['-DI']).replace(0, 1e-9)
        df['ADX'] = df['DX'].ewm(alpha=1/14, adjust=False).mean()

        return df[['+DI', '-DI', 'ADX']]
    except: return None

def evaluar_volumen(hist, ticker):
    try:
        if ticker.startswith("^"): return 1.0  # Índices sintéticos
        df = hist.copy()
        if len(df) < 20: return 1.0
        vol_sma20 = df['Volume'].rolling(20).mean().iloc[-1]
        vol_actual = df['Volume'].iloc[-1]
        return float(vol_actual / vol_sma20) if vol_sma20 > 0 else 1.0
    except: return 1.0

# ==================== LÓGICA DE DECISIÓN ====================
def filtro_anti_cuchillo(d, v):
    c = abs(d["caida"])
    if c >= 0.10 and v < 13: return False, "Bloquea si caída >= 10% y VIX < 13"
    if c >= 0.15 and v < 17: return False, "Bloquea si caída >= 15% y VIX < 17"
    if c >= 0.25 and v < 20: return False, "Bloquea si caída >= 25% y VIX < 20"
    if d["precio"] < d["sma200"] * 0.95 and v < 18: return False, "Bloquea si precio < SMA200*0.95 y VIX < 18"
    return True, "OK"

def decidir_compra(d, reglas, v, ticker):
    caida = d["caida"]
    if caida <= reglas["c3"]: zona = 3
    elif caida <= reglas["c2"]: zona = 2
    elif caida <= reglas["c1"]: zona = 1
    else: return 0, "ESPERAR", f"Falta caída. Descuento actual: {caida:.2%}."
    
    # 1. Filtro VIX Pánico para Zona 3 (Devuelve 0 para evitar alertas falsas y activar el bloque de bloqueo)
    if zona == 3 and v < 20.0:
        return 0, "BLOQUEADO VIX", f"Zona 3 requiere pánico real (VIX >= 20). VIX actual: {v:.1f}"

    # 2. Filtro Anti-Cuchillo Clásico
    seguro, motivo = filtro_anti_cuchillo(d, v)
    if not seguro: return 0, "BLOQUEADO", motivo
    
    # 3. Filtro de Volumen Antitrampa (Cava)
    ratio = evaluar_volumen(d["hist"], ticker)
    if ratio < 0.85 and not ticker.startswith("^"):
        return 0, "BLOQUEADO VOLUMEN", f"Volumen institucional débil ({ratio:.2f}x < 0.85x). Sin absorción."
        
    # 4. Quiebre de Estructura (BOS) para rebotes en caídas mayores
    if zona >= 2 and not d["bos"] and v < 25:
        return 0, "BLOQUEADO BOS", "Sin confirmación de giro diario (BOS 10d). Esperar quiebre."

    return zona, f"COMPRAR ZONA {zona}", f"Caída {caida:.2%}, VIX {v:.1f}, Vol {ratio:.2f}x. Confirmado."

def decidir_venta(d, reglas):
    ds, rsi = d["dist_sma"], d["rsi"]
    if ds >= reglas["v3"] and rsi >= reglas["rsi_v3"]: return 3, "VENTA ZONA 3", "Extremo sobrecalentamiento."
    if ds >= reglas["v2"] and rsi >= reglas["rsi_v2"]: return 2, "VENTA ZONA 2", "Fuerte sobrecalentamiento."
    if ds >= reglas["v1"] and rsi >= reglas["rsi_v1"]: return 1, "VENTA ZONA 1", "Tensión alcista."
    return 0, "MANTENER", "Dentro de parámetros sanos."

def enviar_alerta(asunto, cuerpo, forzar_email=False):
    r, c = [], config_alertas
    if c.get("email_activo") or forzar_email:
        remitente = c.get("email_remitente", "").strip()
        password = c.get("email_password_app", "").replace(" ", "").strip()
        destino = c.get("email_destino", "").strip()
        if not remitente or not password or not destino:
            return "Email: Faltan credenciales"
        try:
            msg = MIMEMultipart()
            msg['From'] = remitente
            msg['To'] = destino
            msg['Subject'] = asunto
            msg.attach(MIMEText(cuerpo, 'plain', 'utf-8'))
            with smtplib.SMTP('smtp.gmail.com', 587, timeout=15) as s:
                s.starttls()
                s.login(remitente, password)
                s.send_message(msg)
            r.append("Email: OK")
        except Exception as e:
            r.append(f"Email Error: {e}")
    if c.get("telegram_activo"):
        try:
            res = requests.post(f"https://api.telegram.org/bot{c['telegram_bot_token']}/sendMessage", data={"chat_id": c["telegram_chat_id"], "text": f"*{asunto}*\n\n{cuerpo}", "parse_mode": "Markdown"}, timeout=10)
            r.append(f"TG: {res.status_code}")
        except Exception as e: r.append(f"TG Error: {e}")
    return " | ".join(r) if r else "Sin canales activos"

def generar_resumen_completo(vix_val):
    linea = "=" * 48
    cuerpo = [
        "📊 RESUMEN EJECUTIVO — RADAR TIBURÓN PRO",
        f"Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"Macro Global (VIX): {vix_val:.2f} — {'Pánico / Estrés' if vix_val >= 20 else 'Mercado Estable'}",
        linea,
        ""
    ]
    for cat, reglas in REGLAS.items():
        d = datos(reglas["ticker"])
        if not d: continue
        zona_c, dec_c, motivo_c = decidir_compra(d, reglas, vix_val, reglas["ticker"])
        zona_v, dec_v, motivo_v = decidir_venta(d, reglas)
        fl_data = flujo(reglas["ticker"])
        sc = fl_data["score"] if fl_data else 0
        dow = dow_theory(d["hist"])
        dow_txt = f"{dow['trend']} ({dow['det']})" if dow else "N/D"
        es_fondo = cat in ["S&P 500", "Nasdaq 100"]
        tipo = "FONDO (Traspaso 5-15 días)" if es_fondo else "ETP/Crypto (Inmediato)"
        divisa = "$" if cat in ["S&P 500", "Nasdaq 100", "Oro", "Bitcoin"] else "€"
        
        cuerpo.append(f"🔹 {cat.upper()} [{tipo}]")
        cuerpo.append(f"  • Cotización: {d['precio']:,.2f} {divisa} | Descuento 52w: {d['caida']:.2%}")
        cuerpo.append(f"  • Línea Vital SMA200: {d['sma200']:,.2f} {divisa} ({d['dist_sma']:+.2%}) | RSI: {d['rsi']:.1f}")
        cuerpo.append(f"  • Señal Compra: {dec_c} -> {motivo_c}")
        cuerpo.append(f"  • Señal Venta: {dec_v} -> {motivo_v}")
        cuerpo.append(f"  • Flujo Institucional: Score {sc:+d} (OBV: {fl_data['obv_sig'] if fl_data else 'N/D'})")
        cuerpo.append(f"  • Teoría de Dow: {dow_txt}")
        cuerpo.append("")
        
    cuerpo.append(linea)
    cuerpo.append("Informe generado a petición del usuario desde Radar Tiburón Pro.")
    return "\n".join(cuerpo)

# ==================== INTERFAZ ====================
st.title("🦈 Radar DCA (Escáner de Mercado)")

c_vix, c_btn = st.columns([3, 1])
v = vix()
with c_vix:
    st.caption(f"VIX actual: **{v:.2f}** | Radar Cuantitativo Institucional.")
with c_btn:
    if st.button("🔄 Forzar Datos en Vivo"):
        st.cache_data.clear()
        st.rerun()

with st.expander("📖 LEYENDAS Y MANUAL DE USO"):
    st.markdown("""
    **ZONAS DE COMPRA (Basadas en descuento 52w real, VIX y volumen/BOS):**
    🟢 **ZONA 1:** Pullback inicial (-4% a -6%). Asignar **30%** de liquidez táctica.
    🟠 **ZONA 2:** Descuento severo (-8% a -15% / -30% BTC). Añadir **30%** (Exige BOS 10d o VIX > 25).
    🔴 **ZONA 3:** Capitulación institucional (-12% a -25% / -50% BTC). Vaciar el **40%** (Exige VIX >= 20 y Vol >= 0.85x).
    """)

tab1, tab2, tab3, tab4 = st.tabs(["🎯 Señales", "🏛️ Rayos X Institucional", "📰 Diario (Teoría de Dow)", "🔔 Avisos"])

with tab1:
    st.subheader("Semáforo del Mercado")
    alertas_hoy = []
    
    for cat, reglas in REGLAS.items():
        d = datos(reglas["ticker"])
        if not d: continue

        zona_c, dec_c, motivo_c = decidir_compra(d, reglas, v, reglas["ticker"])
        zona_v, dec_v, motivo_v = decidir_venta(d, reglas)
        
        fl_data = flujo(reglas["ticker"])
        sc = fl_data["score"] if fl_data else 0
        
        dow = dow_theory(d["hist"])
        dow_txt = f"{dow['color']} {dow['trend']}" if dow else "N/D"

        es_fondo = cat in ["S&P 500", "Nasdaq 100"]
        badge_operativo = "⏱️ TRASPASO 5-15 días" if es_fondo else "⚡ INMEDIATO (segundos)"
        divisa = "$" if cat in ["S&P 500", "Nasdaq 100", "Oro", "Bitcoin"] else "€"

        if dec_c.startswith("BLOQUEADO"): ic = "🛡️"
        elif zona_c > 0: ic = ["🟢", "🟠", "🔴"][zona_c - 1]
        elif zona_v > 0: ic = ["🟡", "🟠", "🔴"][zona_v - 1]
        else: ic = "⚪"

        with st.expander(f"{ic} **{cat}** | {badge_operativo} | {dec_c} | {dec_v} | Estructura: {dow_txt}", expanded=(zona_c > 0 or zona_v > 0 or dec_c.startswith("BLOQUEADO"))):
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Precio Real", f"{d['precio']:,.2f} {divisa}")
            c2.metric("Descuento (52w)", f"{d['caida']:.2%}")
            c3.metric("Línea Vital (SMA200)", f"{d['sma200']:,.2f} {divisa}", f"{d['dist_sma']:+.2%}")
            c4.metric("Fuerza Institucional", f"{sc:+d}")
            
            st.divider()

            # --- GATILLO DE BLOQUEO O COMPRA ---
            if dec_c.startswith("BLOQUEADO"):
                if dec_c == "BLOQUEADO VOLUMEN":
                    st.error(f"#### 🛡️ COMPRA BLOQUEADA POR FALTA DE VOLUMEN: {motivo_c}")
                    st.info("El activo está en precio de compra, pero no hay compradores institucionales. Espera a que el volumen supere 0.85x su media de 20 días.")
                elif dec_c == "BLOQUEADO BOS":
                    st.warning(f"#### 🛡️ COMPRA BLOQUEADA POR ESTRUCTURA: {motivo_c}")
                    st.info("Caída profunda sin suelo confirmado. Requiere superar el máximo de los últimos 10 días o VIX > 25.")
                elif dec_c == "BLOQUEADO VIX":
                    st.warning(f"#### 🛡️ COMPRA BLOQUEADA POR FALTA DE PÁNICO: {motivo_c}")
                    st.info("Zona 3 reservada para capitulación real (VIX >= 20). No gastes tu munición pesada en distribuciones lentas.")
                else:
                    vix_req = 13 if d["caida"] > reglas["c2"] else (17 if d["caida"] > reglas["c3"] else 20)
                    p_gatillo = d['max_52w'] * 0.75
                    caida_req = ((d['precio'] - p_gatillo) / d['precio']) * 100 if d['precio'] > p_gatillo else 0.0
                    
                    st.warning(f"#### 🛡️ COMPRA BLOQUEADA: {motivo_c}")
                    st.markdown(f"""
                    **Gatillo de Desbloqueo:**
                    1. VIX necesario: **{vix_req}** (Actual: {v:.1f})
                    2. Precio gatillo (Capitulación total): **{p_gatillo:,.2f} {divisa}**
                    3. Caída adicional necesaria: **-{caida_req:.2f}%**
                    4. Escenarios: 🅰️ Sube VIX 🅱️ Cae al gatillo 🅲 Rompe estructura (BOS)
                    """)
            
            elif zona_c > 0:
                st.success(f"#### {ic} {dec_c}: {motivo_c}")
                ratio = evaluar_volumen(d['hist'], reglas["ticker"])
                vol_color = "🟢" if ratio >= 1.0 else "🟡"
                
                st.markdown(f"""
                **{vol_color} Filtro de Volumen Validado:**
                - Ratio de volumen vs Media 20d: **{ratio:.2f}x**
                - 👉 **Acción:** Ejecuta la orden correspondiente al tramo.
                """)
                
                clave = f"{cat}_c{zona_c}"
                if config_alertas.get("ultimas_alertas", {}).get(clave) != datetime.now().strftime("%Y-%m-%d"):
                    alertas_hoy.append((cat, dec_c, f"Caída: {d['caida']:.2%}\nRatio vol: {ratio:.2f}x"))
                    config_alertas.setdefault("ultimas_alertas", {})[clave] = datetime.now().strftime("%Y-%m-%d")

            # --- AVISO PREVENTIVO PARA FONDOS ---
            if dec_c == "ESPERAR" and zona_c == 0:
                umbral_z1 = reglas["c1"]
                caida_actual = d["caida"]
                caida_restante = abs(caida_actual - umbral_z1) * 100
                
                if es_fondo and caida_restante < 3:
                    st.warning(f"⏱️ **AVISO DE ANTICIPACIÓN — FONDO (ejecución 5-15 días)**\n\nEstás a **{caida_restante:.2f}%** de activar la Zona 1. Prepara el traspaso con antelación.")
                elif not es_fondo and caida_restante < 2:
                    st.info(f"⚡ **PRÓXIMO A SEÑAL — ETF/ETP**\n\nEstás a **{caida_restante:.2f}%** de activar la Zona 1. Espera a la señal exacta.")

            # --- VENTA ---
            if zona_v > 0:
                st.warning(f"#### {['🟡', '🟠', '🔴'][zona_v-1]} {dec_v}: {motivo_v}")
                df_adx = calcular_adx(d['hist'])
                if df_adx is not None:
                    adx_act, adx_3d = df_adx['ADX'].iloc[-1], df_adx['ADX'].iloc[-4]
                    di_p, di_m = df_adx['+DI'].iloc[-1], df_adx['-DI'].iloc[-1]
                    di_p_prev, di_m_prev = df_adx['+DI'].iloc[-2], df_adx['-DI'].iloc[-2]
                    
                    if adx_act > 40 and adx_act < adx_3d: adx_c, adx_txt = "🟢", "VENTA CONFIRMADA"
                    elif 25 <= adx_act <= 40 and (di_p < di_m and di_p_prev >= di_m_prev): adx_c, adx_txt = "🟡", "VENTA PARCIAL"
                    else: adx_c, adx_txt = "🔴", "SIN CONFIRMACIÓN (mantener)"
                    
                    if es_fondo: msg_accion = "Inicia traspaso al monetario sin coste fiscal."
                    else: msg_accion = "Vender implica tributar al 19-28%. Confirmar con 3 días de ADX bajando antes de ejecutar."
                    
                    st.markdown(f"""
                    **{adx_c} ADX Timing de Venta (Wilder 14):**
                    - Valor ADX: **{adx_act:.1f}** | +DI: **{di_p:.1f}** | -DI: **{di_m:.1f}**
                    - Estado Técnico: **{adx_txt}**
                    - 👉 **Sugerencia:** {msg_accion}
                    """)
                    
                    clave = f"{cat}_v{zona_v}"
                    if config_alertas.get("ultimas_alertas", {}).get(clave) != datetime.now().strftime("%Y-%m-%d"):
                        alertas_hoy.append((cat, dec_v, f"ADX: {adx_act:.1f} ({adx_txt})\n\nAcción sugerida: {msg_accion}"))
                        config_alertas.setdefault("ultimas_alertas", {})[clave] = datetime.now().strftime("%Y-%m-%d")

    if alertas_hoy:
        for cat, asunto, cuerpo in alertas_hoy:
            enviar_alerta(f"🦈 Radar: {cat} — {asunto}", cuerpo)
        guardar_json(F_ALERTAS, config_alertas)
        st.success(f"📤 {len(alertas_hoy)} alertas enviadas.")

with tab2:
    st.subheader("Rayos X Institucional")
    for cat, reglas in REGLAS.items():
        fl_data = flujo(reglas["ticker"])
        if not fl_data: continue
        ic = "🟢" if fl_data['score'] >= 2 else "⚪" if fl_data['score'] >= 0 else "🔴"
        with st.expander(f"{ic} **{cat}** — Score Institucional: {fl_data['score']:+d}", expanded=True):
            c1, c2, c3 = st.columns(3)
            c1.metric("Presión (OBV / Vol)", f"{fl_data['obv']:+.1%}", fl_data["obv_sig"])
            c2.metric("Cierres (A/D / Vol)", f"{fl_data['ad']:+.1%}", fl_data["ad_sig"])
            c3.metric("Precio Tiburón (VWAP)", f"{fl_data['vwap']:,.2f}", f"{fl_data['dist_vwap']:+.2f}%")

with tab3:
    st.subheader("📰 Diario: Teoría de Dow")
    for cat, reglas in REGLAS.items():
        d = datos(reglas["ticker"])
        if not d: continue
        dow = dow_theory(d["hist"])
        if not dow: continue
        with st.expander(f"{dow['color']} **{cat}** — {dow['trend']}", expanded=True):
            st.plotly_chart(grafico_dow(dow, cat), use_container_width=True)

with tab4:
    st.subheader("🔔 Configuración de Alertas")
    with st.form("alertas"):
        ea = st.checkbox("Activar Email", value=config_alertas.get("email_activo", False))
        er = st.text_input("Correo Remitente", value=config_alertas.get("email_remitente", ""))
        ep = st.text_input("Contraseña de Aplicación", value=config_alertas.get("email_password_app", ""))
        ed = st.text_input("Correo Destino", value=config_alertas.get("email_destino", ""))
        if st.form_submit_button("💾 Guardar Datos"):
            config_alertas.update({"email_activo": ea, "email_remitente": er.strip(), "email_password_app": ep.replace(" ","").strip(), "email_destino": ed.strip()})
            guardar_json(F_ALERTAS, config_alertas)
            st.success("Guardado.")
            st.rerun()

    st.divider()
    st.subheader("📬 Enviar Informe Completo Bajo Demanda")
    st.caption("Genera y envía un correo con el estado macro global, los semáforos de compra/venta, flujo institucional y la estructura de Dow Theory.")
    
    if st.button("📊 Enviar Informe Completo al Email"):
        with st.spinner("Compilando métricas y conectando con el servidor de correo..."):
            resumen = generar_resumen_completo(v)
            res = enviar_alerta(
                f"🦈 Radar Tiburón Pro: Informe de Mercado ({datetime.now().strftime('%d/%m/%Y')})",
                resumen,
                forzar_email=True
            )
            if "Email: OK" in res:
                st.success(f"🎉 Informe completo enviado a {config_alertas.get('email_destino')}. Revisa tu bandeja de entrada.")
            else:
                st.error(f"❌ Fallo al enviar el informe: {res}")

    st.divider()
    st.subheader("🧪 Comprobación Rápida")
    st.caption("Envía un ping básico de comprobación técnica.")
    if st.button("📨 Enviar ping de prueba"):
        with st.spinner("Comprobando conexión SMTP..."):
            res = enviar_alerta(
                "🦈 Radar Tiburón Pro: Prueba Técnica",
                f"¡Ping exitoso!\nFecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\nVIX actual: {v:.2f}",
                forzar_email=True
            )
            if "Email: OK" in res:
                st.success(f"🎉 Correo de prueba enviado a {config_alertas.get('email_destino')}.")
            else:
                st.error(f"❌ Fallo en el envío: {res}")
