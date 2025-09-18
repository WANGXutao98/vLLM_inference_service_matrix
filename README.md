# vLLM推理框架

基于过去工作中实现的基于vLLM Inference Framework，目前已将代码框架部分抽象，以支持多种协议和自定义扩展。

## 特性

- 🚀 **高性能**: 基于vLLM的高效推理引擎
- 🔌 **多协议支持**: OpenAI Chat API、Completion API和自定义协议
- 🛡️ **安全可靠**: 完善的错误处理和安全验证
- 📊 **监控完备**: 内置指标收集和性能监控
- 🔧 **易于扩展**: 插件化架构，支持自定义处理器
- 🐳 **容器化**: 完整的Docker支持

## 快速开始

### 环境要求

- Python 3.8+
- CUDA 11.8+ (GPU推理)
- 8GB+ GPU内存

### 安装

```bash
# 克隆仓库
git clone <repository-url>
cd vLLM-Inference-Framework

# 安装依赖
pip install -r requirements.txt

# 配置模型
cp conf/model_config.json.example conf/model_config.json
# 编辑配置文件，设置模型路径和参数
```

### 运行服务

```bash
# 使用默认配置启动
python service/vllm_infer_service.py --model-name your_model_name

# 自定义配置启动
python service/vllm_infer_service.py \
    --model-name your_model_name \
    --host 0.0.0.0 \
    --port 8000 \
    --tensor-parallel-size 1
```

### Docker运行

```bash
# 构建镜像
docker build -t vllm-inference .

# 运行容器
docker run -d \
    --gpus all \
    -p 8000:8000 \
    -v /path/to/models:/models \
    vllm-inference \
    --model-name your_model_name
```

## API使用

### Chat API

```bash
curl -X POST "http://localhost:8000/chat/completions" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "your_model",
    "messages": [
      {"role": "user", "content": "Hello, how are you?"}
    ],
    "temperature": 0.7,
    "max_tokens": 100
  }'
```

### Completion API

```bash
curl -X POST "http://localhost:8000/completions" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "your_model",
    "prompt": "Complete this sentence: The future of AI is",
    "temperature": 0.7,
    "max_tokens": 100
  }'
```

### Custom API

```bash
curl -X POST "http://localhost:8000/generate" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "your_model",
    "prompt": "Your custom prompt",
    "system_info": "System instructions",
    "history_input": ["Previous input"],
    "history_output": ["Previous output"],
    "temperature": 0.7,
    "max_tokens": 100
  }'
```

## 配置说明

### 模型配置

编辑 `conf/model_config.json`:

```json
{
  "your_model_name": {
    "class_name": "OpenAIServingChat",
    "model_path": "/path/to/your/model",
    "max_model_len": 4096,
    "chat_template": "/path/to/chat_template.jinja",
    "response_role": "assistant"
  }
}
```

### 环境变量

```bash
# 服务配置
export SERVICE_PORT=8000
export MODEL_NAME=your_model_name

# Polaris服务发现
# Rainbow配置中心
```

## 架构设计

### 核心组件

- **ServingEngine**: 基础服务引擎抽象
- **ResponseGenerator**: 优化的响应生成器
- **ErrorHandler**: 统一错误处理
- **MetricsReporter**: 指标收集和报告

### 协议支持

- **Chat Protocol**: OpenAI Chat API兼容
- **Completion Protocol**: OpenAI Completion API兼容  
- **Custom Protocol**: 自定义协议，支持历史对话

### 扩展机制

框架支持通过插件系统进行扩展:

```python
from service.core import BaseServingEngine

class CustomServingEngine(BaseServingEngine):
    def create_prompt(self, request, raw_request):
        # 自定义提示词处理
        return custom_prompt
    
    def create_error_response(self, message, **kwargs):
        # 自定义错误响应
        return custom_error_response
```

## 监控和日志

### 指标监控

框架自动收集以下指标:

- 请求总数和成功率
- 响应时间和首包时间
- Token使用统计
- 错误率统计

### 日志配置

日志支持多种输出方式:

- 控制台输出
- 文件输出
- 远程日志服务 (支持智眼日志)

## 性能优化

### 已实现的优化

- ✅ 字符串操作优化
- ✅ 响应缓存机制
- ✅ 异步文件操作
- ✅ 内存使用优化

### 建议配置

- 使用GPU推理: `--tensor-parallel-size 1`
- 调整并发数: `--limit-concurrency 100`
- 优化内存: `--max-model-len 4096`

## 安全特性

- ✅ 输入验证和路径遍历防护
- ✅ 动态类加载白名单
- ✅ 敏感信息环境变量化
- ✅ 错误信息脱敏

## 开发指南

### 代码规范

- 使用Python 3.8+类型注解
- 遵循PEP 8代码风格
- 添加完整的文档字符串
- 编写单元测试

### 贡献流程

1. Fork项目
2. 创建特性分支
3. 提交代码并添加测试
4. 创建Pull Request

### 测试

```bash
# 运行单元测试
python -m pytest tests/

# 运行集成测试
python -m pytest tests/integration/

# 性能测试
python tools/benchmark.py
```


### v1.0.0
- 初始版本发布
- 支持多种协议
- 基础监控和日志功能
- Docker支持