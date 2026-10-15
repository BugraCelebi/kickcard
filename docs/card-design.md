# Kart Tasarım Spesifikasyonu

Durum: taslak, 2026-10-12. Kaynak: "Kickcard Kart Tasarımı" kanvasının 3. sırası (Sarı Bıyık, Krom Kollu Asi, Gölge Yürüyüşçüsü). 2026-10-12'de güncel oyun kararlarına göre revize edildi: üç sabit tip, beş nadirlik, keyword sözlüğü, imza yeteneği, token ve mini kart. 2026-10-13: nadirlik renkleri klasik sisteme (gri, yeşil, mavi, mor, turuncu) geçti, tip renkleri buna göre değişti (Güç kırmızı, Hile pembe, Çeviklik sarı). 2026-10-15: tip renkleri onaylandı, ilk efsanevinin imza yeteneği Diriliş seçildi.

Bu doküman overlay'de gösterilecek kartın görsel spesifikasyonudur. Oyun motorunu etkilemez; motor yalnızca `type`, `rarity`, statlar ve keyword verir, görünüm tamamen overlay katmanında çözülür. Kural ve sabitler için kaynak `docs/plan.md` ve `.claude/rules/rules-game-engine.md`'dir; bu dosya onlarla çelişirse onlar kazanır.

## 1. Temel ilke: üç bağımsız katman

| Katman | Gösterildiği yer | Sete göre değişir mi |
|---|---|---|
| Nadirlik | Kenar metali + foil seviyesi | Hayır |
| Tip | Tip taşı rengi ve simgesi, tip adı, vurgu çizgisi, keyword etiketi | Hayır |
| Set | Görsel dili, alt panel malzemesi, set sembolü | Evet |

Kartın iskeleti (bölgelerin yeri ve boyutu) bütün setlerde aynıdır. Setler mekaniği paylaşır ve aynı destede karışabilir; bu yüzden tip adı ve simgesi her sette aynı kalır. Sete özel olan yalnızca kart adı, görsel, lore ve malzemedir.

## 2. Ölçüler ve yerleşim

Tüm değerler px, 1x ölçekte.

| Öğe | Değer |
|---|---|
| Kart | 360 x 504 (63:88), köşe 18, gölge `0 12px 30px rgba(0,0,0,0.5)` |
| Kenar (rim) | 7, nadirlik metali |
| İç kart | 346 x 490, köşe 12, `inset 0 0 0 1px rgba(0,0,0,0.6)` |
| Görsel alanı | y 0 ile 340 arası, tam genişlik |
| İç çerçeve çizgisi | sol/sağ 12, üst 14, yükseklik 300, kalınlık 1.5, alt kenarı yok, köşe 9. Maske: %55'te tam, %85'te kayboluyor |
| Geçiş katmanı (veil) | y 226, yükseklik 120, z 3. Set zemin rengine: %0 şeffaf, %35'te 0.4, %62'de 0.9, %80'de tam |
| İsim gölgesi (scrim) | y 262, 300 x 82, z 3. Yatay: 0.72, %55'te 0.5, sonra 0. Dikey maske: üst ve alt %28 soluyor |
| Enerji taşı | sol üst, 12/12, 46 çap |
| Tip taşı | sağ üst, 12/12, 36 çap |
| Metin bloğu | y 276'dan stat satırının üstüne kadar, yan boşluk 16, z 4 |
| Stat satırı | yükseklik 44, alt boşluk 10, yan boşluk 12 |

## 3. Tipografi

Fontlar: Barlow Condensed (500, 600, 700, 800) ve Source Serif 4 (400, 600, 400 italik), Google Fonts.

| Öğe | Font | Boyut | Ağırlık | Not |
|---|---|---|---|---|
| Kart adı | Barlow Condensed | 28 | 800 | line-height 1, gölge `0 1px 2px rgba(0,0,0,0.6), 0 2px 14px rgba(0,0,0,0.75)` |
| Tip satırı | Barlow Condensed | 14 | 700 | letter-spacing 1.6, örnek: `▲ GÜÇ · SIRADAN` (tip rengi + nadirlik rengi) |
| Keyword etiketi | Barlow Condensed | 13 | 700 | letter-spacing 1.5, padding 2 8, köşe 4, beyaz yazı, zemin tip rengi |
| Kural metni | Source Serif 4 | 13.5 | 400 | renk `#E7E9EE` (koyu zeminde) |
| Lore | Source Serif 4 | 12.5 | 400 italik | line-height 1.4, en fazla 2 satır |
| Enerji | Barlow Condensed | 26 | 800 | beyaz |
| Hasar / can | Barlow Condensed | 20 | 800 | beyaz |
| Set numarası | Barlow Condensed | 11.5 | 600 | letter-spacing 1.8, örnek: `KM · 030/030` |

