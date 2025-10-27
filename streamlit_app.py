import streamlit as st
import pandas as pd
import base64
from datetime import datetime
import re

# 页面配置
st.set_page_config(
    page_title="ZTE微波脚本生成器",
    page_icon="📡",
    layout="wide"
)

st.title("📡 ZTE微波开站脚本生成器")
st.subheader("简化版本 - 修复IP地址格式问题")

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
        
        # 修复IP地址格式问题
        df = DataProcessor.fix_ip_addresses(df)
        
        return df

    @staticmethod
    def fix_ip_addresses(df):
        """修复IP地址格式问题"""
        if 'IP地址' not in df.columns:
            return df
        
        def convert_ip_format(ip_value):
            if pd.isna(ip_value):
                return ip_value
            
            ip_str = str(ip_value).strip()
            
            # 如果已经是正常IP格式，直接返回
            if re.match(r'^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$', ip_str):
                return ip_str
            
            # 高优先级1: 处理逗号分隔的IP (如 "10,226,106,192")
            if ',' in ip_str:
                ip_parts = ip_str.split(',')
                if len(ip_parts) == 4:
                    # 验证每个部分是否在有效范围内
                    if all(0 <= int(part) <= 255 for part in ip_parts):
                        return '.'.join(ip_parts)
            
            # 高优先级2: 处理AABBBCCCDDD格式 (如 "10226106192")
            ip_num = ip_str.replace('.', '').replace(',', '')
            if ip_num.isdigit() and len(ip_num) == 11:
                # AABBBCCCDDD 格式: AA=10, BBB=226, CCC=106, DDD=192
                part1 = ip_num[:2]    # 10
                part2 = ip_num[2:5]   # 226
                part3 = ip_num[5:8]   # 106
                part4 = ip_num[8:]    # 192
                
                # 验证每个部分是否在有效范围内
                if (0 <= int(part1) <= 255 and 
                    0 <= int(part2) <= 255 and 
                    0 <= int(part3) <= 255 and 
                    0 <= int(part4) <= 255):
                    return f"{part1}.{part2}.{part3}.{part4}"
            
            # 其他情况: 自动智能识别
            if ip_num.isdigit() and len(ip_num) >= 7:
                # 尝试不同的分割方式
                for i in range(1, 4):    # 第一部分长度
                    for j in range(1, 4): # 第二部分长度
                        for k in range(1, 4): # 第三部分长度
                            if i + j + k < len(ip_num):
                                part1 = ip_num[:i]
                                part2 = ip_num[i:i+j]
                                part3 = ip_num[i+j:i+j+k]
                                part4 = ip_num[i+j+k:]
                                
                                # 验证每个部分是否在有效范围内
                                if (0 <= int(part1) <= 255 and 
                                    0 <= int(part2) <= 255 and 
                                    0 <= int(part3) <= 255 and 
                                    0 <= int(part4) <= 255):
                                    return f"{part1}.{part2}.{part3}.{part4}"
            
            # 如果无法解析，返回原始值
            return ip_str
        
        # 应用IP地址格式修复
        original_ips = df['IP地址'].tolist()
        df['IP地址'] = df['IP地址'].apply(convert_ip_format)
        
        # 显示修复信息
        for i, (original, fixed) in enumerate(zip(original_ips, df['IP地址'])):
            if original != fixed:
                st.info(f"🔧 IP地址修复: {original} → {fixed}")
        
        return df

    @staticmethod
    def parse_datasheet_file(file):
        """解析Datasheet文件 - 修复换行符问题"""
        try:
            if file.name.endswith('.csv'):
                df = pd.read_csv(file, header=1)
            elif file.name.endswith(('.xlsx', '.xls')):
                # 先读取原始数据，处理列名中的换行符
                df_raw = pd.read_excel(file, header=1)
                
                # 清理列名：移除换行符和多余空格
                df_raw.columns = [re.sub(r'\s*\n\s*', ' ', str(col).strip()) for col in df_raw.columns]
                
                df = df_raw
            else:
                st.error("❌ 不支持的文件格式")
                return None
                
            return df
            
        except Exception as e:
            st.error(f"❌ Datasheet解析失败: {e}")
            return None
    
    @staticmethod
    def auto_detect_columns(datasheet_data, log_container):
        """自动检测列名 - 修复换行符问题"""
        detected_columns = {}
        
        # 清理后的列名映射（移除换行符）
        column_mapping = {
            'chave': 'Chave',
            'site_a': 'Site ID Estação 1', 
            'site_b': 'Site ID Estação 2',
            'device': 'Nome Elemento Estação 1',
            'bandwidth': 'Largura de banda do canal (MHz)',
            'tx_power': 'Potência TX máxima (dBm)',
            'tx_freq': 'Frequência Central Estação 1 (MHz)',
            'rx_freq': 'Frequência Central Estação 2 (MHz)'
        }
        
        # 清理实际列名（移除换行符）
        cleaned_columns = {}
        for actual_col in datasheet_data.columns:
            cleaned_col = re.sub(r'\s*\n\s*', ' ', str(actual_col).strip())
            cleaned_columns[cleaned_col] = actual_col
        
        # 检查每个列是否存在（使用清理后的列名）
        for col_type, expected_col in column_mapping.items():
            # 清理预期列名
            cleaned_expected = re.sub(r'\s*\n\s*', ' ', expected_col.strip())
            
            if cleaned_expected in cleaned_columns:
                actual_col_name = cleaned_columns[cleaned_expected]
                detected_columns[col_type] = actual_col_name
                log_container.success(f"✅ 找到{col_type}列: '{actual_col_name}'")
            else:
                log_container.error(f"❌ 未找到{col_type}列: '{cleaned_expected}'")
                
                # 尝试部分匹配
                found = False
                for cleaned_col, actual_col in cleaned_columns.items():
                    if any(keyword in cleaned_col for keyword in expected_col.split()[:2]):
                        detected_columns[col_type] = actual_col
                        log_container.warning(f"⚠️ 使用部分匹配 {col_type}: '{actual_col}'")
                        found = True
                        break
                
                if not found:
                    log_container.error(f"❌ 无法匹配 {col_type} 列，请检查文件格式")
        
        return detected_columns
    
    @staticmethod
    def find_site_config(dcn_data, datasheet_data, chave_number, log_container):
        """根据CHAVE查找完整配置"""
        if dcn_data is None or datasheet_data is None:
            return None
        
        log_container.info(f"🔍 正在查找CHAVE: {chave_number}")
        
        # 自动检测列名
        detected_columns = DataProcessor.auto_detect_columns(datasheet_data, log_container)
        
        # 检查必要列
        required_columns = ['chave', 'site_a', 'site_b', 'device']
        missing_columns = [col for col in required_columns if col not in detected_columns]
        
        if missing_columns:
            log_container.error(f"❌ 缺少必要的列: {missing_columns}")
            log_container.info("💡 请检查Datasheet文件格式，或手动指定列名")
            return None
        
        # 查找匹配的CHAVE
        chave_col = detected_columns['chave']
        datasheet_data[chave_col] = datasheet_data[chave_col].astype(str).str.strip()
        matches = datasheet_data[datasheet_data[chave_col] == chave_number.strip()]
        
        if len(matches) == 0:
            log_container.error(f"❌ 未找到CHAVE: {chave_number}")
            # 显示可用的CHAVE值
            unique_chaves = datasheet_data[chave_col].unique()[:10]  # 只显示前10个
            log_container.info(f"可用的CHAVE值: {list(unique_chaves)}")
            return None
        
        match_data = matches.iloc[0]
        log_container.success(f"✅ 找到CHAVE配置")
        
        # 提取站点和设备信息
        site_a = str(match_data.get(detected_columns['site_a'], '')).strip()
        site_b = str(match_data.get(detected_columns['site_b'], '')).strip()
        device_name = str(match_data.get(detected_columns['device'], '')).strip()
        
        log_container.info(f"📡 站点A: {site_a}")
        log_container.info(f"📡 站点B: {site_b}")
        log_container.info(f"🖥️  设备: {device_name}")
        
        if not site_a or not site_b or not device_name:
            log_container.error("❌ 缺少必要的站点或设备信息")
            return None
        
        # 设备名转换 NO → ZT
        device_name = device_name.replace('NO', 'ZT')
        log_container.info(f"🔄 设备名转换后: {device_name}")
        
        # 在DCN中查找站点信息
        site_a_info = None
        site_b_info = None
        
        for _, site_row in dcn_data.iterrows():
            site_name = str(site_row.get('站点名称', '')).strip()
            if site_a in site_name:
                site_a_info = site_row.to_dict()
                log_container.success(f"✅ 在DCN中找到站点A: {site_name}")
                log_container.info(f"   IP地址: {site_a_info.get('IP地址', '未找到')}")
            if site_b in site_name:
                site_b_info = site_row.to_dict()
                log_container.success(f"✅ 在DCN中找到站点B: {site_name}")
                log_container.info(f"   IP地址: {site_b_info.get('IP地址', '未找到')}")
        
        if not site_a_info or not site_b_info:
            log_container.warning("⚠️ 在DCN中未找到完整的站点信息，使用默认值")
        
        # 提取无线参数
        bandwidth = match_data.get(detected_columns.get('bandwidth'), 112)
        tx_power_raw = match_data.get(detected_columns.get('tx_power'), 22)  # 原始值，如22
        tx_freq_a = match_data.get(detected_columns.get('tx_freq'), 14977)  # 站点A的发射频率
        rx_freq_a = match_data.get(detected_columns.get('rx_freq'), 14577)  # 站点A的接收频率
        
        # 转换频率单位 MHz → KHz (乘以1000)
        bandwidth_khz = int(bandwidth) * 1000
        tx_freq_a_khz = int(tx_freq_a) * 1000
        rx_freq_a_khz = int(rx_freq_a) * 1000
        
        # 修正功率值：Datasheet中的值是实际值的1/10，需要乘以10
        tx_power_corrected = int(tx_power_raw) * 10
        
        # 站点B的频率应该是站点A的相反
        # 站点B的TX频率 = 站点A的RX频率
        # 站点B的RX频率 = 站点A的TX频率
        tx_freq_b_khz = rx_freq_a_khz
        rx_freq_b_khz = tx_freq_a_khz
        
        log_container.info(f"📡 无线参数:")
        log_container.info(f"  - 带宽: {bandwidth}MHz → {bandwidth_khz}KHz")
        log_container.info(f"  - 功率: {tx_power_raw}dBm(原始) → {tx_power_corrected}dBm(修正)")
        log_container.info(f"  - 站点A: TX={tx_freq_a}MHz→{tx_freq_a_khz}KHz, RX={rx_freq_a}MHz→{rx_freq_a_khz}KHz")
        log_container.info(f"  - 站点B: TX={rx_freq_a}MHz→{tx_freq_b_khz}KHz, RX={tx_freq_a}MHz→{rx_freq_b_khz}KHz")
        
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
                'device_name': device_name,
                'ip': site_a_info.get('IP地址') if site_a_info else '10.211.51.202',
                'vlan': site_a_info.get('VLAN') if site_a_info else 2929,
                'gateway': gateway_a,
                'tx_frequency': tx_freq_a_khz,
                'rx_frequency': rx_freq_a_khz
            },
            'site_b': {
                'site_name': site_b,
                'device_name': device_name.replace(site_a, site_b) if site_a in device_name else f"MWE-MG-{site_b}-N1-ZT",
                'ip': site_b_info.get('IP地址') if site_b_info else '10.211.51.203',
                'vlan': site_b_info.get('VLAN') if site_b_info else 2929,
                'gateway': gateway_b,
                'tx_frequency': tx_freq_b_khz,
                'rx_frequency': rx_freq_b_khz
            },
            'radio_params': {
                'bandwidth': bandwidth_khz,
                'tx_power': tx_power_corrected,  # 使用修正后的功率值
                'modulation': 'bpsk',
                'operation_mode': 'G02'
            }
        }
        
        return config

