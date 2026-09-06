@echo off
REM 统一最终 Gate：语法编译检查 + 单元测试。通过后才允许 DONE。
cd /d %~dp0
python -m compileall -q boss_archiver tests
if errorlevel 1 ( echo [FAIL] compileall & exit /b 1 )
python -m pytest -q tests
if errorlevel 1 ( echo [FAIL] pytest & exit /b 1 )
echo [PASS] check gate
