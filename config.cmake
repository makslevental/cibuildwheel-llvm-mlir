include(CMakePrintHelpers)

set(LLVM_ENABLE_PROJECTS "llvm;mlir;clang;clang-tools-extra;lld" CACHE STRING "")

option(RUN_TESTS "" OFF)
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

# prevent symbol collision that leads to multiple pass registration and such
set(CMAKE_VISIBILITY_INLINES_HIDDEN ON CACHE STRING "")
set(CMAKE_C_VISIBILITY_PRESET hidden CACHE STRING "")
set(CMAKE_CXX_VISIBILITY_PRESET hidden CACHE STRING "")

if(WIN32)
  set(CMAKE_MSVC_RUNTIME_LIBRARY MultiThreaded CACHE STRING "")
  set(CMAKE_C_COMPILER cl CACHE STRING "")
  set(CMAKE_CXX_COMPILER cl CACHE STRING "")
  set(CMAKE_C_FLAGS "${CMAKE_C_FLAGS} /MT")
  set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} /MT")
  set(LLVM_USE_CRT_MINSIZEREL MT CACHE STRING "")
  set(LLVM_USE_CRT_RELEASE MT CACHE STRING "")
endif()

option(BUILD_CUDA "" OFF)
if(BUILD_CUDA)
  set(MLIR_ENABLE_CUDA_RUNNER ON CACHE BOOL "")
  set(MLIR_ENABLE_CUDA_CONVERSIONS ON CACHE BOOL "")
  set(CMAKE_CUDA_COMPILER /usr/local/cuda/bin/nvcc CACHE STRING "")
  set(CUDAToolkit_ROOT /usr/local/cuda CACHE STRING "")
endif()

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

option(BUILD_OPENMP "" OFF)
if(BUILD_OPENMP)
  list(APPEND LLVM_ENABLE_PROJECTS openmp)
  set(ENABLE_CHECK_TARGETS OFF CACHE BOOL "")
  set(LIBOMP_OMPD_GDB_SUPPORT OFF CACHE BOOL "")
  set(LIBOMP_USE_QUAD_PRECISION False CACHE BOOL "")
  set(OPENMP_ENABLE_LIBOMPTARGET OFF CACHE BOOL "")
endif()

# iree compat
set(LLVM_ENABLE_RUNTIMES "compiler-rt" CACHE STRING "")
set(CLANG_DEFAULT_OBJCOPY llvm-objcopy CACHE STRING "")
set(CLANG_DEFAULT_LINKER lld CACHE STRING "")
set(CLANG_ENABLE_STATIC_ANALYZER ON CACHE BOOL "")
set(LLVM_ENABLE_LIBCXX OFF CACHE BOOL "")
set(LLVM_ENABLE_ZLIB ON CACHE BOOL "")
if(NOT WIN32)
  set(LLVM_BUILD_LLVM_DYLIB ON CACHE BOOL "")
  set(LLVM_LINK_LLVM_DYLIB ON CACHE BOOL "")
endif()
set(LLVM_ENABLE_UNWIND_TABLES OFF CACHE BOOL "")
set(CLANG_ENABLE_ARCMT OFF CACHE BOOL "")
set(CLANG_PLUGIN_SUPPORT OFF CACHE BOOL "")
set(LLVM_ENABLE_TERMINFO OFF CACHE BOOL "")
set(LLVM_ENABLE_Z3_SOLVER OFF CACHE BOOL "")
set(LLVM_INCLUDE_DOCS OFF CACHE BOOL "")
set(LLVM_INCLUDE_GO_TESTS OFF CACHE BOOL "")

get_cmake_property(_variableNames VARIABLES)
list (SORT _variableNames)
cmake_print_variables(${_variableNames})