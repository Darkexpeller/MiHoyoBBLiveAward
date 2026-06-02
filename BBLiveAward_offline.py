import re
from dataclasses import dataclass
import requests
from functools import reduce
from hashlib import md5
import time
from datetime import datetime, timedelta
import concurrent.futures
import threading




mixinKeyEncTab = [
    46, 47, 18, 2, 53, 8, 23, 32, 15, 50, 10, 31, 58, 3, 45, 35, 27, 43, 5, 49,
    33, 9, 42, 19, 29, 28, 14, 39, 12, 38, 41, 13, 37, 48, 7, 16, 24, 55, 40,
    61, 26, 17, 0, 1, 60, 51, 30, 4, 22, 25, 54, 21, 56, 59, 6, 63, 57, 62, 11,
    36, 20, 34, 44, 52
]

snatch_success = False 
snatch_end=False
lock = threading.Lock()

def getMixinKey(orig: str):
    '对 imgKey 和 subKey 进行字符顺序打乱编码'
    return reduce(lambda s, i: s + orig[i], mixinKeyEncTab, '')[:32]

def getWbiKeys() -> tuple[str, str]:
    '获取最新的 img_key 和 sub_key'
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3',
        'Referer': 'https://www.bilibili.com/'
    }
    resp = requests.get('https://api.bilibili.com/x/web-interface/nav', headers=headers)
    resp.raise_for_status()
    json_content = resp.json()
    img_url: str = json_content['data']['wbi_img']['img_url']
    sub_url: str = json_content['data']['wbi_img']['sub_url']
    img_key = img_url.rsplit('/', 1)[1].split('.')[0]
    sub_key = sub_url.rsplit('/', 1)[1].split('.')[0]
    return img_key, sub_key

img_key, sub_key = getWbiKeys()
mixin_key = getMixinKey(img_key + sub_key)

@dataclass
class BiliTask:
    task_id: str
    activity_id: str
    activity_name: str
    task_name: str
    reward_name: str
    status: int

    @classmethod
    def from_response_dict(cls, task_id: str, resp_dict: dict) -> "BiliTask":
        data = resp_dict.get("data", {})
        reward_info = data.get("reward_info", {})
        return cls(
            task_id=task_id,
            activity_id=data.get("act_id", ""),
            activity_name=data.get("act_name", ""),
            task_name=data.get("task_name", ""),
            reward_name=reward_info.get("award_name", ""),
            status=data.get("status", "")
        )

def get_task_info(session: requests.Session, task_id: str, user_cookie: str):
    wts = round(time.time())
    w_rid = md5((f"task_id={task_id}&web_location=888.126558&wts={wts}{mixin_key}").encode()).hexdigest()
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36",
        "accept": "*/*",
        "cookie": user_cookie,
        "Referer": f"https://www.bilibili.com/blackboard/era/award-exchange.html?task_id={task_id}"
    })
    url = f"https://api.bilibili.com/x/activity_components/mission/info?task_id={task_id}&web_location=888.126558&w_rid={w_rid}&wts={wts}"
    resp = session.get(url)
    return resp.json()

def receive_mission(session: requests.Session, task_id: str, activity_id: str, activity_name: str,
                    task_name: str, reward_name: str, user_cookie: str, csrf: str) -> dict:
    body = {
        "task_id": task_id,
        "activity_id": activity_id,
        "activity_name": activity_name,
        "task_name": task_name,
        "reward_name": reward_name,
        "gaia_vtoken": "",
        "receive_from": "missionPage",
        "csrf": csrf,
    }
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36",
        "content-type": "application/x-www-form-urlencoded",
        "Referer": f"https://www.bilibili.com/blackboard/era/award-exchange.html?task_id={task_id}",
        "Cookie": user_cookie
    })
    
    wts = round(time.time())
    w_rid = md5((f"wts={wts}{mixin_key}").encode()).hexdigest()
    url = f"https://api.bilibili.com/x/activity_components/mission/receive?w_rid={w_rid}&wts={wts}"
    
    resp = session.post(url, data=body)
    return resp.json()


