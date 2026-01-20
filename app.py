import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import re
import io
import numpy as np

# ==============================================================================
# 1. 🌸 樱花粉主题 UI 配置 (严格保持不变)
# ==============================================================================
st.set_page_config(page_title="智慧评价审计系统 v16.0 Full", layout="wide", initial_sidebar_state="expanded")

st.markdown("""
    <style>
        /* --- 全局粉色基调 --- */
        .stApp { background-color: #FFF0F5; font-family: 'Helvetica Neue', sans-serif; }
        [data-testid="stSidebar"] {
            background-image: linear-gradient(180deg, #FFE4E1 0%, #FFC0CB 100%); border-right: 1px solid #FFB6C1;
        }
        [data-testid="stSidebar"] * { color: #8B0000 !important; }
        [data-testid="stSidebar"] h1 { color: #C71585 !important; border-bottom: 2px solid #DB7093; padding-bottom: 15px; }
        [data-testid="stSidebar"] .stRadio label { 
            background: rgba(255,255,255,0.4) !important; padding: 10px; border-radius: 10px; margin-bottom: 5px; transition: 0.3s; 
        }
        [data-testid="stSidebar"] .stRadio label:hover { background: white !important; box-shadow: 0 2px 5px rgba(0,0,0,0.05); }
        .main-card {
            background: white; padding: 25px; border-radius: 20px;
            box-shadow: 0 10px 25px rgba(255, 105, 180, 0.1); margin-bottom: 25px;
            border: 2px solid #FFF; border-left: 6px solid #FF69B4; 
        }
        .stat-box {
            background: white; padding: 20px; border-radius: 15px; text-align: center;
            box-shadow: 0 4px 10px rgba(219, 112, 147, 0.1); border: 1px solid #FFE4E1; transition: transform 0.2s;
        }
        .stat-box:hover { transform: translateY(-5px); }
        .stat-val { font-size: 32px; font-weight: 800; color: #C71585; }
        .stat-label { font-size: 13px; color: #DB7093; font-weight: 700; margin-top: 5px; }
        
        .tag { display: inline-block; padding: 3px 10px; border-radius: 12px; font-size: 11px; font-weight: 700; margin-right: 5px; color: white; }
        .tag-brush { background: linear-gradient(45deg, #FF6B6B, #FF8787); } 
        .tag-skip { background: linear-gradient(45deg, #FCC419, #FFD43B); color: #856404; }  
        .tag-silent { background: linear-gradient(45deg, #CC5DE8, #DA77F2); }
        .tag-pass { background: linear-gradient(45deg, #51CF66, #69DB7C); } 
        .tag-none { background: linear-gradient(45deg, #868E96, #ADB5BD); }
        .tag-warn { background: linear-gradient(45deg, #FF9F43, #FFC048); }
        
        .diagnosis-card {
            background: white; padding: 30px; border-radius: 15px;
            box-shadow: 0 5px 15px rgba(0,0,0,0.08); border-top: 8px solid #FF6B6B;
        }
    </style>
""", unsafe_allow_html=True)

