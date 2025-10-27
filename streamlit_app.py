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
    .chave-input {
        font-size: 1.5rem;
        text-align: center;
        padding: 15px;
    }
</style>
""", unsafe_allow_html=True)

class DataProcessor:
    """数据处理类 - 负责CHAVE匹配和数据整合"""
    
    @staticmethod
    def parse_dcn_file(file):
        """解析DCN文件"""
        try:
            if file.name.endswith('.csv'):
                df = pd.read_csv(file)
            else:
                df = pd.read_excel(file)
            
            st.success(f"✅ DCN文件加载成功，共 {len(df)} 条记录")
            return df
        except Exception as e:
            st.error(f"❌ DCN文件解析失败: {e}")
            return None
    
    @staticmethod
    def parse_datasheet_file(file):
        """解析Datasheet文件"""
        try:
            if file.name.endswith('.csv'):
                df = pd.read_csv(file)
            else:
                df = pd.read_excel(file)
            
            st.success(f"✅ Datasheet加载成功，共 {len(df)} 条记录")
            return df
        except Exception as e:
            st.error(f"❌ Datasheet解析失败: {e}")
            return None
    
    @staticmethod
    def find_site_by_chave(dcn_data, chave_number):
        """根据CHAVE号码查找站点信息"""
        if dcn_data is None:
            return None
            
        # 尝试不同的列名匹配
        chave_columns = ['CHAVE', 'Chave', 'chave', '站点编号', '编号', 'ID']
        
        for col in chave_columns:
            if col in dcn_data.columns:
                matched_sites = dcn_data[dn_data[col] == chave_number]
                if len(matched_sites) > 0:
                    return matched_sites.iloc[0].to_dict()
        
        return None
    
    @staticmethod
    def find_device_config(datasheet_data, site_info):
        """根据站点信息查找设备配置"""
        if datasheet_data is None:
            return None
            
        # 尝试匹配设备型号或厂商
        if '设备型号' in site_info and '设备型号' in datasheet_data.columns:
            matched_devices = datasheet_data[datasheet_data['设备型号'] == site_info['设备型号']]
            if len(matched_devices) > 0:
                return matched_devices.iloc[0].to_dict()
        
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
        script = f"""
# 华为微波设备开站脚本
# 生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
# 站点名称: {config['site_name']}
# CHAVE号码: {config['chave_number']}

# 系统配置
system-view
sysname {config['site_name']}

# 接口配置
interface gigabitethernet 0/0/1
 description Connection_to_Router
 port link-type trunk
 port trunk allow-pass vlan {config['vlan_id']}
 undo shutdown

# 无线接口配置
interface radio 0/0/1
 description Radio_Link_to_{config['remote_site']}
 frequency {config['frequency']} MHz
 bandwidth {config['bandwidth']}
 modulation {config['modulation']}
 tx-power {config['tx_power']}
 adaptive-modulation enable
 undo shutdown

# VLAN配置
vlan {config['vlan_id']}
 description Management_VLAN

# 业务配置
interface vlanif {config['vlan_id']}
 ip address {config['ip_address']} {config['subnet_mask']}

