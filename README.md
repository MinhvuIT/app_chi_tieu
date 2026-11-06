# Quản lý chi tiêu

Ứng dụng lưu giao dịch trên Supabase để dữ liệu vẫn tồn tại khi Streamlit
Community Cloud khởi động lại. File CSV trong `data/` chỉ dùng để chuyển dữ liệu
cũ một lần; ứng dụng không tự động chuyển hoặc đồng bộ file này.

## Thiết lập Supabase

1. Tạo một project Supabase (gói miễn phí có thể tạm ngưng project không hoạt
   động; kiểm tra giới hạn và chính sách hiện hành của Supabase).
2. Trong SQL Editor của project, chạy nội dung `supabase/schema.sql`.
3. Trong Settings → API, lấy Project URL và server-side secret key (hoặc khóa
   `service_role` cũ). Không dùng `anon` key: bảng bật Row Level Security và
   không cấp quyền công khai.
4. Sao chép `.streamlit/secrets.toml.example` thành
   `.streamlit/secrets.toml`, rồi điền:

   ```toml
   SUPABASE_URL = "https://YOUR-PROJECT.supabase.co"
   SUPABASE_KEY = "YOUR-SUPABASE-SECRET-KEY"
   APP_PASSWORD = "a-long-unique-password"
   ```

   Giữ file `secrets.toml` ngoài Git. Khóa Supabase có quyền cao chỉ được dùng
   phía server, trong ứng dụng Streamlit; không đưa khóa vào mã trình duyệt,
   repository công khai hoặc chia sẻ cho người dùng. Mật khẩu ứng dụng bảo vệ
   giao diện cá nhân, nhưng đây là một mật khẩu dùng chung, không phải hệ thống
   tài khoản nhiều người.

## Chuyển dữ liệu CSV cũ

Trên Python 3.11 trở lên, trước khi deploy, cài dependencies và cấu hình file
secrets ở trên trên máy có file CSV cũ, sau đó chạy:

```powershell
python -m pip install -r requirements.txt
python migrate_csv.py
```

Script chỉ nhập vào bảng rỗng và từ chối chạy tiếp nếu bảng đã có dữ liệu. Script
không nhập lại ID cũ; Supabase tự sinh ID mới. Nếu một lần nhập bị lỗi giữa chừng,
kiểm tra dữ liệu trên Supabase trước khi xóa dữ liệu nhập dở và chạy lại.
Sau khi xác nhận giao dịch đã có trên Supabase, giữ file CSV ở máy cá nhân; file
này đã được thêm vào `.gitignore` để tránh đẩy dữ liệu tài chính lên GitHub.

## Deploy lên Streamlit Community Cloud

1. Đẩy mã nguồn lên GitHub. `.streamlit/secrets.toml` và
   `data/transactions.csv` đã được loại khỏi Git bằng `.gitignore`.
2. Tạo app Community Cloud từ repository, chọn `app.py` làm entry point.
3. Trong App settings → Secrets, khai báo cùng ba giá trị
   `SUPABASE_URL`, `SUPABASE_KEY`, `APP_PASSWORD` theo định dạng TOML ở trên.
4. Deploy và đăng nhập bằng `APP_PASSWORD`.

Community Cloud có thể khởi động lại bất kỳ lúc nào; dữ liệu giao dịch nằm trên
Supabase nên không phụ thuộc vào filesystem tạm của app. Nếu ứng dụng cần nhiều
người dùng hoặc dữ liệu nhạy cảm hơn, hãy thay mật khẩu dùng chung bằng xác thực
người dùng và chính sách RLS theo từng người dùng.
