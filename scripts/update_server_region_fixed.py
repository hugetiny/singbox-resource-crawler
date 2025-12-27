#!/usr/bin/env python3
import base64
import concurrent.futures
import ipaddress
import json
import os
import re
import sqlite3
import sys
import time
import requests
from threading import Lock

# 导入通用配置
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from config import DATABASE_DB_PATH, API_KEYS, cache_lock, ip_cache

# 数据库路径别名
DB_PATH = DATABASE_DB_PATH

def update_server_region():
    """使用多个API并发获取IP地理位置信息更新server_region字段，统一格式为'国家代码-国家-城市'"""
    try:
        # 连接到SQLite数据库
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        # 获取所有需要更新的资源
        cursor.execute("SELECT id, url FROM resources")
        resources = cursor.fetchall()

        print(f"Found {len(resources)} resources to update")

        updated = 0
        skipped = 0

        for resource_id, url in resources:
            try:
                # 重置API状态
                api_results = {}

                # 从URL中提取IP地址
                ip = extract_ip_from_url(url)
                if not ip:
                    skipped += 1
                    print(
                        f"Skipped resource {resource_id}: Failed to extract IP from URL"
                    )
                    # 更新API状态为0
                    cursor.execute(
                        "UPDATE resources SET api_ipinfo = 0, api_ipapi_co = 0, api_ipgeolocation = 0, api_ipwho = 0 WHERE id = ?",
                        (resource_id,),
                    )
                else:
                    # 测试所有API，返回详细结果
                    geo_info, api_results = get_geo_info_comprehensive(ip)

                    # 更新API状态
                    ipinfo_status = 1 if api_results.get("ipinfo", False) else 0
                    ipapi_co_status = 1 if api_results.get("ipapi_co", False) else 0
                    ipgeolocation_status = (
                        1 if api_results.get("ipgeolocation", False) else 0
                    )
                    ipwho_status = 1 if api_results.get("ipwho", False) else 0

                    if geo_info:
                        # 更新数据库，包括server_region和API状态
                        cursor.execute(
                            "UPDATE resources SET server_region = ?, api_ipinfo = ?, api_ipapi_co = ?, api_ipgeolocation = ?, api_ipwho = ? WHERE id = ?",
                            (
                                geo_info,
                                ipinfo_status,
                                ipapi_co_status,
                                ipgeolocation_status,
                                ipwho_status,
                                resource_id,
                            ),
                        )

                        updated += 1
                        print(f"Updated resource {resource_id}: {ip} -> {geo_info}")
                        api_status = ", ".join(
                            [
                                f"{api}: Success" if result else f"{api}: Failed"
                                for api, result in api_results.items()
                            ]
                        )
                        print(f"  API Results: {api_status}")
                    else:
                        skipped += 1
                        print(f"Skipped resource {resource_id}: {ip} - All APIs failed")
                        # 更新API状态
                        cursor.execute(
                            "UPDATE resources SET api_ipinfo = ?, api_ipapi_co = ?, api_ipgeolocation = ?, api_ipwho = ? WHERE id = ?",
                            (
                                ipinfo_status,
                                ipapi_co_status,
                                ipgeolocation_status,
                                ipwho_status,
                                resource_id,
                            ),
                        )

            except Exception as e:
                skipped += 1
                print(f"Error processing resource {resource_id}: {e}")
                # 更新API状态为0
                cursor.execute(
                    "UPDATE resources SET api_ipinfo = 0, api_ipapi_co = 0, api_ipgeolocation = 0, api_ipwho = 0 WHERE id = ?",
                    (resource_id,),
                )

        # 提交更改
        conn.commit()

        # 关闭连接
        conn.close()

        print(f"\nUpdate completed:")
        print(f"- Total resources: {len(resources)}")
        print(f"- Updated resources: {updated}")
        print(f"- Skipped resources: {skipped}")

        return True

    except Exception as e:
        print(f"Error updating server_region: {e}")
        return False


