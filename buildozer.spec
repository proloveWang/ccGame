# buildozer.spec —— 用于把 main.py 打包成安卓 APK 的配置文件
# 说明：本文件被 Buildozer / python-for-android 读取，控制应用名称、包名、依赖与安卓参数

[app]

# 应用在手机桌面上显示的标题
title = Plane War

# 应用包名的短名（小写字母与数字）
package.name = planewar

# 应用包名的域名部分，组合后完整包名为 org.example.planewar
package.domain = org.example

# 源码所在目录（本配置文件与 main.py 放在同一目录，故用当前目录）
source.dir = .

# 需要打进 APK 的源码扩展名（只打包 Python 文件）
source.include_exts = py

# 打包时排除的目录（IDE 配置、缓存、本地 recipe 与 CI 配置没必要进 APK）
source.exclude_dirs = .idea, __pycache__, tools, .github

# 应用启动时执行的入口文件
source.main = main.py

# 依赖列表：python3 解释器 + pygame 游戏库
# 说明：python-for-android 里稳定的 recipe 名是 pygame（内部构建 SDL2 版 pygame 2.x）；
#      写成 pygame-ce 时，多数 p4a 分支会直接报 Recipe ... not found 而中断打包。
#      本地开发环境装 pygame-ce 即可，两者 API 兼容，不影响这份配置
requirements = python3, pygame

# 启动引导方式：pygame 必须走 SDL2 引导（p4a 默认也是它，这里显式写出避免被覆盖）
p4a.bootstrap = sdl2

# python-for-android 的版本（决定安卓端编译用哪个 Python）
# 说明：p4a master / v2026.05.09 内置 Python 3.14，而 pygame 2.5.x 官方只支持到 3.12；
#      v2024.01.21 内置 Python 3.11.5，是能跑 pygame 的最新一版。
#      改这里之后必须删掉 .buildozer 重建，否则会继续用旧 p4a。
p4a.branch = v2024.01.21

# 本地 recipe 目录：覆盖 p4a 内置的 pygame recipe，把构建版本从 2.1.0 提到 2.5.2
# 原因：pygame 2.1.0 的 src_c/_sdl2/sdl2.c 里 #include "longintrepr.h"，该头文件从 Python 3.11 起
#      已移入 Include/cpython/，直接报 fatal error: 'longintrepr.h' file not found。
p4a.local_recipes = ./tools/p4a_recipes

# 横竖屏方向：portrait 竖屏，适配手机飞机大战
orientation = portrait

# 应用版本号
version = 1.0.0

# 安卓最小支持 SDK 版本
android.minapi = 21

# 安卓目标 SDK 版本
android.api = 33

# 自动接受安卓 SDK 许可协议，避免首次构建卡在交互式 y/N 询问上
android.accept_sdk_license = True

# 安卓 NDK 版本
android.ndk = 25b

# 打包的 CPU 架构：先只打 arm64-v8a，构建更快、包体更小；
# 需要兼容老 32 位手机时再在末尾追加 armeabi-v7a（构建时间与包体会成倍增长）
android.archs = arm64-v8a

# 是否开启全屏（1 全屏，0 保留状态栏）
android.fullscreen = 1

[buildozer]

# 日志级别：2 为详细，便于排查打包错误
log_level = 2

# 是否在打包前检查依赖
warn_on_root = 1