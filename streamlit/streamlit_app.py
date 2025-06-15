import streamlit as st
from agent_runner import run_segment_agent
from knowledge.segment_knowledge_source import SegmentKnowledgeSource
from dotenv import load_dotenv
import os
import openai
import re

# load environment and API key
dotenv_path = load_dotenv()
openai.api_key = os.getenv("OPENAI_API_KEY")

st.set_page_config(page_title="📊 Audience Segment Agent", layout="wide")

# Initialize session state for history and outputs
if "history" not in st.session_state:
    st.session_state.history = []
if "active_output" not in st.session_state:
    st.session_state.active_output = None
if "active_summary" not in st.session_state:
    st.session_state.active_summary = None

# ——————————————————————————————————————————————————
# CSS, Video Background, Title Bubble, Modal, Textbox, Card Styles + Hover
# ——————————————————————————————————————————————————
st.markdown('''
<style>
  .video-background { position:fixed; top:0; left:0; width:100%; height:100%; overflow:hidden; z-index:0; }
  .video-background video { position:absolute; top:5%; left:0; width:100%; height:100%; object-fit:cover; opacity:0.6; z-index:-1; }
  .title-bubble { background:rgba(255,255,255,1) !important; padding:1rem 1.5rem; border-radius:12px;
                   box-shadow:0 2px 6px rgba(0,0,0,0.1); margin-bottom:1.5rem; display:inline-block; position:relative; z-index:9999; }
  .title-bubble h1 { margin:0; font-size:2rem; color:#212529; }
  .title-bubble p  { margin:0.5rem 0 0; font-size:1rem; color:#555; }

  /* lock textarea + hide counter */
  div[data-testid='stTextArea'] { max-width:300px !important; margin:0 0 1rem 0 !important; }
  div[data-testid='stTextArea'] textarea { width:100% !important; box-sizing:border-box !important; }
  div[data-testid='stTextArea'] > div:nth-child(3) { display:none !important; }

  .card-container { display:grid; grid-template-columns:repeat(auto-fit,minmax(500px,1fr)); gap:1.5rem; margin-top:1rem; }
  .card { display:flex; flex-direction:row; background:#f8f9fa; padding:1rem; border-radius:12px;
           border:1px solid #dee2e6; box-shadow:1px 2px 5px rgba(0,0,0,0.1); overflow:hidden; transition:transform 0.2s; }
  .card:hover { transform: scale(1.02); }
  .card img { width:180px; height:180px; object-fit:cover; border-radius:8px; margin-right:1rem; cursor:pointer; }
  .card-content { flex:1; }
  .card-content h4 { margin:0 0 0.5rem; font-size:1.4rem; color:#343a40; }
  .subcard { background:#fff; border:1px solid #dee2e6; border-radius:10px; padding:0.75rem 1rem;
             margin-bottom:1rem; box-shadow:0 1px 3px rgba(0,0,0,0.05); }
  .subcard h5 { margin:0 0 0.5rem; font-size:1.1rem; font-weight:bold; color:#212529; }
  .subcard.engagement, .subcard.campaign-fit { display:none; }
  .card:hover .subcard.engagement, .card:hover .subcard.campaign-fit { display:block; }
  #image-modal { display:none; position:fixed; z-index:10000; left:0; top:0; width:100%; height:100%; background:rgba(0,0,0,0.8); }
  #modal-content { position:relative; margin:5% auto; display:block; max-width:90%; max-height:90%; border-radius:12px; }
</style>
<div id='image-modal' onclick="this.style.display='none'"><img id='modal-content'/></div>
<script>
  function showModal(src){
    document.getElementById('modal-content').src=src;
    document.getElementById('image-modal').style.display='block';
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

# ICON MAP & LINE FORMATTER
t_ICONS = {
    'Audience Segment Id':'🆔','identityGraphName':'🧠','age_range':'🎯','size':'📊',
    'income_level':'💰','location_type':'🏘️','recency':'⏱️','cpm':'📈',
    'confidence':'📌','cpmCap':'📌','estimated_reach':'📌','category':'📂',
    'quality_score':'⭐','data_source':'🔗','programmaticMediaPct':'📌','advertiserDirectPct':'📌'
}

def format_segment_line(line: str) -> str:
    line = line.strip()
    m = re.match(r"- \*\*(.*?)\*\*: (.*?) - (Matches|Mismatch)(.*)", line)
    if m:
        f, v, s, e = m.groups()
        icon = t_ICONS.get(f,'📌')
        if s=='Mismatch' and 'does not specify' in e.lower():
            s='Matches'
        if s=='Matches':
            return f"<div style='margin-bottom:0.5rem;'><strong>{icon} {f}:</strong> {v}</div>"
        return ("<div style='margin-bottom:0.75rem;'>"
                f"<strong style='color:#dc3545;'>{icon} {f}:</strong> {v} ❌<br>"
                f"<span style='color:#dc3545;font-size:0.85rem;'>{e.strip()}</span>"
                "</div>")
    g = re.match(r"- \*\*(.*?)\*\*: (.*)", line)
    if g:
        f, v = g.groups()
        icon = t_ICONS.get(f,'📌')
        return f"<div style='margin-bottom:0.5rem;'><strong>{icon} {f}:</strong> {v}</div>"
    return f"<div style='margin-bottom:0.5rem;'>{line}</div>"

# DALL·E HELPERS
def gen_prompt(q,n,b): return f"Create ad for '{q}', segment '{n}':\n{b}\nStyle: bright, aspirational."
def get_dalle_url(p:str):
    try:
        return openai.images.generate(model='dall-e-3',prompt=p,n=1,
                                      size='1024x1024',response_format='url'
                                     ).data[0].url
    except: return None

# MAIN UI: QUERY & HISTORY
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

if st.session_state.active_output and not (run and query.strip()):
    st.markdown(st.session_state.active_output, unsafe_allow_html=True)
    if st.session_state.active_summary:
        st.markdown(st.session_state.active_summary, unsafe_allow_html=True)

# RUN & RENDER
if run and query.strip():
    st.session_state.active_output  = None
    st.session_state.active_summary = None

    # 1) Finding segments
    with st.spinner('Finding segments…'):
        blocks = run_segment_agent(query).raw.split('### ')

    # 2) Generating cards
    cards = ['<div class="card-container">']
    for b in blocks:
        if not b.strip() or '**Summary**:' in b:
            continue
        lines   = b.strip().splitlines()
        name    = lines[0].strip()
        details = [l for l in lines[1:] if l.strip()]

        # extract each bucket
        id_line   = next((l for l in details if 'Audience Segment Id' in l), '')
        identity  = next((l for l in details if 'identityGraphName'    in l), '')
        age       = next((l for l in details if 'age_range'            in l), '')
        size      = next((l for l in details if '**size**'             in l), '')
        income    = next((l for l in details if 'income_level'         in l), '')
        loc       = next((l for l in details if 'location_type'        in l), '')
        # engagement
        recency   = next((l for l in details if 'recency'            in l), '')
        cpm       = next((l for l in details if '**cpm**'             in l), '')
        cpmCap    = next((l for l in details if 'cpmCap'             in l), '')
        confidence= next((l for l in details if 'confidence'         in l), '')
        # everything else for campaign-fit
        used = {id_line, identity, age, size, income, loc, recency, cpm, cpmCap, confidence}
        fit  = [l for l in details if l not in used and re.search(r"- \*\*.*\*\*: .* - (Matches|Mismatch)", l)]

        # image
        with st.spinner(f"Generating image for '{name}'…"):
            url = get_dalle_url(gen_prompt(query,name,'\n'.join(details)))

        html = '<div class="card">'
        if url:
            html += f"<div onclick=\"showModal('{url}')\"><img src='{url}' class='card-image'/></div>"
        html += '<div class="card-content">'
        html += f"<h4>{name}</h4>"

        # Demographics
        html += '<div class="subcard"><h5>👤 Demographics</h5>'
        for line in (id_line, identity, age, size, income, loc):
            if line: html += format_segment_line(line)
        html += '</div>'

        # Engagement
        html += '<div class="subcard engagement"><h5>📈 Engagement</h5>'
        for line in (recency, cpm, confidence, cpmCap):
            if line: html += format_segment_line(line)
        html += '</div>'

        # Campaign Fit
        html += '<div class="subcard campaign-fit"><h5>🎯 Campaign Fit</h5>'
        for line in fit:
            html += format_segment_line(line)
        html += '</div></div></div>'

        cards.append(html)

    cards.append('</div>')

    # 3) Render to page
    with st.spinner('Organizing results…'):
        full_html = ''.join(cards)
        st.success('Segments generated successfully!')
        st.markdown(full_html, unsafe_allow_html=True)

        summary_text = next(
            (blk.split('There were ')[1].strip().replace('\n','<br>')
             for blk in blocks if '**Summary**:' in blk),
            ''
        )
        summary_html = ''
        if summary_text:
            summary_html = (
                '<div style="margin-top:2rem;padding:1rem;'
                'border-radius:12px;background:#fff;'
                'box-shadow:0 2px 6px rgba(0,0,0,0.1);">'
                '<h4>📌 Summary</h4>'
                f'<p>{summary_text}</p>'
                '</div>'
            )
            st.markdown(summary_html, unsafe_allow_html=True)

        st.session_state.history.append({
            'query': query,
            'html': full_html,
            'summary_html': summary_html
        })


# streamlit run streamlit/streamlit_app.py

# implemented total segment count per query
# fixed output cutoff error
# updated streamlit UI
# add input validator (malicious or bad words)