# 路由配置
ip route-static 0.0.0.0 0.0.0.0 {config['gateway']}

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
        script = f"""
# 中兴微波设备开站脚本
# 生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
# 站点名称: {config['site_name']}
# CHAVE号码: {config['chave_number']}

# 进入配置模式
configure terminal

# 系统配置
hostname {config['site_name']}

# 以太网接口配置
interface gei-0/1
 description "Uplink_Interface"
 switchport mode trunk
 switchport trunk allowed vlan {config['vlan_id']}
 no shutdown

# 无线接口配置
interface radio-0/1
 description "Wireless_Link_to_{config['remote_site']}"
 frequency {config['frequency']}
 bandwidth {config['bandwidth']}
 modulation {config['modulation']}
 output-power {config['tx_power']}
 adaptive-modulation on
 no shutdown

# VLAN配置
vlan {config['vlan_id']}
 name "Management_VLAN"

# IP接口配置
interface vlan {config['vlan_id']}
 ip address {config['ip_address']} {config['subnet_mask']}

# 默认路由
ip route 0.0.0.0/0 {config['gateway']}

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
# 站点名称: {config['site_name']}
# CHAVE号码: {config['chave_number']}

# 基本配置步骤:
# 1. 系统命名: {config['site_name']}
# 2. 配置管理IP: {config['ip_address']}/{config['subnet_mask']}
# 3. 配置网关: {config['gateway']}
# 4. 配置无线参数:
#    - 频率: {config['frequency']} MHz
#    - 带宽: {config['bandwidth']}
#    - 调制方式: {config['modulation']}
#    - 发射功率: {config['tx_power']} dBm
# 5. 配置VLAN: {config['vlan_id']}
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
    st.markdown('<h3 style="text-align: center; color: #666;">输入CHAVE号码，一键生成开站脚本</h3>', unsafe_allow_html=True)
    
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
            st.success(f"✅ Datasheet: {len(st.session_state.datasheet_data)} 设备")
        else:
            st.warning("❌ 未加载Datasheet")
    
    # 主内容区 - CHAVE输入和脚本生成
    col1, col2 = st.columns([1, 2])
    
    with col1:
        st.markdown('<div class="section-header">🔑 输入CHAVE号码</div>', unsafe_allow_html=True)
        
        chave_number = st.text_input(
            "CHAVE号码",
            placeholder="请输入CHAVE号码...",
            key="chave_input"
        )
        
        if chave_number:
            # 查找匹配的站点信息
            site_info = None
            device_config = None
            
            if st.session_state.dcn_data is not None:
                site_info = processor.find_site_by_chave(st.session_state.dcn_data, chave_number)
            
            if site_info and st.session_state.datasheet_data is not None:
                device_config = processor.find_device_config(st.session_state.datasheet_data, site_info)
            
            # 显示匹配结果
            if site_info:
                st.success("✅ 找到匹配的站点信息")
                
                # 创建配置字典
                config = {
                    'chave_number': chave_number,
                    'site_name': site_info.get('站点名称', f'SITE_{chave_number}'),
                    'ip_address': site_info.get('IP地址', '192.168.100.10'),
                    'vlan_id': site_info.get('VLAN', 100),
                    'subnet_mask': '255.255.255.0',
                    'gateway': '192.168.100.1',
                    'frequency': device_config.get('频率', 15000) if device_config else 15000,
                    'bandwidth': device_config.get('带宽', '28MHz') if device_config else '28MHz',
                    'modulation': device_config.get('调制方式', '16QAM') if device_config else '16QAM',
                    'tx_power': device_config.get('发射功率', 15) if device_config else 15,
                    'vendor': device_config.get('厂商', '华为') if device_config else '华为',
                    'snmp_read': 'public',
                    'snmp_write': 'private',
                    'remote_site': site_info.get('对端站点', f'SITE_{chave_number}_PEER')
                }
                
                # 显示配置信息
                with st.expander("📋 站点配置信息", expanded=True):
                    st.json(config)
                
                # 生成脚本按钮
                if st.button("🚀 生成开站脚本", type="primary", use_container_width=True):
                    script = generator.generate_script(config)
                    
                    st.markdown('<div class="section-header">📜 生成的脚本</div>', unsafe_allow_html=True)
                    st.code(script, language='bash')
                    
                    filename = f"{config['vendor']}_{config['site_name']}_CHAVE{chave_number}.txt"
                    st.markdown(create_download_link(script, filename, "📥 下载脚本"), unsafe_allow_html=True)
                    
                    st.success("🎉 脚本生成完成！")
            
            elif st.session_state.dcn_data is None:
                st.error("❌ 请先上传DCN文件")
            else:
                st.error(f"❌ 未找到CHAVE号码 '{chave_number}' 对应的站点信息")
    
    with col2:
        st.markdown('<div class="section-header">📖 使用说明</div>', unsafe_allow_html=True)
        
        st.markdown("""
        <div class="config-box">
        <h4>🚀 快速开始：</h4>
        <ol>
            <li><strong>上传DCN文件</strong> - 包含站点基础信息（站点名称、IP、VLAN等）</li>
            <li><strong>上传Datasheet</strong> - 包含设备技术参数（频率、带宽、调制方式等）</li>
            <li><strong>输入CHAVE号码</strong> - 自动匹配站点和设备信息</li>
            <li><strong>一键生成脚本</strong> - 自动生成对应厂商的开站脚本</li>
        </ol>
        
        <h4>📋 文件格式要求：</h4>
        <ul>
            <li><strong>DCN文件</strong>：必须包含 CHAVE、站点名称、IP地址、VLAN 等列</li>
            <li><strong>Datasheet</strong>：包含设备型号、频率、带宽、调制方式等参数</li>
            <li>支持 Excel (.xlsx, .xls) 和 CSV 格式</li>
        </ul>
        
        <h4>🎯 优势：</h4>
        <ul>
            <li>✅ 只需输入CHAVE号码，无需手动配置</li>
            <li>✅ 自动匹配站点和设备信息</li>
            <li>✅ 减少人工错误，提高效率</li>
            <li>✅ 支持批量处理多个站点</li>
        </ul>
        </div>
        """, unsafe_allow_html=True)

if __name__ == "__main__":
    main()
