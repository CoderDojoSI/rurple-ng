REM replace with a real build system ASAP!

C:\Python26\python.exe setup.py py2exe
"C:\Program Files\Windows Installer XML v3\bin\candle.exe" -out build\rurple.wixobj rurple.wxs
"C:\Program Files\Windows Installer XML v3\bin\light.exe" -out build\rurple.msi build\rurple.wixobj
