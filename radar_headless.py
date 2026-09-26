"""
RADAR TIBURÓN - VERSIÓN HEADLESS v2.0
Para ejecutar en GitHub Actions y enviar alertas por email.

FIX v2.0:
- Corregido bug de acción contradictoria en BLOQUEADO
- Detección automática de hora España (verano/invierno) con zoneinfo
- El workflow se ejecuta cada 10 min y este código decide si es la hora objetivo
"""
import yfinance as yf
import pandas as pd
import numpy as np
import smtplib
import os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
try:
    from zoneinfo import ZoneInfo
    ZONA_MADRID = ZoneInfo("Europe/Madrid")
except Exception:
    ZONA_MADRID = None

# ==================== CONFIGURACIÓN DESDE SECRETOS ====================
EMAIL_REMITENTE = os.environ.get('EMAIL_REMITENTE', '')
EMAIL_PASSWORD_APP = os.environ.get('EMAIL_PASSWORD_APP', '')
EMAIL_DESTINO = os.environ.get('EMAIL_DESTINO', '')

# Ventanas horarias objetivo (hora España) para enviar el email
# Se ejecuta dos veces al día: 09:10 y 16:40
HORAS_OBJETIVO = [(9, 10), (16, 40)]
TOLERANCIA_MINUTOS = 6  # Ventana de ±6 minutos por si el cron llega con retraso

# ==================== REGLAS ====================
REGLAS = {
    "S&P 500": {"ticker": "^GSPC", "c1": -0.04, "c2": -0.10, "c3": -0.20, "v1": 0.15, "v2": 0.30, "v3": 0.40, "rsi_v1": 70, "rsi_v2": 75, "rsi_v3": 80},
    "Nasdaq 100": {"ticker": "^NDX", "c1": -0.06, "c2": -0.15, "c3": -0.25, "v1": 0.18, "v2": 0.35, "v3": 0.45, "rsi_v1": 70, "rsi_v2": 75, "rsi_v3": 80},
    "Oro": {"ticker": "GC=F", "c1": -0.04, "c2": -0.08, "c3": -0.12, "v1": 0.12, "v2": 0.22, "v3": 0.25, "rsi_v1": 70, "rsi_v2": 75, "rsi_v3": 80},
    "Bitcoin": {"ticker": "BTC-USD", "c1": -0.15, "c2": -0.30, "c3": -0.50, "v1": 0.30, "v2": 0.60, "v3": 1.00, "rsi_v1": 75, "rsi_v2": 80, "rsi_v3": 85},
}

# ==================== EXTRACCIÓN ====================
def vix():
    try:
        return float(yf.Ticker("^VIX").history(period="5d")['Close'].iloc[-1])
    except Exception:
        return 18.0


def datos(ticker):
    try:
        h = yf.Ticker(ticker).history(period="2y")
        if len(h) < 200:
            return None
        h52 = h.tail(252)
        p = float(h52['Close'].iloc[-1])
        mx = float(h52['Close'].max())
        caida = (p / mx - 1) if mx > 0 else 0
        sma200 = float(h['Close'].rolling(200).mean().iloc[-1])
        dist_sma = (p / sma200 - 1) if sma200 > 0 else 0
        delta = h52['Close'].diff()
        g = delta.clip(lower=0).ewm(alpha=1/14, adjust=False).mean()
        l = -delta.clip(upper=0).ewm(alpha=1/14, adjust=False).mean()
        rsi = float((100 - 100 / (1 + g / l.replace(0, 1e-9))).iloc[-1])
        return {
            "precio": p, "caida": caida, "sma200": sma200,
            "dist_sma": dist_sma,
            "rsi": rsi if not pd.isna(rsi) else 50.0,
        }
    except Exception:
        return None


# ==================== DECISIÓN ====================
def filtro_anti_cuchillo(d, v):
    c = abs(d["caida"])
    if c >= 0.10 and v < 13:
        return False
    if c >= 0.15 and v < 17:
        return False
    if c >= 0.25 and v < 22:
        return False
    if d["precio"] < d["sma200"] * 0.95 and v < 18:
        return False
    return True


def decidir_compra(d, reglas, v):
    caida = d["caida"]
    if caida <= reglas["c3"]:
        zona = 3
    elif caida <= reglas["c2"]:
        zona = 2
    elif caida <= reglas["c1"]:
        zona = 1
    else:
        return 0, "ESPERAR", f"Sin caída suficiente ({caida:.2%})"
    if not filtro_anti_cuchillo(d, v):
        return zona, "BLOQUEADO", f"Caída {caida:.2%} con VIX {v:.1f} — sin pánico"
    return zona, f"COMPRAR ZONA {zona}", f"Caída {caida:.2%} validada con VIX {v:.1f}"


def decidir_venta(d, reglas):
    ds, rsi = d["dist_sma"], d["rsi"]
    if ds >= reglas["v3"] and rsi >= reglas["rsi_v3"]:
        return 3, "VENTA ZONA 3", f"+{ds:.1%} sobre SMA200, RSI {rsi:.0f}"
    if ds >= reglas["v2"] and rsi >= reglas["rsi_v2"]:
        return 2, "VENTA ZONA 2", f"+{ds:.1%} sobre SMA200, RSI {rsi:.0f}"
    if ds >= reglas["v1"] and rsi >= reglas["rsi_v1"]:
        return 1, "VENTA ZONA 1", f"+{ds:.1%} sobre SMA200, RSI {rsi:.0f}"
    return 0, "MANTENER", f"Distancia sana a su media (+{ds:.1%})"


