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
ADMIN_PASSWORD = "888"  # 管理员密码

# --- 游戏数值规则 ---
MIN_BET_LIMIT = 100       # 单注下限
MAX_BET_LIMIT = 500       # 单注上限
MIN_MARKET_COUNT = 2      # 至少玩几个盘口
SALARY_MAP = {"1": 1000, "2": 1000, "3": 2000}
HOUSE_ODDS = 1.9          # 庄家盘固定赔率 (1赔1.9)

# --- 盘口定义 (区分 PVP 和 PVE) ---
# PVP: 奖池瓜分制 (玩家互赢)
# PVE: 庄家固定赔率 (跟系统对赌)
MARKET_CONFIG = {
    "🏆 谁赢 (胜负)": {
        "type": "PVP", 
        "options": ["蓝方 (A队)", "红方 (B队)"]
    },
    "🩸 一血": {
        "type": "PVE", 
        "options": ["蓝方 (A队)", "红方 (B队)"]
    },
    "🏰 一塔": {
        "type": "PVE", 
        "options": ["蓝方 (A队)", "红方 (B队)"]
    },
    "💀 人头数": {
        "type": "PVE", 
        "options": ["单", "双"]
    },
    "⏳ 对局时长": {
        "type": "PVE", 
        "options": ["大于等于12min", "小于12min"]
    }
}

