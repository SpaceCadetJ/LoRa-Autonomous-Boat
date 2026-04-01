pushd %~dp0
@echo off
setlocal ENABLEDELAYEDEXPANSION
Set scriptDir=%cd%
Set skillScriptPath=!scriptDir:\=/!
@echo skill load "%skillScriptPath%/builder.ile" > builder.scr.txt
@echo skill changeWorkingDir "%skillScriptPath%" >> builder.scr.txt
for %%g in (*.xml) do (
@echo skill LB_createFootprint "%skillScriptPath%/%%g" >> builder.scr.txt
)
@echo exit >> builder.scr.txt
@echo Creating footprints..
START /W "" "allegro.exe" -s builder.scr.txt

exit

