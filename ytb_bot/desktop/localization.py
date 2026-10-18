"""Localize application messages at display boundaries without touching user data.

English remains the canonical internal language. Only complete catalog entries
match; unknown provider messages pass through. Captured template values are
inserted once, without interpreting any braces or markup inside their contents.
"""
import re
from string import Formatter


SUPPORTED_LANGUAGES = ('en', 'vi', 'zh-CN')

# English | Vietnamese | Simplified Chinese. These are application-owned strings,
# never workbook headings, channel values, saved keywords, drafts, or mail history.
_CATALOG = '''Enter an API key and at least one keyword.|Nhập API Key và ít nhất một từ khóa.|请输入 API 密钥和至少一个关键词。
Channel age must be at least 1 day, views at least 0, and depth between 1 and 5 pages.|Tuổi kênh phải từ 1 ngày, lượt xem từ 0 và độ sâu từ 1 đến 5 trang.|频道创建天数必须至少为 1 天，观看次数至少为 0，搜索深度为 1 至 5 页。
A scan is already running.|Một lượt quét đang chạy.|已有扫描正在运行。
Stopping after the current request; collected results will be saved.|Đang dừng sau yêu cầu hiện tại; kết quả đã thu thập sẽ được lưu.|当前请求完成后将停止；已收集的结果会被保存。
Searching across countries and languages; results depend on keywords and page depth.|Đang tìm kiếm trên nhiều quốc gia và ngôn ngữ; kết quả phụ thuộc vào từ khóa và độ sâu tìm kiếm.|正在跨国家和语言搜索；结果取决于关键词和搜索深度。
No new channels match the filters and have public contact details. Saved channels are skipped. Try more keywords or increase the search depth.|Không có kênh mới đáp ứng bộ lọc và có thông tin liên hệ công khai. Các kênh đã lưu được bỏ qua. Thử thêm từ khóa hoặc tăng độ sâu tìm kiếm.|没有符合筛选条件且提供公开联系方式的新频道。已保存的频道会被跳过。请尝试更多关键词或增加搜索深度。
Select a valid Excel file and worksheet.|Chọn file Excel và trang tính hợp lệ.|请选择有效的 Excel 文件和工作表。
The keyword list is invalid or too large.|Danh sách từ khóa không hợp lệ hoặc quá lớn.|关键词列表无效或过大。
No scans yet. Start a scan first.|Chưa có lượt quét nào. Hãy bắt đầu quét trước.|尚无扫描记录。请先开始扫描。
Channel not found in saved history.|Không tìm thấy kênh trong lịch sử đã lưu.|在已保存的历史记录中找不到该频道。
The draft has changed. Save and review it before sending.|Bản nháp đã thay đổi. Lưu và xem lại trước khi gửi.|草稿已更改。请先保存并检查，再发送。
This draft already has a send attempt. Check its history; edit and save a new revision to send again.|Bản nháp này đã có một lần gửi. Kiểm tra lịch sử; chỉnh sửa và lưu phiên bản mới để gửi lại.|此草稿已有发送尝试。请查看历史记录；如需再次发送，请编辑并保存新版本。
Check for updates whenever you need.|Kiểm tra bản cập nhật khi bạn cần.|您可以随时检查更新。
Invalid editing state.|Trạng thái chỉnh sửa không hợp lệ.|编辑状态无效。
The app is restarting to install an update.|Ứng dụng đang khởi động lại để cài đặt bản cập nhật.|应用正在重启以安装更新。
Invalid draft state.|Trạng thái bản nháp không hợp lệ.|草稿状态无效。
An email is being sent. Please wait for the result.|Một email đang được gửi. Hãy chờ kết quả.|邮件正在发送中。请等待结果。
Invalid display preferences.|Tùy chọn giao diện không hợp lệ.|显示偏好设置无效。
Unsupported language.|Ngôn ngữ không được hỗ trợ.|不支持此语言。
Wait for the update to finish before scanning.|Hãy chờ cập nhật hoàn tất trước khi quét.|请等待更新完成后再扫描。
Invalid keyword list.|Danh sách từ khóa không hợp lệ.|关键词列表无效。
Only HTTPS YouTube channel URLs can be opened.|Chỉ mở địa chỉ kênh YouTube HTTPS.|只能打开 HTTPS YouTube 频道链接。
Checking…|Đang kiểm tra…|正在检查…
You are using the latest version.|Bạn đang dùng bản mới nhất.|您正在使用最新版本。
Save the keyword table before updating and restarting.|Lưu bảng từ khóa trước khi cập nhật và khởi động lại.|请先保存关键词表，再更新并重启。
Save the contact draft before updating and restarting.|Lưu bản nháp liên hệ trước khi cập nhật và khởi động lại.|请先保存联系草稿，再更新并重启。
Wait for Gmail to return the send result before updating.|Chờ Gmail trả kết quả gửi trước khi cập nhật.|请等待 Gmail 返回发送结果后再更新。
Wait for the scan to finish before updating.|Chờ lượt quét hoàn tất trước khi cập nhật.|请等待扫描完成后再更新。
Check for updates first.|Hãy kiểm tra bản cập nhật trước.|请先检查更新。
Downloading update…|Đang tải bản cập nhật…|正在下载更新…
Restart canceled. You can update again when ready.|Đã hủy khởi động lại. Bạn có thể cập nhật lại khi sẵn sàng.|已取消重启。准备好后，您可以再次更新。
Gmail account protection is currently supported on Windows.|Tính năng bảo vệ tài khoản Gmail hiện được hỗ trợ trên Windows.|目前仅在 Windows 上支持 Gmail 账户保护。
Unable to open the credential vault for this Windows account.|Không mở được kho đăng nhập của tài khoản Windows này.|无法打开此 Windows 账户的凭据库。
The credential vault is in use by another window. Try again later.|Kho đăng nhập đang được cửa sổ khác sử dụng. Thử lại sau.|凭据库正由另一个窗口使用。请稍后重试。
The configuration file is too large.|File cấu hình quá lớn.|配置文件过大。
Select a Google OAuth Client JSON file for a Desktop app.|Chọn file JSON OAuth Client loại Desktop app của Google.|请选择 Google 桌面应用类型的 OAuth 客户端 JSON 文件。
The account could not be verified or offline access was not granted.|Chưa xác minh được tài khoản hoặc chưa được cấp quyền truy cập ngoại tuyến.|无法验证账户，或尚未授予离线访问权限。
Missing provider message ID|Thiếu mã thư do nhà cung cấp trả về|缺少服务提供商返回的邮件 ID
YTB-BOT: Connected. You can close this tab.|YTB-BOT: Đã kết nối. Bạn có thể đóng thẻ này.|YTB-BOT：已连接。您可以关闭此标签页。
Wait for the current account connection to finish.|Chờ kết nối tài khoản hiện tại hoàn tất.|请等待当前账户连接完成。
Import a Google Desktop OAuth Client file before connecting.|Nhập file OAuth Client Desktop của Google trước khi kết nối.|请先导入 Google 桌面 OAuth 客户端文件，再连接。
Invalid account identity|Danh tính tài khoản không hợp lệ|账户身份无效
Unable to connect to Gmail. Check the configuration, send permissions, and test account, then try again. The sign-in session expires after 3 minutes.|Chưa kết nối được Gmail. Kiểm tra cấu hình, quyền gửi và tài khoản thử nghiệm rồi thử lại. Phiên đăng nhập hết hạn sau 3 phút.|无法连接 Gmail。请检查配置、发送权限和测试账户后重试。登录会话将在 3 分钟后过期。
Invalid draft.|Bản nháp không hợp lệ.|草稿无效。
The subject can contain up to 200 characters and the body up to 50,000 characters.|Tiêu đề tối đa 200 ký tự, nội dung tối đa 50.000 ký tự.|主题最多可包含 200 个字符，正文最多可包含 50,000 个字符。
The subject must not contain line breaks.|Tiêu đề không được chứa xuống dòng.|主题不能包含换行符。
Select a contact from the saved channel data.|Chọn liên hệ trong dữ liệu đã lưu của kênh.|请从已保存的频道数据中选择联系人。
Save and review the draft before sending.|Lưu và xem lại bản nháp trước khi gửi.|请先保存并检查草稿，再发送。
Enter an email subject and body.|Nhập tiêu đề và nội dung email.|请输入邮件主题和正文。
The recipient must be a saved email address for this channel.|Người nhận phải là email đã lưu của kênh.|收件人必须是该频道已保存的电子邮件地址。
Select a connected Gmail account.|Chọn tài khoản Gmail đã kết nối.|请选择已连接的 Gmail 账户。
Unable to refresh sign-in. Reconnect the Gmail account.|Không làm mới được đăng nhập. Kết nối lại tài khoản Gmail.|无法刷新登录状态。请重新连接 Gmail 账户。
It is unknown whether Gmail accepted the email. Check Sent in Gmail before sending again.|Chưa rõ Gmail đã nhận thư hay chưa. Kiểm tra thư Đã gửi trong Gmail trước khi gửi lại.|无法确定 Gmail 是否已接受邮件。再次发送前，请检查 Gmail 的“已发送”文件夹。
Gmail accepted the send request. This status does not confirm delivery to the recipient.|Gmail đã nhận yêu cầu gửi. Trạng thái này không xác nhận thư đã đến người nhận.|Gmail 已接受发送请求。此状态并不表示邮件已送达收件人。
Only saved contact links for this channel can be opened.|Chỉ mở liên kết liên hệ đã lưu của kênh.|只能打开该频道已保存的联系链接。
Unable to open the browser. Copy the link and open it manually.|Không mở được trình duyệt. Sao chép liên kết và mở thủ công.|无法打开浏览器。请复制链接并手动打开。
The version must use the X.Y.Z format.|Phiên bản phải có định dạng X.Y.Z.|版本号必须使用 X.Y.Z 格式。
Invalid update download URL.|Địa chỉ tải cập nhật không hợp lệ.|更新下载链接无效。
The release is missing the EXE or SHA-256 file.|Bản phát hành thiếu file EXE hoặc SHA-256.|此版本缺少 EXE 或 SHA-256 文件。
Invalid update size.|Kích thước bản cập nhật không hợp lệ.|更新大小无效。
Unable to verify the build with the same version: GitHub is missing SHA-256.|Không xác minh được bản build cùng phiên bản: GitHub thiếu SHA-256.|无法验证相同版本号的构建：GitHub 缺少 SHA-256。
Invalid update SHA-256 checksum.|SHA-256 của bản cập nhật không hợp lệ.|更新的 SHA-256 校验和无效。
The update exceeds its published size.|Bản cập nhật vượt kích thước đã công bố.|更新超出了已公布的大小。
The update does not match SHA-256 or the download is incomplete.|Bản cập nhật không khớp SHA-256 hoặc tải chưa đầy đủ.|更新与 SHA-256 不匹配，或下载不完整。
The update is not a Windows executable.|Bản cập nhật không phải file thực thi Windows.|更新不是 Windows 可执行文件。
Automatic updates are only supported by the Windows desktop EXE.|Tự cập nhật chỉ hỗ trợ bản desktop EXE trên Windows.|仅 Windows 桌面 EXE 支持自动更新。
Invalid staged update file.|File cập nhật tạm không hợp lệ.|暂存的更新文件无效。
Update failed. The previous version has been preserved.|Cập nhật thất bại. Bản cũ được giữ lại.|更新失败。已保留之前的版本。
App did not close within 120 seconds.|Ứng dụng không đóng trong vòng 120 giây.|应用未在 120 秒内关闭。
Checksum mismatch.|Mã kiểm tra không khớp.|校验和不匹配。
React has not been built. Run npm ci --prefix frontend and npm run build --prefix frontend.|Chưa build React. Chạy npm ci --prefix frontend và npm run build --prefix frontend.|React 尚未构建。请运行 npm ci --prefix frontend 和 npm run build --prefix frontend。
Sending email|Email đang gửi|正在发送邮件
Gmail is processing the request. Closing now may leave the result unknown. Close anyway?|Gmail đang xử lý yêu cầu. Đóng bây giờ có thể khiến kết quả chưa rõ. Bạn vẫn muốn đóng?|Gmail 正在处理请求。现在关闭可能导致结果未知。仍要关闭吗？
Unsaved contact|Liên hệ chưa lưu|未保存的联系人
The contact draft has unsaved changes. Closing the app will discard them. Close anyway?|Bản nháp liên hệ có thay đổi chưa lưu. Đóng ứng dụng sẽ bỏ các thay đổi đó. Bạn vẫn muốn đóng?|联系草稿有未保存的更改。关闭应用将丢弃这些更改。仍要关闭吗？
Unsaved keywords|Từ khóa chưa lưu|未保存的关键词
The keyword table has unsaved changes. Closing the app will discard them. Close anyway?|Bảng từ khóa có thay đổi chưa lưu. Đóng ứng dụng sẽ bỏ các thay đổi đó. Bạn vẫn muốn đóng?|关键词表有未保存的更改。关闭应用将丢弃这些更改。仍要关闭吗？
Close YTB-BOT|Đóng YTB-BOT|关闭 YTB-BOT
The scan is still running. Closing now may lose unsaved results. Close anyway?|Lượt quét chưa xong. Đóng bây giờ có thể mất kết quả chưa lưu. Bạn vẫn muốn đóng?|扫描仍在进行中。现在关闭可能会丢失未保存的结果。仍要关闭吗？'''

