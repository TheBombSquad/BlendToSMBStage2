#!/bin/bash
set -e

# Script for building/packaging BlendToSMBStage2 on Linux.
#
# Was tested on Arch Linux, may need adjustments for other distros
# Was originally based on a GitHub Actions CI script for building
# Managing Workshop 2's dependencies was a nightmare, so no automated
# Linux builds for now.
#
# Dependencies required:
#
# In general:
# cmake dotnet-sdk mono mono-msbuild
#
# For building Workshop 2:
# qtbase5-dev qttools5-dev libglew-dev libglm-dev libassimp-dev libbullet-dev ninja-build
#

git submodule update --init --recursive

# BUILD WORKSHOP 2
cd ./smblevelworkshop2
echo "Building SMB Level Workshop 2 in directory" $PWD
echo "-------------------------------------------------------------------------------------"

# Set up WS2 environment
mkdir -v build || true

# Run CMake
cmake -G "Ninja" -DCMAKE_BUILD_TYPE="Debug" -DCMAKE_INSTALL_PREFIX=./build/install -S . -B ./build

# Make and install the project
ninja -C ./build -j $(nproc) ws2common/install ws2lz/install ws2lzfrontend/install

# Install prerequisite libraries
ninja -C ./build installprerequisites
        
# Compress artifacts
cd ./build/install
tar -czf ../SMBLevelWorkshop2-Linux.tar.gz .
cd ../..
echo -e "-------------------------------------------------------------------------------------\\n"
      
# BUILD GXMODELVIEWER
cd ../GxUtils/GxUtils
echo "Building GXModelViewer in directory" $PWD
echo "-------------------------------------------------------------------------------------"
        
# Build the project
msbuild /M /P:Configuration='Release - Mono',DebugSymbols=false,DebugType=None,OutputPath=./out
      
# Collect artifacts
mkdir -v ./artifacts || true
mkdir -v ./artifacts/Presets || true
mkbundle -o ./artifacts/GxModelViewer --simple ./GxModelViewer/out/GxModelViewer.exe -L ./GxModelViewer/out/ --no-machine-config --no-config
cp ../CHANGES.txt ./artifacts
cp ../COPYING.txt ./artifacts
cp ../CREDITS.txt ./artifacts
cp ../MiscUtilLicense.txt ./artifacts
cp ../OpenTkLicense.txt ./artifacts
cp ../README.md ./artifacts
tar -C artifacts/ -czf ../GxUtils-Linux.tar.gz .
echo -e "-------------------------------------------------------------------------------------\\n"

# PACKAGE BLEND2SMBSTAGE2
cd ../..
echo "Packaging B2SMB2 in directory" $PWD
echo "-------------------------------------------------------------------------------------"

# Set up working directory for packaging
mkdir -v out || true
cd out

# Copy built ws2
mkdir ws2lzfrontend || true
tar -xvf ../smblevelworkshop2/build/SMBLevelWorkshop2-Linux.tar.gz -C ./ws2lzfrontend
rm -v ../smblevelworkshop2/build/SMBLevelWorkshop2-Linux.tar.gz

# Copy built gxutils
mkdir -v GxUtils || true
tar -xvf ../GxUtils/GxUtils-Linux.tar.gz -C ./GxUtils
rm -v ../GxUtils/GxUtils-Linux.tar.gz

# Copy BlendToSMBStage2
cp -rv $(find .. -maxdepth 1 -type f \( ! -name linux-build.sh ! -name ".*" \)) ../BlendToSMBStage2 .
mkdir BlendToSMBStage2-Out || true
mv $(ls --ignore=BlendToSMBStage2-Out .) BlendToSMBStage2-Out
mv BlendToSMBStage2-Out BlendToSMBStage2
rm BlendToSMBStage2-Linux.zip || true
7z a BlendToSMBStage2-Linux.zip ./BlendToSMBStage2

# Clean up
rm -rv BlendToSMBStage2

echo -e "-------------------------------------------------------------------------------------\\n"

echo "Successfully built B2SMB2 in directory" $PWD



