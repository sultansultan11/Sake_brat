@echo off
rem Fonda (start_hidden.vbs orqali) ishlayotgan botni to'xtatadi.
cd /d "%~dp0"
powershell -NoProfile -Command "$d = (Get-Location).Path + '\'; $p = Get-CimInstance Win32_Process | Where-Object { $_.ExecutablePath -and $_.ExecutablePath.StartsWith($d, 'OrdinalIgnoreCase') -and $_.CommandLine -like '*main.py*' }; if ($p) { $p | ForEach-Object { Stop-Process -Id $_.ProcessId -Force }; exit 0 } else { exit 1 }"
if errorlevel 1 (
    echo Ishlab turgan bot topilmadi.
) else (
    echo Bot to'xtatildi.
)
echo.
pause
