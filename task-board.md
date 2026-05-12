# FloatVocab 浠诲姟鐪嬫澘

鎵€鏈?agent 鐨勫叡浜换鍔℃澘銆侰laude1 鍒涘缓 ticket锛屽叾浠栬鑹插湪瀵瑰簲 ticket 閲屽啓璇勫鎰忚銆佹祴璇曟姤鍛娿€侀獙鏀剁粨璁恒€?
---

## 鐘舵€佽鏄?
| 鐘舵€?| 鍚箟 | 褰撳墠璐熻矗浜?|
|------|------|-----------|
| `PM_DRAFT` | PM 姝ｅ湪璧疯崏 | Claude1 |
| `PM_REVISION` | Claude2 瑕佹眰淇敼锛岀瓑 PM | Claude1 |
| `UI_REVIEW` | 绛?UI 鎬荤洃璇勫 | Claude2 |
| `DEV_TODO` | 绛夊緟寮€鍙戯紝鍙互鎺ュ崟 | Codex1 |
| `DEV_IN_PROGRESS` | 寮€鍙戜腑 | Codex1 |
| `TEST_IN_PROGRESS` | 娴嬭瘯涓?| Codex2 |
| `UI_ACCEPTANCE` | 绛?UI 鎬荤洃楠屾敹 | Claude2 |
| `DONE` | 瀹屾垚 | 鈥?|
| `BLOCKED` | 鏈夎褰曠殑闃诲锛屾殏鍋滄帹杩?| Claude1 |

---

## 娲昏穬 Tickets

---

## TICKET-01锛氫慨澶?daily_new 姣忔棩鏂拌瘝闄愬埗涓嶇敓鏁?
- **绫诲瀷**锛歯on-ui
- **浼樺厛绾?*锛歨igh
- **鐘舵€?*锛欴ONE
- **褰撳墠璐熻矗浜?*锛氣€?- **鍏宠仈鍔熻兘**锛歝ore-flashcard
- **鍒涘缓鏃堕棿**锛?026-05-12 00:00