## 4. Nadirlik

Oyunda beş nadirlik var. Sıralama ve renkler oyunlardaki klasik sistemle aynı: gri, yeşil, mavi, mor, turuncu. Nadirlik bulunabilirliği gösterir, gücü değil; bütün kartlar aynı bütçe formülüne uyar.

| | Sıradan | Sıra Dışı | Nadir | Destansı | Efsanevi |
|---|---|---|---|---|---|
| Motor değeri | `common` | `uncommon` | `rare` | `epic` | `legendary` |
| Renk ailesi | gri | yeşil | mavi | mor | turuncu |
| Kenar metali (135 derece gradyan) | `#2A2D33, #5E636C, #33373E, #6A707A, #2A2D33` | `#14401F, #4FC46B, #1F5F31, #9BEFB0, #174A26, #6FD98A` | `#102F66, #4A8DFF, #1A479A, #A9CBFF, #143B80, #6EA6FF` | `#33105E, #A35CFF, #4E1F8F, #DDB8FF, #3E1773, #B87CFF` | `#6E3205, #FF9F2E, #B35E12, #FFD7A0, #8F4609, #FFB04A` |
| Taş halkaları | `#8A9099` | `#5FD47D` | `#6EA6FF` | `#B87CFF` | `#FFA640` |
| Nadirlik yazısı | `#B9BDC4` | `#6FDC8B` | `#7EB0FF` | `#C08AFF` | `#FFA640` |
| Gökkuşağı kenar | yok | yok | yok | yok | var |
| Işık huzmesi | yok | yok | var | var | var |
| Alt holografik doku | yok | yok | var (0.09) | var (0.13) | var (0.09) |
| Taşan figür | yok | yok | yok | yok | opsiyonel (kesik PNG varsa) |

## 5. Tip

Tipler bütün setlerde ortaktır. Üçgen: **Güç > Hile > Çeviklik > Güç**. Avantajlı tip kart karta vuruşta +10 hasar verir; boş slota vuruşta tip bonusu yoktur.

| Simge | Motor değeri | Oyuncuya görünen ad | Taş rengi | Satır yazısı | Vurgu çizgisi | Keyword etiketi |
|---|---|---|---|---|---|---|
| ▲ | `POWER` | GÜÇ | `#D63A2F` (kırmızı) | `#FF7F73` | `#E5524A` | `#B02A22` |
| ● | `TRICK` | HİLE | `#C2338F` (pembe) | `#FF7FCB` | `#E04FAE` + `0 0 8px rgba(224,79,174,0.6)` | `#9E2373` |
| ◆ | `AGILITY` | ÇEVİKLİK | `#D9A400` (sarı) | `#FFD34D` | `#F2C230` | `#9E7700` |

- Tip renkleri nadirlik renklerinden (gri, yeşil, mavi, mor, turuncu) bilerek uzak tutuldu. Aynı renk ailesi hem kenarda hem taşta olursa kartın nadirliği ile tipi karışır.
- Akılda kalma cümleleri: kaba kuvvet hileyi ezer; hile çevik olanı tuzağa düşürür; çevik olan güçlüden kaçar.
- Çeviklik simgesi kare yerine eşkenar dörtgen (◆) önerildi: kare savunma çağrıştırıyordu, Çeviklik ise hız tipi. Onay bekliyor.
- Tip taşı: radyal gradyan, `circle at 35% 30%`, açık ton, tip rengi (%55), koyu ton (%100). İçinde 13 px beyaz SVG simge (üçgen, daire, eşkenar dörtgen).
- Vurgu çizgisi: tip satırının 6 px altında, 1.5 px, iki ucu %30'a kadar soluyor.
- Set tasarım rehberi (kural değil): Güç yüksek hasar ve maliyet; Çeviklik ucuz kartlar, Aşırı Yük, erken baskı; Hile keyword ve sinerji yoğun kartlar.

