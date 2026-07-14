# Chính sách bảo mật

## Secret và credential

Không ghi API key, access token, password, private key hoặc chuỗi kết nối production trực tiếp trong source code. Không commit các giá trị này lên Git. Secret phải được đọc từ biến môi trường hoặc secret manager được tổ chức phê duyệt. Khi chia sẻ log hoặc đoạn code cho công cụ AI, phải xóa hoặc che secret trước. Sử dụng công cụ quét secret tự động trong pipeline CI để phát hiện secret bị lộ. Nếu phát hiện secret trong commit, coi secret đó đã bị lộ và thực hiện rotate ngay lập tức.

Mỗi ứng dụng có một bộ secret riêng, không dùng chung secret giữa các môi trường development, staging và production. Secret production có quyền truy cập hạn chế và chỉ cấp cho người cần. Thời hạn của secret tối đa 90 ngày, sau đó phải rotate. Lịch sử rotate secret phải được ghi lại trong audit log. Không lưu secret trong file cấu hình dưới dạng plaintext ngay cả trên máy local. Dùng công cụ mã hóa như `sops` hoặc `git-crypt` nếu cần lưu secret trong repo.

## Dữ liệu cá nhân

Email, số điện thoại, địa chỉ, mã người dùng và dữ liệu khách hàng phải được giảm thiểu và ẩn danh trước khi gửi tới dịch vụ bên ngoài. Không dùng dữ liệu production làm ví dụ nếu chưa có phê duyệt và biện pháp bảo vệ phù hợp. Phân loại dữ liệu thành bốn mức: công khai, nội bộ, nhạy cảm và hạn chế. Dữ liệu mức nhạy cảm và hạn chế phải được mã hóa khi lưu trữ và truyền tải. Truy cập dữ liệu mức hạn chế phải được ghi log và giám sát. Việc xuất dữ liệu mức hạn chế ra khỏi hệ thống phải có phê duyệt bằng văn bản.

Tuân thủ quy định bảo vệ dữ liệu cá nhân theo Nghị định 13/2023/NĐ-CP của Chính phủ. Người dùng có quyền yêu cầu xem, sửa và xóa dữ liệu cá nhân của họ. Yêu cầu này phải được xử lý trong vòng 7 ngày làm việc. Khi xảy ra vi phạm dữ liệu, thông báo cho cơ quan chức năng trong vòng 72 giờ và thông báo cho người bị ảnh hưởng trong vòng 7 ngày.

## Sự cố

Nếu nghi ngờ secret đã bị lộ, phải dừng sử dụng secret đó, báo người phụ trách và thực hiện rotate/revoke theo quy trình của tổ chức. Không chỉ xóa secret khỏi commit rồi tiếp tục sử dụng. Phân loại sự cố thành ba mức: thấp, trung bình và cao. Sự cố mức cao phải được xử lý trong vòng 1 giờ, mức trung bình trong vòng 4 giờ, mức thấp trong vòng 24 giờ. Mỗi sự cố phải có ticket riêng và được theo dõi đến khi đóng. Sau khi xử lý xong, viết báo cáo postmortem gồm nguyên nhân gốc rễ, tác động, biện pháp khắc phục và bài học kinh nghiệm. Họp review sự cố hàng tháng để cải thiện quy trình.

## Quyền truy cập

Nguyên tắc least privilege được áp dụng cho tài khoản, token và dịch vụ. Mọi thay đổi quyền production cần người có thẩm quyền review. Tài khoản người dùng được cấp quyền theo vai trò: admin, developer, viewer. Admin có toàn quyền trên môi trường của họ. Developer có quyền đọc và ghi trên môi trường development và staging, chỉ đọc trên production. Viewer chỉ có quyền đọc trên tất cả môi trường.

Rà soát quyền truy cập định kỳ ba tháng một lần. Thu hồi quyền của tài khoản không hoạt động quá 90 ngày. Khi nhân viên nghỉ việc, thu hồi toàn bộ quyền trong vòng 24 giờ. Sử dụng xác thực hai yếu tố cho tất cả tài khoản có quyền truy cập production. Tài khoản service dùng token thay vì mật khẩu, token có thời hạn tối đa một năm và được rotate sáu tháng một lần.

## Bảo mật ứng dụng

Áp dụng OWASP Top 10 cho tất cả ứng dụng web. Kiểm tra bảo mật trong pipeline CI gồm: quét dependency cho thư viện bên thứ ba, quét SAST cho source code, quét container image nếu dùng Docker. Kiểm tra thâm nhập được thực hiện sáu tháng một lần bởi bên thứ ba độc lập. Các lỗ hổng mức cao phải được sửa trong vòng 7 ngày, mức trung bình trong vòng 30 ngày, mức thấp trong vòng 90 ngày.

Xác thực đầu vào từ người dùng để phòng chống SQL injection, XSS và command injection. Sử dụng prepared statement cho tất cả truy vấn database. Mã hóa tất cả dữ liệu nhạy cảm bằng AES-256 khi lưu trữ. Sử dụng HTTPS cho tất cả API endpoint. Header bảo mật CSP, X-Frame-Options và X-Content-Type-Options phải được thiết lập trên tất cả response.

## Audit log

Tất cả hành động sau phải được ghi log: đăng nhập, đăng xuất, thay đổi quyền, thay đổi cấu hình, truy cập dữ liệu nhạy cảm, thao tác xóa dữ liệu. Mỗi log entry gồm: thời gian, người thực hiện, hành động, tài nguyên bị tác động, địa chỉ IP, kết quả thành công hay thất bại. Log phải được lưu trữ tối thiểu một năm và không thể bị sửa đổi hoặc xóa bởi người dùng thông thường. Audit log phải được giám sát tự động và cảnh báo khi phát hiện hành vi bất thường.

## Đào tạo bảo mật

Tất cả nhân viên và thực tập sinh phải tham gia khóa đào tạo bảo mật cơ bản trong tuần đầu tiên. Đào tạo bao gồm: phát hiện email lừa đảo, quản lý mật khẩu, bảo vệ thiết bị, báo cáo sự cố. Đào tạo nâng cao được tổ chức sáu tháng một lần cho developer và admin. Kiểm tra kiến thức bảo mật hàng năm. Kết quả kiểm tra được lưu trong hồ sơ nhân viên.
