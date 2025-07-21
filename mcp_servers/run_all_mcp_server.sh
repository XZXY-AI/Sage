#!/bin/bash

echo "正在后台启动 Serper Search 服务器..."
nohup uv run search/serper_search.py --api_key adb3d320bd42b810c1b7e795104cd753af7cc591 &

echo "正在后台启动 Match Data 服务器..."
nohup uv run search/match_data_server.py &

echo "所有服务器已通过 nohup 在后台启动，断开SSH后将继续运行。"