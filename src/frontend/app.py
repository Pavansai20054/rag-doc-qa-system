import requests
import streamlit as st

DEFAULT_API_URL = "http://localhost:8000"

st.set_page_config(page_title="Enterprise RAG QA", layout="wide")

st.title("Enterprise RAG Document Q&A")

with st.sidebar:
    st.header("Ingestion")
    api_url = st.text_input("API URL", value=DEFAULT_API_URL)
    source_path = st.text_input("Document folder path")
    semantic_chunking = st.checkbox("Semantic chunking", value=False)
    if st.button("Ingest documents"):
        if source_path:
            try:
                resp = requests.post(
                    f"{api_url}/ingest",
                    json={
                        "source_path": source_path,
                        "semantic_chunking": semantic_chunking,
                    },
                    timeout=120,
                )
                if resp.ok:
                    st.write(resp.json())
                else:
                    st.error(resp.text)
            except requests.RequestException as exc:
                st.error(f"API request failed: {exc}")

st.divider()

streaming = st.checkbox("Stream response", value=False)

if "conversation_id" not in st.session_state:
    st.session_state.conversation_id = None

question = st.text_input("Ask a question")

if st.button("Ask") and question:
    payload = {
        "question": question,
        "conversation_id": st.session_state.conversation_id,
    }
    if streaming:
        try:
            response = requests.post(
                f"{api_url}/query/stream", json=payload, stream=True, timeout=120
            )
            if not response.ok:
                st.error(response.text)
            else:
                placeholder = st.empty()
                buffer = ""
                for chunk in response.iter_content(chunk_size=None, decode_unicode=True):
                    if not chunk:
                        continue
                    buffer += chunk
                    placeholder.write(buffer)
        except requests.RequestException as exc:
            st.error(f"API request failed: {exc}")
    else:
        try:
            response = requests.post(f"{api_url}/query", json=payload, timeout=120)
            if not response.ok:
                st.error(response.text)
                st.stop()
            data = response.json()
        except requests.RequestException as exc:
            st.error(f"API request failed: {exc}")
            st.stop()

        if "conversation_id" not in data:
            st.error("API response missing conversation_id. Is the API running?")
            st.write(data)
            st.stop()

        st.session_state.conversation_id = data["conversation_id"]

        st.subheader("Answer")
        st.write(data.get("answer", ""))

        st.subheader("Citations")
        for cite in data.get("citations", []):
            st.write(cite)

        st.subheader("Retrieved Chunks")
        for chunk in data.get("retrieved_chunks", []):
            st.write(chunk.get("metadata"))
            st.write(chunk.get("text"))
            st.divider()
