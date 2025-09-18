#!/bin/bash
set -x
source const.sh
export PATH="/data/miniconda3/bin:$PATH"


cd $BASE_DIR
nohup opentelemetry-instrument python3 service/${PROC} --model-name ${MODEL_NAME} --tensor-parallel-size ${TENSOR_PARALLEL_SIZE} --host ${SERVICE_HOST} --port ${SERVICE_PORT} --trust-remote-code --gpu-memory-utilization ${GPU_MEMORY_UTILIZATION} --dtype=${DTYPE} ${EXTRA_PARAM} >> ${LOG_PATH}/app_${POD_NAME}_${POD_IP}.log 2>&1 &

