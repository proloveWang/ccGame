# -*- coding: utf-8 -*-
# 文件作用：飞机大战游戏主程序，基于 pygame-ce 开发，电脑与安卓手机均可运行
# 设计说明：所有画面均由几何图形绘制，不依赖外部图片素材，方便后续打包成 APK
# 操作方式：电脑用鼠标拖动或方向键移动（键盘一动即接管，指针跟随让位），手机用手指拖动；自动开火；
#           暂停可点右上角按钮，电脑也可按 P 键

# ========== 1. 导入所需标准库与第三方库 ==========
import os                                    # 导入 os 模块，用于识别是否运行在安卓打包环境
import sys                                   # 导入 sys 模块，用于在退出时关闭解释器
import random                               # 导入 random 模块，用于生成随机位置与随机数值
import math                                 # 导入 math 模块，用于角度与距离等数学计算
import pygame                               # 导入 pygame 游戏库，负责画面、事件与帧率控制

# ========== 2. 全局常量：窗口与帧率 ==========
SCREEN_WIDTH = 480                          # 定义游戏逻辑画面宽度（像素），竖屏比例适配手机
SCREEN_HEIGHT = 800                         # 定义游戏逻辑画面高度（像素），竖屏比例适配手机
FPS = 60                                    # 定义每秒刷新帧数，保证动画流畅不卡顿
TITLE = "Plane War"                         # 定义窗口标题文字

# 运行平台判断：python-for-android 打包出的安卓环境会注入 ANDROID_ARGUMENT 环境变量
IS_ANDROID = "ANDROID_ARGUMENT" in os.environ

# 显示模式：SCALED 让游戏始终按 480×800 的逻辑分辨率绘制，再由 SDL 等比缩放到真实窗口，
# 于是不同尺寸/比例的屏幕都能自适应，鼠标坐标也会被自动换算回逻辑坐标。
# 安卓额外叠加 FULLSCREEN 铺满屏幕（多余部分留黑边，不拉伸变形），桌面则允许拖拽改变窗口大小
if IS_ANDROID:
    DISPLAY_FLAGS = pygame.SCALED | pygame.FULLSCREEN     # 安卓：全屏 + 等比缩放
else:
    DISPLAY_FLAGS = pygame.SCALED | pygame.RESIZABLE      # 桌面：可改尺寸 + 等比缩放

# ========== 3. 全局常量：颜色（RGB 元组） ==========
COLOR_BLACK = (8, 10, 24)                   # 背景深空颜色，偏深蓝黑色
COLOR_WHITE = (240, 240, 240)               # 通用白色，用于普通文字
COLOR_YELLOW = (255, 220, 80)               # 子弹与得分高亮颜色
COLOR_RED = (235, 70, 70)                   # 敌机与受伤警示颜色
COLOR_GREEN = (80, 220, 130)                # 玩家与生命颜色
COLOR_BLUE = (90, 160, 255)                 # 道具与大型敌机颜色
COLOR_PURPLE = (180, 110, 255)               # 爆炸粒子渐变颜色之一
COLOR_GRAY = (120, 125, 145)                # 中性灰色，用于边框与次要元素
COLOR_ORANGE = (255, 150, 60)               # 大型敌机主体颜色

# ========== 4. 全局常量：游戏状态编号 ==========
STATE_START = 0                             # 状态编号：开始菜单界面
STATE_PLAYING = 1                           # 状态编号：游戏进行中
STATE_PAUSED = 2                            # 状态编号：暂停界面
STATE_GAMEOVER = 3                          # 状态编号：游戏结束界面

# ========== 5. 全局常量：数值平衡参数 ==========
PLAYER_SPEED = 6                            # 定义玩家键盘移动时的速度（像素/帧）
PLAYER_MAX_HP = 3                           # 定义玩家初始与最大生命值
BULLET_SPEED = 9                            # 定义玩家子弹向上飞行的速度
ENEMY_BULLET_SPEED = 5                      # 定义敌机子弹向下飞行的速度
ENEMY_SPEED = 2.5                           # 定义普通敌机下落的基础速度
SPAWN_INTERVAL = 45                         # 定义普通敌机生成间隔（帧），越小敌机越密集
POWERUP_DROP_RATE = 0.18                    # 定义敌机被击毁后掉落道具的概率
INVINCIBLE_FRAMES = 90                      # 定义玩家受击后的无敌闪烁帧数（约1.5秒）

# 右上角暂停按钮：手机没有键盘，靠这个按钮进入/退出暂停
PAUSE_BUTTON_SIZE = 44                      # 暂停按钮方块边长（逻辑像素，随画面等比缩放）
PAUSE_BUTTON_MARGIN = 12                    # 按钮与屏幕上边缘、右边缘的间距
PAUSE_BUTTON_RECT = pygame.Rect(            # 按钮的命中矩形，直接用于点击判定
    SCREEN_WIDTH - PAUSE_BUTTON_SIZE - PAUSE_BUTTON_MARGIN,  # 左边界：靠右侧留边
    PAUSE_BUTTON_MARGIN,                    # 上边界：靠顶部留边
    PAUSE_BUTTON_SIZE,                      # 宽度
    PAUSE_BUTTON_SIZE                       # 高度
)

# ========== 6. 工具函数：加载字体 ==========
def load_font(size):
    # 函数作用：按指定字号加载字体，优先尝试常见中文字体，失败则回退默认字体
    # 参数 size：需要的字号（整数像素）
    # 返回值：一个可用的 pygame Font 对象，保证在不同设备上都不会因缺字体崩溃
    candidate_names = [                     # 准备一个候选字体名列表，依次尝试加载
        "Microsoft YaHei",                 # 候选字体：微软雅黑（Windows 常见）
        "PingFang SC",                     # 候选字体：苹方（苹果设备常见）
        "Noto Sans CJK SC",                # 候选字体：思源黑体（Linux/安卓常见）
        "WenQuanYi Micro Hei",             # 候选字体：文泉驿微米黑（部分 Linux 常见）
    ]                                       # 候选字体列表结束
    for name in candidate_names:            # 逐个遍历候选字体名进行尝试
        try:                                # 进入异常保护，防止找不到字体时报错
            font = pygame.font.SysFont(name, size)  # 用指定字体名与字号创建字体对象
            return font                     # 加载成功则直接返回该字体对象
        except pygame.error:                # 如果该字体名不存在则捕获 pygame 字体错误
            continue                        # 继续尝试下一个候选字体名
    return pygame.font.Font(None, size)     # 全部失败时使用 pygame 内置默认字体兜底