_CATALOG += '''
Invalid batch draft.|Bản nháp gửi hàng loạt không hợp lệ.|批量邮件草稿无效。
Select between 1 and 100 unique email groups.|Chọn từ 1 đến 100 nhóm email không trùng nhau.|请选择 1 至 100 个不重复的邮件组。
Enter a valid account, subject (200 characters) and body (50,000 characters).|Nhập tài khoản hợp lệ, tiêu đề tối đa 200 ký tự và nội dung tối đa 50.000 ký tự.|请输入有效账户、主题（最多 200 字符）和正文（最多 50,000 字符）。
Only saved email groups can be selected.|Chỉ chọn các nhóm email đã lưu.|只能选择已保存的邮件组。
A mail batch is already running.|Một đợt gửi hàng loạt đang chạy.|已有批量邮件正在发送。
This batch already started. Prepare and review a new draft.|Đợt gửi này đã bắt đầu. Hãy tạo và xem lại bản nháp mới.|此批次已开始。请准备并检查新草稿。
The reviewed sender is no longer connected.|Tài khoản gửi đã xem lại không còn kết nối.|已确认的发件账户已断开连接。
Batch stopped.|Đã dừng đợt gửi.|批次已停止。
Sender account disconnected.|Tài khoản gửi đã ngắt kết nối.|发件账户已断开连接。
Batch not found.|Không tìm thấy đợt gửi.|找不到批次。
This recipient already belongs to a bulk send attempt. Check the contact history.|Người nhận này đã có lần gửi hàng loạt. Hãy kiểm tra lịch sử liên hệ.|此收件人已有批量发送尝试。请检查联系历史。
Wait for the update to finish before sending mail.|Chờ cập nhật hoàn tất trước khi gửi thư.|请等待更新完成后再发送邮件。
A mail send is already running. Wait for its result.|Một lượt gửi thư đang chạy. Hãy chờ kết quả.|邮件正在发送。请等待结果。
Review the bulk email draft before sending.|Xem lại bản nháp gửi hàng loạt trước khi gửi.|请先检查批量邮件草稿，再发送。
Finish the bulk send and save its draft before updating.|Hoàn tất đợt gửi và lưu bản nháp trước khi cập nhật.|请完成批量发送并保存草稿后再更新。
Bulk email is running|Đang gửi thư hàng loạt|正在批量发送邮件
Closing stops the remaining emails. The current request may have an uncertain outcome. Close anyway?|Đóng sẽ dừng các thư còn lại. Yêu cầu hiện tại có thể chưa rõ kết quả. Bạn vẫn muốn đóng?|关闭会停止剩余邮件。当前请求的结果可能不确定。仍要关闭吗？
Unsaved bulk draft|Bản nháp hàng loạt chưa lưu|未保存的批量邮件草稿
The bulk email draft has unsaved changes. Closing will discard them. Close anyway?|Bản nháp hàng loạt có thay đổi chưa lưu. Đóng sẽ bỏ các thay đổi đó. Bạn vẫn muốn đóng?|批量邮件草稿有未保存的更改。关闭将丢弃这些更改。仍要关闭吗？'''

