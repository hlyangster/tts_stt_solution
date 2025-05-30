import os
import sys
sys.path.append(os.path.abspath(os.path.dirname(__file__)))
# 導入 OpenAI 補丁
from modules.openai_patch import patch_openai
import gradio as gr
import json
import time
import zipfile
import tempfile
from pathlib import Path

# 確保可以導入專案模組
sys.path.append(os.path.abspath(os.path.dirname(__file__)))

from modules.text_preprocessing import preprocess_text, PreprocessingError
from modules.homophone_replacement import HomophoneReplacer
from modules.tts_generator import TTSGenerator, TTSGenerationError
from modules.subtitle_corrector import SubtitleCorrector
from modules.srt_generator import SRTGenerator
from modules.audio_merge import AudioMerger, AudioMergeError
from modules import TTS_VOICES, TTS_EMOTIONS
from modules.file_manager import FileManager

# 初始化檔案管理器
file_manager = FileManager()

# 檔案路徑設置
current_dir = Path(__file__).parent
data_dir = current_dir / "data"
dictionary_path = data_dir / "default_dictionary.json"

# 確保資料目錄存在
os.makedirs(data_dir, exist_ok=True)

# 如果字典檔案不存在，創建預設字典
if not dictionary_path.exists():
    try:
        # 從現有字典文件創建
        original_dict_path = current_dir / "dictionary.txt"
        if original_dict_path.exists():
            with open(original_dict_path, 'r', encoding='utf-8') as f:
                dictionary_data = json.load(f)
            
            with open(dictionary_path, 'w', encoding='utf-8') as f:
                json.dump(dictionary_data, f, ensure_ascii=False, indent=2)
            print(f"Created dictionary file at {dictionary_path}")
        else:
            print(f"Warning: Original dictionary file not found at {original_dict_path}")
    except Exception as e:
        print(f"Error creating dictionary file: {e}")

def process_text(input_text, language, google_api_key):
    """處理文本的回調函數"""
    try:
        # 驗證輸入
        if not input_text.strip():
            return "請輸入文本", None, None
        
        if not google_api_key.strip():
            return "請提供 Google AI API 金鑰", None, None
        
        # 創建新的處理識別碼
        identifier = file_manager.create_identifier()
        
        # 調用預處理函數
        processed_text = preprocess_text(input_text, language, google_api_key)
        
        # 保存處理後的文本
        output_path = file_manager.get_file_path(identifier, "step1", "preprocessed.txt")
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(processed_text)
        
        return "處理成功!", processed_text, identifier
    
    except PreprocessingError as e:
        return f"錯誤: {str(e)}", None, None
    except Exception as e:
        return f"未知錯誤: {str(e)}", None, None

def replace_homophones(processed_text, google_api_key, identifier):
    """多音字替換的回調函數"""
    try:
        if not processed_text or not processed_text.strip():
            return "請先完成文本預處理", None, None
        
        if not google_api_key.strip():
            return "請提供 Google AI API 金鑰", None, None
            
        if not identifier:
            return "無效的處理識別碼", None, None
        
        # 初始化多音字替換器
        homophone_replacer = HomophoneReplacer(dictionary_path)
        
        # 將文本分成批次（每10個段落一批）
        text_batches = homophone_replacer.segment_text(processed_text, batch_size=10)
        
        # 使用Google AI處理每個批次
        token_text = homophone_replacer.process_with_google_ai(text_batches, google_api_key)
        
        # 進行多音字替換
        modified_text, report = homophone_replacer.replace_homophones(token_text)
        
        # 生成報告
        human_readable_report = homophone_replacer.get_replacement_report(report)
        
        # 保存替換後的文本
        output_path = file_manager.get_file_path(identifier, "step2", "replaced.txt")
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(modified_text)
            
        # 保存替換報告
        report_path = file_manager.get_file_path(identifier, "step2", "report.txt")
        with open(report_path, "w", encoding="utf-8") as f:
            f.write(human_readable_report)
        
        return "多音字替換成功!", modified_text, human_readable_report
    
    except Exception as e:
        return f"多音字替換錯誤: {str(e)}", None, None

def generate_tts(text, api_key, voice_name, emotion, speed, custom_pronunciation, identifier):
    """TTS語音生成的回調函數"""
    try:
        if not text or not text.strip():
            return "請先完成多音字替換", None, None, None, None
        
        if not api_key.strip():
            return "請提供 Hailuo API 金鑰", None, None, None, None
            
        if not identifier:
            return "無效的處理識別碼", None, None, None, None
        
        # 在temp目錄中創建音频輸出目錄
        audio_output_dir = file_manager.get_file_path(identifier, "step3", "audio")
        os.makedirs(audio_output_dir, exist_ok=True)
        
        # 初始化TTS生成器
        tts_generator = TTSGenerator(api_key, output_dir=audio_output_dir)
        
        # 生成語音
        mp3_files, _ = tts_generator.generate_speech(
            text,
            voice_name=voice_name,
            emotion=emotion,
            speed=float(speed),
            custom_pronunciation=custom_pronunciation,
            identifier=identifier
        )
        
        # 生成語音文件列表
        file_list = ""
        for i, file_path in enumerate(mp3_files):
            file_name = os.path.basename(file_path)
            file_list += f"{i+1}. {file_name}\n"
        
        # 將所有音频文件打包成zip
        zip_path = file_manager.get_file_path(identifier, "step3", "audio.zip")
        with zipfile.ZipFile(zip_path, 'w') as zipf:
            for mp3_file in mp3_files:
                zipf.write(mp3_file, os.path.basename(mp3_file))
        # 保存逐字稿
        transcript_file = file_manager.get_file_path(identifier, "step3", "transcript.txt")
        with open(transcript_file, "w", encoding="utf-8") as f:
            f.write(text)
        
        return "語音生成成功!", file_list, zip_path, transcript_file, mp3_files
    
    except TTSGenerationError as e:
        return f"語音生成錯誤: {str(e)}", None, None, None, None
    except Exception as e:
        return f"未知錯誤: {str(e)}", None, None, None, None

