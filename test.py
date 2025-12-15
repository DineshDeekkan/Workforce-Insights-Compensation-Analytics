import streamlit as st
import pandas as pd
from sqlalchemy import create_engine
import plotly.express as px

# ------------------------------------------------------
# PAGE CONFIG
# ------------------------------------------------------
st.set_page_config(page_title="Employee Dashboard", layout="wide")
st.title("📊 Employee Analytics Dashboard")

# ------------------------------------------------------
# DATABASE CONNECTION
# ------------------------------------------------------
engine = create_engine("postgresql+psycopg2://postgres:Dinesh@localhost:5432/postgres")

@st.cache_data
def load_data():
    return pd.read_sql("SELECT * FROM updated_employees", engine)

df = load_data()

# ------------------------------------------------------
# SIDEBAR - ADVANCED CONTROL PANEL
# ------------------------------------------------------
st.sidebar.title("🧭 Control Panel")

st.sidebar.markdown("### 🎛 Filters")

# Domain Filter
domain_list = ["All"] + sorted(df["domain"].dropna().unique().tolist())
domain_filter = st.sidebar.selectbox("Domain", domain_list)

# Role Filter
role_filter = st.sidebar.multiselect("Roles", sorted(df["role"].unique()), default=sorted(df["role"].unique()))

# Level Filter
level_list = ["All"] + sorted(df["level"].dropna().unique().tolist())
level_filter = st.sidebar.selectbox("Level", level_list)

# Work Mode Filter
mode_list = ["All"] + sorted(df["mode"].dropna().unique().tolist())
mode_filter = st.sidebar.selectbox("Work Mode", mode_list)

# Year Filter
year_list = ["All"] + sorted(df["year"].dropna().unique().tolist())
year_filter = st.sidebar.selectbox("Year", year_list)

# Salary Slider
min_sal, max_sal = int(df["salary"].min()), int(df["salary"].max())
salary_filter = st.sidebar.slider("Salary Range", min_sal, max_sal, (min_sal, max_sal))

# ----------------------------
# 🔘 Toggles
# ----------------------------
st.sidebar.markdown("### 🔘 Toggles")

high_salary_only = st.sidebar.checkbox("Show Only High Salary (₹>2M)")
high_bonus_only = st.sidebar.checkbox("Show Only High Bonus")
top_roles_only = st.sidebar.checkbox("Top 5 Roles Only")

# ----------------------------
# 🔄 Reset
# ----------------------------
if st.sidebar.button("🔄 Reset All Filters"):
    st.experimental_rerun()

st.sidebar.write("---")
st.sidebar.markdown("### 💡 Smart Insights")

# ------------------------------------------------------
# APPLY FILTERS
# ------------------------------------------------------
filtered_df = df.copy()

if domain_filter != "All":
    filtered_df = filtered_df[filtered_df["domain"] == domain_filter]

if level_filter != "All":
    filtered_df = filtered_df[filtered_df["level"] == level_filter]

if mode_filter != "All":
    filtered_df = filtered_df[filtered_df["mode"] == mode_filter]

if year_filter != "All":
    filtered_df = filtered_df[filtered_df["year"] == year_filter]

filtered_df = filtered_df[
    (filtered_df["salary"] >= salary_filter[0]) &
    (filtered_df["salary"] <= salary_filter[1])
]

filtered_df = filtered_df[filtered_df["role"].isin(role_filter)]

if high_salary_only:
    filtered_df = filtered_df[filtered_df["salary"] > 2_000_000]

if high_bonus_only:
    filtered_df = filtered_df[filtered_df["bonus"] > filtered_df["bonus"].median()]

if top_roles_only:
    top_roles = filtered_df['role'].value_counts().nlargest(5).index.tolist()
    filtered_df = filtered_df[filtered_df['role'].isin(top_roles)]

# ------------------------------------------------------
# SMART INSIGHTS
# ------------------------------------------------------
try:
    highest_domain = filtered_df.groupby("domain")["salary"].mean().idxmax()
    st.sidebar.markdown(f"🏆 <b>Top Paying Domain:</b> {highest_domain}", unsafe_allow_html=True)
except:
    st.sidebar.markdown("🏆 No domain insight", unsafe_allow_html=True)

