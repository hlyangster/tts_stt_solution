---
title: TTS_STT_Solution
emoji: 🏃
colorFrom: purple
colorTo: gray
sdk: gradio
sdk_version: 5.23.3
app_file: app.py
pinned: false
short_description: 輸入逐字稿可生成語音與字幕檔，特化解決中文多音字與字幕時戳飄移問題
---

本 Hugging Face Space 提供一個端對端的自動化解決方案，旨在將使用者上傳的文本轉換為高品質的語音檔案以及與之精確同步的 SRT 字幕檔。

系統整合了多個處理步驟，無需使用者在中間進行手動干預：

1.  **文本預處理**: 自動根據語意和段落結構，將原始文本處理成適合語音合成的格式。
2.  **中文多音字處理**: 針對中文文本，自動替換常見的多音字（例如將「銀行」替換為發音更準確的「銀航」），以提高 TTS 的發音準確性。
3.  **語音合成 (TTS)**: 使用 Hailuo 將處理後的文本轉換為多個語音片段。
4.  **字幕生成**: 為每個語音片段生成初步的字幕。
5.  **字幕校對**: 使用使用者**原始**上傳的文本（非多音字替換版）對生成的字幕進行校對和時間軸對齊，確保最終字幕內容的準確性。
6.  **音檔合併**: 將多個語音片段無縫串接成單一、完整的音檔。

使用者只需上傳文本、選擇語言並提供必要的 API 金鑰，即可獲得最終的音檔和 SRT 字幕檔，大大簡化了內容創作流程。

**主要特色**:

*   **完全自動化**: 從文本到最終產出，流程自動執行。
*   **多語言支援**: 目前支援中文和英文。
*   **使用者預覽與調整**: 在正式生成前，使用者可以預覽預處理的文本並進行修改。
*   **高準確度字幕**: 利用原始文本進行校對，提升字幕內容的準確性。
*   **API 整合**: 需要使用者提供 Hailuo TTS API 和 Google AI API 金鑰以進行操作。

請依照以下步驟使用本系統：

1.  **上傳文本與選擇語言**:
    *   點擊「上傳文件」按鈕，選擇您的文本檔案（建議使用 `.txt` 格式）。
    *   或直接在文本框中貼上您的文本內容。
    *   從下拉選單中選擇文本的語言（中文 / English）。

2.  **文本預處理與預覽**:
    *   點擊「預處理文本」按鈕（或類似名稱的按鈕）。
    *   系統將執行文本預處理，並在下方的預覽區域顯示處理後的文本（通常會按段落或語句切分）。

3.  **確認或修改預處理文本**:
    *   請檢查預覽區域的文本。這是將用於生成語音的文本。
    *   如果需要，您可以在預覽區直接修改文本。
    *   確認無誤後，點擊「確認文本」按鈕（或類似名稱）。

4.  **提供 API 金鑰**:
    *   在指定的輸入欄位中，填入您的 Hailuo TTS API 金鑰。
    *   在指定的輸入欄位中，填入您的 Google AI API 金鑰（用於字幕校對等步驟）。
    *   *請注意：您的 API 金鑰僅在本次執行中使用，不會被儲存。*

5.  **開始生成**:
    *   點擊「生成語音與字幕」按鈕。
    *   系統將開始執行後續所有自動化步驟：多音字替換（若為中文）、調用 TTS API 生成語音片段、生成字幕、校對字幕、合併音檔。
    *   此過程可能需要一些時間，具體取決於文本的長度。請耐心等待。

6.  **下載結果**:
    *   處理完成後，系統將提供下載連結。
    *   點擊相應的連結即可下載最終生成的單一音檔（例如 `.mp3` 或 `.wav` 格式）和準確的 SRT 字幕檔 (`.srt` 格式)。


