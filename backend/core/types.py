"""
数据类型定义 - 描述系统中的各种对象
"""
from dataclasses import dataclass, field
from typing import Tuple, List, Dict
from enum import Enum


# ==================== 枚举类型 ====================

class ItemSize(Enum):
    """物品尺寸枚举"""
    SMALL = "small"
    MEDIUM = "medium"
    LARGE = "large"


class ItemColor(Enum):
    """物品颜色枚举"""
    RED = "red"
    GREEN = "green"
    BLUE = "blue"
    YELLOW = "yellow"


class ItemWeight(Enum):
    """物品重量等级枚举"""
    LIGHT = "light"
    MEDIUM = "medium"
    HEAVY = "heavy"


class RobotState(Enum):
    """机械臂状态枚举"""
    IDLE = "idle"                  # 空闲
    MOVING = "moving"              # 运动中
    GRIPPING = "gripping"          # 抓取中
    PLACING = "placing"            # 放置中
    CHARGING = "charging"          # 充电中
    ERROR = "error"                # 故障


class TaskStatus(Enum):
    """任务状态枚举"""
    PENDING = "pending"            # 待处理
    PROCESSING = "processing"      # 处理中
    COMPLETED = "completed"        # 已完成
    FAILED = "failed"              # 失败


# ==================== 数据类 ====================

@dataclass
class Vector3D:
    """3D向量"""
    x: float = 0.0
    y: float = 0.0
    z: float = 0.0
    
    def __add__(self, other):
        return Vector3D(self.x + other.x, self.y + other.y, self.z + other.z)
    
    def __sub__(self, other):
        return Vector3D(self.x - other.x, self.y - other.y, self.z - other.z)
    
    def __mul__(self, scalar):
        return Vector3D(self.x * scalar, self.y * scalar, self.z * scalar)
    
    def length(self):
        """计算向量长度"""
        return (self.x ** 2 + self.y ** 2 + self.z ** 2) ** 0.5
    
    def normalize(self):
        """向量归一化"""
        length = self.length()
        if length > 0:
            return Vector3D(self.x / length, self.y / length, self.z / length)
        return Vector3D(0, 0, 0)
    
    def copy(self):
        """复制向量"""
        return Vector3D(self.x, self.y, self.z)
    
    def to_tuple(self):
        return (self.x, self.y, self.z)


@dataclass
class Item:
    """物品类 - 描述待分拣物品"""
    id: int
    size: ItemSize
    color: ItemColor
    weight: ItemWeight
    position: Vector3D = field(default_factory=lambda: Vector3D())
    velocity: Vector3D = field(default_factory=lambda: Vector3D())
    rotation: Vector3D = field(default_factory=lambda: Vector3D())
    timestamp: float = 0.0          # 物品创建时间
    classification: str = None      # 分类结果
    confidence: float = 0.0         # 分类置信度
    sorted_bin: int = -1            # 分配到的分拣箱 (-1表示未分配)
    
    def __hash__(self):
        return hash(self.id)


@dataclass
class RobotArmState:
    """机械臂状态"""
    arm_id: int
    state: RobotState = RobotState.IDLE
    position: Vector3D = field(default_factory=lambda: Vector3D())
    target_position: Vector3D = field(default_factory=lambda: Vector3D())
    joint_angles: List[float] = field(default_factory=lambda: [0.0] * 6)
    gripper_open: bool = True      # True表示开启, False表示闭合
    current_item: Item = None       # 当前抓取的物品
    battery_level: float = 100.0    # 电量百分比


@dataclass
class SortingBin:
    """分拣箱"""
    bin_id: int
    position: Vector3D
    capacity: int                   # 容量
    current_items: List[Item] = field(default_factory=list)
    full: bool = False
    
    def add_item(self, item: Item) -> bool:
        """添加物品到箱子"""
        if len(self.current_items) < self.capacity:
            self.current_items.append(item)
            self.full = len(self.current_items) >= self.capacity
            return True
        return False
    
    def remove_item(self, item: Item) -> bool:
        """从箱子移除物品"""
        if item in self.current_items:
            self.current_items.remove(item)
            self.full = False
            return True
        return False
    
    def get_fill_rate(self) -> float:
        """获取箱子填充率"""
        return len(self.current_items) / self.capacity


@dataclass
class SensingData:
    """传感器数据"""
    timestamp: float
    camera_frame: object = None      # 相机图像帧
    lidar_scan: List[float] = field(default_factory=list)  # 激光雷达扫描数据
    distance_sensors: Dict[str, float] = field(default_factory=dict)  # 距离传感器
    pressure_sensors: Dict[str, float] = field(default_factory=dict)  # 压力传感器
    imu_data: Dict[str, float] = field(default_factory=dict)  # 惯性测量数据


@dataclass
class Task:
    """分拣任务"""
    task_id: int
    item: Item
    target_bin: int
    status: TaskStatus = TaskStatus.PENDING
    assigned_robot: int = -1        # 分配的机械臂ID (+1表示未分配)
    start_time: float = None
    end_time: float = None
    retries: int = 0               # 重试次数
    
    def get_duration(self) -> float:
        """获取任务耗时"""
        if self.start_time and self.end_time:
            return self.end_time - self.start_time
        return None


@dataclass
class SimulationStats:
    """仿真统计数据"""
    total_items_processed: int = 0
    successful_sorts: int = 0
    failed_sorts: int = 0
    total_time: float = 0.0
    average_sort_time: float = 0.0
    accuracy_rate: float = 0.0
    robot_utilization: Dict[int, float] = field(default_factory=dict)
    bin_fill_rates: Dict[int, float] = field(default_factory=dict)
