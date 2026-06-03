import requests
import json
from dotenv import load_dotenv
import os
import pandas as pd
import concurrent.futures 
from clean import *

load_dotenv()

# 6NP_8NP: 10419458 # link dưới
# wild 9302648
wmc_id = 9302648

base_url = os.getenv("wmc_url")
wmc_url = f"{base_url}/{wmc_id}/children"
auth_header = os.getenv("auth_header")

headers = {
    'accept': 'application/json',
    'Content-type': 'application/json',
    'Authorization': auth_header
}

def get_top_folder(wmc_id):

    all_folders = []
    page = 1
    pageSize = 500
    print(f"Bắt đầu get folder trong Warning Message Catalogue {wmc_id}")
    while True:
        params = {"page": page, "pageSize": pageSize}
        response = requests.get(wmc_url, headers=headers, params=params)

        if response.status_code != 200:
            print(f"Error: {response.status_code} - {response.text}")
            break

        data = response.json()
        item_refs = data.get("itemRefs", data.get("items", []))
        if not item_refs:
            break # nếu trang đó không còn item nào thì dừng

        for item in item_refs:
            all_folders.append({"id":item["id"], "name": item["name"]})
        print(f"Đã quét xong page {page} với {len(item_refs)} folder")

        if len(all_folders) >= data.get("total", 0):
            break # nếu đã lấy đủ số lượng item thì dừng
        page += 1

    print(f"Done! Tổng số folder: {len(all_folders)}")
    return all_folders

# --- HÀM MỚI ĐƯỢC THÊM VÀO ĐỂ CHẠY ĐA LUỒNG ---
def get_single_item_detail(item_id):
    """Hàm phụ trách lấy chi tiết 1 item từ Database"""
    try:
        url = f"{base_url}/{item_id}"
        response = requests.get(url, headers=headers, timeout=15)
        if response.status_code == 200:
            return response.json()
        else:
            print(f"Lỗi ở item {item_id}: {response.status_code}")
            return None
    except Exception as e:
        print(f"Lỗi kết nối item {item_id}: {str(e)}")
        return None

def get_item(parent_id):
    """Hàm lấy tất cả item con kết hợp /children và đa luồng"""
    # Bước 1: Lấy danh sách ID con
    children_url = f"{base_url}/{parent_id}/children"
    page = 1
    pageSize = 500
    items_ref = []
    
    # print(f"Bắt đầu lấy ID các item con trong folder {parent_id}")
    while True:
        params = {"page": page, "pageSize": pageSize}
        response = requests.get(children_url, headers=headers, params=params)
        
        if response.status_code != 200:
            print(f"Lỗi API children: {response.status_code} - {response.text}")
            break
            
        data = response.json()
        current_items = data.get("items", data.get("itemRefs", []))
        
        if not current_items:
            break
            
        items_ref.extend(current_items)
        
        if len(items_ref) >= data.get("total", 0):
            break
        page += 1

    if not items_ref:
        print(f"Done 0 items in folder {parent_id}")
        return []

    # Bước 2: Bắn request song song để lấy chi tiết của danh sách ID vừa thu thập
    full_items = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        future_to_item = {
            executor.submit(get_single_item_detail, item["id"]): item["id"] 
            for item in items_ref
        }
        
        for future in concurrent.futures.as_completed(future_to_item):
            item_data = future.result()
            if item_data:
                full_items.append(item_data)
    
    full_items.sort(key=lambda x: x["id"])
                
    print(f"Done {len(full_items)} items in folder {parent_id}")
    return full_items

# issue name
issue_name_cache = {}
def get_issue_name(issue_id):
    if issue_id in issue_name_cache:
        return issue_name_cache[issue_id]
    
    try:
        url = f"{base_url}/{issue_id}"
        response = requests.get(url, headers=headers, timeout=10)

        if response.status_code == 200:
            data = response.json()
            raw_name = data.get("name")

            if raw_name:
                formatted_name = f"[{raw_name}]"
                issue_name_cache[issue_id] = formatted_name
                return formatted_name
            else:
                formated_name = f"[ISSUE:{issue_id}]"
                issue_name_cache[issue_id] = formated_name
                return formated_name
        else:
            print(f"Lỗi khi lấy tên issue {issue_id}: {response.status_code}")
    except Exception as e:
        print(f"Lỗi kết nối khi lấy tên issue {issue_id}: {str(e)}")
    
    return f"[ISSUE:{issue_id}]"
        
def resolve_issue_tags(text, item_id):
    """Tìm tất cả các chuỗi [ISSUE:xxx] trong đoạn text và thay thế bằng tên thật"""
    if not isinstance(text, str) or "[ISSUE:" not in text:
        return text
    
    pattern = r'\[ISSUE:(\d+)\]'
    
    def replacer(match):
        issue_id = match.group(1)
        print(f"\n[DEBUG] " + "="*50)
        print(f"[DEBUG] [ISSUE:{issue_id}]")
        print(f"[DEBUG] Thuộc: Item ID {item_id}")

        # Dùng repr() để in ra chuỗi nguyên thủy (hiển thị rõ cả ký tự xuống dòng \n, \r)
        print(f"[DEBUG] " + "="*50 + "\n")
        return get_issue_name(issue_id)
    
    return re.sub(pattern, replacer, text)



