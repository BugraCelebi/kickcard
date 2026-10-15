# Kick Kart Oyunu — Proje Planı ve Şartname

**Versiyon:** v1 taslak
**Amaç:** İzleyicilerin sadakat puanıyla kart çektiği, kart topladığı ve birbirleriyle otomatik düello yaptığı, overlay üzerinde gösterilen bir yayın oyunu. Uzun vadede chat RPG sisteminin temeli.

---

## 0. Kapsam kararı

Her projede en önemli belge, **yapmayacağın şeylerin listesi**. v1'de:

| Yapılacak | v1'de YAPILMAYACAK |
|---|---|
| Paket açma (overlay animasyonlu) | Web sitesi |
| Koleksiyon takibi | Kart takası / ticaret |
| Garantili başlangıç destesi | 20+ kartlık deste, mulligan |
| 5 kartlık deste kurma | Maç içi karar penceresi |
| Otomatik düello (karar yok) | **Düello ödülü / bahis** (en sona bırakıldı) |
| Yayın modları (RP uyumu) | Sezon, turnuva |
| Sıralama tablosu | Turnuva, bracket |
| 30 kartlık tek set | Sezon, yeni set, rotasyon |
| Toz ile craft | Kozmetik, kart çerçevesi |

v1'in tek sorusu şu: **izleyici bunu umursuyor mu?** Cevap "evet" değilse geri kalanını yazmanın anlamı yok.

---

## 1. Mimari

```
Kick Chat (Pusher WS)
        │  mesaj + olay akışı
        ▼
┌───────────────────┐
│   Bot / Ingest    │  komut parse, spam filtresi
└─────────┬─────────┘
          ▼
┌───────────────────┐        ┌──────────────┐
│  Oyun Servisi     │◄──────►│    Redis     │  cooldown, aktiflik penceresi,
│  (FastAPI)        │        └──────────────┘  overlay kuyruğu
│                   │        ┌──────────────┐
│  - ekonomi        │◄──────►│  PostgreSQL  │  oyuncu, koleksiyon, deste,
│  - paket açma     │        └──────────────┘  maç geçmişi
│  - düello motoru  │
└─────┬───────────┬─┘
      │           │
      │ WS push   │ Kick API (chat:write)
      ▼           ▼
┌───────────┐   Chat'e tek satır cevap
│  Overlay  │   "@kullanıcı 3 kart çekti → overlay'e bak"
│ (Browser  │
│  Source)  │
└───────────┘
```

**Stack:** Python 3.12 + FastAPI · PostgreSQL · Redis · Overlay: tek sayfa HTML/CSS/JS (framework şart değil) · Tek VPS yeter.

**Neden bu ayrım:** Bot çökerse oyun servisi ayakta kalır. Overlay yenilenirse state kaybolmaz. Düello motoru saf fonksiyon olur, test edilebilir.

---

## 2. Veri modeli

### 2.1 Kart şablonu

Bu, projenin en önemli şablonu. Her kart tam olarak bu alanlara sahip, fazlası yok:

```json
{
  "id": "C025",
  "set": "s1",
  "code": "CYP",
  "name": "Cyberpsycho",
  "type": "POWER",
  "rarity": "epic",
  "cost": 5,
  "damage": 55,
  "hp": 45,
  "keyword": "FIRST_STRIKE",
  "keyword_value": null,
  "lore": "Beş implant fazlası. Üç mahalle eksik."
}
```

Bütçe: 55 + 45 + 35 (FIRST_STRIKE) = 135 = 5 × 25 + 10.

Kartta `text` alanı yok. Keyword'ün hatırlatma yazısı keyword sözlüğünden üretilir (bkz. §2.2).

| Alan | Aralık | Not |
|---|---|---|
| `set` | set kimliği | Kartın ait olduğu set. `"s1"` geçici kimlik; ilk setin adı açık karar (§10) |
| `code` | 3 harf, tekil | Komutlarda kullanılır (`!deste sok,kur,...`). Tüm setlerde tekil |
| `type` | POWER / TRICK / AGILITY | Üçgen aşağıda |
| `rarity` | common / uncommon / rare / epic / legendary | **Güçle ilgisi yok**, sadece bulunabilirlik. Oyuncuya görünen adlar: Sıradan, Sıra Dışı, Nadir, Destansı, Efsanevi |
| `cost` | 1–5 | Enerji |
| `damage` | 10–70 | |
| `hp` | 15–95 | |
| `keyword` | 0 veya 1 tane | v1'de ikisi birden yok |

