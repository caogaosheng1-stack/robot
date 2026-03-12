#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🌟 快速启动脚本 - 一键开启机器人分拣系统演示

使用方法:
    python START_NOW.py          (显示菜单)
    python START_NOW.py verify   (仅验证)
    python START_NOW.py web      (仅Web)
    python START_NOW.py all      (完整流程)

说明:
    这是一个更友好的启动器，比 quick_start.py 提供更详细的反馈
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

import subprocess
import time
import json
from pathlib import Path


def print_header(title):
    """打印美化的标题"""
    print("\n" + "=" * 80)
    print(f"  {title}")
    print("=" * 80 + "\n")


def print_step(step_num, title, description=""):
    """打印步骤信息"""
    print(f"\n[步骤 {step_num}] {title}")
    if description:
        print(f"├─ {description}")


def print_success(msg):
    """打印成功消息"""
    print(f"✅ {msg}")


def print_error(msg):
    """打印错误消息"""
    print(f"❌ {msg}")


def print_info(msg):
    """打印信息消息"""
    print(f"ℹ️  {msg}")


def print_warning(msg):
    """打印警告消息"""
    print(f"⚠️  {msg}")


def run_verification():
    """运行完整验证"""
    print_header("🔍 运行完整验证测试")
    
    print_step(1, "初始化", "准备验证环境")
    time.sleep(0.5)
    
    print_step(2, "启动验证程序", "运行5个综合测试")
    print_info("这将需要约45秒，请耐心等待...\n")
    
    try:
        result = subprocess.run(
            [sys.executable, "run_full_verification.py"],
            capture_output=True,
            text=True,
            encoding='utf-8',
            errors='replace',
            timeout=120
        )
        
        if result.returncode == 0:
            print_success("验证程序执行成功！")
            
            # 尝试读取结果文件
            results_file = Path("verification_results.json")
            if results_file.exists():
                with open(results_file, "r", encoding="utf-8") as f:
                    results = json.load(f)
                    print_step(3, "验证结果概览")
                    
                    # 从tests数组计算统计
                    tests = results.get('tests', [])
                    num_tests = len(tests)
                    passed_tests = sum(1 for t in tests if t.get('status') == 'PASS')
                    failed_tests = num_tests - passed_tests
                    success_rate = (passed_tests / num_tests * 100) if num_tests > 0 else 0
                    
                    print(f"├─ 测试数量: {num_tests}")
                    print(f"├─ 通过测试: {passed_tests}")
                    print(f"├─ 失败测试: {failed_tests}")
                    print(f"└─ 成功率: {success_rate:.1f}%")
                    
                    if success_rate >= 80:
                        print("\n🎉 验证成功！系统运行正常。")
                    else:
                        print_warning("部分测试未通过，请查看详细日志。")
            
            return True
        else:
            print_error("验证程序执行失败！")
            print(result.stderr)
            return False
            
    except subprocess.TimeoutExpired:
        print_error("验证程序超时")
        return False
    except Exception as e:
        print_error(f"验证出错: {e}")
        return False


def run_web_server():
    """启动Web服务器"""
    print_header("🌐 启动Web服务器和可视化界面")
    
    print_step(1, "启动服务器", "自动选择Flask或标准库HTTP模式")
    print_info("服务器启动后，请打开浏览器访问以下地址:\n")
    print("┌─────────────────────────────────────────────┐")
    print("│  🌐 http://localhost:5000                   │")
    print("└─────────────────────────────────────────────┘\n")
    
    print_info("web服务器功能:")
    print("  ├─ 实时仿真可视化")
    print("  ├─ 性能统计数据")
    print("  ├─ 机械臂和物品追踪")
    print("  └─ 分拣结果展示\n")
    
    print_warning("按 Ctrl+C 停止服务器\n")
    
    try:
        subprocess.run(
            [sys.executable, "web_server.py"],
            encoding='utf-8',
            errors='replace',
            timeout=None
        )
        return True
    except KeyboardInterrupt:
        print("\n✅ 服务器已停止")
        return True
    except Exception as e:
        print_error(f"启动服务器失败: {e}")
        return False


def run_all():
    """完整流程：验证 + Web"""
    print_header("🚀 完整演示流程")
    
    print("这将执行以下步骤:")
    print("  1. 运行完整验证测试 (35-45秒)")
    print("  2. 启动Web服务器")
    print("  3. 打开可视化界面\n")
    
    print_step(1, "第一阶段", "验证系统完整性")
    print("─" * 40)
    
    if not run_verification():
        print_error("验证阶段失败，中止流程")
        return False
    
    time.sleep(2)
    
    print_step(2, "第二阶段", "启动Web可视化")
    print("─" * 40)
    
    if run_web_server():
        return True
    else:
        return False


def show_menu():
    """显示交互菜单"""
    print_header("🤖 机器人智能分拣系统 - 启动菜单")
    
    print("请选择要执行的操作:\n")
    print("  1️⃣  运行完整验证      [python START_NOW.py verify]")
    print("  2️⃣  启动Web服务器    [python START_NOW.py web]")
    print("  3️⃣  完整演示流程     [python START_NOW.py all]")
    print("  4️⃣  查看快速参考     [python START_NOW.py info]")
    print("  5️⃣  退出             \n")
    
    while True:
        try:
            choice = input("请输入选项 (1-5): ").strip()
            if choice in ['1', '2', '3', '4', '5']:
                return choice
            else:
                print_warning("请输入有效的选项 (1-5)")
        except KeyboardInterrupt:
            return '5'


def show_info():
    """显示快速参考"""
    with open("QUICK_REFERENCE.txt", "r", encoding="utf-8") as f:
        print(f.read())


def check_environment():
    """检查环境"""
    print("\n检查环境...")
    
    # 检查Python版本
    # 说明：完整依赖（如 Django 4.2）需要 Python 3.8+；
    # 但核心仿真 + Web演示（标准库HTTP/Flask）可在 3.7+ 运行。
    if sys.version_info < (3, 7):
        print_error(f"Python版本过低: {sys.version}")
        print_error("需要Python 3.7或更高版本")
        return False
    
    print_success(f"Python版本: {sys.version_info.major}.{sys.version_info.minor}")
    
    # 检查必要文件
    required_files = [
        "run_full_verification.py",
        "web_server.py",
        "templates/simulator.html",
        "core/simulation_engine.py"
    ]
    
    for file in required_files:
        if Path(file).exists():
            print_success(f"文件: {file}")
        else:
            print_error(f"缺少文件: {file}")
            return False
    
    return True


def main():
    """主函数"""
    os.chdir(Path(__file__).parent)
    
    # 处理命令行参数
    if len(sys.argv) > 1:
        command = sys.argv[1].lower()
        
        if command == "verify":
            run_verification()
        elif command == "web":
            run_web_server()
        elif command == "all":
            run_all()
        elif command == "info":
            show_info()
        else:
            print_error(f"未知命令: {command}")
            print("用法: python START_NOW.py [verify|web|all|info]")
            sys.exit(1)
    else:
        # 交互模式
        if check_environment():
            while True:
                choice = show_menu()
                
                if choice == '1':
                    run_verification()
                elif choice == '2':
                    run_web_server()
                elif choice == '3':
                    run_all()
                elif choice == '4':
                    show_info()
                elif choice == '5':
                    print_info("再见！")
                    break
        else:
            print_error("环境检查失败")
            sys.exit(1)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️  操作已取消")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ 发生错误: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
