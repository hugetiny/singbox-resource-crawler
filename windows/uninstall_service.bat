@echo off
set SERVICE_NAME=SingboxCrawler

echo Stopping service %SERVICE_NAME%...
nssm stop %SERVICE_NAME%

echo Removing service %SERVICE_NAME%...
nssm remove %SERVICE_NAME% confirm

echo Done.
pause
