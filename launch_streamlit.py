#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🚀 Streamlit应用启动器
═════════════════════════════════════════

智能启动脚本：
  • 检查依赖是否安装
  • 自动安装缺失的依赖
  • 启动Streamlit应用
  • 提供有用的命令行选项

用法:
    python launch_streamlit.py              # 使用默认端口 8501
    python launch_streamlit.py --port 8502 # 使用自定义端口
    python launch_streamlit.py --help       # 查看帮助
"""

import sys
import subprocess
import importlib.util
import os
from pathlib import Path

class StreamlitLauncher:
    """Streamlit应用启动器"""

    def __init__(self):
        self.required_packages = {
            'streamlit': 'streamlit>=1.28.0',
            'plotly': 'plotly>=5.14.0',
            'pandas': 'pandas>=2.0.0',
        }
        self.missing_packages = []

    def check_encoding(self):
        """设置UTF-8编码"""
        if sys.stdout.encoding != 'utf-8':
            try:
                sys.stdout.reconfigure(encoding='utf-8')
            except:
                pass

    def check_package(self, package_name):
        """检查包是否已安装"""
        spec = importlib.util.find_spec(package_name)
        return spec is not None

    def check_dependencies(self):
        """检查所有依赖"""
        print("\n" + "="*80)
        print("📦 检查依赖...")
        print("="*80 + "\n")

        self.missing_packages = []
        
        for package_name, package_spec in self.required_packages.items():
            if self.check_package(package_name):
                print(f"✅ {package_name}: 已安装")
            else:
                print(f"❌ {package_name}: 未安装")
                self.missing_packages.append(package_spec)

        if self.missing_packages:
            print(f"\n⚠️  检测到 {len(self.missing_packages)} 个缺失的依赖")
            return False
        else:
            print("\n✅ 所有依赖都已安装！")
            return True

    def install_dependencies(self):
        """安装缺失的依赖"""
        if not self.missing_packages:
            return True

        print("\n" + "="*80)
        print(f"📥 安装 {len(self.missing_packages)} 个缺失的依赖...")
        print("="*80 + "\n")

        try:
            for package in self.missing_packages:
                print(f"安装 {package}...")
                subprocess.check_call([
                    sys.executable, '-m', 'pip', 'install', package
                ])
                print(f"✅ {package} 安装完成\n")
            
            print("\n✅ 所有依赖安装完成！")
            return True
        except subprocess.CalledProcessError as e:
            print(f"\n❌ 安装失败: {e}")
            print("\n💡 尝试手动安装:")
            print(f"   pip install {' '.join(self.missing_packages)}")
            return False

    def launch_streamlit(self, port=8501):
        """启动Streamlit应用"""
        print("\n" + "="*80)
        print("🚀 启动Streamlit应用...")
        print("="*80 + "\n")

        # 确保app.py存在
        app_path = Path(__file__).parent / "app.py"
        if not app_path.exists():
            print("❌ 错误: 找不到 app.py")
            print(f"   预期位置: {app_path}")
            return False

        print(f"📂 项目路径: {Path(__file__).parent}")
        print(f"📄 应用文件: {app_path}")
        print(f"🌐 应用地址: http://localhost:{port}")
        print("\n💡 提示:")
        print("   • 应用启动后，浏览器会自动打开")
        print("   • 按 Ctrl+C 可以停止应用")
        print("   • 修改Python文件后会自动重新运行")
        print("\n" + "="*80 + "\n")

        try:
            cmd = [
                sys.executable, '-m', 'streamlit', 'run',
                str(app_path),
                '--server.port', str(port),
                '--logger.level=info'
            ]
            
            print(f"执行命令: {' '.join(cmd)}\n")
            subprocess.run(cmd)
            
        except KeyboardInterrupt:
            print("\n\n✅ 应用已停止")
        except Exception as e:
            print(f"\n❌ 启动失败: {e}")
            print("\n💡 尝试手动启动:")
            print(f"   streamlit run app.py --server.port {port}")
            return False

        return True

    def show_welcome(self):
        """显示欢迎信息"""
        print("\n" + "╔"+"═"*78+"╗")
        print("║" + " "*78 + "║")
        print("║" + " "*15 + "欢迎使用 Streamlit 机器人分拣系统" + " "*27 + "║")
        print("║" + " "*78 + "║")
        print("╚"+"═"*78+"╝\n")

    def show_help(self):
        """显示帮助信息"""
        help_text = """
用法: python launch_streamlit.py [选项]

选项:
  --port PORT    指定服务器端口 (默认: 8501)
  --help, -h     显示此帮助信息

示例:
  python launch_streamlit.py              # 使用默认端口
  python launch_streamlit.py --port 8502  # 使用自定义端口

关于Streamlit配置的更多信息，请访问:
  https://docs.streamlit.io/library/advanced-features/configuration
"""
        print(help_text)

    def run(self, port=8501):
        """主要运行流程"""
        self.check_encoding()
        self.show_welcome()

        # 检查依赖
        if not self.check_dependencies():
            print("\n❓ 是否要自动安装缺失的依赖? (y/n)")
            response = input("请输入 [y/n]: ").strip().lower()
            
            if response == 'y':
                if not self.install_dependencies():
                    return False
            else:
                print("\n💡 请手动安装依赖:")
                print(f"   pip install {' '.join(self.missing_packages)}")
                return False

        # 启动应用
        return self.launch_streamlit(port)


def main():
    """主函数"""
    import argparse

    parser = argparse.ArgumentParser(
        description='启动Streamlit机器人分拣系统应用',
        add_help=True
    )
    parser.add_argument(
        '--port',
        type=int,
        default=8501,
        help='服务器端口 (默认: 8501)'
    )

    args = parser.parse_args()

    launcher = StreamlitLauncher()
    success = launcher.run(port=args.port)

    sys.exit(0 if success else 1)


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n🛑 已中断")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ 错误: {e}")
        sys.exit(1)
