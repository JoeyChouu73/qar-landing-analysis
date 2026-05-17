import warnings
from io import BytesIO
from math import pi

import matplotlib.lines as mlines
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import seaborn as sns
import streamlit as st
from matplotlib import font_manager
from matplotlib.patches import Patch
from plotly.subplots import make_subplots

warnings.filterwarnings("ignore")

CHINESE_FONT_CANDIDATES = [
    "Microsoft YaHei",
    "SimHei",
    "PingFang SC",
    "Hiragino Sans GB",
    "Noto Sans CJK SC",
    "Noto Sans CJK JP",
    "Noto Sans CJK TC",
    "Noto Sans CJK HK",
    "Noto Serif CJK SC",
    "Noto Serif CJK JP",
    "Source Han Sans CN",
    "WenQuanYi Zen Hei",
    "WenQuanYi Micro Hei",
    "Arial Unicode MS",
    "STHeiti",
    "Songti SC",
]


def detect_chinese_font():
    try:
        font_manager.fontManager = font_manager._load_fontmanager(try_read_cache=False)
    except Exception:
        pass

    available_fonts = {f.name for f in font_manager.fontManager.ttflist}
    for font_name in CHINESE_FONT_CANDIDATES:
        if font_name in available_fonts:
            return font_name

    for font_path in font_manager.findSystemFonts(fontext="ttf") + font_manager.findSystemFonts(fontext="otf"):
        try:
            font_name = font_manager.FontProperties(fname=font_path).get_name()
        except Exception:
            continue
        if any(keyword in font_name for keyword in ["Noto Sans CJK", "Noto Serif CJK", "WenQuanYi", "Source Han"]):
            return font_name

    return "DejaVu Sans"


MATPLOTLIB_CHINESE_FONT = detect_chinese_font()
PLOTLY_FONT_FAMILY = ",".join([f"'{font}'" for font in CHINESE_FONT_CANDIDATES] + ["'DejaVu Sans'", "sans-serif"])

plt.rcParams["font.sans-serif"] = [MATPLOTLIB_CHINESE_FONT, "DejaVu Sans"]
plt.rcParams["axes.unicode_minus"] = False

