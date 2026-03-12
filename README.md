# 🤖 机器人智能分拣系统

基于 **UR5 六轴机械臂**的物品自动分拣仿真系统，使用 Streamlit 实时展示双臂协作抓取过程，Plotly 3D 渲染真实正向运动学关节轨迹。

![Python](https://img.shields.io/badge/Python-3.8+-blue) ![Streamlit](https://img.shields.io/badge/Streamlit-1.28+-red) ![License](https://img.shields.io/badge/License-MIT-green)

## ✨ 功能特性

- **真实 UR5 运动学** — 解析式正/逆运动学，6 自由度关节动画
- **双臂协作分拣** — 两台 UR5 独立状态机，自动任务分配
- **颜色智能分拣** — 红/绿/蓝/黄四色物品自动路由到对应分拣箱
- **实时 3D 可视化** — Plotly 3D 渲染传送带、机械臂关节、分拣箱
- **性能监控** — FPS、处理量、准确率实时图表
- **Streamlit 部署** — 一键本地/云端运行

## 🚀 快速开始

### 1. 安装依赖

```bash
pip install -r requirements_streamlit.txt
```

### 2. 启动应用

```bash
streamlit run app.py
```

浏览器自动打开 `http://localhost:8501`

### 3. 使用步骤

1. 点击侧边栏 **初始化系统**
2. 点击 **启动分拣** 开始仿真
3. 观察 UR5 双臂实时抓取物品
4. 在各 Tab 查看数据分析和性能监控

## 📁 项目结构

```
robot-sorting-system/
├── app.py                          # Streamlit 主应用
├── requirements_streamlit.txt      # 精简依赖（仅 Streamlit 运行所需）
├── requirements.txt                # 完整依赖
├── backend/
│   ├── core/
│   │   ├── simulation_engine.py    # 仿真引擎（任务分配 + 状态机驱动）
│   │   ├── robot_arm.py            # UR5 运动学 + ArmPhase 状态机
│   │   ├── environment.py          # 3D 环境（物品/分拣箱/传送带）
│   │   ├── types.py                # 数据类型定义
│   │   └── physics.py              # 物理模拟
│   └── config/
│       └── constants.py            # 全局参数配置
└── README.md
```

## 🎯 分拣规则

| 物品颜色 | 目标分拣箱 |
|----------|------------|
| 🔴 红色  | Bin 0      |
| 🟢 绿色  | Bin 1      |
| 🔵 蓝色  | Bin 2      |
| 🟡 黄色  | Bin 3      |

## 🔧 技术栈

| 模块 | 技术 |
|------|------|
| 前端框架 | Streamlit |
| 3D 可视化 | Plotly |
| 数据处理 | Pandas / NumPy |
| 机器人运动学 | 纯 Python 解析式 UR5 DH 参数 |
| 物理引擎 | 自定义 Python 物理模拟 |

## ☁️ 部署到 Streamlit Cloud

1. Fork 本仓库到你的 GitHub
2. 访问 [share.streamlit.io](https://share.streamlit.io)
3. 选择仓库、分支和 `app.py` 作为入口文件
4. 在高级设置中指定 `requirements_streamlit.txt`
5. 点击 **Deploy** 完成部署

## 📄 License

MIT License
