import React, { useEffect, useState } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import { tomorrow } from 'react-syntax-highlighter/dist/esm/styles/prism';
import ReactECharts from 'echarts-for-react';
import LoadingMessage from './LoadingMessage';
import ToolCallBubble from './ToolCallBubble';
import MarkdownWithMath from './MarkdownWithMath';
import { Message, ToolCall } from '../types/chat';
import { convertContainerPathsToAlistUrls } from '../utils/pathConverter';

interface MessageBubbleProps {
  message: Message;
  onToolCallClick?: (toolCall: ToolCall) => void;
  onFileClick?: (fileUrl: string, fileName: string) => void;
}

const MessageBubble: React.FC<MessageBubbleProps> = ({ message, onToolCallClick, onFileClick }) => {
  const isUser = message.role === 'user';
  const isError = message.type === 'error';
  
  const formatDuration = (duration: number): string => {
    if (duration === 0) {
      return '<1ms';
    }
    if (duration < 1000) {
      return `${Math.max(1, Math.round(duration))}ms`;
    } else {
      return `${(duration / 1000).toFixed(1)}s`;
    }
  };

  // 根据消息类型返回对应的emoji
  const getMessageTypeEmoji = (type: string | undefined): string => {
    if (!type) return '';
    
    switch (type) {
      case 'tool_call':
        return '🔧'; // 工具调用请求
      case 'tool_call_result':
        return '📋'; // 工具执行结果
      case 'task_analysis_result':
        return '🔍'; // 任务分析
      case 'task_decomposition':
        return '📋'; // 任务分解
      case 'planning_result':
        return '🎯'; // 规划制定
      case 'observation_result':
        return '👁️'; // 观察结果
      case 'do_subtask_result':
        return '⚙️'; // 子任务执行
      case 'final_answer':
        return '✅'; // 最终答案
      case 'loading':
        return '🤔'; // 思考中
      case 'error':
        return '❌'; // 错误
      case 'thinking':
        return '💭'; // 思考过程
      case 'reflection':
        return '🪞'; // 反思
      case 'decision':
        return '🎲'; // 决策
      case 'execution':
        return '🚀'; // 执行
      case 'validation':
        return '✔️'; // 验证
      case 'summary':
        return '📄'; // 总结
      default:
        return ''; // 普通消息不显示emoji
    }
  };

  // 处理消息内容和显示逻辑
  const processMessageContent = () => {
    let displayContent = message.displayContent;
    let shouldShowBubble = true;
    
    if (message.type === 'tool_call' || message.type === 'tool_call_result') {
      // 工具调用相关消息：不显示气泡，只显示按钮
      shouldShowBubble = false;
    } else if (message.toolCalls && message.toolCalls.length > 0) {
      // 检查是否为专业智能体的结构化输出
      const isStructuredOutput = message.displayContent.includes('tasks') || 
                                 message.displayContent.includes('description') || 
                                 message.displayContent.includes('任务拆解') ||
                                 message.displayContent.includes('planning') ||
                                 message.displayContent.includes('observation') ||
                                 message.displayContent.includes('code') ||
                                 message.agentType === 'CodeAgent' ||
                                 message.agentType === 'PlanningAgent' ||
                                 message.agentType === '代码智能体' ||
                                 message.agentType === '任务分析师' ||
                                 message.displayContent.length > 300; // 长内容通常包含有价值信息
      
      if (isStructuredOutput) {
        // 对于专业智能体的结构化输出，只移除明显的重复工具调用信息
        displayContent = message.displayContent
          // 移除工具调用标题
          .replace(/🔧\s*\*\*调用工具[：:]\s*.*?\*\*\s*/g, '')
          // 移除简单的参数描述行
          .replace(/📝\s*\*\*参数\*\*[：:]?\s*/g, '')
          // 移除工具执行状态信息
          .replace(/⚙️\s*执行工具[^。]*。?\s*/g, '')
          // 清理多余的换行符
          .replace(/\n{3,}/g, '\n\n')
          .trim();
      } else {
        // 对于普通工具调用消息，进行更完整的过滤
        displayContent = message.displayContent
          // 移除工具调用标题和描述
          .replace(/🔧\s*\*\*调用工具[：:]\s*.*?\*\*[\s\S]*?(?=\n\n|\n(?=[^\s])|$)/g, '')
          // 移除参数描述
          .replace(/📝\s*\*\*参数\*\*[：:]?[\s\S]*?(?=\n\n|\n(?=[^\s])|$)/g, '')
          // 移除简单的JSON参数块
          .replace(/```json\s*\{[^}]*\}\s*```/g, '')
          // 移除工具执行状态信息
          .replace(/⚙️\s*执行工具[\s\S]*?(?=\n\n|\n(?=[^\s])|$)/g, '')
          // 移除多余的换行符
          .replace(/\n{3,}/g, '\n\n')
          .trim();
          
        // 如果过滤后内容为空，显示简洁的提示信息
        if (!displayContent) {
          const toolNames = message.toolCalls.map(tc => tc.name).join(', ');
          displayContent = `🔧 调用了 ${message.toolCalls.length} 个工具: ${toolNames}`;
        }
      }
    } else {
      // 普通消息：检查是否为loading状态
      shouldShowBubble = message.type === 'loading' || displayContent !== '';
    }
    
    // 转换容器路径为alist URL
    displayContent = convertContainerPathsToAlistUrls(displayContent);
    
    return { displayContent, shouldShowBubble };
  };

  const { displayContent, shouldShowBubble } = processMessageContent();

  return (
    <div
      className="message-bubble"
      style={{
        display: 'flex',
        justifyContent: isUser ? 'flex-end' : 'flex-start',
        marginBottom: '12px'
      }}
    >
      <div style={{
        maxWidth: isUser ? '75%' : '95%',
        minWidth: '120px',
        position: 'relative'
      }}>
        {/* 智能体类型标签 */}
        {!isUser && message.agentType && message.agentType !== 'Zavix' && (
          <div style={{
            fontSize: '12px',
            color: '#8b5cf6',
            marginBottom: '4px',
            fontWeight: 500
          }}>
            {message.agentType}
          </div>
        )}

        {/* 消息气泡 */}
        {shouldShowBubble && (
          <div
            style={{
              background: isUser 
                ? '#6366f1' 
                : isError 
                  ? '#fef2f2' 
                  : '#ffffff',
              color: isUser 
                ? '#ffffff' 
                : isError 
                  ? '#dc2626' 
                  : '#1f2937',
              padding: '10px 14px',
              borderRadius: isUser 
                ? '16px 16px 4px 16px' 
                : '16px 16px 16px 4px',
              boxShadow: isUser 
                ? '0 1px 3px rgba(99, 102, 241, 0.3)'
                : '0 1px 3px rgba(0, 0, 0, 0.1)',
              border: isUser 
                ? 'none'
                : '1px solid #f1f5f9',
              fontSize: '14px',
              lineHeight: '1.5',
              wordBreak: 'break-word',
              position: 'relative'
            }}
          >
            {message.type === 'loading' ? (
              <LoadingMessage message={message.displayContent} />
            ) : (
              <div style={{ position: 'relative' }}>
                {/* 消息类型emoji */}
                {!isUser && getMessageTypeEmoji(message.type) && (
                  <span style={{
                    fontSize: '16px',
                    position: 'absolute',
                    left: '0',
                    top: '0',
                    display: 'block',
                    lineHeight: '1.5'
                  }}>
                    {getMessageTypeEmoji(message.type)}
                  </span>
                )}
                <div style={{ 
                  display: 'block', 
                  marginLeft: !isUser && getMessageTypeEmoji(message.type) ? '24px' : '0'
                }}>
                  <MarkdownWithMath onFileClick={onFileClick}>
                    {displayContent}
                  </MarkdownWithMath>
                </div>
              </div>
            )}
          </div>
        )}
        
        {/* 工具调用按钮 */}
        {!isUser && message.toolCalls && message.toolCalls.length > 0 && (
          <div style={{ 
            marginTop: shouldShowBubble ? '8px' : '0px',
            display: 'flex',
            flexWrap: 'wrap',
            gap: '6px'
          }}>
            {message.toolCalls.map((toolCall) => (
              <ToolCallBubble
                key={toolCall.id}
                toolCall={{
                  id: toolCall.id,
                  toolName: toolCall.name,
                  parameters: toolCall.arguments,
                  result: toolCall.result,
                  duration: toolCall.duration,
                  status: toolCall.status,
                  error: toolCall.error,
                  timestamp: message.timestamp
                }}
                onClick={(toolCallData) => onToolCallClick?.(toolCall)}
              />
            ))}
          </div>
        )}

        {/* 时间戳和耗时 */}
        <div style={{ 
          fontSize: '11px', 
          color: '#9ca3af',
          marginTop: '4px',
          textAlign: isUser ? 'right' : 'left',
          display: 'flex',
          justifyContent: isUser ? 'flex-end' : 'flex-start',
          alignItems: 'center',
          gap: '8px'
        }}>
          <span>
            {message.timestamp.toLocaleTimeString('zh-CN', {
              hour: '2-digit',
              minute: '2-digit'
            })}
          </span>
          {!isUser && message.type !== 'loading' && message.duration !== undefined && message.duration >= 0 && (
            <span style={{
              background: 'rgba(0, 0, 0, 0.05)',
              padding: '1px 4px',
              borderRadius: '3px',
              fontSize: '10px'
            }}>
              {formatDuration(message.duration)}
            </span>
          )}
        </div>
      </div>
    </div>
  );
};

export default MessageBubble; 