###############################################################################
# "Field Operator AI" — AVEVA + Snowflake Edge Demo for AVEVA World 2026
# Streamlit in Snowflake (SiS) — warehouse runtime
#
# A phone-screen chat interface: plant managers / truck drivers interact
# with a Cortex Agent grounded in AVEVA data + OEM knowledge base.
#
# Uses _snowflake.send_snow_api_request() for the REST call (SiS internal).
###############################################################################

import json
import re
import time

import _snowflake
import streamlit as st

# ---------------------------------------------------------------------------
# Page config
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="AVEVA Field AI",
    layout="wide",
    page_icon=":material/phone_iphone:",
)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
AGENT_ENDPOINT = (
    "/api/v2/databases/AVEVA_CONNECT/schemas/PUBLIC"
    "/agents/FIELD_OPERATOR_AGENT:run"
)

# ---------------------------------------------------------------------------
# Agent REST call via SiS internal API
# ---------------------------------------------------------------------------

def call_agent(user_message, chat_history=None):
    """
    Call the Cortex Agent via _snowflake.send_snow_api_request().
    Returns (response_text, payload_dict, elapsed_seconds).
    """
    messages = []
    if chat_history:
        for msg in chat_history[-6:]:
            messages.append({
                "role": msg["role"],
                "content": [{"type": "text", "text": msg["content"]}],
            })
    messages.append({
        "role": "user",
        "content": [{"type": "text", "text": user_message}],
    })

    payload = {"messages": messages, "stream": False}

    start = time.time()
    try:
        resp = _snowflake.send_snow_api_request(
            "POST",          # method
            AGENT_ENDPOINT,  # path
            {},              # headers
            {},              # params
            payload,         # body
            {},              # options
            120000,          # timeout ms
        )
        elapsed = time.time() - start

        if resp["status"] < 400:
            data = json.loads(resp["content"])
            # Extract text from agent response
            content = data.get("message", {}).get("content", [])
            if isinstance(content, list):
                texts = [c.get("text", "") for c in content if c.get("type") == "text"]
                if texts:
                    return "\n".join(texts), payload, elapsed
            # Fallback: try top-level content
            content2 = data.get("content", [])
            if isinstance(content2, list):
                texts2 = [c.get("text", "") for c in content2 if c.get("type") == "text"]
                if texts2:
                    return "\n".join(texts2), payload, elapsed
            return json.dumps(data, indent=2)[:500], payload, elapsed
        else:
            return f"Error {resp['status']}: {resp.get('content', '')[:300]}", payload, elapsed
    except Exception as e:
        elapsed = time.time() - start
        return f"Error: {str(e)[:200]}", payload, elapsed


# ---------------------------------------------------------------------------
# Helper: render markdown-ish text as safe HTML inside the phone
# ---------------------------------------------------------------------------

def _to_phone_html(text):
    """Convert agent text to HTML safe for the phone bubble."""
    t = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    t = re.sub(r'\*\*(.+?)\*\*', r'<b>\1</b>', t)
    t = re.sub(r'\*(.+?)\*', r'<i>\1</i>', t)
    t = t.replace("\n", "<br/>")
    return t


