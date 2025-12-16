import streamlit as st
import pandas as pd
import os
from sqlalchemy import create_engine
import plotly.express as px

# ------------------------------------------------------
# PAGE CONFIG
# ------------------------------------------------------
st.set_page_config(page_title="Employee Dashboard", layout="wide")
st.title("📊 Workforce Insights & Compensation Analytics")

# ------------------------------------------------------
# DATABASE CONNECTION (NEON - SAFE)
# ------------------------------------------------------

DATABASE_URL = os.getenv("DATABASE_URL")

@st.cache_resource
def get_engine():
    return create_engine(
        DATABASE_URL,
        pool_pre_ping=True
    )

engine = get_engine()

# ------------------------------------------------------
# ONE-TIME DATABASE SEED (RUNS ONLY IF TABLE EMPTY)
# ------------------------------------------------------

@st.cache_resource
def seed_database():
    try:
        # ✅ Check ACTUAL row count
        count_df = pd.read_sql(
            "SELECT COUNT(*) AS cnt FROM public.updated_employees",
            engine
        )

        if count_df.loc[0, "cnt"] > 0:
            return f"Data already exists ({count_df.loc[0, 'cnt']} rows)"

    except:
        pass  # table does not exist → load data

    # ⬇️ FORCE LOAD CSV INTO NEON
    csv_url = (
        "https://raw.githubusercontent.com/"
        "DineshDeekkan/Workforce-Insights-Compensation-Analytics/"
        "main/updated_employees.csv"
    )

    df_seed = pd.read_csv(csv_url)

    df_seed.to_sql(
        "updated_employees",
        engine,
        index=False,
        if_exists="replace",
        schema="public"
    )

    return f"Data loaded ({len(df_seed)} rows)"


seed_status = seed_database()
st.caption(f"🗄 DB status: {seed_status}")

# ------------------------------------------------------
# LOAD DATA SAFELY
# ------------------------------------------------------
@st.cache_data
def load_data(_seed_status):
    return pd.read_sql(
        "SELECT * FROM public.updated_employees",
        engine
    )

df = load_data(seed_status)

# ------------------------------------------------------
# SALARY NORMALIZATION (FINAL SOURCE = salary_in_usd)
# ------------------------------------------------------

st.write("Sample salary_in_usd values:")
st.write(df["salary_in_usd"].head(20))

df["salary_usd_clean"] = (
    df["salary_in_usd"]
    .astype(str)
    .str.replace(",", "", regex=False)
    .str.extract(r"(\d+\.?\d*)")[0]
)

df["salary_usd_clean"] = pd.to_numeric(
    df["salary_usd_clean"], errors="coerce"
)

# Convert USD → Lakhs (₹ ≈ 83, 1 lakh ≈ 1200 USD)
df["salary_lakhs"] = df["salary_usd_clean"] / 1200

# Keep valid salaries only
df = df[df["salary_lakhs"] > 0]

st.write("Salary Lakhs Stats AFTER CONVERSION:")
st.write(df["salary_lakhs"].describe())

# ------------------------------------------------------
# SIDEBAR - ADVANCED CONTROL PANEL
# ------------------------------------------------------
st.sidebar.title("🧭 Control Panel")
st.sidebar.markdown("### 🎛 Filters")

# Domain Filter
domain_list = ["All"] + sorted(df["domain"].dropna().unique().tolist())
domain_filter = st.sidebar.selectbox("Domain", domain_list)

# Role Filter
role_filter = st.sidebar.multiselect(
    "Roles",
    sorted(df["role"].unique()),
    default=sorted(df["role"].unique())
)

# Level Filter
level_list = ["All"] + sorted(df["level"].dropna().unique().tolist())
level_filter = st.sidebar.selectbox("Level", level_list)

# Work Mode Filter
mode_list = ["All"] + sorted(df["mode"].dropna().unique().tolist())
mode_filter = st.sidebar.selectbox("Work Mode", mode_list)

# Year Filter
year_list = ["All"] + sorted(df["year"].dropna().unique().tolist())
year_filter = st.sidebar.selectbox("Year", year_list)

sal_min = df["salary_lakhs"].min(skipna=True)
sal_max = df["salary_lakhs"].max(skipna=True)

if pd.isna(sal_min) or pd.isna(sal_max) or sal_min >= sal_max:
    st.sidebar.warning("Salary filter unavailable due to data issues")
    salary_filter = (0, float("inf"))
