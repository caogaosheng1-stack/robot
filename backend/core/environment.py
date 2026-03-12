"""
环境建模 - 虚拟工作空间的定义和管理
"""
from typing import List, Dict, Tuple
from core.types import Vector3D, Item, SortingBin, RobotArmState, RobotState
from config.constants import (
    ENVIRONMENT_WIDTH, ENVIRONMENT_LENGTH, ENVIRONMENT_HEIGHT,
    SORTING_BIN_COUNT, BIN_CAPACITY, ROBOT_ARM_LENGTH
)


class Environment3D:
    """3D环境 - 定义和管理虚拟工作空间"""
    
    def __init__(self, width: float = None, length: float = None, height: float = None):
        """
        初始化环境
        
        Args:
            width: 环境宽度 (mm)
            length: 环境长度 (mm)
            height: 环境高度 (mm)
        """
        self.width = width or ENVIRONMENT_WIDTH
        self.length = length or ENVIRONMENT_LENGTH
        self.height = height or ENVIRONMENT_HEIGHT
        
        # 物品容器
        self.items: Dict[int, Item] = {}
        self.item_counter = 0
        
        # 机械臂
        self.robot_arms: Dict[int, RobotArmState] = {}
        self.robot_counter = 0
        
        # 分拣箱
        self.sorting_bins: Dict[int, SortingBin] = {}
        self._initialize_sorting_bins()
        
        # 传送带等静态物体的位置
        self.conveyor_position = Vector3D(
            self.width / 2,
            self.length / 4,
            50
        )
    
    def _initialize_sorting_bins(self):
        """初始化分拣箱"""
        bin_spacing = self.width / (SORTING_BIN_COUNT + 1)
        
        for i in range(SORTING_BIN_COUNT):
            bin_position = Vector3D(
                bin_spacing * (i + 1),
                self.length - 200,  # 放在环境后方
                0
            )
            
            self.sorting_bins[i] = SortingBin(
                bin_id=i,
                position=bin_position,
                capacity=BIN_CAPACITY
            )
    
    def add_item(self, item: Item) -> int:
        """
        添加物品到环境
        
        Args:
            item: 物品对象
        
        Returns:
            物品ID
        """
        item.id = self.item_counter
        self.items[item.id] = item
        self.item_counter += 1
        return item.id
    
    def remove_item(self, item_id: int) -> bool:
        """
        从环境移除物品
        
        Args:
            item_id: 物品ID
        
        Returns:
            是否成功移除
        """
        if item_id in self.items:
            del self.items[item_id]
            return True
        return False
    
    def get_item(self, item_id: int) -> Item:
        """获取物品"""
        return self.items.get(item_id)
    
    def get_all_items(self) -> List[Item]:
        """获取所有物品"""
        return list(self.items.values())
    
    def add_robot_arm(self, arm_id: int, initial_position: Vector3D = None) -> int:
        """
        添加机械臂
        
        Args:
            arm_id: 机械臂ID
            initial_position: 初始位置
        
        Returns:
            机械臂ID
        """
        position = initial_position or Vector3D(
            self.width / 2,
            self.length / 4,
            self.height - 100
        )
        
        arm = RobotArmState(
            arm_id=arm_id,
            position=position.copy()
        )
        self.robot_arms[arm_id] = arm
        self.robot_counter += 1
        return arm_id
    
    def get_robot_arm(self, arm_id: int) -> RobotArmState:
        """获取机械臂"""
        return self.robot_arms.get(arm_id)
    
    def get_all_robots(self) -> List[RobotArmState]:
        """获取所有机械臂"""
        return list(self.robot_arms.values())
    
    def get_sorting_bin(self, bin_id: int) -> SortingBin:
        """获取分拣箱"""
        return self.sorting_bins.get(bin_id)
    
    def get_all_bins(self) -> List[SortingBin]:
        """获取所有分拣箱"""
        return list(self.sorting_bins.values())
    
    def get_environment_bounds(self) -> Tuple[float, float, float]:
        """获取环境边界"""
        return (self.width, self.length, self.height)
    
    def get_environment_info(self) -> Dict:
        """获取环境信息"""
        return {
            'width': self.width,
            'length': self.length,
            'height': self.height,
            'item_count': len(self.items),
            'robot_count': len(self.robot_arms),
            'bin_count': len(self.sorting_bins),
            'conveyor_position': self.conveyor_position.to_tuple()
        }
    
    def clear(self):
        """清空环境"""
        self.items.clear()
        self.robot_arms.clear()
        self.sorting_bins.clear()
        self._initialize_sorting_bins()
        self.item_counter = 0
        self.robot_counter = 0
