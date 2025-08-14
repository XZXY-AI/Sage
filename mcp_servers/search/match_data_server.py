# 1. 导入所有必要的库
from datetime import datetime, timedelta

import httpx
from mcp.server.fastmcp import FastMCP
from starlette.applications import Starlette
from starlette.routing import Mount
import uvicorn
import argparse
from typing import List, Dict, Any, Optional, Union
import traceback  # <-- 导入 traceback 模块用于打印详细错误

"""
你看一下，为了更好的分析赛事
你看还有哪里可以优化的,目的就是为了让使用者一句话可以得到一个赛事分析
"""

# 2. 初始化 MCP 框架 (不变)
mcp = FastMCP("Match Data Service")

# 3. 设置命令行参数 (不变)
parser = argparse.ArgumentParser(description='启动比赛数据 MCP Server')
args = parser.parse_args()


# ==============================================================================

# query_match_list_by_date 工具获取今天19点35，天津津门虎vs成都蓉城的内容，比赛状态现在是未开始， 我需要获取到这次的赛事id 不要使用其他mcp工具
# 请调用 query_match_list_by_date 工具获取今天19点35，天津津门虎vs成都蓉城的内容，比赛状态现在是未开始， 我需要获取到这次的赛事id
# 请调用 query_match_list_by_date 工具获取今天的足球比赛列表。然后，仅提取每场比赛的主队名称、客队名称、联赛名称和比赛，并以列表的形式呈现给我。
@mcp.tool()
async def query_match_list_by_date(
        match_type: str,
        date: Optional[str] = None,
        league_ids: Optional[str] = None,
        team_id: Optional[str] = None,
        status: Optional[str] = None
) -> Union[List[Dict[str, Any]], str]:
    """
    根据指定条件获取比赛列表。
    Fetches a list of matches based on specified criteria.

    Args:
        match_type (str): 体育类型，必需参数。1 代表足球, 2 代表篮球。
        date (Optional[str]): 查询日期，格式为 YYYY-MM-DD。
        league_ids (Optional[str]): 联赛ID，多个ID用逗号分隔。
        team_id (Optional[str]): 球队ID。
        status (Optional[str]): 比赛状态。1:未开始, 2:完场, 3:赛中, 4:其他。
    """
    params = {"match_type": "1"}
    endpoint = "http://ai-match.fengkuangtiyu.cn/api/v5/matches"
    if match_type:
        params["match_type"] = match_type
    if date:
        cleaned_date = date.replace(" ", "")
        params["date"] = cleaned_date
    if league_ids:
        params["league_ids"] = league_ids
    if team_id:
        params["team_id"] = team_id
    if status:
        params["status"] = status
    print(f"Executing get_match_list with params: {params}")
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(endpoint, params=params)
            response.raise_for_status()

            data = response.json()
            # Check if the API call was successful
            if data.get("code") == "0":
                # If successful, fulfill the promise by returning the LIST
                return data.get("data", [])
            else:
                # If the API returned an error, fulfill the promise by returning a STRING
                return f"API returned an error: {data.get('msg', 'Unknown error')}"

    except httpx.HTTPStatusError as e:
        return f"API request failed with status {e.response.status_code}: {e.response.text}"
    except Exception as e:
        print(f"--- DETAILED ERROR IN query_match_list_by_date ---")
        traceback.print_exc()
        return f"An unexpected error occurred in query_match_list_by_date: [Type: {type(e).__name__}] - [Details: {repr(e)}]"