try:
    most_common_role = filtered_df["role"].value_counts().idxmax()
    st.sidebar.markdown(f"👑 <b>Most Common Role:</b> {most_common_role}", unsafe_allow_html=True)
except:
    st.sidebar.markdown("👑 No role insight", unsafe_allow_html=True)

# ------------------------------------------------------
# KPIs (Salaries in Millions)
# ------------------------------------------------------
st.subheader("📌 Key Performance Indicators")

def to_millions(value):
    return round(value / 1_000_000, 2)

k1, k2, k3, k4, k5, k6 = st.columns(6)

k1.metric("👥 Employees", len(filtered_df))
k2.metric("💰 Avg Salary (M)", f"{to_millions(filtered_df['salary'].mean())} M")
k3.metric("⬆ Max Salary (M)", f"{to_millions(filtered_df['salary'].max())} M")
k4.metric("⬇ Min Salary (M)", f"{to_millions(filtered_df['salary'].min())} M")
k5.metric("🧬 Domains", filtered_df["domain"].nunique())
k6.metric("🛠 Roles", filtered_df["role"].nunique())

# ------------------------------------------------------
# VISUALS
# ------------------------------------------------------

st.subheader("📈 Visual Insights")

col1, col2 = st.columns(2)

# Pie chart
with col1:
    fig_domain = px.pie(filtered_df, names="domain", title="Domain-wise Distribution")
    st.plotly_chart(fig_domain, use_container_width=True)

# Salary histogram
with col2:
    fig_salary = px.histogram(filtered_df, x="salary", nbins=20, title="Salary Distribution (INR)")
    st.plotly_chart(fig_salary, use_container_width=True)

# Avg salary by domain
st.subheader("📊 Average Salary by Domain")
avg_salary_domain = filtered_df.groupby("domain")["salary"].mean().reset_index().sort_values("salary", ascending=False)
fig_compare = px.bar(avg_salary_domain, x="domain", y="salary", text_auto=True, title="Average Salary by Domain", color="salary")
st.plotly_chart(fig_compare, use_container_width=True)

# Level-wise salary
st.subheader("🏆 Level-wise Salary Comparison")
avg_level_salary = filtered_df.groupby("level")["salary"].mean().reset_index().sort_values("salary", ascending=False)
fig_level = px.bar(avg_level_salary, x="level", y="salary", text_auto=True, title="Average Salary by Level", color="salary")
st.plotly_chart(fig_level, use_container_width=True)

# Salary category
st.subheader("📦 Salary Category Distribution (with %)")
salary_cat_df = filtered_df["salary_category"].value_counts().reset_index()
salary_cat_df.columns = ["salary_category", "count"]
total = salary_cat_df["count"].sum()
salary_cat_df["percentage"] = (salary_cat_df["count"] / total * 100).round(2)
salary_cat_df = salary_cat_df.sort_values("count", ascending=True)

color_map = {"Low": "#FFB3BA", "Medium": "#FFDFBA", "High": "#BAFFC9", "Very High": "#BAE1FF"}
bar_colors = [color_map.get(cat, "#A7C7E7") for cat in salary_cat_df["salary_category"]]

fig_salary_cat = px.bar(salary_cat_df, x="count", y="salary_category", orientation="h",
                        text="percentage", title="Salary Category Distribution")
fig_salary_cat.update_traces(marker_color=bar_colors)
st.plotly_chart(fig_salary_cat, use_container_width=True)

# Bonus by domain
st.subheader("💸 Average Bonus by Domain")
bonus_domain_df = filtered_df.groupby("domain")["bonus"].mean().reset_index().sort_values("bonus", ascending=False)
fig_bonus_domain = px.bar(bonus_domain_df, x="domain", y="bonus", text_auto=True, color="bonus", title="Average Bonus by Domain")
st.plotly_chart(fig_bonus_domain, use_container_width=True)

# ------------------------------------------------------
# DATA TABLE
# ------------------------------------------------------
st.subheader("📁 Filtered Employee Data")
st.dataframe(filtered_df, use_container_width=True)

# ------------------------------------------------------
# DOWNLOAD
# ------------------------------------------------------
st.subheader("⬇ Download Filtered Data")
csv_filtered = filtered_df.to_csv(index=False).encode("utf-8")
st.download_button("Download Filtered Employees", csv_filtered, "filtered_employees.csv", "text/csv")