else:
    min_sal = int(sal_min)
    max_sal = int(sal_max)

    salary_filter = st.sidebar.slider(
        "Salary Range (Lakhs)",
        min_sal,
        max_sal,
        (min_sal, max_sal)
    )

# ----------------------------
# 🔘 Toggles
# ----------------------------
st.sidebar.markdown("### 🔘 Toggles")

high_salary_only = st.sidebar.checkbox("Show Only High Salary (> 20 Lakhs)")
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
    (filtered_df["salary_lakhs"] >= salary_filter[0]) &
    (filtered_df["salary_lakhs"] <= salary_filter[1])
]

filtered_df = filtered_df[filtered_df["role"].isin(role_filter)]

if high_salary_only:
    filtered_df = filtered_df[filtered_df["salary_lakhs"] > 20]

if high_bonus_only:
    filtered_df = filtered_df[filtered_df["bonus"] > filtered_df["bonus"].median()]

if top_roles_only:
    top_roles = filtered_df["role"].value_counts().nlargest(5).index
    filtered_df = filtered_df[filtered_df["role"].isin(top_roles)]

# ------------------------------------------------------
# SMART INSIGHTS
# ------------------------------------------------------
try:
    highest_domain = filtered_df.groupby("domain")["salary_lakhs"].mean().idxmax()
    st.sidebar.markdown(
        f"🏆 <b>Top Paying Domain:</b> {highest_domain}",
        unsafe_allow_html=True
    )
except:
    st.sidebar.markdown("🏆 No domain insight")

try:
    most_common_role = filtered_df["role"].value_counts().idxmax()
    st.sidebar.markdown(
        f"👑 <b>Most Common Role:</b> {most_common_role}",
        unsafe_allow_html=True
    )
except:
    st.sidebar.markdown("👑 No role insight")

# ------------------------------------------------------
# KPIs
# ------------------------------------------------------
st.subheader("📌 Key Performance Indicators")

def to_millions(val):
    return round(val / 1_000_000, 2)

k1, k2, k3, k4, k5, k6 = st.columns(6)

k1.metric("👥 Employees", len(filtered_df))
k2.metric("💰 Avg Salary (Lakhs)", round(filtered_df["salary_lakhs"].mean(), 2))
k3.metric("⬆ Max Salary (Lakhs)", round(filtered_df["salary_lakhs"].max(), 2))
k4.metric("⬇ Min Salary (Lakhs)", round(filtered_df["salary_lakhs"].min(), 2))
k5.metric("🧬 Domains", filtered_df["domain"].nunique())
k6.metric("🛠 Roles", filtered_df["role"].nunique())

# ------------------------------------------------------
# VISUALS
# ------------------------------------------------------
st.subheader("📈 Visual Insights")

col1, col2 = st.columns(2)

with col1:
    fig_domain = px.pie(filtered_df, names="domain", title="Domain-wise Distribution")
    st.plotly_chart(fig_domain, use_container_width=True)

with col2:
    fig_salary = px.histogram(filtered_df, x="salary_lakhs", nbins=20, title="Salary Distribution (Lakhs)")
    st.plotly_chart(fig_salary, use_container_width=True)

st.subheader("📊 Average Salary by Domain")
avg_salary_domain = (
    filtered_df.groupby("domain")["salary_lakhs"]
    .mean()
    .reset_index()
    .sort_values("salary_lakhs", ascending=False)
)
st.plotly_chart(
    px.bar(avg_salary_domain, x="domain", y="salary_lakhs", text_auto=True),
    use_container_width=True
)

st.subheader("🏆 Level-wise Salary Comparison")
avg_level_salary = (
    filtered_df.groupby("level")["salary_lakhs"]
    .mean()
    .reset_index()
    .sort_values("salary_lakhs", ascending=False)
)
st.plotly_chart(
    px.bar(avg_level_salary, x="level", y="salary_lakhs", text_auto=True),
    use_container_width=True
)

# ------------------------------------------------------
# DATA TABLE + DOWNLOAD
# ------------------------------------------------------
st.subheader("📁 Filtered Employee Data")
st.dataframe(filtered_df, use_container_width=True)

st.subheader("⬇ Download Filtered Data")
st.download_button(
    "Download Filtered Employees",
    filtered_df.to_csv(index=False),
    "filtered_employees.csv",
    "text/csv"
)
