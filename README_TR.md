<p align="center">
  <img src="assets/icon.png" width="128" height="128" alt="RemoteTyper Logo" />
</p>

<h1 align="center">RemoteTyper</h1>

<p align="center">
  <strong>Sistem Yöneticileri, DevOps & IT Mühendisleri İçin Evrensel Uzak Konsol Tuş Enjektörü</strong>
</p>

<p align="center">
  <a href="https://python.org"><img src="https://img.shields.io/badge/Python-3.8+-3776AB?logo=python&logoColor=white" alt="Python" /></a>
  <a href="https://www.microsoft.com/windows"><img src="https://img.shields.io/badge/Platform-Windows-0078D6?logo=windows&logoColor=white" alt="Platform" /></a>
  <a href="https://github.com/sinezty/RemoteTyper/releases"><img src="https://img.shields.io/github/v/release/sinezty/RemoteTyper?color=22d3ee&logo=github" alt="Release" /></a>
  <img src="https://img.shields.io/badge/License-MIT-green.svg" alt="License" />
  <a href="https://github.com/sinezty"><img src="https://img.shields.io/badge/Developer-sinezty-181717?logo=github" alt="GitHub" /></a>
</p>

<p align="center">
  <a href="README.md"><strong>🇬🇧 English Documentation</strong></a> &nbsp;•&nbsp;
  <strong>🇹🇷 Türkçe Dokümantasyon</strong>
</p>

<p align="center">
  <em>İşletim sistemi panosunun (clipboard) kopyala-yapıştıra izin vermediği uzak konsol ve sanal makinelere metin enjekte edin.</em>
</p>

<p align="center">
  <img src="assets/demo.gif" alt="RemoteTyper Proxmox VE Demo" width="760" />
</p>

---

### 🎯 Problem ve Çözüm

Sistem yöneticileri ve DevOps mühendisleri için uzak sunucu ve sanal makine yönetiminde en sık karşılaşılan sorunlardan biri **pano (clipboard) kopyala-yapıştır işlevinin çalışmamasıdır**:
- **Proxmox VE (noVNC)**, **oVirt** gibi web tabanlı KVM konsolları tarayıcı kopyalama/yapıştırma izinlerini kısıtlar.
- **IPMI / iDRAC / iLO** gibi bant dışı yönetim konsolları işletim sistemi panosuna erişim sağlamaz.
- İzole edilmiş (air-gapped) ağlar, yeni işletim sistemi kurulumları veya konuk araçları (guest tools) yüklü olmayan sanal makinelerde doğrudan metin yapıştırma imkansızdır.

**RemoteTyper**, metinleri karakter karakter **fiziksel klavye vuruşları** olarak enjekte ederek bu sorunu kökten çözer. Hedef sunucu veya sanal makine, gelen veriyi fiziksel bir klavyeden elle yazılan tuş vuruşları olarak algılar.

---

### ✨ Öne Çıkan Özellikler

- **Adım Adım / Satır Satır İlerleme (`F2`)**:
  - Tuşa bastığınızda tek bir satırı yazar, Enter'a basar ve duraklar.
  - Komutun sunucudaki çıktısını inceleyip hazır olduğunuzda tekrar `F2`'ye basarak bir sonraki satıra geçebilirsiniz.
- **Satır Arası Gecikme (Line Delay)**:
  - Her satır/komut sonrası ayarlanabilir bekleme süresi (varsayılan `3s`). Komut çıktılarının ekrana basılması sırasında komutların üst üste binmesini tamamen engeller.
- **Otomatik Çalıştırma (`F8`)**:
  - Sabit 5 saniyelik geri sayım ile hedef konsola geçiş süresi tanır ve tüm satırları satır arası gecikmeyle sırayla enjekte eder.
- **Çift Enjeksiyon Motoru**:
  - **`Direct Type` (Varsayılan)**: Proxmox noVNC, web konsolları ve sanal makineler için optimize edilmiş kesintisiz doğrudan klavye simülasyonu.
  - **`ALT+Numpad` (Evrensel)**: Eski IPMI/iDRAC ve donanım konsolları için ALT+Numpad ASCII kodları enjeksiyonu.
- **Akıllı Satır Sonu (Enter) Güvenliği**:
  - **`Each Line`**: Her satır bitiminde otomatik olarak Enter tuşuna basar.
  - **`Except Last` (Güvenlik Modu)**: Tüm satırları yazar ve aralarında Enter'a basar, ancak son satırda Enter'a basmadan bekler. Böylece kritik komutları (`rm`, `reboot`, config güncellemeleri) çalıştırmadan önce kontrol etmenize olanak tanır.
  - **`Disabled`**: Asla Enter tuşuna basmaz (düz metin girişi).
- **Otomatik Tırnak ve Çizgi Temizleyici (Smart-Quote Sanitizer)**:
  - Web sitelerinden kopyalanan eğik tırnakları (`“ ” ‘ ’`), uzun çizgileri (`— –`) ve bozuk boşluk karakterlerini bash/shell uyumlu standart ASCII karakterlere otomatik olarak dönüştürür.
