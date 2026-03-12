"""
常量定义 - 整个系统的全局配置参数
"""

# ==================== 环境配置 ====================
ENVIRONMENT_WIDTH = 2000        # 分拣台宽度 (mm)
ENVIRONMENT_LENGTH = 3000       # 分拣台长度 (mm)
ENVIRONMENT_HEIGHT = 1500       # 分拣台高度 (mm)

# ==================== 传送带配置 ====================
CONVEYOR_SPEED = 0.5            # 传送带速度 (m/s)
CONVEYOR_WIDTH = 400            # 传送带宽度 (mm)

# ==================== 物品配置 ====================
ITEM_SPAWN_RATE = 0.0008         # 物品生成频率 (物品/ms) ≈ 0.8个/s，适合双臂分拣节奏
ITEM_SIZE_SMALL = (50, 50, 50)  # 小物品尺寸 (mm)
ITEM_SIZE_MEDIUM = (100, 100, 100)
ITEM_SIZE_LARGE = (150, 150, 150)

# 物品颜色定义（RGB）
ITEM_COLORS = {
    'red': (255, 0, 0),
    'green': (0, 255, 0),
    'blue': (0, 0, 255),
    'yellow': (255, 255, 0),
}

# 物品质量范围 (kg)
ITEM_WEIGHT_RANGE = {
    'light': (0.1, 0.5),
    'medium': (0.5, 1.5),
    'heavy': (1.5, 3.0),
}

# ==================== 机械臂配置 ====================
ROBOT_ARM_LENGTH = 1500         # 机械臂伸展长度 (mm)
ROBOT_ARM_SPEED = 500           # 机械臂移动速度 (mm/s)
ROBOT_PICKUP_TIME = 0.5         # 拾取时间 (s)
ROBOT_GRIPPER_FORCE = 50        # 夹爪力度 (N)

# ==================== 分拣箱配置 ====================
SORTING_BIN_COUNT = 4           # 分拣箱数量
BIN_CAPACITY = 100              # 每个箱子容量 (个物品)

# ==================== 物理参数 ====================
GRAVITY = 9.81                  # 重力加速度 (m/s²)
FRICTION_COEFFICIENT = 0.3      # 摩擦系数
RESTITUTION_COEFFICIENT = 0.5   # 恢复系数（碰撞亮度）

# ==================== 时间配置 ====================
SIMULATION_TIMESTEP = 0.01      # 仿真步长 (s)
TARGET_FPS = 60                 # 目标帧率 (fps)
FRAME_TIME = 1.0 / TARGET_FPS   # 每帧时间 (s)

# ==================== 传感器配置 ====================
CAMERA_FPS = 30                 # 相机帧率
CAMERA_RESOLUTION = (1280, 720) # 相机分辨率
LIDAR_RANGE = 2000              # 激光雷达范围 (mm)
LIDAR_RESOLUTION = 360          # 激光雷达角度分辨率

# ==================== 避障配置 ====================
RRT_ITERATIONS = 500            # RRT规划迭代次数
RRT_STEP_SIZE = 100             # RRT步长 (mm)
COLLISION_MARGIN = 50           # 碰撞检测边界 (mm)
OBSTACLE_BUFFER = 30            # 障碍物缓冲区 (mm)

# ==================== 决策系统配置 ====================
CONFIDENCE_THRESHOLD = 0.7      # 分类置信度阈值
MISCLASSIFICATION_RETRY = 3     # 误分类重试次数

# ==================== 数据库配置 ====================
DATABASE_NAME = 'robot_sorting'
DATABASE_HOST = 'localhost'
DATABASE_PORT = 5432
DATABASE_USER = 'postgres'
DATABASE_PASSWORD = 'password'

# ==================== 日志配置 ====================
LOG_LEVEL = 'INFO'
LOG_DIR = './logs'
LOG_FORMAT = '[%(asctime)s] %(levelname)s - %(name)s - %(message)s'
