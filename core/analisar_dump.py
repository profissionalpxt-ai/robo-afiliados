import re

path = r'C:\Users\TRANSRAP05\.gemini\antigravity\brain\3a1d67ca-dfe5-46ca-865b-fdf26104ef8c\.system_generated\steps\360\content.md'
text = open(path, 'r', encoding='utf-8').read()

print("File size:", len(text))
print("OG URL:", re.findall(r'property="og:url"\s+content="([^"]+)"', text))
print("OG IMG:", re.findall(r'property="og:image"\s+content="([^"]+)"', text))
print("OG TITLE:", re.findall(r'property="og:title"\s+content="([^"]+)"', text))
