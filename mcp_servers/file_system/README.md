# 🗂️ 文件系统 (File System)

> 精简高效的 MCP 文件系统服务器，专注核心功能，优化token使用

## 🚀 设计理念

基于**效率优先**的原则，本文件系统只提供**真正需要**的核心工具，其他简单操作推荐使用命令行处理，实现：

- 💰 **Token优化**: 工具数量从15个精简到4个，减少60-70% token使用
- ⚡ **提升效率**: 减少选择复杂度，AI能更快选择合适的工具
- 🎯 **专注核心**: 只做命令行难以实现的复杂功能
- 🔧 **易于维护**: 代码量减少，维护成本大幅降低

## 📋 核心工具 (4个)

### 1. 📄 file_read - 高级文件读取
```python
await file_read(
    file_path="/path/to/file.txt",
    start_line=10,              # 开始行号
    end_line=20,                # 结束行号
    encoding="auto",            # 自动编码检测
    max_size_mb=10.0           # 文件大小限制
)
```

**功能特点**:
- ✅ 按行范围读取
- ✅ 自动编码检测
- ✅ 文件大小保护
- ✅ 安全路径验证

### 2. ✏️ file_write - 智能文件写入
```python
await file_write(
    file_path="/path/to/file.txt",
    content="文件内容",
    mode="overwrite",           # overwrite/append/prepend
    encoding="utf-8",
    auto_upload=False          # 可选云端上传
)
```

**功能特点**:
- ✅ 多种写入模式
- ✅ 自动目录创建
- ✅ 可选云端上传
- ✅ 编码自定义

### 3. ☁️ upload_to_cloud - 云端上传
```python
await upload_to_cloud(
    file_path="/path/to/file.txt",
    upload_url="custom_url",    # 可选自定义URL
    custom_headers={}          # 可选自定义请求头
)
```

**功能特点**:
- ✅ 业务特定功能
- ✅ 自定义上传配置
- ✅ 文件大小限制
- ✅ 详细上传信息

### 4. 🔧 file_operations - 复杂操作
```python
# 正则搜索替换
await file_operations(
    operation="search_replace",
    file_path="/path/to/file.txt",
    search_pattern=r"(\d+)-(\d+)",
    replacement=r"\1****",
    use_regex=True
)

# 获取详细文件信息
await file_operations(
    operation="get_info",
    file_path="/path/to/file.txt"
)

# 批量处理
await file_operations(
    operation="batch_process",
    file_paths=["/file1", "/file2"],
    archive_path="/archive.zip"
)
```

**功能特点**:
- ✅ 正则表达式搜索替换
- ✅ 详细文件元数据
- ✅ 批量文件处理
- ✅ 校验和计算

## 📋 推荐命令行替代

**简单操作建议直接使用命令行，避免额外token消耗：**

| 操作 | 命令行替代 | 说明 |
|------|------------|------|
| 文件复制 | `cp source dest` | 简单直接，无需MCP工具 |
| 文件移动 | `mv source dest` | 系统原生，效率最高 |
| 文件删除 | `rm file` | 标准操作，支持通配符 |
| 目录列表 | `ls -la path` | 丰富的显示选项 |
| 递归列表 | `find path -type f` | 强大的查找功能 |
| 文件信息 | `stat file` | 详细的文件属性 |
| 下载文件 | `curl -o file URL` | 成熟的下载工具 |
| 创建压缩包 | `zip archive.zip files` | 标准压缩工具 |
| 解压文件 | `unzip archive.zip` | 原生解压功能 |
| 系统信息 | `df -h && free -h` | 系统监控命令 |
| 文件搜索 | `grep 'pattern' file` | 高效文本搜索 |
| 简单替换 | `sed 's/old/new/g' file` | 流编辑器替换 |

## 🛡️ 安全特性

### 路径安全验证
```python
# 防止路径遍历攻击
PROTECTED_PATHS = {
    '/System', '/usr/bin', '/usr/sbin', '/bin', '/sbin',
    '/Windows/System32', '/Windows/SysWOW64', '/Program Files'
}

# 危险文件类型检测
DANGEROUS_EXTENSIONS = {
    '.exe', '.bat', '.cmd', '.com', '.pif', '.scr', '.vbs', '.js'
}
```

### 权限和大小限制
- ✅ 读写权限验证
- ✅ 文件大小限制
- ✅ 编码安全检测
- ✅ 路径规范化

## 📊 优化效果对比

