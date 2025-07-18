# 1. 导入所有必要的库
import httpx
from mcp.server.fastmcp import FastMCP
from starlette.applications import Starlette
from starlette.routing import Mount
import uvicorn
import argparse
from typing import List, Dict, Any, Optional, Union
import traceback  # <-- 导入 traceback 模块用于打印详细错误

# 2. 初始化 MCP 框架 (不变)
mcp = FastMCP("Match Data Service")

# 3. 设置命令行参数 (不变)
parser = argparse.ArgumentParser(description='启动比赛数据 MCP Server')
args = parser.parse_args()


# ==============================================================================

@mcp.tool()
async def get_match_list(
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
        params["date"] = date
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
            return response.json()
    except httpx.HTTPStatusError as e:
        return f"API request failed with status {e.response.status_code}: {e.response.text}"
    except Exception as e:
        print(f"--- DETAILED ERROR IN get_match_list ---")
        traceback.print_exc()
        return f"An unexpected error occurred in get_match_list: [Type: {type(e).__name__}] - [Details: {repr(e)}]"

# 获取比赛联赛排名和积分
# http://ai-match.fengkuangtiyu.cn/api/v5/matches/3558764/league_standings?match_type=1
@mcp.tool()
async def get_league_standings(
        match_id: str,
        match_type: Optional[str] = None
) -> Union[Dict[str, Any], str]:
    """
    根据比赛ID获取联赛排名和积分。
    Fetches league standings and points by match ID.

    Args:
        match_id (str): 比赛ID (必需), 例如 '3558764'。
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
async def get_match_essentials(
        match_id: str,
        match_type: Optional[str] = None
) -> Union[Dict[str, Any], str]:
    """
    根据比赛ID获取比赛的核心信息。
    Fetches the essential information for a match by its ID.

    Args:
        match_id (str): 比赛ID (必需), 例如 '3558764'。
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

# http://ai-match.fengkuangtiyu.cn/api/v5/matches/3558764/recent_forms?match_type=1
# 获取比赛近期战绩
# 调用工具根据比赛id 3558764获取他的近期战绩
@mcp.tool()
async def get_match_recent_forms(
        match_id: str,
        match_type: Optional[str] = None
) -> Union[Dict[str, Any], str]:
    """
    根据比赛ID获取比赛双方的近期战绩。
    Fetches the recent forms of the teams involved in a match by its ID.

    Args:
        match_id (str): 比赛ID (必需), 例如 '3558764'。
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
            return response.json()
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
async def get_squad_details(
        match_id: str
) -> Union[Dict[str, Any], str]:
    """
    根据比赛ID获取比赛阵容（仅限足球）。
    Fetches the squad details for a football match by its ID.

    Args:
        match_id (str): 比赛ID (必需), 例如 '3558764'。

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


@mcp.tool()
async def get_match_h2h(
        match_id: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        match_type: Optional[str] = None
) -> Union[Dict[str, Any], str]:
    """
    根据比赛ID获取双方历史交锋信息。
    Fetches the head-to-head (h2h) match history by a given match ID.

    Args:
        match_id (str): 比赛ID (必需), 例如 '3558764'。
        start_date (Optional[str]): 筛选此日期之后的交锋记录，格式 YYYY-MM-DD。
        end_date (Optional[str]): 筛选此日期之前的交锋记录，格式 YYYY-MM-DD。
        match_type (Optional[str]): 体育类型, 1 代表足球, 2 代表篮球。

    Returns:
        Union[Dict[str, Any], str]: 成功时返回历史交锋数据，失败时返回错误信息字符串。
    """
    endpoint = f"http://ai-match.fengkuangtiyu.cn/api/v5/matches/{match_id}/h2h"

    params = {"match_type": "1"}
    if start_date:
        params["start_date"] = start_date
    if end_date:
        params["end_date"] = end_date
    if match_type:
        params["match_type"] = match_type

    print(f"Executing get_match_h2h for match_id: {match_id} with params: {params}")

    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(endpoint, params=params)
            response.raise_for_status()
            return response.json()
    except httpx.HTTPStatusError as e:
        return f"API request failed with status {e.response.status_code}: {e.response.text}"
    except Exception as e:
        import traceback
        print(f"--- DETAILED ERROR IN get_match_h2h ---")
        traceback.print_exc()
        return f"An unexpected error occurred in get_match_h2h: [Type: {type(e).__name__}] - [Details: {repr(e)}]"


@mcp.tool()
async def get_win_draw_lose_odds(
        match_id: str,
        match_type: Optional[str] = None
) -> Union[Dict[str, Any], str]:
    """
    根据比赛ID获取欧赔赔率信息（胜平负）。
    Fetches the European win-draw-lose odds for a match by its ID.

    Args:
        match_id (str): 比赛ID (必需), 例如 '3558764'。
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
async def get_asian_handicap_odds(
        match_id: str,
        match_type: Optional[str] = None
) -> Union[Dict[str, Any], str]:
    """
    根据比赛ID获取亚盘赔率信息。
    Fetches the Asian Handicap odds for a match by its ID.

    Args:
        match_id (str): 比赛ID (必需), 例如 '3558764'。
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
async def get_goal_line_odds(
        match_id: str,
        match_type: Optional[str] = None
) -> Union[Dict[str, Any], str]:
    """
    根据比赛ID获取足球大小球或篮球总分赔率。
    Fetches the Goal Line (Over/Under) or Total Points odds for a match by its ID.

    Args:
        match_id (str): 比赛ID (必需), 例如 '3558764'。
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

# 4. 启动 Web 服务器的代码 (不变)
if __name__ == "__main__":
    app = Starlette(
        routes=[
            Mount('/', app=mcp.sse_app()),
        ]
    )
    uvicorn.run(app, host="0.0.0.0", port=34012)