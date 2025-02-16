import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime
import ttkbootstrap as ttk
from ttkbootstrap.constants import *
import socketio
import webbrowser
import socket
import qrcode
import os
import winsound
import threading
import math

class KafeYonetimSistemi:
    def __init__(self, root):
        self.root = root
        self.root.title("Modern Kafe Yönetim Sistemi")
        self.root.geometry("1200x800")
        
        # Ses dosyası yolu
        self.bildirim_sesi = os.path.join(os.path.dirname(__file__), "notification.wav")
        
        # Ses dosyasını oluştur
        self.ses_olustur()
        
        # Stil ayarları
        style = ttk.Style("darkly")
        
        # Socket.IO istemcisi
        self.sio = socketio.Client()
        self.sio.on('yeni_siparis', self.yeni_siparis_al)
        
        try:
            self.sio.connect('http://localhost:5000')
        except:
            print("Web sunucusuna bağlanılamadı!")
        
        # QR kod oluştur
        self.qr_kod_olustur()
        
        # İçecek menüsü ve fiyatları
        self.menu = {
            "Türk Kahvesi": 90,
            "Latte": 120,
            "Espresso": 80,
            "Cappuccino": 100,
            "Americano": 90,
            "Çay": 40,
            "Sıcak Çikolata": 90,
            "Limonata": 100,
            "Ice Tea": 80,
            "Frappe": 120
        }
        
        # Masa durumları
        self.masalar = {f"Masa {i+1}": False for i in range(20)}  # False = boş, True = dolu
        self.masa_siparisleri = {f"Masa {i+1}": [] for i in range(20)}
        self.masa_butonlari = {}  # Masa butonlarını saklamak için
        
        self.secili_masa = None
        self.create_widgets()
        
    def create_widgets(self):
        # Ana container
        main_container = ttk.Frame(self.root)
        main_container.pack(fill=BOTH, expand=True, padx=10, pady=10)
        
        # Sol panel - Masalar
        masa_frame = ttk.LabelFrame(main_container, text="Masalar", padding="10")
        masa_frame.pack(side=LEFT, fill=BOTH, expand=True, padx=5)
        
        # Masaları grid şeklinde yerleştir
        masa_container = ttk.Frame(masa_frame)
        masa_container.pack(fill=BOTH, expand=True)
        
        for i, (masa, dolu) in enumerate(self.masalar.items()):
            row = i // 5
            col = i % 5
            btn = ttk.Button(
                masa_container,
                text=masa,
                style="success.TButton" if not dolu else "danger.TButton",
                command=lambda m=masa: self.masa_sec(m)
            )
            btn.grid(row=row, column=col, padx=5, pady=5, sticky="nsew")
            self.masa_butonlari[masa] = btn  # Butonu sözlüğe kaydet
        
        # Grid yapılandırması
        for i in range(5):
            masa_container.grid_columnconfigure(i, weight=1)
        for i in range(4):
            masa_container.grid_rowconfigure(i, weight=1)
            
        # Orta panel - Menü ve işlemler
        orta_panel = ttk.Frame(main_container)
        orta_panel.pack(side=LEFT, fill=BOTH, expand=True, padx=5)
        
        # Menü
        menu_frame = ttk.LabelFrame(orta_panel, text="Menü", padding="10")
        menu_frame.pack(fill=BOTH, expand=True, pady=(0, 5))
        
        # Menü listesi için çoklu seçim özelliği ekle
        self.menu_listbox = ttk.Treeview(menu_frame, columns=("urun", "fiyat"), show="headings", height=10, selectmode="extended")
        self.menu_listbox.heading("urun", text="Ürün")
        self.menu_listbox.heading("fiyat", text="Fiyat")
        self.menu_listbox.column("urun", width=150)
        self.menu_listbox.column("fiyat", width=100, anchor=CENTER)
        
        for item, fiyat in self.menu.items():
            self.menu_listbox.insert("", END, values=(item, f"{fiyat} denar"))
        
        scrollbar = ttk.Scrollbar(menu_frame, orient=VERTICAL, command=self.menu_listbox.yview)
        self.menu_listbox.configure(yscrollcommand=scrollbar.set)
        
        self.menu_listbox.pack(side=LEFT, fill=BOTH, expand=True)
        scrollbar.pack(side=RIGHT, fill=Y)
        
        # İşlem butonları
        islem_frame = ttk.LabelFrame(orta_panel, text="İşlemler", padding="10")
        islem_frame.pack(fill=X, pady=5)
        
        ttk.Button(islem_frame, text="Sipariş Ekle", style="primary.TButton", 
                  command=self.siparis_ekle).pack(pady=5, fill=X)
        ttk.Button(islem_frame, text="Siparişi İptal Et", style="warning.TButton",
                  command=self.siparis_iptal).pack(pady=5, fill=X)
        ttk.Button(islem_frame, text="Hesap Al", style="info.TButton",
                  command=self.hesap_al).pack(pady=5, fill=X)
        
        # Sağ panel - Aktif siparişler
        siparis_frame = ttk.LabelFrame(main_container, text="Aktif Siparişler", padding="10")
        siparis_frame.pack(side=LEFT, fill=BOTH, expand=True, padx=5)
        
        self.siparis_listbox = ttk.Treeview(siparis_frame, columns=("urun", "saat"), show="headings", height=15)
        self.siparis_listbox.heading("urun", text="Ürün")
        self.siparis_listbox.heading("saat", text="Saat")
        self.siparis_listbox.column("urun", width=150)
        self.siparis_listbox.column("saat", width=100, anchor=CENTER)
        
        scrollbar_siparis = ttk.Scrollbar(siparis_frame, orient=VERTICAL, command=self.siparis_listbox.yview)
        self.siparis_listbox.configure(yscrollcommand=scrollbar_siparis.set)
        
        self.siparis_listbox.pack(side=LEFT, fill=BOTH, expand=True)
        scrollbar_siparis.pack(side=RIGHT, fill=Y)
        
    def masa_sec(self, masa):
        self.secili_masa = masa
        self.siparis_listbox.delete(*self.siparis_listbox.get_children())
        for siparis in self.masa_siparisleri[masa]:
            self.siparis_listbox.insert("", END, values=(siparis["urun"], siparis["saat"]))
        
        # Masa başlığını güncelle
        self.root.title(f"Modern Kafe Yönetim Sistemi - {masa}")
        
    def masa_renk_guncelle(self, masa):
        # Masa butonunun rengini güncelle
        if masa in self.masa_butonlari:
            if self.masa_siparisleri[masa]:  # Masada sipariş varsa
                self.masa_butonlari[masa].configure(style="danger.TButton")
                self.masalar[masa] = True
            else:  # Masa boşsa
                self.masa_butonlari[masa].configure(style="success.TButton")
                self.masalar[masa] = False
        
    def siparis_ekle(self):
        if not self.secili_masa:
            messagebox.showwarning("Uyarı", "Lütfen önce bir masa seçin!")
            return
            
        selections = self.menu_listbox.selection()  # Çoklu seçimleri al
        if selections:
            for selection in selections:
                secili_urun = self.menu_listbox.item(selection)["values"][0]  # Artık direkt ürün adını alıyoruz
                
                siparis = {
                    "urun": secili_urun,
                    "saat": datetime.now().strftime('%H:%M')
                }
                
                self.masa_siparisleri[self.secili_masa].append(siparis)
                self.siparis_listbox.insert("", END, values=(secili_urun, siparis["saat"]))
            
            # Masa rengini güncelle
            self.masa_renk_guncelle(self.secili_masa)
            
            messagebox.showinfo("Başarılı", f"{self.secili_masa} için {len(selections)} adet sipariş eklendi!")
        else:
            messagebox.showwarning("Uyarı", "Lütfen menüden en az bir ürün seçin!")
            
    def siparis_iptal(self):
        if not self.secili_masa:
            messagebox.showwarning("Uyarı", "Lütfen önce bir masa seçin!")
            return
            
        selection = self.siparis_listbox.selection()
        if selection:
            for item in selection:
                self.siparis_listbox.delete(item)
                if self.masa_siparisleri[self.secili_masa]:
                    self.masa_siparisleri[self.secili_masa].pop(0)
            
            # Masa rengini güncelle
            self.masa_renk_guncelle(self.secili_masa)
            
            messagebox.showinfo("Başarılı", "Seçili siparişler iptal edildi!")
        else:
            messagebox.showwarning("Uyarı", "Lütfen iptal edilecek siparişleri seçin!")
            
    def hesap_al(self):
        if not self.secili_masa:
            messagebox.showwarning("Uyarı", "Lütfen önce bir masa seçin!")
            return
            
        if not self.masa_siparisleri[self.secili_masa]:
            messagebox.showwarning("Uyarı", "Bu masada aktif sipariş bulunmamaktadır!")
            return
            
        # Detaylı hesap özeti oluştur
        ozet = f"{self.secili_masa} Hesap Özeti:\n\n"
        toplam_tutar = 0
        
        # Siparişleri grupla ve say
        siparis_sayilari = {}
        for siparis in self.masa_siparisleri[self.secili_masa]:
            urun = siparis["urun"]
            if urun in siparis_sayilari:
                siparis_sayilari[urun] += 1
            else:
                siparis_sayilari[urun] = 1
        
        # Özete ekle
        for urun, adet in siparis_sayilari.items():
            birim_fiyat = float(self.menu[urun])  # Menu fiyatını float'a çevir
            ara_toplam = birim_fiyat * adet
            toplam_tutar += ara_toplam
            ozet += f"{urun} x {adet} = {ara_toplam:.2f}₺\n"
        
        ozet += f"\nToplam Sipariş Adedi: {len(self.masa_siparisleri[self.secili_masa])}\n"
        ozet += f"Toplam Tutar: {toplam_tutar:.2f}₺"
        
        messagebox.showinfo("Hesap Bilgisi", ozet)
        
        # Masayı temizle
        self.masa_siparisleri[self.secili_masa] = []
        self.siparis_listbox.delete(*self.siparis_listbox.get_children())
        
        # Masa rengini güncelle
        self.masa_renk_guncelle(self.secili_masa)
    
    def qr_kod_olustur(self):
        try:
            # Yerel IP adresini al
            hostname = socket.gethostname()
            local_ip = socket.gethostbyname(hostname)
            
            # QR kod için URL
            url = f"http://{local_ip}:5000"
            
            # QR kod oluştur
            qr = qrcode.QRCode(version=1, box_size=10, border=5)
            qr.add_data(url)
            qr.make(fit=True)
            
            # QR kodu kaydet
            if not os.path.exists('static'):
                os.makedirs('static')
            img = qr.make_image(fill_color="black", back_color="white")
            img.save("static/qr_code.png")
            
            # QR kodu göster butonu ekle
            ttk.Button(
                self.root,
                text="QR Kodu Göster",
                style="info.TButton",
                command=lambda: webbrowser.open("http://127.0.0.1:5000/static/qr_code.png")
            ).pack(pady=10)
            
        except Exception as e:
            print(f"QR kod oluşturma hatası: {e}")
    
    def ses_olustur(self):
        # Windows için varsayılan bildirim sesi
        if not os.path.exists(self.bildirim_sesi):
            import wave
            import struct
            import math
            
            # Basit bir bip sesi oluştur
            sampleRate = 44100
            duration = 0.5  # saniye
            frequency = 440.0  # Hz
            
            wavef = wave.open(self.bildirim_sesi, 'w')
            wavef.setnchannels(1)
            wavef.setsampwidth(2)
            wavef.setframerate(sampleRate)
            
            for i in range(int(duration * sampleRate)):
                # Sinüs dalgası oluştur
                value = int(32767.0 * math.sin(2 * math.pi * frequency * i / sampleRate))
                data = struct.pack('<h', value)
                wavef.writeframesraw(data)
            
            wavef.close()
    
    def ses_cal(self):
        # Sesi ayrı bir thread'de çal
        def play():
            try:
                winsound.PlaySound(self.bildirim_sesi, winsound.SND_FILENAME)
            except Exception as e:
                print(f"Ses çalma hatası: {e}")
        
        threading.Thread(target=play, daemon=True).start()
    
    def yeni_siparis_al(self, data):
        try:
            masa_no = data['masa_no']
            siparisler = data['siparisler']
            saat = data['saat']
            
            # Her bir siparişi ekle
            for siparis in siparisler:
                urun = siparis['urun']
                adet = siparis.get('adet', 1)
                
                for _ in range(adet):
                    yeni_siparis = {
                        "urun": urun,
                        "saat": saat
                    }
                    
                    self.masa_siparisleri[masa_no].append(yeni_siparis)
                    if self.secili_masa == masa_no:
                        self.siparis_listbox.insert("", END, values=(urun, saat))
            
            # Masa rengini güncelle
            self.masa_renk_guncelle(masa_no)
            
            # Bildirim sesi çal
            self.ses_cal()
            
            # Bildirim göster
            messagebox.showinfo("Yeni Sipariş", f"{masa_no} için yeni sipariş alındı!")
            
        except Exception as e:
            print(f"Sipariş işleme hatası: {e}")
    
    def __del__(self):
        try:
            self.sio.disconnect()
        except:
            pass

if __name__ == "__main__":
    root = ttk.Window()
    app = KafeYonetimSistemi(root)
    root.mainloop() 