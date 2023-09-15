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
import requests
import asyncio
from copy import deepcopy

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='!', intents=intents)
load_dotenv('config.env')

# ---------------- 명령어 및 기본 변수 정리 ---------------------------

# 새 명령어 추가시 이 리스트들도 수정필수
comms_live_list = ["이름", "픽률", "승률", "순방"]    # The index can be referred from LIVE_INDEX enum class (and must keep this order)
comms_day_list = ['3', '7', '10']
comms_live_param_list = ["제외", "전체"]

comms_live_string = f"실시간통계 ({','.join(comms_live_list)}) ({','.join(comms_day_list)}) ({','.join(comms_day_list)})"
comms_personal_string = "개인통계 닉네임"

notfound_live_string = f"명령어 확인 불가" \
                       f"\n명령어: 실시간통계 {comms_live_string} 또는" \
                       f"\n 실시간통계 {comms_live_string} {comms_day_list} 또는" \
                       f"\n 실시간통계 {comms_live_string} {comms_day_list} {comms_live_param_list}"

notfound_personal_string = f"명령어 확인 불가\n명령어: {comms_personal_string}"

mainstats_addr = "https://er.dakgg.io/v1/"  # Main api address for getting statistics (DAK.GG API)
livestats_addr = "statistics/realtime?teamMode=SQUAD&type=REALTIME_OVER_DIAMOND&period=DAYS"
personal_addr = "players/"

mainapi_addr = "https://open-api.bser.io/v1/"   # Official api address
mainapi_headers = {'x-api-key': os.getenv('API_KEY')}  # API Key header


# 이름, 픽률, 승률, 순방 순서로 정리됨
livestats3_list = []
livestats7_list = []
livestats10_list = []

PICKRATE_EXCLUSION = 0.01


# Enum class for comms_live_list (The index must match with the list)
class LIVE_INDEX(IntEnum):
    NAME = 0
    PICKRATE = 1
    WINRATE = 2
    TOPTHREE = 3


class DAY_INDEX(IntEnum):
    THREE = 0
    SEVEN = 1
    TEN = 2


# Enum class for comms_live_param_list
class LIVE_PARAM_INDEX(IntEnum):
    EXCLUDE = 0
    INCLUDE = 1


character_names_dict = \
    {
        1:"재키",
        2:"아야",
        3:"피오라",
        4:"매그너스",
        5:"자히르",
        6:"나딘",
        7:"현우",
        8:"하트",
        9:"아이솔",
        10:"리 다이린",
        11:"유키",
        12:"혜진",
        13:"쇼우",
        14:"키아라",
        15:"시셀라",
        16:"실비아",
        17:"아드리아나",
        18:"쇼이치",
        19:"엠마",
        20:"레녹스",
        21:"로지",
        22:"루크",
        23:"캐시",
        24:"아델라",
        25:"버니스",
        26:"바바라",
        27:"알렉스",
        28:"수아",
        29:"레온",
        30:"일레븐",
        31:"리오",
        32:"윌리엄",
        33:"니키",
        34:"나타폰",
        35:"얀",
        36:"이바",
        37:"다니엘",
        38:"제니",
        39:"카밀로",
        40:"클로에",
        41:"요한",
        42:"비앙카",
        43:"셀린",
        44:"에키온",
        45:"마이",
        46:"에이든",
        47:"라우라",
        48:"띠아",
        49:"펠릭스",
        50:"엘레나",
        51:"프리야",
        52:"아디나",
        53:"마커스",
        54:"칼라",
        55:"에스텔",
        56:"피올로",
        57:"마르티나",
        58:"헤이즈",
        59:"아이작",
        60:"타지아",
        61:"이렘",
        62:"테오도르",
        63:"이안",
        64:"바냐",
        65:"데비&마를렌",
        66:"아르다",
        67:"아비게일"
    }

weapon_names_dict = \
    {
        1:"글러브",
        2:"톤파",
        3:"방망이",
        4:"채찍",
        5:"투척",
        6:"암기",
        7:"활",
        8:"석궁",
        9:"권총",
        10:"돌격소총",
        11:"저격총",
        13:"망치",
        14:"도끼",
        15:"단검",
        16:"양손검",
        17:"폴암",
        18:"쌍검",
        19:"창",
        20:"쌍절곤",
        21:"레이피어",
        22:"기타",
        23:"카메라",
        24:"아르카나",
        25:"VF의수"
    }


# ----------------- 프로그램용 함수들 ----------------------

# # 유저 입력 대기하고, 장기간 대기시 봇 종료
# async def wait_for_user_content(ctx):
#     timeout = 10
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
async def get_livestats(day):
    global mainstats_addr, livestats_addr

    stats_url = mainstats_addr + livestats_addr + day

    response = requests.get(stats_url)
    tries = 0
    MAX_TRY = 5
    WAIT_SECOND = 3
    while response.status_code != 200 and tries <= MAX_TRY:
        response = requests.get(stats_url)
        tries += 1
        await asyncio.sleep(WAIT_SECOND)  # Wait for some seconds so that API can handle something

    if tries > MAX_TRY:
        return []   # Means the API is struggling and can't fetch any data

    livestats_json = response.json()
    livestats_rawdata = livestats_json.get("statistics")

    processed_data = []
    for row in livestats_rawdata:
        subject_name = character_names_dict[row.get("characterId")]
        subject_weapon = weapon_names_dict[row.get("weaponTypeId")]

        name = subject_weapon + " " + subject_name
        pickrate = row.get("pickRate")
        winrate = row.get("winRate")

        pick_count = row.get("pickCount")
        if pick_count != 0:
            topthree = row.get("top3Count") / pick_count
            processed_data.append([name, pickrate, winrate, topthree])

    return processed_data


