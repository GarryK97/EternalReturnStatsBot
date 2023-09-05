#-*-coding:utf-8-*-

import discord
from discord.ext import commands
from discord.ext import tasks
import json
from datetime import datetime
from dotenv import load_dotenv
import os
from enum import IntEnum
import tabulate

from bs4 import BeautifulSoup
from selenium import webdriver

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='!', intents=intents)

# ---------------- 명령어 및 기본 변수 정리 ---------------------------

# 새 명령어 추가시 이 리스트들도 수정필수
comms_live_list = ["이름", "픽률", "승률", "순방"]    # Enum 과 통일되도록 만듬
comms_day_list = ['3', '7', '10']

comms_live_string = f"실시간통계 ({','.join(comms_live_list)}) ({','.join(comms_day_list)})"
comms_personal_string = "개인통계 닉네임"

notfound_live_string = f"명령어 확인 불가\n명령어: {comms_live_string}"
notfound_personal_string = f"명령어 확인 불가\n명령어: {comms_personal_string}"

main_addr = "https://dak.gg/er/"  # 통계주소로 사용할 메인주소
livestats_addr = "statistics?teamMode=SQUAD&type=REALTIME_OVER_DIAMOND&period="
personal_addr = "players/"

# 이름, 픽률, 승률, 순방 순서로 정리됨
livestats3_list = []
livestats7_list = []
livestats10_list = []

PICKRATE_EXCLUSION = 1.0


class DATA(IntEnum):
    NAME = 0
    PICKRATE = 1
    WINRATE = 2
    TOPTHREE = 3

# ----------------- 프로그램용 함수들 ----------------------

@bot.event
async def on_ready():
    print(f'Logged in as {bot.user} (ID: {bot.user.id})')
    print('------')

    global livestats3_list, livestats7_list, livestats10_list

    livestats3_list = await get_livestats(livestats_addr + "3")
    livestats7_lsit = await get_livestats(livestats_addr + "7")
    livestats10_list = await get_livestats(livestats_addr + "10")


# @update_stats.before_loop
# async def before_my_task():
#     await bot.wait_until_ready()  # wait until the bot logs in

# --- 유저 입력 대기하고, 장기간 대기시 봇 종료
# async def wait_for_user_content(ctx):
#     timeout = 20
#
#     def check(m):
#         return m.author == ctx.message.author and m.channel == ctx.message.channel
#
#     try:
#         user_input = await bot.wait_for('message', check=check, timeout=timeout)
#         return user_input.content
#     except asyncio.exceptions.TimeoutError:
#         await ctx.send("장기간 대기하여 종료합니다")
#         return ""


# #--- JSON 데이터 업데이트용 함수
# async def update_json(ctx, dict_data, response):
#     try:
#         with open('data.json', 'w', encoding='utf-8') as newf:
#             json.dump(dict_data, newf, indent=2, ensure_ascii=False)
#         await ctx.send(response)
#     except:
#         await ctx.send("!!데이터 수정중 오류가 발생했습니다!!")


@tasks.loop(minutes=60)
async def get_livestats(stats_url):
    options = webdriver.ChromeOptions()
    # options.add_experimental_option("detach", True)   # 창 계속 띄워놓기 (디버그용)
    options.add_argument("headless")  # 디버그할땐 주석해서 비활성화
    driver = webdriver.Chrome('C:\chromedriver_win32\chromedriver.exe', options=options)
    driver.implicitly_wait(10)

    try:
        driver.get(main_addr + stats_url)
    except: # 접속 장애, 홈페이지 문제등 오류 발생시
        driver.quit()
        print(f"닥지지 홈페이지 접속 장애 발생중 ----- {datetime.now().strftime('%H:%M')}")
        return

    html = driver.page_source
    soup = BeautifulSoup(html, 'html.parser')
    all_subjects_data = soup.find_all("tr", {"class" : "border border border-t-0 border-[#e6e6e6]"})

    subjects_data = []
    for each_element in all_subjects_data:
        name = each_element.find("a", {"class" : "keep-all text-left hover:underline"}).text
        pickrate = each_element.find("td", {"class" : "p-[8px] text-center bg-[#f5f5f5] font-bold text-black"}).contents[0].text
        winrate = each_element.find("td", {"class" : "font-bold p-[8px] text-center"}).text
        topthree = each_element.find_all("td", {"class" : "p-[8px] text-center"})[2].text

        if '-' not in [pickrate, winrate, topthree]:
            subjects_data.append([name, pickrate, winrate, topthree])

    return subjects_data


async def check_input(userinput, comms_list):
    if userinput not in comms_list:
        return False
    return True


async def sort_livedata(param, datalist, comms_list):
    global PICKRATE_EXCLUSION

    base = -1

    if param == comms_list[DATA.PICKRATE]:
        datalist.sort(key=lambda x: x[DATA.PICKRATE], reverse=True)
        base = DATA.PICKRATE
    elif param == comms_list[DATA.WINRATE]:
        datalist.sort(key=lambda x: x[DATA.WINRATE], reverse=True)
        base = DATA.WINRATE
    elif param == comms_list[DATA.TOPTHREE]:
        datalist.sort(key=lambda x: x[DATA.TOPTHREE], reverse=True)
        base = DATA.TOPTHREE

    datalist = [x for x in datalist if float(x[DATA.PICKRATE].strip('%')) >= PICKRATE_EXCLUSION]

    for elem in datalist:
        elem[base] = elem[base]  # 디스코드 Bold Text 명령어

    return datalist


async def print_rankbased(ctx, sorted_list, start, end):
    output = "```" + tabulate.tabulate(sorted_list[start:end+1], headers=["실험체", "픽률", "승률", "순방"], tablefmt='simple', stralign='left', showindex=range(start+1,end+2)) + "```"
    output += f"**참고** : 픽률 {PICKRATE_EXCLUSION}% 미만의 실험체는 제외한 결과입니다."
    await ctx.send(output)
    print(output)

# ----------------- 시간단축용 함수들 (끝) ----------------------


# ----------------- 봇 명령어 ------------------------
@bot.command()
async def 명령어(ctx):
    await ctx.send(comms_live_string)
    return


@bot.command()
async def 실시간통계(ctx, *param):
    global livestats3_list, livestats7_list, livestats10_list

    if len(param) < 1:
        await ctx.send(notfound_live_string)
    elif len(param) == 1:   # 날짜 컷 입력 안했을경우 자동으로 3일 기반 데이터 사용 (즉, default = 3)
        sorted_livedata = await sort_livedata(param[0], livestats3_list, comms_live_list)
        await print_rankbased(ctx, sorted_livedata, 0, 9)
    elif len(param) == 2:
        return
    else:
        return


# ----------------- 봇 명령어 (끝) ------------------------

### ------------ Main ------------ ###
load_dotenv('config.env')
bot.run(os.getenv("BOT_TOKEN"))
