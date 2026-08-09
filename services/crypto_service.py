# services/crypto_service.py
# BLOQUE: Cifrado simétrico de datos sensibles (tokens OAuth, etc.)
#
# Usa Fernet (AES-128 en modo CBC + HMAC) para que valores como el
# refresh_token de Google Drive nunca queden en texto plano dentro
# de la base de datos. La clave se lee de la variable de entorno
# TOKEN_ENCRYPTION_KEY, generada una sola vez con:
#
#     python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
#
# Esa clave debe guardarse en el .env local y en las variables de
# entorno de Render. Si se pierde o se cambia, los tokens cifrados
# con la clave anterior dejan de poder descifrarse (los usuarios
# afectados simplemente deberán reconectar su Google Drive).

import os
from cryptography.fernet import Fernet, InvalidToken

_fernet_instancia = None


def _obtener_fernet():
    """Crea (una sola vez) la instancia de Fernet a partir de la clave de entorno."""
    global _fernet_instancia
    if _fernet_instancia is None:
        clave = os.environ.get("TOKEN_ENCRYPTION_KEY")
        if not clave:
            raise ValueError(
                "TOKEN_ENCRYPTION_KEY no está configurada en las variables de entorno. "
                "Genera una con: python -c \"from cryptography.fernet import Fernet; "
                "print(Fernet.generate_key().decode())\" y agrégala a tu .env / Render."
            )
        _fernet_instancia = Fernet(clave.encode())
    return _fernet_instancia


def cifrar_token(texto_plano):
    """Cifra un string (ej. refresh_token) y devuelve el resultado como string."""
    if texto_plano is None:
        return None
    f = _obtener_fernet()
    return f.encrypt(texto_plano.encode("utf-8")).decode("utf-8")


def descifrar_token(texto_cifrado):
    """
    Descifra un string previamente cifrado con cifrar_token().
    Lanza cryptography.fernet.InvalidToken si el valor no es un
    token Fernet válido (por ejemplo, si es un token legado guardado
    en texto plano antes de activar el cifrado).
    """
    if texto_cifrado is None:
        return None
    f = _obtener_fernet()
    return f.decrypt(texto_cifrado.encode("utf-8")).decode("utf-8")


__all__ = ["cifrar_token", "descifrar_token", "InvalidToken"]