# ---------------------------------------------------------------------------
# CSS — Phone only. Dark background. Nothing else.
# ---------------------------------------------------------------------------
st.markdown("""
<style>
/* ── Kill default padding for a cleaner look ── */
.block-container { padding-top: 1rem !important; }

/* ── Phone frame ── */
.phone-center { display: flex; justify-content: center; padding: 0; }
.phone {
    width: 400px; background: #000; border-radius: 52px;
    border: 4px solid #1a1a1a; padding: 14px;
    box-shadow:
        0 30px 90px rgba(0,0,0,0.7),
        0 0 0 1px rgba(255,255,255,0.03),
        inset 0 1px 0 rgba(255,255,255,0.04);
}
.screen {
    background: linear-gradient(180deg, #0a0f1a 0%, #111827 100%);
    border-radius: 42px; overflow: hidden; min-height: 700px;
    display: flex; flex-direction: column;
}

/* ── Dynamic Island ── */
.island {
    width: 120px; height: 34px; background: #000; border-radius: 20px;
    margin: 0 auto; margin-top: -1px; position: relative; z-index: 10;
    display: flex; align-items: center; justify-content: center;
}
.island .cam {
    width: 10px; height: 10px; background: #1a1a2e; border-radius: 50%;
    box-shadow: 0 0 4px rgba(99,102,241,0.4);
}

/* ── Status bar ── */
.sbar {
    display: flex; justify-content: space-between; align-items: center;
    padding: 2px 26px 6px; font-size: 11px; color: #94A3B8;
    font-family: -apple-system, system-ui, sans-serif;
}
.sbar .tm { font-weight: 700; color: #E2E8F0; font-size: 12px; }

/* ── App header ── */
.apphdr {
    padding: 10px 16px 10px;
    background: rgba(0,212,170,0.03);
    border-bottom: 1px solid rgba(0,212,170,0.06);
    display: flex; align-items: center; gap: 10px;
}
.apphdr .icon {
    width: 36px; height: 36px; border-radius: 12px;
    background: linear-gradient(135deg, #00D4AA, #6366F1);
    display: flex; align-items: center; justify-content: center;
    font-size: 13px; color: white; font-weight: 800;
    font-family: -apple-system, system-ui, sans-serif;
}
.apphdr .nm { font-size: 14px; font-weight: 700; color: #E2E8F0; font-family: -apple-system, system-ui, sans-serif; }
.apphdr .st { font-size: 10px; color: #22C55E; font-family: -apple-system, system-ui, sans-serif; }

/* ── Alert cards ── */
.alrt {
    margin: 6px 12px; padding: 10px 12px; border-radius: 14px;
    border-left: 3px solid; background: rgba(30,41,59,0.6);
    font-family: -apple-system, system-ui, sans-serif;
}
.alrt.cr { border-color: #EF4444; }
.alrt.wr { border-color: #F59E0B; }
.alrt.nf { border-color: #00D4AA; }
.alrt .ah { display: flex; justify-content: space-between; align-items: center; margin-bottom: 3px; }
.alrt .tg {
    font-size: 9px; font-weight: 700; text-transform: uppercase;
    letter-spacing: 0.08em; padding: 1px 6px; border-radius: 3px;
}
.tg.cr { background: rgba(239,68,68,0.15); color: #EF4444; }
.tg.wr { background: rgba(245,158,11,0.15); color: #F59E0B; }
.tg.nf { background: rgba(0,212,170,0.1); color: #00D4AA; }
.alrt .at { font-size: 9px; color: #64748B; }
.alrt .tt { font-size: 12.5px; font-weight: 600; color: #E2E8F0; margin-bottom: 1px; }
.alrt .bd { font-size: 11px; color: #94A3B8; line-height: 1.4; }

/* ── Chat ── */
.msgs { flex: 1; padding: 8px 12px; overflow-y: auto; }
.bbl {
    max-width: 84%; padding: 10px 14px; margin: 5px 0;
    border-radius: 18px; font-size: 12.5px; line-height: 1.55;
    word-wrap: break-word;
    font-family: -apple-system, system-ui, sans-serif;
}
.bbl.u {
    background: linear-gradient(135deg, #00D4AA, #059669);
    color: #fff; margin-left: auto; border-bottom-right-radius: 4px;
}
.bbl.a {
    background: rgba(30,41,59,0.85); color: #E2E8F0;
    border: 1px solid rgba(148,163,184,0.08);
    border-bottom-left-radius: 4px;
}
.bbl.a b { color: #00D4AA; }
.bbl .meta { font-size: 9px; color: #64748B; margin-top: 4px; }

/* ── Bottom input bar (decorative) ── */
.inbar {
    padding: 8px 12px 16px;
    background: rgba(10,15,26,0.95);
    border-top: 1px solid rgba(148,163,184,0.06);
}
.pill {
    background: rgba(30,41,59,0.5); border: 1px solid rgba(148,163,184,0.08);
    border-radius: 22px; padding: 10px 16px;
    font-size: 12px; color: #475569;
    font-family: -apple-system, system-ui, sans-serif;
}

/* ── Hide streamlit bits ── */
.stTextInput label { font-size: 0 !important; height: 0 !important; min-height: 0 !important; overflow: hidden !important; }
</style>
""", unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# Session state
# ---------------------------------------------------------------------------
if "chat" not in st.session_state:
    st.session_state.chat = []
if "last_call" not in st.session_state:
    st.session_state.last_call = None

# ---------------------------------------------------------------------------
# Build phone HTML
# ---------------------------------------------------------------------------

chat_bubbles = ""
for msg in st.session_state.chat:
    cls = "u" if msg["role"] == "user" else "a"
    html_text = _to_phone_html(msg["content"])
    meta = ""
    if msg["role"] == "assistant" and "elapsed" in msg:
        meta = f'<div class="meta">Cortex Agent &bull; {msg["elapsed"]:.1f}s</div>'
    chat_bubbles += f'<div class="bbl {cls}">{html_text}{meta}</div>'

alerts_html = ""
if not st.session_state.chat:
    alerts_html = (
        '<div class="alrt cr">'
        '<div class="ah"><span class="tg cr">CRITICAL</span><span class="at">2 min ago</span></div>'
        '<div class="tt">Truck 108 &mdash; Coolant 96.2&deg;C</div>'
        '<div class="bd">Z-score 4.04. Threshold 92&deg;C. Immediate check needed.</div>'
        '</div>'
        '<div class="alrt wr">'
        '<div class="ah"><span class="tg wr">WARNING</span><span class="at">15 min ago</span></div>'
        '<div class="tt">PMP-DMA04A-06 &mdash; Bearing Temp +0.52&deg;C</div>'
        '<div class="bd">Above AVEVA prediction. Weather r=0.31 &mdash; likely environmental.</div>'
        '</div>'
        '<div class="alrt nf">'
        '<div class="ah"><span class="tg nf">INFO</span><span class="at">1 hr ago</span></div>'
        '<div class="tt">PMP-DMA02D-21 &mdash; Maintenance Overdue</div>'
        '<div class="bd">2,980 run hours (fleet avg 2,400). Schedule inspection.</div>'
        '</div>'
    )

phone_html = (
    '<div class="phone-center"><div class="phone"><div class="screen">'
    # Dynamic Island
    '<div class="island"><div class="cam"></div></div>'
    # Status bar
    '<div class="sbar">'
    '<span class="tm">9:41</span>'
    '<span>5G &nbsp;&nbsp; 100%</span>'
    '</div>'
    # App header
    '<div class="apphdr">'
    '<div class="icon">AI</div>'
    '<div><div class="nm">AVEVA Field AI</div>'
    '<div class="st">&#9679; Connected</div></div>'
    '</div>'
    # Alerts or chat
    f'{alerts_html}'
    f'<div class="msgs">{chat_bubbles}</div>'
    # Bottom input bar (decorative — real input is below)
    '<div class="inbar"><div class="pill">Ask about equipment, safety&hellip;</div></div>'
    '</div></div></div>'
)

# ---------------------------------------------------------------------------
# Render
# ---------------------------------------------------------------------------

# Three columns to center the phone
_pad_l, center, _pad_r = st.columns([1, 1.5, 1])

with center:
    st.markdown(phone_html, unsafe_allow_html=True)

    # --- Quick actions ---
    st.markdown("")
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        if st.button("Truck 108?", use_container_width=True):
            st.session_state._pq = "Truck 108 coolant is at 96.2°C with z-score 4.04. Should I pull it from service?"
    with c2:
        if st.button("PMP-06?", use_container_width=True):
            st.session_state._pq = "PMP-DMA04A-06 bearing temp is 0.52°C above prediction. Real problem or weather?"
    with c3:
        if st.button("Priority?", use_container_width=True):
            st.session_state._pq = "Which equipment needs maintenance most urgently right now?"
    with c4:
        if st.button("Weather?", use_container_width=True):
            st.session_state._pq = "How is Calgary weather affecting our pumps and trucks today?"

    # --- Text input ---
    user_input = st.text_input(
        "msg",
        key="fi",
        placeholder="Type a message...",
        label_visibility="collapsed",
    )
    send = st.button("Send", type="primary", use_container_width=True)

    # Handle pending quick-action
    pq = st.session_state.pop("_pq", None)
    if pq:
        user_input = pq
        send = True

    if send and user_input:
        st.session_state.chat.append({"role": "user", "content": user_input})
        with st.spinner("Agent thinking..."):
            text, payload, elapsed = call_agent(user_input, st.session_state.chat[:-1])
        st.session_state.chat.append({"role": "assistant", "content": text, "elapsed": elapsed})
        st.session_state.last_call = {
            "endpoint": AGENT_ENDPOINT,
            "payload": payload,
            "elapsed": elapsed,
            "response": text[:300],
        }
        st.rerun()

    if st.session_state.chat:
        if st.button("Clear", type="secondary"):
            st.session_state.chat = []
            st.session_state.last_call = None
            st.rerun()

# ---------------------------------------------------------------------------
# Side panels: show the API call details (left) and code (right)
# ---------------------------------------------------------------------------
with _pad_l:
    if st.session_state.last_call:
        call = st.session_state.last_call
        with st.expander(":material/terminal: Last API Call", expanded=True):
            st.code(
                f'POST {call["endpoint"]}\n\n'
                f'{json.dumps(call["payload"], indent=2)[:600]}\n\n'
                f'# Response: {call["elapsed"]:.1f}s',
                language="json",
            )

with _pad_r:
    with st.expander(":material/code: REST API Code", expanded=False):
        st.code(
            '''import _snowflake, json

# Cortex Agent REST call from SiS
resp = _snowflake.send_snow_api_request(
    "POST",
    "/api/v2/databases/AVEVA_CONNECT"
    "/schemas/PUBLIC"
    "/agents/FIELD_OPERATOR_AGENT:run",
    {}, {},  # headers, params
    {
        "messages": [{
            "role": "user",
            "content": [{
                "type": "text",
                "text": "Truck 108 coolant 96°C?"
            }]
        }],
        "stream": False
    },
    {},       # options
    120000,   # timeout ms
)

data = json.loads(resp["content"])
answer = data["message"]["content"][0]["text"]''',
            language="python",
        )
    with st.expander(":material/schema: Agent SQL", expanded=False):
        st.code(
            '''CREATE OR REPLACE AGENT
  FIELD_OPERATOR_AGENT
FROM SPECIFICATION $$
models:
  orchestration: mistral-large2
tools:
  - tool_spec:
      type: cortex_search
      name: knowledge_search
tool_resources:
  knowledge_search:
    search_service:
      AVEVA_CONNECT.PUBLIC
      .INDUSTRIAL_DOCS_SEARCH
$$;''',
            language="sql",
        )
