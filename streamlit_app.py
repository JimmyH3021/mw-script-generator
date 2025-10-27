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
st.subheader("直接从第二行识别列名")

class DataProcessor:
    @staticmethod
    def parse_dcn_file(file):
        """解析DCN文件"""
        try:
            if file.name.endswith('.csv'):
                df = pd.read_csv(file)
            elif file.name.endswith(('.xlsx', '.xls')):
                excel_file = pd.ExcelFile(file)
                sheet_names = excel_file.sheet_names
                
                # 自动查找 PROJETO LÓGICO sheet
                target_sheet = None
                for sheet in sheet_names:
                    if 'PROJETO LÓGICO' in sheet.upper() and 'AUTOMÁTICO' not in sheet.upper():
                        target_sheet = sheet
                        break
                
                if target_sheet is None:
                    target_sheet = sheet_names[0]
                
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
        df = df.dropna(how='all')
        
        # 查找数据开始的行
        for idx, row in df.iterrows():
            row_str = ' '.join([str(x) for x in row.values if pd.notna(x)])
            if any(keyword in row_str for keyword in ['End. IP', '10.211.', 'IP地址']):
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
        """解析Datasheet文件 - 直接从第二行开始"""
        try:
            if file.name.endswith('.csv'):
                # 从第二行开始读取，使用第二行作为列名
                df = pd.read_csv(file, header=1)
            elif file.name.endswith(('.xlsx', '.xls')):
                # 从第二行开始读取，使用第二行作为列名
                df = pd.read_excel(file, header=1)
            else:
                st.error("❌ 不支持的文件格式")
                return None
            
            st.success(f"✅ Datasheet加载成功，共 {len(df)} 条记录")
            
            # 显示处理后的列名
            st.info("📋 从第二行识别的列名:")
            columns_info = []
            for i, col in enumerate(df.columns):
                columns_info.append(f"{i}: '{col}'")
            st.write(", ".join(columns_info))
            
            # 显示前3行数据
            st.info("📊 前3行数据:")
            st.dataframe(df.head(3))
            
            return df
            
        except Exception as e:
            st.error(f"❌ Datasheet解析失败: {e}")
            return None
    
    @staticmethod
    def find_site_config(dcn_data, datasheet_data, chave_number):
        """根据CHAVE查找完整配置"""
        if dcn_data is None or datasheet_data is None:
            return None
        
        st.info(f"🔍 正在查找CHAVE: {chave_number}")
        
        # 显示所有列名用于选择
        st.info("📋 请从以下列名中选择对应的列:")
        
        # 创建列选择界面
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            chave_col = st.selectbox("选择CHAVE列", options=datasheet_data.columns.tolist(), key="chave_col")
        
        with col2:
            site_a_col = st.selectbox("选择站点A列", options=datasheet_data.columns.tolist(), key="site_a_col")
        
        with col3:
            site_b_col = st.selectbox("选择站点B列", options=datasheet_data.columns.tolist(), key="site_b_col")
        
        with col4:
            device_col = st.selectbox("选择设备列", options=datasheet_data.columns.tolist(), key="device_col")
        
        # 查找匹配的CHAVE
        datasheet_data[chave_col] = datasheet_data[chave_col].astype(str).str.strip()
        matches = datasheet_data[datasheet_data[chave_col] == chave_number.strip()]
        
        if len(matches) == 0:
            st.error(f"❌ 未找到CHAVE: {chave_number}")
            # 显示可用的CHAVE值
            unique_chaves = datasheet_data[chave_col].unique()
            st.info(f"可用的CHAVE值: {list(unique_chaves)}")
            return None
        
        match_data = matches.iloc[0]
        st.success(f"✅ 找到CHAVE配置")
        
        # 提取站点和设备信息
        site_a = str(match_data.get(site_a_col, '')).strip()
        site_b = str(match_data.get(site_b_col, '')).strip()
        device_name = str(match_data.get(device_col, '')).strip()
        
        st.info(f"📡 站点A: {site_a}")
        st.info(f"📡 站点B: {site_b}")
        st.info(f"🖥️  设备: {device_name}")
        
        if not site_a or not site_b or not device_name:
            st.error("❌ 缺少必要的站点或设备信息")
            return None
        
        # 设备名转换 NO → ZT
        device_name = device_name.replace('NO', 'ZT')
        st.info(f"🔄 设备名转换后: {device_name}")
        
        # 在DCN中查找站点信息
        site_a_info = None
        site_b_info = None
        
        for _, site_row in dcn_data.iterrows():
            site_name = str(site_row.get('站点名称', '')).strip()
            if site_a in site_name:
                site_a_info = site_row.to_dict()
                st.success(f"✅ 在DCN中找到站点A: {site_name}")
            if site_b in site_name:
                site_b_info = site_row.to_dict()
                st.success(f"✅ 在DCN中找到站点B: {site_name}")
        
        # 提取无线参数 - 手动选择列
        st.info("🎛️  请选择无线参数列:")
        
        col5, col6, col7, col8 = st.columns(4)
        
        with col5:
            bandwidth_col = st.selectbox("选择带宽列", options=datasheet_data.columns.tolist(), key="bandwidth_col")
        
        with col6:
            tx_power_col = st.selectbox("选择发射功率列", options=datasheet_data.columns.tolist(), key="tx_power_col")
        
        with col7:
            tx_freq_col = st.selectbox("选择发射频率列", options=datasheet_data.columns.tolist(), key="tx_freq_col")
        
        with col8:
            rx_freq_col = st.selectbox("选择接收频率列", options=datasheet_data.columns.tolist(), key="rx_freq_col")
        
        bandwidth = match_data.get(bandwidth_col, 112000)
        tx_power = match_data.get(tx_power_col, 220)
        tx_freq = match_data.get(tx_freq_col, 14977000)
        rx_freq = match_data.get(rx_freq_col, 14577000)
        
        st.info(f"📡 无线参数: 带宽={bandwidth}, 功率={tx_power}, 发射={tx_freq}, 接收={rx_freq}")
        
        # 计算网关
        def calculate_gateway(ip_with_subnet):
            if not ip_with_subnet or '/' not in str(ip_with_subnet):
                return '10.211.51.201'
            network_ip = str(ip_with_subnet).split('/')[0]
            ip_parts = network_ip.split('.')
            return f"{ip_parts[0]}.{ip_parts[1]}.{ip_parts[2]}.{int(ip_parts[3]) + 1}"
        
        gateway_a = calculate_gateway(site_a_info.get('子网掩码') if site_a_info else None)
        gateway_b = calculate_gateway(site_b_info.get('子网掩码') if site_b_info else None)
        
        config = {
            'chave_number': chave_number,
            'site_a': {
                'site_name': site_a,
                'device_name': f"MWE-MG-{site_a}-N1-ZT",
                'ip': site_a_info.get('IP地址') if site_a_info else '10.211.51.202',
                'vlan': site_a_info.get('VLAN') if site_a_info else 2929,
                'gateway': gateway_a
            },
            'site_b': {
                'site_name': site_b,
                'device_name': f"MWE-MG-{site_b}-N1-ZT",
                'ip': site_b_info.get('IP地址') if site_b_info else '10.211.51.203',
                'vlan': site_b_info.get('VLAN') if site_b_info else 2929,
                'gateway': gateway_b
            },
            'radio_params': {
                'bandwidth': bandwidth,
                'tx_power': tx_power,
                'tx_frequency': tx_freq,
                'rx_frequency': rx_freq,
                'modulation': 'bpsk',
                'operation_mode': 'G02'
            }
        }
        
        return config