## 6. Keyword gösterimi

Keyword adı ve kural metni tek bir keyword sözlüğünden üretilir; kartlara elle yazılmaz. Buradaki metinler oyuncuya görünen kısa hatırlatma yazılarıdır; kuralın tam tanımı `.claude/rules/rules-game-engine.md`'dedir. `ARMOR` satırı görünüm içindir; verideki temsili (`ARMOR` + `keyword_value` ya da `ARMOR_X`) keyword sözlüğü adımında belirlenir. Bir keyword'ün değeri değişince bütün kartların metni kendiliğinden güncellenir. Kart başına en fazla 1 keyword.

| Motor değeri | Etiket | Kural metni (hatırlatma yazısı) |
|---|---|---|
| `FIRST_STRIKE` | İLK VURUŞ | Önce vurur. Rakip ölürse karşılık veremez. |
| `ARMOR` (değer 5/10/15) | ZIRH {X} | Gelen her vuruşu {X} azaltır. |
| `PIERCE` | DELİCİ | Hasarının yarısı doğrudan çekirdeğe gider. |
| `OVERLOAD` | AŞIRI YÜK | İlk turunda +20 hasar, sonra -10. |
| `HANDOFF` | AKTARIM | Ölünce sıradaki kartın +20 hasar ve +20 canla girer. |
| `LINK` | ZİNCİR | Önceki kartın aynı tipteyse +25 hasar. |
| `PROTOCOL` | PROTOKOL | Destendeki her aynı tip kart için +10 hasar (en fazla +40). |
| `SPAWN` | ÇAĞRI | Ölünce yerine 25/25 bir token gelir. |

- Keyword etiketi zemin rengi kartın tipinden gelir (bölüm 5).
- İmza yeteneği (yalnızca efsanevi): etiket `İMZA · {ad}` biçiminde, efsanevi turuncusu gradyan zemin (`#8F4609, #FFB04A, #B35E12`), koyu yazı `#2A1402`. Bkz. bölüm 12.
- Sinerji değerleri başlangıç değeridir; kart seti simülasyonundan sonra değişebilir. Değişirse sadece sözlük güncellenir.

## 7. Set malzemeleri

### Kanal Mimleri (`KM`)
- Zemin: `#121418`. Sembol: konuşma balonu.
- Görsel: arka planı silinmiş PNG. Figür yüksekliği 300, üstten 2, yatayda ortalı, z 2. İç çerçeve çizgisinin önüne taşar.
- Figür efekti: 2.5 px beyaz çıkartma konturu (dört yönlü `drop-shadow`) + `0 10px 12px rgba(30,0,20,0.5)`.
- Fon: `repeating-conic-gradient`, 8 derecelik dilimler, `#FF4D6D` / `#FF8A3D`, merkez %50/%52. Üstünde sıcak merkez ışıması ve kenar karartması.
- Nokta deseni: 7 px aralık, 1.1 px nokta, `rgba(60,0,30,0.28)`, yukarıdan aşağı belirginleşiyor.
- Kapsül ve set numarası rengi: [BELİRLENECEK] (öneri: kapsül `#0B0C0F`, kenar `#2F333B`, set numarası `#8B919B`).

### Neon Gece (`NG`)
- Zemin: `#0B0E1E`. Sembol: şimşek.
- Görsel: `object-fit: cover`, `object-position: 50% 30%`.
- Ton: mor-pembe gradyan, `mix-blend-mode: color`. Tarama çizgisi: 3 px periyot, `rgba(0,0,0,0.18)`.
- Kart adı: ek kromatik sapma gölgesi `-1px 0 rgba(63,224,240,0.6), 1px 0 rgba(255,46,151,0.5)`.
- Alt panel: çok hafif tarama çizgisi dokusu. Kapsül `#070915`, kenar `#2E3760`. Set numarası `#7F8AAE`. Lore `#A9B3D1`.

### Kadim Zindanlar (`KZ`)
- Zemin: taş `#2A2520`. Sembol: altıgen içinde üçgen.
- Görsel: `cover`, kenarlarda sıcak tonlu vinyet `rgba(30,15,5,0.45)`.
- Metin: taş zemin üstünde parşömen kartı. Yan boşluk 12, köşe 8, gölge `0 3px 8px rgba(0,0,0,0.45)`. Renk `#EADFC6`'dan `#D9C9A6`'ya, lekeli doku, üstte 40 x 10 süsleme. Yazı `#4A3B2A`.
- Kapsül `#1C1915`, kenar `#4A4036`. Set numarası `#A3988A`.

