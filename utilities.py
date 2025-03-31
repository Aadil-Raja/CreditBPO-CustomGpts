import re

def cleanMessage(paragraph):
    cleaned_text = re.sub(r"【.*?】", "", paragraph)
    cleaned_text = cleaned_text.replace("\\n", "\n").strip()
    return cleaned_text

