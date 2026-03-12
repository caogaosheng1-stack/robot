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

st.set_page_config(
    page_title="\u673a\u5668\u4eba\u5206\u62e3\u7cfb\u7edf",
    page_icon="\U0001f916",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;700&family=Syne:wght@700;800&display=swap');
html,body,[class*="css"]{font-family:'Syne',sans-serif;}
.stApp{background:#080c14;color:#d0e4f0;}
[data-testid="stSidebar"]{background:#0b1220;border-right:1px solid #1a2a3a;}
.stTabs [data-baseweb="tab-list"]{background:#0d1928;border:1px solid #1a2a3a;border-radius:10px;padding:4px;gap:4px;}
.stTabs [data-baseweb="tab"]{color:#4a6a8a;font-family:'JetBrains Mono',monospace;font-size:12px;letter-spacing:1px;border-radius:7px;padding:6px 16px;}
.stTabs [aria-selected="true"]{color:#00e5ff!important;background:rgba(0,229,255,0.1)!important;}
div[data-testid="metric-container"]{background:linear-gradient(135deg,rgba(0,229,255,0.06),rgba(0,100,160,0.04));border:1px solid rgba(0,229,255,0.18);border-radius:12px;padding:14px 18px;}
div[data-testid="metric-container"] label{color:#4a8aaa!important;font-family:'JetBrains Mono',monospace!important;font-size:11px!important;letter-spacing:2px!important;}
div[data-testid="metric-container"] [data-testid="stMetricValue"]{color:#00e5ff!important;font-family:'JetBrains Mono',monospace!important;font-size:30px!important;}
.stButton>button{background:rgba(0,229,255,0.07);border:1px solid rgba(0,229,255,0.35);color:#00e5ff;font-family:'JetBrains Mono',monospace;font-size:12px;letter-spacing:1px;border-radius:8px;padding:8px 16px;transition:all 0.15s;}
.stButton>button:hover{background:rgba(0,229,255,0.18);border-color:#00e5ff;color:#fff;box-shadow:0 0 12px rgba(0,229,255,0.3);}
hr{border-color:rgba(0,229,255,0.1);}
.arm-card{border-radius:10px;padding:14px;background:linear-gradient(135deg,rgba(0,0,0,0.3),rgba(0,20,40,0.4));}
</style>
""", unsafe_allow_html=True)

for _k,_v in [("engine",None),("running",False),("history",[]),("total_steps",0)]:
    if _k not in st.session_state:
        st.session_state[_k] = _v

def init_engine():
    eng = SimulationEngine(enable_logging=False)
    eng.startup()
    st.session_state.engine      = eng
    st.session_state.history     = []
    st.session_state.total_steps = 0
    st.session_state.running     = False

def step_n(n):
    eng = st.session_state.engine
    if not eng: return
    for _ in range(n): eng.step()
    st.session_state.total_steps += n
    s = eng.get_statistics()
    try: fps = float(str(s.get("fps",0)).replace("s","").strip())
    except: fps = 0.0
    st.session_state.history.append({
        "fps":fps, "processed":s.get("total_items_processed",0),
        "sorted":s.get("successful_sorts",0),
        "in_env":s.get("items_in_environment",0),
        "step":st.session_state.total_steps,
    })

def get_stats():
    eng = st.session_state.engine
    return eng.get_statistics() if eng else None

def get_bins_df():
    eng = st.session_state.engine
    if not eng: return pd.DataFrame()
    rows = []
    for b in eng.environment.get_all_bins():
        fill = len(b.current_items)
        rows.append({"Bin":f"Bin {b.bin_id}",
            "\u989c\u8272":["\u7ea2","\u7eff","\u84dd","\u9ec4"][b.bin_id],
            "\u5df2\u88c5":fill, "\u5bb9\u91cf":b.capacity,
            "\u88c5\u8f7d%":round(fill/b.capacity*100,1)})
    return pd.DataFrame(rows)
_ARM_COL  = ["#00e5ff","#ff6b35"]
_BIN_COL  = ["#00e676","#ff1744","#2979ff","#ffea00"]
_ITEM_COL = {"red":"#ff4444","green":"#44ff88","blue":"#4488ff","yellow":"#ffdd44"}
_PHASE_LBL = {
    ArmPhase.IDLE:"IDLE", ArmPhase.MOVING_TO_ITEM:"FETCH",
    ArmPhase.DESCENDING:"DOWN", ArmPhase.GRIPPING:"GRIP",
    ArmPhase.LIFTING:"LIFT", ArmPhase.MOVING_TO_BIN:"CARRY",
    ArmPhase.PLACING:"PLACE", ArmPhase.RETURNING:"HOME",
}

def build_scene(key=0):
    eng = st.session_state.engine
    if not eng: return None
    fig = go.Figure()
    env = eng.environment
    conv = env.conveyor_position
    cx,cy = conv.x, conv.y

    # Ground
    R=900
    fig.add_trace(go.Mesh3d(
        x=[cx-R,cx+R,cx+R,cx-R], y=[cy-R,cy-R,cy+R,cy+R], z=[0,0,0,0],
        i=[0,0],j=[1,2],k=[2,3], color="#060d18",opacity=1,
        showlegend=False,hoverinfo="skip"))

    # Conveyor
    cw,ch,cl = 180,40,480
    fig.add_trace(go.Mesh3d(
        x=[cx-cw,cx+cw,cx+cw,cx-cw,cx-cw,cx+cw,cx+cw,cx-cw],
        y=[cy-cl,cy-cl,cy+cl,cy+cl,cy-cl,cy-cl,cy+cl,cy+cl],
        z=[0,0,0,0,ch,ch,ch,ch],
        i=[0,0,4,4,0,2], j=[1,3,5,7,4,6], k=[2,2,6,6,5,7],
        color="#1a3a5a",opacity=0.9,
        name="\u4f20\u9001\u5e26",showlegend=True,hoverinfo="name"))
    # Belt rails
    for dx in [-cw,cw]:
        fig.add_trace(go.Scatter3d(
            x=[cx+dx,cx+dx],y=[cy-cl,cy+cl],z=[ch+3,ch+3],
            mode="lines",line=dict(color="rgba(0,229,255,0.5)",width=3),
            showlegend=False,hoverinfo="skip"))
    # Belt stripes
    for dy in range(-cl,cl+1,120):
        fig.add_trace(go.Scatter3d(
            x=[cx-cw,cx+cw],y=[cy+dy,cy+dy],z=[ch+1,ch+1],
            mode="lines",line=dict(color="rgba(0,229,255,0.15)",width=1),
            showlegend=False,hoverinfo="skip"))

    # Sorting bins
    for b in env.get_all_bins():
        bx,by,bz = b.position.x,b.position.y,b.position.z
        hw,bh = 85,170
        col = _BIN_COL[b.bin_id%4]
        fr  = len(b.current_items)/max(b.capacity,1)
        label= ["\u7ea2","\u7eff","\u84dd","\u9ec4"][b.bin_id]
        # Base plate
        fig.add_trace(go.Mesh3d(
            x=[bx-hw,bx+hw,bx+hw,bx-hw], y=[by-hw,by-hw,by+hw,by+hw], z=[0,0,0,0],
            i=[0,0],j=[1,2],k=[2,3], color=col,opacity=0.15,
            showlegend=False,hoverinfo="skip"))
        # Wireframe
        C=[(bx-hw,by-hw,bz),(bx+hw,by-hw,bz),(bx+hw,by+hw,bz),(bx-hw,by+hw,bz),
           (bx-hw,by-hw,bz+bh),(bx+hw,by-hw,bz+bh),(bx+hw,by+hw,bz+bh),(bx-hw,by+hw,bz+bh)]
        for si,ei in [(0,1),(1,2),(2,3),(3,0),(4,5),(5,6),(6,7),(7,4),(0,4),(1,5),(2,6),(3,7)]:
            fig.add_trace(go.Scatter3d(
                x=[C[si][0],C[ei][0]],y=[C[si][1],C[ei][1]],z=[C[si][2],C[ei][2]],
                mode="lines",line=dict(color=col,width=2),
                showlegend=False,hoverinfo="skip"))
        # Fill
        if fr>0:
            fh=max(fr*(bh-8),6)
            fig.add_trace(go.Mesh3d(
                x=[bx-hw+5,bx+hw-5,bx+hw-5,bx-hw+5,bx-hw+5,bx+hw-5,bx+hw-5,bx-hw+5],
                y=[by-hw+5,by-hw+5,by+hw-5,by+hw-5,by-hw+5,by-hw+5,by+hw-5,by+hw-5],
                z=[bz+4,bz+4,bz+4,bz+4,bz+4+fh,bz+4+fh,bz+4+fh,bz+4+fh],
                i=[0,0,0,1,4,4],j=[1,2,3,2,5,6],k=[2,3,1,3,6,7],
                color=col,opacity=0.5,showlegend=False,hoverinfo="skip"))
        # Label
        fig.add_trace(go.Scatter3d(
            x=[bx],y=[by],z=[bz+bh+40],mode="text",
            text=[f"<b>BIN{b.bin_id}</b> {label} {len(b.current_items)}\u4ef6"],
            textfont=dict(color=col,size=12,family="JetBrains Mono"),
            showlegend=False,hoverinfo="skip"))

    # Items
    items = env.get_all_items()
    if items:
        ix,iy,iz,ic,itxt=[],[],[],[],[]
        for it in items:
            ix.append(it.position.x); iy.append(it.position.y)
            iz.append(it.position.z+ch+5)
            ic.append(_ITEM_COL.get(it.color.value,"#aaa"))
            itxt.append(f"{it.color.value.upper()} #{it.id}")
        fig.add_trace(go.Scatter3d(
            x=ix,y=iy,z=iz,mode="markers",
            marker=dict(size=12,color=ic,opacity=1,
                symbol="square",line=dict(width=1,color="rgba(255,255,255,0.6)")),
            name="\u7269\u54c1",text=itxt,
            hovertemplate="%{text}<extra></extra>"))

    # Arms
    for arm in eng.get_arms():
        ad  = arm.to_dict()
        pts = ad["joint_positions"]
        col = _ARM_COL[arm.arm_id%2]
        plb = _PHASE_LBL.get(arm.phase,"?")
        has = ad["has_item"]
        xs=[p["x"] for p in pts]; ys=[p["y"] for p in pts]; zs=[p["z"] for p in pts]
        # Shadow line on ground
        fig.add_trace(go.Scatter3d(
            x=xs,y=ys,z=[2]*len(xs),mode="lines",
            line=dict(color=f"rgba({int(col[1:3],16)},{int(col[3:5],16)},{int(col[5:7],16)},0.15)",width=4),
            showlegend=False,hoverinfo="skip"))
        # Links
        fig.add_trace(go.Scatter3d(
            x=xs,y=ys,z=zs,mode="lines",
            line=dict(color=col,width=8),
            name=f"Arm {arm.arm_id}",showlegend=True,hoverinfo="skip"))
        # Joints
        fig.add_trace(go.Scatter3d(
            x=xs,y=ys,z=zs,mode="markers",
            marker=dict(size=[7,9,9,9,9,9,11],color="#0b1a2a",
                        line=dict(width=2,color=col)),
            showlegend=False,
            hovertemplate=f"Arm {arm.arm_id}<br>{plb}<br>Battery:{ad['battery']}%<extra></extra>"))
        # EE
        ee=ad["end_effector"]
        gcol=("#ff1744" if has else ("#00e676" if arm.gripper==GripperState.OPEN else "#ffea00"))
        fig.add_trace(go.Scatter3d(
            x=[ee["x"]],y=[ee["y"]],z=[ee["z"]],mode="markers",
            marker=dict(size=18,color=gcol,symbol="diamond",
                        line=dict(width=2,color="#fff")),
            showlegend=False,
            hovertemplate=f"Arm {arm.arm_id} EE<br>{plb}<br>Sorted:{arm.items_sorted}<extra></extra>"))
        # Gripper fingers
        sp=30*(1-arm.gripper_progress)
        for dx in [-sp,sp]:
            fig.add_trace(go.Scatter3d(
                x=[ee["x"],ee["x"]+dx],y=[ee["y"],ee["y"]],z=[ee["z"],ee["z"]-40],
                mode="lines",line=dict(color=gcol,width=5),
                showlegend=False,hoverinfo="skip"))
        # Base
        bp=ad["base_pos"]
        fig.add_trace(go.Scatter3d(
            x=[bp["x"]],y=[bp["y"]],z=[bp["z"]],mode="markers",
            marker=dict(size=16,color=col,symbol="square",line=dict(width=2,color="#fff")),
            showlegend=False,
            hovertemplate=f"Arm {arm.arm_id} Base<extra></extra>"))
        # Phase label above EE
        pcol = {"IDLE":"#4a6a8a","FETCH":"#00e5ff","DOWN":"#ffea00",
                "GRIP":"#ff6b35","LIFT":"#ff6b35","CARRY":"#00e676",
                "PLACE":"#00e676","HOME":"#4a6a8a"}.get(plb,col)
        fig.add_trace(go.Scatter3d(
            x=[ee["x"]],y=[ee["y"]],z=[ee["z"]+80],mode="text",
            text=[plb],textfont=dict(color=pcol,size=12,family="JetBrains Mono"),
            showlegend=False,hoverinfo="skip"))

    # Layout — tight camera on work area
    stats = get_stats() or {}
    sorted_n = stats.get("successful_sorts",0)
    fps_s    = stats.get("fps","--")
    fig.update_layout(
        title=dict(
            text=f"\u2022 \u5df2\u5206\u62e3: {sorted_n} \u2022 FPS: {fps_s} \u2022 STEP: {st.session_state.total_steps}",
            font=dict(color="#00e5ff",size=13,family="JetBrains Mono"),x=0.02),
        paper_bgcolor="rgba(0,0,0,0)",
        scene=dict(
            bgcolor="#060d18",
            xaxis=dict(range=[cx-950,cx+950],showgrid=True,gridcolor="#0f2030",
                       backgroundcolor="#060d18",showbackground=True,
                       color="#2a4a6a",title=""),
            yaxis=dict(range=[cy-950,cy+950],showgrid=True,gridcolor="#0f2030",
                       backgroundcolor="#060d18",showbackground=True,
                       color="#2a4a6a",title=""),
            zaxis=dict(range=[0,950],showgrid=True,gridcolor="#0f2030",
                       backgroundcolor="#060d18",showbackground=True,
                       color="#2a4a6a",title=""),
            camera=dict(eye=dict(x=1.5,y=-1.5,z=1.1),
                        center=dict(x=0,y=0,z=-0.1)),
            aspectmode="cube",
        ),
        legend=dict(bgcolor="rgba(6,13,24,0.8)",bordercolor="#1a2a3a",
                    borderwidth=1,font=dict(color="#7aaccc",size=11,
                    family="JetBrains Mono")),
        height=620,
        margin=dict(l=0,r=0,t=36,b=0),
        uirevision=f"scene",
    )
    return fig
# ================================================================
# Sidebar
# ================================================================
with st.sidebar:
    st.markdown('<div style="font-family:\'JetBrains Mono\',monospace;color:#00e5ff;font-size:18px;font-weight:700;letter-spacing:3px;padding:12px 0 8px;border-bottom:1px solid #1a2a3a;margin-bottom:16px;">\u2699 CONTROL</div>', unsafe_allow_html=True)
    steps_per_run = st.slider("每次步进数", 50, 500, 150, 50)
    auto_runs     = st.slider("连续运行次数", 1, 20, 5)
    frame_delay   = st.slider("渲染延迟(s)", 0.0, 0.3, 0.05, 0.05)
    st.divider()
    show_stats = st.checkbox("实时统计",   value=True)
    show_bins  = st.checkbox("分拣箱图表", value=True)
    show_items = st.checkbox("物品列表",   value=False)
    show_perf  = st.checkbox("性能图表",   value=True)
    st.divider()
    with st.expander("使用说明"):
        st.markdown("""
**步骤**
1. 点击 **INIT** 初始化
2. 点击 **RUN** 启动分拣
3. 每次运行自动执行多步
4. 可多次点击 RUN 继续

**颜色规则**
- 红色 → Bin 0
- 绿色 → Bin 1
- 蓝色 → Bin 2
- 黄色 → Bin 3
""")

# ================================================================
# Header
# ================================================================
st.markdown("""
<div style="display:flex;align-items:baseline;gap:16px;margin-bottom:4px;">
<h1 style="font-family:'Syne',sans-serif;color:#00e5ff;font-size:32px;letter-spacing:3px;margin:0;">\U0001f916 机器人分拣系统</h1>
<span style="font-family:'JetBrains Mono',monospace;color:#2a5a7a;font-size:11px;letter-spacing:2px;">UR5 DUAL-ARM v2</span>
</div>
<p style="color:#2a5a7a;font-size:12px;font-family:'JetBrains Mono',monospace;letter-spacing:1px;margin-bottom:16px;">REAL-TIME 3D · UR5 KINEMATICS · COLOR SORTING</p>
""", unsafe_allow_html=True)

tab1,tab2,tab3,tab4 = st.tabs(["🤖  LIVE SIM","📊  ANALYTICS","📈  PERFORMANCE","📋  ABOUT"])

# ================================================================
# TAB 1
# ================================================================
with tab1:
    b1,b2,b3,b4 = st.columns(4)
    with b1:
        init_btn  = st.button("▶ INIT",   use_container_width=True)
    with b2:
        run_btn   = st.button("▶ RUN",    use_container_width=True)
    with b3:
        step_btn  = st.button("▶ STEP",   use_container_width=True)
    with b4:
        reset_btn = st.button("↺ RESET",  use_container_width=True)

    if init_btn:
        init_engine()
        st.toast("System initialized", icon="\U0001f916")
    if reset_btn:
        st.session_state.engine      = None
        st.session_state.running     = False
        st.session_state.history     = []
        st.session_state.total_steps = 0
        st.rerun()
    if step_btn and st.session_state.engine:
        step_n(steps_per_run)

    st.markdown("---")
    eng = st.session_state.engine

    if eng is None:
        st.markdown('<div style="text-align:center;padding:60px;color:#2a5a7a;font-family:\'JetBrains Mono\',monospace;font-size:14px;border:1px dashed #1a2a3a;border-radius:12px;">点击 <b style="color:#00e5ff">INIT</b> 初始化仿真系统</div>', unsafe_allow_html=True)
    else:
        if run_btn:
            ph  = st.empty()
            bar = st.progress(0)
            txt = st.empty()
            for run_i in range(auto_runs):
                step_n(steps_per_run)
                s = get_stats()
                fig3d = build_scene()
                if fig3d:
                    ph.plotly_chart(fig3d, use_container_width=True,
                                    key=f"live_{st.session_state.total_steps}")
                bar.progress((run_i+1)/auto_runs)
                if s:
                    phases = [a["phase"] for a in s.get("arms",[])]
                    sorts  = [a["items_sorted"] for a in s.get("arms",[])]
                    txt.markdown(f"`{run_i+1}/{auto_runs}` Step **{st.session_state.total_steps}** │ 已分拣 **{s.get('successful_sorts',0)}** │ {phases} sorted{sorts}")
                time.sleep(frame_delay)
            st.success(f"完成 — 共分拣 {get_stats().get('successful_sorts',0)} 件")
        else:
            fig3d = build_scene()
            if fig3d:
                st.plotly_chart(fig3d, use_container_width=True,
                                key=f"static_{st.session_state.total_steps}")

    if show_stats and st.session_state.engine:
        st.markdown("---")
        s = get_stats()
        if s:
            c1,c2,c3,c4,c5 = st.columns(5)
            c1.metric("已分拣",   s.get("successful_sorts",0))
            c2.metric("环境物品", s.get("items_in_environment",0))
            c3.metric("FPS",      s.get("fps","--"))
            c4.metric("准确率",   s.get("accuracy_rate","--"))
            c5.metric("仿真时间", s.get("simulation_time","--"))
            arms = s.get("arms",[])
            if arms:
                acols = st.columns(len(arms))
                ph_map = {"idle":"#4a6a8a","moving_to_item":"#00e5ff",
                          "descending":"#ffea00","gripping":"#ff6b35",
                          "lifting":"#ff6b35","moving_to_bin":"#00e676",
                          "placing":"#00e676","returning":"#4a6a8a"}
                for i,a in enumerate(arms):
                    col  = _ARM_COL[a["id"]%2]
                    pcol = ph_map.get(a["phase"],"#aaa")
                    acols[i].markdown(
                        f'<div class="arm-card" style="border:1px solid {col};">'
                        f'<span style="color:{col};font-family:\'JetBrains Mono\',monospace;font-size:11px;">ARM {a["id"]}</span><br>'
                        f'<span style="color:{pcol};font-size:20px;font-weight:700;">{a["phase"].upper()}</span><br>'
                        f'<small style="color:#4a6a8a;">Sorted <b style="color:#fff">{a["items_sorted"]}</b>'
                        f' · Battery <b style="color:{col}">{a["battery"]}%</b></small></div>',
                        unsafe_allow_html=True)

    if show_bins and st.session_state.engine:
        st.markdown("---")
        bins_df = get_bins_df()
        if not bins_df.empty:
            fig_b = go.Figure(go.Bar(
                x=bins_df["Bin"], y=bins_df["装载%"],
                marker=dict(color=_BIN_COL[:len(bins_df)],opacity=0.85,
                            line=dict(color="rgba(255,255,255,0.2)",width=1)),
                text=bins_df["装载%"].apply(lambda x:f"{x:.0f}%"),
                textposition="auto",textfont=dict(color="#fff",family="JetBrains Mono"),
            ))
            fig_b.update_layout(
                paper_bgcolor="rgba(0,0,0,0)",plot_bgcolor="#0a141e",
                font=dict(color="#7aaccc",family="JetBrains Mono"),
                xaxis=dict(gridcolor="#0f2030"),
                yaxis=dict(gridcolor="#0f2030",range=[0,105]),
                height=260,margin=dict(l=10,r=10,t=10,b=10),showlegend=False)
            st.plotly_chart(fig_b, use_container_width=True, key="bins_bar")

    if show_items and st.session_state.engine:
        items_df = get_bins_df()
        if not items_df.empty:
            st.dataframe(items_df, use_container_width=True)
# ================================================================
# TAB 2 — Analytics
# ================================================================
with tab2:
    if not st.session_state.engine:
        st.info("请先初始化系统")
    else:
        s = get_stats()
        if s:
            c1,c2,c3 = st.columns(3)
            c1.metric("总处理",   s.get("total_items_processed",0))
            c2.metric("成功分拣", s.get("successful_sorts",0))
            c3.metric("失败",     s.get("failed_sorts",0))
        bins_df = get_bins_df()
        if not bins_df.empty:
            st.dataframe(bins_df, use_container_width=True)
            pie_vals = [max(v,0.001) for v in bins_df["已装"].tolist()]
            fig_pie = go.Figure(go.Pie(
                labels=bins_df["Bin"], values=pie_vals, hole=0.5,
                marker=dict(colors=_BIN_COL[:4],line=dict(color="#080c14",width=3)),
                textfont=dict(color="#fff",family="JetBrains Mono"),
            ))
            fig_pie.update_layout(
                paper_bgcolor="rgba(0,0,0,0)",
                font=dict(color="#7aaccc",family="JetBrains Mono"),
                height=300,margin=dict(l=0,r=0,t=10,b=0),
                legend=dict(bgcolor="rgba(0,0,0,0)",font=dict(color="#7aaccc")),
                title=dict(text="各箱物品占比",font=dict(color="#00e5ff")),
            )
            st.plotly_chart(fig_pie, use_container_width=True, key="pie")

# ================================================================
# TAB 3 — Performance
# ================================================================
with tab3:
    hist = st.session_state.history
    if show_perf and len(hist) > 1:
        df_h = pd.DataFrame(hist)
        fig_p = make_subplots(rows=2,cols=2,
            subplot_titles=("FPS","环境物品","已处理","已分拣"))
        x = df_h["step"].tolist()
        for col_n,color,row,col in [
            ("fps","#00e5ff",1,1),("in_env","#ff6b35",1,2),
            ("processed","#00e676",2,1),("sorted","#ffea00",2,2),
        ]:
            if col_n in df_h.columns:
                fig_p.add_trace(go.Scatter(
                    x=x,y=df_h[col_n],mode="lines",
                    line=dict(color=color,width=2),showlegend=False),
                    row=row,col=col)
        fig_p.update_layout(
            paper_bgcolor="rgba(0,0,0,0)",plot_bgcolor="#0a141e",
            font=dict(color="#7aaccc",family="JetBrains Mono"),
            height=460,margin=dict(l=10,r=10,t=40,b=10))
        for ann in fig_p.layout.annotations:
            ann.font.update(color="#4a8aaa",family="JetBrains Mono",size=11)
        fig_p.update_xaxes(gridcolor="#0f2030")
        fig_p.update_yaxes(gridcolor="#0f2030")
        st.plotly_chart(fig_p, use_container_width=True, key="perf")
    else:
        st.info("运行仿真后将显示性能图表")

# ================================================================
# TAB 4 — About
# ================================================================
with tab4:
    st.markdown("""
## 🤖 机器人智能分拣系统 v2

### 核心修复
- **机械臂状态机** 改用仿真 dt 驱动（原用 `time.time()` 导致永远卡住）
- **物品生成** 直接在工作区生成（原从 Y=200 推进会在抓取前消失）
- **布局重设** 分拣箱置于机械臂臂展范围内（≤850mm）
- **3D 视角** 聚焦工作区，地面 + 阴影增强空间感

### 架构
```
app.py
backend/core/
  simulation_engine.py  ← 任务分配 + 状态机驱动
  robot_arm.py          ← UR5 FK/IK + ArmPhase
  environment.py        ← 环境建模
```

### 分拣规则
| 颜色 | Bin |
|------|-----|
| 红   | 0   |
| 绿   | 1   |
| 蓝   | 2   |
| 黄   | 3   |

### 部署
```bash
pip install -r requirements_streamlit.txt
streamlit run app.py
```
**版本**: 2.1 | **许可**: MIT
    """)

# Footer
st.markdown("---")
st.markdown(
    '<div style="text-align:center;color:#1a3a5a;font-size:11px;'
    'font-family:\'JetBrains Mono\',monospace;padding:8px;">'
    'UR5 DUAL-ARM SORTING SYSTEM · STREAMLIT · PLOTLY 3D'
    '</div>', unsafe_allow_html=True)
