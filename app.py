import streamlit as st
import pdfplumber
from docx import Document
import io
from openai import OpenAI
import plotly.graph_objects as go

# ================================
# DeepSeek 接口（新式 OpenAI v1）
# ================================
client = OpenAI(
    #api_key="sk-9a02aa26015e41fb95c002cedbbea02e",
    api_key=st.secrets["OPENAI_API_KEY"],  # 建议在 Streamlit Secrets 里放 API Key
    base_url="https://api.deepseek.com"    # DeepSeek 网关
)

# ================================
# 页面配置
# ================================
st.set_page_config(
    page_title="📄 候选人简历智能分析系统",
    page_icon="📄",
    layout="centered"
)

st.markdown(
    """
    # 📄 **候选人简历智能分析系统**
    <span style="font-size: 16px;">选择岗位 JD、补充要求、调节评分权重，一键生成候选人报告、风险预警、招聘建议与面试追问，支持实时 Chat 提问。</span>
    """,
    unsafe_allow_html=True
)

st.markdown("---")

# ================================
# 1️⃣ 上传简历
# ================================
st.subheader("📎 1️⃣ 上传候选人简历")
uploaded_file = st.file_uploader(
    "请上传 PDF 或 Word 格式的简历文件",
    type=["pdf", "docx"]
)

# ================================
# 2️⃣ 岗位库选择 + 个性化补充
# ================================
st.subheader("✏️ 2️⃣ 选择岗位 JD & 可补充要求")

job_library = {
    "人力资源数据分析师": "岗位职责：负责 HR 数据分析、报告生成与数据可视化，要求熟练使用 Python 和 Excel，三年以上人力资源工作经验。",
    "项目管理专员": "岗位职责：协助项目经理规划与跟踪项目进度，及时沟通和协调跨部门资源。",
    "高级市场策划": "岗位职责：策划市场推广活动，撰写宣传方案，具备三年以上品牌策划经验。"
}

jd_choice = st.selectbox(
    "📌 从岗位库选择 JD",
    list(job_library.keys())
)

st.text_area(
    "已选 JD（不可编辑）",
    job_library[jd_choice],
    height=150,
    disabled=True
)

jd_addition = st.text_area(
    "✏️ 可在标准 JD 基础上补充要求（选填）：",
    placeholder="例如：需要英语沟通能力、能接受短期出差等..."
)

# 拼接最终 JD
final_jd = job_library[jd_choice] + ("\n\n补充要求：" + jd_addition if jd_addition.strip() else "")

# ================================
# 简历解析函数
# ================================
def extract_text(file, ext):
    if ext == "pdf":
        with pdfplumber.open(io.BytesIO(file.read())) as pdf:
            return "\n".join([p.extract_text() or "" for p in pdf.pages])
    elif ext == "docx":
        doc = Document(io.BytesIO(file.read()))
        return "\n".join([p.text for p in doc.paragraphs])
    else:
        return ""

# ================================
# 右侧 Sidebar：信息卡 + 权重调节 + Chat
# ================================
st.sidebar.header("⚙️ 分析参数 & 信息")

# 权重调节
st.sidebar.subheader("🔧 评分标准权重")
weight_outstanding = st.sidebar.slider("核心能力突出性", 10, 50, 30)
weight_stability = st.sidebar.slider("能力持续性与稳定性", 10, 50, 30)
weight_risk = st.sidebar.slider("潜在阻碍因子", 10, 50, 20)
weight_fit = st.sidebar.slider("岗位/团队/生态适应度", 10, 50, 20)

total_weight = weight_outstanding + weight_stability + weight_risk + weight_fit
st.sidebar.markdown(f"**🎯 权重总和：{total_weight}%**")

if total_weight != 100:
    st.sidebar.warning("⚠️ 总和应等于 100%")

# 文件信息卡
if uploaded_file:
    st.sidebar.subheader("📎 当前候选人简历")
    st.sidebar.info(
        f"- 文件名：**{uploaded_file.name}**\n"
        f"- 文件大小：**{uploaded_file.size/1024:.1f} KB**"
    )

# JD 信息卡
st.sidebar.subheader("📌 当前岗位 JD")
st.sidebar.info(
    f"- 选中岗位：**{jd_choice}**\n"
    f"- 是否有补充：{'✅ 有补充' if jd_addition.strip() else '❌ 无补充'}"
)

