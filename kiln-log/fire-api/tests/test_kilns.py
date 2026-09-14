"""窑炉档案 + 存量迁移的冒烟测试。

跑法：cd fire-api && python3 -m pytest tests/test_kilns.py
用临时 sqlite 文件库，不影响任何真实数据。
"""

import os
import tempfile

# 必须在 import app 之前指好库，database.py 导入时就读这个变量
os.environ["DATABASE_URL"] = f"sqlite:///{tempfile.mkstemp(suffix='.db')[1]}"

from fastapi.testclient import TestClient
from sqlalchemy import text

from app.database import SessionLocal, engine, init_db
from app.main import app
from app.migrate import run_migration
from app.models import Firing, Kiln


def make_legacy_db():
    """造一个「老库」：firings 没有 kiln_id 列，也没有 kilns 表。"""
    with engine.begin() as conn:
        conn.execute(text("DROP TABLE IF EXISTS firings"))
        conn.execute(
            text(
                """
                CREATE TABLE firings (
                    id INTEGER PRIMARY KEY,
                    name VARCHAR(80) NOT NULL,
                    kiln_name VARCHAR(80) NOT NULL DEFAULT '主窑',
                    atmosphere VARCHAR(10) NOT NULL DEFAULT 'oxidation',
                    status VARCHAR(10) NOT NULL DEFAULT 'planned',
                    shelf_layers INTEGER NOT NULL DEFAULT 4,
                    slots_per_layer INTEGER NOT NULL DEFAULT 6,
                    note TEXT NOT NULL DEFAULT '',
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    started_at DATETIME,
                    opened_at DATETIME
                )
                """
            )
        )
        # 老板手滑现场：「气窑」「汽窑」两档，外加一个带空格的写法
        conn.execute(
            text(
                "INSERT INTO firings (name, kiln_name, status, shelf_layers, slots_per_layer)"
                " VALUES "
                "('第1窑', '气窑', 'opened', 4, 6),"
                "('第2窑', '汽窑', 'opened', 5, 8),"
                "('第3窑', '气窑 ', 'opened', 6, 7)"
            )
        )


def test_migration_merges_legacy_names_and_is_idempotent():
    make_legacy_db()
    init_db()  # create_all：补 kilns 等新表，但不动已存在的 firings
    with SessionLocal() as db:
        run_migration(db)

        kilns = {k.name: k for k in db.query(Kiln).all()}
        # 「气窑 」归并进「气窑」，一共两档；规格取各自最近一窑手敲的值
        assert set(kilns) == {"气窑", "汽窑"}
        assert (kilns["气窑"].shelf_layers, kilns["气窑"].slots_per_layer) == (6, 7)
        assert (kilns["汽窑"].shelf_layers, kilns["汽窑"].slots_per_layer) == (5, 8)

        firings = db.query(Firing).order_by(Firing.id).all()
        assert all(f.kiln_id is not None for f in firings)
        assert [f.kiln_name for f in firings] == ["气窑", "汽窑", "气窑"]
        assert firings[0].kiln_id == kilns["气窑"].id
        assert firings[1].kiln_id == kilns["汽窑"].id

    # 再跑一遍（模拟重启）：不重复建档、不改写已挂好的窑次
    with SessionLocal() as db:
        run_migration(db)
        assert db.query(Kiln).count() == 2
        assert db.query(Firing).filter(Firing.kiln_id.is_(None)).count() == 0


def test_kiln_crud_and_firing_flow():
    with TestClient(app) as client:  # 进 lifespan，又会跑一遍迁移，必须还是幂等
        kilns = {k["name"]: k for k in client.get("/api/kilns").json()}
        assert set(kilns) == {"气窑", "汽窑"}
        qi = kilns["气窑"]["id"]
        assert kilns["气窑"]["firing_count"] == 2

        # 重名建档被拒
        r = client.post(
            "/api/kilns",
            json={"name": "气窑", "shelf_layers": 4, "slots_per_layer": 6},
        )
        assert r.status_code == 409

        # 建窑次：选了窑，层数窑位自动带档案规格，名字快照自档案
        r = client.post("/api/firings", json={"name": "第4窑", "kiln_id": qi})
        assert r.status_code == 201
        f4 = r.json()
        assert (f4["kiln_name"], f4["shelf_layers"], f4["slots_per_layer"]) == ("气窑", 6, 7)

        # 临时覆盖：这一窑用别的层数，档案不动
        r = client.post(
            "/api/firings", json={"name": "第5窑", "kiln_id": qi, "shelf_layers": 3}
        )
        f5 = r.json()
        assert (f5["shelf_layers"], f5["slots_per_layer"]) == (3, 7)
        assert client.get(f"/api/kilns").json()[0]["shelf_layers"] == 6

        # 走完一窑：摆坯 → 点火 → 开窑 → 登记开裂
        pid = client.post(f"/api/firings/{f4['id']}/pieces", json={"name": "盖碗"}).json()["id"]
        client.post(f"/api/firings/{f4['id']}/start")
        client.post(f"/api/firings/{f4['id']}/open")
        client.patch(f"/api/pieces/{pid}", json={"result": "cracked"})

        # 档案改名，挂在名下的窑次名字快照跟着改
        client.patch(f"/api/kilns/{qi}", json={"name": "气窑（主）"})
        names = {f["kiln_name"] for f in client.get("/api/firings").json()[:3]}
        assert names == {"气窑（主）"}

        # 名下有窑次时不让裸删；并给「汽窑」后删除成功
        r = client.delete(f"/api/kilns/{qi}")
        assert r.status_code == 409
        qiyao = kilns["汽窑"]["id"]
        r = client.delete(f"/api/kilns/{qi}?reassign_to={qiyao}")
        assert r.status_code == 204
        after = {f["name"]: f for f in client.get("/api/firings").json()}
        assert after["第4窑"]["kiln_id"] == qiyao
        assert after["第4窑"]["kiln_name"] == "汽窑"

        # 按窑炉分组统计：全部归到「汽窑」，开过 4 窑（第5窑还没点火不算），开裂 1 件
        groups = client.get("/api/stats/cracks/by-kiln").json()
        assert len(groups) == 1
        g = groups[0]
        assert (g["kiln_name"], g["opened_count"], g["cracked"]) == ("汽窑", 4, 1)

        # 老的按窑次统计不受影响
        rows = client.get("/api/stats/cracks").json()
        assert len(rows) == 4
        assert sum(r["cracked"] for r in rows) == 1
