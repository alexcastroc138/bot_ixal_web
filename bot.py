import telebot
import re
import requests
from datetime import datetime

# Configuración
TOKEN = "7566372232:AAG813aW6r4P16kWSUrJ7pil5YqKSdl_Q4k"
WEBHOOK_CREAR_CITA = "https://hook.us2.make.com/1ggwszitkn4u3nm961emr56dylwgov2j"
WEBHOOK_CONSULTAR_DISPONIBILIDAD = "https://hook.us2.make.com/77ayxl20o611ofpzu2efm5qwn6wjyefl"

bot = telebot.TeleBot(TOKEN)

# Diccionario para almacenar estados de los usuarios
usuarios = {}

def extraer_fecha_hora(texto):
    patrones = [
        r"(\d{1,2}) de (\w+) a las (\d{1,2}) ?(AM|PM|am|pm)?",
        r"(\d{1,2}) (\w+) a las (\d{1,2}) ?(AM|PM|am|pm)?"
    ]
    meses = {
        "enero": 1, "febrero": 2, "marzo": 3, "abril": 4, "mayo": 5, "junio": 6,
        "julio": 7, "agosto": 8, "septiembre": 9, "octubre": 10, "noviembre": 11, "diciembre": 12
    }

    for patron in patrones:
        coincidencia = re.search(patron, texto, re.IGNORECASE)
        if coincidencia:
            dia, mes_texto, hora, periodo = coincidencia.groups()
            mes = meses.get(mes_texto.lower())
            if mes:
                ahora = datetime.now()
                año = ahora.year
                hora = int(hora)
                if periodo:
                    if "pm" in periodo.lower() and hora < 12:
                        hora += 12
                    elif "am" in periodo.lower() and hora == 12:
                        hora = 0
                return datetime(año, mes, int(dia), hora)
    return None

def formatear_fecha_legible(fecha_iso):
    fecha_obj = datetime.strptime(fecha_iso, "%Y-%m-%dT%H:%M:%S%z")
    return fecha_obj.strftime("%-d de %B a las %-I %p")

@bot.message_handler(func=lambda message: True)
def responder(message):
    chat_id = message.chat.id
    texto = message.text.strip().lower()

    if texto in ["hola", "buenas", "buen día", "hey"]:
        usuarios[chat_id] = {"estado": "inicio"}
        bot.send_message(chat_id, "¡Hola! 😊 ¿Quieres hacer una reserva?")
        return

    if texto in ["no", "no gracias", "cancelar"]:
        bot.send_message(chat_id, "Entiendo, si necesitas algo más, estaré aquí. ¡Que tengas un buen día! 😊")
        usuarios.pop(chat_id, None)
        return

    if texto in ["sí", "si", "quiero", "reservar"]:
        usuarios[chat_id] = {"estado": "esperando_fecha"}
        bot.send_message(chat_id, "¡Genial! Dime la fecha y hora en la que te gustaría hacer tu reserva. 📅")
        return

    if usuarios.get(chat_id, {}).get("estado") == "esperando_fecha":
        fecha_hora = extraer_fecha_hora(texto)
        if fecha_hora:
            try:
                respuesta = requests.post(WEBHOOK_CONSULTAR_DISPONIBILIDAD, json={"fecha": fecha_hora.strftime("%Y-%m-%dT%H:%M:%S%z")})
                if respuesta.status_code == 200:
                    disponibilidad = respuesta.json()
                    fechas_ocupadas = [item["date"] for item in disponibilidad] if isinstance(disponibilidad, list) else []
                    fecha_solicitada_iso = fecha_hora.strftime("%Y-%m-%dT%H:%M:%S-05:00")
                    
                    if fecha_solicitada_iso not in fechas_ocupadas:
                        usuarios[chat_id]["fecha"] = fecha_hora.strftime("%Y-%m-%d %H:%M")
                        usuarios[chat_id]["estado"] = "esperando_nombre"
                        bot.send_message(chat_id, "¡Perfecto! Ahora dime tu nombre para completar la reserva. 📝")
                    else:
                        bot.send_message(chat_id, "Lo siento, esa fecha no está disponible. 😔 Por favor, elige otra fecha y hora.")
                else:
                    bot.send_message(chat_id, "Hubo un error al consultar la disponibilidad. Intenta más tarde.")
            except Exception as e:
                bot.send_message(chat_id, f"Hubo un error al consultar la disponibilidad: {str(e)}")
        else:
            bot.send_message(chat_id, "No entendí bien la fecha. Intenta con algo como '26 de febrero a las 7 AM'.")
        return

    if usuarios.get(chat_id, {}).get("estado") == "esperando_nombre":
        nombre = texto.title()
        fecha_confirmada = usuarios[chat_id]["fecha"]
        
        # Convertir la fecha confirmada al formato ISO 8601 con timezone
        fecha_iso = datetime.strptime(fecha_confirmada, "%Y-%m-%d %H:%M").strftime("%Y-%m-%dT%H:%M:%S-05:00")
        
        # Crear el JSON con la estructura deseada
        datos_reserva = {
            "name": nombre,
            "startDate": fecha_iso
        }
        
        try:
            # Enviar los datos al webhook
            respuesta = requests.post(WEBHOOK_CREAR_CITA, json=datos_reserva)
            
            # Verificar si la solicitud fue exitosa
            if respuesta.status_code == 200:
                bot.send_message(chat_id, f"¡Gracias {nombre}! 🎉 Tu cita para el {fecha_confirmada} ha sido confirmada. 📅")
                bot.send_message(chat_id, "Si necesitas hacer otra reserva, dime 'Hola' para comenzar de nuevo. 😉")
                usuarios.pop(chat_id, None)
            else:
                bot.send_message(chat_id, "Ocurrió un error al intentar crear la reserva. Inténtalo nuevamente.")
        except Exception as e:
            bot.send_message(chat_id, f"Ocurrió un error al intentar crear la reserva: {str(e)}")
        return

    bot.send_message(chat_id, "No te entendí bien. ¿Quieres hacer una reserva? Responde 'Sí' o 'No'.")

# Mantener el bot activo
bot.infinity_polling()
