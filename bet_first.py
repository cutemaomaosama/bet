import streamlit as st
import pandas as pd
import json
import os
import time

# ==========================================
# ⚙️ 全局配置 (请在此处修改名单)
# ==========================================
DB_FILE = "game_data.json"
ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "888"

# --- 游戏数值 ---
MIN_BET_LIMIT = 100
MAX_BET_LIMIT = 500
MIN_MARKET_COUNT = 2
HOUSE_ODDS = 2
SALARY_MAP = {"1": 1000, "2": 1000, "3": 2000}

# --- 📅 队伍名称配置 ---
# 用于胜负、一血、一塔的选项
TEAM_A_NAME = "温鹏祥队"
TEAM_B_NAME = "何怡君队"
TEAMS_OPTIONS = [TEAM_A_NAME, TEAM_B_NAME]

# --- 🌟 MVP 选手名单配置 (关键修改) ---
# 请在这里填入每一局的 10 个具体队员 ID
MVP_LISTS = {
    "1": [
        "温鹏祥队-上单：童颜", "温鹏祥队-打野：晏晨熙", "温鹏祥队-中单：温鹏祥", "温鹏祥队-射手：李浩", "温鹏祥队-辅助：郝奕博",
        "何怡君队-上单：杨蔚庆", "何怡君队-打野：夏川棋", "何怡君队-中单：吴马倩男", "何怡君队-射手：贺江舟", "何怡君队-辅助：丁亮"
    ],
    "2": [
        "温鹏祥队-上单：乔榛", "温鹏祥队-打野：左天白", "温鹏祥队-中单：张益帆", "温鹏祥队-射手：阮胤广", "温鹏祥队-辅助：黄俊",
        "何怡君队-上单：李思鹏", "何怡君队-打野：李宝琪", "何怡君队-中单：卓慧玲", "何怡君队-射手：何怡君", "何怡君队-辅助：庞汉雄"
    ],
    "3": [
        # 假设第三局有替补，可以在这里换人
        "温鹏祥队-上单：阮胤广", "温鹏祥队-打野：左天白", "温鹏祥队-中单：张益帆", "温鹏祥队-射手：温鹏祥", "温鹏祥队-辅助：黄俊",
        "何怡君队-上单：李思鹏", "何怡君队-打野：李宝琪", "何怡君队-中单：卓慧玲", "何怡君队-射手：何怡君", "何怡君队-辅助：庞汉雄"
    ]
}

# 默认名单 (防止报错)
DEFAULT_MVP_LIST = [f"选手{i}" for i in range(1, 11)]

# ==========================================
# 🎨 规则展示组件 (新增)
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
# 🛠️ 核心逻辑函数
# ==========================================
def get_market_config(round_str):
    """根据局数生成盘口，MVP名单从配置中读取"""
    
    # 获取本局的10人名单
    current_mvp_options = MVP_LISTS.get(round_str, DEFAULT_MVP_LIST)
    
    return {
        # PVP
        "🏆 胜方": {
            "type": "PVP", "options": TEAMS_OPTIONS, "ui": "radio"
        },
        "🌟 胜方MVP": {
            "type": "PVP", "options": current_mvp_options, "ui": "select" 
        },
        # PVE
        "🩸 一血": {
            "type": "PVE", "options": TEAMS_OPTIONS, "ui": "radio"
        },
        "🏰 一塔": {
            "type": "PVE", "options": TEAMS_OPTIONS, "ui": "radio"
        },
        "💀 人头数": {
            "type": "PVE", "options": ["单", "双"], "ui": "radio"
        },
        "⏳ 对局时长": {
            "type": "PVE", "options": ["小于16min", "大于等于16min"], "ui": "radio"
        }
    }