# ==============================================================================
# 2. 强力数据加载内核 (★ 重大升级：多表融合技术)
# ==============================================================================
class UniversalLoader:
    @staticmethod
    def load_file(file):
        try:
            if file.name.lower().endswith('.csv'):
                # 单CSV模式 (保持兼容)
                for encoding in ['utf-8-sig', 'gb18030', 'gbk', 'utf-16']:
                    try:
                        file.seek(0)
                        df = pd.read_csv(file, encoding=encoding)
                        if len(df.columns) > 1: return UniversalLoader._sanitize(df), None
                    except: continue
                return None, None, "CSV读取失败"
            else:
                # ★ Excel 多Sheet 智能融合模式
                xls = pd.ExcelFile(file)
                
                # 1. 寻找核心进度表 (Master Table)
                main_df = pd.DataFrame()
                for sheet in xls.sheet_names:
                    if "进度" in sheet or "详情" in sheet: # 优先找"学生学习进度详情"
                        df_raw = pd.read_excel(xls, sheet_name=sheet, header=None, nrows=20)
                        # 找表头
                        anchor_idx = -1
                        for idx, row in df_raw.iterrows():
                            s = " ".join([str(v) for v in row.values])
                            if '姓名' in s and ('进度' in s or '任务点' in s or '时长' in s):
                                anchor_idx = idx
                                break
                        if anchor_idx != -1:
                            file.seek(0)
                            main_df = pd.read_excel(xls, sheet_name=sheet, header=anchor_idx)
                            main_df = UniversalLoader._sanitize(main_df)
                            break
                
                if main_df.empty:
                    return None, None, "未找到核心进度表"

                # 2. 挖掘“签到”数据 (Attendance)
                try:
                    for sheet in xls.sheet_names:
                        if "签到" in sheet:
                            file.seek(0)
                            # 签到表头通常在前面
                            df_att = pd.read_excel(xls, sheet_name=sheet) # 假设第一行是表头
                            # 寻找表头行
                            if '姓名' not in df_att.columns:
                                df_att = pd.read_excel(xls, sheet_name=sheet, header=2) # 尝试跳过前两行
                            
                            if '姓名' in df_att.columns:
                                # 计算签到率：统计每行有多少个“已签” / 总列数(排除姓名学号等)
                                date_cols = [c for c in df_att.columns if '/' in str(c) or '月' in str(c)]
                                if date_cols:
                                    df_att['签到次数'] = df_att[date_cols].apply(lambda x: x.astype(str).str.contains('已签|出勤').sum(), axis=1)
                                    df_att['总考勤'] = len(date_cols)
                                    df_att['签到率'] = (df_att['签到次数'] / df_att['总考勤'] * 100).fillna(0)
                                    # 合并到主表
                                    main_df = pd.merge(main_df, df_att[['姓名', '签到率']], on='姓名', how='left')
                except: pass # 签到读取失败不影响主流程

                # 3. 挖掘“讨论”数据 (Interaction)
                try:
                    for sheet in xls.sheet_names:
                        if "讨论" in sheet:
                            file.seek(0)
                            df_disc = pd.read_excel(xls, sheet_name=sheet, header=2) # 通常有标题行
                            if '姓名' in df_disc.columns and '获赞数' in df_disc.columns:
                                main_df = pd.merge(main_df, df_disc[['姓名', '获赞数', '回复讨论']], on='姓名', how='left')
                except: pass

                # 4. 挖掘“章节学习次数” (Time Series) -> 用于生成全班学习曲线
                class_trend_df = pd.DataFrame()
                try:
                    for sheet in xls.sheet_names:
                        if "章节学习次数" in sheet:
                            file.seek(0)
                            # 这个表通常是 日期 | 访问次数
                            df_trend = pd.read_excel(xls, sheet_name=sheet, header=2)
                            if '日期' in df_trend.columns and '访问次数' in str(df_trend.columns):
                                class_trend_df = df_trend
                except: pass

                return main_df, class_trend_df, None

        except Exception as e: return None, None, f"解析错误: {str(e)}"

    @staticmethod
    def _sanitize(df):
        df = df.dropna(how='all', axis=0)
        df.columns = [str(c).strip().replace('\n', '') for c in df.columns]
        return df

