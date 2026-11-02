# 🌸 Airi Sensei Telegram Bot (@AiriSenseiBot)

> **Bot Telegram AI thông minh:** Hỏi đáp kiến thức đa lĩnh vực (B.AI / Gemini / OpenAI) và Tạo ảnh nghệ thuật (/image) với cơ chế Cascading Multi-Model Fallback, chạy 24/7 ổn định trên Render Web Service (Starter Plan $7/mo).

---

## 🌟 Tính Năng Nổi Bật

1. 💬 **Hỏi đáp thông minh (AI Q&A):**
   - Trò chuyện tự nhiên bằng tiếng Việt theo phong cách cô giáo "Airi Sensei".
   - Bộ nhớ hội thoại ngữ cảnh (Context Memory).
   - **Cascading Fallback:** Luân chuyển tự động qua các model hàng đầu:
     `DeepSeek-v4.1-Flash` ➔ `Qwen3.8-Flash` ➔ `GLM-5.3-Flash` ➔ `Minimax-m3.1-Flash` ➔ `Fallback Persona`.
2. 🎨 **Tạo ảnh nghệ thuật (/image):**
   - Lệnh: `/image <mô tả>` hoặc `/taoanh <mô tả>`.
   - Sinh ảnh 1024x1024 chất lượng cao bằng engine Flux (Pollinations) hoàn toàn miễn phí.
   - Tự động fallback sang engine Turbo nếu Flux bận.
3. ⚡ **Chạy 24/7 Always-On trên Render:**
   - Sử dụng gói **Starter ($7/tháng)** tận dụng $50 credit của Render (chạy hơn 7 tháng liên tục không lo ngủ đông).
   - Tích hợp HTTP Server nội bộ mở cổng `PORT` và endpoint `/health` phục vụ health check và monitoring.
4. 🔐 **Chuẩn 12-Factor App:**
   - 100% cấu hình qua Biến môi trường (Environment Variables). Không lưu secret trong mã nguồn.

---

## 📋 Danh Sách Lệnh Trên Telegram

| Lệnh | Mô tả |
|---|---|
| `/start` | Lời chào từ Airi Sensei và danh mục tiện ích |
| `/help` | Xem hướng dẫn sử dụng chi tiết |
| `/image <mô tả>` | Sinh ảnh bằng AI từ văn bản (Ví dụ: `/image phi hành gia anime`) |
| `/taoanh <mô tả>` | Cú pháp tiếng Việt tương đương `/image` |
| `/models` | Xem model chính, danh sách fallback và gateway AI |
| `/status` | Xem Uptime, tài nguyên và trạng thái kết nối |
| `/clear` | Xóa bộ nhớ ngữ cảnh để bắt đầu chủ đề mới |
| *Nhắn tin bất kỳ* | Hỏi đáp kiến thức với AI |

---

## ⚙️ Cấu Hình Biến Môi Trường (.env)

| Tên biến | Mặc định | Chức năng |
|---|---|---|
| `BOT_TOKEN` | *(Bắt buộc)* | Mã token lấy từ @BotFather |
| `AI_BASE_URL` | `https://api.b.ai/v1` | Cổng API OpenAI-compatible (B.AI, OpenAI, Groq,...) |
| `AI_API_KEY` | `""` | API Key của B.AI hoặc nhà cung cấp AI |
| `AI_PRIMARY_MODEL` | `deepseek-v4.1-flash` | Model chính ưu tiên trả lời câu hỏi |
| `AI_FALLBACK_MODELS` | `qwen3.8-flash,glm-5.3-flash,minimax-m3.1-flash` | Danh sách model dự phòng |
| `IMAGE_MODEL` | `flux` | Engine sinh ảnh chính |
| `IMAGE_FALLBACK_MODEL` | `turbo` | Engine sinh ảnh dự phòng |
| `PORT` | `8080` | Cổng HTTP Server trên Render |
| `HOST` | `0.0.0.0` | IP lắng nghe HTTP |
| `LOG_LEVEL` | `INFO` | Mức log (DEBUG / INFO / WARNING) |

---

## 🚀 Triển Khai Thủ Công Lên Render (Nếu Cần)

1. **Đẩy code lên GitHub:**
   ```bash
   git add .
   git commit -m "feat: initial commit"
   git push origin main
   ```
2. **Tạo Web Service trên Render:**
   - Truy cập [dashboard.render.com](https://dashboard.render.com).
   - Chọn **New +** ➔ **Web Service** ➔ Kết nối repository GitHub này.
   - Chọn môi trường: **Python** hoặc **Docker**.
   - Build Command: `pip install -r requirements.txt` (nếu dùng Python Native).
   - Start Command: `python -m app.main`.
   - Instance Type: Chọn **Starter ($7/month)** để dùng $50 credit.
   - Thêm Environment Variables: `BOT_TOKEN`, `AI_API_KEY`, `AI_BASE_URL`.
   - Bấm **Create Web Service**!
