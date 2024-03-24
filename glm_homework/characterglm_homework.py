"""
依赖：
pyjwt
requests
streamlit
zhipuai
python-dotenv

运行方式：
```bash
streamlit run characterglm_homework.py
```
"""

import os
import itertools
from typing import Iterator, Optional

import streamlit as st
from dotenv import load_dotenv

# 通过.env文件设置环境变量
# reference: https://github.com/theskumar/python-dotenv
load_dotenv()

import api
from api import (
    generate_role_appearance,
    get_characterglm_response,
)
from data_types import TextMsg, filter_text_msg

st.set_page_config(page_title="CharacterGLM API Demo", page_icon="🤖", layout="wide")
debug = os.getenv("DEBUG", "").lower() in ("1", "yes", "y", "true", "t", "on")


def update_api_key(key: Optional[str] = None):
    if debug:
        print(
            f'update_api_key. st.session_state["API_KEY"] = {st.session_state["API_KEY"]}, key = {key}'
        )
    key = key or st.session_state["API_KEY"]
    if key:
        api.API_KEY = key


# 设置API KEY
api_key = st.sidebar.text_input(
    "API_KEY",
    value=os.getenv("API_KEY", ""),
    key="API_KEY",
    type="password",
    on_change=update_api_key,
)
update_api_key()


# 初始化
if "history" not in st.session_state:
    st.session_state["history"] = []
    st.session_state["chat_round"] = 10
    st.session_state["chat_topic"] = ""
    st.session_state["chat_started"] = False
if "meta" not in st.session_state:
    st.session_state["meta"] = {
        "user_name": "",
        "user_info": "",
        "bot_name": "",
        "bot_info": "",
    }


def update_role_user_info():
    user_info = "".join(generate_role_appearance(st.session_state.user_desc))
    if debug:
        print(f"update user_info. value = {user_info}")
    st.session_state["meta"].update(user_info=user_info)


def update_role_bot_info():
    bot_info = "".join(generate_role_appearance(st.session_state.bot_desc))
    if debug:
        print(f"update bot_info. value = {bot_info}")
    st.session_state["meta"].update(bot_info=bot_info)


# 1x2 layout
with st.container():
    col1, col2 = st.columns(2)
    with col1:
        st.text_area(
            label="角色A描述",
            key="user_desc",
            on_change=update_role_user_info,
            help="角色A的描述信息不可以为空",
        )

    with col2:
        st.text_area(
            label="角色B描述",
            key="bot_desc",
            on_change=update_role_bot_info,
            help="角色B的描述信息不可以为空",
        )

input_labels = {
    "chat_topic": "对话主题",
    "chat_round": "对话轮数",
}


def update_chat_topic():
    if debug:
        print(f"update chat_topic. value = {st.session_state.chat_topic}")
    st.session_state["chat_topic"] = st.session_state.chat_topic


def update_chat_round():
    if debug:
        print(f"update chat_round. value = {st.session_state.chat_round}")
    st.session_state["chat_round"] = st.session_state.chat_round


# 1x2 layout
with st.container():
    button_nums = len(input_labels)
    cols = st.columns(button_nums)
    button_key_to_col = dict(zip(input_labels.keys(), cols))

    with button_key_to_col["chat_topic"]:
        st.text_input(
            label="对话主题",
            placeholder="请输入对话主题",
            key="chat_topic",
            help="两个角色相关的对话主题",
            on_change=update_chat_topic,
        )

    with button_key_to_col["chat_round"]:
        st.number_input(
            label="对话轮数",
            min_value=1,
            max_value=100,
            step=1,
            key="chat_round",
            help="对话轮数[1-100]",
            on_change=update_chat_round,
        )


button_labels = {
    "start_chat": "开始对话",
    "clear_history": "清空对话历史",
    "download_history_file": "下载对话历史",
}


# 保存聊天记录文件
def convert_chat_history_data():
    with open("data/chat_history.txt", "w", encoding="utf-8") as file:
        for msg in st.session_state["history"]:
            content = msg["content"]
            if msg["role"] == "user":
                file.write(f"A：{content}")
            if msg["role"] == "assistant":
                file.write(f"B：{content}")
            file.write("\n")


# 在同一行排列按钮
with st.container():
    button_nums = len(button_labels)
    cols = st.columns(button_nums)
    button_key_to_col = dict(zip(button_labels.keys(), cols))

    with button_key_to_col["start_chat"]:
        start_chat = st.button(label=button_labels["start_chat"], key="start_chat")
        if start_chat:
            st.session_state["history"] = []
            st.session_state["chat_started"] = start_chat
            st.rerun()

    with button_key_to_col["clear_history"]:
        clear_history = st.button(
            label=button_labels["clear_history"], key="clear_history"
        )
        if clear_history:
            st.session_state["history"] = []
            st.session_state["chat_started"] = False
            st.rerun()

    with button_key_to_col["download_history_file"]:
        with open("data/chat_history.txt", "r", encoding="utf-8") as file:
            download_history_file = st.download_button(
                label=button_labels["download_history_file"],
                file_name="chat_history.txt",
                data=file,
                on_click=convert_chat_history_data,
            )
            if download_history_file:
                st.session_state["chat_started"] = False
                st.rerun()


def output_stream_response(response_stream: Iterator[str]) -> str:
    return "".join(response_stream)


# 必要信息校验
def verify_meta() -> bool:
    if (
        st.session_state["meta"]["user_info"] == ""
        or st.session_state["meta"]["bot_info"] == ""
    ):
        st.error("角色的描述信息不能为空")
        return False

    if st.session_state["chat_topic"] == "":
        st.error("角色对话主题不能为空")
        return False

    return True


# 展示对话历史
def show_message(msg: TextMsg):
    if msg["role"] == "user":
        with st.chat_message(name="user", avatar="user"):
            st.markdown(msg["content"])
    elif msg["role"] == "assistant":
        with st.chat_message(name="assistant", avatar="assistant"):
            st.markdown(msg["content"])
    else:
        raise Exception("Invalid role")


def start_chat():
    chat_topic = st.session_state["chat_topic"]
    start_chat_text = f"我们开始对话吧，{chat_topic}"
    st.session_state["history"].append(
        TextMsg({"role": "user", "content": start_chat_text})
    )
    show_message(st.session_state["history"][-1])

    chat_round = st.session_state["chat_round"]
    while chat_round > 0:
        if not verify_meta():
            return
        if not api.API_KEY:
            st.error("未设置API_KEY")

        response_stream = get_characterglm_response(
            filter_text_msg(st.session_state["history"]), meta=st.session_state["meta"]
        )

        bot_response = output_stream_response(response_stream)
        if not bot_response:
            st.markdown("生成出错")
            st.session_state["history"].pop()
        else:
            st.session_state["history"].append(
                TextMsg({"role": "assistant", "content": bot_response})
            )
            show_message(st.session_state["history"][-1])

        response_stream = get_characterglm_response(
            filter_text_msg(st.session_state["history"]), meta=st.session_state["meta"]
        )

        user_response = output_stream_response(response_stream)
        if not bot_response:
            st.markdown("生成出错")
            st.session_state["history"].pop()
        else:
            st.session_state["history"].append(
                TextMsg({"role": "user", "content": user_response})
            )
            show_message(st.session_state["history"][-1])

        print(st.session_state["history"])

        chat_round -= 1


if st.session_state["chat_started"]:
    start_chat()
