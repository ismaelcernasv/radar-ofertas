import requests
import os
import re
import json
import html
from dotenv import load_dotenv
from datetime import datetime, timezone, timedelta

zona_horaria = timezone(timedelta(hours=-6))
fecha_actual = datetime.now(zona_horaria).strftime("%d/%m/%Y %H:%M")

load_dotenv()
api_key = os.getenv("GROQ_API_KEY")
url_groq = "https://api.groq.com/openai/v1/chat/completions"
headers = {
    "Authorization": f"Bearer {api_key}",
    "Content-Type": "application/json"
}

url = "https://store.steampowered.com/api/featuredcategories"
parametros = {
    "l": "spanish",
    "cc": "us"
}

# ---------- Paso 1: pedir las ofertas a Steam ----------
try:
    respuesta = requests.get(url, params=parametros, timeout=15)
    respuesta.raise_for_status()  # si Steam responde con error, salta al except
    datos_json = respuesta.json()
    ofertas = [j for j in datos_json["specials"]["items"] if j["original_price"] > 0]
except (requests.RequestException, KeyError, ValueError) as error:
    print(f"No se pudieron obtener las ofertas de Steam: {error}")
    raise SystemExit(1)

if not ofertas:
    print("Steam no devolvió ofertas.")
    raise SystemExit(1)


def calcular_descuento(juego):
    return int((juego['original_price'] - juego['final_price']) / juego['original_price'] * 100)


def texto_fecha_fin(juego):
    expiracion = juego.get("discount_expiration")
    if not expiracion:
        return ""
    fecha_fin = datetime.fromtimestamp(expiracion, zona_horaria).strftime("%d/%m/%Y")
    return f'<p style="margin: 8px 0 0 0; color: #8f98a0; font-size: 13px;">⏳ Oferta hasta: {fecha_fin}</p>'


texto_juegos = ""
for juego in ofertas:
    descuento = calcular_descuento(juego)
    texto_juegos += f"Juego: {juego['name']}, Precio original: ${juego['original_price'] / 100:.2f}, Precio final: ${juego['final_price'] / 100:.2f}, Descuento: {descuento}%\n"

prompt = f"""Analiza las siguientes ofertas de Steam.
Elige los 3 mejores títulos para comprar y 2 títulos que convenga esperar a que bajen más de precio.
Responde SOLO con JSON válido, sin texto antes ni después, con esta forma:
{{"comprar": [{{"nombre": "...", "razon": "..."}}], "esperar": [{{"nombre": "...", "razon": "..."}}]}}
Usa el nombre del juego exactamente como aparece en la lista. Cada razón debe tener máximo 2 frases.

{texto_juegos}"""

payload = {
    "model": "qwen/qwen3.8-27b",
    "messages": [
        {"role": "system", "content": "Eres un experto en videojuegos, llamado NUKEAI. Responde siempre y únicamente en español. Nunca uses caracteres chinos ni de otros idiomas."},
        {"role": "user", "content": prompt}
    ],
    "temperature": 0.3
}

# ---------- Paso 2: cabecera y tarjetas de ofertas ----------
html_contenido = f'''<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Nuke's Radar - Ofertas de Steam</title>
</head>
<body style="background-color: #1b2838; color: #c6d4df; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; padding: 20px; display: flex; flex-wrap: wrap; justify-content: center; gap: 20px;">
<div style="width: 100%; text-align: center; margin-bottom: 20px; border-bottom: 1px solid #4c6b22; padding-bottom: 15px;">
    <h1 style="color: #a4d007; font-size: 45px; text-transform: uppercase; letter-spacing: 8px; text-shadow: 0 0 10px rgba(164, 208, 7, 0.5), 2px 2px 4px #000000; margin: 0;">☢️ NUKE'S RADAR ☢️</h1>
    <span style="color: #8f98a0; letter-spacing: 4px; font-size: 14px; text-transform: uppercase;">Steam Edition // Interceptando Ofertas</span><br>
    <span style="color: #4c6b22; font-size: 12px; font-weight: bold;">Última actualización: {fecha_actual}</span>
</div>
'''

for juego in ofertas:
    descuento = calcular_descuento(juego)

    html_contenido += f'''
    <div style="background-color: #171a21; padding: 15px; border-radius: 5px; width: 380px; max-width: 100%; box-sizing: border-box;">
        <img src="{juego['header_image']}" style="width: 100%; border-radius: 3px;">
        <h2 style="color: white;">{html.escape(juego['name'])}</h2>
        <p>Precio original: <strike>${juego['original_price'] / 100:.2f}</strike></p>
        <p style="color: #a4d007; font-size: 18px;"><b>Precio final: ${juego['final_price'] / 100:.2f}</b></p>
        <p>Descuento: <span style="background-color: #4c6b22; color: #a4d007; padding: 3px 6px; font-weight: bold;">-{descuento}%</span></p>
        {texto_fecha_fin(juego)}
        <a href="https://store.steampowered.com/app/{juego['id']}" style="background-color: #2a475e; color: #66c0f4; padding: 5px 10px; text-decoration: none; border-radius: 3px; display: inline-block; margin-top: 10px;">Ver en Steam</a>
    </div>
    '''

