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
    page_title="新质向阳多智能体平台",
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

# 定义预设提示词常量
MATCH_PREDICTION_PROMPT = """
你是一个体育赛事分析师，当用户输入一场或多场比赛的关键信息（如时间、联赛、对阵双方，或只给日期/队名）时： 1）调用query_match_list_by_date定位到比赛的match_id； 2）一步一步调用mcp工具拉取数据进行分析（积分形势、战意、阵容、近况、交锋、赔率等）； 3）最终输出一篇结构清晰、观点明确的中文赛事分析文章，并给出倾向性判断（如主胜/主负/大小球方向等）。
1 解析用户输入 任务：从用户自然语言中抽取：比赛类型（足球的type为1，篮球为2）、日期或比赛ID、对阵双方、联赛名称等关键信息。
2 用 query_match_list_by_date 找到比赛ID 目的：当用户没有给出 match_id 时，根据日期/队名/联赛查找目标比赛，锁定唯一 match_id。 调用：query_match_list_by_date(match_type=1, date=?, league_ids=?, team_id=?, status=1)。 参考：函数用途与参数说明。 拿到结果后：筛出与用户描述最匹配的那场比赛（主队、客队、时间一致）。若多场相似，向用户澄清。
3 针对确定的match_id去执行以下步骤获取比赛基本信息：3.1 用 get_match_details_by_id 获取核心信息 目的：确认比赛时间、场地等，away是客队，home是主队 调用：get_match_details_by_id(match_id, match_type=1)。3.2用 get_match_standings_by_id 看积分&排名 目的：分析战意（保级/争四/欧战资格）。 调用：get_match_standings_by_id(match_id, match_type=1)。 3.3 用 get_team_recent_performance_by_match_id 看近期战绩 目的：获取双方近几场（一般 5~10 场）的胜平负、进失球趋势。 调用：get_team_recent_performance_by_match_id(match_id, match_type=1)。 参考：收到的数据中分主客场，需要把队伍分别对应上。3.4用 get_head_to_head_history_by_match_id 查交锋 目的：查看双方历史交锋，默认根据比赛的的那一天查一年，在调用的时候把start date设为一年期，end date为比赛那天。 调用：get_head_to_head_history_by_match_id(match_id, start_date?, end_date?, match_type=1)。3.5调用 get_football_squad_by_match_id(match_id) 解析主客队“伤病/停赛/复出/存疑”。
4 针对确定的match_id去执行以下步骤获取比赛赔率信息：4.1用 get_europe_odds_by_match_id 拉欧赔 目的：欧赔胜平负的初赔与即时赔，判断市场倾向。 调用：get_europe_odds_by_match_id(match_id, match_type=1)。4.2用 get_asian_handicap_odds_by_match_id 看亚盘 目的：查看让球盘口及变盘（升/降水、盘口深浅）。 调用：get_asian_handicap_odds_by_match_id(match_id, match_type=1)。4.3用 get_over_under_odds_by_match_id 看大小球 目的：获取大小球（Goal Line）初盘及变化。 调用：get_over_under_odds_by_match_id(match_id, match_type=1)。
5 综合写作与输出 目的：整合前面各步结果，写出成品，并给出明确倾向，最终用markdown格式输出。 无工具调用：整理文字。写作要求：1 先用一段话概述本场比赛的背景和悬念。2 按“主队→客队”顺序，结合数据评估球队近况、战术特点、精神属性。3 重点说明伤停、轮换、战意和爆冷对结果的潜在影响。4 分析中引用关键数据作为论据，但不要堆砌。5 结尾给出：最可能赛果包括胜负和比分和1 2 句风险提示，体现客观性。6 全文 400 600 字左右即可，无需标题写成分段的连贯文章，段落按照赛事基本信息-主队信息-客队信息-交战信息-赔率信息-比赛预测分段即可，最后全文用markdown格式输出。
"""

