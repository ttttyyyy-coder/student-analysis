import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import re

# --- 1. 网页全局配置与美化 ---
st.set_page_config(page_title="数智教学分析看板 v3.0", layout="wide")
st.markdown("""
    <style>
    .stMetric { background: #ffffff; padding: 20px; border-radius: 12px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); border: 1px solid #f0f2f6; }
    .main { background-color: #f8f9fa; }
    </style>
""", unsafe_allow_html=True)

# --- 2. 核心逻辑：特征提取引擎 ---
def analyze_edu_engine(df):
    """头歌深度审计：提取用时、频率与时序特征"""
    stages = range(1, 11)
    results = []
    for _, row in df.iterrows():
        name, sid = row['真实姓名'], str(row['学号']).strip()
        for s in stages:
            st_col, et_col = f'第{s}关开始时间', f'第{s}关完成时间'
            if pd.notna(row.get(st_col)) and row[st_col] != '--':
                try:
                    start, end = pd.to_datetime(row[st_col]), pd.to_datetime(row[et_col])
                    dur = (end - start).total_seconds()
                    results.append({
                        '姓名': name, '学号': sid, '关卡': f'第{s}关', 
                        '用时': dur, '完成时刻': end.hour, '评测次数': row.get(f'第{s}关评测次数', 0)
                    })
                except: pass
    edu_df = pd.DataFrame(results)
    # 计算动态基准（均值与标准差）
    stats = edu_df.groupby('关卡')['用时'].agg(['mean', 'std']).reset_index()
    edu_df = edu_df.merge(stats, on='关卡')
    # 异常判定：低于均值15% 或 绝对时长 < 45s 为疑似粘贴；凌晨 1-5 点为熬夜
    edu_df['判定'] = '正常'
    edu_df.loc[(edu_df['用时'] < edu_df['mean'] * 0.15) & (edu_df['用时'] < 60), '判定'] = '疑似粘贴'
    edu_df.loc[edu_df['完成时刻'].between(1, 5), '判定'] = '深夜突击'
    return edu_df

def analyze_xxt_engine(video_df):
    """学习通深度审计：提取视频观看真实度"""
    v_names, v_data = video_df.iloc[1], video_df.iloc[4:]
    meta = []
    for i in range(6, len(v_names), 4):
        name = str(v_names[i])
        if "(" in name:
            dur = float(re.search(r'\(([\d\.]+)分钟', name).group(1))
            meta.append((name[:15], dur, i+3)) # i+3 为观看时长列
    
    xxt_list = []
    for _, row in v_data.iterrows():
        name, sid = row[0], str(row[1]).strip()
        for v_name, v_dur, col_idx in meta:
            w_str = str(row[col_idx])
            m = 0
            m_match = re.search(r'([\d\.]+)分', w_str)
            if m_match: m = float(m_match.group(1))
            ratio = (m / v_dur) * 100
            xxt_list.append({
                '姓名': name, '学号': sid, '视频': v_name, 
                '观看占比': ratio, '判定': '速刷' if ratio < 35 else '正常'
            })
    return pd.DataFrame(xxt_list)

# --- 3. 侧边栏与数据加载 ---
st.sidebar.title("🏫 教师教学审计后台")
menu = st.sidebar.radio("分析维度", ["📊 班级整体画像", "💻 头歌详细分析", "🎥 学习通详细分析", "🛑 重点预警名单"])

with st.sidebar.expander("📥 上传数据文件", expanded=True):
    edu_file = st.file_uploader("头歌成绩 CSV", type=['csv', 'xlsx'])
    xxt_file = st.file_uploader("学习通观看详情 CSV", type=['csv', 'xlsx'])

