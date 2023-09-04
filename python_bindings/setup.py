import glob
import os
import platform
import re
import shutil
import subprocess
import sys
from datetime import datetime
from importlib.metadata import version
from pathlib import Path
from pprint import pprint

from setuptools import Extension, setup
from setuptools.command.build_ext import build_ext


def check_env(build):
    return os.environ.get(build, 0) in {"1", "true", "True", "ON", "YES"}


class CMakeExtension(Extension):
    def __init__(self, name: str, sourcedir: str = "") -> None:
        super().__init__(name, sources=[])
        self.sourcedir = os.fspath(Path(sourcedir).resolve())


def get_exe_suffix():
    if platform.system() == "Windows":
        suffix = ".exe"
    else:
        suffix = ""
    return suffix


def get_cross_cmake_args():
    cmake_args = {}

    CIBW_ARCHS = os.environ.get("CIBW_ARCHS")
    if CIBW_ARCHS in {"arm64", "aarch64", "ARM64"}:
        ARCH = cmake_args["LLVM_TARGETS_TO_BUILD"] = "AArch64"
    elif CIBW_ARCHS in {"x86_64", "AMD64"}:
        ARCH = cmake_args["LLVM_TARGETS_TO_BUILD"] = "X86"
    else:
        raise ValueError(f"unknown CIBW_ARCHS={CIBW_ARCHS}")
    if CIBW_ARCHS != platform.machine():
        # cmake_args["LLVM_USE_HOST_TOOLS"] = "ON"
        cmake_args["CMAKE_SYSTEM_NAME"] = platform.system()

    if platform.system() == "Darwin":
        if ARCH == "AArch64":
            cmake_args["CMAKE_OSX_ARCHITECTURES"] = "arm64"
        elif ARCH == "X86":
            cmake_args["CMAKE_OSX_ARCHITECTURES"] = "x86_64"

    return cmake_args


