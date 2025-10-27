# -*- coding: utf-8 -*-
import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime
import base64
import io
import re

# 页面配置
st.set_page_config(
    page_title="ZTE微波开站脚本生成器",
    page_icon="📡",
    layout="wide",
    initial_sidebar_state="expanded"
)

# CSS样式
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        color: #1f77b4;
        text-align: center;
        margin-bottom: 2rem;
    }
    .section-header {
        font-size: 1.5rem;
        color: #ff7f0e;
        margin-top: 2rem;
        margin-bottom: 1rem;
    }
    .success-box {
        background-color: #d4edda;
        border: 1px solid #c3e6cb;
        border-radius: 5px;
        padding: 15px;
        margin: 10px 0;
    }
    .warning-box {
        background-color: #fff3cd;
        border: 1px solid #ffeaa7;
        border-radius: 5px;
        padding: 15px;
        margin: 10px 0;
    }
    .upload-section {
        background-color: #e8f4fd;
        border: 2px dashed #1f77b4;
        border-radius: 10px;
        padding: 20px;
        text-align: center;
        margin: 10px 0;
    }
</style>
""", unsafe_allow_html=True)

class DataProcessor:
    """数据处理类 - 专门针对巴西ZTE微波项目"""
    
    @staticmethod
    def parse_dcn_file(file):
        """解析DCN文件 - 巴西格式"""
        try:
            if file.name.endswith('.csv'):
                df = pd.read_csv(file, encoding='utf-8')
            else:
                # Excel文件
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
            
            # 数据清理
            df_cleaned = DataProcessor.clean_dcn_data(df)
            st.success(f"✅ DCN文件加载成功，共 {len(df_cleaned)} 条记录")
            return df_cleaned
                
        except Exception as e:
            st.error(f"❌ DCN文件解析失败: {e}")
            return None
    
    @staticmethod
    def clean_dcn_data(df):
        """清理DCN数据"""
        # 移除全空行
        df = df.dropna(how='all')
        
        # 查找数据开始的行
        data_start_row = 0
        for idx, row in df.iterrows():
            row_str = ' '.join([str(x) for x in row.values if pd.notna(x)])
            if 'End. IP' in row_str or '10.211.' in row_str:
                data_start_row = idx
                break
        
        if data_start_row > 0:
            new_columns = df.iloc[data_start_row]
            df = df.iloc[data_start_row + 1:]
            df = df.reset_index(drop=True)
            df.columns = [str(col).strip() for col in new_columns.values]
        
        # 标准化列名
        column_mapping = {
            'End. IP': 'IP地址',
            'Subnet': '子网掩码', 
            'Obs': '站点名称',
            'Vlan': 'VLAN'
        }
        
        df = df.rename(columns=column_mapping)
        df = df.dropna(how='all')
        
        return df

    @staticmethod
    def parse_datasheet_file(file):
        """解析Datasheet文件 - 专门针对ZTE微波格式"""
        try:
            if file.name.endswith('.csv'):
                df = pd.read_csv(file, encoding='utf-8')
            else:
                df = pd.read_excel(file)
            
            st.success(f"✅ Datasheet加载成功，共 {len(df)} 条记录")
            
            # 显示列名帮助调试
            st.info(f"📋 Datasheet列名: {', '.join(df.columns.tolist())}")
            
            return df
        except Exception as e:
            st.error(f"❌ Datasheet解析失败: {e}")
            return None
    
    @staticmethod
    def find_site_config(dcn_data, datasheet_data, chave_number):
        """根据CHAVE号码查找完整的站点配置"""
        if dcn_data is None or datasheet_data is None:
            return None
        
        st.info(f"🔍 正在查找CHAVE: {chave_number}")
        
        # 1. 在Datasheet中查找CHAVE
        chave_match = None
        if 'Chave' in datasheet_data.columns:
            datasheet_data['Chave'] = datasheet_data['Chave'].astype(str)
            chave_match = datasheet_data[datasheet_data['Chave'] == str(chave_number)]
        
        if len(chave_match) == 0:
            st.error(f"❌ 在Datasheet中未找到CHAVE: {chave_number}")
            return None
        
        datasheet_info = chave_match.iloc[0]
        st.success(f"✅ 在Datasheet中找到CHAVE配置")
        
        # 2. 在DCN中查找对应的站点信息
        site_a_name = str(datasheet_info.get('L', '')).strip()  # 站点A名称
        site_b_name = str(datasheet_info.get('M', '')).strip()  # 站点B名称
        
        st.info(f"📡 关联站点: {site_a_name} ↔ {site_b_name}")
        
        # 查找站点A在DCN中的信息
        site_a_info = None
        site_b_info = None
        
        for idx, site_info in dcn_data.iterrows():
            site_name = str(site_info.get('站点名称', '')).strip()
            if site_a_name in site_name:
                site_a_info = site_info.to_dict()
            if site_b_name in site_name:
                site_b_info = site_info.to_dict()
        
        if not site_a_info and not site_b_info:
            st.error("❌ 在DCN中未找到对应的站点信息")
            return None
        
        # 3. 提取设备配置
        device_a = str(datasheet_info.get('N', '')).strip()  # 设备A
        device_b = str(datasheet_info.get('O', '')).strip()  # 设备B
        
        # 设备名称处理：将NO改为ZT
        device_a = device_a.replace('NO', 'ZT')
        device_b = device_b.replace('NO', 'ZT')
        
        # 4. 提取无线参数
        bandwidth = datasheet_info.get('AN', 112000)  # 带宽
        tx_power = datasheet_info.get('AS', 220)      # 发射功率
        tx_freq = datasheet_info.get('DR', 14977000)  # 发射频率
        rx_freq = datasheet_info.get('DS', 14577000)  # 接收频率
        
        # 返回完整配置
        config = {
            'chave_number': chave_number,
            'site_a': {
                'name': site_a_name,
                'device': device_a,
                'ip': site_a_info.get('IP地址') if site_a_info else None,
                'vlan': site_a_info.get('VLAN') if site_a_info else 2929,
                'subnet': site_a_info.get('子网掩码') if site_a_info else '10.211.51.200/29',
                'is_zt': 'ZT' in device_a
            },
            'site_b': {
                'name': site_b_name,
                'device': device_b,
                'ip': site_b_info.get('IP地址') if site_b_info else None,
                'vlan': site_b_info.get('VLAN') if site_b_info else 2929,
                'subnet': site_b_info.get('子网掩码') if site_b_info else '10.211.51.200/29',
                'is_zt': 'ZT' in device_b
            },
            'radio_params': {
                'bandwidth': bandwidth,
                'tx_power': tx_power,
                'tx_frequency': tx_freq,
                'rx_frequency': rx_freq,
                'modulation': 'qpsk',
                'operation_mode': 'G02'
            }
        }
        
        return config

class ZTEScriptGenerator:
    """ZTE微波脚本生成器 - 基于实际模板"""
    
    @staticmethod
    def generate_script(config, for_site_a=True):
        """生成ZTE微波设备脚本"""
        if for_site_a:
            site_config = config['site_a']
            peer_site = config['site_b']
            site_direction = "To_" + peer_site['name'].split('-')[-1]  # 提取如CODV29部分
        else:
            site_config = config['site_b']
            peer_site = config['site_a']
            site_direction = "To_" + peer_site['name'].split('-')[-1]  # 提取如4G-CORD10部分
        
        # 计算网关（子网第一个IP+1）
        subnet = site_config.get('subnet', '10.211.51.200/29')
        network_ip = subnet.split('/')[0]
        ip_parts = network_ip.split('.')
        gateway = f"{ip_parts[0]}.{ip_parts[1]}.{ip_parts[2]}.{int(ip_parts[3]) + 1}"
        
        # 站点ID（从设备名提取）
        site_id = site_config['device'].split('-')[-2] if '-' in site_config['device'] else site_config['name']
        
        script = f"""configure terminal

