#!/usr/bin/env python3
import json
import os
import socket
import sqlite3
from datetime import datetime

import requests

# 配置
DB_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "data.db",
)

# List of free IP geolocation APIs
GEOIP_APIS = [
    "https://ipapi.co/{}/json/",
    "https://ipinfo.io/{}/json",
    "https://api.ipgeolocation.io/ipgeo?apiKey=free&ip={}",
    "https://freegeoip.app/json/{}",
    "https://ipwho.is/{}",
]

# 缓存文件放到tmp目录
CACHE_FILE = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "tmp",
    "ip_geo_cache.json",
)


class IPGeoResolver:
    def __init__(self):
        self.cache = self._load_cache()
        self.conn = sqlite3.connect(DB_PATH)
        self.cursor = self.conn.cursor()
        self._ensure_db_structure()

    def _load_cache(self):
        """Load IP geolocation cache"""
        if os.path.exists(CACHE_FILE):
            try:
                with open(CACHE_FILE, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                print(f"Failed to load cache: {e}")
        return {}

    def _save_cache(self):
        """Save IP geolocation cache"""
        try:
            with open(CACHE_FILE, "w", encoding="utf-8") as f:
                json.dump(self.cache, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"Failed to save cache: {e}")

    def _ensure_db_structure(self):
        """Ensure database structure is correct"""
        # Add server_region column to resources table if not exists
        self.cursor.execute("PRAGMA table_info(resources)")
        columns = [column[1] for column in self.cursor.fetchall()]
        if "server_region" not in columns:
            print("Adding server_region column to resources table...")
            self.cursor.execute("ALTER TABLE resources ADD COLUMN server_region TEXT")
            self.conn.commit()

    def get_ip_from_url(self, url):
        """Extract IP address from URL, including base64 encoded URLs"""
        try:
            # Handle different protocols
            if "://" in url:
                protocol, encoded = url.split("://", 1)

                # Handle base64 encoded URLs (vmess, ss, etc.)
                if protocol in ["vmess", "ss", "ssr"]:
                    try:
                        # Decode base64
                        import base64

                        if protocol == "ssr":
                            # SSR has a different format
                            decoded = base64.b64decode(encoded).decode("utf-8")
                            # SSR format: server:port:protocol:method:obfs:password_base64/?params
                            if ":" in decoded:
                                server = decoded.split(":")[0]
                                return self._get_ip_from_server(server)
                        elif protocol == "ss":
                            # SS format: method:password@server:port
                            if "@" in encoded:
                                _, server_port = encoded.rsplit("@", 1)
                                server = server_port.split(":")[0]
                                return self._get_ip_from_server(server)
                        elif protocol == "vmess":
                            # VMess is JSON encoded
                            decoded = base64.b64decode(encoded).decode("utf-8")
                            import json

                            vmess_config = json.loads(decoded)
                            if "add" in vmess_config:
                                server = vmess_config["add"]
                                return self._get_ip_from_server(server)
                            elif "aid" in vmess_config:
                                # Old VMess format
                                return self._get_ip_from_server(
                                    vmess_config.get("add", "")
                                )
                    except Exception as e:
                        print(f"Failed to decode {protocol} URL: {e}")
                        return None

                # For other protocols, use normal processing
                url = encoded

            # Simple processing to extract domain or IP from regular URLs
            if "/" in url:
                url = url.split("/")[0]
            if "@" in url:
                url = url.split("@")[1]
            if ":" in url:
                url = url.split(":")[0]

            return self._get_ip_from_server(url)
        except Exception as e:
            print(f"Failed to extract IP from {url}: {e}")
            return None

    def _get_ip_from_server(self, server):
        """Get IP from server address (domain or IP)"""
        if not server:
            return None

        try:
            # Check if it's already an IP
            socket.inet_aton(server)
            return server
        except socket.error:
            # Resolve domain name
            return socket.gethostbyname(server)

    def get_geo_info(self, ip):
        """Get IP geolocation information using multiple free APIs"""
        if ip in self.cache:
            return self.cache[ip]

        print(f"Querying IP geolocation: {ip}")

        # Try each API in list
        for api_url in GEOIP_APIS:
            try:
                response = requests.get(api_url.format(ip), timeout=5)
                response.raise_for_status()
                data = response.json()

                # Parse response based on API
                country = "Unknown"
                region = "Unknown"
                city = "Unknown"

                if "country_name" in data:  # ipapi.co
                    country = data["country_name"] or "Unknown"
                    region = data["region"] or "Unknown"
                    city = data["city"] or "Unknown"
                elif "country" in data:  # ipinfo.io, ipwho.is
                    if isinstance(data["country"], dict):  # ipwho.is
                        country = data["country"].get("name", "Unknown")
                        region = (
                            data["region"].get("name", "Unknown")
                            if "region" in data and isinstance(data["region"], dict)
                            else "Unknown"
                        )
                        city = data["city"] or "Unknown"
                    else:  # ipinfo.io
                        country = data["country"] or "Unknown"
                        region = data.get("region", "Unknown")
                        city = data.get("city", "Unknown")
                elif "country_name" in data:  # freegeoip.app
                    country = data["country_name"] or "Unknown"
                    region = data["region_name"] or "Unknown"
                    city = data["city"] or "Unknown"
                elif "country_name" in data:  # api.ipgeolocation.io
                    country = data["country_name"] or "Unknown"
                    region = data["state_prov"] or "Unknown"
                    city = data["city"] or "Unknown"

                # Only return if we got at least country information
                if country != "Unknown":
                    geo_info = f"{country}-{region}-{city}"
                    self.cache[ip] = geo_info
                    self._save_cache()
                    return geo_info
            except Exception as e:
                print(f"Failed to query with {api_url}: {e}")
                continue

        # If all APIs fail, return unknown
        geo_info = "Unknown-Unknown-Unknown"
        self.cache[ip] = geo_info
        self._save_cache()
        return geo_info

    def update_all_resources_geo(self):
        """Update geo location information for all resources"""
        print(f"Starting to update geo location information for resources...")

        # Get all resources
        self.cursor.execute("SELECT id, url, server_region FROM resources LIMIT 50")
        resources = self.cursor.fetchall()

        total = len(resources)
        updated = 0
        skipped = 0

        print(f"Found {total} resources to update")

        for resource_id, url, server_region in resources:
            if server_region and server_region != "Unknown-Unknown-Unknown":
                skipped += 1
                continue

            # Extract IP
            ip = self.get_ip_from_url(url)
            if not ip:
                skipped += 1
                continue

            # Get geo information
            geo_info = self.get_geo_info(ip)

            # Update database
            self.cursor.execute(
                "UPDATE resources SET server_region = ? WHERE id = ?",
                (geo_info, resource_id),
            )
            updated += 1
            print(f"Updated resource {resource_id}: {url} -> {ip} -> {geo_info}")

            # Commit every 10 resources
            if updated % 10 == 0:
                self.conn.commit()

        # Final commit
        self.conn.commit()

        print(f"\nUpdate completed:")
        print(f"- Total resources: {total}")
        print(f"- Updated resources: {updated}")
        print(f"- Skipped resources: {skipped}")

    def get_current_location(self):
        """Get current location information"""
        print("Getting current location information...")
        try:
            response = requests.get("https://ipapi.co/json/", timeout=5)
            response.raise_for_status()
            data = response.json()
            country = data.get("country_name", "Unknown")
            region = data.get("region", "Unknown")
            city = data.get("city", "Unknown")
            current_location = f"{country}-{region}-{city}"
            print(f"Current location: {current_location}")
            return current_location
        except Exception as e:
            print(f"Failed to get current location: {e}")
            return "Unknown-Unknown-Unknown"

    def close(self):
        """关闭数据库连接"""
        self.conn.close()


def main():
    """主函数"""
    resolver = IPGeoResolver()
    try:
        # 获取当前位置
        current_location = resolver.get_current_location()
        print(f"\n当前测试执行位置: {current_location}")
        # 更新所有资源的地理位置
        resolver.update_all_resources_geo()
    finally:
        resolver.close()


if __name__ == "__main__":
    main()
