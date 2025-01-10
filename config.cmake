include(CMakePrintHelpers)

set(LLVM_ENABLE_PROJECTS "llvm;mlir;clang;lld" CACHE STRING "")

set(CMAKE_POLICY_DEFAULT_CMP0175 OLD CACHE STRING "")

option(RUN_TESTS "" OFF)
set(LLVM_INCLUDE_TESTS ${RUN_TESTS} CACHE BOOL "")
set(LLVM_BUILD_TESTS ${RUN_TESTS} CACHE BOOL "")
set(LLVM_INCLUDE_TESTS ${RUN_TESTS} CACHE BOOL "")
set(MLIR_INCLUDE_INTEGRATION_TESTS ${RUN_TESTS} CACHE BOOL "")
set(MLIR_INCLUDE_TESTS ${RUN_TESTS} CACHE BOOL "")

set(BUILD_SHARED_LIBS OFF CACHE BOOL "")
set(LLVM_BUILD_BENCHMARKS OFF CACHE BOOL "")
set(LLVM_BUILD_EXAMPLES OFF CACHE BOOL "")

set(LLVM_BUILD_TOOLS ON CACHE BOOL "")
set(LLVM_BUILD_UTILS ON CACHE BOOL "")
set(LLVM_CCACHE_BUILD ON CACHE BOOL "")
set(LLVM_ENABLE_ASSERTIONS ON CACHE BOOL "")
set(LLVM_ENABLE_RTTI ON CACHE BOOL "")
set(LLVM_ENABLE_ZSTD OFF CACHE BOOL "")
set(LLVM_INCLUDE_BENCHMARKS OFF CACHE BOOL "")
set(LLVM_INCLUDE_EXAMPLES OFF CACHE BOOL "")

set(LLVM_INCLUDE_TOOLS ON CACHE BOOL "")
set(LLVM_INCLUDE_UTILS ON CACHE BOOL "")
set(LLVM_INSTALL_UTILS ON CACHE BOOL "")
set(LLVM_ENABLE_WARNINGS ON CACHE BOOL "")
set(MLIR_BUILD_MLIR_C_DYLIB ON CACHE BOOL "")
set(MLIR_ENABLE_BINDINGS_PYTHON ON CACHE BOOL "")
set(MLIR_ENABLE_EXECUTION_ENGINE ON CACHE BOOL "")
set(MLIR_ENABLE_SPIRV_CPU_RUNNER ON CACHE BOOL "")

# get rid of that annoying af git on the end of .17git
set(LLVM_VERSION_SUFFIX "" CACHE STRING "")
# Disables generation of "version soname" (i.e. libFoo.so.<version>),
# which causes pure duplication of various shlibs for Python wheels.
set(CMAKE_PLATFORM_NO_VERSIONED_SONAME ON CACHE BOOL "")

if(WIN32)
  set(CMAKE_MSVC_RUNTIME_LIBRARY MultiThreaded CACHE STRING "")
  set(CMAKE_C_COMPILER cl CACHE STRING "")
  set(CMAKE_CXX_COMPILER cl CACHE STRING "")
  list(APPEND CMAKE_C_FLAGS "/MT")
  list(APPEND CMAKE_CXX_FLAGS "/MT")
  set(LLVM_USE_CRT_MINSIZEREL MT CACHE STRING "")
  set(LLVM_USE_CRT_RELEASE MT CACHE STRING "")
endif()

set(CIBW_ARCHS "x86_64" CACHE STRING "")
if(CIBW_ARCHS MATCHES "AArch64|arm64|aarch64|ARM64")
  set(ARCH "AArch64" CACHE STRING "")
elseif(CIBW_ARCHS MATCHES "X86|x86_64|AMD64")
  set(ARCH "X86" CACHE STRING "")
else()
  message(FATAL_ERROR "Unrecognized CIBW_ARCHS=${CIBW_ARCHS}")
endif()

