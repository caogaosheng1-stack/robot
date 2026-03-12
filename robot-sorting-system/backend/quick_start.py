#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
快速启动脚本 - 运行验证和启动web服务器

使用方法:
    python quick_start.py verify     # 运行完整验证
    python quick_start.py web        # 启动web服务器
    python quick_start.py all        # 运行验证后启动web服务器
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

import subprocess
import time


def run_verification():
    """运行完整验证"""
    print("\n" + "="*70)
    print("  运行完整验证测试")
    print("="*70 + "\n")
    
    try:
        result = subprocess.run(
            [sys.executable, 'run_full_verification.py'],
            encoding='utf-8',
            errors='replace',
            cwd=os.path.abspath(os.path.dirname(__file__))
        )
        return result.returncode == 0
    except Exception as e:
        print(f"验证失败: {e}")
        return False


def start_web_server():
    """启动web服务器"""
    print("\n" + "="*70)
    print("  启动Web可视化服务器")
    print("="*70 + "\n")
    
    try:
        import flask
        print("✓ Flask已安装")
    except ImportError:
        print("✗ Flask未安装，正在安装...")
        subprocess.run([sys.executable, '-m', 'pip', 'install', 'flask'],
                      capture_output=True,
                      encoding='utf-8',
                      errors='replace')
        print("✓ Flask安装完成")
    
    print("\n启动服务器...\n")
    
    try:
        result = subprocess.run(
            [sys.executable, 'web_server.py'],
            encoding='utf-8',
            errors='replace',
            cwd=os.path.abspath(os.path.dirname(__file__))
        )
        return result.returncode == 0
    except Exception as e:
        print(f"启动失败: {e}")
        return False


def main():
    """主函数"""
    if len(sys.argv) > 1:
        command = sys.argv[1].lower()
    else:
        command = 'all'
    
    print("\n" + "🤖 " + "="*66 + " 🤖")
    print("    机器人智能分拣系统 - 快速启动")
    print("🤖 " + "="*66 + " 🤖\n")
    
    if command == 'verify':
        success = run_verification()
        sys.exit(0 if success else 1)
    
    elif command == 'web':
        start_web_server()
    
    elif command == 'all':
        print("将依次执行:")
        print("  1. 运行完整验证")
        print("  2. 启动Web服务器")
        print()
        
        time.sleep(2)
        
        print("\n[步骤1/2] 运行完整验证...")
        if run_verification():
            print("\n✅ 验证通过！\n")
            time.sleep(2)
            
            print("[步骤2/2] 启动Web服务器...")
            start_web_server()
        else:
            print("\n❌ 验证失败，中止启动")
            sys.exit(1)
    
    else:
        print("未知命令:", command)
        print("\n用法:")
        print("  python quick_start.py verify     # 运行完整验证")
        print("  python quick_start.py web        # 启动web服务器")  
        print("  python quick_start.py all        # 全部执行(默认)")


if __name__ == '__main__':
    main()
