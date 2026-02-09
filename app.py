import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import re
import json
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
            'discuss': ['讨论', '互动'],
            'last_active': ['最后学习时间', '最近学习', '最后登录', '登录时间', '提交时间', '活跃时间', '时间戳', '最后访问', '最近访问', '最后活跃']
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

    def execute_audit(self, mode="LMS", detect_night=True, night_window=(0,5)):
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

        # 解析最后活跃时间（若存在），提取小时用于“深夜学习”检测
        if 'last_active' in c:
            try:
                last_series = pd.to_datetime(self.df[c['last_active']], errors='coerce')
                res['最后活跃时间'] = last_series
                res['最后活跃小时'] = last_series.dt.hour.fillna(-1).astype(int)
            except Exception:
                res['最后活跃时间'] = pd.NaT
                res['最后活跃小时'] = -1
        
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

        # 夜间活跃检测：若 audit 调用方要求检测且存在小时列
        if detect_night and '最后活跃小时' in res.columns:
            start_h, end_h = night_window
            def is_night(h):
                try:
                    h = int(h)
                    if start_h <= end_h:
                        return start_h <= h <= end_h
                    else:
                        # 跨午夜，例如 start=22 end=3
                        return h >= start_h or h <= end_h
                except:
                    return False

            night_mask = res['最后活跃小时'].apply(is_night)
            for i in res[night_mask].index:
                entry = res.at[i, '证据链']
                if isinstance(entry, list):
                    if '🌙深夜学习' not in entry:
                        entry = entry + ['🌙深夜学习']
                elif isinstance(entry, str):
                    if entry == '🟢正常':
                        entry = ['🌙深夜学习']
                    else:
                        entry = [entry, '🌙深夜学习']
                else:
                    entry = ['🌙深夜学习']
                res.at[i, '证据链'] = entry
                prev = res.at[i, '异常原因']
                if '深夜' not in str(prev):
                    if isinstance(prev, str) and '符合常态' in prev:
                        res.at[i, '异常原因'] = '深夜活跃'
                    else:
                        res.at[i, '异常原因'] = (str(prev) + ' | 深夜活跃') if prev else '深夜活跃'
                res.at[i, '状态'] = '异常'
        
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

            # 侧边栏：深夜活跃检测设置（教师可配置）
            st.sidebar.markdown('**深夜活跃检测**')
            detect_night = st.sidebar.checkbox('启用深夜活跃可疑检测', value=True, key='detect_night')
            night_start = st.sidebar.slider('深夜开始小时', 0, 23, 0, key='night_start')
            night_end = st.sidebar.slider('深夜结束小时', 0, 23, 5, key='night_end')

            engine = AuditCore(raw_df)
            audit_df, logic_err = engine.execute_audit(mode, detect_night=detect_night, night_window=(night_start, night_end))
            
            if audit_df is None or audit_df.empty:
                st.warning("⚠️ 数据解析为空，请检查文件。")
                return

            # 将“未完成人群”合并到“不健康/异常人群”中：
            # 对进度 < 99.9 的记录，追加证据标签并标记为异常，便于合并统计
            unfinished_mask = pd.to_numeric(audit_df['进度'], errors='coerce').fillna(0) < 99.9
            if unfinished_mask.any():
                for i in audit_df[unfinished_mask].index:
                    entry = audit_df.at[i, '证据链']
                    # 规范化并追加标签
                    if isinstance(entry, list):
                        if '⚠️未完结' not in entry:
                            entry = entry + ['⚠️未完结']
                    elif isinstance(entry, str):
                        if entry == '🟢正常':
                            entry = ['⚠️未完结']
                        else:
                            entry = [entry, '⚠️未完结']
                    else:
                        entry = ['⚠️未完结']
                    audit_df.at[i, '证据链'] = entry
                    prev = audit_df.at[i, '异常原因']
                    if '未完结' not in str(prev):
                        if isinstance(prev, str) and '符合常态' in prev:
                            audit_df.at[i, '异常原因'] = '未完结'
                        else:
                            audit_df.at[i, '异常原因'] = (str(prev) + ' | 未完结') if prev else '未完结'
                    audit_df.at[i, '状态'] = '异常'

            risk_count = len(audit_df[audit_df['状态']=='异常'])
            # 修复未完结统计逻辑（保持未完结下载视图用）
            unfinished_count = len(audit_df[pd.to_numeric(audit_df['进度'], errors='coerce').fillna(0) < 99.9])
            
            # 侧边栏：综合得分权重（可调）
            st.sidebar.markdown("---")
            st.sidebar.markdown("**综合得分权重（归一化后应用）**")
            w_prog = st.sidebar.slider('进度 权重', 0.0, 1.0, 0.4, 0.05, key='w_prog')
            w_score = st.sidebar.slider('成绩 权重', 0.0, 1.0, 0.3, 0.05, key='w_score')
            w_time = st.sidebar.slider('时长 权重', 0.0, 1.0, 0.2, 0.05, key='w_time')
            w_discuss = st.sidebar.slider('讨论 权重', 0.0, 1.0, 0.1, 0.05, key='w_discuss')
            # 归一化权重
            total_w = (w_prog + w_score + w_time + w_discuss)
            if total_w == 0:
                w_prog = w_score = w_time = w_discuss = 0.25
                total_w = 1.0
            w_prog /= total_w; w_score /= total_w; w_time /= total_w; w_discuss /= total_w

            # 权重配置管理（导出/导入）
            st.sidebar.markdown('**权重配置管理**')
            cfg = {
                'w_prog': st.session_state.get('w_prog', w_prog),
                'w_score': st.session_state.get('w_score', w_score),
                'w_time': st.session_state.get('w_time', w_time),
                'w_discuss': st.session_state.get('w_discuss', w_discuss),
            }
            cfg_bytes = json.dumps(cfg, ensure_ascii=False).encode('utf-8')
            st.sidebar.download_button('导出当前权重配置 (JSON)', cfg_bytes, 'weights_config.json')
            uploaded_cfg = st.sidebar.file_uploader('加载权重配置 (JSON)', type=['json'], key='load_weights')
            if uploaded_cfg is not None:
                try:
                    loaded = json.load(uploaded_cfg)
                    for k, v in loaded.items():
                        st.session_state[k] = v
                    st.experimental_rerun()
                except Exception as e:
                    st.sidebar.error(f'配置加载失败: {e}')

            # 计算综合得分（0-100），使用 min-max 归一化（稳健处理常量列）
            def safe_minmax(s):
                s = pd.to_numeric(s, errors='coerce').fillna(0).astype(float)
                mn = s.min(); mx = s.max()
                if pd.isna(mn) or pd.isna(mx) or mx == mn:
                    return pd.Series(0.5, index=s.index)
                return (s - mn) / (mx - mn)

            prog_norm = audit_df['进度'].clip(0,100) / 100.0 if '进度' in audit_df.columns else pd.Series(0.0, index=audit_df.index)
            time_norm = safe_minmax(audit_df['时长']) if '时长' in audit_df.columns else pd.Series(0.0, index=audit_df.index)
            score_norm = safe_minmax(audit_df['成绩']) if '成绩' in audit_df.columns else pd.Series(0.0, index=audit_df.index)
            discuss_norm = safe_minmax(audit_df['讨论']) if '讨论' in audit_df.columns else pd.Series(0.0, index=audit_df.index)

            audit_df['综合得分'] = (prog_norm * w_prog + score_norm * w_score + time_norm * w_time + discuss_norm * w_discuss) * 100
            # 计算班内百分位与分组（用于排名/分层）
            if '综合得分' in audit_df.columns:
                audit_df['综合百分位'] = audit_df['综合得分'].rank(pct=True).mul(100)
                n_bins = st.sidebar.slider('分层组数 (用于排名，越大越细)', 2, 10, 4, key='n_bins')
                bin_idx = (audit_df['综合百分位'] * n_bins / 100.0).apply(np.ceil).clip(1, n_bins).astype(int)
                labels = []
                for i in range(1, n_bins+1):
                    lo = int((i-1) * 100 / n_bins)
                    hi = int(i * 100 / n_bins)
                    labels.append(f"{lo}-{hi}%")
                audit_df['综合分组'] = bin_idx.apply(lambda x: labels[x-1])

            # 参与度权重（老师可调）
            st.sidebar.markdown('**学习参与度权重（讨论 / 时长稳定 / 完整率）**')
            p_w_discuss = st.sidebar.slider('讨论 权重', 0.0, 1.0, 0.4, 0.05, key='p_w_discuss')
            p_w_stability = st.sidebar.slider('时长稳定性 权重', 0.0, 1.0, 0.3, 0.05, key='p_w_stability')
            p_w_complete = st.sidebar.slider('提交完整率(进度) 权重', 0.0, 1.0, 0.3, 0.05, key='p_w_complete')
            p_total = (p_w_discuss + p_w_stability + p_w_complete)
            if p_total == 0:
                p_w_discuss = p_w_stability = p_w_complete = 1/3
                p_total = 1.0
            p_w_discuss /= p_total; p_w_stability /= p_total; p_w_complete /= p_total

            # 计算参与度：讨论频次（discuss_norm） + 时长稳定性 + 提交完整率（prog_norm）
            # discuss_norm 已计算为 discuss_norm
            discuss_norm = discuss_norm if 'discuss_norm' in locals() else (safe_minmax(audit_df['讨论']) if '讨论' in audit_df.columns else pd.Series(0.0, index=audit_df.index))
            # 时长稳定性：接近中位时长视为稳定
            if '时长' in audit_df.columns:
                time_norm_local = time_norm if 'time_norm' in locals() else safe_minmax(audit_df['时长'])
                median_t = time_norm_local.median()
                stability_raw = 1 - (time_norm_local - median_t).abs()
                if stability_raw.max() == stability_raw.min():
                    stability_norm = pd.Series(0.5, index=stability_raw.index)
                else:
                    stability_norm = (stability_raw - stability_raw.min()) / (stability_raw.max() - stability_raw.min())
            else:
                stability_norm = pd.Series(0.0, index=audit_df.index)

            prog_norm_local = prog_norm if 'prog_norm' in locals() else (audit_df['进度'].clip(0,100) / 100.0 if '进度' in audit_df.columns else pd.Series(0.0, index=audit_df.index))

            audit_df['参与度'] = (discuss_norm * p_w_discuss + stability_norm * p_w_stability + prog_norm_local * p_w_complete) * 100

            # 参与度阈值（低参与标记）
            low_part_thr = st.sidebar.slider('低参与度阈值', 0, 100, 40, key='low_part_thr')
            low_part_mask = pd.to_numeric(audit_df['参与度'], errors='coerce').fillna(0) < low_part_thr
            if low_part_mask.any():
                def add_low_part_tag(x):
                    if isinstance(x, list):
                        return x + ['🟠参与度低'] if '🟠参与度低' not in x else x
                    if isinstance(x, str):
                        if x == '🟢正常':
                            return ['🟠参与度低']
                        return [x, '🟠参与度低']
                    return ['🟠参与度低']

                audit_df.loc[low_part_mask, '证据链'] = audit_df.loc[low_part_mask, '证据链'].apply(add_low_part_tag)
                audit_df.loc[low_part_mask, '异常原因'] = audit_df.loc[low_part_mask, '异常原因'].apply(lambda x: (str(x) + ' | 参与度低') if '参与度低' not in str(x) else x)
                audit_df.loc[low_part_mask, '状态'] = '异常'

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
                    # 优先显示计算得出的综合得分平均值
                    avg_val = audit_df['综合得分'].mean() if '综合得分' in audit_df.columns else (audit_df["进度" if mode=="LMS" else "成绩"].mean())
                    c4.markdown(f'<div class="stat-box"><div class="stat-val">{avg_val:.1f}</div><div class="stat-label">平均综合得分</div></div>', unsafe_allow_html=True)

                    col_chart1, col_chart2 = st.columns(2)
                    with col_chart1:
                        st.markdown('<div class="main-card"><h5>🎨 证据画像分布</h5>', unsafe_allow_html=True)
                        tags_flat = []
                        for entry in audit_df['证据链']:
                            if isinstance(entry, list):
                                tags_flat.extend([t for t in entry if t != '🟢正常'])
                            elif isinstance(entry, str):
                                if entry != '🟢正常':
                                    tags_flat.append(entry)
                        if not tags_flat:
                            tags_flat = ["🟢正常"]
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
                
                tab1, tab2, tab3 = st.tabs(["🔥 关联性分析", "🧩 智能聚类画像", "📈 时序热力图"])
                
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

                    # --- 时长 vs 成绩 回归拟合与异常值检测 ---
                    if '时长' in audit_df.columns and '成绩' in audit_df.columns:
                        x = audit_df['时长']
                        y = audit_df['成绩']
                        mask = x.notna() & y.notna()
                        if mask.sum() > 2:
                            coeff = np.polyfit(x[mask], y[mask], 1)
                            trend = np.poly1d(coeff)
                            fig_fit = px.scatter(audit_df, x='时长', y='成绩', title='时长 vs 成绩 散点与线性拟合', color_discrete_sequence=['#FFB6C1'])
                            xs = np.linspace(x.min(), x.max(), 50)
                            fig_fit.add_trace(go.Scatter(x=xs, y=trend(xs), mode='lines', line=dict(color='red', dash='dash'), name='线性拟合'))
                            st.plotly_chart(fig_fit, use_container_width=True)

                            # 简单异常值检测（z-score）
                            outliers = pd.DataFrame()
                            for col in ['时长', '成绩']:
                                if col in audit_df.columns:
                                    col_mean = audit_df[col].mean()
                                    col_std = audit_df[col].std()
                                    if col_std and not np.isnan(col_std):
                                        z = (audit_df[col] - col_mean) / col_std
                                        audit_df[f'{col}_z'] = z
                            # 标出任一指标 z-score 超过 2 的记录
                            if any(c.endswith('_z') for c in audit_df.columns):
                                z_cols = [c for c in audit_df.columns if c.endswith('_z')]
                                outlier_mask = audit_df[z_cols].abs().max(axis=1) > 2
                                outliers = audit_df[outlier_mask][['姓名','时长','成绩'] + z_cols]
                                if not outliers.empty:
                                    st.markdown('#### ⚠️ 检测到异常值 (任一指标 |z|>2)')
                                    st.dataframe(outliers.reset_index(drop=True), use_container_width=True)

                    # --- 新增：学习效率分析（进度/时长） ---
                    if '时长' in audit_df.columns and '进度' in audit_df.columns:
                        # 计算效率（单位：进度百分比/分钟）
                        with np.errstate(divide='ignore', invalid='ignore'):
                            eff = audit_df['进度'] / audit_df['时长'].replace(0, np.nan)
                        audit_df['效率(进度/分)'] = eff.fillna(0)

                        st.markdown('#### 📊 学习效率分析 (进度% / 时长(分))')
                        ce1, ce2 = st.columns([3,1])
                        with ce1:
                            fig_eff = px.histogram(audit_df, x='效率(进度/分)', nbins=30, title='学习效率分布', color_discrete_sequence=['#FFB6C1'])
                            st.plotly_chart(fig_eff, use_container_width=True)
                        with ce2:
                            # 计算安全的上界与默认阈值
                            valid_eff = audit_df['效率(进度/分)'].replace([np.inf, -np.inf], np.nan).dropna()
                            max_val = float(valid_eff.max()) if not valid_eff.empty else 100.0
                            default_thr = float(np.nanpercentile(valid_eff, 90)) if not valid_eff.empty else max_val * 0.5
                            eff_thr = st.slider('效率上界阈值 (用于标记高效可疑)', min_value=0.0, max_value=max(max_val * 2.0, default_thr + 1.0), value=default_thr, step=0.1, key='eff_thr')
                            st.caption('阈值用于识别可能的“速刷/高效可疑”行为，可调整灵敏度。')

                        # 列出高/低效率学生
                        top_eff = audit_df.sort_values('效率(进度/分)', ascending=False).head(10)[['姓名', '进度', '时长', '效率(进度/分)']]
                        low_eff = audit_df.sort_values('效率(进度/分)').head(10)[['姓名', '进度', '时长', '效率(进度/分)']]
                        st.markdown('**效率 Top10（可能异常高效）**')
                        st.dataframe(top_eff.reset_index(drop=True), use_container_width=True)
                        st.markdown('**效率 最低10（学习投入高但产出低）**')
                        st.dataframe(low_eff.reset_index(drop=True), use_container_width=True)

                        # 散点视图：时长 vs 效率
                        fig_sc = px.scatter(audit_df, x='时长', y='效率(进度/分)', hover_name='姓名', title='时长 vs 学习效率', color_discrete_sequence=['#FF6B6B'])
                        st.plotly_chart(fig_sc, use_container_width=True)

                        # 将高效可疑者标注到证据链与异常原因中
                        try:
                            sus_mask = audit_df['效率(进度/分)'] > eff_thr
                            if sus_mask.any():
                                def add_high_eff_tag(x):
                                    if isinstance(x, list):
                                        return x + ['🚨高效可疑'] if '🚨高效可疑' not in x else x
                                    if isinstance(x, str):
                                        if x == '🟢正常':
                                            return ['🚨高效可疑']
                                        return [x, '🚨高效可疑']
                                    return ['🚨高效可疑']

                                audit_df.loc[sus_mask, '证据链'] = audit_df.loc[sus_mask, '证据链'].apply(add_high_eff_tag)
                                audit_df.loc[sus_mask, '异常原因'] = audit_df.loc[sus_mask, '异常原因'].apply(lambda x: (str(x) + ' | 高效异常') if '高效异常' not in str(x) else x)
                                audit_df.loc[sus_mask, '状态'] = '异常'
                        except Exception:
                            pass

                    # --- 新增：综合得分分布与排名展示 ---
                    if '综合得分' in audit_df.columns:
                        st.markdown('#### 🧾 综合得分分布与排名')
                        comp_col1, comp_col2 = st.columns([3,1])
                        with comp_col1:
                            fig_comp = px.histogram(audit_df, x='综合得分', nbins=20, title='综合得分分布', color_discrete_sequence=['#B19CD9'])
                            fig_comp.add_vline(x=audit_df['综合得分'].mean(), line_dash='dash', line_color='red', annotation_text='平均综合得分')
                            st.plotly_chart(fig_comp, use_container_width=True)
                        with comp_col2:
                            top_comp = audit_df.sort_values('综合得分', ascending=False).head(10)[['姓名','综合得分']]
                            low_comp = audit_df.sort_values('综合得分').head(10)[['姓名','综合得分']]
                            st.markdown('**Top 综合得分**')
                            st.table(top_comp.reset_index(drop=True))
                            st.markdown('**Lowest 综合得分**')
                            st.table(low_comp.reset_index(drop=True))
                        # --- 新增：参与度分布与低参与名单 ---
                        if '参与度' in audit_df.columns:
                            st.markdown('#### 📣 学习参与度分布与低参与预警')
                            pcol1, pcol2 = st.columns([3,1])
                            with pcol1:
                                fig_part = px.histogram(audit_df, x='参与度', nbins=20, title='参与度分布', color_discrete_sequence=['#FFD580'])
                                fig_part.add_vline(x=audit_df['参与度'].mean(), line_dash='dash', line_color='red', annotation_text='平均参与度')
                                st.plotly_chart(fig_part, use_container_width=True)
                            with pcol2:
                                low_p = audit_df.sort_values('参与度').head(10)[['姓名','参与度']]
                                st.markdown('**低参与 Top10**')
                                st.table(low_p.reset_index(drop=True))

                            # 参与度 vs 综合得分 散点
                            if '综合得分' in audit_df.columns:
                                fig_pp = px.scatter(audit_df, x='参与度', y='综合得分', hover_name='姓名', title='参与度 vs 综合得分')
                                st.plotly_chart(fig_pp, use_container_width=True)

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
                        # 群体汇总统计与导出
                        st.markdown("---")
                        st.markdown("**群体/班级汇总统计**")
                        grp = audit_df.groupby('学习群体').agg(
                            人数=('姓名', 'count'),
                            平均时长=('时长', 'mean'),
                            平均成绩=('成绩', 'mean'),
                            未完结率=('进度', lambda s: (pd.to_numeric(s, errors='coerce').fillna(0) < 99.9).mean()),
                            平均综合得分=('综合得分', 'mean'),
                            平均参与度=('参与度', 'mean')
                        ).reset_index()
                        # 美化数值
                        for col in ['平均时长', '平均成绩', '平均综合得分', '平均参与度']:
                            if col in grp.columns:
                                grp[col] = grp[col].round(1)
                        grp['未完结率'] = (grp['未完结率'] * 100).round(1).astype(str) + '%'
                        st.dataframe(grp, use_container_width=True)

                        output_grp = io.BytesIO()
                        with pd.ExcelWriter(output_grp, engine='xlsxwriter') as writer:
                            grp.to_excel(writer, index=False, sheet_name='群体汇总')
                            # 同时写入全表供老师进一步分析
                            audit_df.to_excel(writer, index=False, sheet_name='全班明细')
                        output_grp.seek(0)
                        st.download_button('📥 导出群体统计与明细', output_grp.getvalue(), '群体统计.xlsx')

                with tab3:
                    st.markdown('#### 📈 时序热力图 & 学习路径覆盖')
                    st.caption('展示按小时的活跃分布与进度覆盖率，支持按群体/分组拆分。')

                    # 时序热力图（基于最后活跃小时）
                    if '最后活跃小时' in audit_df.columns:
                        df_hour = audit_df[audit_df['最后活跃小时'] >= 0].copy()
                        if not df_hour.empty:
                            group_col = '学习群体' if '学习群体' in audit_df.columns else ('综合分组' if '综合分组' in audit_df.columns else None)
                            if group_col:
                                pivot = pd.crosstab(df_hour[group_col], df_hour['最后活跃小时']).reindex(columns=list(range(24)), fill_value=0)
                                fig_heat = px.imshow(pivot.values, x=pivot.columns, y=pivot.index, labels={'x':'小时','y':'群体','color':'人数'}, color_continuous_scale='YlOrRd')
                                st.plotly_chart(fig_heat, use_container_width=True)
                                # 导出数据
                                out_h = io.BytesIO()
                                pivot.to_excel(out_h, sheet_name='hour_pivot')
                                out_h.seek(0)
                                st.download_button('📥 导出时序矩阵', out_h.getvalue(), '时序矩阵.xlsx')
                            else:
                                counts = df_hour['最后活跃小时'].value_counts().reindex(list(range(24)), fill_value=0)
                                fig_bar = px.bar(x=counts.index, y=counts.values, labels={'x':'小时','y':'活跃人数'}, title='按小时活跃人数')
                                st.plotly_chart(fig_bar, use_container_width=True)
                        else:
                            st.info('未检测到可用于时序分析的活跃时间数据。')
                    else:
                        st.info('数据中未包含“最后活跃时间”字段，无法绘制时序热力图。')

                    # 学习路径覆盖率（进度覆盖）
                    if '进度' in audit_df.columns:
                        bins = list(range(0, 110, 10))
                        audit_df['进度区间'] = pd.cut(audit_df['进度'].fillna(0), bins=bins, include_lowest=True, right=False)
                        cov_grp = audit_df.groupby('进度区间').size().reset_index(name='人数')
                        cov_grp['占比'] = (cov_grp['人数'] / cov_grp['人数'].sum() * 100).round(1)
                        # 将区间转换为字符串以避免 Plotly JSON 序列化错误
                        cov_grp['进度区间'] = cov_grp['进度区间'].astype(str)
                        # 使用 Plotly Graph Objects，确保传入的 x/y/text 为原生 Python 列表，避免序列化错误
                        x_vals = cov_grp['进度区间'].astype(str).tolist()
                        y_vals = cov_grp['人数'].tolist()
                        text_vals = cov_grp['占比'].astype(str).tolist()
                        fig_cov = go.Figure(data=[go.Bar(x=x_vals, y=y_vals, text=text_vals, marker_color='#7DD3FC')])
                        fig_cov.update_layout(title='学习路径覆盖：进度区间人数分布', xaxis_title='进度区间', yaxis_title='人数')
                        st.plotly_chart(fig_cov, use_container_width=True)
                        st.markdown('**进度覆盖表**')
                        st.table(cov_grp)
                    else:
                        st.info('无进度数据可用于覆盖率计算。')

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
                        output.seek(0)
                        st.download_button("📥 导出诊断报告", output.getvalue(), "异常诊断表.xlsx", use_container_width=True)
                        
                        student_name = st.radio("点击查看详情：", risk_df['姓名'].unique(), key="s_select")
                    
                    with col_detail:
                        if student_name:
                            row = risk_df[risk_df['姓名'] == student_name].iloc[0]
                            # 安全生成标签 HTML（适配 list / str / empty）
                            entry = row.get('证据链', []) if isinstance(row, (pd.Series, dict)) else row['证据链']
                            tags_list = []
                            if isinstance(entry, list):
                                tags_list = [t for t in entry if t != '🟢正常']
                            elif isinstance(entry, str):
                                if entry != '🟢正常':
                                    tags_list = [entry]
                            tags_html = ''
                            for t in tags_list:
                                if '秒刷' in t:
                                    cls = 'tag-brush'
                                elif '存疑' in t or '未开始' in t:
                                    cls = 'tag-skip'
                                elif '正常' in t:
                                    cls = 'tag-none'
                                else:
                                    cls = 'tag-pass'
                                tags_html += f'<span class="tag {cls}">{t}</span>'

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
                                            <div style="text-align:center;">
                                                <div style="font-size:12px; color:#888;">综合得分</div>
                                                <div style="font-size:20px; font-weight:bold; color:#D946EF;">{row.get('综合得分', 0):.1f}</div>
                                                <div style="font-size:12px; color:#999;">({row.get('综合百分位', 0):.1f}百分位)</div>
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
                    output.seek(0)
                    st.download_button("📥 导出未完结名单", output.getvalue(), "未完结名单.xlsx")
                    
                    unfinished_df['进度条'] = unfinished_df['进度'].apply(lambda x: f'<div style="background:#eee;width:100px;height:8px;border-radius:4px;"><div style="background:#3B82F6;width:{x}px;height:8px;border-radius:4px;"></div></div>')
                    st.write(unfinished_df[['姓名', '学号', '进度', '进度条']].to_html(escape=False, index=False), unsafe_allow_html=True)

            # === VIEW 5: 原始表 ===
            elif "原始数据表" in nav:
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