from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .database import SessionLocal, init_db
from .migrate import run_migration
from .routers import firings, kilns, pieces, readings, stats


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()  # 启动时建表，数据库没就绪会重试
    with SessionLocal() as db:
        run_migration(db)  # 补 kiln_id 列、按老 kiln_name 归并出窑炉档案，幂等
    yield


app = FastAPI(title="烧窑记录 Kiln Log", version="1.0.0", lifespan=lifespan)

# 开发时 vite  dev server 跨域调接口用；compose 部署走 nginx 同源反代
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
def health():
    return {"ok": True}


app.include_router(kilns.router)
app.include_router(firings.router)
app.include_router(pieces.router)
app.include_router(readings.router)
app.include_router(stats.router)