def get_geo_info_comprehensive(ip):
    """测试所有API获取IP地理位置信息，返回统一格式'国家代码-国家-城市'和API结果详情"""
    # 检查缓存
    with cache_lock:
        if ip in ip_cache:
            # 返回缓存结果和空的API结果（因为缓存时没有记录API状态）
            return ip_cache[ip], {}

    # 按照优先级排序的API列表
    apis = [
        ("ipinfo", f"https://ipinfo.io/{ip}/json", API_KEYS["ipinfo"]),
        (
            "ipapi_co",
            f"http://ip-api.com/json/{ip}?fields=status,message,country,countryCode,region,regionName,city,query",
            None,
        ),
        (
            "ipgeolocation",
            f"https://api.ipgeolocation.io/ipgeo?apiKey={API_KEYS['ipgeolocation']}&ip={ip}",
            None,
        ),
        ("ipwho", f"https://ipwho.is/{ip}", None),
    ]

    # 测试所有API
    api_results = {}
    best_result = None

    for api_name, url, token in apis:
        try:
            # 请求当前API
            data = fetch_geo_info(api_name, url, token)
            api_results[api_name] = bool(data)

            if data:
                # 解析地理位置数据
                country_code, country, city = parse_geo_data(api_name, data)

                # 检查是否获取到有效信息
                if country_code and country:
                    # 构造结果
                    result = f"{country_code}-{country}-{city or 'Unknown'}"
                    # 如果还没有结果，或者当前结果更完整（有城市），则更新
                    if not best_result or (city and "Unknown" not in best_result):
                        best_result = result
        except Exception as e:
            api_results[api_name] = False
            print(f"Error with {api_name} API: {e}")

    # 缓存结果
    with cache_lock:
        ip_cache[ip] = best_result

    return best_result, api_results


def fetch_geo_info(api_name, url, token):
    """从API获取地理位置信息"""
    try:
        headers = {}
        if token:
            headers["Authorization"] = f"Bearer {token}"

        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"Error fetching from {api_name}: {e}")
        return None


def parse_geo_data(api_name, data):
    """解析不同API返回的地理位置数据，返回(国家代码, 国家, 城市)"""
    try:
        if api_name == "ipinfo":
            # 从ipinfo获取数据
            country_code = data.get("country", "")
            # 获取完整国家名称
            country = get_country_name(country_code)
            city = data.get("city", "")
        elif api_name == "ipapi_co":
            # 从ip-api.com获取数据
            if data.get("status") == "fail":
                return "", "", ""
            country_code = data.get("countryCode", "")
            country = data.get("country", "")
            city = data.get("city", "")
        elif api_name == "ipgeolocation":
            # 从ipgeolocation.io获取数据
            country_code = data.get("country_code2", "")
            country = data.get("country_name", "")
            city = data.get("city", "")
        elif api_name == "ipwho":
            # 从ipwho.is获取数据
            country_code = data.get("country_code", "")
            country = data.get("country", "")
            city = data.get("city", "")
        else:
            return "", "", ""

        return country_code, country, city
    except Exception as e:
        print(f"Error parsing geo data from {api_name}: {e}")
        return "", "", ""


def get_country_name(country_code):
    """根据国家代码获取完整国家名称"""
    country_map = {
        "US": "United States",
        "CN": "China",
        "GB": "United Kingdom",
        "DE": "Germany",
        "FR": "France",
        "JP": "Japan",
        "KR": "South Korea",
        "SG": "Singapore",
        "HK": "Hong Kong",
        "TW": "Taiwan",
        "CA": "Canada",
        "AU": "Australia",
        "RU": "Russia",
        "BR": "Brazil",
        "IN": "India",
        "IT": "Italy",
        "ES": "Spain",
        "NL": "Netherlands",
        "BE": "Belgium",
        "CH": "Switzerland",
        "AT": "Austria",
        "SE": "Sweden",
        "NO": "Norway",
        "DK": "Denmark",
        "FI": "Finland",
        "IE": "Ireland",
        "PT": "Portugal",
        "GR": "Greece",
        "CZ": "Czech Republic",
        "HU": "Hungary",
        "PL": "Poland",
        "RO": "Romania",
        "IL": "Israel",
        "AE": "United Arab Emirates",
        "SA": "Saudi Arabia",
        "TR": "Turkey",
        "ZA": "South Africa",
        "MX": "Mexico",
        "AR": "Argentina",
        "CL": "Chile",
        "TH": "Thailand",
        "MY": "Malaysia",
        "ID": "Indonesia",
        "PH": "Philippines",
        "VN": "Vietnam",
    }

    return country_map.get(country_code, country_code)


