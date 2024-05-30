import os
import platform
import re
import shutil
import subprocess
import sys
from datetime import datetime
from distutils.command.install_data import install_data
from pathlib import Path
from pprint import pprint

from setuptools import Extension, setup
from setuptools.command.build_ext import build_ext


class CMakeExtension(Extension):
    def __init__(self, name: str, sourcedir: str = "") -> None:
        super().__init__(name, sources=[])
        self.sourcedir = os.fspath(Path(sourcedir).resolve())


def get_cross_cmake_args():
    cmake_args = {}

    CIBW_ARCHS = os.environ.get("CIBW_ARCHS")
    if CIBW_ARCHS in {"arm64", "aarch64", "ARM64"}:
        ARCH = cmake_args["LLVM_TARGETS_TO_BUILD"] = "AArch64"
    elif CIBW_ARCHS in {"x86_64", "AMD64"}:
        ARCH = cmake_args["LLVM_TARGETS_TO_BUILD"] = "X86"
    elif CIBW_ARCHS in {"wasm32"}:
        cmake_args["LLVM_TARGETS_TO_BUILD"] = "WebAssembly"
        ARCH = "wasm32-wasi"
    else:
        raise ValueError(f"unknown CIBW_ARCHS={CIBW_ARCHS}")
    if CIBW_ARCHS != platform.machine():
        cmake_args["CMAKE_SYSTEM_NAME"] = platform.system()

    cmake_args["LLVM_TARGET_ARCH"] = ARCH

    if platform.system() == "Darwin":
        if ARCH == "AArch64":
            cmake_args["CMAKE_CROSSCOMPILING"] = "ON"
            cmake_args["CMAKE_OSX_ARCHITECTURES"] = "arm64"
            cmake_args["LLVM_HOST_TRIPLE"] = cmake_args[
                "LLVM_DEFAULT_TARGET_TRIPLE"
            ] = "arm64-apple-darwin21.6.0"
            # see llvm/cmake/modules/CrossCompile.cmake:llvm_create_cross_target
            cmake_args[
                "CROSS_TOOLCHAIN_FLAGS_NATIVE:STRING"
            ] = "-DCMAKE_C_COMPILER=clang;-DCMAKE_CXX_COMPILER=clang++"
    elif platform.system() == "Linux":
        if ARCH == "AArch64":
            cmake_args["CMAKE_CROSSCOMPILING"] = "ON"
            cmake_args["CMAKE_CXX_COMPILER"] = "aarch64-linux-gnu-g++"
            cmake_args["CMAKE_CXX_FLAGS"] = "-static-libgcc -static-libstdc++"
            cmake_args["CMAKE_C_COMPILER"] = "aarch64-linux-gnu-gcc"
            cmake_args[
                "CROSS_TOOLCHAIN_FLAGS_NATIVE:STRING"
            ] = "-DCMAKE_C_COMPILER=gcc;-DCMAKE_CXX_COMPILER=g++"
            cmake_args["LLVM_HOST_TRIPLE"] = cmake_args[
                "LLVM_DEFAULT_TARGET_TRIPLE"
            ] = "aarch64-linux-gnu"
        elif ARCH == "wasm32-wasi":
            cmake_args["CMAKE_CROSSCOMPILING"] = "ON"
            cmake_args[
                "CMAKE_EXE_LINKER_FLAGS"
            ] = "-sSTANDALONE_WASM=1 -sWASM=1 -sWASM_BIGINT=1"
            cmake_args["CMAKE_SYSTEM_NAME"] = "Emscripten"
            cmake_args["CMAKE_TOOLCHAIN_FILE"] = os.getenv("CMAKE_TOOLCHAIN_FILE")
            cmake_args[
                "CROSS_TOOLCHAIN_FLAGS_NATIVE:STRING"
            ] = "-DCMAKE_C_COMPILER=gcc;-DCMAKE_CXX_COMPILER=g++"
            cmake_args["LLVM_BUILD_DOCS"] = "OFF"
            cmake_args["LLVM_BUILD_TOOLS"] = "OFF"
            cmake_args["LLVM_HOST_TRIPLE"] = cmake_args[
                "LLVM_DEFAULT_TARGET_TRIPLE"
            ] = "wasm32-wasi"
            cmake_args["LLVM_ENABLE_BACKTRACES"] = "OFF"
            cmake_args["LLVM_ENABLE_BINDINGS"] = "OFF"
            cmake_args["LLVM_ENABLE_CRASH_OVERRIDES"] = "OFF"
            cmake_args["LLVM_ENABLE_LIBEDIT"] = "OFF"
            cmake_args["LLVM_ENABLE_LIBPFM"] = "OFF"
            cmake_args["LLVM_ENABLE_LIBXML2"] = "OFF"
            cmake_args["LLVM_ENABLE_OCAMLDOC"] = "OFF"
            cmake_args["LLVM_ENABLE_PIC"] = "OFF"
            cmake_args["LLVM_ENABLE_TERMINFO"] = "OFF"
            cmake_args["LLVM_ENABLE_THREADS"] = "OFF"
            cmake_args["LLVM_ENABLE_UNWIND_TABLES"] = "OFF"
            cmake_args["LLVM_ENABLE_ZLIB"] = "OFF"
            cmake_args["LLVM_ENABLE_ZSTD"] = "OFF"
            cmake_args["LLVM_HAVE_LIBXAR"] = "OFF"
            cmake_args["LLVM_INCLUDE_BENCHMARKS"] = "OFF"
            cmake_args["LLVM_INCLUDE_EXAMPLES"] = "OFF"
            cmake_args["LLVM_INCLUDE_TESTS"] = "OFF"
            cmake_args["LLVM_INCLUDE_UTILS"] = "OFF"
            cmake_args["LLVM_TARGETS_TO_BUILD"] = "WebAssembly"

    if BUILD_CUDA:
        cmake_args["LLVM_TARGETS_TO_BUILD"] += ";NVPTX"

    return cmake_args


