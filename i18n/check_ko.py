#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ko.json 검증 스크립트.

사용법:
    python3 -I check_ko.py                   # 같은 폴더의 ko.json을 앱의 카탈로그와 대조
    python3 -I check_ko.py --ko other.json --xcstrings path/Localizable.xcstrings

기본 카탈로그는 이 폴더 기준 ../Resources/Localizable.xcstrings (앱의 카탈로그).
다른 카탈로그와 대조하려면 --xcstrings 로 경로를 준다.

필수 검사(하나라도 실패하면 종료 코드 1)
  1. xcstrings의 모든 키가 ko.json에 있는가 (여분의 키도 실패)
  2. 키마다 서식 지정자(%@ %lld %d %%)의 종류·개수가 en 원문과 같은가
     - 위치 지정자(%1$@)는 번호가 아니라 종류로 비교하고, 섞어 쓰거나 번호가 비면 실패
     - 복수형 키는 one/other 변형을 각각 en 변형과 비교
  3. 값에 Coucou / Mochi가 남지 않았는가 (경로·URL 안의 소문자 coucou는 허용하고 따로 알림)
  4. 빈 문자열이 없는가

추가 검사(실패하면 1)
  5. {APP} {PET} 외의 중괄호 자리표시가 없는가
  6. 줄바꿈(\\n)과 • 개수, 앞쪽 공백이 en과 같은가
  7. ~/ 경로, 제품명(Claude Code, Codex, GitHub, ...)이 en에 있으면 값에도 그대로 있는가
  8. 프랑스식 따옴표 « » 와 U+202F(좁은 줄바꿈 없는 공백), 이모지, 웃는 기호가 없는가
  9. 한글이 하나도 없는 값은 허용 목록(제품명·기호·언어 이름 등)에만 있는가
