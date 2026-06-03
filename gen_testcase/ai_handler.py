import time
import json
import re
import pandas as pd
from google import genai
from google.genai import types


def remove_excel_illegal_chars(val):
    if isinstance(val, str):
        val = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]', '', val)
        if val.strip().startswith('=') and not val.strip().startswith('=HYPERLINK'): val = "'" + val.strip()
    return val


def extract_clean_json_array(raw_text):
    raw_text = raw_text.strip()
    start_idx = raw_text.find('[')
    if start_idx == -1:
        return raw_text  # Không tìm thấy mảng, trả về nguyên bản để json.loads báo lỗi gốc
    
    bracket_count = 0
    in_string = False
    escape_active = False
    
    for i in range(start_idx, len(raw_text)):
        char = raw_text[i]
        
        # Bỏ qua ký tự escape (ví dụ: \") bên trong chuỗi text
        if escape_active:
            escape_active = False
            continue
        if char == '\\':
            escape_active = True
            continue
            
        # Kiểm tra xem có đang nằm trong dấu chuỗi văn bản không
        if char == '"':
            in_string = not in_string
            continue
            
        # Nếu nằm ngoài chuỗi văn bản thì mới đếm ngoặc vuông
        if not in_string:
            if char == '[':
                bracket_count += 1
            elif char == ']':
                bracket_count -= 1
                # Khi mảng bự nhất đóng lại hoàn toàn, cắt bỏ toàn bộ phần thừa phía sau
                if bracket_count == 0:
                    return raw_text[start_idx:i+1]
                    
    return raw_text


def call_ai_batch(client, batch_rows, prompt_file_path="prompt.txt"):
    input_data = []
    for row in batch_rows:
        def clean(v): return "" if (pd.isna(v) or str(v).lower().strip() in ['nan', 'null', 'n/a', '']) else str(v).strip()
        input_data.append({
            "Task_ID": clean(row.get('Task_ID')),
            "Req_ID": clean(row.get('ID Requirement')),
            "Warning_Msg_ID": clean(row.get('Warning message ID')),
            "Name": clean(row.get('FIF_Summary')),
            "Timeframe": clean(row.get('Timeframe')),
            "Requirement": clean(row.get('Set requirement for Head Unit')),
            "Condition_to_clear_warning": clean(row.get('Conditions to clear warning')),
            "Title": clean(row.get('Warning title - EN (New)')),
            "Content": clean(row.get('Warning content - EN (New)')),
            "Full_Content": clean(row.get('Full Warning Content - EN (New)')),
            "Icon": clean(row.get('Warning message icon')),
            "Icon_id": clean(row.get('Warning message icon ID')),
            "Acoustic": clean(row.get('Warning acoustic signal (New)')),
            "Telltale_Symbol":   clean(row.get('Telltale Symbol')),
            "Telltale_Behavior": clean(row.get('Telltale Behavior')),
        })

    try:
        with open(prompt_file_path, "r", encoding="utf-8") as f: prompt_template = f.read()
        prompt = prompt_template.replace("__BATCH_COUNT__", str(len(batch_rows))).replace("__INPUT_DATA_PLACEHOLDER__", json.dumps(input_data, ensure_ascii=False, indent=2))
    except FileNotFoundError:
        print(f"Không tìm thấy file prompt tại đường dẫn: {prompt_file_path}")
        return []
        
    for attempt in range(3):
        try:
            response = client.models.generate_content(
                model="gemini-3.1-flash-lite", contents=prompt,
                config=types.GenerateContentConfig(response_mime_type="application/json",
                                                   temperature=0.2)
            )
            
            clean_json_text = extract_clean_json_array(response.text)
            return json.loads(clean_json_text)





        except Exception as e:
            error_msg = str(e)
            error_type = type(e).__name__ # Lấy tên loại lỗi (VD: APIError, ResourceExhausted...)
            if "JSONDecodeError" in error_msg or "JSONDecodeError" in error_type:
                # Lấy ID của hàng đầu và hàng cuối trong batch để đặt tên file cho dễ tìm
                start_id = batch_rows[0].get('Task_ID', 'start')
                end_id = batch_rows[-1].get('Task_ID', 'end')
                file_debug_name = f"debug_error_batch_{start_id}_to_{end_id}.txt"
                
                with open(file_debug_name, "w", encoding="utf-8") as f:
                    f.write(f"--- CHI TIẾT LỖI ---\n{error_msg}\n\n")
                    f.write(f"--- DỮ LIỆU THÔ AI TRẢ VỀ (RAW TEXT) ---\n")
                    f.write(response.text) # Ghi lại toàn bộ những gì AI viết ra
                print(f"Đã xuất file dữ liệu lỗi để kiểm tra: {file_debug_name}")
            # =========================================================================

            # Dùng next() để bắt chính xác từ khóa nào đã xuất hiện thay vì dùng any()
            keywords = ["503", "UNAVAILABLE", "ResourceExhausted", "429"]

            matched_keyword = next((k for k in keywords if k in error_msg), None)

            if matched_keyword:
                delay = 3 * (2 ** attempt)
                print(f"[Attempt {attempt+1}/3] API bị chặn do lỗi '{matched_keyword}' [{error_type}].")
                print(f"Chi tiết: {error_msg}")
                print(f"Đang thử lại sau {delay}s...")
                time.sleep(delay)
            else:
                # Nếu không phải lỗi Rate Limit/Quá tải thì in ra đỏ chót và dừng luôn
                print(f"API Error nghiêm trọng [{error_type}]: {error_msg}")
                break
        return []