def load_data():
    if not os.path.exists(DB_FILE):
        data = {
            "users": {ADMIN_USERNAME: ADMIN_PASSWORD},
            "round": 1,
            "vault": {},
            "bets": [],
            "logs": [],
            "is_locked": False,
            "reg_closed": False,  # 新增：注册锁
            "match_history": [],  # 新增：比赛胜者记录 ["温鹏祥队", "何怡君队"]
            "game_over": False    # 新增：比赛是否结束
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
# 🔐 登录/注册页面
# ==========================================
def login_page():
    st.set_page_config(page_title="策划杯竞猜", page_icon="⚔️", layout="wide")
    st.title("⚔️ 策划杯竞猜 ")
    
    data = load_data()
    
    # 如果比赛已结束
    if data.get("game_over", False):
        st.error("🏁 比赛已全部结束！无法登录，请联系管理员查看最终榜单。")
        # 这里为了查看榜单，可以允许登录，但下文会限制操作。
        # 暂时保持正常登录流程，但在主界面拦截。
    
    tab1, tab2 = st.tabs(["🔑 登录", "📝 注册新账号"])
    
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
        # 检查注册锁
        if data.get("reg_closed", False):
            st.error("🚫 比赛已经开始 (第一局已封盘)，停止新用户注册！")
            st.caption("迟到的朋友请围观。")
        else:
            with st.form("reg"):
                nu = st.text_input("新账号ID")
                np = st.text_input("密码", type="password")
                if st.form_submit_button("注册并登录"):
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
    st.set_page_config(page_title="策划杯竞猜", page_icon="⚔️", layout="wide")
    user = st.session_state.current_user
    data = load_data()
    is_admin = (user == ADMIN_USERNAME)
    
    # 获取状态
    curr_round_num = data["round"]
    curr_round_str = str(curr_round_num)
    is_game_over = data.get("game_over", False)
    
    # 如果没结束，获取工资；如果结束了，工资为0
    salary = SALARY_MAP.get(curr_round_str, 0) if not is_game_over else 0
    MARKET_CONFIG = get_market_config(curr_round_str)

    # --- 侧边栏 ---
    with st.sidebar:
        st.header(f"👤 {user}")
        if st.button("🚪 退出"):
            st.session_state.current_user = None
            st.rerun()
        st.divider()
        if st.button("🔄 刷新"): st.rerun()

    # --- 顶部标题 ---
    if is_game_over:
        st.title("🏁 比赛已结束 (Game Over)")
        winner_history = data.get("match_history", [])
        if len(winner_history) >= 2 and winner_history[0] == winner_history[1]:
            st.success(f"🏆 {winner_history[0]} 以 2:0 横扫获胜！无需进行第三局。")
        else:
            st.info(f"比分记录: {' - '.join(winner_history)}")
    else:
        st.title(f"⚔️ 第 {curr_round_str} 局")
        st.info(f"本局对阵: {TEAM_A_NAME} vs {TEAM_B_NAME}")

    # ------------------------------------
    #  场景 A: 管理员
    # ------------------------------------
    if is_admin:
        st.subheader("🔧 管理后台")
        c1, c2 = st.columns(2)
        with c1:
            # 封盘逻辑优化：第一局封盘时，锁注册
            btn_text = "🛑 封盘 (并锁注册)" if (curr_round_num == 1 and not data["is_locked"]) else "🛑 封盘 / 解锁"
            
            if st.button(btn_text, type="primary" if not data["is_locked"] else "secondary", disabled=is_game_over):
                new_lock_state = not data["is_locked"]
                data["is_locked"] = new_lock_state
                # 如果是第一局且执行封盘，则锁定注册
                if curr_round_num == 1 and new_lock_state:
                    data["reg_closed"] = True
                save_data(data)
                st.rerun()
            
            status_text = '🔒 已封盘' if data['is_locked'] else '🟢 开放中'
            if data.get("reg_closed"): status_text += " | 🚫 注册已关"
            st.caption(f"状态: {status_text}")
            
        with c2:
            if st.button("🗑️ 删档重置"):
                if os.path.exists(DB_FILE): os.remove(DB_FILE)
                st.session_state.current_user = None
                st.rerun()
        
        st.divider()
        
        if not is_game_over:
            # 监控
            st.subheader("👮 监控")
            if data["bets"]:
                df = pd.DataFrame(data["bets"])
                players = [u for u in data["users"] if u != ADMIN_USERNAME]
                stats = []
                for p in players:
                    pb = df[df['player'] == p]
                    spent = pb['amount'].sum() if not pb.empty else 0
                    mkts = pb['market'].nunique() if not pb.empty else 0
                    status = "✅"
                    if mkts < MIN_MARKET_COUNT: status = f"❌ 盘口少"
                    elif spent != salary: status += " (余额未清)"
                    stats.append({"玩家": p, "已花": spent, "盘口": mkts, "状态": status})
                st.dataframe(pd.DataFrame(stats), hide_index=True, use_container_width=True)
            else:
                st.info("无下注数据")

            st.divider()
            
            # 结算
            st.subheader("⚖️ 结算本局")
            with st.form("settle"):
                settle_res = {}
                cols = st.columns(3)
                idx = 0
                for m_name, cfg in MARKET_CONFIG.items():
                    with cols[idx % 3]:
                        settle_res[m_name] = st.selectbox(m_name, cfg["options"])
                    idx += 1
                
                if st.form_submit_button("💰 结算并进入下一阶段", type="primary", use_container_width=True):
                    logs = [f"=== 第 {curr_round_str} 局结算 ==="]
                    profit_map = {u: 0.0 for u in data["users"] if u != ADMIN_USERNAME}
                    bets_df = pd.DataFrame(data["bets"])
                    
                    # 1. 算钱
                    if not bets_df.empty:
                        for m_name, result in settle_res.items():
                            m_bets = bets_df[bets_df['market'] == m_name]
                            if m_bets.empty: continue
                            
                            m_type = MARKET_CONFIG[m_name]["type"]
                            winners = m_bets[m_bets['choice'] == result]
                            win_pool = winners['amount'].sum()
                            logs.append(f"[{m_name}] 结果: {result}")
                            
                            if m_type == "PVE": # 庄家
                                if win_pool > 0:
                                    for _, r in winners.iterrows():
                                        profit_map[r['player']] += r['amount'] * HOUSE_ODDS
                            else: # PVP
                                total_pool = m_bets['amount'].sum()
                                if win_pool > 0:
                                    ratio = total_pool / win_pool
                                    logs.append(f" -> 赔率 {ratio:.2f}")
                                    for _, r in winners.iterrows():
                                        profit_map[r['player']] += r['amount'] * ratio

                    # 2. 发钱
                    for p, val in profit_map.items():
                        data["vault"][p] = data["vault"].get(p, 0) + val
                        if val > 0: logs.append(f"{p} +{val:.1f}")
                    
                    # 3. 记录胜负结果 (用于BO3判断)
                    winner_team = settle_res.get("🏆 胜负")
                    # 这里假设选项是纯队名，或者是 "温鹏祥队" / "何怡君队"
                    # 如果选项是 "温鹏祥队", "何怡君队" 则直接存
                    if winner_team:
                        data["match_history"].append(winner_team)
                        logs.append(f"📌 本局胜者记录: {winner_team}")

                    # 4. 判断是否结束
                    # 如果已经打了2局，且2局胜者相同 -> 结束
                    history = data["match_history"]
                    should_end = False
                    
                    if len(history) == 2:
                        if history[0] == history[1]:
                            should_end = True
                            logs.append(f"🏁 {history[0]} 2:0 获胜，比赛提前结束！")
                    elif len(history) == 3:
                        should_end = True
                        logs.append("🏁 BO3 打满，比赛结束！")

                    # 5. 状态流转
                    data["bets"] = []
                    data["logs"].extend(logs)
                    data["is_locked"] = False
                    
                    if should_end:
                        data["game_over"] = True
                    else:
                        data["round"] += 1
                        
                    save_data(data)
                    st.success("结算完成")
                    time.sleep(2)
                    st.rerun()
        else:
            st.warning("比赛已结束，请查看最终榜单。")
            if st.button("强制重启 (清空所有状态)"):
                if os.path.exists(DB_FILE): os.remove(DB_FILE)
                st.rerun()

    # ------------------------------------
    #  场景 B: 玩家
    # ------------------------------------
    else:
        # 显示金库
        c1, c2 = st.columns(2)
        c1.metric("🏦 我的总分 ", f"{data['vault'].get(user, 0):.1f}")
        
        if is_game_over:
            c2.metric("当前状态", "🏁 已完赛")
            st.divider()
            st.success("辛苦了！比赛已结束，请查看下方最终排名。")
        else:
            # 游戏进行中
            my_bets = [b for b in data["bets"] if b["player"] == user]
            used = sum(b["amount"] for b in my_bets)
            remaining = salary - used
            my_mkts = set(b['market'] for b in my_bets)
            
            c2.metric("💰 本局剩余积分", remaining)
            
            # 状态栏
            if len(my_mkts) >= MIN_MARKET_COUNT:
                st.success(f"✅ 任务达标 ({len(my_mkts)}/{MIN_MARKET_COUNT})")
            else:
                st.warning(f"⚠️ 还需下注 {MIN_MARKET_COUNT - len(my_mkts)} 个盘口")

            st.divider()

            if data["is_locked"]:
                st.error("🔒 管理员已封盘，等待结算...")
            else:
                with st.container(border=True):
                    st.subheader("📝 提交预测")
                    m_choice = st.selectbox("项目", list(MARKET_CONFIG.keys()))
                    cfg = MARKET_CONFIG[m_choice]
                    
                    if cfg["type"] == "PVE": st.caption(f"🏦 庄家盘 (固定赔率 {HOUSE_ODDS})")
                    else: st.caption(f"⚔️ 对战盘 (动态赔率)")

                    c_opt, c_amt = st.columns([2, 1])
                    with c_opt:
                        if cfg["ui"] == "select":
                            # MVP 列表在这里显示
                            user_pick = st.selectbox("预测", cfg["options"])
                        else:
                            user_pick = st.radio("预测", cfg["options"], horizontal=True)
                    
                    with c_amt:
                        max_val = min(remaining, MAX_BET_LIMIT)
                        if max_val < MIN_BET_LIMIT:
                            st.number_input("余额不足", disabled=True, value=0)
                            can_bet = False
                        else:
                            amt = st.number_input(f"金额", MIN_BET_LIMIT, max_val, step=50)
                            can_bet = True
                    
                    if st.button("确认", disabled=not can_bet, use_container_width=True, type="primary"):
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
    #  通用：排行榜
    # ------------------------------------
    st.divider()
    st.subheader("🏆 排行榜")
    rank_data = {k:v for k,v in data["vault"].items() if k != ADMIN_USERNAME}
    if rank_data:
        df = pd.DataFrame(list(rank_data.items()), columns=["玩家", "金库"])
        df = df.sort_values("金库", ascending=False).reset_index(drop=True)
        df.index += 1
        st.dataframe(df, use_container_width=True)

    with st.expander("📜 历史日志"):
        for l in reversed(data["logs"]):
            st.text(l)

# 入口
if "current_user" not in st.session_state: st.session_state.current_user = None
if st.session_state.current_user is None: login_page()
else: main_app()