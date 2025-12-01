import discord
from discord.ext import commands
import asyncio

intents = discord.Intents.all()
bot = commands.Bot(command_prefix="!", intents=intents)

# ============================
# 🔥 티어 정보
# ============================
TIER_ORDER = {
    "레디언트": 1,
    "불멸": 2,
    "초월자": 3,
    "다이아몬드": 4,
    "플래티넘": 5,
    "골드": 6,
    "실버": 7,
    "브론즈": 8,
    "아이언": 9,
    "언랭": 10
}

TIER_EMOJI = {
    "언랭": "<:unranked:1438766662018142238>",
    "아이언": "<:iron:1438367319901474848>",
    "브론즈": "<:bronze:1438367373278187520>",
    "실버": "<:silver:1438367415544184923>",
    "골드": "<:gold:1438367459060224113>",
    "플래티넘": "<:plat:1438367501774753832>",
    "다이아몬드": "<:dia:1438367537875128361>",
    "초월자": "<:asc:1438367584746606642>",
    "불멸": "<:imm:1438367627910185091>",
    "레디언트": "<:rad:1438367673380634735>"
}

LOBBY_CHANNEL_ID = 1438798318862860391

# ============================
# 🔥 모집 데이터
# ============================
recruit_data = {
    "message": None,
    "players": [],
    "owner": None,
    "timeout_task": None
}

# ============================
# 📌 티어 정렬 + 임베드 생성
# ============================
def build_embed():
    embed = discord.Embed(
        title="VALORANT 내전 요원 모집!",
        description="현재 참여중인 요원:\n",
        color=discord.Color.red()
    )

    players_sorted = sorted(recruit_data["players"], key=lambda x: TIER_ORDER[x["tier"]])

    if len(players_sorted) == 0:
        embed.description += "아직 참가한 요원이 없습니다.\n"
    else:
        for idx, p in enumerate(players_sorted, start=1):
            emoji = TIER_EMOJI[p["tier"]]
            embed.description += f"{idx}. {emoji} <@{p['id']}> ({p['tier']})\n"

    remaining = 10 - len(players_sorted)
    embed.add_field(name="남은 인원", value=f"{remaining}명", inline=False)

    embed.set_footer(
        text="⚠️ 기재되어 있는 티어는 현티어가 아닌 최고 티어 기준입니다.\n⛔ 1시간 동안 인원 미달 시 자동 종료됩니다."
    )
    return embed

# ============================
# 🔥 버튼 UI
# ============================
class RecruitButtons(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="⭕ 참가하기", style=discord.ButtonStyle.success)
    async def join(self, interaction: discord.Interaction, button: discord.ui.Button):
        user = interaction.user

        # 이미 참가했는지 확인
        for p in recruit_data["players"]:
            if p["id"] == user.id:
                return await interaction.response.send_message("이미 참가 중입니다!", ephemeral=True)

        # 티어 탐색
        user_roles = [r.name for r in user.roles]
        tier = "언랭"
        for t in TIER_ORDER.keys():
            if t in user_roles:
                tier = t
                break

        recruit_data["players"].append({"id": user.id, "tier": tier})

        await recruit_data["message"].edit(embed=build_embed(), view=self)
        await interaction.response.send_message("참가 완료!", ephemeral=True)

        # ★ 10명 찼으면 자동 종료 실행
        if len(recruit_data["players"]) == 10:
            await send_complete_message(interaction.channel)
            await auto_close_now(interaction.channel)

    @discord.ui.button(label="❌ 취소하기", style=discord.ButtonStyle.danger)
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
        user = interaction.user

        before = len(recruit_data["players"])
        recruit_data["players"] = [p for p in recruit_data["players"] if p["id"] != user.id]

        if before == len(recruit_data["players"]):
            return await interaction.response.send_message("참가 중이 아닙니다!", ephemeral=True)

        await recruit_data["message"].edit(embed=build_embed(), view=self)
        await interaction.response.send_message("취소 처리됨!", ephemeral=True)

    @discord.ui.button(label="🔒 모집 종료", style=discord.ButtonStyle.secondary)
    async def end(self, interaction: discord.Interaction, button: discord.ui.Button):

        # 권한 체크 (모집자 + 관리자만 가능)
        if not (
            interaction.user.id == recruit_data["owner"]
            or interaction.user.guild_permissions.manage_channels
        ):
            return await interaction.response.send_message(
                "❌ 이 버튼은 모집 생성자 또는 관리자만 사용할 수 있습니다.", ephemeral=True)

        await auto_close_now(interaction.channel)
        await interaction.response.send_message("📢 모집이 종료되었습니다.", ephemeral=True)


