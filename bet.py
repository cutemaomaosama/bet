import streamlit as st
import pandas as pd
import json
import os
import time

# ==========================================
# ⚙️ 全局配置与盘口定义
# ==========================================
DB_FILE = "game_data.json"
ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "888"  # 管理员密码

# --- 数值规则 ---
MIN_BET_LIMIT = 100       # 单注下限
MAX_BET_LIMIT = 500       # 单注上限
MIN_MARKET_COUNT = 2      # 每人至少玩几个盘口
SALARY_MAP = {"1": 1000, "2": 1000, "3": 2000}
HOUSE_ODDS = 1.9          # 庄家盘(PVE)固定赔率

# --- 盘口构建 ---
# 1. 构建MVP的10个选项
TEAMS = ["温鹏祥队", "何怡君队"]
POSITIONS = ["上单", "打野", "中单", "射手", "辅助"]
MVP_OPTIONS = [f"{t}-{p}" for t in TEAMS for p in POSITIONS] 
# 结果示例: ['温鹏祥队-上单', '温鹏祥队-打野' ... '何怡君队-辅助']

MARKET_CONFIG = {
    # PVP: 玩家互赢 (浮动赔率)
    "🏆 胜负": {
        "type": "PVP", 
        "options": ["温鹏祥队", "何怡君队"],
        "ui": "radio" # 选项少用按钮
    },
    "🌟 胜方MVP": {
        "type": "PVP", 
        "options": MVP_OPTIONS,
        "ui": "select" # 选项多用下拉框
    },
    
    # PVE: 庄家接单 (固定赔率)
    "🩸 一血": {
        "type": "PVE", 
        "options": ["温鹏祥队", "何怡君队"],
        "ui": "radio"
    },
    "🏰 一塔": {
        "type": "PVE", 
        "options": ["温鹏祥队", "何怡君队"],
        "ui": "radio"
    },
    "⏳ 时长": {
        "type": "PVE", 
        "options": ["< 20分钟", "≥ 20分钟"], # 您可以根据版本调整这个时间
        "ui": "radio"
    }
}

# ==========================================
# 🛠️ 核心逻辑
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
# 🔐 登录注册页
# ==========================================
def login_page():
    st.title("⚔️ 峡谷预测家")
    data = load_data()
    tab1, tab2 = st.tabs(["🔑 登录", "📝 注册"])
    
    with tab1:
        with st.form("login"):
            u = st.text_input("账号")
            p = st.text_input("密码", type="password")
            if st.form_submit_button("登录", type="primary", use_container_width=True):
                users = data.get("users", {})
                if u in users and users[u] == p:
                    st.session_state.current_user = u
                    st.rerun()
                else:
                    st.error("账号或密码错误")
    
    with tab2:
        with st.form("reg"):
            nu = st.text_input("新ID")
            np = st.text_input("新密码", type="password")
            if st.form_submit_button("注册"):
                if nu in data["users"]:
                    st.error("ID已存在")
                elif not nu or not np:
                    st.warning("不能为空")
                else:
                    data["users"][nu] = np
                    if nu not in data["vault"]: data["vault"][nu] = 0.0
                    save_data(data)
                    st.session_state.current_user = nu
                    st.success("注册成功")
                    time.sleep(0.5)
                    st.rerun()

