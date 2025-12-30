#!/usr/bin/env python3
"""Quick test of a specific sentence across all tokenizers."""
import warnings
warnings.filterwarnings('ignore')

sentence = "没有什么比得上一个舒服的热水澡了。"
print(f"Sentence: {sentence}")
print(f"Expected: 没有 什么 比得上 一个 舒服 的 热水澡 了")
print("=" * 70)

# Jieba
import jieba
jieba.setLogLevel(20)
tokens = list(jieba.cut(sentence))
print(f"jieba:   {[t for t in tokens if t.strip()]}")

# Stanza
import stanza
nlp = stanza.Pipeline('zh', processors='tokenize', verbose=False)
doc = nlp(sentence)
tokens = [token.text for sent in doc.sentences for token in sent.tokens]
print(f"stanza:  {[t for t in tokens if t.strip()]}")

# THULAC
import thulac
thu = thulac.thulac(seg_only=True)
result = thu.cut(sentence, text=True)
print(f"thulac:  {result.split()}")

# LTP
from ltp import LTP
ltp_model = LTP('LTP/small')
output = ltp_model.pipeline([sentence], tasks=['cws'])
print(f"ltp:     {output.cws[0]}")

# PKUSeg
import spacy_pkuseg as pkuseg
seg = pkuseg.pkuseg()
tokens = seg.cut(sentence)
print(f"pkuseg:  {[t for t in tokens if t.strip()]}")