# ============================
# 🔥 자동 종료 함수 (1시간)
# ============================
async def auto_close():
    await asyncio.sleep(3600)

    if len(recruit_data["players"]) < 10:
        channel = recruit_data["message"].channel
        await auto_close_now(channel)

# ============================
# 🔥 즉시 종료 함수 (10명 찼을 때 사용)
# ============================
async def auto_close_now(channel):
    # 버튼 비활성화
    view = RecruitButtons()
    for child in view.children:
        child.disabled = True

    if recruit_data["message"]:
        await recruit_data["message"].edit(view=view)

    # 데이터 초기화
    recruit_data["players"].clear()
    recruit_data["owner"] = None

    await channel.send("🔒 10명 모집 완료되어 자동 종료되었습니다.")


# ============================
# 🔥 10명 완료 메시지
# ============================
async def send_complete_message(channel):
    mentions = " ".join([f"<@{p['id']}>" for p in recruit_data["players"]])

    await channel.send(
        f"{mentions}\n🚩 요원이 10명 모집되었습니다! 로비에서 준비 해주세요!\n➡️ <#{LOBBY_CHANNEL_ID}>"
    )


# ============================
# 🟩 명령어: 발로내전
# ============================
@bot.command()
async def 발로내전(ctx):
    embed = build_embed()
    view = RecruitButtons()

    message = await ctx.send(embed=embed, view=view)
    recruit_data["message"] = message
    recruit_data["owner"] = ctx.author.id

    if recruit_data["timeout_task"]:
        recruit_data["timeout_task"].cancel()

    recruit_data["timeout_task"] = asyncio.create_task(auto_close())

# ==============================
# 🔵⚔️ 자동 팀 배정 기능 (수동 실행)
# ==============================

@bot.command()
async def 팀배정(ctx):
    """티어 밸런스 기반 5:5 자동 팀 배정"""
    players = recruit_data["players"]

    if len(players) != 10:
        return await ctx.send("❌ 팀 배정은 **10명이 모집된 이후** 사용할 수 있습니다.")

    # 티어 높은 순 정렬
    sorted_players = sorted(players, key=lambda x: TIER_ORDER[x['tier']])

    attack_team = []   # 🔵 공격팀
    defense_team = []  # 🔴 수비팀
    atk_score = 0
    def_score = 0

    # 자동 밸런스 배정 알고리즘
    for p in sorted_players:
        tier_value = TIER_ORDER[p['tier']]
        if atk_score <= def_score:
            attack_team.append(p)
            atk_score += tier_value
        else:
            defense_team.append(p)
            def_score += tier_value

    # 평균 티어 계산
    def avg_tier(team):
        if not team:
            return "N/A"
        avg = sum(TIER_ORDER[p['tier']] for p in team) / len(team)
        # 가장 가까운 티어 이름 찾기
        closest = min(TIER_ORDER.keys(), key=lambda t: abs(TIER_ORDER[t] - avg))
        return closest

    atk_avg = avg_tier(attack_team)
    def_avg = avg_tier(defense_team)

    # 결과 메시지 작성
    msg = "⚔️ **자동 팀 배정 결과**\n\n"

    msg += "🔵 **공격팀 (Attack Team)**\n"
    for p in attack_team:
        msg += f"- {TIER_EMOJI[p['tier']]} <@{p['id']}> ({p['tier']})\n"
    msg += f"➡️ **평균 티어: {atk_avg}**\n\n"

    msg += "🔴 **수비팀 (Defense Team)**\n"
    for p in defense_team:
        msg += f"- {TIER_EMOJI[p['tier']]} <@{p['id']}> ({p['tier']})\n"
    msg += f"➡️ **평균 티어: {def_avg}**\n\n"

    # 밸런스 안내
    diff = abs(atk_score - def_score)
    if diff <= 1:
        msg += "✅ **매우 균형 잡힌 매치입니다!**"
    elif diff <= 3:
        msg += "⚠️ **팀 간 티어가 약간 차이납니다.**"
    else:
        msg += "❗ **티어 차이가 크므로 팀 조정을 권장합니다.**"

    await ctx.send(msg)


