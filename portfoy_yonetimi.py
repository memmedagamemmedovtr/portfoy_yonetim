
from tvDatafeed import TvDatafeed, Interval
import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
import numpy as np
import math
import mplfinance as mpf
import time

plt.ion()  # interactive mode açıldı

tv = TvDatafeed()

portfoy_df = pd.DataFrame()

def yukle():
    global portfoy_df
    try:
        portfoy_df = pd.read_csv("portfoy.csv", parse_dates=["AlimTarihi"])
        # Eğer ArtanPara sütunu yoksa ekle
        if "ArtanPara" not in portfoy_df.columns:
            portfoy_df["ArtanPara"] = 0.0
    except FileNotFoundError:
        portfoy_df = pd.DataFrame(columns=["Sembol","AlimTarihi","Lot","AlisFiyati","SonFiyat",
                                          "Anapara","Bakiye","KarZararPct","GunSayisi","ArtanPara"])
    # Tip dönüşümleri
    portfoy_df = portfoy_df.astype({
        "Sembol": str,
        "AlimTarihi": 'datetime64[ns]',
        "Lot": int,
        "AlisFiyati": float,
        "SonFiyat": float,
        "Anapara": float,
        "Bakiye": float,
        "KarZararPct": float,
        "GunSayisi": int,
        "ArtanPara": float
    })
    print("Portföy dosyası yüklendi veya yeni portföy başlatıldı.")


def fiyat_getir(s):
    try:
        df = tv.get_hist(symbol=s, exchange='BIST', interval=Interval.in_daily, n_bars=1)
        if df.empty:
            print(f"Uyarı: {s} sembolü için veri bulunamadı.")
            return None
        return df['close'].iloc[-1]
    except Exception as e:
        print(f"Hata: {e}")
        return None