# 获取比赛联赛排名和积分
# http://ai-match.fengkuangtiyu.cn/api/v5/matches/3558764/league_standings?match_type=1
@mcp.tool()
async def get_match_standings_by_id(
        match_id: str,
        match_type: Optional[str] = None
) -> Union[Dict[str, Any], str]:
    """
    根据比赛获取联赛排名和积分。
    Fetches league standings and points by match ID.

    Args:
        match_id (str): 比赛 (必需), 例如 '3558764'。
        match_type (Optional[str]): 体育类型, 1 代表足球, 2 代表篮球。

    Returns:
        Union[Dict[str, Any], str]: 成功时返回排名积分数据，失败时返回错误信息字符串。
    """
    endpoint = f"http://ai-match.fengkuangtiyu.cn/api/v5/matches/{match_id}/league_standings"

    # --- vvv 修改的部分 vvv ---
    # 即使 AI 没有提供 match_type，我们也默认设置为 '1'
    params = {"match_type": "1"}
    # 如果 AI 提供了，就使用 AI 提供的值覆盖默认值
    if match_type:
        params["match_type"] = match_type
    # --- ^^^ 修改的部分 ^^^ ---

    print(f"Executing get_league_standings for match_id: {match_id} with params: {params}")

    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(endpoint, params=params)
            response.raise_for_status()
            return response.json()
    except httpx.HTTPStatusError as e:
        return f"API request failed with status {e.response.status_code}: {e.response.text}"
    except Exception as e:
        import traceback
        print(f"--- DETAILED ERROR IN get_league_standings ---")
        traceback.print_exc()
        return f"An unexpected error occurred in get_league_standings: [Type: {type(e).__name__}] - [Details: {repr(e)}]"


# 比赛信息
# http://ai-match.fengkuangtiyu.cn/api/v5/matches/3558764/essentials?match_type=1
@mcp.tool()
async def get_match_details_by_id(
        match_id: str,
        match_type: Optional[str] = None
) -> Union[Dict[str, Any], str]:
    """
    根据比赛获取比赛的核心信息。
    Fetches the essential information for a match by its ID.

    Args:
        match_id (str): 比赛 (必需), 例如 '3558764'。
        match_type (Optional[str]): 体育类型, 1 代表足球, 2 代表篮球。

    Returns:
        Union[Dict[str, Any], str]: 成功时返回比赛信息数据，失败时返回错误信息字符串。
    """
    endpoint = f"http://ai-match.fengkuangtiyu.cn/api/v5/matches/{match_id}/essentials"

    # 即使 AI 没有提供 match_type，我们也默认设置为 '1'
    params = {"match_type": "1"}
    if match_type:
        params["match_type"] = match_type

    print(f"Executing get_match_essentials for match_id: {match_id} with params: {params}")

    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(endpoint, params=params)
            response.raise_for_status()
            return response.json()
    except httpx.HTTPStatusError as e:
        return f"API request failed with status {e.response.status_code}: {e.response.text}"
    except Exception as e:
        import traceback
        print(f"--- DETAILED ERROR IN get_match_essentials ---")
        traceback.print_exc()
        return f"An unexpected error occurred in get_match_essentials: [Type: {type(e).__name__}] - [Details: {repr(e)}]"