"""
import argparse
import json
import os
import re
import sys
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT_XC = os.path.normpath(os.path.join(HERE, '..', 'Resources', 'Localizable.xcstrings'))

# 서식 지정자: %% 또는 %[N$][길이]종류  (이 카탈로그에서 쓰는 @ d lld 위주, 일반 printf 종류도 인식)
SPEC_RE = re.compile(r'%%|%(?:(\d+)\$)?(?:ll|l|h|hh|q|z|t|j)?([@dDiuUxXoOfeEgGcCsSpaA])')

# 한글이 없어도 되는 키(제품명·기호·언어 이름·경로 등 번역하지 않는 값)
ALLOW_NO_HANGUL = {
    '  %@', ' +%@', ' −%@', '—', '%@', '%@ %%', '%@: %@', '%@/%@', '%@#%@', '%@%%',
    '+%@', '−%@', '★ %@', '✕',
    'Apple Music', 'Bahasa Indonesia', 'Cal.com', 'English', 'Español', 'Français',
    'GitHub', 'LM Studio', 'n8n', 'Notion', 'Ollama',
    'Português (Brasil)', 'Resend', 'Spotify', 'Stripe', 'Vercel', 'z',
    'Русский', 'العربية', 'हिन्दी', 'বাংলা', '简体中文',
    'chat.anthropic-api.title', 'chat.google-ai', 'chat.openai', 'plugin.hermes.title',
    'voice.pill-replaced', 'Coucou',
}

# en에 있으면 한국어 값에도 그대로 있어야 하는 이름(번역 금지)
PRODUCTS = [
    'Claude Code', 'Claude Desktop', 'Codex', 'Gemini CLI', 'GitHub Copilot CLI', 'Copilot CLI',
    'GitHub', 'Spotify', 'n8n', 'Vercel', 'Stripe', 'Ollama', 'LM Studio', 'ElevenLabs',
    'Notion', 'Cal.com', 'Anthropic', 'OpenAI', 'Google AI', 'Google Gemini', 'Hermes',
    'Antigravity', 'Muse Code', 'OpenCode', 'Amp', 'Cursor', 'VS Code', 'Visual Studio Code',
    'Binance', 'Bybit', 'Coinbase', 'Kraken', 'OKX', 'Apple Music', 'Gmail', 'Open-Meteo',
    'iCloud', 'iPhone', 'Dynamic Island', 'Apple Intelligence', 'ChatGPT', 'Warp', 'iTerm',
    'macOS', 'Mail', 'Music', 'JSON', 'AI Studio',
]

EMOJI_RE = re.compile('[\U0001F300-\U0001FAFF\U00002600-\U000026FF\U00002700-\U000027BF]')
# ✓(2713) ❌(274C) ★(2605) ✕(2715) 은 en 원문이 쓰는 기호라 허용 → 아래에서 en에 있는 것은 제외
SMILEY_RE = re.compile(r'ㅋ{2,}|ㅎ{2,}|\^\^|:\)|:-\)|;\)|\(\^|\bTT\b|ㅠㅠ')
HANGUL_RE = re.compile('[가-힣ㄱ-ㆎ]')
BRACE_RE = re.compile(r'\{[^{}]*\}')
PATH_RE = re.compile(r'~/[^\s,;()「」“”]+')


def en_source(strings, key):
    """번역 원문: en stringUnit 값, 복수형이면 {one, other}, 없으면 키 자체."""
    loc = strings[key].get('localizations', {}).get('en')
    if not loc:
        return key
    if 'stringUnit' in loc:
        return loc['stringUnit']['value']
    if 'variations' in loc:
        return {p: v['stringUnit']['value'] for p, v in loc['variations']['plural'].items()}
    raise ValueError(f'알 수 없는 en 구조: {key!r}')


def specs(s):
    """[(위치번호 또는 None, 종류), ...]  종류: '@', 'd', '%'(리터럴 %%) 등. lld는 'd'로 본다."""
    out = []
    for m in SPEC_RE.finditer(s):
        if m.group(0) == '%%':
            out.append((None, '%'))
        else:
            kind = m.group(2)
            kind = 'd' if kind in 'dDiuU' else kind
            out.append((int(m.group(1)) if m.group(1) else None, kind))
    return out


def compare_specs(en_s, ko_s):
    """문제 문자열 목록(없으면 통과)."""
    problems = []
    e, k = specs(en_s), specs(ko_s)
    ec = Counter(kind for _, kind in e)
    kc = Counter(kind for _, kind in k)
    if ec != kc:
        problems.append(f'서식 지정자 종류·개수 불일치: en={dict(ec)} ko={dict(kc)}')
        return problems
    # 위치 지정자 일관성 (%% 제외)
    e_args = [(p, kind) for p, kind in e if kind != '%']
    k_args = [(p, kind) for p, kind in k if kind != '%']
    k_pos = [p for p, _ in k_args if p is not None]
    if k_pos:
        if len(k_pos) != len(k_args):
            problems.append('위치 지정자(%1$@)와 일반 지정자(%@)를 섞어 썼어요')
        elif sorted(k_pos) != list(range(1, len(k_args) + 1)):
            problems.append(f'위치 지정자 번호가 1..{len(k_args)}가 아님: {k_pos}')
        else:
            # 번호별 종류가 en의 같은 번호(또는 en 순서) 종류와 같아야 함
            en_by_idx = {}
            for i, (p, kind) in enumerate(e_args, 1):
                en_by_idx[p if p is not None else i] = kind
            ko_by_idx = {p: kind for p, kind in k_args}
            if en_by_idx != ko_by_idx:
                problems.append(f'위치 번호별 종류 불일치: en={en_by_idx} ko={ko_by_idx}')
    else:
        # 일반 지정자만 쓴 경우: en이 위치 지정이든 아니든 종류의 순서가 같아야 함
        if [kind for _, kind in e_args] != [kind for _, kind in k_args] and \
           all(p is None for p, _ in e_args):
            problems.append('일반 지정자의 순서가 en과 달라요(순서를 바꾸려면 위치 지정자 사용)')
    return problems


def flat_pairs(en_v, ko_v):
    """(변형이름, en문자열, ko문자열) 목록. 구조가 다르면 None."""
    if isinstance(en_v, dict):
        if not isinstance(ko_v, dict) or set(en_v) - set(ko_v):
            return None
        return [(p, en_v[p], ko_v[p]) for p in en_v]
    if isinstance(ko_v, dict):
        return None
    return [('', en_v, ko_v)]


def main():
    ap = argparse.ArgumentParser(description='ko.json 검증')
    ap.add_argument('--ko', default=os.path.join(HERE, 'ko.json'))
    ap.add_argument('--xcstrings', default=DEFAULT_XC,
                    help='대조할 Localizable.xcstrings (기본: ../Resources/Localizable.xcstrings)')
    args = ap.parse_args()

    for label, path in (('xcstrings', args.xcstrings), ('ko.json', args.ko)):
        if not os.path.isfile(path):
            sys.exit(f'{label} 파일을 찾을 수 없어요: {path}\n'
                     f'--xcstrings / --ko 로 경로를 직접 지정해 주세요.')

    xc = json.load(open(args.xcstrings, encoding='utf-8'))
    strings = xc['strings']
    ko = json.load(open(args.ko, encoding='utf-8'))

    fails = {n: [] for n in range(1, 10)}
    infos = []

    # 1. 키 빠짐·여분
    missing = [k for k in strings if k not in ko]
    extra = [k for k in ko if k not in strings]
    for k in missing:
        fails[1].append(f'빠진 키: {k!r}')
    for k in extra:
        fails[1].append(f'xcstrings에 없는 여분 키: {k!r}')

    for key in strings:
        if key not in ko:
            continue
        en_v = en_source(strings, key)
        ko_v = ko[key]
        pairs = flat_pairs(en_v, ko_v)
        if pairs is None:
            fails[2].append(f'{key!r}: 값의 모양이 en과 달라요(복수형이면 {{"one","other"}} 둘 다 필요, 아니면 문자열)')
            continue
        for var, en_s, ko_s in pairs:
            tag = f'{key!r}' + (f'[{var}]' if var else '')
            if not isinstance(ko_s, str):
                fails[2].append(f'{tag}: 문자열이 아님')
                continue
            # 2. 서식 지정자
            for p in compare_specs(en_s, ko_s):
                fails[2].append(f'{tag}: {p}\n      en={en_s!r}\n      ko={ko_s!r}')
            # 3. Coucou / Mochi
            for m in re.finditer(r'coucou|mochi', ko_s, flags=re.I):
                word = m.group(0)
                if word.lower() == word:
                    # 소문자는 경로·URL·파일명 토큰 안에서만 허용
                    start = ko_s.rfind(' ', 0, m.start()) + 1
                    end = ko_s.find(' ', m.end())
                    token = ko_s[start:end if end != -1 else len(ko_s)]
                    if '/' in token or '.' in token:
                        infos.append(f'경로/URL 안의 소문자 {word}: {tag} -> {token}')
                        continue
                fails[3].append(f'{tag}: {word!r} 남음 -> {ko_s!r}')
            # 4. 빈 문자열
            if ko_s.strip() == '':
                fails[4].append(f'{tag}: 빈 문자열')
            # 5. 자리표시
            for b in BRACE_RE.findall(ko_s):
                if b not in ('{APP}', '{PET}'):
                    fails[5].append(f'{tag}: 알 수 없는 자리표시 {b}')
            if re.search(r'[{}]', BRACE_RE.sub('', ko_s)):
                fails[5].append(f'{tag}: 짝이 안 맞는 중괄호 -> {ko_s!r}')
            # 6. 줄바꿈 · 불릿 · 앞쪽 공백
            if en_s.count('\n') != ko_s.count('\n'):
                fails[6].append(f'{tag}: 줄바꿈 수 en={en_s.count(chr(10))} ko={ko_s.count(chr(10))}')
            if en_s.count('•') != ko_s.count('•'):
                fails[6].append(f'{tag}: • 개수 불일치')
            lead_en = en_s[:len(en_s) - len(en_s.lstrip(' '))]
            lead_ko = ko_s[:len(ko_s) - len(ko_s.lstrip(' '))]
            if lead_en != lead_ko:
                fails[6].append(f'{tag}: 앞쪽 공백 불일치 en={lead_en!r} ko={lead_ko!r}')
            # 7. 경로·제품명
            for pth in PATH_RE.findall(en_s):
                pth = pth.rstrip('.:?!,;…')
                if pth not in ko_s:
                    fails[7].append(f'{tag}: 경로 {pth} 가 값에 없음')
            en_cmp = en_s if key not in ('Open Settings…',) else ''
            for name in PRODUCTS:
                if re.search(r'(?<![A-Za-z])' + re.escape(name) + r'(?![A-Za-z])', en_cmp) \
                        and name not in ko_s:
                    # 긴 이름이 짧은 이름을 포함하는 경우(Claude Code ⊃ Code 등)는 위 정규식으로 구분됨
                    fails[7].append(f'{tag}: 제품명 {name!r} 이 값에 없음 -> {ko_s!r}')
            # 8. 따옴표·공백·이모지·웃는 기호
            if '«' in ko_s or '»' in ko_s or ' ' in ko_s:
                fails[8].append(f'{tag}: « » 또는 U+202F 남음 -> {ko_s!r}')
            for ch in EMOJI_RE.findall(ko_s):
                if ch not in en_s and ch not in '✓✕❌★':
                    fails[8].append(f'{tag}: 이모지/기호 {ch!r} 는 en에 없음')
            if SMILEY_RE.search(ko_s):
                fails[8].append(f'{tag}: 웃는 기호/ㅋㅋ 류 -> {ko_s!r}')
            # 9. 한글 없는 값
            if not HANGUL_RE.search(ko_s) and key not in ALLOW_NO_HANGUL:
                fails[9].append(f'{tag}: 한글이 없음(번역 누락?) -> {ko_s!r}')

    # en에 Coucou/Mochi가 있는데 ko에 {APP}/{PET}이 없는 경우는 참고로만 알림
    for key in strings:
        if key not in ko:
            continue
        en_v = en_source(strings, key)
        en_all = ' '.join(en_v.values()) if isinstance(en_v, dict) else en_v
        ko_all = ' '.join(ko[key].values()) if isinstance(ko[key], dict) else ko[key]
        if 'Coucou' in en_all and '{APP}' not in ko_all and 'coucou' not in ko_all:
            infos.append(f'en에 Coucou가 있는데 ko에 {{APP}}이 없음: {key!r}')
        if 'Mochi' in en_all and '{PET}' not in ko_all:
            infos.append(f'en에 Mochi가 있는데 ko에 {{PET}}이 없음: {key!r}')

    names = {
        1: '모든 키가 ko.json에 있음',
        2: '서식 지정자 종류·개수가 en과 같음',
        3: 'Coucou/Mochi가 남지 않음',
        4: '빈 문자열 없음',
        5: '{APP}/{PET} 외 자리표시 없음',
        6: '줄바꿈·불릿·앞쪽 공백 보존',
        7: '경로·제품명 보존',
        8: '« »·U+202F·이모지·웃는 기호 없음',
        9: '한글 없는 값은 허용 목록뿐',
    }
    total = len(strings)
    print(f'xcstrings 키 {total}개 / ko.json 키 {len(ko)}개')
    bad = False
    for n in range(1, 10):
        if fails[n]:
            bad = True
            print(f'[실패] ({n}) {names[n]}  — {len(fails[n])}건')
            for line in fails[n][:40]:
                print('   ', line)
            if len(fails[n]) > 40:
                print(f'    ... 외 {len(fails[n]) - 40}건')
        else:
            print(f'[통과] ({n}) {names[n]}')
    if infos:
        print(f'\n참고 {len(infos)}건')
        for line in infos:
            print('  -', line)
    print('\n결과:', '실패' if bad else '전부 통과')
    sys.exit(1 if bad else 0)


if __name__ == '__main__':
    main()
