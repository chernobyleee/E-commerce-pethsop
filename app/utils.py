# Contoh di app/utils.py
from urllib.parse import quote_plus
from flask import current_app # Untuk mengambil nama toko dari config jika ada

def generate_whatsapp_refund_link(order, customer_phone_number):
    if not customer_phone_number:
        return None

    # Pastikan nomor telepon dalam format internasional tanpa '+' atau spasi
    # Anda mungkin perlu logika pembersihan nomor telepon di sini
    # Contoh sederhana:
    if customer_phone_number.startswith('0'):
        customer_phone_number = '62' + customer_phone_number[1:]
    elif customer_phone_number.startswith('+62'):
        customer_phone_number = customer_phone_number.replace('+', '')

    # Hapus karakter non-digit selain di awal (misal spasi atau strip)
    customer_phone_number = ''.join(filter(str.isdigit, customer_phone_number))
    if not customer_phone_number.startswith('62'): # Jika setelah dibersihkan tidak ada 62
         if len(customer_phone_number) > 9 and len(customer_phone_number) < 15: # Cek panjang wajar
             customer_phone_number = '62' + customer_phone_number


    shop_name = current_app.config.get('SHOP_NAME', "PePETSHOP") # Ambil dari config
    admin_contact = current_app.config.get('SHOP_ADMIN_WHATSAPP', "087887676435") # Nomor WA admin jika perlu

    message_template = f""" Halo Kak {order.customer.name if order.customer else 'Pelanggan'},Kami dari {shop_name}.
                            Kami telah menerima dan memproses permintaan pembatalan untuk pesanan Anda dengan detail berikut:
                            Nomor Invoice: {order.invoice_number}
                            Total Pembayaran: Rp {order.total:,.0f}
                            Proses pengembalian dana (refund) akan segera kami lakukan. Untuk kelancaran proses, mohon konfirmasi data berikut:

                            Nama Pemilik Rekening:
                            Nama Bank:
                            Nomor Rekening:
                            Atau, jika Anda memiliki preferensi metode pengembalian dana lain (misalnya e-wallet), silakan informasikan kepada kami beserta detail yang diperlukan.

                            Kami akan memproses pengembalian dana Anda dalam waktu [misalnya: 1-3 hari kerja] setelah kami menerima konfirmasi data dari Anda.

                            Mohon maaf atas ketidaknyamanannya dan terima kasih atas pengertiannya.

                            Salam,
                            Tim {shop_name}
                            """
                            # Jika ingin admin mengirimkan dari nomornya sendiri, teksnya mungkin sedikit berbeda,
                            # atau link ini untuk admin agar bisa langsung chat ke pelanggan.

    encoded_message = quote_plus(message_template)
    whatsapp_link = f"https://wa.me/{customer_phone_number}?text={encoded_message}"
    return whatsapp_link





