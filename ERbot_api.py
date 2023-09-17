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
import wcwidth
import requests
import asyncio
from copy import deepcopy
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By


intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='!', intents=intents)
client = discord.Client(intents=intents)
load_dotenv('config.env')

chrome_options = Options()
chrome_options.add_argument('--no-sandbox')
chrome_options.add_argument('--disable-dev-shm-usage')
chrome_options.add_argument('headless')
DRIVER = webdriver.Chrome(options=chrome_options)
DRIVER.implicitly_wait(10)

# ---------------- 명령어 및 기본 변수 정리 ---------------------------

# 새 명령어 추가시 이 리스트들도 수정필수
comms_live_list = ["이름", "픽률", "승률", "순방"]    # The index can be referred from LIVE_INDEX enum class (and must keep this order)
comms_day_list = ['3', '7', '10']
comms_live_param_list = ["제외", "전체"]

comms_live_string =    f"명령어:" \
                       f"\n 실시간통계 {comms_live_list} OR" \
                       f"\n 실시간통계 {comms_live_list} {comms_live_param_list} OR" \
                       f"\n 실시간통계 {comms_live_list} {comms_day_list} OR" \
                       f"\n 실시간통계 {comms_live_list} {comms_day_list} {comms_live_param_list}"

comms_personal_string = "개인통계 닉네임"

notfound_live_string = f"명령어 확인 불가\n" \
                       f"{comms_live_string}"

notfound_personal_string = f"명령어 확인 불가\n명령어: {comms_personal_string}"

dakgg_addr = "https://er.dakgg.io/v1/"  # Main api address for getting statistics (DAK.GG API)
dakgg_livestats_addr = "statistics/realtime?teamMode=SQUAD&type=REALTIME_OVER_DIAMOND&period=DAYS"
dakgg_personal_addr = "players/"

officialapi_addr = "https://open-api.bser.io/v1/"   # Official api address
officialapi_headers = {'x-api-key': os.getenv('API_KEY')}  # API Key header


# 이름, 픽률, 승률, 순방 순서로 정리됨
# Only used to display total statistics (e.g. TOP10 subjects)
livestats3_list = []
livestats7_list = []
livestats10_list = []

# Used to quickly access data
subjects_data_dict = {}

# Used to navigate user to the next page (e.g. Top 11 - 20)
last_livestats = []
last_livestats_startindex = -1
last_isexcluded = False

ROWS_PER_PAGE = 10

PICKRATE_EXCLUSION = 0.01

CURRENT_SEASON = "SEASON_10"      # Official season 1 id


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


class SUBJECT_DATA_INDEX(IntEnum):
    NAME = 0
    WINRATE = 1
    PICKRATE = 2
    AVG_PLACEMENT = 3
    AVG_DAMAGE = 4
    AVG_KILLS = 5



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
        12:"None",
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

@tasks.loop(minutes=30)
async def get_livestats(day):
    global dakgg_addr, dakgg_livestats_addr, subjects_data_dict

    stats_url = dakgg_addr + dakgg_livestats_addr + day

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

        # Stores subject specific data in separated dictionary
        cid = row.get("characterId")
        avg_placement = round(row.get("avgPlacement"), 1)
        avg_damage = int(round(row.get("avgDamageToPlayer")))
        avg_kills = round(row.get("avgPlayerKill"), 1)

        if not subjects_data_dict.get(cid):
            subjects_data_dict[cid] = [subject_name, winrate, pickrate, avg_placement, avg_damage, avg_kills]
        else:
            # Only stores the major weapon type data for characters
            if pickrate > subjects_data_dict[cid][SUBJECT_DATA_INDEX.PICKRATE]:
                subjects_data_dict[cid] = [subject_name, winrate, pickrate, avg_placement, avg_damage, avg_kills]

    return processed_data