set(LLVM_TARGET_ARCH ${ARCH} CACHE STRING "")
set(_llvm_targets_to_build ${ARCH})

# probably i'm doing this wrong and i should be reading CMAKE_HOST_SYSTEM_PROCESSOR
if(ARCH STREQUAL "AArch64")
  set(CMAKE_CROSSCOMPILING ON CACHE BOOL "")
  if(CMAKE_SYSTEM_NAME STREQUAL "Darwin")
    set(CMAKE_OSX_ARCHITECTURES "arm64" CACHE STRING "")
    set(LLVM_HOST_TRIPLE "arm64-apple-darwin21.6.0" CACHE STRING "")
    set(LLVM_DEFAULT_TARGET_TRIPLE "arm64-apple-darwin21.6.0" CACHE STRING "")
    # see llvm/cmake/modules/CrossCompile.cmake:llvm_create_cross_target
    set(CROSS_TOOLCHAIN_FLAGS_NATIVE "-DCMAKE_C_COMPILER=clang;-DCMAKE_CXX_COMPILER=clang++" CACHE STRING "")
  elseif(CMAKE_SYSTEM_NAME STREQUAL "Linux")
    set(LLVM_HOST_TRIPLE "aarch64-linux-gnu" CACHE STRING "")
    set(LLVM_DEFAULT_TARGET_TRIPLE "aarch64-linux-gnu" CACHE STRING "")
    # see llvm/cmake/modules/CrossCompile.cmake:llvm_create_cross_target
    set(CROSS_TOOLCHAIN_FLAGS_NATIVE "-DCMAKE_C_COMPILER=gcc;-DCMAKE_CXX_COMPILER=g++" CACHE STRING "")
    # obv this presume this toolchain (i.e. sudo apt-get install -y binutils-aarch64-linux-gnu g++-aarch64-linux-gnu
    # gcc-aarch64-linux-gnu)
    set(CMAKE_CXX_COMPILER "aarch64-linux-gnu-g++" CACHE STRING "")
    set(CMAKE_C_COMPILER "aarch64-linux-gnu-gcc" CACHE STRING "")
    list(APPEND CMAKE_CXX_FLAGS "-static-libgcc" "-static-libstdc++")
  endif()
endif()

option(BUILD_CUDA "" OFF)
if(BUILD_CUDA)
  set(MLIR_ENABLE_CUDA_RUNNER ON CACHE BOOL "")
  set(MLIR_ENABLE_CUDA_CONVERSIONS ON CACHE BOOL "")
  set(CMAKE_CUDA_COMPILER /usr/local/cuda/bin/nvcc CACHE STRING "")
  set(CUDAToolkit_ROOT /usr/local/cuda CACHE STRING "")
  set(_cuda_lib_paths
      /usr/local/cuda/lib64/lib/x86_64-linux-gnu /usr/local/cuda/lib64/lib/x64 /usr/local/cuda/lib64/lib64
      /usr/local/cuda/lib64/lib /usr/local/cuda/lib64/lib64/stubs /usr/local/cuda/lib64/lib/stubs /usr/local/cuda/lib64)
  set(CMAKE_LIBRARY_PATH ${_cuda_lib_paths} CACHE STRING "")
  list(APPEND _llvm_targets_to_build NVPTX)
endif()

option(BUILD_AMDGPU "" OFF)
if(BUILD_AMDGPU)
  list(APPEND _llvm_targets_to_build AMDGPU)
endif()

# for some reason if you set a CACHE var twice it actually creates two of them
# and they're not _both_ respected (llvm wasn't building NVPTX...)
set(LLVM_TARGETS_TO_BUILD ${_llvm_targets_to_build} CACHE STRING "")

