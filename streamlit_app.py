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
st.subheader("巴西项目专用 - 修复数据读取")

class DataProcessor:
    @staticmethod
    def parse_dcn_file(file):
        """解析DCN文件 - 支持Excel格式"""
        try:
            if file.name.endswith('.csv'):
                df = pd.read_csv(file)
            elif file.name.endswith(('.xlsx', '.xls')):
                # 读取Excel文件
                excel_file = pd.ExcelFile(file)
                sheet_names = excel_file.sheet_names
                
                st.info(f"📑 检测到 {len(sheet_names)} 个sheet")
                
                # 自动查找 PROJETO LÓGICO sheet
                target_sheet = None
                for sheet in sheet_names:
                    if 'PROJETO LÓGICO' in sheet.upper() and 'AUTOMÁTICO' not in sheet.upper():
                        target_sheet = sheet
                        break
                
                if target_sheet is None:
                    target_sheet = sheet_names[0]
                    st.warning(f"使用第一个sheet: {target_sheet}")
                else:
                    st.success(f"使用sheet: {target_sheet}")
                
                df = pd.read_excel(file, sheet_name=target_sheet)
            else:
                st.error("❌ 不支持的文件格式")
                return None
            
            # 数据清理
            df = DataProcessor.clean_dcn_data(df)
            st.success(f"✅ DCN文件加载成功，共 {len(df)} 条记录")
            return df
            
        except Exception as e:
            st.error(f"❌ DCN文件解析失败: {e}")
            return None
    
    @staticmethod
    def clean_dcn_data(df):
        """清理DCN数据"""
        # 移除全空行
        df = df.dropna(how='all')
        
        # 查找数据开始的行
        for idx, row in df.iterrows():
            row_str = ' '.join([str(x) for x in row.values if pd.notna(x)])
            if any(keyword in row_str for keyword in ['End. IP', '10.211.', 'IP地址']):
                # 重新设置列名
                new_columns = df.iloc[idx]
                df = df.iloc[idx + 1:]
                df.columns = [str(col).strip() for col in new_columns.values]
                break
        
        # 标准化列名
        column_mapping = {
            'End. IP': 'IP地址',
            'Subnet': '子网掩码', 
            'Obs': '站点名称',
            'Vlan': 'VLAN'
        }
        
        for old_col, new_col in column_mapping.items():
            if old_col in df.columns:
                df = df.rename(columns={old_col: new_col})
        
        df = df.dropna(how='all')
        return df

    @staticmethod
    def parse_datasheet_file(file):
        """解析Datasheet文件 - 从第二行开始读取数据"""
        try:
            if file.name.endswith('.csv'):
                # CSV文件：跳过第一行（表头），使用第二行作为列名
                df = pd.read_csv(file, header=1)  # header=1 表示使用第二行作为列名
                st.info("📋 使用第二行作为列名（CSV格式）")
            elif file.name.endswith(('.xlsx', '.xls')):
                # Excel文件：跳过第一行，使用第二行作为列名
                df = pd.read_excel(file, header=1)  # header=1 表示使用第二行作为列名
                st.info("📋 使用第二行作为列名（Excel格式）")
            else:
                st.error("❌ 不支持的文件格式")
                return None
            
            st.success(f"✅ Datasheet加载成功，共 {len(df)} 条记录")
            
            # 显示处理后的列名和数据
            st.info(f"📋 处理后的列名: {list(df.columns)}")
            st.info(f"📊 前3行数据:")
            st.dataframe(df.head(3))
            
            return df
            
        except Exception as e:
            st.error(f"❌ Datasheet解析失败: {e}")
            return None
    
    @staticmethod
    def find_chave_column(datasheet_data):
        """查找CHAVE列"""
        chave_columns = ['Chave', 'CHAVE', 'chave', '站点编号', 'Unnamed: 0']
        
        # 显示所有列名用于调试
        st.info(f"🔍 正在查找CHAVE列，可用列: {list(datasheet_data.columns)}")
        
        for col in chave_columns:
            if col in datasheet_data.columns:
                st.success(f"✅ 找到CHAVE列: '{col}'")
                return col
        
        # 如果没有找到标准列名，尝试查找包含'chave'的列
        for col in datasheet_data.columns:
            if 'chave' in str(col).lower():
                st.success(f"✅ 找到CHAVE列（模糊匹配）: '{col}'")
                return col
        
        return None
    
    @staticmethod
    def find_site_config(dcn_data, datasheet_data, chave_number):
        """根据CHAVE查找完整配置"""
        if dcn_data is None or datasheet_data is None:
            return None
        
        # 查找CHAVE列
        chave_col = DataProcessor.find_chave_column(datasheet_data)
        if not chave_col:
            st.error("❌ 未找到CHAVE列")
            return None
        
        # 清理CHAVE列数据
        datasheet_data[chave_col] = datasheet_data[chave_col].astype(str).str.strip()
        
        # 显示CHAVE列的所有值用于调试
        unique_chaves = datasheet_data[chave_col].unique()
        st.info(f"📋 CHAVE列中的所有值: {list(unique_chaves)}")
        
        # 查找匹配的CHAVE
        matches = datasheet_data[datasheet_data[chave_col] == chave_number.strip()]
        
        if len(matches) == 0:
            st.error(f"❌ 未找到CHAVE: {chave_number}")
            st.info(f"💡 请检查CHAVE号码是否正确。可用的CHAVE值: {list(unique_chaves)}")
            return None
        
        match_data = matches.iloc[0]
        st.success(f"✅ 找到CHAVE配置")
        
        # 显示匹配的完整数据用于调试
        st.info("📊 匹配的完整数据:")
        st.dataframe(matches)
        
        # 提取站点名称 (L/M列) - 使用字母列名
        site_a = None
        site_b = None
        
        # 尝试不同的列名格式
        for col in ['L', 'M', 'Unnamed: 11', 'Unnamed: 12']:  # L和M列可能被重命名
            if col in match_data:
                if site_a is None:
                    site_a = str(match_data[col]).strip()
                    st.info(f"✅ 找到站点A ({col}): {site_a}")
                else:
                    site_b = str(match_data[col]).strip()
                    st.info(f"✅ 找到站点B ({col}): {site_b}")
                    break
        
        if not site_a or not site_b:
            st.error("❌ 未找到站点名称(L/M列)")
            st.info(f"💡 可用的列: {list(match_data.index)}")
            return None
        
        st.success(f"📡 关联站点: {site_a} ↔ {site_b}")
        
        # 在DCN中查找站点信息
        site_a_info = None
        site_b_info = None
        
        for _, site_row in dcn_data.iterrows():
            site_name = str(site_row.get('站点名称', '')).strip()
            if site_a in site_name:
                site_a_info = site_row.to_dict()
                st.info(f"✅ 在DCN中找到站点A: {site_name}")
            if site_b in site_name:
                site_b_info = site_row.to_dict()
                st.info(f"✅ 在DCN中找到站点B: {site_name}")
        
        # 提取设备名称 (N/O列) 并转换 NO → ZT
        device_a = None
        device_b = None
        
        for col in ['N', 'O', 'Unnamed: 13', 'Unnamed: 14']:  # N和O列可能被重命名
            if col in match_data:
                if device_a is None:
                    device_a = str(match_data[col]).strip()
                    st.info(f"✅ 找到设备A ({col}): {device_a}")
                else:
                    device_b = str(match_data[col]).strip()
                    st.info(f"✅ 找到设备B ({col}): {device_b}")
                    break
        
        # 设备名转换 NO → ZT
        if device_a:
            device_a = device_a.replace('NO', 'ZT')
            st.info(f"🔄 设备A转换后: {device_a}")
        else:
            device_a = f"设备A_{chave_number}"
            
        if device_b:
            device_b = device_b.replace('NO', 'ZT')
            st.info(f"🔄 设备B转换后: {device_b}")
        else:
            device_b = f"设备B_{chave_number}"
        
        # 提取无线参数
        bandwidth = match_data.get('AN', 112000)
        tx_power = match_data.get('AS', 220)
        tx_freq = match_data.get('DR', 14977000)
        rx_freq = match_data.get('DS', 14577000)
        
        st.info(f"📡 无线参数: 带宽={bandwidth}, 功率={tx_power}, 发射={tx_freq}, 接收={rx_freq}")
        
        config = {
            'chave_number': chave_number,
            'site_a': {
                'name': site_a,
                'device': device_a,
                'ip': site_a_info.get('IP地址') if site_a_info else '10.211.51.202',
                'vlan': site_a_info.get('VLAN') if site_a_info else 2929,
            },
            'site_b': {
                'name': site_b,
                'device': device_b,
                'ip': site_b_info.get('IP地址') if site_b_info else '10.211.51.203',
                'vlan': site_b_info.get('VLAN') if site_b_info else 2929,
            },
            'radio_params': {
                'bandwidth': bandwidth,
                'tx_power': tx_power,
                'tx_frequency': tx_freq,
                'rx_frequency': rx_freq,
                'modulation': 'qpsk'
            }
        }
        
        return config