# Sidebar 实时 Chat
st.sidebar.subheader("💬 侧栏实时提问")
user_question_sidebar = st.sidebar.text_input("输入你的问题")
if user_question_sidebar and st.sidebar.button("🔍 侧栏提问"):
    if uploaded_file and final_jd.strip():
        resume_text_temp = extract_text(uploaded_file, uploaded_file.name.split(".")[-1].lower())
        prompt = f"""
基于以下简历与 JD，简洁专业回答 HR 的提问。

---
【简历】
{resume_text_temp[:2000]}

---
【JD】
{final_jd}

---
【HR 提问】
{user_question_sidebar}

请开始：
"""
        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=[{"role": "user", "content": prompt}]
        )
        st.sidebar.success(response.choices[0].message.content)
    else:
        st.sidebar.warning("请先上传简历并选择 JD！")

# ================================
# 主报告函数（含风险预警 & 决策建议）
# ================================
def generate_main_report(resume, jd, w1, w2, w3, w4):
    prompt = f"""
你是一名具有人性材质学分析背景的 HR 顾问。请根据以下简历与 JD，结合以下自定义权重：
- 核心能力突出性：{w1}%
- 能力持续性与稳定性：{w2}%
- 潜在阻碍因子：{w3}%
- 岗位/团队/生态适应度：{w4}%

生成完整候选人分析报告，包括：

【1️⃣ 核心能力突出性】  
【2️⃣ 能力持续性与稳定性】  
【3️⃣ 可能的阻碍因子】  
【4️⃣ 岗位匹配度】  
【5️⃣ 团队适应度】  
【6️⃣ 企业生态适应度】  
【7️⃣ 推荐工资区间】  
【8️⃣ 人才画像】  
【9️⃣ 候选人风险预警】  
- 总结潜在风险标签（如：跳槽频繁、履历中断、冲突倾向等）。

【🔟 招聘决策建议】  
- 给出是否推荐录用 / 面试验证 / 不建议录用，并简要理由。

中文输出，客观专业，分模块。

---
【简历】
{resume[:2000]}

---
【JD】
{jd}

请开始：
"""
    response = client.chat.completions.create(
        model="deepseek-chat",
        messages=[{"role": "user", "content": prompt}]
    )
    return response.choices[0].message.content

# ================================
# 追问问题生成
# ================================
def generate_followup_questions(resume, jd):
    prompt = f"""
根据以下简历与 JD，生成 5~10 个有针对性的面试追问问题，帮助面试官核实候选人的能力、稳定性及潜在风险。

---
【简历】
{resume[:2000]}

---
【JD】
{jd}

请开始：
"""
    response = client.chat.completions.create(
        model="deepseek-chat",
        messages=[{"role": "user", "content": prompt}]
    )
    return response.choices[0].message.content

# ================================
# 页面执行逻辑：主区按钮
# ================================
if uploaded_file:
    ext = uploaded_file.name.split(".")[-1].lower()
    resume_text = extract_text(uploaded_file, ext)
    st.success(f"✅ 简历已解析，约 {len(resume_text)} 字")

    st.markdown("---")
    st.subheader("🚀 3️⃣ 选择需要执行的操作")

    if st.button("📑 生成分析报告（含风险预警 & 决策建议）"):
        if not final_jd.strip():
            st.warning("⚠️ JD 不能为空！")
        elif total_weight != 100:
            st.warning("⚠️ 权重总和必须等于 100%！")
        else:
            with st.spinner("正在生成，请稍候..."):
                main_report = generate_main_report(
                    resume_text, final_jd,
                    weight_outstanding, weight_stability, weight_risk, weight_fit
                )
                st.subheader("📑 **候选人分析报告**")
                st.info(main_report)

    if st.button("💡 生成面试官追问建议"):
        if not final_jd.strip():
            st.warning("⚠️ JD 不能为空！")
        else:
            with st.spinner("正在生成，请稍候..."):
                followup = generate_followup_questions(resume_text, final_jd)
                st.subheader("💡 **面试官追问建议**")
                st.info(followup)

    # （可选）主区也留一个实时 Chat
    st.markdown("---")
    st.subheader("💬 4️⃣ 实时 Chat 提问")
    user_question_main = st.text_input("输入你的问题（基于简历与 JD）")
    if user_question_main and st.button("🔍 主区提问"):
        with st.spinner("AI 正在分析，请稍候..."):
            prompt = f"""
基于以下简历与 JD，只针对 HR 的提问作答，简洁专业。

---
【简历】
{resume_text[:2000]}

---
【JD】
{final_jd}

---
【HR 提问】
{user_question_main}

请开始：
"""
            response = client.chat.completions.create(
                model="deepseek-chat",
                messages=[{"role": "user", "content": prompt}]
            )
            st.success(response.choices[0].message.content)

else:
    st.info("👆 请先上传候选人简历以继续。")
