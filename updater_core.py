import os
import sys
import requests
import subprocess
VERSION_CHECK_URL = "https://philia093.online/BBLiveAward/update.json"
CURRENT_VERSION = "1.0.8"

def get_real_dir():
    """获取当前程序运行的真实目录"""
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))

def execute_bat_and_exit(new_exe_path):
    """生成批处理脚本，执行覆盖替换并重启"""
    current_exe = sys.executable
    real_dir = get_real_dir()
    
    bat_content = f"""@echo off
echo ====================================
echo   正在应用更新，请勿关闭此窗口...
echo ====================================
ping 127.0.0.1 -n 3 > nul
del /f /q "{current_exe}"
move /y "{new_exe_path}" "{current_exe}"
start "" "{current_exe}"
del "%~f0"
"""
    bat_path = os.path.join(real_dir, "execute_update.bat")
    
    with open(bat_path, "w", encoding="gbk") as f:
        f.write(bat_content)
        
    print("准备重启并应用新版本...")
    subprocess.Popen([bat_path], creationflags=subprocess.CREATE_NEW_CONSOLE)
    sys.exit(0) 
def download_with_progress(url: str, output_path: str):
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept-Encoding": "gzip, deflate, br",
        "Connection": "keep-alive"
    }
    with requests.Session() as session:
        with session.get(url, stream=True, headers=headers, timeout=60.0) as r:
            r.raise_for_status()
            with open(output_path, 'wb') as f:
                for chunk in r.iter_content(chunk_size=1048576):
                    if chunk:
                        f.write(chunk)
                        
            print("下载完成...")
def check_and_do_update():
    print(f"[*] 当前本地软件版本: {CURRENT_VERSION}")
    
    if not sys.executable.endswith(".exe") or "python" in sys.executable.lower():
        print("已跳过更新。")
        return True
    try:
        #拉取远程版本信息
        print("[*] 正在检查远程服务器更新...")
        response = requests.get(VERSION_CHECK_URL, timeout=5)
        response.raise_for_status()
        remote_data = response.json()
        
        remote_ver = remote_data.get("latest_version")
        download_url = remote_data.get("download_url")
        
        if remote_ver != CURRENT_VERSION:
            print(f"🎉 发现新版本 {remote_ver}！准备下载...")
            
            temp_new_exe = os.path.join(get_real_dir(), "app_new.exe_tmp")
            
            print("[*] 正在下载新版本文件，请稍候...")
            download_with_progress(download_url,temp_new_exe)
            
            execute_bat_and_exit(temp_new_exe)
            
        else:
            print("当前已是最新版本，无需更新。")
            return True
            
    except requests.RequestException as e:
        print(f"网络请求失败，请检查网络或服务器: {e}")
        return False
    except Exception as e:
        print(f"检查更新过程中发生未知错误: {e}")
        return False