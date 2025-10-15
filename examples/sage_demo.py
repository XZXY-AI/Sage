"""
“你是一名专业的足球比赛数据分析师。请对比赛ID为 3558764 的比赛进行一次全面的赛前分析。请遵循以下步骤：
1. 获取比赛的基本信息、双方排名和积分。
2. 获取双方的近期战绩和历史交锋记录。
3. 获取比赛的阵容详情和欧盘、亚盘赔率。
4. 最后，综合以上所有信息，给出一个包含基本面、战绩分析、赔率参考和最终结论的报告。”
Sage Multi-Agent Demo
智能多智能体协作演示应用
主要优化：代码结构、错误处理、用户体验、性能

"""

import os
import sys
import json
import uuid
import argparse
import traceback
from pathlib import Path
from typing import List, Dict, Any, Optional
from dataclasses import dataclass

import streamlit as st
from openai import OpenAI, AzureOpenAI

# 设置页面配置 - 必须在任何其他streamlit调用之前
st.set_page_config(
    page_title="Sage多智能体自动架构平台",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 项目路径配置
project_root = Path(os.path.realpath(__file__)).parent.parent
sys.path.insert(0, str(project_root))

import sagents
print("sagents loaded from:", sagents.__file__)

from sagents.agent.agent_controller import AgentController
from sagents.professional_agents.code_agents import CodeAgent
from sagents.tool.tool_manager import ToolManager
from sagents.utils import logger
from sagents.config import get_settings, update_settings, Settings
from sagents.utils import (
    SageException, 
    ToolExecutionError, 
    AgentTimeoutError,
    with_retry,
    exponential_backoff,
    handle_exception
)

# 预制提示词（不在页面显示，但在代码中使用）
PREDEFINED_PROMPT = """
agent 总体目标：你是一个体育赛事分析师，接收用户的输入，然后根据用户的输入首先判定下任务类别，然后根据不同的任务类别，调用不同的mcp工具解决用户的问题，然后用纯中文生成回答，每次只需要回答用户本轮的提问，具体流程如下： 1 解析用户输入 任务：你一共需要负责执行三种任务：一是体育提问，用户询问体育或赛事的一些信息，但是不需要体系化的分析，则执行流程A；二是赛事结果分析预测，用户会指定比赛由你来产出赛事分析，如果识别到赛事预测，则执行流程B，如果执行B找不到比赛就转回流程A执行；三是投注分析，用户会让你给出未来几天有竞彩比赛的投注建议，如果识别到投注分析，则执行流程C，注意提到玩法一类的词也是投注分析。 A体育提问 A1 解析用户提问 任务：从用户自然语言中抽取用户的提问需求。 A2 根据任务从可选的工具中选择合适的（可组合多个工具）工具获取所需的信息，如果没有合适的工具则不调用，可选工具如下：1 用 query_match_list_by_date 找到比赛ID 目的：当用户没有给出 match_id 时，根据日期/队名/联赛查找目标比赛，锁定唯一 match_id。 调用：query_match_list_by_date(match_type=1, date=?, league_ids=?, team_id=?, status=?)，如果match_type为1找不到匹配赛事时，将match_type设为2再调用一次。2 用 get_match_details_by_id 获取核心信息 目的：确认比赛时间、场地等，away是客队，home是主队 调用：get_match_details_by_id(match_id, match_type=1)。3 用 get_match_details_by_id 获取核心信息 目的：确认比赛时间、场地等，away是客队，home是主队 调用：get_match_details_by_id(match_id, match_type=1)。4 用 get_match_standings_by_id 看积分&排名 目的：分析战意（保级/争四/欧战资格）。 调用：get_match_standings_by_id(match_id, match_type=1)。5 用 get_match_standings_by_id 看积分&排名 目的：分析战意（保级/争四/欧战资格）。 调用：get_match_standings_by_id(match_id, match_type=1)。6 用 get_head_to_head_history_by_match_id 查交锋 目的：查看双方历史交锋，默认根据比赛的的那一天查一年，在调用的时候把start date设为一年期，end date为比赛那天。 调用：get_head_to_head_history_by_match_id(match_id, start_date?, end_date?, match_type=1)。7 调用 get_football_squad_by_match_id(match_id) 解析主客队“伤病/停赛/复出/存疑”。8 用 get_europe_odds_by_match_id 拉欧赔 目的：欧赔胜平负的初赔与即时赔，判断市场倾向。 调用：get_europe_odds_by_match_id(match_id, match_type=1)。9 用 get_asian_handicap_odds_by_match_id 看亚盘 目的：查看让球盘口及变盘（升/降水、盘口深浅）。 调用：get_asian_handicap_odds_by_match_id(match_id, match_type=1)。10 用 get_over_under_odds_by_match_id 看大小球 目的：获取大小球（Goal Line）初盘及变化。 调用：get_over_under_odds_by_match_id(match_id, match_type=1)。11 调取get_upcoming_competitive_matches(match_type: 1) 传参：match_type=\"1\"（足球）。找到所有可以投注的赛事列表，当收到类似周四007或者竞足这类的输入时，就可能是竞彩比赛，就需要调取这个工具，拉取列表。12 调取get_history_match，获取已经结束的竞彩比赛，当收到类似周四007这类的输入时，就可能时竞彩比赛，就需要调取这个工具，拉取列表。 13 目的：当其他结构化工具（如伤病、阵容、赔率等）信息不足或需要获取最新动态（如最新伤病情况、更衣室氛围、关键球员状态、战术打法分析、媒体或球迷舆论等）时，调用 search_web_page 进行网络搜索。调用：search_web_page(query, date_range)。使用说明：query：为了获得最广泛和最及时的资讯，请务必使用英文进行检索。例如，可以搜索 \"Manchester City injury news\" 或 \"Real Madrid tactical analysis\"。date_range：为了确保信息的时效性，请遵循以下顺序：优先设置 date_range='qdr:d' 检索最近一天的信息。如果一天内的信息不足以支撑分析，再设置 date_range='qdr:w' 检索最近一周的信息。 A3 综合获取到的信息，回答用户的提问，仅需要回答用户本轮问题，无需其他额外信息。通过search_web_page搜索到的信息里如果有提到时间，都需要切换为北京时间再输出给用户。 B 赛事预测 B1 用 query_match_list_by_date 找到match_id 目的：根据日期/队名/联赛查找目标比赛，锁定唯一 match_id，当用户没有提供日期时，把就近的5天都查一遍。 调用：query_match_list_by_date(match_type=1, date=recent 5 days, league_ids=?, team_id=?, status=?)。拿到结果后：筛出与用户描述最匹配的那场比赛（主队、客队、时间一致），如果match_type为1找不到匹配赛事时，将match_type设为2再调用一次。当收到类似周四007这类的输入时，就可能是竞彩比赛，就需要调取get_upcoming_competitive_matches(match_type: 1足球 2篮球)来确认对应的赛事id。 B3 用 get_match_details_by_id 获取核心信息 目的：确认比赛时间、场地等，away是客队，home是主队 调用：get_match_details_by_id(match_id, match_type=1)。 B4 用 get_match_standings_by_id 看积分&排名 目的：分析战意（保级/争四/欧战资格）。 调用：get_match_standings_by_id(match_id, match_type=1)。 B5 用 get_team_recent_performance_by_match_id 看近期战绩 目的：获取双方近几场的胜平负、进失球趋势。 B6 用 get_head_to_head_history_by_match_id 查交锋 目的：查看双方历史交锋，默认根据比赛的的那一天查一年，在调用的时候把start date设为一年期，end date为比赛那天。 调用：get_head_to_head_history_by_match_id(match_id, start_date?, end_date?, match_type=1)。 B7 调用 get_football_squad_by_match_id(match_id) 解析主客队“伤病/停赛/复出/存疑”； B8 用 get_europe_odds_by_match_id 拉欧赔 目的：欧赔胜平负的初赔与即时赔，判断市场倾向。 调用：get_europe_odds_by_match_id(match_id, match_type=1)。 B9 用 get_asian_handicap_odds_by_match_id 看亚盘 目的：查看让球盘口及变盘（升/降水、盘口深浅）。 调用：get_asian_handicap_odds_by_match_id(match_id, match_type=1)。 B10 用 get_over_under_odds_by_match_id 看大小球 目的：获取大小球（Goal Line）初盘及变化。 调用：get_over_under_odds_by_match_id(match_id, match_type=1)。 B11 爆冷分析 目的：整合前面各步结果，分析各类爆冷因素，为最终成品写作提供参考。 分析逻辑：1、一方多线作战，比赛结果对当前联赛的排名没有太大影响。2、赛程密集或阵容伤病严重导致体能损耗严重。3、极端恶劣天气。4、弱队在保级、晋级或杯赛淘汰制一般都会有更强的战意5、主场优势。6、球队突发情况，例如欠薪被曝光、俱乐部丑闻等。 B12 综合写作与输出，仅需要回答用户本轮问题 目的：整合前面各步结果，写出成品，并给出明确倾向。 无工具调用：整理文字。写作要求：1 先用一段话概述本场比赛的背景和悬念。2 按“主队→客队”顺序，结合数据评估球队近况、战术特点、精神属性。3 重点说明排名、阵容、战意对结果的潜在影响。4 分析中引用关键数据作为论据，但不要堆砌。5 结尾给出：最可能赛果包括胜负和比分和12 句风险提示，体现客观性。6 全文 400到600 字左右即可，无需标题，段落按照赛事基本信息-主队信息-客队信息-交战信息-赔率信息-比赛预测分段即可，最后写出完整文章。 C投注建议 C1 解析用户输入 任务：从用户自然语言中抽取：比赛类型（足球）、日期、想要下注的时间以及是否有指定具体赛事等关键信息。 C2 候选检索 get_upcoming_competitive_matches(match_type: 1) 传参：match_type=\"1\"（足球）。找到所有可以投注的赛事列表，然后按照用户的要求汇总成一个match_id集合，若用户要查看所有竞彩比赛则汇总所有match_id，若用户指定了比赛数量则按照用户的选择来，若用户无明确要求则默认选12个match_id构成集合，若用户指定了具体比赛则只围绕该场比赛的match_id进行分析。 C3 针对match_id集合里的每一个match_id，都去执行如下步骤： C3.1 用 get_match_details_by_id 获取核心信息 目的：确认比赛时间、场地等，away是客队，home是主队，一定要按照home和away将比赛双方和队伍对齐。 调用：get_match_details_by_id(match_id, match_type=1)。 C3.2 用 get_match_standings_by_id 看积分&排名 目的：分析战意（保级/争四/欧战资格）。 调用：get_match_standings_by_id(match_id, match_type=1)。 B3.3 用 get_team_recent_performance_by_match_id 看近期战绩 目的：获取双方近几场（一般 5~10 场）的胜平负、进失球趋势。 调用：get_team_recent_performance_by_match_id(match_id, match_type=1)。 参考：收到的数据中分主客场，需要把队伍分别对应上 C3.4 用 get_europe_odds_by_match_id 拉欧赔 目的：欧赔胜平负的初赔与即时赔，判断市场倾向。 调用：get_europe_odds_by_match_id(match_id, match_type=1)。 C3.5 用 get_asian_handicap_odds_by_match_id 看亚盘 目的：查看让球盘口及变盘（升/降水、盘口深浅）。 调用：get_asian_handicap_odds_by_match_id(match_id, match_type=1)。 C3.6 用 get_over_under_odds_by_match_id 看大小球 目的：获取大小球（Goal Line）初盘及变化。 调用：get_over_under_odds_by_match_id(match_id, match_type=1)。 当调用完成后，针对每一个match_id，生成一个赛事简报，用于支撑最后的投注建议。 C4 综合写作与输出，仅需要回答用户本轮问题 目的：整合前面各步结果，写出成品，并给出明确倾向，最终用markdown格式输出。 无工具调用：整理文字。多场比赛综合投注推荐写作要求：输出格式（Markdown · 仅输出组合，不写长评，每场比赛附带比赛日期）先列出选择了哪些比赛，再给出投注方案。 一、基础组合原则 避免全热门； 强弱搭配 + 防平局（芬超/瑞超/德比常有高平率）； 分散联赛和开赛时段，降低相关性； 临场如阵容突发或赔率剧烈波动，优先替换/剔除。 二、实战组合方案（按风险排序） 统一表头： 场次 | 选择理由 | 推荐选项 行例：联赛 缩写·HH:MM 主 vs 客 | 近5主队4胜；客场胜率20% | 主胜(1.65) 方案1：稳健型（3串1，预计赔率 3–5 倍） 表格列出 3 行；末尾写“优势 / 100 元→约 [乘积] 倍”。 方案2：平衡型（4串1，预计赔率 8–12 倍） 表格列出 4 行；末尾给优势与示例回报。 方案3：博冷型（3串4，容错玩法） 列出 3 行高赔方向；解释 3串4 拆分与盈亏阈值；举“中两场”的乘积示例。 三、关键数据辅助决策 给 3–5 条最关键事实（德比平率、赔变方向、主客近况），每条一行，不堆砌。单场比赛投注推荐写作要求：比赛：[联赛] [比赛日期 HH:MM] [主队] vs [客队]，推荐选项：主胜 (赔率) / 平局 (赔率) / 客胜 (赔率)，核心理由:[关键理由1，如：主队近期攻击力冠绝联赛，场均打入3球。][关键理由2，如：客队核心后卫本场停赛，防线存在巨大隐患。][关键理由3，如：往绩交锋主队占据压倒性优势。]。风险提示：[用一句话指出潜在风险，如：客队擅长密集防守反击，可能对主队造成威胁。]  任9投注推荐写作要求：用一个表格将9场备选比赛信息（比赛日期，对战双方），推荐下注（主胜，客胜，平只能选一个）和推荐理由都列出来。
"""


class ComponentManager:
    """组件管理器 - 负责初始化和管理核心组件"""
    
    def __init__(self, api_key: str, model_name: str = None, base_url: str = None, 
                 tools_folders: List[str] = None, max_tokens: int = None, temperature: float = None):
        # 获取已更新的全局配置
        self.settings = get_settings()
        
        logger.debug(f"使用配置 - 模型: {self.settings.model.model_name}, 温度: {self.settings.model.temperature}")
        
        # 设置工具文件夹
        self.tools_folders = tools_folders or []
        
        # 初始化组件变量
        self._tool_manager: Optional[ToolManager] = None
        self._controller: Optional[AgentController] = None
        self._model: Optional[OpenAI] = None
        
    def initialize(self) -> tuple[ToolManager, AgentController]:
        """初始化所有组件"""
        try:
            logger.info(f"初始化组件，模型: {self.settings.model.model_name}")
            
            # 初始化工具管理器
            self._tool_manager = self._init_tool_manager()
            
            # 初始化模型和控制器
            self._model = self._init_model()
            self._controller = self._init_controller()
            
            logger.info("所有组件初始化成功")
            return self._tool_manager, self._controller
            
        except Exception as e:
            logger.error(f"组件初始化失败: {str(e)}")
            logger.error(traceback.format_exc())
            raise
    
    def _init_tool_manager(self) -> ToolManager:
        """初始化工具管理器"""
        logger.debug("初始化工具管理器")
        tool_manager = ToolManager()
        
        # 注册工具目录
        for folder in self.tools_folders:
            if Path(folder).exists():
                logger.debug(f"注册工具目录: {folder}")
                tool_manager.register_tools_from_directory(folder)
            else:
                logger.warning(f"工具目录不存在: {folder}")
        
        return tool_manager

    @with_retry(exponential_backoff(max_attempts=3, base_delay=1.0, max_delay=5.0))
    def _init_model(self) -> OpenAI:
        """初始化模型"""
        logger.debug(f"初始化模型，base_url: {self.settings.model.base_url}")
        try:
            # Azure OpenAI 配置
            if "azure.com" in self.settings.model.base_url:
                logger.info("检测到 Azure 配置，使用 AzureOpenAI 客户端")
                return AzureOpenAI(
                    api_key=self.settings.model.api_key,
                    azure_endpoint=self.settings.model.base_url,
                    api_version="2025-01-01-preview"
                )
            # Azure OpenAI 配置结束

            # 保留原来的逻辑作为默认选项
            return OpenAI(
                api_key=self.settings.model.api_key,
                base_url=self.settings.model.base_url
            )
        except Exception as e:
            logger.error(f"模型初始化失败: {str(e)}")
            raise SageException(f"无法连接到 API: {str(e)}")
    
    @with_retry(exponential_backoff(max_attempts=2, base_delay=0.5, max_delay=2.0))
    def _init_controller(self) -> AgentController:
        """初始化控制器"""
        try:
            model_config = {
                "model": self.settings.model.model_name,
                "temperature": self.settings.model.temperature,
                "max_tokens": self.settings.model.max_tokens
            }

            workspace_path = os.path.join(project_root, "workspace")
            os.makedirs(workspace_path, exist_ok=True)  # 这行能确保文件夹存在

            # 使用这个新路径来初始化控制器
            controller = AgentController(self._model, model_config, workspace=workspace_path)
            
            # 注册代码智能体
            try:
                code_agent = CodeAgent(self._model, model_config)
                self._tool_manager.register_tool(code_agent.to_tool())
                logger.debug("代码智能体注册成功")
            except Exception as e:
                logger.warning(f"代码智能体注册失败: {str(e)}")
                # 不中断整个初始化过程，代码智能体是可选的
            
            return controller
            
        except Exception as e:
            logger.error(f"控制器初始化失败: {str(e)}")
            raise SageException(f"无法初始化智能体控制器: {str(e)}")


def convert_messages_for_show(messages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """转换消息格式用于显示"""
    logger.debug(f"转换 {len(messages)} 条消息用于显示")
    new_messages = []
    
    for message in messages:
        if not message.get('show_content'):
            continue
            
        new_message = {
            'message_id': message.get('message_id', str(uuid.uuid4())),
            'role': 'assistant' if message['role'] != 'user' else 'user',
            'content': message.get('show_content')
        }
        new_messages.append(new_message)
        
    return new_messages


def create_user_message(content: str) -> Dict[str, Any]:
    """创建用户消息"""
    return {
        "role": "user",
        "content": content,
        "type": "normal",
        "message_id": str(uuid.uuid4())
    }


class StreamingHandler:
    """流式处理器 - 处理实时消息流"""
    
    def __init__(self, controller: AgentController):
        self.controller = controller
        self._current_stream = None
        self._current_stream_id = None
    
    def process_stream(self, 
                      messages: List[Dict[str, Any]], 
                      tool_manager: ToolManager,
                      session_id: Optional[str] = None,
                      use_deepthink: bool = True,
                      use_multi_agent: bool = True) -> List[Dict[str, Any]]:
        """处理消息流"""
        logger.debug("开始处理流式响应")
        
        new_messages = []
        
        try:
            for chunk in self.controller.run_stream(
                messages,
                tool_manager,
                session_id=session_id,
                deep_thinking=use_deepthink,
                summary=True,
                deep_research=use_multi_agent
            ):
                new_messages.extend(chunk)
                self._update_display(messages, new_messages)
                
        except Exception as e:
            error_info = handle_exception(e, {
                'method': 'process_stream',
                'session_id': session_id,
                'use_deepthink': use_deepthink,
                'use_multi_agent': use_multi_agent,
                'message_count': len(messages)
            })
            
            logger.error(f"流式处理出错: {str(e)}")
            
            # 根据异常类型提供不同的错误消息
            if isinstance(e, ToolExecutionError):
                error_message = f"工具执行失败: {str(e)}"
            elif isinstance(e, AgentTimeoutError):
                error_message = f"智能体响应超时: {str(e)}"
            elif isinstance(e, SageException):
                error_message = f"系统错误: {str(e)}"
            else:
                error_message = f"抱歉，处理过程中出现意外错误: {str(e)}"
            
            error_response = {
                "role": "assistant",
                "content": error_message,
                "message_id": str(uuid.uuid4()),
                "error_info": error_info
            }
            new_messages.append(error_response)
        
        return new_messages
    
    def _update_display(self, base_messages: List[Dict], new_messages: List[Dict]):
        """更新显示内容"""
        merged_messages = self.controller.task_analysis_agent._merge_messages(base_messages.copy(), new_messages)
        display_messages = convert_messages_for_show(merged_messages)
        
        # 找到最新的助手消息
        latest_assistant_msg = None
        for msg in reversed(display_messages):
            if msg['role'] in ['assistant', 'tool']:
                latest_assistant_msg = msg
                break
        
        if latest_assistant_msg:
            msg_id = latest_assistant_msg.get('message_id')
            
            # 处理新的消息流
            if msg_id != self._current_stream_id:
                logger.debug(f"检测到新消息流: {msg_id}")
                self._current_stream_id = msg_id
                self._current_stream = st.chat_message('assistant').empty()
            
            # 更新显示内容
            if self._current_stream:
                self._current_stream.write(latest_assistant_msg['content'])


def setup_ui():
    """设置用户界面"""
    st.title("🧠 Sage多智能体自动架构平台")
    st.markdown("**智能多智能体协作平台**")
    
    # 获取全局配置
    settings = get_settings()
    
    # 侧边栏设置 - 已隐藏
    # with st.sidebar:
    #     st.header("⚙️ 设置")
    #     
    #     # 多智能体选项
    #     use_multi_agent = st.toggle('🤖 启用多智能体推理', 
    #                                value=False)
    #     use_deepthink = st.toggle('🧠 启用深度思考', 
    #                              value=False)
    #     
    #     # 系统信息
    #     st.subheader("📊 系统信息")
    #     st.info(f"**模型**: {settings.model.model_name}")
    #     st.info(f"**温度**: {settings.model.temperature}")
    #     st.info(f"**最大标记**: {settings.model.max_tokens}")
    #     st.info(f"**环境**: {settings.environment}")
    #     
    #     # 工具列表
    #     if st.session_state.get('tool_manager'):
    #         display_tools(st.session_state.tool_manager)
    #     
    #     # 清除历史按钮
    #     if st.button("🗑️ 清除对话历史", type="secondary"):
    #         clear_history()
    
    # 设置默认值（原来从侧边栏获取）
    use_multi_agent = False
    use_deepthink = False
    
    return use_multi_agent, use_deepthink


# def display_tools(tool_manager: ToolManager):
#     """显示可用工具"""
#     st.subheader("🛠️ 可用工具")
#     tools = tool_manager.list_tools_simplified()
#     
#     if tools:
#         for tool_info in tools:
#             with st.expander(f"🔧 {tool_info['name']}", expanded=False):
#                 st.write(tool_info['description'])
#     else:
#         st.info("暂无可用工具")


def clear_history():
    """清除对话历史"""
    logger.info("用户清除对话历史")
    st.session_state.conversation = []
    st.session_state.inference_conversation = []
    st.session_state.is_first_input = True  # 重置首次输入标志
    st.rerun()


def init_session_state():
    """初始化会话状态"""
    if 'conversation' not in st.session_state:
        st.session_state.conversation = []
    if 'inference_conversation' not in st.session_state:
        st.session_state.inference_conversation = []
    if 'components_initialized' not in st.session_state:
        st.session_state.components_initialized = False
    if 'is_first_input' not in st.session_state:
        st.session_state.is_first_input = True


def display_conversation_history():
    """显示对话历史"""
    for msg in st.session_state.conversation:
        if msg['role'] == 'user':
            with st.chat_message("user"):
                st.write(msg['content'])
        elif msg['role'] == 'assistant':
            with st.chat_message("assistant"):
                st.write(msg['content'])


def process_user_input(user_input: str, tool_manager: ToolManager, controller: AgentController):
    """处理用户输入"""
    logger.info(f"处理用户输入: {user_input[:50]}{'...' if len(user_input) > 50 else ''}")
    
    # 如果是首次输入，拼接预制提示词
    if st.session_state.is_first_input:
        actual_input = PREDEFINED_PROMPT + user_input
        st.session_state.is_first_input = False
    else:
        actual_input = user_input
    
    # 创建用户消息（使用拼接后的内容）
    user_msg = create_user_message(actual_input)
    # 创建显示用的用户消息（只显示原始输入）
    display_user_msg = create_user_message(user_input)
    
    # 添加到对话历史（推理用拼接后的，显示用原始的）
    st.session_state.conversation.append(display_user_msg)
    st.session_state.inference_conversation.append(user_msg)
    
    # 显示用户消息（只显示原始输入）
    with st.chat_message("user"):
        st.write(user_input)
    
    # 处理响应
    with st.spinner("🤔 正在思考..."):
        try:
            generate_response(tool_manager, controller)
        except Exception as e:
            logger.error(f"生成响应时出错: {str(e)}")
            with st.chat_message("assistant"):
                st.error(f"抱歉，处理您的请求时出现了错误: {str(e)}")


def generate_response(tool_manager: ToolManager, controller: AgentController):
    """生成智能体响应"""
    streaming_handler = StreamingHandler(controller)
    
    # 处理流式响应
    new_messages = streaming_handler.process_stream(
        st.session_state.inference_conversation.copy(),
        tool_manager,
        session_id=None,
        use_deepthink=st.session_state.get('use_deepthink', True),
        use_multi_agent=st.session_state.get('use_multi_agent', True)
    )
    
    # 合并消息
    if new_messages:
        merged_messages = controller.task_analysis_agent._merge_messages(
            st.session_state.inference_conversation, new_messages
        )
        st.session_state.inference_conversation = merged_messages
        
        # 更新显示对话
        display_messages = convert_messages_for_show(merged_messages)
        st.session_state.conversation = display_messages
        
        logger.info("响应生成完成")


def update_global_settings(api_key: str, model_name: str = None, base_url: str = None, 
                          max_tokens: int = None, temperature: float = None):
    """提前更新全局设置，确保UI能显示正确的配置信息"""
    settings = get_settings()
    
    # 直接更新全局配置
    if api_key:
        settings.model.api_key = api_key
    if model_name:
        settings.model.model_name = model_name
    if base_url:
        settings.model.base_url = base_url
    if max_tokens:
        settings.model.max_tokens = max_tokens
    if temperature is not None:
        settings.model.temperature = temperature
    
    logger.debug(f"全局配置已更新 - 模型: {settings.model.model_name}, 温度: {settings.model.temperature}")


def run_web_demo(api_key: str, model_name: str = None, base_url: str = None, 
                 tools_folders: List[str] = None, max_tokens: int = None, temperature: float = None):
    """运行 Streamlit web 界面"""
    logger.info("启动 Streamlit web 演示")
    
    # 提前更新全局设置，确保UI显示正确的配置
    update_global_settings(api_key, model_name, base_url, max_tokens, temperature)
    
    # 初始化会话状态
    init_session_state()
    
    # 设置界面（此时能获取到正确的配置）
    use_multi_agent, use_deepthink = setup_ui()
    
    # 存储设置到会话状态
    st.session_state.use_multi_agent = use_multi_agent
    st.session_state.use_deepthink = use_deepthink
    
    # 初始化组件（只执行一次）
    if not st.session_state.components_initialized:
        try:
            with st.spinner("正在初始化系统组件..."):
                component_manager = ComponentManager(
                    api_key=api_key,
                    model_name=model_name,
                    base_url=base_url,
                    tools_folders=tools_folders,
                    max_tokens=max_tokens,
                    temperature=temperature
                )
                tool_manager, controller = component_manager.initialize()
                st.session_state.tool_manager = tool_manager
                st.session_state.controller = controller
                st.session_state.components_initialized = True
                st.session_state.config_updated = True  # 标记配置已更新
            st.success("系统初始化完成！")
            # 打印已注册工具，便于调试
            print("已注册工具：", [t['name'] for t in tool_manager.list_tools_simplified()])
            # 初始化完成后重新运行，确保UI显示更新后的配置
            st.rerun()
        except SageException as e:
            # 系统级异常，提供详细的错误信息和建议
            st.error(f"系统初始化失败: {str(e)}")
            error_info = handle_exception(e, {'component': 'system_initialization'})
            
            st.warning("**建议解决方案:**")
            for suggestion in error_info.get('recovery_suggestions', []):
                st.write(f"• {suggestion}")
            
            if 'API' in str(e):
                st.info("💡 **提示**: 请检查您的 API key 是否正确，网络连接是否正常")
            
            st.stop()
        except Exception as e:
            # 其他异常
            st.error(f"系统初始化失败: {str(e)}")
            error_info = handle_exception(e, {'component': 'system_initialization'})
            
            st.warning("**技术详情:**")
            st.code(traceback.format_exc())
            
            st.stop()
    
    # 显示历史对话
    display_conversation_history()
    
    # 用户输入
    user_input = st.chat_input("💬 请输入您的问题...")
    
    if user_input and user_input.strip():
        process_user_input(
            user_input.strip(), 
            st.session_state.tool_manager, 
            st.session_state.controller
        )


def parse_arguments() -> Dict[str, Any]:
    """解析命令行参数"""
    parser = argparse.ArgumentParser(
        description='Sage Multi-Agent Interactive Chat',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例用法:
  python sage_demo.py --api_key YOUR_API_KEY
  python sage_demo.py --api_key YOUR_API_KEY --model gpt-4 --tools_folders ./tools
        """
    )
    
    parser.add_argument('--api_key', 
                       default='2a3981750a3a4110b25296b6c064c99a',
                       help='Azure OpenAI API key')
    parser.add_argument('--model', 
                       default='gpt-4.1',
                       help='模型名称')
    parser.add_argument('--base_url', 
                       default='https://openai-api-aiapp-usest.openai.azure.com/',
                       help='Azure OpenAI endpoint')
    parser.add_argument('--tools_folders', nargs='+', default=[],
                       help='工具目录路径（多个路径用空格分隔）')
    parser.add_argument('--max_tokens', type=int, default=4096,
                       help='最大令牌数')
    parser.add_argument('--temperature', type=float, default=0.2,
                       help='温度参数')
    
    args = parser.parse_args()
    
    return {
        'api_key': args.api_key,
        'model_name': args.model,
        'base_url': args.base_url,
        'tools_folders': args.tools_folders,
        'max_tokens': args.max_tokens,
        'temperature': args.temperature
    }


def main():
    """主函数"""
    try:
        # 解析配置
        config = parse_arguments()
        logger.info(f"启动应用，模型: {config['model_name']}")
        
        # 运行 Web 演示
        run_web_demo(
            config['api_key'],
            config['model_name'],
            config['base_url'],
            config['tools_folders'],
            config['max_tokens'],
            config['temperature']
        )
        
    except SageException as e:
        logger.error(f"应用启动失败: {str(e)}")
        st.error(f"系统错误: {str(e)}")
        error_info = handle_exception(e, {'component': 'main_application'})
        
        st.warning("**恢复建议:**")
        for suggestion in error_info.get('recovery_suggestions', []):
            st.write(f"• {suggestion}")
            
    except Exception as e:
        logger.error(f"应用启动失败: {str(e)}")
        logger.error(traceback.format_exc())
        
        st.error(f"应用启动失败: {str(e)}")
        error_info = handle_exception(e, {'component': 'main_application'})
        
        with st.expander("🔍 查看技术详情", expanded=False):
            st.code(traceback.format_exc())


if __name__ == "__main__":
    main()
