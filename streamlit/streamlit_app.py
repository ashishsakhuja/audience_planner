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
st.markdown('''
<style>
  /* Video background */
  .video-background { position:fixed; top:0; left:0; width:100%; height:100%; overflow:hidden; z-index:0; }
  .video-background video { position:absolute; top:5%; left:0; width:100%; height:100%; object-fit:cover; opacity:0.6; z-index:-1; }

  /* Title bubble */
  .title-bubble {
    background:rgba(255,255,255,1)!important;
    padding:1rem 1.5rem;
    border-radius:12px;
    box-shadow:0 2px 6px rgba(0,0,0,0.1);
    margin-bottom:1.5rem;
    display:inline-block;
    position:relative;
    z-index:9999;
  }
  .title-bubble h1 { margin:0; font-size:2rem; color:#212529; }
  .title-bubble p  { margin:0.5rem 0 0; font-size:1rem; color:#555; }

  /* Lock textarea + hide counter */
  div[data-testid='stTextArea'] { max-width:300px!important; margin:0 0 1rem 0!important; }
  div[data-testid='stTextArea'] textarea { width:100%!important; box-sizing:border-box!important; }
  div[data-testid='stTextArea'] > div:nth-child(3) { display:none!important; }

  /* Total Matches box */
  .matches-box {
    display:inline-block;
    background:#fff;
    border:1px solid #dee2e6;
    border-radius:8px;
    padding:0.5rem 1rem;
    margin-bottom:1rem;
    box-shadow:0 1px 3px rgba(0,0,0,0.1);
    font-weight:600;
  }

  /* Card grid */
  .card-container {
    display:grid;
    grid-template-columns:repeat(auto-fit,minmax(500px,1fr));
    gap:1.5rem;
    margin-top:1rem;
  }
  .card {
    display:flex;
    background:#f8f9fa;
    padding:1rem;
    border-radius:12px;
    border:1px solid #dee2e6;
    box-shadow:1px 2px 5px rgba(0,0,0,0.1);
    transition:transform 0.2s;
    overflow:hidden;
  }
  .card:hover { transform:scale(1.02); }
  .card img {
    width:180px;
    height:180px;
    object-fit:cover;
    border-radius:8px;
    margin-right:1rem;
    cursor:pointer;
  }
  .card-content { flex:1; display:flex; flex-direction:column; }
  .card-content h4 { margin:0 0 0.75rem; font-size:1.4rem; color:#343a40; }

  .subcards-container {
    display:flex;
    flex-direction:column;
    gap:1rem;
    margin-bottom:1rem;
  }
  .subcard {
    background:#fff;
    border:1px solid #dee2e6;
    border-radius:10px;
    padding:0.75rem 1rem;
    box-shadow:0 1px 3px rgba(0,0,0,0.05);
    transition:opacity 0.2s;
  }
  .subcard h5 {
    margin:0 0 0.5rem;
    font-size:1.1rem;
    font-weight:600;
    color:#212529;
  }
  .subcard.engagement, .subcard.campaign-fit {
    opacity:0;
    height:0;
    padding:0;
    border:none;
    box-shadow:none;
  }
  .card:hover .subcard.engagement,
  .card:hover .subcard.campaign-fit {
    opacity:1;
    height:auto;
    padding:0.75rem 1rem;
    border:1px solid #dee2e6;
    box-shadow:0 1px 3px rgba(0,0,0,0.05);
  }

  /* Summary box */
  .summary-box {
    background: #fff;
    border: 1px solid #dee2e6;
    border-radius: 8px;
    padding: 1rem;
    margin-top: 1.5rem;
    box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
  }

  /* Modal for images */
  #image-modal {
    display:none;
    position:fixed;
    z-index:10000;
    left:0; top:0;
    width:100%; height:100%;
    background:rgba(0,0,0,0.8);
  }
  #modal-content {
    position:relative;
    margin:5% auto;
    display:block;
    max-width:90%;
    max-height:90%;
    border-radius:12px;
  }
</style>
<div id='image-modal' onclick="this.style.display='none'">
  <img id='modal-content'/>
</div>
<script>
  function showModal(src){
    document.getElementById('modal-content').src = src;
    document.getElementById('image-modal').style.display = 'block';
  }
</script>
<div class='video-background'>
  <video autoplay muted loop playsinline>
    <source src='https://raw.githubusercontent.com/ashishsakhuja/audience_planner/main/UI_video_fixed.mp4' type='video/mp4'/>
  </video>
</div>
<div class='title-bubble'>
  <h1>📊 Audience Segment Agent</h1>
  <p>Use this tool to select and validate audience segments for your campaign.</p>
</div>
''', unsafe_allow_html=True)

