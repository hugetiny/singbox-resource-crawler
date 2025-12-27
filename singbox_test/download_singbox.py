#!/usr/bin/env python3
import os
import platform
import shutil
import sys
import tarfile
import zipfile
from datetime import datetime

import requests
from tqdm import tqdm

# 配置
DOWNLOAD_DIR = os.path.dirname(os.path.abspath(__file__))
SINGBOX_BINARY = os.path.join(DOWNLOAD_DIR, "sing-box")
GITHUB_API_URL = "https://api.github.com/repos/SagerNet/sing-box/releases"

# 确保可执行文件扩展符合平台要求
if platform.system() == "Windows":
    SINGBOX_BINARY += ".exe"

# 支持的平台和架构映射
SUPPORTED_PLATFORMS = {
    "Windows": ["amd64", "arm64"],
    "Darwin": ["amd64", "arm64"],
    "Linux": ["amd64", "arm64", "armv7", "i386"],
}

# 版本信息（自动获取）
SINGBOX_VERSION = None


class SingBoxDownloader:
    def __init__(self):
        self.release_info = None
        self.download_urls = {}

    def get_download_url(self, system, arch):
        """获取特定平台和架构的下载URL"""
        print(f"正在获取 {system} {arch} 平台的sing-box下载URL...")
        try:
            response = requests.get(GITHUB_API_URL, params={"per_page": 5}, timeout=30)
            response.raise_for_status()
            releases = response.json()

            # 确定文件扩展名
            if system == "Windows":
                ext = ".zip"
            else:
                ext = ".tar.gz"

            # 存储所有匹配的资产，以便后续排序
            matched_assets = []

            # 遍历所有release，查找匹配的资产
            for release in releases:
                print(
                    f"检查release: {release['tag_name']} (预发布: {release['prerelease']})"
                )
                assets = release["assets"]

                for asset in assets:
                    asset_name = asset["name"]
                    print(f"  检查资产: {asset_name}")

                    # 检查平台和架构是否匹配
                    platform_match = False
                    arch_match = False

                    # 平台匹配
                    if system == "Windows" and "windows" in asset_name.lower():
                        platform_match = True
                    elif system == "Darwin" and "darwin" in asset_name.lower():
                        platform_match = True
                    elif system == "Linux" and "linux" in asset_name.lower():
                        platform_match = True

                    # 架构匹配
                    if arch in asset_name.lower():
                        arch_match = True
                    elif arch == "amd64" and "x86_64" in asset_name.lower():
                        arch_match = True
                    elif arch == "arm64" and "aarch64" in asset_name.lower():
                        arch_match = True

                    # 文件扩展名匹配
                    ext_match = ext in asset_name

                    if platform_match and arch_match and ext_match:
                        # 将匹配的资产添加到列表
                        is_legacy = "legacy" in asset_name.lower()
                        matched_assets.append((is_legacy, asset))
                        print(f"  找到匹配的资产: {asset_name}")

            if matched_assets:
                # 排序资产：优先选择非legacy版本
                matched_assets.sort(key=lambda x: (x[0], x[1]["name"]))
                # 选择第一个（非legacy或最合适的）资产
                selected_asset = matched_assets[0][1]
                print(f"  选择的资产: {selected_asset['name']}")
                print(f"  下载URL: {selected_asset['browser_download_url']}")
                return selected_asset["browser_download_url"]

            print(f"未找到适合 {system} {arch} 平台的资产")
            return None
        except Exception as e:
            print(f"获取下载URL失败: {e}")
            return None


def get_platform_info():
    """获取当前平台信息"""
    system = platform.system()
    machine = platform.machine()

    # 映射机器架构到标准名称
    arch_mapping = {
        "x86_64": "amd64",
        "AMD64": "amd64",
        "aarch64": "arm64",
        "arm64": "arm64",
        "armv7l": "armv7",
        "i386": "i386",
    }

    arch = arch_mapping.get(machine, machine)
    return system, arch


def download_file(url, save_path, max_retries=3):
    """下载文件并显示进度，支持重试机制"""
    print(f"正在下载: {url}")
    print(f"保存路径: {save_path}")
    print(f"最大重试次数: {max_retries}")

    for retry in range(max_retries):
        try:
            print(f"  尝试下载 ({retry + 1}/{max_retries})...")
            response = requests.get(url, stream=True, timeout=60)
            response.raise_for_status()

            total_size = int(response.headers.get("content-length", 0))

            with open(save_path, "wb") as f, tqdm(
                desc="下载进度",
                total=total_size,
                unit="B",
                unit_scale=True,
                unit_divisor=1024,
                dynamic_ncols=True,
            ) as bar:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        bar.update(len(chunk))

            print(f"下载完成: {save_path}")
            return True
        except Exception as e:
            print(f"  下载失败: {e}")
            if retry < max_retries - 1:
                print(f"  等待3秒后重试...")
                import time

                time.sleep(3)
            else:
                print(f"所有重试均失败")
                return False


