import streamlit as st
import pandas as pd
import json
import os
import time

# ==========================================
# ⚙️ 全局配置
# ==========================================
DB_FILE = "game_data.json"
ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "991029"

# 数值规则
MIN_BET_LIMIT = 100
MAX_BET_LIMIT = 1000
MIN_MARKET_COUNT = 2
HOUSE_ODDS = 2
SALARY_MAP = {"1": 1000, "2": 1000, "3": 2000}

# 队伍配置
TEAM_A_NAME = "温鹏祥队"
TEAM_B_NAME = "何博文队"
TEAMS_OPTIONS = [TEAM_A_NAME, TEAM_B_NAME]

# MVP 名单
MVP_LISTS = {
    "1": [f"{TEAM_A_NAME}-{p}" for p in ["上单：乔榛","打野：晏晨熙","中单：梁辰","射手：李浩","辅助：郝奕博"]] + 
         [f"{TEAM_B_NAME}-{p}" for p in ["上单：邓淦","打野：贾宇新","中单：苏宇","射手：赵宇涵","辅助：刘培俊"]],
    "2": [f"{TEAM_A_NAME}-{p}" for p in ["上单：阮胤广","打野：左天白","中单：张益帆","射手：温鹏祥","辅助：黄俊"]] + 
         [f"{TEAM_B_NAME}-{p}" for p in ["上单：马浩","打野：何博文","中单：王铭宇","射手：钟文迪","辅助：刘宇骅"]],
    "3": [f"{TEAM_A_NAME}-{p}" for p in ["上单：阮胤广","打野：左天白","中单：张益帆","射手：温鹏祥","辅助：黄俊"]] + 
         [f"{TEAM_B_NAME}-{p}" for p in ["上单：马浩","打野：何博文","中单：王铭宇","射手：钟文迪","辅助：刘宇骅"]]
}
DEFAULT_MVP_LIST = [f"选手{i}" for i in range(1, 11)]

# ==========================================
# 🛠️ 核心函数
# ==========================================
def get_market_config(round_str):
    mvp_opts = MVP_LISTS.get(round_str, DEFAULT_MVP_LIST)
    return {
        "🏆 胜负": {"type": "PVP", "options": TEAMS_OPTIONS, "ui": "radio"},
        "🌟 胜方MVP": {"type": "PVP", "options": mvp_opts, "ui": "select"},
        "🩸 一血": {"type": "PVE", "options": TEAMS_OPTIONS, "ui": "radio"},
        "🏰 一塔": {"type": "PVE", "options": TEAMS_OPTIONS, "ui": "radio"},
        "💀 人头数": {"type": "PVE", "options": ["单", "双"], "ui": "radio"},
        "⏳ 对局时长": {"type": "PVE", "options": ["小于16min", "大于等于16min"], "ui": "radio"}
    }

def load_data():
    if not os.path.exists(DB_FILE):
        data = {
            "users": {ADMIN_USERNAME: ADMIN_PASSWORD},
            "round": 1, "vault": {}, "bets": [], "logs": [],
            "is_locked": False, "reg_closed": False, 
            "match_history": [], "game_over": False
        }
        save_data(data)
        return data
    try:
        with open(DB_FILE, "r", encoding="utf-8") as f: return json.load(f)
    except: return {}

def save_data(data):
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

# 🔥 新增：计算实时赔率
def calculate_realtime_odds(bets, market_name, market_type, option):
    if market_type == "PVE":
        return HOUSE_ODDS
    
    # PVP 逻辑
    df = pd.DataFrame(bets)
    if df.empty: return 1.0
    
    # 筛选该盘口的所有注单
    m_bets = df[df['market'] == market_name]
    if m_bets.empty: return 1.0
    
    total_pool = m_bets['amount'].sum()
    
    # 筛选该选项的注单
    opt_bets = m_bets[m_bets['choice'] == option]
    opt_pool = opt_bets['amount'].sum()
    
    if opt_pool == 0:
        return 99.9 # 显示 99.9 代表还没人买，赔率无限大
    
    return total_pool / opt_pool

# ==========================================
# 🎨 UI 组件
# ==========================================
def show_rules(expanded=False):
    """显示规则的统一组件"""
    with st.expander("📜 比赛规则说明 (点击展开/收起)", expanded=expanded):
        st.markdown(f"""
        ### 1. 💰 积分发放
        - **第一/二局**：系统发放 **{SALARY_MAP['1']}** 积分。
        - **第三局**：系统发放 **{SALARY_MAP['3']}** 积分。
        - **⚠️ 清空机制**：每局未下注的积分**直接清空**，不累计到下一局！请务必把工资花完。

        ### 2. 🎲 赔率类型
        - **⚔️ 玩家博弈 (PVP)**：`胜方`、`胜方MVP`
          - 动态赔率，赢家瓜分输家筹码。买的人越少，赔率越高！
        - **🏦 庄家固定 (PVE)**：`一血`、`一塔`、`人头数`、`时长`
          - 固定赔率 **{HOUSE_ODDS}倍**。无论多少人买，中了系统就赔。

        ### 3. 🚫 下注限制
        - **单注金额**：{MIN_BET_LIMIT} ~ {MAX_BET_LIMIT}
        - **最少参与**：每局至少下注 **{MIN_MARKET_COUNT}** 个不同盘口。

        ### 4. 🏁 特殊赛制
        - **BO3 机制**：若前两局同一队获胜 (2:0)，比赛直接结束。
        - **MVP 评选**：需准确预测 **胜方** 的 **具体选手** (10选1)。
        - **注册锁定**：第一局封盘后，停止新玩家注册。
        """)

