# WikipediaPehoejiDataQuality

Source dump: `zh_min_nanwiki-20261001-all-titles-in-ns0.gz`

## Counts

|  | count |
|---|---|
| Namespace-0 titles in dump | 679,227 |
| Titles kept (contain Pe̍h-ōe-jī) | 293,009 |
| Titles dropped | 386,218 |
| Rows merged into another (same text, same article) | 3,644 |
| Rows published | 289,365 |
| … whose text was corrected | 210 |
| … with a multi-tone word | 1,448 |
| … with a caron on a tone-bearing letter | 105 |

Namespace-0 titles include redirects. The dump does not mark them, so
both a redirect and its target are kept — e.g. `'Amran-séng`,
`'Amran Séng` and `'Amran séng` are all present. Only rows whose
corrected text is identical and that lead to the same article are
merged, keeping the article's own row: `10 goe̍h 10 ji̍t (kūle̍k)` and
`10 goe̍h 10 ji̍t (kū-le̍k)` are one row. Every merge is listed in
`WikipediaPehoejiDataQuality.json`.

## 1. Title text — corrections

`PojUnicode` is the title made as good as possible for finding by
Pe̍h-ōe-jī; `LaigoanBangchi` keeps the exact page. `_` is a space
(`Tâi-oân-koān (1684~1887)`), and these corrections were made:

