#!/usr/bin/env python3
import json
import os
import platform
import queue
import sqlite3
import subprocess
import threading
import time
from datetime import datetime

# 配置
import sys
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

# 从环境变量获取数据库路径，默认为data.db
DB_PATH = os.environ.get("DATABASE_DB_PATH", "data.db")

# 如果数据库路径不是绝对路径，则相对于项目根目录
if not os.path.isabs(DB_PATH):
    DB_PATH = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))), DB_PATH
    )

SINGBOX_BINARY = os.path.join(os.path.dirname(os.path.abspath(__file__)), "sing-box")
THREAD_COUNT = 5
TEST_TIMEOUT = 10  # 每个资源的测试超时时间（秒）

# 确保可执行文件扩展符合平台要求
if platform.system() == "Windows":
    SINGBOX_BINARY += ".exe"

# 导入IP地理位置解析器
sys.path.insert(0, os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "utils"
))
from ip_verification.ip_geo import IPGeoResolver


class ResourceTester:
    def __init__(self):
        # 不在这里创建数据库连接，而是在每个线程中创建
        self.resolver = IPGeoResolver()
        self.test_results = []
        # 获取当前位置，如果失败则使用默认值
        try:
            self.current_location = self.resolver.get_current_location()
        except Exception as e:
            print(f"获取当前位置失败: {e}")
            self.current_location = "未知-未知-未知"

    def get_resources(self):
        """获取所有资源"""
        # 在主线程中创建数据库连接来获取资源
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id, url, protocol, source, server_region, crawl_time, status FROM resources"
        )
        resources = cursor.fetchall()
        conn.close()
        return resources

    def test_resource(self, resource):
        """测试单个资源的可用性"""
        resource_id, url, protocol, source, server_region, crawl_time, status = resource

        result = {
            "id": resource_id,
            "url": url,
            "protocol": protocol,
            "source": source,
            "server_region": server_region,
            "crawl_time": crawl_time,
            "status": status,
            "test_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "test_location": self.current_location,
            "response_time": 0,
            "error_message": "",
            "details": {},
        }

        start_time = time.time()

        try:
            # 根据协议类型执行不同的测试
            if protocol in ["clash_sub", "singbox_sub"]:
                # 订阅链接测试
                self._test_subscription(url, result)
            else:
                # 普通代理链接测试
                self._test_proxy(url, protocol, result)

            # 更新服务器区域（如果之前为空）
            if not result["server_region"] and hasattr(
                result["details"], "server_region"
            ):
                result["server_region"] = result["details"]["server_region"]

        except Exception as e:
            result["error_message"] = str(e)

        end_time = time.time()
        result["response_time"] = round(end_time - start_time, 3)

        # 更新数据库
        self._update_resource_in_db(result)

        return result

    def _update_resource_in_db(self, result):
        """将测试结果更新到数据库"""
        try:
            # 在每次调用时创建新的数据库连接，避免跨线程问题
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE resources SET status = ?, server_region = ? WHERE id = ?",
                (result["status"], result["server_region"], result["id"]),
            )
            conn.commit()
            conn.close()
            print(
                f"  数据库已更新: ID {result['id']} - 状态: {result['status']} - 区域: {result['server_region']}"
            )
        except Exception as e:
            print(f"  更新数据库失败: {e}")

    def _test_subscription(self, url, result):
        """测试订阅链接"""
        import requests

        try:
            response = requests.get(url, timeout=TEST_TIMEOUT)
            if response.status_code < 400:
                result["status"] = "success"
                result["details"] = {
                    "status_code": response.status_code,
                    "content_length": len(response.content),
                    "content_type": response.headers.get("Content-Type", ""),
                }
            else:
                result["error_message"] = f"HTTP {response.status_code}"
        except Exception as e:
            result["error_message"] = f"订阅链接测试失败: {e}"

    def _test_proxy(self, url, protocol, result):
        """测试普通代理链接"""
        # 检查sing-box是否存在
        if not os.path.exists(SINGBOX_BINARY):
            result["error_message"] = "sing-box 二进制文件不存在"
            return

        # 根据协议类型生成不同的配置
        # Singbox支持的协议类型
        protocol_mapping = {
            "vmess": "vmess",
            "vless": "vless",
            "ss": "shadowsocks",
            "ssr": "shadowsocks",
            "trojan": "trojan",
            "tuic": "tuic",
            "hysteria": "hysteria",
            "hysteria2": "hysteria2",
            "hy2": "hysteria2",
            "wireguard": "wireguard",
        }

        # 获取singbox支持的协议类型
        singbox_protocol = protocol_mapping.get(protocol, protocol)

        # 创建临时配置文件（放到tmp目录）
        tmp_dir = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tmp"
        )
        os.makedirs(tmp_dir, exist_ok=True)
        config_path = os.path.join(tmp_dir, f"temp_config_{result['id']}.json")

        temp_config = {
            "inbounds": [
                {
                    "type": "socks",
                    "listen": "127.0.0.1",
                    "listen_port": 0,
                    "tag": "socks-in",
                }
            ],
            "outbounds": [
                {"type": singbox_protocol, "tag": "proxy-out", "server": url},
                {"type": "direct", "tag": "direct-out"},
            ],
            "route": {
                "final": "proxy-out",
            },
        }

        with open(config_path, "w", encoding="utf-8") as f:
            json.dump(temp_config, f, ensure_ascii=False, indent=2)

        try:
            # 启动sing-box测试
            cmd = [SINGBOX_BINARY, "check", "--config", config_path]
            process = subprocess.run(
                cmd, capture_output=True, text=True, timeout=TEST_TIMEOUT
            )

            if process.returncode == 0:
                result["status"] = "success"
                result["details"] = {"output": process.stdout.strip()}
            else:
                result["error_message"] = f"配置检查失败: {process.stderr.strip()}"
        except subprocess.TimeoutExpired:
            result["error_message"] = "测试超时"
        except Exception as e:
            result["error_message"] = f"代理测试失败: {e}"
        finally:
            # 清理临时文件
            if os.path.exists(config_path):
                os.remove(config_path)

    def test_resources(self):
        """批量测试所有资源"""
        print(f"{'-'*60}")
        print(f"资源测试器 v1.0")
        print(f"测试执行位置: {self.current_location}")
        print(f"测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"线程数: {THREAD_COUNT}")
        print(f"超时时间: {TEST_TIMEOUT}秒")
        print(f"{'-'*60}")

        # 获取所有资源
        resources = self.get_resources()
        total = len(resources)
        print(f"共找到 {total} 个资源，开始测试...")

        # 创建队列
        resource_queue = queue.Queue()
        result_queue = queue.Queue()

        for resource in resources:
            resource_queue.put(resource)

        # 定义工作线程
        def worker():
            while True:
                try:
                    resource = resource_queue.get(timeout=1)
                    result = self.test_resource(resource)
                    result_queue.put(result)
                    print(f"测试完成 [{result['status'].upper()}]: {resource[1]}")
                    resource_queue.task_done()
                except queue.Empty:
                    break
                except Exception as e:
                    print(f"工作线程错误: {e}")
                    break

        # 启动工作线程
        threads = []
        for _ in range(min(THREAD_COUNT, total)):
            t = threading.Thread(target=worker)
            t.daemon = True
            t.start()
            threads.append(t)

        # 等待所有任务完成
        resource_queue.join()

        # 收集结果
        while not result_queue.empty():
            self.test_results.append(result_queue.get())

        print(f"\n{'-'*60}")
        print("所有测试完成!")
        self.generate_report()

    def generate_report(self):
        """生成测试报告"""
        # 统计结果
        total = len(self.test_results)
        success = sum(1 for r in self.test_results if r["status"] == "success")
        failed = total - success
        success_rate = (success / total * 100) if total > 0 else 0
        avg_response_time = (
            sum(r["response_time"] for r in self.test_results) / total
            if total > 0
            else 0
        )

        # 按地区统计
        region_stats = {}
        for result in self.test_results:
            region = result["server_region"] or "未知"
            if region not in region_stats:
                region_stats[region] = {"total": 0, "success": 0, "failed": 0}
            region_stats[region]["total"] += 1
            if result["status"] == "success":
                region_stats[region]["success"] += 1
            else:
                region_stats[region]["failed"] += 1

        # 按协议统计
        protocol_stats = {}
        for result in self.test_results:
            protocol = result["protocol"]
            if protocol not in protocol_stats:
                protocol_stats[protocol] = {"total": 0, "success": 0, "failed": 0}
            protocol_stats[protocol]["total"] += 1
            if result["status"] == "success":
                protocol_stats[protocol]["success"] += 1
            else:
                protocol_stats[protocol]["failed"] += 1

        # 生成报告文件名（放到tmp目录）
        tmp_dir = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tmp"
        )
        os.makedirs(tmp_dir, exist_ok=True)
        report_filename = (
            f"resource_test_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        )
        report_path = os.path.join(tmp_dir, report_filename)

        # 生成JSON报告
        report = {
            "summary": {
                "total_resources": total,
                "success": success,
                "failed": failed,
                "success_rate": round(success_rate, 2),
                "avg_response_time": round(avg_response_time, 3),
                "test_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "test_location": self.current_location,
                "thread_count": THREAD_COUNT,
                "timeout": TEST_TIMEOUT,
            },
            "region_stats": region_stats,
            "protocol_stats": protocol_stats,
            "detailed_results": self.test_results,
        }

        with open(report_path, "w", encoding="utf-8") as f:
            json.dump(report, f, ensure_ascii=False, indent=2)

        # 打印简要报告
        print(f"\n测试报告摘要:")
        print(f"{'-'*60}")
        print(f"总资源数: {total}")
        print(f"成功: {success} ({success_rate:.2f}%)")
        print(f"失败: {failed}")
        print(f"平均响应时间: {avg_response_time:.3f}秒")
        print(f"{'-'*60}")

        print(f"\n按协议统计:")
        print(f"{'-'*60}")
        for protocol, stats in protocol_stats.items():
            protocol_success_rate = (
                (stats["success"] / stats["total"] * 100) if stats["total"] > 0 else 0
            )
            print(
                f"{protocol:15} | 总: {stats['total']:4} | 成功: {stats['success']:4} | 失败: {stats['failed']:4} | 成功率: {protocol_success_rate:6.2f}%"
            )

        print(f"\n按地区统计:")
        print(f"{'-'*60}")
        for region, stats in region_stats.items():
            region_success_rate = (
                (stats["success"] / stats["total"] * 100) if stats["total"] > 0 else 0
            )
            print(
                f"{region:30} | 总: {stats['total']:4} | 成功: {stats['success']:4} | 失败: {stats['failed']:4} | 成功率: {region_success_rate:6.2f}%"
            )

        print(f"\n{'-'*60}")
        print(f"详细报告已保存到: {report_path}")
        print(f"{'-'*60}")

    def close(self):
        """关闭资源"""
        # 只关闭 IP 解析器，因为数据库连接是在每次调用时创建和关闭的
        self.resolver.close()


def main():
    """主函数"""
    tester = ResourceTester()

    try:
        tester.test_resources()
    finally:
        tester.close()


if __name__ == "__main__":
    main()