def portfoy_ekle():
    global portfoy_df
    while True:
        sembol = input("Hisse sembolü (bitirmek için boş bırak): ").upper().strip()
        if sembol == "":
            break

        son_fiyat = fiyat_getir(sembol)
        if son_fiyat is not None:
            print(f"{sembol} son fiyat: {son_fiyat:.2f} TRY")
            fiyat_kayit = input(f"Fiyatı kullan (E) / Manuel gir (H)? [E/H]: ").strip().upper()
            if fiyat_kayit == "H":
                try:
                    son_fiyat = float(input("Manuel fiyat girin: "))
                except:
                    print("Geçersiz fiyat girdiniz, son fiyat kullanılacak.")
        else:
            try:
                son_fiyat = float(input("Fiyat verisi bulunamadı, manuel fiyat girin: "))
            except:
                print("Geçersiz fiyat, işlem iptal edildi.")
                continue

        while True:
            secim = input("Lot sayısı (L) veya Tutar (T) girilecek? [L/T]: ").strip().upper()
            if secim == "L":
                try:
                    lot = int(float(input("Lot sayısını girin (tam sayı): ")))
                    tutar = lot * son_fiyat
                    artan_para = 0.0
                    break
                except:
                    print("Geçersiz sayı, tekrar deneyin.")
            elif secim == "T":
                try:
                    tutar = float(input("Toplam tutar girin (TRY): "))
                    lot = math.floor(tutar / son_fiyat)
                    # portfoy_ekle fonksiyonunda:
                    harcanan_tutar = lot * son_fiyat
                    artan_para = tutar - harcanan_tutar  # "artan_para" olmalı, "artan_para" yanlış yazılmış
                    print(f"Alınabilecek tam lot sayısı: {lot}, kullanılacak tutar: {harcanan_tutar:.2f} TRY, artan para: {artan_para:.2f} TRY")
                    break
                except:
                    print("Geçersiz tutar, tekrar deneyin.")
            else:
                print("L veya T girin.")

        tarih_str = input(f"Alım tarihi girin (YYYY-MM-DD) veya boş bırak güncel tarih için: ").strip()
        if tarih_str == "":
            alim_tarihi = pd.Timestamp(datetime.today())
        else:
            try:
                alim_tarihi = pd.Timestamp(datetime.strptime(tarih_str, "%Y-%m-%d"))
            except:
                print("Geçersiz tarih, bugünün tarihi kullanılacak.")
                alim_tarihi = pd.Timestamp(datetime.today())

        anapara = lot * son_fiyat
        bakiye = anapara
        kar_zarar = 0.0
        gun_sayisi = 0

        yeni_satir = {
            "Sembol": sembol,
            "AlimTarihi": alim_tarihi,
            "Lot": lot,
            "AlisFiyati": son_fiyat,
            "SonFiyat": son_fiyat,
            "Anapara": anapara,
            "Bakiye": bakiye,
            "KarZararPct": kar_zarar,
            "GunSayisi": gun_sayisi,
            "ArtanPara": artan_para
        }

        portfoy_df = pd.concat([portfoy_df, pd.DataFrame([yeni_satir])], ignore_index=True)
        print(f"{sembol} portföye eklendi.
")

def portfoy_guncelle():
    global portfoy_df
    bugun = pd.Timestamp(datetime.today())
    for i, row in portfoy_df.iterrows():
        sembol = row["Sembol"]
        son_fiyat = fiyat_getir(sembol)
        if son_fiyat is None:
            son_fiyat = row["SonFiyat"]
        portfoy_df.at[i, "SonFiyat"] = son_fiyat
        portfoy_df.at[i, "GunSayisi"] = (bugun - row["AlimTarihi"]).days
        portfoy_df.at[i, "Bakiye"] = son_fiyat * row["Lot"] + row["ArtanPara"]  # artan para portföyde tutuluyor
        portfoy_df.at[i, "KarZararPct"] = ((portfoy_df.at[i, "Bakiye"] - row["Anapara"]) / row["Anapara"]) * 100

def portfoy_listele():
    global portfoy_df
    print("
------ PORTFÖY DURUMU ------")
    if portfoy_df.empty:
        print("Portföyde hisse bulunmamaktadır.")
        return

    toplam_anapara = portfoy_df["Anapara"].sum()
    toplam_bakiye = (portfoy_df["Bakiye"]).sum()
    toplam_karzarar_pct = (toplam_bakiye - toplam_anapara) / toplam_anapara * 100 if toplam_anapara != 0 else 0

    # Lot tam sayı olarak göster
    print(portfoy_df[["Sembol","AlimTarihi","Lot","AlisFiyati","SonFiyat","GunSayisi","KarZararPct","Anapara","Bakiye","ArtanPara"]].to_string(index=False, formatters={
        'Lot': '{:.0f}'.format,
        'KarZararPct': '{:.2f}'.format,
        'AlisFiyati': '{:.2f}'.format,
        'SonFiyat': '{:.2f}'.format,
        'Anapara': '{:.2f}'.format,
        'Bakiye': '{:.2f}'.format,
        'ArtanPara': '{:.2f}'.format
    }))

    print("
PORTFÖY TOPLAMI:")
    print(f"Anapara: {toplam_anapara:.2f} TRY")
    print(f"Güncel Değer: {toplam_bakiye:.2f} TRY")
    print(f"Toplam % Kar/Zarar: {toplam_karzarar_pct:.2f} %")


def portfoy_sil():
    global portfoy_df
    confirm = input("Portföyü tamamen silmek istediğinize emin misiniz? (E/H): ").strip().upper()
    if confirm == "E":
        portfoy_df = portfoy_df.iloc[0:0]  # boş dataframe
        try:
            import os
            os.remove("portfoy.csv")
            print("Portföy dosyası silindi.")
        except FileNotFoundError:
            pass
        print("Portföy tamamen temizlendi.")
    else:
        print("Portföy silme işlemi iptal edildi.")


import mplfinance as mpf

def portfoy_hacimli_grafik():
    global portfoy_df

    if portfoy_df.empty:
        print("Portföyde hisse yok, grafik çizilemiyor.")
        return

    n_bars = 100  # çekilecek günlük bar sayısı

    for sembol in portfoy_df["Sembol"].unique():
        print(f"{sembol} için veri çekiliyor...")
        try:
            df = tv.get_hist(symbol=sembol, exchange='BIST', interval=Interval.in_daily, n_bars=n_bars)
            if df.empty:
                print(f"{sembol} için veri bulunamadı.")
                continue

            # mplfinance için tarih index zaten datetime olmalı, kontrol edelim:
            df.index.name = 'Date'
            df.index = pd.to_datetime(df.index)

            # Stil ayarı (isteğe bağlı)
            mc = mpf.make_marketcolors(up='g', down='r', edge='inherit', volume='in', wick='inherit')
            s  = mpf.make_mpf_style(marketcolors=mc, gridstyle="--")

            print(f"{sembol} grafiği çiziliyor...")
            mpf.plot(df,
                     type='candle',
                     style=s,
                     volume=True,
                     title=f"{sembol} - Günlük Hacimli Mum Grafik",
                     ylabel='Fiyat (TRY)',
                     ylabel_lower='Hacim',
                     mav=(5, 13, 21),  # opsiyonel hareketli ortalama
                     figsize=(12,8),
                     tight_layout=True)
            
        except Exception as e:
            print(f"{sembol} için grafik çizilirken hata: {e}")



def grafik_ciz():
    global portfoy_df
    if portfoy_df.empty:
        print("Grafik için portföyde veri yok.")
        return

    bugun = pd.Timestamp(datetime.today())
    gun_sayilari = []
    toplam_degerler = []

    min_gun = portfoy_df["AlimTarihi"].min()
    toplam_gun = (bugun - min_gun).days + 1
    tarih_listesi = [min_gun + timedelta(days=x) for x in range(toplam_gun)]

    for gun in tarih_listesi:
        toplam = 0
        for i, row in portfoy_df.iterrows():
            if gun >= row["AlimTarihi"]:
                toplam += row["SonFiyat"] * row["Lot"] + row["ArtanPara"]
        gun_sayilari.append(gun)
        toplam_degerler.append(toplam)

    plt.figure(figsize=(12,6))
    plt.plot(gun_sayilari, toplam_degerler, marker='o')
    plt.title("Portföy Günlük Toplam Değeri (Güncel Fiyatlarla)")
    plt.xlabel("Tarih")
    plt.ylabel("Toplam Değer (TRY)")
    plt.grid(True)
    plt.show(block=False)   # <-- block=False eklendi
    plt.pause(0.1)  # event loop’un tepki vermesi için kısa süre bekle


def kaydet():
    global portfoy_df
    portfoy_df.to_csv("portfoy.csv", index=False)
    print("Portföy dosyası kaydedildi.")

print("PORTFÖY YÖNETİM SİSTEMİ
")
yukle()

# Menüde 4. seçenek kaldırıldı, listelemeden sonra grafik çağrılıyor

while True:
    print("
Seçenekler:")
    print("1) Portföye hisse ekle")
    print("2) Portföyü güncelle")
    print("3) Portföyü listele ve grafik göster")
    print("4) Portföyü tamamen sil")
    print("5) Portföydeki tüm hisselerin hacimli mum grafiğini çiz")
    print("6) Kaydet")
    print("7) Çıkış")
    
    print("Seçim bekleniyor...")
    secim = input("Seçiminiz: ")
    print(f"Seçim alındı: {secim}")


    if secim == "1":
        portfoy_ekle()
    elif secim == "2":
        portfoy_guncelle()
        print("Portföy güncellendi.")
    elif secim == "3":
        portfoy_listele()
        grafik_ciz()
    elif secim == "4":
        portfoy_sil()
    elif secim == "5":
        portfoy_hacimli_grafik()
    elif secim == "6":
        kaydet()
    elif secim == "7":
        print("Programdan çıkılıyor...")
        break
    else:
        print("Geçersiz seçim, tekrar deneyin.")



print("Portföy yönetim kodu")
