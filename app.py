"""FreeQuota 主界面：浏览器聊天 + 额度油表（开箱即用中文客户端）。

面向不懂编程的普通人：
    pip install -r requirements.txt
    streamlit run app.py
然后在浏览器打开提示的地址即可。
"""

import os

import streamlit as st

from core.relay import load_config, relay_chat

st.set_page_config(page_title="FreeQuota", layout="wide")

st.title("FreeQuota")
st.caption(
    "把各家大模型厂商送的免费额度聚在一起，一个中文界面直接聊天。"
    "一家用完了，自动换下一家。"
)

# 既支持 exe 启动器写入的 FREQUOTA_CONFIG，也兼容直接 python 运行时的 cwd 查找
CONFIG_PATH = os.environ.get("FREQUOTA_CONFIG", "config.json")
cfg = load_config(CONFIG_PATH)
gateway = cfg["gateway"]
providers = cfg["providers"]

# 判定当前生效模式，并显示横幅
mode = cfg["mode"]
use_gateway = (mode in ("auto", "gateway")) and gateway and gateway.is_configured()
if use_gateway:
    st.success(f"当前模式：进阶（已指向网关 {gateway.base_url}，由它路由几百家模型）")
elif providers:
    st.info("当前模式：极简（FreeQuota 内置轻量接力，国内免费 Key 轮流试）")
else:
    st.error(
        "没有可用的配置。请先复制 config.example.json 为 config.json，"
        "填入国内免费 Key，或在 gateway 中填好你的网关地址，并删除占位符文字。"
    )
    st.stop()

# 侧边栏：额度油表
with st.sidebar:
    st.header("额度油表")
    if use_gateway:
        st.caption("进阶模式：连通性由网关负责，FreeQuota 只显示网关状态")
        if gateway.last_status == "正常":
            color = "green"
        elif gateway.last_status.startswith("失败"):
            color = "red"
        else:
            color = "gray"
        st.markdown(
            f"<span style='color:{color}'>●</span> "
            f"**网关 {gateway.base_url}**<br>"
            f"<small>{gateway.last_status}</small>",
            unsafe_allow_html=True,
        )
    else:
        st.caption("极简模式：灰色=未测试，绿=正常，红=本轮失败")
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
                content, used, log = relay_chat(clean, cfg)
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
