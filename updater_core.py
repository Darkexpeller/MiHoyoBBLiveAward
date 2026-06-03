import os
import sys
import time
import requests
import configparser
import subprocess

VERSION_CHECK_URL = "https://philia093.online/BBLiveAward/update.json"
CURRENT_VERSION = "1.0.4"

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

def check_and_do_update():
    print(f"[*] 当前本地软件版本: {CURRENT_VERSION}")
    
    if not sys.executable.endswith(".exe") or "python" in sys.executable.lower():
        print("已跳过更新。")
        return True

    try:
        # 2. 拉取远程版本信息
        print("[*] 正在检查远程服务器更新...")
        response = requests.get(VERSION_CHECK_URL, timeout=5)
        response.raise_for_status()
        remote_data = response.json()
        
        remote_ver = remote_data.get("latest_version")
        download_url = remote_data.get("download_url")
        
        # 3. 极简对比逻辑
        if remote_ver != CURRENT_VERSION:
            print(f"🎉 发现新版本 {remote_ver}！准备下载...")
            
            temp_new_exe = os.path.join(get_real_dir(), "app_new.exe_tmp")
            
            # 4. 流式下载新版文件
            print("[*] 正在下载新版本文件，请稍候...")
            with requests.get(download_url, stream=True, timeout=30) as r:
                r.raise_for_status()
                with open(temp_new_exe, 'wb') as f:
                    for chunk in r.iter_content(chunk_size=8192):
                        if chunk:
                            f.write(chunk)
                            
            print("新版本文件下载完成。")
            
            # 5. 直接呼叫 bat 进行自杀替换
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