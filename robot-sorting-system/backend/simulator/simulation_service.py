import json
import math
import threading
import time
from collections import deque
from datetime import datetime

from core.simulation_engine import SimulationEngine
from core.robot_arm import UR5Arm, ArmPhase
from core.types import Vector3D, ItemColor, ItemSize


def _safe_float_seconds(v):
    try:
        s = str(v).strip().rstrip('s')
        return float(s)
    except Exception:
        return 0.0


def _safe_float(v, default=0.0):
    try:
        return float(str(v).split()[0])
    except Exception:
        return float(default)


# 分拣规则：按颜色分箱
COLOR_TO_BIN = {
    ItemColor.RED:    0,
    ItemColor.GREEN:  1,
    ItemColor.BLUE:   2,
    ItemColor.YELLOW: 3,
}

# 颜色中文名
COLOR_ZH = {
    'red': '红色', 'green': '绿色',
    'blue': '蓝色', 'yellow': '黄色'
}

SIZE_ZH = {'small': '小', 'medium': '中', 'large': '大'}

# 动力学历史记录最大长度
HISTORY_LEN = 300


class SimulationService:
    def __init__(self):
        self._lock    = threading.Lock()
        self._engine  = None
        self._arms    = []       # List[UR5Arm]
        self._thread  = None
        self._running = False
        self._data    = self._empty_data()
        # 动力学历史（供科研图表使用）
        self._history = {
            'time':        deque(maxlen=HISTORY_LEN),
            'joints_0':    [deque(maxlen=HISTORY_LEN) for _ in range(6)],
            'joints_1':    [deque(maxlen=HISTORY_LEN) for _ in range(6)],
            'ee_x_0':      deque(maxlen=HISTORY_LEN),
            'ee_y_0':      deque(maxlen=HISTORY_LEN),
            'ee_z_0':      deque(maxlen=HISTORY_LEN),
            'ee_x_1':      deque(maxlen=HISTORY_LEN),
            'ee_y_1':      deque(maxlen=HISTORY_LEN),
            'ee_z_1':      deque(maxlen=HISTORY_LEN),
            'torque_0':    [deque(maxlen=HISTORY_LEN) for _ in range(6)],
            'torque_1':    [deque(maxlen=HISTORY_LEN) for _ in range(6)],
            'sorted_count': deque(maxlen=HISTORY_LEN),
            'item_count':   deque(maxlen=HISTORY_LEN),
        }
        self._sort_count = 0

    # ------------------------------------------------------------------
    # 公开 API
    # ------------------------------------------------------------------

    def snapshot(self):
        with self._lock:
            return json.loads(json.dumps(self._data, ensure_ascii=False))

    def get_history(self):
        """返回动力学历史数据（供科研图表）"""
        with self._lock:
            h = self._history
            return {
                'time':      list(h['time']),
                'joints_0':  [list(q) for q in h['joints_0']],
                'joints_1':  [list(q) for q in h['joints_1']],
                'ee_0': {
                    'x': list(h['ee_x_0']),
                    'y': list(h['ee_y_0']),
                    'z': list(h['ee_z_0']),
                },
                'ee_1': {
                    'x': list(h['ee_x_1']),
                    'y': list(h['ee_y_1']),
                    'z': list(h['ee_z_1']),
                },
                'torque_0':  [list(q) for q in h['torque_0']],
                'torque_1':  [list(q) for q in h['torque_1']],
                'sorted_count': list(h['sorted_count']),
                'item_count':   list(h['item_count']),
            }

    def start(self, duration_seconds=600):
        with self._lock:
            if self._running:
                return False, {"error": "仿真已在运行"}
            self._running = True
            self._data = self._empty_data()
            self._sort_count = 0
            # 清空历史
            for q in self._history.values():
                if isinstance(q, list):
                    for qq in q:
                        qq.clear()
                else:
                    q.clear()

        self._thread = threading.Thread(
            target=self._run_loop,
            args=(int(duration_seconds or 120),),
            daemon=True,
        )
        self._thread.start()
        return True, {"status": "started", "message": "仿真已启动"}

    def stop(self):
        with self._lock:
            self._running = False
            if self._data.get("status") == "running":
                self._data["status"] = "stopped"
        return True, {"status": "stopped", "message": "仿真已停止"}

    # ------------------------------------------------------------------
    # 内部逻辑
    # ------------------------------------------------------------------

    @staticmethod
    def _empty_data():
        return {
            "status":    "idle",
            "stats":     {},
            "items":     [],
            "robots":    [],
            "bins":      [],
            "time_data": {"simulation_time": 0.0, "fps": 0.0, "frames": 0},
            "messages":  [],
            "timestamp": "",
        }

    def _setup_arms(self):
        """
        创建两台 UR5。
        环境坐标系：宽=2000mm，长=3000mm，高=1500mm。
        传送带在 x≈1000, z≈50。
        机械臂底座设置在传送带侧面，Z=0（地面），
        通过 IK 计算伸向传送带高度。
        """
        # 底座紧贴传送带两侧，Z=0（工作台面）
        # 机械臂需要能到达传送带中心 (x=1000, y=750, z=50)
        arm0 = UR5Arm(arm_id=0, base_pos=Vector3D(680,  900, 0))
        arm1 = UR5Arm(arm_id=1, base_pos=Vector3D(1320, 900, 0))
        self._arms = [arm0, arm1]

    def _assign_tasks(self):
        """将传送带上等待分拣的物品分配给空闲机械臂"""
        env = self._engine.environment
        items = env.get_all_items()

        held_ids = set()
        for arm in self._arms:
            if arm.target_item:
                held_ids.add(arm.target_item.id)

        # 只分配 sorted_bin==-1（未被任何臂标记）的物品
        available = [
            it for it in items
            if it.sorted_bin == -1 and it.id not in held_ids
        ]
        if not available:
            return

        UR5_REACH = 800  # UR5 有效抓取半径 (mm)

        for arm in self._arms:
            if arm.phase != ArmPhase.IDLE:
                continue
            if not available:
                break

            reachable = [
                it for it in available
                if ((it.position.x - arm.base_pos.x)**2 +
                    (it.position.y - arm.base_pos.y)**2) ** 0.5 <= UR5_REACH
            ]
            if not reachable:
                continue

            reachable.sort(
                key=lambda it: (it.position.x - arm.base_pos.x)**2 +
                               (it.position.y - arm.base_pos.y)**2
            )
            item = reachable[0]
            available.remove(item)

            bin_id = COLOR_TO_BIN.get(item.color, 0)
            bin_obj = env.get_sorting_bin(bin_id)
            if bin_obj is None:
                continue

            item.sorted_bin = bin_id
            arm.assign_task(
                item=item,
                bin_pos=bin_obj.position,
                bin_id=bin_id,
            )

    @staticmethod
    def _estimate_torque(joints, arm_idx):
        """简化动力学：用关节角估算各轴扭矩（牛·米）"""
        # UR5 连杆质量近似值 (kg)
        link_mass = [3.7, 8.3, 2.3, 1.2, 1.2, 0.25]
        # 连杆长度 (m)
        link_len  = [0.0, 0.425, 0.392, 0.133, 0.100, 0.083]
        g = 9.81
        torques = []
        cum_angle = 0.0
        for i in range(6):
            cum_angle += joints[i]
            lever = link_len[i] * abs(math.cos(cum_angle))
            mass_sum = sum(link_mass[i:])
            torques.append(round(mass_sum * g * lever, 3))
        return torques

    def _record_history(self, sim_time, sorted_count, item_count):
        """记录动力学历史数据"""
        with self._lock:
            h = self._history
            h['time'].append(round(sim_time, 3))
            h['sorted_count'].append(sorted_count)
            h['item_count'].append(item_count)
            for i, arm in enumerate(self._arms):
                jk = f'joints_{i}'
                ek_x, ek_y, ek_z = f'ee_x_{i}', f'ee_y_{i}', f'ee_z_{i}'
                tk = f'torque_{i}'
                ee = arm.get_end_effector_world()
                torques = self._estimate_torque(arm.joints, i)
                for j in range(6):
                    h[jk][j].append(round(math.degrees(arm.joints[j]), 2))
                    h[tk][j].append(torques[j])
                h[ek_x].append(round(ee.x, 1))
                h[ek_y].append(round(ee.y, 1))
                h[ek_z].append(round(ee.z, 1))

    def _collect(self, dt: float):
        """更新机械臂状态机 + 收集快照数据"""
        env = self._engine.environment

        events = []
        for arm in self._arms:
            ev = arm.update(dt, env)
            if ev:
                events.append(ev)

        for ev in events:
            if ev["type"] == "item_placed":
                item   = ev["item"]
                bin_id = ev["bin_id"]
                if item:
                    env.remove_item(item.id)
                    bin_obj = env.get_sorting_bin(bin_id)
                    if bin_obj:
                        bin_obj.add_item(item)
                    self._engine.stats.successful_sorts += 1
                    self._sort_count += 1
                    color_zh = COLOR_ZH.get(item.color.value if hasattr(item.color,'value') else str(item.color), '未知')
                    with self._lock:
                        self._data["messages"].append(
                            f"[{datetime.now().strftime('%H:%M:%S')}] "
                            f"机械臂{ev['arm_id']} 成功将{color_zh}物品放入 {bin_id} 号箱"
                        )

        stats = self._engine.get_statistics()
        sim_time = _safe_float_seconds(stats.get("simulation_time", "0s"))
        item_count = len(env.get_all_items())

        items_list = [
            {
                "id":       it.id,
                "color":    it.color.value,
                "size":     it.size.value,
                "weight":   it.weight.value,
                "position": {"x": round(it.position.x, 1),
                             "y": round(it.position.y, 1),
                             "z": round(it.position.z, 1)},
                "sorted_bin": it.sorted_bin,
            }
            for it in env.get_all_items()
        ]

        robots_list = [arm.to_dict() for arm in self._arms]

        bins_list = [
            {
                "id":            b.bin_id,
                "capacity":      b.capacity,
                "current_count": len(b.current_items),
                "fill_rate":     round(b.get_fill_rate() * 100, 1),
                "position":      {"x": round(b.position.x, 1),
                                  "y": round(b.position.y, 1),
                                  "z": round(b.position.z, 1)},
            }
            for b in env.get_all_bins()
        ]

        time_data = {
            "simulation_time": sim_time,
            "fps":             _safe_float(stats.get("fps", "0")),
            "frames":          int(stats.get("total_frames", 0) or 0),
        }

        with self._lock:
            self._data["stats"]     = stats
            self._data["items"]     = items_list
            self._data["robots"]    = robots_list
            self._data["bins"]      = bins_list
            self._data["time_data"] = time_data
            self._data["timestamp"] = datetime.now().isoformat()

        # 每5帧记录一次历史（降低开销）
        if int(stats.get("total_frames", 0)) % 5 == 0:
            self._record_history(sim_time, self._sort_count, item_count)

    def _run_loop(self, duration_seconds: int):
        try:
            self._engine = SimulationEngine(enable_physics=True, enable_logging=False)
            self._engine.startup()
            self._setup_arms()

            with self._lock:
                self._data["status"] = "running"
                self._data["messages"].append("UR5 仿真引擎启动成功")
                self._data["messages"].append("2 台 UR5 机械臂已就位，等待任务分配")

            start        = time.time()
            last_t       = start
            assign_interval = 0.2   # 每 0.2s 做一次任务分配（更频繁）
            last_assign  = start

            while self._running and (time.time() - start) < duration_seconds:
                now = time.time()
                dt  = min(now - last_t, 0.05)  # 限制 dt 防抖
                last_t = now

                self._engine.step()

                if now - last_assign >= assign_interval:
                    self._assign_tasks()
                    last_assign = now

                self._collect(dt)
                time.sleep(0.016)   # ~60 fps

            self._engine.shutdown()
            elapsed = time.time() - start
            final_status = "completed" if elapsed >= duration_seconds else "stopped"
            with self._lock:
                self._data["status"] = final_status
                total = self._sort_count
                self._data["messages"].append(
                    f"仿真完成，共成功分拣 {total} 件物品" if final_status == "completed"
                    else f"仿真已停止，已分拣 {total} 件物品"
                )
        except Exception as e:
            import traceback
            with self._lock:
                self._data["status"] = "error"
                self._data["messages"].append(f"错误: {e}")
                self._data["messages"].append(traceback.format_exc())
        finally:
            self._running = False


service = SimulationService()
