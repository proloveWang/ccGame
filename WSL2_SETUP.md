# WSL2 安装排错与离线安装手册

本文件记录 **Windows 上把 WSL2 装成功** 的完整过程，重点是绕开 `wsl --install` 报 **HTTP 403（已禁止）** 的处理办法。

> 适用场景：在 Windows 上执行 `wsl --install -d Ubuntu` 报 403 / 无法从 Microsoft Store 获取分发包，但目标是得到一台能跑 Buildozer 的 Ubuntu。
> 装好之后打包 APK 的步骤见 [BUILD_ANDROID.md](BUILD_ANDROID.md)。

---

## 目录

- [1. 问题现象](#1-问题现象)
- [2. 根因分析](#2-根因分析)
- [3. 实测证据（本机）](#3-实测证据本机)
- [4. 正确安装流程（4 步）](#4-正确安装流程4-步)
- [5. 每步的验证方法](#5-每步的验证方法)
- [6. 装好之后做什么](#6-装好之后做什么)
- [7. 常见问题](#7-常见问题)
- [8. 不想装 WSL 的替代方案](#8-不想装-wsl-的替代方案)

---

## 1. 问题现象

在普通（非管理员）PowerShell 里执行：

```powershell
wsl --install -d Ubuntu
```

返回：

```
已禁止(403)。
```

同一条命令此前还会看到一个提示：

```
按任意键安装适用于 Linux 的 Windows 子系统。
按 CTRL-C 或关闭此窗口以取消。
此提示将在 60 秒后超时。
```

说明 **WSL 功能本身没有启用**，`wsl.exe` 正在引导你去安装。

## 2. 根因分析

403 与「网络被墙」无关，是**分发通道**的问题，叠加两个前置条件：

1. **`C:\Windows\System32\wsl.exe` 是 Windows 11 24H2 的内置「存根版」**（本例版本 `10.0.26100.1710`）。它的 `--help` 只有四个参数：

   ```
   --install / --update / --status / --help
   ```

   没有 `--import`、`--web-download`、`-d <发行版>` 的本地能力。它唯一能做的事，就是从 **Microsoft Store 分发通道** 下载完整的 WSL 包 —— 403 就发生在这个下载环节。

2. **WSL 可选功能未启用**：系统里查不到 `LxssManager` 服务，`wsl --help` 只打印安装引导而不是真正的帮助。

3. **当前进程不是管理员**：`whoami /groups` 显示 `BUILTIN\Administrators ... Group used for deny only` + `Mandatory Label\Medium`，即账号在管理员组但 UAC 未提权。非管理员上下文 + 功能未启用时，`wsl --install` 只能走 Store 用户级安装，被拦即 403。

**结论：不是命令写错，也不是网络问题。正确路径是「手动启用可选功能 → 绕开 Store 安装 WSL 本体 → 用 --web-download 或离线 rootfs 装发行版」。**

## 3. 实测证据（本机）

排查时执行的只读检查项与结果：

| 检查项 | 命令 | 结果 | 判断 |
| --- | --- | --- | --- |
| wsl.exe 版本 | `(Get-Item C:\Windows\System32\wsl.exe).VersionInfo.FileVersion` | `10.0.26100.1710` | 24H2 存根版 |
| wsl 能力 | `wsl --help` | 只有 install/update/status/help | 无 import / web-download |
| WSL 服务 | `Get-Service LxssManager` | **不存在** | WSL 功能未启用 |
| 虚拟化平台 | `Get-Service vmcompute,hns` | 均 Running | Hyper-V 相关平台在跑 |
| 虚拟化 | `(Get-CimInstance Win32_ComputerSystem).HypervisorPresent` | `True` | 虚拟化可用，WSL2 满足前提 |
| 固件虚拟化 | `(Get-CimInstance Win32_Processor).VirtualizationFirmwareEnabled` | `False` | Hypervisor 已接管时该字段常为 False，**不代表 VT 关闭** |
| 管理员 | `whoami /groups` | Medium 完整性 | 需提权 |
| Store 包 | `Get-AppxPackage Microsoft.WindowsStore` | `Status = Ok` | Store 本体正常 |
| Store 策略 | `HKLM:\SOFTWARE\Policies\Microsoft\WindowsStore` | 键不存在 | 未被组策略禁用 |
| 代理 | `netsh winhttp show proxy` | 直接访问 | 无代理干扰 |
| 网络 | HEAD `aka.ms/wslinstall` / `github.com` / `cloud-images.ubuntu.com` / `dl.google.com` | 全部 **200** | 网络可达 |
| 系统版本 | `Win32_OperatingSystem` | Windows 11 Pro `10.0.26100` | 24H2 |

## 4. 正确安装流程（4 步）

> 全程需要 **管理员权限**，第 1 步之后**必须重启**。

### 第 1 步：启用两个 Windows 可选功能

右键开始菜单 → **终端(管理员)**：

```powershell
dism.exe /online /enable-feature /featurename:Microsoft-Windows-Subsystem-Linux /all /norestart
dism.exe /online /enable-feature /featurename:VirtualMachinePlatform /all /norestart
```

两条都应显示「操作成功完成」。

### 第 2 步：重启电脑

必须重启，`LxssManager` 等服务要在启动时重新注册。

### 第 3 步：安装 WSL 本体（绕开 Store，走 GitHub）

重启后仍用**管理员**窗口。先试官方推荐的网页下载方式：

```powershell
wsl --update --web-download
```

若仍 403、或提示不认识 `--web-download`，直接装官方 MSI（GitHub release 通道）：

```powershell
curl.exe -L -o "$env:TEMP\wsl.msi" https://github.com/microsoft/WSL/releases/download/3.0.5/wsl.3.0.5.0.x64.msi
msiexec /i "$env:TEMP\wsl.msi" /qn
wsl --version
```

> MSI 约 367 MB。地址里的 `3.0.5` 是撰写本文时的最新版，若已更新，到 <https://github.com/microsoft/WSL/releases/latest> 取同名的 `wsl.<版本>.0.x64.msi`。

### 第 4 步：安装 Ubuntu 发行版

```powershell
wsl --set-default-version 2
wsl --install -d Ubuntu --web-download
```

`--web-download` 是绕 403 的关键：它让 WSL 从网页（GitHub）而不是 Store 拉取发行版。

首次进入需要设置 UNIX 用户名和密码（密码输入时不回显，正常）。

若这一步仍然 403，改用下面两种兜底之一：

**兜底 A：Microsoft Store 客户端手动安装**

打开 Microsoft Store → 搜索 `Ubuntu 24.04` → 安装 → 启动一次完成初始化。

**兜底 B：官方 rootfs 离线导入（完全不依赖任何分发通道）**

```powershell
# 1) 下载 Ubuntu 24.04 的 WSL rootfs（约 500 MB，站点较慢，耐心等）
curl.exe -L -o "$env:TEMP\noble.tar.gz" https://cloud-images.ubuntu.com/wsl/noble/current/ubuntu-noble-wsl-amd64-wsl.rootfs.tar.gz

# 2) 建目录并导入为名为 Ubuntu 的发行版
New-Item -ItemType Directory -Force C:\WSL\Ubuntu | Out-Null
wsl --import Ubuntu C:\WSL\Ubuntu "$env:TEMP\noble.tar.gz" --version 2

# 3) 进入（默认是 root）
wsl -d Ubuntu
```

导入的发行版默认用户是 root，可在 Ubuntu 内创建普通用户并设为默认：

```bash
adduser --gecos "" dev
usermod -aG sudo dev
printf '[user]\ndefault=dev\n' > /etc/wsl.conf
exit
```

然后回到 PowerShell 执行 `wsl --terminate Ubuntu`，下次进入即为 `dev` 用户。

## 5. 每步的验证方法

| 阶段 | 命令 | 期望结果 |
| --- | --- | --- |
| 功能已启用 | `Get-Service LxssManager` | 服务存在（Stopped 属正常） |
| WSL 本体已装 | `wsl --version` | 打印 `WSL 版本: x.x.x.x`、内核版本等 |
| 发行版已注册 | `wsl -l -v` | 列出 `Ubuntu`，且 `VERSION` 为 `2` |
| 能进系统 | `wsl -d Ubuntu -- uname -a` | 输出 `Linux ... x86_64 GNU/Linux` |

## 6. 装好之后做什么

进入 Ubuntu，按 [BUILD_ANDROID.md](BUILD_ANDROID.md) 执行：

1. **2.2 节**：`apt install` 打包所需系统依赖（含 `openjdk-17-jdk`）；
2. **2.3 节**：建 venv 装 `buildozer`；
3. **2.4 节**：把项目复制进 Linux 文件系统（**不要**在 `/mnt/e` 下构建）；
4. **2.5 节**：`buildozer -v android debug`。

> 注意：WSL 是**新装的空系统**，Windows 侧已装的 Python / pygame 与它无关，一切依赖都要在 Ubuntu 内重新装。

## 7. 常见问题

| 现象 | 原因 | 处理 |
| --- | --- | --- |
| DISM 报「需要提升」 | 窗口不是管理员 | 开始菜单搜索 PowerShell → 右键「以管理员身份运行」 |
| 重启后 `wsl --version` 仍提示「若要安装…」 | 功能刚启用但 WSL 本体还没装 | 继续第 3 步装 MSI |
| `wsl --install -d Ubuntu` 依旧 403 | 发行版分发通道仍被拦 | 加 `--web-download`；或走兜底 A/B |
| `wsl -l -v` 显示 VERSION 为 1 | 默认版本未设为 2 | `wsl --set-default-version 2`，必要时 `wsl --set-version Ubuntu 2` |
| 报 `WSL 2 requires an update to its kernel component` | 内核组件缺失 | `wsl --update`，或装上面的 MSI |
| `wsl --import` 报文件不存在 | curl 下载失败或路径含中文/空格 | 确认 `$env:TEMP\noble.tar.gz` 有约 500 MB，路径用绝对路径 |
| 进入 Ubuntu 后 apt 很慢 | 默认源在国外 | 换国内镜像源后再装依赖 |
| 启动时报 `0x80370102` | 虚拟化未开启 | BIOS 中开启 VT-x/SVM；若开了 Hyper-V/VBS 仍需确认 `VirtualMachinePlatform` 已启用 |

## 8. 不想装 WSL 的替代方案

如果本机受管控、装不了 WSL，仍有两条例外路径：

1. **GitHub Actions 云端构建**（本项目已配置）：推送代码后在仓库 Actions 页面自动出 APK，产物在 Artifacts 下载。不占本机资源、不需要虚拟化。工作流见 `.github/workflows/build-apk.yml`。
2. **远程 Linux 机器**：任意有 sudo 的 Ubuntu 机器 + `scp` 项目过去构建，产物 scp 回来。

---

## 附：本文对应的一次真实排查记录

1. 执行 `wsl --install -d Ubuntu` → `已禁止(403)`；
2. 检查 `wsl --help` → 只有 4 个参数，确认是存根版；
3. 检查 `Get-Service LxssManager` → 服务不存在，确认功能未启用；
4. 检查网络 4 个关键站点 → 全 200，排除网络因素；
5. 检查 `HypervisorPresent` → True，排除虚拟化不足；
6. 确认 `whoami /groups` → 未提权；
7. 结论：走本文第 4 步的「启用功能 → 重启 → MSI → `--web-download`」路线。