# ==========================================
# 🔐 登录注册
# ==========================================
def login_page():
    st.set_page_config(page_title="策划杯竞猜", layout="wide")
    st.title("⚔️ 策划杯竞猜")
    show_rules(True)
    data = load_data()
    
    if data.get("game_over"): st.error("🏁 比赛已结束")
    
    t1, t2 = st.tabs(["登录", "注册"])
    with t1:
        with st.form("login"):
            u = st.text_input("账号")
            p = st.text_input("密码", type="password")
            if st.form_submit_button("登录", use_container_width=True):
                users = data.get("users", {})
                if u in users and users[u] == p:
                    st.session_state.current_user = u
                    st.rerun()
                else: st.error("错误")
    with t2:
        if data.get("reg_closed"): st.error("🚫 注册已关闭")
        else:
            with st.form("reg"):
                nu = st.text_input("新账号"); np = st.text_input("密码", type="password")
                if st.form_submit_button("注册"):
                    if nu in data["users"]: st.error("ID存在")
                    elif not nu: st.warning("不能为空")
                    else:
                        data["users"][nu] = np
                        if nu not in data["vault"]: data["vault"][nu] = 0.0
                        save_data(data)
                        st.session_state.current_user = nu
                        st.success("成功"); time.sleep(0.5); st.rerun()