def extract_archive(archive_path, extract_dir):
    """解压归档文件"""
    print(f"正在解压: {archive_path}")

    try:
        if archive_path.endswith(".zip"):
            with zipfile.ZipFile(archive_path, "r") as zip_ref:
                zip_ref.extractall(extract_dir)
        elif archive_path.endswith(".tar.gz"):
            with tarfile.open(archive_path, "r:gz") as tar_ref:
                tar_ref.extractall(extract_dir)
        else:
            print(f"不支持的归档格式: {archive_path}")
            return False

        print(f"解压完成")
        return True
    except Exception as e:
        print(f"解压失败: {e}")
        return False


def find_singbox_binary(extract_dir):
    """查找解压后的sing-box可执行文件"""
    # 搜索所有目录
    for root, dirs, files in os.walk(extract_dir):
        for file in files:
            if file == "sing-box" or file == "sing-box.exe":
                return os.path.join(root, file)
    return None


def verify_singbox():
    """验证sing-box是否可执行"""
    if not os.path.exists(SINGBOX_BINARY):
        print(f"sing-box 二进制文件不存在: {SINGBOX_BINARY}")
        return False

    # 尝试获取版本信息
    try:
        import subprocess

        result = subprocess.run(
            [SINGBOX_BINARY, "version"], capture_output=True, text=True, timeout=10
        )
        if result.returncode == 0:
            print("sing-box 版本信息:")
            print(result.stdout.strip())
            return True
        else:
            print(f"获取版本信息失败: {result.stderr.strip()}")
            return False
    except Exception as e:
        print(f"验证失败: {e}")
        return False


def download_singbox():
    """下载并安装sing-box客户端"""
    print(f"{'-'*50}")
    print(f"SingBox 下载器 v1.0")
    print(f"当前时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"目标版本: 自动检测最新全量版本")
    print(f"{'-'*50}")

    # 检查是否已经存在
    if verify_singbox():
        print(f"\n{'='*50}")
        print("sing-box 已成功安装，跳过下载")
        print(f"{'='*50}")
        return True

    # 创建下载器实例
    downloader = SingBoxDownloader()

    # 获取平台信息
    system, arch = get_platform_info()
    print(f"\n检测到平台:")
    print(f"- 操作系统: {system}")
    print(f"- 架构: {arch}")

    # 获取下载URL
    download_url = downloader.get_download_url(system, arch)
    if not download_url:
        print("获取下载URL失败")
        return False

    print(f"\n准备下载:")
    print(f"- 下载URL: {download_url}")

    # 下载文件
    temp_dir = os.path.join(DOWNLOAD_DIR, "temp")
    os.makedirs(temp_dir, exist_ok=True)

    archive_name = os.path.basename(download_url)
    archive_path = os.path.join(temp_dir, archive_name)

    if not download_file(download_url, archive_path):
        shutil.rmtree(temp_dir, ignore_errors=True)
        return False

    # 解压文件
    if not extract_archive(archive_path, temp_dir):
        shutil.rmtree(temp_dir, ignore_errors=True)
        return False

    # 查找并移动二进制文件
    found_binary = find_singbox_binary(temp_dir)
    if not found_binary:
        print("未找到 sing-box 可执行文件")
        shutil.rmtree(temp_dir, ignore_errors=True)
        return False

    # 移动二进制文件到目标位置
    print(f"移动 sing-box 到目标位置: {SINGBOX_BINARY}")
    shutil.move(found_binary, SINGBOX_BINARY)

    # 设置执行权限（非Windows平台）
    if platform.system() != "Windows":
        os.chmod(SINGBOX_BINARY, 0o755)

    # 清理临时文件
    shutil.rmtree(temp_dir, ignore_errors=True)

    # 验证安装
    print(f"\n验证 sing-box 安装...")
    if verify_singbox():
        print(f"\n{'='*50}")
        print("sing-box 下载并安装成功!")
        print(f"二进制文件位置: {SINGBOX_BINARY}")
        print(f"{'='*50}")
        return True
    else:
        print(f"\n{'='*50}")
        print("sing-box 安装失败!")
        print(f"{'='*50}")
        return False


if __name__ == "__main__":
    success = download_singbox()
    sys.exit(0 if success else 1)