# ---------- Paso 3: recomendaciones de la IA ----------
juegos_por_nombre = {j["name"]: j for j in ofertas}


def tarjeta_ia(item, etiqueta, color):
    juego = juegos_por_nombre.get(item["nombre"])
    if juego is None:
        return "" 
    descuento = calcular_descuento(juego)
    return f'''
    <div style="background-color: #171a21; border-top: 3px solid {color}; border-radius: 5px; width: 340px; max-width: 100%; overflow: hidden;">
        <img src="{juego['header_image']}" style="width: 100%; display: block;">
        <div style="padding: 15px;">
            <span style="background-color: {color}; color: #000; padding: 3px 8px; font-size: 12px; font-weight: bold; letter-spacing: 2px;">{etiqueta}</span>
            <h3 style="color: white; margin: 12px 0 6px 0;">{html.escape(juego['name'])}</h3>
            <p style="margin: 0 0 10px 0; color: #a4d007; font-weight: bold;">
                ${juego['final_price'] / 100:.2f} <span style="color: #8f98a0; font-weight: normal;">(-{descuento}%)</span>
            </p>
            <p style="margin: 0; color: #c6d4df; line-height: 1.5; font-size: 15px;">{html.escape(item['razon'])}</p>
            {texto_fecha_fin(juego)}
        </div>
    </div>
    '''


print("\nConsultando a Qwen...")
try:
    respuesta_ia = requests.post(url_groq, headers=headers, json=payload, timeout=60)
    respuesta_ia.raise_for_status()
    mensaje_final = respuesta_ia.json()['choices'][0]['message']['content']

    
    coincidencia = re.search(r"\{.*\}", mensaje_final, re.DOTALL)
    recomendaciones = json.loads(coincidencia.group())

    tarjetas_comprar = ""
    for item in recomendaciones["comprar"]:
        tarjetas_comprar += tarjeta_ia(item, "COMPRAR", "#a4d007")

    tarjetas_esperar = ""
    for item in recomendaciones["esperar"]:
        tarjetas_esperar += tarjeta_ia(item, "ESPERAR", "#f0a30a")

    panel_ia = f'''
<div style="width: 100%; box-sizing: border-box; background-color: #0a0a0a; border: 1px solid #a4d007; border-radius: 5px; padding: 25px; margin-top: 30px; box-shadow: 0 0 20px rgba(164, 208, 7, 0.2);">
    <h2 style="color: #a4d007; margin-top: 0; letter-spacing: 3px; font-family: 'Courier New', monospace; text-align: center;">☢️ RECOMENDACIONES NUKE AI ☢️</h2>
    <h3 style="color: #8f98a0; letter-spacing: 2px; text-align: center;">TOP 3 PARA COMPRAR AHORA</h3>
    <div style="display: flex; flex-wrap: wrap; justify-content: center; gap: 20px;">{tarjetas_comprar}</div>
    <h3 style="color: #8f98a0; letter-spacing: 2px; margin-top: 30px; text-align: center;">MEJOR ESPERAR UN POCO</h3>
    <div style="display: flex; flex-wrap: wrap; justify-content: center; gap: 20px;">{tarjetas_esperar}</div>
</div>
'''
except (requests.RequestException, KeyError, IndexError, TypeError, AttributeError, ValueError) as error:
    print(f"No se pudieron obtener las recomendaciones de la IA: {error}")
    panel_ia = '''
<div style="width: 100%; box-sizing: border-box; background-color: #0a0a0a; border: 1px solid #f0a30a; border-radius: 5px; padding: 25px; margin-top: 30px; text-align: center;">
    <h2 style="color: #a4d007; margin-top: 0; letter-spacing: 3px; font-family: 'Courier New', monospace;">☢️ RECOMENDACIONES NUKE AI ☢️</h2>
    <p style="color: #c6d4df;">Las recomendaciones no están disponibles en este momento. Intenta de nuevo más tarde.</p>
</div>
'''

html_contenido += panel_ia
html_contenido += "</body>\n</html>"

with open("index.html", "w", encoding="utf-8") as archivo:
    archivo.write(html_contenido)

print("Listo: index.html generado.")