# ==========================================
# 🎮 主程序
# ==========================================
def main_app():
    st.set_page_config(page_title="策划赛竞猜", layout="wide")
    user = st.session_state.current_user
    data = load_data()
    is_admin = (user == ADMIN_USERNAME)
    
    r_str = str(data["round"])
    salary = SALARY_MAP.get(r_str, 0) if not data.get("game_over") else 0
    MARKET_CONFIG = get_market_config(r_str)

    # 侧边栏
    with st.sidebar:
        st.header(f"👤 {user}")
        if st.button("🚪 退出"): st.session_state.current_user = None; st.rerun()
        st.divider()
        if st.button("🔄 刷新赔率"): st.rerun() # 必须提供刷新按钮

    if data.get("game_over"):
        st.title("🏁 比赛结束"); st.info(f"历史: {data.get('match_history')}")
    else:
        st.title(f"⚔️ 第 {r_str} 局")
        show_rules(False)

    # --- 管理员 ---
    if is_admin:
        st.subheader("🔧 后台")
        c1, c2 = st.columns(2)
        with c1:
            lbl = "🛑 封盘(锁注册)" if (data["round"]==1 and not data["is_locked"]) else "🛑 封盘/解锁"
            if st.button(lbl, type="primary" if not data["is_locked"] else "secondary"):
                data["is_locked"] = not data["is_locked"]
                if data["round"]==1 and data["is_locked"]: data["reg_closed"] = True
                save_data(data); st.rerun()
            st.caption(f"状态: {'🔒 封盘' if data['is_locked'] else '🟢 开放'}")
        with c2:
            if st.button("🗑️ 删档"):
                if os.path.exists(DB_FILE): os.remove(DB_FILE); st.session_state.current_user=None; st.rerun()
        
        # 结算面板
        st.divider(); st.subheader("⚖️ 结算")
        with st.form("settle"):
            res = {}
            cols = st.columns(3)
            for i, (m, cfg) in enumerate(MARKET_CONFIG.items()):
                with cols[i%3]: res[m] = st.selectbox(m, cfg["options"])
            
            if st.form_submit_button("💰 结算", type="primary", use_container_width=True):
                logs = [f"=== 第 {r_str} 局结算 ==="]
                pmap = {u:0.0 for u in data["users"] if u!=ADMIN_USERNAME}
                df = pd.DataFrame(data["bets"])
                
                if not df.empty:
                    for m, r in res.items():
                        mb = df[df['market']==m]
                        if mb.empty: continue
                        wins = mb[mb['choice']==r]
                        logs.append(f"[{m}] 结果:{r}")
                        
                        if MARKET_CONFIG[m]["type"]=="PVP":
                            pool = mb['amount'].sum(); w_pool = wins['amount'].sum()
                            if w_pool>0:
                                ratio = pool/w_pool; logs.append(f" -> 赔率 {ratio:.2f}")
                                for _,row in wins.iterrows(): pmap[row['player']] += row['amount']*ratio
                            else: logs.append(" -> 通杀")
                        else: # PVE
                            if not wins.empty:
                                for _,row in wins.iterrows(): pmap[row['player']] += row['amount']*HOUSE_ODDS

                for p,v in pmap.items(): 
                    data["vault"][p] = data["vault"].get(p,0)+v
                    if v>0: logs.append(f"{p} +{v:.1f}")
                
                if res.get("🏆 胜负"): data["match_history"].append(res["🏆 胜负"])
                
                h = data["match_history"]
                if (len(h)==2 and h[0]==h[1]) or len(h)==3: data["game_over"]=True
                else: data["round"]+=1
                
                data["bets"]=[]; data["logs"].extend(logs); data["is_locked"]=False
                save_data(data); st.success("结算完毕"); time.sleep(1); st.rerun()

    # --- 玩家界面 (平铺展示核心逻辑) ---
    else:
        # 顶部资产栏
        my_bets = [b for b in data["bets"] if b["player"] == user]
        used = sum(b["amount"] for b in my_bets)
        rem = salary - used
        mkts = set(b['market'] for b in my_bets)
        
        c1, c2, c3 = st.columns(3)
        c1.metric("💰 剩余工资", rem)
        c2.metric("🏦 金库总分", f"{data['vault'].get(user,0):.1f}")
        c3.metric("✅ 达标情况", f"{len(mkts)}/{MIN_MARKET_COUNT}", delta_color="normal" if len(mkts)>=MIN_MARKET_COUNT else "inverse")

        st.divider()
        if data["is_locked"]: st.error("🔒 已封盘"); st.stop()

        # 🔥 平铺布局核心: 使用2列网格展示所有盘口
        st.subheader("📝 快速下注")
        
        # 将盘口转为列表方便遍历
        market_items = list(MARKET_CONFIG.items())
        # 创建 2 列容器
        grid = st.columns(2)
        
        for idx, (m_name, cfg) in enumerate(market_items):
            # 决定放在左列还是右列
            col = grid[idx % 2]
            
            with col:
                with st.container(border=True):
                    # 标题栏: 名称 + 赔率类型
                    tag = "🏦 PVE" if cfg["type"] == "PVE" else "⚔️ PVP"
                    st.markdown(f"**{m_name}** <small style='color:gray'>{tag}</small>", unsafe_allow_html=True)
                    
                    # 1. 选项输入
                    key_prefix = f"{r_str}_{m_name}" # 唯一Key防止冲突
                    
                    if cfg["ui"] == "select":
                        user_choice = st.selectbox("选择预测", cfg["options"], key=f"sel_{key_prefix}")
                    else:
                        user_choice = st.radio("选择预测", cfg["options"], horizontal=True, key=f"rad_{key_prefix}")
                    
                    # 2. 实时赔率展示 (PVP核心)
                    if cfg["type"] == "PVP":
                        curr_odds = calculate_realtime_odds(data["bets"], m_name, "PVP", user_choice)
                        if curr_odds >= 99:
                            st.caption(f"🔥 当前实时赔率: **暂无** (你是第一个!)")
                        else:
                            st.caption(f"🔥 当前实时赔率: **{curr_odds:.2f} 倍**")
                    else:
                        st.caption(f"🛡️ 固定赔率: **{HOUSE_ODDS} 倍**")

                    # 3. 金额与提交 (独立的一行)
                    sub_c1, sub_c2 = st.columns([1, 1])
                    with sub_c1:
                        max_val = min(rem, MAX_BET_LIMIT)
                        val_enabled = max_val >= MIN_BET_LIMIT
                        amount = st.number_input("金额", 
                                               min_value=MIN_BET_LIMIT, 
                                               max_value=max_val if val_enabled else MIN_BET_LIMIT, 
                                               step=50, 
                                               label_visibility="collapsed",
                                               disabled=not val_enabled,
                                               key=f"amt_{key_prefix}")
                    
                    with sub_c2:
                        if st.button("下注", 
                                     key=f"btn_{key_prefix}", 
                                     disabled=not val_enabled, 
                                     use_container_width=True,
                                     type="primary"):
                            
                            data["bets"].append({
                                "player": user, "market": m_name,
                                "choice": user_choice, "amount": int(amount),
                                "timestamp": time.time()
                            })
                            save_data(data)
                            st.toast(f"✅ {m_name}: 已下注 {amount}")
                            time.sleep(0.5)
                            st.rerun()

        # 底部显示已下注单
        if my_bets:
            st.divider()
            st.caption("🧾 本局我的注单")
            st.dataframe(pd.DataFrame(my_bets)[["market", "choice", "amount"]], use_container_width=True, hide_index=True)

    # 排行榜
    st.divider(); st.subheader("🏆 排行榜")
    rd = {k:v for k,v in data["vault"].items() if k!=ADMIN_USERNAME}
    if rd: 
        df = pd.DataFrame(list(rd.items()), columns=["玩家","金库"]).sort_values("金库", ascending=False)
        df.index += 1; st.dataframe(df, use_container_width=True)
    
    with st.expander("历史日志"): 
        for l in reversed(data["logs"]): st.text(l)

if "current_user" not in st.session_state: st.session_state.current_user = None
if st.session_state.current_user is None: login_page()
else: main_app()