# ZTEScriptGenerator 类保持不变（与之前相同）
class ZTEScriptGenerator:
    @staticmethod
    def generate_script(config, for_site_a=True):
        """生成精确的ZTE脚本 - 修复频率映射问题"""
        if for_site_a:
            site = config['site_a']
            peer = config['site_b']
            site_id = site['site_name']
            tx_frequency = site['tx_frequency']  # 使用站点A自己的TX频率
            rx_frequency = site['rx_frequency']  # 使用站点A自己的RX频率
        else:
            site = config['site_b']
            peer = config['site_a']
            site_id = site['site_name']
            tx_frequency = site['tx_frequency']  # 使用站点B自己的TX频率
            rx_frequency = site['rx_frequency']  # 使用站点B自己的RX频率
        
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
tx-frequency  {tx_frequency} 
rx-frequency  {rx_frequency} 
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
tx-frequency  {tx_frequency} 
rx-frequency  {rx_frequency} 
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
if 'config' not in st.session_state:
    st.session_state.config = None

# 文件上传
st.sidebar.header("文件上传")

dcn_file = st.sidebar.file_uploader("上传DCN文件", type=['xlsx', 'xls', 'csv'], key="dcn")
datasheet_file = st.sidebar.file_uploader("上传Datasheet", type=['xlsx', 'xls', 'csv'], key="datasheet")

