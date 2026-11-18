"""本地覆盖版 p4a recipe：pygame

为什么要覆盖
------------
python-for-android（p4a）自带的 pygame recipe 一直锁在 pygame 2.1.0（2022 年），
而 2.1.0 的 ``src_c/_sdl2/sdl2.c`` 里有::

    #if CYTHON_USE_PYLONG_INTERNALS
    #include "longintrepr.h"

这个头文件从 CPython 3.11 起就被移到了 ``Include/cpython/`` 下，顶层不再存在，
于是不论 p4a 内置的是 Python 3.11（v2024.01.21）还是 3.14（master），
编译都停在::

    src_c/_sdl2/sdl2.c:211:12: fatal error: 'longintrepr.h' file not found

pygame 2.5.x 的 C 源码已经不引用这个头文件，因此这里把版本提到 2.5.2，
其余构建逻辑与 p4a v2024.01.21 的 recipe 完全一致（Setup.Android.SDL2.in 模板两版相同）。

下载源为什么是 PyPI 的 sdist，而不是 GitHub 源码归档
---------------------------------------------------
GitHub 的 ``archive/{version}.tar.gz`` 只提交了 ``.pyx``（Cython 源），没有生成的 ``.c``，
setup.py 于是会走编译 Cython 分支，需要 hostpython 里装有 Cython，否则直接失败::

    Compiling Cython files
    You need cython. https://cython.org/, python -m pip install cython --user

而 PyPI 的 sdist（15.7 MB，比源码归档大 10 MB）带了全套预生成 ``.c``，
setup.py 检测到 ``src_c/_sdl2/audio.c`` 与 ``src_c/pypm.c`` 存在就打印
``Skipping Cython compilation``，完全不需要 Cython。

使用方式：buildozer.spec 里 ``p4a.local_recipes = ./tools/p4a_recipes``
"""

from os.path import join

from pythonforandroid.recipe import CompiledComponentsPythonRecipe
from pythonforandroid.toolchain import current_directory


class Pygame2Recipe(CompiledComponentsPythonRecipe):
    """
    Recipe to build apps based on SDL2-based pygame.

    .. warning:: Some pygame functionality is still untested, and some
        dependencies like freetype, postmidi and libjpeg are currently
        not part of the build. It's usable, but not complete.
    """

    # 与上游的差异：2.1.0 -> 2.5.2，且下载源换成带预生成 C 的 PyPI sdist
    version = '2.5.2'
    url = ('https://files.pythonhosted.org/packages/c6/aa/'
           '2c0c867d6cff00966cfc2152b25f61599f87e88b239e4dcb8ad5357f0f69/'
           'pygame-{version}.tar.gz')

    site_packages_name = 'pygame'
    name = 'pygame'

    depends = ['sdl2', 'sdl2_image', 'sdl2_mixer', 'sdl2_ttf', 'setuptools', 'jpeg', 'png']
    call_hostpython_via_targetpython = False  # Due to setuptools
    install_in_hostpython = False

    def prebuild_arch(self, arch):
        super().prebuild_arch(arch)
        with current_directory(self.get_build_dir(arch.arch)):
            setup_template = open(join("buildconfig", "Setup.Android.SDL2.in")).read()
            env = self.get_recipe_env(arch)
            env['ANDROID_ROOT'] = join(self.ctx.ndk.sysroot, 'usr')

            png = self.get_recipe('png', self.ctx)
            png_lib_dir = join(png.get_build_dir(arch.arch), '.libs')
            png_inc_dir = png.get_build_dir(arch)

            jpeg = self.get_recipe('jpeg', self.ctx)
            jpeg_inc_dir = jpeg_lib_dir = jpeg.get_build_dir(arch.arch)

            sdl_mixer_includes = ""
            sdl2_mixer_recipe = self.get_recipe('sdl2_mixer', self.ctx)
            for include_dir in sdl2_mixer_recipe.get_include_dirs(arch):
                sdl_mixer_includes += f"-I{include_dir} "

            sdl2_image_includes = ""
            sdl2_image_recipe = self.get_recipe('sdl2_image', self.ctx)
            for include_dir in sdl2_image_recipe.get_include_dirs(arch):
                sdl2_image_includes += f"-I{include_dir} "

            setup_file = setup_template.format(
                sdl_includes=(
                    " -I" + join(self.ctx.bootstrap.build_dir, 'jni', 'SDL', 'include') +
                    " -L" + join(self.ctx.bootstrap.build_dir, "libs", str(arch)) +
                    " -L" + png_lib_dir + " -L" + jpeg_lib_dir + " -L" + arch.ndk_lib_dir_versioned),
                sdl_ttf_includes="-I"+join(self.ctx.bootstrap.build_dir, 'jni', 'SDL2_ttf'),
                sdl_image_includes=sdl2_image_includes,
                sdl_mixer_includes=sdl_mixer_includes,
                jpeg_includes="-I"+jpeg_inc_dir,
                png_includes="-I"+png_inc_dir,
                freetype_includes=""
            )
            open("Setup", "w").write(setup_file)

    def get_recipe_env(self, arch):
        env = super().get_recipe_env(arch)
        env['USE_SDL2'] = '1'
        env["PYGAME_CROSS_COMPILE"] = "TRUE"
        env["PYGAME_ANDROID"] = "TRUE"
        return env


recipe = Pygame2Recipe()
