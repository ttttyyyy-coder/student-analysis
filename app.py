import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import re
import io
import numpy as np

# ==============================================================================
# 1. 🌸 樱花粉主题 UI 配置 (保持高颜值)
# ==============================================================================
st.set_page_config(page_title="智慧评价审计系统 v15.0 Pro", layout="wide", initial_sidebar_state="expanded")

st.markdown("""
    <style>
        /* --- 全局粉色基调 --- */
        .stApp { background-color: #FFF0F5; font-family: 'Helvetica Neue', sans-serif; }
        
        /* --- 侧边栏深度定制 --- */
        [data-testid="stSidebar"] {
            background-image: linear-gradient(180deg, #FFE4E1 0%, #FFC0CB 100%);
            border-right: 1px solid #FFB6C1;
        }
        [data-testid="stSidebar"] * { color: #8B0000 !important; }
        [data-testid="stSidebar"] h1 { color: #C71585 !important; border-bottom: 2px solid #DB7093; padding-bottom: 15px; }
        [data-testid="stSidebar"] .stRadio label { 
            background: rgba(255,255,255,0.4) !important; padding: 10px; border-radius: 10px; margin-bottom: 5px; transition: 0.3s; 
        }
        [data-testid="stSidebar"] .stRadio label:hover { background: white !important; box-shadow: 0 2px 5px rgba(0,0,0,0.05); }

        /* --- 核心卡片容器 --- */
        .main-card {
            background: white; padding: 25px; border-radius: 20px;
            box-shadow: 0 10px 25px rgba(255, 105, 180, 0.1); margin-bottom: 25px;
            border: 2px solid #FFF; border-left: 6px solid #FF69B4; 
        }
        
        /* --- 统计数字卡片 --- */
        .stat-box {
            background: white; padding: 20px; border-radius: 15px; text-align: center;
            box-shadow: 0 4px 10px rgba(219, 112, 147, 0.1); border: 1px solid #FFE4E1; transition: transform 0.2s;
        }
        .stat-box:hover { transform: translateY(-5px); }
        .stat-val { font-size: 32px; font-weight: 800; color: #C71585; }
        .stat-label { font-size: 13px; color: #DB7093; font-weight: 700; margin-top: 5px; }
        
        /* --- 标签体系 --- */
        .tag { display: inline-block; padding: 3px 10px; border-radius: 12px; font-size: 11px; font-weight: 700; margin-right: 5px; color: white; }
        .tag-brush { background: linear-gradient(45deg, #FF6B6B, #FF8787); } 
        .tag-skip { background: linear-gradient(45deg, #FCC419, #FFD43B); color: #856404; }  
        .tag-silent { background: linear-gradient(45deg, #CC5DE8, #DA77F2); }
        .tag-pass { background: linear-gradient(45deg, #51CF66, #69DB7C); } 
        .tag-none { background: linear-gradient(45deg, #868E96, #ADB5BD); }
        
        /* --- 诊断卡片 --- */
        .diagnosis-card {
            background: white; padding: 30px; border-radius: 15px;
            box-shadow: 0 5px 15px rgba(0,0,0,0.08); border-top: 8px solid #FF6B6B;
        }
    </style>
""", unsafe_allow_html=True)

# ==============================================================================
# 2. 强力数据加载内核 (双平台兼容)
# ==============================================================================
class UniversalLoader:
    @staticmethod
    def load_file(file):
        try:
            if file.name.lower().endswith('.csv'):
                for encoding in ['utf-8-sig', 'gb18030', 'gbk', 'utf-16']:
                    try:
                        file.seek(0)
                        df = pd.read_csv(file, encoding=encoding)
                        if len(df.columns) > 1: return UniversalLoader._sanitize(df)
                    except: continue
                return None, "CSV读取失败"
            else:
                xls = pd.ExcelFile(file)
                target_sheet = xls.sheet_names[0]
                for sheet in xls.sheet_names:
                    if "进度" in sheet or "详情" in sheet:
                        target_sheet = sheet
                        break
                
                df_raw = pd.read_excel(xls, sheet_name=target_sheet, header=None, nrows=20)
                anchor_idx = -1
                for idx, row in df_raw.iterrows():
                    row_str = " ".join([str(val) for val in row.values])
                    if ('姓名' in row_str or '学号' in row_str) and \
                       ('进度' in row_str or '时长' in row_str or '任务点' in row_str or \
                        '耗时' in row_str or '成绩' in row_str or '分' in row_str):
                        anchor_idx = idx
                        break
                
                if anchor_idx == -1: return None, "未找到有效表头"
                file.seek(0)
                df = pd.read_excel(xls, sheet_name=target_sheet, header=anchor_idx)
                return UniversalLoader._sanitize(df)
        except Exception as e: return None, f"文件解析错误: {str(e)}"

    @staticmethod
    def _sanitize(df):
        df = df.dropna(how='all', axis=0)
        df.columns = [str(c).strip().replace('\n', '') for c in df.columns]
        return df, None

