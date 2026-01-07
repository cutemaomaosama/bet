import streamlit as st
import pandas as pd
import json
import os
import time

# === 配置文件路径 ===
# 使用本地文件作为简易数据库，实现多设备数据同步
DB_FILE = "game_data.json"

# === 初始默认配置 ===
DEFAULT_PLAYERS = ["玩家A", "玩家B", "玩家C", "玩家D"]
SALARY_MAP = {"1": 1000, "2": 1000, "3": 2000}

# === 数据读写函数 ===
def load_data():
    if not os.path.exists(DB_FILE):
        # 初始化数据库
        data = {
            "round": 1,
            "vault": {p: 0.0 for p in DEFAULT_PLAYERS}, # 金库
            "bets": [], # 当前局下注记录
            "logs": [], # 历史日志
            "players": DEFAULT_PLAYERS,
            "is_locked": False # 是否封盘
        }
        save_data(data)
        return data
    with open(DB_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def save_data(data):
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

# === 页面设置 ===
st.set_page_config(page_title="峡谷预测家Pro", page_icon="🎮", layout="wide")
st.title("🏆 峡谷预测家 Pro")

# 加载数据
data = load_data()
current_round = str(data["round"])
current_salary = SALARY_MAP.get(current_round, 2000)

# === 侧边栏：身份选择 ===
with st.sidebar:
    st.header("👤 身份登录")
    # 合并管理员和玩家列表
    identity_options = ["管理员"] + data["players"]
    user_id = st.selectbox("你是谁？", identity_options)
    
    st.divider()
    if st.button("🔄 刷新数据 (点我同步)"):
        st.rerun()

# ==================================================
#  场景 A：玩家界面 (Player View)
# ==================================================
if user_id != "管理员":
    # 1. 个人资产展示
    st.subheader(f"👋 欢迎, {user_id}")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("💰 本局工资 (筹码)", f"{current_salary}")
    with col2:
        my_vault = data["vault"].get(user_id, 0)
        st.metric("🏦 我的小金库", f"{my_vault:.2f}")
    with col3:
        st.metric("🏁 当前局数", f"第 {current_round} 局")

    st.divider()

    # 2. 下注区域
    st.subheader("📝 提交下注")
    
    if data["is_locked"]:
        st.warning("🚫 管理员已封盘，无法下注！安心看比赛吧。")
    else:
        # 计算已用额度
        my_bets = [b for b in data["bets"] if b["player"] == user_id]
        used_amount = sum(b["amount"] for b in my_bets)
        remaining = current_salary - used_amount
        
        st.info(f"本局剩余额度: **{remaining}**")

        with st.form("bet_form"):
            c1, c2, c3 = st.columns(3)
            with c1:
                market = st.selectbox("选择盘口", ["胜负", "单双", "MVP位置", "一血", "一塔"])
            with c2:
                # 根据盘口智能提示选项，但也允许自由输入
                options_map = {
                    "胜负": ["红方胜", "蓝方胜"],
                    "单双": ["单数", "双数"],
                    "MVP位置": ["上单", "打野", "中单", "射手", "辅助"]
                }
                suggestion = options_map.get(market, [])
                choice = st.text_input("下注内容 (或手动输入)", placeholder="如: 红方胜")
                if suggestion:
                    st.caption(f"推荐选项: {', '.join(suggestion)}")
            with c3:
                amount = st.number_input("下注金额", min_value=0, max_value=int(remaining), step=10)
            
            submitted = st.form_submit_button("确认下注 🚀")
            
            if submitted:
                if amount <= 0:
                    st.error("金额必须大于0")
                elif not choice:
                    st.error("请输入下注内容")
                elif amount > remaining:
                    st.error("余额不足！")
                else:
                    new_bet = {
                        "player": user_id,
                        "market": market,
                        "choice": choice.strip(),
                        "amount": int(amount),
                        "timestamp": time.time()
                    }
                    data["bets"].append(new_bet)
                    save_data(data)
                    st.success("下注成功！")
                    time.sleep(1)
                    st.rerun()

    # 3. 我的下注记录
    if my_bets:
        st.subheader("🧾 我的本局注单")
        df_my = pd.DataFrame(my_bets)[["market", "choice", "amount"]]
        st.dataframe(df_my, use_container_width=True)

# ==================================================
#  场景 B：管理员界面 (Admin View)
# ==================================================
else:
    st.warning("🔧 管理员模式")
    
    # 1. 游戏控制
    c1, c2, c3 = st.columns(3)
    with c1:
        if st.button("🛑 封盘 / 解锁"):
            data["is_locked"] = not data["is_locked"]
            save_data(data)
            st.rerun()
        st.caption(f"当前状态: {'🔒 已封盘' if data['is_locked'] else '🟢 开放中'}")
        
    with c3:
        if st.button("⚠️ 重置游戏 (慎点)", type="primary"):
            if os.path.exists(DB_FILE):
                os.remove(DB_FILE)
            st.rerun()

    st.divider()

    # 2. 监控所有下注
    st.subheader("📊 全员下注监控")
    if data["bets"]:
        all_bets_df = pd.DataFrame(data["bets"])
        # 透视表：看每个人剩多少钱没花
        summary = all_bets_df.groupby("player")["amount"].sum().reset_index()
        summary["剩余工资"] = current_salary - summary["amount"]
        
        col_a, col_b = st.columns([1, 2])
        with col_a:
            st.write("资金消耗概览:")
            st.dataframe(summary, hide_index=True)
        with col_b:
            st.write("详细注单:")
            st.dataframe(all_bets_df[["player", "market", "choice", "amount"]], hide_index=True, use_container_width=True)
    else:
        st.info("暂无下注数据")

    # 3. 结算区域
    st.divider()
    st.subheader("⚖️ 比赛结算")
    
    with st.form("settle_form"):
        col1, col2, col3 = st.columns(3)
        res_winner = col1.selectbox("胜负结果", ["红方胜", "蓝方胜"])
        res_oddeven = col2.selectbox("击杀单双", ["单数", "双数"])
        res_mvp = col3.selectbox("MVP位置", ["上单", "打野", "中单", "射手", "辅助"])
        
        # 允许管理员手动添加额外结果
        extra_key = st.text_input("额外盘口名 (选填, 如'一血')", placeholder="对应玩家下注的盘口名")
        extra_val = st.text_input("额外结果 (选填)", placeholder="对应玩家下注的选项")

        confirm_settle = st.form_submit_button("💰 开始结算")
        
        if confirm_settle:
            results_dict = {
                "胜负": res_winner,
                "单双": res_oddeven,
                "MVP位置": res_mvp
            }
            if extra_key and extra_val:
                results_dict[extra_key] = extra_val
            
            logs = []
            logs.append(f"=== 第 {current_round} 局结算 ===")
            
            # 读取最新数据防止冲突
            data = load_data()
            bets_df = pd.DataFrame(data["bets"])
            round_profit = {p: 0.0 for p in data["players"]}

            if not bets_df.empty:
                markets = bets_df['market'].unique()
                for m in markets:
                    correct = results_dict.get(m)
                    if not correct:
                        logs.append(f"⚠️ 跳过盘口 [{m}] (未输入结果)")
                        continue
                    
                    market_bets = bets_df[bets_df['market'] == m]
                    total_pool = market_bets['amount'].sum()
                    winner_bets = market_bets[market_bets['choice'] == correct]
                    winner_pool = winner_bets['amount'].sum()
                    
                    logs.append(f"[{m}] 结果: {correct} | 总池: {total_pool}")
                    
                    if winner_pool > 0:
                        ratio = total_pool / winner_pool
                        logs.append(f"  -> 赔率: {ratio:.2f}倍")
                        for _, row in winner_bets.iterrows():
                            p = row['player']
                            amt = row['amount']
                            win = amt * ratio
                            round_profit[p] += win
                    else:
                        logs.append("  -> 💀 无人猜中")

            # 更新金库
            for p, prof in round_profit.items():
                data["vault"][p] = data["vault"].get(p, 0) + prof
                logs.append(f"{p} 收益: +{prof:.1f}")
            
            # 保存并进入下一局
            data["logs"].extend(logs)
            data["round"] += 1
            data["bets"] = [] # 清空注单
            data["is_locked"] = False # 解锁
            save_data(data)
            st.success("结算完成！")
            time.sleep(2)
            st.rerun()

# ==================================================
#  通用：排行榜 (所有人可见)
# ==================================================
st.divider()
st.subheader("🏆 实时金库排行榜")
vault_df = pd.DataFrame(list(data["vault"].items()), columns=["玩家", "金库总分"])
vault_df = vault_df.sort_values("金库总分", ascending=False).reset_index(drop=True)
vault_df.index += 1
st.dataframe(vault_df, use_container_width=True)

# 历史日志折叠
with st.expander("📜 历史结算记录"):
    for log in reversed(data["logs"]):
        st.text(log)