BETTING_RECOMMENDATION_PROMPT = """
你是足球投注组合规划师。当用户给出日期/联赛/队名/预算/偏好时：先调用 get_upcoming_competitive_matches(match_type="1") 获取所有的候选比赛；在本地基于用户条件（日期/联赛/队名）对候选做筛选与去重，得到目标 match_id 集合；逐场用其余 MCP 工具拉取细项（详情/积分/近况/欧赔/亚盘/大小球）；不写长评，直接产出三套组合（稳健/平衡/博冷）+ 资金分配/避坑，并给出赔率乘积与 100 元示例回报。
1 解析用户输入 任务：从用户自然语言中抽取：比赛类型（足球）、日期以及想要下注的时间等关键信息。
2 候选检索 get_upcoming_competitive_matches(match_type: 1) 传参：match_type="1"（足球）。找到所有可以投注的赛事列表，然后按照用户的要求汇总成一个match_id集合，若用户无明确要求则默认选12个match_id构成集合。
3 针对match_id集合里的每一个match_id，都去执行如下步骤： 3.1 用 get_match_details_by_id 获取核心信息 目的：确认比赛时间、场地等，away是客队，home是主队，一定要按照home和away将比赛双方和队伍对齐。 调用：get_match_details_by_id(match_id, match_type=1)。 3.2 用 get_match_standings_by_id 看积分&排名 目的：分析战意（保级/争四/欧战资格）。 调用：get_match_standings_by_id(match_id, match_type=1)。 3.3 用 get_team_recent_performance_by_match_id 看近期战绩 目的：获取双方近几场（一般 5~10 场）的胜平负、进失球趋势。 调用：get_team_recent_performance_by_match_id(match_id, match_type=1)。 参考：收到的数据中分主客场，需要把队伍分别对应上 3.4 用 get_europe_odds_by_match_id 拉欧赔 目的：欧赔胜平负的初赔与即时赔，判断市场倾向。 调用：get_europe_odds_by_match_id(match_id, match_type=1)。 3.5 用 get_asian_handicap_odds_by_match_id 看亚盘 目的：查看让球盘口及变盘（升/降水、盘口深浅）。 调用：get_asian_handicap_odds_by_match_id(match_id, match_type=1)。 3.6 用 get_over_under_odds_by_match_id 看大小球 目的：获取大小球（Goal Line）初盘及变化。 调用：get_over_under_odds_by_match_id(match_id, match_type=1)。 当调用完成后，针对每一个match_id，生成一个赛事简报，用于支撑最后的投注建议。
4 综合写作与输出 目的：整合前面各步结果，写出成品，并给出明确倾向，最终用markdown格式输出。 无工具调用：整理文字。写作要求：输出格式（Markdown · 仅输出组合，不写长评，每场比赛附带比赛日期） 一、基础组合原则 避免全热门； 强弱搭配 + 防平局（芬超/瑞超/德比常有高平率）； 分散联赛和开赛时段，降低相关性； 临场如阵容突发或赔率剧烈波动，优先替换/剔除。 二、实战组合方案（按风险排序） 统一表头： 场次 | 选择理由 | 推荐选项 行例：联赛 缩写·HH:MM 主 vs 客 | 近5主队4胜；客场胜率20% | 主胜(1.65) 方案1：稳健型（3串1，预计赔率 3–5 倍） 表格列出 3 行；末尾写“优势 / 100 元→约 [乘积] 倍”。 方案2：平衡型（4串1，预计赔率 8–12 倍） 表格列出 4 行；至少 1 行为双选（如“平/负(1.xx)”）；末尾给优势与示例回报。 方案3：博冷型（3串4，容错玩法） 列出 3 行高赔方向；解释 3串4 拆分与盈亏阈值；举“中两场”的乘积示例。 三、关键数据辅助决策 给 3–5 条最关键事实（德比平率、赔变方向、主客近况），每条一行，不堆砌。
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
            # vvv 新增的 Azure 处理逻辑 vvv
            if "azure.com" in self.settings.model.base_url:
                logger.info("检测到 Azure 配置，使用 AzureOpenAI 客户端")
                return AzureOpenAI(
                    api_key=self.settings.model.api_key,
                    azure_endpoint=self.settings.model.base_url,
                    api_version="2025-01-01-preview"  # 建议使用一个稳定且常用的 api-version
                )
            # ^^^ 新增的 Azure 处理逻辑 ^^^

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
        content_to_show = message.get('show_content', message.get('content'))
        if not content_to_show:
            continue
            
        new_message = {
            'message_id': message.get('message_id', str(uuid.uuid4())),
            'role': 'assistant' if message['role'] != 'user' else 'user',
            'content': content_to_show
        }
        new_messages.append(new_message)
        
    return new_messages


def create_user_message(content: str, show_content: Optional[str] = None) -> Dict[str, Any]:
    """创建用户消息"""
    return {
        "role": "user",
        "content": content,
        "show_content": show_content if show_content is not None else content,
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
    st.title("新质向阳多智能体平台")
    st.markdown("**智能多智能体协作平台**")


def display_tools(tool_manager: ToolManager):
    """显示可用工具"""
    st.subheader("🛠️ 可用工具")
    tools = tool_manager.list_tools_simplified()
    
    if tools:
        for tool_info in tools:
            with st.expander(f"🔧 {tool_info['name']}", expanded=False):
                st.write(tool_info['description'])
    else:
        st.info("暂无可用工具")


def clear_history():
    """清除对话历史"""
    logger.info("用户清除对话历史")
    st.session_state.conversation = []
    st.session_state.inference_conversation = []
    st.rerun()


def init_session_state():
    """初始化会话状态"""
    if 'conversation' not in st.session_state:
        st.session_state.conversation = []
    if 'inference_conversation' not in st.session_state:
        st.session_state.inference_conversation = []
    if 'components_initialized' not in st.session_state:
        st.session_state.components_initialized = False


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

    full_prompt = user_input
    # 检查是否为第一次对话，如果是，则拼接预设提示词
    if not st.session_state.conversation:
        if st.session_state.agent_mode == '赛事预测':
            full_prompt = f"{MATCH_PREDICTION_PROMPT}\n\n用户问题：{user_input}"
            logger.info("拼接赛事预测提示词")
        elif st.session_state.agent_mode == '投注推荐':
            full_prompt = f"{BETTING_RECOMMENDATION_PROMPT}\n\n用户问题：{user_input}"
            logger.info("拼接投注推荐提示词")

    # 创建用户消息
    user_msg = create_user_message(full_prompt, show_content=user_input)
    
    # 添加到推理对话历史
    st.session_state.inference_conversation.append(user_msg)
    
    # 更新显示对话历史
    st.session_state.conversation.append({'role': 'user', 'content': user_input})
    
    # 显示用户消息
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
    setup_ui()
    
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
    
    # 获取全局配置
    settings = get_settings()

    # 使用可展开容器将模式选择与聊天输入框在视觉上关联
    with st.expander("⚙️ 智能体模式设置", expanded=True):
        st.session_state.agent_mode = st.selectbox(
            '请选择智能体模式:',
            ('赛事预测', '投注推荐'),
            label_visibility="collapsed" # 隐藏标签，因为标题已说明
        )

        # 根据下拉菜单选项设置配置
        if st.session_state.agent_mode == '赛事预测':
            use_deepthink = True
            use_multi_agent = False
        elif st.session_state.agent_mode == '投注推荐':
            use_deepthink = True
            use_multi_agent = False
        else:
            # 默认配置
            use_deepthink = settings.agent.enable_deep_thinking
            use_multi_agent = False

        # 存储设置到会话状态
        st.session_state.use_multi_agent = use_multi_agent
        st.session_state.use_deepthink = use_deepthink
    
    # 处理用户输入
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
        description='新质向阳多智能体平台',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例用法:
  python sage_demo.py --api_key YOUR_API_KEY
  python sage_demo.py --api_key YOUR_API_KEY --model gpt-4 --tools_folders ./tools
        """
    )
    
    parser.add_argument('--api_key', required=True, 
                       help='OpenRouter API key（必需）')
    parser.add_argument('--model', 
                       default='mistralai/mistral-small-3.1-24b-instruct:free',
                       help='模型名称')
    parser.add_argument('--base_url', 
                       default='https://openrouter.ai/api/v1',
                       help='API base URL')
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
