# -*- coding: utf-8 -*-
import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime
import base64
import io
import json
import re

# 页面配置
st.set_page_config(
    page_title="微波开站脚本生成器",
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
    """数据处理类 - 专门针对巴西DCN文件格式"""
    
    @staticmethod
    def parse_dcn_file(file):
        """解析DCN文件 - 专门处理巴西格式"""
        try:
            if file.name.endswith('.csv'):
                df = pd.read_csv(file, encoding='utf-8')
                st.success(f"✅ DCN文件加载成功，共 {len(df)} 条记录")
                return df
            else:
                # Excel文件，直接读取 PROJETO LÓGICO sheet
                excel_file = pd.ExcelFile(file)
                sheet_names = excel_file.sheet_names
                
                st.info(f"📑 检测到 {len(sheet_names)} 个sheet: {', '.join(sheet_names)}")
                
                # 自动查找 PROJETO LÓGICO sheet
                target_sheet = None
                for sheet in sheet_names:
                    if 'PROJETO LÓGICO' in sheet.upper() and 'AUTOMÁTICO' not in sheet.upper():
                        target_sheet = sheet
                        break
                
                if target_sheet is None:
                    st.warning("⚠️ 未找到 'PROJETO LÓGICO' sheet，请手动选择")
                    target_sheet = st.selectbox(
                        "请选择包含站点信息的sheet",
                        options=sheet_names,
                        index=0
                    )
                else:
                    st.success(f"🎯 自动选择: {target_sheet}")
                
                # 读取选中的sheet
                df = pd.read_excel(file, sheet_name=target_sheet)
                
                # 清理数据 - 移除空行和标题行
                df = df.dropna(how='all')  # 移除全空行
                
                # 查找数据开始的行（跳过表头）
                data_start_row = 0
                for idx, row in df.iterrows():
                    if 'End. IP' in str(row.values) or '10.211.' in str(row.values):
                        data_start_row = idx
                        break
                
                if data_start_row > 0:
                    df = df.iloc[data_start_row:]
                    df.columns = df.iloc[0]  # 第一行作为列名
                    df = df[1:]  # 移除原来的标题行
                    df = df.reset_index(drop=True)
                
                st.success(f"✅ 从 '{target_sheet}' 加载成功，共 {len(df)} 条记录")
                
                # 标准化列名
                column_mapping = {
                    'End. IP': 'IP地址',
                    'Subnet': '子网掩码', 
                    'Obs': '站点名称',
                    'Vlan': 'VLAN'
                }
                
                df = df.rename(columns=column_mapping)
                
                # 显示处理后的数据
                st.info(f"📋 处理后的列名: {', '.join(df.columns.tolist())}")
                st.dataframe(df.head())
                
                return df
                
        except Exception as e:
            st.error(f"❌ DCN文件解析失败: {e}")
            return None
    
    @staticmethod
    def parse_datasheet_file(file):
        """解析Datasheet文件"""
        try:
            if file.name.endswith('.csv'):
                df = pd.read_csv(file, encoding='utf-8')
            else:
                df = pd.read_excel(file)
            
            st.success(f"✅ Datasheet加载成功，共 {len(df)} 条记录")
            st.dataframe(df.head())
            return df
        except Exception as e:
            st.error(f"❌ Datasheet解析失败: {e}")
            return None
    
    @staticmethod
    def find_site_by_chave(dcn_data, chave_number):
        """根据CHAVE号码查找站点信息 - 针对巴西DCN格式"""
        if dcn_data is None:
            return None
            
        st.info(f"🔍 正在查找CHAVE: {chave_number}")
        
        # 显示数据预览
        st.write("📊 数据预览:")
        st.dataframe(dcn_data.head())
        
        # 在巴西DCN中，CHAVE可能隐藏在站点名称中
        # 比如站点名称 "MWE-MG-4G-CORD10-N1-ZT" 中的 "CORD10" 可能是CHAVE
        site_name_columns = ['站点名称', 'Obs', 'SITE ID', 'Site Id']
        
        for col in site_name_columns:
            if col in dcn_data.columns:
                # 在站点名称中搜索CHAVE号码
                dcn_data[col] = dcn_data[col].astype(str)
                matched_sites = dcn_data[dcn_data[col].str.contains(str(chave_number), na=False)]
                
                if len(matched_sites) > 0:
                    st.success(f"🎯 在列 '{col}' 中找到 {len(matched_sites)} 个匹配站点")
                    site_info = matched_sites.iloc[0].to_dict()
                    
                    # 从站点名称中提取更友好的名称
                    site_name = site_info.get('站点名称', '')
                    if 'MWE-' in site_name:
                        # 提取站点标识，如从 "MWE-MG-4G-CORD10-N1-ZT" 提取 "CORD10"
                        parts = site_name.split('-')
                        if len(parts) >= 4:
                            friendly_name = parts[3]  # 取CORD10部分
                            site_info['站点名称'] = friendly_name
                    
                    return site_info
        
        # 如果没有找到，显示所有可能的站点名称
        st.error(f"❌ 未找到包含 '{chave_number}' 的站点")
        st.info("📋 文件中存在的站点名称示例:")
        for col in site_name_columns:
            if col in dcn_data.columns:
                sample_values = dcn_data[col].astype(str).unique()[:5]
                st.write(f"- {col}: {', '.join(sample_values)}")
        
        return None

class MicrowaveScriptGenerator:
    """微波开站脚本生成器"""
    
    def __init__(self):
        self.vendors = {
            "华为": "Huawei",
            "中兴": "ZTE", 
            "爱立信": "Ericsson",
            "诺基亚": "Nokia"
        }
    
    def generate_huawei_script(self, config):
        """生成华为设备脚本"""
        # 从子网掩码中提取网关（通常是第一个可用IP）
        subnet = config.get('子网掩码', '10.211.51.200/29')
        network_ip = subnet.split('/')[0] if '/' in subnet else '10.211.51.200'
        ip_parts = network_ip.split('.')
        gateway = f"{ip_parts[0]}.{ip_parts[1]}.{ip_parts[2]}.{int(ip_parts[3]) + 1}"
        
        script = f"""
# 华为微波设备开站脚本
# 生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
# 站点名称: {config['站点名称']}
# CHAVE号码: {config['chave_number']}

# 系统配置
system-view
sysname {config['站点名称']}

# 接口配置
interface gigabitethernet 0/0/1
 description Connection_to_Router
 port link-type trunk
 port trunk allow-pass vlan {config['VLAN']}
 undo shutdown

# 无线接口配置
interface radio 0/0/1
 description Radio_Link_to_PEER
 frequency {config['frequency']} MHz
 bandwidth {config['bandwidth']}
 modulation {config['modulation']}
 tx-power {config['tx_power']}
 adaptive-modulation enable
 undo shutdown

# VLAN配置
vlan {config['VLAN']}
 description Management_VLAN

# 业务配置
interface vlanif {config['VLAN']}
 ip address {config['IP地址']} 255.255.255.248

# 路由配置
ip route-static 0.0.0.0 0.0.0.0 {gateway}

# 管理配置
snmp-agent
snmp-agent community read {config['snmp_read']}
snmp-agent community write {config['snmp_write']}

# 保存配置
save
y

# 开站完成
display radio 0/0/1
display interface gigabitethernet 0/0/1
        """
        return script
    
    def generate_zte_script(self, config):
        """生成中兴设备脚本"""
        subnet = config.get('子网掩码', '10.211.51.200/29')
        network_ip = subnet.split('/')[0] if '/' in subnet else '10.211.51.200'
        ip_parts = network_ip.split('.')
        gateway = f"{ip_parts[0]}.{ip_parts[1]}.{ip_parts[2]}.{int(ip_parts[3]) + 1}"
        
        script = f"""
# 中兴微波设备开站脚本
# 生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
# 站点名称: {config['站点名称']}
# CHAVE号码: {config['chave_number']}

# 进入配置模式
configure terminal

# 系统配置
hostname {config['站点名称']}

# 以太网接口配置
interface gei-0/1
 description "Uplink_Interface"
 switchport mode trunk
 switchport trunk allowed vlan {config['VLAN']}
 no shutdown

# 无线接口配置
interface radio-0/1
 description "Wireless_Link_to_PEER"
 frequency {config['frequency']}
 bandwidth {config['bandwidth']}
 modulation {config['modulation']}
 output-power {config['tx_power']}
 adaptive-modulation on
 no shutdown

# VLAN配置
vlan {config['VLAN']}
 name "Management_VLAN"

# IP接口配置
interface vlan {config['VLAN']}
 ip address {config['IP地址']} 255.255.255.248

# 默认路由
ip route 0.0.0.0/0 {gateway}

# SNMP配置
snmp-server community {config['snmp_read']} ro
snmp-server community {config['snmp_write']} rw

# 保存配置
write memory

# 验证配置
show interface radio-0/1
show interface gei-0/1
        """
        return script
    
    def generate_script(self, config):
        """根据配置生成脚本"""
        vendor = config.get('vendor', '华为')
        
        if vendor == "华为":
            return self.generate_huawei_script(config)
        elif vendor == "中兴":
            return self.generate_zte_script(config)
        else:
            return self.generate_generic_script(config)
    
    def generate_generic_script(self, config):
        """生成通用脚本模板"""
        script = f"""
# 微波设备开站脚本
# 生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
# 站点名称: {config['站点名称']}
# CHAVE号码: {config['chave_number']}

# 基本配置步骤:
# 1. 系统命名: {config['站点名称']}
# 2. 配置管理IP: {config['IP地址']}/29
# 3. 配置网关: {config['IP地址'].rsplit('.', 1)[0]}.1
# 4. 配置无线参数:
#    - 频率: {config['frequency']} MHz
#    - 带宽: {config['bandwidth']}
#    - 调制方式: {config['modulation']}
#    - 发射功率: {config['tx_power']} dBm
# 5. 配置VLAN: {config['VLAN']}
# 6. 配置SNMP:
#    - 只读团体字: {config['snmp_read']}
#    - 读写团体字: {config['snmp_write']}
# 7. 保存配置
        """
        return script

def create_download_link(content, filename, text):
    """创建下载链接"""
    b64 = base64.b64encode(content.encode()).decode()
    href = f'<a href="data:file/txt;base64,{b64}" download="{filename}">{text}</a>'
    return href

def main():
    """主应用"""
    st.markdown('<h1 class="main-header">📡 微波开站脚本生成器</h1>', unsafe_allow_html=True)
    st.markdown('<h3 style="text-align: center; color: #666;">巴西DCN格式 - 输入CHAVE号码，一键生成开站脚本</h3>', unsafe_allow_html=True)
    
    # 初始化处理器和生成器
    processor = DataProcessor()
    generator = MicrowaveScriptGenerator()
    
    # 会话状态初始化
    if 'dcn_data' not in st.session_state:
        st.session_state.dcn_data = None
    if 'datasheet_data' not in st.session_state:
        st.session_state.datasheet_data = None
    
    # 侧边栏 - 文件上传
    with st.sidebar:
        st.header("📁 文件上传")
        
        # DCN文件上传
        dcn_file = st.file_uploader("上传DCN文件 (巴西格式)", type=['xlsx', 'xls', 'csv'], key="dcn_uploader")
        if dcn_file is not None:
            st.session_state.dcn_data = processor.parse_dcn_file(dcn_file)
        
        # Datasheet文件上传
        datasheet_file = st.file_uploader("上传Datasheet", type=['xlsx', 'xls', 'csv'], key="datasheet_uploader")
        if datasheet_file is not None:
            st.session_state.datasheet_data = processor.parse_datasheet_file(datasheet_file)
        
        st.markdown("---")
        st.header("📊 数据状态")
        if st.session_state.dcn_data is not None:
            st.success(f"✅ DCN: {len(st.session_state.dcn_data)} 站点")
        else:
            st.warning("❌ 未加载DCN文件")
            
        if st.session_state.datasheet_data is not None:
            st.success(f"✅ Datasheet: {len(st.session_state.datasheet_data)} 设备")
        else:
            st.warning("❌ 未加载Datasheet")
    
    # 主内容区 - CHAVE输入和脚本生成
    col1, col2 = st.columns([1, 2])
    
    with col1:
        st.markdown('<div class="section-header">🔑 输入CHAVE号码</div>', unsafe_allow_html=True)
        
        st.info("💡 在巴西DCN中，CHAVE通常是站点名称的一部分，如 'CORD10'")
        
        chave_number = st.text_input(
            "CHAVE号码",
            placeholder="例如: CORD10, CODV29...",
            key="chave_input"
        )
        
        if chave_number:
            # 查找匹配的站点信息
            site_info = None
            
            if st.session_state.dcn_data is not None:
                site_info = processor.find_site_by_chave(st.session_state.dcn_data, chave_number)
            
            # 显示匹配结果
            if site_info:
                st.success("✅ 找到匹配的站点信息")
                
                # 创建配置字典
                config = {
                    'chave_number': chave_number,
                    '站点名称': site_info.get('站点名称', f'SITE_{chave_number}'),
                    'IP地址': site_info.get('IP地址', '10.211.51.202'),
                    'VLAN': site_info.get('VLAN', 2929),
                    '子网掩码': site_info.get('子网掩码', '10.211.51.200/29'),
                    'frequency': 15000,
                    'bandwidth': '28MHz',
                    'modulation': '16QAM',
                    'tx_power': 15,
                    'vendor': '中兴',  # 根据DCN文件，默认中兴设备
                    'snmp_read': 'public',
                    'snmp_write': 'private'
                }
                
                # 显示配置信息
                with st.expander("📋 站点配置信息", expanded=True):
                    st.json(config)
                
                # 设备厂商选择
                vendor = st.selectbox("设备厂商", options=list(generator.vendors.keys()), index=1)  # 默认选中兴
                config['vendor'] = vendor
                
                # 生成脚本按钮
                if st.button("🚀 生成开站脚本", type="primary", use_container_width=True):
                    script = generator.generate_script(config)
                    
                    st.markdown('<div class="section-header">📜 生成的脚本</div>', unsafe_allow_html=True)
                    st.code(script, language='bash')
                    
                    filename = f"{config['vendor']}_{config['站点名称']}_CHAVE{chave_number}.txt"
                    st.markdown(create_download_link(script, filename, "📥 下载脚本"), unsafe_allow_html=True)
                    
                    st.success("🎉 脚本生成完成！")
            
            elif st.session_state.dcn_data is None:
                st.error("❌ 请先上传DCN文件")
    
    with col2:
        st.markdown('<div class="section-header">📖 巴西DCN使用说明</div>', unsafe_allow_html=True)
        
        st.markdown("""
        <div class="config-box">
        <h4>🚀 针对巴西DCN格式优化：</h4>
        <ol>
            <li><strong>上传巴西DCN文件</strong> - 自动识别 'PROJETO LÓGICO' sheet</li>
            <li><strong>输入CHAVE号码</strong> - 如 CORD10, CODV29 等（在站点名称中搜索）</li>
            <li><strong>自动匹配</strong> - 从DCN中提取IP、VLAN、站点名称</li>
            <li><strong>一键生成脚本</strong> - 支持华为、中兴等设备</li>
        </ol>
        
        <h4>📋 巴西DCN文件结构：</h4>
        <ul>
            <li><strong>PROJETO LÓGICO sheet</strong>：包含主要站点信息</li>
            <li><strong>End. IP</strong>：站点IP地址 (如 10.211.51.202)</li>
            <li><strong>Subnet</strong>：子网掩码 (如 10.211.51.200/29)</li>
            <li><strong>Obs</strong>：站点名称 (如 MWE-MG-4G-CORD10-N1-ZT)</li>
            <li><strong>Vlan</strong>：VLAN ID (如 2929)</li>
        </ul>
        
        <h4>🎯 CHAVE号码示例：</h4>
        <ul>
            <li>从 "MWE-MG-4G-<strong>CORD10</strong>-N1-ZT" 中提取 <strong>CORD10</strong></li>
            <li>从 "MWE-MG-<strong>CODV29</strong>-N1-ZT" 中提取 <strong>CODV29</strong></li>
        </ul>
        </div>
        """, unsafe_allow_html=True)

if __name__ == "__main__":
    main()