Not: set adları ve kısaltmaları çalışma adlarıdır. İlk setin adı ve teması `docs/plan.md` §10'da açık karar.

## 8. Stat kapsülleri

- Yükseklik 30, köşe 15, padding `0 10 0 8`, simge ile sayı arası 6.
- Hasar simgesi: 15 px kılıç, çizgi kalınlığı 1.8, renk `#FF8A6A` (KZ'de `#FF9A70`).
- Can simgesi: 15 px kalp, tip satırı rengiyle.
- Sıra: hasar sol, set numarası orta, can sağ.
- Kartın canı "can" olarak gösterilir; oyuncunun canı overlay'de "Çekirdek" adıyla ayrı bir bar olarak durur. İki kavram aynı kelimeyi paylaşmaz.

## 9. Animasyonlar

Yalnızca CSS. JavaScript gerekmiyor. `prefers-reduced-motion` açıksa animasyonlar durur.

| Efekt | Süre | Tanım |
|---|---|---|
| Gökkuşağı kenar | 3 sn, `ease-in-out infinite alternate` | Gradyan `115deg: #FF2BD6, #FF7A1A, #FFE53B, #FFFFFF, #31E8FF, #7B5CFF, #FF2BD6, #FF7A1A`, `background-size: 300%`, konum %0'dan %100'e. Yalnızca 7 px kenara maskeli (`mask-composite: exclude`). Opaklık 0.9, `saturate(1.3) brightness(1.1)` |
| Işık huzmesi | 6 sn, `ease-in-out infinite` | Beyaz bant `115deg`, %42 ile %58 arası, tepe 0.55. `mix-blend-mode: soft-light`, `background-size: 260% 100%`. Sürenin %0 ile %55 arasında %160'tan -%60'a geçer, kalan sürede bekler |
| Alt holografik doku | 8 sn, `alternate` | Gökkuşağı + 4 px çapraz çizgi deseni, `mix-blend-mode: screen`, opaklık bölüm 4'teki gibi. y 300'ün altında, üst %30'u soluyor |

Not: Gökkuşağı görselin üstünden geçmez. Görselin renklerini bozduğu için bu bilinçli bir karar.

## 10. Katman sırası

| z | Katman |
|---|---|
| 0 | Görsel veya fon, ton, doku |
| 1 | İç çerçeve çizgisi |
| 2 | Taşan figür (sadece efsanevi ve KM figürleri) |
| 3 | Geçiş katmanı, alt holografik doku, isim gölgesi |
| 4 | Taşlar, metin bloğu, stat satırı |
| 6 | Gökkuşağı kenar |
| 7 | Işık huzmesi |

## 11. Token ve mini kart

### Token
Çağrı (`SPAWN`) ile gelen kart. Desteye girmez, koleksiyonda yoktur.
- Nadirlik taşımaz: nötr kenar `#1D2026, #3A3F48, #22252B, #3A3F48, #1D2026`, taş halkası `#5C626C`.
- İç çerçeve çizgisi kesikli. Enerji taşında 0. Tip satırı: `{simge} {TİP} · TOKEN`. Set numarası yerine `TOKEN`.
- Tipi onu çağıran kartın tipidir; görseli ve zemini onu çağıran kartın setinden gelir.
- Statlar 25/25, keyword yok.

### Mini kart (düello paneli)
Tam kart düello panelinde çok yer kaplıyor. Düelloda aynı kimliği taşıyan küçük sürüm kullanılır.
- 180 x 252, kenar 4, iç köşe 9. Görsel alanı 150 yükseklik.
- Kalanlar: enerji taşı (32), tip taşı (26), kart adı (20), keyword etiketi (12, sadece ad ve değer), stat kapsülleri (sayı 21).
- Düşenler: kural metni, lore, set numarası, iç çerçeve çizgisi, foil efektleri (gökkuşağı kenar efsanevide kalır).
- Keyword açıklaması tam kartta ve `!kart` cevabında görülür.

## 12. İmza yeteneği (efsanevi)

Her efsanevi kart, başka hiçbir kartta olmayan bir imza yeteneği taşıyabilir. İmza yeteneği de bütçe formülüyle fiyatlanır ve simülasyonda test edilir; efsanevi kartın gücü sıradan bir maliyet-5 keyword kartından belirgin şekilde fazla olmaz. Heyecan güçten değil gösteriden gelir (özel paket açılış animasyonu, chat duyurusu).

Simülasyonla fiyatlanan adaylar (2026-10-12, ilk set için):

| Yetenek | Kural metni | Bütçe maliyeti |
|---|---|---|
| MİRAS | Girdiğinde, bu maçta ölen her (token olmayan) kartın için +10 hasar (en fazla +40). | 20-25 |
| HÜKÜM | Girdiğinde rakibin aktif kartına çarpışmadan önce 25 hasar. | 20 |
| DİRİLİŞ | İlk öldüğünde canının yarısıyla geri döner. Bir kez. | 10-15 |

İlk efsanevi için seçilen: **DİRİLİŞ** (`REBIRTH`), bütçe maliyeti 15. Kural: ilk öldüğünde o anki maksimum canının yarısıyla (5'in katına aşağı yuvarlanır, en az 5) aynı slota geri döner; hasar bonusları korunur, geri dönüş yeni konuşlanma sayılmaz, öldüğü vuruştaki taşma çekirdeğe geçer; ikinci ölüm kalıcıdır. Kural metninin kaynağı `.claude/rules/rules-game-engine.md`; kart üstündeki hatırlatma yazısı bilerek kısadır. Seçim geçicidir, sonra değiştirilebilir. Kesin maliyet set simülasyonunda doğrulanır.

İmza yetenekleri keyword sözlüğünde "yalnızca efsanevi" işaretiyle tutulur.

## 13. Görsel standardı

- Görsel alanı 346 x 340, yaklaşık kare. Kaynak en az 700 x 700 olmalı (2x keskinlik için).
- Odak noktası (yüz) üst %30'da olmalı; alt kısım isim ve geçişin altında kalır.
- Kesik figür (efsanevi ve KM): şeffaf PNG. Düz kesilmiş alt kenar y 302 civarına denk gelmeli ki geçiş katmanı örtsün.
- Kullanım hakkı net olmayan görsel (oyun tanıtım görseli, başka bir yapımın karakteri, hayran çizimi) canlı sette kullanılmaz. Kanvastaki Krom Kollu Asi ve Gölge Yürüyüşçüsü görselleri sadece denemedir.

## 14. Overlay yerleşimi

- Paket açılışı (1920 x 1080): beş kart %75 ölçekte (270 x 378), arada 30 px. Toplam 1470 px, iki yanda 225 px boşluk.
- Düello: mini kart (bölüm 11).
- Overlay panelinin boyutu ve konumu ayarlanabilir olur; kompakt seçenek vardır.
- Overlay'in kendi görsel teması (panel, çekirdek barı, yazılar) henüz belirlenmedi; kart tasarımından bağımsızdır. Tema tek bir CSS dosyasındaki değişkenlerden okunur (panel rengi, çizgi, vurgu, çekirdek barı, enerji, font, köşe); tema değişince HTML ve JS değişmez.

## 15. Uygulama notları

- Kart tek bir HTML şablonu olmalı. Nadirlik, tip ve set CSS sınıflarıyla seçilir; değişen sadece veridir (isim, statlar, görsel, keyword, lore).
- Renkler ve fontlar CSS değişkenlerinden okunur; tema değişince yalnızca değişken değerleri değişir.
- Overlay metni Türkçe, sınıf ve değişken adları İngilizce (proje dil politikası).
- `mask-composite`, `mix-blend-mode` ve `object-fit` Chromium'da çalışır. OBS browser source Chromium tabanlıdır, yine de ilk overlay denemesinde OBS içinde kontrol edilmeli.
- Sayfa kaydırma çubuğu çıkmaması için `html, body { overflow: hidden }`.

## 16. Açık kararlar

1. Foil kademelendirmesinin onayı (bölüm 4).
2. Çeviklik simgesi: ◆ önerisi (bölüm 5).
3. Kanal Mimleri kapsül ve set numarası renkleri.
4. Gerçek setler için görsel kaynağı ve hakları.
5. İlk setin adı ve teması; set kısaltmaları.
6. Overlay çerçevesinin teması.
