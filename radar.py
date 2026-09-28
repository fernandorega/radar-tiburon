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

st.set_page_config(page_title="🦈 Radar Tiburón", page_icon="🦈", layout="wide")

# ==================== ESTILOS VISUALES (CONTRASTE) ====================
st.markdown("""
<style>
    .stAlert {
        border-radius: 8px;
        font-weight: 500;
    }
    div[data-testid="stMetricValue"] {
        font-size: 1.6rem;
    }
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

# ==================== REGLAS ACTUALES ====================
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
        h52 = h.tail(252)
        p = float(h52['Close'].iloc[-1])
        mx = float(h52['Close'].max())
        caida = (p/mx - 1) if mx > 0 else 0
        sma200 = float(h['Close'].rolling(200).mean().iloc[-1])
        dist_sma = (p/sma200 - 1) if sma200 > 0 else 0
        delta = h52['Close'].diff()
        g = delta.clip(lower=0).ewm(alpha=1/14, adjust=False).mean()
        l = -delta.clip(upper=0).ewm(alpha=1/14, adjust=False).mean()
        rsi = float((100 - 100/(1 + g/l.replace(0,1e-9))).iloc[-1])
        idx_mx = h52['Close'].idxmax()
        dias_mx = (h52.index[-1] - idx_mx).days
        mn = float(h52['Close'].loc[idx_mx:].min())
        return {"precio": p, "caida": caida, "sma200": sma200, "dist_sma": dist_sma, "rsi": rsi if not pd.isna(rsi) else 50.0, "max_52w": mx, "dias_desde_max": dias_mx, "rebote": (p/mn - 1) if mn > 0 else 0, "hist": h}
    except: return None

@st.cache_data(ttl=300)
def flujo(ticker):
    try:
        h = yf.Ticker(ticker).history(period="1y")
        if len(h) < 60: return None
        d = h.copy()
        
        # Normalización matemática por volumen real acumulado de 20 sesiones
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

# ==================== FUNCIONES DE TIMING ====================
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

def evaluar_volumen(hist):
    try:
        df = hist.copy()
        if len(df) < 20: return 1.0
        vol_sma20 = df['Volume'].rolling(20).mean().iloc[-1]
        vol_actual = df['Volume'].iloc[-1]
        return vol_actual / vol_sma20 if vol_sma20 > 0 else 1.0
    except: return 1.0

# ==================== LÓGICA DE DECISIÓN ====================
def filtro_anti_cuchillo(d, v):
    c = abs(d["caida"])
    if c >= 0.10 and v < 13: return False, "Bloquea si caída >= 10% y VIX < 13"
    if c >= 0.15 and v < 17: return False, "Bloquea si caída >= 15% y VIX < 17"
    if c >= 0.25 and v < 22: return False, "Bloquea si caída >= 25% y VIX < 22"
    if d["precio"] < d["sma200"] * 0.95 and v < 18: return False, "Bloquea si precio < SMA200*0.95 y VIX < 18"
    return True, "OK"

def decidir_compra(d, reglas, v):
    caida = d["caida"]
    if caida <= reglas["c3"]: zona = 3
    elif caida <= reglas["c2"]: zona = 2
    elif caida <= reglas["c1"]: zona = 1
    else: return 0, "ESPERAR", f"Falta caída. Descuento actual: {caida:.2%}."
    seguro, motivo = filtro_anti_cuchillo(d, v)
    if not seguro: return zona, "BLOQUEADO", motivo
    return zona, f"COMPRAR ZONA {zona}", "Señal activada por reglas de caída y VIX."

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
            return "Email: Faltan credenciales (remitente, contraseña o destino)"
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
    return " | ".join(r) if r else "Sin canales activos (marca la casilla 'Activar Email' y guarda)"

def generar_resumen_completo(vix_val):
    linea = "=" * 48
    cuerpo = [
        "📊 RESUMEN EJECUTIVO — RADAR TIBURÓN",
        f"Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"Macro Global (VIX): {vix_val:.2f} — {'Pánico / Estrés' if vix_val >= 20 else 'Mercado Estable'}",
        linea,
        ""
    ]
    for cat, reglas in REGLAS.items():
        d = datos(reglas["ticker"])
        if not d: continue
        zona_c, dec_c, motivo_c = decidir_compra(d, reglas, vix_val)
        zona_v, dec_v, motivo_v = decidir_venta(d, reglas)
        fl_data = flujo(reglas["ticker"])
        sc = fl_data["score"] if fl_data else 0
        dow = dow_theory(d["hist"])
        dow_txt = f"{dow['trend']} ({dow['det']})" if dow else "N/D"
        es_fondo = cat in ["S&P 500", "Nasdaq 100"]
        tipo = "FONDO (Traspaso 5-15 días)" if es_fondo else "ETP (Inmediato)"
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
    cuerpo.append("Informe generado a petición del usuario desde Radar DCA.")
    return "\n".join(cuerpo)

# ==================== INTERFAZ ====================
st.title("🦈 Radar DCA (Escáner de Mercado)")
v = vix()
st.caption(f"VIX actual: **{v:.2f}** | Radar puramente matemático y stateless.")

with st.expander("📖 LEYENDAS Y MANUAL DE USO (Haz clic para leer)"):
    st.markdown("""
    **ZONAS DE COMPRA (Basadas en el descuento)**
    🟢 **ZONA 1:** Caída leve. Destina el **30%** de tu presupuesto.
    🟠 **ZONA 2:** Sangre en las calles. Añade otro **30%**.
    🔴 **ZONA 3:** Pánico absoluto. Vacía el cargador con el **40%**.
    
    **ZONAS DE VENTA (Basadas en la sobrecompra)**
    🟡 **ZONA 1:** Euforia inicial. Vende un **20%** para recuperar liquidez.
    🟠 **ZONA 2:** Sobrecalentamiento. Vende un **30%**.
    🔴 **ZONA 3:** Burbuja técnica. Vende un **50%**.
    """)

tab1, tab2, tab3, tab4 = st.tabs(["🎯 Señales", "🏛️ Rayos X Institucional", "📰 Diario (Teoría de Dow)", "🔔 Avisos"])

with tab1:
    st.subheader("Semáforo del Mercado")
    alertas_hoy = []
    
    for cat, reglas in REGLAS.items():
        d = datos(reglas["ticker"])
        if not d: continue

        zona_c, dec_c, motivo_c = decidir_compra(d, reglas, v)
        zona_v, dec_v, motivo_v = decidir_venta(d, reglas)
        
        fl_data = flujo(reglas["ticker"])
        sc = fl_data["score"] if fl_data else 0
        
        dow = dow_theory(d["hist"])
        dow_txt = f"{dow['color']} {dow['trend']}" if dow else "N/D"

        es_fondo = cat in ["S&P 500", "Nasdaq 100"]
        badge_operativo = "⏱️ TRASPASO 5-15 días" if es_fondo else "⚡ INMEDIATO (segundos)"
        divisa = "$" if cat in ["S&P 500", "Nasdaq 100", "Oro", "Bitcoin"] else "€"

        if dec_c == "BLOQUEADO": ic = "🛡️"
        elif zona_c > 0: ic = ["🟢", "🟠", "🔴"][zona_c - 1]
        elif zona_v > 0: ic = ["🟡", "🟠", "🔴"][zona_v - 1]
        else: ic = "⚪"

        with st.expander(f"{ic} **{cat}** | {badge_operativo} | {dec_c} | {dec_v} | Estructura: {dow_txt}", expanded=(zona_c > 0 or zona_v > 0 or dec_c == "BLOQUEADO")):
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Precio Real", f"{d['precio']:,.2f} {divisa}")
            c2.metric("Descuento (52w)", f"{d['caida']:.2%}")
            c3.metric("Línea Vital (SMA200)", f"{d['sma200']:,.2f} {divisa}", f"{d['dist_sma']:+.2%}")
            c4.metric("Fuerza Institucional", f"{sc:+d}")
            
            st.divider()

            # --- GATILLO DE DESBLOQUEO ---
            if dec_c == "BLOQUEADO":
                vix_req = 13 if zona_c == 1 else (17 if zona_c == 2 else (22 if zona_c == 3 else 18))
                p_gatillo = d['max_52w'] * 0.75
                caida_req = ((d['precio'] - p_gatillo) / d['precio']) * 100 if d['precio'] > p_gatillo else 0.0
                
                st.warning(f"#### 🛡️ COMPRA BLOQUEADA: {motivo_c}")
                st.markdown(f"""
                **Gatillo de Desbloqueo (Zona {zona_c if zona_c > 0 else 'Base'}):**
                1. VIX necesario: **{vix_req}**
                2. Diferencia actual: **Faltan {(vix_req - v):.2f} puntos de VIX**
                3. Precio gatillo (Capitulación total): **{p_gatillo:,.2f} {divisa}**
                4. Caída adicional necesaria: **-{caida_req:.2f}%** desde el precio de hoy
                5. **Tres escenarios de desbloqueo posibles:**
                   - 🅰️ VIX sube al necesario manteniendo precio → *desbloqueo por pánico*
                   - 🅱️ Precio cae al gatillo de capitulación con VIX actual → *desbloqueo por caída extrema*
                   - 🅲 Activo recupera SMA200 con volumen → *reconsideración al alza*
                """)
            
            # --- VOLUMEN DE ENTRADA ---
            elif zona_c > 0:
                st.success(f"#### {ic} {dec_c}: {motivo_c}")
                ratio = evaluar_volumen(d['hist'])
                if ratio > 1.3: vol_color, ratio_txt, vol_act = "🟢", "Volumen fuerte", "Ejecuta la compra completa ahora"
                elif ratio >= 1.0: vol_color, ratio_txt, vol_act = "🟡", "Volumen normal", "Ejecuta el 100% (volumen normal aceptable)"
                else: vol_color, ratio_txt, vol_act = "🔴", "Volumen débil", "Ejecuta el 50% ahora, el 50% esperando confirmación de volumen en 2-3 días"
                
                st.markdown(f"""
                **{vol_color} Filtro de Volumen de Entrada:**
                - Ratio de volumen vs Media 20d: **{ratio:.2f}x** ({ratio_txt})
                - 👉 **Sugerencia:** {vol_act}
                """)
                
                clave = f"{cat}_c{zona_c}"
                if config_alertas.get("ultimas_alertas", {}).get(clave) != datetime.now().strftime("%Y-%m-%d"):
                    alertas_hoy.append((cat, dec_c, f"Caída: {d['caida']:.2%}\nRatio vol: {ratio:.2f}x\n\nAcción sugerida: {vol_act}"))
                    config_alertas.setdefault("ultimas_alertas", {})[clave] = datetime.now().strftime("%Y-%m-%d")

            # --- AVISO DE ANTICIPACIÓN OPERATIVA ---
            if dec_c == "ESPERAR" and zona_c == 0:
                umbral_z1 = reglas["c1"]
                caida_actual = d["caida"]
                caida_restante = abs(caida_actual - umbral_z1) * 100
                
                if es_fondo and caida_restante < 3:
                    st.warning(f"""
                    ⏱️ **AVISO DE ANTICIPACIÓN — FONDO (ejecución 5-15 días)**
                    
                    Estás a **{caida_restante:.2f}%** de activar la Zona 1.
                    
                    Como este activo es un fondo que tarda **5-15 días** en ejecutarse, debes preparar el traspaso con antelación. Si esperas a que salte la señal exacta, cuando se procese la orden el precio habrá cambiado.
                    
                    **Acción preventiva:** prepara la orden en MyInvestor ahora y ejecútala cuando veas la confirmación.
                    """)
                
                if not es_fondo and caida_restante < 2:
                    st.info(f"""
                    ⚡ **PRÓXIMO A SEÑAL — ETF/ETP (ejecución inmediata)**
                    
                    Estás a **{caida_restante:.2f}%** de activar la Zona 1.
                    
                    Como es un ETF/ETP de ejecución instantánea, **puedes esperar a la señal exacta** sin riesgo operativo. Precio de ejecución = precio del momento.
                    """)

            # --- ADX PARA VENTA ---
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
                    
                    if es_fondo: msg_accion = "Inicia traspaso al monetario sin coste fiscal. Tiempo ejecución: 2-5 días intra-gestora, 8-15 días entre gestoras."
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
            
            if zona_c == 0 and zona_v == 0 and dec_c != "BLOQUEADO":
                st.info(f"#### 💤 ESPERAR\nNo hay señales activas de entrada ni de salida.")

    if alertas_hoy:
        for cat, asunto, cuerpo in alertas_hoy:
            enviar_alerta(f"🦈 Radar: {cat} — {asunto}", cuerpo)
        guardar_json(F_ALERTAS, config_alertas)
        st.success(f"📤 {len(alertas_hoy)} alertas enviadas")

with tab2:
    st.subheader("Rayos X Institucional")
    for cat, reglas in REGLAS.items():
        fl_data = flujo(reglas["ticker"])
        if not fl_data: continue
        ic = "🟢" if fl_data['score'] >= 2 else "⚪" if fl_data['score'] >= 0 else "🔴"
        with st.expander(f"{ic} **{cat}** — Score Institucional Total: {fl_data['score']:+d}", expanded=True):
            c1, c2, c3 = st.columns(3)
            c1.metric("1. Presión (OBV / Vol)", f"{fl_data['obv']:+.1%}", fl_data["obv_sig"])
            c2.metric("2. Cierres (A/D / Vol)", f"{fl_data['ad']:+.1%}", fl_data["ad_sig"])
            c3.metric("3. Precio Tiburón (VWAP)", f"{fl_data['vwap']:,.2f}", f"{fl_data['dist_vwap']:+.2f}%")

with tab3:
    st.subheader("📰 Diario: Teoría de Dow")
    for cat, reglas in REGLAS.items():
        d = datos(reglas["ticker"])
        if not d: continue
        dow = dow_theory(d["hist"])
        if not dow: continue
        with st.expander(f"{dow['color']} **{cat}** — Tendencia {dow['trend']}", expanded=True):
            st.markdown(f"**Estructura actual:** `{dow['det']}`")
            st.plotly_chart(grafico_dow(dow, cat), use_container_width=True)

with tab4:
    st.subheader("🔔 Configuración de Alertas por Correo")
    
    with st.form("alertas"):
        ea = st.checkbox("Activar Email", value=config_alertas.get("email_activo", False))
        er = st.text_input("Tu Correo Remitente (Gmail)", value=config_alertas.get("email_remitente", ""))
        ep = st.text_input("Contraseña de Aplicación de Google", value=config_alertas.get("email_password_app", ""), help="Puedes pegarla con o sin espacios; el sistema los eliminará automáticamente al guardar.")
        ed = st.text_input("Correo Destino", value=config_alertas.get("email_destino", ""))
        
        if st.form_submit_button("💾 Guardar Datos"):
            ep_limpia = ep.replace(" ", "").strip()
            config_alertas.update({
                "email_activo": ea,
                "email_remitente": er.strip(),
                "email_password_app": ep_limpia,
                "email_destino": ed.strip()
            })
            guardar_json(F_ALERTAS, config_alertas)
            st.success("✅ Datos guardados correctamente. Espacios en contraseña eliminados.")
            st.rerun()

    st.divider()
    st.subheader("📬 Enviar Informe Completo Bajo Demanda")
    st.caption("Genera y envía un correo con el estado macro global, los semáforos de compra/venta, flujo institucional y la estructura de Dow Theory.")
    
    if st.button("📊 Enviar Informe Completo al Email"):
        with st.spinner("Compilando métricas y conectando con el servidor de correo..."):
            resumen = generar_resumen_completo(v)
            res = enviar_alerta(
                f"🦈 Radar Tiburón: Informe de Mercado ({datetime.now().strftime('%d/%m/%Y')})",
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
                "🦈 Radar Tiburón: Prueba Técnica",
                f"¡Ping exitoso!\nFecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\nVIX actual: {v:.2f}",
                forzar_email=True
            )
            if "Email: OK" in res:
                st.success(f"🎉 Correo de prueba enviado a {config_alertas.get('email_destino')}.")
            else:
                st.error(f"❌ Fallo en el envío: {res}")