option(BUILD_VULKAN "" OFF)
if(BUILD_VULKAN)
  set(MLIR_ENABLE_VULKAN_RUNNER ON CACHE BOOL "")
  if(${CMAKE_SYSTEM_NAME} MATCHES "Darwin")
    set(vulkan_library /usr/local/lib/libvulkan.dylib)
  elseif(${CMAKE_SYSTEM_NAME} MATCHES "Linux")
    set(vulkan_library /usr/local/lib64/libvulkan.so)
  else()
    message(FATAL_ERROR "${CMAKE_SYSTEM_NAME} not supported with BUILD_VULKAN")
  endif()
  set(Vulkan_LIBRARY ${vulkan_library} CACHE STRING "")
endif()

# iree compat
# currently this fails under cross-compile (surface symptom is lack of __bf16 on mac arm cross)
# eventually figure this out https://llvm.org/docs/HowToCrossCompileBuiltinsOnArm.html
# and thus restore access to sanitizers
#set(LLVM_ENABLE_RUNTIMES "compiler-rt" CACHE STRING "")
set(CLANG_DEFAULT_OBJCOPY llvm-objcopy CACHE STRING "")
set(CLANG_DEFAULT_LINKER lld CACHE STRING "")
set(CLANG_ENABLE_STATIC_ANALYZER ON CACHE BOOL "")
set(LLVM_ENABLE_LIBEDIT OFF CACHE BOOL "")
set(LLVM_ENABLE_LIBXML2 OFF CACHE BOOL "")
set(LLVM_ENABLE_LIBCXX OFF CACHE BOOL "")
set(LLVM_ENABLE_ZLIB OFF CACHE BOOL "")
set(LLVM_ENABLE_ZSTD OFF CACHE BOOL "")
set(LLVM_FORCE_ENABLE_STATS ON CACHE BOOL "")

set(LLVM_BUILD_LLVM_DYLIB ON CACHE BOOL "")
# All the tools will use libllvm shared library
# (but doesn't work on windows)
if (NOT WIN32)
  set(LLVM_LINK_LLVM_DYLIB ON CACHE BOOL "")
  set(MLIR_LINK_MLIR_DYLIB ON CACHE BOOL "")
endif()

set(LLVM_ENABLE_UNWIND_TABLES OFF CACHE BOOL "")
set(CLANG_ENABLE_ARCMT OFF CACHE BOOL "")
set(CLANG_PLUGIN_SUPPORT OFF CACHE BOOL "")
set(LLVM_ENABLE_TERMINFO OFF CACHE BOOL "")
set(LLVM_ENABLE_Z3_SOLVER OFF CACHE BOOL "")
set(LLVM_INCLUDE_DOCS OFF CACHE BOOL "")
set(LLVM_INCLUDE_GO_TESTS OFF CACHE BOOL "")

# malloc(): corrupted top size
# LLVM_ENABLE_ASSERTIONS=ON makes [NDEBUG un-defined](https://github.com/shark-infra/llvm-project/blob/32b91ec395529ef7ad8b5520fe692464f7512b41/llvm/cmake/modules/HandleLLVMOptions.cmake#L121)
# In IREE that would require [IREE_ENABLE_ASSERTIONS=ON](https://github.com/iree-org/iree/blob/3d6a8ee260be3f32614aa18207d5a35c81f86401/CMakeLists.txt#L516)
#
# Because of https://github.com/iree-org/iree/blob/112fad0047bdaa6595387afd9791f3027913d56b/compiler/src/iree/compiler/Dialect/Util/Transforms/FoldGlobals.cpp#L523-L526
# and https://github.com/shark-infra/llvm-project/blob/9144e4933463d35df259ca8a5207119e1fc0c97c/llvm/include/llvm/ADT/Statistic.h#L38
# just set LLVM_FORCE_ENABLE_STATS and eat the cost for the sake of simplicity
set(LLVM_FORCE_ENABLE_STATS ON CACHE BOOL "")

get_cmake_property(_variableNames VARIABLES)
list(SORT _variableNames)
cmake_print_variables(${_variableNames})
