import re
from abc import ABC, abstractmethod
from fastapi import Request
from typing import Union, Optional, List, Dict, Pattern

from service.serving_chat import OpenAIServingChat
from service.chat_protocol import ChatCompletionRequest

class TextPostProcessor(ABC):
    """文本后处理器接口：定义文本处理逻辑的统一规范"""
    @abstractmethod
    def process(self, text: str) -> str:
        """处理文本，返回处理后结果"""
        pass


class MessageContentExtractor(ABC):
    """消息内容提取器接口：定义不同角色（user/assistant）的内容提取逻辑"""
    @abstractmethod
    def extract(self, role: str, content: str) -> Optional[str]:
        """
        从消息内容中提取目标内容
        :param role: 消息角色（如"user"、"assistant"）
        :param content: 原始消息内容
        :return: 提取到的内容（无匹配则返回None）
        """
        pass


class PromptTemplate(ABC):
    """Prompt模板接口：定义Prompt生成的统一规范"""
    @abstractmethod
    def render(self, input_content: str) -> str:
        """
        根据输入内容生成最终Prompt
        :param input_content: 提取后的核心输入内容
        :return: 格式化后的Prompt字符串
        """
        pass


class PromptValidator(ABC):
    """Prompt验证与Token化接口：定义验证和Token处理规范"""
    @abstractmethod
    def validate_and_tokenize(
        self,
        request: Union[ChatCompletionRequest],
        prompt: Optional[str] = None,
        prompt_ids: Optional[List[int]] = None
    ) -> Optional[List[int]]:
        """
        验证Prompt并进行Token化处理
        :param request: 聊天请求对象
        :param prompt: 生成的Prompt（可选）
        :param prompt_ids: 预生成的Prompt Token（可选）
        :return: Token列表（或None，根据业务需求）
        """
        pass

class StripLeftPostProcessor(TextPostProcessor):
    """默认文本后处理器：实现原post_process的左空格清除逻辑"""
    def process(self, text: str) -> str:
        return text.lstrip()


class LuaContentExtractor(MessageContentExtractor):
    """Lua代码块提取器：实现原user/assistant的Lua代码块提取逻辑"""
    def __init__(
        self,
        user_pattern: Pattern[str] = re.compile(r"^```lua\n([\s\S]*?)```$"),
        assistant_pattern: Pattern[str] = re.compile(r"^```lua\n([\s\S]*?)$")
    ):
        """
        初始化Lua提取器，支持自定义正则（提升灵活性，如适配不同代码块格式）
        :param user_pattern: 用户消息的Lua匹配正则
        :param assistant_pattern: 助手消息的Lua匹配正则
        """
        self.role_patterns: Dict[str, Pattern[str]] = {
            "user": user_pattern,
            "assistant": assistant_pattern
        }

    def extract(self, role: str, content: str) -> Optional[str]:
        # 获取当前角色对应的正则（无匹配角色时返回原始内容）
        pattern = self.role_patterns.get(role)
        if not pattern:
            return content
        
        # 提取匹配内容（原逻辑的findall取第一个结果）
        match_result = pattern.findall(content)
        return match_result[0] if match_result else content


class InstructionPromptTemplate(PromptTemplate):
    """指令型Prompt模板：实现原create_prompt的硬编码模板逻辑"""
    def __init__(self, template: str = None):
        """
        初始化模板，支持自定义模板（默认使用原有INSTRUCTION格式）
        :param template: 自定义Prompt模板（需包含"{input}"占位符）
        """
        self.template = template or (
            "Below is an instruction that describes a task. "
            "Write a response that appropriately completes the request.\n\n"
            "### Instruction:\n{input}\n\n### Response:"
        )

    def render(self, input_content: str) -> str:
        # 替换模板中的占位符，生成最终Prompt
        return self.template.format(input=input_content)


class DefaultPromptValidator(PromptValidator):
    """默认Prompt验证器：实现原_validate_prompt_and_tokenize的空逻辑"""
    def validate_and_tokenize(
        self,
        request: Union[ChatCompletionRequest],
        prompt: Optional[str] = None,
        prompt_ids: Optional[List[int]] = None
    ) -> Optional[List[int]]:
        return None  # 保持原有空实现


# ------------------------------ 抽象化后的核心Agent类------------------------------
class GameAgent(OpenAIServingChat):
    """抽象化后的GameAgent：依赖接口而非硬编码，支持灵活配置"""
    def __init__(
        self,
        post_processor: TextPostProcessor,
        content_extractor: MessageContentExtractor,
        prompt_template: PromptTemplate,
        prompt_validator: PromptValidator,
        *args,
        **kwargs
    ):
        """
        构造函数：通过依赖注入传入所有具体实现（解耦硬编码）
        :param post_processor: 文本后处理器（如清除空格）
        :param content_extractor: 消息内容提取器（如Lua代码块提取）
        :param prompt_template: Prompt模板（如指令型模板）
        :param prompt_validator: Prompt验证器（如Token化处理）
        :param args: 父类OpenAIServingChat的位置参数
        :param kwargs: 父类OpenAIServingChat的关键字参数
        """
        super().__init__(*args, **kwargs)
        # 注入依赖（而非硬编码实现）
        self.post_processor = post_processor
        self.content_extractor = content_extractor
        self.prompt_template = prompt_template
        self.prompt_validator = prompt_validator

    def _format_message(self, message: Dict[str, str]) -> Dict[str, str]:
        """格式化消息：使用注入的提取器处理内容（原逻辑抽象化）"""
        role = message.get("role", "")
        original_content = message.get("content", "")
        
        # 调用提取器提取内容（替换原硬编码的正则判断）
        extracted_content = self.content_extractor.extract(role, original_content)
        message["content"] = self.post_processor.process(extracted_content)  # 后处理
        
        return message

    def create_prompt(self, request: ChatCompletionRequest, raw_request: Request) -> str:
        """创建Prompt：使用注入的模板生成（原硬编码模板抽象化）"""
        # 校验消息非空（保留原异常逻辑）
        if len(request.messages) < 1:
            raise Exception("messages为空")
        
        # 格式化最后一条消息（保留原逻辑）
        last_message = self._format_message(request.messages[-1])
        core_input = last_message["content"]
        
        # 调用模板生成Prompt（替换原硬编码的INSTRUCTION）
        return self.prompt_template.render(core_input)

    def _validate_prompt_and_tokenize(
        self,
        request: Union[ChatCompletionRequest],
        prompt: Optional[str] = None,
        prompt_ids: Optional[List[int]] = None
    ) -> Optional[List[int]]:
        """验证与Token化：委托给注入的验证器（原空逻辑抽象化）"""
        return self.prompt_validator.validate_and_tokenize(request, prompt, prompt_ids)


def create_default_game_agent(*args, **kwargs) -> GameAgent:
    """创建默认配置的GameAgent（保留原有全部逻辑，方便快速使用）"""
    # 组装默认依赖（与原代码逻辑完全一致）
    default_post_processor = StripLeftPostProcessor()
    default_content_extractor = LuaContentExtractor()
    default_prompt_template = InstructionPromptTemplate()
    default_validator = DefaultPromptValidator()
    
    return GameAgent(
        post_processor=default_post_processor,
        content_extractor=default_content_extractor,
        prompt_template=default_prompt_template,
        prompt_validator=default_validator,
        *args,
        **kwargs
    )