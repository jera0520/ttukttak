#!/usr/bin/env bash
# build.sh - build 뚝딱.app (executable Ttukttak) with swiftc only (no Xcode, xcodegen or actool needed).
#
#   scripts/build.sh [--debug] [--clean] [-h|--help]
#
#   --debug   swiftc -Onone -g instead of -O (much faster to compile, slower to run)
#   --clean   delete build/ first
#
# Result: build/뚝딱.app (ad-hoc signed). Run it with:  open -g -n build/뚝딱.app
# More (requirements, what the build changes, Coucou credits): README.md, NOTICE.md
set -euo pipefail

# ------------------------------------------------------------------ settings
APP_NAME=Ttukttak                   # executable and process name (ASCII: pkill -x, logs, folders)
DISPLAY_NAME=뚝딱                   # .app folder, CFBundleName/DisplayName, {APP} in the texts
BUNDLE_ID=kr.jinhyeon.ttukttak      # must differ from Coucou's fr.louisraille.NotchBuddy
VERSION=0.1.1                       # CFBundleShortVersionString
BUILD=2                             # CFBundleVersion
PET_NAME=복슬깨비                   # {PET} in the translation overlays; replaces "Mochi" in the catalog
# ---------------------------------------------------------------------------
MIN_MACOS=15.0
ARCH=arm64
SWIFT_MODULE=Ttukttak               # Swift module name

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BUILD_DIR="${TT_BUILD_DIR:-$ROOT/build}"      # override only for side-by-side test builds
I18N_DIR="${TT_I18N_DIR:-$ROOT/i18n}"         # <lang>.json overlays (ko.json ...)
APP="$BUILD_DIR/$DISPLAY_NAME.app"
CONTENTS="$APP/Contents"
LOG="$BUILD_DIR/swiftc.log"

usage() { sed -n '2,10p' "${BASH_SOURCE[0]}" | sed 's/^# \{0,1\}//'; }

OPT=release
CLEAN=0
for arg in "$@"; do
  case "$arg" in
    --debug) OPT=debug ;;
    --clean) CLEAN=1 ;;
    -h|--help) usage; exit 0 ;;
    *) echo "build.sh: unknown option: $arg" >&2; usage >&2; exit 2 ;;
  esac
done

say()  { printf '==> %s\n' "$*"; }
die()  { printf 'build.sh: error: %s\n' "$*" >&2; exit 1; }

for tool in swiftc plutil codesign python3 find xargs sed grep; do
  command -v "$tool" >/dev/null 2>&1 || die "'$tool' not found (needs the Xcode Command Line Tools: xcode-select --install)"
done
[ -x /usr/libexec/PlistBuddy ] || die "/usr/libexec/PlistBuddy not found"
[ -f "$ROOT/Resources/Info.plist" ] || die "$ROOT/Resources/Info.plist is missing"

if [ "$CLEAN" = 1 ]; then
  say "clean: removing $BUILD_DIR"
  rm -rf "$BUILD_DIR"
fi

# ------------------------------------------------- 1. generated assets (only the missing ones; the repo has them)
need_icons=0
for f in AppIcon.icns MenuBarIcon.png "MenuBarIcon@2x.png"; do
  [ -f "$ROOT/Resources/$f" ] || need_icons=1
done
need_sounds=0
sound_names="$(sed -n '/static let soundNames/,/\]/p' "$ROOT/Sources/App/SoundEngine.swift" | grep -o '"[A-Za-z]*"' | tr -d '"')"
[ -n "$sound_names" ] || die "could not read the sound names from Sources/App/SoundEngine.swift"
for n in $sound_names; do
  [ -f "$ROOT/Resources/sounds/$n.wav" ] || need_sounds=1
done
if [ "$need_sounds" = 1 ]; then
  say "generating sound effects (scripts/make_sounds.py, needs numpy)"
  python3 "$ROOT/scripts/make_sounds.py" --only-missing | tail -1
fi
if [ "$need_icons" = 1 ]; then
  say "generating icons (scripts/make_icons.py, needs Pillow)"
  python3 "$ROOT/scripts/make_icons.py" --only-missing
fi

# ------------------------------------------------- 2. bundle skeleton
mkdir -p "$BUILD_DIR"
rm -rf "$APP"
mkdir -p "$CONTENTS/MacOS" "$CONTENTS/Resources"

# ------------------------------------------------- 3. compile
if [ "$OPT" = debug ]; then OPT_FLAGS=(-Onone -g); else OPT_FLAGS=(-O); fi
file_count="$(cd "$ROOT" && find Sources -name '*.swift' | wc -l | tr -d ' ')"
[ "$file_count" -gt 0 ] || die "no .swift files under $ROOT/Sources"
say "compiling $file_count Swift files (${OPT_FLAGS[*]}, $ARCH, macOS $MIN_MACOS) - log: $LOG"
[ "$OPT" = debug ] || say "   -O takes several minutes (one big file dominates); '--debug' compiles much faster"
t0=$SECONDS
# swiftc and the linker keep their .o files in $TMPDIR. A long (or slow, on a busy machine) build must not lose
# them to somebody else cleaning the global temp folder (that happened once: "clang: no such file ... -1.o"),
# so they get a private folder inside the build directory.
TMP_BUILD="$BUILD_DIR/tmp"
rm -rf "$TMP_BUILD"; mkdir -p "$TMP_BUILD"
(
  cd "$ROOT"
  export TMPDIR="$TMP_BUILD/"
  find Sources -name '*.swift' -print0 |
    xargs -0 swiftc -swift-version 6 "${OPT_FLAGS[@]}" -target "$ARCH-apple-macos$MIN_MACOS" \
      -parse-as-library -module-name "$SWIFT_MODULE" -o "$CONTENTS/MacOS/$APP_NAME"
) >"$LOG" 2>&1 &
compile_pid=$!
beat=60
while kill -0 "$compile_pid" 2>/dev/null; do
  sleep 2
  if [ $((SECONDS - t0)) -ge "$beat" ]; then
    printf '    ... still compiling (%ds)\n' $((SECONDS - t0))
    beat=$((beat + 60))
  fi
