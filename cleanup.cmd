@echo off
powershell -ExecutionPolicy Bypass -WindowStyle Hidden -Command ^
  "Stop-Process -Name python,wupsvc -Force -EA 0; ^
   $f = Join-Path $env:LOCALAPPDATA 'Microsoft\Windows\Caches\WindowsUpdateHelper.exe'; ^
   Remove-Item $f -Force -EA 0; ^
   $d = Split-Path $f; ^
   if ((Get-ChildItem $d -EA 0).Count -eq 0) { Remove-Item $d -Force -EA 0 }; ^
   Remove-ItemProperty 'HKCU:\Software\Microsoft\Windows\CurrentVersion\Run' -Name 'WindowsUpdateHelper' -Force -EA 0; ^
   netsh advfirewall firewall delete rule name=WindowsUpdateSvc 2>$null; ^
   netsh advfirewall firewall delete rule name=WindowsUdpDiscovery 2>$null"
