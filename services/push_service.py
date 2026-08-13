import os
import json
from datetime import datetime
from zoneinfo import ZoneInfo 
from pywebpush import webpush, WebPushException
from apscheduler.schedulers.background import BackgroundScheduler
from config import Config
from services.logger import obtener_logger

logger = obtener_logger("push_service")

def cargar_suscripciones(filepath):
    if os.path.exists(filepath):
        with open(filepath, 'r', encoding='utf-8') as f:
            try:
                return json.load(f)
            except Exception:
                return {}
    return {}

def guardar_suscripciones(filepath, data):
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2)

def enviar_push(subscription_info, titulo, mensaje, tag="general"):
    try:
        payload = json.dumps({
            "title": titulo,
            "body": mensaje,
            "tag": tag,
            "url": "/recordatorios"
        })
        webpush(
            subscription_info=subscription_info,
            data=payload,
            vapid_private_key=Config.VAPID_PRIVATE_KEY,
            vapid_claims=Config.VAPID_CLAIMS
        )
        return True
    except WebPushException as ex:
        logger.error(f"Error enviando Push: {ex}")
        return False

def iniciar_scheduler(subscriptions_file):
    def verificar_recordatorios():
        ahora = datetime.now(ZoneInfo("America/Bogota"))
        hora_actual = ahora.strftime("%H:%M")
        minutos_del_dia = ahora.hour * 60 + ahora.minute

        suscripciones = cargar_suscripciones(subscriptions_file)
        for key, item in list(suscripciones.items()):
            sub = item.get('subscription')
            cfg = item.get('config', {})

            if cfg.get('notif_matutino') and cfg.get('hora_matutino') == hora_actual:
                enviar_push(sub, "☀️ ¡Buenos días!", "No olvides registrar tu sueño antes de que se borre de tu memoria.", "matutino")

            if cfg.get('notif_nocturno') and cfg.get('hora_nocturno') == hora_actual:
                enviar_push(sub, "🌙 Repaso Nocturno", "Repasa tus objetivos e intenciones antes de dormir.", "nocturno")

            if cfg.get('notif_rc'):
                frec = int(cfg.get('frec_rc', 120))
                if minutos_del_dia > 0 and minutos_del_dia % frec == 0:
                    enviar_push(sub, "👁️ Reality Check", "¿Estás soñando ahora mismo? Revisa tus manos o mira un reloj.", "rc")

    scheduler = BackgroundScheduler()
    scheduler.add_job(func=verificar_recordatorios, trigger="interval", minutes=1)
    scheduler.start()
    return scheduler