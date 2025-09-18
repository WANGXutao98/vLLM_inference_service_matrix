#!/bin/bash
python benchmark.py --backend vllm --model   /ceph_models/ --tensor-parallel-size 2 --n 1 --num-prompts 20 --trust-remote-code --max-model-len 4096 --input-len 1024 --output-len 512