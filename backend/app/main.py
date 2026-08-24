from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.modules.auth.routes import router as auth_router
from app.modules.categorias.routes import router as categorias_router
from app.modules.cuentas_bancos.routes import router as cuentas_bancos_router
from app.modules.divisas.routes import router as divisas_router
from app.modules.flujo_caja.routes import router as flujo_caja_router
from app.modules.imports.routes import router as imports_router
from app.modules.reports.routes import router as reports_router
from app.modules.sucursales.routes import router as sucursales_router
from app.modules.transacciones.routes import router as transacciones_router
from app.modules.usuarios.routes import router as users_router
from app.modules.vendedores.routes import router as vendedores_router

app = FastAPI(title=settings.project_name, openapi_url="/api/v1/openapi.json")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.backend_cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/v1/health", tags=["health"])
def health_check() -> dict[str, str]:
    return {"status": "ok"}


app.include_router(auth_router, prefix="/api/v1")
app.include_router(users_router, prefix="/api/v1")
app.include_router(cuentas_bancos_router, prefix="/api/v1")
app.include_router(sucursales_router, prefix="/api/v1")
app.include_router(vendedores_router, prefix="/api/v1")
app.include_router(categorias_router, prefix="/api/v1")
app.include_router(divisas_router, prefix="/api/v1")
app.include_router(imports_router, prefix="/api/v1")
app.include_router(reports_router, prefix="/api/v1")
app.include_router(transacciones_router, prefix="/api/v1")
app.include_router(flujo_caja_router, prefix="/api/v1")