async def fetch_all_livedata():
    global livestats3_list, livestats7_list, livestats10_list, dakgg_livestats_addr

    livestats3_list = await get_livestats("3")
    livestats7_list = await get_livestats("7")
    livestats10_list = await get_livestats("10")


async def sort_livedata(param, datalist):
    global comms_live_list

    if param == comms_live_list[LIVE_INDEX.PICKRATE]:
        datalist.sort(key=lambda x: x[LIVE_INDEX.PICKRATE], reverse=True)
    elif param == comms_live_list[LIVE_INDEX.WINRATE]:
        datalist.sort(key=lambda x: x[LIVE_INDEX.WINRATE], reverse=True)
    elif param == comms_live_list[LIVE_INDEX.TOPTHREE]:
        datalist.sort(key=lambda x: x[LIVE_INDEX.TOPTHREE], reverse=True)

    return datalist


# 특정 픽률보다 낮은 실험체는 통계에서 제외 (너무 적어서 무의미한 통계라고 판단 (주관적))
# PICKRATE_EXCLSUION 보다 낮은 픽률은 모두 제외됨.
async def exclude_lowpick(datalist):
    ex_datalist = [x for x in deepcopy(datalist) if x[LIVE_INDEX.PICKRATE] >= PICKRATE_EXCLUSION]
    return ex_datalist


async def beautify_output(output_list, start, end, is_pick_excluded):
    output = "```" + tabulate.tabulate(output_list[start:end], headers=["실험체", "픽률", "승률", "순방"], tablefmt='simple', rowalign='left', showindex=range(start+1, end+1)) + "```"
    if is_pick_excluded:
        output += f"**참고** 픽률 {int(PICKRATE_EXCLUSION * 100)}% 미만의 실험체는 제외한 결과입니다."

    return output


async def print_rankbased(ctx, sorted_list, start, is_pick_excluded):
    global last_livestats, last_livestats_startindex, last_isexcluded, ROWS_PER_PAGE

    if is_pick_excluded:
        output_list = await exclude_lowpick(sorted_list)
    else:
        output_list = deepcopy(sorted_list)   # To prevent overwriting the global list

    for i in range(len(output_list)):
        output_list[i][LIVE_INDEX.PICKRATE] = str(round(output_list[i][LIVE_INDEX.PICKRATE] * 100, 1)) + '%'
        output_list[i][LIVE_INDEX.WINRATE] = str(round(output_list[i][LIVE_INDEX.WINRATE] * 100, 1)) + '%'
        output_list[i][LIVE_INDEX.TOPTHREE] = str(round(output_list[i][LIVE_INDEX.TOPTHREE] * 100, 1)) + '%'

    output = await beautify_output(output_list, start, start+ROWS_PER_PAGE, is_pick_excluded)
    await ctx.send(output)

    # Remembers the last list and index shown to the user for future use
    last_livestats = output_list
    last_livestats_startindex = start
    last_isexcluded = is_pick_excluded


async def select_livestats_day(day):
    global livestats3_list, livestats7_list, livestats10_list

    chosen_list = livestats3_list
    if day == '7':
        chosen_list = livestats7_list
    elif day == '10':
        chosen_list = livestats10_list

    return chosen_list


async def do_pick_exclusion(pickinput):
    global comms_live_param_list

    if pickinput == comms_live_param_list[LIVE_PARAM_INDEX.EXCLUDE]:
        return True
    elif pickinput == comms_live_param_list[LIVE_PARAM_INDEX.INCLUDE]:
        return False

    raise Exception("Invalid Input for pick exclusion (do_pick_exclusion)")


async def updown_str(num):
    if num > 0:
        return str(num) + " ▲"
    if num < 0:
        return str(num) + " ▽"
    else:
        return str(num) + " ="


