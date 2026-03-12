"""
UR5 机械臂运动学模型
纯 Python 解析式正/逆运动学，无需第三方机器人库
UR5 是目前工业界最广泛部署的协作机器人，6自由度，臂展 850mm
参考: Universal Robots UR5 Technical Specification
"""
import math
import time
from enum import Enum
from dataclasses import dataclass, field
from typing import List, Optional, Tuple
from core.types import Vector3D, RobotState


# ============================================================
# 枚举
# ============================================================

class GripperState(Enum):
    OPEN    = "open"
    CLOSING = "closing"
    CLOSED  = "closed"
    OPENING = "opening"


class ArmPhase(Enum):
    IDLE            = "idle"
    MOVING_TO_ITEM  = "moving_to_item"
    DESCENDING      = "descending"
    GRIPPING        = "gripping"
    LIFTING         = "lifting"
    MOVING_TO_BIN   = "moving_to_bin"
    PLACING         = "placing"
    RETURNING       = "returning"


# ============================================================
# UR5 DH 参数  (标准 DH,  单位 m / rad)
# (a,       d,        alpha,       theta_offset)
# ============================================================
UR5_DH = [
    (0.0,      0.08916,   math.pi/2,  0.0),
    (-0.4250,  0.0,       0.0,        0.0),
    (-0.3922,  0.0,       0.0,        0.0),
    (0.0,      0.10915,   math.pi/2,  0.0),
    (0.0,      0.09465,  -math.pi/2,  0.0),
    (0.0,      0.0823,    0.0,        0.0),
]

# HOME 姿态：末端朝下，臂自然展开
HOME_JOINTS = [0.0, -math.pi/2, math.pi/2, -math.pi/2, -math.pi/2, 0.0]

# 仿真坐标 mm -> m
SIM_SCALE = 0.001


# ============================================================
# 运动学工具函数
# ============================================================

def _dh_matrix(a, d, alpha, theta):
    """单关节 DH 齐次变换矩阵 4x4"""
    ca, sa = math.cos(alpha), math.sin(alpha)
    ct, st = math.cos(theta), math.sin(theta)
    return [
        [ct,      -st,       0,    a    ],
        [st*ca,    ct*ca,   -sa,  -sa*d ],
        [st*sa,    ct*sa,    ca,   ca*d ],
        [0,        0,        0,    1    ],
    ]


def _mat4(A, B):
    """4x4 矩阵乘法"""
    C = [[0.0]*4 for _ in range(4)]
    for i in range(4):
        for j in range(4):
            for k in range(4):
                C[i][j] += A[i][k] * B[k][j]
    return C


def ur5_fk(joints: List[float]) -> Tuple[Vector3D, List[Vector3D]]:
    """
    UR5 正向运动学
    Args:
        joints: 6 个关节角 (rad)
    Returns:
        (末端坐标 mm, 各关节坐标列表 mm)  -- 相对底座
    """
    T = [[1,0,0,0],[0,1,0,0],[0,0,1,0],[0,0,0,1]]
    positions = [Vector3D(0, 0, 0)]
    for i, (a, d, alpha, t0) in enumerate(UR5_DH):
        T = _mat4(T, _dh_matrix(a, d, alpha, joints[i] + t0))
        positions.append(Vector3D(
            T[0][3] * 1000,
            T[1][3] * 1000,
            T[2][3] * 1000,
        ))
    end = Vector3D(T[0][3]*1000, T[1][3]*1000, T[2][3]*1000)
    return end, positions


def ur5_ik(target_mm: Vector3D) -> List[float]:
    """
    UR5 解析逆运动学（末端朝下抓取构型）
    Args:
        target_mm: 相对底座的目标位置 (mm)
    Returns:
        6 个关节角 (rad)
    """
    x = target_mm.x * SIM_SCALE
    y = target_mm.y * SIM_SCALE
    z = target_mm.z * SIM_SCALE

    j1 = math.atan2(y, x)
    r  = math.sqrt(x*x + y*y)

    l2 = 0.4250
    l3 = 0.3922
    # 末端朝下时腕部中心 Z 补偿
    wz = z + 0.1915
    wr = r

    dist2 = wr*wr + wz*wz
    dist  = math.sqrt(dist2)
    lo = abs(l2 - l3) + 0.001
    hi = l2 + l3 - 0.001
    if dist > hi:
        s = hi / dist; wr *= s; wz *= s; dist2 = wr*wr + wz*wz
    elif dist < lo:
        s = lo / max(dist, 1e-9); wr *= s; wz *= s; dist2 = wr*wr + wz*wz

    cos3 = max(-1.0, min(1.0, (dist2 - l2*l2 - l3*l3) / (2*l2*l3)))
    j3   = -math.acos(cos3)

    beta  = math.atan2(wz, wr)
    gamma = math.atan2(l3*math.sin(-j3), l2 + l3*math.cos(-j3))
    j2    = beta - gamma - math.pi/2

    j4 = -j2 - j3
    j5 = -math.pi/2
    j6 = j1
    return [j1, j2, j3, j4, j5, j6]


