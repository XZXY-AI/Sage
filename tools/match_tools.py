# 1. 只导入工具逻辑本身需要的库
import httpx
import os
from typing import List, Dict, Any, Optional, Union
from sagents.tool import tool  # <--- 1. 必须导入

# 2. 工具函数，移除了 @mcp.tool() 装饰器
@tool()
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
        match_type (str): 体育类型，必需参数。1 代表足球, 2 代表篮球。 (Sport type, required. 1 for football, 2 for basketball.)
        date (Optional[str]): 查询日期，格式为 YYYY-MM-DD。 (Query date, format YYYY-MM-DD.)
        league_ids (Optional[str]): 联赛ID，多个ID用逗号分隔。 (League IDs, separated by commas.)
        team_id (Optional[str]): 球队ID。 (Team ID.)
        status (Optional[str]): 比赛状态。1:未开始, 2:完场, 3:赛中, 4:其他。 (Match status. 1:Not started, 2:Finished, 3:In progress, 4:Other.)

    Returns:
        Union[List[Dict[str, Any]], str]: 成功时返回比赛数据列表，失败时返回错误信息字符串。
    """
    # API 的固定地址
    endpoint = "http://ai-match.fengkuangtiyu.cn/api/v5/matches"

    # 由于假设不需要 API Key，headers 为空
    # (如果需要 Key，逻辑应改为从环境变量 os.environ.get 读取)
    headers = {}

    # 动态构建查询参数，只有当用户提供了值的时候才添加到请求中
    params = {"match_type": match_type}
    if date:
        params["date"] = date
    if league_ids:
        params["league_ids"] = league_ids
    if team_id:
        params["team_id"] = team_id
    if status:
        params["status"] = status

    print(f"Executing get_match_list tool with params: {params}")

    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(endpoint, headers=headers, params=params)
            response.raise_for_status()  # 如果请求失败 (如 4xx 或 5xx 错误) 则抛出异常
            return response.json()
    except httpx.HTTPStatusError as e:
        return f"API request failed with status {e.response.status_code}: {e.response.text}"
    except Exception as e:
        return f"An unexpected error occurred: {str(e)}"

# 你可以在这个文件末尾继续添加其他工具函数
# 例如： async def get_match_info(match_id: str): ...