class ZTEScriptGenerator:
    @staticmethod
    def generate_script(config, for_site_a=True):
        """生成ZTE脚本"""
        if for_site_a:
            site = config['site_a']
            peer = config['site_b']
            direction = f"To_{peer['name'].split('-')[-1]}_H1"
        else:
            site = config['site_b']
            peer = config['site_a']
            direction = f"To_{peer['name'].split('-')[-1]}_H1"
        
        script = f"""configure terminal

hostname {site['device']}

device-para neIpv4 {site['ip']}

nms-vlan {site['vlan']}
interface vlan{site['vlan']}
ip address {site['ip']} 255.255.255.248
$

radio-channel radio-1/1/0/1
bandwidth {config['radio_params']['bandwidth']}
modulation
fixed-modulation {config['radio_params']['modulation']}
$
tx-frequency {config['radio_params']['tx_frequency']}
rx-frequency {config['radio_params']['rx_frequency']}
tx-power {config['radio_params']['tx_power']}
discription {direction}
yes
$

write
"""
        return script

def create_download_link(content, filename, text):
    """创建下载链接"""
    b64 = base64.b64encode(content.encode()).decode()
    href = f'<a href="data:file/txt;base64,{b64}" download="{filename}">{text}</a>'
    return href

# 初始化会话状态
if 'dcn_data' not in st.session_state:
    st.session_state.dcn_data = None
