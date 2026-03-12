"""
Franka Panda 机械臂运动学模型
7自由度协作机器人，臂展 855mm，白色流线外形，工业/研究界标杆
纯 Python 正向运动学 + 解析逆运动学近似
"""
import math
from enum import Enum
from dataclasses import dataclass, field
from typing import List, Optional, Tuple
from core.types import Vector3D, RobotState


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


# Franka Panda Modified-DH 参数 (单位 m)
# (a, d, alpha, theta_offset)
PANDA_DH = [
    (0.0,      0.333,   0.0,          0.0),
    (0.0,      0.0,    -math.pi/2,    0.0),
    (0.0,      0.316,   math.pi/2,    0.0),
    (0.0825,   0.0,     math.pi/2,    0.0),
    (-0.0825,  0.384,  -math.pi/2,    0.0),
    (0.0,      0.0,     math.pi/2,    0.0),
    (0.088,    0.107,   math.pi/2,    0.0),
]

HOME_JOINTS = [
    0.0, -math.pi/4, 0.0, -3*math.pi/4, 0.0, math.pi/2, math.pi/4
]

JOINT_LIMITS = [
    (-2.8973, 2.8973), (-1.7628, 1.7628), (-2.8973, 2.8973),
    (-3.0718,-0.0698), (-2.8973, 2.8973), (-0.0175, 3.7525),
    (-2.8973, 2.8973),
]

SIM_SCALE = 0.001


def _dh(a, d, alpha, theta):
    ca, sa = math.cos(alpha), math.sin(alpha)
    ct, st = math.cos(theta), math.sin(theta)
    return [
        [ct,     -st,      0,    a   ],
        [st*ca,   ct*ca,  -sa,  -sa*d],
        [st*sa,   ct*sa,   ca,   ca*d],
        [0,       0,       0,    1   ],
    ]


def _mm(A, B):
    C = [[0.0]*4 for _ in range(4)]
    for i in range(4):
        for j in range(4):
            for k in range(4):
                C[i][j] += A[i][k] * B[k][j]
    return C


def panda_fk(joints: List[float]) -> Tuple[Vector3D, List[Vector3D]]:
    """Panda 正向运动学，返回 (末端mm, 各关节mm列表)"""
    T = [[1,0,0,0],[0,1,0,0],[0,0,1,0],[0,0,0,1]]
    positions = [Vector3D(0, 0, 0)]
    q = list(joints) + [0.0] * max(0, 7 - len(joints))
    for i, (a, d, alpha, t0) in enumerate(PANDA_DH):
        T = _mm(T, _dh(a, d, alpha, q[i] + t0))
        positions.append(Vector3D(T[0][3]*1000, T[1][3]*1000, T[2][3]*1000))
    return Vector3D(T[0][3]*1000, T[1][3]*1000, T[2][3]*1000), positions


def _clamp(joints):
    return [max(lo, min(hi, j)) for j,(lo,hi) in zip(joints, JOINT_LIMITS)]


def panda_ik(target_mm: Vector3D, seed: List[float] = None) -> List[float]:
    """Panda 逆运动学（解析近似，末端朝下抓取构型）"""
    x = target_mm.x * SIM_SCALE
    y = target_mm.y * SIM_SCALE
    z = target_mm.z * SIM_SCALE

    j1 = math.atan2(y, x)
    r  = math.sqrt(x*x + y*y)
    L1, L2 = 0.649, 0.491

    wz = z + 0.107
    wr = r
    dist = math.sqrt(max(wr*wr + wz*wz, 1e-9))
    dist = max(abs(L1-L2)+0.02, min(L1+L2-0.02, dist))
    scale = dist / max(math.sqrt(wr*wr+wz*wz), 1e-9)
    wr *= scale; wz *= scale
    dist2 = wr*wr + wz*wz

    c3 = max(-1.0, min(1.0, (dist2 - L1*L1 - L2*L2) / (2*L1*L2)))
    j3a = math.acos(c3)
    beta  = math.atan2(wz, wr)
    gamma = math.atan2(L2*math.sin(j3a), L1 + L2*c3)
    j2a   = beta - gamma - math.pi/2

    q = [
        j1,
        max(-1.76, min(1.76, j2a)),
        0.0,
        max(-3.07, min(-0.07, -math.pi/2 - j3a*0.5)),
        0.0,
        max(0.0,   min(3.75,  math.pi/2 + j3a*0.3)),
        j1 * 0.5,
    ]
    return _clamp(q)


