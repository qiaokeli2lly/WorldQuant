# app.py
import streamlit as st
import config_page
import result_page

st.set_page_config(layout="wide", page_title="MiniQuant 量化分析平台", page_icon="📈")

# 初始化 session_state
if 'page' not in st.session_state:
    st.session_state.page = 'config'

# 页面路由
if st.session_state.page == 'config':
    config_page.show()
else:
    result_page.show()