import streamlit as st
import pandas as pd
import json
import os
import time

# ==========================================
# ⚙️ 配置与常量
# ==========================================
DB_FILE = "game_data.json"

# 内置管理员账号 (账号名固定为 admin)
ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "888"  # <--- 你可以在这里修改管理员密码

# 游戏数值规则
MIN_BET_LIMIT = 100
MAX_BET_LIMIT = 500
MIN_MARKET_COUNT = 2
SALARY_MAP = {"1": 1000, "2": 1000, "3": 2000}

# 固定盘口
MARKET_CONFIG = {
    "🏆 谁赢 (胜负)": ["蓝方 (A队)", "红方 (B队)"],
    "🩸 一血": ["蓝方 (A队)", "红方 (B队)"],
    "🏰 一塔": ["蓝方 (A队)", "红方 (B队)"],
    "💀 人头数": ["单", "双"],
    "⏳ 对局时长": ["大于等于12min", "小于12min"]
}

# ==========================================
# 🛠️ 数据存取函数
# ==========================================
def load_data():
    # 如果文件不存在，初始化结构
    if not os.path.exists(DB_FILE):
        data = {
            "users": {ADMIN_USERNAME: ADMIN_PASSWORD},  # 存储 "用户名": "密码"
            "round": 1,
            "vault": {},  # 金库
            "bets": [],   # 下注记录
            "logs": [],   # 日志
            "is_locked": False
        }
        save_data(data)
        return data
    
    # 读取数据
    try:
        with open(DB_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return {} # 容错

def save_data(data):
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

# ==========================================
# 🔐 认证界面 (登录/注册)
# ==========================================
def login_page():
    st.title("⚔️ 峡谷预测家 Pro")
    
    data = load_data()
    
    tab1, tab2 = st.tabs(["🔑 登录", "📝 注册新玩家"])
    
    # --- 登录模块 ---
    with tab1:
        with st.form("login_form"):
            username = st.text_input("账号")
            password = st.text_input("密码", type="password")
            submit = st.form_submit_button("登录", type="primary", use_container_width=True)
            
            if submit:
                users = data.get("users", {})
                if username in users and users[username] == password:
                    st.session_state.current_user = username
                    st.success(f"欢迎回来, {username}!")
                    time.sleep(0.5)
                    st.rerun()
                else:
                    st.error("账号或密码错误！")

    # --- 注册模块 ---
    with tab2:
        with st.form("register_form"):
            new_user = st.text_input("设置你的ID (如: uzi)")
            new_pwd = st.text_input("设置密码", type="password")
            confirm_pwd = st.text_input("确认密码", type="password")
            reg_submit = st.form_submit_button("注册并进入", use_container_width=True)
            
            if reg_submit:
                users = data.get("users", {})
                if not new_user or not new_pwd:
                    st.warning("账号密码不能为空")
                elif new_user in users:
                    st.error("该ID已被注册，请换一个！")
                elif new_pwd != confirm_pwd:
                    st.error("两次密码输入不一致")
                else:
                    # 写入新用户
                    data["users"][new_user] = new_pwd
                    # 初始化金库（如果是中途加入，金库为0）
                    if new_user not in data["vault"]:
                        data["vault"][new_user] = 0.0
                    save_data(data)
                    
                    # 自动登录
                    st.session_state.current_user = new_user
                    st.success("注册成功！")
                    time.sleep(0.5)
                    st.rerun()

# ==========================================
# 🎮 主游戏界面
# ==========================================
def main_app():
    user_id = st.session_state.current_user
    data = load_data()
    
    # 确定是否是管理员
    is_admin = (user_id == ADMIN_USERNAME)
    
    # 侧边栏：用户信息与登出
    with st.sidebar:
        st.header(f"👤 {user_id}")
        if is_admin:
            st.success("身份：管理员")
        else:
            st.info("身份：玩家")
            
        if st.button("🚪 退出登录"):
            st.session_state.current_user = None
            st.rerun()
            
        st.divider()
        if st.button("🔄 刷新数据"):
            st.rerun()

    current_round = str(data["round"])
    current_salary = SALARY_MAP.get(current_round, 2000)

    st.title(f"⚔️ 峡谷预测家 (第 {current_round} 局)")

    # ==========================
    #  场景 A: 管理员视图
    # ==========================
    if is_admin:
        st.subheader("🔧 管理控制台")
        
        c1, c2 = st.columns(2)
        with c1:
            if st.button("🛑 封盘 / 解锁", type="primary" if not data["is_locked"] else "secondary"):
                data["is_locked"] = not data["is_locked"]
                save_data(data)
                st.rerun()
            st.caption(f"状态: {'🔒 已封盘' if data['is_locked'] else '🟢 开放中'}")
        
        with c2:
            if st.button("🗑️ 删档重置 (清空所有数据)"):
                if os.path.exists(DB_FILE): os.remove(DB_FILE)
                st.session_state.current_user = None # 踢出所有登录
                st.rerun()

        st.divider()
        st.subheader("👮 下注合规检查")
        
        if data["bets"]:
            df = pd.DataFrame(data["bets"])
            # 统计所有非管理员用户
            all_players = [u for u in data["users"].keys() if u != ADMIN_USERNAME]
            
            stats = []
            for p in all_players:
                p_bets = df[df['player'] == p]
                spent = p_bets['amount'].sum() if not p_bets.empty else 0
                unique_markets = p_bets['market'].nunique() if not p_bets.empty else 0
                
                status = "✅"
                if unique_markets < MIN_MARKET_COUNT:
                    status = f"❌ 盘口不足 ({unique_markets}/{MIN_MARKET_COUNT})"
                elif spent != current_salary:
                    status += " (余额未清)"
                
                stats.append({
                    "玩家": p,
                    "已花": spent,
                    "剩余": current_salary - spent,
                    "盘口数": unique_markets,
                    "状态": status
                })
            st.dataframe(pd.DataFrame(stats), hide_index=True, use_container_width=True)
            
            with st.expander("所有注单明细"):
                st.dataframe(df, use_container_width=True)
        else:
            st.info("暂无下注")

        st.divider()
        st.subheader("⚖️ 结算比赛")
        with st.form("settle"):
            settle_res = {}
            cols = st.columns(3)
            for i, (m, opts) in enumerate(MARKET_CONFIG.items()):
                with cols[i%3]:
                    settle_res[m] = st.selectbox(m, opts)
            
            if st.form_submit_button("💰 结算", type="primary", use_container_width=True):
                logs = [f"=== 第 {current_round} 局结算 ==="]
                profit_map = {u: 0.0 for u in data["users"] if u != ADMIN_USERNAME}
                bets_df = pd.DataFrame(data["bets"])
                
                if not bets_df.empty:
                    for m, correct in settle_res.items():
                        m_bets = bets_df[bets_df['market'] == m]
                        pool = m_bets['amount'].sum()
                        winners = m_bets[m_bets['choice'] == correct]
                        win_pool = winners['amount'].sum()
                        
                        logs.append(f"[{m}] 结果: {correct}")
                        if win_pool > 0:
                            ratio = pool / win_pool
                            logs.append(f" -> 赔率 {ratio:.2f} (池 {pool})")
                            for _, r in winners.iterrows():
                                profit_map[r['player']] += r['amount'] * ratio
                        elif pool > 0:
                            logs.append(" -> 💀 通杀")
                        else:
                            pass
                
                for p, val in profit_map.items():
                    data["vault"][p] = data["vault"].get(p, 0) + val
                    if val > 0: logs.append(f"{p} +{val:.1f}")
                
                data["round"] += 1
                data["bets"] = []
                data["logs"].extend(logs)
                data["is_locked"] = False
                save_data(data)
                st.success("结算完毕")
                time.sleep(1)
                st.rerun()

    # ==========================
    #  场景 B: 玩家视图
    # ==========================
    else:
        # 1. 顶部资产
        my_bets = [b for b in data["bets"] if b["player"] == user_id]
        used = sum(b["amount"] for b in my_bets)
        remaining = current_salary - used
        my_markets = set(b['market'] for b in my_bets)
        
        c1, c2, c3 = st.columns(3)
        c1.metric("💰 本局余额", remaining)
        c2.metric("🏦 小金库", f"{data['vault'].get(user_id, 0):.1f}")
        
        # 状态指示
        if len(my_markets) >= MIN_MARKET_COUNT:
            c3.success(f"✅ 任务达标 ({len(my_markets)}/{MIN_MARKET_COUNT})")
        else:
            c3.error(f"❌ 任务未完成 ({len(my_markets)}/{MIN_MARKET_COUNT})")

        st.divider()

        # 2. 下注区
        if data["is_locked"]:
            st.warning("🔒 已封盘，无法下注")
        else:
            with st.container(border=True):
                m_choice = st.selectbox("选择盘口", list(MARKET_CONFIG.keys()))
                opts = MARKET_CONFIG[m_choice]
                
                c_opt, c_amt = st.columns([2, 1])
                user_pick = c_opt.radio("你的预测", opts, horizontal=True)
                
                max_val = min(remaining, MAX_BET_LIMIT)
                if max_val < MIN_BET_LIMIT:
                    c_amt.warning("余额/额度不足")
                    can_bet = False
                else:
                    amt = c_amt.number_input("金额", MIN_BET_LIMIT, max_val, step=50)
                    can_bet = True
                
                if st.button("提交下注", disabled=not can_bet, use_container_width=True, type="primary"):
                    data["bets"].append({
                        "player": user_id, "market": m_choice,
                        "choice": user_pick, "amount": int(amt),
                        "timestamp": time.time()
                    })
                    save_data(data)
                    st.success("成功")
                    time.sleep(0.5)
                    st.rerun()

        if my_bets:
            st.caption("我的注单")
            st.dataframe(pd.DataFrame(my_bets)[["market", "choice", "amount"]], use_container_width=True, hide_index=True)

    # ==========================
    #  通用: 排行榜与日志
    # ==========================
    st.divider()
    st.subheader("🏆 排行榜")
    # 过滤掉 admin 账号显示在排行榜
    rank_data = {k:v for k,v in data["vault"].items() if k != ADMIN_USERNAME}
    if rank_data:
        df = pd.DataFrame(list(rank_data.items()), columns=["玩家", "金库"])
        df = df.sort_values("金库", ascending=False).reset_index(drop=True)
        df.index += 1
        st.dataframe(df, use_container_width=True)
    
    with st.expander("历史日志"):
        for l in reversed(data["logs"]):
            st.text(l)

# ==========================================
# 🚀 程序入口
# ==========================================
# 初始化 session user
if "current_user" not in st.session_state:
    st.session_state.current_user = None

# 路由逻辑：如果没登录显示登录页，否则显示主程序
if st.session_state.current_user is None:
    login_page()
else:
    main_app()