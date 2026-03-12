## 路线 C：Django + Channels + React（本地开发）

### 1) 后端（Django + Channels）

> 说明：你的机器当前是 Python 3.7。原 `requirements.txt` 里的 `Django==4.2.3` / `channels==4` 需要更高版本 Python。
>
> 为了兼容 Python 3.7，这里使用 `backend/requirements_django_py37.txt`（Django 3.2 LTS + Channels 3）。

在 `robot-sorting-system/backend` 目录：

```bash
python -m venv venv
venv\Scripts\activate

pip install -r requirements_django_py37.txt
python manage.py runserver 127.0.0.1:8000
```

后端地址：
- 首页：`http://127.0.0.1:8000/`
- API：`/api/*`
- WebSocket：`ws://127.0.0.1:8000/ws/sim`

### 2) 前端（React + Vite）

在 `robot-sorting-system/frontend` 目录：

```bash
npm install
npm run dev
```

前端地址：`http://127.0.0.1:5173/`

Vite 已配置代理：
- `http://127.0.0.1:5173/api/*` → `http://127.0.0.1:8000/api/*`
- `ws://127.0.0.1:5173/ws/*` → `ws://127.0.0.1:8000/ws/*`

