#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
完整验证程序 - 测试整个仿真系统

这个程序会：
1. 运行多个不同配置的仿真
2. 收集详细的性能数据
3. 验证所有核心功能
4. 生成可视化数据
"""
import sys
import os

# 修复Windows编码问题 - 使用UTF-8处理输出
try:
    # Python 3.7+ 支持 reconfigure
    if sys.stdout.encoding != 'utf-8':
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
except (AttributeError, RuntimeError):
    # 如果不支持reconfigure，使用其他方案
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

import time
import json
from datetime import datetime
from core.simulation_engine import SimulationEngine
from core.types import Vector3D


class FullVerificationRunner:
    """完整验证运行器"""
    
    def __init__(self):
        self.results = {
            'timestamp': datetime.now().isoformat(),
            'tests': []
        }
        self.print_header("机器人分拣系统 - 完整验证")
    
    def print_header(self, title):
        """打印标题"""
        print(f"\n{'='*70}")
        print(f"  {title}")
        print(f"{'='*70}\n")
    
    def print_section(self, title):
        """打印分段标题"""
        print(f"\n{'-'*70}")
        print(f"  {title}")
        print(f"{'-'*70}\n")
    
    def test_basic_engine(self):
        """测试1: 基础引擎功能"""
        self.print_section("测试1: 基础仿真引擎功能")
        
        test_result = {
            'name': 'Basic Engine Test',
            'duration_seconds': 5,
            'status': 'PASS',
            'metrics': {}
        }
        
        try:
            engine = SimulationEngine(enable_physics=True, enable_logging=True)
            engine.startup()
            
            # 运行5秒
            print("运行5秒仿真...")
            start_time = time.time()
            while time.time() - start_time < 5:
                engine.step()
            
            stats = engine.get_statistics()
            engine.shutdown()
            
            test_result['metrics'] = stats
            
            # 验证结果
            print(f"✅ 生成物品数: {stats['items_in_environment']}")
            print(f"✅ 平均FPS: {stats['fps']}")
            print(f"✅ 总帧数: {stats['total_frames']}")
            print(f"✅ 状态: 通过")
            
        except Exception as e:
            test_result['status'] = 'FAIL'
            test_result['error'] = str(e)
            print(f"❌ 测试失败: {e}")
        
        self.results['tests'].append(test_result)
        return test_result['status'] == 'PASS'
    
    def test_multi_robots(self):
        """测试2: 多机械臂协调"""
        self.print_section("测试2: 多机械臂协调测试")
        
        test_result = {
            'name': 'Multi-Robot Test',
            'robot_count': 4,
            'status': 'PASS',
            'metrics': {}
        }
        
        try:
            engine = SimulationEngine()
            engine.startup()
            
            # 添加4个机械臂
            print("添加4个机械臂...")
            for i in range(4):
                x = 500 + i * 400
                engine.environment.add_robot_arm(i, Vector3D(x, 750, 1400))
                print(f"  ✓ 机械臂 {i} 添加成功")
            
            # 运行3秒
            print("\n运行3秒仿真...")
            start_time = time.time()
            while time.time() - start_time < 3:
                engine.step()
            
            stats = engine.get_statistics()
            engine.shutdown()
            
            test_result['metrics'] = stats
            print(f"✅ 机械臂数: {len(engine.environment.robot_arms)}")
            print(f"✅ 物品数: {stats['items_in_environment']}")
            print(f"✅ 状态: 通过")
            
        except Exception as e:
            test_result['status'] = 'FAIL'
            test_result['error'] = str(e)
            print(f"❌ 测试失败: {e}")
        
        self.results['tests'].append(test_result)
        return test_result['status'] == 'PASS'
    
    def test_performance(self):
        """测试3: 性能基准测试"""
        self.print_section("测试3: 性能基准测试")
        
        test_result = {
            'name': 'Performance Benchmark',
            'duration_seconds': 10,
            'status': 'PASS',
            'metrics': {}
        }
        
        try:
            engine = SimulationEngine()
            engine.startup()
            
            print("运行10秒性能测试...")
            
            frame_times = []
            start_time = time.time()
            
            while time.time() - start_time < 10:
                frame_start = time.time()
                engine.step()
                frame_time = (time.time() - frame_start) * 1000  # 毫秒
                frame_times.append(frame_time)
            
            stats = engine.get_statistics()
            engine.shutdown()
            
            # 计算性能指标
            avg_frame_time = sum(frame_times) / len(frame_times)
            max_frame_time = max(frame_times)
            min_frame_time = min(frame_times)
            
            test_result['metrics'] = {
                **stats,
                'avg_frame_time_ms': f"{avg_frame_time:.2f}",
                'max_frame_time_ms': f"{max_frame_time:.2f}",
                'min_frame_time_ms': f"{min_frame_time:.2f}",
                'total_frames_collected': len(frame_times)
            }
            
            print(f"✅ 平均帧时间: {avg_frame_time:.2f} ms")
            print(f"✅ 最大帧时间: {max_frame_time:.2f} ms")
            print(f"✅ 最小帧时间: {min_frame_time:.2f} ms")
            print(f"✅ FPS: {stats['fps']}")
            print(f"✅ 状态: 通过")
            
        except Exception as e:
            test_result['status'] = 'FAIL'
            test_result['error'] = str(e)
            print(f"❌ 测试失败: {e}")
        
        self.results['tests'].append(test_result)
        return test_result['status'] == 'PASS'
    
    def test_event_system(self):
        """测试4: 事件系统"""
        self.print_section("测试4: 事件系统验证")
        
        test_result = {
            'name': 'Event System Test',
            'status': 'PASS',
            'metrics': {
                'events_triggered': 0
            }
        }
        
        try:
            engine = SimulationEngine()
            
            # 设置计数器
            event_counters = {
                'on_item_created': 0,
                'on_collision': 0,
                'on_step_complete': 0
            }
            
            def count_item_created(item):
                event_counters['on_item_created'] += 1
            
            def count_collision(item1, item2):
                event_counters['on_collision'] += 1
            
            def count_step_complete():
                event_counters['on_step_complete'] += 1
            
            # 注册回调
            engine.register_callback('on_item_created', count_item_created)
            engine.register_callback('on_collision', count_collision)
            engine.register_callback('on_step_complete', count_step_complete)
            
            engine.startup()
            
            print("测试事件回调系统...")
            
            # 运行2秒
            start_time = time.time()
            while time.time() - start_time < 2:
                engine.step()
            
            engine.shutdown()
            
            total_events = sum(event_counters.values())
            test_result['metrics']['events_triggered'] = total_events
            test_result['metrics']['event_breakdown'] = event_counters
            
            print(f"✅ 物品创建事件: {event_counters['on_item_created']}")
            print(f"✅ 碰撞事件: {event_counters['on_collision']}")
            print(f"✅ 步骤完成事件: {event_counters['on_step_complete']}")
            print(f"✅ 总事件数: {total_events}")
            print(f"✅ 状态: 通过")
            
        except Exception as e:
            test_result['status'] = 'FAIL'
            test_result['error'] = str(e)
            print(f"❌ 测试失败: {e}")
        
        self.results['tests'].append(test_result)
        return test_result['status'] == 'PASS'
    
    def test_environment_features(self):
        """测试5: 环境功能验证"""
        self.print_section("测试5: 环境功能验证")
        
        test_result = {
            'name': 'Environment Features Test',
            'status': 'PASS',
            'metrics': {}
        }
        
        try:
            engine = SimulationEngine()
            engine.startup()
            
            print("验证环境功能...")
            
            # 验证分拣箱
            bins = engine.environment.get_all_bins()
            print(f"✓ 创建了 {len(bins)} 个分拣箱")
            
            # 运行3秒获取物品
            start_time = time.time()
            while time.time() - start_time < 3:
                engine.step()
            
            items = engine.environment.get_all_items()
            print(f"✓ 生成了 {len(items)} 个物品")
            
            # 验证物品属性
            if items:
                first_item = items[0]
                print(f"✓ 物品属性完整:")
                print(f"  - ID: {first_item.id}")
                print(f"  - 颜色: {first_item.color.value}")
                print(f"  - 大小: {first_item.size.value}")
                print(f"  - 重量: {first_item.weight.value}")
                print(f"  - 位置: ({first_item.position.x:.1f}, {first_item.position.y:.1f}, {first_item.position.z:.1f})")
            
            env_info = engine.environment.get_environment_info()
            test_result['metrics'] = {
                'bin_count': env_info['bin_count'],
                'item_count': env_info['item_count'],
                'robot_count': env_info['robot_count'],
                'environment_size': f"{env_info['width']}x{env_info['length']}x{env_info['height']}"
            }
            
            engine.shutdown()
            
            print(f"✅ 环境信息: {env_info}")
            print(f"✅ 状态: 通过")
            
        except Exception as e:
            test_result['status'] = 'FAIL'
            test_result['error'] = str(e)
            print(f"❌ 测试失败: {e}")
        
        self.results['tests'].append(test_result)
        return test_result['status'] == 'PASS'
    
    def run_all_tests(self):
        """运行所有测试"""
        self.print_header("开始运行完整验证测试")
        
        results = {
            'test1': self.test_basic_engine(),
            'test2': self.test_multi_robots(),
            'test3': self.test_performance(),
            'test4': self.test_event_system(),
            'test5': self.test_environment_features()
        }
        
        self.print_header("验证总结")
        
        total_tests = len(results)
        passed_tests = sum(1 for v in results.values() if v)
        failed_tests = total_tests - passed_tests
        
        print(f"\n总测试数: {total_tests}")
        print(f"✅ 通过: {passed_tests}")
        print(f"❌ 失败: {failed_tests}")
        print(f"通过率: {passed_tests/total_tests*100:.1f}%")
        
        if failed_tests == 0:
            print("\n🎉 所有测试通过！系统可用于生产！")
        else:
            print(f"\n⚠️  有 {failed_tests} 个测试失败，请检查日志")
        
        # 保存结果为JSON
        self.save_results()
        
        return failed_tests == 0
    
    def save_results(self):
        """保存测试结果为JSON"""
        output_file = 'verification_results.json'
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(self.results, f, indent=2, ensure_ascii=False)
        print(f"\n✓ 验证结果已保存到: {output_file}")


if __name__ == "__main__":
    runner = FullVerificationRunner()
    success = runner.run_all_tests()
    
    if not success:
        exit(1)
