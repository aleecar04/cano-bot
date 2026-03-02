import logging
from app.core.db import supabase
from app.core.config import settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def init() -> None:
    # Crear superusuario inicial si no existe
    user = supabase.auth.admin.list_users()
    # aquí tu lógica de inicialización

def main() -> None:
    logger.info("Creating initial data")
    init()
    logger.info("Initial data created")

if __name__ == "__main__":
    main()