# 新增函數：僅生成字幕，不進行校正
def generate_subtitle_only(audio_zip, whisper_api_key, language, identifier):
    """只從音频生成字幕的回調函數，不進行校正"""
    try:
        if not audio_zip:
            return "請先上傳音频或生成音频文件", None, None
        
        if not whisper_api_key.strip():
            return "請提供 Whisper API 金鑰", None, None
            
        if not identifier:
            return "無效的處理識別碼", None, None
        
        # 初始化字幕生成器
        subtitle_generator = SRTGenerator()
        
        # 創建音频臨時目錄
        audio_temp_dir = file_manager.get_file_path(identifier, "step4", "audio_temp")
        os.makedirs(audio_temp_dir, exist_ok=True)
        
        try:
            # 嘗試先使用上傳的音頻檔案
            if isinstance(audio_zip, str) and os.path.exists(audio_zip):
                audio_zip_path = audio_zip
            else:
                # 如果上傳的檔案無效，嘗試使用步驟3的音頻檔案
                audio_zip_path = file_manager.get_file_path(identifier, "step3", "audio.zip")
                if not os.path.exists(audio_zip_path):
                    return "找不到音頻檔案，請先上傳或生成音頻", None, None

            # 解壓縮音频文件
            with zipfile.ZipFile(audio_zip_path, 'r') as zip_ref:
                zip_ref.extractall(audio_temp_dir)
        except Exception as e:
            return f"處理音頻檔案時發生錯誤：{str(e)}", None, None
        
        # 取得所有音频文件的路徑
        audio_files = [os.path.join(audio_temp_dir, f) for f in os.listdir(audio_temp_dir) if f.endswith('.mp3')]
        audio_files.sort()  # 確保按照檔名排序
        
        if not audio_files:
            return "未找到任何MP3音頻文件", None, None
        
        # 生成字幕
        initial_srt_file = file_manager.get_file_path(identifier, "step4", "initial_subtitle.srt")
        
        # 為每個音頻文件生成字幕
        all_srt_entries = []
        current_index = 1
        time_offset = 0  # 時間偏移量（毫秒）
        
        for audio_file in audio_files:
            # 使用Whisper API轉錄音頻
            srt_content = subtitle_generator.transcribe(audio_file, whisper_api_key, language)
            if not srt_content:
                continue
                
            # 解析SRT內容
            entries = subtitle_generator.parse_srt(srt_content)
            if not entries:
                continue
                
            # 調整時間戳和序號
            for entry in entries:
                # 調整時間戳
                start_ms = subtitle_generator.time_to_ms(entry['start_time']) + time_offset
                end_ms = subtitle_generator.time_to_ms(entry['end_time']) + time_offset
                
                entry['start_time'] = subtitle_generator.ms_to_time(start_ms)
                entry['end_time'] = subtitle_generator.ms_to_time(end_ms)
                entry['index'] = current_index
                
                all_srt_entries.append(entry)
                current_index += 1
            
            # 更新時間偏移量
            last_entry = entries[-1]
            time_offset = subtitle_generator.time_to_ms(last_entry['end_time'])
        
        # 生成合併後的SRT內容
        combined_srt = ""
        for entry in all_srt_entries:
            combined_srt += f"{entry['index']}\n"
            combined_srt += f"{entry['start_time']} --> {entry['end_time']}\n"
            combined_srt += f"{entry['text']}\n\n"
        
        # 保存合併後的字幕文件
        with open(initial_srt_file, "w", encoding="utf-8") as f:
            f.write(combined_srt)
        
        # 清理臨時文件
        for audio_file in audio_files:
            os.remove(audio_file)
        os.rmdir(audio_temp_dir)
        
        if not combined_srt:
            return "字幕生成失敗：未能從音頻中提取文字", None, None
        
        return "字幕生成成功!", combined_srt, initial_srt_file
    
    except Exception as e:
        return f"字幕生成過程中出錯: {str(e)}", None, None

