"""
物理引擎 - 处理碰撞、重力、摩擦等物理计算
"""
import math
from typing import List, Tuple
from core.types import Vector3D, Item
from config.constants import (
    GRAVITY, FRICTION_COEFFICIENT, RESTITUTION_COEFFICIENT,
    COLLISION_MARGIN
)


class PhysicsSimulator:
    """物理模拟器 - 单体引擎计算物理过程"""
    
    def __init__(self):
        """初始化物理模拟器"""
        self.gravity = GRAVITY
        self.friction = FRICTION_COEFFICIENT
        self.restitution = RESTITUTION_COEFFICIENT
        self.collision_margin = COLLISION_MARGIN
        self.active_objects = []  # 需要进行物理计算的对象
    
    def update_item_physics(self, item: Item, delta_time: float, bounds: Tuple[float, float, float]):
        """
        更新物品的物理状态（位置、速度等）
        
        Args:
            item: 物品对象
            delta_time: 时间增量
            bounds: 环境边界 (width, length, height)
        """
        # 应用重力
        item.velocity.z -= self.gravity * delta_time
        
        # 应用摩擦力
        friction_deceleration = self.friction * self.gravity
        if item.velocity.x != 0:
            item.velocity.x *= (1 - friction_deceleration * delta_time)
        if item.velocity.y != 0:
            item.velocity.y *= (1 - friction_deceleration * delta_time)
        
        # 更新位置
        item.position.x += item.velocity.x * delta_time
        item.position.y += item.velocity.y * delta_time
        item.position.z += item.velocity.z * delta_time
        
        # 边界碰撞检测
        self._handle_boundary_collision(item, bounds)
    
    def _handle_boundary_collision(self, item: Item, bounds: Tuple[float, float, float]):
        """
        处理物品与环境边界的碰撞
        
        Args:
            item: 物品对象
            bounds: 环境边界 (width, length, height)
        """
        width, length, height = bounds
        item_radius = 25  # 假设物品是半径为25的球体
        
        # 检查X轴边界
        if item.position.x - item_radius < 0:
            item.position.x = item_radius
            item.velocity.x *= -self.restitution
        elif item.position.x + item_radius > width:
            item.position.x = width - item_radius
            item.velocity.x *= -self.restitution
        
        # 检查Y轴边界
        if item.position.y - item_radius < 0:
            item.position.y = item_radius
            item.velocity.y *= -self.restitution
        elif item.position.y + item_radius > length:
            item.position.y = length - item_radius
            item.velocity.y *= -self.restitution
        
        # 检查Z轴边界（地面）
        if item.position.z - item_radius < 0:
            item.position.z = item_radius
            item.velocity.z *= -self.restitution
        elif item.position.z + item_radius > height:
            item.position.z = height - item_radius
            item.velocity.z = 0
    
    def check_collision(self, item1: Item, item2: Item) -> bool:
        """
        检查两个物品是否碰撞
        
        Args:
            item1: 第一个物品
            item2: 第二个物品
        
        Returns:
            是否碰撞
        """
        # 简化为球体碰撞检测
        item_radius = 25
        distance = (item1.position - item2.position).length()
        return distance < (2 * item_radius + self.collision_margin)
    
    def resolve_collision(self, item1: Item, item2: Item):
        """
        解决两个物品的碰撞
        
        Args:
            item1: 第一个物品
            item2: 第二个物品
        """
        # 计算碰撞法向量
        normal = (item2.position - item1.position).normalize()
        
        # 交换速度分量（简化碰撞响应）
        relative_velocity = (item1.velocity - item2.velocity)
        dot_product = (relative_velocity.x * normal.x + 
                      relative_velocity.y * normal.y + 
                      relative_velocity.z * normal.z)
        
        if dot_product > 0:  # 物体在相互分离
            return
        
        # 应用恢复系数
        impulse = -(1 + self.restitution) * dot_product / 2
        
        impulse_vec = Vector3D(
            normal.x * impulse,
            normal.y * impulse,
            normal.z * impulse
        )
        
        item1.velocity = item1.velocity + impulse_vec
        item2.velocity = item2.velocity - impulse_vec
    
    def get_distance(self, pos1: Vector3D, pos2: Vector3D) -> float:
        """计算两点之间的距离"""
        return (pos1 - pos2).length()
    
    def calculate_fall_height(self, initial_height: float, velocity_z: float, time: float) -> float:
        """
        计算物品下落高度
        
        Args:
            initial_height: 初始高度
            velocity_z: Z轴速度
            time: 时间
        
        Returns:
            下落后的高度
        """
        height = initial_height + velocity_z * time - 0.5 * self.gravity * time ** 2
        return max(0, height)
