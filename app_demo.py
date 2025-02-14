import re
import os
import streamlit as st
from openai import OpenAI
from dotenv import load_dotenv
from apify_client import ApifyClient

# Load API keys from .env file
load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY_2")
APIFY_API_KEY = os.getenv("APIFY_API_KEY")

POS = 2
NEG = 0
NEU = 1

MODEL = "deepseek/deepseek-r1:free"
# MODEL = "deepseek/deepseek-r1-distill-llama-70b:free"
# MODEL = "google/gemini-2.0-flash-lite-preview-02-05:free"
# MODEL = "google/gemini-2.0-pro-exp-02-05:free"
# MODEL = "qwen/qwen-vl-plus:free"


class Post():
    def __init__(self, text):
        self.text = text
        self.text_limit = text if len(text) < 100 else text[:100] + "..."
        self.summary = summarize(text)
        if "Tích cực" in self.summary:
            self.sentiment = POS
        elif "Tiêu cực" in self.summary:
            self.sentiment = NEG
        else:
            self.sentiment = NEU


client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=OPENAI_API_KEY,
)


system_prompt = """
Bạn là một quản trị viên trường học. Dưới đây là một bình luận có thể liên quan đến trường của bạn.
Hãy tóm tắt nội dung bình luận, đánh giá mức độ tích cực / tiêu cực / trung lập, và đề xuất giải pháp.
Trả lời bằng tiếng Việt.
"""


def user_prompt_for(content):
    return f"""
    Bạn chỉ có thông tin sau, không hỏi thêm.
    Nội dung bài đăng trên Facebook: {content}.
    Nội dung theo dạng sau sau:
    Nội dung: (Bài viết đã tóm tắt)
    Loại: chỉ ghi ("Tích cực", "Tiêu cực", "Trung lập")
    Giải pháp: (Giải pháp nếu cần hoặc không làm gì)
    """


def message_for(content):
    return [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt_for(content)},
    ]


def summarize(content):
    try:
        completion = client.chat.completions.create(
            model=MODEL,
            messages=message_for(content)
        )

        # if server so busy
        if not completion.choices or not completion.choices[0].message or not completion.choices[0].message.content:
            return None

        return completion.choices[0].message.content
    except Exception as e:
        return f"Lỗi: {e}"


# Initialize ApifyClient securely
apify_client = ApifyClient(APIFY_API_KEY)

# Regex pattern
post_pattern = re.compile(r"#[-\w.,:;!?(){}\[\]\"'_+/\\|*]+")

facebook_pattern = re.compile(r'^[A-Za-z0-9_.]+$')


class Post():
    def __init__(self, text):
        self.text = text
        self.text_limit = text if len(text) < 100 else text[:100] + "..."
        self.summary = summarize(text)
        if self.summary:
            if "Tích cực" in self.summary:
                self.sentiment = POS
            elif "Tiêu cực" in self.summary:
                self.sentiment = NEG
            else:
                self.sentiment = NEU


st.title("📌 Phân tích Confessions")
st.write("Lấy dữ liệu từ Confessions và phân tích nội dung")

# URL confess
confess = st.text_input("Link Confessions",
                        placeholder="eg. https://www.facebook.com/Utc2Confessions")

if facebook_pattern.match(confess):
    is_valid_link = True
else:
    is_valid_link = False

# Maximun Posts
options = [str(i) for i in range(10, 51, 10)]
posts_num = st.selectbox("Số lượng bài viết", options)


# Button to fetch posts
if st.button("📥 Lấy bài đăng mới", disabled=is_valid_link):
    with st.spinner("Đang phân tích..."):
        run_input = {
            "startUrls": [{"url": confess}],
            "resultsLimit": int(posts_num) if posts_num else 10
        }
        run = apify_client.actor("KoJrdxJCTtpon81KY").call(run_input=run_input)

        for item in apify_client.dataset(run["defaultDatasetId"]).iterate_items():
            post_text = item.get("text", "No text")
            # get like and comments
            if post_pattern.match(post_text):
                post = Post(post_text)

                st.write(f"**📝 Nội Dung Gốc:** {post.text_limit}")
                st.write(f"**👍 Lượt likes:** {item.get("likes", 0)}")
                st.write(f"**💬 Lượt comments:** {item.get("comments", 0)}")

                if post.summary:
                    st.write(f"**📌 Tóm tắt:**")
                    st.write(post.summary)

                    # Display sentiment label
                    if post.sentiment == POS:
                        sentiment_label = '<span style="color: green; font-weight: bold;">Tích cực</span>'
                    elif post.sentiment == NEG:
                        sentiment_label = '<span style="color: red; font-weight: bold;">Tiêu cực</span>'
                    else:
                        sentiment_label = '<span style="color: gray; font-weight: bold;">Trung lập</span>'

                    st.markdown(
                        f"**📊 Cảm xúc:** {sentiment_label}", unsafe_allow_html=True)
                else:
                    st.write("Xài free nên thông cảm, lâu lâu lỗi...")

                st.divider()

        # with st.container():
        #     with open("data.csv", mode="r", encoding="utf-8") as file:
        #         reader = csv.reader(file)
        #         next(reader)  # Skip the header row
        #         for row in reader:
        #             post = Post(row[0])
