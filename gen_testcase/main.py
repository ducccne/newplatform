import os
import sys
import time
from google.genai import types
from dotenv import load_dotenv
from google import genai

import data_processing as dp
import ai_handler as ai


RUN_MODE = "TEST"  # "TEST" hoặc "FULL"

TEST_START_INDEX = 30
TEST_END_INDEX = 35

if len(sys.argv) > 1:
    INPUT_FILE_PATH = sys.argv[1]
else:
    INPUT_FILE_PATH = r"C:/AI/NP/codebeamer/VFVFWild_NP.xlsx"

MAPPING_ICON_PATH = "mapping_icon.xlsx"
PROMPT_FILE_PATH = "prompt2.txt"
# OUTPUT_FILE_PATH = "Final_Testcases_Output.xlsx"

def get_next_output_file_name(base_name="VFVFWild_NP_TC", extension=".xlsx"):
    counter = 1
    while True:
        filename = f"{base_name}_{counter}{extension}"
        if not os.path.exists(filename):
            return filename
        counter += 1
        
OUTPUT_FILE_PATH = get_next_output_file_name()


client = genai.Client(
    api_key="sk-a5TCnYUmvwX9Hoh24gjUVXFn4vuT1R0KBVScwm1Adh7SXwLT",
    http_options=types.HttpOptions(
        base_url="https://llm.wokushop.com/v1beta/models/gemini-2.5-flash:generateContent"
    )
)




if __name__ == "__main__":

    # load_dotenv()
    # api_key = os.getenv("api_anh_tuan")
    # if not api_key:
    #     print("Khong tim thay API key")
    #     sys.exit(1)
        
    # client = genai.Client(api_key=api_key)
    
    if not os.path.exists(INPUT_FILE_PATH):
        print(f"Không tìm thấy tệp tin Excel tại: {INPUT_FILE_PATH}")
        sys.exit(1)

    start_time = time.time()
    
    # BƯỚC 1: Quét tọa độ radar động, gỡ cấu trúc ô gộp (nếu có) và dọn sạch mã rác văn bản
    df_clean = dp.load_excel_and_clean(INPUT_FILE_PATH, MAPPING_ICON_PATH)
    
    # BƯỚC 2: Dựng khung ma trận cây thư mục kiểm thử mẫu
    df_structure = dp.build_testcase_structure(df_clean, MAPPING_ICON_PATH)
    
    if RUN_MODE.upper() == "TEST":
        print(f"\nChế độ TEST từ {TEST_START_INDEX} đến {TEST_END_INDEX}...")
        df_structure = df_structure.iloc[TEST_START_INDEX:TEST_END_INDEX].copy()
        if df_structure.empty:
            print("Khoảng dòng kiểm thử bạn chọn nằm ngoài phạm vi dữ liệu tệp!")
            sys.exit(0)
    else:
        print(f"\nChế độ FULL: {len(df_structure)} hàng bản ghi sang cho AI...")
    
    df_final_testcases = ai.generate_testcases_with_ai(
        client=client, 
        df_structure=df_structure, 
        batch_size=5, # sua batch o day
        prompt_file_path=PROMPT_FILE_PATH
    )
    
    # BƯỚC 4: Xuất bản dữ liệu hoàn tất ra tệp Excel đích sạch sẽ
    df_final_testcases.to_excel(OUTPUT_FILE_PATH, index=False)
    
    print("\n======================================================================")
    print("DONE")
    print(f"Kết quả lưu tại: {os.path.abspath(OUTPUT_FILE_PATH)}")
    print(f"Tổng thời gian: {round(time.time() - start_time, 2)} giây.")