def _ease(t):
    t = max(0.0, min(1.0, t))
    return t*t*(3 - 2*t)

def _lerp(a, b, t): return a + (b-a)*t
def _lerp_joints(q0, q1, t): return [_lerp(a,b,t) for a,b in zip(q0,q1)]

@dataclass
class UR5Arm:  # 保持类名兼容引擎代码，内部实现为 Franka Panda
    """
    Franka Panda 7轴机械臂状态机控制器
    （类名保持 UR5Arm 以兼容 simulation_engine.py）
    """
    arm_id:   int
    base_pos: Vector3D

    joints:        List[float] = field(default_factory=lambda: list(HOME_JOINTS))
    target_joints: List[float] = field(default_factory=lambda: list(HOME_JOINTS))

    gripper:          GripperState = GripperState.OPEN
    gripper_progress: float = 0.0

    phase: ArmPhase   = ArmPhase.IDLE
    state: RobotState = RobotState.IDLE

    target_item:    Optional[object]   = None
    target_bin_pos: Optional[Vector3D] = None
    target_bin_id:  int                = -1

    move_progress:      float      = 0.0
    phase_start_joints: List[float] = field(default_factory=lambda: list(HOME_JOINTS))
    phase_duration:     float      = 1.0
    phase_elapsed:      float      = 0.0

    items_sorted:  int   = 0
    battery_level: float = 100.0

    def get_end_effector_world(self) -> Vector3D:
        local, _ = panda_fk(self.joints)
        return Vector3D(self.base_pos.x+local.x, self.base_pos.y+local.y, self.base_pos.z+local.z)

    def get_joint_world_positions(self) -> List[Vector3D]:
        _, locs = panda_fk(self.joints)
        return [Vector3D(self.base_pos.x+p.x, self.base_pos.y+p.y, self.base_pos.z+p.z) for p in locs]

    def _ik(self, world_pos: Vector3D) -> List[float]:
        rel = Vector3D(world_pos.x-self.base_pos.x, world_pos.y-self.base_pos.y, world_pos.z-self.base_pos.z)
        return panda_ik(rel, seed=list(self.joints))

    def _start_phase(self, phase, target_joints, duration):
        self.phase              = phase
        self.phase_start_joints = list(self.joints)
        self.target_joints      = list(target_joints)
        self.phase_duration     = max(duration, 0.05)
        self.phase_elapsed      = 0.0
        self.move_progress      = 0.0

    def assign_task(self, item, bin_pos: Vector3D, bin_id: int) -> bool:
        if self.phase != ArmPhase.IDLE:
            return False
        self.target_item    = item
        self.target_bin_pos = bin_pos
        self.target_bin_id  = bin_id
        hover = Vector3D(item.position.x, item.position.y, item.position.z + 320)
        self._start_phase(ArmPhase.MOVING_TO_ITEM, self._ik(hover), 1.2)
        self.state = RobotState.MOVING
        return True

    def _advance_phase(self, environment):
        ph = self.phase
        if ph == ArmPhase.MOVING_TO_ITEM:
            if self.target_item is None:
                self._go_home(); return None
            grab = Vector3D(self.target_item.position.x,
                            self.target_item.position.y,
                            self.target_item.position.z + 70)
            self._start_phase(ArmPhase.DESCENDING, self._ik(grab), 0.8)

        elif ph == ArmPhase.DESCENDING:
            self.gripper = GripperState.CLOSING
            self._start_phase(ArmPhase.GRIPPING, list(self.joints), 0.5)
            self.state = RobotState.GRIPPING

        elif ph == ArmPhase.GRIPPING:
            if self.target_item:
                lift = Vector3D(self.target_item.position.x,
                                self.target_item.position.y,
                                self.target_item.position.z + 420)
                self._start_phase(ArmPhase.LIFTING, self._ik(lift), 0.7)

        elif ph == ArmPhase.LIFTING:
            if self.target_bin_pos:
                hover_bin = Vector3D(self.target_bin_pos.x,
                                     self.target_bin_pos.y,
                                     self.target_bin_pos.z + 380)
                self._start_phase(ArmPhase.MOVING_TO_BIN, self._ik(hover_bin), 1.4)
                self.state = RobotState.MOVING

        elif ph == ArmPhase.MOVING_TO_BIN:
            if self.target_bin_pos:
                place = Vector3D(self.target_bin_pos.x,
                                 self.target_bin_pos.y,
                                 self.target_bin_pos.z + 90)
                self._start_phase(ArmPhase.PLACING, self._ik(place), 0.8)
                self.state = RobotState.PLACING

        elif ph == ArmPhase.PLACING:
            self.gripper = GripperState.OPENING
            event = {"type":"item_placed","arm_id":self.arm_id,
                     "item":self.target_item,"bin_id":self.target_bin_id}
            self.items_sorted += 1
            self.target_item = self.target_bin_pos = None
            self.target_bin_id = -1
            self._go_home()
            return event

        elif ph == ArmPhase.RETURNING:
            self.phase = ArmPhase.IDLE
            self.state = RobotState.IDLE

        return None

    def _go_home(self):
        self._start_phase(ArmPhase.RETURNING, list(HOME_JOINTS), 1.0)
        self.state = RobotState.MOVING

    def update(self, dt: float, environment=None):
        self.phase_elapsed += dt
        t = _ease(min(self.phase_elapsed / self.phase_duration, 1.0))
        self.move_progress = t
        self.joints = _lerp_joints(self.phase_start_joints, self.target_joints, t)

        if self.gripper == GripperState.CLOSING:
            self.gripper_progress = min(self.gripper_progress + dt*3.0, 1.0)
            if self.gripper_progress >= 1.0:
                self.gripper = GripperState.CLOSED
        elif self.gripper == GripperState.OPENING:
            self.gripper_progress = max(self.gripper_progress - dt*3.0, 0.0)
            if self.gripper_progress <= 0.0:
                self.gripper = GripperState.OPEN

        if self.target_item and self.phase in (
            ArmPhase.GRIPPING, ArmPhase.LIFTING,
            ArmPhase.MOVING_TO_BIN, ArmPhase.PLACING
        ):
            ee = self.get_end_effector_world()
            self.target_item.position.x = ee.x
            self.target_item.position.y = ee.y
            self.target_item.position.z = ee.z - 60

        _map = {
            ArmPhase.IDLE:RobotState.IDLE, ArmPhase.MOVING_TO_ITEM:RobotState.MOVING,
            ArmPhase.DESCENDING:RobotState.MOVING, ArmPhase.GRIPPING:RobotState.GRIPPING,
            ArmPhase.LIFTING:RobotState.MOVING, ArmPhase.MOVING_TO_BIN:RobotState.MOVING,
            ArmPhase.PLACING:RobotState.PLACING, ArmPhase.RETURNING:RobotState.MOVING,
        }
        self.state = _map.get(self.phase, RobotState.IDLE)

        if self.phase != ArmPhase.IDLE:
            self.battery_level = max(0.0, self.battery_level - dt*0.04)

        if t >= 1.0:
            return self._advance_phase(environment)
        return None

    def to_dict(self) -> dict:
        ee = self.get_end_effector_world()
        joint_world = self.get_joint_world_positions()
        return {
            "id":               self.arm_id,
            "state":            self.state.value,
            "phase":            self.phase.value,
            "joints":           [round(j,4) for j in self.joints],
            "gripper":          self.gripper.value,
            "gripper_progress": round(self.gripper_progress, 3),
            "move_progress":    round(self.move_progress, 3),
            "battery":          round(self.battery_level, 1),
            "items_sorted":     self.items_sorted,
            "end_effector":     {"x":round(ee.x,1),"y":round(ee.y,1),"z":round(ee.z,1)},
            "joint_positions":  [{"x":round(p.x,1),"y":round(p.y,1),"z":round(p.z,1)}
                                  for p in joint_world],
            "base_pos":         {"x":round(self.base_pos.x,1),
                                  "y":round(self.base_pos.y,1),
                                  "z":round(self.base_pos.z,1)},
            "has_item":         self.target_item is not None,
        }