radio-global-switch enable 

!
device-para siteId  {site_id} 
hostname {site_config['device']}

!
device-para neIpType  ipv4 
device-para neIpv4  {site_config['ip']} 

!
nms-vlan  {site_config['vlan']} 
interface   vlan{site_config['vlan']} 
ip address  {site_config['ip']}  255.255.255.248 
$

!
ip route 0.0.0.0 0.0.0.0  {gateway} 

!

clock timezone  America/Sao_Paulo  -3 


!
ntp  enable 
ntp poll-interval  8 
ntp source ipv4  {site_config['ip']} 

!
ntp server     10.192.12.200  priority  1 

ntp server     10.216.96.174  priority  2 

!
snmp-server version v3  enable 
snmp-server  enable trap snmp 
snmp-server trap-source  {site_config['ip']} 

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
discription  {site_direction}_H1 
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
discription  {site_direction}_V1 
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
switchport trunk vlan  {site_config['vlan']} 
$
$

switchvlan-configuration
interface  xgei-1/1/0/5 
switchport mode trunk
switchport trunk vlan  {site_config['vlan']} 
$
$

switchvlan-configuration
interface  xgei-1/1/0/6 
switchport mode trunk
switchport trunk vlan  {site_config['vlan']} 
$
$

switchvlan-configuration
interface  xgei-1/1/0/7 
switchport mode trunk
switchport trunk vlan  {site_config['vlan']} 
$
$

