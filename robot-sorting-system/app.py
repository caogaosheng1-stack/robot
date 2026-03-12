#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import streamlit as st
import sys, os, time
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

ROOT = os.path.dirname(os.path.abspath(__file__))
BACKEND = os.path.join(ROOT, 'backend')
if BACKEND not in sys.path:
    sys.path.insert(0, BACKEND)

from backend.core.simulation_engine import SimulationEngine
from backend.core.robot_arm import ArmPhase, GripperState

# ================================================================
# Page config
# ================================================================
st.set_page_config(
    page_title="\u673a\u5668\u4eba\u667a\u80fd\u5206\u62e3\u7cfb\u7edf",
    page_icon="\U0001f916",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Share+Tech+Mono&family=Rajdhani:wght@500;700&display=swap');
html,body,[class*="css"]{font-family:'Rajdhani',sans-serif;}
.stApp{background:linear-gradient(135deg,#0a0e1a 0%,#0d1b2a 50%,#0a1628 100%);color:#c8d8e8;}
.stTabs [data-baseweb="tab-list"]{background:rgba(255,255,255,0.04);border-radius:8px;padding:4px;}
.stTabs [data-baseweb="tab"]{color:#7a9bb5;font-family:'Rajdhani',sans-serif;font-weight:700;font-size:15px;letter-spacing:1px;}
.stTabs [aria-selected="true"]{color:#00d4ff!important;background:rgba(0,212,255,0.12)!important;border-radius:6px;}
div[data-testid="metric-container"]{background:rgba(0,212,255,0.06);border:1px solid rgba(0,212,255,0.2);border-radius:10px;padding:12px 16px;}
div[data-testid="metric-container"] label{color:#7ab8d4!important;font-size:12px!important;letter-spacing:1px!important;}
div[data-testid="metric-container"] [data-testid="stMetricValue"]{color:#00d4ff!important;font-family:'Share Tech Mono',monospace!important;font-size:28px!important;}
.stButton>button{background:rgba(0,212,255,0.1);border:1px solid rgba(0,212,255,0.4);color:#00d4ff;font-family:'Rajdhani',sans-serif;font-weight:700;letter-spacing:1px;border-radius:6px;transition:all 0.2s;}
.stButton>button:hover{background:rgba(0,212,255,0.22);border-color:#00d4ff;color:#fff;}
hr{border-color:rgba(0,212,255,0.15);}
.sec{font-family:'Share Tech Mono',monospace;color:#00d4ff;font-size:12px;letter-spacing:3px;text-transform:uppercase;border-bottom:1px solid rgba(0,212,255,0.2);padding-bottom:4px;margin-bottom:8px;}
</style>
""", unsafe_allow_html=True)

# ================================================================
# Session state
# ================================================================
for _k, _v in [("engine",None),("is_running",False),("stats_history",[]),("event_log",[])]:
    if _k not in st.session_state:
        st.session_state[_k] = _v

# ================================================================
# Helpers
# ================================================================
def init_engine():
    st.session_state.engine = SimulationEngine(enable_logging=False)
    st.session_state.engine.startup()
    st.session_state.stats_history = []
    st.session_state.event_log = []

def get_stats():
    if st.session_state.engine:
        return st.session_state.engine.get_statistics()
    return None

def get_bins_df():
    eng = st.session_state.engine
    if eng is None:
        return pd.DataFrame()
    rows = []
    for b in eng.environment.get_all_bins():
        fill = len(b.current_items)
        rows.append({
            '\u5206\u62e3\u7b31': f'Bin {b.bin_id}',
            '\u5df2\u5b58\u7269\u54c1': fill,
            '\u5bb9\u91cf': b.capacity,
            '\u88c5\u8f7d\u7387(%)': round(fill / b.capacity * 100, 1),
        })
    return pd.DataFrame(rows)

def get_items_df():
    eng = st.session_state.engine
    if eng is None:
        return pd.DataFrame()
    rows = []
    for item in list(eng.environment.get_all_items())[:30]:
        rows.append({
            'ID': item.id,
            '\u989c\u8272': item.color.value,
            '\u5c3a\u5bf8': item.size.value,
            '\u91cd\u91cf': item.weight.value,
            'X(mm)': round(item.position.x, 0),
            'Y(mm)': round(item.position.y, 0),
            '\u5df2\u5206\u62e3': '\u2713' if item.sorted_bin >= 0 else '\u2014',
        })
    return pd.DataFrame(rows)
# ================================================================
# 3-D scene builder
# ================================================================
_ARM_COLORS = ["#00d4ff", "#ff6b35"]
_PHASE_LBL = {
    ArmPhase.IDLE: "IDLE",
    ArmPhase.MOVING_TO_ITEM: "->ITEM",
    ArmPhase.DESCENDING: "DOWN",
    ArmPhase.GRIPPING: "GRIP",
    ArmPhase.LIFTING: "LIFT",
    ArmPhase.MOVING_TO_BIN: "->BIN",
    ArmPhase.PLACING: "PLACE",
    ArmPhase.RETURNING: "HOME",
}

def build_3d_scene():
    eng = st.session_state.engine
    if eng is None:
        return None
    fig = go.Figure()
    env = eng.environment
    cx = env.conveyor_position.x
    cz = env.conveyor_position.z
    w  = 200

    # --- Conveyor belt ---
    fig.add_trace(go.Mesh3d(
        x=[cx-w, cx+w, cx+w, cx-w],
        y=[50, 50, env.length-100, env.length-100],
        z=[cz, cz, cz, cz],
        i=[0, 0], j=[1, 2], k=[2, 3],
        color="#1e3a4a", opacity=0.55,
        name="传送带", showlegend=True, hoverinfo="name",
    ))
    for dx in [-w, w]:
        fig.add_trace(go.Scatter3d(
            x=[cx+dx, cx+dx], y=[50, env.length-100], z=[cz+2, cz+2],
            mode="lines", line=dict(color="#00d4ff", width=2),
            showlegend=False, hoverinfo="skip"))

    # --- Sorting bins ---
    bin_pal = ["#2ecc71", "#e74c3c", "#3498db", "#f39c12"]
    for b in env.get_all_bins():
        bx, by, bz = b.position.x, b.position.y, b.position.z
        hw = 80
        col = bin_pal[b.bin_id % 4]
        fr  = len(b.current_items) / max(b.capacity, 1)
        corners = [
            (bx-hw, by-hw, bz),   (bx+hw, by-hw, bz),
            (bx+hw, by+hw, bz),   (bx-hw, by+hw, bz),
            (bx-hw, by-hw, bz+160),(bx+hw, by-hw, bz+160),
            (bx+hw, by+hw, bz+160),(bx-hw, by+hw, bz+160),
        ]
        edges = [(0,1),(1,2),(2,3),(3,0),(4,5),(5,6),(6,7),(7,4),(0,4),(1,5),(2,6),(3,7)]
        for s, e in edges:
            fig.add_trace(go.Scatter3d(
                x=[corners[s][0], corners[e][0]],
                y=[corners[s][1], corners[e][1]],
                z=[corners[s][2], corners[e][2]],
                mode="lines", line=dict(color=col, width=3),
                showlegend=False, hoverinfo="skip"))
        if fr > 0:
            fh = fr * 150
            fig.add_trace(go.Mesh3d(
                x=[bx-hw+6,bx+hw-6,bx+hw-6,bx-hw+6,bx-hw+6,bx+hw-6,bx+hw-6,bx-hw+6],
                y=[by-hw+6,by-hw+6,by+hw-6,by+hw-6,by-hw+6,by-hw+6,by+hw-6,by+hw-6],
                z=[bz+6,bz+6,bz+6,bz+6,bz+6+fh,bz+6+fh,bz+6+fh,bz+6+fh],
                i=[0,0,0,1,4,4], j=[1,2,3,2,5,6], k=[2,3,1,3,6,7],
                color=col, opacity=0.35, showlegend=False, hoverinfo="skip"))
        fig.add_trace(go.Scatter3d(
            x=[bx], y=[by], z=[bz+230],
            mode="text",
            text=[f"Bin {b.bin_id}  {len(b.current_items)}件"],
            textfont=dict(color=col, size=12, family="Share Tech Mono"),
            showlegend=False, hoverinfo="skip"))

    # --- Items on conveyor ---
    items = env.get_all_items()
    if items:
        cmap = {"red":"#ff4444","green":"#44ff88","blue":"#4488ff","yellow":"#ffdd44"}
        ix, iy, iz, ic, itxt = [], [], [], [], []
        for it in items:
            ix.append(it.position.x)
            iy.append(it.position.y)
            iz.append(it.position.z + 20)
            ic.append(cmap.get(it.color.value, "#aaa"))
            itxt.append(f"ID:{it.id} {it.color.value} {it.size.value}")
        fig.add_trace(go.Scatter3d(
            x=ix, y=iy, z=iz, mode="markers",
            marker=dict(size=10, color=ic, opacity=0.95, line=dict(width=1, color="#fff")),
            name="传送带物品", text=itxt,
            hovertemplate="%{text}<extra></extra>"))

    # --- UR5 arms (real FK joint positions) ---
    for arm in eng.get_arms():
        ad  = arm.to_dict()
        pts = ad["joint_positions"]
        col = _ARM_COLORS[arm.arm_id % 2]
        plb = _PHASE_LBL.get(arm.phase, arm.phase.value)
        has = ad["has_item"]
        xs = [p["x"] for p in pts]
        ys = [p["y"] for p in pts]
        zs = [p["z"] for p in pts]
        # links
        fig.add_trace(go.Scatter3d(
            x=xs, y=ys, z=zs, mode="lines",
            line=dict(color=col, width=7),
            name=f"Arm {arm.arm_id}", showlegend=True, hoverinfo="skip"))
        # joints
        fig.add_trace(go.Scatter3d(
            x=xs, y=ys, z=zs, mode="markers",
            marker=dict(size=[8,10,10,10,10,10,12], color=col, line=dict(width=1, color="#fff")),
            showlegend=False,
            hovertemplate=f"Arm {arm.arm_id}<br>Phase:{plb}<br>Battery:{ad['battery']}%<extra></extra>"))
        # end-effector
        ee = ad["end_effector"]
        gcol = "#ff0055" if has else ("#00ff88" if arm.gripper == GripperState.OPEN else "#ffaa00")
        fig.add_trace(go.Scatter3d(
            x=[ee["x"]], y=[ee["y"]], z=[ee["z"]], mode="markers",
            marker=dict(size=16, color=gcol, symbol="diamond", line=dict(width=2, color="#fff")),
            showlegend=False,
            hovertemplate=f"Arm {arm.arm_id} EE<br>Phase:{plb}<br>Sorted:{arm.items_sorted}<extra></extra>"))
        # gripper fingers
        sp = 28 * (1 - arm.gripper_progress)
        for dx in [-sp, sp]:
            fig.add_trace(go.Scatter3d(
                x=[ee["x"], ee["x"]+dx], y=[ee["y"], ee["y"]], z=[ee["z"], ee["z"]-35],
                mode="lines", line=dict(color=gcol, width=4),
                showlegend=False, hoverinfo="skip"))
        # base marker
        bp = ad["base_pos"]
        fig.add_trace(go.Scatter3d(
            x=[bp["x"]], y=[bp["y"]], z=[bp["z"]], mode="markers",
            marker=dict(size=14, color=col, symbol="square", line=dict(width=2, color="#fff")),
            showlegend=False,
            hovertemplate=f"Arm {arm.arm_id} Base<extra></extra>"))
        # phase label
        fig.add_trace(go.Scatter3d(
            x=[ee["x"]], y=[ee["y"]], z=[ee["z"]+65],
            mode="text", text=[plb],
            textfont=dict(color=col, size=11, family="Share Tech Mono"),
            showlegend=False, hoverinfo="skip"))

    # --- Layout ---
    stats = get_stats() or {}
    title_txt = (
        f"UR5 双臂分拣仿真 │ "
        f"已分拣: {stats.get('successful_sorts',0)} │ "
        f"FPS: {stats.get('fps','--')}"
    )
    fig.update_layout(
        title=dict(text=title_txt, font=dict(color="#00d4ff", size=14, family="Share Tech Mono"), x=0.02),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        scene=dict(
            bgcolor="rgba(8,16,32,0.95)",
            xaxis=dict(title="X (mm)", gridcolor="#1a2a3a", backgroundcolor="rgba(0,0,0,0)",
                       showbackground=True, color="#4a7a9b"),
            yaxis=dict(title="Y (mm)", gridcolor="#1a2a3a", backgroundcolor="rgba(0,0,0,0)",
                       showbackground=True, color="#4a7a9b"),
            zaxis=dict(title="Z (mm)", gridcolor="#1a2a3a", backgroundcolor="rgba(0,0,0,0)",
                       showbackground=True, color="#4a7a9b", range=[-100, 1200]),
            camera=dict(eye=dict(x=1.4, 
            y=-1.4, z=1.0)),
            aspectmode="manual",
            aspectratio=dict(x=1, y=1.5, z=0.7),
        ),
        legend=dict(
            bgcolor="rgba(0,0,0,0.4)",
            bordercolor="rgba(0,212,255,0.3)",
            borderwidth=1,
            font=dict(color="#c8d8e8", size=11),
        ),
        height=650,
        margin=dict(l=0, r=0, t=40, b=0),
    )
    return fig
# ================================================================
# Sidebar
# ================================================================
with st.sidebar:
    st.markdown('<p style="color:#00d4ff;font-size:22px;font-weight:700;letter-spacing:2px;">⚙ 控制面板</p>', unsafe_allow_html=True)
    st.markdown("**仿真参数**")
    sim_steps  = st.slider("每次运行步数", 20, 200, 60, 10)
    step_delay = st.slider("帧间延迟 (s)", 0.02, 0.2, 0.05, 0.01)
    st.divider()
    st.markdown("**显示选项**")
    show_stats = st.checkbox("实时统计",   value=True)
    show_bins  = st.checkbox("分拣箱图表", value=True)
    show_items = st.checkbox("物品列表",   value=False)
    show_perf  = st.checkbox("性能图表",   value=True)
    st.divider()
    with st.expander("使用说明"):
        st.markdown("""
**操作步骤**
1. 点击 **初始化系统**
2. 点击 **启动分拣** 运行仿真
3. 观察 UR5 双臂实时抓取
4. 查看分拣箱装载与统计

**颜色→分拣箱规则**
- 红色 → Bin 0  
- 绿色 → Bin 1  
- 蓝色 → Bin 2  
- 黄色 → Bin 3
        """)

# ================================================================
# Header
# ================================================================
st.markdown(
    '<h1 style="font-family:\'Share Tech Mono\',monospace;color:#00d4ff;'
    'letter-spacing:4px;font-size:28px;">🤖 机器人智能分拣系统</h1>',
    unsafe_allow_html=True)
st.markdown(
    '<p style="color:#4a7a9b;font-size:13px;letter-spacing:2px;">'
    'UR5 双臂 · 实时 3D 可视化 · 颜色分拣 · Streamlit</p>',
    unsafe_allow_html=True)

tab1, tab2, tab3, tab4 = st.tabs(["🤖 实时仿真", "📊 数据分析", "📈 性能监控", "📝 关于"])

# ================================================================
# Tab1: Live simulation
# ================================================================
with tab1:
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        if st.button("🚀 初始化系统", use_container_width=True):
            init_engine()
            st.success("系统已初始化")
    with c2:
        if st.button("▶ 启动分拣", use_container_width=True):
            if st.session_state.engine is None:
                init_engine()
            st.session_state.is_running = True
    with c3:
        if st.button("⏸ 停止", use_container_width=True):
            st.session_state.is_running = False
    with c4:
        if st.button("🔄 重置", use_container_width=True):
            st.session_state.engine        = None
            st.session_state.is_running    = False
            st.session_state.stats_history = []
            st.session_state.event_log     = []
            st.rerun()
    st.markdown("---")
    eng = st.session_state.engine
    if eng is None:
        st.info("请先点击 **初始化系统**")
    else:
        if st.session_state.is_running:
            ph_fig  = st.empty()
            ph_prog = st.empty()
            ph_stat = st.empty()
            for step in range(sim_steps):
                if not st.session_state.is_running:
                    break
                eng.step()
                stats = get_stats()
                if stats:
                    try:
                        fps_val = float(str(stats.get("fps", 0)).replace("s", "").strip())
                    except Exception:
                        fps_val = 0.0
                    st.session_state.stats_history.append({
                        "fps":       fps_val,
                        "processed": stats.get("total_items_processed", 0),
                        "sorted":    stats.get("successful_sorts", 0),
                        "in_env":    stats.get("items_in_environment", 0),
                    })
                fig3d = build_3d_scene()
                if fig3d:
                    ph_fig.plotly_chart(fig3d, use_container_width=True)
                ph_prog.progress((step + 1) / sim_steps)
                if stats:
                    arms_info = ""
                    for a in stats.get("arms", []):
                        arms_info += f"  Arm{a['id']}: **{a['phase']}** (sorted {a['items_sorted']})"
                    ph_stat.markdown(
                        f"⚙ Step {step+1}/{sim_steps} │ "
                        f"已分拣: **{stats.get('successful_sorts',0)}**" + arms_info)
                time.sleep(step_delay)
            st.session_state.is_running = False
            st.success("✅ 本轮仿真完成")
        else:
            fig3d = build_3d_scene()
            if fig3d:
                st.plotly_chart(fig3d, use_container_width=True)
            else:
                st.warning("无法渲染场景")
    # Real-time stats
    if show_stats and st.session_state.engine is not None:
        st.markdown("---")
        st.markdown('<p class="sec">实时统计</p>', unsafe_allow_html=True)
        stats = get_stats()
        if stats:
            mc1,mc2,mc3,mc4,mc5 = st.columns(5)
            mc1.metric("已分拣",   stats.get("successful_sorts", 0))
            mc2.metric("环境物品", stats.get("items_in_environment", 0))
            mc3.metric("FPS",      stats.get("fps", "--"))
            mc4.metric("准确率",   stats.get("accuracy_rate", "--"))
            mc5.metric("仿真时间", stats.get("simulation_time", "--"))
            arms_list = stats.get("arms", [])
            if arms_list:
                st.markdown("**机械臂状态**")
                acols = st.columns(len(arms_list))
                for i, a in enumerate(arms_list):
                    color = _ARM_COLORS[a["id"] % len(_ARM_COLORS)]
                    acols[i].markdown(
                        f'<div style="border:1px solid {color};border-radius:8px;padding:10px;">'
                        f'<b style="color:{color}">Arm {a["id"]}</b><br>'
                        f'Phase: <code>{a["phase"]}</code><br>'
                        f'Sorted: <b>{a["items_sorted"]}</b><br>'
                        f'Battery: {a["battery"]}%<br>'
                        f'Gripper: {a["gripper"]}'
                        f'</div>', unsafe_allow_html=True)

    # Bin chart
    if show_bins and st.session_state.engine is not None:
        st.markdown("---")
        st.markdown('<p class="sec">分拣箱装载</p>', unsafe_allow_html=True)
        bins_df = get_bins_df()
        if not bins_df.empty:
            bin_pal = ["#2ecc71","#e74c3c","#3498db","#f39c12"]
            fig_b = go.Figure(go.Bar(
                x=bins_df["分拣箱"],
                y=bins_df["装载率(%)"],
                marker=dict(color=[bin_pal[i%4] for i in range(len(bins_df))],
                            opacity=0.85,line=dict(color="rgba(255,255,255,0.3)",width=1)),
                text=bins_df["装载率(%)"].apply(lambda x: f"{x:.1f}%"),
                textposition="auto",
            ))
            fig_b.update_layout(
                paper_bgcolor="rgba(0,0,0,0)",plot_bgcolor="rgba(8,16,32,0.6)",
                font=dict(color="#c8d8e8"),
                xaxis=dict(gridcolor="#1a2a3a"),
                yaxis=dict(gridcolor="#1a2a3a",range=[0,105]),
                height=280,margin=dict(l=10,r=10,t=20,b=10),showlegend=False)
            st.plotly_chart(fig_b, use_container_width=True)

    # Items table
    if show_items and st.session_state.engine is not None:
        st.markdown("---")
        st.markdown('<p class="sec">当前物品</p>', unsafe_allow_html=True)
        items_df = get_items_df()
        if not items_df.empty:
            st.dataframe(items_df, use_container_width=True)
        else:
            st.info("当前无物品")

# ================================================================
# Tab2: Data analysis
# ================================================================
with tab2:
    st.markdown('<p class="sec">分拣数据分析</p>', unsafe_allow_html=True)
    if st.session_state.engine is None:
        st.info("请先初始化系统")
    else:
        stats = get_stats()
        if stats:
            dc1,dc2,dc3 = st.columns(3)
            dc1.metric("总处理",   stats.get("total_items_processed", 0))
            dc2.metric("成功分拣", stats.get("successful_sorts", 0))
            dc3.metric("失败",     stats.get("failed_sorts", 0))
        st.markdown("---")
        bins_df = get_bins_df()
        if not bins_df.empty:
            st.dataframe(bins_df, use_container_width=True)
            bin_pal=["#2ecc71","#e74c3c","#3498db","#f39c12"]
            pie_vals = [max(v, 0.001) for v in bins_df["已存物品"].tolist()]
            fig_pie = go.Figure(go.Pie(
                labels=bins_df["分拣箱"], values=pie_vals, hole=0.45,
                marker=dict(colors=bin_pal,line=dict(color="#0d1b2a",width=2)),
                textfont=dict(color="#ffffff"),
            ))
            fig_pie.update_layout(
                paper_bgcolor="rgba(0,0,0,0)",font=dict(color="#c8d8e8"),
                height=320,margin=dict(l=0,r=0,t=20,b=0),
                legend=dict(bgcolor="rgba(0,0,0,0)"),
                title=dict(text="各箱物品占比",font=dict(color="#00d4ff")),
            )
            st.plotly_chart(fig_pie, use_container_width=True)

# ================================================================
# Tab3: Performance
# ================================================================
with tab3:
    st.markdown('<p class="sec">性能监控</p>', unsafe_allow_html=True)
    hist = st.session_state.stats_history
    if show_perf and len(hist) > 1:
        df_h = pd.DataFrame(hist)
        fig_p = make_subplots(
            rows=2, cols=2,
            subplot_titles=("FPS","环境物品数","已处理物品","已分拣物品"),
        )
        x = list(range(len(df_h)))
        for col_name,color,row,col in [
            ("fps","#00d4ff",1,1),("in_env","#ff6b35",1,2),
            ("processed","#44ff88",2,1),("sorted","#ffdd44",2,2),
        ]:
            if col_name in df_h.columns:
                fig_p.add_trace(
                    go.Scatter(x=x,y=df_h[col_name],mode="lines",
                               line=dict(color=color,width=2),showlegend=False),
                    row=row,col=col)
        fig_p.update_layout(
            paper_bgcolor="rgba(0,0,0,0)",plot_bgcolor="rgba(8,16,32,0.6)",
            font=dict(color="#c8d8e8"),height=480,
            margin=dict(l=10,r=10,t=40,b=10))
        for ann in fig_p.layout.annotations:
            ann.font.color = "#7ab8d4"
        fig_p.update_xaxes(gridcolor="#1a2a3a")
        fig_p.update_yaxes(gridcolor="#1a2a3a")
        st.plotly_chart(fig_p, use_container_width=True)
    else:
        st.info("运行仿真后将显示性能图表")

# ================================================================
# Tab4: About
# ================================================================
with tab4:
    st.markdown("""
## 🤖 机器人智能分拣系统

### 项目概述
基于 UR5 六轴机械臂的物品自动分拣仿真系统，通过 Streamlit 实时展示双臂协作抓取，
Plotly 3D 渲染真实正向运动学关节轨迹。

### 系统架构
```
app.py                         ← Streamlit 前端
backend/
  core/
    simulation_engine.py       ← 仿真引擎（任务分配 + 状态机驱动）
    robot_arm.py               ← UR5 运动学 + ArmPhase 状态机
    environment.py             ← 3D 环境（物品/分拣箱/传送带）
    types.py                   ← 数据类型定义
    physics.py                 ← 物理模拟
  config/constants.py          ← 全局参数
```

### 分拣规则
| 颜色   | 目标分拣箱 |
|--------|------------|
| 红色   | Bin 0      |
| 绿色   | Bin 1      |
| 蓝色   | Bin 2      |
| 黄色   | Bin 3      |

### 技术栈
- 仿真: 自定义 UR5 解析式正/逆运动学（纯 Python）
- 前端: Streamlit + Plotly 3D
- 数据: Pandas
- 语言: Python 3.8+

### 快速开始
```bash
pip install -r requirements_streamlit.txt
streamlit run app.py
```

**版本**: 2.0.0 | **许可**: MIT
    """)

# ================================================================
# Footer
# ================================================================
st.markdown("---")
st.markdown(
    '<div style="text-align:center;color:#2a4a6a;font-size:12px;padding:10px;">'
    '🤖 Robot Sorting System · UR5 Dual-Arm · Streamlit · Plotly 3D'
    '</div>', unsafe_allow_html=True)
