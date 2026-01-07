import streamlit as st
import pandas as pd

# === 页面配置 ===
st.set_page_config(page_title="峡谷预测家", page_icon="🎮", layout="centered")

# === 初始化 Session State (用于存储游戏数据) ===
if 'vault' not in st.session_state:
    # 默认玩家 (您可以修改这里)
    st.session_state.players = ["玩家A", "玩家B", "玩家C", "玩家D", "玩家E"]
    st.session_state.vault = {p: 0.0 for p in st.session_state.players} # 金库
    st.session_state.round = 1
    st.session_state.logs = [] # 历史记录

# === 侧边栏：全局控制 ===
with st.sidebar:
    st.header("⚙️ 管理员面板")
    
    # 修改玩家名单
    new_players = st.text_area("玩家名单 (用逗号分隔)", value=",".join(st.session_state.players))
    if st.button("更新玩家"):
        p_list = [p.strip() for p in new_players.split(",") if p.strip()]
        st.session_state.players = p_list
        # 初始化新玩家的金库
        for p in p_list:
            if p not in st.session_state.vault:
                st.session_state.vault[p] = 0.0
        st.success("玩家名单已更新")

    st.divider()
    
    if st.button("🔴 重置整个游戏", type="primary"):
        st.session_state.vault = {p: 0.0 for p in st.session_state.players}
        st.session_state.round = 1
        st.session_state.logs = []
        st.rerun()

# === 主界面 ===
st.title("🏆 峡谷预测家 (无庄家版)")

# 确定本局工资
salary_map = {1: 1000, 2: 1000, 3: 2000}
current_salary = salary_map.get(st.session_state.round, 2000)

st.info(f"🔥 **当前：第 {st.session_state.round} 局** | 💰 本局每人发放工资: **{current_salary}**")
st.caption("规则：工资必须花完，至少下注2个盘口，单项上限70% (第3局无上限)")

# --- 第一步：录入下注 ---
st.subheader("1️⃣ 下注录入")

# 创建一个空的 DataFrame 用于录入
# 预设一些行，方便大家填
default_data = {
    "玩家": [],
    "盘口": [],
    "选项": [],
    "金额": []
}

# 盘口定义
market_options = {
    "胜负": ["红方胜", "蓝方胜"],
    "单双": ["单数", "双数"],
    "MVP位置": ["上单", "打野", "中单", "射手", "辅助"]
}

# 使用 data_editor 进行交互式表格录入
# 这是一个非常强大的组件，类似 Excel
with st.expander("点击展开下注表格", expanded=True):
    # 构造编辑器的配置
    col_config = {
        "玩家": st.column_config.SelectboxColumn("玩家", options=st.session_state.players, required=True),
        "盘口": st.column_config.SelectboxColumn("盘口", options=list(market_options.keys()), required=True),
        "选项": st.column_config.TextColumn("选项 (填红方胜/单数/打野等)", required=True),
        "金额": st.column_config.NumberColumn("金额", min_value=0, max_value=current_salary, step=10, required=True),
    }
    
    st.markdown("👇 **请在下方表格直接添加下注数据**")
    
    # 初始化一个空的df给用户填，或者如果 session 里有缓存则读取
    if 'editor_df' not in st.session_state:
        st.session_state.editor_df = pd.DataFrame(columns=["玩家", "盘口", "选项", "金额"])

    edited_df = st.data_editor(
        st.session_state.editor_df,
        column_config=col_config,
        num_rows="dynamic", # 允许动态添加行
        use_container_width=True,
        key="bet_editor" 
    )

# --- 第二步：录入结果与结算 ---
st.subheader("2️⃣ 比赛结算")

col1, col2, col3 = st.columns(3)
with col1:
    res_winner = st.selectbox("胜负结果", ["红方胜", "蓝方胜"])
with col2:
    res_oddeven = st.selectbox("击杀单双", ["单数", "双数"])
with col3:
    res_mvp = st.selectbox("MVP位置", ["上单", "打野", "中单", "射手", "辅助"])

results = {"胜负": res_winner, "单双": res_oddeven, "MVP位置": res_mvp}

if st.button("🚀 结算本局积分", type="primary", use_container_width=True):
    if edited_df.empty:
        st.error("还没有人下注！请先在表格里添加数据。")
    else:
        # === 核心算法 ===
        current_logs = []
        round_profit = {p: 0.0 for p in st.session_state.players}
        
        # 按盘口分组计算
        markets = edited_df['盘口'].unique()
        
        for market in markets:
            correct_choice = results.get(market)
            # 筛选该盘口的所有下注
            market_bets = edited_df[edited_df['盘口'] == market]
            
            total_pool = market_bets['金额'].sum()
            winner_bets = market_bets[market_bets['选项'] == correct_choice]
            winner_pool_total = winner_bets['金额'].sum()
            
            log_msg = f"【{market}】结果: {correct_choice} | 总奖池: {total_pool} | 赢家池: {winner_pool_total}"
            current_logs.append(log_msg)
            
            if winner_pool_total > 0:
                ratio = total_pool / winner_pool_total
                current_logs.append(f"  -> 赔率系数: {ratio:.2f}倍")
                
                # 分配奖金
                for index, row in winner_bets.iterrows():
                    p_name = row['玩家']
                    winnings = row['金额'] * ratio
                    round_profit[p_name] += winnings
            else:
                current_logs.append("  -> 😱 无人猜中！奖池流局 (或被系统吞没)。")

        # 更新金库
        st.session_state.logs.append(f"--- 第 {st.session_state.round} 局结算 ---")
        st.session_state.logs.extend(current_logs)
        
        for p, profit in round_profit.items():
            st.session_state.vault[p] += profit
            
        st.success("结算完成！金库已更新。")
        st.session_state.round += 1
        # 清空下注表
        st.session_state.editor_df = pd.DataFrame(columns=["玩家", "盘口", "选项", "金额"])
        st.rerun()

# --- 第三步：排行榜展示 ---
st.divider()
st.subheader("🏆 实时金库排行榜")

# 转换金库为 DataFrame 并排序
leaderboard = pd.DataFrame(list(st.session_state.vault.items()), columns=['玩家', '金库总分'])
leaderboard = leaderboard.sort_values(by='金库总分', ascending=False).reset_index(drop=True)
leaderboard.index += 1 # 排名从1开始

st.dataframe(
    leaderboard, 
    use_container_width=True,
    column_config={
        "金库总分": st.column_config.ProgressColumn(
            "金库总分", 
            format="%.2f", 
            min_value=0, 
            max_value=max(leaderboard['金库总分'].max(), 5000)
        )
    }
)

# --- 历史日志 ---
with st.expander("查看历史结算日志"):
    for log in st.session_state.logs:
        st.text(log)