processor = DataProcessor()
generator = ZTEScriptGenerator()

if dcn_file:
    st.session_state.dcn_data = processor.parse_dcn_file(dcn_file)
    if st.session_state.dcn_data is not None:
        st.success(f"✅ DCN文件加载成功，共 {len(st.session_state.dcn_data)} 条记录")
        # 显示DCN数据预览（IP地址修复后）
        with st.expander("📊 DCN数据预览", expanded=False):
            st.dataframe(st.session_state.dcn_data.head())

if datasheet_file:
    st.session_state.datasheet_data = processor.parse_datasheet_file(datasheet_file)
    if st.session_state.datasheet_data is not None:
        st.success(f"✅ Datasheet加载成功，共 {len(st.session_state.datasheet_data)} 条记录")

# CHAVE输入和脚本生成
st.markdown("---")
chave_number = st.text_input("输入CHAVE号码:", placeholder="例如: CODV29, 4G-CORD10")

if chave_number and st.session_state.dcn_data is not None and st.session_state.datasheet_data is not None:
    # 创建日志容器
    with st.expander("📋 处理日志", expanded=False):
        log_container = st.container()
        
        with log_container:
            config = processor.find_site_config(
                st.session_state.dcn_data, 
                st.session_state.datasheet_data, 
                chave_number,
                log_container
            )
    
    if config:
        st.session_state.config = config
        st.success("🎯 配置匹配成功！")

