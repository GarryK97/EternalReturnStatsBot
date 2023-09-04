#-*-coding:utf-8-*-

import time
import discord
import selenium.common
from discord.ext import commands
from discord.ext import tasks
import asyncio
import json
from datetime import datetime
from datetime import timedelta
from dotenv import load_dotenv
import os

from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.common.by import By

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='!!', intents=intents)

# ---------------- 명령어 및 기본 변수 정리 ---------------------------
comms_array = []  # Ordered 되야하기때문에 어레이로 사용
comms_string = ", ".join(comms_array)  # 명령어 안내등 필요할시 사용할 명령어 스트링

notfound_string = f"명령어 확인 불가\n명령어: {comms_string}\n"

mainstats_addr = "https://dak.gg/er/"  # 통계주소로 사용할 메인주소

# ----------------- 시간단축용 함수들 ----------------------
async def process_time_input(ctx):
    await ctx.send("섬 시간을 입력해주세요 (ex. 17:30 0:20, 여러번 입력가능, 종료시엔 ㅇㅇ 입력)")
    time_input_list = []
    end = False
    while end is False:
        user_input = await wait_for_user_content(ctx)
        if user_input != "ㅇㅇ":
            time_input_list.append(user_input)
            await ctx.send(" | ".join(time_input_list))
        else:
            await ctx.send("최종시간 확인")
            await ctx.send(" | ".join(time_input_list))
            await ctx.send("입력한 시간이 맞습니까? (ㅇㅇ, ㄴㄴ)")

            confirm_input = await wait_for_user_content(ctx)
            if confirm_input == "ㅇㅇ":
                end = True
            else:
                time_input_list = []
                await ctx.send("입력된 시간을 리셋합니다")
                await ctx.send("섬 시간을 입력해주세요 (ex. 17:30 0:20, 여러번 입력가능, 종료시엔 ㅇㅇ 입력)")

    return time_input_list


async def wait_for_user_content(ctx):
    timeout = 20

    def check(m):
        return m.author == ctx.message.author and m.channel == ctx.message.channel

    try:
        user_input = await bot.wait_for('message', check=check, timeout=timeout)
        return user_input.content
    except asyncio.exceptions.TimeoutError:
        await ctx.send("장기간 대기하여 종료합니다")
        return ""


async def update_json(ctx, dict_data, response):
    try:
        with open('data.json', 'w', encoding='utf-8') as newf:
            json.dump(dict_data, newf, indent=2, ensure_ascii=False)
        await ctx.send(response)
    except:
        await ctx.send("!!섬 데이터 수정중 오류가 발생했습니다!!")


async def print_no_data(ctx, island_name):
    await ctx.send(f"입력하신 {island_name} 섬은 존재하지 않습니다. 확인 후 다시 시도해주세요")

# ----------------- 시간단축용 함수들 (끝) ----------------------


# ------------ 반복 태스크들용 함수들 ------------
@bot.event
async def on_ready():
    print(f'Logged in as {bot.user} (ID: {bot.user.id})')
    print('------')


@tasks.loop(seconds=60)
async def alarm_task():
    for island in data.keys():
        current_time = datetime.strptime(datetime.now().strftime("%H:%M"), "%H:%M")
        for island_time_string in data[island]['times']:
            island_time = datetime.strptime(island_time_string, "%H:%M")
            if island_time.hour == 0:
                island_time = island_time + timedelta(days=1)

            time_left = island_time - current_time
            if data[island]['alarm_on'] is True and time_left > timedelta(seconds=1) and time_left.total_seconds() // 60 == data[island]["alarm_time"]:
                hour = datetime.strftime(island_time, "%H")
                minute = datetime.strftime(island_time, "%M")
                channel = bot.get_channel(1072387867600506990)  # 스카이넷일터 채널에 전송
                await channel.send(f'{hour}시 {minute}분 {island} {data[island]["alarm_time"]}분전입니다', tts=True)