# ==========================================
# 🛠️ 数据存取
# ==========================================
def load_data():
    if not os.path.exists(DB_FILE):
        data = {
            "users": {ADMIN_USERNAME: ADMIN_PASSWORD},
            "round": 1,
            "vault": {},
            "bets": [],
            "logs": [],
            "is_locked": False
        }
        save_data(data)
        return data
    try:
        with open(DB_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return {}

def save_data(data):
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

# ==========================================
# 🔐 登录/注册模块
# ==========================================
def login_page():
    st.title("⚔️ 峡谷预测家 Pro (庄家版)")
    data = load_data()
    tab1, tab2 = st.tabs(["🔑 登录", "📝 注册"])
    
    with tab1:
        with st.form("login"):
            user = st.text_input("账号")
            pwd = st.text_input("密码", type="password")
            if st.form_submit_button("登录", type="primary", use_container_width=True):
                users = data.get("users", {})
                if user in users and users[user] == pwd:
                    st.session_state.current_user = user
                    st.success("登录成功")
                    time.sleep(0.5)
                    st.rerun()
                else:
                    st.error("账号密码错误")
    
    with tab2:
        with st.form("reg"):
            new_u = st.text_input("新账号ID")
            new_p = st.text_input("设置密码", type="password")
            if st.form_submit_button("注册"):
                if new_u in data["users"]:
                    st.error("账号已存在")
                elif not new_u or not new_p:
                    st.warning("不能为空")
                else:
                    data["users"][new_u] = new_p
                    if new_u not in data["vault"]:
                        data["vault"][new_u] = 0.0
                    save_data(data)
                    st.session_state.current_user = new_u
                    st.success("注册成功")
                    time.sleep(0.5)
                    st.rerun()

# ==========================================
# 🎮 主程序
# ==========================================
def main_app():
    user_id = st.session_state.current_user
    data = load_data()
    is_admin = (user_id == ADMIN_USERNAME)
    
    current_round = str(data["round"])
    current_salary = SALARY_MAP.get(current_round, 2000)

    # 侧边栏
    with st.sidebar:
        st.header(f"👤 {user_id}")
        st.caption("身份: " + ("管理员" if is_admin else "玩家"))
        if st.button("🚪 注销"):
            st.session_state.current_user = None
            st.rerun()
        st.divider()
        if st.button("🔄 刷新"): st.rerun()

    st.title(f"⚔️ 第 {current_round} 局")

    # ----------------------------------
    #  场景 A: 管理员后台
    # ----------------------------------
    if is_admin:
        st.subheader("🔧 控制台")
        c1, c2 = st.columns(2)
        with c1:
            if st.button("🛑 封盘/解锁", type="primary" if not data["is_locked"] else "secondary"):
                data["is_locked"] = not data["is_locked"]
                save_data(data)
                st.rerun()
            st.caption(f"状态: {'🔒 已封盘' if data['is_locked'] else '🟢 开放中'}")
        with c2:
            if st.button("🗑️ 删档重置"):
                if os.path.exists(DB_FILE): os.remove(DB_FILE)
                st.session_state.current_user = None
                st.rerun()
        
        st.divider()
        
        # 监控面板
        st.subheader("👮 下注监控")
        if data["bets"]:
            df = pd.DataFrame(data["bets"])
            players = [u for u in data["users"] if u != ADMIN_USERNAME]
            stats = []
            for p in players:
                pb = df[df['player'] == p]
                spent = pb['amount'].sum() if not pb.empty else 0
                mkts = pb['market'].nunique() if not pb.empty else 0
                status = "✅"
                if mkts < MIN_MARKET_COUNT: status = f"❌ 缺盘口 ({mkts}/{MIN_MARKET_COUNT})"
                elif spent != current_salary: status += " (余额未清)"
                stats.append({"玩家": p, "已花": spent, "盘口数": mkts, "状态": status})
            st.dataframe(pd.DataFrame(stats), hide_index=True, use_container_width=True)
        else:
            st.info("等待下注...")

        st.divider()
        
        # 结算面板
        st.subheader("⚖️ 结算比赛")
        with st.form("settle"):
            settle_res = {}
            cols = st.columns(3)
            # 动态生成结算选项
            for i, (m_name, m_cfg) in enumerate(MARKET_CONFIG.items()):
                with cols[i%3]:
                    settle_res[m_name] = st.selectbox(m_name, m_cfg["options"])
            
            if st.form_submit_button("💰 结算", type="primary", use_container_width=True):
                logs = [f"=== 第 {current_round} 局结算 ==="]
                profit_map = {u: 0.0 for u in data["users"] if u != ADMIN_USERNAME}
                bets_df = pd.DataFrame(data["bets"])
                
                if not bets_df.empty:
                    for market_name, correct_opt in settle_res.items():
                        m_type = MARKET_CONFIG[market_name]["type"]
                        m_bets = bets_df[bets_df['market'] == market_name]
                        
                        if m_bets.empty: continue
                        
                        logs.append(f"📌 [{market_name}] 结果: {correct_opt}")
                        
                        # --- 结算逻辑分支 ---
                        winners = m_bets[m_bets['choice'] == correct_opt]
                        win_amt = winners['amount'].sum()
                        
                        # 1. PVP 模式 (奖池瓜分)
                        if m_type == "PVP":
                            total_pool = m_bets['amount'].sum()
                            if win_amt > 0:
                                ratio = total_pool / win_amt
                                logs.append(f"   ⚔️ PVP池: {total_pool} | 赔率: {ratio:.2f}")
                                for _, r in winners.iterrows():
                                    profit_map[r['player']] += r['amount'] * ratio
                            else:
                                logs.append("   💀 PVP通杀 (无人猜中)")
                                
                        # 2. PVE 模式 (庄家固定赔率)
                        else:
                            logs.append(f"   🏦 庄家盘 | 赔率: {HOUSE_ODDS}")
                            if win_amt > 0:
                                for _, r in winners.iterrows():
                                    win_coins = r['amount'] * HOUSE_ODDS
                                    profit_map[r['player']] += win_coins
                                    # 注意：PVE模式下，系统直接发钱，不需要计算输家的钱
                            else:
                                logs.append("   💤 庄家通吃")

                # 更新金库
                for p, val in profit_map.items():
                    data["vault"][p] = data["vault"].get(p, 0) + val
                    if val > 0: logs.append(f"🎉 {p} +{val:.1f}")
                
                data["round"] += 1
                data["bets"] = []
                data["logs"].extend(logs)
                data["is_locked"] = False
                save_data(data)
                st.success("结算完成")
                time.sleep(1)
                st.rerun()

    # ----------------------------------
    #  场景 B: 玩家界面
    # ----------------------------------
    else:
        # 资产计算
        my_bets = [b for b in data["bets"] if b["player"] == user_id]
        used = sum(b["amount"] for b in my_bets)
        remaining = current_salary - used
        my_mkts = set(b['market'] for b in my_bets)
        
        c1, c2, c3 = st.columns(3)
        c1.metric("💰 余额", remaining)
        c2.metric("🏦 金库", f"{data['vault'].get(user_id, 0):.1f}")
        
        # 状态指示灯
        status_color = "off"
        if len(my_mkts) >= MIN_MARKET_COUNT:
            c3.success(f"✅ 盘口达标 ({len(my_mkts)}/{MIN_MARKET_COUNT})")
        else:
            c3.warning(f"⚠️ 盘口不足 ({len(my_mkts)}/{MIN_MARKET_COUNT})")

        st.divider()

        if data["is_locked"]:
            st.error("🔒 管理员已封盘")
        else:
            with st.container(border=True):
                # 选择盘口
                m_choice = st.selectbox("选择竞猜项目", list(MARKET_CONFIG.keys()))
                m_info = MARKET_CONFIG[m_choice]
                
                # 显示赔率类型提示
                if m_info["type"] == "PVE":
                    st.caption(f"🏦 **庄家盘** (固定赔率 {HOUSE_ODDS}倍) - 无论别人怎么买，中了就赔！")
                else:
                    st.caption("⚔️ **对战盘** (动态赔率) - 赢家瓜分输家的筹码")

                # 选择选项
                c_opt, c_amt = st.columns([2, 1])
                user_pick = c_opt.radio("你的预测", m_info["options"], horizontal=True)
                
                # 输入金额
                max_val = min(remaining, MAX_BET_LIMIT)
                if max_val < MIN_BET_LIMIT:
                    c_amt.number_input("余额不足", disabled=True, value=0)
                    can_bet = False
                else:
                    amt = c_amt.number_input("金额", MIN_BET_LIMIT, max_val, step=50)
                    can_bet = True
                
                if st.button("提交下注 🚀", disabled=not can_bet, use_container_width=True, type="primary"):
                    data["bets"].append({
                        "player": user_id, 
                        "market": m_choice,
                        "choice": user_pick, 
                        "amount": int(amt),
                        "timestamp": time.time()
                    })
                    save_data(data)
                    st.success("下注成功")
                    time.sleep(0.5)
                    st.rerun()
        
        if my_bets:
            st.caption("我的注单:")
            st.dataframe(pd.DataFrame(my_bets)[["market", "choice", "amount"]], use_container_width=True, hide_index=True)

    # ----------------------------------
    #  通用显示
    # ----------------------------------
    st.divider()
    st.subheader("🏆 排行榜")
    rank_data = {k:v for k,v in data["vault"].items() if k != ADMIN_USERNAME}
    if rank_data:
        df = pd.DataFrame(list(rank_data.items()), columns=["玩家", "金库"])
        df = df.sort_values("金库", ascending=False).reset_index(drop=True)
        df.index += 1
        st.dataframe(df, use_container_width=True)
    
    with st.expander("📜 比赛日志"):
        for l in reversed(data["logs"]):
            st.text(l)

# 入口
if "current_user" not in st.session_state:
    st.session_state.current_user = None

if st.session_state.current_user is None:
    login_page()
else:
    main_app()