done
if wait "$compile_pid"; then
  rm -rf "$TMP_BUILD"
  warnings="$(grep -c 'warning:' "$LOG" || true)"
  say "swiftc OK in $((SECONDS - t0))s ($warnings warnings, see log)"
else
  echo "---- compiler errors ----" >&2
  if grep -q 'error:' "$LOG"; then
    grep -E -A6 'error:' "$LOG" | head -80 >&2
  else
    tail -40 "$LOG" >&2
  fi
  die "swiftc failed after $((SECONDS - t0))s - full log: $LOG"
fi
[ -x "$CONTENTS/MacOS/$APP_NAME" ] || die "swiftc did not produce $CONTENTS/MacOS/$APP_NAME"

# ------------------------------------------------- 4. Info.plist (Xcode build variables filled in)
say "Info.plist"
PLIST="$CONTENTS/Info.plist"
sedesc() { printf '%s' "$1" | sed -e 's/[\\&|]/\\&/g'; }
# the commit the build came from (shown in the voice log), "dev" outside a git checkout
GIT_HASH="$(git -C "$ROOT" rev-parse --short HEAD 2>/dev/null || echo dev)"
sed \
  -e "s|[\$](DEVELOPMENT_LANGUAGE)|en|g" \
  -e "s|[\$](EXECUTABLE_NAME)|$(sedesc "$APP_NAME")|g" \
  -e "s|[\$](PRODUCT_NAME)|$(sedesc "$DISPLAY_NAME")|g" \
  -e "s|[\$](PRODUCT_BUNDLE_IDENTIFIER)|$(sedesc "$BUNDLE_ID")|g" \
  -e "s|[\$](MARKETING_VERSION)|$(sedesc "$VERSION")|g" \
  -e "s|[\$](CURRENT_PROJECT_VERSION)|$(sedesc "$BUILD")|g" \
  -e "s|[\$](MACOSX_DEPLOYMENT_TARGET)|$(sedesc "$MIN_MACOS")|g" \
  -e "s|[\$](TTUKTTAK_GIT_HASH)|$(sedesc "$GIT_HASH")|g" \
  "$ROOT/Resources/Info.plist" >"$PLIST"
if grep -q '[$](' "$PLIST"; then
  grep -n '[$](' "$PLIST" >&2
  die "Info.plist still has unfilled \$(...) variables"
fi
plutil -lint "$PLIST" >/dev/null

# ------------------------------------------------- 5. translations: xcstrings -> <lang>.lproj
say "translations (scripts/xcstrings2strings.py, overlays from $I18N_DIR)"
LANGS="$(plutil -extract CFBundleLocalizations xml1 -o - "$ROOT/Resources/Info.plist" |
         sed -n 's|.*<string>\(.*\)</string>.*|\1|p' | tr '\n' ' ')"
[ -n "$LANGS" ] || die "no CFBundleLocalizations in Resources/Info.plist"
python3 "$ROOT/scripts/xcstrings2strings.py" \
  --xcstrings "$ROOT/Resources/Localizable.xcstrings" --out "$CONTENTS/Resources" \
  --i18n "$I18N_DIR" --app-name "$DISPLAY_NAME" --pet-name "$PET_NAME" --languages "$LANGS" \
  --rename "Coucou=$DISPLAY_NAME" --rename "Mochi=$PET_NAME" \
  --warn-regex 'nb-hook|NotchBuddy|[.]claude/coucou|plugins/coucou|hooks/coucou|coucou[.](js|ts|json)|nb[.]sock|Coucou|Mochi'
# a language that exists only as an overlay (ko) must be declared in the bundle too
for dir in "$CONTENTS/Resources"/*.lproj; do
  lang="$(basename "$dir" .lproj)"
  if ! /usr/libexec/PlistBuddy -c 'Print :CFBundleLocalizations' "$PLIST" | grep -q "^ *$lang\$"; then
    /usr/libexec/PlistBuddy -c "Add :CFBundleLocalizations: string $lang" "$PLIST"
    echo "  declared $lang in CFBundleLocalizations"
  fi
done
plutil -lint "$PLIST" >/dev/null

# ------------------------------------------------- 6. sounds, icons, licences
say "sounds, icons and licences"
cp -R "$ROOT/Resources/sounds" "$CONTENTS/Resources/sounds"
cp "$ROOT/Resources/AppIcon.icns" "$ROOT/Resources/MenuBarIcon.png" "$ROOT/Resources/MenuBarIcon@2x.png" "$CONTENTS/Resources/"
# MIT asks for its notice in every copy, the built app included
for f in LICENSE LICENSE-ASSETS LICENSE-Coucou.txt NOTICE.md; do
  [ -f "$ROOT/$f" ] || die "$ROOT/$f is missing"
  cp "$ROOT/$f" "$CONTENTS/Resources/"
done
printf 'APPL????' >"$CONTENTS/PkgInfo"

# ------------------------------------------------- 7. ad-hoc signature
say "codesign (ad-hoc)"
codesign --force --deep --sign - "$APP"
codesign --verify --deep --strict "$APP"

say "done: $APP  (v$VERSION build $BUILD, $BUNDLE_ID, $(du -sh "$APP" | cut -f1), total $SECONDS s)"
echo "    run:  open -g -n \"$APP\""