msg_list = []
@tasks.loop(seconds=90)
async def special_card_alarm_task():
    options = webdriver.ChromeOptions()
    options.add_argument("headless")
    url = "https://kloa.gg/merchant?utm_source=discord&utm_medium=bot&utm_campaign=divider"
    driver = webdriver.Chrome('./chromedriver.exe', options=options)
    driver.implicitly_wait(10)
    try:
        driver.get(url)
    except:
        driver.quit()
        print(f"클로아 홈페이지 접속 장애 발생중 ----- {datetime.now().strftime('%H:%M')}")
        return

    try:
        merchant_list = driver.find_element(By.CLASS_NAME, 'w-full.h-full.flex.justify-center.overflow-y-scroll.merchant_merchant_list__HaOZR')
        for _ in range(7):  # 7번 반복
            driver.execute_script("arguments[0].scrollBy(0,1080)", merchant_list)
            await asyncio.sleep(0.5)
    # 클로아 홈페이지 자체가 로딩이 안되는 경우 간혹발생, 그 경우 아예 포기
    except selenium.common.NoSuchElementException:
        driver.quit()
        print(f"클로아 홈페이지 접속 장애 발생중 ----- {datetime.now().strftime('%H:%M')}")
        return



    html = driver.page_source
    soup = BeautifulSoup(html, 'html.parser')
    driver.quit()  # 크롬탭 여러개 실행하는 메모리 누수 방지

    active_servers = ["실리안", "니나브", "루페온"]
    active_items = ["웨이 카드", "에버그레이스 카드", "바르칸 카드", "오징어"]

    random_merchant_data = soup.find_all("div", {"class": "first:rounded-t-[10px] last:rounded-b-[10px] flex items-center w-full h-[60px] justify-between relative px-[30px] border-t border-l-2 border-r-2 border-basicGrey first:border-t-2 last:border-b-2 bg-white"})
    for each_table in random_merchant_data:
        server_name = each_table.find("span", {"class": "self-center text-sm"}).text  # 서버이름
        location_name = each_table.find("span", {
            "class": "self-center group-hover:text-main2 text-lg text-head font-medium leading-[22px] transition-all duration-200 ease-in-out"}).text  # 떠상 지역
        merchant_hour = each_table.find("span", {"class": "self-center w-[48px]"}).text[:2]
        # 설정한 서버일때만, 그리고 현재 등장한것만 체크 (과거에 등장한것까지 알림하는걸 예외처리하기위함)
        if server_name in active_servers and int(merchant_hour) == datetime.now().hour:
            all_items = each_table.select('[class^="px-[4px] leading-[22px]"]')  # 나온 템
            for item in all_items:
                inform_string = f"{server_name} 서버 | {location_name}에 {item.text}가 등장했습니다."
                if item.text in active_items and inform_string not in msg_list:
                    channel = bot.get_channel(409244295372079106)   # General 채널에 전송
                    await channel.send(inform_string, tts=True)
                    channel = bot.get_channel(1072387867600506990)  # 스카이넷일터 채널에 전송
                    await channel.send(inform_string, tts=True)
                    msg_list.append(inform_string)  # 같은 알림이 여러번 전송되는것 방지

    # 매 정각마다 보냈던 메세지 리스트 초기화
    if 0 <= datetime.now().minute <= 3:
        msg_list.clear()


@alarm_task.before_loop
@special_card_alarm_task.before_loop
async def before_my_task():
    await bot.wait_until_ready()  # wait until the bot logs in

# ------------ 반복 태스크들용 함수들 (끝) ------------


