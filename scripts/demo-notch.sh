#!/bin/bash
# demo-notch.sh - 실제 노치에서 캐릭터가 상태마다 움직이는 걸 보여 준다(가짜 Claude Code 세션, 약 1분).
#
#   scripts/demo-notch.sh                      # 노치를 직접 보면서
#   scripts/demo-notch.sh --record 시연.mov    # 노치 주변을 화면 녹화(screencapture -v)
#   scripts/demo-notch.sh --sound              # 효과음도 켠다(기본은 시연 동안 끈다)
#   scripts/demo-notch.sh --keep               # 끝나도 시연 앱을 켜 둔다(설정·기록도 되돌리지 않고, 시연 앱은 실제 세션 신호를 못 받는다)
#   scripts/demo-notch.sh --lang en            # 화면 글자 언어(기본 ko). 맥·앱 설정은 바꾸지 않고 이번 실행에만 쓴다
#   DEMO_APP=/Applications/뚝딱.app scripts/demo-notch.sh   # 다른 사본으로 시연(기본 build/뚝딱.app)
#   DEMO_CWD=~/projects/my-app scripts/demo-notch.sh        # 카드에 보이는 작업 폴더 이름을 바꾼다(기본 ~/projects/notch-app)
#   scripts/demo-notch.sh --scene multi-error  # 세션 두 개 중 하나가 오류로 멈추는 장면(약 40초, 배지·소리 확인용)
#   scripts/demo-notch.sh --snap 폴더           # 장면마다 노치 둘레(720×60pt)를 사진으로 남긴다(확인용. 노치 옆 메뉴 막대도 찍히니 밖에 내보내지 않는다)
#
# 하는 일:
# 1. 이미 켜져 있는 뚝딱(설치본 등)과 Coucou를 끈다(같은 노치 자리·같은 소켓을 쓰므로). 지우지 않는다.
# 2. 앱 설정(defaults)과 주간 리캡 기록(recap.json)을 임시 폴더에 떠 둔다.
# 3. 시연 앱을 켠다(-g: 다른 창 앞으로 나오지 않게). 켜자마자 인사 장면이 나온다.
# 4. 우리 훅(~/Library/Application Support/Ttukttak/tt-hook)에 Claude Code가 보내는 것과 같은 모양의
#    신호를 차례로 넣는다: 시작 → 생각 → 작업 → 질문 → 사용량 한도 → 허락 요청 → 끝 → 낮잠 → 오류 → 종료.
#    시연 앱은 tt.sock 대신 tt-demo.sock으로 듣고(-TTSocketName), 시연 신호도 그리로 보낸다(TT_SOCKET_NAME).
# 5. 시연 앱을 끄고(--keep이면 그대로), 떠 둔 설정·기록을 그대로 되돌린 뒤 1에서 끈 앱을 다시 켠다.
#    그래서 가짜 신호가 실제 주간 통계에 섞이지 않는다.
#
# ~/.claude/settings.json은 읽지도 고치지도 않는다. 신호는 이 스크립트가 직접 훅에 넣는다.
# 열려 있는 실제 Claude Code 세션의 신호는 늘 tt.sock으로 가므로 시연에 섞이지 않는다. 그래서 다른 세션 내용이
# 노치·녹화에 나오지 않고, 다른 세션이 일하는 중이라 끝남·오류 카드가 안 뜨는 일도 없다.
# 시연하는 1분 동안 실제 세션의 훅은 앱이 꺼져 있을 때처럼 바로 넘어간다(노치 표시·허락 카드만 잠깐 없다).
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
APP="${DEMO_APP:-$ROOT/build/뚝딱.app}"
EXE="Ttukttak"                                   # 실행 파일(프로세스) 이름
DOMAIN="kr.jinhyeon.ttukttak"
SUPPORT="$HOME/Library/Application Support/Ttukttak"
HOOK="$SUPPORT/tt-hook"
DEMO_SOCK_NAME="tt-demo.sock"                   # 시연 앱만 쓰는 소켓(실제 세션은 tt.sock)
SOCK="$SUPPORT/$DEMO_SOCK_NAME"
RECAP="$SUPPORT/recap.json"
COUCOU_APP="/Applications/Coucou.app"

