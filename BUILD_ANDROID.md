# ccGame · 安卓 APK 打包操作手册

本文是 [README.md](README.md) 中「打包成安卓 APK」的完整展开版，包含环境安装、构建、装机、签名与排错。

> 当前项目已验证可在 Python 3.13.7 + pygame-ce 2.5.8 下本地运行；APK 构建流程在本文中给出，需要你在自己的 Linux 环境里执行（Windows 侧无法直接构建）。

---

## 目录

- [0. 结论先行](#0-结论先行)
- [1. 为什么 Windows 上不能直接打包](#1-为什么-windows-上不能直接打包)
- [2. 方案 A：WSL2（本机构建）](#2-方案-awsl2本机构建)
- [3. 方案 B：GitHub Actions](#3-方案-bgithub-actions)
- [4. 方案 C：Docker](#4-方案-cdocker)
- [5. 构建配置说明（buildozer.spec）](#5-构建配置说明buildozerspec)
- [6. 常用命令清单](#6-常用命令清单)
- [7. 常见报错排查](#7-常见报错排查)
- [8. release 签名与上架](#8-release-签名与上架)
- [9. 打包后验收清单](#9-打包后验收清单)
- [10. 时间与磁盘预估](#10-时间与磁盘预估)

---

## 0. 结论先行

| 项目 | 说明 |
| --- | --- |
| 构建产物 | `bin/planewar-1.0.0-arm64-v8a-debug.apk` |
| 构建命令 | `buildozer -v android debug` |
| 必需平台 | Linux / macOS（Windows 走 WSL2 或 Docker） |
| 首次耗时 | 约 30–90 分钟（要下载 Android SDK / NDK / JDK） |
| 增量耗时 | 约 2–5 分钟 |
| 磁盘占用 | 首次约 3–5 GB（`~/.buildozer` + `.buildozer/`） |
| 网络要求 | 能访问 dl.google.com、pypi、github（下载 SDK/NDK/recipe） |
| 装机方式 | `adb install -r xxx.apk`，或把 APK 传到手机点击安装 |
| 零环境路径 | 代码推到 GitHub，由 Actions 云端出包并下载（见第 3 章，无需本机装任何东西） |

最小可用流程（已装好 WSL2 的情况下）：

```bash
# 1) 复制项目到 Linux 文件系统（必须，别在 /mnt/e 下构建）
cp -r /mnt/e/it-python/ccGame ~/ccGame
cd ~/ccGame

# 2) 构建
buildozer -v android debug

# 3) 取产物
ls -lh bin/*.apk
```

---

## 1. 为什么 Windows 上不能直接打包

Buildozer 本质是「下载 Android SDK/NDK + 调 python-for-android 交叉编译 CPython 和第三方库 + 用 Gradle 出包」的编排脚本，它依赖大量 **Unix 工具链**（autoconf、libtool、make、pkg-config、bash 脚本、符号链接）。Windows 原生没有这套环境，所以官方只支持 Linux/macOS。

在 Windows 上只有两条正路：

- **WSL2**：装一个真正的 Linux 子系统，最稳、最快（推荐）。
- **Docker**：用官方 `kivy/buildozer` 镜像，省去手动装依赖，但受 Windows 目录挂载拖累速度。

另外两个容易搞混的点：

- Windows 上的 `java.exe`（Oracle JRE/JDK）**与打包无关**，Buildozer 用的是它自己下载的 JDK，Linux 内需另装 `openjdk-17-jdk`。
- Windows 上的 `adb` 只用于**装包**，构建全程不需要它。

---

## 2. 方案 A：WSL2（本机构建）

### 2.1 安装 WSL2 + Ubuntu（只需一次）

以**管理员身份**打开 PowerShell：

```powershell
wsl --install -d Ubuntu
```

> ⚠️ 若这条命令报 **`已禁止(403)`**（Windows 11 24H2 的存根版 `wsl.exe` 走 Microsoft Store 通道时常见），按 [WSL2_SETUP.md](WSL2_SETUP.md) 的离线安装流程操作：启用两个可选功能 → 重启 → 装 GitHub 上的 WSL MSI → `wsl --install -d Ubuntu --web-download`。

按提示重启电脑，重启后会弹出 Ubuntu 窗口，设置 UNIX 用户名和密码（密码输入时不显示，正常）。

装好后确认版本：

```powershell
wsl --list --verbose
```

`VERSION` 必须是 `2`。若显示 1，执行 `wsl --set-default-version 2` 后重装发行版。

进入 Linux 终端：在任意 PowerShell 窗口输入 `wsl` 回车（后续所有 `bash` 命令都在这个窗口里执行）。

### 2.2 安装打包所需的系统依赖

```bash
sudo apt update
sudo apt install -y python3-pip python3-venv git zip unzip openjdk-17-jdk \
  autoconf automake libtool pkg-config zlib1g-dev libncurses5-dev \
  libncursesw5-dev libtinfo6 cmake libffi-dev libssl-dev build-essential
```

安装后确认 Java 版本（必须是 17）：

```bash
java -version
```

> 如果出现版本不符：`sudo update-alternatives --config java` 选择 17。

### 2.3 安装 Buildozer

装在独立虚拟环境里，避免污染系统 Python：

```bash
python3 -m venv ~/venv-buildozer
source ~/venv-buildozer/bin/activate
pip install --upgrade pip cython buildozer
buildozer --version
```

以后每次新开终端都要先 `source ~/venv-buildozer/bin/activate`。

> 若遇到 Cython 3 相关的 recipe 编译错误，可退回：`pip install "cython<3"` 再重试。

### 2.4 把项目复制进 Linux 文件系统

```bash
cp -r /mnt/e/it-python/ccGame ~/ccGame
cd ~/ccGame
ls
```

⚠️ **这一步不要跳过。** `/mnt/e/...` 是 Windows 盘通过 drvfs 挂载的，构建时会产生海量小文件 I/O，速度可能慢十倍以上，还可能因为权限/软链接导致 recipe 编译失败。

### 2.5 构建 debug APK

```bash
cd ~/ccGame
buildozer -v android debug
```

首次执行会依次自动完成：

1. 下载并解压 Android SDK（`~/.buildozer/android/platform/android-sdk`）
2. 下载 NDK 25b 与 JDK 17
3. 编译 CPython for Android（含 SDL2 引导）
4. 编译 `pygame` recipe
5. 打包你的 `main.py` 并用 Gradle 生成 APK

过程中任何一步都可能因网络中断失败，**直接重跑同一条命令**即可续传。

### 2.6 取产物并安装到手机

产物在：

```
~/ccGame/bin/planewar-1.0.0-arm64-v8a-debug.apk
```

**方式一：adb（推荐）**

手机端：设置 → 关于手机 → 连点「版本号」7 次开启开发者选项 → 开启「USB 调试」→ 用数据线连电脑并在弹窗中允许调试。

Windows 侧装 platform-tools（[Android 开发者官网下载](https://developer.android.com/studio/releases/platform-tools)），然后在 **PowerShell** 执行：

```powershell
adb devices      # 确认设备列表里有你的手机
adb install -r \\wsl$\Ubuntu\home\<你的用户名>\ccGame\bin\planewar-1.0.0-arm64-v8a-debug.apk
```

**方式二：手动传输**

```bash
# 在 WSL 里把 APK 放回 Windows 盘
cp ~/ccGame/bin/*.apk /mnt/e/it-python/
```

再从 Windows 用数据线 / 微信文件助手传到手机，点击安装（需允许「安装未知来源应用」）。

**方式三：无线 adb**

```powershell
adb tcpip 5555
adb connect <手机IP>:5555
adb install -r planewar-1.0.0-arm64-v8a-debug.apk
```

---

## 3. 方案 B：GitHub Actions

本机什么都不用装：把代码推到 GitHub，仓库自带的云端 Linux 机器完成编译，APK 作为 Artifact 下载。工作流文件已就位 —— [`.github/workflows/build-apk.yml`](.github/workflows/build-apk.yml)。

### 3.1 触发构建

两种方式任选：

- **自动**：向 `master`（或 `main`）推送改动了 `main.py` / `buildozer.spec` / `requirements.txt` / 工作流文件的提交；
- **手动**：仓库页面 → **Actions** → 左侧 **Build Android APK** → 右侧 **Run workflow**；想兼容老 32 位手机，在 `archs` 填 `arm64-v8a, armeabi-v7a`，否则留空。

### 3.2 取 APK

1. 进入仓库 **Actions** 页，点开最新一次 `Build Android APK` 运行（绿勾 = 成功）；
2. 页面底部 **Artifacts** 区域下载 `planewar-1.0.0-arm64-v8a-debug.apk`；
3. 解压上传到手机点击安装（需允许「安装未知来源应用」）。

失败时下载 `build-log` 产物，里面是完整 buildozer 输出，对照第 7 章的报错表排查。

### 3.3 耗时与额度

| 项目 | 说明 |
| --- | --- |
| 首次构建 | 约 40–70 分钟（下载 SDK/NDK + 编译 CPython + pygame） |
| 后续构建 | 缓存命中约 10–25 分钟（工作流缓存 `~/.buildozer` 与 `~/.gradle`） |
| 单次上限 | 工作流设 300 分钟，GitHub 硬上限 6 小时 |
| 免费额度 | **公开仓库的 Actions 不限时长**；私有仓库每月 2000 分钟 |
| 缓存上限 | 单仓库 10 GB，超出后旧缓存被自动淘汰 |

> 仓库设为 public 是最省心的用法：不限时长、不花钱。

### 3.4 改工作流

工作流就是普通 YAML，提交到仓库即生效：

| 需求 | 改法 |
| --- | --- |
| 换触发分支名 | 改 `on.push.branches` |
| 每次推送都构建（不限改动文件） | 删掉 `on.push.paths` 整段 |
| 产物保留更久 | 改 `retention-days`（最大 90） |
| 顺带出 release 包 | 加一步 `buildozer android release`，并把 keystore 放进仓库 Secrets |

---

## 4. 方案 C：Docker

适合不想在 WSL 里装一堆依赖、或想复现干净构建环境的场景。

1. 安装 Docker Desktop（Windows 版本，启用 WSL2 backend）。
2. 在 PowerShell 中：

```powershell
cd E:\it-python\ccGame
docker run --rm -v "${PWD}:/home/user/hostcwd" kivy/buildozer -v android debug
```

3. 产物直接出现在 Windows 侧 `E:\it-python\ccGame\bin\`。

> 挂载 Windows 目录构建会明显变慢。追求速度时用交互式容器，把项目复制到容器内家目录再构建：

```powershell
docker run -it -v "${PWD}:/home/user/hostcwd" kivy/buildozer bash
```

容器内：

```bash
cp -r /home/user/hostcwd ~/ccGame
cd ~/ccGame
buildozer -v android debug
mkdir -p /home/user/hostcwd/bin && cp bin/*.apk /home/user/hostcwd/bin/
```

Docker 方案的代价：每次 `--rm` 后 `~/.buildozer` 缓存丢失，下次仍要重新下载 SDK/NDK。要复用就挂一个卷：

```powershell
docker run --rm -v "${PWD}:/home/user/hostcwd" -v ccgame-buildozer:/home/user/.buildozer kivy/buildozer -v android debug
```

---

## 5. 构建配置说明（buildozer.spec）

| 配置项 | 当前值 | 说明 |
| --- | --- | --- |
| `title` | `Plane War` | 手机桌面显示的应用名 |
| `package.name` | `planewar` | 包名短名（小写） |
| `package.domain` | `org.example` | 完整包名 `org.example.planewar`，同一手机装两个应用需改这里 |
| `source.dir` | `.` | 源码目录 |
| `source.include_exts` | `py` | 只打包 Python 文件；若后续加素材需补 `png,jpg,wav,ogg` 等 |
| `source.exclude_dirs` | `.idea, __pycache__` | 排除 IDE 与缓存目录 |
| `requirements` | `python3, pygame` | **必须写 `pygame`**！p4a 没有 `pygame-ce` recipe，写成它会导致构建中断 |
| `p4a.bootstrap` | `sdl2` | pygame 必须走 SDL2 引导 |
| `p4a.branch` | `v2024.01.21` | 固定 p4a 版本：新版已内置 Python 3.14，而它的 pygame recipe 仍锁 pygame 2.1.0，会报 `longintrepr.h` 找不到；这个版内置 Python 3.11，能编过 |
| `orientation` | `portrait` | 竖屏 |
| `version` | `1.0.0` | 版本号，出现在产物文件名里 |
| `android.api` | `33` | 编译用目标 SDK；上架 Google Play 需 ≥34 |
| `android.minapi` | `21` | 最低支持 Android 5.0 |
| `android.ndk` | `25b` | 与 p4a 当前版本匹配，别随意改 |
| `android.archs` | `arm64-v8a` | 只打 64 位；要兼容 32 位老机型再追加 `armeabi-v7a`（构建时间翻倍） |
| `android.accept_sdk_license` | `True` | 自动接受 SDK 许可，避免卡在交互式确认 |
| `android.fullscreen` | `1` | 全屏 |

游戏内部的屏幕自适应由 `main.py` 负责：`pygame.SCALED` 让游戏始终按 480×800 逻辑分辨率绘制，SDL 再等比缩放到真实屏幕，多余部分留黑边（不拉伸）。安卓上还额外叠加 `FULLSCREEN`。

---

## 6. 常用命令清单

在 WSL 中、项目目录内执行：

```bash
buildozer -v android debug        # 构建 debug 包（改代码后增量构建）
buildozer android clean           # 清理构建目录（改 requirements 后必须执行）
buildozer android logcat          # 实时抓手机日志，排查闪退
buildozer android deploy run      # 构建 + 安装 + 启动（需要 Linux 内 adb 可用）
buildozer android p4a -- help     # 查看底层 python-for-android 参数
```

清理更彻底（连 SDK/NDK 缓存一起删，下次需重新下载）：

```bash
rm -rf ~/.buildozer ~/ccGame/.buildozer ~/ccGame/bin
```

把最新代码同步进 WSL（改完 Windows 侧代码后）：

```bash
cp -r /mnt/e/it-python/ccGame/* ~/ccGame/
cd ~/ccGame && buildozer -v android debug
```

---

## 7. 常见报错排查

| 现象 | 原因 | 处理 |
| --- | --- | --- |
| `Recipe for pygame-ce ... not found` / 构建中断 | `requirements` 被改成 `pygame-ce` | 改回 `pygame`，执行 `buildozer android clean` 后重建 |
| `src_c/_sdl2/sdl2.c: fatal error: 'longintrepr.h' file not found` | p4a 用的是 Python 3.13+，而 pygame recipe 里的 pygame 2.1.0 不支持 | 设 `p4a.branch = v2024.01.21`（Python 3.11），删 `.buildozer` 后重建 |
| `Java version ... not supported` / `javac` 相关错误 | JDK 不是 17 | `sudo apt install openjdk-17-jdk`，`update-alternatives` 选 17 |
| 下载 SDK/NDK 卡住或超时 | 网络问题 | 直接重跑命令续传；或手动下载后放进 `~/.buildozer/android/platform/` |
| 构建极慢、`Permission denied`、软链接失败 | 项目放在 `/mnt/e` 等 Windows 挂载盘 | `cp -r` 到 `~/ccGame` 再构建 |
| `Android SDK license not accepted` | 许可证未接受 | 确认 `android.accept_sdk_license = True`，或重建前删 `~/.buildozer` |
| 手机提示「应用未安装」/「解析包出错」 | 手机是 32 位架构或 Android 版本低于 21 | 在 `android.archs` 追加 `armeabi-v7a`，或确认手机 ≥ Android 5.0 |
| 安装成功但闪退 | Python 层异常 | `buildozer android logcat` 看 traceback，通常是缺依赖或字体/路径问题 |
| 画面有黑边 | 屏幕比例与 480:800 不同，等比缩放留边 | 正常现象；想要满屏需在代码里按屏幕比例扩展绘制区域 |
| `ModuleNotFoundError` | `requirements` 漏了库 | 补进 `requirements` 后 `buildozer android clean` 重建 |
| 构建通过但代码是旧的 | 改了 Windows 侧文件但没同步进 WSL | 先 `cp` 同步再构建 |

---

## 8. release 签名与上架

debug 包用的是调试证书，只适合自己安装体验。要正式分发或上架：

```bash
# 1) 生成 keystore（只需一次，务必保存好）
keytool -genkey -v -keystore ~/planewar.keystore -alias planewar \
  -keyalg RSA -keysize 2048 -validity 10000

# 2) 构建未签名 release 包
buildozer android release
```

在 `buildozer.spec` 的 `[app]` 段补充签名信息后可直接产出已签名包：

```ini
android.release_artifact = aab
android.keystore = /home/<user>/planewar.keystore
android.keyalias = planewar
android.keystore_passwd = 你的密码
```

手动签名（不使用上面的配置时）：

```bash
# 对齐 + 签名
zipalign -v -p 4 bin/planewar-1.0.0-arm64-v8a-release-unsigned.apk aligned.apk
apksigner sign --ks ~/planewar.keystore --out planewar-release.apk aligned.apk
apksigner verify planewar-release.apk
```

> `zipalign` / `apksigner` 在 `~/.buildozer/android/platform/android-sdk/build-tools/<版本>/` 下。

---

## 9. 打包后验收清单

装到手机后按顺序确认：

- [ ] 桌面图标名称显示为 `Plane War`，点击能启动不闪退
- [ ] 全屏显示，上下或左右有黑边属正常（等比缩放不拉伸）
- [ ] 开始界面显示标题与操作提示，点屏幕进入游戏
- [ ] 手指拖动时战机跟手且不会飞出屏幕
- [ ] 子弹自动发射，击中敌机加分、有爆炸粒子
- [ ] 点右上角暂停按钮能暂停，再点屏幕能继续
- [ ] 生命归零出现 `GAME OVER`，点屏幕能重开且分数归零
- [ ] 返回桌面再切回应用不崩溃
- [ ] 连续玩 5 分钟无明显掉帧（`buildozer android logcat` 无异常刷屏）

---

## 10. 时间与磁盘预估

| 阶段 | 首次 | 之后 |
| --- | --- | --- |
| 环境准备（WSL + apt + pip） | 10–20 分钟 | — |
| SDK / NDK / JDK 下载 | 10–30 分钟（看网速） | 0（已缓存） |
| CPython + pygame 交叉编译 | 10–25 分钟 | 0（已缓存） |
| 打包 APK | 2–5 分钟 | 2–5 分钟 |
| **合计** | **30–90 分钟** | **2–5 分钟** |

磁盘：`~/.buildozer` 约 2–4 GB，项目内 `.buildozer/` 约 0.5–1 GB，`bin/` 下每个 APK 约 15–30 MB。
