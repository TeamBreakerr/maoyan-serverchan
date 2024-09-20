import json
import logging
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from typing import Optional, Union
from Monitor_DM import DM
from Monitor_FWD import FWD
from Monitor_MY import MY
from Monitor_PXQ import PXQ

import os
import urllib.parse
import urllib.request


def get_task(show: dict) -> Optional[Union[DM, MY, FWD, PXQ]]:
    platform_map = {
        0: DM,
        1: MY,
        2: FWD,
        3: PXQ
    }
    task_class = platform_map.get(show.get("platform"))
    return task_class(show) if task_class else None


class Runner:
    threadPool = ThreadPoolExecutor(max_workers=100, thread_name_prefix="ticket_monitor_")

    @staticmethod
    def sc_send(text, desp='', key='[SENDKEY]'):
        postdata = urllib.parse.urlencode({'text': text, 'desp': desp}).encode('utf-8')
        url = f'https://sctapi.ftqq.com/{key}.send'
        req = urllib.request.Request(url, data=postdata, method='POST')
        with urllib.request.urlopen(req) as response:
            result = response.read().decode('utf-8')
        return result

    @staticmethod
    def loop_monitor(monitor: Union[DM, MY, FWD, PXQ], show: dict, key: str) -> None:
        while datetime.strptime(show.get("deadline"), "%Y-%m-%d %H:%M:%S") > datetime.now():
            try:
                if monitor.monitor():
                    info = f"平台{show.get('platform')} {show.get('show_name')} 已回流，请及时购票！"
                    ret = Runner.sc_send(info, '', key)
                    print(ret)
                    logging.info(info)
                    monitor.bark_alert(info)
            except Exception as e:
                logging.error(f"发生错误：{e}", exc_info=True)
            finally:
                time.sleep(1)  # 或者使用 monitor.get_interval()

    def start(self):
        # 加载配置文件和环境变量
        try:
            with open("config.json", "r", encoding="utf-8") as file:
                show_list = json.load(file)
        except FileNotFoundError:
            logging.error("配置文件 config.json 未找到！")
            return
        except json.JSONDecodeError:
            logging.error("配置文件 config.json 格式错误！")
            return

        # 加载环境变量
        env_path = os.path.join(os.path.dirname(__file__), '.env')
        try:
            with open(env_path, 'r') as f:
                data = dict(line.strip().split('=') for line in f if '=' in line)
            key = data.get('SENDKEY', '')
            if not key:
                logging.error("未找到SENDKEY环境变量！")
                return
        except FileNotFoundError:
            logging.error(f"环境文件 {env_path} 未找到！")
            return
        except Exception as e:
            logging.error(f"读取环境变量失败：{e}", exc_info=True)
            return

        # 提交监控任务
        with self.threadPool as pool:
            for show in show_list:
                task = get_task(show)
                if task:
                    pool.submit(self.loop_monitor, task, show, key)
                else:
                    logging.error(f"监控对象 {show.get('show_name')} 加载失败 show_id: {show.get('show_id')}")


if __name__ == '__main__':
    runner = Runner()

    # 加载环境变量
    env_path = os.path.join(os.path.dirname(__file__), '.env')
    try:
        with open(env_path, 'r') as f:
            data = dict(line.strip().split('=') for line in f if '=' in line)
        key = data.get('SENDKEY', '')
        if not key:
            logging.error("未找到SENDKEY环境变量！")
            exit(1)
    except FileNotFoundError:
        logging.error(f"环境文件 {env_path} 未找到！")
        exit(1)
    except Exception as e:
        logging.error(f"读取环境变量失败：{e}", exc_info=True)
        exit(1)

    ret = Runner.sc_send('start!!!', '', key)
    print(ret)
    runner.start()