# ==============================================================================
# 3. AI 审计核心 (全维度数据融合)
# ==============================================================================
class AuditCore:
    def __init__(self, df):
        self.df = df
        self.cols = self._map_columns()

    def _map_columns(self):
        mapping = {}
        targets = {
            'name': ['姓名', '真实姓名'],
            'id': ['学号', 'UID'],
            'prog': ['进度', '百分比', '任务点'],
            'time': ['时长', '耗时'],
            'score': ['综合成绩', '成绩', '总分'],
            'discuss': ['讨论', '互动'],
            'attend': ['签到率'], # 新增
            'likes': ['获赞数']   # 新增
        }
        for key, possible_names in targets.items():
            for col in self.df.columns:
                if any(p in col for p in possible_names):
                    mapping[key] = col
                    break
        return mapping

    def _parse_time(self, val):
        if pd.isna(val): return 0.0
        s = str(val)
        nums = re.findall(r'(\d+\.?\d*)', s)
        if not nums: return 0.0
        if '分钟' in s: return float(nums[0])
        if '时' in s: return float(nums[0])*60 + (float(nums[1]) if len(nums)>1 else 0)
        return float(nums[0])

    def execute_audit(self, mode="LMS"):
        c = self.cols
        if 'name' not in c: return None, "缺少姓名列"
        
        res = pd.DataFrame()
        res['姓名'] = self.df[c['name']]
        res['学号'] = self.df[c['id']] if 'id' in c else "未知"
        
        # 基础数据
        if 'prog' in c:
            raw_p = pd.to_numeric(self.df[c['prog']], errors='coerce').fillna(0)
            res['进度'] = raw_p * 100 if raw_p.max() <= 1.1 else raw_p
        else: res['进度'] = 0.0
        
        res['时长'] = self.df[c['time']].apply(self._parse_time) if 'time' in c else 0.0
        res['成绩'] = pd.to_numeric(self.df[c['score']], errors='coerce').fillna(0) if 'score' in c else 0
        res['讨论'] = pd.to_numeric(self.df[c['discuss']], errors='coerce').fillna(0) if 'discuss' in c else 0
        
        # 扩展数据 (如果融合成功)
        res['签到率'] = pd.to_numeric(self.df[c['attend']], errors='coerce').fillna(100) if 'attend' in c else 100
        res['获赞'] = pd.to_numeric(self.df[c['likes']], errors='coerce').fillna(0) if 'likes' in c else 0

        # 动态基准
        valid_times = res[res['时长']>5]['时长']
        avg_time = valid_times.mean() if not valid_times.empty else 60
        
        def ai_diagnosis(row):
            tags = []
            reasons = []
            p, t = row['进度'], row['时长']
            
            if mode == "LMS":
                # 1. 刷课
                thresh = avg_time * 0.15
                if p > 90 and (t < 15 or t < thresh):
                    tags.append("🚨AI:秒刷")
                    reasons.append(f"进度{p:.0f}%但时长仅{t:.1f}分(均值{avg_time:.0f})")
                elif p > 80 and t < (avg_time * 0.4):
                    tags.append("🟡时长存疑")
                    reasons.append("进度与时长不成正比")
                
                # 2. 互动
                if p > 50 and row['讨论'] == 0: tags.append("🟣零互动")
                
                # 3. 假学 (进度满但成绩极低)
                if p > 90 and row['成绩'] < 40 and row['成绩'] > 0:
                    tags.append("🐌无效刷课")
                    reasons.append(f"进度满但成绩仅{row['成绩']}分")
                
                # 4. 考勤 (新增)
                if row['签到率'] < 60:
                    tags.append("📉缺勤")
                    reasons.append(f"签到率仅{row['签到率']:.0f}%")
            
            else: # 头歌
                if row['成绩'] == 0 and t < 1: tags.append("🌑未开始"); reasons.append("未开始实训")
                elif row['成绩'] >= 90 and t < 15: tags.append("🚨代码拷贝"); reasons.append("高分极速完成")
                elif row['成绩'] >= 60 and t < 5: tags.append("⚡极速完成")

            return tags if reasons or tags else ["🟢正常"], " | ".join(reasons)

        analysis = res.apply(ai_diagnosis, axis=1)
        res['证据链'] = analysis.apply(lambda x: x[0])
        res['异常原因'] = analysis.apply(lambda x: x[1])
        res['状态'] = res['异常原因'].apply(lambda x: '正常' if not x else '异常')
        res['主标签'] = res['证据链'].apply(lambda x: x[0])
        
        # 聚类画像
        def get_cluster(row):
            t_score = 1 if row['时长'] >= avg_time else 0
            metric = row['进度'] if mode=="LMS" else row['成绩']
            p_score = 1 if metric >= res['进度'].mean() else 0
            if t_score==1 and p_score==1: return "🌟 领跑集团"
            if t_score==0 and p_score==1: return "🚀 效率/刷课组"
            if t_score==1 and p_score==0: return "🐢 努力困境组"
            return "💤 待激活组"
        res['学习群体'] = res.apply(get_cluster, axis=1)
        res['真实度'] = (res['时长'] / (res['进度']*avg_time/100+1)*100).clip(0,100)
        
        return res, None