def auto_process_all(transcript_file_path, google_api_key, tts_api_key, whisper_api_key, gemini_api_key, 
                    language, voice_name, emotion, speed, custom_pronunciation, batch_size):
    """一鍵處理所有步驟的整合函數"""
    try:
        # 檢查必要參數
        if not transcript_file_path or not os.path.exists(transcript_file_path):
            return "請上傳逐字稿文件", "處理中斷", None, None
        
        if not all([google_api_key, tts_api_key, whisper_api_key, gemini_api_key]):
            return "請填寫所有必要的 API 金鑰", "處理中斷", None, None
        
        progress(0.05, "正在準備處理...")
        timestamp = int(time.time())
        log_messages = []
        
        # 獲取原始檔案名稱（不含路徑和副檔名）
        original_filename = os.path.basename(transcript_file_path)
        base_filename = os.path.splitext(original_filename)[0]
        log_messages.append(f"處理檔案: {original_filename}")
        
        # 讀取上傳的逐字稿檔案
        with open(transcript_file_path, 'r', encoding='utf-8') as f:
            input_text = f.read()
        
        if not input_text.strip():
            return "逐字稿文件為空", "處理中斷", None, None
        
        # 步驟1: 文本預處理
        progress(0.1, "步驟1: 文本預處理...")
        log_messages.append("=== 步驟1: 文本預處理 ===")
        status_msg, processed_text = process_text(input_text, language, google_api_key)
        
        if not processed_text:
            return f"文本預處理失敗: {status_msg}", "\n".join(log_messages), None, None
        
        log_messages.append(f"預處理狀態: {status_msg}")
        log_messages.append(f"處理後文本長度: {len(processed_text)} 字符")
        
        # 步驟2: 多音字替換
        progress(0.3, "步驟2: 多音字替換...")
        log_messages.append("\n=== 步驟2: 多音字替換 ===")
        status_msg, modified_text, report = replace_homophones(processed_text, google_api_key)
        
        if not modified_text:
            return f"多音字替換失敗: {status_msg}", "\n".join(log_messages), None, None
        
        log_messages.append(f"替換狀態: {status_msg}")
        
        # 步驟3: TTS語音生成
        progress(0.5, "步驟3: TTS語音生成...")
        log_messages.append("\n=== 步驟3: TTS語音生成 ===")
        status_msg, file_list, zip_path, transcript_file, mp3_files = generate_tts(
            modified_text, tts_api_key, voice_name, emotion, speed, custom_pronunciation
        )
        
        if not zip_path or not os.path.exists(zip_path):
            return f"語音生成失敗: {status_msg}", "\n".join(log_messages), None, None
        
        # 重命名ZIP檔案，使用原始檔案名稱
        new_zip_path = os.path.join(os.path.dirname(zip_path), f"{base_filename}.zip")
        try:
            # 如果同名檔案已存在，先刪除
            if os.path.exists(new_zip_path):
                os.remove(new_zip_path)
            os.rename(zip_path, new_zip_path)
            zip_path = new_zip_path
            log_messages.append(f"重命名音頻ZIP檔案為: {os.path.basename(new_zip_path)}")
        except Exception as e:
            log_messages.append(f"警告: 無法重命名ZIP檔案: {str(e)}")
        
        log_messages.append(f"語音生成狀態: {status_msg}")
        log_messages.append(f"生成了 {len(mp3_files)} 個音頻文件")
        
        # 步驟4: 字幕生成與校正
        progress(0.8, "步驟4: 字幕生成與校正...")
        log_messages.append("\n=== 步驟4: 字幕生成與校正 ===")
        status_msg, subtitle_file, report_file, initial_srt_file = generate_subtitle(
            zip_path, transcript_file, whisper_api_key, gemini_api_key, language, batch_size
        )
        
        if not subtitle_file or not os.path.exists(subtitle_file):
            return f"字幕生成與校正失敗: {status_msg}", "\n".join(log_messages), zip_path, None
        
        # 重命名SRT檔案，使用原始檔案名稱
        new_srt_path = os.path.join(os.path.dirname(subtitle_file), f"{base_filename}.srt")
        try:
            # 如果同名檔案已存在，先刪除
            if os.path.exists(new_srt_path):
                os.remove(new_srt_path)
            os.rename(subtitle_file, new_srt_path)
            subtitle_file = new_srt_path
            log_messages.append(f"重命名字幕檔案為: {os.path.basename(new_srt_path)}")
        except Exception as e:
            log_messages.append(f"警告: 無法重命名SRT檔案: {str(e)}")
        
        log_messages.append(f"字幕生成狀態: {status_msg}")
        
        # 處理完成
        progress(1.0, "全部處理完成!")
        log_messages.append("\n=== 處理完成 ===")
        
        return "全部處理完成!", "\n".join(log_messages), zip_path, subtitle_file
    
    except Exception as e:
        import traceback
        error_msg = f"處理過程中發生錯誤: {str(e)}\n{traceback.format_exc()}"
        return error_msg, "處理出錯，請查看狀態信息", None, None

    
    except Exception as e:
        return f"字幕校正過程中出錯: {str(e)}", None, None, None

def generate_subtitle(audio_zip, transcript_file, whisper_api_key, gemini_api_key, language, batch_size):
    """從音頻和逐字稿生成和校正字幕的回調函數"""
    try:
        if not audio_zip or not os.path.exists(audio_zip):
            return "請先生成音頻文件", None, None, None
        
        if not transcript_file or not os.path.exists(transcript_file):
            return "找不到逐字稿文件", None, None, None
        
        if not whisper_api_key.strip():
            return "請提供 Whisper API 金鑰", None, None, None
        
        if not gemini_api_key.strip():
            return "請提供 Google Gemini API 金鑰", None, None, None
        
        # 從音頻文件名中提取識別碼
        identifier = os.path.basename(audio_zip).split('_')[0]
        
        progress(0.1, "解壓音頻文件...")
        
        # 創建臨時目錄解壓音頻文件
        extract_dir = tempfile.mkdtemp()
        
        # 解壓ZIP文件
        with zipfile.ZipFile(audio_zip, 'r') as zip_ref:
            zip_ref.extractall(extract_dir)
        
        # 獲取所有MP3文件
        audio_files = sorted([os.path.join(extract_dir, f) for f in os.listdir(extract_dir) if f.endswith('.mp3')])
        
        if not audio_files:
            return "未在ZIP文件中找到MP3音頻", None, None, None
        
        progress(0.3, "使用Whisper API生成字幕...")
        
        # 使用SRTGenerator從音頻文件生成SRT
        srt_generator = SRTGenerator()
        
        # 使用file_manager獲取檔案路徑
        initial_srt_path = file_manager.get_file_path(identifier, "step4", "initial_subtitle.srt")
        
        # 使用Whisper API轉錄
        all_srt_content = []
        for audio_file in audio_files:
            srt_content = srt_generator.transcribe(audio_file, whisper_api_key, language)
            if srt_content:
                # 獲取音頻時長用於時間戳校正
                audio_duration = srt_generator.get_audio_duration(audio_file)
                # 校正時間戳
                corrected_srt = srt_generator.correct_timestamps_proportionally(srt_content, audio_duration)
                all_srt_content.append(corrected_srt)
        
        # 合併所有SRT內容
        combined_srt = "\n\n".join(all_srt_content)
        
        if not combined_srt:
            return "字幕生成失敗：未能從音頻中提取文字", None, None, None
        
        # 保存原始字幕
        with open(initial_srt_path, "w", encoding="utf-8") as f:
            f.write(combined_srt)
        
        progress(0.6, "校正字幕中...")
        
        # 使用SubtitleCorrector校正字幕
        subtitle_corrector = SubtitleCorrector(gemini_api_key)
        error, corrected_srt, reports = subtitle_corrector.correct_subtitles(
            transcript_file,
            initial_srt_path,
            int(batch_size)
        )
        
        if error:
            return f"字幕校正失敗: {error}", None, None, None
        
        # 保存校正後的字幕
        corrected_srt_path = file_manager.get_file_path(identifier, "step4", "corrected_subtitle.srt")
        
        # 讀取校正後的字幕內容
        corrected_content = corrected_srt.to_string()
        
        # 保存校正後的字幕
        with open(corrected_srt_path, "w", encoding="utf-8") as f:
            f.write(corrected_content)
        
        # 清理臨時文件
        for audio_file in audio_files:
            os.remove(audio_file)
        os.rmdir(extract_dir)
        
        # 保存修改報告
        report_file = file_manager.get_file_path(identifier, "step4", f"correction_report.txt")
        with open(report_file, "w", encoding="utf-8") as f:
            f.write("\n".join(reports) if reports else "沒有進行任何修改")
        
        progress(1.0, "完成!")
        
        return "字幕生成與校正成功!", combined_srt, corrected_content, corrected_srt_path
    
    except Exception as e:
        return f"字幕生成過程中出錯: {str(e)}", None, None, None

