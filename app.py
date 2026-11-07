"""ResumeIQ — ATS resume analyzer & AI career coach (Streamlit UI)."""
import os
from io import BytesIO
from pathlib import Path

import plotly.graph_objects as go
import streamlit as st
from dotenv import load_dotenv

from src.analyzer import analyze
from src.parser import extract_text
from src.skills import group_by_category

load_dotenv()
st.set_page_config(page_title="ResumeIQ — ATS Resume Analyzer", page_icon="🎯", layout="wide")

SAMPLES = Path(__file__).parent / "samples"
BLUE, GREEN, ORANGE, RED, MUTED = "#2a78d6", "#1baf7a", "#eb6834", "#d63c3c", "#8a8f98"

st.markdown(
    """
    <style>
      .chip {display:inline-block; padding:4px 10px; margin:3px 4px 3px 0; border-radius:999px;
             font-size:0.85rem; font-weight:500; border:1px solid transparent}
      .chip.ok {background:rgba(27,175,122,.12); color:#0f7a54; border-color:rgba(27,175,122,.35)}
      .chip.miss {background:rgba(235,104,52,.12); color:#b4461c; border-color:rgba(235,104,52,.35)}
      .chip.extra {background:rgba(138,143,152,.12); color:#555b64; border-color:rgba(138,143,152,.35)}
      .cat {font-size:.78rem; text-transform:uppercase; letter-spacing:.05em; color:#8a8f98; margin-top:.6rem}
      .bullet-row {padding:.45rem 0; border-bottom:1px solid rgba(128,128,128,.15); font-size:.92rem}
    </style>
    """,
    unsafe_allow_html=True,
)


def chips(items, kind):
    return "".join(f'<span class="chip {kind}">{i}</span>' for i in items) or "<i>None</i>"


def grouped_chips(items, kind):
    html = ""
    for cat, skills in group_by_category(items).items():
        html += f'<div class="cat">{cat}</div>{chips(skills, kind)}'
    return html or "<i>None</i>"


def gauge(score: int) -> go.Figure:
    color = GREEN if score >= 65 else ORANGE if score >= 50 else RED
    fig = go.Figure(go.Indicator(
        mode="gauge+number", value=score, number={"suffix": "/100", "font": {"size": 40}},
        gauge={
            "axis": {"range": [0, 100], "visible": False},
            "bar": {"color": color, "thickness": 0.75},
            "bgcolor": "rgba(128,128,128,.12)", "borderwidth": 0,
        },
    ))
    fig.update_layout(height=220, margin=dict(l=20, r=20, t=10, b=0), paper_bgcolor="rgba(0,0,0,0)")
    return fig