# ----------------- 봇 명령어 ------------------------
@bot.command()
async def 섬(ctx, *param):
    # 명령어 2개 이상 입력시 (ex. !섬 에라스모 or !섬 시간변경)
    if len(param) > 0:
        name_input = param[0]
        if name_input == comms_array[0]:    # [0] = ""
            await ctx.send("섬을 추가합니다")

            end = False
            while end is False:
                await ctx.send("섬 이름을 입력해주세요")
                island_name_input = await wait_for_user_content(ctx)
                if island_name_input == "":
                    return

                await ctx.send("최종이름 확인")
                await ctx.send(island_name_input)
                await ctx.send("입력한 이름이 맞습니까? (ㅇㅇ, ㄴㄴ)")
                confirm_input = await wait_for_user_content(ctx)
                if confirm_input == "ㅇㅇ":
                    end = True
                else:
                    await ctx.send("이름을 다시 입력받습니다")

            time_input_list = await process_time_input(ctx)

            await ctx.send("알람 설정을 하시겠습니까? (ㅇㅇ, ㄴㄴ)")
            alarm_input = await wait_for_user_content(ctx)
            alarm_on = False
            alarm_time_input = 10  # default
            if alarm_input == "ㅇㅇ":
                alarm_on = True
                await ctx.send("몇분 전에 알림을 전송할까요? (ex. 10 => 10분전 알람 전송)")
                alarm_time_input = await wait_for_user_content(ctx)
                await ctx.send(f"{alarm_time_input}분 전에 알람을 전송합니다")

            new_island_data = {'name': island_name_input, 'times': time_input_list, 'alarm_time': int(alarm_time_input), 'alarm_on': alarm_on}
            data[island_name_input] = new_island_data
            await update_json(ctx, data, f"새로운 {island_name_input} 섬을 성공적으로 추가했습니다")

        elif name_input == "전체":
            await ctx.send(" | ".join(data.keys()))

        elif name_input == "삭제":
            await ctx.send("삭제할 섬의 이름을 입력해주세요 (저장 데이터와 동일해야함)")
            delete_name_input = await wait_for_user_content(ctx)
            if delete_name_input in data.keys():
                await ctx.send(f"정말 {delete_name_input} 섬을 삭제하시겠습니까? (ㅇㅇ, ㄴㄴ)")
                confirm_input = await wait_for_user_content(ctx)
                if confirm_input == "ㅇㅇ":
                    data.pop(delete_name_input)
                    await update_json(ctx, data, f"{delete_name_input} 섬을(를) 문제없이 삭제했습니다")
                    return
                else:
                    await ctx.send("섬 삭제 명령이 취소되었습니다")
                    return
            else:
                await print_no_data(ctx, delete_name_input)

        else:
            try:
                island_data = data[name_input]
            except KeyError:
                await print_no_data(ctx, name_input)
                return

            if len(param) > 1:
                detail = param[1]
                if detail == "전체시간":
                    island_times = island_data['times']
                    time_string = " | ".join(island_times)
                    await ctx.send(name_input + "의 전체 시간은 " + time_string + " 입니다")
                    return

                elif detail == "다음시간":
                    min_time = timedelta(days=2)    # Min value 찾기위한 디폴트값
                    min_time_island = ""
                    current_time = datetime.strptime(datetime.now().strftime("%H:%M"), "%H:%M")
                    for a_time in island_data['times']:
                        island_time = datetime.strptime(a_time, "%H:%M")
                        if island_time.hour == 0:
                            island_time = island_time + timedelta(days=1)
                        time_diff = island_time - current_time
                        if time_diff > timedelta(seconds=1):
                            if time_diff < min_time:
                                min_time = time_diff
                                min_time_island = island_time.strftime("%H:%M")

                    time_left = int(min_time.total_seconds() // 60)
                    if time_left >= 60:
                        await ctx.send(f"{name_input} 섬의 다음 등장 시간 - {min_time_island} ({time_left // 60}시간 {time_left % 60}분 뒤 출현)")
                    else:
                        await ctx.send(name_input + " 섬의 다음 등장 시간 - " + min_time_island + " (" + str(time_left) + "분 뒤 출현)")
                    return

                elif detail == "시간변경":
                    time_input_list = await process_time_input(ctx)
                    island_data['times'] = time_input_list
                    await update_json(ctx, data, f"{island_data['name']} 섬의 시간이 성공적으로 변경되었습니다")
                    return

                elif detail == "알람확인":
                    on_off_status = "ON" if island_data['alarm_on'] is True else "OFF"
                    await ctx.send(f"{name_input} 섬의 알람 설정은 {island_data['alarm_time']}분 전 알람입니다.\n{name_input} 섬의 알람은 현재 {on_off_status} 상태입니다.")

                elif detail == "알람변경":
                    on_off_status = "ON" if island_data['alarm_on'] is True else "OFF"
                    await ctx.send(f"{name_input} 섬의 알람 설정은 {island_data['alarm_time']}분 전 알람입니다.\n{name_input} 섬의 알람은 현재 {on_off_status} 상태입니다.")
                    await ctx.send(f"{name_input} 섬의 알람 시간을 변경하시겠습니까? (ㅇㅇ, ㄴㄴ)")
                    yes_no_input = await wait_for_user_content(ctx)
                    if yes_no_input == "ㅇㅇ":
                        await ctx.send("변경할 알람 시간을 입력해주세요. (ex. 10 => 10분전 알람)")
                        alarm_time_input = await wait_for_user_content(ctx)

                        island_data['alarm_time'] = int(alarm_time_input)
                        await update_json(ctx, data, f"{name_input} 섬의 알람이 {alarm_time_input} 분 전으로 변경되었습니다")
                        return

                elif detail == "알람켜":
                    island_data['alarm_on'] = True
                    await update_json(ctx, data, f"{name_input} 섬의 알람이 {island_data['alarm_time']} 분 전에 설정되었습니다")

                elif detail == "알람꺼":
                    island_data['alarm_on'] = False
                    await update_json(ctx, data, f"{name_input} 섬의 알람이 종료되었습니다")

                else:
                    await ctx.send(feedback_string)
            else:
                await ctx.send(feedback_string)
    #!섬 만 입력시 따로 명령어 안내
    else:
        await ctx.send(feedback_string)

@bot.command()
async def 명령어(ctx):
    commands_list = ["!섬"]
    await ctx.send(", ".join(commands_list))
    return


# ----------------- 봇 명령어 (끝) ------------------------



### ------------ Main ------------ ###
load_dotenv('config.env')
bot.run(os.getenv("BOT_TOKEN"))
