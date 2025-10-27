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

class DCNParser:
    """DCN文件解析器 - 不使用openpyxl"""
    
    @staticmethod
    def parse_excel(file):
        """解析Excel格式的DCN文件 - 使用pandas内置引擎"""
        try:
            # 使用pandas自动选择引擎，不依赖openpyxl
            df = pd.read_excel(file)
            st.success(f"成功读取DCN文件，共 {len(df)} 条记录")
            return df
        except Exception as e:
            st.error(f"解析Excel文件失败: {e}")
            # 提供备用方案
            st.info("💡 提示：请尝试上传CSV格式文件，或检查Excel文件格式")
            return None
    
    @staticmethod
    def parse_csv(file):
        """解析CSV格式的DCN文件"""
        try:
            df = pd.read_csv(file)
            st.success(f"成功读取DCN文件，共 {len(df)} 条记录")
            return df
        except Exception as e:
            st.error(f"解析CSV文件失败: {e}")
            return None
    
    @staticmethod
    def validate_dcn_data(df):
        """验证DCN数据格式"""
        required_columns = ['站点名称', 'IP地址', 'VLAN']
        missing_columns = [col for col in required_columns if col not in df.columns]
        
        if missing_columns:
            st.error(f"DCN文件缺少必要列: {', '.join(missing_columns)}")
            return False
        
        return True

class DatasheetParser:
    """微波设备Datasheet解析器 - 不使用openpyxl"""
    
    @staticmethod
    def parse_datasheet(file):
        """解析设备Datasheet - 简化版本"""
        try:
            if file.name.endswith(('.xlsx', '.xls')):
                # 使用pandas读取Excel
                df = pd.read_excel(file)
                st.info(f"Datasheet包含 {len(df)} 行数据，列: {', '.join(df.columns.tolist()[:5])}...")
                return df
            else:
                # 文本文件
                content = file.getvalue().decode('utf-8')
                st.info("📄 文本格式Datasheet已上传，请在下方手动配置参数")
                return content
        except Exception as e:
            st.error(f"解析Datasheet失败: {e}")
            st.info("请手动在界面中配置参数")
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
        
        self.device_models = {
            "华为": ["RTN 900", "RTN 900A", "RTN 980", "ATN 910"],
            "中兴": ["ZXMP M7200", "ZXCTN 6500", "ZXCTN 9000"],
            "爱立信": ["MINI-LINK 6366", "MINI-LINK 6651", "MINI-LINK 6691"],
            "诺基亚": ["1830 PSS-4", "1830 PSS-8", "1830 PSS-16"]
        }
        
        self.modulation_modes = ["QPSK", "16QAM", "32QAM", "64QAM", "128QAM", "256QAM"]
        self.bandwidth_options = ["7MHz", "14MHz", "28MHz", "56MHz"]
    
    def generate_huawei_script(self, config):
        """生成华为设备脚本"""
        script = f"""
# 华为微波设备开站脚本
# 生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
# 站点名称: {config['site_name']}

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
    
    def generate_ericsson_script(self, config):
        """生成爱立信设备脚本"""
        script = f"""
# 爱立信微波设备开站脚本
# 生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
# 站点名称: {config['site_name']}

# 系统配置
set system name {config['site_name']}

# 以太网接口配置
set interface eth 1
set interface eth 1 vlan {config['vlan_id']}
set interface eth 1 state up

# 无线链路配置
set radio 1
set radio 1 frequency {config['frequency']}
set radio 1 bandwidth {config['bandwidth']}
set radio 1 modulation {config['modulation']}
set radio 1 tx-power {config['tx_power']}
set radio 1 adaptive on
set radio 1 remote-unit "{config['remote_site']}"
set radio 1 state up

# IP配置
set ip interface vlan{config['vlan_id']}
set ip interface vlan{config['vlan_id']} address {config['ip_address']}
set ip interface vlan{config['vlan_id']} mask {config['subnet_mask']}
set ip route add default gateway {config['gateway']}

# SNMP配置
set snmp community public {config['snmp_read']}
set snmp community private {config['snmp_write']}

# 保存配置
save configuration