RECORD="" SOUND=0 KEEP=0 DEMO_LANG="ko" SCENE="tour" SNAP_DIR=""
while [ $# -gt 0 ]; do
  case "$1" in
    --scene)  SCENE="${2:?--scene 다음에 장면 이름(tour, multi-error)}"; shift 2 ;;
    --snap)   SNAP_DIR="${2:?--snap 다음에 사진을 둘 폴더}"; shift 2 ;;
    --record) RECORD="${2:?--record 다음에 저장할 파일(.mov)}"; shift 2 ;;
    --sound)  SOUND=1; shift ;;
    --keep)   KEEP=1; shift ;;
    --lang)   DEMO_LANG="${2:?--lang 다음에 언어 코드(ko, en …)}"; shift 2 ;;
    -h|--help) awk 'NR > 1 && /^#/ { sub(/^# ?/, ""); print; next } NR > 1 { exit }' "$0"; exit 0 ;;
    *) echo "모르는 옵션: $1" >&2; exit 2 ;;
  esac
done

say() { printf '==> %s\n' "$*"; }
case "$SCENE" in tour|multi-error) ;; *) echo "모르는 장면: $SCENE (tour, multi-error)" >&2; exit 2 ;; esac
[ -d "$APP" ] || { echo "앱이 없다: $APP (먼저 scripts/build.sh)" >&2; exit 1; }

stop_ttukttak() {   # 켜진 뚝딱을 모두 끈다(5초 안에 안 꺼지면 강제로)
  pkill -TERM -x "$EXE" 2>/dev/null || return 0
  for _ in $(seq 1 50); do pgrep -x "$EXE" >/dev/null || return 0; sleep 0.1; done
  pkill -KILL -x "$EXE" 2>/dev/null || true
  sleep 0.3
}

