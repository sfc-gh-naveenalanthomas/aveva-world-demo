"""
Field Operator AI — Flask backend
Connects to Snowflake via snowflake-connector-python (my_polaris_connection)
and calls the Cortex Agent REST API.
"""

import json
import os
import time

import requests
import snowflake.connector
from flask import Flask, Response, jsonify, render_template, request, stream_with_context

app = Flask(__name__, static_folder="static", template_folder="templates")

# ---------------------------------------------------------------------------
# Snowflake connection
# ---------------------------------------------------------------------------
SNOWFLAKE_ACCOUNT = os.getenv("SNOWFLAKE_ACCOUNT", "SFSENORTHAMERICA-POLARIS1")
SNOWFLAKE_USER = os.getenv("SNOWFLAKE_USER", "nthomas")
SNOWFLAKE_PASSWORD = os.getenv("SNOWFLAKE_PASSWORD", "")
SNOWFLAKE_WAREHOUSE = os.getenv("SNOWFLAKE_WAREHOUSE", "compute_wh")
SNOWFLAKE_ROLE = os.getenv("SNOWFLAKE_ROLE", "accountadmin")

AGENT_DATABASE = "AVEVA_CONNECT"
AGENT_SCHEMA = "PUBLIC"
AGENT_NAME = "FIELD_OPERATOR_AGENT"


def _get_connection():
    """Create a Snowflake connection using env vars or connection name."""
    # Try named connection first
    try:
        return snowflake.connector.connect(connection_name="my_polaris_connection")
    except Exception:
        pass
    # Fall back to explicit params
    return snowflake.connector.connect(
        account=SNOWFLAKE_ACCOUNT,
        user=SNOWFLAKE_USER,
        password=SNOWFLAKE_PASSWORD,
        warehouse=SNOWFLAKE_WAREHOUSE,
        role=SNOWFLAKE_ROLE,
    )


def _translate(text, from_lang="en", to_lang="it"):
    """Translate text using Snowflake Cortex TRANSLATE."""
    import re
    conn = _get_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT SNOWFLAKE.CORTEX.TRANSLATE(%s, %s, %s)",
            (text, from_lang, to_lang),
        )
        row = cur.fetchone()
        result = row[0] if row else text
        # Cortex Translate sometimes converts \n to <BR> tags — normalize back
        result = re.sub(r'<BR\s*/?>', '\n', result, flags=re.IGNORECASE)
        return result
    except Exception:
        return text
    finally:
        conn.close()


