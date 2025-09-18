"""
基础引擎抽象类
提供通用的功能和服务接口
"""
import time
from abc import ABC, abstractmethod
from typing import AsyncGenerator, AsyncIterator, Union, Optional, List, Callable
from fastapi import Request
from http import HTTPStatus

from vllm.engine.async_llm_engine import AsyncLLMEngine
from vllm.outputs import RequestOutput
from utils.logger import logger
from utils.monitor import report_metrics


class BaseServingEngine(ABC):
    """基础服务引擎抽象类"""
    
    def __init__(self, engine: AsyncLLMEngine, served_model: str, protocol: str = "default", *args, **kwargs):
        self.engine = engine
        self.served_model = served_model
        self.protocol = protocol
        self.max_model_len = 0
        self.tokenizer = None
        self.post_process: Optional[Callable] = None

    @abstractmethod
    def create_prompt(self, request, raw_request: Request) -> str:
        """创建提示词"""
        pass

    @abstractmethod
    def create_error_response(self, message: str, **kwargs):
        """创建错误响应"""
        pass

    def report_tokens(self, usage, tags: dict):
        """报告token使用情况"""
        tags.update({"protocol": self.protocol})
        metrics_map = {
            "prompt_tokens": usage.prompt_tokens,
            "completion_tokens": usage.completion_tokens,
            "total_tokens": usage.total_tokens,
        }
        report_metrics(metrics_map, tags)

    def report_performance_metrics(self, start_time: float, usage, tags: dict):
        """报告性能指标"""
        cost_time = round((time.perf_counter() - start_time) * 1000)
        speed = 0 if cost_time <= 0 else usage.completion_tokens * 1000 / cost_time
        report_metrics({"request_cost_time": cost_time, "speed": speed}, tags)

    def report_first_token_metrics(self, start_time: float, tags: dict):
        """报告首包时间指标"""
        first_cost = round((time.perf_counter() - start_time) * 1000)
        report_metrics({"first_pkg_cost_time": first_cost}, tags)
        return first_cost


class MetricsReporter:
    """统一的指标报告器"""
    
    def __init__(self, protocol: str):
        self.protocol = protocol
    
    def report_request_metrics(self, request, tags: dict):
        """报告请求指标"""
        base_tags = {
            "model": request.model,
            "stream": str(request.stream),
            "protocol": self.protocol
        }
        base_tags.update(tags)
        report_metrics({"request_total": 1}, base_tags, ["add"])
    
    def report_success_metrics(self, tags: dict):
        """报告成功指标"""
        report_metrics({"request_success": 1}, tags, ["add"])
    
    def report_failure_metrics(self, tags: dict):
        """报告失败指标"""
        report_metrics({"request_failure": 1}, tags, ["add"])


class ErrorHandler:
    """统一错误处理器"""
    
    @staticmethod
    def create_error_response(
        message: str,
        error_type: str = "BadRequestError",
        status_code: HTTPStatus = HTTPStatus.BAD_REQUEST,
        request_id: Optional[str] = None,
        protocol: str = "default"
    ):
        """创建错误响应"""
        if protocol == "custom":
            from service.custom_protocol import CustomErrorResponse
            return CustomErrorResponse(ret_msg=message, ret_code=status_code.value, request_id=request_id)
        else:
            from service.chat_protocol import ErrorResponse
            return ErrorResponse(message=message, type=error_type, code=status_code.value, request_id=request_id)