# 新增函數：顯示逐字稿內容
def load_transcript(transcript_file):
    """載入並顯示逐字稿內容"""
    if not transcript_file or not os.path.exists(transcript_file):
        return "無法載入逐字稿文件"
    
    try:
        with open(transcript_file, 'r', encoding='utf-8') as f:
            content = f.read()
        return content
    except Exception as e:
        return f"載入逐字稿錯誤: {str(e)}"

# 新增函數：顯示SRT文件內容
def load_srt_content(srt_file):
    """載入並顯示SRT字幕內容"""
    if not srt_file or not os.path.exists(srt_file):
        return "無法載入SRT文件"
    
    try:
        with open(srt_file, 'r', encoding='utf-8') as f:
            content = f.read()
        return content
    except Exception as e:
        return f"載入SRT文件錯誤: {str(e)}"

# 新增函數：更新預覽區域 (這個函數目前沒有被使用到，可以考慮刪除或修改)
def update_previews(status, subtitle_file, correction_report, initial_srt_file):
    """字幕生成成功後更新所有預覽區域"""
    initial_content = load_srt_content(initial_srt_file) if initial_srt_file else "尚未生成原始字幕"
    corrected_content = load_srt_content(subtitle_file) if subtitle_file else "尚未生成校正後字幕"
    
    return status, initial_content, corrected_content, subtitle_file, correction_report, initial_srt_file

# 新增函數：下載校正後字幕
def download_corrected_srt(subtitle_file):
    """返回校正後的字幕文件以供下載"""
    return subtitle_file

# 新增函數：創建視頻預覽
def create_video_preview(mp3_files, subtitle_file, identifier):
    """從音频文件和字幕文件創建視頻預覽"""
    try:
        if not mp3_files or not subtitle_file:
            return "請先生成音频和字幕文件", None
            
        if not identifier:
            return "無效的處理識別碼", None
        
        # 創建臨時目錄
        temp_dir = file_manager.get_file_path(identifier, "step5", "temp")
        os.makedirs(temp_dir, exist_ok=True)
        
        # 將多個音频文件合併成一個
        merged_audio = os.path.join(temp_dir, "merged_audio.mp3")
        
        if isinstance(mp3_files, list) and len(mp3_files) > 1:
            # 合併多個音频文件
            audio_segments = [AudioSegment.from_mp3(mp3_file) for mp3_file in mp3_files]
            combined_audio = sum(audio_segments)
            combined_audio.export(merged_audio, format="mp3")
        else:
            # 如果只有一個音频文件，直接使用它
            merged_audio = mp3_files[0] if isinstance(mp3_files, list) else mp3_files
        
        # 創建視頻
        video_path = file_manager.get_file_path(identifier, "step5", "preview.mp4")
        
        # 使用ffmpeg創建視頻
        audio_duration = AudioSegment.from_mp3(merged_audio).duration_seconds
        
        # 創建黑色背景視頻
        cmd = [
            "ffmpeg", "-y",
            "-f", "lavfi", "-i", f"color=c=black:s=1280x720:d={audio_duration}",
            "-i", merged_audio,
            "-vf", f"subtitles='{subtitle_file}':force_style='Fontsize=24'",
            "-c:v", "libx264", "-c:a", "aac",
            "-shortest",
            video_path
        ]
        
        subprocess.run(cmd, check=True)
        
        # 清理臨時文件
        if isinstance(mp3_files, list) and len(mp3_files) > 1:
            os.remove(merged_audio)
        os.rmdir(temp_dir)
        
        return "視頻預覽創建成功!", video_path
    
    except Exception as e:
        return f"視頻預覽創建失敗: {str(e)}", None
    except Exception as e:
        return f"未知錯誤: {str(e)}", None