**Tip üçgeni** — kendi kendini açıklayacak şekilde kurgulandı, oyuncu ezberlemek zorunda kalmasın:

```
   POWER  ──────►  TRICK         POWER > TRICK     kaba kuvvet hileyi ezer
     ▲               │           TRICK > AGILITY   hile çevik olanı tuzağa düşürür
     │               ▼           AGILITY > POWER   çevik olan güçlüden kaçar
   AGILITY ◄─────────┘
```

Oyuncuya görünen adlar: **Güç > Hile > Çeviklik > Güç.**

Avantajlı tip **+10 hasar** verir (çarpan değil, sabit; okunması ve dengelenmesi kolay). Bonus **sadece kart karta vuruşta** geçerlidir. Boş slota (çekirdeğe) vuruşta tip bonusu yoktur.

Kartlar birden fazla temalı setten gelebilir. Setler mekaniği (tipler, keyword'ler, bütçe) paylaşır ve aynı destede karışabilir; kart adı, illüstrasyon ve lore sete özeldir.

### 2.2 Güç bütçesi formülü

Denge burada tutuluyor. Her kart bir bütçe harcar:

```
budget = cost * 25 + 10

spend  = damage + hp + keyword_cost

Kart dengeli ise:  spend ≈ budget  (±5 tolerans)
```

| Maliyet | Bütçe | Örnek dağılım (saldırgan) | Örnek dağılım (savunmacı) |
|---|---|---|---|
| 1 | 35 | 20 hasar / 15 can | 10 hasar / 25 can |
| 2 | 60 | 35 / 25 | 20 / 40 |
| 3 | 85 | 50 / 35 | 30 / 55 |
| 4 | 110 | 65 / 45 | 40 / 70 |
| 5 | 135 | 80 / 55 | 50 / 85 |

**Keyword maliyetleri** (bütçeden düşülür):

| Keyword | Maliyet | Kural |
|---|---|---|
| `FIRST_STRIKE` | 35 | Önce vurur; rakip ölürse karşılık veremez. İki taraf da FIRST_STRIKE ise eşzamanlı. |
| `ARMOR_X` (X = 5/10/15) | X + 10 | Karta gelen her vuruşu X azaltır. PIERCE'ın çekirdeğe giden kısmını ve taşmayı ayrıca azaltmaz. |
| `PIERCE` | 15 | Tip bonusu eklendikten sonra hasarın yarısı (aşağı yuvarlanır) doğrudan çekirdeğe, kalanı karta. |
| `OVERLOAD` | 20 | Kartın sahadaki ilk çarpışma turunda +20, sonraki turlarda -10 (en az 0). Boş slota vuruşta da geçerli. |
| `HANDOFF` | 30 | Ölünce sahibinin destedeki sıradaki kartı +20 hasar ve +20 canla girer. Birden fazla HANDOFF üst üste biner. |
| `LINK` | 20 | Sahibinin bir önceki sahaya çıkardığı deste kartı aynı tipteyse +25 hasar. Token'lar sayılmaz. |
| `PROTOCOL` | 20 | Sahibinin destesindeki (sahadaki değil) kendisi hariç her aynı tip kart için +10 hasar, en fazla +40. |
| `SPAWN` | 15 | Ölünce aynı slota kendi tipinde, keyword'süz, 25/25 bir token girer. Sıradaki kart token ölene kadar bekler. Token'ın ölümü hiçbir şeyi tetiklemez. |

Kart başına en fazla 1 keyword. Ölüm tetikleyicileri (HANDOFF, SPAWN, REBIRTH) Temizlik adımında çalışır.

**Keyword sözlüğü tek kaynaktır.** Keyword'ün adı, maliyeti ve hatırlatma yazısı oradan okunur; kartlara elle yazılmaz. Bir değer değişince bütün kartların metni kendiliğinden güncellenir.

Sinerji değerleri (HANDOFF, LINK, PROTOCOL, SPAWN) başlangıç değeridir; kart seti hazır olunca simülasyonla ölçülecek. Herhangi bir deste havuza karşı %60 üstü kazanıyorsa değerler düşürülür veya karta binen toplam bonusa tavan konur.

ECHO ve RECYCLE v1'den çıkarıldı (bkz. Backlog).

Nadirliğin işi güç değil, **karmaşıklık**: common'lar keyword'süz düz kartlar, legendary'ler keyword'lü ve niş. Aynı bütçe, farklı şekil. Bunun en uç hali imza yeteneğidir: legendary'yi farklı kılan güç değil, başka hiçbir kartta olmayan bir davranış. Legendary'nin heyecanı gösteriden gelir: özel paket açılış animasyonu, chat'e düşen nadir olay.

#### İmza yeteneği

- Her legendary kart, başka hiçbir kartta olmayan bir imza yeteneği taşıyabilir.
- İmza yeteneği, keyword sözlüğünde "yalnızca legendary" işaretli bir keyword'dür. O kartın tek keyword'üdür ve bütçe formülüyle fiyatlanır.
- İlk legendary için seçilen: **`REBIRTH` (Diriliş), maliyet 15.** Seçim geçicidir, ileride değişebilir.

**REBIRTH kuralı:** Kart ilk kez öldüğünde, kartın o anki maksimum canının yarısıyla (5'in katına aşağı yuvarlanır, en az 5) aynı slota geri döner. Hasar bonusları korunur. Geri dönüş yeni bir konuşlanma sayılmaz; slot dolu kaldığı için sıradaki kart bekler. Öldüğü vuruştaki taşma hasarı yine çekirdeğe geçer. İkinci ölüm kalıcıdır.

### 2.3 Veritabanı tabloları

```sql
player          (kick_user_id PK, username, eddies, dust,
                 pity_counter, created_at, last_active_at)

collection      (kick_user_id, card_id, quantity)      -- PK (user, card)

deck            (kick_user_id PK, card_ids JSONB)      -- ordered, 5 entries

duel            (id PK, player_a, player_b, winner,
                 turn_log JSONB, created_at)           -- turn_log = overlay replay

ledger_entry    (id PK, kick_user_id, kind, amount, reason, created_at)
```

`duel.turn_log` her kartın o maçtaki statlarının anlık kopyasını içerir; sonradan yapılan denge değişiklikleri eski replay'leri bozmaz.

`ledger_entry` şart — ekonomide bir şey ters gittiğinde nereden bozulduğunu ancak buradan bulursun.

---

## 3. Oyun kuralları v1

### 3.1 Kurulum

- Her oyuncu **5 kartlık sıralı** bir deste kurar. Aynı karttan 1 kopya.
- Her oyuncunun bir **Çekirdeği** var: **100 can**.
- Her oyuncunun bir **aktif slotu** var (tek kart).
- Enerji 0'dan başlar.

### 3.2 Tur akışı

Her tur, iki oyuncu için eşzamanlı işler:

1. **Enerji:** Her oyuncu +2 enerji kazanır (0'dan başlar, üst limit 10).
2. **Konuşlanma:** Aktif slot boşsa, destedeki **sıradaki** kart kontrol edilir. Enerji yetiyorsa sahaya çıkar, maliyeti düşülür. Yetmiyorsa slot boş kalır ve enerji birikmeye devam eder.
3. **Çarpışma:**
   - İki tarafta da kart varsa: **eşzamanlı** hasar. Tip avantajı varsa **+10 hasar** (sadece kart karta).
   - `FIRST_STRIKE` varsa o kart önce vurur; rakip ölürse karşılık veremez.
   - Bir tarafın slotu boşsa: karşı kart hasarını **doğrudan çekirdeğe** verir. Tip bonusu eklenmez.
4. **Taşma:** Kartı öldüren hasarın fazlası çekirdeğe geçer.
   *Örnek: 55 hasar, 40 canlı karta → kart ölür, 15 hasar çekirdeğe.*
5. **Temizlik:** Canı ≤ 0 olan kartlar sahadan çıkar. Ölüm tetikleyicileri (`HANDOFF`, `SPAWN`, `REBIRTH`) burada çalışır.

### 3.3 Kazanma

- Rakibin çekirdeği **0'a inerse** kazanırsın.
- **20 turda** biri ölmezse çekirdek canı fazla olan kazanır. Eşitse berabere.

### 3.4 Neden bu tasarım

- **Maç içi karar yok** → 200 kişi oynayabilir, kimse AFK kalamaz, maç 30 saniyede animasyonla akar.
- **Skill deste sıralamasında.** Pahalı kartı öne koyarsan 2 tur boşta kalıp çekirdeğinden yersin. Ucuz kartla açarsan tempo alırsın ama sonu zayıf kalır. Bu tek karar bile ciddi bir meta üretiyor.
- **Çekirdek barı** overlay'de okunması en kolay şey. İzleyici kuralları bilmese bile kimin kazandığını görüyor.
- **Neden çekirdek 100 ve +2 enerji.** Çekirdek 30 ve +1 enerjiyle maçlar ~3 turda bitiyordu, maliyeti 5 olan kartlar hiç sahaya çıkmıyordu ve "ucuzdan pahalıya diz" tek doğru cevap oluyordu. Çekirdek 100 ve +2 enerji ile sıralama kararı gerçek beceri haline geldi; sinerji keyword'leri de deste kurmayı yönlendiriyor.

---

## 4. Ekonomi

### 4.0 Terim: "eddie" = sadakat puanı

Belgede geçen **eddie**, kanalın sadakat puanının kendisi — ayrı bir para birimi değil, sadece evrene uygun ismi. İzleyici yayında geçirdiği zamanla kazanır, paket açmakta harcar.

v1'de **tek eksen** var: kazan → harca. RPG fazında konuştuğumuz ikinci eksen (harcanamayan, sadece biriken XP) buraya sonradan eklenecek. Şimdilik eklemiyoruz çünkü kart oyununda seviye kavramı yok, ve iki para birimini boşuna açıklamak yeni oyuncuyu yoruyor.

### 4.1 Eddie kazanımı

| Kaynak | Miktar | Kural |
|---|---|---|
| Aktiflik | 10 eddie / 5 dk | Son 10 dk içinde mesaj atmış olmak şart |
| Takip | 100 | Tek seferlik |
| Abonelik | 300 | Her ay |
| Hediye abonelik | 150 | Hediye edene |
| Kicks bahşişi | 1 eddie / 1 Kick | |
| Yayın başı tavan | **500** | Aktiflikten kazanılabilecek maksimum |

Tavan şart: 8 saat lurk edenle 1 saat katılan arasındaki fark saçmalaşmasın, tablo donmasın.

### 4.2 Paket

**Fiyat: 100 eddie. İçerik: 5 kart.**

| Slot | Dağılım |
|---|---|
| 1–3 | Common |
| 4 | Uncommon %85 / Rare %15 |
| 5 | Rare %80 / Epic %18 / **Legendary %2** |

**Pity:** 30 pakette legendary çıkmadıysa 30. pakette garanti. Sayaç sıfırlanır.

### 4.3 Toz (duplicate dönüşümü)

Zaten sahip olduğun kart tekrar gelirse toza dönüşür:

| Nadirlik | Toz getirisi | Craft maliyeti |
|---|---|---|
| Common | 5 | 20 |
| Uncommon | 15 | 60 |
| Rare | 50 | 200 |
| Epic | 150 | 600 |
| Legendary | 500 | 2000 |

Craft, gacha'nın umutsuzluğunu kırar ve deterministik hedef verir: *"3 yayın daha, Cyberpsycho'yu üreteceğim."*

### 4.4 Başlangıç destesi (garantili)

`!kayıt` yazan herkese **aynı 5 common kart** verilir ve otomatik olarak destesi kurulur. Bu kartlar koleksiyonun bir parçasıdır ve toza dönüştürülemez.

Sebep: oyuncu hiç paket açmadan, hiç `!deste` yazmadan, kayıt olduğu saniye düello yapabilmeli. Deste kurmayı zorunlu bir adım yaparsan yeni gelenlerin yarısını orada kaybedersin. Başlangıç destesi zayıf ama **yapısal olarak dezavantajlı değil** — bütçe formülüne uyuyor, sadece keyword'süz ve düz.

Ayrıca 3 bedava paket verilir, böylece ilk açılış deneyimini hemen yaşar.

### 4.5 Ekonomi sağlık kontrolü

İki yayında ölçülen gerçek veri: ortalama izleyici kazancı 129 ve 86 eddie, medyan 80 ve 50. 400+ eddie'ye ulaşan yalnızca en sadık izleyicilerin %3-8'i — "ortalama izleyici ~400 kazanır" varsayımı yanlış çıktı. Tavan 500'e çıkarıldı (bkz. `.claude/rules/rules-economy.md`), ama bu artık ortalama izleyicinin ulaştığı bir eşik değil, en üstteki farm koruması. Koleksiyon tamamlama hızı gerçekte medyan izleyiciye göre şekilleniyor; daha fazla veri (bkz. `docs/progress.md` Sprint 4) toplanana kadar bu bölüm gözden geçirilmeye devam edecek.

**Kırmızı çizgi:** v1'de eddie'nin tek harcama yeri paket açmak. Düello ödülü/bahsi bilinçli olarak ertelendi (bkz. Backlog), yani koleksiyonu tamamlayan oyuncu ekonomiden düşecek. 30 kartlık set ~5 yayında tamamlandığına göre bu, sistemin üzerinde çalışan bir sayaç — **ilk oyuncular koleksiyonu bitirmeden ikinci harcama kalemi hazır olmalı.**

---

## 5. Komut seti

| Komut | İşlev | Cooldown |
|---|---|---|
| `!kayıt` | Hesap açar, 3 bedava paket verir | — |
| `!eddie` | Bakiye + toz gösterir | 30 sn |
| `!paket` | Paket açar → overlay kuyruğuna girer | Yayın başı 3 |
| `!koleksiyon` | Sahip olunan kart sayısı, eksikler | 60 sn |
| `!kart <kod/ad>` | Tek kartın statlarını ve keyword hatırlatma yazısını chat'e yazar (tek satır) | 15 sn |
| `!deste sok,kur,rip,cyp,krb` | Desteyi sıralı olarak kurar (kart kodlarıyla) | 10 sn |
| `!deste oto` | Sistem koleksiyondan en iyi 5'i seçip sıralar | 30 sn |
| `!deste` | Mevcut desteyi gösterir | 30 sn |
| `!düello @kişi` | Meydan okur (60 sn geçerli) | 2 dk |
| `!kabul` | Meydan okumayı kabul eder → maç başlar | — |
| `!craft <kart>` | Tozla kart üretir | — |
| `!sıralama` | İlk 5 (galibiyet sayısına göre) | 60 sn |
| `!mod game/silent/off` | Yayın modunu değiştirir — **sadece yayıncı ve modlar** | — |

### 5.1 Girdi toleransı

Kart referansı üç şekilde de çalışmalı, ve yazım hatasını affetmeli:

- Kod: `cyp`
- Tam ad: `cyberpsycho`
- Hatalı ad: `cyberpsyco`, `Cyber Psycho` → Levenshtein mesafesi ≤ 2 ise eşleş

Eşleşme belirsizse chat'e seçenek yaz: `"cyb" 2 kartla eşleşti: CYP Cyberpsycho, CYB Cyber-Sıçan`. Sessizce yanlış kartı koyma — oyuncu düelloyu kaybedene kadar fark etmez ve sinirlenir.

Sayı yerine kod kullanmanın sebebi: `!deste 17,4,22,9,31` yazan oyuncu 17'nin ne olduğunu bilmiyor, `!koleksiyon` çıktısına geri dönüp bakmak zorunda kalıyor. Kodlar okunabilir olduğu için akılda kalıyor ve chat'te başkasının destesini görünce anlaşılıyor — bu da meta tartışmasını besliyor.

**Chat'e yazılan cevap tek satır olmalı.** Gösteri overlay'de, chat sadece onay veriyor:

```
@kullanici → Paket sıraya girdi (2 kişi önünde) · Kalan: 240 eddie
@kullanici → Deste kuruldu: Sokak Çocuğu → Kurye → Ripperdoc → Cyberpsycho → Kara Buz
@kullanici vs @rakip → düello başlıyor, ekrana bak
```

---

## 6. Overlay

### 6.1 Sahneler

| Sahne | Süre | Tetikleyici |
|---|---|---|
| **Boşta** | — | Görünmez (şeffaf) |
| **Paket açılışı** | 8 sn | `!paket` kuyruğu |
| **Düello** | 30–40 sn | Kabul edilmiş meydan okuma |
| **Sıralama** | 15 sn | Yayın kapanışı / manuel |

Overlay panelinin boyutu ve konumu ayarlanabilir; kalabalık sahneler için kompakt seçenek vardır.

### 6.2 Kuyruk mantığı

Overlay aynı anda tek şey gösterebiliyor. Redis'te tek bir kuyruk:

- Düello **her zaman** paket açılışının önüne geçer (daha büyük olay).
- Kuyruk 10'u geçerse yeni `!paket` reddedilir: *"kuyruk dolu, biraz sonra dene"*.
- Kişi başı yayın başına 3 paket limiti → overlay senin içeriğinin önüne geçmez.

### 6.3 Yayın modları — RP yayınları için

RP yayınlarında overlay atmosferi bozuyor. Çözüm sistemi kapatmak değil, **modlamak.** Overlay ve bot tek bir `mode` state'i dinler:

| Mod | Overlay | Bot chat cevabı | Eddie kazanımı | `!paket` | `!düello` |
|---|---|---|---|---|---|
| **GAME** | Tam | Normal | Açık | Açılır | Açık |
| **SILENT** | **Hiç çizmez** | Kapalı | **Açık** | **Kasaya girer, açılmaz** | Kapalı |
| **OFF** | Yok | Kapalı | Kapalı | Kapalı | Kapalı |

**SILENT modun kilit fikri — kasa:** RP yayınında `!paket` yazan oyuncu paketi satın alır ama paket **açılmadan kasasına** eklenir. Bir sonraki GAME yayınında `!kasa` ile birikmiş paketlerin hepsini arka arkaya açar.

Bu, kısıtı avantaja çeviriyor:

- RP izleyicisi yayında geçirdiği zamanın karşılığını almaya devam ediyor
- Biriken 5 paketi tek seferde açmak, tek tek açmaktan **çok daha büyük bir olay**
- RP izleyicisine oyun yayınına gelmek için somut bir sebep veriyor — iki format arasında köprü kuruyor

**Dikkat:** SILENT modda bot'un chat cevaplarını da kesmen şart. RP yayınında bot spam'i overlay kadar atmosfer bozuyor. Tek istisna: hata mesajları sessizce yutulmasın, yoksa oyuncu komutun çalışıp çalışmadığını bilemiyor — çözüm, satın alma onayını **bir sonraki GAME yayınının başında toplu olarak** chat'e yazmak.

Teknik: mod Redis'te tek bir anahtar. Overlay WS üzerinden değişimi dinler ve SILENT'a geçince kendini boşaltır (animasyonu kesme, fade-out yap — anlık kaybolma da dikkat çekiyor).

### 6.4 Görsel yön

**Kartlarda illüstrasyon var.** Kartın görsel spesifikasyonu (ölçüler, nadirlik ve tip renkleri, simgeler, set malzemeleri, token, mini kart) `docs/card-design.md`'dedir; bu belge görsel ayrıntıyı tekrarlamaz.

- Keyword hatırlatma yazısı kartın üstünde gösterilir ama keyword sözlüğünden üretilir (§2.2).
- Düelloda tam kart yerine **mini kart** kullanılır (`docs/card-design.md` bölüm 11).
- Overlay düello etiketlerinde sadece keyword adı ve değeri görünür (örn. "ZİNCİR +25").
- Overlay'in kendi görsel teması (panel, çekirdek barı, yazılar) henüz belirlenmedi ve kart tasarımından bağımsızdır. Tema tek bir CSS dosyasındaki değişkenlerden okunur; tema değişince HTML ve JS değişmez.
- Kart bileşeni tek bir HTML template; nadirlik, tip ve set CSS class'larıyla seçilir. Overlay ve (ileride) site aynı bileşeni kullanır.

---

## 7. İlk set — 30 kart

### 7.1 Dağılım

| Nadirlik | Adet | Rol |
|---|---|---|
| Common | 12 | Düz statlar, keyword yok, maliyet 1–3 |
| Uncommon | 8 | Basit keyword, maliyet 2–4 |
| Rare | 6 | Keyword + belirgin şekil, maliyet 3–5 |
| Epic | 3 | Niş, kombo isteyen, maliyet 4–5 |
| Legendary | 1 | İmza kart, imza yeteneği taşır (§2.2), maliyet 5 |

Tip dağılımı her nadirlikte dengeli olsun (POWER/TRICK/AGILITY ≈ eşit), yoksa bir tip metayı ele geçirir. Özellikle üst maliyet kartlarında dengesizlik olursa üçgen anlamını kaybediyor.

**Tip kimliği** bir set tasarım rehberidir, kural değildir:

- **POWER (Güç):** yüksek hasar ve maliyet.
- **AGILITY (Çeviklik):** ucuz kartlar, OVERLOAD, erken baskı.
- **TRICK (Hile):** keyword ve sinerji yoğun.

### 7.2 Kart tablosu şablonu

Bu tabloyu doldurarak seti kuruyorsun. `Bütçe kontrol` sütunu = `damage + hp + keyword_cost − (cost × 25 + 10)`. **Hedef: 0 (±5).**

| id | set | code | name | type | rarity | cost | damage | hp | keyword | check |
|---|---|---|---|---|---|---|---|---|---|---|
| | | | | | | | | | | |

**Başlangıç destesi** (herkeste sabit, toza dönüştürülemez): 5 common kart. Üç tipi de içermeli ki oyuncu tip üçgenini ilk maçta öğrensin.

### 7.3 Set tasarım kuralları

- Her maliyet seviyesinde en az 4 kart olsun, yoksa deste kurma tıkanır.
- Common'ların hepsi keyword'süz. Yeni oyuncunun ilk destesi anlaşılır olmalı.
- `FIRST_STRIKE` en güçlü keyword — sette 3'ten fazla olmasın.
- Legendary imza yeteneği taşır, ama gücü bütçe formülüyle sınırlıdır. Legendary dahil her kart formüle uyar.
- Her kart için tek cümlelik lore yaz. Maliyeti sıfır, bağlanma etkisi büyük.

---

## 8. Aşamalar

Güncel görev listesi docs/progress.md'dedir; bu bölüm ilk plandır ve güncellenmez.

### Sprint 0 — Temel (1 hafta) · yayında değil

- [ ] Kick chat'i Pusher WS ile okuma, mesajları parse etme
- [ ] Postgres şeması + Redis bağlantısı
- [ ] Eddie kazanım motoru (aktiflik penceresi + tavan) — sessizce çalışsın
- [ ] `!eddie` komutu, chat'e cevap yazma

**Çıktı:** İzleyiciler farkında olmadan eddie biriktirmeye başlar. Yayın günü geldiğinde herkesin bakiyesi var — bu, lansmanı çok daha iyi yapıyor.

### Sprint 1 — Kart ve paket (1 hafta)

- [ ] 30 kartlık seti JSON olarak yaz (kodlarıyla), bütçe formülüyle doğrula
- [ ] Kart HTML/CSS bileşeni
- [ ] `!kayıt` → başlangıç destesi + 3 bedava paket
- [ ] `!paket`, `!koleksiyon`, `!kart` + bulanık eşleşme
- [ ] Overlay: paket açılış animasyonu + kuyruk
- [ ] **Yayın modları** (`!mod`) — RP yayınından önce hazır olmalı, kasa mekaniği dahil

**Çıktı:** Yayında duyurulur. Bu ilk gerçek test — insanlar paket açıyor mu, açılışı izliyor mu?

### Sprint 2 — Düello (1–2 hafta)

- [ ] Düello motoru (saf fonksiyon, girdi: 2 deste → çıktı: tur kaydı)
- [ ] Motor için birim testler (özellikle taşma hasarı ve `FIRST_STRIKE`)
- [ ] `!deste`, `!düello`, `!kabul`
- [ ] Overlay: tur tur oynatma animasyonu, çekirdek barları

**Çıktı:** Rekabetçi katman açılır. Burada meta oluşmaya başlar ve sen yayında bunu yorumlarsın.

### Sprint 3 — Cila (1 hafta)

- [ ] Toz + `!craft`
- [ ] `!sıralama` + yayın kapanış sahnesi
- [ ] Pity sayacı
- [ ] Anti-abuse: hesap yaşı kontrolü, ilk 3 mesaj eddie vermez

### Sprint 4 — Denge ve genişleme (sürekli)

- [ ] Maç verisinden kart kazanma oranları (hangi kart %60+ ise nerf)
- [ ] İkinci eddie harcama kalemi
- [ ] Web sitesi (koleksiyon tarama, deste kurma)
- [ ] Haftalık turnuva

**Toplam ilk yayınlanabilir sürüme kadar: ~2 hafta.** Sprint 0+1 bitince zaten sahnede bir şey var.

---

## 9. Riskler

| Risk | Neden olur | Önlem |
|---|---|---|
| Kimse umursamaz | Sistem sessiz çalışır, sen sahiplenmezsin | Yayında sözlü olarak sürekli referans ver. "X legendary çekti" demezsen olmamış sayılır. |
| Overlay yayının önüne geçer | Kuyruk sürekli dolu | Kişi başı limit + düello önceliği + boşta tamamen şeffaf |
| Bot/farm hesapları | Kick'te viewbot yaygın | Hesap yaşı eşiği, ilk 3 mesaj XP vermez, IP/isim örüntü kontrolü |
| Tek deste metayı kilitler | Bir kart aşırı güçlü | Sprint 3'ten itibaren kazanma oranı takibi; nerf'i yayında duyur, sürpriz yapma |
| Sinerji kombosu metayı kilitler | HANDOFF, LINK, PROTOCOL gibi bonuslar aynı destede üst üste biner | Set simülasyonu; herhangi bir deste havuza karşı %60 üstü kazanıyorsa değerler düşürülür veya karta binen toplam bonusa tavan konur |
| Yeni oyuncu açığı | Kurulmuş deste, rastgele desteyi simülasyonda %94-99 yeniyor | Açık (bkz. §10) |
| Pusher API kırılır | Resmi olmayan endpoint | Ingest katmanını soyutla; resmi webhook'a geçiş tek dosya değişikliği olsun |
| Sen bakımını bırakırsın | En olası risk | Sprint 3'ten sonra her şey opsiyonel olacak şekilde tasarla. v1 kendi başına ayakta durmalı. |

---

## 10. Karar durumu

### Karara bağlandı

| Konu | Karar |
|---|---|
| Sadakat puanı | "eddie" adıyla tek para birimi; XP ayrımı RPG fazına ertelendi |
| Tipler | POWER > TRICK > AGILITY > POWER (Güç > Hile > Çeviklik). Tip avantajı +10, sadece kart karta |
| Çekirdek ve enerji | Çekirdek 100 can; her tur +2 enerji, 0'dan başlar, limit 10 |
| Keyword seti | v1'de 8 keyword (§2.2); ECHO ve RECYCLE backlog'da |
| İmza yeteneği | Legendary'ye özel, bütçeyle fiyatlanır; ilk legendary için REBIRTH (Diriliş), maliyet 15 |
| Çoklu set | Setler mekaniği paylaşır, aynı destede karışabilir; ad, illüstrasyon ve lore sete özel; kodlar tüm setlerde tekil |
| İllüstrasyon | Kartlarda illüstrasyon var (eski "illüstrasyon yok" kararı kalktı) |
| Keyword sözlüğü | Tek kaynak; hatırlatma yazısı kartlara elle yazılmaz, kart şemasında `text` alanı yok |
| Kart görsel spesifikasyonu | `docs/card-design.md` |
| Deste komutu | Sayı değil 3 harfli kod + bulanık eşleşme + `!deste oto` |
| Yeni oyuncu | Garantili başlangıç destesi, deste kurmak zorunlu değil |
| RP yayınları | Yayın modları + kasa mekaniği |
| Düello ödülü | **Ertelendi** — ekonomi oturduktan sonra |

### Açık

1. **İlk setin adı ve teması**, 30 kartın isimleri ve lore'u. Evren kanalın mevcut estetiğiyle mi ortak, ayrı mı?
2. **Legendary kartın kimliği.** İmza kart, muhtemelen kanal maskotu. İmza yeteneği seçildi: REBIRTH.
3. **Başlangıç destesindeki 5 kart** — üç tipi de içerecek şekilde hangileri?
4. **Overlay görsel teması** (panel, çekirdek barı, yazılar). Kart tasarımından bağımsız.
5. **Yeni oyuncu açığı.** Kurulmuş deste rastgele desteyi simülasyonda %94-99 yeniyor; önlem belirlenmedi.

---

## Backlog (v1 sonrası)

- **Düello ödülü / bahis sistemi.** Ekonomi oturduktan sonra ele alınacak. Aday model: iki taraf 50 eddie yatırır, kazanan 80 alır, 20 yakılır — hem harcama kalemi açar hem enflasyonu emer. Risk: kaybetme acısı yeni oyuncuyu kaçırabilir, o yüzden ilk N maç bahissiz olmalı.
- **İkinci harcama kalemi** (kozmetik çerçeve, kart yükseltme) — koleksiyonu ilk tamamlayan oyuncudan önce hazır olmalı.
- **15 kartlık genişleme seti** — v1 lansmanından ~1 ay sonra. 30 kartlık set bu sürede çözülüyor ve meta donuyor.
- Web sitesi (koleksiyon tarama, deste kurma, kart kataloğu, keyword sözlüğü, düello replay'leri)
- **v1'den çıkarılan keyword'ler:** `ECHO` (ölünce rakip aktif karta hasar) ve `RECYCLE`.
- **İmza yeteneği adayları** (ileride eklenecek legendary'ler için):
  - `LEGACY` (Miras, maliyet 20-25): sahaya çıktığında sahibinin bu maçta ölen her token olmayan kartı için +10 hasar, en fazla +40.
  - `VERDICT` (Hüküm, maliyet 20): sahaya çıktığında, çarpışmadan önce rakibin aktif kartına 25 hasar.
- Haftalık turnuva + bracket overlay
- Sezon / soft reset
- RPG sistemine geçiş: XP ekseni, karakter, kartların envanter olması