class MyInstallData(install_data):
    def run(self):
        self.mkpath(self.install_dir)
        for f in self.data_files:
            print(f)

        print(type(self.distribution.data_files))
        for f in self.distribution.data_files:
            print(f)


class CMakeBuild(build_ext):
    def build_extension(self, ext: CMakeExtension) -> None:
        ext_fullpath = Path.cwd() / self.get_ext_fullpath(ext.name)
        extdir = ext_fullpath.parent.resolve()
        install_dir = extdir / "mlir"
        cfg = "Release"

        cmake_generator = os.environ.get("CMAKE_GENERATOR", "Ninja")

        RUN_TESTS = 1 if check_env("RUN_TESTS") else 0
        # make windows happy
        PYTHON_EXECUTABLE = str(Path(sys.executable))
        if platform.system() == "Windows":
            PYTHON_EXECUTABLE = PYTHON_EXECUTABLE.replace("\\", "\\\\")

        cmake_args = [
            f"-B{build_temp}",
            f"-G {cmake_generator}",
            "-DBUILD_SHARED_LIBS=OFF",
            "-DLLVM_BUILD_BENCHMARKS=OFF",
            "-DLLVM_BUILD_EXAMPLES=OFF",
            "-DLLVM_BUILD_RUNTIMES=OFF",
            f"-DLLVM_BUILD_TESTS={RUN_TESTS}",
            "-DLLVM_BUILD_TOOLS=ON",
            "-DLLVM_BUILD_UTILS=ON",
            "-DLLVM_CCACHE_BUILD=ON",
            "-DLLVM_ENABLE_ASSERTIONS=ON",
            "-DLLVM_ENABLE_RTTI=ON",
            "-DLLVM_ENABLE_ZSTD=OFF",
            "-DLLVM_INCLUDE_BENCHMARKS=OFF",
            "-DLLVM_INCLUDE_EXAMPLES=OFF",
            "-DLLVM_INCLUDE_RUNTIMES=OFF",
            f"-DLLVM_INCLUDE_TESTS={RUN_TESTS}",
            "-DLLVM_INCLUDE_TOOLS=ON",
            "-DLLVM_INCLUDE_UTILS=ON",
            "-DLLVM_INSTALL_UTILS=ON",
            "-DLLVM_ENABLE_WARNINGS=ON",
            "-DMLIR_BUILD_MLIR_C_DYLIB=1",
            "-DMLIR_ENABLE_EXECUTION_ENGINE=ON",
            "-DMLIR_ENABLE_SPIRV_CPU_RUNNER=ON",
            f"-DMLIR_INCLUDE_INTEGRATION_TESTS={RUN_TESTS}",
            f"-DMLIR_INCLUDE_TESTS={RUN_TESTS}",
            # get rid of that annoying af git on the end of .17git
            "-DLLVM_VERSION_SUFFIX=",
            # Disables generation of "version soname" (i.e. libFoo.so.<version>), which
            # causes pure duplication of various shlibs for Python wheels.
            "-DCMAKE_PLATFORM_NO_VERSIONED_SONAME=ON",
            f"-DCMAKE_INSTALL_PREFIX={install_dir}",
            f"-DCMAKE_LIBRARY_OUTPUT_DIRECTORY={extdir}{os.sep}",
            f"-DPython3_EXECUTABLE={PYTHON_EXECUTABLE}",
            f"-DCMAKE_BUILD_TYPE={cfg}",  # not used on MSVC, but no harm
            # prevent symbol collision that leads to multiple pass registration and such
            "-DCMAKE_VISIBILITY_INLINES_HIDDEN=ON",
            "-DCMAKE_C_VISIBILITY_PRESET=hidden",
            "-DCMAKE_CXX_VISIBILITY_PRESET=hidden",
        ]
        if platform.system() == "Windows":
            cmake_args += [
                "-DCMAKE_C_COMPILER=cl",
                "-DCMAKE_CXX_COMPILER=cl",
                "-DCMAKE_MSVC_RUNTIME_LIBRARY=MultiThreaded",
                "-DCMAKE_C_FLAGS=/MT",
                "-DCMAKE_CXX_FLAGS=/MT",
                "-DLLVM_USE_CRT_MINSIZEREL=MT",
                "-DLLVM_USE_CRT_RELEASE=MT",
            ]

        cmake_args_dict = get_cross_cmake_args()
        cmake_args += [f"-D{k}={v}" for k, v in cmake_args_dict.items()]
        if "WebAssembly" not in cmake_args_dict["LLVM_TARGETS_TO_BUILD"]:
            cmake_args += ["-DMLIR_ENABLE_BINDINGS_PYTHON=ON"]

        LLVM_ENABLE_PROJECTS = "llvm;mlir"

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

        if BUILD_OPENMP:
            cmake_args += [
                "-DENABLE_CHECK_TARGETS=OFF",
                "-DLIBOMP_OMPD_GDB_SUPPORT=OFF",
                "-DLIBOMP_USE_QUAD_PRECISION=False",
                "-DOPENMP_ENABLE_LIBOMPTARGET=OFF",
            ]
            LLVM_ENABLE_PROJECTS += ";openmp"

        cmake_args += [f"-DLLVM_ENABLE_PROJECTS={LLVM_ENABLE_PROJECTS}"]

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
            macosx_deployment_target = os.getenv("MACOSX_DEPLOYMENT_TARGET", "11.6")
            cmake_args += [f"-DCMAKE_OSX_DEPLOYMENT_TARGET={macosx_deployment_target}"]
            # Cross-compile support for macOS - respect ARCHFLAGS if set
            archs = re.findall(r"-arch (\S+)", os.environ.get("ARCHFLAGS", ""))
            if archs:
                cmake_args += ["-DCMAKE_OSX_ARCHITECTURES={}".format(";".join(archs))]

        if "PARALLEL_LEVEL" not in os.environ:
            build_args += [f"-j{str(2 * os.cpu_count())}"]
        else:
            build_args += [f"-j{os.environ.get('PARALLEL_LEVEL')}"]

        print("ENV", pprint(os.environ), file=sys.stderr)
        print("CMAKE_ARGS", cmake_args, file=sys.stderr)

        subprocess.run(
            ["cmake", ext.sourcedir, *cmake_args], cwd=build_temp, check=True
        )
        if check_env("DEBUG_CI_FAST_BUILD"):
            subprocess.run(
                ["cmake", "--build", ".", "--target", "llvm-tblgen", *build_args],
                cwd=build_temp,
                check=True,
            )
            shutil.rmtree(install_dir / "bin", ignore_errors=True)
            shutil.copytree(build_temp / "bin", install_dir / "bin")
        else:
            subprocess.run(
                ["cmake", "--build", ".", "--target", "install", *build_args],
                cwd=build_temp,
                check=True,
            )
            if RUN_TESTS:
                env = os.environ.copy()
                # PYTHONPATH needs to be set to find build deps like numpy
                # https://github.com/llvm/llvm-project/pull/89296
                env["MLIR_LIT_PYTHONPATH"] = os.pathsep.join(sys.path)
                subprocess.run(
                    ["cmake", "--build", ".", "--target", "check-all", *build_args],
                    cwd=build_temp,
                    env=env,
                    check=False,
                )
            shutil.rmtree(install_dir / "python_packages", ignore_errors=True)

        subprocess.run(
            [
                "find",
                ".",
                "-exec",
                "touch",
                "-a",
                "-m",
                "-t",
                "197001010000",
                "{}",
                ";",
            ],
            cwd=install_dir,
            check=False,
        )


