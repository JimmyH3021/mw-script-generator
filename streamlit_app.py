@staticmethod
def find_site_config(dcn_data, datasheet_data, chave_number):
    """根据CHAVE号码查找完整的站点配置"""
    if dcn_data is None or datasheet_data is None:
        return None
    
    st.info(f"🔍 正在查找CHAVE: {chave_number}")
    
    # 显示Datasheet的所有列名用于调试
    st.info(f"📋 Datasheet所有列名: {list(datasheet_data.columns)}")
    
    # 1. 在Datasheet中查找CHAVE
    chave_match = None
    
    # 增强列名匹配 - 处理大小写和空格问题
    chave_columns = [
        'Chave', 'CHAVE', 'chave', 'Chave ', 'CHAVE ', 'chave ',  # 带空格的变体
        '站点编号', '编号', 'ID', 'Codigo', 'Código'
    ]
    
    chave_col = None
    for col in chave_columns:
        # 精确匹配
        if col in datasheet_data.columns:
            chave_col = col
            break
        # 忽略大小写和空格的匹配
        for actual_col in datasheet_data.columns:
            if col.strip().lower() == actual_col.strip().lower():
                chave_col = actual_col
                break
        if chave_col:
            break
    
    if chave_col is None:
        st.error("❌ 在Datasheet中未找到CHAVE列")
        st.info(f"📋 可用的列: {', '.join(datasheet_data.columns.tolist())}")
        return None
    
    st.success(f"✅ 找到CHAVE列: '{chave_col}'")
    
    # 清理CHAVE列数据
    datasheet_data[chave_col] = datasheet_data[chave_col].astype(str).str.strip()
    chave_match = datasheet_data[datasheet_data[chave_col] == str(chave_number).strip()]
    
    if len(chave_match) == 0:
        st.error(f"❌ 在Datasheet中未找到CHAVE: {chave_number}")
        # 显示前几个CHAVE值帮助调试
        sample_values = datasheet_data[chave_col].unique()[:10]
        st.info(f"📋 文件中存在的CHAVE值示例: {', '.join(map(str, sample_values))}")
        return None
    
    # 其余代码保持不变...
    datasheet_info = chave_match.iloc[0]
    st.success(f"✅ 在Datasheet中找到CHAVE配置")
    
    # 2. 提取站点名称（L/M列）- 同样增强匹配
    site_a_name = None
    site_b_name = None
    
    # 增强列名匹配
    site_columns = ['L', 'M', '站点A', '站点B', 'Site A', 'Site B']
    for col in site_columns:
        if col in datasheet_info:
            if site_a_name is None:
                site_a_name = str(datasheet_info[col]).strip()
            else:
                site_b_name = str(datasheet_info[col]).strip()
                break
    
    if not site_a_name or not site_b_name:
        st.error("❌ 无法找到站点名称信息")
        st.info("💡 请检查L/M列是否存在")
        return None
    
    st.info(f"📡 关联站点: {site_a_name} ↔ {site_b_name}")
    
    # 3. 在DCN中查找对应的站点信息
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
        # 显示DCN中的站点名称示例
        if '站点名称' in dcn_data.columns:
            sample_sites = dcn_data['站点名称'].astype(str).str.strip().unique()[:10]
            st.info(f"📋 DCN中站点名称示例: {', '.join(sample_sites)}")
        return None
    
    # 4. 提取设备配置（N/O列）- 增强匹配
    device_a = None
    device_b = None
    
    device_columns = ['N', 'O', '设备A', '设备B', 'Device A', 'Device B']
    for col in device_columns:
        if col in datasheet_info:
            if device_a is None:
                device_a = str(datasheet_info[col]).strip()
            else:
                device_b = str(datasheet_info[col]).strip()
                break
    
    # 如果没找到，使用默认值
    if not device_a:
        device_a = f"设备A_{chave_number}"
    if not device_b:
        device_b = f"设备B_{chave_number}"
    
    # 设备名称处理：将NO改为ZT
    device_a = device_a.replace('NO', 'ZT')
    device_b = device_b.replace('NO', 'ZT')
    
    # 5. 提取无线参数 - 增强匹配
    bandwidth_columns = ['AN', '带宽', 'Bandwidth']
    tx_power_columns = ['AS', '发射功率', 'TX Power']
    tx_freq_columns = ['DR', '发射频率', 'TX Frequency']
    rx_freq_columns = ['DS', '接收频率', 'RX Frequency']
    
    bandwidth = 112000
    tx_power = 220
    tx_freq = 14977000
    rx_freq = 14577000
    
    # 查找带宽
    for col in bandwidth_columns:
        if col in datasheet_info:
            bandwidth = datasheet_info[col]
            break
    
    # 查找发射功率
    for col in tx_power_columns:
        if col in datasheet_info:
            tx_power = datasheet_info[col]
            break
    
    # 查找发射频率
    for col in tx_freq_columns:
        if col in datasheet_info:
            tx_freq = datasheet_info[col]
            break
    
    # 查找接收频率
    for col in rx_freq_columns:
        if col in datasheet_info:
            rx_freq = datasheet_info[col]
            break
    
    st.info(f"📡 无线参数: 带宽={bandwidth}, 功率={tx_power}, 发射={tx_freq}, 接收={rx_freq}")
    
    # 返回完整配置
    config = {
        'chave_number': chave_number,
        'site_a': {
            'name': site_a_name,
            'device': device_a,
            'ip': site_a_info.get('IP地址') if site_a_info else None,
            'vlan': site_a_info.get('VLAN') if site_a_info else 2929,
            'subnet': site_a_info.get('子网掩码') if site_a_info else '10.211.51.200/29',
        },
        'site_b': {
            'name': site_b_name,
            'device': device_b,
            'ip': site_b_info.get('IP地址') if site_b_info else None,
            'vlan': site_b_info.get('VLAN') if site_b_info else 2929,
            'subnet': site_b_info.get('子网掩码') if site_b_info else '10.211.51.200/29',
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