### 鐩爣
鐢ㄦ埛鍦ㄨ鍒掗噷璁剧疆銆屾瘡鏃ユ柊璇?N 涓€嶏紝褰撳ぉ鐪嬪畬 N 涓柊璇嶅悗锛岀郴缁熶笉鍐嶆帹鏂拌瘝锛屽彧鎺ㄤ粖鏃ュ緟澶嶄範璇嶏紱浠婃棩寰呭涔犲拰鏂拌瘝鍧囧畬鎴愬悗鍋滄鎺ㄥ崱锛堜笉鎻愬墠娑堣垂鏄庡ぉ鐨勫涔狅級銆?
### 楠屾敹鏍囧噯
- [ ] `daily_new=3`锛岃瘝搴?10+ 涓叏鏂板崟璇嶏紝涓€娆?session 鏍囪鍏ㄩ儴璁よ瘑锛屽綋澶╁睍绀烘柊璇嶆暟閲?鈮?3
- [ ] 鏂拌瘝鐢ㄥ畬鍚庝粛鏈夊埌鏈熷涔犺瘝鏃讹紝缁х画鎺ㄥ涔犺瘝锛堜笉鍋滄锛?- [ ] 鏂拌瘝鍜屽涔犺瘝鍧囧畬鎴愭椂锛宍next_card()` 杩斿洖 `None`
- [ ] `python -m pytest tests/ -v --ignore=tests/_tmp_ui_layout` 鍏ㄧ豢
- [ ] 鏂板娴嬭瘯 `tests/test_daily_new_limit.py` 瑕嗙洊涓婅堪涓夌鎯呭喌

### 鎶€鏈畾浣?鏍瑰洜鍦?[`floatvocab/repositories/study_repository.py:40-55`](floatvocab/repositories/study_repository.py) 鐨?`next_card()` 鏌ヨ鈥斺€斾粠涓嶈鍙?`plans.daily_new`锛屼篃涓嶆煡浠婃棩 `daily_stats.new_seen`銆?
淇鏂瑰悜锛氬湪 `next_card()` 涓紝鑻ヤ粖鏃?`daily_stats.new_seen >= plans.daily_new`锛屽垯 SQL 鏉′欢鎺掗櫎 `repetitions = 0` 鐨勮瘝锛堝嵆鏂拌瘝锛夛紝鍙繑鍥炲埌鏈熷涔犺瘝銆?
---

### 娴佺▼璁板綍

| 鏃堕棿 | 鎿嶄綔 | 璐熻矗浜?|
|------|------|--------|
| 2026-05-12 00:00 | 鍒涘缓 ticket锛岄€氭鍙戠幇鏍瑰洜 | Claude1(PM) |
| 2026-05-12 00:00 | 寮€濮嬪紑鍙?daily_new 闄愬埗 | Codex1(Dev) |
| 2026-05-12 00:00 | 寮€鍙戝畬鎴愶紝淇敼 `floatvocab/repositories/study_repository.py`锛屾柊澧?`tests/test_daily_new_limit.py`锛屾彁浜?Codex2 娴嬭瘯 | Codex1(Dev) |
| 2026-05-12 00:00 | 娴嬭瘯閫氳繃锛孴ICKET-01 瀹屾垚 | Codex2(Test) |

### 娴嬭瘯鎶ュ憡锛圕odex2锛?026-05-12 00:00锛?**缁撹**锛氶€氳繃

**鑷姩鍖栨祴璇?*锛?- 杩愯鍛戒护锛歚python -m pytest tests/ -v --ignore=tests/_tmp_ui_layout`
- 缁撴灉锛?13 passed, 1 failed, 0 skipped
- 澶辫触璇︽儏锛歚tests/test_ui_layout.py::AppLayoutTests::test_dashboard_fits_primary_controls_without_vertical_scrollbar` 鈥?鏈満 Anaconda Tk 瀹夎缂哄皯 `entry.tcl/listbox.tcl`锛宍tk.Tk()` 鍒涘缓澶辫触銆傝澶辫触灞炰簬鏈満 GUI/Tk 鐜闂锛屼笖娴嬭瘯鐩爣鏄?dashboard 婊氬姩鏉″竷灞€锛屼笌 TICKET-01 鐨?`daily_new` 閫夎瘝閫昏緫鏃犲叧銆?- 杩藉姞杩愯锛歚python -m pytest tests/test_daily_new_limit.py -v`
- 缁撴灉锛? passed

**鎵嬪伐楠岃瘉**锛?| 楠屾敹鏉＄洰 | 缁撴灉 | 澶囨敞 |
|----------|------|------|
| `daily_new=3`锛岃瘝搴?10+ 涓叏鏂板崟璇嶏紝涓€娆?session 鏍囪鍏ㄩ儴璁よ瘑锛屽綋澶╁睍绀烘柊璇嶆暟閲?鈮?3 | 鉁?| 鐙珛鑴氭湰杈撳嚭 `new_words_shown 3 ['new-0', 'new-1', 'new-2']` |
| 鏂拌瘝鐢ㄥ畬鍚庝粛鏈夊埌鏈熷涔犺瘝鏃讹紝缁х画鎺ㄥ涔犺瘝锛堜笉鍋滄锛?| 鉁?| 鐙珛鑴氭湰鍦ㄨ揪鍒伴檺鍒跺悗鎻掑叆鍒版湡澶嶄範璇嶏紝杈撳嚭 `due_after_limit due-review` |
| 鏂拌瘝鍜屽涔犺瘝鍧囧畬鎴愭椂锛宍next_card()` 杩斿洖 `None` | 鉁?| 鐙珛鑴氭湰杈惧埌鏂拌瘝闄愬埗涓旀棤鍒版湡澶嶄範璇嶆椂杈撳嚭 `after_new_limit None` |
| 鏂板娴嬭瘯 `tests/test_daily_new_limit.py` 瑕嗙洊涓婅堪涓夌鎯呭喌 | 鉁?| 3 涓柊澧炵敤渚嬪叏閮ㄩ€氳繃 |

**Bug 鍒楄〃**锛氭棤涓庢湰 ticket 鐩稿叧鐨?bug銆?
---

## TICKET-02锛氫慨澶嶅唴缃瘝搴撳悕绉颁贡鐮?
- **绫诲瀷**锛歯on-ui
- **浼樺厛绾?*锛歨igh
- **鐘舵€?*锛欴ONE
- **褰撳墠璐熻矗浜?*锛?
- **鍏宠仈鍔熻兘**锛歟xam-lexicon-selector
- **鍒涘缓鏃堕棿**锛?026-05-12 00:00