# async def get_tier(mmr, rank):
#     if rank <= 200:
#         return "이터니티"
#     elif rank <= 700:
#         return "데미갓"
#
#     tier = "아이언"
#     if mmr >= 6000:
#         tier = "미스릴"
#     elif mmr >= 5000:
#         tier = "다이아몬드"
#     elif mmr >= 4000:
#         tier = "플레티넘"
#     elif mmr >= 3000:
#         tier = "골드"
#     elif mmr >= 2000:
#         tier = "실버"
#     elif mmr >= 1000:
#         tier = "브론즈"
#
#     division = "4"
#     division_mmr = mmr % 1000
#     if division_mmr >= 750:
#         division = "3"
#     elif division_mmr >= 500:
#         division = "2"
#     elif division_mmr >= 250:
#         division = "1"
#
#     return tier + " " + division

# ----------------- 프로그램용 함수들 (끝) ----------------------


# ----------------- 봇 명령어 관련 ------------------------
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


# ----------------- 봇 명령어 ------------------------

@bot.command()
async def 명령어(ctx):
    all_commands_string = f"가능한 명령어\n{comms_live_string}\n{comms_personal_string}"
    await ctx.send(all_commands_string)
    return


@bot.command()
async def 다음(ctx):
    global last_livestats, last_livestats_startindex, last_isexcluded, ROWS_PER_PAGE

    if last_livestats_startindex + ROWS_PER_PAGE > len(last_livestats):
        await ctx.send("더이상 정보가 없습니다.")
        return

    last_livestats_startindex += ROWS_PER_PAGE
    end = last_livestats_startindex + ROWS_PER_PAGE
    if end >= len(last_livestats):
        end = len(last_livestats)

    output = await beautify_output(last_livestats, last_livestats_startindex, end, last_isexcluded)
    await ctx.send(output)


@bot.command()
async def 실시간통계(ctx, *param):
    global livestats3_list, livestats7_list, livestats10_list, comms_live_list, comms_day_list, comms_live_param_list

    # Input must be validated because the workings of the below codes assume that the inputs are all valid
    if not await check_inputs(param, comms_live_list, comms_day_list, comms_live_param_list) and \
            not await check_inputs(param, comms_live_list, comms_live_param_list):
        await ctx.send(notfound_live_string)
        return

    if len(param) == 1:   # 날짜 컷, 픽률제외 입력 안했을경우 자동으로 3일 기반 데이터 사용 및 픽률 제외
        sorted_data = await sort_livedata(param[0], livestats3_list)
        await print_rankbased(ctx, sorted_data, 0, True)
        return

    elif len(param) == 2:   # 날짜 컷 입력 안했을경우 자동으로 3일 기반 데이터 사용 (즉, default = 3)
        # If the user inputs 'day' as a parameter
        if param[1] in comms_day_list:
            chosen_list = await select_livestats_day(param[1])
            is_pick_excluded = True
        # else if the user inputs 'pick_exclusion' as a parameter
        else:
            chosen_list = livestats3_list
            is_pick_excluded = await do_pick_exclusion(param[1])

        sorted_data = await sort_livedata(param[0], chosen_list)
        await print_rankbased(ctx, sorted_data, 0, is_pick_excluded)
        return

    elif len(param) == 3:
        is_pick_excluded = await do_pick_exclusion(param[2])
        chosen_list = await select_livestats_day(param[1])
        sorted_data = await sort_livedata(param[0], chosen_list)
        await print_rankbased(ctx, sorted_data, 0, is_pick_excluded)

    else:
        return