def check_env(build):
    return os.environ.get(build, 0) in {"1", "true", "True", "ON", "YES"}


cmake_txt = open("llvm-project/cmake/Modules/LLVMVersion.cmake").read()
llvm_version = []
for v in ["LLVM_VERSION_MAJOR", "LLVM_VERSION_MINOR", "LLVM_VERSION_PATCH"]:
    vn = re.findall(rf"set\({v} (\d+)\)", cmake_txt)
    assert vn, f"couldn't find {v} in cmake txt"
    llvm_version.append(vn[0])

commit_hash = os.environ.get("LLVM_PROJECT_COMMIT", "DEADBEEF")

now = datetime.now()
llvm_datetime = os.environ.get(
    "DATETIME", f"{now.year}{now.month:02}{now.day:02}{now.hour:02}"
)

version = f"{llvm_version[0]}.{llvm_version[1]}.{llvm_version[2]}.{llvm_datetime}+"

local_version = []
BUILD_CUDA = check_env("BUILD_CUDA")
if BUILD_CUDA:
    local_version += ["cuda"]
BUILD_VULKAN = check_env("BUILD_VULKAN")
if BUILD_VULKAN:
    local_version += ["vulkan"]
BUILD_OPENMP = check_env("BUILD_OPENMP")
if BUILD_OPENMP:
    local_version += ["openmp"]