# 请调用 get_team_recent_performance_by_match_id 工具，参数为 match_id: "3566777"，总结一下这个比赛的双方近期战绩结果。
import re
# 辅助函数：计算单队近10场战绩
def calculate_team_recent_10_games(matches: List[Dict], team_key: str = None) -> str:
    """
    计算队伍近10场比赛的胜负平统计
    
    Args:
        matches: 比赛列表
        team_key: 队伍标识，用于区分主客队（如果需要）
    
    Returns:
        格式化的战绩字符串，如 '8Win2Lose0Draw'
    """
    if not matches or not isinstance(matches, list):
        return "0Win0Lose0Draw"
    
    # 只取前10场比赛
    recent_matches = matches[:10]
    
    wins = 0
    loses = 0
    draws = 0
    
    for match in recent_matches:
        if not isinstance(match, dict):
            continue
            
        result = match.get('result')
        # 处理不同的字段名：penalty_score 或 penaltyScore
        penalty_score = match.get('penalty_score') or match.get('penaltyScore', '')
        # 处理不同的字段名：is_home 或 isHome
        is_home = match.get('is_home') or match.get('isHome')
        
        print(f"DEBUG: 处理比赛 - date: {match.get('date')}, result: {result}, penalty_score: {penalty_score}, is_home: {is_home}")
        
        # 确保result和is_home都是整数类型
        try:
            result = int(result) if result is not None else None
        except (ValueError, TypeError):
            result = None
            
        try:
            is_home = int(is_home) if is_home is not None else None
        except (ValueError, TypeError):
            is_home = None
            
        print(f"DEBUG: 转换后 - result: {result}, is_home: {is_home}")
            
        if result == 3:  # 胜
            wins += 1
            print(f"DEBUG: result=3, 胜")
        elif result == 0:  # 负
            loses += 1
            print(f"DEBUG: result=0, 负")
        elif result == 1:  # 需要进一步判断
            print(f"DEBUG: result=1, 检查点球")
            if not penalty_score:  # 没有点球，则是平局
                draws += 1
                print(f"DEBUG: 无点球, 平局")
            else:
                print(f"DEBUG: 有点球: {penalty_score}")
                # 有点球，根据is_home和penalty_score判断胜负
                # penalty_score格式可能是 "4:2" 或类似格式
                split_pattern = r'[\-–—−]'
                score_parts = re.split(split_pattern, penalty_score)
                if len(score_parts) == 2:  # 确保分割后正好是两部分
                    try:
                        left_score = int(score_parts[0].strip())
                        right_score = int(score_parts[1].strip())

                        print(
                            f"DEBUG: 点球处理 - date: {match.get('date')}, is_home: {is_home}, penalty: {penalty_score}, left: {left_score}, right: {right_score}")

                        if is_home == 1:
                            if left_score > right_score:
                                wins += 1
                                print(f"DEBUG: 主队点球胜")
                            else:
                                loses += 1
                                print(f"DEBUG: 主队点球负")
                        elif is_home == 0:
                            if right_score > left_score:
                                wins += 1
                                print(f"DEBUG: 客队点球胜")
                            else:
                                loses += 1
                                print(f"DEBUG: 客队点球负")
                        else:
                            loses += 1
                            print(f"DEBUG: is_home值无效，计为负")

                    except (ValueError, AttributeError) as e:
                        print(f"DEBUG: 点球解析异常 - {e}，计为负")
                        loses += 1
                else:
                    print(f"DEBUG: 点球格式分割后部分不为2，计为负")
                    loses += 1
        # 其他result值默认不统计
    
    return f"{wins}Win{loses}Lose{draws}Draw"


# http://ai-match.fengkuangtiyu.cn/api/v5/matches/3558764/recent_forms?match_type=1
# 获取比赛近期战绩
# 调用工具根据比赛 3558764获取他的近期战绩
@mcp.tool()
async def get_team_recent_performance_by_match_id(
        match_id: str,
        match_type: Optional[str] = None
) -> Union[Dict[str, Any], str]:
    """
    根据比赛获取比赛双方的近期战绩。
    Fetches the recent forms of the teams involved in a match by its ID.

    Args:
        match_id (str): 比赛 (必需), 例如 '3558764'。
        match_type (Optional[str]): 体育类型, 1 代表足球, 2 代表篮球。

    Returns:
        Union[Dict[str, Any], str]: 成功时返回近期战绩数据，失败时返回错误信息字符串。
    """
    endpoint = f"http://ai-match.fengkuangtiyu.cn/api/v5/matches/{match_id}/recent_forms"

    params = {"match_type": "1"}
    if match_type:
        params["match_type"] = match_type

    print(f"Executing get_match_recent_forms for match_id: {match_id} with params: {params}")

    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(endpoint, params=params)
            response.raise_for_status()
            original_data = response.json()
            
            # 如果API返回成功，添加近10场战绩统计
            if isinstance(original_data, dict) and original_data.get("code") == "0":
                data = original_data.get("data", {})
                
                # 处理主队近期战绩 - API返回的home_team直接是数组
                if "home_team" in data and isinstance(data["home_team"], list):
                    home_matches = data["home_team"]
                    home_recent_10 = calculate_team_recent_10_games(home_matches)
                    # 将统计结果添加到data层级
                    data["home_team_recent10Games"] = home_recent_10
                
                # 处理客队近期战绩 - API返回的guest_team直接是数组  
                if "guest_team" in data and isinstance(data["guest_team"], list):
                    guest_matches = data["guest_team"]
                    guest_recent_10 = calculate_team_recent_10_games(guest_matches)
                    # 将统计结果添加到data层级
                    data["guest_team_recent10Games"] = guest_recent_10
                
                # 更新原始数据
                original_data["data"] = data
            
            return original_data
            
    except httpx.HTTPStatusError as e:
        return f"API request failed with status {e.response.status_code}: {e.response.text}"
    except Exception as e:
        import traceback
        print(f"--- DETAILED ERROR IN get_match_recent_forms ---")
        traceback.print_exc()
        return f"An unexpected error occurred in get_match_recent_forms: [Type: {type(e).__name__}] - [Details: {repr(e)}]"