# 状态检查
show radio 1
show interface eth 1
        """
        return script
    
    def generate_script(self, config):
        """根据配置生成脚本"""
        vendor = config['vendor']
        
        if vendor == "华为":
            return self.generate_huawei_script(config)
        elif vendor == "中兴":
            return self.generate_zte_script(config)
        elif vendor == "爱立信":
            return self.generate_ericsson_script(config)
        else:
            return self.generate_generic_script(config)
    
    def generate_generic_script(self, config):
        """生成通用脚本模板"""
        script = f"""
# 微波设备开站脚本 - {config['vendor']} {config['device_model']}
# 生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
# 站点名称: {config['site_name']}

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

# 请根据具体设备手册调整命令语法
        """
        return script

def create_download_link(content, filename, text):
    """创建下载链接"""
    b64 = base64.b64encode(content.encode()).decode()
    href = f'<a href="data:file/txt;base64,{b64}" download="{filename}">{text}</a>'
    return href

def main():
    """主应用"""
    st.markdown('<h1 class="main-header">📡 微波开站脚本生成工具</h1>', unsafe_allow_html=True)
    
    # 初始化生成器
    generator = MicrowaveScriptGenerator()
    dcn_parser = DCNParser()
    
    # 会话状态初始化
    if 'dcn_data' not in st.session_state:
        st.session_state.dcn_data = None
    if 'selected_sites' not in st.session_state:
        st.session_state.selected_sites = []
    
    # 侧边栏
    with st.sidebar:
        st.header("🔧 配置选项")
        
        vendor = st.selectbox(
            "选择设备厂商",
            options=list(generator.vendors.keys()),
            index=0
        )
        
        device_model = st.selectbox(
            "选择设备型号",
            options=generator.device_models[vendor],
            index=0
        )
        
        st.markdown("---")
        st.subheader("📊 数据源状态")
        
        if st.session_state.dcn_data is not None:
            st.success(f"✅ DCN文件已加载 ({len(st.session_state.dcn_data)} 站点)")
        else:
            st.warning("❌ 未加载DCN文件")
    
    # 文件上传区域
    st.markdown('<div class="section-header">📁 上传DCN文件</div>', unsafe_allow_html=True)
    st.markdown('<div class="upload-section">', unsafe_allow_html=True)
    
    col1, col2 = st.columns([1, 1])
    
    with col1:
        st.subheader("Excel格式")
        dcn_excel_file = st.file_uploader(
            "上传DCN文件 (Excel)",
            type=['xlsx', 'xls'],
            key="dcn_excel_uploader"
        )
        
        if dcn_excel_file is not None:
            dcn_data = dcn_parser.parse_excel(dcn_excel_file)
            if dcn_data is not None and dcn_parser.validate_dcn_data(dcn_data):
                st.session_state.dcn_data = dcn_data
    
    with col2:
        st.subheader("CSV格式")
        dcn_csv_file = st.file_uploader(
            "上传DCN文件 (CSV)",
            type=['csv'],
            key="dcn_csv_uploader"
        )
        
        if dcn_csv_file is not None:
            dcn_data = dcn_parser.parse_csv(dcn_csv_file)
            if dcn_data is not None and dcn_parser.validate_dcn_data(dcn_data):
                st.session_state.dcn_data = dcn_data
    
    st.markdown('</div>', unsafe_allow_html=True)
    
    # 手动配置模式
    if st.session_state.dcn_data is None:
        st.markdown("""
        <div class="warning-box">
            <h3>📋 使用说明</h3>
            <p>请先上传DCN文件或使用手动配置模式。DCN文件应包含以下列：</p>
            <ul>
                <li><strong>站点名称</strong>: 站点的唯一标识</li>
                <li><strong>IP地址</strong>: 设备管理IP地址</li>
                <li><strong>VLAN</strong>: 管理VLAN ID</li>
            </ul>
        </div>
        """, unsafe_allow_html=True)
        
        # 手动配置
        st.markdown('<div class="section-header">🔧 手动配置模式</div>', unsafe_allow_html=True)
        
        col3, col4 = st.columns(2)
        
        with col3:
            site_name = st.text_input("站点名称", value="MW_SITE_001")
            ip_address = st.text_input("IP地址", value="192.168.100.10")
            vlan_id = st.number_input("VLAN ID", min_value=1, max_value=4094, value=100)
        
        with col4:
            subnet_mask = st.text_input("子网掩码", value="255.255.255.0")
            gateway = st.text_input("网关地址", value="192.168.100.1")
            frequency = st.number_input("频率 (MHz)", min_value=1000, max_value=40000, value=15000)
        
        bandwidth = st.selectbox("带宽", options=generator.bandwidth_options, index=2)
        modulation = st.selectbox("调制方式", options=generator.modulation_modes, index=1)
        tx_power = st.slider("发射功率 (dBm)", min_value=-10, max_value=30, value=15)
        
        if st.button("生成脚本", type="primary", key="manual_generate"):
            config = {
                'vendor': vendor,
                'device_model': device_model,
                'site_name': site_name,
                'remote_site': f"{site_name}_PEER",
                'vlan_id': vlan_id,
                'ip_address': ip_address,
                'subnet_mask': subnet_mask,
                'gateway': gateway,
                'frequency': frequency,
                'bandwidth': bandwidth,
                'modulation': modulation,
                'tx_power': tx_power,
                'snmp_read': 'public',
                'snmp_write': 'private'
            }
            
            script = generator.generate_script(config)
            st.markdown('<div class="section-header">📜 生成的脚本</div>', unsafe_allow_html=True)
            st.code(script, language='bash')
            
            filename = f"{vendor}_{site_name}_脚本_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
            st.markdown(create_download_link(script, filename, "📥 下载脚本"), unsafe_allow_html=True)
    
    else:
        # DCN文件已加载的模式
        st.markdown('<div class="section-header">🏢 站点选择与配置</div>', unsafe_allow_html=True)
        
        site_options = st.session_state.dcn_data['站点名称'].tolist()
        selected_sites = st.multiselect(
            "选择要生成脚本的站点",
            options=site_options,
            default=st.session_state.selected_sites
        )
        
        if selected_sites:
            for site_name in selected_sites:
                with st.expander(f"配置站点: {site_name}"):
                    site_data = st.session_state.dcn_data[
                        st.session_state.dcn_data['站点名称'] == site_name
                    ].iloc[0]
                    
                    col5, col6 = st.columns(2)
                    
                    with col5:
                        ip_address = st.text_input("IP地址", value=str(site_data.get('IP地址', '192.168.100.10')), key=f"ip_{site_name}")
                        vlan_id = st.number_input("VLAN ID", value=int(site_data.get('VLAN', 100)), key=f"vlan_{site_name}")
                        subnet_mask = st.text_input("子网掩码", value="255.255.255.0", key=f"mask_{site_name}")
                    
                    with col6:
                        gateway = st.text_input("网关地址", value="192.168.100.1", key=f"gateway_{site_name}")
                        frequency = st.number_input("频率 (MHz)", value=15000, key=f"freq_{site_name}")
                    
                    bandwidth = st.selectbox("带宽", options=generator.bandwidth_options, index=2, key=f"bw_{site_name}")
                    modulation = st.selectbox("调制方式", options=generator.modulation_modes, index=1, key=f"mod_{site_name}")
                    
                    if st.button(f"生成 {site_name} 脚本", key=f"btn_{site_name}"):
                        config = {
                            'vendor': vendor,
                            'device_model': device_model,
                            'site_name': site_name,
                            'remote_site': f"{site_name}_PEER",
                            'vlan_id': vlan_id,
                            'ip_address': ip_address,
                            'subnet_mask': subnet_mask,
                            'gateway': gateway,
                            'frequency': frequency,
                            'bandwidth': bandwidth,
                            'modulation': modulation,
                            'tx_power': 15,
                            'snmp_read': 'public',
                            'snmp_write': 'private'
                        }
                        
                        script = generator.generate_script(config)
                        st.code(script, language='bash')
                        
                        filename = f"{vendor}_{site_name}_脚本.txt"
                        st.markdown(create_download_link(script, filename, f"📥 下载 {site_name} 脚本"), unsafe_allow_html=True)

if __name__ == "__main__":
    main()