class ZTEScriptGenerator:
    @staticmethod
    def generate_script(config, for_site_a=True):
        """生成精确的ZTE脚本"""
        if for_site_a:
            site = config['site_a']
            peer = config['site_b']
            site_id = site['site_name']
        else:
            site = config['site_b']
            peer = config['site_a']
            site_id = site['site_name']
        
        # 生成对端描述
        peer_suffix = peer['site_name'].split('-')[-1] if '-' in peer['site_name'] else peer['site_name']
        
        script = f"""configure terminal

radio-global-switch enable 

!
device-para siteId  {site_id} 
hostname {site['device_name']}

!
device-para neIpType  ipv4 
device-para neIpv4  {site['ip']} 

!
nms-vlan  {site['vlan']} 
interface   vlan{site['vlan']} 
ip address  {site['ip']}  255.255.255.248 
$

!
ip route 0.0.0.0 0.0.0.0  {site['gateway']} 

!

clock timezone  America/Sao_Paulo  -3 


!
ntp  enable 
ntp poll-interval  8 
ntp source ipv4  {site['ip']} 

!
ntp server     10.192.12.200  priority  1 

ntp server     10.216.96.174  priority  2 

!
snmp-server version v3  enable 
snmp-server  enable trap snmp 
snmp-server trap-source  {site['ip']} 

!
snmp-server group   group1 v3 priv read AllView write AllView notify AllView 
snmp-server user  zte  group1 v3 auth  md5   ZXMW.nr10 priv des56   Ztesnmp2014 

snmp-server group   group1 v3 priv read AllView write AllView notify AllView 
snmp-server user  telco_zte  group1 v3 auth  md5   Telco@zte123 priv des56   Telco@zte123 

!
snmp-server host    10.98.178.109 trap version 3 priv  zte udp-port 162 snmp 

snmp-server host    10.103.67.13 trap version 3 priv  zte udp-port 162 snmp 

snmp-server host    10.216.59.50 trap version 3 priv  telco_zte udp-port 162 snmp 

snmp-server host    10.192.67.183 trap version 3 priv  telco_zte udp-port 162 snmp 

snmp-server host    10.221.63.226 trap version 3 priv  telco_zte udp-port 162 snmp 


radio-group xpic
xpic  xpic-1 
mode auto
members
member  tu-1/1/0/1 horizontal 
member  tu-1/1/0/2 vertical 
activate
yes
$
$
$
!
pla
pla-group  pla-1/1/0/1 
member  tu-1/1/0/1 
yes
$
member  tu-1/1/0/2 
yes
$
$

!
radio-channel  radio-1/1/0/1 
bandwidth  {config['radio_params']['bandwidth']} 
yes
modulation
fixed-modulation  {config['radio_params']['modulation']} 
$
tx-frequency  {config['radio_params']['tx_frequency']} 
rx-frequency  {config['radio_params']['rx_frequency']} 
tx-power  {config['radio_params']['tx_power']} 
discription  To_{peer_suffix}_H1 
operation-mode  {config['radio_params']['operation_mode']} 
yes
$

!
radio-channel  radio-1/1/0/2 
bandwidth  {config['radio_params']['bandwidth']} 
yes
modulation
fixed-modulation  {config['radio_params']['modulation']} 
$
tx-frequency  {config['radio_params']['tx_frequency']} 
rx-frequency  {config['radio_params']['rx_frequency']} 
tx-power  {config['radio_params']['tx_power']} 
discription  To_{peer_suffix}_V1 
operation-mode  {config['radio_params']['operation_mode']} 
yes
$

!
!

antenna 1
tu-name radio-1/1/0/1
azimuth 256.38
elevation -1.09
height 19.0
install-pol-type horizontal
manufactures ZTE
size 0.6
type MA06U15
$

antenna 2
tu-name radio-1/1/0/2
azimuth 256.38
elevation -1.09
height 19.0
install-pol-type vertical
manufactures ZTE
size 0.6
type MA06U15
$

$
interface  xgei-1/1/0/5 
no shutdown
description  
speed  speed-10G 
$

interface  xgei-1/1/0/6 
no shutdown
description  
speed  speed-10G 
$

interface  xgei-1/1/0/7 
no shutdown
description  
speed  speed-10G 
$

interface  xgei-1/1/0/8 
no shutdown
description  
speed  speed-10G 
$

!
switchvlan-configuration
interface  pla-1/1/0/1 
switchport mode trunk
switchport trunk vlan  {site['vlan']} 
$
$

switchvlan-configuration
interface  xgei-1/1/0/5 
switchport mode trunk
switchport trunk vlan  {site['vlan']} 
$
$

switchvlan-configuration
interface  xgei-1/1/0/6 
switchport mode trunk
switchport trunk vlan  {site['vlan']} 
$
$

switchvlan-configuration
interface  xgei-1/1/0/7 
switchport mode trunk
switchport trunk vlan  {site['vlan']} 
$
$

switchvlan-configuration
interface  xgei-1/1/0/8 
switchport mode trunk
switchport trunk vlan  {site['vlan']} 
$
$

! 

line   netconf absolute-timeout 0  

line netconf   idle-timeout 0  

exit 

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
            if st.button(f"生成 {config['site_a']['device_name']} 脚本", use_container_width=True):
                script = generator.generate_script(config, for_site_a=True)
                st.session_state.script_a = script
                st.session_state.site_a = config['site_a']['device_name']
        
        with col2:
            if st.button(f"生成 {config['site_b']['device_name']} 脚本", use_container_width=True):
                script = generator.generate_script(config, for_site_a=False)
                st.session_state.script_b = script
                st.session_state.site_b = config['site_b']['device_name']

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
**使用说明:**
1. 上传DCN和Datasheet文件
2. 查看从第二行识别的列名
3. 手动选择对应的列
4. 输入CHAVE号码
5. 生成脚本
""")