def _ease(t: float) -> float:
    t = max(0.0, min(1.0, t))
    return t * t * (3 - 2*t)


def _lerp(a, b, t):
    return a + (b - a) * t


def _lerp_joints(q0, q1, t):
    return [_lerp(a, b, t) for a, b in zip(q0, q1)]


# ============================================================
# UR5 机械臂控制器
# ============================================================

@dataclass
class UR5Arm:
    """
    UR5 六轴机械臂完整状态与状态机控制器。
    坐标系：仿真 mm，底座位于 base_pos（世界坐标）。
    """
    arm_id:   int
    base_pos: Vector3D

    joints:        List[float] = field(default_factory=lambda: list(HOME_JOINTS))
    target_joints: List[float] = field(default_factory=lambda: list(HOME_JOINTS))

    gripper:          GripperState = GripperState.OPEN
    gripper_progress: float = 0.0   # 0=全开, 1=全闭

    phase: ArmPhase   = ArmPhase.IDLE
    state: RobotState = RobotState.IDLE

    target_item:    Optional[object]    = None
    target_bin_pos: Optional[Vector3D]  = None
    target_bin_id:  int                 = -1

    move_progress:      float      = 0.0
    phase_start_joints: List[float] = field(default_factory=lambda: list(HOME_JOINTS))
    phase_duration:     float      = 1.0
    phase_elapsed:      float      = 0.0   # accumulated dt since phase start

    items_sorted:  int   = 0
    battery_level: float = 100.0

    # ---- 运动学 ----

    def get_end_effector_world(self) -> Vector3D:
        local, _ = ur5_fk(self.joints)
        return Vector3D(
            self.base_pos.x + local.x,
            self.base_pos.y + local.y,
            self.base_pos.z + local.z,
        )

    def get_joint_world_positions(self) -> List[Vector3D]:
        _, locals_ = ur5_fk(self.joints)
        return [
            Vector3D(
                self.base_pos.x + p.x,
                self.base_pos.y + p.y,
                self.base_pos.z + p.z,
            )
            for p in locals_
        ]

    def _ik(self, world_pos: Vector3D) -> List[float]:
        rel = Vector3D(
            world_pos.x - self.base_pos.x,
            world_pos.y - self.base_pos.y,
            world_pos.z - self.base_pos.z,
        )
        return ur5_ik(rel)

    # ---- 阶段控制 ----

    def _start_phase(self, phase: ArmPhase, target_joints: List[float], duration: float):
        self.phase              = phase
        self.phase_start_joints = list(self.joints)
        self.target_joints      = target_joints
        self.phase_duration     = max(duration, 0.05)
        self.phase_elapsed      = 0.0
        self.move_progress      = 0.0

    def assign_task(self, item, bin_pos: Vector3D, bin_id: int) -> bool:
        """从外部分配抓取任务"""
        if self.phase != ArmPhase.IDLE:
            return False
        self.target_item    = item
        self.target_bin_pos = bin_pos
        self.target_bin_id  = bin_id
        hover = Vector3D(item.position.x, item.position.y, item.position.z + 300)
        self._start_phase(ArmPhase.MOVING_TO_ITEM, self._ik(hover), 1.2)
        self.state = RobotState.MOVING
        return True

    def _advance_phase(self, environment) -> Optional[dict]:
        """当前阶段完成后推进到下一阶段"""
        ph = self.phase

        if ph == ArmPhase.MOVING_TO_ITEM:
            if self.target_item is None:
                self._go_home()
                return None
            grab_pos = Vector3D(
                self.target_item.position.x,
                self.target_item.position.y,
                self.target_item.position.z + 60,
            )
            self._start_phase(ArmPhase.DESCENDING, self._ik(grab_pos), 0.8)

        elif ph == ArmPhase.DESCENDING:
            self.gripper = GripperState.CLOSING
            self._start_phase(ArmPhase.GRIPPING, list(self.joints), 0.6)
            self.state = RobotState.GRIPPING

        elif ph == ArmPhase.GRIPPING:
            if self.target_item:
                lift_pos = Vector3D(
                    self.target_item.position.x,
                    self.target_item.position.y,
                    self.target_item.position.z + 400,
                )
                self._start_phase(ArmPhase.LIFTING, self._ik(lift_pos), 0.7)

        elif ph == ArmPhase.LIFTING:
            if self.target_bin_pos:
                hover_bin = Vector3D(
                    self.target_bin_pos.x,
                    self.target_bin_pos.y,
                    self.target_bin_pos.z + 350,
                )
                self._start_phase(ArmPhase.MOVING_TO_BIN, self._ik(hover_bin), 1.4)
                self.state = RobotState.MOVING

        elif ph == ArmPhase.MOVING_TO_BIN:
            if self.target_bin_pos:
                place_pos = Vector3D(
                    self.target_bin_pos.x,
                    self.target_bin_pos.y,
                    self.target_bin_pos.z + 80,
                )
                self._start_phase(ArmPhase.PLACING, self._ik(place_pos), 0.8)
                self.state = RobotState.PLACING

        elif ph == ArmPhase.PLACING:
            self.gripper = GripperState.OPENING
            event = {
                "type":   "item_placed",
                "arm_id": self.arm_id,
                "item":   self.target_item,
                "bin_id": self.target_bin_id,
            }
            self.items_sorted  += 1
            self.target_item    = None
            self.target_bin_pos = None
            self.target_bin_id  = -1
            self._go_home()
            return event

        elif ph == ArmPhase.RETURNING:
            self.phase = ArmPhase.IDLE
            self.state = RobotState.IDLE

        return None

    def _go_home(self):
        self._start_phase(ArmPhase.RETURNING, list(HOME_JOINTS), 1.0)
        self.state = RobotState.MOVING

    # ---- 主更新 ----

    def update(self, dt: float, environment=None) -> Optional[dict]:
        """
        每帧调用，驱动状态机 + 关节插值。
        Returns: 事件字典 or None
        """
        self.phase_elapsed += dt
        t = _ease(min(self.phase_elapsed / self.phase_duration, 1.0))
        self.move_progress = t

        # 关节角插值
        self.joints = _lerp_joints(self.phase_start_joints, self.target_joints, t)

        # 夹爪动画
        if self.gripper == GripperState.CLOSING:
            self.gripper_progress = min(self.gripper_progress + dt * 3.0, 1.0)
            if self.gripper_progress >= 1.0:
                self.gripper = GripperState.CLOSED
        elif self.gripper == GripperState.OPENING:
            self.gripper_progress = max(self.gripper_progress - dt * 3.0, 0.0)
            if self.gripper_progress <= 0.0:
                self.gripper = GripperState.OPEN

        # 携带物品时跟随末端
        if self.target_item and self.phase in (
            ArmPhase.GRIPPING, ArmPhase.LIFTING,
            ArmPhase.MOVING_TO_BIN, ArmPhase.PLACING
        ):
            ee = self.get_end_effector_world()
            self.target_item.position.x = ee.x
            self.target_item.position.y = ee.y
            self.target_item.position.z = ee.z - 60

        # 同步 RobotState
        _map = {
            ArmPhase.IDLE:           RobotState.IDLE,
            ArmPhase.MOVING_TO_ITEM: RobotState.MOVING,
            ArmPhase.DESCENDING:     RobotState.MOVING,
            ArmPhase.GRIPPING:       RobotState.GRIPPING,
            ArmPhase.LIFTING:        RobotState.MOVING,
            ArmPhase.MOVING_TO_BIN:  RobotState.MOVING,
            ArmPhase.PLACING:        RobotState.PLACING,
            ArmPhase.RETURNING:      RobotState.MOVING,
        }
        self.state = _map.get(self.phase, RobotState.IDLE)

        # 电量消耗
        if self.phase != ArmPhase.IDLE:
            self.battery_level = max(0.0, self.battery_level - dt * 0.05)

        # 阶段完成 → 推进状态机
        event = None
        if t >= 1.0:
            event = self._advance_phase(environment)
        return event

    def to_dict(self) -> dict:
        """序列化为 JSON 友好字典（供前端 Three.js 渲染）"""
        ee = self.get_end_effector_world()
        joint_world = self.get_joint_world_positions()
        return {
            "id":               self.arm_id,
            "state":            self.state.value,
            "phase":            self.phase.value,
            "joints":           [round(j, 4) for j in self.joints],
            "gripper":          self.gripper.value,
            "gripper_progress": round(self.gripper_progress, 3),
            "move_progress":    round(self.move_progress, 3),
            "battery":          round(self.battery_level, 1),
            "items_sorted":     self.items_sorted,
            "end_effector": {
                "x": round(ee.x, 1),
                "y": round(ee.y, 1),
                "z": round(ee.z, 1),
            },
            "joint_positions": [
                {"x": round(p.x, 1), "y": round(p.y, 1), "z": round(p.z, 1)}
                for p in joint_world
            ],
            "base_pos": {
                "x": round(self.base_pos.x, 1),
                "y": round(self.base_pos.y, 1),
                "z": round(self.base_pos.z, 1),
            },
            "has_item": self.target_item is not None,
        } 