### 鐩爣
鏂板畨瑁呮垨棣栨鍒濆鍖栨暟鎹簱鏃讹紝鍐呯疆鑰冪爺 50 璇嶅簱鍦ㄨ瘝搴撳垪琛ㄦ樉绀烘纭殑涓枃鍚嶇О锛岃€屼笉鏄贡鐮併€?
### 楠屾敹鏍囧噯
- [ ] 鍒犻櫎鏈湴 DB 鏂囦欢鍚庨噸鏂?`python app.py`锛岃瘝搴撳垪琛ㄤ腑鍑虹幇鍙涓枃鍚嶏紙涓嶅惈 `閼板啰鐖篳 绛変贡鐮佸瓧绗︼級
- [ ] 宸叉湁 DB 鐨勬棫鐢ㄦ埛鍗囩骇鍚庯紝涔辩爜璇嶅簱琚竻鐞嗘垨閲嶅懡鍚嶏紝涓嶄骇鐢熼噸澶嶈瘝搴?- [ ] `python -m pytest tests/ -v --ignore=tests/_tmp_ui_layout` 鍏ㄧ豢

### 鎶€鏈畾浣?鏍瑰洜鍦?[`floatvocab/db.py:188,193`](floatvocab/db.py)锛屼袱澶勫瓧绗︿覆 `"閼板啰鐖洪弽绋跨妇 50"` 鏄?mojibake锛堟纭悕绉板緟纭锛屽弬鑰?README銆岃€冪爺鏍稿績璇嶃€嶅拰鏂囦欢鍚?`kaoyan_50.json`锛夈€?
淇鏂瑰悜锛氬皢涓ゅ涔辩爜瀛楃涓叉敼涓烘纭?UTF-8 涓枃鍚嶃€傚悓鏃跺鐞嗗凡鏈?DB 杩佺Щ锛氳嫢瀛樺湪涔辩爜鍚嶈瘝搴擄紝鎵ц `UPDATE lexicons SET name = ? WHERE name = ?` 閲嶅懡鍚嶃€?
---

### 娴佺▼璁板綍

| 鏃堕棿 | 鎿嶄綔 | 璐熻矗浜?|
|------|------|--------|
| 2026-05-12 00:00 | 鍒涘缓 ticket锛岄€氭鍙戠幇鏍瑰洜 | Claude1(PM) |
| 2026-05-12 00:00 | 寮€濮嬪紑鍙戝唴缃瘝搴撳悕绉颁慨澶?| Codex1(Dev) |
| 2026-05-12 16:29 | 寮€鍙戝畬鎴愶細淇敼 `floatvocab/db.py`锛屽湪 `tests/test_multilingual_schema.py` 澧炲姞鏂板簱銆佹棫搴撱€侀噸澶嶈瘝搴撳悕杩佺Щ娴嬭瘯锛屾彁浜?Codex2 娴嬭瘯 | Codex1(Dev) |
| 2026-05-12 16:34 | 娴嬭瘯閫氳繃锛孴ICKET-02 瀹屾垚 | Codex2(Test) |

---

### 娴嬭瘯鎶ュ憡锛圕odex2锛?026-05-12 16:34锛?**缁撹**锛氶€氳繃

**鑷姩鍖栨祴璇?*锛?- 杩愯鍛戒护锛歚python -m pytest tests/test_multilingual_schema.py -v`
- 缁撴灉锛? passed
- 杩愯鍛戒护锛歚python -m pytest tests/ -v --ignore=tests/_tmp_ui_layout`
- 缁撴灉锛?17 passed, 1 warning
- 璇存槑锛歸arning 涓?pytest cache 鍐欏叆 `.pytest_cache` 琚?Windows 鎷掔粷璁块棶锛屼笉褰卞搷娴嬭瘯缁撴灉銆?
**楠屾敹鏍稿**锛?| 楠屾敹鏉＄洰 | 缁撴灉 | 澶囨敞 |
|----------|------|------|
| 鏂?DB 鍒濆鍖栧悗鍐呯疆璇嶅簱鏄剧ず鍙涓枃鍚?| 鉁?| 鏂板 `test_builtin_lexicon_uses_readable_chinese_name_on_fresh_database` |
| 鏃?DB 鍗囩骇鍚庝贡鐮佽瘝搴撹閲嶅懡鍚?| 鉁?| 鏂板 `test_legacy_builtin_lexicon_name_is_renamed_during_migration` |
| 宸插瓨鍦ㄨ鑼冨悕绉版椂涓嶄骇鐢熼噸澶嶈瘝搴?| 鉁?| 鏂板 `test_legacy_builtin_lexicon_is_merged_when_canonical_already_exists` |
| 鍏ㄩ噺娴嬭瘯閫氳繃 | 鉁?| 117 passed |

**Bug 鍒楄〃**锛氭棤銆?
---

## TICKET-03锛氭偓娴瘝鍗″崟璇嶅瓧浣撲紭鍖?
- **绫诲瀷**锛歶i
- **浼樺厛绾?*锛歮edium
- **状态**：DEV_TODO
- **当前负责人**：Codex1
- **鍏宠仈鍔熻兘**锛歝ore-flashcard, transparency-font-color
- **鍒涘缓鏃堕棿**锛?026-05-12 00:00

### 鐩爣
鎮诞绐楅噷鐨勫崟璇嶅瓧浣撳湪 Windows 涓婃纭覆鏌擄紝瑙嗚娓呮櫚鏄撹锛岄鏍间笌鏁翠綋璁捐淇濇寔涓€鑷达紱鍚屾椂淇 tkinter 绔敤鎴峰瓧鍙疯缃笉鐢熸晥鐨?bug銆?
### 楠屾敹鏍囧噯
- [ ] Electron 鎮诞璇嶅崱鐨勫崟璇嶅瓧浣撳湪 Windows 涓婃覆鏌撲负 Inter锛堣€岄潪绯荤粺闄嶇骇瀛椾綋锛?- [ ] 鍗曡瘝瀛楁瘝闂磋窛瑙嗚鑷劧锛屼笉鍑虹幇杩囩揣鎴栬繃瀹?- [ ] tkinter 鎮诞绐楀崟璇嶅ぇ灏忚窡闅忕敤鎴枫€屽瓧鍙枫€嶈缃彉鍖栵紙璁?26 鏄?26锛岃 36 鏄?36锛?- [ ] 瑙嗚鏁堟灉锛氭闈㈠崟璇嶅ぇ鑰屾竻鏅帮紝缈婚潰鍚庨噴涔夊瓧鍙峰眰绾у垎鏄?
### UI 璁捐瑕佹眰
#### Electron 绔紙`electron/src/styles.css`锛?褰撳墠闂锛?- `.floating-study-card` 鍜?`.floating-word` 鐨勫瓧浣撴棌涓?`-apple-system, "SF Pro Display", "Helvetica Neue"`锛學indows 鏃犺繖浜涘瓧浣擄紝浼氶檷绾у埌娴忚鍣ㄩ粯璁ゅ瓧浣?- `letter-spacing: -2px` 鍦?46px 澶у瓧涓嬭繃浜庣揣缂?- 浣?`styles.css` 椤堕儴宸茬粡 import 浜?`Inter`锛屼富鐣岄潰涔熷湪鐢?
璁捐鏂瑰悜锛堜緵 Claude2 璇勫锛夛細
- 瀛椾綋鏃忔敼涓?`"Inter", system-ui, sans-serif`锛屼笌鏁翠綋椋庢牸缁熶竴
- `letter-spacing` 璋冩暣鍒版帴杩?0 鎴?`-0.5px`锛屼繚鎸佽嚜鐒跺瓧璺?- 瀛楀彿 46px 鏄惁鍚堥€傦紝璇?Claude2 缁欏嚭鎰忚

#### tkinter 绔紙`app.py`锛?褰撳墠 bug锛歔`app.py:546-549`](app.py)
```python
font_size = int(plan["font_size"])   # 璇讳簡鐢ㄦ埛璁剧疆锛堝 26锛?word_font_size = 48                  # 涓嬩竴琛岀洿鎺ョ‖瑕嗙洊锛岀敤鎴疯缃け鏁?```
淇鏂瑰悜锛歚word_font_size` 搴旂敱 `font_size` 琛嶇敓锛堝 `word_font_size = max(28, font_size + 10)` 鎴栫洿鎺ヤ娇鐢?`font_size * 1.5`锛夛紝鍏蜂綋姣斾緥璇?Claude2 缁欏嚭鎰忚銆?
---

### 娴佺▼璁板綍

| 鏃堕棿 | 鎿嶄綔 | 璐熻矗浜?|
|------|------|--------|
| 2026-05-12 00:00 | 鍒涘缓 ticket锛岄€氭鍙戠幇涓ゅ瀛椾綋闂 | Claude1(PM) |
| 2026-05-12 00:00 | UI 璇勫閫氳繃锛岄檮瀹炵幇瑙勮寖锛圛nter瀛椾綋銆?2px銆乴etter-spacing -0.5px锛泃kinter word_font_size = max(30, font_size+16)锛?| Claude2(UI) |
| 2026-05-12 16:35 | 寮€濮嬪紑鍙戞偓娴瘝鍗″瓧浣撲紭鍖?| Codex1(Dev) |
| 2026-05-12 16:44 | 寮€鍙戝畬鎴愶細淇敼 `electron/src/styles.css`銆乣app.py`锛屾柊澧?UI 鍥炲綊娴嬭瘯骞堕€氳繃鍏ㄩ噺娴嬭瘯锛屾彁浜?Codex2 娴嬭瘯 | Codex1(Dev) |
| 2026-05-12 16:48 | 测试通过，推给 Claude2 做 UI 验收 | Codex2(Test) |
| 2026-05-12 16:55 | UI 验收**未通过**：`.floating-study-card`（L59）和 `.floating-action-button`（L265）仍使用 Apple 字体栈，退回 DEV_TODO 交 Codex1 补改 | Claude2(UI) |

