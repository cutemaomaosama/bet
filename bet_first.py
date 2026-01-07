import streamlit as st
import pandas as pd
import json
import os
import time

# ==========================================
# ⚙️ 配置区
# ==========================================
ADMIN_PASSWORD = "888"  # 管理员密码
DB_FILE = "game_data.json"

# 定义固定的盘口和选项 (根据您的要求严格定制)
MARKET_CONFIG = {
    "🏆 谁赢 (胜负)": ["蓝方 (A队)", "红方 (B队)"],
    "🩸 一血": ["蓝方 (A队)", "红方 (B队)"],
    "pj 🏰 一塔": ["蓝方 (A队)", "红方 (B队)"], # 加点emoji好辨认
    "💀 人头数": ["单", "双"],
    "⏳ 对局时长": ["大于等于12min", "小于12min"]
}

DEFAULT_PLAYERS = ["玩家A", "玩家B", "玩家C", "玩家D"]
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
st.set_page_config(page_title="峡谷预测家Pro", page_icon="⚔️", layout="wide")
st.title("⚔️ 峡谷预测家 Pro (固定盘口版)")

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
    
    # 管理员验证逻辑
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
        st.session_state.admin_unlocked = False # 切换回玩家时自动上锁
        user_id = user_selection

    st.divider()
    if st.button("🔄 刷新数据 (同步状态)"):
        st.rerun()

# ------------------------------------------
# 🎮 场景 A：玩家下注界面
# ------------------------------------------
if not is_admin_mode:
    if user_selection == "🔧 管理员入口":
        st.info("👋 请输入密码以进入管理后台。")
        st.stop()

    # 顶部信息栏
    st.subheader(f"👋 欢迎, {user_id}")
    c1, c2, c3 = st.columns(3)
    c1.metric("💰 本局筹码", current_salary, help="单次最少100，最多500")
    c2.metric("🏦 我的积分", f"{data['vault'].get(user_id, 0):.1f}")
    c3.metric("🚩 当前对局", f"第 {current_round} 局")
    
    st.divider()

    # 下注表单
    st.subheader("📝 提交预测")
    
    if data["is_locked"]:
        st.warning("🛑 管理员已封盘，停止下注！")
    else:
        # 计算余额
        my_bets = [b for b in data["bets"] if b["player"] == user_id]
        used = sum(b["amount"] for b in my_bets)
        remaining = current_salary - used
        
        st.info(f"剩余额度: **{remaining}** / {current_salary}")
        
        with st.container(border=True):
            # 1. 选择盘口
            market_choice = st.selectbox("Step 1: 选择竞猜项目", list(MARKET_CONFIG.keys()))
            
            # 2. 获取该盘口的固定选项
            valid_options = MARKET_CONFIG[market_choice]
            
            # 3. 显示选项 (使用单选按钮，手机上更好点)
            col_opt, col_amt = st.columns([2, 1])
            with col_opt:
                user_choice = st.radio("Step 2: 你的预测", valid_options, horizontal=True)
            with col_amt:
                amount = st.number_input("Step 3: 下注金额", min_value=0, max_value=int(remaining) if remaining > 0 else 0, step=50)
            
            # 提交按钮
            if st.button("确认提交 ✅", use_container_width=True, type="primary"):
                if amount <= 0:
                    st.toast("⚠️ 金额必须大于 0")
                elif amount > remaining:
                    st.toast("⚠️ 余额不足！")
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

    # 显示我的注单
    if my_bets:
        st.markdown("---")
        st.caption("🧾 本局已下注单")
        st.dataframe(pd.DataFrame(my_bets)[["market", "choice", "amount"]], use_container_width=True, hide_index=True)

# ------------------------------------------
# 🔧 场景 B：管理员后台
# ------------------------------------------
else:
    st.error("🔧 管理员控制台")
    
    # 控制区
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
    
    # 监控区
    st.subheader("📊 下注监控")
    if data["bets"]:
        df = pd.DataFrame(data["bets"])
        # 资金消耗统计
        usage = df.groupby("player")["amount"].sum().reset_index()
        usage["剩余"] = current_salary - usage["amount"]
        st.dataframe(usage, hide_index=True)
        
        with st.expander("查看所有注单详情"):
            st.dataframe(df, use_container_width=True)
    else:
        st.info("⏳ 等待玩家下注...")

    st.divider()

    # 结算区 (动态生成)
    st.subheader("⚖️ 比赛结算")
    
    with st.form("settle_form"):
        st.markdown("请根据比赛结果选择正确选项：")
        
        # 动态生成所有盘口的结算下拉框
        settlement_results = {}
        cols = st.columns(3) # 每行显示3个
        
        for idx, (market, options) in enumerate(MARKET_CONFIG.items()):
            with cols[idx % 3]:
                # 默认设为 None，强迫管理员确认，或者默认第一个
                val = st.selectbox(f"{market}", options, key=f"settle_{idx}")
                settlement_results[market] = val
        
        st.markdown("")
        if st.form_submit_button("💰 开始结算", type="primary", use_container_width=True):
            logs = [f"=== 第 {current_round} 局结算报告 ==="]
            round_profit = {p: 0.0 for p in data["players"]}
            bets_df = pd.DataFrame(data["bets"])
            
            if not bets_df.empty:
                for market, correct_option in settlement_results.items():
                    # 筛选该盘口的所有注单
                    market_bets = bets_df[bets_df['market'] == market]
                    total_pool = market_bets['amount'].sum()
                    
                    # 筛选赢家
                    winners = market_bets[market_bets['choice'] == correct_option]
                    win_pool = winners['amount'].sum()
                    
                    logs.append(f"📌 [{market}] 结果: {correct_option}")
                    logs.append(f"   总池: {total_pool} | 赢家池: {win_pool}")
                    
                    if win_pool > 0:
                        ratio = total_pool / win_pool
                        logs.append(f"   📈 赔率: {ratio:.2f} 倍")
                        # 分钱
                        for _, row in winners.iterrows():
                            profit = row['amount'] * ratio
                            round_profit[row['player']] += profit
                    elif total_pool > 0:
                        logs.append("   💀 无人猜中，奖池销毁")
                    else:
                        logs.append("   💤 无人参与")
                    logs.append("-" * 20)

            # 更新金库
            for p, val in round_profit.items():
                data["vault"][p] = data["vault"].get(p, 0) + val
                if val > 0:
                    logs.append(f"🎉 {p} 赢得: {val:.1f}")
            
            # 进入下一局
            data["logs"].extend(logs)
            data["round"] += 1
            data["bets"] = []
            data["is_locked"] = False
            save_data(data)
            st.success("结算完成！进入下一局。")
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