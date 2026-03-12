#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
简单测试程序 - 演示核心仿真引擎的使用
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

import time

# 添加后端目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core.simulation_engine import SimulationEngine
from core.types import Vector3D


def print_separator(title: str = ""):
    """打印分界线"""
    if title:
        print(f"\n{'='*60}")
        print(f"  {title}")
        print(f"{'='*60}\n")
    else:
        print(f"{'-'*60}")


def on_item_created(item):
    """物品创建回调 - 简化版"""
    pass  # 注释掉详细日志，只在关键时刻输出


def on_item_removed(item):
    """物品移除回调 - 简化版"""
    pass  # 注释掉详细日志


def on_collision(item1, item2):
    """碰撞回调 - 简化版，不输出详细信息"""
    pass  # 注释掉详细日志以减少输出


def main():
    """主测试函数"""
    print_separator("机器人分拣系统 - 仿真引擎测试")
    
    # 1. 创建仿真引擎
    print("1. 初始化仿真引擎...")
    engine = SimulationEngine(enable_physics=True, enable_logging=True)
    engine.register_callback('on_item_created', on_item_created)
    engine.register_callback('on_item_removed', on_item_removed)
    engine.register_callback('on_collision', on_collision)
    
    # 2. 启动仿真
    print("\n2. 启动仿真...")
    engine.startup()
    
    # 3. 添加机械臂
    print("\n3. 添加机械臂...")
    engine.environment.add_robot_arm(0, Vector3D(1000, 750, 1400))
    engine.environment.add_robot_arm(1, Vector3D(1000, 750, 1400))
    print(f"✓ 添加 {len(engine.environment.get_all_robots())} 个机械臂")
    
    # 4. 运行仿真
    print_separator("运行仿真 (10秒)")
    print("生成物品和运行物理模拟...")
    print()
    
    start_time = time.time()
    while time.time() - start_time < 10:
        engine.step(spawn_items=True, update_physics=True)
        
        # 每1秒打印一次统计信息
        if engine.total_frames % 60 == 0:
            stats = engine.get_statistics()
            print(f"\n[第 {stats['total_frames']} 帧] "
                  f"时间: {stats['simulation_time']}, "
                  f"FPS: {stats['fps']}, "
                  f"物品总数: {stats['items_in_environment']}")
    
    # 5. 输出最终统计
    print_separator("仿真统计")
    stats = engine.get_statistics()
    for key, value in stats.items():
        print(f"  {key:.<40} {value}")
    
    # 6. 输出环境信息
    print_separator("环境信息")
    env_info = engine.environment.get_environment_info()
    for key, value in env_info.items():
        print(f"  {key:.<40} {value}")
    
    # 7. 输出分拣箱信息
    print_separator("分拣箱状态")
    for bin_obj in engine.environment.get_all_bins():
        fill_rate = bin_obj.get_fill_rate() * 100
        print(f"  分拣箱 {bin_obj.bin_id}: {len(bin_obj.current_items)}/{bin_obj.capacity} "
              f"({fill_rate:.1f}%)")
    
    # 8. 关闭仿真
    print_separator("关闭仿真")
    engine.shutdown()
    print(f"\n✓ 仿真完成！总耗时: {time.time() - start_time:.2f}s")


if __name__ == "__main__":
    main()