if 'datasheet_data' not in st.session_state:
    st.session_state.datasheet_data = None

# 文件上传
st.sidebar.header("文件上传")

dcn_file = st.sidebar.file_uploader("上传DCN文件", type=['xlsx', 'xls', 'csv'], key="dcn")
datasheet_file = st.sidebar.file_uploader("上传Datasheet", type=['xlsx', 'xls', 'csv'], key="datasheet")

processor = DataProcessor()
generator = ZTEScriptGenerator()

if dcn_file:
    st.session_state.dcn_data = processor.parse_dcn_file(dcn_file)

if datasheet_file:
    st.session_state.datasheet_data = processor.parse_datasheet_file(datasheet_file)

# CHAVE输入和脚本生成
st.markdown("---")
chave_number = st.text_input("输入CHAVE号码:", placeholder="例如: CODV29, 4G-CORD10")

if chave_number and st.session_state.dcn_data is not None and st.session_state.datasheet_data is not None:
    config = processor.find_site_config(
        st.session_state.dcn_data, 
        st.session_state.datasheet_data, 
        chave_number
    )
    
    if config:
        st.success("🎯 配置匹配成功！")
        
        # 显示配置详情
        with st.expander("配置详情"):
            st.json(config)
        
        # 生成脚本
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button(f"生成 {config['site_a']['name']} 脚本"):
                script = generator.generate_script(config, for_site_a=True)
                st.session_state.script_a = script
                st.session_state.site_a = config['site_a']['name']
        
        with col2:
            if st.button(f"生成 {config['site_b']['name']} 脚本"):
                script = generator.generate_script(config, for_site_a=False)
                st.session_state.script_b = script
                st.session_state.site_b = config['site_b']['name']

# 显示生成的脚本
if hasattr(st.session_state, 'script_a'):
    st.markdown("---")
    st.subheader(f"脚本 - {st.session_state.site_a}")
    st.code(st.session_state.script_a, language='bash')
    filename = f"{st.session_state.site_a}.txt"
    st.markdown(create_download_link(st.session_state.script_a, filename, "📥 下载脚本"), unsafe_allow_html=True)

if hasattr(st.session_state, 'script_b'):
    st.markdown("---")
    st.subheader(f"脚本 - {st.session_state.site_b}")
    st.code(st.session_state.script_b, language='bash')
    filename = f"{st.session_state.site_b}.txt"
    st.markdown(create_download_link(st.session_state.script_b, filename, "📥 下载脚本"), unsafe_allow_html=True)

st.sidebar.markdown("---")
st.sidebar.info("""
**修复说明:**
✅ 从第二行开始读取数据
✅ 增强列名识别
✅ 详细的调试信息
✅ 支持Excel格式
""")