if local_version:
    version += ".".join(local_version + [commit_hash])
else:
    version += commit_hash

if len(sys.argv) > 1 and sys.argv[1] == "--mlir-version":
    print(version)
    exit()

llvm_url = f"https://github.com/llvm/llvm-project/commit/{commit_hash}"

build_temp = Path.cwd() / "build" / "temp"
if not build_temp.exists():
    build_temp.mkdir(parents=True)

EXE_EXT = ".exe" if platform.system() == "Windows" else ""
if not check_env("DEBUG_CI_FAST_BUILD"):
    exes = [
        "mlir-cpu-runner",
        "mlir-opt",
        "mlir-translate",
    ]
else:
    exes = ["llvm-tblgen"]

data_files = [("bin", [str(build_temp / "bin" / x) + EXE_EXT for x in exes])]

setup(
    name="mlir",
    version=version,
    author="Maksim Levental",
    author_email="maksim.levental@gmail.com",
    description=f"MLIR distribution as wheel. Created at {now} build of {llvm_url}",
    long_description=f"MLIR distribution as wheel. Created at {now} build of [llvm/llvm-project/{commit_hash}]({llvm_url})",
    long_description_content_type="text/markdown",
    ext_modules=[CMakeExtension("mlir", sourcedir="llvm-project/llvm")],
    cmdclass={"build_ext": CMakeBuild},
    zip_safe=False,
    download_url=llvm_url,
    data_files=data_files,
)