def generate_testcases_with_ai(client, df_structure, batch_size=5, prompt_file_path="prompt.txt"):
    """Đẩy khối dữ liệu sang AI thiết kế kịch bản chi tiết và quản lý mảng cấu trúc cuối cùng."""
    final_rows = []
    records = df_structure.to_dict('records')
    
    for i in range(0, len(records), batch_size):
        batch = records[i : i + batch_size]
        print(f"--> [AI Handler]: Đang xử lý theo batch: Hàng {i+1} đến {min(i + batch_size, len(records))} / Tổng {len(records)}...")
        ai_results = call_ai_batch(client, batch, prompt_file_path)
        
        ai_dict = {}
        if isinstance(ai_results, list):
            for item in ai_results:
                if item.get('Task_ID'): ai_dict[str(item['Task_ID'])] = item.get('test_cases', [])

        for row in batch:
            task_id = str(row.get('Task_ID', ''))
            ai_generated_list = ai_dict.get(task_id, [])
            
            # ─── LỚP PHÒNG VỆ CHỐNG SÓT KỊCH BẢN (FALLBACK) ───
            if not ai_generated_list:
                msg_id = str(row.get('Warning message ID', '')).replace('nan', '')
                if not msg_id or msg_id.lower() == 'nan': msg_id = "Warning"
                req = str(row.get('Set requirement for Head Unit', '')).replace('nan', '')
                title, content = str(row.get('Warning title - EN (New)', '')).replace('nan', ''), str(row.get('Warning content - EN (New)', '')).replace('nan', '')
                
                fallback_row = row.copy()
                fallback_row['Program'] = fallback_row['Market'] = 'All'
                fallback_row['Test Purpose'] = f"Verify warning {row.get('FIF_Summary', '')}"
                fallback_row['Pre-Action'] = f"1. MHU is ON\n2. Timeframe: {row.get('Timeframe', '')}"
                
                if "precondition" in req.lower() or "if " in req.lower():
                    fallback_row['Test Steps.Action'] = f"1. Check Precondition\n2. Set error: {req.strip()}\n3. Unset to normal"
                    fallback_row['Test Steps.Expected result'] = f"1. \n2. Warning {msg_id} is displayed;\n**Warning title:** \"{title}\"\n**Warning content:** \"{content}\"\n3. Warning cleared"
                else:
                    fallback_row['Test Steps.Action'] = f"1. Set error: {req.strip()}\n2. Unset to normal"
                    fallback_row['Test Steps.Expected result'] = f"1. Warning {msg_id} is displayed;\n**Warning title:** \"{title}\"\n**Warning content:** \"{content}\"\n2. Warning cleared"
                final_rows.append(fallback_row)
                continue
            
            # ─── GHI KẾT QUẢ AI SINH THÀNH CÔNG ───
            for ai_tc in ai_generated_list:
                new_row = row.copy()
                new_row['Program'] = ai_tc.get('Program', row.get('Program', 'All'))
                new_row['Market'] = ai_tc.get('Market', row.get('Market', 'All'))
                new_row['Test Purpose'] = ai_tc.get('Test_Purpose', f"Verify warning {row.get('FIF_Summary', '')}")
                new_row['Pre-Action'] = ai_tc.get('Pre_Action', '')
                new_row['Test Steps.Action'] = ai_tc.get('Action', '')
                new_row['Test Steps.Expected result'] = ai_tc.get('Expected_Result', '')
                final_rows.append(new_row)
                
        time.sleep(2)
        
    df_final = pd.DataFrame(final_rows)

    # Tự động Re-build cấu trúc Hyperlink sang file Requirement gốc của hệ thống
    def build_excel_hyperlink(r):
        req_id, link_target = str(r.get('ID Requirement', '')).strip(), str(r.get('_ID_Hyperlink_Target', '')).strip()
        if req_id.endswith('.0'): req_id = req_id[:-2]
        return f'=HYPERLINK("{link_target}", "{req_id}")' if (link_target and link_target != 'nan') else req_id

    if not df_final.empty: df_final['ID Requirement'] = df_final.apply(build_excel_hyperlink, axis=1)
    df_final = df_final.map(remove_excel_illegal_chars) if hasattr(df_final, 'map') else df_final.applymap(remove_excel_illegal_chars)
    
    desired_columns = [
        "ID Requirement", "Functional Level 1", "FIP_ID", "FIP_ID & Summary", "FIF_Summary", "Priority", 
        "Environment", "Vehicle Status", "Power State", "Test Purpose", "Name", "Pre-Action", 
        "Test Steps.Action", "Test Steps.Expected result", "Precondition signal", "Test Steps.signal input CAN/Lin signal", "Variant", "Market", "Program"
    ]
    return df_final[[c for c in desired_columns if c in df_final.columns]]