# ========== 7. 背景星星类：实现向下滚动的星空 ==========
class Star:
    # 类作用：表示背景中的一颗星星，负责自身位置更新与绘制
    def __init__(self):
        # 初始化方法：创建一颗随机位置、随机亮度、随机速度的星星
        self.reset(random_y=True)           # 调用重置方法，random_y=True 表示允许随机初始纵向位置

    def reset(self, random_y=False):
        # 方法作用：把星星重新放回屏幕顶部（或随机纵向位置），用于循环滚动
        # 参数 random_y：True 时纵向位置随机，用于开局铺满整个背景
        self.x = random.randint(0, SCREEN_WIDTH)  # 随机生成星星的横坐标
        if random_y:                        # 如果是开局铺背景
            self.y = random.randint(0, SCREEN_HEIGHT)  # 随机生成星星的纵坐标
        else:                               # 如果是被回收后重新出现
            self.y = -2                     # 把星星放到屏幕顶部外侧一点点
        self.speed = random.uniform(0.5, 2.5)  # 随机生成星星下落速度，形成远近层次
        self.brightness = random.randint(80, 220)  # 随机生成星星亮度，形成明暗差异
        self.size = random.choice([1, 1, 2, 2, 3])  # 随机生成星星大小，多数为小点

    def update(self):
        # 方法作用：每帧更新星星位置，并在飞出屏幕底部后回收
        self.y += self.speed                # 按自身速度向下移动一帧
        if self.y > SCREEN_HEIGHT:          # 判断星星是否已经飞出屏幕底部
            self.reset(random_y=False)      # 飞出后重置到顶部，实现无限滚动

    def draw(self, surface):
        # 方法作用：把星星绘制到指定的画面表面上
        # 参数 surface：pygame 画面表面对象
        color = (self.brightness, self.brightness, self.brightness)  # 根据亮度生成灰色星光颜色
        pygame.draw.circle(surface, color, (int(self.x), int(self.y)), self.size)  # 画一个小圆点表示星星


# ========== 8. 子弹类：玩家子弹与敌机子弹共用 ==========
class Bullet:
    # 类作用：表示一颗飞行中的子弹，区分我方（向上）与敌方（向下）
    def __init__(self, x, y, speed, friendly=True, radius=5):
        # 初始化方法：设置子弹起点、速度、归属与大小
        # 参数 x,y：子弹初始坐标；speed：纵向速度；friendly：是否我方子弹；radius：子弹半径
        self.x = x                          # 记录子弹横坐标
        self.y = y                          # 记录子弹纵坐标
        self.speed = speed                  # 记录子弹纵向速度（带方向）
        self.friendly = friendly            # 记录子弹归属：True 我方，False 敌方
        self.radius = radius                # 记录子弹圆形半径
        self.alive = True                   # 记录子弹是否存活，便于后续从列表移除
        # 根据归属选择子弹颜色：我方黄色，敌方红色
        self.color = COLOR_YELLOW if friendly else COLOR_RED

    def update(self):
        # 方法作用：每帧移动子弹，并判断是否飞出屏幕
        direction = -1 if self.friendly else 1  # 我方向上为负方向，敌方向下为正方向
        self.y += self.speed * direction     # 按方向与速度更新纵坐标
        if self.y < -20 or self.y > SCREEN_HEIGHT + 20:  # 判断是否飞出屏幕上下外侧
            self.alive = False              # 飞出后标记为不存活，等待移除

    def get_rect(self):
        # 方法作用：返回子弹的矩形碰撞区域，用于碰撞检测
        return pygame.Rect(                 # 构造一个矩形对象作为碰撞盒
            self.x - self.radius,           # 矩形左边界
            self.y - self.radius,           # 矩形上边界
            self.radius * 2,                # 矩形宽度
            self.radius * 2                 # 矩形高度
        )

    def draw(self, surface):
        # 方法作用：在画面上绘制子弹圆形，外加一圈亮边增强观感
        pygame.draw.circle(surface, self.color, (int(self.x), int(self.y)), self.radius)  # 绘制子弹主体圆
        pygame.draw.circle(surface, COLOR_WHITE, (int(self.x), int(self.y)), self.radius, 1)  # 绘制白色细描边