_STATIC = {}
for _line in _CATALOG.splitlines():
    _english, _vi, _zh = _line.split('|')
    _STATIC[_english] = {'vi': _vi, 'zh-CN': _zh}

# Each variable has an explicit grammar. Free-text captures are greedy so the
# terminal numeric marker is used even when user text contains similar markers.
_VARIABLES = {
    'count': r'\d+', 'index': r'\d+', 'total': r'\d+',
    'views': r'\d[\d,]*', 'code': r'\d{3}',
    'version': r'\d+\.\d+\.\d+', 'keyword': r'.*',
    'name': r'.*', 'detail': r'.*', 'path': r'.*',
}
_TEMPLATES = (
    ('Checked {count} channels in history. Only new channel IDs will be included.',
     'Đã kiểm tra {count} kênh trong lịch sử. Chỉ các mã kênh mới được đưa vào.',
     '已检查历史记录中的 {count} 个频道。仅包含新的频道 ID。'),
    ('Scanning: {keyword} ({index}/{total})',
     'Đang quét: {keyword} ({index}/{total})', '正在扫描：{keyword}（{index}/{total}）'),
    ('Found {count} channels with recent videos. Checking filters...',
     'Tìm thấy {count} kênh có video mới. Đang kiểm tra bộ lọc...',
     '找到 {count} 个最近发布视频的频道。正在检查筛选条件…'),
    ('Match: {name} · {views} views',
     'Phù hợp: {name} · {views} lượt xem', '匹配：{name} · {views} 次观看'),
    ('Skipped {count} channels already in history.',
     'Đã bỏ qua {count} kênh đã có trong lịch sử.', '已跳过历史记录中已有的 {count} 个频道。'),
    ('Saved {count} channels. Open Results to review them.',
     'Đã lưu {count} kênh. Mở Kết quả để xem lại.', '已保存 {count} 个频道。打开“结果”以查看。'),
    ('Could not save results: {detail}',
     'Không lưu được kết quả: {detail}', '无法保存结果：{detail}'),
    ('Update available: v{version}',
     'Có bản cập nhật v{version}', '有可用更新：v{version}'),
    ('Unable to check for updates (HTTP {code}).',
     'Không thể kiểm tra cập nhật (HTTP {code}).', '无法检查更新（HTTP {code}）。'),
    ('Gmail rejected the request (HTTP {code}). Check send permissions and the account.',
     'Gmail từ chối yêu cầu (HTTP {code}). Kiểm tra quyền gửi và tài khoản.',
     'Gmail 拒绝了请求（HTTP {code}）。请检查发送权限和账户。'),
    ('Could not open YTB-BOT. Check the Microsoft Edge WebView2 Runtime.\nDetails: {path}',
     'Không mở được YTB-BOT. Kiểm tra Microsoft Edge WebView2 Runtime.\nChi tiết: {path}',
     '无法打开 YTB-BOT。请检查 Microsoft Edge WebView2 Runtime。\n详细信息：{path}'),
)


def _compile_template(source):
    parts = []
    for literal, field, format_spec, conversion in Formatter().parse(source):
        parts.append(re.escape(literal))
        if field is not None:
            if format_spec or conversion:
                raise ValueError('Localization templates must use plain named fields.')
            parts.append(f'(?P<{field}>{_VARIABLES[field]})')
    return re.compile(''.join(parts), re.DOTALL)


_DYNAMIC = tuple((_compile_template(english), {'vi': vi, 'zh-CN': zh})
                 for english, vi, zh in _TEMPLATES)


def translate_message(message, language='en'):
    """Translate a known display message; unsupported locales fall back to English.

    No fuzzy matching or recursive translation occurs. Callers should apply this
    only to app-owned display metadata, never to channel records or user content.
    """
    if language not in ('vi', 'zh-CN') or not isinstance(message, str):
        return message
    if message in _STATIC:
        return _STATIC[message][language]
    for pattern, translations in _DYNAMIC:
        match = pattern.fullmatch(message)
        if match is not None:
            return translations[language].format_map(match.groupdict())
    return message
