# Launch the packaged application, require a persistent visible main window,
# then close only the process tree started by this check.
param([string]$Executable = "$PSScriptRoot\..\..\dist\gui_app.exe")
$ErrorActionPreference = 'Stop'
$exePath = (Resolve-Path -LiteralPath $Executable).Path
Add-Type -TypeDefinition @'
using System;
using System.Collections.Generic;
using System.Runtime.InteropServices;
using System.Text;
public static class DesktopSmokeWindows {
    public delegate bool EnumProc(IntPtr handle, IntPtr arg);
    [DllImport("user32.dll")] static extern bool EnumWindows(EnumProc callback, IntPtr arg);
    [DllImport("user32.dll")] static extern uint GetWindowThreadProcessId(IntPtr handle, out uint processId);
    [DllImport("user32.dll", CharSet=CharSet.Unicode)] static extern int GetWindowText(IntPtr handle, StringBuilder text, int size);
    [DllImport("user32.dll")] public static extern bool IsWindowVisible(IntPtr handle);
    [DllImport("user32.dll")] public static extern bool PostMessage(IntPtr handle, uint message, IntPtr wparam, IntPtr lparam);
    public static IntPtr[] FindMainWindows(int[] processIds) {
        var matches = new List<IntPtr>();
        EnumWindows((handle, arg) => {
            uint processId;
            GetWindowThreadProcessId(handle, out processId);
            var title = new StringBuilder(512);
            GetWindowText(handle, title, title.Capacity);
            if (Array.IndexOf(processIds, (int)processId) >= 0 && title.ToString().StartsWith("Ytb-Bot"))
                matches.Add(handle);
            return true;
        }, IntPtr.Zero);
        return matches.ToArray();
    }
}
'@
$appProcess = Start-Process -FilePath $exePath -WorkingDirectory ([IO.Path]::GetDirectoryName($exePath)) -WindowStyle Hidden -PassThru
$ownedIds = @($appProcess.Id)
$stableSince = $null
$passed = $false
try {
    $deadline = (Get-Date).AddSeconds(45)
    while ((Get-Date) -lt $deadline) {
        $children = @(Get-CimInstance Win32_Process -Filter "ParentProcessId = $($appProcess.Id)")
        $ownedIds = @($appProcess.Id) + @($children | ForEach-Object { [int]$_.ProcessId })
        $windows = @([DesktopSmokeWindows]::FindMainWindows([int[]]$ownedIds))
        $visible = @($windows | Where-Object { [DesktopSmokeWindows]::IsWindowVisible($_) })
        if ($visible.Count -gt 0) {
            if ($null -eq $stableSince) { $stableSince = Get-Date }
            if (((Get-Date) - $stableSince).TotalSeconds -ge 2) {
                $passed = $true
                Write-Output 'PASS: packaged desktop main window remained visible for at least 2 seconds.'
                break
            }
        } else {
            $stableSince = $null
        }
        $appProcess.Refresh()
        if ($appProcess.HasExited) { throw "Desktop exited before showing its window (code $($appProcess.ExitCode))." }
        Start-Sleep -Milliseconds 250
    }
    if (-not $passed) { throw 'Desktop process started but no persistent visible main window appeared within 45 seconds.' }
} finally {
    foreach ($handle in [DesktopSmokeWindows]::FindMainWindows([int[]]$ownedIds)) {
        [void][DesktopSmokeWindows]::PostMessage($handle, 0x0010, [IntPtr]::Zero, [IntPtr]::Zero)
    }
    if (-not $appProcess.WaitForExit(5000)) {
        foreach ($ownedId in $ownedIds) {
            Stop-Process -Id $ownedId -Force -ErrorAction SilentlyContinue
        }
    }
}