# http://ai-match.fengkuangtiyu.cn/api/v5/matches/3558764/squad_details
# 阵容（仅足球）
@mcp.tool()
async def get_football_squad_by_match_id(
        match_id: str
) -> Union[Dict[str, Any], str]:
    """
    根据比赛获取比赛阵容（仅限足球）。
    Fetches the squad details for a football match by its ID.

    Args:
        match_id (str): 比赛 (必需), 例如 '3558764'。

    Returns:
        Union[Dict[str, Any], str]: 成功时返回阵容数据，失败时返回错误信息字符串。
    """
    endpoint = f"http://ai-match.fengkuangtiyu.cn/api/v5/matches/{match_id}/squad_details"

    print(f"Executing get_squad_details for match_id: {match_id}")

    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(endpoint)  # 这个接口不需要任何 query 参数
            response.raise_for_status()
            return response.json()
    except httpx.HTTPStatusError as e:
        return f"API request failed with status {e.response.status_code}: {e.response.text}"
    except Exception as e:
        import traceback
        print(f"--- DETAILED ERROR IN get_squad_details ---")
        traceback.print_exc()
        return f"An unexpected error occurred in get_squad_details: [Type: {type(e).__name__}] - [Details: {repr(e)}]"


def calculate_h2h_summary(matches: List[Dict], team1_name: str, team2_name: str) -> Dict[str, Any]:
    """
    计算历史交锋汇总信息
    
    Args:
        matches: 历史交锋比赛列表
        team1_name: 队伍1名称
        team2_name: 队伍2名称
    
    Returns:
        包含total_matches, team1, team2, draw的汇总信息
    """
    if not matches or not isinstance(matches, list):
        return {
            "total_matches": 0,
            "team1": f"{team1_name} 0胜",
            "team2": f"{team2_name} 0胜", 
            "draw": 0
        }
    
    team1_wins = 0
    team2_wins = 0
    draws = 0
    
    for match in matches:
        if not isinstance(match, dict):
            continue
            
        result = match.get('result') or match.get('match_result')
        penalty_score = match.get('penalty_score') or match.get('penaltyScore', '')
        is_home = match.get('is_home') or match.get('isHome')
        home_team_name = match.get('home_team_name') or match.get('home_team', '')
        guest_team_name = match.get('guest_team_name') or match.get('away_team', '')
        
        # 确保result和is_home都是整数类型
        try:
            result = int(result) if result is not None else None
        except (ValueError, TypeError):
            result = None
            
        try:
            is_home = int(is_home) if is_home is not None else None
        except (ValueError, TypeError):
            is_home = None
            
        # 判断当前比赛中team1是主队还是客队
        team1_is_home = (home_team_name == team1_name)
        
        if result == 3:  # 胜
            if team1_is_home:
                team1_wins += 1
            else:
                team2_wins += 1
        elif result == 0:  # 负
            if team1_is_home:
                team2_wins += 1
            else:
                team1_wins += 1
        elif result == 1:  # 需要进一步判断
            if not penalty_score:  # 没有点球，则是平局
                draws += 1
            else:
                # 有点球，根据is_home和penalty_score判断胜负
                split_pattern = r'[\-–—−]'
                score_parts = re.split(split_pattern, penalty_score)
                if len(score_parts) == 2:
                    try:
                        left_score = int(score_parts[0].strip())
                        right_score = int(score_parts[1].strip())

                        # 主队点球胜
                        if is_home == 1 and left_score > right_score:
                            if team1_is_home:
                                team1_wins += 1
                            else:
                                team2_wins += 1
                        # 主队点球负
                        elif is_home == 1 and left_score < right_score:
                            if team1_is_home:
                                team2_wins += 1
                            else:
                                team1_wins += 1
                        # 客队点球胜
                        elif is_home == 0 and right_score > left_score:
                            if team1_is_home:
                                team2_wins += 1
                            else:
                                team1_wins += 1
                        # 客队点球负
                        elif is_home == 0 and right_score < left_score:
                            if team1_is_home:
                                team1_wins += 1
                            else:
                                team2_wins += 1
                        else:
                            draws += 1  # 默认计为平局

                    except (ValueError, AttributeError):
                        draws += 1  # 解析失败计为平局
                else:
                    draws += 1  # 格式异常计为平局
    
    total_matches = len(matches)
    
    return {
        "total_matches": total_matches,
        "team1": f"{team1_name} {team1_wins}胜",
        "team2": f"{team2_name} {team2_wins}胜",
        "draw": draws
    }


