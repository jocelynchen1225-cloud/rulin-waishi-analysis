# 忽略无关警告（干净终端输出）
import warnings
warnings.filterwarnings('ignore')

# 导入所需库
import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import folium
from streamlit_folium import st_folium

# --------------------------
# 1. 页面配置（标题、图标）
# --------------------------
st.set_page_config(
    page_title="《儒林外史》1-20回地点-人物-活动分析",
    page_icon="📜",
    layout="wide"  # 宽屏显示，方便可视化
)

# 页面标题和说明
st.title("📜《儒林外史》1-20回地点-人物-活动交互分析")
st.markdown("""
本应用基于中国哲学书电子化计划（Ctext）文本，统计1-20回核心地点出现频次、分析人物活动类型分布，并通过GIS地图可视化地理特征。
数据来源：https://ctext.org/rulin-waishi
""")

# --------------------------
# 2. 读取数据（100%匹配你的表头，直接读取Excel）
# --------------------------
@st.cache_data  # 缓存数据，加快加载速度
def load_data():
    # 此处填写你的Excel文件完整路径（Mac系统示例，根据实际路径修改）
    df = pd.read_excel("rulin_waishi_data.xlsx")
    # 数据预处理：确保关键列格式正确（避免可视化报错）
    df["章回"] = pd.to_numeric(df["章回"], errors="coerce").fillna(0).astype(int)
    df["北纬"] = pd.to_numeric(df["北纬"], errors="coerce").fillna(0)
    df["东经"] = pd.to_numeric(df["东经"], errors="coerce").fillna(0)
    df["本章频次"] = pd.to_numeric(df["本章频次"], errors="coerce").fillna(0).astype(int)
    df["总频次"] = pd.to_numeric(df["总频次"], errors="coerce").fillna(0).astype(int)
    return df

# 加载数据并显示基本信息
df = load_data()
st.subheader("📊 数据概览")
st.write(f"共统计 {len(df)} 条有效记录，覆盖 {df['地点'].nunique()} 个核心地点、{df['人物'].nunique()} 位关键人物")
# 数据概览显示所有表头列，顺序与Excel一致
st.dataframe(df[["章回", "地点", "北纬", "东经", "人物", "活动类型", "活动描述", "原文摘录", "本章频次", "总频次"]].head(10), width='stretch')

# --------------------------
# 3. 交互式筛选器（适配你的表头）
# --------------------------
st.sidebar.header("🔍 筛选条件")
selected_location = st.sidebar.multiselect(
    "选择地点",
    options=df["地点"].unique(),
    default=df["地点"].unique()  # 默认选中所有地点
)
selected_activity = st.sidebar.multiselect(
    "选择活动类型",
    options=df["活动类型"].unique(),
    default=df["活动类型"].unique()  # 默认选中所有活动类型
)
selected_chapter = st.sidebar.multiselect(
    "选择章回",
    options=df["章回"].unique(),
    default=df["章回"].unique()  # 默认选中所有章回
)

# 根据筛选条件过滤数据
filtered_df = df[
    (df["地点"].isin(selected_location)) & 
    (df["活动类型"].isin(selected_activity)) &
    (df["章回"].isin(selected_chapter))
]

# --------------------------
# 4. 可视化1：地点出现频次对比（柱状图，无警告）
# --------------------------
st.subheader("📈 核心地点总出现频次对比")
# 计算各地点总频次（按总频次列取唯一值，避免重复计算）
location_freq = filtered_df.groupby("地点")["总频次"].first().sort_values(ascending=False)

# 设置中文字体（Mac系统适配，避免中文乱码）
plt.switch_backend('Agg')

