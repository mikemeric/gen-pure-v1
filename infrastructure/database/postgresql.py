from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base
from core.config import settings
import logging

# Configuration des logs
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 1. Adaptation de l'URL pour le pilote asynchrone (asyncpg)
# SQLAlchemy a besoin de 'postgresql+asyncpg://' au lieu de 'postgresql://'
DB_URL = settings.DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://")

# 2. Création du moteur
engine = create_async_engine(DB_URL, echo=False, future=True)

# 3. Factory de sessions
SessionLocal = sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)

Base = declarative_base()

# 4. Fonction d'initialisation (Celle qui manquait !)
async def init_db():
    """
    Tente de créer les tables. 
    Si la DB n'est pas là, on log une erreur mais ON NE CRASH PAS le serveur.
    """
    try:
        async with engine.begin() as conn:
            # Ici on créerait les tables : await conn.run_sync(Base.metadata.create_all)
            pass
        logger.info("✅ Connexion Base de Données : SUCCÈS")
    except Exception as e:
        logger.warning(f"⚠️ ATTENTION: Impossible de se connecter à la Base de Données. Le Dashboard s'affichera mais sans données réelles.")
        logger.warning(f"Erreur technique : {e}")

# 5. Dépendance pour les routes (Dependency Injection)
async def get_db():
    async with SessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()