- **Donanım Düzeyinde Tuş Güvenliği**:
  - `try...finally` güvencesi sayesinde yazma işlemi yarıda kesilse bile ALT, Shift veya Ctrl tuşları sisteminizde asla basılı kalmaz.
- **Ultra-Kompakt TUI/CLI Tasarımı**:
  - Editör alanını maksimize eden kompakt 2 satırlı alt kontrol paneli.
  - InnoSetup tarzı gömülü ilerleme çubuğu, yüzde göstergesi ve karakter sayacı.
  - Yüksek kontrastlı, gözü yormayan modern koyu terminal teması.
- **Global Kısayol Tuşları**:
  - **`F2`**: Satır satır adım adım işletir ve bekler.
  - **`F8`**: Otomatik enjeksiyonu başlatır (5sn geri sayım).
  - **`F9`**: Acil durdurma — uygulama simge durumunda olsa bile anında yazmayı keser.
  - **`Escape`**: Odaklı durumdayken yazmayı iptal eder.
- **Pin on Top**: Uygulamanın uzak konsol pencerelerinin üzerinde her zaman en üstte kalmasını sağlar.

---

### 🚀 Hızlı Başlangıç

#### Yöntem 1: Hazır EXE İndirme (Tavsiye Edilen)
Python kurulumu gerektirmez.
1. [Releases](https://github.com/sinezty/RemoteTyper/releases) sayfasından **`RemoteTyper.exe`** dosyasını indirin.
2. `RemoteTyper.exe` dosyasına çift tıklayarak çalıştırın.

#### Yöntem 2: Kaynak Koddan Çalıştırma
```bash
# Projeyi klonlayın
git clone https://github.com/sinezty/RemoteTyper.git
cd RemoteTyper

# Bağımlılıkları yükleyin
pip install -r requirements.txt

# Uygulamayı başlatın
python remotetyper.py

# İsteğe bağlı: Hata ayıklama günlükleri ile çalıştırma
python remotetyper.py --debug
```

---

### 🎮 Nasıl Kullanılır?

1. Kod veya komutlarınızı editör alanına yapıştırın.
2. **Mode** seçiminizi yapın (Proxmox/noVNC için `Direct Type`, donanım konsolları için `ALT+Numpad`).
3. **Speed** (Hız: `Normal`, `Slow`, `Fast`) ve **Line Delay** (satır arası bekleme: `3s`) belirleyin.
4. **Enter at EOL** modunuzu belirleyin (`Each Line`, `Except Last` veya `Disabled`).
5. Çalıştırma tercihinizi yapın:
   - **Adım Adım (`F2`)**: Tek tek satır işletmek için **`F2`** tuşuna veya **[ ⏭ STEP (F2) ]** butonuna basın.
   - **Otomatik (`F8`)**: Tüm satırları sırayla göndermek için **[ ▶ AUTO (F8) ]** butonuna tıklayın veya **`F8`** tuşuna basın (5 saniyelik sayaç içinde uzak konsola odaklanın).
6. İhtiyaç halinde dilediğiniz an **`F9`** tuşuna basarak yazmayı acil olarak durdurun.

| Kısayol | İşlem | Açıklama |
|:---:|:---:|---|
| **`F2`** | **Adım (Step)** | Tek bir satırı yazar, Enter'a basar ve duraklar |
| **`F8`** | **Otomatik (Auto)**| 5sn sayaç ile başlar, satır arası bekleme ile tüm satırları yazar |
| **`F9`** | **Durdur (Abort)** | Acil durdurma — tuş gönderimini derhal keser |
| **`Escape`** | **İptal** | Pencere odaktayken işlemi durdurur |
| **`Ctrl + A`** | **Tümünü Seç** | Editör içindeki metnin tamamını seçer |

---

### ❓ Sıkça Sorulan Sorular

#### Windows SmartScreen neden "Windows bilgisayarınızı korudu" uyarısı verdi?
İnternetten yeni indirilen ve henüz Microsoft bulutunda indirme sayısı birikmemiş bağımsız açık kaynaklı uygulamalarda bu uyarı standarttır.
- **"Ek bilgi"** → **"Yine de çalıştır"** seçeneğine tıklayarak uygulamayı başlatabilirsiniz.
- RemoteTyper tamamen açık kaynaklıdır; tüm kaynak kodları [`remotetyper.py`](remotetyper.py) dosyasında inceleyebilir veya kendi bilgisayarınızda PyInstaller ile derleyebilirsiniz.

#### Tuşlar hedef konsola yazılmıyor?
1. **Yönetici Olarak Çalıştırın**: Hedef uygulamanız (yönetici olarak açılmış PowerShell, uzak masaüstü veya sanallaştırma istemcisi) yönetici yetkileriyle çalışıyorsa, Windows güvenlik politikası (UIPI) gereği `RemoteTyper.exe` dosyasını da **"Yönetici olarak çalıştır"** seçeneği ile başlatmalısınız.
2. **Web Konsolları (Proxmox noVNC)**: Tarayıcı WebSocket kararlılığı için varsayılan **`Direct Type`** modunu ve **`Normal`** veya **`Slow`** hızını kullanın.

---

## 📄 Lisans

Bu proje **MIT Lisansı** ile lisanslanmıştır.

Geliştirici: **[@sinezty](https://github.com/sinezty)**