# ==============================================================================
# 4. 主程序
# ==============================================================================
def main():
    st.sidebar.markdown("""
        <div style="text-align: center; padding: 20px;">
            <h1 style="font-size: 60px; margin:0;">🌸</h1>
            <h2 style="color: #C71585 !important;">智慧评价审计</h2>
            <p style="color: #DB7093;">v16.0 Full Mining</p>
        </div>
    """, unsafe_allow_html=True)
    
    mode_label = st.sidebar.radio("选择平台", ["学习通 (LMS)", "头歌 (EduCoder)"], label_visibility="collapsed")
    mode = "LMS" if "学习通" in mode_label else "HG"
    file = st.sidebar.file_uploader("📂 上传统计一键导出.xlsx", type=['xlsx', 'csv'])

    if file:
        with st.spinner("🤖 AI 正在全表扫描挖掘数据..."):
            # 注意：这里返回两个表，一个是主表，一个是班级趋势表
            raw_df, trend_df, err = UniversalLoader.load_file(file)
            if err: st.error(f"❌ {err}"); return

            engine = AuditCore(raw_df)
            audit_df, logic_err = engine.execute_audit(mode)
            
            if audit_df is None or audit_df.empty:
                st.warning("⚠️ 数据解析为空"); return

            risk_count = len(audit_df[audit_df['状态']=='异常'])
            unfinished_count = len(audit_df[pd.to_numeric(audit_df['进度'], errors='coerce').fillna(0) < 99.9])
            
            st.sidebar.markdown("---")
            nav = st.sidebar.radio("AI 深度视角", [
                "📊 全局数据看板",
                "🔮 深度数据挖掘 (Pro)",
                f"🚨 异常数据分栏 ({risk_count})",
                f"📉 未完结名单统计 ({unfinished_count})",
                "📋 原始数据清洗表"
            ])

            # === VIEW 1: Dashboard ===
            if "全局数据看板" in nav:
                st.markdown("### 🌸 班级学情大数据看板")
                try:
                    c1, c2, c3, c4 = st.columns(4)
                    c1.markdown(f'<div class="stat-box"><div class="stat-val">{len(audit_df)}</div><div class="stat-label">总人数</div></div>', unsafe_allow_html=True)
                    c2.markdown(f'<div class="stat-box"><div class="stat-val" style="color:#10B981">{len(audit_df)-risk_count}</div><div class="stat-label">健康人数</div></div>', unsafe_allow_html=True)
                    c3.markdown(f'<div class="stat-box"><div class="stat-val" style="color:#FF69B4">{risk_count}</div><div class="stat-label">AI 预警</div></div>', unsafe_allow_html=True)
                    
                    # 动态展示：如果有签到数据，显示平均签到率
                    if '签到率' in audit_df.columns and audit_df['签到率'].mean() < 99:
                        val = f"{audit_df['签到率'].mean():.1f}%"
                        label = "平均签到率"
                    else:
                        val = f"{audit_df['进度'].mean():.1f}%"
                        label = "平均进度"
                    c4.markdown(f'<div class="stat-box"><div class="stat-val">{val}</div><div class="stat-label">{label}</div></div>', unsafe_allow_html=True)

                    col_chart1, col_chart2 = st.columns(2)
                    with col_chart1:
                        st.markdown('<div class="main-card"><h5>🎨 证据画像分布</h5>', unsafe_allow_html=True)
                        tags_flat = [t for sublist in audit_df['证据链'] for t in sublist if t != '🟢正常']
                        if not tags_flat: tags_flat = ["🟢正常"]
                        fig = px.pie(values=pd.Series(tags_flat).value_counts().values, names=pd.Series(tags_flat).value_counts().index, hole=0.5, color_discrete_sequence=px.colors.qualitative.Pastel)
                        st.plotly_chart(fig, use_container_width=True)
                        st.markdown('</div>', unsafe_allow_html=True)
                    
                    with col_chart2:
                        st.markdown('<div class="main-card"><h5>⏱️ 学习时长分布</h5>', unsafe_allow_html=True)
                        fig_hist = px.histogram(audit_df, x="时长", nbins=20, color_discrete_sequence=['#FFB6C1'])
                        fig_hist.add_vline(x=audit_df['时长'].mean(), line_dash="dash", line_color="red")
                        st.plotly_chart(fig_hist, use_container_width=True)
                        st.markdown('</div>', unsafe_allow_html=True)
                except Exception as e: st.error(f"渲染错误: {e}")

            # === VIEW 2: 深度挖掘 (新增全班趋势) ===
            elif "深度数据挖掘" in nav:
                st.markdown("### 🔮 深度数据价值挖掘")
                tab1, tab2, tab3 = st.tabs(["📈 全班学习曲线", "🔥 关联性分析", "🧩 智能聚类"])
                
                with tab1:
                    st.markdown("#### 全班每日学习活跃度")
                    if trend_df is not None and not trend_df.empty:
                        # 尝试寻找日期列和次数列
                        date_col = [c for c in trend_df.columns if '日期' in str(c)]
                        val_col = [c for c in trend_df.columns if '次数' in str(c) or '访问' in str(c)]
                        if date_col and val_col:
                            fig_line = px.line(trend_df, x=date_col[0], y=val_col[0], title="学习热度趋势", markers=True, line_shape='spline', color_discrete_sequence=['#FF69B4'])
                            st.plotly_chart(fig_line, use_container_width=True)
                            st.info("💡 峰值通常对应作业截止日或考前突击。")
                        else:
                            st.warning("未在文件中找到【章节学习次数】表，无法绘制曲线。")
                    else:
                        st.warning("上传的文件中缺少【章节学习次数】Sheet，无法分析时间趋势。")

                with tab2:
                    st.markdown("#### 核心指标相关性")
                    # 自动把能分析的列都放进去
                    valid_cols = [c for c in ['时长', '进度', '成绩', '讨论', '签到率', '获赞'] if c in audit_df.columns]
                    if len(valid_cols) > 1:
                        corr = audit_df[valid_cols].corr()
                        fig_corr = px.imshow(corr, text_auto=True, color_continuous_scale='RdBu_r')
                        st.plotly_chart(fig_corr, use_container_width=True)
                    else: st.info("数据维度不足")

                with tab3:
                    st.markdown("#### 学生群体智能画像")
                    col_q1, col_q2 = st.columns([3, 1])
                    with col_q1:
                        y_axis = "进度" if mode == "LMS" else "成绩"
                        fig_clus = px.scatter(audit_df, x="时长", y=y_axis, color="学习群体", hover_name="姓名", size="时长", size_max=15,
                                            color_discrete_map={"🌟 领跑集团": "#10B981", "🚀 效率/刷课组": "#FF6B6B", "🐢 努力困境组": "#F59E0B", "💤 待激活组": "#ADB5BD"})
                        st.plotly_chart(fig_clus, use_container_width=True)
                    with col_q2:
                        cluster_type = st.selectbox("选择群体", audit_df['学习群体'].unique())
                        st.dataframe(audit_df[audit_df['学习群体'] == cluster_type][['姓名', '时长', y_axis]], hide_index=True)

            # === VIEW 3: 异常分栏 ===
            elif "异常数据分栏" in nav:
                st.markdown("### 🚨 异常行为诊断中心")
                risk_df = audit_df[audit_df['状态']=='异常'].copy()
                if risk_df.empty: st.success("🎉 无异常！")
                else:
                    col_list, col_detail = st.columns([1, 2])
                    with col_list:
                        st.markdown("#### 📋 风险名单")
                        output = io.BytesIO()
                        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                            risk_df.drop(columns=['证据链', '主标签']).to_excel(writer, index=False)
                        st.download_button("📥 导出Excel", output.getvalue(), "异常表.xlsx", use_container_width=True)
                        student_name = st.radio("点击查看详情：", risk_df['姓名'].unique(), key="s_select")
                    
                    with col_detail:
                        if student_name:
                            row = risk_df[risk_df['姓名'] == student_name].iloc[0]
                            tags_html = "".join([f'<span class="tag tag-brush">{t}</span>' if "秒刷" in t else (f'<span class="tag tag-warn">{t}</span>' if "缺勤" in t else f'<span class="tag tag-skip">{t}</span>') for t in row['证据链'] if t != '🟢正常'])
                            st.markdown(f"""
                            <div class="diagnosis-card">
                                <h2 style="color:#C71585; margin:0;">👤 {row['姓名']} <span style="font-size:18px; color:#666;">({row['学号']})</span></h2>
                                <hr style="border-top: 1px dashed #FFB6C1;">
                                <div style="display:flex; justify-content:space-between; margin-bottom:20px;">
                                    <div style="text-align:center;"><div style="font-size:12px; color:#888;">进度</div><div style="font-size:24px; font-weight:bold; color:#3B82F6;">{row['进度']:.1f}%</div></div>
                                    <div style="text-align:center;"><div style="font-size:12px; color:#888;">时长</div><div style="font-size:24px; font-weight:bold; color:#F59E0B;">{row['时长']:.1f}m</div></div>
                                    <div style="text-align:center;"><div style="font-size:12px; color:#888;">签到率</div><div style="font-size:24px; font-weight:bold; color:#8B5CF6;">{row.get('签到率', 100):.0f}%</div></div>
                                </div>
                                <h4 style="color:#C71585;">🩺 AI 诊断结论</h4>
                                <p style="background:#FFF0F5; padding:15px; border-radius:8px; border-left:4px solid #FF69B4; color:#C71585; font-weight:bold;">{row['异常原因']}</p>
                                <div>{tags_html}</div>
                            </div>
                            """, unsafe_allow_html=True)
                            
                            # 个体雷达图 (增强版)
                            st.markdown("#### 📊 综合能力雷达")
                            vals = [row['进度'], min(100, row['时长']/2), row['成绩'], row.get('签到率', 100), row.get('获赞', 0)*10]
                            cats = ['进度', '投入', '成绩', '签到', '影响力']
                            fig_r = go.Figure(data=go.Scatterpolar(r=vals, theta=cats, fill='toself', line_color='#FF69B4'))
                            st.plotly_chart(fig_r, use_container_width=True)

            # === VIEW 4: 未完结名单 ===
            elif "未完结名单统计" in nav:
                st.markdown("### 📉 章节任务未完结统计")
                unfinished_df = audit_df[pd.to_numeric(audit_df['进度'], errors='coerce').fillna(0) < 99.9].sort_values('进度')
                if unfinished_df.empty: st.success("🎉 全部完成！")
                else:
                    st.info(f"共有 **{len(unfinished_df)}** 名同学未完结。")
                    output = io.BytesIO()
                    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                        unfinished_df[['姓名', '学号', '进度', '时长']].to_excel(writer, index=False)
                    st.download_button("📥 导出名单", output.getvalue(), "未完结名单.xlsx")
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
                <p>支持全文件数据挖掘：签到、讨论、时长、进度综合分析</p>
            </div>
        """, unsafe_allow_html=True)

if __name__ == "__main__":
    main()