#  请调用 get_head_to_head_history_by_match_id 工具，参数为 match_id: "3558764"
@mcp.tool()
async def get_head_to_head_history_by_match_id(
        match_id: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        match_type: Optional[str] = None
) -> Union[Dict[str, Any], str]:
    """
        根据比赛获取双方历史交锋信息。默认查询近三个月的数据。
        Fetches the head-to-head (h2h) match history by a given match ID. Defaults to the last 3 months.

        Args:
            match_id (str): 比赛 (必需), 例如 '3558764'。
            start_date (Optional[str]): 筛选此日期之后的交锋记录，格式 YYYY-MM-DD。
            end_date (Optional[str]): 筛选此日期之前的交锋记录，格式 YYYY-MM-DD。
            match_type (Optional[str]): 体育类型, 1 代表足球, 2 代表篮球。

        Returns:
            Union[Dict[str, Any], str]: 成功时返回历史交锋数据，失败时返回错误信息字符串。
        """
    endpoint = f"http://ai-match.fengkuangtiyu.cn/api/v5/matches/{match_id}/h2h"

    # --- vvv 新增的默认日期处理 vvv ---
    # 如果调用者没有提供结束日期，则默认为今天
    if not end_date:
        end_date = datetime.now().strftime('%Y-%m-%d')

    # 如果调用者没有提供开始日期，则默认为三个月前的今天
    if not start_date:
        three_years_ago = datetime.now() - timedelta(days=3 * 30)
        start_date = three_years_ago.strftime('%Y-%m-%d')
    # --- ^^^ 新增的默认日期处理 ^^^ ---

    params = {"match_type": "1", "start_date": start_date, "end_date": end_date}
    if match_type:
        params["match_type"] = match_type

    # 注意：我们直接将处理后的 start_date 和 end_date 放入 params，不再需要 if 判断

    print(f"Executing get_head_to_head_history_by_match_id for match_id: {match_id} with params: {params}")

    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(endpoint, params=params)
            response.raise_for_status()
            original_data = response.json()
            
            # 如果API返回成功，添加历史交锋汇总信息
            if isinstance(original_data, dict) and original_data.get("code") == "0":
                data = original_data.get("data", {})
                
                # 获取比赛信息以确定队伍名称（兼容不同的字段名）
                matches = data.get("matches", []) or data.get("recent_matches", [])
                if matches and len(matches) > 0:
                    # 从第一场比赛获取队伍名称（兼容不同的字段名）
                    first_match = matches[0]
                    team1_name = first_match.get('home_team_name') or first_match.get('home_team', 'Team1')
                    team2_name = first_match.get('guest_team_name') or first_match.get('away_team', 'Team2')
                    
                    # 计算汇总信息
                    summary = calculate_h2h_summary(matches, team1_name, team2_name)
                    
                    # 将汇总信息添加到data层级
                    data["summary"] = summary
                else:
                    # 如果没有比赛数据，提供默认汇总
                    data["summary"] = {
                        "total_matches": 0,
                        "team1": "Team1 0胜",
                        "team2": "Team2 0胜",
                        "draw": 0
                    }
                
                # 更新原始数据
                original_data["data"] = data
            
            return original_data
            
    except httpx.HTTPStatusError as e:
        return f"API request failed with status {e.response.status_code}: {e.response.text}"
    except Exception as e:
        import traceback
        print(f"--- DETAILED ERROR IN get_head_to_head_history_by_match_id ---")
        traceback.print_exc()
        return f"An unexpected error occurred in get_head_to_head_history_by_match_id: [Type: {type(e).__name__}] - [Details: {repr(e)}]"


