#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Web服务器 - 提供仿真的实时可视化

优先使用Flask提供API和web界面；如果Flask不可用，则自动降级到标准库HTTP服务器。
"""
import sys
import os

# 修复Windows编码问题 - 使用UTF-8处理输出
try:
    if sys.stdout.encoding != 'utf-8':
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
except (AttributeError, RuntimeError):
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

import json
import threading
import time
from datetime import datetime
from core.simulation_engine import SimulationEngine
from core.types import Vector3D


def _safe_float_seconds(simulation_time_str):
    """将 '12.34s' / '12.34' 安全转换为 float 秒数"""
    try:
        s = str(simulation_time_str).strip()
        if s.endswith("s"):
            s = s[:-1]
        return float(s)
    except Exception:
        return 0.0


def _safe_float(value, default=0.0):
    try:
        return float(value)
    except Exception:
        return float(default)


class SimulationService:
    """仿真服务层：统一状态、线程安全、同时支持Flask与标准库HTTP"""

    def __init__(self):
        self._lock = threading.Lock()
        self._engine = None
        self._thread = None
        self._running = False
        self._data = {
            "status": "idle",  # idle, running, completed, stopped, error
            "stats": {},
            "items": [],
            "robots": [],
            "bins": [],
            "time_data": {"simulation_time": 0.0, "fps": 0.0, "frames": 0},
            "messages": [],
            "timestamp": "",
        }

    def snapshot(self):
        with self._lock:
            return json.loads(json.dumps(self._data, ensure_ascii=False))

    def _set_message(self, msg):
        with self._lock:
            self._data["messages"].append(msg)

    def _collect(self):
        engine = self._engine
        if not engine:
            return

        stats = engine.get_statistics()

        items = []
        for item in engine.environment.get_all_items():
            items.append(
                {
                    "id": item.id,
                    "color": item.color.value,
                    "size": item.size.value,
                    "position": {
                        "x": round(item.position.x, 2),
                        "y": round(item.position.y, 2),
                        "z": round(item.position.z, 2),
                    },
                    "velocity": {
                        "x": round(item.velocity.x, 2),
                        "y": round(item.velocity.y, 2),
                        "z": round(item.velocity.z, 2),
                    },
                }
            )

        robots = []
        for robot in engine.environment.get_all_robots():
            robots.append(
                {
                    "id": robot.arm_id,
                    "state": robot.state.value,
                    "position": {
                        "x": round(robot.position.x, 2),
                        "y": round(robot.position.y, 2),
                        "z": round(robot.position.z, 2),
                    },
                    "battery": robot.battery_level,
                }
            )

        bins = []
        for bin_obj in engine.environment.get_all_bins():
            bins.append(
                {
                    "id": bin_obj.bin_id,
                    "capacity": bin_obj.capacity,
                    "current_count": len(bin_obj.current_items),
                    "fill_rate": round(bin_obj.get_fill_rate() * 100, 1),
                }
            )

        time_data = {
            "simulation_time": _safe_float_seconds(stats.get("simulation_time", "0s")),
            "fps": _safe_float(str(stats.get("fps", "0")).split()[0], 0.0),
            "frames": int(stats.get("total_frames", 0) or 0),
        }

        with self._lock:
            self._data["stats"] = stats
            self._data["items"] = items
            self._data["robots"] = robots
            self._data["bins"] = bins
            self._data["time_data"] = time_data
            self._data["timestamp"] = datetime.now().isoformat()

    def _run_loop(self, duration_seconds):
        try:
            self._engine = SimulationEngine(enable_physics=True, enable_logging=False)
            self._engine.startup()

            self._engine.environment.add_robot_arm(0, Vector3D(1000, 750, 1400))
            self._engine.environment.add_robot_arm(1, Vector3D(1500, 750, 1400))

            with self._lock:
                self._data["status"] = "running"
                self._data["messages"].append("✅ 仿真引擎启动成功")

            start = time.time()
            while self._running and (time.time() - start) < duration_seconds:
                self._engine.step()
                self._collect()
                time.sleep(0.01)  # 降低CPU占用

            self._engine.shutdown()
            with self._lock:
                self._data["status"] = "completed" if (time.time() - start) >= duration_seconds else "stopped"
                self._data["messages"].append("✅ 仿真完成" if self._data["status"] == "completed" else "⏹ 已停止")
        except Exception as e:
            with self._lock:
                self._data["status"] = "error"
                self._data["messages"].append("❌ 错误: %s" % (e,))
        finally:
            self._running = False

    def start(self, duration_seconds=30):
        with self._lock:
            if self._running:
                return False, {"error": "仿真已在运行"}
            self._running = True
            self._data["messages"] = []
            self._data["items"] = []
            self._data["robots"] = []
            self._data["bins"] = []
            self._data["stats"] = {}
            self._data["time_data"] = {"simulation_time": 0.0, "fps": 0.0, "frames": 0}
            self._data["status"] = "idle"

        self._thread = threading.Thread(target=self._run_loop, args=(int(duration_seconds or 30),))
        self._thread.daemon = True
        self._thread.start()
        return True, {"status": "started", "message": "仿真已启动"}

    def stop(self):
        with self._lock:
            self._running = False
            if self._data.get("status") == "running":
                self._data["status"] = "stopped"
        return True, {"status": "stopped", "message": "仿真已停止"}


service = SimulationService()


def _print_banner(server_name, host, port):
    print("=" * 70)
    print("  机器人分拣系统 - Web可视化服务器 (%s)" % server_name)
    print("=" * 70)
    print("\n访问地址: http://%s:%s" % (host, port))
    print("\nAPI端点:")
    print("  POST /api/start    - 启动仿真")
    print("  POST /api/stop     - 停止仿真")
    print("  GET  /api/data     - 获取完整数据")
    print("  GET  /api/stats    - 获取统计数据")
    print("  GET  /api/items    - 获取物品列表")
    print("  GET  /api/robots   - 获取机械臂数据")
    print("  GET  /api/bins     - 获取分拣箱数据")
    print("  GET  /api/time     - 获取时间数据")
    print("\n" + "=" * 70 + "\n")


def _try_run_flask(host, port):
    try:
        from flask import Flask, render_template, jsonify, request  # type: ignore
    except Exception:
        return False

    app = Flask(__name__)
    app.config["JSON_AS_ASCII"] = False

    @app.route("/")
    def index():
        return render_template("simulator.html")

    @app.route("/api/start", methods=["POST"])
    def api_start_simulation():
        body = request.get_json(silent=True) or {}
        duration = body.get("duration", 30)
        ok, payload = service.start(duration_seconds=duration)
        return (jsonify(payload), 200) if ok else (jsonify(payload), 400)

    @app.route("/api/stop", methods=["POST"])
    def api_stop_simulation():
        _, payload = service.stop()
        return jsonify(payload)

    @app.route("/api/data")
    def api_get_data():
        return jsonify(service.snapshot())

    @app.route("/api/stats")
    def api_get_stats():
        snap = service.snapshot()
        return jsonify({"status": snap.get("status"), "stats": snap.get("stats"), "timestamp": snap.get("timestamp", "")})

    @app.route("/api/items")
    def api_get_items():
        snap = service.snapshot()
        items = snap.get("items") or []
        return jsonify({"count": len(items), "items": items[:20]})

    @app.route("/api/robots")
    def api_get_robots():
        snap = service.snapshot()
        robots = snap.get("robots") or []
        return jsonify({"count": len(robots), "robots": robots})

    @app.route("/api/bins")
    def api_get_bins():
        snap = service.snapshot()
        bins = snap.get("bins") or []
        return jsonify({"count": len(bins), "bins": bins})

    @app.route("/api/time")
    def api_get_time():
        snap = service.snapshot()
        return jsonify(snap.get("time_data") or {"simulation_time": 0.0, "fps": 0.0, "frames": 0})

    _print_banner("Flask", host, port)
    app.run(debug=False, host=host, port=port)
    return True


def _run_stdlib_http(host, port):
    import urllib.parse
    from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

    base_dir = os.path.abspath(os.path.dirname(__file__))
    template_path = os.path.join(base_dir, "templates", "simulator.html")

    def _json_bytes(payload, status=200):
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        return status, [("Content-Type", "application/json; charset=utf-8"), ("Content-Length", str(len(data)))], data

    def _html_bytes(html, status=200):
        data = html.encode("utf-8")
        return status, [("Content-Type", "text/html; charset=utf-8"), ("Content-Length", str(len(data)))], data

    class Handler(BaseHTTPRequestHandler):
        server_version = "RobotSortingStdlibHTTP/0.1"

        def _send(self, status, headers, body):
            self.send_response(status)
            for k, v in headers:
                self.send_header(k, v)
            self.end_headers()
            self.wfile.write(body)

        def _read_json_body(self):
            try:
                length = int(self.headers.get("Content-Length") or 0)
            except Exception:
                length = 0
            if length <= 0:
                return {}
            raw = self.rfile.read(length)
            try:
                return json.loads(raw.decode("utf-8"))
            except Exception:
                return {}

        def do_GET(self):  # noqa: N802
            path = urllib.parse.urlparse(self.path).path
            if path == "/":
                try:
                    with open(template_path, "r", encoding="utf-8") as f:
                        html = f.read()
                except Exception as e:
                    status, headers, body = _html_bytes("模板读取失败: %s" % (e,), status=500)
                    return self._send(status, headers, body)
                status, headers, body = _html_bytes(html)
                return self._send(status, headers, body)

            if path == "/api/data":
                status, headers, body = _json_bytes(service.snapshot())
                return self._send(status, headers, body)
            if path == "/api/stats":
                snap = service.snapshot()
                status, headers, body = _json_bytes(
                    {"status": snap.get("status"), "stats": snap.get("stats"), "timestamp": snap.get("timestamp", "")}
                )
                return self._send(status, headers, body)
            if path == "/api/items":
                snap = service.snapshot()
                items = snap.get("items") or []
                status, headers, body = _json_bytes({"count": len(items), "items": items[:20]})
                return self._send(status, headers, body)
            if path == "/api/robots":
                snap = service.snapshot()
                robots = snap.get("robots") or []
                status, headers, body = _json_bytes({"count": len(robots), "robots": robots})
                return self._send(status, headers, body)
            if path == "/api/bins":
                snap = service.snapshot()
                bins = snap.get("bins") or []
                status, headers, body = _json_bytes({"count": len(bins), "bins": bins})
                return self._send(status, headers, body)
            if path == "/api/time":
                snap = service.snapshot()
                status, headers, body = _json_bytes(snap.get("time_data") or {"simulation_time": 0.0, "fps": 0.0, "frames": 0})
                return self._send(status, headers, body)

            status, headers, body = _json_bytes({"error": "页面未找到"}, status=404)
            return self._send(status, headers, body)

        def do_POST(self):  # noqa: N802
            path = urllib.parse.urlparse(self.path).path
            if path == "/api/start":
                body = self._read_json_body()
                duration = body.get("duration", 30)
                ok, payload = service.start(duration_seconds=duration)
                status, headers, data = _json_bytes(payload, status=200 if ok else 400)
                return self._send(status, headers, data)
            if path == "/api/stop":
                _, payload = service.stop()
                status, headers, data = _json_bytes(payload, status=200)
                return self._send(status, headers, data)

            status, headers, body = _json_bytes({"error": "页面未找到"}, status=404)
            return self._send(status, headers, body)

        def log_message(self, format, *args):  # noqa: A002
            # 降噪：保持控制台整洁
            return

    _print_banner("StdlibHTTP (no Flask)", host, port)
    httpd = ThreadingHTTPServer((host, int(port)), Handler)
    httpd.serve_forever()


if __name__ == "__main__":
    # 默认配置：尽量“开箱即用”
    host = os.environ.get("ROBOT_WEB_HOST", "127.0.0.1")
    port = int(os.environ.get("ROBOT_WEB_PORT", "5000"))

    if not _try_run_flask(host=host, port=port):
        _run_stdlib_http(host=host, port=port)
