import sys
sys.path.insert(0, 'scripts/tokenization')
from pretokenize_korean import create_tokenizer, tokenize_sentence

kiwi = create_tokenizer()

tests = [
    # Particles
    ('고양이가 예뻐요', 'The cat is pretty'),
    ('책을 읽었어', 'I read a book'),

    # Vowel harmony endings
    ('갔어요', 'went (polite)'),
    ('먹었어요', 'ate (polite)'),

    # Consonant stem endings
    ('가면', 'if go'),
    ('먹으면', 'if eat'),
    ('가니까', 'because go'),
    ('먹으니까', 'because eat'),
    ('가러', 'in order to go'),
    ('먹으러', 'in order to eat'),

    # Adnominal endings
    ('갈 거예요', 'will go'),
    ('먹을 수 있어요', 'can eat'),
    ('먹은 음식', 'food that was eaten'),

    # Copula
    ('학생이에요', 'is a student'),
    ('의사예요', 'is a doctor'),

    # Complex sentence
    ('3년 동안 못 만난 친구를 만났어', 'I met a friend I hadnt seen for 3 years'),
]

print('Testing comprehensive allomorph merging:\n')
for sent, desc in tests:
    tokens = tokenize_sentence(kiwi, sent, merge_allomorphs=True)
    print(f'{desc}')
    print(f'  Input:  {sent}')
    print(f'  Tokens: {tokens}')
    print()