def batch_process_all_files(transcript_files, google_api_key, tts_api_key, whisper_api_key, gemini_api_key, 
                          language, voice_name, emotion, speed, custom_pronunciation, batch_size):
    """批次處理多個逐字稿檔案，每個檔案獨立處理並打包"""
    if not transcript_files:
        return "請上傳至少一個逐字稿檔案", "未處理任何檔案", None
    
    if not all([google_api_key, tts_api_key, whisper_api_key, gemini_api_key]):
        return "請填寫所有必要的 API 金鑰", "處理中斷", None
    
    # 準備存放處理結果的容器
    status_messages = []
    log_messages = []
    all_package_files = []
    
    # 計算總進度基準
    file_count = len(transcript_files)
    
    # 處理每個檔案
    for idx, file_path in enumerate(transcript_files):
        # 計算此檔案的進度範圍
        progress_start = idx / file_count
        progress_end = (idx + 1) / file_count
        
        # 檔案處理的進度包裝器
        def file_progress(value, desc=""):
            overall_progress = progress_start + (progress_end - progress_start) * value
            progress(overall_progress, f"[{idx+1}/{file_count}] {desc}")
        
        # 處理單一檔案
        file_status, file_log, zip_file, srt_file = auto_process_all(
            file_path, google_api_key, tts_api_key, whisper_api_key, gemini_api_key,
            language, voice_name, emotion, speed, custom_pronunciation, batch_size,
            progress=file_progress
        )
        
        # 記錄處理結果
        file_name = os.path.basename(file_path)
        base_name = os.path.splitext(file_name)[0]
        status_messages.append(f"檔案 {idx+1}/{file_count} ({file_name}): {file_status}")
        log_messages.append(f"\n{'='*50}\n檔案: {file_name}\n{'='*50}")
        log_messages.append(file_log)
        
        # 為每個檔案創建獨立的整合包
        if (zip_file and os.path.exists(zip_file)) and (srt_file and os.path.exists(srt_file)):
            # 創建整合包
            package_zip = str(temp_dir / f"整合_{base_name}.zip")
            
            # 如果同名檔案已存在，先刪除
            if os.path.exists(package_zip):
                os.remove(package_zip)
                
            with zipfile.ZipFile(package_zip, 'w') as package:
                # 添加音頻ZIP檔案（保留原始檔名）
                package.write(zip_file, os.path.basename(zip_file))
                # 添加SRT字幕檔案（保留原始檔名）
                package.write(srt_file, os.path.basename(srt_file))
            
            all_package_files.append(package_zip)
            log_messages.append(f"已創建整合包: 整合_{base_name}.zip")
    
    # 合併所有檔案處理狀態
    final_status = f"處理完成: {len(all_package_files)}/{file_count} 個檔案成功生成整合包"
    combined_logs = "\n".join(log_messages)
    
    # 創建所有整合包的索引ZIP
    timestamp = int(time.time())
    index_zip = str(temp_dir / f"所有整合包_{timestamp}.zip")
    
    with zipfile.ZipFile(index_zip, 'w') as index_package:
        for package_file in all_package_files:
            index_package.write(package_file, os.path.basename(package_file))
             
    return final_status, combined_logs, index_zip