switchvlan-configuration
interface  xgei-1/1/0/8 
switchport mode trunk
switchport trunk vlan  {site_config['vlan']} 
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

def main():
    """主应用"""
    st.markdown('<h1 class="main-header">📡 ZTE微波开站脚本生成器</h1>', unsafe_allow_html=True)
    st.markdown('<h3 style="text-align: center; color: #666;">巴西项目专用 - 基于实际脚本模板</h3>', unsafe_allow_html=True)
    
    # 初始化处理器和生成器
    processor = DataProcessor()
    generator = ZTEScriptGenerator()
    
    # 会话状态初始化
    if 'dcn_data' not in st.session_state:
        st.session_state.dcn_data = None
    if 'datasheet_data' not in st.session_state:
        st.session_state.datasheet_data = None
    if 'current_config' not in st.session_state:
        st.session_state.current_config = None
    
    # 侧边栏 - 文件上传
    with st.sidebar:
        st.header("📁 文件上传")
        
        # DCN文件上传
        dcn_file = st.file_uploader("上传DCN文件", type=['xlsx', 'xls', 'csv'], key="dcn_uploader")
        if dcn_file is not None:
            st.session_state.dcn_data = processor.parse_dcn_file(dcn_file)
            if st.session_state.dcn_data is not None:
                st.dataframe(st.session_state.dcn_data.head(3))
        
        # Datasheet文件上传
        datasheet_file = st.file_uploader("上传Datasheet", type=['xlsx', 'xls', 'csv'], key="datasheet_uploader")
        if datasheet_file is not None:
            st.session_state.datasheet_data = processor.parse_datasheet_file(datasheet_file)
            if st.session_state.datasheet_data is not None:
                st.dataframe(st.session_state.datasheet_data.head(3))
        
        st.markdown("---")
        st.header("📊 数据状态")
        if st.session_state.dcn_data is not None:
            st.success(f"✅ DCN: {len(st.session_state.dcn_data)} 站点")
        else:
            st.warning("❌ 未加载DCN文件")
            
        if st.session_state.datasheet_data is not None:
            st.success(f"✅ Datasheet: {len(st.session_state.datasheet_data)} 记录")
        else:
            st.warning("❌ 未加载Datasheet")
    
    # 主内容区
    col1, col2 = st.columns([1, 2])
    
    with col1:
        st.markdown('<div class="section-header">🔑 输入CHAVE号码</div>', unsafe_allow_html=True)
        
        chave_number = st.text_input(
            "CHAVE号码",
            placeholder="例如: CODV29, 4G-CORD10...",
            key="chave_input"
        )
        
        if chave_number:
            if st.session_state.dcn_data is not None and st.session_state.datasheet_data is not None:
                config = processor.find_site_config(
                    st.session_state.dcn_data, 
                    st.session_state.datasheet_data, 
                    chave_number
                )
                
                if config:
                    st.session_state.current_config = config
                    st.success("✅ 找到完整的站点配置")
                    
                    # 显示配置信息
                    with st.expander("📋 配置详情", expanded=True):
                        st.json(config)
                    
                    # 生成脚本选项
                    st.markdown('<div class="section-header">🚀 生成脚本</div>', unsafe_allow_html=True)
                    
                    if config['site_a']['ip'] and config['site_b']['ip']:
                        col1, col2 = st.columns(2)
                        
                        with col1:
                            if st.button(f"生成 {config['site_a']['name']} 脚本", use_container_width=True):
                                script = generator.generate_script(config, for_site_a=True)
                                st.session_state.current_script = script
                                st.session_state.script_for = config['site_a']['name']
                        
                        with col2:
                            if st.button(f"生成 {config['site_b']['name']} 脚本", use_container_width=True):
                                script = generator.generate_script(config, for_site_a=False)
                                st.session_state.current_script = script
                                st.session_state.script_for = config['site_b']['name']
                    else:
                        st.error("❌ 缺少IP地址信息，无法生成脚本")
            
            elif st.session_state.dcn_data is None:
                st.error("❌ 请先上传DCN文件")
            elif st.session_state.datasheet_data is None:
                st.error("❌ 请先上传Datasheet文件")
    
    with col2:
        st.markdown('<div class="section-header">📖 使用说明</div>', unsafe_allow_html=True)
        
        st.markdown("""
        <div class="config-box">
        <h4>🚀 专用工作流程：</h4>
        <ol>
            <li><strong>上传DCN文件</strong> - 包含站点IP、VLAN信息</li>
            <li><strong>上传Datasheet</strong> - 包含CHAVE、站点名称、设备参数</li>
            <li><strong>输入CHAVE号码</strong> - 自动匹配所有信息</li>
            <li><strong>一键生成脚本</strong> - 按照实际ZTE模板生成</li>
        </ol>
        
        <h4>🎯 自动处理功能：</h4>
        <ul>
            <li>✅ 自动匹配CHAVE对应的两个站点</li>
            <li>✅ 自动将设备名 NO 改为 ZT</li>
            <li>✅ 自动提取无线参数（带宽、功率、频率）</li>
            <li>✅ 自动设置调制方式为 QPSK</li>
            <li>✅ 自动计算网关地址</li>
            <li>✅ 按照实际ZTE脚本模板生成</li>
        </ul>
        
        <h4>📋 数据映射：</h4>
        <ul>
            <li><strong>Datasheet A列</strong>: CHAVE号码</li>
            <li><strong>Datasheet L/M列</strong>: 站点A/B名称</li>
            <li><strong>Datasheet N/O列</strong>: 设备名称 (NO→ZT)</li>
            <li><strong>Datasheet AN列</strong>: 带宽</li>
            <li><strong>Datasheet AS列</strong>: 发射功率</li>
            <li><strong>Datasheet DR/DS列</strong>: 收发频率</li>
        </ul>
        </div>
        """, unsafe_allow_html=True)
    
    # 显示生成的脚本
    if hasattr(st.session_state, 'current_script'):
        st.markdown("---")
        st.markdown(f'<div class="section-header">📜 生成的脚本 - {st.session_state.script_for}</div>', unsafe_allow_html=True)
        st.code(st.session_state.current_script, language='bash')
        
        # 下载链接
        filename = f"{st.session_state.script_for}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        st.markdown(create_download_link(st.session_state.current_script, filename, "📥 下载脚本"), unsafe_allow_html=True)

if __name__ == "__main__":
    main()
