"""
时间管理系统 - 控制仿真的时钟和帧率
"""
import time
from config.constants import SIMULATION_TIMESTEP, FRAME_TIME


class TimeManager:
    """时间管理器 - 管理仿真时间和真实时间同步"""
    
    def __init__(self):
        """初始化时间管理器"""
        self.simulation_time = 0.0      # 仿真时间 (s)
        self.real_time = 0.0            # 真实时间 (s)
        self.delta_time = SIMULATION_TIMESTEP  # 每步时间增量
        self.frame_count = 0            # 帧计数
        self.fps = 0                    # 当前FPS
        self.last_time = time.time()    # 上次时间戳
        self.time_speed = 1.0           # 时间加速倍数 (1.0 = 正常速度)
        self.paused = False             # 是否暂停
        self.frame_times = []           # 用于FPS计算
        self.max_fps_history = 60       # 保留最近60帧的时间数据
    
    def update(self):
        """
        更新时间信息
        需要在每个仿真步骤中调用一次
        """
        current_time = time.time()
        frame_elapsed = current_time - self.last_time
        
        # 记录帧时间用于FPS计算
        self.frame_times.append(frame_elapsed)
        if len(self.frame_times) > self.max_fps_history:
            self.frame_times.pop(0)
        
        # 计算当前FPS
        if len(self.frame_times) > 0:
            avg_frame_time = sum(self.frame_times) / len(self.frame_times)
            self.fps = 1.0 / avg_frame_time if avg_frame_time > 0 else 0
        
        # 更新时间戳
        self.last_time = current_time
        
        if not self.paused:
            # 更新仿真时间和真实时间
            actual_delta = self.delta_time * self.time_speed
            self.simulation_time += actual_delta
            self.real_time += frame_elapsed
            self.frame_count += 1
    
    def get_simulation_time(self):
        """获取仿真时间"""
        return self.simulation_time
    
    def get_delta_time(self):
        """获取上一帧的时间增量"""
        return self.delta_time * self.time_speed
    
    def get_fps(self):
        """获取当前FPS"""
        return self.fps
    
    def get_frame_count(self):
        """获取总帧数"""
        return self.frame_count
    
    def set_time_speed(self, speed):
        """
        设置时间加速倍数
        Args:
            speed: 倍数 (0.5 = 半速, 2.0 = 双倍速)
        """
        self.time_speed = max(0.1, speed)  # 最小0.1倍速
    
    def pause(self):
        """暂停仿真"""
        self.paused = True
    
    def resume(self):
        """继续仿真"""
        self.paused = False
    
    def reset(self):
        """重置时间管理器"""
        self.simulation_time = 0.0
        self.real_time = 0.0
        self.frame_count = 0
        self.fps = 0
        self.last_time = time.time()
        self.frame_times = []
    
    def __str__(self):
        return f"TimeManager(sim_time={self.simulation_time:.2f}s, fps={self.fps:.1f}, frame={self.frame_count})"