async def fetch_all_livedata():
    global livestats3_list, livestats7_list, livestats10_list, livestats_addr

    livestats3_list = await get_livestats("3")
    livestats7_list = await get_livestats("7")
    livestats10_list = await get_livestats("10")


async def sort_livedata(param, datalist, comms_list):

    if param == comms_list[LIVE_INDEX.PICKRATE]:
        datalist.sort(key=lambda x: x[LIVE_INDEX.PICKRATE], reverse=True)
    elif param == comms_list[LIVE_INDEX.WINRATE]:
        datalist.sort(key=lambda x: x[LIVE_INDEX.WINRATE], reverse=True)
    elif param == comms_list[LIVE_INDEX.TOPTHREE]:
        datalist.sort(key=lambda x: x[LIVE_INDEX.TOPTHREE], reverse=True)

    return datalist


# 특정 픽률보다 낮은 실험체는 통계에서 제외 (너무 적어서 무의미한 통계라고 판단 (주관적))
# PICKRATE_EXCLSUION 보다 낮은 픽률은 모두 제외됨.
async def exclude_lowpick(datalist):
    ex_datalist = [x for x in deepcopy(datalist) if x[LIVE_INDEX.PICKRATE] >= PICKRATE_EXCLUSION]
    return ex_datalist


async def print_rankbased(ctx, sorted_list, start, end, is_pick_excluded):
    if is_pick_excluded:
        output_list = await exclude_lowpick(sorted_list)
    else:
        output_list = sorted_list   # To prevent overwriting the global list

    for i in range(len(output_list)):
        output_list[i][LIVE_INDEX.PICKRATE] = str(round(output_list[i][LIVE_INDEX.PICKRATE] * 100, 1)) + '%'
        output_list[i][LIVE_INDEX.WINRATE] = str(round(output_list[i][LIVE_INDEX.WINRATE] * 100, 1)) + '%'
        output_list[i][LIVE_INDEX.TOPTHREE] = str(round(output_list[i][LIVE_INDEX.TOPTHREE] * 100, 1)) + '%'

    output = "```" + tabulate.tabulate(output_list[start:end+1], headers=["실험체", "픽률", "승률", "순방"], tablefmt='simple', stralign='left', showindex=range(start+1,end+2)) + "```"
    if is_pick_excluded:
        output += f"**참고** 픽률 {int(PICKRATE_EXCLUSION * 100)}% 미만의 실험체는 제외한 결과입니다."
    await ctx.send(output)

# ----------------- 프로그램용 함수들 (끝) ----------------------


# ----------------- 봇 명령어 ------------------------
@bot.event
async def on_ready():
    print(f'Logged in as {bot.user} (ID: {bot.user.id})')
    print('------')

    print("Fetching Live Statistics...")

    # Gets all data and remembers the data when bot starts (for fast processing)
    await asyncio.gather(fetch_all_livedata())  # waits to finish all live stats fetch operations

    print("FINISHED")
    print("------")


@get_livestats.before_loop
async def before_my_task():
    await bot.wait_until_ready()  # wait until the bot logs in


# Helper function to check valid inputs
async def check_inputs(userparams, *comms_list):
    """
    :condition length of userparams and comms_list must match.
    :param userparams: input from the user (Type: List)
    :param comms_list: list of commands that will validate the inputs (Type: List)
    """
    if len(userparams) < 1:
        return False
    else:
        for i in range(len(userparams)):
            if userparams[i] not in comms_list[i]:
                return False

    return True     # if the inputs are valid, the code will reach here


@bot.command()
async def 명령어(ctx):
    all_commands_string = f"가능한 명령어\n{comms_live_string}\n{comms_personal_string}"
    await ctx.send(all_commands_string)
    return


@bot.command()
async def 실시간통계(ctx, *param):
    global livestats3_list, livestats7_list, livestats10_list

    if not check_inputs(param, comms_live_list, comms_day_list, comms_live_param_list):
        ctx.send(notfound_live_string)
        return

    # TODO: Reject Unavailable Commands. (Currently, it just checks the number of params)
    if len(param) == 1:   # 날짜 컷, 픽률제외 입력 안했을경우 자동으로 3일 기반 데이터 사용 및 픽률 제외
        sorted_data = await sort_livedata(param[0], livestats3_list, comms_live_list)
        await print_rankbased(ctx, sorted_data, 0, 9, True)
        return

    # TODO: Accept 'Day' commands (e.g. 실시간통계 순방 7)
    elif len(param) == 2:   # 날짜 컷 입력 안했을경우 자동으로 3일 기반 데이터 사용 (즉, default = 3)
        sorted_data = await sort_livedata(param[0], livestats3_list, comms_live_list)
        return
    # TODO: Add Full Stats search without Pick Rate Exclusion ---

    else:
        return


# ----------------- 봇 명령어 (끝) ------------------------

### ------------ Main ------------ ###
bot.run(os.getenv("BOT_TOKEN"))