# --- 4. 主页面逻辑 ---
if edu_file and xxt_file:
    df_e_raw = pd.read_csv(edu_file) if edu_file.name.endswith('.csv') else pd.read_excel(edu_file)
    df_x_raw = pd.read_csv(xxt_file, header=None) if xxt_file.name.endswith('.csv') else pd.read_excel(xxt_file, header=None)
    
    df_e = analyze_edu_engine(df_e_raw)
    df_x = analyze_xxt_engine(df_x_raw)

    # --- 模块：班级画像 ---
    if menu == "📊 班级整体画像":
        st.title("📈 班级学习表现大数据看板")
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("分析总人数", len(df_e['学号'].unique()))
        m2.metric("异常行为人次", len(df_e[df_e['判定'] != '正常']) + len(df_x[df_x['判定'] == '速刷']))
        m3.metric("头歌平均成绩", f"{df_e_raw['最终成绩'].mean():.1f}")
        m4.metric("平均视频观看度", f"{df_x['观看占比'].mean():.1f}%")

        st.divider()
        c1, c2 = st.columns(2)
        with c1:
            st.subheader("🌙 24小时学习活跃分布")
            hour_counts = df_e.groupby('完成时刻').size().reset_index(name='提交次数')
            fig_h = px.bar(hour_counts, x='完成时刻', y='提交次数', color='提交次数', color_continuous_scale='Viridis')
            st.plotly_chart(fig_h, use_container_width=True)
            
        with c2:
            st.subheader("📍 编程效率离群点分析")
            fig_s = px.scatter(df_e, x='用时', y='评测次数', color='判定', hover_data=['姓名', '关卡'], 
                              log_x=True, title="左下角红色点：极大概率为抄袭粘贴")
            st.plotly_chart(fig_s, use_container_width=True)

    # --- 模块：头歌深度分析 ---
    elif menu == "💻 头歌详细分析":
        st.title("👩‍💻 头歌编程行为审计")
        stage = st.selectbox("选择要审计的关卡", df_e['关卡'].unique())
        s_data = df_e[df_e['关卡'] == stage]
        
        st.subheader(f"{stage} - 全班耗时分布盒须图")
        fig_box = px.box(s_data, y='用时', points="all", hover_data=['姓名'], color_discrete_sequence=['#636EFA'])
        st.plotly_chart(fig_box, use_container_width=True)
        
        
        st.subheader("📑 疑似粘贴代码名单")
        st.dataframe(s_data[s_data['判定'] == '疑似粘贴'][['姓名', '用时', '评测次数']], use_container_width=True)

    # --- 模块：学习通深度分析 ---
    elif menu == "🎥 学习通详细分析":
        st.title("📺 视频学习真实性审计")
        fig_hist = px.histogram(df_x, x='观看占比', nbins=25, color='判定', color_discrete_map={'正常':'#00CC96','速刷':'#EF553B'})
        st.plotly_chart(fig_hist, use_container_width=True)
        
        st.subheader("📋 详细异常观看记录")
        st.dataframe(df_x[df_x['判定'] == '速刷'], use_container_width=True)

    # --- 模块：重点预警名单 ---
    elif menu == "🛑 重点预警名单":
        st.title("🚨 重点预警与约谈建议")
        st.info("系统通过跨平台关联，找出在头歌和学习通均有严重异常行为的学生。")
        
        e_bad = df_e[df_e['判定'] != '正常'].groupby('姓名').size().reset_index(name='头歌异常次数')
        x_bad = df_x[df_x['判定'] == '速刷'].groupby('姓名').size().reset_index(name='视频速刷次数')
        
        cross_df = pd.merge(e_bad, x_bad, on='姓名', how='outer').fillna(0)
        cross_df['风险评分'] = cross_df['头歌异常次数'] * 3 + cross_df['视频速刷次数'] * 2
        
        st.subheader("🚩 综合风险排行榜 (评分越高，行为越不认真)")
        st.dataframe(cross_df.sort_values('风险评分', ascending=False), use_container_width=True)
        st.download_button("📥 导出黑名单 CSV", cross_df.to_csv(index=False), "warning_list.csv")

else:
    st.title("👋 欢迎使用学生线上表现审计系统")
    st.info("请在左侧上传两个平台的 CSV/Excel 文件以生成详细报告。")
    st.image("https://img.icons8.com/illustrations/lexir/400/learning.png")
