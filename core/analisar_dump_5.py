import re

with open('midia/googlebot_dump.html', 'r', encoding='utf-8') as f:
    txt = f.read()

print("Length:", len(txt))

# Search for any string mentioning item or product
matches = re.findall(r'"(name|title|itemName|item_name|caption)":\s*"([^"]+)"', txt)
for k, v in matches:
    if len(v) > 5 and not v.startswith("Shopee") and not v.startswith("http"):
        print(f"{k} -> {v}")

# Search for image urls
img_matches = re.findall(r'https://down-br\.img\.susercontent\.com/file/[a-zA-Z0-9_-]+', txt)
print("Imgs found:", set(img_matches))
