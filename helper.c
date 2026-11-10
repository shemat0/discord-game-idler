#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <shellapi.h>
#include <wchar.h>

static wchar_t body[2048];
static COLORREF background = RGB(16, 23, 34);
static COLORREF foreground = RGB(230, 237, 245);

static void paint(HWND window, HDC dc)
{
    RECT area;
    GetClientRect(window, &area);
    SetDCBrushColor(dc, background);
    FillRect(dc, &area, GetStockObject(DC_BRUSH));
    InflateRect(&area, -16, -16);
    SetBkMode(dc, TRANSPARENT);
    SetTextColor(dc, foreground);
    SelectObject(dc, GetStockObject(DEFAULT_GUI_FONT));
    DrawTextW(dc, body, -1, &area, DT_LEFT | DT_TOP | DT_WORDBREAK | DT_NOPREFIX);
}

static LRESULT CALLBACK window_proc(HWND window, UINT message, WPARAM wparam, LPARAM lparam)
{
    PAINTSTRUCT ps;
    switch (message) {
    case WM_PAINT:
        paint(window, BeginPaint(window, &ps));
        EndPaint(window, &ps);
        return 0;
    case WM_PRINTCLIENT:
        paint(window, (HDC)wparam);
        return 0;
    case WM_PRINT:
        if (lparam & PRF_CLIENT) paint(window, (HDC)wparam);
        return 0;
    case WM_DESTROY:
        PostQuitMessage(0);
        return 0;
    }
    return DefWindowProcW(window, message, wparam, lparam);
}

static wchar_t *next_line(wchar_t *line)
{
    wchar_t *end = wcschr(line, L'\n');
    if (!end) return NULL;
    *end = L'\0';
    if (end > line && end[-1] == L'\r') end[-1] = L'\0';
    return end + 1;
}

static void refresh(HWND window, const wchar_t *name, const wchar_t *path, FILETIME *previous)
{
    WIN32_FILE_ATTRIBUTE_DATA attributes;
    if (!GetFileAttributesExW(path, GetFileExInfoStandard, &attributes) ||
        CompareFileTime(previous, &attributes.ftLastWriteTime) == 0)
        return;
    HANDLE file = CreateFileW(path, GENERIC_READ, FILE_SHARE_READ | FILE_SHARE_WRITE | FILE_SHARE_DELETE,
                              NULL, OPEN_EXISTING, FILE_ATTRIBUTE_NORMAL, NULL);
    if (file == INVALID_HANDLE_VALUE) return;
    char utf8[4096];
    wchar_t text[4096];
    DWORD bytes = 0;
    BOOL ok = ReadFile(file, utf8, sizeof(utf8), &bytes, NULL);
    CloseHandle(file);
    if (!ok || !bytes || bytes >= sizeof(utf8)) return;
    int length = MultiByteToWideChar(CP_UTF8, MB_ERR_INVALID_CHARS, utf8, bytes, text, ARRAYSIZE(text) - 1);
    if (!length) return;
    text[length] = L'\0';
    wchar_t *suffix = next_line(text);
    wchar_t *description = suffix ? next_line(suffix) : NULL;
    if (!description) return;
    BOOL light = wcscmp(text, L"light") == 0;
    background = light ? RGB(246, 248, 251) : RGB(16, 23, 34);
    foreground = light ? RGB(31, 41, 55) : RGB(230, 237, 245);
    wcsncpy_s(body, ARRAYSIZE(body), description, _TRUNCATE);
    wchar_t title[512];
    _snwprintf_s(title, ARRAYSIZE(title), _TRUNCATE, L"%ls \x2014 %ls", name, suffix);
    SetWindowTextW(window, title);
    InvalidateRect(window, NULL, FALSE);
    *previous = attributes.ftLastWriteTime;
}

int WINAPI wWinMain(HINSTANCE instance, HINSTANCE previous_instance, LPWSTR command, int show)
{
    int argc;
    LPWSTR *argv = CommandLineToArgvW(GetCommandLineW(), &argc);
    if (!argv || argc != 4) {
        LocalFree(argv);
        return 2;
    }
    HANDLE parent = OpenProcess(SYNCHRONIZE, FALSE, wcstoul(argv[1], NULL, 10));
    if (!parent) {
        LocalFree(argv);
        return 1;
    }
    WNDCLASSW cls = {0};
    cls.lpfnWndProc = window_proc;
    cls.hInstance = instance;
    cls.hCursor = LoadCursorW(NULL, IDC_ARROW);
    cls.lpszClassName = L"DiscordGameIdlerHelper";
    RegisterClassW(&cls);
    DWORD style = WS_OVERLAPPED | WS_CAPTION | WS_SYSMENU | WS_MINIMIZEBOX;
    RECT area = {0, 0, 310, 105};
    AdjustWindowRect(&area, style, FALSE);
    HWND window = CreateWindowExW(WS_EX_APPWINDOW, cls.lpszClassName, argv[2], style,
                                  CW_USEDEFAULT, CW_USEDEFAULT, area.right - area.left, area.bottom - area.top,
                                  NULL, NULL, instance, NULL);
    if (window) {
        FILETIME last = {0};
        refresh(window, argv[2], argv[3], &last);
        ShowWindow(window, SW_SHOWNOACTIVATE);
        BOOL running = TRUE;
        ULONGLONG next_refresh = GetTickCount64() + 750;
        while (running) {
            ULONGLONG now = GetTickCount64();
            if (now >= next_refresh) {
                refresh(window, argv[2], argv[3], &last);
                next_refresh = now + 750;
            }
            DWORD result = MsgWaitForMultipleObjects(1, &parent, FALSE, (DWORD)(next_refresh - now), QS_ALLINPUT);
            if (result == WAIT_OBJECT_0 || result == WAIT_FAILED) break;
            MSG message;
            while (PeekMessageW(&message, NULL, 0, 0, PM_REMOVE)) {
                if (message.message == WM_QUIT) {
                    running = FALSE;
                    break;
                }
                TranslateMessage(&message);
                DispatchMessageW(&message);
            }
        }
        if (IsWindow(window)) DestroyWindow(window);
    }
    CloseHandle(parent);
    LocalFree(argv);
    return window ? 0 : 1;
}
