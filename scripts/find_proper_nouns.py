"""
Find all proper nouns (names) in the Chinese dataset.
Strategy:
1. Look for names with middle dot (·) - these are transliterated foreign names
2. Look for common name patterns that appear frequently
3. Cross-reference with English translations for name detection
"""
import json
import os
import re
from collections import Counter

data_dir = "frontend/static/data-zh/chunks"

# Known common transliterated names (will expand this list)
KNOWN_NAMES = {
    '汤姆', '玛丽', '杰克', '约翰', '玛丽亚', '彼得', '保罗', '大卫', 
    '迈克', '麦克', '史密斯', '约翰逊', '威廉', '詹姆斯', '罗伯特',
    '查尔斯', '乔治', '爱德华', '亨利', '弗兰克', '艾伦', '布莱恩',
    '丹尼尔', '马修', '安东尼', '马克', '史蒂夫', '史蒂芬', '凯文',
    '杰森', '杰夫', '布鲁斯', '克里斯', '尼克', '亚当', '安迪',
    '本', '鲍勃', '比尔', '卡尔', '丹', '唐', '埃里克', '弗雷德',
    '格雷格', '哈利', '伊万', '杰瑞', '乔', '肯', '拉里', '里奥',
    '马丁', '尼尔', '奥斯卡', '帕特', '菲尔', '雷', '罗恩', '山姆',
    '西蒙', '托德', '汤姆', '维克多', '沃尔特', '威尔',
    # Female names
    '安娜', '艾米', '贝蒂', '卡罗尔', '黛安', '伊丽莎白', '艾玛',
    '格蕾丝', '海伦', '艾琳', '珍妮', '朱莉', '凯特', '劳拉', '丽莎',
    '玛格丽特', '南希', '帕特里夏', '蕾切尔', '萨拉', '苏珊', '温迪',
    '爱丽丝', '芭芭拉', '辛西娅', '黛博拉', '伊芙', '费利西亚',
}

# Find all names with middle dot (foreign full names)
dot_names = set()
# Find potential names by analyzing sentences
potential_names = Counter()

print("Scanning all sentences...")

for filename in sorted(os.listdir(data_dir)):
    if not filename.endswith('.json'):
        continue
    with open(os.path.join(data_dir, filename), 'r') as f:
        chunk = json.load(f)
        for sent in chunk:
            zh = sent['zh']
            
            # Find names with middle dot (·)
            dot_matches = re.findall(r'[\u4e00-\u9fff]+·[\u4e00-\u9fff·]+', zh)
            for m in dot_matches:
                dot_names.add(m)
            
            # Look for English names in the English text and try to find corresponding Chinese
            en = sent['en']
            # Common pattern: English has capitalized names
            en_names = re.findall(r'\b[A-Z][a-z]+\b', en)
            
            # Check if any known names appear
            for name in KNOWN_NAMES:
                if name in zh:
                    potential_names[name] += 1

print(f"\n=== Names with middle dot (·) - {len(dot_names)} unique ===")
for name in sorted(dot_names)[:50]:
    print(f"  {name}")
if len(dot_names) > 50:
    print(f"  ... and {len(dot_names) - 50} more")

print(f"\n=== Known names found (top 30) ===")
for name, count in potential_names.most_common(30):
    print(f"  {name}: {count} occurrences")

# Now let's extract the base names from dot-names (first part before ·)
base_names_from_dots = set()
for name in dot_names:
    parts = name.split('·')
    base_names_from_dots.add(parts[0])  # First name

print(f"\n=== Base names extracted from full names ===")
print(sorted(base_names_from_dots))

# Combine all names
all_names = KNOWN_NAMES | base_names_from_dots | dot_names
print(f"\n=== Total unique names: {len(all_names)} ===")

