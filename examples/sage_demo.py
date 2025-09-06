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
    page_title="新质向阳多智能体自动架构平台",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 项目路径配置
project_root = Path(os.path.realpath(__file__)).parent.parent
sys.path.insert(0, str(project_root))

import sagents
print("sagents loaded from:", sagents.__file__)

from sagents.sagents import SAgent
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
"""


class ComponentManager:
    """组件管理器 - 负责初始化和管理核心组件"""
    
    def __init__(self, api_key: str, model_name: str = None, base_url: str = None, 
                 tools_folders: List[str] = None, max_tokens: int = None, temperature: float = None):
        logger.debug(f"使用配置 - 模型: {model_name}, 温度: {temperature}")
        self.api_key = api_key
        self.model_name = model_name
        self.base_url = base_url
        self.max_tokens = max_tokens
        self.temperature = temperature

        # 设置工具文件夹
        self.tools_folders = tools_folders or []
        
        # 初始化组件变量
        self._tool_manager: Optional[ToolManager] = None
        self._controller: Optional[SAgent] = None
        self._model: Optional[OpenAI] = None
        
    def initialize(self) -> tuple[ToolManager, SAgent]:
        """初始化所有组件"""
        try:
            logger.info(f"初始化组件，模型: {self.model_name}")
            
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
                api_key=self.api_key,
                base_url=self.base_url
            )
        except Exception as e:
            logger.error(f"模型初始化失败: {str(e)}")
            raise SageException(f"无法连接到 API: {str(e)}")
    
    def _init_controller(self) -> SAgent:
        """初始化控制器"""
        try:
            model_config = {
                "model": self.model_name,
                "temperature": self.temperature,
                "max_tokens": self.max_tokens
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
            raise 


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
    
    def __init__(self, controller: SAgent):
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
                multi_agent=use_multi_agent
            ):
                # 将message chunk类型的chunks 转化成字典
                chunks_dict = [msg.to_dict() for msg in chunk]
                new_messages.extend(chunks_dict)
                self._update_display(messages, new_messages)
                
        except Exception as e:
            logger.error(traceback.format_exc())            
            error_response = {
                "role": "assistant",
                "content": f"流式处理出错: {str(e)}",
                "message_id": str(uuid.uuid4()),
            }
            new_messages.append(error_response)
        
        return new_messages
    
    def _update_display(self, base_messages: List[Dict], new_messages: List[Dict]):
        """更新显示内容"""
        merged_messages = MessageManager.merge_new_messages_to_old_messages(new_messages,base_messages.copy() )
        merged_messages_dict = [msg.to_dict() for msg in merged_messages]
        display_messages = convert_messages_for_show(merged_messages_dict)
        
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


def setup_ui(config: Dict):
    """设置用户界面"""
    st.title("🧠 新质向阳多智能体自动架构平台")
    st.markdown("**智能多智能体协作平台**")
        
    # 侧边栏设置
    with st.sidebar:
        st.header("⚙️ 设置")
        
        # 多智能体选项
        use_multi_agent = st.toggle('🤖 启用多智能体推理', 
                                   value=config.get('use_multi_agent', True))
        use_deepthink = st.toggle('🧠 启用深度思考', 
                                 value=config.get('use_deepthink', True))
        
        # 系统信息
        st.subheader("📊 系统信息")
        st.info(f"**模型**: {config.get('model_name', '未配置')}")
        st.info(f"**温度**: {config.get('temperature', '未配置')}")
        st.info(f"**最大标记**: {config.get('max_tokens', '未配置')}")
        st.info(f"**环境**: {config.get('environment', '未配置')}")
        
        # 工具列表
        if st.session_state.get('tool_manager'):
            display_tools(st.session_state.tool_manager)
        
        # 清除历史按钮
        if st.button("🗑️ 清除对话历史", type="secondary"):
            clear_history()
    
    return use_multi_agent, use_deepthink


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


def process_user_input(user_input: str, tool_manager: ToolManager, controller: SAgent):
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
            logger.error(traceback.format_exc())
            logger.error(f"生成响应时出错: {str(e)}")
            with st.chat_message("assistant"):
                st.error(f"抱歉，处理您的请求时出现了错误: {str(e)}")


def generate_response(tool_manager: ToolManager, controller: SAgent):
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
        merged_messages = MessageManager.merge_new_messages_to_old_messages(
            new_messages,st.session_state.inference_conversation 
        )
        merged_messages_dict = [msg.to_dict() for msg in merged_messages]
        st.session_state.inference_conversation = merged_messages_dict
        
        # 更新显示对话
        display_messages = convert_messages_for_show(merged_messages_dict)
        st.session_state.conversation = display_messages
        
        logger.info("响应生成完成")

def run_web_demo(api_key: str, model_name: str = None, base_url: str = None, 
                 tools_folders: List[str] = None, max_tokens: int = None, temperature: float = None):
    """运行 Streamlit web 界面"""
    logger.info("启动 Streamlit web 演示")
        
    # 初始化会话状态
    init_session_state()
    config = {
        'api_key': api_key,
        'model_name': model_name,
        'base_url': base_url,
        'tools_folders': tools_folders,
        'max_tokens': max_tokens,
        'temperature': temperature
    }
    # 设置界面（此时能获取到正确的配置）
    use_multi_agent, use_deepthink = setup_ui(config)
    
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
        except Exception as e:
            # 其他异常
            st.error(f"系统初始化失败: {str(e)}")
            
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
        
            
    except Exception as e:
        logger.error(f"应用启动失败: {str(e)}")
        logger.error(traceback.format_exc())
        
        st.error(f"应用启动失败: {str(e)}")
        
        with st.expander("🔍 查看技术详情", expanded=False):
            st.code(traceback.format_exc())


if __name__ == "__main__":
    main()