@mcp.tool()
async def get_europe_odds_by_match_id(
        match_id: str,
        match_type: Optional[str] = None
) -> Union[Dict[str, Any], str]:
    """
    根据比赛获取欧赔赔率信息（胜平负）。
    Fetches the European win-draw-lose odds for a match by its ID.

    Args:
        match_id (str): 比赛 (必需), 例如 '3558764'。
        match_type (Optional[str]): 体育类型, 1 代表足球, 2 代表篮球。

    Returns:
        Union[Dict[str, Any], str]: 成功时返回赔率数据，失败时返回错误信息字符串。
    """
    endpoint = f"http://ai-match.fengkuangtiyu.cn/api/v5/matches/{match_id}/odds/win_draw_lose"

    params = {"match_type": "1"}
    if match_type:
        params["match_type"] = match_type

    print(f"Executing get_win_draw_lose_odds for match_id: {match_id} with params: {params}")

    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(endpoint, params=params)
            response.raise_for_status()
            return response.json()
    except httpx.HTTPStatusError as e:
        return f"API request failed with status {e.response.status_code}: {e.response.text}"
    except Exception as e:
        import traceback
        print(f"--- DETAILED ERROR IN get_win_draw_lose_odds ---")
        traceback.print_exc()
        return f"An unexpected error occurred in get_win_draw_lose_odds: [Type: {type(e).__name__}] - [Details: {repr(e)}]"


@mcp.tool()
async def get_asian_handicap_odds_by_match_id(
        match_id: str,
        match_type: Optional[str] = None
) -> Union[Dict[str, Any], str]:
    """
    根据比赛获取亚盘赔率信息。
    Fetches the Asian Handicap odds for a match by its ID.

    Args:
        match_id (str): 比赛 (必需), 例如 '3558764'。
        match_type (Optional[str]): 体育类型, 1 代表足球, 2 代表篮球。

    Returns:
        Union[Dict[str, Any], str]: 成功时返回赔率数据，失败时返回错误信息字符串。
    """
    endpoint = f"http://ai-match.fengkuangtiyu.cn/api/v5/matches/{match_id}/odds/asian_handicap"

    # --- 遵照你的要求，设置默认值 ---
    # 即使 AI 没有提供 match_type，我们也默认设置为 '1'
    params = {"match_type": "1"}
    # 如果 AI 提供了，就使用 AI 提供的值覆盖默认值
    if match_type:
        params["match_type"] = match_type
    # ---------------------------------

    print(f"Executing get_asian_handicap_odds for match_id: {match_id} with params: {params}")

    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(endpoint, params=params)
            response.raise_for_status()
            return response.json()
    except httpx.HTTPStatusError as e:
        return f"API request failed with status {e.response.status_code}: {e.response.text}"
    except Exception as e:
        import traceback
        print(f"--- DETAILED ERROR IN get_asian_handicap_odds ---")
        traceback.print_exc()
        return f"An unexpected error occurred in get_asian_handicap_odds: [Type: {type(e).__name__}] - [Details: {repr(e)}]"


