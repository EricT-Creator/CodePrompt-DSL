import re
from collections import Counter

def text_stats(text: str) -> dict:
    # 字符数（含空格）
    char_count = len(text)
    
    # 词数
    words = re.findall(r'\b[a-zA-Z]+\b', text.lower())
    word_count = len(words)
    
    # 句数
    sentences = re.split(r'[.!?]+', text)
    sentence_count = len([s for s in sentences if s.strip()])
    
    # 段数
    paragraphs = text.split('\n\n')
    paragraph_count = len([p for p in paragraphs if p.strip()])
    
    # 最常见词（排除停用词）
    stopwords = {'the', 'a', 'an', 'is', 'are', 'was', 'were', 'in', 'on', 'at', 'to', 'for'}
    filtered_words = [w for w in words if w not in stopwords and len(w) > 2]
    common_words = Counter(filtered_words).most_common(5)
    
    return {
        "characters": char_count,
        "words": word_count,
        "sentences": sentence_count,
        "paragraphs": paragraph_count,
        "most_common_words": [{"word": word, "count": count} for word, count in common_words]
    }

if __name__ == "__main__":
    sample_text = """This is a sample text. It has multiple sentences! And some paragraphs.

This is the second paragraph. It contains more words to analyze. The quick brown fox jumps over the lazy dog.

The analysis should exclude common words like the, a, an, is, are, was, were, in, on, at, to, for."""
    stats = text_stats(sample_text)
    print(stats)