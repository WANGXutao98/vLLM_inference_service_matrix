"""
优化的响应生成器
提供高性能的流式和完整响应生成
"""
import time
from typing import AsyncGenerator, AsyncIterator, List, Dict, Any
from fastapi import Request
from vllm.outputs import RequestOutput

from utils.logger import logger
from utils.monitor import report_metrics


class OptimizedResponseGenerator:
    """优化的响应生成器"""
    
    def __init__(self, protocol: str):
        self.protocol = protocol
        self._text_cache: Dict[str, str] = {}
        self._length_cache: Dict[str, int] = {}
    
    def get_delta_text(self, output_text: str, previous_text: str, cache_key: str) -> str:
        """高效计算增量文本"""
        if cache_key in self._text_cache:
            cached_text = self._text_cache[cache_key]
            if cached_text == previous_text:
                # 使用缓存的长度避免重复切片
                cached_length = self._length_cache.get(cache_key, 0)
                return output_text[cached_length:]
        
        # 计算增量并缓存
        delta_text = output_text[len(previous_text):]
        self._text_cache[cache_key] = previous_text
        self._length_cache[cache_key] = len(previous_text)
        
        return delta_text
    
    def clear_cache(self, cache_key: str):
        """清理缓存"""
        self._text_cache.pop(cache_key, None)
        self._length_cache.pop(cache_key, None)
    
    async def generate_stream_response(
        self,
        request,
        result_generator: AsyncIterator[RequestOutput],
        request_id: str,
        response_creator_func,
        tags: Dict[str, Any]
    ) -> AsyncGenerator[str, None]:
        """生成流式响应"""
        start_time = time.perf_counter()
        
        # 初始化状态数组
        n_choices = getattr(request, 'n', 1)
        previous_texts = [""] * n_choices
        previous_num_tokens = [0] * n_choices
        finish_reason_sent = [False] * n_choices
        has_report_first = [False] * n_choices
        
        async for res in result_generator:
            res: RequestOutput
            for output in res.outputs:
                i = output.index
                
                if finish_reason_sent[i]:
                    continue
                
                # 使用优化的增量文本计算
                cache_key = f"{request_id}_{i}"
                delta_text = self.get_delta_text(output.text, previous_texts[i], cache_key)
                previous_texts[i] = output.text
                previous_num_tokens[i] = len(output.token_ids)
                
                # 报告首包时间
                if not has_report_first[i] and previous_num_tokens[i] > 0:
                    has_report_first[i] = True
                    first_cost = round((time.perf_counter() - start_time) * 1000)
                    report_metrics({"first_pkg_cost_time": first_cost}, tags)
                    logger.info(f"{request_id}|response begin, index:{i}, first_cost:{first_cost}")
                
                if output.finish_reason is None:
                    # 生成增量响应
                    chunk_data = response_creator_func(
                        request_id=request_id,
                        index=i,
                        delta_text=delta_text,
                        finish_reason=None
                    )
                    yield f"data: {chunk_data.json(exclude_unset=True)}\n\n"
                else:
                    # 生成完成响应
                    prompt_tokens = len(res.prompt_token_ids)
                    final_usage = self._create_usage_info(prompt_tokens, previous_num_tokens[i])
                    
                    chunk_data = response_creator_func(
                        request_id=request_id,
                        index=i,
                        delta_text=delta_text,
                        finish_reason=output.finish_reason,
                        usage=final_usage
                    )
                    
                    # 报告性能指标
                    cost_time = round((time.perf_counter() - start_time) * 1000)
                    speed = 0 if cost_time <= 0 else final_usage.completion_tokens * 1000 / cost_time
                    report_metrics({"request_cost_time": cost_time, "speed": speed}, tags)
                    logger.info(f"{request_id}|Finish stream request, index:{i}, cost_time:{cost_time}, final_usage:{final_usage}, speed:{speed}")
                    
                    yield f"data: {chunk_data.json(exclude_unset=True, exclude_none=True)}\n\n"
                    finish_reason_sent[i] = True
                    
                    # 清理缓存
                    self.clear_cache(cache_key)
        
        # 发送结束标记
        yield "data: [DONE]\n\n"
        cost_time = round((time.perf_counter() - start_time) * 1000)
        logger.info(f"{request_id}|Finish stream request, cost_time:{cost_time}")
    
    async def generate_full_response(
        self,
        request,
        raw_request: Request,
        result_generator: AsyncIterator[RequestOutput],
        request_id: str,
        response_creator_func,
        tags: Dict[str, Any]
    ):
        """生成完整响应"""
        start_time = time.perf_counter()
        final_res: RequestOutput = None
        
        async for res in result_generator:
            if await raw_request.is_disconnected():
                # 处理客户端断开连接
                await self._handle_client_disconnect(request_id)
                return self._create_disconnect_error_response(request_id)
            final_res = res
        
        assert final_res is not None
        
        # 创建响应
        response = response_creator_func(final_res, request, request_id)
        
        # 报告性能指标
        cost_time = round((time.perf_counter() - start_time) * 1000)
        speed = 0 if cost_time <= 0 else response.usage.completion_tokens * 1000 / cost_time
        report_metrics({"request_cost_time": cost_time, "speed": speed}, tags)
        
        logger.info(f"{request_id}|Finish request, cost_time:{cost_time}, usage:{response.usage}")
        return response
    
    def _create_usage_info(self, prompt_tokens: int, completion_tokens: int):
        """创建使用情况信息"""
        from service.chat_protocol import UsageInfo
        return UsageInfo(
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=prompt_tokens + completion_tokens,
        )
    
    async def _handle_client_disconnect(self, request_id: str):
        """处理客户端断开连接"""
        # 这里应该调用engine.abort，但需要engine实例
        logger.warning(f"Client disconnected for request {request_id}")
    
    def _create_disconnect_error_response(self, request_id: str):
        """创建断开连接错误响应"""
        from service.core.base_engine import ErrorHandler
        return ErrorHandler.create_error_response(
            message="Client disconnected",
            error_type="ClientDisconnected",
            request_id=request_id,
            protocol=self.protocol
        )