def call_cortex_agent(user_message, chat_history=None):
    """
    Call the Cortex Agent via REST API.
    Returns (response_text, elapsed_seconds, request_info).
    """
    conn = _get_connection()
    try:
        token = conn.rest.token
        host = conn.host

        url = (
            f"https://{host}/api/v2/databases/{AGENT_DATABASE}"
            f"/schemas/{AGENT_SCHEMA}/agents/{AGENT_NAME}:run"
        )

        headers = {
            "Authorization": f'Snowflake Token="{token}"',
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

        messages = []
        if chat_history:
            for msg in chat_history[-10:]:
                messages.append({
                    "role": msg["role"],
                    "content": [{"type": "text", "text": msg["content"]}],
                })
        messages.append({
            "role": "user",
            "content": [{"type": "text", "text": user_message}],
        })

        payload = {"messages": messages, "stream": False}

        request_info = {
            "method": "POST",
            "url": url.replace(f"https://{host}", ""),
            "headers": {
                "Authorization": 'Snowflake Token="••••••"',
                "Content-Type": "application/json",
            },
            "body": payload,
        }

        start = time.time()
        resp = requests.post(url, headers=headers, json=payload, timeout=180)
        elapsed = time.time() - start

        if resp.status_code >= 400:
            return f"Error {resp.status_code}: {resp.text[:300]}", elapsed, request_info

        data = resp.json()

        # Extract text from response
        msg_obj = data.get("message", {})
        content = msg_obj.get("content", [])
        if isinstance(content, list):
            texts = [c.get("text", "") for c in content if c.get("type") == "text"]
            if texts:
                return "\n".join(texts), elapsed, request_info

        # Fallback
        content2 = data.get("content", [])
        if isinstance(content2, list):
            texts2 = [c.get("text", "") for c in content2 if c.get("type") == "text"]
            if texts2:
                return "\n".join(texts2), elapsed, request_info

        return json.dumps(data, indent=2)[:600], elapsed, request_info

    except Exception as e:
        return f"Connection error: {str(e)[:300]}", 0, {}
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/chat", methods=["POST"])
def chat():
    try:
        body = request.json
        user_message = body.get("message", "")
        history = body.get("history", [])

        if not user_message:
            return jsonify({"error": "No message provided"}), 400

        response_text, elapsed, request_info = call_cortex_agent(user_message, history)

        return jsonify({
            "response": response_text,
            "elapsed": round(elapsed, 1),
            "request_info": request_info,
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/chat/stream", methods=["POST"])
def chat_stream():
    """Streaming endpoint — relays Cortex Agent SSE to the browser."""
    body = request.json
    user_message = body.get("message", "")
    history = body.get("history", [])
    lang = body.get("lang", "en")  # "en" or "it"

    if not user_message:
        return jsonify({"error": "No message provided"}), 400

    # Create connection outside generator to catch errors before streaming
    try:
        conn = _get_connection()
    except Exception as e:
        error_msg = str(e)[:300]
        def error_gen():
            yield f"event: error\ndata: {json.dumps({'error': error_msg})}\n\n"
        return Response(error_gen(), mimetype="text/event-stream",
                        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})

    def generate():
        full_text = ""
        try:
            token = conn.rest.token
            host = conn.host

            url = (
                f"https://{host}/api/v2/databases/{AGENT_DATABASE}"
                f"/schemas/{AGENT_SCHEMA}/agents/{AGENT_NAME}:run"
            )

            headers = {
                "Authorization": f'Snowflake Token="{token}"',
                "Content-Type": "application/json",
            }

            messages = []
            if history:
                for msg in history[-10:]:
                    messages.append({
                        "role": msg["role"],
                        "content": [{"type": "text", "text": msg["content"]}],
                    })
            messages.append({
                "role": "user",
                "content": [{"type": "text", "text": user_message}],
            })

            payload = {"messages": messages}  # stream=true is the default

            start = time.time()
            resp = requests.post(
                url, headers=headers, json=payload, stream=True, timeout=180
            )

            if resp.status_code >= 400:
                error_text = resp.text[:300]
                yield f"event: error\ndata: {json.dumps({'error': error_text})}\n\n"
                return

            event_type = None
            done_sent = False
            for line in resp.iter_lines():
                if not line:
                    continue
                decoded = line.decode("utf-8")
                if decoded.startswith("event: "):
                    event_type = decoded[7:].strip()
                elif decoded.startswith("data: "):
                    try:
                        data = json.loads(decoded[6:])
                    except json.JSONDecodeError:
                        # Handle non-JSON done markers like data: [DONE]
                        if event_type == "done":
                            elapsed = round(time.time() - start, 1)
                            yield f"event: done\ndata: {json.dumps({'elapsed': elapsed})}\n\n"
                            done_sent = True
                            if lang != "en" and full_text.strip():
                                try:
                                    translated = _translate(full_text, "en", lang)
                                    yield f"event: translated\ndata: {json.dumps({'text': translated, 'lang': lang})}\n\n"
                                except Exception:
                                    pass
                            return
                        continue

                    if event_type == "response.text.delta":
                        text_chunk = data.get("text", "")
                        if text_chunk:
                            full_text += text_chunk
                            yield f"event: text\ndata: {json.dumps({'text': text_chunk})}\n\n"

                    elif event_type == "done":
                        elapsed = round(time.time() - start, 1)
                        yield f"event: done\ndata: {json.dumps({'elapsed': elapsed})}\n\n"
                        done_sent = True

                        # If non-English language requested, translate and send
                        if lang != "en" and full_text.strip():
                            try:
                                translated = _translate(full_text, "en", lang)
                                yield f"event: translated\ndata: {json.dumps({'text': translated, 'lang': lang})}\n\n"
                            except Exception:
                                pass
                        return

            # Stream ended without explicit done event — send our own
            if not done_sent and full_text.strip():
                elapsed = round(time.time() - start, 1)
                yield f"event: done\ndata: {json.dumps({'elapsed': elapsed})}\n\n"

                if lang != "en":
                    try:
                        translated = _translate(full_text, "en", lang)
                        yield f"event: translated\ndata: {json.dumps({'text': translated, 'lang': lang})}\n\n"
                    except Exception:
                        pass

        except Exception as e:
            yield f"event: error\ndata: {json.dumps({'error': str(e)[:300]})}\n\n"
        finally:
            conn.close()

    return Response(
        stream_with_context(generate()),
        mimetype="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@app.route("/api/health")
def health():
    return jsonify({"status": "ok", "agent": f"{AGENT_DATABASE}.{AGENT_SCHEMA}.{AGENT_NAME}"})


# ---------------------------------------------------------------------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5001, debug=False)
