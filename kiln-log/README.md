# 烧窑记录 Kiln Log

陶艺工作室的窑次账本：坯件勾进窑位图、三段烧成曲线、看火补记、开窑登记成品/开裂/釉缩，
首页把近十窑的开裂件数摊出来，给老板定下一窑保温要不要加长。

## 一次拉起

```bash
cd kiln-log
docker compose up --build
```

然后浏览器打开 **http://localhost:8080**（页面端口在 `docker-compose.yml` 的 `shelf-ui.ports` 里改）。

| 容器     | 作用                          | 端口                     |
| -------- | ----------------------------- | ------------------------ |
| db       | PostgreSQL 16，账都存在这里   | 容器内 5432（默认不映射） |
| fire-api | FastAPI 接口，文档在 `/docs`  | 8000                     |
| shelf-ui | Vue3 页面，nginx 反代 `/api`  | 8080                     |

数据落在 compose 的 `db-data` 卷里，`docker compose down` 不会丢；`down -v` 才会清账。

## 一窑的走法

1. **建窑次**：首页「新窑次」，填窑次名、气氛（氧化/还原）、棚板层数和每层窑位数。
2. **摆坯件**：详情页添坯件，点「待摆」里的坯件再点图上的空窑位；点已摆的可撤下来。图上标着第几层棚板。
3. **填曲线**：升温、保温、降温三段，各填目标温度和分钟数，下方会画出目标曲线。
4. **点火开烧**：状态变「烧窑中」，窑位锁定；烧着时在「看火记录」补实际温度（可补记时间），实测线会叠到曲线图上。
5. **开窑**：状态变「已开窑」，逐件登记 成品 / 开裂 / 釉缩，窑位图按结果上色。
6. 首页「近十窑开裂情况」列出每窑保温时长和开裂件数，用来商量下一窑保温加不加长。

## 本地开发（不用 Docker）

```bash
# 接口（默认连本机 PostgreSQL，可用 DATABASE_URL 指到别处，含 sqlite）
cd fire-api && pip install -r requirements.txt
uvicorn app.main:app --reload   # http://localhost:8000/docs

# 页面（vite 已把 /api 代理到 8000）
cd shelf-ui && npm install && npm run dev   # http://localhost:5173
```

## 接口一览

- `GET/POST /api/firings`，`GET/PATCH/DELETE /api/firings/{id}`
- `POST /api/firings/{id}/start` 点火、`/open` 开窑
- `PUT /api/firings/{id}/curve` 三段曲线整段替换
- `POST /api/firings/{id}/pieces`、`POST /api/pieces/{id}/place|unplace`、`PATCH/DELETE /api/pieces/{id}`
- `POST /api/firings/{id}/readings`、`DELETE /api/readings/{id}`
- `GET /api/stats/cracks?limit=10` 近几窑开裂统计
