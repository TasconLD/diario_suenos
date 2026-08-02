# BLOQUE: Servicio Centralizado de Correos con Resend
import os
import resend

class EmailService:
    @staticmethod
    def _obtener_api_key():
        return os.environ.get('RESEND_API_KEY')

    @staticmethod
    def _obtener_remitente():
        return os.environ.get('MAIL_DEFAULT_SENDER', 'Entrenador Onírico <onboarding@resend.dev>')

    @classmethod
    def enviar_correo_restablecimiento(cls, email_destino: str, url_reset: str) -> bool:
        """Envia el correo con el enlace para restablecer contraseña."""
        api_key = cls._obtener_api_key()
        
        # Plantilla HTML estilizada
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <style>
                body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background-color: #f8fafc; color: #1e293b; margin: 0; padding: 20px; }}
                .container {{ max-width: 500px; margin: 0 auto; background: #ffffff; border-radius: 16px; padding: 32px; border: 1px solid #e2e8f0; shadow: 0 4px 6px -1px rgba(0,0,0,0.1); }}
                .header {{ text-align: center; margin-bottom: 24px; }}
                .title {{ color: #4f46e5; font-size: 20px; font-weight: 700; margin: 0; }}
                .btn {{ display: inline-block; background-color: #4f46e5; color: #ffffff !important; font-weight: 600; padding: 12px 24px; border-radius: 12px; text-decoration: none; margin: 20px 0; text-align: center; }}
                .footer {{ text-align: center; font-size: 12px; color: #94a3b8; margin-top: 24px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h2 class="title">Entrenador Onírico</h2>
                </div>
                <p>Hola,</p>
                <p>Has solicitado restablecer tu contraseña. Haz clic en el botón de abajo para ingresar una nueva clave de acceso:</p>
                <div style="text-align: center;">
                    <a href="{url_reset}" class="btn">Restablecer Contraseña</a>
                </div>
                <p style="font-size: 13px; color: #64748b;">Este enlace es válido por 1 hora. Si no solicitaste este cambio, puedes ignorar este correo de forma segura.</p>
                <div class="footer">
                    <p>&copy; Entrenador Onírico. Todos los derechos reservados.</p>
                </div>
            </div>
        </body>
        </html>
        """

        if not api_key:
            print(f"\n[MODO DEV - RESEND NO CONFIGURADO] Enlace Reset para {email_destino}:\n{url_reset}\n")
            return True

        try:
            resend.api_key = api_key
            params = {
                "from": cls._obtener_remitente(),
                "to": [email_destino],
                "subject": "Restablecer Contraseña - Entrenador Onírico",
                "html": html_content,
            }
            resend.Emails.send(params)
            print(f"--> [Resend] Correo de reset enviado con éxito a: {email_destino}")
            return True
        except Exception as e:
            print(f"Error enviando correo vía Resend: {e}")
            return False

    @classmethod
    def enviar_correo_verificacion(cls, email_destino: str, url_confirmacion: str) -> bool:
        """Envia el correo de confirmación de registro."""
        api_key = cls._obtener_api_key()

        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <style>
                body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background-color: #f8fafc; color: #1e293b; margin: 0; padding: 20px; }}
                .container {{ max-width: 500px; margin: 0 auto; background: #ffffff; border-radius: 16px; padding: 32px; border: 1px solid #e2e8f0; }}
                .title {{ color: #4f46e5; font-size: 20px; font-weight: 700; text-align: center; }}
                .btn {{ display: inline-block; background-color: #4f46e5; color: #ffffff !important; font-weight: 600; padding: 12px 24px; border-radius: 12px; text-decoration: none; margin: 20px 0; }}
            </style>
        </head>
        <body>
            <div class="container">
                <h2 class="title">¡Bienvenido a Entrenador Onírico!</h2>
                <p>Por favor confirma tu dirección de correo electrónico para activar completas todas las funciones de tu diario.</p>
                <div style="text-align: center;">
                    <a href="{url_confirmacion}" class="btn">Confirmar mi Correo</a>
                </div>
                <p style="font-size: 13px; color: #64748b;">Este enlace expira en 24 horas.</p>
            </div>
        </body>
        </html>
        """

        if not api_key:
            print(f"\n[MODO DEV - RESEND NO CONFIGURADO] Enlace Confirmación para {email_destino}:\n{url_confirmacion}\n")
            return True

        try:
            resend.api_key = api_key
            params = {
                "from": cls._obtener_remitente(),
                "to": [email_destino],
                "subject": "Confirma tu correo - Entrenador Onírico",
                "html": html_content,
            }
            resend.Emails.send(params)
            print(f"--> [Resend] Correo de verificación enviado con éxito a: {email_destino}")
            return True
        except Exception as e:
            print(f"Error enviando correo de verificación vía Resend: {e}")
            return False