# 字体设置：只保留服务器必有的 Unicode 字体，不找本地字体
plt.rcParams['font.sans-serif'] = ['Arial Unicode MS', 'Songti SC', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False


# 绘制柱状图（修复palette警告，保持颜色效果）
fig, ax = plt.subplots(figsize=(10, 6))
sns.barplot(
    x=location_freq.index, 
    y=location_freq.values, 
    ax=ax, 
    hue=location_freq.index,  # 新增hue参数，消除警告
    palette="viridis", 
    legend=False  # 关闭多余图例
)
ax.set_title("各地点总出现频次（10-20回）", fontsize=14)
ax.set_xlabel("地点", fontsize=12)
ax.set_ylabel("总频次", fontsize=12)
ax.tick_params(axis='x', rotation=45)  # 地点名称旋转45度，避免重叠

# 在柱子上标注具体数值
for i, v in enumerate(location_freq.values):
    ax.text(i, v + 0.1, str(int(v)), ha='center', va='bottom')

st.pyplot(fig)


# 绘制堆叠柱状图
fig2, ax2 = plt.subplots(figsize=(12, 7))
activity_cross.plot(kind="bar", stacked=True, ax=ax2, colormap="Set2")
ax2.set_title("各地点活动类型分布（按次数统计）", fontsize=14)
ax2.set_xlabel("地点", fontsize=12)
ax2.set_ylabel("活动次数", fontsize=12)
ax2.legend(title="活动类型", bbox_to_anchor=(1.05, 1), loc='upper left')  # 图例放在右侧
ax2.tick_params(axis='x', rotation=45)

st.pyplot(fig2)

# --------------------------
# 6. 可视化3：GIS地图可视化（优化版：更大更醒目）
# --------------------------
st.subheader("🗺️ 核心地点GIS可视化")
# 计算各地点的平均经纬度（避免同一地点多次标注）
location_coords = filtered_df.groupby("地点").agg({
    "北纬": "mean",
    "东经": "mean",
    "总频次": "first"  # 总频次取第一个值（同一地点总频次一致）
}).reset_index()

# 过滤掉经纬度为0的无效数据
location_coords = location_coords[(location_coords["北纬"] != 0) & (location_coords["东经"] != 0)]

# 创建folium地图（中心设为江南+京师中间点，适配南北双核心，更合理）
m = folium.Map(location=[35.0, 118.0], zoom_start=8, tiles="Cartodb positron")

# 给每个地点添加标记（优化：更大气泡+加粗边框+高亮颜色+悬浮提示）
for _, row in location_coords.iterrows():
    # 气泡半径：直接用总频次（比原来大2倍以上，更醒目），最低半径3避免太小看不见
    radius = row["总频次"] if row["总频次"] > 0 else 3
    # 收集该地点的活动详情和人物（保持原有逻辑，优化展示格式）
    location_details = filtered_df[filtered_df["地点"] == row["地点"]]
    activity_stats = location_details["活动类型"].value_counts().to_string()
    person_list = location_details["人物"].unique().tolist()
    person_str = "、".join(person_list) if person_list else "无"
    
    # 弹出窗口内容（优化：字体加粗+换行清晰+样式美化，更易读）
    popup_content = f"""
    <div style="font-size:14px; line-height:1.5;">
    <strong style="color:#2E86AB; font-size:16px;">{row['地点']}</strong><br>
    <strong>总出现频次：</strong>{int(row['总频次'])}<br>
    <strong>涉及人物：</strong>{person_str}<br>
    <strong>活动类型分布：</strong><br>
    <pre style="font-size:12px; margin:0;">{activity_stats}</pre>
    </div>
    """
    # 按频次设置气泡颜色（更鲜艳的渐变色，醒目度大幅提升）
    if row["总频次"] >= 10:
        color = "#E74C3C"  # 高频：红色（最醒目）
        border_color = "#C0392B"  # 加深边框，增强立体感
    elif row["总频次"] >= 5:
        color = "#3498DB"  # 中频：蓝色
        border_color = "#2980B9"
    else:
        color = "#F39C12"  # 低频：橙色
        border_color = "#D35400"
    
    # 添加圆形标记（核心优化：更大半径+加粗边框+更高不透明度）
    folium.CircleMarker(
        location=[row["北纬"], row["东经"]],
        radius=radius,  # 半径放大（原：总频次/2 → 现：直接用总频次）
        color=border_color,  # 边框颜色加深，更醒目
        weight=3,  # 边框加粗（原默认1，现3，立体感更强）
        fill=True,
        fill_color=color,
        fill_opacity=0.8,  # 不透明度提升（原0.7→0.8，颜色更鲜艳）
        popup=folium.Popup(popup_content, max_width=350),  # 弹窗宽度优化
        tooltip=row["地点"]  # 新增：鼠标悬浮显示地点名称，快速识别
    ).add_to(m)

# 在Streamlit中显示地图（高度放大，更清晰）
st_folium(m, width=1200, height=700)

# --------------------------
# 7. 详细数据展示（100%匹配你的表头，无遗漏列）
# --------------------------
st.subheader("📋 详细数据记录")
st.dataframe(
    filtered_df[["章回", "地点", "北纬", "东经", "人物", "活动类型", "活动描述", "原文摘录", "本章频次", "总频次"]],
    width='stretch'  # 适配新版本，消除use_container_width警告
)

# --------------------------
# 8. 数据下载功能（完整保留所有列）
# --------------------------
st.sidebar.markdown("### 📥 数据下载")
# 生成CSV格式数据供下载（包含所有表头列）
csv_data = filtered_df[["章回", "地点", "北纬", "东经", "人物", "活动类型", "活动描述", "原文摘录", "本章频次", "总频次"]].to_csv(index=False, encoding="utf-8-sig")
st.sidebar.download_button(
    label="下载筛选后数据（CSV）",
    data=csv_data,
    file_name="儒林外史_10-20回地点分析数据.csv",
    mime="text/csv"
)
