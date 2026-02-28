import asyncio
import aiohttp
import os
from google import genai
from google.cloud import translate_v2 as translate
import deepl

class Translator:
    """Translation engine with multiple providers."""
    
    def __init__(self, provider="google", api_key=None, target_lang="zh-TW"):
        self.provider = provider.lower()
        self.api_key = api_key
        self.target_lang = target_lang
        self._session = None
        self._init_provider()

    async def get_session(self):
        """Lazy load aiohttp session for connection pooling."""
        if self._session is None or self._session.closed:
            # 使用長駐連線池減少 HTTPS 握手延遲
            connector = aiohttp.TCPConnector(limit_per_host=5, keepalive_timeout=60)
            self._session = aiohttp.ClientSession(connector=connector)
        return self._session

    async def close_session(self):
        """Clean up the session."""
        if self._session and not self._session.closed:
            await self._session.close()

    def _init_provider(self):
        if self.provider == "gemini":
            if self.api_key:
                self.client = genai.Client(api_key=self.api_key)
        elif self.provider == "deepl":
            if self.api_key:
                self.deepl_translator = deepl.Translator(self.api_key)
        elif self.provider == "google":
            # Google Translate client usually expects GOOGLE_APPLICATION_CREDENTIALS
            # or it can be initialized with an API key for REST.
            # Here we'll assume a basic setup or placeholder for now.
            pass

    async def translate(self, text: str, source_lang: str = "en") -> str:
        if not text or not text.strip():
            return ""
            
        if self.provider == "gemini":
            return await self._translate_gemini(text, source_lang)
        elif self.provider == "deepl":
            return await self._translate_deepl(text, source_lang)
        elif self.provider == "google_free":
            return await self._translate_google_free(text, source_lang)
        else:
            return text # Fallback or not implemented

    async def _translate_gemini(self, text, source_lang):
        try:
            prompt = (
                f"你是一個專業的影視翻譯。請將以下 {source_lang} 的語音辨識文字翻譯成自然流暢的 繁體中文。\n"
                "規則：\n"
                "1. 只輸出翻譯內容，不要有任何解釋。\n"
                "2. 語氣要口語且自然。\n"
                "3. 保持繁體中文 (Taiwan standard) 的用語規範。\n\n"
                f"文字：{text}"
            )
            # Use asyncio.to_thread for synchronous SDK call
            response = await asyncio.to_thread(
                self.client.models.generate_content,
                model='gemini-1.5-flash',
                contents=prompt
            )
            return response.text.strip()
        except Exception as e:
            print(f"Gemini translation error: {e}")
            return text

    async def _translate_deepl(self, text, source_lang):
        try:
            # Handle language code mapping for DeepL if needed (e.g., 'en' -> 'EN-US')
            target = self.target_lang.upper()
            if target == "ZH-TW": target = "ZH" # DeepL uses ZH for Chinese
            
            result = await asyncio.to_thread(
                self.deepl_translator.translate_text, 
                text, 
                target_lang=target
            )
            return result.text
        except Exception as e:
            print(f"DeepL translation error: {e}")
            return text

    async def _translate_google_free(self, text, source_lang):
        """Free Google Translate using unofficial API (use with caution)."""
        try:
            url = "https://translate.googleapis.com/translate_a/single"
            params = {
                "client": "gtx",
                "sl": source_lang,
                "tl": self.target_lang,
                "dt": "t",
                "q": text
            }
            
            # 使用連線池，不再每次重建 Session
            session = await self.get_session()
            async with session.get(url, params=params) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    return "".join([sent[0] for sent in data[0]])
            return text
        except Exception as e:
            print(f"Google Free translation error: {e}")
            return text

if __name__ == "__main__":
    # Test
    translator = Translator(provider="google_free")
    async def main():
        res = await translator.translate("Hello world", source_lang="en")
        print(f"Translation: {res}")
    
    asyncio.run(main())
