import streamlit as st
import pandas as pd
import json
import os
import time

# ==========================================
# ⚙️ 规则配置区 (已更新限制)
# ==========================================
ADMIN_PASSWORD = "888"   # 管理员密码
DB_FILE = "game_data.json"

# --- 核心数值限制 ---
MIN_BET_LIMIT = 100      # 单注最小金额
MAX_BET_LIMIT = 500      # 单注最大金额
MIN_MARKET_COUNT = 2     # 每人至少参与几个盘口

# 固定的盘口和选项
MARKET_CONFIG = {
    "🏆 谁赢 (胜负)": ["蓝方 (A队)", "红方 (B队)"],
    "🩸 一血": ["蓝方 (A队)", "红方 (B队)"],
    "🏰 一塔": ["蓝方 (A队)", "红方 (B队)"],
    "💀 人头数": ["单", "双"],
    "⏳ 对局时长": ["大于等于12min", "小于12min"]
}

DEFAULT_PLAYERS = ["孙尚香", "孙权", "孙策", "孙悟空"]
SALARY_MAP = {"1": 1000, "2": 1000, "3": 2000}

# ==========================================
# 🛠️ 核心函数
# ==========================================
def load_data():
    if not os.path.exists(DB_FILE):
        data = {
            "round": 1,
            "vault": {p: 0.0 for p in DEFAULT_PLAYERS},
            "bets": [],
            "logs": [],
            "players": DEFAULT_PLAYERS,
            "is_locked": False
        }
        save_data(data)
        return data
    with open(DB_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def save_data(data):
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

# ==========================================
# 🎨 页面UI
# ==========================================
st.set_page_config(page_title="峡谷预测家", page_icon="⚔️", layout="wide")
st.title("⚔️ 峡谷预测家")

if 'admin_unlocked' not in st.session_state:
    st.session_state.admin_unlocked = False

data = load_data()
current_round = str(data["round"])
current_salary = SALARY_MAP.get(current_round, 2000)

# ------------------------------------------
# 👤 侧边栏：登录
# ------------------------------------------
with st.sidebar:
    st.header("👤 身份选择")
    identity_options = data["players"] + ["🔧 管理员入口"]
    user_selection = st.selectbox("你是谁？", identity_options)
    
    is_admin_mode = False
    
    if user_selection == "🔧 管理员入口":
        st.divider()
        if not st.session_state.admin_unlocked:
            pwd = st.text_input("管理员密码", type="password")
            if pwd == ADMIN_PASSWORD:
                st.session_state.admin_unlocked = True
                st.rerun()
            elif pwd:
                st.error("密码错误")
        
        if st.session_state.admin_unlocked:
            is_admin_mode = True
            st.success("🟢 管理员已授权")
            if st.button("🔒 退出"):
                st.session_state.admin_unlocked = False
                st.rerun()
    else:
        st.session_state.admin_unlocked = False
        user_id = user_selection

    st.divider()
    if st.button("🔄 刷新数据"):
        st.rerun()

# ------------------------------------------
# 🎮 场景 A：玩家下注界面
# ------------------------------------------
if not is_admin_mode:
    if user_selection == "🔧 管理员入口":
        st.info("👋 请输入密码以进入管理后台。")
        st.stop()

    # --- 1. 顶部状态栏 ---
    st.subheader(f"👋 欢迎, {user_id}")
    
    # 计算当前玩家状态
    my_bets = [b for b in data["bets"] if b["player"] == user_id]
    used_amount = sum(b["amount"] for b in my_bets)
    remaining = current_salary - used_amount
    
    # 计算已玩过的盘口数量
    my_played_markets = set([b['market'] for b in my_bets])
    played_count = len(my_played_markets)
    is_qualified = played_count >= MIN_MARKET_COUNT

    col1, col2, col3 = st.columns(3)
    col1.metric("💰 本局剩余", f"{remaining}", help=f"总补贴: {current_salary}")
    col2.metric("🏦 我的总分", f"{data['vault'].get(user_id, 0):.1f}")
    col3.metric("🚩 当前对局", f"第 {current_round} 局")
    
    # 显示合规状态警告
    if not is_qualified:
        st.warning(f"⚠️ 任务未完成：当前参与 {played_count} 个盘口，还需 {MIN_MARKET_COUNT - played_count} 个！")
    else:
        st.success(f"✅ 任务达标：已参与 {played_count} 个盘口 (>=2)")

    st.divider()

    # --- 2. 下注表单 ---
    st.subheader("📝 提交预测")
    
    if data["is_locked"]:
        st.warning("🛑 管理员已封盘，停止下注！")
    else:
        with st.container(border=True):
            # 规则提示
            st.caption(f"📜 规则：单注 {MIN_BET_LIMIT}~{MAX_BET_LIMIT} 分 | 至少玩 {MIN_MARKET_COUNT} 个不同盘口")
            
            # Step 1: 选盘口
            market_choice = st.selectbox("Step 1: 选择竞猜项目", list(MARKET_CONFIG.keys()))
            valid_options = MARKET_CONFIG[market_choice]
            
            # Step 2: 选结果
            col_opt, col_amt = st.columns([2, 1])
            with col_opt:
                user_choice = st.radio("Step 2: 你的预测", valid_options, horizontal=True)
            
            # Step 3: 输入金额 (自动限制范围)
            # 计算当前允许的最大值：不能超过余额，也不能超过单注上限
            current_max_bet = min(remaining, MAX_BET_LIMIT)
            
            with col_amt:
                if current_max_bet < MIN_BET_LIMIT:
                     st.number_input("余额不足无法下注", disabled=True, value=0)
                     st.error(f"余额不足 {MIN_BET_LIMIT}")
                     can_bet = False
                else:
                    amount = st.number_input(
                        f"Step 3: 金额 ({MIN_BET_LIMIT}-{MAX_BET_LIMIT})", 
                        min_value=MIN_BET_LIMIT, 
                        max_value=current_max_bet, 
                        step=50,
                        value=MIN_BET_LIMIT
                    )
                    can_bet = True
            
            # 提交
            if st.button("确认提交 ✅", use_container_width=True, type="primary", disabled=not can_bet):
                if not can_bet:
                    st.error("无法下注")
                else:
                    new_bet = {
                        "player": user_id,
                        "market": market_choice,
                        "choice": user_choice,
                        "amount": int(amount),
                        "timestamp": time.time()
                    }
                    data["bets"].append(new_bet)
                    save_data(data)
                    st.success(f"成功下注：{market_choice} - {user_choice} ({amount})")
                    time.sleep(0.5)
                    st.rerun()

    # --- 3. 我的注单 ---
    if my_bets:
        st.markdown("---")
        st.caption("🧾 本局已下注单")
        st.dataframe(pd.DataFrame(my_bets)[["market", "choice", "amount"]], use_container_width=True, hide_index=True)

# ------------------------------------------
# 🔧 场景 B：管理员后台
# ------------------------------------------
else:
    st.error("🔧 管理员控制台")
    
    # 封盘/删档
    col1, col2 = st.columns([1, 1])
    with col1:
        if st.button("🛑 封盘 / 解锁", type="primary" if not data["is_locked"] else "secondary"):
            data["is_locked"] = not data["is_locked"]
            save_data(data)
            st.rerun()
        st.caption(f"当前状态: {'🔒 已封盘' if data['is_locked'] else '🟢 开放中'}")
    
    with col2:
        if st.button("🗑️ 删档重置 (慎用)"):
            if os.path.exists(DB_FILE): os.remove(DB_FILE)
            st.rerun()

    st.divider()
    
    # --- 📊 合规性检查面板 (新增) ---
    st.subheader("👮 下注合规监控")
    if data["bets"]:
        df = pd.DataFrame(data["bets"])
        
        # 统计每人的消费和盘口数
        player_stats = []
        for p in data["players"]:
            p_bets = df[df['player'] == p]
            spent = p_bets['amount'].sum() if not p_bets.empty else 0
            # 统计参与了几个不同的盘口
            unique_markets = p_bets['market'].nunique() if not p_bets.empty else 0
            
            status = "✅ 合规"
            if unique_markets < MIN_MARKET_COUNT:
                status = f"❌ 盘口少于{MIN_MARKET_COUNT}"
            elif spent != current_salary:
                # 提示是否花完工资，虽然不是硬性要求必须花完，但最好提醒
                status += " (工资未花完)" 
                
            player_stats.append({
                "玩家": p,
                "已用金额": spent,
                "剩余金额": current_salary - spent,
                "参与盘口数": unique_markets,
                "状态": status
            })
            
        stats_df = pd.DataFrame(player_stats)
        
        # 使用样式高亮不合规的行 (Streamlit dataframe 简单展示)
        st.dataframe(stats_df, hide_index=True, use_container_width=True)
        
        with st.expander("查看详细注单"):
            st.dataframe(df, use_container_width=True)
    else:
        st.info("⏳ 等待玩家下注...")

    st.divider()

    # --- ⚖️ 结算区 ---
    st.subheader("⚖️ 比赛结算")
    
    with st.form("settle_form"):
        st.markdown("请根据比赛结果选择正确选项：")
        settlement_results = {}
        cols = st.columns(3)
        for idx, (market, options) in enumerate(MARKET_CONFIG.items()):
            with cols[idx % 3]:
                val = st.selectbox(f"{market}", options, key=f"settle_{idx}")
                settlement_results[market] = val
        
        st.markdown("")
        if st.form_submit_button("💰 开始结算", type="primary", use_container_width=True):
            # 结算逻辑
            logs = [f"=== 第 {current_round} 局结算报告 ==="]
            round_profit = {p: 0.0 for p in data["players"]}
            bets_df = pd.DataFrame(data["bets"])
            
            if not bets_df.empty:
                for market, correct_option in settlement_results.items():
                    market_bets = bets_df[bets_df['market'] == market]
                    total_pool = market_bets['amount'].sum()
                    winners = market_bets[market_bets['choice'] == correct_option]
                    win_pool = winners['amount'].sum()
                    
                    logs.append(f"📌 [{market}] 结果: {correct_option}")
                    
                    if win_pool > 0:
                        ratio = total_pool / win_pool
                        logs.append(f"   📈 赔率: {ratio:.2f} 倍 (总池 {total_pool})")
                        for _, row in winners.iterrows():
                            round_profit[row['player']] += row['amount'] * ratio
                    elif total_pool > 0:
                        logs.append("   💀 无人猜中，奖池销毁")
                    else:
                        pass # 无人玩此盘口
            
            # 更新金库
            for p, val in round_profit.items():
                data["vault"][p] = data["vault"].get(p, 0) + val
                if val > 0:
                    logs.append(f"🎉 {p} 赢得: {val:.1f}")
            
            data["logs"].extend(logs)
            data["round"] += 1
            data["bets"] = []
            data["is_locked"] = False
            save_data(data)
            st.success("结算完成！")
            time.sleep(2)
            st.rerun()

# ------------------------------------------
# 🏆 通用：排行榜
# ------------------------------------------
st.divider()
st.subheader("🏆 实时排行榜")
if data["vault"]:
    v_df = pd.DataFrame(list(data["vault"].items()), columns=["玩家", "金库总分"])
    v_df = v_df.sort_values("金库总分", ascending=False).reset_index(drop=True)
    v_df.index += 1
    st.dataframe(v_df, use_container_width=True)

with st.expander("📜 历史结算日志"):
    for l in reversed(data["logs"]):
        st.text(l)