# ========== 9. 道具类：加血道具与火力道具 ==========
class PowerUp:
    # 类作用：表示从敌机掉落的补给道具，向下漂浮，被玩家拾取后生效
    def __init__(self, x, y, kind):
        # 初始化方法：设置道具位置、类型与下落速度
        # 参数 kind："heal" 表示加血，"power" 表示火力升级
        self.x = x                          # 记录道具横坐标
        self.y = y                          # 记录道具纵坐标
        self.kind = kind                    # 记录道具类型
        self.speed = 2.2                    # 记录道具下落速度
        self.alive = True                   # 记录道具是否存活
        self.radius = 14                    # 记录道具圆形半径
        self.sway = random.uniform(0, math.pi * 2)  # 记录左右摇摆的初始相位

    def update(self):
        # 方法作用：每帧更新道具位置，加入轻微左右摆动
        self.y += self.speed                # 道具向下漂浮一帧
        self.sway += 0.05                   # 推进摇摆相位
        self.x += math.sin(self.sway) * 1.2  # 用正弦函数实现左右轻微摆动
        if self.y > SCREEN_HEIGHT + 20:     # 判断道具是否飞出屏幕底部
            self.alive = False              # 飞出后标记不存活

    def get_rect(self):
        # 方法作用：返回道具矩形碰撞盒
        return pygame.Rect(                 # 构造道具碰撞矩形
            self.x - self.radius,           # 左边界
            self.y - self.radius,           # 上边界
            self.radius * 2,                # 宽度
            self.radius * 2                 # 高度
        )

    def draw(self, surface):
        # 方法作用：绘制道具圆圈与内部符号，加血画十字，火力画闪电形
        color = COLOR_RED if self.kind == "heal" else COLOR_BLUE  # 按类型选择外圈颜色
        pygame.draw.circle(surface, color, (int(self.x), int(self.y)), self.radius, 2)  # 绘制彩色圆环
        pygame.draw.circle(surface, COLOR_BLACK, (int(self.x), int(self.y)), self.radius - 2)  # 绘制黑色内底
        if self.kind == "heal":             # 如果是加血道具
            pygame.draw.line(surface, COLOR_RED, (self.x - 6, self.y), (self.x + 6, self.y), 3)  # 画横笔画
            pygame.draw.line(surface, COLOR_RED, (self.x, self.y - 6), (self.x, self.y + 6), 3)  # 画竖笔画组成十字
        else:                               # 否则是火力道具
            pygame.draw.polygon(surface, COLOR_BLUE, [  # 用多边形画一道闪电
                (self.x + 2, self.y - 8),       # 闪电上顶点
                (self.x - 5, self.y + 1),       # 闪电左拐点
                (self.x, self.y + 1),           # 闪电中拐点
                (self.x - 2, self.y + 8),       # 闪电下顶点
                (self.x + 5, self.y - 1),       # 闪电右拐点
                (self.x, self.y - 1)            # 闪电中右点
            ])


# ========== 10. 爆炸粒子类：击毁敌机时的四散火花 ==========
class Particle:
    # 类作用：表示爆炸中的一个火花粒子，带初速度、寿命与渐隐效果
    def __init__(self, x, y):
        # 初始化方法：在指定位置生成一颗随机方向、随机速度的粒子
        self.x = x                          # 记录粒子横坐标
        self.y = y                          # 记录粒子纵坐标
        angle = random.uniform(0, math.pi * 2)  # 随机生成放射方向角度
        speed = random.uniform(1, 4)         # 随机生成粒子飞行速度
        self.vx = math.cos(angle) * speed    # 分解出水平方向速度分量
        self.vy = math.sin(angle) * speed    # 分解出垂直方向速度分量
        self.life = random.randint(20, 35)   # 记录粒子剩余寿命（帧）
        self.max_life = self.life            # 记录粒子初始寿命，用于计算透明度比例
        self.color = random.choice([COLOR_ORANGE, COLOR_YELLOW, COLOR_RED, COLOR_PURPLE])  # 随机选择火花颜色

    def update(self):
        # 方法作用：每帧更新粒子位置、减速并扣减寿命
        self.x += self.vx                   # 更新水平位置
        self.y += self.vy                   # 更新垂直位置
        self.vx *= 0.95                     # 水平速度逐渐衰减（阻力）
        self.vy *= 0.95                     # 垂直速度逐渐衰减（阻力）
        self.life -= 1                      # 寿命减一帧

    def draw(self, surface):
        # 方法作用：按剩余寿命比例绘制渐隐的粒子小圆点
        ratio = max(self.life / self.max_life, 0)  # 计算寿命剩余比例，限制不为负
        radius = max(int(3 * ratio), 1)     # 根据比例缩小粒子半径
        pygame.draw.circle(surface, self.color, (int(self.x), int(self.y)), radius)  # 绘制粒子


# ========== 11. 敌机类：普通敌机与大型敌机 ==========
class Enemy:
    # 类作用：表示一架敌机，包含移动、开火、受击与绘制逻辑
    def __init__(self, big=False):
        # 初始化方法：按是否大型生成不同体型、血量与速度的敌机
        self.big = big                      # 记录是否为大型敌机
        self.x = random.randint(40, SCREEN_WIDTH - 40)  # 随机生成横坐标，留出边距
        self.y = -60                        # 初始纵坐标放在屏幕顶部外侧
        if self.big:                        # 如果是大型敌机
            self.width = 70                # 设置机身宽度
            self.height = 52               # 设置机身高度
            self.hp = 5                    # 设置较高血量，需要多颗子弹击毁
            self.speed = 1.4               # 设置较慢的下落速度
            self.color = COLOR_ORANGE      # 大型敌机主体颜色
            self.score = 50                # 击毁后奖励分数
            self.fire_chance = 0.012       # 每帧开火概率较高
        else:                               # 如果是普通敌机
            self.width = 40                # 设置机身宽度
            self.height = 34               # 设置机身高度
            self.hp = 1                    # 设置血量，一颗子弹即可击毁
            self.speed = ENEMY_SPEED + random.uniform(0, 1.2)  # 速度在基础值上随机浮动
            self.color = COLOR_RED         # 普通敌机主体颜色
            self.score = 10                # 击毁后奖励分数
            self.fire_chance = 0.006       # 每帧开火概率较低
        self.alive = True                   # 记录敌机是否存活
        self.wobble = random.uniform(0, math.pi * 2)  # 记录横向摆动初始相位

    def update(self):
        # 方法作用：每帧更新敌机下落位置与横向摆动
        self.y += self.speed                # 向下移动一帧
        self.wobble += 0.04                 # 推进摆动相位
        self.x += math.sin(self.wobble) * 1.5  # 正弦摆动让敌机路线更自然
        if self.y > SCREEN_HEIGHT + 60:     # 判断敌机是否飞出屏幕底部
            self.alive = False             # 飞出后标记不存活（不算击毁）

    def try_fire(self):
        # 方法作用：按概率尝试开火，返回一颗敌机子弹或 None
        # 返回值：生成的 Bullet 对象，或 None 表示本帧不开火
        if random.random() < self.fire_chance:  # 用随机数与开火概率比较
            return Bullet(self.x, self.y + self.height / 2, ENEMY_BULLET_SPEED, friendly=False, radius=5)  # 发射向下子弹
        return None                         # 未达到概率则不开火

    def hit(self):
        # 方法作用：敌机受击一次，扣血并判断是否击毁
        self.hp -= 1                        # 血量减一
        return self.hp <= 0                 # 血量归零则返回 True 表示已击毁

    def get_rect(self):
        # 方法作用：返回敌机矩形碰撞盒
        return pygame.Rect(                 # 构造敌机碰撞矩形
            self.x - self.width / 2,        # 左边界（以中心计算）
            self.y - self.height / 2,       # 上边界（以中心计算）
            self.width,                      # 宽度
            self.height                     # 高度
        )

    def draw(self, surface):
        # 方法作用：绘制敌机机身、座舱与机翼
        rect = self.get_rect()              # 取出碰撞盒用于定位绘制
        pygame.draw.ellipse(surface, self.color, rect)  # 绘制椭圆机身
        cockpit = pygame.Rect(               # 构造座舱矩形
            self.x - 8, self.y - 10, 16, 14  # 座舱位于机身上半部居中
        )
        pygame.draw.ellipse(surface, COLOR_BLACK, cockpit)  # 绘制黑色座舱
        pygame.draw.line(surface, self.color, (self.x - self.width / 2, self.y), (self.x + self.width / 2, self.y), 5)  # 绘制水平机翼