# ==========================================
# 🎮 游戏主程序
# ==========================================
def main_app():
    user = st.session_state.current_user
    data = load_data()
    is_admin = (user == ADMIN_USERNAME)
    
    curr_round = str(data["round"])
    salary = SALARY_MAP.get(curr_round, 2000)

    # 侧边栏
    with st.sidebar:
        st.header(f"👤 {user}")
        if st.button("🚪 退出"):
            st.session_state.current_user = None
            st.rerun()
        st.divider()
        if st.button("🔄 刷新数据"): st.rerun()

    st.title(f"⚔️ 第 {curr_round} 局")

    # ------------------------------------
    #  场景 A: 管理员 (Admin)
    # ------------------------------------
    if is_admin:
        st.subheader("🔧 管理后台")
        c1, c2 = st.columns(2)
        with c1:
            if st.button("🛑 封盘/解锁", type="primary" if not data["is_locked"] else "secondary"):
                data["is_locked"] = not data["is_locked"]
                save_data(data)
                st.rerun()
            st.caption(f"状态: {'🔒 已封盘' if data['is_locked'] else '🟢 下注中'}")
        with c2:
            if st.button("🗑️ 删档重置"):
                if os.path.exists(DB_FILE): os.remove(DB_FILE)
                st.session_state.current_user = None
                st.rerun()
        
        st.divider()
        st.subheader("👮 监控合规性")
        if data["bets"]:
            df = pd.DataFrame(data["bets"])
            players = [u for u in data["users"] if u != ADMIN_USERNAME]
            stats = []
            for p in players:
                pb = df[df['player'] == p]
                spent = pb['amount'].sum() if not pb.empty else 0
                mkts = pb['market'].nunique() if not pb.empty else 0
                status = "✅"
                if mkts < MIN_MARKET_COUNT: status = f"❌ 盘口少 ({mkts})"
                elif spent != salary: status += " (未花完)"
                stats.append({"玩家": p, "已花": spent, "盘口": mkts, "状态": status})
            st.dataframe(pd.DataFrame(stats), hide_index=True, use_container_width=True)
        else:
            st.info("暂无下注")

        st.divider()
        st.subheader("⚖️ 结算")
        with st.form("settle"):
            settle_res = {}
            # 动态生成结算表单
            for m_name, cfg in MARKET_CONFIG.items():
                settle_res[m_name] = st.selectbox(m_name, cfg["options"])
            
            if st.form_submit_button("💰 结算本局", type="primary", use_container_width=True):
                logs = [f"=== 第 {curr_round} 局结算 ==="]
                profit_map = {u: 0.0 for u in data["users"] if u != ADMIN_USERNAME}
                bets_df = pd.DataFrame(data["bets"])
                
                if not bets_df.empty:
                    for m_name, result in settle_res.items():
                        m_type = MARKET_CONFIG[m_name]["type"]
                        m_bets = bets_df[bets_df['market'] == m_name]
                        
                        if m_bets.empty: continue
                        
                        winners = m_bets[m_bets['choice'] == result]
                        win_pool = winners['amount'].sum()
                        
                        logs.append(f"📌 [{m_name}] 结果: {result}")
                        
                        # PVP 结算
                        if m_type == "PVP":
                            total_pool = m_bets['amount'].sum()
                            if win_pool > 0:
                                ratio = total_pool / win_pool
                                logs.append(f"   ⚔️ 奖池: {total_pool} | 赔率: {ratio:.2f}倍")
                                for _, r in winners.iterrows():
                                    profit_map[r['player']] += r['amount'] * ratio
                            else:
                                logs.append("   💀 无人猜中")
                        
                        # PVE 结算
                        else:
                            logs.append(f"   🏦 庄家盘 | 固定赔率: {HOUSE_ODDS}")
                            if win_pool > 0:
                                for _, r in winners.iterrows():
                                    profit_map[r['player']] += r['amount'] * HOUSE_ODDS
                            else:
                                logs.append("   💤 庄家通吃")

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

    # ------------------------------------
    #  场景 B: 玩家 (Player)
    # ------------------------------------
    else:
        # 资产计算
        my_bets = [b for b in data["bets"] if b["player"] == user]
        used = sum(b["amount"] for b in my_bets)
        remaining = salary - used
        my_mkts = set(b['market'] for b in my_bets)
        
        c1, c2, c3 = st.columns(3)
        c1.metric("💰 本轮剩余积分", remaining, help="必须花完")
        c2.metric("🏦 玩家总积分", f"{data['vault'].get(user, 0):.1f}")
        
        status_text = f"已玩 {len(my_mkts)}/{MIN_MARKET_COUNT} 盘口"
        if len(my_mkts) >= MIN_MARKET_COUNT:
            c3.success(f"✅ {status_text}")
        else:
            c3.error(f"❌ {status_text}")

        st.divider()

        if data["is_locked"]:
            st.error("🔒 已封盘")
        else:
            with st.container(border=True):
                # 1. 选盘口
                m_choice = st.selectbox("Step 1: 选择竞猜项目", list(MARKET_CONFIG.keys()))
                cfg = MARKET_CONFIG[m_choice]
                
                # 提示赔率类型
                if cfg["type"] == "PVE":
                    st.info(f"🏦 **庄家盘**: 只要猜中就赔 {HOUSE_ODDS} 倍")
                else:
                    st.warning(f"⚔️ **对战盘**: 赢家瓜分所有输家的钱")

                # 2. 选选项 (根据配置自动切换 UI)
                c_opt, c_amt = st.columns([2, 1])
                with c_opt:
                    if cfg["ui"] == "select":
                        # MVP用下拉框，因为有10个选项
                        user_pick = st.selectbox("Step 2: 你的预测", cfg["options"])
                    else:
                        # 其他用单选按钮
                        user_pick = st.radio("Step 2: 你的预测", cfg["options"], horizontal=True)
                
                # 3. 输入金额
                with c_amt:
                    max_val = min(remaining, MAX_BET_LIMIT)
                    if max_val < MIN_BET_LIMIT:
                        st.number_input("积分余额不足", disabled=True, value=0)
                        can_bet = False
                    else:
                        amt = st.number_input(f"积分 ({MIN_BET_LIMIT}-{MAX_BET_LIMIT})", MIN_BET_LIMIT, max_val, step=50)
                        can_bet = True
                
                # 提交
                if st.button("确认下注", disabled=not can_bet, use_container_width=True, type="primary"):
                    data["bets"].append({
                        "player": user, "market": m_choice,
                        "choice": user_pick, "amount": int(amt),
                        "timestamp": time.time()
                    })
                    save_data(data)
                    st.success("成功")
                    time.sleep(0.5)
                    st.rerun()
        
        if my_bets:
            st.caption("我的注单:")
            st.dataframe(pd.DataFrame(my_bets)[["market", "choice", "amount"]], use_container_width=True, hide_index=True)

    # ------------------------------------
    #  通用显示
    # ------------------------------------
    st.divider()
    st.subheader("🏆 排行榜")
    rank_data = {k:v for k,v in data["vault"].items() if k != ADMIN_USERNAME}
    if rank_data:
        df = pd.DataFrame(list(rank_data.items()), columns=["玩家", "总积分"])
        df = df.sort_values("总积分", ascending=False).reset_index(drop=True)
        df.index += 1
        st.dataframe(df, use_container_width=True)

    with st.expander("📜 历史日志"):
        for l in reversed(data["logs"]):
            st.text(l)

# 入口
if "current_user" not in st.session_state:
    st.session_state.current_user = None
if st.session_state.current_user is None:
    login_page()
else:
    main_app()