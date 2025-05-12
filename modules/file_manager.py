import os
import time

class FileManager:
    def __init__(self):
        """初始化 FileManager"""
        self.temp_dir = "temp"  # 相對路徑
        os.makedirs(self.temp_dir, exist_ok=True)
        
    def create_identifier(self):
        """創建時間戳識別碼"""
        return time.strftime("%Y%m%d_%H%M%S")
    
    def get_file_path(self, identifier, step, file_type):
        """
        獲取檔案路徑
        Args:
            identifier (str): 時間戳識別碼，例如 "20250512_152332"
            step (str): 步驟名稱，例如 "step1", "step2"
            file_type (str): 檔案類型，例如 "text", "audio.zip", "subtitle.srt"
        Returns:
            str: 檔案的相對路徑
        """
        filename = f"{identifier}_{step}_{file_type}"
        return os.path.join(self.temp_dir, filename)
    
    def get_latest_file(self, step, file_type):
        """
        獲取特定步驟和類型的最新檔案
        """
        if not os.path.exists(self.temp_dir):
            return None
            
        files = []
        for file in os.listdir(self.temp_dir):
            if f"_{step}_{file_type}" in file:
                files.append(file)
        
        if not files:
            return None
            
        # 根據檔名排序（因為包含時間戳，所以最後的檔案就是最新的）
        latest_file = sorted(files)[-1]
        return os.path.join(self.temp_dir, latest_file)
    
    def get_identifier_from_file(self, filepath):
        """
        從檔案路徑中提取識別碼
        """
        if not filepath:
            return None
        filename = os.path.basename(filepath)
        # 檔名格式：identifier_step_filetype
        return filename.split('_')[0]
