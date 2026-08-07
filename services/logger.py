# BLOQUE: Servicio Centralizado de Logging
import logging
import os

def obtener_logger(nombre: str = "diario_suenos") -> logging.Logger:
    """
    Configura y retorna una instancia del logger centralizado.
    Escribe logs formateados en consola y los guarda en 'app.log'.
    """
    logger = logging.getLogger(nombre)
    logger.setLevel(logging.INFO)

    if not logger.handlers:
        # Formato de los mensajes de log
        formatter = logging.Formatter(
            '[%(asctime)s] [%(levelname)s] [%(name)s]: %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )

        # Handler de Consola
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)

        # Handler de Archivo
        log_file = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'app.log')
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    return logger