# ========== 12. 玩家飞机类 ==========
class Player:
    # 类作用：表示玩家操控的战机，负责移动、开火、受击与状态记录
    def __init__(self):
        # 初始化方法：把玩家放在屏幕底部中央，初始化生命与火力状态
        self.width = 44                    # 记录玩家机身宽度
        self.height = 40                   # 记录玩家机身高度
        self.x = SCREEN_WIDTH / 2          # 初始横坐标为屏幕中央
        self.y = SCREEN_HEIGHT - 110       # 初始纵坐标靠近屏幕底部
        self.hp = PLAYER_MAX_HP            # 初始化生命值为最大值
        self.fire_cooldown = 0             # 记录开火冷却剩余帧数
        self.invincible = 0                # 记录剩余无敌闪烁帧数
        self.power_level = 1               # 记录火力等级：1单发，2双发，3三发
        self.power_timer = 0                # 记录火力升级剩余时间（帧）
        self.target_x = self.x             # 记录指针/手指指向的目标横坐标
        self.target_y = self.y             # 记录指针/手指指向的目标纵坐标
        self.pointer_active = False         # 标记指针跟随是否生效，键盘一动就让位给键盘

    def set_target(self, x, y):
        # 方法作用：记录外部指针（鼠标/手指）给出的目标位置
        self.target_x = x                  # 更新目标横坐标
        self.target_y = y                  # 更新目标纵坐标
        self.pointer_active = True          # 指针给出了新目标，重新启用指针跟随

    def update(self, keys):
        # 方法作用：每帧根据键盘与指针更新位置，并处理冷却、无敌、火力计时
        # 参数 keys：pygame 键盘按键状态集合
        dx = 0                             # 初始化水平位移量
        dy = 0                             # 初始化垂直位移量
        if keys[pygame.K_LEFT] or keys[pygame.K_a]:   # 按下左键或 A 键
            dx -= PLAYER_SPEED             # 水平位移向左
        if keys[pygame.K_RIGHT] or keys[pygame.K_d]:  # 按下右键或 D 键
            dx += PLAYER_SPEED             # 水平位移向右
        if keys[pygame.K_UP] or keys[pygame.K_w]:     # 按上键或 W 键
            dy -= PLAYER_SPEED             # 垂直位移向上
        if keys[pygame.K_DOWN] or keys[pygame.K_s]:   # 按下键或 S 键
            dy += PLAYER_SPEED             # 垂直位移向下
        self.x += dx                       # 应用键盘水平位移
        self.y += dy                       # 应用键盘垂直位移
        if dx != 0 or dy != 0:             # 只要键盘本帧产生了位移
            self.pointer_active = False     # 立刻放弃指针跟随，避免两套输入互相拉扯
        elif self.pointer_active:          # 键盘未动且指针跟随仍生效时才做缓动
            offset_x = self.target_x - self.x  # 计算与指针目标的横向差值
            offset_y = self.target_y - self.y  # 计算与指针目标的纵向差值
            if math.hypot(offset_x, offset_y) > 1:  # 距离仍在阈值外才继续平滑跟随
                self.x += offset_x * 0.35   # 平滑跟随指针横坐标
                self.y += offset_y * 0.35   # 平滑跟随指针纵坐标
            else:                           # 已经贴到鼠标/手指所在位置
                self.pointer_active = False  # 结束本次跟随，避免无限微调
        self.x = max(self.width / 2, min(self.x, SCREEN_WIDTH - self.width / 2))  # 限制横坐标不越左右边界
        self.y = max(self.height / 2, min(self.y, SCREEN_HEIGHT - self.height / 2))  # 限制纵坐标不越上下边界
        if self.fire_cooldown > 0:          # 如果开火冷却尚未结束
            self.fire_cooldown -= 1         # 冷却帧数减一
        if self.invincible > 0:             # 如果处于无敌时间内
            self.invincible -= 1            # 无敌帧数减一
        if self.power_timer > 0:           # 如果火力升级仍在持续
            self.power_timer -= 1          # 火力计时减一
            if self.power_timer == 0:      # 火力计时归零
                self.power_level = 1        # 火力等级降回单发

    def try_fire(self):
        # 方法作用：冷却结束时按火力等级返回子弹列表，否则返回空列表
        # 返回值：本帧应发射的 Bullet 对象列表
        if self.fire_cooldown > 0:          # 冷却未结束则不开火
            return []                       # 返回空子弹列表
        self.fire_cooldown = 12             # 设置下一次开火前的冷却帧数
        bullets = []                       # 准备子弹列表
        if self.power_level == 1:          # 单发火力：正中一颗
            bullets.append(Bullet(self.x, self.y - self.height / 2, BULLET_SPEED, friendly=True))  # 正中子弹
        elif self.power_level == 2:         # 双发火力：左右各一颗
            bullets.append(Bullet(self.x - 12, self.y - self.height / 2, BULLET_SPEED, friendly=True))  # 左侧子弹
            bullets.append(Bullet(self.x + 12, self.y - self.height / 2, BULLET_SPEED, friendly=True))  # 右侧子弹
        else:                              # 三发火力：正中加左右斜向
            bullets.append(Bullet(self.x, self.y - self.height / 2, BULLET_SPEED, friendly=True))  # 正中子弹
            bullets.append(Bullet(self.x - 16, self.y - self.height / 2 + 6, BULLET_SPEED - 1, friendly=True))  # 左侧斜子弹
            bullets.append(Bullet(self.x + 16, self.y - self.height / 2 + 6, BULLET_SPEED - 1, friendly=True))  # 右侧斜子弹
        return bullets                     # 返回本帧生成的全部子弹

    def take_damage(self):
        # 方法作用：玩家受击扣血，若不处于无敌中则返回 True 表示真正掉血
        if self.invincible > 0:            # 处于无敌时间内不扣血
            return False                   # 返回 False 表示本次伤害被忽略
        self.hp = max(self.hp - 1, 0)      # 生命值减一，且不允许跌破 0
        self.invincible = INVINCIBLE_FRAMES  # 进入受击后无敌状态
        return True                        # 返回 True 表示成功扣血

    def heal(self):
        # 方法作用：拾取加血道具，恢复一点生命（不超过上限）
        self.hp = min(self.hp + 1, PLAYER_MAX_HP)  # 生命加一但封顶在最大值

    def upgrade_power(self):
        # 方法作用：拾取火力道具，提升火力等级并重置持续时间
        self.power_level = min(self.power_level + 1, 3)  # 火力升级，最高三发
        self.power_timer = FPS * 12        # 火力持续约 12 秒

    def get_rect(self):
        # 方法作用：返回玩家矩形碰撞盒
        return pygame.Rect(                 # 构造玩家碰撞矩形
            self.x - self.width / 2,        # 左边界
            self.y - self.height / 2,       # 上边界
            self.width,                     # 宽度
            self.height                     # 高度
        )

    def draw(self, surface):
        # 方法作用：绘制玩家战机，无敌时做闪烁处理
        if self.invincible > 0 and self.invincible % 10 < 5:  # 无敌帧内按间隔闪烁
            return                          # 该帧跳过绘制，形成闪烁效果
        body = self.get_rect()              # 取出玩家碰撞盒定位
        pygame.draw.polygon(surface, COLOR_GREEN, [  # 绘制三角形主机翼
            (self.x, self.y - self.height / 2),        # 机头顶点
            (self.x - self.width / 2, self.y + self.height / 2),  # 左翼后点
            (self.x, self.y + self.height / 4),         # 机腹内点
            (self.x + self.width / 2, self.y + self.height / 2)  # 右翼后点
        ])
        pygame.draw.ellipse(surface, COLOR_WHITE, (self.x - 8, self.y - 8, 16, 20))  # 绘制白色座舱
        pygame.draw.rect(surface, COLOR_GRAY, (self.x - self.width / 2, self.y + 6, self.width, 6))  # 绘制尾部水平机翼


