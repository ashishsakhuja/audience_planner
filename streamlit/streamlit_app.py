import streamlit as st
import json, re
from agent_runner import run_segment_agent
from knowledge.segment_knowledge_source import SegmentKnowledgeSource
from dotenv import load_dotenv
import os
import openai

# ─── Setup ──────────────────────────────────────────────────────────────────────
load_dotenv()
openai.api_key = os.getenv("OPENAI_API_KEY")
st.set_page_config(page_title="📊 Audience Segment Agent", layout="wide")

# ─── Session State ──────────────────────────────────────────────────────────────
if "history" not in st.session_state:
    st.session_state.history = []
if "active_output" not in st.session_state:
    st.session_state.active_output = None
if "active_summary" not in st.session_state:
    st.session_state.active_summary = None

# ─── CSS + Video BG + Title Bubble + Textarea Lock + Summary Box ────────────────
st.markdown('''<style>/* … your existing CSS here … */</style>''', unsafe_allow_html=True)

# ─── ICON MAP & LINE FORMATTER ─────────────────────────────────────────────────
t_ICONS = {
    'Audience Segment Id':'🆔','identityGraphName':'🧠','age_range':'🎯','size':'📊',
    'income_level':'💰','location_type':'🏘️','recency':'⏱️','cpm':'📈',
    'confidence':'📌','cpmCap':'📌','estReach':'🔢','category':'📂',
    'quality_score':'⭐','data_source':'🔗','programmaticMediaPct':'📊','advertiserDirectPct':'📊'
}
def format_segment_line(line: str) -> str:
    # … your existing formatter …

# ─── DALL·E HELPERS ─────────────────────────────────────────────────────────────
def gen_prompt(q, n, b):
    return f"Create ad for '{q}', segment '{n}':\n{b}\nStyle: bright, aspirational."
def get_dalle_url(prompt: str):
    try:
        resp = openai.images.generate(
            model='dall-e-3',
            prompt=prompt,
            n=1,
            size='1024x1024',
            response_format='url'
        )
        return resp.data[0].url
    except:
        return None

# ─── QUERY & HISTORY UI ────────────────────────────────────────────────────────
left, right = st.columns([2,1], gap='large')
with left:
    query = st.text_area('Campaign Query', height=80, placeholder='Describe your target audience…')
    run   = st.button('Run Segment Agent')
with right:
    if st.session_state.history:
        st.markdown('### 🕘 History')
        for i,h in enumerate(reversed(st.session_state.history)):
            if st.button(f"🔁 {h['query'][:25]}…", key=f'h{i}'):
                st.session_state.active_output  = h['html']
                st.session_state.active_summary = h['summary_html']

# ─── Replay previous run ───────────────────────────────────────────────────────
if st.session_state.active_output and not (run and query.strip()):
    st.markdown(st.session_state.active_output, unsafe_allow_html=True)
    if st.session_state.active_summary:
        st.markdown("---")
        st.markdown(
            f"<div class='summary-box'><h3 style='margin-top:0;'>Summary</h3>"
            f"{st.session_state.active_summary}</div>",
            unsafe_allow_html=True
        )

# ─── RUN & RENDER ───────────────────────────────────────────────────────────────
if run and query.strip():
    st.session_state.active_output  = None
    st.session_state.active_summary = None

    # 1) call agent
    with st.spinner('Finding segments…'):
        raw = run_segment_agent(query).raw

    # 2) strip any ```json``` fence
    fence_match = re.search(r"```(?:json)?\s*([\s\S]*?)```", raw)
    candidate   = fence_match.group(1) if fence_match else raw

    # 3) balanced‐brace JSON extraction
    start = candidate.find('{')
    if start == -1:
        st.error("❌ No JSON object found in the agent response.")
        st.write(candidate[:500])
        st.stop()

    depth = 0
    end   = None
    for i, ch in enumerate(candidate[start:], start):
        if ch == '{':
            depth += 1
        elif ch == '}':
            depth -= 1
            if depth == 0:
                end = i
                break

    if end is None:
        st.error("❌ Could not find the end of the JSON object.")
        st.write(candidate[start:start+500])
        st.stop()

    json_str = candidate[start:end+1]

    # ─── inject comma if summary missing ───────────────────────────────────────────
    json_str = re.sub(r'(\])(\s*)(\"summary\":)', r'\1,\2\3', json_str)

    # 4) parse JSON
    try:
        data = json.loads(json_str)
    except Exception as e:
        st.error(f"❌ JSON parse error: {e}")
        st.code(json_str[:500], language="json")
        st.stop()

    # ─── handle too many matches ──────────────────────────────────────────────────
    tm = data.get("totalMatches")
    if tm is not None and tm > 10:
        st.warning(
            f"I found {tm} segments matching your criteria. "
            "You might want to specify additional criteria "
            "(e.g., age_range, income_level, location_type, recency, or cpmCap) "
            "to narrow down your audience."
        )
    # ─── build cards ──────────────────────────────────────────────────────────────
    cards = []

    # extract summary
    summary_text = data.get("summary", "")
    st.session_state.active_summary = summary_text

    # totalMatches chip
    if tm is not None:
        cards.append(f"<div class='matches-box'>Total Matches: {tm}</div>")

    cards.append('<div class="card-container">')
    for seg in data.get("validatedSegments", []):
        # … your existing loop to build each card …
    cards.append('</div>')

    full_html = "".join(cards)
    st.session_state.active_output = full_html
    st.session_state.history.append({
        "query":       query,
        "html":        full_html,
        "summary_html": summary_text,
    })

    st.success("Segments generated successfully!")
    st.markdown(full_html, unsafe_allow_html=True)
    if st.session_state.active_summary:
        st.markdown("---")
        st.markdown(
            f"<div class='summary-box'><h3 style='margin-top:0;'>Summary</h3>"
            f"{st.session_state.active_summary}</div>",
            unsafe_allow_html=True
        )


# streamlit run streamlit/streamlit_app.py