@mcp.tool()
async def get_over_under_odds_by_match_id(
        match_id: str,
        match_type: Optional[str] = None
) -> Union[Dict[str, Any], str]:
    """
    根据比赛获取足球大小球或篮球总分赔率。
    Fetches the Goal Line (Over/Under) or Total Points odds for a match by its ID.

    Args:
        match_id (str): 比赛 (必需), 例如 '3558764'。
        match_type (Optional[str]): 体育类型, 1 代表足球, 2 代表篮球。

    Returns:
        Union[Dict[str, Any], str]: 成功时返回赔率数据，失败时返回错误信息字符串。
    """
    endpoint = f"http://ai-match.fengkuangtiyu.cn/api/v5/matches/{match_id}/odds/goal_line"

    # 遵照你的要求，设置默认值
    params = {"match_type": "1"}
    if match_type:
        params["match_type"] = match_type

    print(f"Executing get_goal_line_odds for match_id: {match_id} with params: {params}")

    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(endpoint, params=params)
            response.raise_for_status()
            return response.json()
    except httpx.HTTPStatusError as e:
        return f"API request failed with status {e.response.status_code}: {e.response.text}"
    except Exception as e:
        import traceback
        print(f"--- DETAILED ERROR IN get_goal_line_odds ---")
        traceback.print_exc()
        return f"An unexpected error occurred in get_goal_line_odds: [Type: {type(e).__name__}] - [Details: {repr(e)}]"


import asyncio  # 确保在文件顶部加上这个导入

"""
你是一名专业的足球比赛数据分析师。请对比赛 ID 为 3551089 的比赛进行一次全面的赛前分析。请利用你可用的工具获取所有必要信息，并基于这些信息，为我撰写一份包含基本面分析、近期战绩和交锋分析以及最终结论和比分预测的专业报告。
"""
@mcp.tool()
async def generate_full_match_report_by_id(match_id: str) -> Union[Dict[str, Any], str]:
    """
    根据比赛，生成一份包含所有可用信息的完整比赛分析报告。这是进行比赛分析的首选工具。
    它会自动处理ID有效性检查，如果ID无效，会直接返回错误信息。
    Generates a full pre-match analysis report with all available information for a given match ID. This is the preferred tool for match analysis.
    It automatically handles the validity check of the ID and returns an error message if the ID is invalid.

    Args:
        match_id (str): 比赛 (必需), 例如 '3558764'。

    Returns:
        Union[Dict[str, Any], str]: 一份包含多维度数据的完整报告，或明确的错误信息字符串。
    """
    print(f"🚀 [START] Generating full report for match_id: {match_id}")

    try:
        # --- 优化点 1: 优先进行核心数据检查 ---
        # 首先，只调用最核心的 get_match_details_by_id。
        # 这一步既能获取基础信息，又能充当“有效性检查”。
        # FIX: Switched to triple quotes for multi-line f-string.
        print(f"""step 1:
  - Checking match validity and fetching essential details...""")
        match_details = await get_match_details_by_id(match_id=match_id)

        # 如果返回的是字符串，说明API调用失败（例如404 Not Found），ID很可能无效。
        if isinstance(match_details, str):
            print(f"❌ [STOP] Invalid match_id or API error. Reason: {match_details}")
            # 直接将这个清晰的错误返回给 AI，AI 就能理解比赛有问题。
            return f"无法为比赛 '{match_id}' 生成报告，因为它可能是无效的或数据暂时不可用。错误详情: {match_details}"

        # 如果代码能走到这里，说明 ID 是有效的，match_details 是一个包含数据的 dict。
        # FIX: Switched to triple quotes for multi-line f-string.
        print(f"""✅ step 1:
  - Match ID is valid. Home: {match_details.get('data', {}).get('home_team_name')}, Away: {match_details.get('data', {}).get('away_team_name')}""")

        # --- 优化点 2: 并发获取剩余数据 ---
        # 现在我们确认ID有效，可以安全地并发获取所有其他辅助数据。
        # FIX: Switched to triple quotes for multi-line f-string.
        print(f"""step 2:
  - Concurrently fetching all other data points...""")
        other_data_tasks = [
            get_match_standings_by_id(match_id=match_id),
            get_team_recent_performance_by_match_id(match_id=match_id),
            get_head_to_head_history_by_match_id(match_id=match_id),
            get_football_squad_by_match_id(match_id=match_id),
            get_europe_odds_by_match_id(match_id=match_id),
            get_asian_handicap_odds_by_match_id(match_id=match_id),
            get_over_under_odds_by_match_id(match_id=match_id),
        ]

        # 使用 asyncio.gather 并发执行，并设置 return_exceptions=True
        # 这样即使某个API（比如阵容）失败，也不会中断整个流程。
        results = await asyncio.gather(*other_data_tasks, return_exceptions=True)
        # FIX: Switched to triple quotes for multi-line f-string.
        print(f"""✅ step 2:
  - All data fetching tasks completed.""")

        # --- 优化点 3: 结构化地组装报告 ---
        # 将所有成功或失败的结果清晰地组装起来。
        report = {
            # 核心数据已在第一步获取
            "match_details": match_details,
            # 其他数据
            "standings": results[0],
            "recent_performance": results[1],
            "h2h_history": results[2],
            "squad": results[3],
            "europe_odds": results[4],
            "asian_handicap_odds": results[5],
            "over_under_odds": results[6],
        }

        # 检查是否有失败的调用，并将异常转换为可读的错误信息
        for key, value in report.items():
            if isinstance(value, Exception):
                error_message = f"Failed to fetch {key}: {str(value)}"
                report[key] = {"error": error_message}  # 使用结构化的错误
                print(f"⚠️ Warning: Partial data failure for '{key}'. Reason: {error_message}")

        print(f"✅ [SUCCESS] Full report generated for match_id: {match_id}")
        return report

    except Exception as e:
        # 捕获意外的顶层异常
        error_details = f"An unexpected error occurred in generate_full_match_report_by_id: [Type: {type(e).__name__}] - [Details: {repr(e)}]"
        traceback.print_exc()
        print(f"❌ [FATAL] {error_details}")
        return f"生成完整报告时发生严重错误: {error_details}"


