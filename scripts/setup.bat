@echo off
echo ================================
echo VisionDrive 项目初始化
echo ================================

echo.
echo [1/3] 初始化前端...
cd /d %~dp0..\frontend
call npm install

echo.
echo [2/3] 初始化算法服务...
cd /d %~dp0..\algorithm
python -m venv venv
call venv\Scripts\activate
pip install -r requirements.txt

echo.
echo [3/3] 初始化后端 (请用IDE打开backend目录)...
echo 使用 IntelliJ IDEA / Eclipse 导入 backend 目录作为 Maven 项目

echo.
echo ================================
echo 初始化完成!
echo ================================
pause
