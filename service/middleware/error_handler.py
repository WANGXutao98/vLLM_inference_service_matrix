"""
错误处理中间件
提供统一的错误处理和响应格式
"""
import traceback
from typing import Union
from fastapi import Request, HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from http import HTTPStatus

from service.chat_protocol import ErrorResponse
from service.custom_protocol import CustomErrorResponse
from utils.logger import logger
from utils.monitor import report_metrics


class ErrorHandlerMiddleware:
    """错误处理中间件"""
    
    @staticmethod
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        """处理请求验证错误"""
        tags = {"ret_code": str(HTTPStatus.BAD_REQUEST.value)}
        report_methods = ["add"]
        report_metrics({"request_total": 1}, tags, report_methods, False)
        report_metrics({"request_failure": 1}, tags, report_methods, False)
        
        # 根据请求路径确定协议类型
        protocol = "default"
        if "/generate" in str(request.url):
            protocol = "custom"
        
        error_response = ErrorHandlerMiddleware._create_error_response(
            message=str(exc),
            error_type="ValidationError",
            status_code=HTTPStatus.BAD_REQUEST,
            protocol=protocol
        )
        
        return JSONResponse(error_response.dict(), status_code=HTTPStatus.BAD_REQUEST)
    
    @staticmethod
    async def http_exception_handler(request: Request, exc: HTTPException):
        """处理HTTP异常"""
        tags = {"ret_code": str(exc.status_code)}
        report_methods = ["add"]
        report_metrics({"request_total": 1}, tags, report_methods, False)
        report_metrics({"request_failure": 1}, tags, report_methods, False)
        
        protocol = "default"
        if "/generate" in str(request.url):
            protocol = "custom"
        
        error_response = ErrorHandlerMiddleware._create_error_response(
            message=exc.detail,
            error_type="HTTPException",
            status_code=HTTPStatus(exc.status_code),
            protocol=protocol
        )
        
        return JSONResponse(error_response.dict(), status_code=exc.status_code)
    
    @staticmethod
    async def general_exception_handler(request: Request, exc: Exception):
        """处理通用异常"""
        logger.error(f"Unhandled exception: {exc}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        
        tags = {"ret_code": str(HTTPStatus.INTERNAL_SERVER_ERROR.value)}
        report_methods = ["add"]
        report_metrics({"request_total": 1}, tags, report_methods, False)
        report_metrics({"request_failure": 1}, tags, report_methods, False)
        
        protocol = "default"
        if "/generate" in str(request.url):
            protocol = "custom"
        
        error_response = ErrorHandlerMiddleware._create_error_response(
            message="Internal server error",
            error_type="InternalServerError",
            status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
            protocol=protocol
        )
        
        return JSONResponse(error_response.dict(), status_code=HTTPStatus.INTERNAL_SERVER_ERROR)
    
    @staticmethod
    def _create_error_response(
        message: str,
        error_type: str = "BadRequestError",
        status_code: HTTPStatus = HTTPStatus.BAD_REQUEST,
        request_id: str = None,
        protocol: str = "default"
    ) -> Union[ErrorResponse, CustomErrorResponse]:
        """创建错误响应"""
        if protocol == "custom":
            return CustomErrorResponse(
                ret_msg=message,
                ret_code=status_code.value,
                request_id=request_id
            )
        else:
            return ErrorResponse(
                message=message,
                type=error_type,
                code=status_code.value,
                request_id=request_id
            )