# ==============================================================================
# 3. AI 审计核心 (集成聚类逻辑)
# ==============================================================================
class AuditCore:
    def __init__(self, df):
        self.df = df
        self.cols = self._map_columns()

    def _map_columns(self):
        mapping = {}
        targets = {
            'name': ['姓名', '真实姓名', '学生姓名'],
            'id': ['学号', '工号', 'UID'],
            'prog': ['进度', '百分比', '完成度', '任务点'],
            'time': ['时长', '观看时长', '耗时', '总耗时'],
            'score': ['综合成绩', '最终成绩', '总分', '成绩', '得分'],
            'discuss': ['讨论', '互动']
        }
        for key, possible_names in targets.items():
            for col in self.df.columns:
                if any(p in col for p in possible_names):
                    mapping[key] = col
                    break
        return mapping

    def _parse_time(self, val):
        if pd.isna(val) or str(val).strip() in ['--', '-', '']: return 0.0
        s = str(val)
        nums = re.findall(r'(\d+\.?\d*)', s)
        if not nums: return 0.0
        if '分钟' in s: return float(nums[0])
        if '时' in s and '分' in s: return float(nums[0]) * 60 + float(nums[1])
        elif '时' in s: return float(nums[0]) * 60
        else: return float(nums[0])

    def execute_audit(self, mode="LMS"):
        c = self.cols
        if 'name' not in c: return None, "表格中未找到【姓名】列"
        
        res = pd.DataFrame()
        res['姓名'] = self.df[c['name']]
        res['学号'] = self.df[c['id']] if 'id' in c else "未知"
        
        if 'prog' in c:
            raw_p = pd.to_numeric(self.df[c['prog']], errors='coerce').fillna(0)
            res['进度'] = raw_p * 100 if raw_p.max() <= 1.1 else raw_p
        else: res['进度'] = 0.0
        
        res['时长'] = self.df[c['time']].apply(self._parse_time) if 'time' in c else 0.0
        res['成绩'] = pd.to_numeric(self.df[c['score']], errors='coerce').fillna(0) if 'score' in c else 0
        res['讨论'] = pd.to_numeric(self.df[c['discuss']], errors='coerce').fillna(0) if 'discuss' in c else 0
        
        valid_times = res[res['时长'] > 5]['时长']
        avg_time = valid_times.mean() if not valid_times.empty else 60 
        
        # --- 异常判定逻辑 ---
        def ai_diagnosis(row):
            tags = []
            reasons = []
            p = row['进度']
            t = row['时长']
            
            if mode == "LMS":
                dynamic_threshold = avg_time * 0.15
                if p > 90 and (t < 15 or t < dynamic_threshold):
                    tags.append("🚨AI:秒刷")
                    reasons.append(f"进度{p:.0f}%，但时长仅{t:.1f}分(班级平均{avg_time:.0f}分)，极速完成")
                elif p > 80 and t < (avg_time * 0.4):
                    tags.append("🟡时长存疑")
                    reasons.append(f"进度{p:.0f}%但时长{t:.1f}分，严重不成正比")
                if p > 50 and row['讨论'] == 0:
                    tags.append("🟣零互动")
                if p > 90 and row['成绩'] < 40 and row['成绩'] > 0:
                    tags.append("🐌无效刷课")
                    reasons.append(f"进度满但成绩极低({row['成绩']}分)")
            else: # 头歌
                if row['成绩'] == 0 and t < 1:
                    tags.append("🌑未开始")
                    reasons.append("未开始实训")
                elif row['成绩'] >= 90 and t < 15:
                    tags.append("🚨代码拷贝")
                    reasons.append(f"高分({row['成绩']}分)但耗时极短")
                elif row['成绩'] >= 60 and t < 5:
                    tags.append("⚡极速完成")

            is_abnormal = len(reasons) > 0
            if not is_abnormal: return ["🟢正常"], "符合常态"
            return tags, " | ".join(reasons)

        analysis = res.apply(ai_diagnosis, axis=1)
        res['证据链'] = analysis.apply(lambda x: x[0])
        res['异常原因'] = analysis.apply(lambda x: x[1])
        res['状态'] = res['异常原因'].apply(lambda x: '正常' if '符合常态' in x else '异常')
        res['主标签'] = res['证据链'].apply(lambda x: x[0])
        
        # --- 聚类分析 (新增) ---
        # 简单高效的 RFM 分层逻辑 (无需 sklearn)
        def get_cluster(row):
            # T: Time Score, P: Progress Score
            t_score = 1 if row['时长'] >= avg_time else 0
            metric = row['进度'] if mode == "LMS" else row['成绩']
            metric_avg = res['进度'].mean() if mode == "LMS" else res['成绩'].mean()
            p_score = 1 if metric >= metric_avg else 0
            
            if t_score == 1 and p_score == 1: return "🌟 领跑集团 (双高)"
            if t_score == 0 and p_score == 1: return "🚀 效率/刷课组 (低时高产)"
            if t_score == 1 and p_score == 0: return "🐢 努力困境组 (高时低产)"
            return "💤 待激活组 (双低)"
            
        res['学习群体'] = res.apply(get_cluster, axis=1)
        
        return res, None