# ==============================
# 🔥 테스트용 가짜 플레이어 자동 생성
# ==============================
@bot.command()
async def 가짜10명(ctx):
    """테스트용 가짜 10명 자동 생성"""

    fake_players = [
        {"id": 1, "tier": "레디언트"},
        {"id": 2, "tier": "불멸"},
        {"id": 3, "tier": "초월자"},
        {"id": 4, "tier": "다이아몬드"},
        {"id": 5, "tier": "플래티넘"},
        {"id": 6, "tier": "골드"},
        {"id": 7, "tier": "실버"},
        {"id": 8, "tier": "브론즈"},
        {"id": 9, "tier": "아이언"},
        {"id": 10, "tier": "언랭"},
    ]

    recruit_data["players"] = fake_players
    recruit_data["owner"] = ctx.author.id  # 임시 값

    await ctx.send("🧪 **테스트용 가짜 10명 생성 완료!**\n이제 `!팀배정` 실행해서 테스트 하세요.")



# ==============================
# 🎲 경기맵 랜덤 뽑기 기능
# ==============================

VALORANT_MAPS = [
    "어센트",
    "바인드",
    "헤이븐",
    "스플릿",
    "로터스",
    "프랙처",
    "아이스박스",
    "펄",
    "선셋",
    "어비스",   # 추가됨
    "코로드"    # 추가됨
]

@bot.command()
async def 맵(ctx):
    """발로란트 경기맵 랜덤 선택"""
    import random
    selected = random.choice(VALORANT_MAPS)
    await ctx.send(f"🎯 **오늘의 랜덤 맵은… → `{selected}` 입니다!**")



# ============================
# 🟧 테스트: 가짜 참가자 10명 채우기
# ============================
@bot.command()
async def 가짜테스트(ctx):
    if recruit_data["message"] is None:
        return await ctx.send("먼저 !발로내전 으로 모집글을 생성해주세요.")

    fake_players = [
        {"id": 1111, "tier": "레디언트"},
        {"id": 2222, "tier": "불멸"},
        {"id": 3333, "tier": "초월자"},
        {"id": 4444, "tier": "다이아몬드"},
        {"id": 5555, "tier": "플래티넘"},
        {"id": 6666, "tier": "골드"},
        {"id": 7777, "tier": "실버"},
        {"id": 8888, "tier": "브론즈"},
        {"id": 9999, "tier": "아이언"},
        {"id": 1010, "tier": "언랭"},
    ]

    recruit_data["players"] = fake_players
    recruit_data["players"].sort(key=lambda x: TIER_ORDER[x["tier"]])

    await recruit_data["message"].edit(embed=build_embed(), view=RecruitButtons())
    await send_complete_message(ctx.channel)
    await auto_close_now(ctx.channel)

    await ctx.send("🔥 테스트용 참가자 10명이 자동으로 채워졌습니다!")


# ============================
# 🔥 봇 실행
# ============================
import os
bot.run(os.getenv("TOKEN"))


