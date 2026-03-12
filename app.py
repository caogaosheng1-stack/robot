#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Franka Panda 双臂分拣系统 - Streamlit 可视化"""
import streamlit as st
import sys, os, time
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

ROOT = os.path.dirname(os.path.abspath(__file__))
if os.path.join(ROOT,'backend') not in sys.path:
    sys.path.insert(0, os.path.join(ROOT,'backend'))

from backend.core.simulation_engine import SimulationEngine
from backend.core.robot_arm import ArmPhase, GripperState

st.set_page_config(
    page_title="Franka Panda 分拣系统",
    page_icon="\U0001f9be",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Mono:wght@400;500&family=DM+Sans:wght@400;600;700&display=swap');
html,body,[class*="css"]{font-family:'DM Sans',sans-serif;}
.stApp{background:#07090f;color:#ccd6f6;}
[data-testid="stSidebar"]{background:#0b0e18;border-right:1px solid rgba(100,255,218,0.1);}
.stTabs [data-baseweb="tab-list"]{background:rgba(255,255,255,0.03);border:1px solid rgba(100,255,218,0.12);border-radius:12px;padding:4px;}
.stTabs [data-baseweb="tab"]{color:#495670;font-family:'DM Mono',monospace;font-size:11px;letter-spacing:1.5px;text-transform:uppercase;border-radius:8px;padding:7px 18px;}
.stTabs [aria-selected="true"]{color:#64ffda!important;background:rgba(100,255,218,0.08)!important;}
div[data-testid="metric-container"]{background:linear-gradient(135deg,rgba(100,255,218,0.05),rgba(0,0,0,0));border:1px solid rgba(100,255,218,0.15);border-radius:14px;padding:16px 20px;}
div[data-testid="metric-container"] label{color:#495670!important;font-family:'DM Mono',monospace!important;font-size:10px!important;letter-spacing:2px!important;text-transform:uppercase!important;}
div[data-testid="metric-container"] [data-testid="stMetricValue"]{color:#64ffda!important;font-family:'DM Mono',monospace!important;font-size:32px!important;}
.stButton>button{background:rgba(100,255,218,0.06);border:1px solid rgba(100,255,218,0.3);color:#64ffda;font-family:'DM Mono',monospace;font-size:11px;text-transform:uppercase;letter-spacing:1.5px;border-radius:10px;padding:9px 18px;transition:all 0.2s;}
.stButton>button:hover{background:rgba(100,255,218,0.15);border-color:#64ffda;color:#fff;box-shadow:0 0 20px rgba(100,255,218,0.2);}
.stButton>button[kind="primary"]{background:rgba(100,255,218,0.15);border-color:#64ffda;}
hr{border-color:rgba(100,255,218,0.08);}
.phase-badge{display:inline-block;font-family:'DM Mono',monospace;font-size:10px;font-weight:500;letter-spacing:2px;text-transform:uppercase;padding:3px 10px;border-radius:20px;}
</style>
""", unsafe_allow_html=True)

for _k,_v in [("engine",None),("history",[]),("steps",0)]:
    if _k not in st.session_state:
        st.session_state[_k] = _v

# ================================================================
# Engine helpers
# ================================================================
def init_engine():
    eng = SimulationEngine(enable_logging=False)
    eng.startup()
    st.session_state.engine  = eng
    st.session_state.history = []
    st.session_state.steps   = 0

def run_steps(n):
    eng = st.session_state.engine
    if not eng: return
    for _ in range(n): eng.step()
    st.session_state.steps += n
    s = eng.get_statistics()
    try: fps = float(str(s.get('fps',0)).replace('s','').strip())
    except: fps = 0.0
    st.session_state.history.append({
        'fps':fps,'processed':s.get('total_items_processed',0),
        'sorted':s.get('successful_sorts',0),
        'in_env':s.get('items_in_environment',0),
        'step':st.session_state.steps,
    })

def stats(): return st.session_state.engine.get_statistics() if st.session_state.engine else None

def bins_df():
    eng = st.session_state.engine
    if not eng: return pd.DataFrame()
    rows=[]
    for b in eng.environment.get_all_bins():
        f=len(b.current_items)
        rows.append({'Bin':f'Bin {b.bin_id}',
            '\u989c\u8272':['\u7ea2','\u7eff','\u84dd','\u9ec4'][b.bin_id],
            '\u5df2\u88c5':f,'\u5bb9\u91cf':b.capacity,
            '\u88c5\u8f7d%':round(f/b.capacity*100,1)})
    return pd.DataFrame(rows)
# ================================================================
# 常量
# ================================================================
_ARM_COL  = ["#64ffda", "#ff6b6b"]
_BIN_COL  = ["#00e676", "#ff1744", "#448aff", "#ffd740"]
_ITEM_COL = {"red":"#ff5252","green":"#69f0ae","blue":"#40c4ff","yellow":"#ffd740"}
_ITEM_SHAPE = {"small":"circle","medium":"square","large":"diamond"}
_PHASE_COL = {
    "idle":"#495670","moving_to_item":"#64ffda",
    "descending":"#ffd740","gripping":"#ff6b6b",
    "lifting":"#ff6b6b","moving_to_bin":"#69f0ae",
    "placing":"#69f0ae","returning":"#495670",
}
_PHASE_LBL = {
    ArmPhase.IDLE:"IDLE", ArmPhase.MOVING_TO_ITEM:"FETCH",
    ArmPhase.DESCENDING:"DOWN", ArmPhase.GRIPPING:"GRIP",
    ArmPhase.LIFTING:"LIFT", ArmPhase.MOVING_TO_BIN:"CARRY",
    ArmPhase.PLACING:"DROP", ArmPhase.RETURNING:"HOME",
}

# ================================================================
# 3D 场景构建  —  优化：最少 trace 数
# ================================================================
def _tube(x0,y0,z0,x1,y1,z1,r,col,n=8):
    """用 Mesh3d 画一段圆柱连杆，减少 Scatter3d 数量"""
    import math
    dx,dy,dz = x1-x0,y1-y0,z1-z0
    L = math.sqrt(dx*dx+dy*dy+dz*dz)
    if L<1: return None
    # 局部坐标系
    ax,ay,az = dx/L,dy/L,dz/L
    # 找一个垂直向量
    if abs(ax)<0.9: px,py,pz=1,0,0
    else:           px,py,pz=0,1,0
    # 叉积
    bx=ay*pz-az*py; by=az*px-ax*pz; bz=ax*py-ay*px
    bl=math.sqrt(bx*bx+by*by+bz*bz)
    bx/=bl;by/=bl;bz/=bl
    cx=ay*bz-az*by;cy=az*bx-ax*bz;cz=ax*by-ay*bx
    xs,ys,zs=[],[],[]
    for side in [0,1]:
        ox,oy,oz=(x0,y0,z0) if side==0 else (x1,y1,z1)
        for k in range(n):
            a=2*math.pi*k/n
            xs.append(ox+r*(math.cos(a)*bx+math.sin(a)*cx))
            ys.append(oy+r*(math.cos(a)*by+math.sin(a)*cy))
            zs.append(oz+r*(math.cos(a)*bz+math.sin(a)*cz))
    ii,jj,kk=[],[],[]
    for k in range(n):
        nk=(k+1)%n
        ii+=[k,k,n+k,n+k]
        jj+=[nk,n+k,n+nk,nk]
        kk+=[n+k,n+nk,nk,k]
    return go.Mesh3d(x=xs,y=ys,z=zs,i=ii,j=jj,k=kk,
                    color=col,opacity=1.0,flatshading=False,
                    lighting=dict(ambient=0.5,diffuse=0.8,specular=0.3,roughness=0.4),
                    lightposition=dict(x=500,y=500,z=800),
                    showlegend=False,hoverinfo="skip")

def _sphere(cx,cy,cz,r,col,n=10):
    """球形关节 Mesh3d"""
    import math
    xs,ys,zs=[],[],[]
    for i in range(n+1):
        lat=math.pi*(-0.5+i/n)
        for j in range(n+1):
            lon=2*math.pi*j/n
            xs.append(cx+r*math.cos(lat)*math.cos(lon))
            ys.append(cy+r*math.cos(lat)*math.sin(lon))
            zs.append(cz+r*math.sin(lat))
    ii,jj,kk=[],[],[]
    for i in range(n):
        for j in range(n):
            p=i*(n+1)+j
            ii+=[p,p+1]
            jj+=[p+1,p+n+2]
            kk+=[p+n+2,p+n+1]
    return go.Mesh3d(x=xs,y=ys,z=zs,i=ii,j=jj,k=kk,
                    color=col,opacity=1.0,flatshading=False,
                    lighting=dict(ambient=0.5,diffuse=0.8,specular=0.5,roughness=0.3),
                    showlegend=False,hoverinfo="skip")

def build_scene():
    eng = st.session_state.engine
    if not eng: return None
    fig = go.Figure()
    env = eng.environment
    conv = env.conveyor_position
    cx,cy = conv.x, conv.y

    # ---- 地面网格 (单个 Mesh3d) ----
    R=920
    gx=[cx-R,cx+R,cx+R,cx-R]; gy=[cy-R,cy-R,cy+R,cy+R]; gz=[0,0,0,0]
    fig.add_trace(go.Mesh3d(x=gx,y=gy,z=gz,i=[0,0],j=[1,2],k=[2,3],
        color="#0d1117",opacity=1,showlegend=False,hoverinfo="skip"))
    # 地面网格线 (合并为单 trace)
    gxl,gyl,gzl=[],[],[]
    step=200
    for v in range(-R,R+1,step):
        gxl+=[cx+v,cx+v,None,cx-R,cx+R,None]
        gyl+=[cy-R,cy+R,None,cy+v,cy+v,None]
        gzl+=[1,1,None,1,1,None]
    fig.add_trace(go.Scatter3d(x=gxl,y=gyl,z=gzl,mode='lines',
        line=dict(color='rgba(100,255,218,0.04)',width=1),
        showlegend=False,hoverinfo='skip'))

    # ---- 传送带 (Mesh3d 主体 + 2条导轨) ----
    cw,ch,cl=180,45,500
    fig.add_trace(go.Mesh3d(
        x=[cx-cw,cx+cw,cx+cw,cx-cw,cx-cw,cx+cw,cx+cw,cx-cw],
        y=[cy-cl,cy-cl,cy+cl,cy+cl,cy-cl,cy-cl,cy+cl,cy+cl],
        z=[0,0,0,0,ch,ch,ch,ch],
        i=[0,0,4,1,5,2],j=[1,3,5,5,6,6],k=[5,2,1,6,2,7],
        color="#1a2744",opacity=1,
        lighting=dict(ambient=0.6,diffuse=0.6),
        name="传送带",showlegend=True,hoverinfo="name"))
    # 传送带导轨 (合并)
    rx,ry,rz=[],[],[]
    for dx2 in [-cw,cw]:
        rx+=[cx+dx2,cx+dx2,None]
        ry+=[cy-cl,cy+cl,None]
        rz+=[ch+4,ch+4,None]
    fig.add_trace(go.Scatter3d(x=rx,y=ry,z=rz,mode='lines',
        line=dict(color='rgba(100,255,218,0.6)',width=4),
        showlegend=False,hoverinfo='skip'))
    # 传送带条纹 (合并)
    sx,sy,sz=[],[],[]
    for dy2 in range(-cl,cl+1,100):
        sx+=[cx-cw,cx+cw,None]; sy+=[cy+dy2,cy+dy2,None]; sz+=[ch+2,ch+2,None]
    fig.add_trace(go.Scatter3d(x=sx,y=sy,z=sz,mode='lines',
        line=dict(color='rgba(100,255,218,0.12)',width=1),
        showlegend=False,hoverinfo='skip'))

    # ---- 分拣箱 (每个箱 2 个 trace: 底板+线框合并) ----
    for b in env.get_all_bins():
        bx,by,bz=b.position.x,b.position.y,b.position.z
        hw,bh=90,180
        col=_BIN_COL[b.bin_id%4]
        fr=len(b.current_items)/max(b.capacity,1)
        lbl=['RED','GRN','BLU','YEL'][b.bin_id]
        # 底板
        fig.add_trace(go.Mesh3d(
            x=[bx-hw,bx+hw,bx+hw,bx-hw],y=[by-hw,by-hw,by+hw,by+hw],z=[0,0,0,0],
            i=[0,0],j=[1,2],k=[2,3],color=col,opacity=0.12,
            showlegend=False,hoverinfo='skip'))
        # 12条边合并为单 trace
        C=[(bx-hw,by-hw,bz),(bx+hw,by-hw,bz),(bx+hw,by+hw,bz),(bx-hw,by+hw,bz),
           (bx-hw,by-hw,bz+bh),(bx+hw,by-hw,bz+bh),(bx+hw,by+hw,bz+bh),(bx-hw,by+hw,bz+bh)]
        ex,ey,ez=[],[],[]
        for si,ei in [(0,1),(1,2),(2,3),(3,0),(4,5),(5,6),(6,7),(7,4),(0,4),(1,5),(2,6),(3,7)]:
            ex+=[C[si][0],C[ei][0],None]; ey+=[C[si][1],C[ei][1],None]; ez+=[C[si][2],C[ei][2],None]
        fig.add_trace(go.Scatter3d(x=ex,y=ey,z=ez,mode='lines',
            line=dict(color=col,width=2),showlegend=False,hoverinfo='skip'))
        # 填充块
        if fr>0.01:
            fh=max(fr*(bh-8),5)
            fig.add_trace(go.Mesh3d(
                x=[bx-hw+6,bx+hw-6,bx+hw-6,bx-hw+6,bx-hw+6,bx+hw-6,bx+hw-6,bx-hw+6],
                y=[by-hw+6,by-hw+6,by+hw-6,by+hw-6,by-hw+6,by-hw+6,by+hw-6,by+hw-6],
                z=[bz+4,bz+4,bz+4,bz+4,bz+4+fh,bz+4+fh,bz+4+fh,bz+4+fh],
                i=[0,0,0,1,4,4],j=[1,2,3,2,5,6],k=[2,3,1,3,6,7],
                color=col,opacity=0.45,showlegend=False,hoverinfo='skip'))
        # 标签
        fig.add_trace(go.Scatter3d(
            x=[bx],y=[by],z=[bz+bh+50],mode='text',
            text=[f'<b>{lbl}</b> {len(b.current_items)}\u4ef6'],
            textfont=dict(color=col,size=13,family='DM Mono'),
            showlegend=False,hoverinfo='skip'))
    # ---- 物品 (合并为单 trace，按颜色分组) ----
    items = env.get_all_items()
    if items:
        by_col = {}
        for it in items:
            c = it.color.value
            if c not in by_col: by_col[c]=[]
            by_col[c].append(it)
        for c,its in by_col.items():
            col=_ITEM_COL.get(c,'#aaa')
            shp=_ITEM_SHAPE.get(its[0].size.value if hasattr(its[0],'size') else 'medium','square')
            fig.add_trace(go.Scatter3d(
                x=[i.position.x for i in its],
                y=[i.position.y for i in its],
                z=[i.position.z+ch+8 for i in its],
                mode='markers',
                marker=dict(size=14,color=col,symbol=shp,opacity=1,
                    line=dict(width=1.5,color='rgba(255,255,255,0.5)')),
                name=c.upper(),
                text=[f'{c.upper()} #{i.id}' for i in its],
                hovertemplate='%{text}<extra></extra>'))

    # ---- Franka Panda 机械臂 (立体圆柱管体) ----
    for arm in eng.get_arms():
        ad  = arm.to_dict()
        pts = ad['joint_positions']
        col = _ARM_COL[arm.arm_id % 2]
        plb = _PHASE_LBL.get(arm.phase, '?')
        pcol= _PHASE_COL.get(arm.phase.value, col)
        has = ad['has_item']

        # 关节世界坐标
        jx=[p['x'] for p in pts]; jy=[p['y'] for p in pts]; jz=[p['z'] for p in pts]

        # 底座板
        bp=ad['base_pos']
        fig.add_trace(go.Mesh3d(
            x=[bp['x']-70,bp['x']+70,bp['x']+70,bp['x']-70],
            y=[bp['y']-70,bp['y']-70,bp['y']+70,bp['y']+70],
            z=[2,2,2,2],i=[0,0],j=[1,2],k=[2,3],
            color=col,opacity=0.25,showlegend=False,hoverinfo='skip'))

        # 连杆：圆柱 Mesh3d (半径随关节序号变化)
        radii=[28,22,20,18,14,12,10]
        for k in range(min(len(jx)-1, len(radii))):
            r=radii[k]
            t=_tube(jx[k],jy[k],jz[k],jx[k+1],jy[k+1],jz[k+1],r,col)
            if t: fig.add_trace(t)

        # 关节球 (仅画前6个主关节)
        for k in range(min(len(jx),7)):
            sr=radii[k]+4 if k<len(radii) else 12
            s=_sphere(jx[k],jy[k],jz[k],sr,'#1e2d40')
            if s: fig.add_trace(s)
            # 关节亮圈
            fig.add_trace(go.Scatter3d(
                x=[jx[k]],y=[jy[k]],z=[jz[k]],mode='markers',
                marker=dict(size=sr//3+2,color=col,opacity=0.9,
                    line=dict(width=1,color='#fff')),
                showlegend=False,hoverinfo='skip'))

        # 末端执行器
        ee=ad['end_effector']
        gcol='#ff1744' if has else ('#64ffda' if arm.gripper==GripperState.OPEN else '#ffd740')
        fig.add_trace(go.Scatter3d(
            x=[ee['x']],y=[ee['y']],z=[ee['z']],mode='markers',
            marker=dict(size=20,color=gcol,symbol='diamond',
                line=dict(width=2,color='#fff')),
            name=f'Panda {arm.arm_id}',showlegend=True,
            hovertemplate=f'Panda {arm.arm_id}<br>{plb}<br>Sorted:{arm.items_sorted}<extra></extra>'))

        # 夹爪手指 (2根)
        sp=35*(1-arm.gripper_progress)
        fx,fy,fz=[],[],[]
        for dx2 in [-sp,sp]:
            fx+=[ee['x'],ee['x']+dx2,None]
            fy+=[ee['y'],ee['y'],None]
            fz+=[ee['z'],ee['z']-55,None]
        fig.add_trace(go.Scatter3d(x=fx,y=fy,z=fz,mode='lines',
            line=dict(color=gcol,width=7),showlegend=False,hoverinfo='skip'))

        # 地面阴影
        sx2=[x*0.998+bp['x']*0.002 for x in jx]
        fig.add_trace(go.Scatter3d(x=sx2,y=jy,z=[3]*len(jx),mode='lines',
            line=dict(color=f'rgba(100,255,218,0.08)',width=5),
            showlegend=False,hoverinfo='skip'))

        # 相位标签
        fig.add_trace(go.Scatter3d(
            x=[ee['x']],y=[ee['y']],z=[ee['z']+90],mode='text',
            text=[plb],textfont=dict(color=pcol,size=13,family='DM Mono'),
            showlegend=False,hoverinfo='skip'))

    # ---- 布局 ----
    s = stats() or {}
    fig.update_layout(
        title=dict(
            text=f"PANDA DUAL-ARM  |  Sorted: {s.get('successful_sorts',0)}  |  Step: {st.session_state.steps}",
            font=dict(color='#64ffda',size=13,family='DM Mono'),x=0.02),
        paper_bgcolor='rgba(0,0,0,0)',
        scene=dict(
            bgcolor='#07090f',
            xaxis=dict(range=[cx-950,cx+950],visible=False),
            yaxis=dict(range=[cy-950,cy+950],visible=False),
            zaxis=dict(range=[0,900],visible=False),
            camera=dict(eye=dict(x=1.6,y=-1.6,z=1.0),
                        center=dict(x=0,y=0,z=-0.15)),
            aspectmode='cube',
        ),
        legend=dict(bgcolor='rgba(7,9,15,0.8)',bordercolor='rgba(100,255,218,0.15)',
            borderwidth=1,font=dict(color='#8892b0',size=11,family='DM Mono'),
            orientation='v',x=0.01,y=0.99),
        height=640,margin=dict(l=0,r=0,t=36,b=0),
        uirevision='scene',
    )
    return fig
# ================================================================
# Sidebar
# ================================================================
with st.sidebar:
    st.markdown('<div style="font-family:\'DM Mono\',monospace;color:#64ffda;font-size:16px;letter-spacing:3px;padding:10px 0 8px;border-bottom:1px solid rgba(100,255,218,0.15);margin-bottom:16px;">CONTROL PANEL</div>',unsafe_allow_html=True)
    steps_per_run = st.slider('每次步进数',  50, 600, 200, 50)
    auto_runs     = st.slider('连续运行次数', 1,  30,   8)
    frame_delay   = st.slider('帧延迟 (s)',  0.0, 0.5, 0.05, 0.05)
    st.divider()
    show_stats = st.checkbox('实时统计',   value=True)
    show_bins  = st.checkbox('分拣箱图表', value=True)
    show_perf  = st.checkbox('性能图表',   value=True)
    st.divider()
    with st.expander('使用说明'):
        st.markdown("""
**Franka Panda 7轴协作机器人**

1. 点击 **INIT** 初始化双臂
2. 点击 **RUN** 开始分拣
3. 物品颜色决定目标箱:
   - 🔴 红 → Bin 0 · 🟢 绿 → Bin 1
   - 🔵 蓝 → Bin 2 · 🟡 黄 → Bin 3
""")
    st.markdown('<div style="margin-top:16px;padding:12px;background:rgba(100,255,218,0.04);border:1px solid rgba(100,255,218,0.1);border-radius:10px;font-family:\'DM Mono\',monospace;font-size:10px;color:#495670;">FRANKA PANDA<br>7-DOF · 855mm reach<br>3kg payload · Sub-mm</div>',unsafe_allow_html=True)

# ================================================================
# Header
# ================================================================
st.markdown("""
<div style="margin-bottom:18px;">
<h1 style="font-family:'DM Sans',sans-serif;font-weight:700;font-size:34px;background:linear-gradient(90deg,#64ffda,#ccd6f6);-webkit-background-clip:text;-webkit-text-fill-color:transparent;margin:0 0 4px;">Franka Panda 智能分拣系统</h1>
<p style="color:#495670;font-family:'DM Mono',monospace;font-size:11px;letter-spacing:2px;margin:0;">7-AXIS COLLABORATIVE ROBOT · REAL-TIME 3D · COLOR SORTING</p>
</div>
""",unsafe_allow_html=True)

tab1,tab2,tab3,tab4=st.tabs(['🦾  LIVE 3D','📊  ANALYTICS','📈  PERFORMANCE','ℹ  ABOUT'])
# ================================================================
# TAB 1
# ================================================================
with tab1:
    b1,b2,b3,b4=st.columns(4)
    with b1: init_btn =st.button('▶ INIT',  use_container_width=True)
    with b2: run_btn  =st.button('▶ RUN',   use_container_width=True)
    with b3: step_btn =st.button('▶ STEP',  use_container_width=True)
    with b4: reset_btn=st.button('↺ RESET', use_container_width=True)

    if init_btn:
        init_engine(); st.toast('Panda 双臂已初始化',icon='🦾')
    if reset_btn:
        st.session_state.engine=None; st.session_state.history=[]; st.session_state.steps=0; st.rerun()
    if step_btn and st.session_state.engine:
        run_steps(steps_per_run)

    st.markdown('---')
    if st.session_state.engine is None:
        st.markdown('<div style="text-align:center;padding:80px;border:1px dashed rgba(100,255,218,0.15);border-radius:16px;color:#495670;font-family:\'DM Mono\',monospace;font-size:13px;letter-spacing:2px;">🦾<br><br>Click <span style="color:#64ffda">INIT</span> to boot Franka Panda dual-arm</div>',unsafe_allow_html=True)
    else:
        if run_btn:
            ph=st.empty(); bar=st.progress(0); info=st.empty()
            for i in range(auto_runs):
                run_steps(steps_per_run)
                s=stats()
                fig3d=build_scene()
                if fig3d: ph.plotly_chart(fig3d,use_container_width=True,key=f'live_{st.session_state.steps}')
                bar.progress((i+1)/auto_runs)
                if s:
                    phs=[a['phase'] for a in s.get('arms',[])]
                    srt=[a['items_sorted'] for a in s.get('arms',[])]
                    info.markdown(f'`{i+1}/{auto_runs}` Step **{st.session_state.steps}** │ Sorted **{s.get("successful_sorts",0)}** │ {phs} {srt}')
                time.sleep(frame_delay)
            st.success(f"完成 — 共分拣 {stats().get('successful_sorts',0)} 件")
        else:
            fig3d=build_scene()
            if fig3d: st.plotly_chart(fig3d,use_container_width=True,key=f'static_{st.session_state.steps}')

    if show_stats and st.session_state.engine:
        st.markdown('---')
        s=stats()
        if s:
            c1,c2,c3,c4,c5=st.columns(5)
            c1.metric('已分拣',   s.get('successful_sorts',0))
            c2.metric('环境物品', s.get('items_in_environment',0))
            c3.metric('FPS',      s.get('fps','--'))
            c4.metric('准确率',   s.get('accuracy_rate','--'))
            c5.metric('仿真时间', s.get('simulation_time','--'))
            arms=s.get('arms',[])
            if arms:
                acols=st.columns(len(arms))
                for i,a in enumerate(arms):
                    col=_ARM_COL[a['id']%2]
                    pcol=_PHASE_COL.get(a['phase'],'#aaa')
                    acols[i].markdown(
                        f'<div style="border:1px solid {col};border-radius:12px;padding:14px;background:rgba(0,0,0,0.3);">'
                        f'<div style="color:{col};font-family:\'DM Mono\',monospace;font-size:10px;letter-spacing:2px;">PANDA {a["id"]}</div>'
                        f'<div style="color:{pcol};font-size:22px;font-weight:700;margin:4px 0;">{a["phase"].upper()}</div>'
                        f'<div style="color:#8892b0;font-size:12px;">Sorted <b style="color:#ccd6f6">{a["items_sorted"]}</b>'
                        f' &nbsp;·&nbsp; Battery <b style="color:{col}">{a["battery"]}%</b></div></div>',
                        unsafe_allow_html=True)

    if show_bins and st.session_state.engine:
        st.markdown('---')
        df=bins_df()
        if not df.empty:
            fig_b=go.Figure(go.Bar(
                x=df['Bin'],y=df['装载%'],
                marker=dict(color=_BIN_COL[:len(df)],opacity=0.8,line=dict(color='rgba(255,255,255,0.15)',width=1)),
                text=df['装载%'].apply(lambda v:f'{v:.0f}%'),
                textposition='auto',textfont=dict(color='#fff',family='DM Mono')))
            fig_b.update_layout(
                paper_bgcolor='rgba(0,0,0,0)',plot_bgcolor='#0d1117',
                font=dict(color='#8892b0',family='DM Mono'),
                xaxis=dict(gridcolor='#1e2d3d'),yaxis=dict(gridcolor='#1e2d3d',range=[0,105]),
                height=240,margin=dict(l=10,r=10,t=10,b=10),showlegend=False)
            st.plotly_chart(fig_b,use_container_width=True,key='bins_bar')

# ================================================================
# TAB 2
# ================================================================
with tab2:
    if not st.session_state.engine:
        st.info('请先初始化系统')
    else:
        s=stats()
        if s:
            c1,c2,c3=st.columns(3)
            c1.metric('总处理',s.get('total_items_processed',0))
            c2.metric('成功',  s.get('successful_sorts',0))
            c3.metric('失败',  s.get('failed_sorts',0))
        df=bins_df()
        if not df.empty:
            st.dataframe(df,use_container_width=True)
            fig_pie=go.Figure(go.Pie(
                labels=df['Bin'],values=[max(v,0.001) for v in df['已装'].tolist()],hole=0.5,
                marker=dict(colors=_BIN_COL[:4],line=dict(color='#07090f',width=3)),
                textfont=dict(color='#fff',family='DM Mono')))
            fig_pie.update_layout(
                paper_bgcolor='rgba(0,0,0,0)',font=dict(color='#8892b0',family='DM Mono'),
                height=300,margin=dict(l=0,r=0,t=10,b=0),
                legend=dict(bgcolor='rgba(0,0,0,0)'),
                title=dict(text='各箱物品占比',font=dict(color='#64ffda')))
            st.plotly_chart(fig_pie,use_container_width=True,key='pie')

# ================================================================
# TAB 3
# ================================================================
with tab3:
    hist=st.session_state.history
    if show_perf and len(hist)>1:
        df_h=pd.DataFrame(hist)
        fig_p=make_subplots(rows=2,cols=2,subplot_titles=('FPS','环境物品','已处理','已分拣'))
        x=df_h['step'].tolist()
        for cn,color,r,c in [('fps','#64ffda',1,1),('in_env','#ff6b6b',1,2),('processed','#69f0ae',2,1),('sorted','#ffd740',2,2)]:
            if cn in df_h.columns:
                fig_p.add_trace(go.Scatter(x=x,y=df_h[cn],mode='lines',line=dict(color=color,width=2),showlegend=False),row=r,col=c)
        fig_p.update_layout(
            paper_bgcolor='rgba(0,0,0,0)',plot_bgcolor='#0d1117',
            font=dict(color='#8892b0',family='DM Mono'),
            height=460,margin=dict(l=10,r=10,t=40,b=10))
        for ann in fig_p.layout.annotations: ann.font.update(color='#64ffda',family='DM Mono',size=11)
        fig_p.update_xaxes(gridcolor='#1e2d3d'); fig_p.update_yaxes(gridcolor='#1e2d3d')
        st.plotly_chart(fig_p,use_container_width=True,key='perf')
    else:
        st.info('运行仿真后将显示性能图表')

# ================================================================
# TAB 4
# ================================================================
with tab4:
    st.markdown("""
## 🦾 Franka Panda 智能分拣系统

### 机器人规格
| 参数 | 值 |
|------|----|
| 型号 | Franka Panda |
| 自由度 | 7-DOF |
| 臂展 | 855 mm |
| 有效载荷 | 3 kg |
| 重复精度 | ±0.1 mm |
| 关节数 | 7 |

### 系统架构
```
app.py                       ← Streamlit 前端
backend/core/
  robot_arm.py               ← Franka Panda 7轴运动学
  simulation_engine.py       ← 任务分配 + 状态机
  environment.py             ← 3D 工作环境
```

### 分拣规则
🔴 红 → Bin 0 · 🟢 绿 → Bin 1 · 🔵 蓝 → Bin 2 · 🟡 黄 → Bin 3

```bash
pip install -r requirements.txt
streamlit run app.py
```
""")

st.markdown('<div style="text-align:center;color:#1e2d3d;font-family:\'DM Mono\',monospace;font-size:10px;padding:12px;margin-top:8px;">FRANKA PANDA DUAL-ARM SORTING · STREAMLIT · PLOTLY 3D</div>',unsafe_allow_html=True)