| correction | rows |
|---|---|
| full-width punctuation → ASCII | 5 |
| o· → o͘ | 45 |
| ı̍ / ἰ → i̍ | 1 |
| non-breaking hyphen → - | 1 |
| space before ( | 6 |
| hyphens between run-together syllables | 156 |

Run-together syllables are split only into a hyphenated form that
Wikipedia's own titles use somewhere, so a foreign name that happens to
parse as syllables (`Hélène`) is never split, and that form decides
between two parses (`sîtāi` → `sî-tāi`, not `sît-āi`).

| written | `PojUnicode` | rows |
|---|---|---|
| `Tâioân` | `Tâi-oân` | 25 |
| `Kiōngsántóng` | `Kiōng-sán-tóng` | 21 |
| `Choânkok` | `Choân-kok` | 19 |
| `Tāihoē` | `Tāi-hoē` | 19 |
| `Tāipiáu` | `Tāi-piáu` | 19 |
| `Konghn̂g` | `Kong-hn̂g` | 9 |
| `Hōesiā` | `Hōe-siā` | 8 |
| `Iláng` | `I-láng` | 5 |
| `Tāiha̍k` | `Tāi-ha̍k` | 4 |
| `Bûchīn` | `Bû-chīn` | 3 |
| `Hôlân` | `Hô-lân` | 3 |
| `Kokli̍p` | `Kok-li̍p` | 3 |
| `tētāng` | `tē-tāng` | 3 |
| `Bânlâm` | `Bân-lâm` | 2 |
| `Bôngkó͘` | `Bông-kó͘` | 2 |
| `Chiàncheng` | `Chiàn-cheng` | 2 |
| `Chiùchoā` | `Chiù-choā` | 2 |
| `Choânthé` | `Choân-thé` | 2 |
| `Gînhâng` | `Gîn-hâng` | 2 |
| `Hoēgī` | `Hoē-gī` | 2 |
| `Hunlân` | `Hun-lân` | 2 |
| `Háiiûⁿ` | `Hái-iûⁿ` | 2 |
| `Ji̍tpún` | `Ji̍t-pún` | 2 |
| `Kiōngsán` | `Kiōng-sán` | 2 |
| `Kòetiû` | `Kòe-tiû` | 2 |
| `Málâisea` | `Má-lâi-se-a` | 2 |
| `Pholân` | `Pho-lân` | 2 |
| `Pûiliāu` | `Pûi-liāu` | 2 |
| `Sepangâ` | `Se-pan-gâ` | 2 |
| `Sinpakchhī` | `Sin-pak-chhī` | 2 |
| `Siōnggoân` | `Siōng-goân` | 2 |
| `Soánkí` | `Soán-kí` | 2 |
| `konghn̂g` | `kong-hn̂g` | 2 |
| `Ìntō͘` | `Ìn-tō͘` | 2 |
| `Úioânhoē` | `Úi-oân-hoē` | 2 |
| `Abó` | `A-bó` | 1 |
| `Aiki̍p` | `Ai-ki̍p` | 1 |
| `Auiông` | `Au-iông` | 1 |
| `Bu̍tsán` | `Bu̍t-sán` | 1 |
| `Bíhó` | `Bí-hó` | 1 |
| `Bíkok` | `Bí-kok` | 1 |
| `Bînchiòng` | `Bîn-chiòng` | 1 |
| `Bînkok` | `Bîn-kok` | 1 |
| `Bûnhoà` | `Bûn-hoà` | 1 |
| `Chesī` | `Che-sī` | 1 |
| `Chionghòachhī` | `Chiong-hòa-chhī` | 1 |
| `Chiâⁿsi̍tê` | `Chiâⁿ-si̍t-ê` | 1 |
| `Chêngpò` | `Chêng-pò` | 1 |
| `Chóngtokhú` | `Chóng-tok-hú` | 1 |
| `Chúgī` | `Chú-gī` | 1 |

155 distinct words; the first 50 are shown. Every corrected row is in `WikipediaPehoejiDataQuality.json`.

## 2. Multi-tone words — `PojInput` left unconverted

A Pe̍h-ōe-jī syllable carries at most one tone mark. These words carry
two or more and could not be split into syllables: mostly foreign names
(`Pyrénées`, `Józefów`), kept because another part of their title is a
syllable, and a few run-together syllables no title writes hyphenated.
There is no single tone number to append, so the word is copied into
`PojInput` as-is rather than guessed at.

| word | titles |
|---|---|
| `Pyrénées` | 297 |
| `Józefów` | 64 |
| `Mézières` | 42 |
| `Pińczów` | 39 |
| `Évêque` | 39 |
| `Sălăuța` | 28 |
| `Bârgău` | 12 |
| `Bălăneasa` | 12 |
| `Vézère` | 12 |
| `Fântâna` | 11 |
| `Pévèle` | 11 |
| `Pârâul` | 10 |
| `Adâncă` | 9 |
| `Célé` | 9 |
| `Gârbău` | 9 |
| `Bângăleasa` | 8 |
| `Fântânele` | 8 |
| `Léré` | 8 |
| `Părău` | 8 |
| `Văsălatu` | 8 |
| `Brûlée` | 6 |
| `Chérencé` | 6 |
| `Céré` | 6 |
| `Geamărtălui` | 6 |
| `Guérétois` | 6 |
| `Hălmăgel` | 6 |
| `Médéa` | 6 |
| `Strâmbă` | 6 |
| `Sălătruc` | 6 |
| `Tărcăița` | 6 |
| `Brûlé` | 5 |
| `Cléré` | 5 |
| `Dénezé` | 5 |
| `Guémené` | 5 |
| `Gârbăul` | 5 |
| `Hélène` | 5 |
| `Ménétréol` | 5 |
| `Năsăud` | 5 |
| `Sévérac` | 5 |
| `Zagórów` | 5 |
| `Épeigné` | 5 |
| `Bârsănești` | 4 |
| `Căldărești` | 4 |
| `Călmățui` | 4 |
| `Călugărului` | 4 |
| `Călăraşi` | 4 |
| `Căpățâna` | 4 |
| `Cătăuți` | 4 |
| `Jérôme` | 4 |
| `Józefków` | 4 |

397 distinct multi-tone words; the 50 most frequent are shown. The full list is in `WikipediaPehoejiDataQuality.json`.

### Caron on a tone-bearing letter — left as written

A caron (`ǔ`, `ě`) is not read as a tone mark, as in KonvertToPOJ: no
number is appended for it. Most are Czech and Slovak names (`Moravě`);
a few are Taigi written with a tone-6 caron (`Diô-jiǔ-oē`).

`Andělská Hora (Karlovy Vary)`, `Andělská Hora (Moravia-Silesia)`, `Bezděčí u Trnávky`, `Brno-město Koān`, `Brodek u Prostějova`, `Buková u Příbramě`, `Běleč (Lâm Bohemia)`, `Běleč (Lâm Moravia)`, `Běleč (Tiong Bohemia)`, `Bělušice (Tiong Bohemia)`, `Bělá u Jevíčka`, `Chlum (Plzeň-jih)`, `Chlum u Třeboně`, `Diô-jiǔ-oē`, `Dobronice u Bechyně`, `Dobrá Voda u Českých Budějovic`, `Dolce (Plzeň-jih)`, `Dětkovice (Lâm Moravia)`, `Dětřichov u Moravské Třebové`, `Děčín Koān`, `Hostouň (Tiong Bohemia)`, `Hořice na Šumavě`, `Hradiště (Plzeň-jih)`, `Hradiště (Tiong Bohemia)`, `Ivaň (Lâm Moravia)`, `Jakubov u Moravských Budějovic`, `Jarov (Plzeň-jih)`, `Jiřice u Moravských Budějovic`, `Kaliště (Tiong Bohemia)`, `Kněževes (Lâm Moravia)`, `Kněžice (Tiong Bohemia)`, `Kostelec u Heřmanova Městce`, `Kout na Šumavě`, `Kroměříž Koān`, `Leština u Světlé`, `Lhota u Příbramě`, `Litoměřice Koān`, `Loděnice (Lâm Moravia)`, `Loděnice (Tiong Bohemia)`, `Mladějov na Moravě`, `Mutěnice (Lâm Bohemia)`, `Mutěnice (Lâm Moravia)`, `Mělník Koān`, `Nezdice na Šumavě`, `Nová Ves (Plzeň-jih)`, `Nová Ves u Chotěboře`, `Nová Ves u Nového Města na Moravě`, `Nová Ves u Světlé`, `Nové Město na Moravě`, `Náměšť na Hané`

105 titles; the first 50 are shown.

## 3. English, Chinese and Japanese titles — `EngBun`, `HoaBun`, `JitBun`

From the interlanguage links of the same dump run (`langlinks`, which
includes Wikidata sitelinks). A title takes the links of the first page
along its redirect chain that has links of its own: usually the article
it leads to, but a redirect that Wikidata attaches to an item of its own
keeps its own (`Bart Simpson`, a redirect to `Nancy Cartwright`, keeps en
`Bart Simpson`). Each linked title is then looked up on its wiki:
redirects there are followed, zh titles are given in the zh-tw variant,
and a link to a section, a missing page or a page that is not an
article is dropped.

|  | count |
|---|---|
| Rows with at least one title | 268,096 |
| … of which the Pe̍h-ōe-jī title is a redirect | 108,079 |
| … of which it is a redirect with interlanguage links of its own, used | 18 |
| Rows with no title | 21,269 |
| Linked titles answered from an earlier run (`--resolved`) | 274,284 |

### Rows with no title, and why

|  | rows |
|---|---|
| No interlanguage links at all | 2,609 |
| Interlanguage links, but none to en, zh or ja | 16,027 |
| Every en/zh/ja link dropped (per-language table below) | 53 |
| A redirect to a section | 2,029 |
| A redirect out of the article namespace | 436 |
| A broken redirect | 115 |

A redirect to a section (`Jı̍t-pún sî-tāi` → `Tâi-oân le̍k-sú#Jı̍t-pún sî-tāi`,
`48 nî chhut-sì` → `48 nî#Chhut-sì`) is given no titles: the article's
links name the whole article (`History of Taiwan`, `AD 48`), not the
section the title names. Nor is a redirect out of the article namespace
(`0 nî-tāi chhut-sì` → `Category:0 nî-tāi chhut-sì`).

|  | column | rows | linked page redirected or converted | link to a section — dropped | linked page missing — dropped | linked page not an article — dropped |
|---|---|---|---|---|---|---|
| English | `EngBun` | 249,608 | 12,692 | 7 | 0 | 1 |
| Chinese (zh-tw) | `HoaBun` | 156,880 | 70,458 | 36 | 19 | 20 |
| Japanese | `JitBun` | 80,005 | 280 | 0 | 0 | 23 |

### English: linked title → title of the page it lands on

| linked | `EngBun` |
|---|---|
| `1402 Eri` | `List of minor planets: 1001–2000` |
| `1450 in Norway` | `15th century in Norway` |
| `1455 in Norway` | `15th century in Norway` |
| `1476 in Norway` | `15th century in Norway` |
| `1483 in Norway` | `15th century in Norway` |
| `1488 Aura` | `List of minor planets: 1001–2000` |
| `1496 in Norway` | `15th century in Norway` |
| `1502 in Norway` | `16th century in Norway` |
| `1503 in Norway` | `16th century in Norway` |
| `1504 in Norway` | `16th century in Norway` |
| `1505 in Norway` | `16th century in Norway` |
| `1514 in Norway` | `16th century in Norway` |
| `1523 in Norway` | `16th century in Norway` |
| `1535 in Norway` | `16th century in Norway` |
| `1536 in Norway` | `16th century in Norway` |
| `1537 in Norway` | `16th century in Norway` |
| `1538 in Norway` | `16th century in Norway` |
| `1539 in Norway` | `16th century in Norway` |
| `1545 in Norway` | `16th century in Norway` |
| `1548 in Norway` | `16th century in Norway` |
| `1555 in Norway` | `16th century in Norway` |
| `1557 in Norway` | `16th century in Norway` |
| `1558 in Norway` | `16th century in Norway` |
| `1561 in Norway` | `16th century in Norway` |
| `1563 in Norway` | `16th century in Norway` |
| `1564 in Norway` | `16th century in Norway` |
| `1567 in Norway` | `16th century in Norway` |
| `1570 in Norway` | `16th century in Norway` |
| `1572 in Norway` | `16th century in Norway` |
| `1575 in Norway` | `16th century in Norway` |
| `1576 in Norway` | `16th century in Norway` |
| `1577 in Norway` | `16th century in Norway` |
| `1578 in Norway` | `16th century in Norway` |
| `1579 in Norway` | `16th century in Norway` |
| `1580 in Norway` | `16th century in Norway` |
| `1581 in Norway` | `16th century in Norway` |
| `1588 in Norway` | `16th century in Norway` |
| `1589 in Norway` | `16th century in Norway` |
| `1590 in Norway` | `16th century in Norway` |
| `1591 in Norway` | `16th century in Norway` |
| `1592 in Norway` | `16th century in Norway` |
| `1595 in Norway` | `16th century in Norway` |
| `1600 in Norway` | `16th century in Norway` |
| `1666 van Gent` | `List of minor planets: 1001–2000` |
| `1744 Harriet` | `List of minor planets: 1001–2000` |
| `1752 van Herk` | `List of minor planets: 1001–2000` |
| `1802 Zhang Heng` | `List of minor planets: 1001–2000` |
| `1885 Herero` | `List of minor planets: 1001–2000` |
| `1888 Zu Chong-Zhi` | `List of minor planets: 1001–2000` |
| `1895 Larink` | `List of minor planets: 1001–2000` |

5,885 distinct titles; the first 50 are shown.

### Chinese (zh-tw): linked title → title of the page it lands on

| linked | `HoaBun` |
|---|---|
| `09VI型核潜艇` | `09VI型核潛艇` |
| `1.5微米制程` | `1.5微米製程` |
| `101号弗吉尼亚州州道` | `101號維吉尼亞州州道` |
| `105号州际公路 (俄勒冈州)` | `105號州際公路 (俄勒岡州)` |
| `10世纪` | `10世紀` |
| `10号弗吉尼亚州州道` | `10號維吉尼亞州州道` |
| `10号染色体` | `10號染色體` |
| `10号科罗拉多州州道` | `10號科羅拉多州州道` |
| `10号阿肯色州州道` | `10號阿肯色州州道` |
| `10微米制程` | `10微米製程` |
| `10纳米制程` | `10納米製程` |
| `111号加利福尼亚州州道` | `111號加利福尼亞州州道` |
| `118号宾夕法尼亚州州道` | `118號賓夕法尼亞州州道` |
| `11世纪` | `11世紀` |
| `11号密苏里州州道` | `11號密蘇里州州道` |
| `11号科罗拉多州州道` | `11號科羅拉多州州道` |
| `11号阿肯色州州道` | `11號阿肯色州州道` |
| `121号加利福尼亚州州道` | `121號加利福尼亞州州道` |
| `121号纽约州州道` | `121號紐約州州道` |
| `125号加利福尼亚州州道` | `125號加利福尼亞州州道` |
| `128号犹他州州道` | `128號猶他州州道` |
| `12世纪` | `12世紀` |
| `12号加利福尼亚州州道` | `12號加利福尼亞州州道` |
| `12号密西西比州州道` | `12號密西西比州州道` |
| `12号染色体` | `12號染色體` |
| `12号科罗拉多州州道` | `12號科羅拉多州州道` |
| `12号阿肯色州州道` | `12號阿肯色州州道` |
| `130号德克萨斯州州道` | `130號德克薩斯州州道` |
| `136号宾夕法尼亚州州道` | `136號賓夕法尼亞州州道` |
| `139号阿肯色州州道` | `139號阿肯色州州道` |
| `13世纪` | `13世紀` |
| `13号加利福尼亚州州道` | `13號加利福尼亞州州道` |
| `13号密西西比州州道` | `13號密西西比州州道` |
| `13号弗吉尼亚州州道` | `13號維吉尼亞州州道` |
| `13号染色体` | `13號染色體` |
| `13号科罗拉多州州道` | `13號科羅拉多州州道` |
| `1499年国家领导人列表` | `1499年國家領導人列表` |
| `14世纪` | `14世紀` |
| `14号加利福尼亚州州道` | `14號加利福尼亞州州道` |
| `14号华盛顿州州道` | `14號華盛頓州州道` |
| `14号密西西比州州道` | `14號密西西比州州道` |
| `14号弗吉尼亚州州道` | `14號維吉尼亞州州道` |
| `14号染色体` | `14號染色體` |
| `14号科罗拉多州州道` | `14號科羅拉多州州道` |
| `14号阿肯色州州道` | `14號阿肯色州州道` |
| `14纳米制程` | `14納米製程` |
| `1500年国家领导人列表` | `1500年國家領導人列表` |
| `1501年国家领导人列表` | `1501年國家領導人列表` |
| `1502年国家领导人列表` | `1502年國家領導人列表` |
| `1503年国家领导人列表` | `1503年國家領導人列表` |

34,380 distinct titles; the first 50 are shown.

### Japanese: linked title → title of the page it lands on

| linked | `JitBun` |
|---|---|
| `1884年の野球` | `1884年のメジャーリーグベースボール` |
| `2060年` | `2060年代` |
| `2061年` | `2060年代` |
| `2062年` | `2060年代` |
| `2063年` | `2060年代` |
| `2064年` | `2060年代` |
| `2065年` | `2060年代` |
| `2066年` | `2060年代` |
| `2067年` | `2060年代` |
| `2068年` | `2060年代` |
| `2069年` | `2060年代` |
| `2070年` | `2070年代` |
| `2071年` | `2070年代` |
| `2072年` | `2070年代` |
| `2073年` | `2070年代` |
| `2074年` | `2070年代` |
| `2075年` | `2070年代` |
| `2076年` | `2070年代` |
| `2077年` | `2070年代` |
| `2078年` | `2070年代` |
| `2079年` | `2070年代` |
| `2080年` | `2080年代` |
| `2081年` | `2080年代` |
| `2082年` | `2080年代` |
| `2083年` | `2080年代` |
| `2084年` | `2080年代` |
| `2085年` | `2080年代` |
| `2086年` | `2080年代` |
| `2087年` | `2080年代` |
| `2088年` | `2080年代` |
| `2089年` | `2080年代` |
| `2090年` | `2090年代` |
| `2091年` | `2090年代` |
| `2092年` | `2090年代` |
| `2093年` | `2090年代` |
| `2094年` | `2090年代` |
| `2095年` | `2090年代` |
| `2096年` | `2090年代` |
| `2097年` | `2090年代` |
| `2098年` | `2090年代` |
| `2099年` | `2090年代` |
| `IATA空港コード` | `空港コード` |
| `おねえさん` | `姉` |
| `と小鎌` | `鎌` |
| `アジア大陸` | `アジア` |
| `アメリカ合衆国ドルの硬貨` | `アメリカ合衆国ドル` |
| `アルカリ金属` | `第1族元素` |
| `ウツドン` | `ポケモンの一覧 (52-101)` |
| `エイジ オブ エンパイア: ライズ オブ ローマ` | `エイジ オブ エンパイア` |
| `エホバ` | `ヤハウェ` |

154 distinct titles; the first 50 are shown.

### English: link names a section

`Berry#Modified berries`, `Folk music#Traditional folk music`, `Han Dynasty#Western Han`, `List of World Heritage Sites#Asia`

4 distinct titles.

### Chinese (zh-tw): link names a section

`ㄅ#相關變體`, `ㄇ#相關變體`, `ㄈ#相關變體`, `ㄉ#相關變體`, `ㄋ#相關變體`, `ㄌ#相關變體`, `ㄍ#相關變體`, `ㄏ#相關變體`, `ㄐ#相關變體`, `ㄒ#相關變體`, `ㄗ#相關變體`, `ㄚ#相關變體`, `ㄛ#相關變體`, `ㄜ#相關變體`, `ㄝ#相關變體`, `ㄞ#相關變體`, `ㄠ#相關變體`, `ㄥ#相關變體`, `ㄧ#相關變體`, `ㄨ#相關變體`, `ㄫ#相關變體`, `蓮池潭#龍虎塔`

22 distinct titles.

### English: linked page is not an article

| linked | lands on |
|---|---|
| `Template:Governorates of Kuwait` | `Template:Governorates of Kuwait` |

1 distinct title.

### Chinese (zh-tw): linked page is not an article

| linked | lands on |
|---|---|
| `Category:1759年科學` | `分類:1759年科學` |
| `Category:2065年` | `分類:2065年` |
| `Template:科威特行政區劃` | `模板:科威特行政區劃` |
| `Wikipedia:吳語維基百科` | `維基百科:吳語維基百科` |
| `Wikipedia:客家語維基百科` | `維基百科:客家語維基百科` |
| `Wikipedia:粵文維基百科` | `維基百科:粵文維基百科` |
| `Wikipedia:贛語維基百科` | `維基百科:贛語維基百科` |
| `Wikipedia:閩東語維基百科` | `維基百科:閩東語維基百科` |

8 distinct titles.

### Japanese: linked page is not an article

| linked | lands on |
|---|---|
| `Category:1895年のフランス` | `Category:1895年のフランス` |
| `Category:1987年のスウェーデン` | `Category:1987年のスウェーデン` |
| `Portal:最近の出来事/2010年10月` | `Portal:最近の出来事/2010年10月` |
| `Portal:最近の出来事/2010年11月` | `Portal:最近の出来事/2010年11月` |
| `Portal:最近の出来事/2010年12月` | `Portal:最近の出来事/2010年12月` |
| `Portal:最近の出来事/2010年6月` | `Portal:最近の出来事/2010年6月` |
| `Portal:最近の出来事/2010年7月` | `Portal:最近の出来事/2010年7月` |
| `Portal:最近の出来事/2010年8月` | `Portal:最近の出来事/2010年8月` |
| `Portal:最近の出来事/2010年9月` | `Portal:最近の出来事/2010年9月` |
| `Portal:最近の出来事/2011年10月` | `Portal:最近の出来事/2011年10月` |
| `Portal:最近の出来事/2011年11月` | `Portal:最近の出来事/2011年11月` |
| `Portal:最近の出来事/2011年12月` | `Portal:最近の出来事/2011年12月` |
| `Portal:最近の出来事/2011年1月` | `Portal:最近の出来事/2011年1月` |
| `Portal:最近の出来事/2011年2月` | `Portal:最近の出来事/2011年2月` |
| `Portal:最近の出来事/2011年3月` | `Portal:最近の出来事/2011年3月` |
| `Portal:最近の出来事/2011年4月` | `Portal:最近の出来事/2011年4月` |
| `Portal:最近の出来事/2011年5月` | `Portal:最近の出来事/2011年5月` |
| `Portal:最近の出来事/2011年6月` | `Portal:最近の出来事/2011年6月` |
| `Portal:最近の出来事/2011年7月` | `Portal:最近の出来事/2011年7月` |
| `Portal:最近の出来事/2011年8月` | `Portal:最近の出来事/2011年8月` |
| `Portal:最近の出来事/2011年9月` | `Portal:最近の出来事/2011年9月` |
| `Template:クウェートの県` | `Template:クウェートの県` |
| `Wikipedia:一覧の一覧` | `Wikipedia:一覧の一覧` |

23 distinct titles.

### Chinese (zh-tw): linked page does not exist

`亞布盧奇涅 (洛佐瓦區)`, `亞歷山德里夫卡 (克希奇夫卡市鎮)`, `亞歷山德里夫卡 (納塔利涅市鎮)`, `列夫基夫齊 (圖利欽區)`, `別列斯特基 (佩爾沃邁西基區)`, `卡米亞納巴爾卡 (佩爾沃邁斯基區)`, `安德里伊夫卡 (克希奇夫卡市镇)`, `戈爾季伊夫卡 (利波韋茨區)`, `戈羅季謝 (喬爾努希區)`, `扎哈里夫西克 (洛佐瓦區)`, `斯特魯京卡 (利波韋茨區)`, `格拉巴里夫卡 (皮先卡區)`, `波利奧瓦斯洛比德卡 (季夫里夫區)`, `澤列尼夫卡 (佩爾沃邁西基區)`, `科扎奇基 (列季奇夫區)`, `維索克 (佩爾沃邁西基區)`, `韋德梅季夫卡 (米羅諾夫卡區)`, `馬斯利夫卡 (佩爾沃邁西基區)`, `魯季夫卡 (普里盧基區)`

19 distinct titles.

Full lists are in `WikipediaPehoejiDataQuality.json`.