| 指标 | v1.0.0 | v2.0.0 (旧) | v2.1.0 (新) | 优化效果 |
|------|--------|-------------|-------------|----------|
| 工具数量 | 4个 | 15个 | 4个 | **精简73%** |
| 代码行数 | 207行 | 1133行 | 650行 | **减少43%** |
| Token使用 | 基础 | 高 | 优化 | **节省60-70%** |
| 选择复杂度 | 低 | 高 | 低 | **大幅降低** |
| 维护成本 | 低 | 高 | 中 | **显著下降** |

## 🧪 测试验证

运行测试脚本验证所有功能：

```bash
cd mcp_servers/file_system
python test_file_system.py
```

**测试结果**:
```
总测试数: 9
通过: 9 ✅
失败: 0 ❌
成功率: 100.0%
```

**测试覆盖**:
- ✅ 文件读取（基础、行范围）
- ✅ 文件写入（覆盖、追加）
- ✅ 搜索替换（简单、正则）
- ✅ 文件信息获取
- ✅ 编码检测
- ✅ 安全验证

## 🔧 配置说明

### 服务器配置
```python
# 默认端口
PORT = 34003

# 云存储配置
DEFAULT_UPLOAD_URL = "http://36.133.44.114:20034/askonce/api/v1/doc/upload"
DEFAULT_HEADERS = {"User-Source": 'AskOnce_backend'}

# 安全限制
MAX_FILE_SIZE_MB = 100  # 云端上传限制
DEFAULT_READ_LIMIT_MB = 10  # 默认读取限制
```

### MCP 客户端配置
```json
{
  "mcpServers": {
    "file_system": {
      "command": "python",
      "args": ["/path/to/file_system.py"],
      "env": {}
    }
  }
}
```

## 📖 使用示例

### 核心操作示例

```python
# 高级文件读取
result = await file_read(
    file_path="/path/to/config.json",
    start_line=10,
    end_line=50,
    encoding="auto"
)

# 智能文件写入
result = await file_write(
    file_path="/path/to/output.txt",
    content="新的配置内容",
    mode="append",
    auto_upload=True
)

# 正则搜索替换
result = await file_operations(
    operation="search_replace",
    file_path="/path/to/source.py",
    search_pattern=r'"debug":\s*true',
    replacement='"debug": false',
    use_regex=True
)

# 获取详细文件信息
result = await file_operations(
    operation="get_info",
    file_path="/path/to/data.csv"
)
```

### 命令行操作示例

```bash
# 简单文件操作（推荐用命令行）
cp source.txt backup.txt           # 文件复制
mv temp.txt archive/               # 文件移动
rm outdated.log                    # 文件删除
ls -la /project/                   # 目录列表
find . -name "*.py" -type f        # 文件查找
grep "TODO" *.py                   # 内容搜索
sed 's/old/new/g' config.txt       # 简单替换
```

## 🛠️ 依赖要求

```bash
pip install httpx fastmcp starlette uvicorn chardet
```

## 🚀 快速开始

1. **安装依赖**
```bash
pip install -r requirements.txt
```

2. **启动服务器**
```bash
python file_system.py
```

3. **配置MCP客户端**
```json
{
  "mcpServers": {
    "file_system": {
      "command": "python",
      "args": ["./file_system.py"]
    }
  }
}
```

## 🤝 最佳实践

### Token优化策略
- **简单操作**: 直接使用命令行，节省token
- **复杂操作**: 使用MCP工具，发挥其优势
- **批量操作**: 使用file_operations批处理
- **常见任务**: 优先考虑命令行方案

### 使用决策树
```
需要文件操作？
├─ 简单操作（复制、移动、删除）→ 使用命令行
├─ 读取文件
│  ├─ 简单读取 → cat/head/tail 命令
│  └─ 复杂需求（行范围、编码）→ file_read
├─ 写入文件
│  ├─ 简单写入 → echo/cat 重定向
│  └─ 复杂模式（追加、云端）→ file_write
├─ 搜索替换
│  ├─ 简单替换 → sed 命令
│  └─ 正则表达式 → file_operations
└─ 其他复杂操作 → file_operations
```

### 性能建议
- 文件大小 < 1MB → 优先命令行
- 复杂逻辑处理 → 使用MCP工具
- 批量操作 → file_operations批处理
- 云端集成 → 必须使用MCP工具

## 📞 技术支持

如有问题或建议，请联系开发团队或提交Issue。

---

**文件系统 v2.1.0** - 精简高效，专注核心，优化token使用的智能选择！ 