# ========== 13. 游戏主控类：状态、资源与主流程 ==========
class Game:
    # 类作用：串联所有对象，管理游戏状态、事件、更新、绘制与碰撞结算
    def __init__(self):
        # 初始化方法：初始化 pygame、窗口、字体与各类游戏数据
        pygame.init()                      # 初始化 pygame 全部子系统
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT), DISPLAY_FLAGS)  # 创建可自适应缩放的窗口
        pygame.display.set_caption(TITLE)   # 设置窗口标题
        self.clock = pygame.time.Clock()    # 创建时钟对象用于控制帧率
        self.font_big = load_font(44)        # 加载大号字体用于标题与结算
        self.font_mid = load_font(26)       # 加载中号字体用于提示文字
        self.font_small = load_font(18)      # 加载小号字体用于 HUD 信息
        self.state = STATE_START            # 初始状态设为开始菜单
        self.stars = [Star() for _ in range(70)]  # 生成 70 颗背景星星
        self.reset_game()                   # 调用方法初始化一局游戏数据

    def reset_game(self):
        # 方法作用：重置一局游戏的分数、对象列表与玩家状态
        self.player = Player()              # 创建新的玩家对象
        self.player_bullets = []            # 清空我方子弹列表
        self.enemy_bullets = []             # 清空敌方子弹列表
        self.enemies = []                   # 清空敌机列表
        self.powerups = []                  # 清空道具列表
        self.particles = []                 # 清空爆炸粒子列表
        self.score = 0                      # 分数清零
        self.spawn_timer = 0                # 敌机生成计时器清零
        self.boss_timer = FPS * 18          # 大型敌机首次出现倒计时（约18秒）
        self.text_cache = {}                # 清空 HUD 文字缓存，避免沿用上一局的旧分数

    def handle_events(self):
        # 方法作用：处理外部事件（退出、按键、鼠标、触屏），并更新玩家目标
        for event in pygame.event.get():    # 遍历当前全部事件
            if event.type == pygame.QUIT:   # 收到窗口关闭事件
                self.quit_game()            # 调用退出方法
            elif event.type == pygame.KEYDOWN:  # 收到按键按下事件
                if event.key == pygame.K_ESCAPE:  # 按下 Esc 键
                    self.quit_game()        # 退出游戏
                if event.key == pygame.K_p:  # 按下 P 键
                    self.toggle_pause()      # 切换暂停/继续状态
                if self.state == STATE_START and event.key == pygame.K_RETURN:  # 开始界面按回车
                    self.start_game()        # 开始新一局
                elif self.state == STATE_GAMEOVER and event.key == pygame.K_RETURN:  # 结束界面按回车
                    self.reset_game()        # 重置一局
                    self.state = STATE_PLAYING  # 直接进入游戏中
            elif event.type == pygame.MOUSEBUTTONDOWN:  # 收到鼠标按下事件
                if not getattr(event, "touch", False):  # 跳过触屏合成的鼠标事件，避免与 FINGERDOWN 重复触发
                    self.handle_pointer(event.pos, tap=True)  # 把鼠标位置交给指针处理（按点击处理）
            elif event.type == pygame.MOUSEMOTION and event.buttons[0]:  # 按住鼠标拖动
                if not getattr(event, "touch", False):  # 同样跳过触屏合成的拖动事件
                    self.handle_pointer(event.pos, tap=False)  # 跟随更新指针目标（按拖动处理）
            elif event.type == pygame.FINGERDOWN:  # 收到安卓手指按下事件
                pos = (event.x * SCREEN_WIDTH, event.y * SCREEN_HEIGHT)  # 归一化坐标换算为逻辑像素
                self.handle_pointer(pos, tap=True)  # 交给指针处理（按点击处理）
            elif event.type == pygame.FINGERMOTION:  # 收到安卓手指移动事件
                pos = (event.x * SCREEN_WIDTH, event.y * SCREEN_HEIGHT)  # 换算为逻辑像素坐标
                self.handle_pointer(pos, tap=False)  # 跟随更新指针目标（按拖动处理）

    def handle_pointer(self, pos, tap=False):
        # 方法作用：根据当前状态处理指针点击（tap=True）或按住拖动（tap=False）
        # 参数 pos：逻辑像素坐标元组 (x, y)；tap：是否为一次按下动作
        if self.state == STATE_START:       # 在开始界面
            if tap:                         # 只有点按才开局，拖动不误触发
                self.start_game()           # 开始新一局
        elif self.state == STATE_GAMEOVER:  # 在结束界面
            if tap:                         # 只有点按才重开，避免手指还按着时立刻重开
                self.reset_game()           # 重置一局
                self.state = STATE_PLAYING  # 进入游戏中
        elif self.state == STATE_PAUSED:    # 在暂停界面
            if tap:                         # 只有点按才继续，拖动不误触发
                self.state = STATE_PLAYING  # 点击后继续游戏
        else:                               # 游戏进行中
            if tap and PAUSE_BUTTON_RECT.collidepoint(pos):  # 点中了右上角暂停按钮
                self.player.pointer_active = False  # 放开指针跟随，恢复时战机不会飘向按钮
                self.toggle_pause()         # 进入暂停状态
                return                      # 本次点击不再当作移动指令
            self.player.set_target(pos[0], pos[1])  # 更新玩家跟随目标位置

    def start_game(self):
        # 方法作用：从开始菜单进入游戏，重置数据并切换状态
        self.reset_game()                   # 重置本局全部数据
        self.state = STATE_PLAYING          # 切换到游戏进行状态

    def toggle_pause(self):
        # 方法作用：在游戏中与暂停状态之间切换（键盘 P 键与右上角按钮共用）
        if self.state == STATE_PLAYING:     # 当前正在游戏
            self.state = STATE_PAUSED       # 切换为暂停
            self.player.pointer_active = False  # 清掉指针跟随，恢复后战机不会自己飘走
        elif self.state == STATE_PAUSED:     # 当前处于暂停
            self.state = STATE_PLAYING      # 恢复为游戏中

    def quit_game(self):
        # 方法作用：安全退出 pygame 与解释器
        pygame.quit()                       # 关闭 pygame 子系统
        sys.exit()                          # 退出 Python 解释器

    def spawn_enemies(self):
        # 方法作用：按计时器生成普通敌机与大型敌机
        self.spawn_timer += 1               # 普通敌机计时器加一帧
        if self.spawn_timer >= SPAWN_INTERVAL:  # 达到生成间隔
            self.spawn_timer = 0            # 计时器清零
            self.enemies.append(Enemy(big=False))  # 生成一架普通敌机
        self.boss_timer -= 1                # 大型敌机倒计时减一帧
        if self.boss_timer <= 0:            # 倒计时归零
            self.boss_timer = FPS * 15      # 重置下一架大型敌机倒计时（约15秒）
            self.enemies.append(Enemy(big=True))   # 生成一架大型敌机

    def update_gameplay(self):
        # 方法作用：游戏进行中的核心更新逻辑：移动、生成、开火、碰撞结算
        keys = pygame.key.get_pressed()     # 获取当前全部按键状态
        self.player.update(keys)             # 更新玩家位置与状态
        for bullet in self.player.try_fire():  # 取出本帧玩家应发射的子弹
            self.player_bullets.append(bullet)  # 加入我方子弹列表
        self.spawn_enemies()                # 按规则生成敌机
        for enemy in self.enemies:          # 遍历所有敌机
            enemy.update()                 # 更新敌机位置
            shot = enemy.try_fire()         # 尝试让敌机开火
            if shot:                        # 如果生成了子弹
                self.enemy_bullets.append(shot)  # 加入敌方子弹列表
        for bullet in self.player_bullets:  # 遍历我方子弹
            bullet.update()                # 更新子弹位置
        for bullet in self.enemy_bullets:    # 遍历敌方子弹
            bullet.update()                # 更新子弹位置
        for powerup in self.powerups:       # 遍历道具
            powerup.update()               # 更新道具位置
        for particle in self.particles:      # 遍历爆炸粒子
            particle.update()              # 更新粒子位置与寿命
        self.handle_collisions()            # 调用碰撞检测与结算
        # 清理所有已不存活的对象，避免列表无限增长
        self.player_bullets = [b for b in self.player_bullets if b.alive]  # 保留存活我方子弹
        self.enemy_bullets = [b for b in self.enemy_bullets if b.alive]     # 保留存活敌方子弹
        self.enemies = [e for e in self.enemies if e.alive]                 # 保留存活敌机
        self.powerups = [p for p in self.powerups if p.alive]              # 保留存活道具
        self.particles = [p for p in self.particles if p.life > 0]        # 保留仍有寿命的粒子

    def handle_collisions(self):
        # 方法作用：检测并结算子弹击敌、敌机撞玩家、道具拾取等碰撞
        # 我方子弹命中敌机
        for bullet in self.player_bullets:  # 遍历每颗我方子弹
            if not bullet.alive:            # 子弹已失效则跳过
                continue
            for enemy in self.enemies:       # 遍历每架敌机
                if not enemy.alive:          # 敌机已击毁则跳过
                    continue
                if bullet.get_rect().colliderect(enemy.get_rect()):  # 子弹与敌机矩形相交
                    bullet.alive = False     # 子弹命中后消失
                    destroyed = enemy.hit()  # 敌机扣血并判断是否击毁
                    if destroyed:           # 如果敌机被击毁
                        self.on_enemy_destroyed(enemy)  # 执行击毁结算
                    break                    # 跳出敌机循环，一颗子弹只命中一个目标
        # 敌方子弹命中玩家
        for bullet in self.enemy_bullets:  # 遍历每颗敌方子弹
            if not bullet.alive:            # 子弹已失效则跳过
                continue
            if bullet.get_rect().colliderect(self.player.get_rect()):  # 子弹命中玩家
                bullet.alive = False        # 子弹消失
                self.on_player_hit()        # 执行玩家受击结算
                if self.state != STATE_PLAYING:  # 本局已经结束
                    return                  # 立即停止后续结算，避免死后再扣血
        # 敌机机身直接撞击玩家
        for enemy in self.enemies:         # 遍历每架敌机
            if not enemy.alive:             # 敌机已失效则跳过
                continue
            if not enemy.get_rect().colliderect(self.player.get_rect()):  # 机身未与玩家相撞
                continue                    # 跳过这架敌机
            if self.player.invincible > 0:  # 玩家正在无敌时间内
                continue                    # 视作直接穿过：既不扣血，也不让敌机白炸
            enemy.alive = False             # 敌机坠毁
            self.spawn_explosion(enemy.x, enemy.y)  # 生成撞击爆炸
            self.on_player_hit()            # 玩家同时受击
            if self.state != STATE_PLAYING:  # 本局已经结束
                return                      # 立即停止后续结算，避免死后再扣血
        # 道具被玩家拾取
        for powerup in self.powerups:       # 遍历每个道具
            if not powerup.alive:           # 道具已失效则跳过
                continue
            if powerup.get_rect().colliderect(self.player.get_rect()):  # 玩家碰到道具
                powerup.alive = False       # 道具被拾取消失
                if powerup.kind == "heal":  # 如果是加血道具
                    self.player.heal()      # 恢复玩家生命
                else:                       # 否则是火力道具
                    self.player.upgrade_power()  # 提升玩家火力

    def on_enemy_destroyed(self, enemy):
        # 方法作用：敌机被击毁后的结算：加分、爆粒子、概率掉道具
        self.score += enemy.score           # 累加击毁得分
        self.spawn_explosion(enemy.x, enemy.y)  # 在敌机位置生成爆炸粒子
        if random.random() < POWERUP_DROP_RATE:  # 按概率判定掉落道具
            kind = "heal" if random.random() < 0.5 else "power"  # 随机决定道具类型
            self.powerups.append(PowerUp(enemy.x, enemy.y, kind))  # 在敌机位置生成道具

    def on_player_hit(self):
        # 方法作用：玩家受击结算，扣血并在生命归零时切换到结束界面
        damaged = self.player.take_damage()  # 尝试扣血，记录是否真正掉血
        if damaged and self.player.hp <= 0:  # 如果真正掉血且生命归零
            self.state = STATE_GAMEOVER     # 切换到游戏结束状态

    def spawn_explosion(self, x, y):
        # 方法作用：在指定位置生成一组爆炸粒子
        for _ in range(18):                 # 循环生成 18 颗火花粒子
            self.particles.append(Particle(x, y))  # 加入粒子列表

    def cached_text(self, key, text, font, color):
        # 方法作用：按缓存键复用已渲染的文字画面，避免每帧重复栅格化
        # 参数 key：缓存键；text：文字内容；font：字体；color：颜色
        # 返回值：可直接 blit 到屏幕的 Surface
        cached = self.text_cache.get(key)   # 取出该键已有的缓存条目
        if cached is not None and cached[0] == text:  # 文字内容与缓存一致才复用
            return cached[1]                # 直接返回缓存的画面
        rendered = font.render(text, True, color)  # 内容变化时才重新渲染
        self.text_cache[key] = (text, rendered)  # 写入缓存，供后续帧复用
        return rendered                     # 返回本次渲染结果

    def draw_hud(self):
        # 方法作用：在游戏界面顶部绘制分数、生命与火力状态
        score_text = self.cached_text("score", f"SCORE: {self.score}", self.font_small, COLOR_WHITE)  # 取分数文字画面
        self.screen.blit(score_text, (16, 12))  # 把分数贴到左上角
        hp_text = self.cached_text("hp", f"HP: {self.player.hp}/{PLAYER_MAX_HP}", self.font_small, COLOR_GREEN)  # 取生命文字画面
        self.screen.blit(hp_text, (16, 36))  # 把生命贴到分数下方
        power_text = self.cached_text("power", f"POWER: {self.player.power_level}", self.font_small, COLOR_BLUE)  # 取火力文字画面
        self.screen.blit(power_text, (16, 60))  # 把火力贴到生命下方

    def draw_pause_button(self):
        # 方法作用：绘制右上角暂停按钮（圆角深色底 + 灰色描边 + 两根白色竖条）
        pygame.draw.rect(self.screen, (26, 30, 48), PAUSE_BUTTON_RECT, border_radius=10)  # 绘制按钮底色
        pygame.draw.rect(self.screen, COLOR_GRAY, PAUSE_BUTTON_RECT, 2, border_radius=10)  # 绘制按钮描边
        bar_width = 6                       # 暂停图标的单根竖条宽度
        bar_height = 20                     # 暂停图标的单根竖条高度
        bar_top = PAUSE_BUTTON_RECT.centery - bar_height // 2  # 竖条顶部（垂直居中）
        left_bar_x = PAUSE_BUTTON_RECT.centerx - 9   # 左侧竖条的左边界
        right_bar_x = PAUSE_BUTTON_RECT.centerx + 3  # 右侧竖条的左边界
        pygame.draw.rect(self.screen, COLOR_WHITE, (left_bar_x, bar_top, bar_width, bar_height), border_radius=2)  # 左侧竖条
        pygame.draw.rect(self.screen, COLOR_WHITE, (right_bar_x, bar_top, bar_width, bar_height), border_radius=2)  # 右侧竖条

    def draw_center_text(self, text, font, color, y_offset=0):
        # 方法作用：在屏幕水平居中位置绘制文字
        # 参数 text：文字内容；font：字体；color：颜色；y_offset：纵向偏移
        rendered = font.render(text, True, color)  # 渲染文字为图像
        rect = rendered.get_rect()             # 取得文字图像矩形
        rect.center = (SCREEN_WIDTH / 2, SCREEN_HEIGHT / 2 + y_offset)  # 居中并应用纵向偏移
        self.screen.blit(rendered, rect)       # 贴到屏幕上

    def draw(self):
        # 方法作用：按当前状态绘制整帧画面
        self.screen.fill(COLOR_BLACK)          # 先以背景色清空整屏
        for star in self.stars:                # 遍历背景星星
            star.draw(self.screen)             # 绘制每颗星星
        if self.state == STATE_START:          # 如果处于开始菜单
            self.draw_center_text(TITLE, self.font_big, COLOR_GREEN, -120)  # 绘制大标题
            self.draw_center_text("Touch / Click to Start", self.font_mid, COLOR_WHITE, -40)  # 绘制开始提示
            self.draw_center_text("Move: drag or arrow keys", self.font_small, COLOR_GRAY, 10)  # 绘制移动说明
            self.draw_center_text("Pause: P key or top-right button", self.font_small, COLOR_GRAY, 36)  # 绘制暂停说明
        elif self.state == STATE_PLAYING or self.state == STATE_PAUSED:  # 游戏中或暂停
            for powerup in self.powerups:      # 绘制所有道具
                powerup.draw(self.screen)      # 贴出道具
            for enemy in self.enemies:         # 绘制所有敌机
                enemy.draw(self.screen)        # 贴出敌机
            for bullet in self.player_bullets:  # 绘制我方子弹
                bullet.draw(self.screen)       # 贴出我方子弹
            for bullet in self.enemy_bullets:  # 绘制敌方子弹
                bullet.draw(self.screen)       # 贴出敌方子弹
            self.player.draw(self.screen)      # 绘制玩家战机
            for particle in self.particles:    # 绘制爆炸粒子
                particle.draw(self.screen)     # 贴出粒子
            self.draw_hud()                    # 绘制顶部 HUD 信息
            if self.state == STATE_PLAYING:     # 仅游戏进行中显示暂停按钮
                self.draw_pause_button()        # 绘制右上角暂停按钮
            if self.state == STATE_PAUSED:     # 如果处于暂停状态
                overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))  # 创建半透明遮罩层
                overlay.set_alpha(160)         # 设置遮罩透明度
                overlay.fill(COLOR_BLACK)       # 填充遮罩颜色
                self.screen.blit(overlay, (0, 0))  # 盖上遮罩压暗背景
                self.draw_center_text("PAUSED", self.font_big, COLOR_YELLOW, 0)  # 绘制暂停标题
                self.draw_center_text("Touch to Resume", self.font_mid, COLOR_WHITE, 50)  # 绘制继续提示
        elif self.state == STATE_GAMEOVER:     # 如果处于结束界面
            for enemy in self.enemies:         # 保留绘制场上剩余敌机
                enemy.draw(self.screen)        # 贴出敌机
            self.draw_center_text("GAME OVER", self.font_big, COLOR_RED, -80)  # 绘制结束标题
            self.draw_center_text(f"Score: {self.score}", self.font_mid, COLOR_WHITE, 0)  # 绘制最终得分
            self.draw_center_text("Touch / Click to Restart", self.font_mid, COLOR_YELLOW, 50)  # 绘制重开提示

    def run(self):
        # 方法作用：游戏主循环，不断处理事件、更新、绘制并控制帧率
        while True:                            # 进入无限主循环
            self.handle_events()               # 处理输入事件
            if self.state == STATE_PLAYING:    # 仅在游戏中更新玩法逻辑
                self.update_gameplay()         # 更新移动、生成、碰撞等
            else:                              # 非游戏中状态仍需更新背景
                for star in self.stars:        # 遍历星星
                    star.update()              # 让背景继续滚动
            self.draw()                       # 绘制当前帧
            pygame.display.flip()              # 把后备画面刷新到屏幕
            self.clock.tick(FPS)               # 按限定帧率等待下一帧


# ========== 14. 程序入口 ==========
def main():
    # 函数作用：创建游戏对象并启动主循环
    game = Game()                          # 实例化主控游戏对象
    game.run()                             # 进入游戏主循环


if __name__ == "__main__":
    # 判断是否作为主程序直接运行（被打包或被执行时进入）
    main()                                 # 调用入口函数启动游戏