# ==============================================================================
# 4. 主程序
# ==============================================================================
def main():
    st.sidebar.markdown("""
        <div style="text-align: center; padding: 20px;">
            <h1 style="font-size: 60px; margin:0;">🌸</h1>
            <h2 style="color: #C71585 !important;">智慧评价审计</h2>
            <p style="color: #DB7093;">v15.0 AI Mining</p>
        </div>
    """, unsafe_allow_html=True)
    
    mode_label = st.sidebar.radio("选择平台", ["学习通 (LMS)", "头歌 (EduCoder)"], label_visibility="collapsed")
    mode = "LMS" if "学习通" in mode_label else "HG"
    file = st.sidebar.file_uploader("📂 上传原始数据", type=['xlsx', 'csv'])

    if file:
        with st.spinner("🤖 AI 正在挖掘数据价值..."):
            raw_df, err = UniversalLoader.load_file(file)
            if err:
                st.error(f"❌ {err}")
                return

            engine = AuditCore(raw_df)
            audit_df, logic_err = engine.execute_audit(mode)
            
            if audit_df is None or audit_df.empty:
                st.warning("⚠️ 数据解析为空，请检查文件。")
                return

            risk_count = len(audit_df[audit_df['状态']=='异常'])
            # 修复未完结统计逻辑：强制转数字后比较
            unfinished_count = len(audit_df[pd.to_numeric(audit_df['进度'], errors='coerce').fillna(0) < 99.9])
            
            st.sidebar.markdown("---")
            nav = st.sidebar.radio("功能导航", [
                "📊 全局数据看板",
                "🔮 深度数据挖掘 (New!)",
                f"🚨 异常数据分栏 ({risk_count})",
                f"📉 未完结名单统计 ({unfinished_count})",
                "📋 原始数据表"
            ])

            # === VIEW 1: Dashboard ===
            if "全局数据看板" in nav:
                st.markdown("### 🌸 班级学情大数据看板")
                try:
                    c1, c2, c3, c4 = st.columns(4)
                    c1.markdown(f'<div class="stat-box"><div class="stat-val">{len(audit_df)}</div><div class="stat-label">总人数</div></div>', unsafe_allow_html=True)
                    c2.markdown(f'<div class="stat-box"><div class="stat-val" style="color:#10B981">{len(audit_df)-risk_count}</div><div class="stat-label">健康人数</div></div>', unsafe_allow_html=True)
                    c3.markdown(f'<div class="stat-box"><div class="stat-val" style="color:#FF69B4">{risk_count}</div><div class="stat-label">AI 预警</div></div>', unsafe_allow_html=True)
                    avg_val = audit_df["进度" if mode=="LMS" else "成绩"].mean()
                    c4.markdown(f'<div class="stat-box"><div class="stat-val">{avg_val:.1f}</div><div class="stat-label">平均绩效</div></div>', unsafe_allow_html=True)

                    col_chart1, col_chart2 = st.columns(2)
                    with col_chart1:
                        st.markdown('<div class="main-card"><h5>🎨 证据画像分布</h5>', unsafe_allow_html=True)
                        tags_flat = [t for sublist in audit_df['证据链'] for t in sublist if t != '🟢正常']
                        if not tags_flat: tags_flat = ["🟢正常"]
                        tag_counts = pd.Series(tags_flat).value_counts()
                        fig = px.pie(values=tag_counts.values, names=tag_counts.index, hole=0.5, color_discrete_sequence=px.colors.qualitative.Pastel)
                        st.plotly_chart(fig, use_container_width=True)
                        st.markdown('</div>', unsafe_allow_html=True)
                    
                    with col_chart2:
                        st.markdown('<div class="main-card"><h5>⏱️ 学习时长分布</h5>', unsafe_allow_html=True)
                        fig_hist = px.histogram(audit_df, x="时长", nbins=20, color_discrete_sequence=['#FFB6C1'])
                        fig_hist.add_vline(x=audit_df['时长'].mean(), line_dash="dash", line_color="red", annotation_text="平均时长")
                        st.plotly_chart(fig_hist, use_container_width=True)
                        st.markdown('</div>', unsafe_allow_html=True)
                except Exception as e: st.error(f"渲染错误: {e}")

            # === VIEW 2: 深度数据挖掘 (New!) ===
            elif "深度数据挖掘" in nav:
                st.markdown("### 🔮 深度数据价值挖掘")
                st.info("💡 运用统计学方法，发现数据背后的隐藏规律。")
                
                tab1, tab2 = st.tabs(["🔥 关联性分析", "🧩 智能聚类画像"])
                
                with tab1:
                    st.markdown("#### 核心指标相关性热力图")
                    st.caption("颜色越红/越深，代表两个指标之间的关系越紧密（例如：投入时长是否真正带来了高分？）")
                    
                    # 计算相关性矩阵
                    corr_cols = ['时长', '进度', '成绩', '讨论']
                    valid_cols = [c for c in corr_cols if c in audit_df.columns]
                    if len(valid_cols) > 1:
                        corr_matrix = audit_df[valid_cols].corr()
                        fig_corr = px.imshow(corr_matrix, text_auto=True, color_continuous_scale='RdBu_r', aspect="auto")
                        st.plotly_chart(fig_corr, use_container_width=True)
                    
                    st.markdown("#### 📈 成绩正态分布检测")
                    col_d1, col_d2 = st.columns(2)
                    with col_d1:
                        fig_dist = px.histogram(audit_df, x="成绩", nbins=15, title="成绩分布图", color_discrete_sequence=['#87CEFA'])
                        st.plotly_chart(fig_dist, use_container_width=True)
                    with col_d2:
                        st.markdown("""
                        **数据洞察：**
                        - 若呈现**中间高两头低**（钟形），说明教学难度适中。
                        - 若呈现**左偏**（低分多），说明课程难度较大或学情不佳。
                        - 若呈现**右偏**（高分多），说明题目可能偏简单。
                        """)

                with tab2:
                    st.markdown("#### 🧩 学生群体智能聚类")
                    st.caption("基于“投入-产出”模型，自动将学生划分为四大典型群体：")
                    
                    col_q1, col_q2 = st.columns([3, 1])
                    with col_q1:
                        y_axis = "进度" if mode == "LMS" else "成绩"
                        fig_clus = px.scatter(audit_df, x="时长", y=y_axis, color="学习群体", 
                                            hover_name="姓名", size="时长", size_max=15,
                                            color_discrete_map={
                                                "🌟 领跑集团 (双高)": "#10B981", 
                                                "🚀 效率/刷课组 (低时高产)": "#FF6B6B", 
                                                "🐢 努力困境组 (高时低产)": "#F59E0B", 
                                                "💤 待激活组 (双低)": "#ADB5BD"
                                            })
                        # 添加平均线辅助线
                        fig_clus.add_hline(y=audit_df[y_axis].mean(), line_dash="dash", line_color="gray", annotation_text="平均产出")
                        fig_clus.add_vline(x=audit_df['时长'].mean(), line_dash="dash", line_color="gray", annotation_text="平均投入")
                        st.plotly_chart(fig_clus, use_container_width=True)
                    
                    with col_q2:
                        st.markdown("**群体筛选：**")
                        cluster_type = st.selectbox("选择群体", audit_df['学习群体'].unique())
                        target_list = audit_df[audit_df['学习群体'] == cluster_type]
                        st.success(f"该群体共 {len(target_list)} 人")
                        with st.expander("查看名单", expanded=True):
                            st.dataframe(target_list[['姓名', '时长', y_axis]], hide_index=True)

            # === VIEW 3: 异常数据分栏 (修复版) ===
            elif "异常数据分栏" in nav:
                st.markdown("### 🚨 异常行为诊断中心")
                risk_df = audit_df[audit_df['状态']=='异常'].copy()
                
                if risk_df.empty:
                    st.success("🎉 全班表现完美！")
                else:
                    col_list, col_detail = st.columns([1, 2])
                    with col_list:
                        st.markdown("#### 📋 风险名单")
                        output = io.BytesIO()
                        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                            risk_df.drop(columns=['证据链', '主标签']).to_excel(writer, index=False)
                        st.download_button("📥 导出诊断报告", output.getvalue(), "异常诊断表.xlsx", use_container_width=True)
                        
                        student_name = st.radio("点击查看详情：", risk_df['姓名'].unique(), key="s_select")
                    
                    with col_detail:
                        if student_name:
                            row = risk_df[risk_df['姓名'] == student_name].iloc[0]
                            tags_html = "".join([f'<span class="tag tag-brush">{t}</span>' if "秒刷" in t else (f'<span class="tag tag-skip">{t}</span>' if "存疑" in t or "未开始" in t else f'<span class="tag tag-pass">{t}</span>') for t in row['证据链'] if t != '🟢正常'])
                            
                            st.markdown(f"""
                            <div class="diagnosis-card">
                                <h2 style="color:#C71585; margin:0;">👤 {row['姓名']} <span style="font-size:18px; color:#666;">({row['学号']})</span></h2>
                                <hr style="border-top: 1px dashed #FFB6C1;">
                                <div style="display:flex; justify-content:space-between; margin-bottom:20px;">
                                    <div style="text-align:center;">
                                        <div style="font-size:12px; color:#888;">进度/产出</div>
                                        <div style="font-size:24px; font-weight:bold; color:#3B82F6;">{row['进度']:.1f}%</div>
                                    </div>
                                    <div style="text-align:center;">
                                        <div style="font-size:12px; color:#888;">投入时长</div>
                                        <div style="font-size:24px; font-weight:bold; color:#F59E0B;">{row['时长']:.1f}m</div>
                                    </div>
                                    <div style="text-align:center;">
                                        <div style="font-size:12px; color:#888;">成绩/得分</div>
                                        <div style="font-size:24px; font-weight:bold; color:#8B5CF6;">{row['成绩']:.1f}</div>
                                    </div>
                                </div>
                                <h4 style="color:#C71585;">🩺 AI 诊断结论</h4>
                                <p style="background:#FFF0F5; padding:15px; border-radius:8px; border-left:4px solid #FF69B4; color:#C71585; font-weight:bold;">
                                    {row['异常原因']}
                                </p>
                                <h4 style="color:#C71585;">🏷️ 风险标签</h4>
                                <div>{tags_html}</div>
                            </div>
                            """, unsafe_allow_html=True)

            # === VIEW 4: 未完结名单统计 (修复版) ===
            elif "未完结名单统计" in nav:
                st.markdown("### 📉 章节任务未完结统计")
                unfinished_df = audit_df[pd.to_numeric(audit_df['进度'], errors='coerce').fillna(0) < 99.9].sort_values('进度')
                
                if unfinished_df.empty:
                    st.success("🎉 全班已全部完成任务！")
                else:
                    st.info(f"共有 **{len(unfinished_df)}** 名同学未完结，请督促。")
                    output = io.BytesIO()
                    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                        unfinished_df[['姓名', '学号', '进度', '时长']].to_excel(writer, index=False)
                    st.download_button("📥 导出未完结名单", output.getvalue(), "未完结名单.xlsx")
                    
                    unfinished_df['进度条'] = unfinished_df['进度'].apply(lambda x: f'<div style="background:#eee;width:100px;height:8px;border-radius:4px;"><div style="background:#3B82F6;width:{x}px;height:8px;border-radius:4px;"></div></div>')
                    st.write(unfinished_df[['姓名', '学号', '进度', '进度条']].to_html(escape=False, index=False), unsafe_allow_html=True)

            # === VIEW 5: 原始表 ===
            elif "原始数据清洗表" in nav:
                st.dataframe(audit_df, use_container_width=True)

    else:
        st.markdown("""
            <div style="text-align: center; padding: 80px; color: #DB7093;">
                <h1 style="font-size: 80px;">🧠</h1>
                <h3>请上传 学习通/头歌 导出文件</h3>
                <p>系统将自动诊断“时间不准”和“速刷”行为，并挖掘深层数据价值</p>
            </div>
        """, unsafe_allow_html=True)

if __name__ == "__main__":
    main()