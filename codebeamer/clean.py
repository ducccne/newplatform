import re

import re

import re

def clean_wiki(text):
    if not isinstance(text, str):
        return text
    
    # 1. Bóc tách thẻ [! ... !] ra khỏi chuỗi [{Image...}]
    text = re.sub(r'\[\{\s*Image.*?(\[!.*?!\]).*?\}\]', r'\1', text, flags=re.DOTALL)
    
    # 2. Xóa mã hash thừa: Đổi [!image.png#hash!] thành [!image.png!]
    text = re.sub(r'(\[!.*?)(#[^!]+)(!\])', r'\1\3', text)
    
    # 3. Xóa các khối [{ ... }] thừa khác nếu có
    text = re.sub(r'\[\{.*?\}\]', '', text, flags=re.DOTALL)
    
    # ---------------------------------------------------------
    # 3.5. XỬ LÝ CHỮ BỊ GẠCH NGANG AN TOÀN TUYỆT ĐỐI
    # Thay vì cố gắng match cả khối lớn, ta tìm chính xác thẻ mở chứa 'line-through' 
    # và tìm thẻ đóng '%!' tương ứng với nó để xóa toàn bộ nội dung bên trong.
    
    # Kỹ thuật: Phá vỡ từng cặp thẻ từ trong ra ngoài để tránh lỗi khi lồng nhau
    while re.search(r'%%\([^)]*line-through[^)]*\)', text, flags=re.IGNORECASE):
        # Biểu thức này tìm một thẻ line-through mở, theo sau là bất kỳ text nào (không chứa thẻ mở '%%(' khác), 
        # và kết thúc bằng thẻ đóng '%!'. 
        # Nó sẽ xóa phần lõi trong cùng trước, sau đó vòng lặp quay lại xóa các lớp bên ngoài.
        text_before = text
        text = re.sub(r'%%\([^)]*line-through[^)]*\)(?:(?!%%\().)*?%!', '', text, flags=re.IGNORECASE | re.DOTALL)
        
        # Đề phòng vòng lặp vô hạn nếu cấu trúc Wiki bị lỗi (thiếu thẻ đóng)
        if text == text_before:
            # Nếu regex trên không bắt được cặp đóng mở hợp lệ, ta phải dùng cách "bạo lực" hơn một chút
            # Xóa thẻ mở line-through và nội dung tới thẻ đóng '%!' đầu tiên nó thấy
            text = re.sub(r'%%\([^)]*line-through[^)]*\).*?%!', '', text, count=1, flags=re.IGNORECASE | re.DOTALL)
            break 
    # ---------------------------------------------------------
    
    # 4. FIX LỖI THẺ CSS (Bản chốt hạ không trượt phát nào)
    # Ràng buộc chặt chẽ: Chỉ kết thúc khi gặp dấu ')' không nằm trong thẻ lồng nào khác
    text = re.sub(r'%%\((?:[^)(]+|\([^)(]*\))*\)', '', text)
    
    # 4.2 Xóa sạch các thẻ đóng của CSS (%! hoặc %%)
    text = text.replace('%!', '')
    text = re.sub(r'%%(?!\()', '', text) 
    
    # 5. Loại bỏ dấu '~' dùng để escape các ký tự đặc biệt
    text = re.sub(r'~([^a-zA-Z0-9\s])', r'\1', text)
    
    # 5.1 Xóa dấu gạch chéo ngược (thẻ ép dòng của Wiki)
    text = re.sub(r'\\+', '\n', text)
    
    # 5.2 Xóa thẻ in đậm/gạch chân '__' (nhưng giữ lại '_' đơn lẻ)
    text = text.replace('__', '')
    
    # 5.3 Dọn dẹp các ký tự list (#, *, -, chữ số) mồ côi nằm trơ trọi do text đã bị xóa
    text = re.sub(r'^[#*\-\d.]+\s*$', '', text, flags=re.MULTILINE)
    
    # 6. DỌN DẸP DÒNG TRỐNG TRIỆT ĐỂ
    text = re.sub(r'\s*\n\s*', '\n', text)
    
    return text.strip()


if __name__ == "__main__":
    sample_text = """%%(text-decoration:line-through;)When following conditions are satisfied:%!\r\n\r\n# %%(text-decoration:line-through;)LDML~_ControllerSts == 0x0 \"Normal\"%!\r\n# %%(text-decoration:line-through;)LDMR~_ControllerSts == 0x0 \"Normal\"%!"""

    print("--- KẾT QUẢ SAU KHI LÀM SẠCH ---")
    print(clean_wiki(sample_text))