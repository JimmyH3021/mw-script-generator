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
st.subheader("巴西项目专用 - 增强版")

class DataProcessor:
    @staticmethod
    def parse_dcn_file(file):
        """解析DCN文件"""
        try:
            if file.name.endswith('.csv'):
                df = pd.read_csv(file)
                st.success(f"✅ DCN文件加载成功，共 {len(df)} 条记录")
                return df
            else:
                st.error("❌ 请上传CSV格式文件")
                return None
        except Exception as e:
            st.error(f"❌ DCN文件解析失败: {e}")
            return None
    
    @staticmethod
    def parse_datasheet_file(file):
        """解析Datasheet文件"""
        try:
            if file.name.endswith('.csv'):
                df = pd.read_csv(file)
                st.success(f"✅ Datasheet加载成功，共 {len(df)} 条记录")
                # 显示列名用于调试
                st.info(f"📋 文件列名: {list(df.columns)}")
                return df
            else:
                st.error("❌ 请上传CSV格式文件")
                return None
        except Exception as e:
            st.error(f"❌ Datasheet解析失败: {e}")
            return None
    
    @staticmethod
    def find_chave_column(datasheet_data):
        """查找CHAVE列"""
        chave_columns = ['Chave', 'CHAVE', 'chave', '站点编号']
        for col in chave_columns:
            if col in datasheet_data.columns:
                return col
        return None

# 初始化会话状态
if 'dcn_data' not in st.session_state:
    st.session_state.dcn_data = None
if 'datasheet_data' not in st.session_state:
    st.session_state.datasheet_data = None

# 文件上传
st.sidebar.header("文件上传")

dcn_file = st.sidebar.file_uploader("上传DCN文件", type=['csv'], key="dcn")
datasheet_file = st.sidebar.file_uploader("上传Datasheet", type=['csv'], key="datasheet")

processor = DataProcessor()

if dcn_file:
    st.session_state.dcn_data = processor.parse_dcn_file(dcn_file)

if datasheet_file:
    st.session_state.datasheet_data = processor.parse_datasheet_file(datasheet_file)

# CHAVE输入和匹配
st.markdown("---")
chave_number = st.text_input("输入CHAVE号码:", placeholder="例如: CODV29, 4G-CORD10")

if chave_number and st.session_state.datasheet_data is not None:
    datasheet_data = st.session_state.datasheet_data
    
    # 查找CHAVE列
    chave_col = processor.find_chave_column(datasheet_data)
    
    if chave_col:
        st.success(f"✅ 找到CHAVE列: '{chave_col}'")
        
        # 查找匹配的CHAVE
        datasheet_data[chave_col] = datasheet_data[chave_col].astype(str).str.strip()
        matches = datasheet_data[datasheet_data[chave_col] == chave_number.strip()]
        
        if len(matches) > 0:
            st.success(f"🎯 找到 {len(matches)} 个匹配记录")
            
            # 显示匹配的数据
            st.write("匹配的数据:")
            st.dataframe(matches)
            
            # 生成简单脚本
            st.markdown("### 生成的脚本")
            script = f"""configure terminal
hostname SITE_{chave_number}
device-para neIpv4 10.211.51.202
nms-vlan 2929
write"""
            
            st.code(script, language='bash')
        else:
            st.error(f"❌ 未找到CHAVE: {chave_number}")
            # 显示可用的CHAVE值
            sample_values = datasheet_data[chave_col].unique()[:5]
            st.info(f"可用的CHAVE值示例: {', '.join(sample_values)}")
    else:
        st.error("❌ 未找到CHAVE列")
        st.info(f"请检查Datasheet是否包含 'Chave' 列。当前列名: {list(datasheet_data.columns)}")

st.sidebar.markdown("---")
st.sidebar.info("""
**使用说明:**
1. 上传CSV格式的DCN和Datasheet
2. 输入CHAVE号码
3. 自动匹配并生成脚本

**下一步功能:**
- 设备名自动转换 (NO → ZT)
- 无线参数自动提取
- 完整ZTE脚本生成
""")
