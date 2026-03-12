"""
核心仿真引擎 - 整个系统的中枢
集成 UR5Arm 机械臂状态机，实现真实抓取/放置逻辑
"""
import random
import time
from typing import List, Dict, Callable, Optional
from core.types import (
    Item, ItemSize, ItemColor, ItemWeight, Vector3D,
    RobotState, SimulationStats
)
from core.physics import PhysicsSimulator
from core.environment import Environment3D
from core.robot_arm import UR5Arm, ArmPhase
from utils.timer import TimeManager
from utils.logger import get_logger
from config.constants import (
    ITEM_SPAWN_RATE, SORTING_BIN_COUNT
)

# 分拣规则：根据物品颜色决定投入哪个箱子
COLOR_TO_BIN = {
    'red':    0,
    'green':  1,
    'blue':   2,
    'yellow': 3,
}


class SimulationEngine:
    """仿真引擎 - 核心仿真系统，含 UR5 机械臂抓取"""

    def __init__(self, enable_physics: bool = True, enable_logging: bool = True):
        self.logger = get_logger() if enable_logging else None
        self.time_manager = TimeManager()
        self.environment = Environment3D()
        self.physics_simulator = PhysicsSimulator() if enable_physics else None
        self.enable_physics = enable_physics
        self.stats = SimulationStats()
        self.callbacks: Dict[str, list] = {
            'on_item_created':     [],
            'on_item_removed':     [],
            'on_collision':        [],
            'on_step_complete':    [],
            'on_simulation_start': [],
            'on_simulation_stop':  [],
            'on_item_sorted':      [],
        }
        self.running = False
        self.total_frames = 0
        self.last_spawn_time = 0.0
        self.spawn_accumulator = 0.0
        self.arms: List[UR5Arm] = []
        self._assigned_item_ids: set = set()
        if self.logger:
            self.logger.info("SimulationEngine initialized")

    # ------------------------------------------------------------------
    # 生命周期
    # ------------------------------------------------------------------

    def startup(self):
        """启动仿真引擎，创建机械臂并重新布置分拣箱"""
        self.running = True
        self.time_manager.reset()
        self.stats = SimulationStats()
        self._assigned_item_ids.clear()

        env  = self.environment
        conv = env.conveyor_position  # X=1000, Y=750, Z=50

        # 两台 UR5 底座位于传送带左右两侧，Y 与传送带中心对齐
        # 臂展 850 mm，底座距传送带中心 400 mm → 物品可达
        arm_bases = [
            Vector3D(conv.x - 400, conv.y, 0),
            Vector3D(conv.x + 400, conv.y, 0),
        ]
        self.arms = [UR5Arm(arm_id=i, base_pos=b) for i, b in enumerate(arm_bases)]

        # 分拣箱放在机械臂外侧，仍在臂展范围内（距底座 ~650 mm）
        bin_positions = [
            Vector3D(conv.x - 750, conv.y - 250, 0),
            Vector3D(conv.x - 750, conv.y + 250, 0),
            Vector3D(conv.x + 750, conv.y - 250, 0),
            Vector3D(conv.x + 750, conv.y + 250, 0),
        ]
        for bid, pos in enumerate(bin_positions):
            if bid in env.sorting_bins:
                env.sorting_bins[bid].position = pos

        self._trigger_callbacks('on_simulation_start')
        if self.logger:
            self.logger.info(f"SimulationEngine started, {len(self.arms)} arms")

    def shutdown(self):
        self.running = False
        self._trigger_callbacks('on_simulation_stop')

    # ------------------------------------------------------------------
    # 主循环
    # ------------------------------------------------------------------

    def step(self, spawn_items: bool = True, update_physics: bool = True) -> bool:
        if not self.running:
            return False
        self.time_manager.update()
        dt = self.time_manager.get_delta_time()
        if spawn_items:
            self._spawn_items()
        self._update_conveyor(dt)
        if update_physics and self.enable_physics:
            self._update_physics(dt)
        if self.enable_physics:
            self._handle_collisions()
        self._assign_tasks()
        self._update_arms(dt)
        self._trigger_callbacks('on_step_complete')
        self.total_frames += 1
        return True

    # ------------------------------------------------------------------
    # 物品生成：直接在传送带工作区中段生成，机械臂可立即抓取
    # ------------------------------------------------------------------

    def _spawn_items(self):
        current_time = self.time_manager.get_simulation_time()
        elapsed = current_time - self.last_spawn_time
        self.spawn_accumulator += elapsed

        spawn_count = 1 if self.spawn_accumulator >= 1.5 else 0
        if len(self.environment.get_all_items()) >= 10:
            spawn_count = 0

        conv = self.environment.conveyor_position
        for _ in range(spawn_count):
            size   = random.choice(list(ItemSize))
            color  = random.choice(list(ItemColor))
            weight = random.choice(list(ItemWeight))
            # 在传送带中段（机械臂工作区）随机散布生成
            position = Vector3D(
                conv.x + random.uniform(-60, 60),
                conv.y + random.uniform(-200, 200),
                conv.z,
            )
            item = Item(
                id=-1, size=size, color=color, weight=weight,
                position=position, timestamp=current_time,
            )
            self.environment.add_item(item)
            self._trigger_callbacks('on_item_created', item)
            self.stats.total_items_processed += 1

        self.last_spawn_time = current_time
        if spawn_count > 0:
            self.spawn_accumulator = 0.0

    # ------------------------------------------------------------------
    # 传送带：物品静止等待抓取，漂出工作区才移除
    # ------------------------------------------------------------------

    def _update_conveyor(self, dt: float):
        conv = self.environment.conveyor_position
        for item in list(self.environment.get_all_items()):
            if item.sorted_bin == -1 and item.id not in self._assigned_item_ids:
                if (abs(item.position.x - conv.x) > 500 or
                        abs(item.position.y - conv.y) > 700):
                    self.environment.remove_item(item.id)

    # ------------------------------------------------------------------
    # 物理
    # ------------------------------------------------------------------

    def _update_physics(self, dt: float):
        bounds = self.environment.get_environment_bounds()
        for item in self.environment.get_all_items():
            self.physics_simulator.update_item_physics(item, dt, bounds)

    def _handle_collisions(self):
        items = self.environment.get_all_items()
        for i in range(len(items)):
            for j in range(i + 1, len(items)):
                if self.physics_simulator.check_collision(items[i], items[j]):
                    self.physics_simulator.resolve_collision(items[i], items[j])
                    self._trigger_callbacks('on_collision', items[i], items[j])

    # ------------------------------------------------------------------
    # 任务分配：为空闲机械臂选最近物品
    # ------------------------------------------------------------------

    def _assign_tasks(self):
        items = self.environment.get_all_items()
        available = [
            it for it in items
            if it.sorted_bin == -1 and it.id not in self._assigned_item_ids
        ]
        for arm in self.arms:
            if arm.phase != ArmPhase.IDLE or not available:
                continue
            best = min(
                available,
                key=lambda it: (
                    (it.position.x - arm.base_pos.x) ** 2 +
                    (it.position.y - arm.base_pos.y) ** 2
                ) ** 0.5
            )
            color_name = best.color.value
            bin_id = COLOR_TO_BIN.get(color_name, 0) % SORTING_BIN_COUNT
            target_bin = self.environment.get_sorting_bin(bin_id)
            if target_bin is None:
                continue
            if arm.assign_task(best, target_bin.position, bin_id):
                self._assigned_item_ids.add(best.id)
                available.remove(best)
                if self.logger:
                    self.logger.info(
                        f"Arm {arm.arm_id} -> item {best.id} ({color_name}) -> bin {bin_id}"
                    )

    # ------------------------------------------------------------------
    # 机械臂更新
    # ------------------------------------------------------------------

    def _update_arms(self, dt: float):
        for arm in self.arms:
            event = arm.update(dt, self.environment)
            if event and event.get('type') == 'item_placed':
                item   = event['item']
                bin_id = event['bin_id']
                self.add_item_to_bin(item, bin_id)
                if item:
                    self._assigned_item_ids.discard(item.id)
                    self.environment.remove_item(item.id)
                self._trigger_callbacks('on_item_sorted', item, bin_id, True)
                if self.logger:
                    self.logger.info(
                        f"Arm {arm.arm_id} placed item {getattr(item,'id','?')} into bin {bin_id}"
                    )

    # ------------------------------------------------------------------
    # 工具方法
    # ------------------------------------------------------------------

    def add_item_to_bin(self, item: Item, bin_id: int) -> bool:
        bin_obj = self.environment.get_sorting_bin(bin_id)
        if bin_obj and bin_obj.add_item(item):
            if item:
                item.sorted_bin = bin_id
            self.stats.successful_sorts += 1
            return True
        self.stats.failed_sorts += 1
        return False

    def remove_item(self, item_id: int) -> bool:
        item = self.environment.get_item(item_id)
        if item:
            self.environment.remove_item(item_id)
            self._assigned_item_ids.discard(item_id)
            self._trigger_callbacks('on_item_removed', item)
            return True
        return False

    def register_callback(self, event: str, callback: Callable):
        if event in self.callbacks:
            self.callbacks[event].append(callback)

    def _trigger_callbacks(self, event: str, *args):
        for cb in self.callbacks.get(event, []):
            try:
                cb(*args)
            except Exception as e:
                if self.logger:
                    self.logger.error(f"Callback error [{event}]: {e}")

    def get_statistics(self) -> Dict:
        total   = self.stats.total_items_processed
        success = self.stats.successful_sorts
        accuracy = (success / total * 100) if total > 0 else 0.0
        return {
            'total_items_processed': total,
            'successful_sorts':      success,
            'failed_sorts':          self.stats.failed_sorts,
            'accuracy_rate':         f"{accuracy:.1f}%",
            'simulation_time':       f"{self.time_manager.get_simulation_time():.2f}s",
            'fps':                   f"{self.time_manager.get_fps():.1f}",
            'total_frames':          self.total_frames,
            'items_in_environment':  len(self.environment.get_all_items()),
            'arms':                  [a.to_dict() for a in self.arms],
        }

    def get_arms(self) -> List[UR5Arm]:
        return self.arms

    def reset(self):
        self.environment.clear()
        self.time_manager.reset()
        self.stats = SimulationStats()
        self.total_frames = 0
        self.last_spawn_time = 0.0
        self.spawn_accumulator = 0.0
        self.arms = []
        self._assigned_item_ids.clear()
