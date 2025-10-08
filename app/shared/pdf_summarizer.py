"""
PDF文書要約機能
"""
import logging
import os
from typing import List, Dict, Optional

import PyPDF2
from openai import OpenAI

from config import MODEL_NAME, OPENAI_API_KEY

# ログ設定
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class PDFSummarizer:
    """PDF文書を要約するクラス"""
    
    def __init__(self):
        if not OPENAI_API_KEY:
            raise ValueError("OPENAI_API_KEY environment variable is required")
        
        self.client = OpenAI(api_key=OPENAI_API_KEY)
        self.model = MODEL_NAME
    
    def extract_text_from_pdf(self, filepath: str) -> str:
        """PDFからテキストを抽出"""
        try:
            with open(filepath, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                text = ""
                
                for page_num in range(min(len(pdf_reader.pages), 10)):  # 最初の10ページまで
                    page = pdf_reader.pages[page_num]
                    text += page.extract_text() + "\n"
                
                return text.strip()
                
        except Exception as e:
            logger.error(f"Error extracting text from PDF {filepath}: {e}")
            return ""
    
    def summarize_pdf(self, filepath: str, title: str) -> str:
        """PDF文書を要約"""
        try:
            # PDFからテキストを抽出
            text = self.extract_text_from_pdf(filepath)
            if not text:
                return "PDFからテキストを抽出できませんでした。"
            
            # テキストが長すぎる場合は最初の部分のみ使用
            if len(text) > 8000:
                text = text[:8000] + "..."
            
            prompt = f"""
以下のEMA（European Medicines Agency）の文書「{title}」を日本語で詳細に要約してください。

要件:
1. 文書の目的と背景を説明
2. 主要な内容を要点リスト（5-7項目）で整理
3. 重要な推奨事項や指針があれば明記
4. 関係者への影響や意義を説明
5. 日本語で分かりやすく要約

文書内容:
{text}

要約:
"""
            
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "あなたはEMA文書の専門要約者です。医療規制に関する文書を日本語で分かりやすく要約してください。"
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                max_tokens=2000,
                temperature=0.7
            )
            
            return response.choices[0].message.content.strip()
            
        except Exception as e:
            logger.error(f"Error summarizing PDF {filepath}: {e}")
            return f"PDF要約中にエラーが発生しました: {str(e)}"
    
    def summarize_documents(self, documents: List[Dict[str, str]]) -> List[Dict[str, str]]:
        """複数の文書を要約"""
        summarized_docs = []
        
        for doc in documents:
            try:
                summary = self.summarize_pdf(doc['filepath'], doc['title'])
                summarized_docs.append({
                    'title': doc['title'],
                    'url': doc['url'],
                    'summary': summary,
                    'size': doc['size']
                })
                
                # 一時ファイルを削除
                if os.path.exists(doc['filepath']):
                    os.remove(doc['filepath'])
                    
            except Exception as e:
                logger.error(f"Error processing document {doc['title']}: {e}")
                summarized_docs.append({
                    'title': doc['title'],
                    'url': doc['url'],
                    'summary': f"要約中にエラーが発生しました: {str(e)}",
                    'size': doc['size']
                })
        
        return summarized_docs


def summarize_pdf_documents(documents: List[Dict[str, str]]) -> List[Dict[str, str]]:
    """
    PDF文書を要約するメイン関数
    
    Args:
        documents: 文書のリスト
        
    Returns:
        要約された文書のリスト
    """
    if not documents:
        return []
    
    summarizer = PDFSummarizer()
    return summarizer.summarize_documents(documents)