def extract_ip_from_url(url):
    """从URL中提取IP地址"""
    try:
        # 首先检查URL本身是否包含IP地址
        ip_pattern = r"\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b"
        ips = re.findall(ip_pattern, url)
        if ips:
            return ips[0]

        # 处理不同协议的URL
        if "://" in url:
            protocol, encoded = url.split("://", 1)

            # 处理base64编码的URL
            if protocol in ["vmess", "ss", "ssr"]:
                try:
                    # 移除可能的后缀（如vmess、trojan等）和多余字符
                    encoded_clean = (
                        encoded.split("vmess")[0].split("trojan")[0].split("|")[0]
                    )
                    # 处理base64填充问题
                    padding = "=" * ((4 - len(encoded_clean) % 4) % 4)
                    encoded_clean += padding

                    decoded = base64.b64decode(encoded_clean).decode("utf-8")

                    # 检查是否是JSON格式
                    if decoded.startswith("{") and decoded.endswith("}"):
                        # JSON格式配置
                        try:
                            config = json.loads(decoded)
                            # 从JSON中提取IP地址
                            if "add" in config and config["add"]:
                                ip = config["add"]
                                if re.match(ip_pattern, ip):
                                    return ip
                                return extract_ip_from_server(ip)
                            if "host" in config and config["host"]:
                                host = config["host"]
                                if re.match(ip_pattern, host):
                                    return host
                                return extract_ip_from_server(host)
                            if "addr" in config and config["addr"]:
                                addr = config["addr"]
                                if re.match(ip_pattern, addr):
                                    return addr
                                return extract_ip_from_server(addr)
                        except json.JSONDecodeError:
                            pass
                    elif ":" in decoded:
                        # SSR或传统SS格式
                        if protocol == "ssr":
                            # SSR格式: server:port:protocol:method:obfs:password_base64/?params
                            server = decoded.split(":")[0]
                            if re.match(ip_pattern, server):
                                return server
                            return extract_ip_from_server(server)
                        elif "@" in decoded:
                            # 传统SS格式: method:password@server:port
                            _, server_port = decoded.rsplit("@", 1)
                            server = server_port.split(":")[0]
                            if re.match(ip_pattern, server):
                                return server
                            return extract_ip_from_server(server)
                except Exception as e:
                    # 尝试从原始encoded字符串中直接提取IP
                    ip_in_encoded = re.findall(ip_pattern, encoded)
                    if ip_in_encoded:
                        return ip_in_encoded[0]
                    print(f"Error decoding {protocol} URL: {e}")
                    pass

            # 对于其他协议，使用正常处理
            url = encoded

        # 从URL的剩余部分提取IP
        if "/" in url:
            url = url.split("/")[0]
        if "@" in url:
            url = url.split("@")[1]
        if ":" in url:
            url = url.split(":")[0]

        # 最后检查是否是IP
        if re.match(ip_pattern, url):
            return url

        return None
    except Exception as e:
        print(f"Error extracting IP from URL: {e}")
        return None


def extract_ip_from_server(server):
    """从服务器地址中提取IP地址"""
    if not server:
        return None

    try:
        # 检查是否已经是IP
        ipaddress.ip_address(server)
        return server
    except ValueError:
        # 解析域名
        import socket

        try:
            return socket.gethostbyname(server)
        except Exception as e:
            print(f"Error resolving domain {server}: {e}")
            return None


if __name__ == "__main__":
    success = update_server_region()
    if success:
        print("Server region update completed successfully!")
    else:
        print("Failed to update server region!")