def breakdown_chart(breakdown: dict) -> go.Figure:
    maxima = {"Skills match": 40, "Keywords": 20, "Sections": 15, "Impact": 15, "Contact & format": 10}
    labels = list(maxima)[::-1]
    pct = [breakdown[k] / maxima[k] * 100 for k in labels]
    fig = go.Figure()
    fig.add_bar(y=labels, x=[100] * len(labels), orientation="h", marker_color="rgba(128,128,128,.13)",
                hoverinfo="skip", showlegend=False)
    fig.add_bar(y=labels, x=pct, orientation="h", marker_color=BLUE, showlegend=False,
                text=[f"{breakdown[k]:g} / {maxima[k]}" for k in labels], textposition="outside",
                hovertemplate="%{y}: %{x:.0f}%<extra></extra>")
    fig.update_layout(barmode="overlay", height=220, margin=dict(l=0, r=60, t=10, b=0),
                      xaxis=dict(visible=False, range=[0, 118]), bargap=0.45,
                      paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
    return fig


# ---------------- Sidebar ----------------
with st.sidebar:
    st.title("🎯 ResumeIQ")
    st.caption("ATS resume analyzer & AI career coach")
    server_key = os.getenv("GEMINI_API_KEY", "")
    if not server_key:
        try:
            server_key = st.secrets.get("GEMINI_API_KEY", "")
        except Exception:
            server_key = ""
    user_key = st.text_input(
        "Gemini API key" + (" (optional)" if server_key else " (for AI Coach)"), type="password",
        placeholder="Using the app's built-in key" if server_key else "Paste your key",
        help="Free key: https://aistudio.google.com/apikey — ATS analysis works without it.",
    )
    api_key = user_key or server_key
    st.divider()
    st.markdown("**How the score works**")
    st.markdown(
        "- 40 · Skills required by the job\n- 20 · Job keywords\n- 15 · Standard sections\n"
        "- 15 · Impact (numbers & action verbs)\n- 10 · Contact info & length"
    )
    st.caption("🔒 Your resume is processed in memory and never stored.")

# ---------------- Inputs ----------------
st.title("Will your resume pass the ATS?")
st.write("Upload your resume and paste a job description to get an instant match score, "
         "skill gaps and AI-powered rewrites.")

use_sample = st.toggle("Try with a sample resume & job description", value=False)
left, right = st.columns(2)
with left:
    if use_sample:
        st.info("📄 Using **samples/sample_resume.pdf** (fictional candidate)")
        uploaded = None
    else:
        uploaded = st.file_uploader("Your resume", type=["pdf", "docx", "txt"])
with right:
    default_jd = (SAMPLES / "sample_job_description.txt").read_text() if use_sample else ""
    jd = st.text_area("Job description", value=default_jd, height=220,
                      placeholder="Paste the full job posting here…")

if st.button("Analyze resume", type="primary", disabled=not ((uploaded or use_sample) and jd.strip())):
    try:
        if use_sample:
            data, name = (SAMPLES / "sample_resume.pdf").read_bytes(), "sample_resume.pdf"
        else:
            data, name = uploaded.getvalue(), uploaded.name
        resume_text = extract_text(BytesIO(data), name)
        if len(resume_text.split()) < 50:
            st.error("Could not read enough text. Is this a scanned image PDF? Try a DOCX or text-based PDF.")
            st.stop()
        st.session_state.report = analyze(resume_text, jd)
        st.session_state.resume_text, st.session_state.jd = resume_text, jd
        st.session_state.pop("coach", None)
    except ValueError as exc:
        st.error(str(exc))

report = st.session_state.get("report")
if not report:
    st.stop()

# ---------------- Results ----------------
st.divider()
c1, c2, c3 = st.columns([1.1, 1.6, 1.1])
with c1:
    st.markdown("#### Match score")
    st.plotly_chart(gauge(report.score), width="stretch", config={"displayModeBar": False})
    st.markdown(f"<div style='text-align:center;font-weight:600'>{report.grade}</div>", unsafe_allow_html=True)
with c2:
    st.markdown("#### Score breakdown")
    st.plotly_chart(breakdown_chart(report.breakdown), width="stretch", config={"displayModeBar": False})
with c3:
    st.markdown("#### At a glance")
    total = len(report.matched_skills) + len(report.missing_skills)
    st.metric("Required skills matched", f"{len(report.matched_skills)} / {total}")
    st.metric("Bullets with numbers", f"{report.quantified_ratio:.0%}")
    st.metric("Word count", report.word_count)

tab_skills, tab_kw, tab_struct, tab_tips, tab_ai = st.tabs(
    ["🧩 Skills", "🔑 Keywords", "📋 Structure & impact", "💡 Suggestions", "🤖 AI Coach"]
)

with tab_skills:
    a, b = st.columns(2)
    with a:
        st.markdown(f"**✅ Matched ({len(report.matched_skills)})**")
        st.markdown(grouped_chips(report.matched_skills, "ok"), unsafe_allow_html=True)
    with b:
        st.markdown(f"**⚠️ Missing from your resume ({len(report.missing_skills)})**")
        st.markdown(grouped_chips(report.missing_skills, "miss"), unsafe_allow_html=True)
    with st.expander(f"Other skills on your resume ({len(report.extra_skills)})"):
        st.markdown(chips(report.extra_skills, "extra"), unsafe_allow_html=True)

with tab_kw:
    st.markdown(f"Your resume contains **{report.keyword_coverage:.0%}** of the job's most important keywords.")
    st.progress(report.keyword_coverage)
    st.markdown("**Found**")
    st.markdown(chips(report.matched_keywords, "ok"), unsafe_allow_html=True)
    st.markdown("**Not found**")
    st.markdown(chips(report.missing_keywords, "miss"), unsafe_allow_html=True)

with tab_struct:
    s1, s2 = st.columns(2)
    with s1:
        st.markdown("**Sections**")
        for name, ok in report.sections.items():
            st.markdown(f"{'✅' if ok else '➖'} {name}")
    with s2:
        st.markdown("**Contact details**")
        for name, ok in report.contact.items():
            st.markdown(f"{'✅' if ok else '❌'} {name}")
    st.markdown("**Bullet point audit**")
    from src.analyzer import ACTION_VERBS, NUMBER_RE  # noqa: E402

    for bullet in report.bullets:
        has_num = bool(NUMBER_RE.search(bullet))
        has_verb = bullet.split()[0].lower().strip(",.") in ACTION_VERBS
        tags = ("🔢" if has_num else "⚪") + (" 💪" if has_verb else " ⚪")
        st.markdown(f"<div class='bullet-row'>{tags}&nbsp;&nbsp;{bullet}</div>", unsafe_allow_html=True)
    st.caption("🔢 contains a number · 💪 starts with an action verb")

with tab_tips:
    for i, tip in enumerate(report.suggestions, 1):
        st.markdown(f"**{i}.** {tip}")

with tab_ai:
    if not api_key:
        st.info("Add a free Gemini API key in the sidebar to get a tailored summary, rewritten bullets, "
                "likely interview questions and a learning plan.")
    elif st.button("✨ Generate AI coaching", type="primary"):
        from src.ai import coach

        with st.spinner("Your AI coach is reading your resume…"):
            try:
                st.session_state.coach = coach(
                    st.session_state.resume_text, st.session_state.jd, report.missing_skills, api_key)
            except Exception as exc:
                st.error(f"AI request failed: {exc}")
    result = st.session_state.get("coach")
    if result:
        st.markdown("##### ✍️ Tailored summary")
        st.success(result["summary"])
        st.markdown("##### 🔁 Stronger bullet points")
        for item in result["rewritten_bullets"]:
            st.markdown(f"~~{item['original']}~~  \n➡️ **{item['improved']}**")
        q, l = st.columns(2)
        with q:
            st.markdown("##### 🎤 Likely interview questions")
            for x in result["interview_questions"]:
                st.markdown(f"- {x}")
        with l:
            st.markdown("##### 📚 Learning plan")
            for x in result["learning_plan"]:
                st.markdown(f"- {x}")
