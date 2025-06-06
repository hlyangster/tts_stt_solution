# -*- coding: utf-8 -*-
# modules/openai_patch.py
"""
OpenAI 補丁模塊 - 用於解決 proxies 參數問題
注意: 這個文件需要在其他模塊之前導入
"""

def patch_openai():
    """
    修復 OpenAI 模塊初始化時 proxies 參數造成的問題
    這個補丁會攔截 OpenAI 客戶端初始化，移除不支持的 proxies 參數
    """
    import sys
    import importlib
    
    # 檢查 openai 是否已經被導入
    if 'openai' in sys.modules:
        openai_module = sys.modules['openai']
        
        # 檢查是否有舊版的 OpenAI 屬性
        if hasattr(openai_module, 'OpenAI'):
            original_openai = openai_module.OpenAI
            
            # 創建一個包裝函數來過濾 proxies 參數
            def patched_openai_init(*args, **kwargs):
                if 'proxies' in kwargs:
                    print("[openai_patch] Removing unsupported 'proxies' parameter")
                    del kwargs['proxies']
                return original_openai(*args, **kwargs)
            
            # 替換原始的 OpenAI 類
            openai_module.OpenAI = patched_openai_init
            print("[openai_patch] Successfully patched OpenAI client initialization")
        else:
            print("[openai_patch] OpenAI class not found, might be using a different version")
    else:
        print("[openai_patch] OpenAI module not imported, will initialize and patch it")
        # 如果尚未導入，先導入它然後應用補丁
        import openai
        from openai import OpenAI
        
        # 保存原始的 OpenAI 類
        original_openai = OpenAI
        
        # 創建一個包裝函數來過濾 proxies 參數
        def patched_openai_init(*args, **kwargs):
            if 'proxies' in kwargs:
                print("[openai_patch] Removing unsupported 'proxies' parameter")
                del kwargs['proxies']
            return original_openai(*args, **kwargs)
        
        # 替換原始的 OpenAI 類
        openai.OpenAI = patched_openai_init
        print("[openai_patch] 成功預先修補 OpenAI 客戶端初始化函數")

# 自動執行補丁
patch_openai()