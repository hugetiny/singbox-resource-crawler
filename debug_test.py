import re
import pybase64

# 模拟从爬虫中提取出的逻辑
PROTOCOL_PATTERNS = {
    'ss': r'ss://[a-zA-Z0-9+/=]+(?:#[^ \n\r\t<>"]+)?',
    'vmess': r'vmess://[a-zA-Z0-9+/=]+',
    'vless': r'vless://[a-f0-9-]+@[^ \n\r\t<>"]+',
    'trojan': r'trojan://[a-zA-Z0-9]+@[^ \n\r\t<>"]+',
    'tuic': r'tuic://[a-f0-9-]+:[^ \n\r\t<>"]+',
    'hysteria2': r'(?:hysteria2|hy2)://[a-zA-Z0-9-]+@[^ \n\r\t<>"]+',
    'wireguard': r'wireguard://[^ \n\r\t<>"]+',
}

def test_extraction():
    sample_text = """
    Here are some nodes:
    ss://YWVzLTI1Ni1nY206cGFzc3dvcmRAMTI3LjAuMC4xOjQ0Mw==#TestNode
    vmess://eyJhZGQiOiI4LjguOC44IiwicG9ydCI6NDQzLCJpZCI6ImFiYyJ9
    hysteria2://user:pass@1.1.1.1:1234
    """
    
    print("--- Starting Extraction Test ---")
    for proto, pattern in PROTOCOL_PATTERNS.items():
        matches = re.findall(pattern, sample_text, re.IGNORECASE)
        for m in matches:
            print(f"Found {proto.upper()}: {m}")

    # 测试 Base64 解码逻辑
    print("\n--- Starting Base64 Test ---")
    b64_data = pybase64.b64encode(b"vless://uuid@host:port").decode()
    print(f"Encoded data: {b64_data}")
    decoded = pybase64.b64decode(b64_data).decode()
    if "vless://" in decoded:
        print("Base64 decoding logic: SUCCESS")

if __name__ == "__main__":
    test_extraction()