# ─── ICON MAP & LINE FORMATTER ─────────────────────────────────────────────────
t_ICONS = {
  'Audience Segment Id':'🆔','identityGraphName':'🧠','age_range':'🎯','size':'📊',
  'income_level':'💰','location_type':'🏘️','recency':'⏱️','cpm':'📈',
  'confidence':'📌','cpmCap':'📌','estReach':'🔢','category':'📂',
  'quality_score':'⭐','data_source':'🔗','programmaticMediaPct':'📊','advertiserDirectPct':'📊'
}
def format_segment_line(line: str) -> str:
    line = line.strip()
    m = re.match(r"- \*\*(.*?)\*\*: (.*?) - (Matches|Mismatch)(.*)", line)
    if m:
        f, v, s, e = m.groups()
        icon = t_ICONS.get(f,'📌')
        if s == 'Mismatch':
            return (
                f"<div style='margin-bottom:0.5rem;'>"
                f"<strong style='color:#dc3545;'>{icon} {f}:</strong> {v} ❌<br>"
                f"<span style='color:#dc3545;font-size:0.85rem;'>{e.strip()}</span>"
                "</div>"
            )
        return f"<div style='margin-bottom:0.5rem;'><strong>{icon} {f}:</strong> {v}</div>"
    g = re.match(r"- \*\*(.*?)\*\*: (.*)", line)
    if g:
        f, v = g.groups()
        icon = t_ICONS.get(f,'📌')
        return f"<div style='margin-bottom:0.5rem;'><strong>{icon} {f}:</strong> {v}</div>"
    return f"<div style='margin-bottom:0.5rem;'>{line}</div>"

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
            "Could you please specify additional criteria "
            "(e.g., age_range, income_level, location_type, recency, or cpmCap) "
            "to narrow the results?"
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
        name = seg.get("name","Unnamed Segment")

        # demographics
        id_line   = f"- **Audience Segment Id**: {seg['segmentId']}"
        identity  = f"- **identityGraphName**: {seg['identityGraphName']}"
        age       = f"- **age_range**: {seg['age_range']['value']} - {seg['age_range']['status']} ({seg['age_range']['explanation']})"
        size      = f"- **size**: {seg['size']['value']} - {seg['size']['status']} ({seg['size']['explanation']})"
        income    = f"- **income_level**: {seg['income_level']['value']} - {seg['income_level']['status']} ({seg['income_level']['explanation']})"
        loc       = f"- **location_type**: {seg['location_type']['value']} - {seg['location_type']['status']} ({seg['location_type']['explanation']})"

        # engagement
        recency   = f"- **recency**: {seg['recency']['value']} - {seg['recency']['status']} ({seg['recency']['explanation']})"
        cpm       = f"- **cpm**: {seg['cpm']['value']} - {seg['cpm']['status']} ({seg['cpm']['explanation']})"
        cpmCap    = f"- **cpmCap**: {seg['cpmCap']['value']} - {seg['cpmCap']['status']} ({seg['cpmCap']['explanation']})"
        confidence= f"- **confidence**: {seg['confidence']['value']}"

        # campaign fit
        fit_lines=[]
        for key in ("estReach","programmaticMediaPct","advertiserDirectPct","category","quality_score","data_source"):
            val = seg.get(key)
            if isinstance(val, dict):
                v, s, exp = val.get("value",""), val.get("status"), val.get("explanation","")
                if s:
                    fit_lines.append(f"- **{key}**: {v} - {s} ({exp})")
                else:
                    fit_lines.append(f"- **{key}**: {v} ({exp})")
            else:
                fit_lines.append(f"- **{key}**: {val}")

        # build campaign ad image
        prompt_details = "\n".join([
            id_line, identity, age, size, income, loc,
            recency, cpm, cpmCap, confidence
        ])
        url = get_dalle_url(gen_prompt(query, name, prompt_details))

        # assemble HTML
        html = '<div class="card">'
        if url:
            html += (
                f"<div onclick=\"showModal('{url}')\" "
                f"style='margin-bottom:1rem;text-align:center;'>"
                f"<img src='{url}' style='max-width:100%;border-radius:8px;'/>"
                "</div>"
            )
        html += '<div class="card-content">'
        html += f"<h4>{name}</h4>"
        html += '<div class="subcards-container">'

        # Demographics
        html += '<div class="subcard"><h5>👤 Demographics</h5>'
        for line in (id_line, identity, age, size, income, loc):
            html += format_segment_line(line)
        html += '</div>'

        # Engagement
        html += '<div class="subcard engagement"><h5>📈 Engagement</h5>'
        for line in (recency, cpm, confidence, cpmCap):
            html += format_segment_line(line)
        html += '</div>'

        # Campaign Fit
        html += '<div class="subcard campaign-fit"><h5>🎯 Campaign Fit</h5>'
        for line in fit_lines:
            html += format_segment_line(line)
        html += '</div>'

        html += '</div></div></div>'
        cards.append(html)

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