# 并排显示脚本
if hasattr(st.session_state, 'config') and st.session_state.config:
    st.markdown("---")
    st.subheader("📜 生成的配置脚本")
    
    # 生成两个站点的脚本
    script_a = generator.generate_script(st.session_state.config, for_site_a=True)
    script_b = generator.generate_script(st.session_state.config, for_site_a=False)
    
    site_a_name = st.session_state.config['site_a']['device_name']
    site_b_name = st.session_state.config['site_b']['device_name']
    
    # 并排显示脚本
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader(f"📍 {site_a_name}")
        st.info(f"IP: {st.session_state.config['site_a']['ip']}")
        st.info(f"TX: {st.session_state.config['site_a']['tx_frequency']} KHz")
        st.info(f"RX: {st.session_state.config['site_a']['rx_frequency']} KHz")
        st.info(f"功率: {st.session_state.config['radio_params']['tx_power']} dBm")
        with st.expander(f"查看 {site_a_name} 脚本", expanded=True):
            st.code(script_a, language='bash')
        st.markdown(create_download_link(script_a, f"{site_a_name}.txt", "📥 下载脚本"), unsafe_allow_html=True)
    
    with col2:
        st.subheader(f"📍 {site_b_name}")
        st.info(f"IP: {st.session_state.config['site_b']['ip']}")
        st.info(f"TX: {st.session_state.config['site_b']['tx_frequency']} KHz")
        st.info(f"RX: {st.session_state.config['site_b']['rx_frequency']} KHz")
        st.info(f"功率: {st.session_state.config['radio_params']['tx_power']} dBm")
        with st.expander(f"查看 {site_b_name} 脚本", expanded=True):
            st.code(script_b, language='bash')
        st.markdown(create_download_link(script_b, f"{site_b_name}.txt", "📥 下载脚本"), unsafe_allow_html=True)

# 配置详情折叠页
if hasattr(st.session_state, 'config') and st.session_state.config:
    with st.expander("🔧 配置详情", expanded=False):
        st.json(st.session_state.config)

st.sidebar.markdown("---")
st.sidebar.info("""
**IP地址智能识别版本:**
✅ 高优先级: 逗号分隔格式
✅ 高优先级: AABBBCCCDDD格式  
✅ 自动智能识别其他格式
✅ 实时显示修复过程
""")