# 请调用 get_upcoming_competitive_matches 工具，match_type 为 "1"，直接调用，不要使用其他工具
@mcp.tool()
async def get_upcoming_competitive_matches(
        match_type: str
) -> Union[List[Dict[str, Any]], str]:
    """
    获取竞彩足球和篮球未开始的比赛列表。
    Fetches upcoming competitive football and basketball matches that haven't started yet.

    Args:
        match_type (str): 体育类型，必需参数。1 代表竞彩足球, 2 代表竞彩篮球。

    Returns:
        Union[List[Dict[str, Any]], str]: 成功时返回未开始比赛列表，失败时返回错误信息字符串。
    """
    endpoint = "http://ai-match.fengkuangtiyu.cn/api/v5/matches/getNotStartMatch"
    params = {"match_type": match_type}
    
    print(f"Executing get_upcoming_competitive_matches with params: {params}")
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(endpoint, params=params)
            response.raise_for_status()

            data = response.json()
            # Check if the API call was successful
            if data.get("code") == "0":
                # If successful, return the data list
                return data.get("data", [])
            else:
                # If the API returned an error, return error message
                return f"API returned an error: {data.get('msg', 'Unknown error')}"

    except httpx.HTTPStatusError as e:
        return f"API request failed with status {e.response.status_code}: {e.response.text}"
    except Exception as e:
        print(f"--- DETAILED ERROR IN get_upcoming_competitive_matches ---")
        traceback.print_exc()
        return f"An unexpected error occurred in get_upcoming_competitive_matches: [Type: {type(e).__name__}] - [Details: {repr(e)}]"


# 4. 启动 Web 服务器的代码 (不变)
if __name__ == "__main__":
    app = Starlette(
        routes=[
            Mount('/', app=mcp.sse_app()),
        ]
    )
    uvicorn.run(app, host="0.0.0.0", port=34012)