# ---------------------------------------------------------------- 1. 켜져 있던 앱 잠깐 끄기
PREV_APPS=""   # 끝나면 다시 켤 뚝딱 사본(.app 경로, 한 줄에 하나)
for pid in $(pgrep -x "$EXE" || true); do
  exe="$(ps -o comm= -p "$pid" 2>/dev/null || true)"
  case "$exe" in */Contents/MacOS/*) PREV_APPS="$PREV_APPS${exe%/Contents/MacOS/*}"$'\n' ;; esac
done
if [ -n "$PREV_APPS" ]; then
  say "켜져 있던 뚝딱 잠깐 끔 (끝나면 다시 켬): $(printf '%s' "$PREV_APPS" | tr '\n' ' ')"
  stop_ttukttak
fi
coucou_pid="$(pgrep -f "$COUCOU_APP/Contents/MacOS/Coucou" || true)"
if [ -n "$coucou_pid" ]; then
  say "Coucou 잠깐 끔 (pid $coucou_pid, 끝나면 다시 켬)"
  kill -TERM $coucou_pid
  for _ in $(seq 1 50); do pgrep -f "$COUCOU_APP/Contents/MacOS/Coucou" >/dev/null || break; sleep 0.1; done
fi

# ---------------------------------------------------------------- 2. 설정·기록 떠 두기
TMPD="$(mktemp -d "${TMPDIR:-/tmp}/tt-demo.XXXXXX")"
defaults export "$DOMAIN" "$TMPD/prefs.plist"      # 설정이 없으면 빈 목록이 저장된다
RECAP_SAVED=0
[ -f "$RECAP" ] && cp -p "$RECAP" "$TMPD/recap.json" && RECAP_SAVED=1

REC_PID="" PERM_PID=""
restore() {
  # 도중에 멈췄으면 녹화와 허락 요청 신호도 멈춘다(정상으로 끝났으면 이미 끝나 있다).
  [ -n "$REC_PID" ] && kill -INT "$REC_PID" 2>/dev/null || true
  [ -n "$PERM_PID" ] && kill "$PERM_PID" 2>/dev/null || true
  if [ "$KEEP" -eq 0 ]; then
    stop_ttukttak
    # import는 합치기만 하므로 먼저 지운다. 그래야 시연 전과 똑같아진다.
    defaults delete "$DOMAIN" 2>/dev/null || true
    defaults import "$DOMAIN" "$TMPD/prefs.plist" && say "설정 되돌림"
    if [ "$RECAP_SAVED" -eq 1 ]; then cp -p "$TMPD/recap.json" "$RECAP"; else rm -f "$RECAP"; fi
    say "주간 리캡 기록 되돌림"
    printf '%s' "$PREV_APPS" | while IFS= read -r app; do
      [ -n "$app" ] && [ -d "$app" ] && open -g "$app" && say "다시 켬: $app"
    done || true
    if [ -n "$coucou_pid" ] && [ -d "$COUCOU_APP" ]; then
      sleep 0.5
      open -g "$COUCOU_APP" && say "Coucou 다시 켬"
    fi
    rm -f "$SOCK"
    rm -rf "$TMPD"
  else
    say "--keep: 시연 앱을 켜 둔다. 시연 전 설정·기록은 $TMPD 에 있다"
  fi
}
trap restore EXIT
trap 'exit 130' INT TERM

# ---------------------------------------------------------------- 3. 시연 설정, 녹화, 앱 켜기
defaults write "$DOMAIN" petNapSeconds -float 12          # 12초 쉬면 낮잠(평소 90초)
[ "$SOUND" -eq 1 ] || defaults write "$DOMAIN" soundEnabled -bool false
defaults write "$DOMAIN" terminalCardsEnabled -bool true  # 터미널 세션의 허락 요청도 노치 카드로(평소엔 설정에서 켠다)

TOTAL=68; [ "$SCENE" = "multi-error" ] && TOTAL=42
if [ -n "$RECORD" ]; then
  # 노치를 가운데 두고 펼친 섬(640×176)까지 들어가게 720×200pt를 녹화한다.
  read -r SW <<<"$(osascript -l JavaScript -e 'ObjC.import("AppKit"); $.NSScreen.mainScreen.frame.size.width')"
  RX=$(( ${SW%.*} / 2 - 360 ))
  rm -f "$RECORD"
  screencapture -v -x -V "$TOTAL" -R"$RX,0,720,200" "$RECORD" >/dev/null 2>&1 &
  REC_PID=$!
  say "녹화 시작 (${TOTAL}초, x=$RX y=0 720×200) → $RECORD"
  sleep 1.5
fi

say "뚝딱 켬 — 인사 장면 (화면 언어 $DEMO_LANG, $APP)"
rm -f "$SOCK"   # 지난번 시연이 남긴 소켓이 있으면 앱이 준비되기 전에 아래 확인을 통과해 버린다
open -g -n "$APP" --args -AppleLanguages "($DEMO_LANG)" -TTSocketName "$DEMO_SOCK_NAME"
for _ in $(seq 1 150); do [ -S "$SOCK" ] && [ -x "$HOOK" ] && break; sleep 0.1; done
[ -S "$SOCK" ] || { echo "$DEMO_SOCK_NAME이 생기지 않았다(이 기능이 없는 옛 빌드면 다시 빌드)" >&2; exit 1; }
sleep 5.5   # 인사 장면(약 4.6초)이 끝날 때까지

# ---------------------------------------------------------------- 4. 신호 넣기
SID="ttdemo-$(date +%s)"
CWD="${DEMO_CWD:-$HOME/projects/notch-app}"   # 노치 카드에 보이는 작업 폴더(이름만 쓴다. 홍보 녹화 땐 DEMO_CWD로 바꾼다)
send() {   # send '{"hook_event_name": ..., ...}' [세션 꼬리표]  (session_id·cwd·터미널 정보는 여기서 붙인다)
  python3 -I -c '
import json, sys
p = json.loads(sys.argv[1])
p.update(session_id=sys.argv[2], cwd=sys.argv[3], term_program="Apple_Terminal", bundle_id="com.apple.Terminal")
print(json.dumps(p, ensure_ascii=False))' "$1" "$SID${2:+-$2}" "$CWD" | TT_SOCKET_NAME="$DEMO_SOCK_NAME" "$HOOK" >/dev/null 2>&1 || true
}
step() { say "$1"; }
snap() {   # snap 이름 — --snap을 줬을 때만, 노치를 가운데 둔 720×60pt
  [ -n "$SNAP_DIR" ] || return 0
  mkdir -p "$SNAP_DIR"
  local sw; sw="$(osascript -l JavaScript -e 'ObjC.import("AppKit"); $.NSScreen.mainScreen.frame.size.width')"
  screencapture -x -R"$(( ${sw%.*} / 2 - 360 )),0,720,60" "$SNAP_DIR/$1.png" 2>/dev/null || true
}

scene_tour() {   # 한 세션이 상태를 차례로 거친다(약 1분)
  step "시작 (쉬는 중)";            send '{"hook_event_name":"SessionStart","source":"startup"}'; sleep 3.5
  step "생각 중";                   send '{"hook_event_name":"UserPromptSubmit","prompt":"복슬깨비 노치 시연"}'; sleep 3
  step "작업 중 (방망이로 뚝딱)";   send '{"hook_event_name":"PreToolUse","tool_name":"Bash","tool_input":{"command":"scripts/build.sh"}}'; sleep 3
  step "질문 있어";                 send '{"hook_event_name":"Notification","message":"어느 쪽으로 할까요?"}'; sleep 3
  step "다시 작업";                 send '{"hook_event_name":"PreToolUse","tool_name":"Edit","tool_input":{"file_path":"'"$CWD"'/README.md"}}'; sleep 2
  step "사용량 한도 (오래 기다림)"; send '{"hook_event_name":"Notification","message":"Claude usage limit reached (rate limit)"}'; sleep 3.5
  step "허락해 줘!";
  PERM='{"hook_event_name":"PermissionRequest","tool_name":"Bash","tool_input":{"command":"open -g build/뚝딱.app"}}'
  send "$PERM" & PERM_PID=$!
  sleep 4.5
  # 터미널에서 허락한 것처럼: 같은 도구가 끝났다는 신호가 오면 섬의 허락 카드가 닫힌다.
  send '{"hook_event_name":"PostToolUse","tool_name":"Bash","tool_input":{"command":"open -g build/뚝딱.app"}}'
  sleep 1; kill "$PERM_PID" 2>/dev/null || true; PERM_PID=""
  step "끝났어 (금 나와라 뚝딱)";   send '{"hook_event_name":"Stop","last_assistant_message":"다 됐어요! 노치에 복슬깨비가 들어갔어요."}'; sleep 6.5
  step "쉬다가 낮잠 (12초 뒤 Zzz)"; sleep 15
  step "다시 생각";                 send '{"hook_event_name":"UserPromptSubmit","prompt":"하나만 더"}'; sleep 2
  step "오류 (서버가 붐빔)";        send '{"hook_event_name":"StopFailure","error":"overloaded","last_assistant_message":"API Error: 529 Overloaded"}'; sleep 4.5
  step "세션 끝 (카드 닫힘)";       send '{"hook_event_name":"SessionEnd","reason":"exit"}'; sleep 2
}

scene_multi_error() {   # 같은 터미널 알약에 세션 두 개(A·B). A가 일하는 동안 B가 오류로 멈춘다.
  step "A 시작·작업";                send '{"hook_event_name":"SessionStart","source":"startup"}' a
  send '{"hook_event_name":"UserPromptSubmit","prompt":"긴 작업"}' a
  send '{"hook_event_name":"PreToolUse","tool_name":"Bash","tool_input":{"command":"scripts/build.sh"}}' a; sleep 2.5
  step "B 시작·작업";                send '{"hook_event_name":"SessionStart","source":"startup"}' b
  send '{"hook_event_name":"UserPromptSubmit","prompt":"다른 작업"}' b
  send '{"hook_event_name":"PreToolUse","tool_name":"Edit","tool_input":{"file_path":"'"$CWD"'/README.md"}}' b; sleep 2.5
  step "B 오류 (A는 계속 일함) → 오류 소리·빨간 배지"
  send '{"hook_event_name":"StopFailure","error":"overloaded","last_assistant_message":"API Error: 529 Overloaded"}' b; sleep 1.2; snap 1-b-error; sleep 3.8
  step "A 계속 작업 (배지 그대로)";   send '{"hook_event_name":"PreToolUse","tool_name":"Read","tool_input":{"file_path":"'"$CWD"'/NOTICE.md"}}' a; sleep 3
  step "A 끝 (끝남 카드)";            send '{"hook_event_name":"Stop","last_assistant_message":"A 작업이 끝났어요."}' a; sleep 6
  step "A 새 질문 (카드 닫힘, B 배지는 남음)"
  send '{"hook_event_name":"UserPromptSubmit","prompt":"A에게 하나 더"}' a; sleep 3; snap 2-a-new-prompt; sleep 1.5
  step "B 다시 시킴 (배지 사라짐)";   send '{"hook_event_name":"UserPromptSubmit","prompt":"B 다시"}' b; sleep 1.5; snap 3-b-retried; sleep 3
  step "둘 다 끝·종료";               send '{"hook_event_name":"Stop","last_assistant_message":"둘 다 끝."}' a
  send '{"hook_event_name":"Stop","last_assistant_message":"B도 끝."}' b; sleep 2
  send '{"hook_event_name":"SessionEnd","reason":"exit"}' a
  send '{"hook_event_name":"SessionEnd","reason":"exit"}' b; sleep 2
}

case "$SCENE" in
  tour)        scene_tour ;;
  multi-error) scene_multi_error ;;
esac

if [ -n "$RECORD" ]; then
  say "녹화 마무리 기다리는 중"
  wait "$REC_PID" 2>/dev/null || true
  REC_PID=""
  [ -s "$RECORD" ] && say "녹화: $RECORD ($(du -h "$RECORD" | cut -f1))" || echo "녹화 파일이 비었다(화면 기록 권한 확인)" >&2
fi
say "끝"