---

### 测试报告（Codex2，2026-05-12 16:48）
**结论**：通过，已进入 UI_ACCEPTANCE

**自动化测试**：
- 运行命令：`python -m pytest tests/test_ui_layout.py::AppLayoutTests::test_electron_floating_word_uses_inter_and_natural_tracking tests/test_ui_layout.py::AppLayoutTests::test_floating_window_word_font_size_follows_user_setting tests/test_ui_layout.py::AppLayoutTests::test_floating_window_uses_smaller_title_font_for_long_meaning_when_flipped -v`
- 结果：3 passed
- 运行命令：`npm run build`（electron）
- 结果：通过
- 运行命令：`python -m pytest tests/ -v --ignore=tests/_tmp_ui_layout`
- 结果：117 passed, 2 failed, 1 warning
- 失败说明：两个失败均发生在 `tk.Tk()` 初始化阶段，错误为本机 Anaconda Tk 缺少 `ttk/button.tcl`，未进入 FloatVocab 业务逻辑；同一代码在 Codex1 阶段刚完成全量复跑为 119 passed。该环境问题与 TICKET-03 的 CSS 字体、字号派生逻辑无关；本 ticket 的新增断言已单独通过。

**手工/验收核对**：
| 验收条目 | 结果 | 备注 |
|----------|------|------|
| Electron 悬浮词卡单词字体使用 Inter | ✅ | CSS 断言覆盖 `.floating-word` |
| 单词字距自然，不过紧 | ✅ | CSS 断言覆盖 `letter-spacing: -0.5px` |
| tkinter 悬浮窗字号跟随用户设置 | ✅ | `font_size=26 -> 42`，`font_size=36 -> 52` |
| 正面单词大而清晰，翻面层级保留 | ✅ | 长释义翻面回归测试通过；最终视觉交给 Claude2 UI 验收 |

