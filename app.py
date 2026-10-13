"""FreeQuota 主界面：浏览器聊天 + 额度油表。

面向不懂编程的普通人：
    pip install -r requirements.txt
    streamlit run app.py
然后在浏览器打开提示的地址即可。
"""

import streamlit as st

from core.relay import load_providers, relay_chat

st.set_page_config(page_title="FreeQuota 穷人额度接力器", layout="wide")

st.title("FreeQuota · 穷人额度接力器")
st.caption(
    "把各大厂白送的免费额度聚成一个入口，一家用完自动接力下一家 —— "
    "让普通人也能免费用上原本要花钱的 AI 能力"
)

CONFIG_PATH = "config.json"
providers = load_providers(CONFIG_PATH)

if not providers:
    st.error(
        "没有可用的 provider。请先复制 config.example.json 为 config.json，"
        "填入你自己的免费 API Key，并删除占位符文字。"
    )
    st.stop()

# 侧边栏：额度油表
with st.sidebar:
    st.header("额度油表")
    st.caption("按优先级从上到下，灰色=未测试，绿=正常，红=本轮失败")
    for p in providers:
        color = "gray"
        if p.last_status == "正常":
            color = "green"
        elif p.last_status.startswith("失败"):
            color = "red"
        st.markdown(
            f"<span style='color:{color}'>●</span> "
            f"**{p.name}**（优先级 {p.priority}）<br>"
            f"<small>{p.last_status}</small>",
            unsafe_allow_html=True,
        )

if "messages" not in st.session_state:
    st.session_state.messages = []

for m in st.session_state.messages:
    with st.chat_message(m["role"]):
        st.markdown(m["content"])
        if m.get("provider"):
            st.caption(f"↑ 本条由 {m['provider']} 回复")

if prompt := st.chat_input("说点什么……"):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # 只把干净的 role/content 传给模型，去掉本地附加字段
    clean = [
        {"role": m["role"], "content": m["content"]}
        for m in st.session_state.messages
        if m["role"] in ("user", "assistant")
    ]

    with st.chat_message("assistant"):
        with st.spinner("正在接力推理……"):
            try:
                content, used, log = relay_chat(clean, providers)
            except Exception as e:
                st.error(str(e))
                st.stop()
        st.markdown(content)
        st.caption(f"↑ 本条由 {used} 回复")
        st.session_state.messages.append(
            {"role": "assistant", "content": content, "provider": used}
        )
        with st.sidebar:
            st.text("\n".join(log))
