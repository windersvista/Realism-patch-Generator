@echo off
chcp 65001 >nul
echo ============================================================
echo EFT 现实主义数值生成器 v3.17
echo ============================================================
echo.

if exist ".venv\Scripts\python.exe" (
	".venv\Scripts\python.exe" generate_realism_patch.py
) else (
	python generate_realism_patch.py
)

echo.
echo ============================================================
echo 按任意键退出...
pause >nul