class CMakeBuild(build_ext):
    def build_extension(self, ext: CMakeExtension) -> None:
        ext_fullpath = Path.cwd() / self.get_ext_fullpath(ext.name)
        extdir = ext_fullpath.parent.resolve()
        install_dir = extdir
        cfg = "Release"

        cmake_generator = os.environ.get("CMAKE_GENERATOR", "Ninja")
        import mlir

        MLIR_INSTALL_ABS_PATH = Path(mlir.__path__[0])
        if platform.system() == "Windows":
            # fatal error LNK1170: line in command file contains 131071 or more characters
            shutil.move(MLIR_INSTALL_ABS_PATH, "/tmp/m")
            MLIR_INSTALL_ABS_PATH = Path("/tmp/m").absolute()

        GLIBCXX_USE_CXX11_ABI = os.environ.get("GLIBCXX_USE_CXX11_ABI", 0)

        cmake_args = [
            f"-G {cmake_generator}",
            "-DLLVM_CCACHE_BUILD=ON",
            "-DMLIR_INCLUDE_TESTS=ON",
            f"-DCMAKE_PREFIX_PATH={MLIR_INSTALL_ABS_PATH}",
            f"-DCMAKE_INSTALL_PREFIX={install_dir}",
            f"-D_GLIBCXX_USE_CXX11_ABI={GLIBCXX_USE_CXX11_ABI}",
            f"-DPython3_EXECUTABLE={sys.executable}",
            f"-DCMAKE_BUILD_TYPE={cfg}",  # not used on MSVC, but no harm
        ]
        if platform.system() == "Windows":
            cmake_args += [
                "-DCMAKE_C_COMPILER=cl",
                "-DCMAKE_CXX_COMPILER=cl",
                "-DCMAKE_MSVC_RUNTIME_LIBRARY=MultiThreaded",
                "-DCMAKE_C_FLAGS=/MT",
                "-DCMAKE_CXX_FLAGS=/MT",
            ]

        cmake_args_dict = get_cross_cmake_args()
        cmake_args += [f"-D{k}={v}" for k, v in cmake_args_dict.items()]

        if BUILD_CUDA:
            cmake_args += [
                "-DMLIR_ENABLE_CUDA_RUNNER=ON",
                "-DMLIR_ENABLE_CUDA_CONVERSIONS=ON",
                "-DCMAKE_CUDA_COMPILER=/usr/local/cuda/bin/nvcc",
                "-DCUDAToolkit_ROOT=/usr/local/cuda",
            ]

        if BUILD_VULKAN:
            cmake_args += ["-DMLIR_ENABLE_VULKAN_RUNNER=ON"]
            if platform.system() == "Darwin":
                vulkan_library = "/usr/local/lib/libvulkan.dylib"
            elif platform.system() == "Linux":
                vulkan_library = "/usr/local/lib64/libvulkan.so"
            else:
                raise ValueError(f"unknown location for vulkan lib")
            cmake_args += [f"-DVulkan_LIBRARY={vulkan_library}"]

        if "CMAKE_ARGS" in os.environ:
            cmake_args += [item for item in os.environ["CMAKE_ARGS"].split(" ") if item]

        build_args = []
        if self.compiler.compiler_type != "msvc":
            if not cmake_generator or cmake_generator == "Ninja":
                try:
                    import ninja

                    ninja_executable_path = Path(ninja.BIN_DIR) / "ninja"
                    cmake_args += [
                        "-GNinja",
                        f"-DCMAKE_MAKE_PROGRAM:FILEPATH={ninja_executable_path}",
                    ]
                except ImportError:
                    pass

        else:
            single_config = any(x in cmake_generator for x in {"NMake", "Ninja"})
            contains_arch = any(x in cmake_generator for x in {"ARM", "Win64"})
            if not single_config and not contains_arch:
                PLAT_TO_CMAKE = {
                    "win32": "Win32",
                    "win-amd64": "x64",
                    "win-arm32": "ARM",
                    "win-arm64": "ARM64",
                }
                cmake_args += ["-A", PLAT_TO_CMAKE[self.plat_name]]
            if not single_config:
                cmake_args += [
                    f"-DCMAKE_LIBRARY_OUTPUT_DIRECTORY_{cfg.upper()}={extdir}"
                ]
                build_args += ["--config", cfg]

        if sys.platform.startswith("darwin"):
            cmake_args += ["-DCMAKE_OSX_DEPLOYMENT_TARGET=11.6"]
            # Cross-compile support for macOS - respect ARCHFLAGS if set
            archs = re.findall(r"-arch (\S+)", os.environ.get("ARCHFLAGS", ""))
            if archs:
                cmake_args += ["-DCMAKE_OSX_ARCHITECTURES={}".format(";".join(archs))]

        if "PARALLEL_LEVEL" not in os.environ:
            build_args += [f"-j{str(2 * os.cpu_count())}"]
        else:
            build_args += [f"-j{os.environ.get('PARALLEL_LEVEL')}"]

        build_temp = Path(self.build_temp) / ext.name
        if not build_temp.exists():
            build_temp.mkdir(parents=True)

        print("ENV", pprint(os.environ), file=sys.stderr)
        print("CMAKE_ARGS", cmake_args, file=sys.stderr)

        subprocess.run(
            ["cmake", ext.sourcedir, *cmake_args], cwd=build_temp, check=True
        )
        subprocess.run(
            ["cmake", "--build", ".", "--target", "install", *build_args],
            cwd=build_temp,
            check=True,
        )

        shlibs = [
            "mlir_async_runtime",
            "mlir_c_runner_utils",
            "mlir_float16_utils",
            "mlir_runner_utils",
        ]
        if BUILD_CUDA:
            shlibs += ["mlir_cuda_runtime"]
        if BUILD_OPENMP:
            shlibs += ["omp"]
        if BUILD_VULKAN:
            shlibs += ["vulkan-runtime-wrappers"]

        mlir_libs_dir = install_dir / "mlir" / "_mlir_libs"
        for shlib in shlibs:
            shlib_name = f"{shlib}"
            shlib_fps = glob.glob(
                str(MLIR_INSTALL_ABS_PATH.absolute() / "lib" / ("*" + shlib_name + "*"))
            )
            assert len(shlib_fps), f"couldn't find shlib {shlib_name}"
            for shlib_fp in shlib_fps:
                dst_path = mlir_libs_dir / os.path.basename(shlib_fp)
                shutil.copyfile(shlib_fp, dst_path, follow_symlinks=True)


BUILD_CUDA = check_env("BUILD_CUDA")
BUILD_VULKAN = check_env("BUILD_VULKAN")
BUILD_OPENMP = check_env("BUILD_OPENMP")

version = version("mlir")

_datetime, commit_hash = version.split("+")
now = datetime.now()
commit_hash = commit_hash.rsplit(".", 1)[-1]
llvm_url = f"https://github.com/llvm/llvm-project/commit/{commit_hash}"
setup(
    version=version,
    author="",
    name="mlir-python-bindings",
    include_package_data=True,
    author_email="maksim.levental@gmail.com",
    description=f"MLIR Python bindings. Created at {now} build of {llvm_url}",
    long_description=f"MLIR Python bindings. Created at {now} build of [llvm/llvm-project/{commit_hash}]({llvm_url})",
    long_description_content_type="text/markdown",
    ext_modules=[CMakeExtension("_mlir", sourcedir=".")],
    cmdclass={"build_ext": CMakeBuild},
    zip_safe=False,
    python_requires=">=3.10",
    download_url=llvm_url,
)