# ==================== INFORME ====================
def generar_informe():
    v = vix()
    ahora = datetime.now(ZONA_MADRID).strftime('%d/%m/%Y %H:%M') if ZONA_MADRID else datetime.now().strftime('%d/%m/%Y %H:%M')

    lineas = [
        f"🦈 RADAR TIBURÓN — {ahora}",
        f"VIX: {v:.2f}",
        "=" * 55,
        ""
    ]

    for cat, reglas in REGLAS.items():
        d = datos(reglas["ticker"])
        if not d:
            lineas.append(f"❌ {cat}: SIN DATOS")
            lineas.append("")
            continue

        zona_c, dec_c, motivo_c = decidir_compra(d, reglas, v)
        zona_v, dec_v, motivo_v = decidir_venta(d, reglas)

        # Icono según decisión
        if dec_c == "BLOQUEADO":
            icono = "🛡️"
        elif zona_c > 0:
            icono = ["🟢", "🟠", "🔴"][zona_c - 1]
        elif zona_v > 0:
            icono = ["🟡", "🟠", "🔴"][zona_v - 1]
        else:
            icono = "⚪"

        lineas.append(f"{icono} {cat}")
        lineas.append(f"   Precio: {d['precio']:,.2f} | Caída: {d['caida']:.2%} | RSI: {d['rsi']:.1f}")
        lineas.append(f"   SMA200: {d['sma200']:,.2f} | Distancia: {d['dist_sma']:+.2%}")
        lineas.append(f"   Compra: {dec_c} | Venta: {dec_v}")

        # ---- ACCIÓN DE COMPRA ----
        # FIX: Solo mostrar "Inyectar X%" si la decisión REAL es COMPRAR
        if dec_c.startswith("COMPRAR"):
            pct = [30, 30, 40][zona_c - 1]
            lineas.append(f"   👉 ACCIÓN: Inyectar {pct}% de pólvora")
        elif dec_c == "BLOQUEADO":
            lineas.append(f"   🛡️ COMPRA BLOQUEADA — {motivo_c}")
            # Añadir gatillo de desbloqueo
            vix_req = 13 if zona_c == 1 else (17 if zona_c == 2 else 22)
            lineas.append(f"   ⏱️ Gatillo: VIX > {vix_req} o recuperar SMA200")

        # ---- ACCIÓN DE VENTA ----
        # FIX: Solo mostrar "Recoger X%" si la decisión REAL es VENTA
        if dec_v.startswith("VENTA"):
            pct = [20, 30, 50][zona_v - 1]
            lineas.append(f"   👉 ACCIÓN: Recoger {pct}% de beneficios")

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


# ==================== COMPROBACIÓN DE HORA ====================
def es_hora_objetivo():
    """
    Devuelve True si la hora actual en Madrid coincide con una de las
    ventanas objetivo (09:10 o 16:40) con una tolerancia de ±6 min.

    Esto permite que el workflow se ejecute cada 10 min y solo envíe
    email cuando realmente toca, sin necesidad de cambiar el cron
    cuando cambie el horario de verano/invierno.
    """
    if ZONA_MADRID is None:
        # Fallback: si no hay zoneinfo, solo enviar siempre
        return True

    ahora = datetime.now(ZONA_MADRID)
    # Solo días laborables (L-V). El cron ya lo filtra, pero por seguridad
    if ahora.weekday() >= 5:  # 5=Sábado, 6=Domingo
        return False

    hora = ahora.hour
    minuto = ahora.minute

    for h_obj, m_obj in HORAS_OBJETIVO:
        # Calcular diferencia en minutos respecto a la hora objetivo
        diff = (hora * 60 + minuto) - (h_obj * 60 + m_obj)
        # Ventana: entre 0 y +TOLERANCIA minutos después de la hora objetivo
        # (así no envía antes de tiempo)
        if 0 <= diff <= TOLERANCIA_MINUTOS:
            return True

    return False


# ==================== MAIN ====================
if __name__ == "__main__":
    ahora_madrid = datetime.now(ZONA_MADRID) if ZONA_MADRID else datetime.now()
    print(f"🦈 Radar Tiburón — Ejecución {ahora_madrid.strftime('%d/%m/%Y %H:%M')} (hora Madrid)")

    if not es_hora_objetivo():
        print("⏸️  Fuera de ventana horaria objetivo. Saliendo sin enviar email.")
        print(f"   Ventanas configuradas (hora Madrid): {HORAS_OBJETIVO}")
        print(f"   Hora actual: {ahora_madrid.strftime('%H:%M')}")
        exit(0)

    print("🎯 Dentro de ventana objetivo. Generando informe...")
    informe = generar_informe()
    print(informe)

    asunto = f"🦈 Radar Tiburón — {ahora_madrid.strftime('%d/%m %H:%M')}"
    enviar_email(asunto, informe)