def wait_until_target_time(target_hour=1, target_minute=0):
    now = datetime.now()
    target_time = now.replace(hour=target_hour, minute=target_minute, second=0, microsecond=0)
    
    # 如果今天的时间已经过了，就设为明天的 1:00
    if now >= target_time:
        target_time += timedelta(days=1)
        
    wake_up_time = target_time - timedelta(seconds=1)
    sleep_seconds = (wake_up_time - now).total_seconds()
    
    if sleep_seconds > 0:
        print(f"[*] 当前时间: {now.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"[*] 目标唤醒: {wake_up_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"[*] 程序进入休眠，将等待 {sleep_seconds:.2f} 秒...\n")
        time.sleep(sleep_seconds)

def single_snatch_worker(thread_id, session, task, cookie, csrf):
    print(f"Thread-{thread_id} start")
    global snatch_success
    global snatch_end
    if snatch_success:
        return
        
    try:
        if(not snatch_end):
            ret = receive_mission(
                session, task.task_id, task.activity_id, 
                task.activity_name, task.task_name, task.reward_name, 
                cookie, csrf
            )
        else:
            print("snatch_end=true 提前终止")
            return 
        print(f"[Thread-{thread_id} {datetime.now().strftime('%H:%M:%S.%f')[:-3]}] 返回: {ret}")
        with lock:
            if not snatch_end:
                
                code=ret.get("code")
                if code == 0:
                    print(f"领取成功")
                    snatch_success = True
                    snatch_end=True
                elif code==202031:
                    print("任务奖励已经领取")
                    snatch_success = True
                    snatch_end=True
                elif code==202032:
                    print("无资格领取奖励")
                    snatch_end=True
                elif code==-101:
                    print("疑似cookie错误，请检查cookie")
                    snatch_end=True
                elif code==-705:
                    print("请求过于频繁，请稍后再试")
                elif code==202120:
                    print(f"未到每日领取时间")
                    
    except Exception as e:
        print(f"err:{e}")
        pass 

def multi_thread_snatch(session, task, cookie, csrf):
    global snatch_success
    global snatch_end
    snatch_success = False
    snatch_end=False
    max_workers = 4 
    total_attempts = 60
    
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = []
        for i in range(total_attempts):
            if  not snatch_end:
                future = executor.submit(single_snatch_worker, i, session, task, cookie, csrf)
                futures.append(future)
                time.sleep(0.55) 
            else:
                break
        concurrent.futures.wait(futures)
def fetch_and_select_task(json_url: str):
    """
    读取远程 JSON 并让用户在命令行选择任务
    :param json_url: 远程 task.json 的网络地址
    :return: 选中的 task_id (字符串)
    """

    print("正在获取远程任务列表...")
    
    try:
        # 1. 请求远程 JSON 数据
        response = requests.get(json_url, timeout=10)
        response.raise_for_status()
        task_data = response.json()
    except Exception as e:
        print(f"获取任务 JSON 失败: {e}")
        return None

    all_tasks = []
    
    print("\n==============================")
    print("       请选择要执行的任务       ")
    print("==============================")
    
    if "everyday_task" in task_data and task_data["everyday_task"]:
        print("\n[ 每日任务 ]")
        for task in task_data["everyday_task"]:
            all_tasks.append(task)
            print(f"  {len(all_tasks)}. {task['task_name']}")
            
    if "seasonal_task" in task_data and task_data["seasonal_task"]:
        print("\n[ 版本任务 ]")
        for task in task_data["seasonal_task"]:
            all_tasks.append(task)
            print(f"  {len(all_tasks)}. {task['task_name']}")
            
    print("\n==============================")


    while True:
        try:
            user_input = input(f"请输入任务编号 (1-{len(all_tasks)}): ").strip()
            
            # 将用户输入的字符转换为索引 (序号减 1)
            choice_idx = int(user_input) - 1
            
            if 0 <= choice_idx < len(all_tasks):
                selected_task = all_tasks[choice_idx]
                print(f"任务名称: {selected_task['task_name']}")
                print(f"任务 ID : {selected_task['task_id']}\n")
            
                return selected_task['task_id']
            else:
                print(f"编号超出范围，请输入 1 到 {len(all_tasks)} 之间的数字。")
                
        except ValueError:
            print("输入格式错误，请只输入数字！")
        except KeyboardInterrupt:
            print("\n用户取消了选择。")
            return None

def main():
    session = requests.Session()
    cookie = input("请输入用户cookie:")
    selected_task_id=input("请输入:task_id")
    match = re.search(r'bili_jct=([^;]+)', cookie)
    if match:
        csrf = match.group(1).strip()
    else:
        print("提取 CSRF 失败")
        return
    TaskInfo = get_task_info(session, selected_task_id, cookie)
    task = BiliTask.from_response_dict(selected_task_id, TaskInfo)
    print(task)
    if task.status == 6:
        print(f"[{task.task_name}] 奖励今天已经领取过了")
        return
    if task.status == 2:
        print(f"[{task.task_name}] 每日库存已达上限")
        return
    if task.status==0:
        print("当前可以领取")
        print(f"[*] 任务就绪: {task.task_name} | 奖品: {task.reward_name}")
        multi_thread_snatch(session, task, cookie, csrf)
        input("按任意键退出")
        return
        
    print(f"[*] 任务就绪: {task.task_name} | 奖品: {task.reward_name}")
    
    wait_until_target_time(target_hour=1, target_minute=0)
    
    multi_thread_snatch(session, task, cookie, csrf)
    input("按任意键退出")
if __name__ == "__main__":
    main()