# 定義Gradio界面
with gr.Blocks(
    title="AI語音生成與字幕系統",
    css="""
    .wrap-text textarea {
        white-space: pre-wrap !important;
        word-wrap: break-word !important;
        overflow-y: auto !important;
        max-height: 300px !important;
    }
    """
) as app:
    gr.Markdown("# AI語音生成與字幕系統")
    
    # 創建一個共享的狀態變量來存儲步驟1的預處理文本
    preprocessed_text_state = gr.State("")
    # 創建一個共享的狀態變量來存儲步驟3生成的 MP3 檔案
    mp3_files_state = gr.State([])
    # 創建一個共享的狀態變量來存儲處理識別碼
    identifier_state = gr.State("")
    
    with gr.Tabs() as tabs:
        # 第一步：文本預處理部分
        with gr.TabItem("步驟1: 文本預處理") as tab1:
            with gr.Row():
                with gr.Column():
                    input_text = gr.Textbox(
                        label="請輸入原始文本",
                        placeholder="在此輸入需要生成語音和字幕的文本...",
                        lines=10
                    )
                    
                    with gr.Row():
                        language = gr.Dropdown(
                            choices=["zh", "en"],
                            label="選擇語言",
                            value="zh"
                        )
                        google_api_key = gr.Textbox(
                            label="Google AI API 金鑰",
                            placeholder="請輸入您的 API 金鑰",
                            type="password"
                        )
                    
                    process_btn = gr.Button("預處理文本")
                    
                    status_msg = gr.Textbox(label="狀態", interactive=False)
                
                with gr.Column():
                    processed_text = gr.Textbox(
                        label="預處理後的文本",
                        placeholder="預處理結果將顯示在這裡...",
                        lines=15,
                        interactive=True
                    )
                    
                    next_step_btn = gr.Button("進入多音字處理")
        
        # 第二步：多音字替換部分
        with gr.TabItem("步驟2: 多音字替換") as tab2:
            with gr.Row():
                with gr.Column():
                    step2_processed_text = gr.Textbox(
                        label="預處理後的文本",
                        placeholder="從步驟1獲得的預處理文本...",
                        lines=10
                    )
                    
                    step2_google_api_key = gr.Textbox(
                        label="Google AI API 金鑰",
                        placeholder="請輸入您的 API 金鑰",
                        type="password"
                    )
                    
                    replace_btn = gr.Button("進行多音字替換")
                    
                    step2_status_msg = gr.Textbox(label="狀態", interactive=False)
                
                with gr.Column():
                    replaced_text = gr.Textbox(
                        label="替換後的文本",
                        placeholder="多音字替換後的文本將顯示在這裡...",
                        lines=10,
                        interactive=True
                    )
                    
                    replacement_report = gr.Markdown(
                        label="替換報告",
                        value="替換報告將顯示在這裡..."
                    )
                    
                    next_step_btn2 = gr.Button("進入語音生成", interactive=True)  # 設置為始終可用
        
        # 第三步：TTS語音生成部分
        with gr.TabItem("步驟3: 語音生成") as tab3:
            with gr.Row():
                with gr.Column():
                    step3_replaced_text = gr.Textbox(
                    label="替換後的文本",
                    placeholder="從步驟2獲得的替換後文本...",
                    lines=10,
                    interactive=False
                    )
                    
                    step3_api_key = gr.Textbox(
                        label="語音生成 API 金鑰",
                        placeholder="請輸入您的 語音生成 API 金鑰",
                        type="password"
                    )
                    
                    with gr.Row():
                        voice_name = gr.Dropdown(
                            choices=list(TTS_VOICES.keys()),
                            label="選擇語音",
                            value="訓練長"
                        )
                        
                        emotion = gr.Dropdown(
                            choices=TTS_EMOTIONS,
                            label="選擇情緒",
                            value="neutral"
                        )
                    
                    speed = gr.Slider(
                        minimum=0.5,
                        maximum=2.0,
                        step=0.1,
                        value=1.0,
                        label="語速"
                    )
                    
                    custom_pronunciation = gr.Textbox(
                        label="自定義發音詞條 (多個詞條用逗號分隔)",
                        placeholder="例如: 調整/(tiao2)(zheng3),行為/(xing2)(wei2)",
                        lines=3
                    )
                    
                    generate_btn = gr.Button("生成語音")
                    
                    step3_status_msg = gr.Textbox(label="狀態", interactive=False)
                
                with gr.Column():
                    generated_files = gr.Textbox(
                        label="生成的語音文件",
                        placeholder="生成的語音文件將顯示在這裡...",
                        lines=10,
                        interactive=False
                    )
                    
                    audio_zip = gr.File(
                        label="語音檔案 (ZIP)",
                        interactive=False
                    )
                    
                    # 隱藏的逐字稿文件路徑
                    transcript_file_path = gr.Textbox(visible=False)
                    
                    next_step_btn3 = gr.Button("進入字幕生成")
        
        # 第四步：字幕生成與校對部分 - 全新設計的UI
        with gr.TabItem("步驟4: 字幕生成與校對") as tab4:
            # 頂部區域 - 左右兩欄佈局
            with gr.Row():
                # 左欄 - 包含上下兩列
                with gr.Column(scale=3):
                    # 上列 - API 金鑰
                    with gr.Row(equal_height=True):
                        step4_whisper_api_key = gr.Textbox(
                            label="Whisper API 金鑰",
                            placeholder="請輸入您的 OpenAI API 金鑰",
                            type="password",
                            scale=1
                        )
                        step4_gemini_api_key = gr.Textbox(
                            label="Google Gemini API 金鑰",
                            placeholder="請輸入您的 Google Gemini API 金鑰",
                            type="password",
                            scale=1
                        )
                    
                    # 下列 - 語言、批次大小和狀態
                    with gr.Row(equal_height=True):
                        step4_language = gr.Dropdown(
                            label="語言",
                            choices=[("中文", "zh"), ("英文", "en"), ("日文", "ja")],
                            value="zh",
                            scale=1
                        )
                        batch_size = gr.Dropdown(
                            label="字幕批次大小",
                            choices=[5, 10, 15, 20, 25, 30],
                            value=20,
                            scale=1
                        )
                        step4_status_msg = gr.Textbox(
                            label="狀態",
                            placeholder="處理狀態將顯示在這裡...",
                            interactive=False,
                            scale=2
                        )
                
                # 右欄 - 語音檔案上傳
                with gr.Column(scale=1):
                    step4_audio_zip = gr.File(
                        label="語音檔案上傳",
                        file_types=[".zip"],
                        interactive=True
                    )
            
            # 三欄佈局（左中右）
            with gr.Row():
                # 左欄 - 逐字稿預覽
                with gr.Column(scale=1):
                    gr.Markdown("### 逐字稿預覽")
                    transcript_preview = gr.TextArea(
                        label="逐字稿內容",
                        placeholder="逐字稿內容將顯示在這裡...",
                        lines=20,
                        interactive=False
                    )
                    
                    generate_subtitle_btn = gr.Button("生成字幕", variant="primary")
                
                # 中欄 - 原始識別字幕預覽
                with gr.Column(scale=1):
                    gr.Markdown("### 原始識別字幕預覽")
                    original_srt_preview = gr.TextArea(
                        label="原始字幕內容",
                        placeholder="原始識別的字幕內容將顯示在這裡...",
                        lines=20,
                        interactive=False
                    )
                    
                    correct_subtitle_btn = gr.Button("校正字幕", variant="primary")
                
                # 右欄 - 校正後字幕預覽
                with gr.Column(scale=1):
                    gr.Markdown("### 校正後字幕預覽")
                    corrected_srt_preview = gr.TextArea(
                        label="校正後字幕內容",
                        placeholder="校正後的字幕內容將顯示在這裡...",
                        lines=20,
                        interactive=True
                    )
                    
                    download_srt_btn = gr.Button("下載校正後字幕(SRT)", variant="primary")
                    preview_effect_btn = gr.Button("預覽效果", variant="primary")  # 新增預覽效果按鈕
            
            # 隱藏的文件路徑
            step4_transcript_file = gr.File(
                label="逐字稿檔案",
                file_types=[".txt"],
                interactive=True,
                visible=False
            )
            subtitle_file = gr.File(
                label="校正後的字幕 (SRT)",
                interactive=False,
                visible=False
            )
            correction_report = gr.File(
                label="校正報告",
                interactive=False,
                visible=False
            )
            initial_srt_file = gr.File(
                label="原始識別字幕 (SRT)",
                interactive=False,
                visible=False
            )
        
        # 第五步：視頻預覽部分
        with gr.TabItem("步驟5: 視頻預覽") as tab5:
            with gr.Row():
                with gr.Column(scale=1):
                    gr.Markdown("### 視頻源文件")
                    step5_status_msg = gr.Textbox(
                        label="狀態",
                        placeholder="處理狀態將顯示在這裡...",
                        interactive=False
                    )
                    
                    # 字幕內容預覽（從步驟4帶過來）
                    step5_subtitle_content = gr.TextArea(
                        label="字幕內容",
                        placeholder="字幕內容將顯示在這裡...",
                        lines=10,
                        interactive=False,
                        elem_classes=["wrap-text"]  # 添加自定義 CSS 類 
                    )
                    
                    # 隱藏的狀態保存
                    step5_subtitle_file = gr.Textbox(visible=False)
                    
                    create_preview_btn = gr.Button("生成視頻預覽", variant="primary")
                
                with gr.Column(scale=2):
                    gr.Markdown("### 視頻預覽")
                    
                    # 視頻預覽元件
                    video_preview = gr.Video(
                        label="視頻預覽",
                        interactive=False
                    )
                    
                    # 下載視頻按鈕
                    download_video_btn = gr.Button("下載視頻", variant="primary")
        # 新增第六步：全自動處理頁籤
        with gr.TabItem("一鍵處理") as tab6:
            with gr.Row():
                with gr.Column(scale=1):
                    gr.Markdown("### 自動化處理設定")
                    auto_transcript_files = gr.File(
                        label="上傳逐字稿文件 (可多選)",
                        file_types=[".txt"],
                        interactive=True,
                        file_count="multiple"
                    )
                    
                    # API 金鑰區塊
                    with gr.Group():
                        gr.Markdown("#### API 金鑰設定")
                        auto_google_api_key = gr.Textbox(
                            label="Google AI API 金鑰",
                            placeholder="請輸入您的 Google AI API 金鑰",
                            type="password"
                        )
                        auto_tts_api_key = gr.Textbox(
                            label="語音生成 API 金鑰",
                            placeholder="請輸入您的 語音生成 API 金鑰",
                            type="password"
                        )
                        auto_whisper_api_key = gr.Textbox(
                            label="Whisper API 金鑰",
                            placeholder="請輸入您的 OpenAI API 金鑰",
                            type="password"
                        )
                        auto_gemini_api_key = gr.Textbox(
                            label="Google Gemini API 金鑰",
                            placeholder="請輸入您的 Google Gemini API 金鑰",
                            type="password"
                        )
                    
                    # 基本設定區塊
                    with gr.Group():
                        gr.Markdown("#### 基本設定")
                        with gr.Row():
                            auto_language = gr.Dropdown(
                                choices=["zh", "en"],
                                label="選擇語言",
                                value="zh"
                            )
                            auto_batch_size = gr.Dropdown(
                                label="字幕批次大小",
                                choices=[5, 10, 15, 20, 25, 30],
                                value=20
                            )
                        
                        # 語音設定區塊
                        with gr.Row():
                            auto_voice_name = gr.Dropdown(
                                choices=list(TTS_VOICES.keys()),
                                label="選擇語音",
                                value="訓練長"
                            )
                            auto_emotion = gr.Dropdown(
                                choices=TTS_EMOTIONS,
                                label="選擇情緒",
                                value="neutral"
                            )
                        
                        auto_speed = gr.Slider(
                            minimum=0.5,
                            maximum=2.0,
                            step=0.1,
                            value=1.0,
                            label="語速"
                        )
                        
                        auto_custom_pronunciation = gr.Textbox(
                            label="自定義發音詞條 (多個詞條用逗號分隔)",
                            placeholder="例如: 調整/(tiao2)(zheng3),行為/(xing2)(wei2)",
                            lines=2
                        )
                    
                    # 啟動按鈕
                    auto_process_btn = gr.Button("開始一鍵處理", variant="primary", size="lg")
                
                with gr.Column(scale=1):
                    gr.Markdown("### 處理進度與結果")
                    
                    auto_status_msg = gr.Textbox(
                        label="處理狀態",
                        placeholder="處理狀態將顯示在這裡...",
                        lines=2,
                        interactive=False
                    )
                    
                    auto_progress = gr.Textbox(
                        label="處理進度",
                        placeholder="處理進度將顯示在這裡...",
                        lines=10,
                        interactive=False
                    )
                    
                    # 結果下載
                    gr.Markdown("### 下載結果")
                    # 修改為:
                    auto_packages_zip = gr.File(
                        label="整合包檔案 (包含音頻和字幕)",
                        interactive=False
                    )
    
    
    
    
    # 設置回調
    # 步驟1的回調
    def process_and_save(input_text, language, google_api_key):
        status, result, identifier = process_text(input_text, language, google_api_key)
        return status, result, result, identifier  # 更新狀態變量和識別碼
    
    process_btn.click(
        fn=process_and_save,
        inputs=[input_text, language, google_api_key],
        outputs=[status_msg, processed_text, preprocessed_text_state, identifier_state],
        api_name="process_text"
    )
    
    # 從步驟1到步驟2的回調 - 只傳遞數據
    next_step_btn.click(
        fn=lambda t, key: (t, key, "資料已送出：文本已傳遞到多音字處理步驟"),
        inputs=[processed_text, google_api_key],
        outputs=[step2_processed_text, step2_google_api_key, status_msg]
    )
    
    # 步驟2的多音字替換回調
    def replace_homophones_and_save(processed_text, google_api_key, identifier):
        status, result, report = replace_homophones(processed_text, google_api_key, identifier)
        return status, result, report, identifier

    replace_btn.click(
        fn=replace_homophones_and_save,
        inputs=[step2_processed_text, step2_google_api_key, identifier_state],
        outputs=[step2_status_msg, replaced_text, replacement_report, identifier_state],
        api_name="replace_homophones"
    )
    
    # 從步驟2到步驟3的回調 - 只傳遞數據
    next_step_btn2.click(
        fn=lambda t, identifier: (t, identifier, "資料已送出：文本已傳遞到語音生成步驟"),
        inputs=[replaced_text, identifier_state],
        outputs=[step3_replaced_text, identifier_state, step2_status_msg]
    )
    
    # 步驟3的TTS生成回調
    def generate_tts_and_save(text, api_key, voice_name, emotion, speed, custom_pronunciation, identifier):
        status, file_list, zip_path, transcript_file, mp3_files = generate_tts(text, api_key, voice_name, emotion, speed, custom_pronunciation, identifier)
        return status, file_list, zip_path, transcript_file, mp3_files

    generate_btn.click(
        fn=generate_tts_and_save,
        inputs=[
            step3_replaced_text,
            step3_api_key,
            voice_name,
            emotion,
            speed,
            custom_pronunciation,
            identifier_state  # 增加識別碼參數
        ],
        outputs=[
            step3_status_msg,
            generated_files,
            audio_zip,
            transcript_file_path,
            mp3_files_state  # 儲存 mp3_files 到狀態變量
        ]
    )
    
    # 當上傳逐字稿文件時更新預覽
    step4_transcript_file.change(
        fn=load_transcript,
        inputs=[step4_transcript_file],
        outputs=[transcript_preview]
    )
    
    # 生成字幕按鈕回調 - 修改為只生成不校正
    def generate_subtitle_and_save(audio_zip, whisper_api_key, language, identifier):
        return generate_subtitle_only(audio_zip, whisper_api_key, language, identifier)

    generate_subtitle_btn.click(
        fn=generate_subtitle_and_save,
        inputs=[
            step4_audio_zip,
            step4_whisper_api_key,
            step4_language,
            identifier_state
        ],
        outputs=[
            step4_status_msg,
            original_srt_preview,
            initial_srt_file
        ]
    )
    
    # 校正字幕按鈕回調 - 使用生成的原始字幕進行校正
    def correct_subtitle_and_save(transcript_file, initial_srt_file, gemini_api_key, batch_size, identifier):
        try:
            # 初始化字幕校正器
            subtitle_corrector = SubtitleCorrector(gemini_api_key)
            
            # 進行字幕校正
            error, corrected_srt, reports = subtitle_corrector.correct_subtitles(
                transcript_file,
                initial_srt_file,
                int(batch_size)
            )
            
            if error:
                return error, None, None, None
            
            # 保存校正後的字幕
            corrected_srt_path = file_manager.get_file_path(identifier, "step4", "corrected_subtitle.srt")
            
            # 將 SubRipFile 物件轉換為可讀的文本格式
            corrected_content = ""
            for sub in corrected_srt:
                corrected_content += f"{sub.index}\n{sub.start} --> {sub.end}\n{sub.text}\n\n"
            
            with open(corrected_srt_path, "w", encoding="utf-8") as f:
                f.write(corrected_content)
            
            # 保存修改報告
            report_path = file_manager.get_file_path(identifier, "step4", "correction_report.txt")
            with open(report_path, "w", encoding="utf-8") as f:
                f.write("\n".join(reports) if reports else "沒有進行任何修改")
            
            return "字幕校正成功!", corrected_content, corrected_srt_path, report_path
            
        except Exception as e:
            return f"字幕校正過程中出錯: {str(e)}", None, None, None

    correct_subtitle_btn.click(
        fn=correct_subtitle_and_save,
        inputs=[
            step4_transcript_file,
            initial_srt_file,
            step4_gemini_api_key,
            batch_size,
            identifier_state
        ],
        outputs=[
            step4_status_msg,
            corrected_srt_preview,
            subtitle_file,
            correction_report
        ]
    )

    # 下載校正後字幕按鈕回調
    download_srt_btn.click(
        fn=download_corrected_srt,
        inputs=[subtitle_file],
        outputs=[subtitle_file]
    )

    # 從步驟4到步驟5的回調 - 只傳遞數據
    # 從步驟3到步驟4的回調 - 只傳遞數據
    def prepare_step4_and_save(audio_zip, preprocessed_text, identifier):
        """準備步驟4的數據，使用步驟1的預處理文本作為逐字稿"""
        if not identifier:
            return None, None, None, None, "準備失敗：無效的處理識別碼"
        
        # 從temp目錄讀取最新的預處理文本
        preprocessed_file = file_manager.get_latest_file("step1", "preprocessed.txt")
        if not preprocessed_file or not os.path.exists(preprocessed_file):
            return None, None, None, None, "準備失敗：找不到預處理文本"
            
        # 讀取預處理後的文本作為逐字稿
        with open(preprocessed_file, "r", encoding="utf-8") as f:
            transcript_content = f.read()
        
        # 直接使用 step3 的音頻文件
        audio_zip_path = file_manager.get_latest_file("step3", "audio.zip")
        if not os.path.exists(audio_zip_path):
            return None, None, None, None, "準備失敗：找不到音頻文件"
        
        return audio_zip_path, preprocessed_file, "zh", transcript_content, "資料已送出：音频和逐字稿已傳遞到字幕生成步驟"

    next_step_btn3.click(
        fn=prepare_step4_and_save,
        inputs=[audio_zip, preprocessed_text_state, identifier_state],
        outputs=[step4_audio_zip, step4_transcript_file, step4_language, transcript_preview, step4_status_msg]
    )

    # 從步驟4到步驟5的回調 - 只傳遞數據
    def prepare_step5(subtitle_file, corrected_srt_content):
        return subtitle_file, corrected_srt_content, "資料已送出：字幕已傳遞到預覽效果步驟", subtitle_file

    preview_effect_btn.click(
        fn=prepare_step5,
        inputs=[subtitle_file, corrected_srt_preview],
        outputs=[step5_subtitle_content, step5_subtitle_file, step4_status_msg]
    )

    # 步驟5的視频預覽回調
    def create_video_preview_callback(mp3_files, subtitle_file, identifier):
        status, video_path = create_video_preview(mp3_files, subtitle_file, identifier)
        return status, video_path

    create_preview_btn.click(
        fn=create_video_preview_callback,
        inputs=[mp3_files_state, step5_subtitle_file, identifier_state],
        outputs=[step5_status_msg, video_preview]
    )

    # 步驟5的視頻下載回調 (暫時移除，因為 Gradio 的 Video 元件可以直接下載)
    # download_video_btn.click(...)
    # 一鍵處理按鈕回調
    auto_process_btn.click(
        fn=batch_process_all_files,  # 改用新的批次處理函數
        inputs=[
            auto_transcript_files,  
            auto_google_api_key,
            auto_tts_api_key,
            auto_whisper_api_key,
            auto_gemini_api_key,
            auto_language,
            auto_voice_name,
            auto_emotion,
            auto_speed,
            auto_custom_pronunciation,
            auto_batch_size
        ],
        outputs=[
            auto_status_msg,
            auto_progress,
            auto_packages_zip
        ],
        api_name="batch_process_all"
    )

if __name__ == "__main__":
    app.launch(server_name="0.0.0.0", server_port=7863)