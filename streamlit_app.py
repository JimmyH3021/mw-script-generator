import streamlit as st
import pandas as pd
import base64
from datetime import datetime

# 页面配置
st.set_page_config(
    page_title="ZTE微波脚本生成器",
    page_icon="📡",
    layout="wide"
)

st.title("📡 ZTE微波开站脚本生成器")
st.subheader("巴西项目专用")

# 初始化会话状态
if 'dcn_data' not in st.session_state:
    st.session_state.dcn_data = None
if 'datasheet_data' not in st.session_state:
    st.session_state.datasheet_data = None

# 文件上传
st.sidebar.header("文件上传")

dcn_file = st.sidebar.file_uploader("上传DCN文件", type=['csv'], key="dcn")
datasheet_file = st.sidebar.file_uploader("上传Datasheet", type=['csv'], key="datasheet")

# 主界面
st.info("💡 请先上传CSV格式的DCN文件和Datasheet文件")

if dcn_file and datasheet_file:
    try:
        # 读取文件
        dcn_df = pd.read_csv(dcn_file)
        datasheet_df = pd.read_csv(datasheet_file)
        
        st.session_state.dcn_data = dcn_df
        st.session_state.datasheet_data = datasheet_df
        
        st.success("✅ 文件加载成功！")
        
        # 显示文件信息
        col1, col2 = st.columns(2)
        with col1:
            st.write("DCN文件预览:")
            st.dataframe(dcn_df.head(3))
        with col2:
            st.write("Datasheet预览:")
            st.dataframe(datasheet_df.head(3))
            
    except Exception as e:
        st.error(f"文件读取失败: {e}")

# CHAVE输入
chave_number = st.text_input("输入CHAVE号码:", placeholder="例如: CODV29")

if chave_number and st.session_state.datasheet_data is not None:
    st.write(f"正在查找CHAVE: {chave_number}")
    
    # 简单的脚本生成示例
    st.code(f"""
configure terminal
hostname SITE_{chave_number}
ip address 10.211.51.202 255.255.255.248
vlan 2929
write
    """, language='bash')

st.sidebar.info("""
使用说明:
1. 上传CSV格式文件
2. 输入CHAVE号码
3. 生成配置脚本
""")
