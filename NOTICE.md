# NOTICE

## 한국어

뚝딱은 Louis Raillé의 [Coucou](https://github.com/Louis-CFM/coucou)(MIT)를 바탕으로 만들었고, 코드를 고쳤습니다.
Coucou·Mochi 이름, Mochi 캐릭터, Coucou의 아이콘·효과음은 들어 있지 않습니다.

- `Sources/` 의 코드는 Coucou 맥 앱의 소스에서 복사한 뒤 고친 것입니다. Coucou 코드는 MIT 라이선스이고,
  라이선스가 요구하는 대로 라이선스 전문과 저작권 표시("Copyright (c) 2026 Louis Raillé")를
  `LICENSE-Coucou.txt` 에 그대로 두었습니다. `LICENSE` 에도 같은 저작권 표시가 있습니다.
- 새로 만든 것: 캐릭터 복슬깨비(`design/pet/`, `Sources/TtukttakKit/PetSprite.swift`, 자동 생성 파일
  `PetSpriteData.swift`), 앱·메뉴 막대 아이콘(`scripts/make_icons.py` 가 복슬깨비 그림으로 그림),
  효과음 29개(`scripts/make_sounds.py` 가 처음부터 합성), 한국어 문구(`i18n/`), 빌드 스크립트(Xcode 없이 `swiftc` 로 빌드).
- Coucou에서 지운 것: Mochi를 그리던 코드와 옷장, iPhone 연동, 원작자 개인 프로젝트 이름(프로젝트 색 목록).
  이름·경로·훅 신호도 모두 바꿨습니다
  (지원 폴더 `Ttukttak`, 훅 `tt-hook`, 소켓 `tt.sock`, 신호 필드 `tt_*`, 번들 ID `kr.jinhyeon.ttukttak`,
  음성 호출어 "OK Ttukttak"). 그래서 Coucou와 한 맥에 같이 깔려도 서로의 훅을 건드리지 않습니다.
- 문구 카탈로그(`Resources/Localizable.xcstrings`)는 Coucou에서 가져왔습니다(MIT 코드의 일부).
  키 11개에 원래 이름 "Coucou"·"Mochi"가 아직 들어 있는데, 키는 코드가 문구를 찾는 이름이라 그대로 두었고
  `scripts/build.sh` 가 번역 파일을 만들 때 값 속 이름을 "뚝딱"·"복슬깨비"로 바꿉니다. 앱 화면에는 나오지 않습니다.
- 캐릭터 그림·아이콘·이름의 이용 조건은 `LICENSE-ASSETS` 에 있습니다(코드의 MIT와 별개).
- 이 프로젝트는 독립 프로젝트이며, Louis Raillé가 만들거나 보증하거나 지원하는 것이 아닙니다.

## English

Ttukttak (뚝딱) is based on [Coucou](https://github.com/Louis-CFM/coucou) by Louis Raillé (MIT); the code was modified.
Coucou's and Mochi's names, the Mochi character, and Coucou's icons and sounds are not included.

- The code in `Sources/` was copied from the source of Coucou's macOS app and then modified. Coucou's code is
  MIT-licensed; as the license requires, its text and copyright line ("Copyright (c) 2026 Louis Raillé") are kept
  unchanged in `LICENSE-Coucou.txt`, and the same line is in `LICENSE`.
- Made for this project: the Bokseul-kkaebi character (`design/pet/`, `Sources/TtukttakKit/PetSprite.swift` and the
  generated `PetSpriteData.swift`), the app and menu bar icons (drawn from the character by `scripts/make_icons.py`),
  the 29 sound effects (synthesised from scratch by `scripts/make_sounds.py`), the Korean strings (`i18n/`), and the
  build script (plain `swiftc`, no Xcode).
- Removed from Coucou: the Mochi drawing code and its wardrobe, the iPhone link, and the author's personal project
  names (project colour list). Names, paths and hook signals were all changed
  (support folder `Ttukttak`, hook `tt-hook`, socket `tt.sock`, signal fields `tt_*`, bundle ID `kr.jinhyeon.ttukttak`,
  voice wake phrase "OK Ttukttak"), so it can sit next to Coucou on one Mac without touching Coucou's hooks.
- The string catalog (`Resources/Localizable.xcstrings`) comes from Coucou (part of the MIT code). Eleven keys still
  contain the original names "Coucou" and "Mochi": keys are what the code looks strings up by, so they were kept, and
  `scripts/build.sh` replaces the names in the values with this app's names when it writes the translations.
  They never show in the app.
- The terms for the character art, the icons and the names are in `LICENSE-ASSETS` (separate from the code's MIT license).
- This project is independent. It is not made, endorsed, or supported by Louis Raillé.
