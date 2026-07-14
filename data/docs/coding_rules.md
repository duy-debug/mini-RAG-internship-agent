# Quy ước phát triển phần mềm

## Branch và commit

Branch tính năng dùng mẫu `feature/<mo-ta-ngan>`. Branch sửa lỗi dùng mẫu `fix/<mo-ta-ngan>`. Branch hotfix cho production dùng mẫu `hotfix/<mo-ta-ngan>`. Branch release dùng mẫu `release/<version>`. Branch cá nhân dùng mẫu `dev/<ten>/<mo-ta>`. Không tạo branch trùng tên hoặc branch có tên chung chung như `fix-bug` hay `update-code`. Mỗi branch chỉ chứa một đơn vị công việc duy nhất. Khi hoàn thành, branch phải được xóa trên remote sau khi merge.

Commit áp dụng Conventional Commits. Ví dụ: `feat(auth): thêm đăng nhập bằng JWT`, `fix(booking): ngăn đặt trùng slot`, `docs: cập nhật hướng dẫn chạy`. Các loại commit được phép gồm: `feat`, `fix`, `docs`, `style`, `refactor`, `perf`, `test`, `chore`, `ci`. Mỗi commit chỉ chứa một thay đổi logic duy nhất. Không commit code chưa chạy được, code có debug statement hoặc code chứa secret. Nội dung commit phải giải thích được lý do thay đổi, không viết chung chung như "sửa lỗi" hay "update". Với commit có nhiều thay đổi, dùng dòng tiêu đề ngắn dưới 72 ký tự và thân commit mô tả chi tiết từng thay đổi.

## Pull request

Mỗi pull request phải mô tả mục tiêu, thay đổi chính, cách kiểm thử và rủi ro. Pull request cần ít nhất một người review trước khi merge. Tác giả không tự merge PR của chính mình. Người review có trách nhiệm kiểm tra logic, coding convention, bảo mật và hiệu năng. Nếu PR có thay đổi lớn hơn 400 dòng code, cần chia nhỏ thành nhiều PR hoặc có giải trình lý do. Mỗi PR phải kèm ảnh chụp màn hình hoặc video demo nếu thay đổi giao diện người dùng.

Không merge khi build hoặc test bắt buộc đang thất bại. Pipeline CI phải chạy đầy đủ các bước: lint, typecheck, unit test, integration test, build. Nếu pipeline thất bại, tác giả phải sửa trước khi yêu cầu review lại. Không dùng quyền admin để merge PR bất chấp pipeline đỏ. Với hotfix production, có thể bỏ qua một số bước kiểm tra nhưng phải có phê duyệt của lead kỹ thuật và tạo ticket để bổ sung test sau.

## Kiểm thử

Thay đổi nghiệp vụ phải có test cho luồng đúng, luồng sai và trường hợp biên. Với authentication, authorization, thanh toán, migration và xử lý đồng thời, cần verify nặng và chạy trên môi trường test trước. Mọi hàm public trong module phải có unit test với độ phủ tối thiểu 80%. Hàm xử lý logic nghiệp vụ phải đạt độ phủ 100%. Test phải chạy độc lập, không phụ thuộc vào thứ tự và không phụ thuộc vào dữ liệu ngoài. Dùng mock cho các dependency bên ngoài như database, API, file system. Integration test chỉ chạy khi có biến môi trường `INTEGRATION_TEST` được bật.

Viết test theo pattern Arrange-Act-Assert. Đặt tên test function theo mẫu `test_<ten ham>_<dieu kien>_<ket qua mong doi>`. Ví dụ: `test_calculate_total_with_empty_cart_returns_zero`. Không dùng assert chung chung, mỗi assert phải kiểm tra một giá trị cụ thể. Khi phát hiện lỗi, viết test tái hiện lỗi trước khi sửa. Chạy toàn bộ test suite trước khi push. Không push code làm hỏng test của người khác.

## Code review

Code review tập trung vào: tính đúng đắn của logic, tuân thủ coding convention, bảo mật (SQL injection, XSS, CSRF, lộ secret), hiệu năng (N+1 query, vòng lặp không cần thiết), khả năng đọc hiểu (tên biến rõ ràng, function không quá dài), xử lý lỗi (không bỏ qua exception, không dùng catch chung). Người review không sửa code trực tiếp trong PR, chỉ góp ý qua comment. Nếu có bất đồng, giải quyết qua trao đổi trực tiếp hoặc họp. Không review PR khi đang mệt hoặc thiếu thời gian.

## Coding convention

Sử dụng 4 spaces cho indent, không dùng tab. Đặt tên biến bằng camelCase, tên class bằng PascalCase, tên hằng số bằng UPPER_SNAKE_CASE, tên hàm bằng camelCase. Độ dài tối đa một dòng code là 120 ký tự. Mỗi file không quá 500 dòng code. Mỗi hàm không quá 50 dòng. Import theo thứ tự: thư viện chuẩn, thư viện bên thứ ba, module nội bộ. Giữa các nhóm import cách một dòng trống. Không dùng wildcard import. Xóa import không dùng trước khi commit.

## Xử lý lỗi

Không dùng exception để điều khiển luồng. Xử lý lỗi ở tầng phù hợp, không catch exception quá sớm hoặc quá muộn. Log lỗi với đầy đủ stack trace và context. Không để lộ thông tin nhạy cảm trong error message trả về cho client. Với lỗi từ bên ngoài, chuyển đổi về dạng lỗi nội bộ trước khi xử lý. Luôn có fallback plan cho các lỗi không thể phục hồi.

## Tài liệu

Mỗi module phải có README mô tả cách cài đặt, cấu hình và chạy. Mỗi API endpoint phải được document bằng OpenAPI. Cập nhật tài liệu khi có thay đổi. Xóa tài liệu cũ không còn dùng. Viết changelog cho mỗi release.

## CI/CD

Pipeline CI chạy trên mỗi pull request và mỗi push lên nhánh chính. Pipeline CD chạy sau khi merge vào nhánh main và tag release. Môi trường staging dùng để kiểm thử trước production. Môi trường production chỉ được deploy qua pipeline, không deploy thủ công. Cấu hình môi trường phải được quản lý qua biến môi trường hoặc file config riêng, không hardcode.
