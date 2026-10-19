#!/bin/sh
set -eu
cd "$(dirname "$0")/.."
export CLANG_MODULE_CACHE_PATH="$PWD/.build/clang-cache"
swift build -c release --disable-sandbox --cache-path "$PWD/.build/cache"
APP="$PWD/dist/Second Brain.app"
mkdir -p "$APP/Contents/MacOS"
cp .build/release/SecondBrain "$APP/Contents/MacOS/SecondBrain"
cat > "$APP/Contents/Info.plist" <<'PLIST'
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict>
<key>CFBundleIdentifier</key><string>local.secondbrain.app</string>
<key>CFBundleName</key><string>Second Brain</string>
<key>CFBundleExecutable</key><string>SecondBrain</string>
<key>CFBundlePackageType</key><string>APPL</string>
<key>CFBundleShortVersionString</key><string>0.1.0</string>
<key>CFBundleVersion</key><string>1</string>
<key>LSMinimumSystemVersion</key><string>14.0</string>
<key>NSHighResolutionCapable</key><true/>
</dict></plist>
PLIST
python3 - "$APP/Contents/Info.plist" "$PWD" <<'PYPLIST'
import plistlib,sys
path=sys.argv[1]
with open(path,'rb') as f: data=plistlib.load(f)
data['SecondBrainProjectRoot']=sys.argv[2]
data['CFBundleShortVersionString']='0.3.0'
with open(path,'wb') as f: plistlib.dump(data,f)
PYPLIST
if [ -z "${SECOND_BRAIN_SIGNING_IDENTITY:-}" ]; then
  printf 'Warning: ad-hoc signing; macOS capture permission may need renewal. See docs/signing.md.\n' >&2
fi
codesign --force --sign "${SECOND_BRAIN_SIGNING_IDENTITY:--}" "$APP"
printf 'Built %s\n' "$APP"
