#!/usr/bin/env bash
set -xe

export PIP_FIND_LINKS="wheelhouse https://github.com/makslevental/mlir-wheels/releases/expanded_assets/latest"

SITE_PACKAGES=$(python -c "import site; print(site.getsitepackages()[0])")

pip cache purge

if [ ! -z "$MLIR_WHEEL_VERSION" ]; then
  pip install mlir-native-tools==$MLIR_WHEEL_VERSION --force -U

  DATE=$(echo $MLIR_WHEEL_VERSION | cut -d "+" -f 1)
  HASH=$(echo $MLIR_WHEEL_VERSION | cut -d "+" -f 2)
  LOCAL_VERSION=""
  if [ x"$BUILD_CUDA" == x"true" ]; then
    LOCAL_VERSION="$LOCAL_VERSION cuda"
  fi
  LOCAL_VERSION="$LOCAL_VERSION $HASH"
  LOCAL_VERSION=$(echo $LOCAL_VERSION | tr ' ' '.')
  MLIR_WHEEL_VERSION="==$DATE+$LOCAL_VERSION"
else
  pip install mlir-native-tools --force -U
fi

if [ x"$CIBW_ARCHS" == x"arm64" ] || [ x"$CIBW_ARCHS" == x"aarch64" ]; then
  if [ x"$MATRIX_OS" == x"macos-13" ] || [ x"$MATRIX_OS" == x"macos-13" ]; then
    PLAT=macosx_12_0_arm64
  elif [ x"$MATRIX_OS" == x"ubuntu-20.04" ]; then
    PLAT=linux_aarch64
  fi
  pip install mlir$MLIR_WHEEL_VERSION --platform $PLAT --only-binary=:all: --target $SITE_PACKAGES --no-deps --force -U
else
  pip install mlir$MLIR_WHEEL_VERSION --force -U
fi