@bot.command()
async def 팀원(ctx):
    global CURRENT_SEASON, DRIVER

    teammates = []
    await ctx.send("팀원들의 닉네임을 입력받습니다. 한명씩 입력해주세요 (쓰기힘들거나 비우고싶은경우 'ㄴ' 입력)")

    def check(m):
        return m.channel == ctx.channel and m.author == ctx.author

    msg = await bot.wait_for("message", check=check, timeout=15)
    if (msg.content != 'ㄴ'):
        teammates.append(msg.content)
    msg = await bot.wait_for("message", check=check, timeout=15)
    if (msg.content != 'ㄴ'):
        teammates.append(msg.content)

    for nickname in teammates:
        user_addr = dakgg_addr + dakgg_personal_addr + nickname + f"?teamMode=SQUAD&season={CURRENT_SEASON}"
        asd = requests.get(user_addr).text
        if asd == '{}':
            await ctx.send(f"입력하신 {nickname} 은 존재하지않습니다. 다시 확인해주세요.")
            continue

        DRIVER.get("https://dak.gg/er/players/" + nickname + f"?teamMode=SQUAD&season={CURRENT_SEASON}")
        update_button = DRIVER.find_element(By.XPATH, "//*[@id=\"content-container\"]/header/div/div[2]/div[2]/button[1]")
        update_button.click()
        await asyncio.sleep(1)

        userstats_json = requests.get(user_addr).json()
        user_tier = userstats_json.get("teamModeSummary")[2].get("playerTier").get("name")
        user_lp = userstats_json.get("teamModeSummary")[2].get("playerTier").get("lp")

        mostplayed_chars_string = f"\n**안내**:[]안의 값은 전체 실험체 평균값과 비교한 결과입니다.\n"
        mostplayed_charstats = userstats_json.get("characterSummary")
        max_range = 3 if len(mostplayed_charstats) >= 3 else len(mostplayed_charstats)
        for i in range(max_range):
            mostplayed_stats = mostplayed_charstats[i]
            mostplayed_char_id = int(mostplayed_stats.get("characterId"))
            mostplayed_char_name = character_names_dict[mostplayed_char_id]
            mostplayed_pick_num = mostplayed_stats.get("pickCount")
            mostplayed_win_rate = mostplayed_stats.get("winRate")
            mostplayed_avg_place = mostplayed_stats.get("avgPlacement")
            mostplayed_avg_damage = mostplayed_stats.get("avgDamageToPlayer")
            mostplayed_avg_kills = mostplayed_stats.get("avgPlayerKill")

            subject_livestat = subjects_data_dict[mostplayed_char_id]
            diff_win_rate = round((mostplayed_win_rate - subject_livestat[SUBJECT_DATA_INDEX.WINRATE]) * 100, 1)  # *100 = converts to percentile
            diff_avg_place = round(mostplayed_avg_place - subject_livestat[SUBJECT_DATA_INDEX.AVG_PLACEMENT], 1)
            diff_avg_damage = round(mostplayed_avg_damage - subject_livestat[SUBJECT_DATA_INDEX.AVG_DAMAGE])
            diff_avg_kills = round(mostplayed_avg_kills - subject_livestat[SUBJECT_DATA_INDEX.AVG_KILLS], 1)

            display_win_rate = round(mostplayed_win_rate * 100, 1)
            display_avg_place = round(mostplayed_avg_place, 1)
            display_avg_damage = round(mostplayed_avg_damage)
            display_avg_kills = round(mostplayed_avg_kills, 1)

            mostplayed_chars_string += f"{i+1}. **{mostplayed_char_name}** {mostplayed_pick_num}게임\n" \
                                       f"--- 승률:{display_win_rate}% *[{await updown_str(diff_win_rate)}]* | " \
                                       f"--- 평균 순위:{display_avg_place} *[{await updown_str(diff_avg_place)}]* | " \
                                       f"--- 평균 데미지:{display_avg_damage} *[{await updown_str(diff_avg_damage)}]* | " \
                                       f"--- 평균 킬:{display_avg_kills} *[{await updown_str(diff_avg_kills)}]*\n"

        await ctx.send(f"\n--------------------------------------------------------------------------------------------\n"
                       f"**{nickname}**\n"
                       f"**{user_tier} - {user_lp} 포인트**\n" +
                       mostplayed_chars_string +
                       f"\n--------------------------------------------------------------------------------------------\n")


# ----------------- 봇 명령어 (끝) ------------------------

### ------------ Main ------------ ###
bot.run(os.getenv("BOT_TOKEN"))