### EXPORT
def export_to_excel(folders_list):
    output_file = "VFVFWild_NP.xlsx"
    excel_rows = []
    
    column_order = [
        "ID",
        # "Folder Name",
        "Summary",
        "Type",
        "Warning Message ID",
        "Category",
        "Service Level",
        "Conditions to set warning (Reference)",
        "Conditions to show warning",
        "Conditions to clear warning",

        "Telltale Symbol",
        "Telltale Color",
        "Telltale Behavior",
        "Warning Message Icon",
        "Warning Message Icon Color",
        "Special Display",
        "Warning Message Icon ID",
        "Acoustic",
        "Timeframe",  

        "Warning Title-EN",  
        "Warning Content-EN",     
        "Full Warning Content-EN",
    ]

    print("Bắt đầu xuất dữ liệu ra Excel...")

    for index, folder in enumerate(folders_list):
        folder_id = folder["id"]
        folder_name = folder["name"]

        print(f"[{index+1}/{len(folders_list)}] Đang lấy dữ liệu cụm: {folder_name}")
        
        # 1. Tạo hàng đại diện cho Folder
        folder_row = {}
        for col in column_order:
            folder_row[col] = ""
        folder_row["ID"] = folder_id
        folder_row["Folder Name"] = folder_name
        folder_row["Type"] = "Folder"
        folder_row["Summary"] = folder_name

        excel_rows.append(folder_row)
        
        # 2. Gọi hàm lấy item con
        child_items = get_item(folder_id)

        # 3. Duyệt từng item con
        for item in child_items:
            cf_dict = {}
            for field in item.get("customFields", []):
                # Chuẩn hóa tên trường trong JSON về dạng viết thường để tra cứu
                name_in_json = str(field.get("name", "")).lower().strip()
                name_in_json = name_in_json.replace(" - ", "-").replace("- ", "-").replace(" -", "-")

                if "value" in field:
                    raw_text = clean_wiki(field["value"])
                    cf_dict[name_in_json] = resolve_issue_tags(raw_text, item.get("id"))
                elif "values" in field and field["values"]:
                    raw_text = clean_wiki(field["values"][0].get("name"))
                    cf_dict[name_in_json] = resolve_issue_tags(raw_text, item.get("id"))

            categories = item.get("categories", [])
            item_type = categories[0].get("name") if categories else ""

            item_row = {
                "ID": item.get("id"),
                "Summary": clean_wiki(item.get("name", "")),
                # "Folder Name": folder_name,
                "Type": item_type,  
                "Warning Message ID": cf_dict.get("warning message id", ""),
                "Category": cf_dict.get("category", ""),
                "Service Level": cf_dict.get("service level", ""),
                "Conditions to set warning (Reference)": cf_dict.get("conditions to set warning", ""),  
                "Conditions to show warning": cf_dict.get("conditions to show warning", ""),
                "Conditions to clear warning": cf_dict.get("conditions to clear warning", ""),
                "Telltale Symbol": cf_dict.get("telltale symbol", ""),
                "Telltale Color": cf_dict.get("telltale color", ""),
                "Telltale Behavior": cf_dict.get("telltale behavior", ""),
                "Warning Message Icon": cf_dict.get("warning message icon", ""),
                "Warning Message Icon Color": cf_dict.get("warning message icon color", ""),
                "Special Display": cf_dict.get("special display", ""),
                "Warning Message Icon ID": cf_dict.get("warning message icon id", ""),
                "Acoustic": cf_dict.get("acoustic", ""),
                "Timeframe": cf_dict.get("timeframe", ""),  

                "Warning Title-EN": cf_dict.get("warning title-en", ""),  
                "Warning Content-EN": cf_dict.get("warning content-en", ""),  
                "Full Warning Content-EN": cf_dict.get("full warning content-en", ""),
            }

            excel_rows.append(item_row)

        df = pd.DataFrame(excel_rows)
        df = df.reindex(columns=column_order)
        df.to_excel(output_file, index=False)

    print(f"\nDone! File Excel đúng định dạng cấu trúc cột đã xuất tại: {output_file}")

if __name__ == "__main__":

    all_top_folders = get_top_folder(wmc_id)
    is_test = False
    if all_top_folders:
        if is_test:
            only_first_folder = all_top_folders[:1]
            print(f"\n[TEST] Tiến hành xuất thử Excel cho cụm trước: {only_first_folder[0]['name']}")
            export_to_excel(only_first_folder)
        else:
            print(f"\nTiến hành xuất Excel cho tất cả {len(all_top_folders)} WMC...")
            export_to_excel(all_top_folders)