st.set_page_config(
    page_title="绿色QAR着陆分析系统（静态规则版）",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
<style>
    .main-header {
        font-size: 2.4rem;
        font-weight: bold;
        text-align: center;
        color: #1f3c2f;
        margin-bottom: 1.5rem;
    }
    .sub-header {
        font-size: 1.35rem;
        font-weight: bold;
        color: #2c3e50;
        margin-top: 1rem;
        margin-bottom: 1rem;
        border-left: 4px solid #2ecc71;
        padding-left: 1rem;
    }
    .metric-card {
        background-color: #f8f9fa;
        border-radius: 10px;
        padding: 1rem;
        text-align: center;
        box-shadow: 0 2px 4px rgba(0,0,0,0.08);
    }
    .metric-value {
        font-size: 1.9rem;
        font-weight: bold;
        color: #2ecc71;
    }
    .metric-label {
        font-size: 0.9rem;
        color: #6b7280;
        margin-top: 0.4rem;
    }
    html, body, [class*="css"], [data-testid="stAppViewContainer"] {
        font-family: "Microsoft YaHei", "PingFang SC", "Noto Sans CJK SC", "SimHei", sans-serif;
    }
</style>
""",
    unsafe_allow_html=True,
)

CHECK_COLUMNS = [
    "GLIDEANGLE",
    "平飘距离",
    "着陆垂直载荷",
    "入口高度",
    "入口空速",
    "入口下降率",
    "入口横向偏差",
    "拉开始高度",
    "20英尺下降率",
    "10英尺下降率",
    "收光油门杆高度",
    "接地横向偏差",
    "接地空速",
    "接地航迹交叉",
    "着陆滑跑方向不稳定",
    "最大姿态",
    "接地姿态",
    "最大坡度",
    "接地坡度",
    "收光油门杆下降率",
    "拉反推时机",
    "收反推空速",
    "收反推地速",
    "着陆操纵者",
    "所属大队",
    "技术等级",
]

REMOVE_TECH_LEVELS = ["二级副驾驶", "三级副驾驶", "型别教员", "资深机长", "责任机长"]
REMOVE_TEAMS = ["返聘人员", "无效人员"]
ABS_COLUMNS = ["入口横向偏差", "接地横向偏差", "最大坡度", "接地坡度"]
DESCENT_RATE_COLUMNS = ["入口下降率", "20英尺下降率", "10英尺下降率", "收光油门杆下降率"]
TEAM_ORDER = ["一大队", "二大队", "三大队", "四大队", "五大队", "六大队", "七大队", "八大队", "九大队", "十大队"]
ORDERED_PARAMS = [
    "入口高度",
    "入口下降率",
    "拉开始高度",
    "20英尺下降率",
    "10英尺下降率",
    "收光油门杆高度",
    "收光油门杆下降率",
    "接地姿态",
    "平飘距离",
    "着陆垂直载荷",
    "空速差额（入口-接地）",
    "GLIDEANGLE",
    "最大姿态",
    "入口横向偏差",
    "接地横向偏差",
    "接地航迹交叉",
    "最大坡度",
    "接地坡度",
    "着陆滑跑方向不稳定",
    "拉反推时机",
    "收反推空速",
    "收反推地速",
]

# 静态固定评分规则：不再根据新上传数据重新计算绿色区间
FIXED_SCORING_RULES = {
    "GLIDEANGLE": {"green": (2.93, 3.19), "caution_lower": 2.80, "caution_upper": 3.30, "weight": 3, "type": "both"},
    "平飘距离": {"green": (1354, 1993), "caution_lower": 1034, "caution_upper": 2313, "weight": 5, "type": "both"},
    "着陆垂直载荷": {"green": (None, 1.39), "caution_lower": None, "caution_upper": 1.78, "weight": 7, "type": "upper"},
    "入口高度": {"green": (39, 48), "caution_lower": 34, "caution_upper": 53, "weight": 5, "type": "both"},
    "入口下降率": {"green": (564, 712), "caution_lower": 490, "caution_upper": 786, "weight": 3, "type": "both"},
    "入口横向偏差": {"green": (None, 2.8), "caution_lower": None, "caution_upper": 4.1, "weight": 5, "type": "upper"},
    "拉开始高度": {"green": (32, 46), "caution_lower": 25, "caution_upper": 54, "weight": 5, "type": "both"},
    "20英尺下降率": {"green": (469, 654), "caution_lower": 377, "caution_upper": 747, "weight": 3, "type": "both"},
    "10英尺下降率": {"green": (273, 465), "caution_lower": 176, "caution_upper": 562, "weight": 4, "type": "both"},
    "收光油门杆高度": {"green": (3.75, 10.99), "caution_lower": 0.13, "caution_upper": 14.61, "weight": 3, "type": "both"},
    "接地横向偏差": {"green": (None, 1.9), "caution_lower": None, "caution_upper": 2.8, "weight": 6, "type": "upper"},
    "接地航迹交叉": {"green": (None, 1.5), "caution_lower": None, "caution_upper": 3.0, "weight": 5, "type": "upper"},
    "着陆滑跑方向不稳定": {"green": (None, 1.49), "caution_lower": None, "caution_upper": 1.95, "weight": 6, "type": "upper"},
    "最大姿态": {"green": (3.4, 4.4), "caution_lower": 2.86, "caution_upper": 4.94, "weight": 5, "type": "both"},
    "接地姿态": {"green": (2.06, 3.56), "caution_lower": 1.3, "caution_upper": 4.3, "weight": 6, "type": "both"},
    "最大坡度": {"green": (None, 2.26), "caution_lower": None, "caution_upper": 2.84, "weight": 5, "type": "upper"},
    "接地坡度": {"green": (None, 0.8), "caution_lower": None, "caution_upper": 1.1, "weight": 5, "type": "upper"},
    "收光油门杆下降率": {"green": (193, 378), "caution_lower": 100, "caution_upper": 470, "weight": 3, "type": "both"},
    "拉反推时机": {"green": (None, 2.2), "caution_lower": None, "caution_upper": 3.1, "weight": 4, "type": "upper"},
    "收反推空速": {"green": (51, 63), "caution_lower": 45, "caution_upper": 69, "weight": 4, "type": "both"},
    "收反推地速": {"green": (55, 67), "caution_lower": 48, "caution_upper": 73, "weight": 3, "type": "both"},
    "空速差额（入口-接地）": {"green": (6.09, 11.35), "caution_lower": 3.46, "caution_upper": 13.98, "weight": 5, "type": "both"},
}


def init_session_state():
    defaults = {
        "df_raw": None,
        "df_processed": None,
        "df_scored": None,
        "score_columns": [],
        "analysis_done": False,
        "total_possible_score": 0,
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


@st.cache_data(show_spinner=False)
def load_data_from_bytes(file_bytes, file_name):
    file_suffix = file_name.rsplit(".", 1)[-1].lower() if "." in file_name else ""

    if file_suffix in ["xlsx", "xls"]:
        return pd.read_excel(BytesIO(file_bytes))

    try:
        return pd.read_csv(BytesIO(file_bytes), encoding="gbk")
    except UnicodeDecodeError:
        return pd.read_csv(BytesIO(file_bytes), encoding="utf-8-sig")


def load_data(uploaded_file):
    file_name = getattr(uploaded_file, "name", "")

    try:
        return load_data_from_bytes(uploaded_file.getvalue(), file_name)
    except Exception as exc:
        st.error(f"文件读取失败：{exc}")
        st.info("请确认文件格式为 CSV、XLSX 或 XLS；CSV 建议使用 GBK 或 UTF-8 编码。")
        return None


def preprocess_data(df):
    df_processed = df.copy()
    logs = []

    original_rows = len(df_processed)
    df_processed = df_processed.dropna(subset=[col for col in CHECK_COLUMNS if col in df_processed.columns])
    logs.append(f"删除缺失值: {original_rows - len(df_processed)} 行")

    if "技术等级" in df_processed.columns:
        before_filter = len(df_processed)
        df_processed = df_processed[~df_processed["技术等级"].isin(REMOVE_TECH_LEVELS)]
        logs.append(f"过滤技术等级: {before_filter - len(df_processed)} 行")

    if "所属大队" in df_processed.columns:
        before_team = len(df_processed)
        df_processed = df_processed[~df_processed["所属大队"].isin(REMOVE_TEAMS)]
        logs.append(f"过滤大队: {before_team - len(df_processed)} 行")

    if "拉反推时机" in df_processed.columns:
        before_count = len(df_processed)
        df_processed = df_processed[df_processed["拉反推时机"] >= 0]
        logs.append(f"删除拉反推时机负数: {before_count - len(df_processed)} 行")

    for col in ABS_COLUMNS:
        if col in df_processed.columns:
            df_processed.loc[:, col] = df_processed[col].abs()

    if "入口空速" in df_processed.columns and "接地空速" in df_processed.columns:
        df_processed.loc[:, "空速差额（入口-接地）"] = df_processed["入口空速"] - df_processed["接地空速"]

    for col in DESCENT_RATE_COLUMNS:
        if col in df_processed.columns:
            before_count = len(df_processed)
            df_processed = df_processed[df_processed[col] < 0]
            df_processed.loc[:, col] = df_processed[col].abs()
            removed_count = before_count - len(df_processed)
            if removed_count > 0:
                logs.append(f"{col}: 删除 {removed_count} 行非负值数据")

    return df_processed, logs


@st.cache_data(show_spinner=False)
def preprocess_data_cached(df):
    return preprocess_data(df)


def calculate_score(value, rule):
    if pd.isna(value):
        return 0.0

    green_lower, green_upper = rule["green"]
    caution_lower = rule["caution_lower"]
    caution_upper = rule["caution_upper"]
    weight = rule["weight"]

    if green_lower is not None and green_upper is not None:
        if green_lower <= value <= green_upper:
            return float(weight)
        if caution_lower is not None and value < green_lower:
            ratio = (value - caution_lower) / (green_lower - caution_lower)
            return float(weight) * max(0.0, min(1.0, ratio))
        if caution_upper is not None and value > green_upper:
            ratio = (caution_upper - value) / (caution_upper - green_upper)
            return float(weight) * max(0.0, min(1.0, ratio))
        return 0.0

    if green_lower is None and green_upper is not None:
        if value <= green_upper:
            return float(weight)
        if caution_upper is not None and value <= caution_upper:
            ratio = (caution_upper - value) / (caution_upper - green_upper)
            return float(weight) * max(0.0, min(1.0, ratio))
        return 0.0

    if green_lower is not None and green_upper is None:
        if value >= green_lower:
            return float(weight)
        if caution_lower is not None and value >= caution_lower:
            ratio = (value - caution_lower) / (green_lower - caution_lower)
            return float(weight) * max(0.0, min(1.0, ratio))
        return 0.0

    return 0.0


def classify_zone(value, rule):
    if pd.isna(value):
        return "缺失"

    green_lower, green_upper = rule["green"]
    caution_lower = rule["caution_lower"]
    caution_upper = rule["caution_upper"]

    if green_lower is not None and green_upper is not None:
        if green_lower <= value <= green_upper:
            return "绿色"
        if caution_lower is not None and caution_upper is not None and caution_lower <= value <= caution_upper:
            return "蓝色"
        return "橙色"

    if green_lower is None and green_upper is not None:
        if value <= green_upper:
            return "绿色"
        if caution_upper is not None and value <= caution_upper:
            return "蓝色"
        return "橙色"

    if green_lower is not None and green_upper is None:
        if value >= green_lower:
            return "绿色"
        if caution_lower is not None and value >= caution_lower:
            return "蓝色"
        return "橙色"

    return "未定义"


def score_dataset(df):
    df_scored = df.copy()
    available_rules = {}
    for param, rule in FIXED_SCORING_RULES.items():
        if param in df_scored.columns:
            df_scored[f"{param}_得分"] = df_scored[param].apply(lambda x: calculate_score(x, rule))
            available_rules[param] = rule
    score_columns = [f"{param}_得分" for param in available_rules]
    df_scored["总分"] = df_scored[score_columns].sum(axis=1) if score_columns else 0
    total_possible_score = sum(rule["weight"] for rule in available_rules.values())
    return df_scored, score_columns, total_possible_score, available_rules


@st.cache_data(show_spinner=False)
def score_dataset_cached(df):
    return score_dataset(df)


def prepare_rule_check_data(df, use_full_preprocess=False, auto_normalize=True):
    if use_full_preprocess:
        return preprocess_data(df)

    df_checked = df.copy()
    logs = []

    numeric_columns = set(FIXED_SCORING_RULES.keys()) | {"入口空速", "接地空速"}
    for col in numeric_columns:
        if col in df_checked.columns:
            before_missing = df_checked[col].isna().sum()
            df_checked.loc[:, col] = pd.to_numeric(df_checked[col], errors="coerce")
            after_missing = df_checked[col].isna().sum()
            new_missing = after_missing - before_missing
            if new_missing > 0:
                logs.append(f"{col}: {new_missing} 个值无法转为数字，已按缺失处理")

    if auto_normalize:
        for col in ABS_COLUMNS:
            if col in df_checked.columns:
                df_checked.loc[:, col] = df_checked[col].abs()

        for col in DESCENT_RATE_COLUMNS:
            if col in df_checked.columns:
                negative_count = int((df_checked[col] < 0).sum())
                df_checked.loc[df_checked[col] < 0, col] = df_checked.loc[df_checked[col] < 0, col].abs()
                if negative_count > 0:
                    logs.append(f"{col}: {negative_count} 个负值已转为正值用于规则判定")

    if "空速差额（入口-接地）" not in df_checked.columns and {"入口空速", "接地空速"}.issubset(df_checked.columns):
        df_checked.loc[:, "空速差额（入口-接地）"] = df_checked["入口空速"] - df_checked["接地空速"]
        logs.append("已根据入口空速和接地空速生成空速差额（入口-接地）")

    return df_checked, logs


@st.cache_data(show_spinner=False)
def prepare_rule_check_data_cached(df, use_full_preprocess=False, auto_normalize=True):
    return prepare_rule_check_data(df, use_full_preprocess, auto_normalize)


def score_and_classify_rule_data(df):
    df_result = df.copy()
    available_rules = {}

    for param, rule in FIXED_SCORING_RULES.items():
        if param not in df_result.columns:
            continue
        df_result[f"{param}_区间"] = df_result[param].apply(lambda x: classify_zone(x, rule))
        df_result[f"{param}_得分"] = df_result[param].apply(lambda x: calculate_score(x, rule))
        available_rules[param] = rule

    score_columns = [f"{param}_得分" for param in available_rules]
    df_result["总分"] = df_result[score_columns].sum(axis=1) if score_columns else 0
    total_possible_score = sum(rule["weight"] for rule in available_rules.values())
    if total_possible_score > 0:
        df_result["总得分率"] = df_result["总分"] / total_possible_score
    else:
        df_result["总得分率"] = 0

    return df_result, available_rules, score_columns, total_possible_score


@st.cache_data(show_spinner=False)
def score_and_classify_rule_data_cached(df):
    return score_and_classify_rule_data(df)


def build_rule_check_summary(df_result, scoring_rules):
    rows = []
    for param, rule in scoring_rules.items():
        zone_col = f"{param}_区间"
        score_col = f"{param}_得分"
        if zone_col not in df_result.columns or score_col not in df_result.columns:
            continue

        zone_counts = df_result[zone_col].value_counts()
        valid_count = int(df_result[param].notna().sum()) if param in df_result.columns else 0
        rows.append(
            {
                "参数": param,
                "权重": rule["weight"],
                "有效记录数": valid_count,
                "绿色": int(zone_counts.get("绿色", 0)),
                "蓝色": int(zone_counts.get("蓝色", 0)),
                "橙色": int(zone_counts.get("橙色", 0)),
                "缺失": int(zone_counts.get("缺失", 0)),
                "平均得分": round(df_result[score_col].mean(), 2),
            }
        )
    return pd.DataFrame(rows)


def build_scoring_rule_table(scoring_rules):
    rows = []
    for param, rule in scoring_rules.items():
        green_lower, green_upper = rule["green"]
        rows.append(
            {
                "参数": param,
                "绿色下限": "-" if green_lower is None else round(green_lower, 4),
                "绿色上限": "-" if green_upper is None else round(green_upper, 4),
                "蓝色下界": "-" if rule["caution_lower"] is None else round(rule["caution_lower"], 4),
                "蓝色上界": "-" if rule["caution_upper"] is None else round(rule["caution_upper"], 4),
                "权重": rule["weight"],
                "区间类型": rule["type"],
            }
        )
    return pd.DataFrame(rows)


def create_total_score_histogram(df_scored):
    fig, ax = plt.subplots(figsize=(10, 5))
    ax.hist(df_scored["总分"], bins=20, color="skyblue", edgecolor="black", alpha=0.75)
    ax.axvline(df_scored["总分"].mean(), color="red", linestyle="--", linewidth=2, label=f'均值: {df_scored["总分"].mean():.2f}')
    ax.axvline(df_scored["总分"].median(), color="green", linestyle="--", linewidth=2, label=f'中位数: {df_scored["总分"].median():.2f}')
    ax.set_xlabel("总分")
    ax.set_ylabel("频数")
    ax.set_title("航班总分分布直方图")
    ax.legend()
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    return fig


def create_score_corr_heatmap(df_scored, score_columns):
    if not score_columns:
        return None
    score_corr = df_scored[score_columns].corr()
    simplified_cols = [col.replace("_得分", "") for col in score_columns]
    score_corr.columns = simplified_cols
    score_corr.index = simplified_cols

    fig, ax = plt.subplots(figsize=(14, 12))
    mask = np.triu(np.ones_like(score_corr, dtype=bool))
    sns.heatmap(
        score_corr,
        mask=mask,
        annot=True,
        fmt=".2f",
        cmap="RdBu_r",
        center=0,
        square=True,
        linewidths=0.5,
        cbar_kws={"shrink": 0.8},
        ax=ax,
    )
    ax.set_title("各参数得分相关性热图", fontsize=14, fontweight="bold")
    ax.tick_params(axis="x", rotation=45)
    fig.tight_layout()
    return fig


def create_team_stats(df_scored):
    if "所属大队" not in df_scored.columns:
        return pd.DataFrame()
    return df_scored.groupby("所属大队")["总分"].describe().round(2).sort_values("mean", ascending=False)


def create_tech_stats(df_scored):
    if "技术等级" not in df_scored.columns:
        return pd.DataFrame()
    return df_scored.groupby("技术等级").agg({"总分": ["count", "mean", "std", "min", "max"]}).round(2)


def sort_teams(values):
    values = [str(v) for v in values if pd.notna(v) and str(v).lower() != "nan"]
    ordered = [team for team in TEAM_ORDER if team in values]
    others = sorted([team for team in values if team not in TEAM_ORDER])
    return ordered + others


def filter_dataframe(df, team="全部", tech="全部", pilot="全部"):
    filtered = df.copy()
    if team != "全部" and "所属大队" in filtered.columns:
        filtered = filtered[filtered["所属大队"].astype(str) == str(team)]
    if tech != "全部" and "技术等级" in filtered.columns:
        filtered = filtered[filtered["技术等级"].astype(str) == str(tech)]
    if pilot != "全部" and "着陆操纵者" in filtered.columns:
        filtered = filtered[filtered["着陆操纵者"].astype(str) == str(pilot)]
    return filtered


def create_pilot_distribution_figure(df_scored, scoring_rules, pilot_name):
    pilot_data = df_scored[df_scored["着陆操纵者"] == pilot_name]
    if pilot_data.empty:
        return None

    params = list(scoring_rules.keys())
    green_counts = []
    blue_counts = []
    orange_counts = []

    for param in params:
        if param not in pilot_data.columns:
            green_counts.append(0)
            blue_counts.append(0)
            orange_counts.append(0)
            continue

        zones = pilot_data[param].apply(lambda x: classify_zone(x, scoring_rules[param]))
        green_counts.append(int((zones == "绿色").sum()))
        blue_counts.append(int((zones == "蓝色").sum()))
        orange_counts.append(int((zones == "橙色").sum()))

    fig, ax = plt.subplots(figsize=(14, 12))
    y_pos = np.arange(len(params))
    ax.barh(y_pos, green_counts, color="#2E8B57", label="绿色区间", alpha=0.9)
    ax.barh(y_pos, blue_counts, left=green_counts, color="#0033A0", label="蓝色区间", alpha=0.9)
    ax.barh(y_pos, orange_counts, left=np.array(green_counts) + np.array(blue_counts), color="#FF671F", label="橙色区间", alpha=0.9)

    ax.set_yticks(y_pos)
    ax.set_yticklabels(params, fontsize=10)
    ax.set_xlabel("航班数量")
    ax.set_ylabel("参数名称")
    ax.set_title(f"{pilot_name} 各参数区间分布")
    ax.legend(loc="lower right")
    ax.grid(True, alpha=0.2, axis="x", linestyle="--")
    fig.tight_layout()
    return fig


def build_pilot_analysis_data(df_scored, scoring_rules, pilot_name):
    pilot_data = df_scored[df_scored["着陆操纵者"] == pilot_name].copy()
    if pilot_data.empty:
        return None

    best_flight = pilot_data.loc[pilot_data["总分"].idxmax()]
    worst_flight = pilot_data.loc[pilot_data["总分"].idxmin()]
    param_data = []
    param_labels = []

    for param in ORDERED_PARAMS:
        if param not in scoring_rules or param not in pilot_data.columns:
            continue
        score_col = f"{param}_得分"
        if score_col not in pilot_data.columns:
            continue

        scores = pilot_data[score_col].values
        actual_values = pilot_data[param].dropna()
        fleet_values = df_scored[param].dropna()
        fleet_mean = fleet_values.mean() if not fleet_values.empty else 0
        fleet_std = fleet_values.std() if not fleet_values.empty else 0

        zones = pilot_data[param].apply(lambda x: classify_zone(x, scoring_rules[param]))

        param_data.append(
            {
                "name": param,
                "weight": scoring_rules[param]["weight"],
                "mean": float(np.mean(scores)) if len(scores) else 0,
                "std": float(np.std(scores, ddof=1)) if len(scores) > 1 else 0,
                "green_pct": float((zones == "绿色").mean() * 100),
                "blue_pct": float((zones == "蓝色").mean() * 100),
                "orange_pct": float((zones == "橙色").mean() * 100),
                "fleet_actual_mean": fleet_mean,
                "fleet_actual_std": fleet_std,
                "pilot_actual_mean": actual_values.mean() if not actual_values.empty else 0,
                "green_lower": scoring_rules[param]["green"][0] if scoring_rules[param]["green"][0] is not None else -np.inf,
                "green_upper": scoring_rules[param]["green"][1] if scoring_rules[param]["green"][1] is not None else np.inf,
                "caution_lower": scoring_rules[param]["caution_lower"] if scoring_rules[param]["caution_lower"] is not None else -np.inf,
                "caution_upper": scoring_rules[param]["caution_upper"] if scoring_rules[param]["caution_upper"] is not None else np.inf,
            }
        )
        param_labels.append(param)

    return {
        "pilot_data": pilot_data,
        "best_flight": best_flight,
        "worst_flight": worst_flight,
        "param_data": param_data,
        "param_labels": param_labels,
    }


def create_pilot_radar_figure(analysis_data, pilot_name):
    param_data = analysis_data["param_data"]
    if len(param_data) < 3:
        return None

    angles = [n / float(len(param_data)) * 2 * pi for n in range(len(param_data))]
    angles += angles[:1]

    z_scores = []
    labels = []
    for item in param_data:
        fleet_std = item["fleet_actual_std"]
        if pd.notna(fleet_std) and fleet_std > 0:
            z_score = (item["pilot_actual_mean"] - item["fleet_actual_mean"]) / fleet_std
        else:
            z_score = 0
        z_scores.append(z_score)
        labels.append(item["name"])

    z_scores_closed = z_scores + z_scores[:1]
    max_abs_z = max(abs(min(z_scores)), abs(max(z_scores)), 1)
    max_z = max_abs_z * 1.4

    fig = plt.figure(figsize=(12, 10))
    ax = plt.subplot(111, projection="polar")
    ax.plot(angles, [0] * len(angles), "-", linewidth=2.2, color="#7f8c8d", alpha=0.8, label="机队平均")
    ax.plot(angles, z_scores_closed, "o-", linewidth=3, color="#e67e22", markersize=7, label=f"{pilot_name}平均")
    ax.fill(angles, z_scores_closed, color="#f39c12", alpha=0.12)
    ax.set_xticks(angles[:-1])
    ax.set_xticklabels(labels, fontsize=9)
    ax.set_ylim(-max_z, max_z)
    ax.set_yticks(np.arange(-2, 2.5, 1))
    ax.set_yticklabels(["-2σ", "-1σ", "0", "+1σ", "+2σ"])
    ax.set_title(f"{pilot_name} 参数雷达图（相对机队均值）", fontsize=14, fontweight="bold", pad=20)
    ax.legend(loc="upper right", bbox_to_anchor=(1.2, 1.1))
    return fig


def create_pilot_parameter_table(analysis_data):
    rows = []
    for item in analysis_data["param_data"]:
        rows.append(
            {
                "参数": item["name"],
                "权重": item["weight"],
                "平均分": round(item["mean"], 2),
                "标准差": round(item["std"], 2),
                "绿色占比": f"{item['green_pct']:.1f}%",
                "蓝色占比": f"{item['blue_pct']:.1f}%",
                "橙色占比": f"{item['orange_pct']:.1f}%",
                "机队均值": round(item["fleet_actual_mean"], 2),
                "个人均值": round(item["pilot_actual_mean"], 2),
            }
        )
    return pd.DataFrame(rows)


def build_flight_identifier_options(df_scored):
    candidates = ["FILENAME", "文件名", "航班号"]
    id_col = next((candidate for candidate in candidates if candidate in df_scored.columns), None)
    option_rows = []
    for idx, row in df_scored.iterrows():
        date_text = str(row["日期"]) if "日期" in df_scored.columns else f"行{idx}"
        pilot_text = str(row["着陆操纵者"]) if "着陆操纵者" in df_scored.columns else "未知飞行员"
        plane_text = str(row["机号"]) if "机号" in df_scored.columns else "未知机号"
        airport_text = str(row["着陆机场"]) if "着陆机场" in df_scored.columns else "未知机场"
        id_text = str(row[id_col]) if id_col else f"记录{idx}"
        option_rows.append({"label": f"{date_text} | {pilot_text} | {plane_text} | {airport_text} | {id_text}", "index": idx})
    return option_rows


def build_flight_parameter_table(flight_row, scoring_rules):
    rows = []
    for param, rule in scoring_rules.items():
        if param not in flight_row.index:
            continue
        score_col = f"{param}_得分"
        score_value = flight_row[score_col] if score_col in flight_row.index else np.nan
        green_lower, green_upper = rule["green"]
        rows.append(
            {
                "参数": param,
                "原始值": round(flight_row[param], 4) if pd.notna(flight_row[param]) else np.nan,
                "区间颜色": classify_zone(flight_row[param], rule),
                "得分": round(score_value, 4) if pd.notna(score_value) else np.nan,
                "权重": rule["weight"],
                "得分率": f"{(score_value / rule['weight'] * 100):.1f}%" if pd.notna(score_value) and rule["weight"] > 0 else "-",
                "绿色下限": "-" if green_lower is None else round(green_lower, 4),
                "绿色上限": "-" if green_upper is None else round(green_upper, 4),
                "蓝色下界": "-" if rule["caution_lower"] is None else round(rule["caution_lower"], 4),
                "蓝色上界": "-" if rule["caution_upper"] is None else round(rule["caution_upper"], 4),
            }
        )
    return pd.DataFrame(rows)


def create_flight_zone_distribution_figure(flight_param_df, flight_label):
    zone_counts = flight_param_df["区间颜色"].value_counts()
    zone_order = [label for label in ["绿色", "蓝色", "橙色", "缺失"] if label in zone_counts.index]
    if not zone_order:
        return None

    colors = {"绿色": "#2E8B57", "蓝色": "#0033A0", "橙色": "#FF671F", "缺失": "#A0A0A0"}
    values = [zone_counts[label] for label in zone_order]

    fig, ax = plt.subplots(figsize=(8, 5))
    bars = ax.bar(zone_order, values, color=[colors[label] for label in zone_order], alpha=0.9)
    for bar, value in zip(bars, values):
        ax.text(bar.get_x() + bar.get_width() / 2, value + 0.05, str(value), ha="center", va="bottom", fontsize=10, fontweight="bold")
    ax.set_ylabel("参数数量")
    ax.set_title(f"{flight_label} 参数区间分布")
    ax.grid(True, alpha=0.2, axis="y")
    fig.tight_layout()
    return fig


def create_rankings(df_scored):
    if not {"着陆操纵者", "所属大队", "技术等级", "总分"}.issubset(df_scored.columns):
        return pd.DataFrame(), pd.DataFrame(), pd.DataFrame()

    pilot_stats = (
        df_scored.groupby(["着陆操纵者", "所属大队", "技术等级"])["总分"]
        .agg(平均分="mean", 航班数="count", 标准差="std", 最低分="min", 最高分="max")
        .round(2)
        .sort_values("平均分", ascending=False)
        .reset_index()
    )
    pilot_stats.insert(0, "总体排名", range(1, len(pilot_stats) + 1))

    concern = pilot_stats[(pilot_stats["平均分"] < pilot_stats["平均分"].mean()) | (pilot_stats["标准差"] > pilot_stats["标准差"].quantile(0.75))].copy()
    concern["关注原因"] = ""
    concern.loc[concern["平均分"] < pilot_stats["平均分"].mean(), "关注原因"] += "低于平均分"
    concern.loc[concern["标准差"] > pilot_stats["标准差"].quantile(0.75), "关注原因"] += " 波动大"
    concern = concern[["总体排名", "着陆操纵者", "所属大队", "技术等级", "平均分", "标准差", "航班数", "关注原因"]]

    return pilot_stats, concern, df_scored


def render_external_rule_checker():
    st.markdown("### 外部数据规则判定")
    st.caption("上传包含任意固定规则字段的数据文件，即可按当前静态规则输出绿色、蓝色、橙色区间和得分。")

    checker_file = st.file_uploader("上传待判定文件", type=["csv", "xlsx", "xls"], key="external_rule_checker_file")
    if checker_file is not None:
        st.caption(f"当前文件大小：{checker_file.size / 1024 / 1024:.2f} MB。大文件建议优先使用 CSV，通常比 Excel 快很多。")
    c1, c2 = st.columns(2)
    with c1:
        use_full_preprocess = st.checkbox("套用完整QAR预处理逻辑", value=False, key="external_full_preprocess")
    with c2:
        auto_normalize = st.checkbox("自动修正方向值", value=True, key="external_auto_normalize", disabled=use_full_preprocess)

    st.caption("方向值修正包括：横向偏差/坡度取绝对值，下降率负值转为正值。完整预处理还会过滤缺失、指定技术等级/大队和拉反推时机负数。")

    if checker_file is None:
        st.info("请上传一份 CSV、XLSX 或 XLS。字段名只要与固定规则中的参数一致，就会被自动识别。")
        st.dataframe(build_scoring_rule_table(FIXED_SCORING_RULES), use_container_width=True, hide_index=True)
        return

    external_raw = load_data(checker_file)
    if external_raw is None:
        return

    with st.spinner("正在按固定规则判定外部数据..."):
        prepared_df, check_logs = prepare_rule_check_data_cached(
            external_raw,
            use_full_preprocess=use_full_preprocess,
            auto_normalize=auto_normalize,
        )
        result_df, external_rules, external_score_columns, total_possible_score = score_and_classify_rule_data_cached(prepared_df)

    if not external_rules:
        st.warning("未识别到可判定字段。请确认CSV列名与固定规则参数名一致。")
        st.write("可识别字段：")
        st.write("、".join(FIXED_SCORING_RULES.keys()))
        return

    missing_rule_columns = [param for param in FIXED_SCORING_RULES if param not in prepared_df.columns]
    mc1, mc2, mc3, mc4 = st.columns(4)
    mc1.metric("上传行数", f"{len(external_raw):,}")
    mc2.metric("判定行数", f"{len(result_df):,}")
    mc3.metric("识别参数", f"{len(external_rules)}")
    mc4.metric("可得总分", f"{total_possible_score:.0f}")

    if check_logs:
        with st.expander("查看本次判定处理日志"):
            for line in check_logs:
                st.write(f"- {line}")

    if missing_rule_columns:
        with st.expander("未在本次CSV中找到的规则字段"):
            st.write("、".join(missing_rule_columns))

    st.markdown("### 区间判定汇总")
    st.dataframe(build_rule_check_summary(result_df, external_rules), use_container_width=True, hide_index=True)

    st.markdown("### 判定结果预览")
    identity_columns = [col for col in ["FILENAME", "文件名", "航班号", "日期", "着陆操纵者", "所属大队", "技术等级", "机号", "着陆机场"] if col in result_df.columns]
    rule_output_columns = []
    for param in external_rules:
        rule_output_columns.extend([param, f"{param}_区间", f"{param}_得分"])
    preview_columns = identity_columns + ["总分", "总得分率"] + rule_output_columns
    preview_columns = [col for col in preview_columns if col in result_df.columns]
    st.dataframe(result_df[preview_columns].head(500), use_container_width=True, hide_index=True)

    csv_bytes = result_df.to_csv(index=False, encoding="utf-8-sig").encode("utf-8-sig")
    st.download_button(
        "下载完整判定结果CSV",
        data=csv_bytes,
        file_name="外部数据_静态规则判定结果.csv",
        mime="text/csv",
        key="download_external_rule_result",
    )


def main():
    init_session_state()

    st.markdown('<div class="main-header">✈️ 绿色QAR着陆分析系统（静态规则版）</div>', unsafe_allow_html=True)

    with st.sidebar:
        st.markdown("### 📂 数据上传")
        uploaded_file = st.file_uploader("选择数据文件", type=["csv", "xlsx", "xls"])
        if uploaded_file is not None:
            st.caption(f"文件大小：{uploaded_file.size / 1024 / 1024:.2f} MB。大文件建议优先上传 CSV。")

        if uploaded_file is not None and st.button("🔄 加载并分析"):
            with st.spinner("正在处理数据..."):
                df_raw = load_data(uploaded_file)
                if df_raw is not None:
                    df_processed, preprocess_logs = preprocess_data_cached(df_raw)
                    df_scored, score_columns, total_possible_score, scoring_rules = score_dataset_cached(df_processed)
                    st.session_state.df_raw = df_raw
                    st.session_state.df_processed = df_processed
                    st.session_state.df_scored = df_scored
                    st.session_state.score_columns = score_columns
                    st.session_state.total_possible_score = total_possible_score
                    st.session_state.analysis_done = True
                    st.session_state.preprocess_logs = preprocess_logs
                    st.success("数据分析完成！")

        st.markdown("---")
        st.markdown("### 📌 规则说明")
        st.markdown(
            """
        - 本页面使用固定绿色QAR评分规则
        - 上传新数据后直接按固定规则评分
        - 不再展示绿色区间计算与修正过程
        """
        )

    if not st.session_state.analysis_done:
        st.info("👈 如需完整分析，请先上传与原始格式一致的CSV文件并点击【加载并分析】。也可以直接使用下面的外部数据规则判定接口。")
        render_external_rule_checker()
        return

    df_raw = st.session_state.df_raw
    df_processed = st.session_state.df_processed
    df_scored = st.session_state.df_scored
    score_columns = st.session_state.score_columns
    total_possible_score = st.session_state.total_possible_score
    scoring_rules = {param: FIXED_SCORING_RULES[param] for param in FIXED_SCORING_RULES if param in df_scored.columns}

    st.markdown('<div class="sub-header">📈 数据概览</div>', unsafe_allow_html=True)
    c1, c2, c3, c4 = st.columns(4)
    removed = len(df_raw) - len(df_processed)
    c1.markdown(f'<div class="metric-card"><div class="metric-value">{len(df_raw):,}</div><div class="metric-label">原始数据行数</div></div>', unsafe_allow_html=True)
    c2.markdown(f'<div class="metric-card"><div class="metric-value">{len(df_processed):,}</div><div class="metric-label">处理后行数</div></div>', unsafe_allow_html=True)
    c3.markdown(f'<div class="metric-card"><div class="metric-value">{removed:,}</div><div class="metric-label">删除数据行数</div></div>', unsafe_allow_html=True)
    c4.markdown(f'<div class="metric-card"><div class="metric-value">{total_possible_score:.0f}</div><div class="metric-label">总可能得分</div></div>', unsafe_allow_html=True)

    with st.expander("查看预处理日志"):
        for line in st.session_state.preprocess_logs:
            st.write(f"- {line}")

    tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs(["📋 固定规则", "📊 总体分析", "🏢 分组分析", "👨‍✈️ 飞行员分析", "🛬 单航班分析", "🔎 外部数据判定"])

    with tab1:
        st.markdown("### 当前固定评分规则")
        st.dataframe(build_scoring_rule_table(scoring_rules), use_container_width=True, hide_index=True)

    with tab2:
        st.markdown("### 总分分布")
        total_fig = create_total_score_histogram(df_scored)
        st.pyplot(total_fig, use_container_width=True)
        plt.close(total_fig)

        st.markdown("### 参数得分相关性热图")
        heatmap_fig = create_score_corr_heatmap(df_scored, score_columns)
        if heatmap_fig is not None:
            st.pyplot(heatmap_fig, use_container_width=True)
            plt.close(heatmap_fig)

        st.markdown("### 评分结果预览")
        preview_columns = [col for col in ["FILENAME", "日期", "着陆操纵者", "所属大队", "技术等级", "总分"] if col in df_scored.columns]
        st.dataframe(df_scored[preview_columns + score_columns].head(300), use_container_width=True)

    with tab3:
        st.markdown("### 按大队统计")
        team_stats = create_team_stats(df_scored)
        if not team_stats.empty:
            st.dataframe(team_stats, use_container_width=True)

        st.markdown("### 按技术等级统计")
        tech_stats = create_tech_stats(df_scored)
        if not tech_stats.empty:
            st.dataframe(tech_stats, use_container_width=True)

        st.markdown("### 排名与关注对象")
        pilot_stats, concern, _ = create_rankings(df_scored)
        if not pilot_stats.empty:
            st.dataframe(pilot_stats.head(100), use_container_width=True, hide_index=True)
        if not concern.empty:
            st.markdown("**重点关注飞行员**")
            st.dataframe(concern, use_container_width=True, hide_index=True)

    with tab4:
        if "着陆操纵者" not in df_scored.columns:
            st.warning("数据中缺少“着陆操纵者”字段，无法进行飞行员分析。")
        else:
            fc1, fc2, fc3 = st.columns(3)
            with fc1:
                team_options = ["全部"] + sort_teams(df_scored["所属大队"].dropna().unique()) if "所属大队" in df_scored.columns else ["全部"]
                selected_team = st.selectbox("筛选大队", options=team_options, key="pilot_team_filter_static")
            filtered_team = filter_dataframe(df_scored, team=selected_team)

            with fc2:
                tech_options = ["全部"] + sorted(filtered_team["技术等级"].dropna().astype(str).unique().tolist()) if "技术等级" in filtered_team.columns else ["全部"]
                selected_tech = st.selectbox("筛选技术等级", options=tech_options, key="pilot_tech_filter_static")
            filtered_tech = filter_dataframe(filtered_team, tech=selected_tech)

            with fc3:
                pilot_options = sorted(filtered_tech["着陆操纵者"].dropna().astype(str).unique().tolist())
                selected_pilot = st.selectbox("选择飞行员", options=pilot_options, key="pilot_name_static") if pilot_options else None

            if not pilot_options:
                st.warning("当前筛选条件下没有可分析的飞行员。")
            else:
                analysis_data = build_pilot_analysis_data(df_scored, scoring_rules, selected_pilot)
                if analysis_data is None:
                    st.warning("未找到该飞行员的可分析数据。")
                else:
                    pc1, pc2, pc3, pc4 = st.columns(4)
                    snapshot = analysis_data["pilot_data"].iloc[0]
                    pc1.metric("所属大队", str(snapshot["所属大队"]) if "所属大队" in snapshot.index else "-")
                    pc2.metric("技术等级", str(snapshot["技术等级"]) if "技术等级" in snapshot.index else "-")
                    pc3.metric("航班数", len(analysis_data["pilot_data"]))
                    pc4.metric("平均总分", f"{analysis_data['pilot_data']['总分'].mean():.2f}")

                    radar_fig = create_pilot_radar_figure(analysis_data, selected_pilot)
                    if radar_fig is not None:
                        st.pyplot(radar_fig, use_container_width=True)
                        plt.close(radar_fig)

                    dist_fig = create_pilot_distribution_figure(df_scored, scoring_rules, selected_pilot)
                    if dist_fig is not None:
                        st.pyplot(dist_fig, use_container_width=True)
                        plt.close(dist_fig)

                    st.markdown("### 参数分析表")
                    st.dataframe(create_pilot_parameter_table(analysis_data), use_container_width=True, hide_index=True)

    with tab5:
        fc1, fc2, fc3 = st.columns(3)
        with fc1:
            team_options = ["全部"] + sort_teams(df_scored["所属大队"].dropna().unique()) if "所属大队" in df_scored.columns else ["全部"]
            selected_flight_team = st.selectbox("筛选大队", options=team_options, key="flight_team_static")
        flight_filtered = filter_dataframe(df_scored, team=selected_flight_team)

        with fc2:
            tech_options = ["全部"] + sorted(flight_filtered["技术等级"].dropna().astype(str).unique().tolist()) if "技术等级" in flight_filtered.columns else ["全部"]
            selected_flight_tech = st.selectbox("筛选技术等级", options=tech_options, key="flight_tech_static")
        flight_filtered = filter_dataframe(flight_filtered, tech=selected_flight_tech)

        with fc3:
            pilot_options = ["全部"] + sorted(flight_filtered["着陆操纵者"].dropna().astype(str).unique().tolist()) if "着陆操纵者" in flight_filtered.columns else ["全部"]
            selected_flight_pilot = st.selectbox("筛选飞行员", options=pilot_options, key="flight_pilot_static")
        flight_filtered = filter_dataframe(flight_filtered, pilot=selected_flight_pilot)

        flight_options = build_flight_identifier_options(flight_filtered)
        if not flight_options:
            st.warning("当前筛选条件下没有可用航班。")
        else:
            label_to_index = {item["label"]: item["index"] for item in flight_options}
            selected_flight_label = st.selectbox("选择航班", options=list(label_to_index.keys()), key="flight_select_static")
            flight_row = flight_filtered.loc[label_to_index[selected_flight_label]]
            flight_param_df = build_flight_parameter_table(flight_row, scoring_rules)

            mc1, mc2, mc3, mc4 = st.columns(4)
            mc1.metric("总分", f"{flight_row['总分']:.2f}")
            mc2.metric("飞行员", str(flight_row["着陆操纵者"]) if "着陆操纵者" in flight_row.index else "-")
            mc3.metric("所属大队", str(flight_row["所属大队"]) if "所属大队" in flight_row.index else "-")
            mc4.metric("技术等级", str(flight_row["技术等级"]) if "技术等级" in flight_row.index else "-")

            zone_fig = create_flight_zone_distribution_figure(flight_param_df, selected_flight_label)
            if zone_fig is not None:
                st.pyplot(zone_fig, use_container_width=True)
                plt.close(zone_fig)

            st.markdown("### 单航班参数明细")
            st.dataframe(flight_param_df, use_container_width=True, hide_index=True)

    with tab6:
        render_external_rule_checker()


if __name__ == "__main__":
    main()
