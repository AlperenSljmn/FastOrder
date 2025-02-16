from flask import Flask, render_template, request, jsonify
from flask_socketio import SocketIO
import qrcode
from datetime import datetime
import json
import os

app = Flask(__name__)
socketio = SocketIO(app)

# Menü
MENU = {
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

def create_qr():
    # Sunucu IP adresini al (gerçek uygulamada kendi IP adresinizi kullanın)
    server_url = "http://localhost:5000"
    
    # QR kod oluştur
    qr = qrcode.QRCode(version=1, box_size=10, border=5)
    qr.add_data(server_url)
    qr.make(fit=True)
    
    # QR kodu kaydet
    img = qr.make_image(fill_color="black", back_color="white")
    img.save("static/qr_code.png")

@app.route('/')
def index():
    return render_template('index.html', menu=MENU)

@app.route('/siparis', methods=['POST'])
def siparis_al():
    data = request.json
    masa_no = data.get('masa_no')
    siparisler = data.get('siparisler', [])
    
    # Siparişi işle ve masaüstü uygulamasına bildir
    siparis_bilgisi = {
        'masa_no': masa_no,
        'siparisler': siparisler,
        'saat': datetime.now().strftime('%H:%M')
    }
    
    # WebSocket ile masaüstü uygulamasına bildir
    socketio.emit('yeni_siparis', siparis_bilgisi)
    
    return jsonify({'success': True, 'message': 'Sipariş alındı'})

if __name__ == '__main__':
    # Static klasörü oluştur
    if not os.path.exists('static'):
        os.makedirs('static')
    
    # QR kodu oluştur
    create_qr()
    
    # Sunucuyu başlat
    socketio.run(app, debug=True, host='0.0.0.0') 