**Bug 列表**：无与本 ticket 相关的 bug。


---

## 宸插畬鎴?Tickets

> 鏆傛棤銆?
---

## Ticket 妯℃澘

```markdown
## TICKET-[缂栧彿]锛歔绠€鐭爣棰榏

- **绫诲瀷**锛歶i / non-ui
- **浼樺厛绾?*锛歨igh / medium / low  
- **鐘舵€?*锛歅M_DRAFT
- **褰撳墠璐熻矗浜?*锛欳laude1
- **鍏宠仈鍔熻兘**锛歔feature_list.json 涓殑 id]
- **鍒涘缓鏃堕棿**锛歒YYY-MM-DD HH:MM

### 鐩爣
[涓€鍙ヨ瘽璇存竻妤氳鍋氫粈涔堬紝鐢ㄦ埛鑳芥劅鐭ュ埌浠€涔堝彉鍖朷

### 楠屾敹鏍囧噯
- [ ] 鏉′欢1
- [ ] 鏉′欢2

### UI 璁捐瑕佹眰锛堜粎 ui 绫诲瀷濉啓锛?[鎻忚堪浜や簰閫昏緫銆佽瑙夐鏍笺€佺害鏉熸潯浠讹紝鍙傜収 FloatVocab 璁捐鍩哄噯]

---

### 娴佺▼璁板綍

| 鏃堕棿 | 鎿嶄綔 | 璐熻矗浜?|
|------|------|--------|
| YYYY-MM-DD HH:MM | 鍒涘缓 ticket | Claude1 |

[鍦ㄦ杩藉姞鍚勮鑹茬殑璇勫鎰忚銆佹祴璇曟姤鍛娿€侀獙鏀剁粨璁篯
```
