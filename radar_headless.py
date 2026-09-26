"""
RADAR TIBURÓN - VERSIÓN HEADLESS (SIN STREAMLIT)
Para ejecutar en GitHub Actions y enviar alertas por email
"""
import yfinance as yf
import pandas as pd
import numpy as np
import smtplib
import os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime

# ==================== CONFIGURACIÓN DESDE SECRETOS ====================
EMAIL_REMITENTE = os.environ.get('EMAIL_REMITENTE', '')
EMAIL_PASSWORD_APP = os.environ.get('EMAIL_PASSWORD_APP', '')
EMAIL_DESTINO = os.environ.get('EMAIL_DESTINO', '')

# ==================== REGLAS ====================
REGLAS = {
    "S&P 500": {"ticker": "^GSPC", "c1": -0.04, "c2": -0.10, "c3": -0.20, "v1": 0.15, "v2": 0.30, "v3": 0.40, "rsi_v1": 70, "rsi_v2": 75, "rsi_v3": 80},
    "Nasdaq 100": {"ticker": "^NDX", "c1": -0.06, "c2": -0.15, "c3": -0.25, "v1": 0.18, "v2": 0.35, "v3": 0.45, "rsi_v1": 70, "rsi_v2": 75, "rsi_v3": 80},
    "Oro": {"ticker": "GC=F", "c1": -0.04, "c2": -0.08, "c3": -0.12, "v1": 0.12, "v2": 0.22, "v3": 0.25, "rsi_v1": 70, "rsi_v2": 75, "rsi_v3": 80},
    "Bitcoin": {"ticker": "BTC-USD", "c1": -0.15, "c2": -0.30, "c3": -0.50, "v1": 0.30, "v2": 0.60, "v3": 1.00, "rsi_v1": 75, "rsi_v2": 80, "rsi_v3": 85},
}

# ==================== EXTRACCIÓN ====================
def vix():
    try: return float(yf.Ticker("^VIX").history(period="5d")['Close'].iloc[-1])
    except: return 18.0

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
        return {"precio": p, "caida": caida, "sma200": sma200, "dist_sma": dist_sma, "rsi": rsi if not pd.isna(rsi) else 50.0}
    except: return None

# ==================== DECISIÓN ====================
def filtro_anti_cuchillo(d, v):
    c = abs(d["caida"])
    if c >= 0.10 and v < 13: return False
    if c >= 0.15 and v < 17: return False
    if c >= 0.25 and v < 22: return False
    if d["precio"] < d["sma200"] * 0.95 and v < 18: return False
    return True

def decidir_compra(d, reglas, v):
    caida = d["caida"]
    if caida <= reglas["c3"]: zona = 3
    elif caida <= reglas["c2"]: zona = 2
    elif caida <= reglas["c1"]: zona = 1
    else: return 0, "ESPERAR", ""
    if not filtro_anti_cuchillo(d, v): return zona, "BLOQUEADO", ""
    return zona, f"COMPRAR ZONA {zona}", ""

def decidir_venta(d, reglas):
    ds, rsi = d["dist_sma"], d["rsi"]
    if ds >= reglas["v3"] and rsi >= reglas["rsi_v3"]: return 3, "VENTA ZONA 3", ""
    if ds >= reglas["v2"] and rsi >= reglas["rsi_v2"]: return 2, "VENTA ZONA 2", ""
    if ds >= reglas["v1"] and rsi >= reglas["rsi_v1"]: return 1, "VENTA ZONA 1", ""
    return 0, "MANTENER", ""

# ==================== INFORME ====================
def generar_informe():
    v = vix()
    ahora = datetime.now().strftime('%d/%m/%Y %H:%M')
    lineas = [
        f"🦈 RADAR TIBURÓN — {ahora}",
        f"VIX: {v:.2f}",
        "=" * 50,
        ""
    ]

    for cat, reglas in REGLAS.items():
        d = datos(reglas["ticker"])
        if not d:
            lineas.append(f"❌ {cat}: SIN DATOS")
            continue

        zona_c, dec_c, _ = decidir_compra(d, reglas, v)
        zona_v, dec_v, _ = decidir_venta(d, reglas)

        icono = "🟢" if zona_c > 0 else "🛡️" if dec_c == "BLOQUEADO" else "🔴" if zona_v > 0 else "⚪"
        lineas.append(f"{icono} {cat}")
        lineas.append(f"   Precio: {d['precio']:,.2f} | Caída: {d['caida']:.2%} | RSI: {d['rsi']:.1f}")
        lineas.append(f"   SMA200: {d['sma200']:,.2f} | Distancia: {d['dist_sma']:+.2%}")
        lineas.append(f"   Compra: {dec_c} | Venta: {dec_v}")

        if zona_c > 0:
            lineas.append(f"   👉 ACCIÓN: Inyectar {[30,30,40][zona_c-1]}% de pólvora")
        if zona_v > 0:
            lineas.append(f"   👉 ACCIÓN: Recoger {[20,30,50][zona_v-1]}% de beneficios")

        lineas.append("")

    return "\n".join(lineas)

# ==================== ENVÍO ====================
def enviar_email(asunto, cuerpo):
    if not EMAIL_REMITENTE or not EMAIL_PASSWORD_APP:
        print("❌ Faltan credenciales de email")
        return False

    try:
        msg = MIMEMultipart()
        msg['From'] = EMAIL_REMITENTE
        msg['To'] = EMAIL_DESTINO or EMAIL_REMITENTE
        msg['Subject'] = asunto
        msg.attach(MIMEText(cuerpo, 'plain', 'utf-8'))

        with smtplib.SMTP('smtp.gmail.com', 587) as s:
            s.starttls()
            s.login(EMAIL_REMITENTE, EMAIL_PASSWORD_APP)
            s.send_message(msg)

        print("✅ Email enviado")
        return True
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

# ==================== MAIN ====================
if __name__ == "__main__":
    print(f"🦈 Radar Tiburón — {datetime.now().strftime('%d/%m/%Y %H:%M')}")
    informe = generar_informe()
    print(informe)

    asunto = f"🦈 Radar Tiburón — {datetime.now().strftime('%d/%m %H:%M')}"
    enviar_email(asunto, informe)